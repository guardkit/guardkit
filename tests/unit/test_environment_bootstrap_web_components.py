"""Declared install cache for a repo with declared components (web readiness).

What the implementation must do
-------------------------------
When the root ``.guardkit/config.yaml`` declares ``toolchain.install``, the
bootstrap runs that one command for the whole repo. Today its success marker
covers only the declaration file, so a builder who changes
``apps/web/package-lock.json`` or ``apps/api/go.sum`` leaves the verifier on
the old dependencies. The repair belongs to the reliability lane (web
readiness design review, finding R7); these tests state the behaviour it must
deliver and flip loudly (``xfail(strict=True)``) once it lands.

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
4. The marker also records the environment it was made in (the declared
   ``runtime`` pins and the image or tool identity). A marker made in another
   environment, or in another worktree, is not reused.
5. Traversal is bounded. It never leaves the worktree and never reads inside
   dependency or cache folders such as ``node_modules``. A component ``cwd``
   that escapes the worktree, including through a symlink, fails the
   bootstrap with a clear message.
6. An unreadable dependency input fails the bootstrap; it never produces a
   success or a cache hit. A failed install stays failed and retryable under
   the existing limits.
7. A component's own ``install:`` stays declared but not run, and repos
   without a declared install behave exactly as before (no new discovery).

The tests use only public seams: ``ProjectEnvironmentDetector.detect``,
``EnvironmentBootstrapper.bootstrap``, ``refresh_environment_for_changes`` and
the files on disk. "The install ran" means the declared command reached
``subprocess.run``. Version and env probes pass through to the real
``subprocess.run``, so an implementation may probe tools that way; nothing is
ever installed.

Tests without the xfail mark already pass today and guard properties the
implementation must keep.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest
import yaml

from guardkit.orchestrator.environment_bootstrap import (
    EnvironmentBootstrapper,
    ProjectEnvironmentDetector,
    refresh_environment_for_changes,
)

_REAL_RUN = subprocess.run

_DECLARED_INSTALL = ["npm", "ci"]

_R7 = pytest.mark.xfail(
    strict=True,
    reason=(
        "reliability lane: declared component install cache — "
        "web readiness R7"
    ),
)


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
    @_R7
    def test_reruns_after_a_root_lock_change(self, web_repo):
        _installed_once(web_repo)
        (web_repo / "package-lock.json").write_text(
            '{"lockfileVersion":3,"packages":{"":{"name":"root"}}}\n', "utf-8"
        )
        assert _reruns(web_repo)

    @_R7
    def test_reruns_after_a_web_component_lock_change(self, web_repo):
        _installed_once(web_repo)
        (web_repo / "apps" / "web" / "package-lock.json").write_text(
            '{"lockfileVersion":3,"packages":{"node_modules/x":{}}}\n', "utf-8"
        )
        assert _reruns(web_repo)

    @_R7
    def test_reruns_after_an_api_component_go_sum_change(self, web_repo):
        _installed_once(web_repo)
        (web_repo / "apps" / "api" / "go.sum").write_text(
            "example.com/dep v1.0.1 h1:bbbb=\n", "utf-8"
        )
        assert _reruns(web_repo)

    @_R7
    def test_reruns_after_a_component_manifest_is_added(self, web_repo):
        (web_repo / "apps" / "api" / "go.sum").unlink()
        _installed_once(web_repo)
        (web_repo / "apps" / "api" / "go.sum").write_text(
            "example.com/dep v1.0.0 h1:aaaa=\n", "utf-8"
        )
        assert _reruns(web_repo)

    @_R7
    def test_reruns_after_a_component_manifest_is_removed(self, web_repo):
        _installed_once(web_repo)
        (web_repo / "apps" / "web" / "package-lock.json").unlink()
        assert _reruns(web_repo)

    @_R7
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

    @_R7
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

    @_R7
    def test_reruns_when_the_install_tool_resolves_to_another_executable(
        self, web_repo, tmp_path, monkeypatch
    ):
        """An execution-identity change: the same command now resolves to a
        different ``npm`` (a replaced image or toolchain). The old marker
        belongs to the old environment and must not be reused."""
        bins = []
        for name, version in (("bin-a", "10.0.0"), ("bin-b", "11.0.0")):
            directory = tmp_path / name
            directory.mkdir()
            tool = directory / "npm"
            tool.write_text(f"#!/bin/sh\necho {version}\n", "utf-8")
            tool.chmod(0o755)
            bins.append(directory)
        original_path = os.environ.get("PATH", "")
        monkeypatch.setenv("PATH", f"{bins[0]}{os.pathsep}{original_path}")
        _installed_once(web_repo)
        monkeypatch.setenv("PATH", f"{bins[1]}{os.pathsep}{original_path}")
        assert _reruns(web_repo)

    def test_a_copied_worktree_does_not_reuse_the_marker(self, web_repo, tmp_path):
        """Guard (passes today): a worktree copied elsewhere, success marker
        included, installs again rather than trusting the copy."""
        _installed_once(web_repo)
        copy = tmp_path / "copy"
        shutil.copytree(web_repo, copy)
        assert _reruns(copy)

    @_R7
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
    @_R7
    def test_an_unreadable_component_lock_fails_the_first_bootstrap(
        self, web_repo, unreadable
    ):
        unreadable(web_repo / "apps" / "web" / "package-lock.json")
        result, _calls = _bootstrap(web_repo)
        assert result.success is False
        assert result.error

    @_R7
    def test_an_unreadable_component_lock_is_never_a_cache_hit(
        self, web_repo, unreadable
    ):
        _installed_once(web_repo)
        unreadable(web_repo / "apps" / "api" / "go.sum")
        result, _calls = _bootstrap(web_repo)
        assert result.success is False
        assert result.skipped is False

    @_R7
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
