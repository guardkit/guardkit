"""
Integration tests for TASK-FIX-FF62: pth-leak scanner wired into the
``/feature-complete``-style cleanup boundary.

The actual ``WorktreeManager.cleanup(...)`` callsite for feature-complete
is in ``feature_orchestrator._clean_state``. ``feature_complete.py``'s
``_archival_phase`` is currently a TASK-FC-003 placeholder and does not
yet call cleanup, so wiring there would emit no warning at runtime. We
target ``_clean_state`` so the AC-010 / AC-011 / AC-012 invariants hold
on the real path.

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureExecution,
    FeatureOrchestration,
    FeatureTask,
)
from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.worktrees import Worktree, WorktreeManager


# ============================================================================
# Helpers
# ============================================================================


def _build_feature(
    feature_id: str, worktree_path: Path, *, with_worktree: bool = True
) -> Feature:
    """Construct a minimal Feature whose execution.worktree_path is set."""
    task = FeatureTask(
        id="TASK-001",
        name="Task 1",
        file_path=Path("tasks/backlog/TASK-001.md"),
        complexity=3,
        dependencies=[],
        status="completed",
        implementation_mode="task-work",
        estimated_minutes=15,
        started_at=None,
        completed_at=None,
        turns_completed=0,
        current_turn=0,
        result=None,
    )
    execution = FeatureExecution(
        started_at=None,
        completed_at=None,
        worktree_path=str(worktree_path) if with_worktree else None,
        current_wave=0,
        completed_waves=[],
        tasks_completed=1,
        tasks_failed=0,
        total_turns=0,
        last_updated=None,
    )
    orchestration = FeatureOrchestration(
        parallel_groups=[["TASK-001"]],
        estimated_duration_minutes=15,
        recommended_parallel=1,
    )
    return Feature(
        id=feature_id,
        name=f"Test {feature_id}",
        description="Integration test fixture",
        created="2026-05-06T00:00:00Z",
        status="in_progress",
        complexity=3,
        estimated_tasks=1,
        tasks=[task],
        orchestration=orchestration,
        execution=execution,
    )


def _make_orchestrator(repo_root: Path) -> tuple[FeatureOrchestrator, MagicMock]:
    """Build a FeatureOrchestrator with a mocked WorktreeManager.cleanup."""
    mock_worktree_manager = MagicMock(spec=WorktreeManager)
    orchestrator = FeatureOrchestrator(
        repo_root=repo_root,
        worktree_manager=mock_worktree_manager,
        skip_validation=True,
    )
    return orchestrator, mock_worktree_manager


def _seed_leaking_pth(repo_root: Path, worktree_path: Path) -> Path:
    """Plant a leaking _editable_impl_*.pth in repo_root/.venv."""
    site_packages = (
        repo_root / ".venv" / "lib" / "python3.13" / "site-packages"
    )
    site_packages.mkdir(parents=True, exist_ok=True)
    pth = site_packages / "_editable_impl_demo.pth"
    pth.write_text(str(worktree_path / "src") + "\n", encoding="utf-8")
    return pth


# ============================================================================
# AC-010: warning emitted, cleanup NOT aborted
# ============================================================================


def test_warns_but_does_not_abort(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    AC-010: leaking .pth in parent .venv → warning printed AND
    WorktreeManager.cleanup is still invoked (with force=True per
    existing _clean_state behaviour).
    """
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-WARN"
    worktree_path.mkdir(parents=True)
    pth_file = _seed_leaking_pth(repo_root, worktree_path)

    orchestrator, mock_wm = _make_orchestrator(repo_root)
    feature = _build_feature("FEAT-WARN", worktree_path)

    with patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.reset_state"
    ), patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"
    ):
        orchestrator._clean_state(feature)

    captured = capsys.readouterr()
    combined = captured.err + captured.out

    # AC-010 (a): warning was emitted with the leaking file path
    assert "warning" in combined.lower()
    assert str(pth_file) in combined
    assert "uv pip install -e . --no-deps" in combined

    # AC-010 (b): cleanup STILL ran
    mock_wm.cleanup.assert_called_once()
    call_kwargs = mock_wm.cleanup.call_args.kwargs
    assert call_kwargs.get("force") is True


