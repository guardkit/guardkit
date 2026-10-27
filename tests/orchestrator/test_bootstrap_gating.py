"""Bootstrap failures and interpreter mismatches are advice, never a stop.

Step 2 (26 October 2026): the bootstrap hard-fail gate
(``bootstrap_failure_mode``, TASK-FIX-7A04) and its requires-python smart
default (TASK-ABSR-A1B2) are removed. An install that fails, or an interpreter
that does not meet a manifest's ``requires-python``, is a warning and the
build goes on; when the project's tests then cannot start, the reviewer is
told so. What still stops the bootstrap: a toolchain declaration that cannot
be read, a refused component ``cwd`` and a refused declared input.
"""

from __future__ import annotations

from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.environment_bootstrap import (
    BootstrapFailureDetail,
    BootstrapResult,
    RequiresPythonMismatch,
    check_requires_python_precheck,
    format_requires_python_remediation,
)
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrationError,
    FeatureOrchestrator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    *,
    installs_attempted: int,
    installs_failed: int,
    stacks_detected: List[str],
    failure_details: List[BootstrapFailureDetail] | None = None,
    skipped: bool = False,
) -> BootstrapResult:
    """Build a BootstrapResult with just enough fields for gate tests."""
    return BootstrapResult(
        success=installs_failed == 0,
        skipped=skipped,
        stacks_detected=list(stacks_detected),
        manifests_found=[],
        installs_attempted=installs_attempted,
        installs_failed=installs_failed,
        error=(
            f"{installs_failed}/{installs_attempted} install(s) failed"
            if installs_failed
            else None
        ),
        failure_details=list(failure_details or []),
    )


def _build_orchestrator(tmp_path: Path) -> FeatureOrchestrator:
    """Instantiate FeatureOrchestrator with the repo_root pinned to ``tmp_path``."""
    # WorktreeManager validates that repo_root is a real git checkout during
    # __init__; in these unit tests tmp_path is not a repo, so inject a
    # MagicMock in its place — these tests never exercise the manager.
    return FeatureOrchestrator(
        repo_root=tmp_path,
        skip_validation=True,
        worktree_manager=MagicMock(),
    )


# ---------------------------------------------------------------------------
# TASK-REV-JMBP Workstream E — requires-python pre-check
# ---------------------------------------------------------------------------


def test_precheck_returns_empty_when_interpreter_satisfies_specifier(
    tmp_path: Path,
) -> None:
    # Specifier accepts the active version → no mismatches.
    manifest = _FakeManifest("python", requires_python=">=3.0,<4.0")
    mismatches = check_requires_python_precheck([manifest])
    assert mismatches == []


def test_precheck_flags_jarvis_like_mismatch() -> None:
    # Integration-style fixture: jarvis's real pyproject constraint vs a
    # fabricated Python 3.14 — the exact shape that triggered TASK-REV-JMBP.
    manifest = _FakeManifest("python", requires_python="<3.13,>=3.12")
    mismatches = check_requires_python_precheck(
        [manifest], active_version="3.14.2"
    )
    assert len(mismatches) == 1
    m = mismatches[0]
    assert m.specifier == "<3.13,>=3.12"
    assert m.active_version == "3.14.2"


def test_precheck_returns_empty_when_python_3_12_meets_jarvis_constraint() -> None:
    manifest = _FakeManifest("python", requires_python="<3.13,>=3.12")
    assert (
        check_requires_python_precheck(
            [manifest], active_version="3.12.6"
        )
        == []
    )


def test_precheck_skips_manifest_without_requires_python() -> None:
    manifest = _FakeManifest("python", requires_python=None)
    assert check_requires_python_precheck([manifest]) == []


def test_precheck_skips_non_python_stack() -> None:
    # Node / dotnet / etc never have requires-python.
    manifest = _FakeManifest("node", requires_python=None)
    assert check_requires_python_precheck([manifest]) == []


def test_precheck_skips_invalid_specifier_gracefully(
    caplog: pytest.LogCaptureFixture,
) -> None:
    manifest = _FakeManifest("python", requires_python=">>>garbage<<<")
    with caplog.at_level("DEBUG"):
        mismatches = check_requires_python_precheck([manifest])
    # Invalid specifier → pip remains authoritative; pre-check returns empty.
    assert mismatches == []


