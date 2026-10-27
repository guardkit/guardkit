"""Declared install cache for a repo with declared components (web readiness).

What the implementation must do
-------------------------------
When the root ``.guardkit/config.yaml`` declares ``toolchain.install``, the
bootstrap runs that one command for the whole repo. Today its success marker
covers only the declaration file, so a builder who changes
``apps/web/package-lock.json`` or ``apps/api/go.sum`` leaves the verifier on
the old dependencies. The repair belongs to the reliability lane (web
readiness design review, finding R7); these tests state the behaviour it must
deliver. They were written as strict xfails and the marks were removed when
the follow-up fixes of 13 October 2026 landed.

1. The marker for a declared install covers the declaration file, the
   recognised dependency files (manifests and lockfiles) at the root, the same
   files in every declared component ``cwd``, and recognised manifests in the
   directories between a component and the root (workspace configuration).
2. Which directories are read comes from the declaration's ``components``,
   not from hard-coded file names or paths. Which files count reuses the
   existing recognised dependency-file lists; ``go.sum`` is one of them.
3. The hash is deterministic: each input's relative POSIX path plus its
   contents, in sorted order, so an edit, an addition, a removal or a rename
   all change it.
4. The marker also records an execution identity: the declared ``runtime``
   pins plus the image identity from the environment (``FORGE_IMAGE_IDENTITY``,
   which the reliability lane forwards into the build container). A marker
   made under another identity is not reused. The execution identity includes
   the worktree's own root, so a copied or new worktree never reuses another
   worktree's marker, while file contents are hashed by relative path.
5. Traversal is bounded. It never leaves the worktree and never reads inside
   dependency or cache folders such as ``node_modules``. A component ``cwd``
   that escapes the worktree, including through a symlink, fails the
   bootstrap with a clear message. A ``..`` or absolute component ``cwd`` is
   refused visibly; it must not silently drop the whole declaration and fall
   back to guessing from manifest files.
6. An unreadable dependency input fails the bootstrap; it never produces a
   success or a cache hit. A failed install stays failed and retryable under
   the existing limits.
7. A declared root install is always essential, whatever stacks the change
   touched. The per-turn refresh scopes essential stacks by the changed
   file names (a ``go.sum`` edit reads as ``go``), but the declared root
   install carries one label for the whole repo (``node`` or ``declared``), so
   its failure must still fail the refresh rather than be counted as a
   non-blocking warning and saved as success.
8. A component's own ``install:`` stays declared but not run, and repos
   without a declared install behave exactly as before (no new discovery).

The tests use only public seams: ``ProjectEnvironmentDetector.detect``,
``EnvironmentBootstrapper.bootstrap``, ``refresh_environment_for_changes`` and
the files on disk. "The install ran" means the declared command reached
``subprocess.run``. Version and env probes pass through to the real
``subprocess.run``, so an implementation may probe tools that way; nothing is
ever installed.

Eleven of these tests passed before the repair (the guards); they pin
properties the implementation must keep.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import List
from unittest.mock import MagicMock, patch

import pytest
import yaml

from guardkit.orchestrator.environment_bootstrap import (
    EnvironmentBootstrapper,
    ProjectEnvironmentDetector,
    refresh_environment_for_changes,
    stacks_for_changed_manifests,
)

_REAL_RUN = subprocess.run

_DECLARED_INSTALL = ["npm", "ci"]

def _declare(root: Path, components: dict, runtime: dict | None = None) -> None:
    block: dict = {"install": " ".join(_DECLARED_INSTALL), "components": components}
    if runtime is not None:
        block["runtime"] = runtime
    cfg = root / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": block}), encoding="utf-8"
    )


_COMPONENTS = {
    "api": {"cwd": "apps/api", "test": "go test ./..."},
    "web": {"cwd": "apps/web", "test": "npm test"},
}
_RUNTIME = {"node": "v22.23.2", "go": "1.26.9"}


@pytest.fixture
def web_repo(tmp_path: Path) -> Path:
    """A neutral two-component repo: a Go API and a web app, two levels down."""
    root = tmp_path / "repo"
    (root / "apps" / "api").mkdir(parents=True)
    (root / "apps" / "web").mkdir(parents=True)
    (root / "package.json").write_text(
        '{"name":"root","private":true,"workspaces":["apps/web"]}\n', "utf-8"
    )
    (root / "package-lock.json").write_text('{"lockfileVersion":3}\n', "utf-8")
    (root / "apps" / "api" / "go.mod").write_text(
        "module example.com/api\n\ngo 1.26\n", "utf-8"
    )
    (root / "apps" / "api" / "go.sum").write_text(
        "example.com/dep v1.0.0 h1:aaaa=\n", "utf-8"
    )
    (root / "apps" / "web" / "package.json").write_text(
        '{"name":"web","version":"0.1.0"}\n', "utf-8"
    )
    (root / "apps" / "web" / "package-lock.json").write_text(
        '{"lockfileVersion":3,"packages":{}}\n', "utf-8"
    )
    _declare(root, _COMPONENTS, _RUNTIME)
    return root


def _declared_calls(mock_run: MagicMock) -> List[list]:
    return [c for c in mock_run.call_args_list if list(c.args[0]) == _DECLARED_INSTALL]


_PROBE_ARGS = frozenset({"--version", "-v", "version", "env"})


def _fake_run(returncode: int = 0):
    """Stand in for every install; let read-only tool probes really run.

    The declared install returns *returncode*; any other command that is not
    a version/env probe (an inferred install, a venv creation) succeeds
    without running, so no test ever installs anything.
    """

    def run(cmd, *args, **kwargs):
        argv = [str(a) for a in cmd]
        if argv == _DECLARED_INSTALL:
            return MagicMock(returncode=returncode, stdout="", stderr="")
        if _PROBE_ARGS.intersection(argv[1:]):
            return _REAL_RUN(cmd, *args, **kwargs)
        return MagicMock(returncode=0, stdout="", stderr="")

    return run


def _bootstrap(root: Path, returncode: int = 0):
    """Detect and bootstrap *root*; return (result, declared install calls)."""
    with patch("subprocess.run", side_effect=_fake_run(returncode)) as mock_run:
        manifests = ProjectEnvironmentDetector(root).detect()
        result = EnvironmentBootstrapper(root).bootstrap(manifests)
    return result, _declared_calls(mock_run)


def _installed_once(root: Path) -> None:
    result, calls = _bootstrap(root)
    assert result.success is True
    assert len(calls) == 1, "the first bootstrap must run the declared install"


def _reruns(root: Path) -> bool:
    result, calls = _bootstrap(root)
    return len(calls) == 1 and result.success is True


# =========================================================================
# 1. The install re-runs when a dependency input changes
# =========================================================================


class TestDeclaredInstallReruns:
    def test_reruns_after_a_root_lock_change(self, web_repo):
        _installed_once(web_repo)
        (web_repo / "package-lock.json").write_text(
            '{"lockfileVersion":3,"packages":{"":{"name":"root"}}}\n', "utf-8"
        )
        assert _reruns(web_repo)

    def test_reruns_after_a_web_component_lock_change(self, web_repo):
        _installed_once(web_repo)
        (web_repo / "apps" / "web" / "package-lock.json").write_text(
            '{"lockfileVersion":3,"packages":{"node_modules/x":{}}}\n', "utf-8"
        )
        assert _reruns(web_repo)

    def test_reruns_after_an_api_component_go_sum_change(self, web_repo):
        _installed_once(web_repo)
        (web_repo / "apps" / "api" / "go.sum").write_text(
            "example.com/dep v1.0.1 h1:bbbb=\n", "utf-8"
        )
        assert _reruns(web_repo)

    def test_reruns_after_a_component_manifest_is_added(self, web_repo):
        (web_repo / "apps" / "api" / "go.sum").unlink()
        _installed_once(web_repo)
        (web_repo / "apps" / "api" / "go.sum").write_text(
            "example.com/dep v1.0.0 h1:aaaa=\n", "utf-8"
        )
        assert _reruns(web_repo)

    def test_reruns_after_a_component_manifest_is_removed(self, web_repo):
        _installed_once(web_repo)
        (web_repo / "apps" / "web" / "package-lock.json").unlink()
        assert _reruns(web_repo)

    def test_reruns_after_a_workspace_manifest_between_component_and_root(
        self, web_repo
    ):
        """A manifest between a component and the root is workspace
        configuration the install reads. ``packages/ui`` sits two levels
        down, so nothing else in the bootstrap looks there today."""
        (web_repo / "packages" / "ui" / "lib").mkdir(parents=True)
        (web_repo / "packages" / "ui" / "lib" / "package.json").write_text(
            '{"name":"ui-lib"}\n', "utf-8"
        )
        _declare(
            web_repo,
            dict(_COMPONENTS, ui={"cwd": "packages/ui/lib", "test": "npm test"}),
            _RUNTIME,
        )
        _installed_once(web_repo)
        (web_repo / "packages" / "ui" / "package.json").write_text(
            '{"name":"ui","private":true,"workspaces":["lib"]}\n', "utf-8"
        )
        assert _reruns(web_repo)

    def test_after_a_component_cwd_change_the_new_directory_is_tracked(
        self, web_repo
    ):
        """Moving a component re-runs the install (the declaration changed),
        and from then on a lock change in the NEW directory re-runs it too."""
        _installed_once(web_repo)
        (web_repo / "apps" / "web").rename(web_repo / "apps" / "frontend")
        moved = dict(_COMPONENTS, web={"cwd": "apps/frontend", "test": "npm test"})
        _declare(web_repo, moved, _RUNTIME)
        assert _reruns(web_repo)
        (web_repo / "apps" / "frontend" / "package-lock.json").write_text(
            '{"lockfileVersion":3,"packages":{"node_modules/y":{}}}\n', "utf-8"
        )
        assert _reruns(web_repo)

    def test_reruns_after_a_component_cwd_change(self, web_repo):
        """Guard (passes today: the declaration's bytes are hashed)."""
        _installed_once(web_repo)
        (web_repo / "apps" / "web").rename(web_repo / "apps" / "frontend")
        moved = dict(_COMPONENTS, web={"cwd": "apps/frontend", "test": "npm test"})
        _declare(web_repo, moved, _RUNTIME)
        assert _reruns(web_repo)

    def test_reruns_after_a_runtime_pin_change(self, web_repo):
        """Guard (passes today: the declaration's bytes are hashed)."""
        _installed_once(web_repo)
        _declare(web_repo, _COMPONENTS, dict(_RUNTIME, node="v22.24.0"))
        assert _reruns(web_repo)

    def test_reruns_when_the_image_identity_changes(self, web_repo, monkeypatch):
        """An execution-identity change: the build container was replaced by
        another image. The old marker belongs to the old image."""
        monkeypatch.setenv("FORGE_IMAGE_IDENTITY", "a" * 64)
        _installed_once(web_repo)
        monkeypatch.setenv("FORGE_IMAGE_IDENTITY", "b" * 64)
        assert _reruns(web_repo)

    def test_a_copied_worktree_does_not_reuse_the_marker(self, web_repo, tmp_path):
        """Guard (passes today, because today's hash includes absolute
        paths). The requirement it pins: the execution identity includes the
        worktree's own root, so a worktree copied elsewhere, success marker
        and identical files included, installs again rather than trusting the
        copy. Moving to relative-path hashing must not lose this."""
        _installed_once(web_repo)
        copy = tmp_path / "copy"
        shutil.copytree(web_repo, copy)
        state = Path(".guardkit") / "bootstrap_state.json"
        assert (copy / state).read_bytes() == (web_repo / state).read_bytes()
        assert _reruns(copy)
        # The original, unchanged, is still a cache hit in its own root.
        result, calls = _bootstrap(web_repo)
        assert calls == [] and result.success is True

    def test_a_builder_edit_to_a_component_lock_refreshes_before_verification(
        self, web_repo
    ):
        """The per-turn refresh: a builder changed ``apps/web/package-lock.json``,
        so the declared install must run again before the verifier."""
        _installed_once(web_repo)
        (web_repo / "apps" / "web" / "package-lock.json").write_text(
            '{"lockfileVersion":3,"packages":{"node_modules/z":{}}}\n', "utf-8"
        )
        with patch("subprocess.run", side_effect=_fake_run()) as mock_run:
            result = refresh_environment_for_changes(
                web_repo, ["apps/web/package-lock.json"]
            )
        assert result is not None and result.success is True
        assert len(_declared_calls(mock_run)) == 1


# =========================================================================
# 2. The install does NOT re-run when nothing relevant changed
# =========================================================================


class TestDeclaredInstallStaysCached:
    def test_no_rerun_when_nothing_changed(self, web_repo):
        _installed_once(web_repo)
        result, calls = _bootstrap(web_repo)
        assert calls == []
        assert result.success is True

    def test_node_modules_contents_are_never_hashed(self, web_repo):
        _installed_once(web_repo)
        for base in (web_repo, web_repo / "apps" / "web"):
            pkg = base / "node_modules" / "left-pad"
            pkg.mkdir(parents=True)
            (pkg / "package.json").write_text('{"name":"left-pad"}\n', "utf-8")
            (pkg / "package-lock.json").write_text("{}\n", "utf-8")
        result, calls = _bootstrap(web_repo)
        assert calls == []
        assert result.success is True

    def test_an_undeclared_directory_is_not_tracked(self, web_repo):
        """Only declared directories count: a lock in an undeclared project
        two levels down does not re-run the root install."""
        (web_repo / "tools" / "scratch").mkdir(parents=True)
        lock = web_repo / "tools" / "scratch" / "package-lock.json"
        lock.write_text("{}\n", "utf-8")
        _installed_once(web_repo)
        lock.write_text('{"changed":true}\n', "utf-8")
        result, calls = _bootstrap(web_repo)
        assert calls == []


# =========================================================================
# 3. Unsafe or unreadable inputs fail the bootstrap
# =========================================================================


@pytest.fixture
def unreadable(request):
    """chmod a file to 000 for the test, restoring it afterwards."""
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root can read a mode-000 file")
    restored: List[Path] = []

    def make(path: Path) -> None:
        path.chmod(0)
        restored.append(path)

    yield make
    for path in restored:
        path.chmod(0o644)


class TestDeclaredInstallFailsSafely:
    def test_an_unreadable_component_lock_fails_the_first_bootstrap(
        self, web_repo, unreadable
    ):
        unreadable(web_repo / "apps" / "web" / "package-lock.json")
        result, _calls = _bootstrap(web_repo)
        assert result.success is False
        assert result.error

    def test_an_unreadable_component_lock_is_never_a_cache_hit(
        self, web_repo, unreadable
    ):
        _installed_once(web_repo)
        unreadable(web_repo / "apps" / "api" / "go.sum")
        result, _calls = _bootstrap(web_repo)
        assert result.success is False
        assert result.skipped is False

    def test_an_unreadable_declaration_stops_the_build_in_warning_mode(
        self, web_repo, unreadable
    ):
        """An existing ``.guardkit/config.yaml`` that cannot be read must not
        drop the declaration and guess the install from the root lockfile.
        Detection refuses, and ``_bootstrap_environment`` turns that into a
        stopping error even in warning mode, before anything is installed."""
        from guardkit.orchestrator.feature_orchestrator import (
            FeatureOrchestrationError,
            FeatureOrchestrator,
        )
        from guardkit.orchestrator.toolchain_declaration import (
            ToolchainDeclarationError,
        )

        orchestrator = FeatureOrchestrator(
            repo_root=web_repo.parent,
            skip_validation=True,
            worktree_manager=MagicMock(),
        )
        unreadable(web_repo / ".guardkit" / "config.yaml")

        with pytest.raises(ToolchainDeclarationError):
            ProjectEnvironmentDetector(web_repo)
        with patch("subprocess.run", side_effect=_fake_run()) as mock_run:
            with pytest.raises(FeatureOrchestrationError) as exc:
                orchestrator._bootstrap_environment(SimpleNamespace(path=web_repo))
        assert "config.yaml" in str(exc.value)
        assert _declared_calls(mock_run) == []
        assert not (web_repo / ".guardkit" / "bootstrap_state.json").exists()

    def test_a_component_cwd_that_escapes_through_a_symlink_fails(
        self, web_repo, tmp_path
    ):
        outside = tmp_path / "outside-web"
        outside.mkdir()
        (outside / "package.json").write_text('{"name":"elsewhere"}\n', "utf-8")
        shutil.rmtree(web_repo / "apps" / "web")
        (web_repo / "apps" / "web").symlink_to(outside, target_is_directory=True)
        result, _calls = _bootstrap(web_repo)
        assert result.success is False
        assert result.error

    def test_a_failed_install_is_not_recorded_as_success(self, web_repo):
        """Guard (passes today): a failing declared install stays failed."""
        result, calls = _bootstrap(web_repo, returncode=1)
        assert len(calls) == 1
        assert result.success is False

    def test_a_failed_install_is_retried_once_the_cooldown_has_passed(
        self, web_repo
    ):
        """Guard (passes today): the existing retry limit. Within the cooldown
        a failed install is not run again; once it has passed, it is."""
        with patch("subprocess.run", side_effect=_fake_run(returncode=1)) as first:
            manifests = ProjectEnvironmentDetector(web_repo).detect()
            failed = EnvironmentBootstrapper(
                web_repo, retry_cooldown_seconds=3600
            ).bootstrap(manifests)
        assert failed.success is False and len(_declared_calls(first)) == 1

        with patch("subprocess.run", side_effect=_fake_run()) as waiting:
            manifests = ProjectEnvironmentDetector(web_repo).detect()
            EnvironmentBootstrapper(
                web_repo, retry_cooldown_seconds=3600
            ).bootstrap(manifests)
        assert _declared_calls(waiting) == []

        with patch("subprocess.run", side_effect=_fake_run()) as retried:
            manifests = ProjectEnvironmentDetector(web_repo).detect()
            result = EnvironmentBootstrapper(
                web_repo, retry_cooldown_seconds=0
            ).bootstrap(manifests)
        assert len(_declared_calls(retried)) == 1
        assert result.success is True

    @pytest.mark.parametrize("root_label", ["node", "declared"])
    def test_a_failing_declared_install_fails_the_per_turn_refresh(
        self, web_repo, root_label
    ):
        """Through ``refresh_environment_for_changes``, with
        ``relevant_stacks`` computed the way the per-turn caller computes it
        (from the changed file names), so a ``go.sum`` edit reads as ``go``
        while the declared root install is labelled for the whole repo
        (``node``, or ``declared`` for a mixed root). A failing declared
        install must still fail the refresh, not be counted as a non-blocking
        warning and saved as success. The next test goes through the real
        caller itself."""
        if root_label == "declared":
            (web_repo / "go.mod").write_text("module example.com/root\n", "utf-8")
        [declared] = ProjectEnvironmentDetector(web_repo).detect()
        assert declared.stack == root_label
        changed = ["apps/api/go.sum"]
        (web_repo / "apps" / "api" / "go.sum").write_text(
            "example.com/dep v1.0.1 h1:bbbb=\n", "utf-8"
        )
        with patch("subprocess.run", side_effect=_fake_run(returncode=1)) as mock_run:
            result = refresh_environment_for_changes(
                web_repo,
                changed,
                relevant_stacks=stacks_for_changed_manifests(changed) or None,
            )
        assert len(_declared_calls(mock_run)) == 1
        assert result is not None
        assert result.success is False
        assert result.installs_failed >= 1

    def test_the_real_per_turn_caller_reports_a_failing_declared_install(
        self, web_repo
    ):
        """Through ``AutoBuildOrchestrator._maybe_refresh_venv_for_manifest_change``
        itself: after a ``go.sum``-only change the failing declared install
        runs, and the caller must return feedback for the Player, not
        ``None`` (a silent pass)."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        orchestrator._venv_python = None
        (web_repo / "apps" / "api" / "go.sum").write_text(
            "example.com/dep v1.0.1 h1:bbbb=\n", "utf-8"
        )
        with patch("subprocess.run", side_effect=_fake_run(returncode=1)) as mock_run:
            feedback = orchestrator._maybe_refresh_venv_for_manifest_change(
                SimpleNamespace(report={"files_modified": ["apps/api/go.sum"]}),
                SimpleNamespace(path=str(web_repo)),
                1,
            )
        assert len(_declared_calls(mock_run)) == 1
        assert feedback, "a failed declared install was swallowed into a silent pass"

    @pytest.mark.parametrize("escaping", ["../outside-web", "/srv/outside-web"])
    def test_a_dot_dot_or_absolute_component_cwd_is_refused_visibly(
        self, web_repo, escaping
    ):
        """A ``..`` or absolute ``cwd`` must not silently drop the whole
        declaration so the bootstrap falls back to guessing from manifest
        files. Either detection refuses with an error naming the ``cwd``, or
        the bootstrap fails and says why."""
        _declare(
            web_repo,
            dict(_COMPONENTS, web={"cwd": escaping, "test": "npm test"}),
            _RUNTIME,
        )
        with patch("subprocess.run", side_effect=_fake_run()):
            try:
                manifests = ProjectEnvironmentDetector(web_repo).detect()
                result = EnvironmentBootstrapper(web_repo).bootstrap(manifests)
            except Exception as exc:  # noqa: BLE001 - a visible refusal counts
                assert escaping in str(exc)
                return
        assert result.success is False
        assert escaping in (result.error or "")

    def test_a_components_own_install_is_never_run(self, web_repo):
        """Guard (passes today): only the declared root install runs; a
        component's ``install:`` stays declared but not run."""
        _declare(
            web_repo,
            dict(
                _COMPONENTS,
                web={"cwd": "apps/web", "test": "npm test", "install": "npm run setup-web"},
            ),
            _RUNTIME,
        )
        with patch("subprocess.run", side_effect=_fake_run()) as mock_run:
            manifests = ProjectEnvironmentDetector(web_repo).detect()
            EnvironmentBootstrapper(web_repo).bootstrap(manifests)
        ran = [list(map(str, c.args[0])) for c in mock_run.call_args_list]
        assert ["npm", "run", "setup-web"] not in ran
        assert len(_declared_calls(mock_run)) == 1


# =========================================================================
# 4. Repos without a declared install are unchanged
# =========================================================================


class TestUndeclaredRepoUnchanged:
    @pytest.fixture
    def undeclared_repo(self, web_repo):
        (web_repo / ".guardkit" / "config.yaml").unlink()
        return web_repo

    def test_detection_is_root_and_one_level_only(self, undeclared_repo):
        manifests = ProjectEnvironmentDetector(undeclared_repo).detect()
        assert [m.path.relative_to(undeclared_repo).as_posix() for m in manifests] == [
            "package-lock.json"
        ]
        assert all(m.declared is False for m in manifests)

    def test_a_two_level_lock_change_does_not_rerun(self, undeclared_repo):
        with patch("subprocess.run", side_effect=_fake_run()) as first:
            manifests = ProjectEnvironmentDetector(undeclared_repo).detect()
            EnvironmentBootstrapper(undeclared_repo).bootstrap(manifests)
        assert len(_declared_calls(first)) == 1  # inferred `npm ci` at the root
        (undeclared_repo / "apps" / "web" / "package-lock.json").write_text(
            '{"changed":true}\n', "utf-8"
        )
        with patch("subprocess.run", side_effect=_fake_run()) as second:
            manifests = ProjectEnvironmentDetector(undeclared_repo).detect()
            result = EnvironmentBootstrapper(undeclared_repo).bootstrap(manifests)
        assert _declared_calls(second) == []
        assert result.skipped is True