# ============================================================================
# AC-011: silent steady state
# ============================================================================


def test_silent_when_no_leaks(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    AC-011: no leaking .pth → no warning emitted (DEBUG log allowed but
    not stderr/stdout WARNING). Cleanup still runs.
    """
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-SILENT"
    worktree_path.mkdir(parents=True)
    # NO leaking .pth — but a non-leaking .pth exists to prove the scanner
    # ran without false-positives.
    site_packages = (
        repo_root / ".venv" / "lib" / "python3.13" / "site-packages"
    )
    site_packages.mkdir(parents=True)
    (site_packages / "_editable_impl_other.pth").write_text(
        "/some/other/place/src\n"
    )

    orchestrator, mock_wm = _make_orchestrator(repo_root)
    feature = _build_feature("FEAT-SILENT", worktree_path)

    with patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.reset_state"
    ), patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"
    ):
        orchestrator._clean_state(feature)

    captured = capsys.readouterr()
    combined = captured.err + captured.out
    assert "warning" not in combined.lower() or "Editable install" not in combined
    assert "Editable install" not in combined

    mock_wm.cleanup.assert_called_once()


# ============================================================================
# AC-012: no Python venv at all (e.g. pure Node project)
# ============================================================================


def test_no_python_venv_no_warning(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    AC-012: project has no .venv directory at all (e.g. pure Node).
    Scanner returns []; no warning; cleanup runs.
    """
    repo_root = tmp_path / "node-project"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-NODE"
    worktree_path.mkdir(parents=True)
    # Note: no .venv/, no .guardkit/venv/ created.

    orchestrator, mock_wm = _make_orchestrator(repo_root)
    feature = _build_feature("FEAT-NODE", worktree_path)

    with patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.reset_state"
    ), patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"
    ):
        orchestrator._clean_state(feature)

    captured = capsys.readouterr()
    combined = captured.err + captured.out
    assert "Editable install" not in combined

    mock_wm.cleanup.assert_called_once()


# ============================================================================
# Defence-in-depth: scanner crash does not abort cleanup
# ============================================================================


def test_scanner_failure_does_not_abort_cleanup(
    tmp_path: Path,
) -> None:
    """
    Defense-in-depth: even if warn_pth_leaks itself raises (via a bug in
    a future scan-root extension), _clean_state must still call
    WorktreeManager.cleanup. The hook is informational, never blocking.
    """
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-CRASH"
    worktree_path.mkdir(parents=True)

    orchestrator, mock_wm = _make_orchestrator(repo_root)
    feature = _build_feature("FEAT-CRASH", worktree_path)

    with patch(
        "guardkit.orchestrator.feature_orchestrator.warn_pth_leaks",
        side_effect=RuntimeError("forced bug"),
    ), patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.reset_state"
    ), patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"
    ):
        # Must not raise.
        orchestrator._clean_state(feature)

    mock_wm.cleanup.assert_called_once()


# ============================================================================
# Sanity: no worktree → no scan attempted
# ============================================================================


def test_no_worktree_path_skips_scanner(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    AC-004 boundary: when feature.execution.worktree_path is None,
    _clean_state never enters the cleanup branch, so the scanner is not
    invoked. No exception, no warning, no cleanup call.
    """
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()

    orchestrator, mock_wm = _make_orchestrator(repo_root)
    feature = _build_feature("FEAT-NONE", repo_root, with_worktree=False)

    with patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.reset_state"
    ), patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"
    ):
        orchestrator._clean_state(feature)

    captured = capsys.readouterr()
    assert "Editable install" not in (captured.err + captured.out)
    mock_wm.cleanup.assert_not_called()