def test_format_remediation_includes_uv_pyenv_conda_and_version_example() -> None:
    mismatch = RequiresPythonMismatch(
        manifest_path="/repo/pyproject.toml",
        specifier="<3.13,>=3.12",
        active_version="3.14.2",
    )
    msg = format_requires_python_remediation(mismatch)
    assert "uv python install" in msg
    assert "pyenv install" in msg
    assert "conda create" in msg
    assert "3.12" in msg  # example version picked from specifier
    assert "/repo/pyproject.toml" in msg

_MISMATCH = RequiresPythonMismatch(
    manifest_path="/repo/pyproject.toml",
    specifier="<3.13,>=3.12",
    active_version="3.14.2",
)


def test_requires_python_mismatch_logs_structured_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    orchestrator = _build_orchestrator(tmp_path)

    manifest = _FakeManifest("python", requires_python="<3.13,>=3.12")
    with patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[_MISMATCH],
    ):
        with caplog.at_level("WARNING"):
            orchestrator._warn_requires_python([manifest])

    # The structured warning shape specified by AC-REQPY-PRECHECK; no raise.
    assert any(
        "does not satisfy requires-python=" in rec.message
        for rec in caplog.records
    )
    assert any(
        "3.14.2" in rec.message and "<3.13,>=3.12" in rec.message
        for rec in caplog.records
    )


def test_requires_python_no_mismatch_is_noop(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(tmp_path)
    with patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[],
    ):
        orchestrator._warn_requires_python([])


# ---------------------------------------------------------------------------
# End-to-end: _bootstrap_environment wires the gate through a mocked bootstrapper
# ---------------------------------------------------------------------------


class _FakeManifest:
    """
    Minimal DetectedManifest stand-in.

    Exposes the three surface points the pre-check + gate need: ``stack``
    (detector branch), ``path`` (used in mismatch records and debug logs),
    and ``get_requires_python()`` (pre-check — ``None`` = no constraint
    declared, making the pre-check a silent no-op).
    """

    def __init__(
        self,
        stack: str,
        requires_python: "str | None" = None,
        path: "Path | None" = None,
    ) -> None:
        self.stack = stack
        self._requires_python = requires_python
        self.path = path or Path(f"/tmp/fake-{stack}-manifest")

    def get_requires_python(self) -> "str | None":
        return self._requires_python


class _FakeWorktree:
    def __init__(self, path: Path) -> None:
        self.path = path

def _all_installs_failed(tmp_path: Path) -> BootstrapResult:
    return _make_result(
        installs_attempted=1,
        installs_failed=1,
        stacks_detected=["python"],
        failure_details=[
            BootstrapFailureDetail(
                stack="python",
                manifest_path=str(tmp_path / "pyproject.toml"),
                stderr_excerpt="ERROR: externally-managed-environment",
                is_pep668=True,
                requires_python=">=3.13",
                essential=True,
            )
        ],
    )


