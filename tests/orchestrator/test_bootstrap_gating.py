"""Bootstrap failures are advice, never a stop.

Step 2 (26 October 2026): the bootstrap hard-fail gate
(``bootstrap_failure_mode``, TASK-FIX-7A04) and its requires-python smart
default (TASK-ABSR-A1B2) are removed. A declared install that fails is a
warning and the build goes on; when the project's tests then cannot start,
the reviewer is told so. What still stops the bootstrap: a toolchain
declaration that cannot be read (and, until toolchain_declaration.py changes,
a refused component ``cwd``). Since 1 November 2026 only a declared install
runs: no declaration means nothing is installed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrationError,
    FeatureOrchestrator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


class _FakeWorktree:
    def __init__(self, path: Path) -> None:
        self.path = path


def test_a_failed_declared_install_goes_on(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A declared install that fails is a warning; the result is returned
    and the build goes on (step 2; formerly a stop in block mode)."""
    import yaml

    orchestrator = _build_orchestrator(tmp_path)
    worktree = tmp_path / "worktree"
    (worktree / ".guardkit").mkdir(parents=True)
    (worktree / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": {"install": "false", "test": "true"}}),
        encoding="utf-8",
    )

    got = orchestrator._bootstrap_environment(_FakeWorktree(worktree))

    assert got is not None and got.declared is True and got.success is False
    assert "the declared install `false` failed" in capsys.readouterr().out


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


def test_a_missing_declaration_directory_installs_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """No ``.guardkit`` at all means "not declared": nothing is installed,
    though the worktree holds a lockfile (1 November 2026: no install is
    inferred from a project's files)."""
    import shutil

    orchestrator = _build_orchestrator(tmp_path)
    worktree = _declared_web_worktree(tmp_path, "apps/web")
    shutil.rmtree(worktree / ".guardkit")

    with patch("subprocess.run", _no_installs()) as run:
        result = orchestrator._bootstrap_environment(_FakeWorktree(worktree))

    assert result is not None and result.success is True and result.declared is False
    run.assert_not_called()
    assert "no install declared; nothing installed" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Declared inputs: "not found" is an absent entry in the install's cache key.
# ---------------------------------------------------------------------------


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