def test_bootstrap_environment_with_every_install_failed_goes_on(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Every essential install failing is a warning; the result is returned
    and the build goes on (step 2; formerly a stop in block mode)."""
    orchestrator = _build_orchestrator(tmp_path)
    fake_result = _all_installs_failed(tmp_path)

    with patch(
        "guardkit.orchestrator.feature_orchestrator.ProjectEnvironmentDetector"
    ) as det_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.EnvironmentBootstrapper"
    ) as boot_cls:
        det_cls.return_value.detect.return_value = [
            _FakeManifest("python", requires_python=">=3.13")
        ]
        boot_cls.return_value.bootstrap.return_value = fake_result

        got = orchestrator._bootstrap_environment(_FakeWorktree(tmp_path))

    assert got is fake_result
    assert "Environment bootstrap partial: 0/1 succeeded" in capsys.readouterr().out


def test_replay_feat_j004_702c_preflight_warns_and_installs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """
    Replay TASK-REV-FA04 / FEAT-J004-702C: a worktree whose pyproject
    declares a ``requires-python`` the active interpreter cannot satisfy.
    Since step 2 the mismatch is named in a warning before pip runs, the
    install is still attempted and its result returned; the build is not
    stopped. If the project's tests then cannot start, the reviewer is told.
    """
    orchestrator = _build_orchestrator(tmp_path)
    fake_result = _all_installs_failed(tmp_path)

    with patch(
        "guardkit.orchestrator.feature_orchestrator.ProjectEnvironmentDetector"
    ) as det_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.EnvironmentBootstrapper"
    ) as boot_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[
            RequiresPythonMismatch(
                manifest_path=str(tmp_path / "pyproject.toml"),
                specifier="<3.13,>=3.12",
                active_version="3.14.2",
            )
        ],
    ):
        det_cls.return_value.detect.return_value = [
            _FakeManifest("python", requires_python="<3.13,>=3.12")
        ]
        boot_cls.return_value.bootstrap.return_value = fake_result

        with caplog.at_level("WARNING"):
            got = orchestrator._bootstrap_environment(_FakeWorktree(tmp_path))

    boot_cls.return_value.bootstrap.assert_called_once()
    assert got is fake_result
    assert any(
        "does not satisfy requires-python=`<3.13,>=3.12`" in rec.message
        for rec in caplog.records
    )


# ---------------------------------------------------------------------------
# Follow-up fixes 2026-10-13 (3b): a refused component ``cwd`` stops the build,
# through the real detector and bootstrapper.
# ---------------------------------------------------------------------------


def _declared_web_worktree(tmp_path: Path, web_cwd: str) -> Path:
    """A worktree (separate from the orchestrator's repo root) that declares
    a root install and a ``web`` component at *web_cwd*."""
    import yaml

    worktree = tmp_path / "worktree"
    (worktree / "apps" / "web").mkdir(parents=True)
    (worktree / "package.json").write_text('{"name":"root"}\n', "utf-8")
    (worktree / "package-lock.json").write_text('{"lockfileVersion":3}\n', "utf-8")
    (worktree / "apps" / "web" / "package.json").write_text('{"name":"web"}\n', "utf-8")
    cfg = worktree / ".guardkit"
    cfg.mkdir()
    (cfg / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "toolchain": {
                    "install": "npm ci",
                    "components": {"web": {"cwd": web_cwd, "test": "npm test"}},
                }
            }
        ),
        encoding="utf-8",
    )
    return worktree


def _no_installs() -> MagicMock:
    return MagicMock(return_value=MagicMock(returncode=0, stdout="", stderr=""))


@pytest.mark.parametrize("escaping", ["../outside-web", "/srv/outside-web"])
def test_a_refused_component_cwd_stops_the_bootstrap_in_every_mode(
    tmp_path: Path, escaping
) -> None:
    orchestrator = _build_orchestrator(tmp_path)
    worktree = _declared_web_worktree(tmp_path, escaping)

    with patch("subprocess.run", _no_installs()) as run:
        with pytest.raises(FeatureOrchestrationError) as exc:
            orchestrator._bootstrap_environment(_FakeWorktree(worktree))

    msg = str(exc.value)
    assert "'web'" in msg
    assert escaping in msg
    assert not any(list(c.args[0]) == ["npm", "ci"] for c in run.call_args_list)


def test_a_component_cwd_escaping_through_a_symlink_stops_the_bootstrap(
    tmp_path: Path,
) -> None:
    """The refused-input result (not an exception) stops the build too."""
    import shutil

    orchestrator = _build_orchestrator(tmp_path)
    worktree = _declared_web_worktree(tmp_path, "apps/web")
    outside = tmp_path / "outside-web"
    outside.mkdir()
    shutil.rmtree(worktree / "apps" / "web")
    (worktree / "apps" / "web").symlink_to(outside, target_is_directory=True)

    with patch("subprocess.run", _no_installs()):
        with pytest.raises(FeatureOrchestrationError) as exc:
            orchestrator._bootstrap_environment(_FakeWorktree(worktree))
    assert "'web'" in str(exc.value)


def test_a_component_cwd_that_is_a_symlink_loop_stops_the_bootstrap(
    tmp_path: Path,
) -> None:
    """A self-looping symlink as the declared ``cwd`` is refused (named by
    component and path), not swallowed as a generic error in warning mode."""
    import shutil

    orchestrator = _build_orchestrator(tmp_path)
    worktree = _declared_web_worktree(tmp_path, "apps/web")
    shutil.rmtree(worktree / "apps" / "web")
    (worktree / "apps" / "web").symlink_to("web")

    with patch("subprocess.run", _no_installs()) as run:
        with pytest.raises(FeatureOrchestrationError) as exc:
            orchestrator._bootstrap_environment(_FakeWorktree(worktree))
    assert "'web'" in str(exc.value)
    assert "apps/web" in str(exc.value)
    assert not any(list(c.args[0]) == ["npm", "ci"] for c in run.call_args_list)


def test_a_valid_component_cwd_bootstraps_as_today(tmp_path: Path) -> None:
    """Control: a relative ``cwd`` inside the worktree loads and installs."""
    orchestrator = _build_orchestrator(tmp_path)
    worktree = _declared_web_worktree(tmp_path, "apps/web")

    with patch("subprocess.run", _no_installs()) as run:
        result = orchestrator._bootstrap_environment(_FakeWorktree(worktree))

    assert result is not None and result.success is True
    assert any(list(c.args[0]) == ["npm", "ci"] for c in run.call_args_list)


def test_a_refused_component_cwd_stops_admitted_bootstrap_before_player(tmp_path: Path) -> None:
    """Real creation and admission preserve a refused bootstrap's cause."""
    import subprocess
    from types import SimpleNamespace
    from guardkit.worktrees import WorktreeManager
    from guardkit.orchestrator.task_work_scope import checkout_lease

    source = _declared_web_worktree(tmp_path, "../outside-web")
    for args in (["init", "-b", "main"], ["config", "user.name", "Fixture"],
                 ["config", "user.email", "fixture@example.invalid"],
                 ["add", "."], ["commit", "-m", "pinned source"]):
        subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True)
    orchestrator = FeatureOrchestrator(repo_root=source, worktree_manager=WorktreeManager(source),
                                      enable_context=False, quiet=True)
    feature = MagicMock()
    feature.id = "FEAT-WEB"
    feature.status = "planned"
    feature.file_path = None
    feature.evidence_repos = []
    feature.bootstrap_extras = []
    feature.smoke_gates = None
    with patch.object(orchestrator, "_copy_tasks_to_worktree"), patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"
    ), patch("guardkit.orchestrator.feature_orchestrator.EnvironmentBootstrapper.bootstrap") as install, patch.object(
        orchestrator, "_execute_task_owned"
    ) as player:
        _, worktree = orchestrator._create_new_worktree(feature, feature.id, "main")
        with pytest.raises(FeatureOrchestrationError) as exc:
            orchestrator._execute_task(SimpleNamespace(id="TASK-WEB"), feature, worktree)
    assert "../outside-web" in str(exc.value)
    install.assert_not_called()
    player.assert_not_called()
    result = orchestrator._create_error_result("TASK-WEB", exc.value)
    assert result.error_type == type(exc.value.__cause__).__name__
    with checkout_lease(worktree.path) as lease:  # the next writer is admitted (step 2)
        lease.admit("TASK-NEXT")


def test_an_inaccessible_declaration_directory_stops_the_bootstrap(
    tmp_path: Path
) -> None:
    """``.guardkit`` cannot be searched, so whether the declaration exists is
    unknown. That stops the build in every mode instead of escaping as a
    generic error the bootstrap only warns about."""
    import os

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root can search a mode-000 directory")
    orchestrator = _build_orchestrator(tmp_path)
    worktree = _declared_web_worktree(tmp_path, "apps/web")
    guardkit_dir = worktree / ".guardkit"
    guardkit_dir.chmod(0)
    try:
        with patch("subprocess.run", _no_installs()) as run:
            with pytest.raises(FeatureOrchestrationError) as exc:
                orchestrator._bootstrap_environment(_FakeWorktree(worktree))
    finally:
        guardkit_dir.chmod(0o755)
    assert "config.yaml" in str(exc.value)
    assert not any(list(c.args[0]) == ["npm", "ci"] for c in run.call_args_list)


def test_a_missing_declaration_directory_bootstraps_as_today(
    tmp_path: Path
) -> None:
    """Control: no ``.guardkit`` at all means "not declared"; the install is
    inferred from the lockfile as before."""
    import shutil

    orchestrator = _build_orchestrator(tmp_path)
    worktree = _declared_web_worktree(tmp_path, "apps/web")
    shutil.rmtree(worktree / ".guardkit")

    with patch("subprocess.run", _no_installs()) as run:
        result = orchestrator._bootstrap_environment(_FakeWorktree(worktree))

    assert result is not None and result.success is True
    assert any(list(c.args[0]) == ["npm", "ci"] for c in run.call_args_list)


# ---------------------------------------------------------------------------
# Declared inputs: only "not found" means absent; any other filesystem error
# refuses the bootstrap and stops the build (Codex review R3/R4).
# ---------------------------------------------------------------------------


def _skip_if_root() -> None:
    import os

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")


def _bootstrap_once_then_restrict(
    tmp_path: Path, worktree: Path, restricted: Path, mode: int
):
    """Bootstrap successfully, then restrict *restricted* and bootstrap again.

    Returns the error raised by the second bootstrap, the second run's
    subprocess mock, and whether the saved state was left unchanged.
    Permissions are restored before returning.
    """
    orchestrator = _build_orchestrator(tmp_path)
    with patch("subprocess.run", _no_installs()):
        first = orchestrator._bootstrap_environment(_FakeWorktree(worktree))
    assert first is not None and first.success is True
    state_file = worktree / ".guardkit" / "bootstrap_state.json"
    saved = state_file.read_bytes()

    restricted.chmod(mode)
    try:
        with patch("subprocess.run", _no_installs()) as run:
            with pytest.raises(FeatureOrchestrationError) as exc:
                orchestrator._bootstrap_environment(_FakeWorktree(worktree))
    finally:
        restricted.chmod(0o755)
    return exc.value, run, state_file.read_bytes() == saved


def test_a_dependency_link_into_an_unsearchable_directory_stops_the_bootstrap(
    tmp_path: Path
) -> None:
    """``apps/web/package-lock.json`` links to a file in ``.deps``, which then
    cannot be searched: the link's target cannot be looked up."""
    _skip_if_root()
    worktree = _declared_web_worktree(tmp_path, "apps/web")
    deps = worktree / ".deps"
    deps.mkdir()
    (deps / "lock.json").write_text('{"lockfileVersion":3}\n', "utf-8")
    (worktree / "apps" / "web" / "package-lock.json").symlink_to(
        "../../.deps/lock.json"
    )

    error, run, state_unchanged = _bootstrap_once_then_restrict(
        tmp_path, worktree, deps, 0o644
    )

    assert "'web'" in str(error) and "apps/web/package-lock.json" in str(error)
    assert not any(list(c.args[0]) == ["npm", "ci"] for c in run.call_args_list)
    assert state_unchanged


def test_an_unsearchable_intermediate_directory_stops_the_bootstrap(
    tmp_path: Path
) -> None:
    """``packages/ui`` is readable but cannot be searched, so whether the
    declared ``packages/ui/lib`` exists is unknown; it is not "absent"."""
    import yaml

    _skip_if_root()
    worktree = _declared_web_worktree(tmp_path, "apps/web")
    lib = worktree / "packages" / "ui" / "lib"
    lib.mkdir(parents=True)
    (lib / "package.json").write_text('{"name":"ui-lib"}\n', "utf-8")
    cfg = worktree / ".guardkit" / "config.yaml"
    block = yaml.safe_load(cfg.read_text("utf-8"))
    block["toolchain"]["components"]["ui"] = {"cwd": "packages/ui/lib", "test": "npm test"}
    cfg.write_text(yaml.safe_dump(block), encoding="utf-8")

    error, run, state_unchanged = _bootstrap_once_then_restrict(
        tmp_path, worktree, worktree / "packages" / "ui", 0o444
    )

    assert "'ui'" in str(error) and "packages/ui/lib" in str(error)
    assert not any(list(c.args[0]) == ["npm", "ci"] for c in run.call_args_list)
    assert state_unchanged


def test_a_missing_declared_directory_is_still_absent(
    tmp_path: Path
) -> None:
    """Control: a declared ``cwd`` that does not exist is an "absent" entry;
    the install runs, and creating the directory later reruns it."""
    orchestrator = _build_orchestrator(tmp_path)
    worktree = _declared_web_worktree(tmp_path, "apps/not-yet")

    with patch("subprocess.run", _no_installs()) as run:
        result = orchestrator._bootstrap_environment(_FakeWorktree(worktree))
    assert result is not None and result.success is True and result.skipped is False
    assert any(list(c.args[0]) == ["npm", "ci"] for c in run.call_args_list)

    (worktree / "apps" / "not-yet").mkdir()
    with patch("subprocess.run", _no_installs()) as run:
        again = orchestrator._bootstrap_environment(_FakeWorktree(worktree))
    assert again is not None and again.skipped is False
    assert any(list(c.args[0]) == ["npm", "ci"] for c in run.call_args_list)
