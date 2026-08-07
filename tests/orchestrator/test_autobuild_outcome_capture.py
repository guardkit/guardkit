"""Tests for automatic build-outcome capture at every autobuild terminal.

The memory flywheel only turns if finished builds write themselves down.
Before this seam existed, the factory path read priors on every build but
never wrote an outcome back — only the CLI completion path did.

Covers:
- the approved terminal writes a TASK_COMPLETED outcome
- a failed terminal writes a TASK_FAILED outcome (a failed build is exactly
  the prior a future gate wants)
- memory OFF: one plain log line, no write, no raise
- writer unreachable / failing: one plain log line, no raise
- writer slower than the ceiling: one plain log line, no raise, no hang
- orchestrate() reaches its normal result even when the writer blows up

The memory writer is faked in every test — no broker, no store, no network.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.knowledge.entities.outcome import OutcomeType

AUTOBUILD_LOGGER = "guardkit.orchestrator.autobuild"


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """Minimal repo root (no git operations are performed)."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".guardkit").mkdir()
    return tmp_path


@pytest.fixture
def orchestrator(repo_root: Path):
    """AutoBuildOrchestrator with every outside dependency mocked."""
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    return AutoBuildOrchestrator(
        repo_root=repo_root,
        max_turns=3,
        worktree_manager=MagicMock(),
        enable_pre_loop=False,
    )


def _memory_on() -> MagicMock:
    """A fake memory client that reports itself enabled."""
    client = MagicMock()
    client.enabled = True
    return client


def _memory_off() -> MagicMock:
    """A fake memory client that reports itself disabled."""
    client = MagicMock()
    client.enabled = False
    return client


# ============================================================================
# The write itself
# ============================================================================


class TestCaptureOnSuccessTerminal:
    """The approved terminal records a completed outcome."""

    def test_success_terminal_writes_task_completed(self, orchestrator):
        writer = AsyncMock(return_value="OUT-ABCD1234")

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            outcome_id = orchestrator._capture_build_outcome(
                "TASK-CAP-001",
                success=True,
                final_decision="approved",
                turn_history=[MagicMock(), MagicMock()],
                task_title="Wire capture into autobuild",
                requirements="Fire the outcome write at the terminal",
            )

        assert outcome_id == "OUT-ABCD1234"
        writer.assert_awaited_once()
        kwargs = writer.await_args.kwargs
        assert kwargs["outcome_type"] is OutcomeType.TASK_COMPLETED
        assert kwargs["success"] is True
        assert kwargs["task_id"] == "TASK-CAP-001"
        assert kwargs["task_title"] == "Wire capture into autobuild"
        assert kwargs["task_requirements"] == "Fire the outcome write at the terminal"
        assert kwargs["review_cycles"] == 2
        assert kwargs["problems_encountered"] is None
        assert kwargs["feature_id"] == "FEAT-CAP"
        assert kwargs["completed_at"] is not None
        # The repo the build ran in is named in the summary a gate reads back.
        assert orchestrator.repo_root.name in kwargs["summary"]
        # The writer's build_outcome payload drops `summary` and keeps
        # `lessons`, so the same sentence must ride there too.
        assert kwargs["lessons_learned"] == [kwargs["summary"]]

    def test_title_falls_back_to_task_id(self, orchestrator):
        writer = AsyncMock(return_value="OUT-1")

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            orchestrator._capture_build_outcome(
                "TASK-CAP-002",
                success=True,
                final_decision="approved",
                turn_history=[],
            )

        assert writer.await_args.kwargs["task_title"] == "TASK-CAP-002"

    def test_started_at_and_duration_carried_when_known(self, orchestrator):
        from datetime import datetime, timedelta

        started = datetime.now() - timedelta(minutes=7)
        orchestrator._orchestrate_started_at = started
        writer = AsyncMock(return_value="OUT-2")

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            orchestrator._capture_build_outcome(
                "TASK-CAP-003",
                success=True,
                final_decision="approved",
                turn_history=[],
            )

        kwargs = writer.await_args.kwargs
        assert kwargs["started_at"] == started
        assert kwargs["duration_minutes"] == 7


class TestCaptureOnFailureTerminal:
    """A build that stopped without approval is recorded just as carefully."""

    def test_failure_terminal_writes_task_failed(self, orchestrator):
        writer = AsyncMock(return_value="OUT-FAIL0001")

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            outcome_id = orchestrator._capture_build_outcome(
                "TASK-CAP-010",
                success=False,
                final_decision="unrecoverable_stall",
                turn_history=[MagicMock(), MagicMock(), MagicMock()],
                task_title="A build that stalled",
                requirements="Do the thing",
                error="Three consecutive test failures",
            )

        assert outcome_id == "OUT-FAIL0001"
        kwargs = writer.await_args.kwargs
        assert kwargs["outcome_type"] is OutcomeType.TASK_FAILED
        assert kwargs["success"] is False
        assert kwargs["review_cycles"] == 3
        assert kwargs["problems_encountered"] == ["Three consecutive test failures"]
        # The terminal label AND the reason are in the summary, so a future
        # gate can see how this build ended, not merely that it failed.
        assert "unrecoverable_stall" in kwargs["summary"]
        assert "Three consecutive test failures" in kwargs["summary"]
        # ... and in the field the writer's payload actually keeps.
        assert kwargs["lessons_learned"] == [kwargs["summary"]]

    def test_failure_without_error_still_names_the_terminal(self, orchestrator):
        writer = AsyncMock(return_value="OUT-3")

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            orchestrator._capture_build_outcome(
                "TASK-CAP-011",
                success=False,
                final_decision="pre_loop_blocked",
                turn_history=[],
            )

        problems = writer.await_args.kwargs["problems_encountered"]
        assert problems and "pre_loop_blocked" in problems[0]


# ============================================================================
# Loud degrade (the 4c99357d pattern): one plain line, never fatal
# ============================================================================


class TestLoudDegrade:
    """Memory being unavailable is announced once and changes nothing."""

    def test_memory_off_logs_one_warning_and_skips_the_write(
        self, orchestrator, caplog
    ):
        writer = AsyncMock(return_value="OUT-NEVER")

        with caplog.at_level(logging.WARNING, logger=AUTOBUILD_LOGGER), \
             patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=None), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            result = orchestrator._capture_build_outcome(
                "TASK-CAP-020",
                success=True,
                final_decision="approved",
                turn_history=[],
            )

        assert result is None
        writer.assert_not_awaited()
        lines = [
            r.getMessage()
            for r in caplog.records
            if r.name == AUTOBUILD_LOGGER and r.levelno >= logging.WARNING
        ]
        assert len(lines) == 1, lines
        assert "build outcome NOT captured" in lines[0]
        assert "TASK-CAP-020" in lines[0]
        assert "FLEET_MEMORY_ENABLED" in lines[0]

    def test_disabled_client_logs_one_warning_and_skips_the_write(
        self, orchestrator, caplog
    ):
        writer = AsyncMock(return_value="OUT-NEVER")

        with caplog.at_level(logging.WARNING, logger=AUTOBUILD_LOGGER), \
             patch(
                 f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_off()
             ), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            result = orchestrator._capture_build_outcome(
                "TASK-CAP-021",
                success=False,
                final_decision="max_turns_exceeded",
                turn_history=[],
            )

        assert result is None
        writer.assert_not_awaited()
        warnings = [
            r for r in caplog.records
            if r.name == AUTOBUILD_LOGGER and r.levelno >= logging.WARNING
        ]
        assert len(warnings) == 1

    def test_writer_failure_is_one_warning_and_never_raises(
        self, orchestrator, caplog
    ):
        writer = AsyncMock(side_effect=RuntimeError("writer unreachable"))

        with caplog.at_level(logging.WARNING, logger=AUTOBUILD_LOGGER), \
             patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            result = orchestrator._capture_build_outcome(
                "TASK-CAP-022",
                success=True,
                final_decision="approved",
                turn_history=[],
            )

        assert result is None
        lines = [
            r.getMessage()
            for r in caplog.records
            if r.name == AUTOBUILD_LOGGER and r.levelno >= logging.WARNING
        ]
        assert len(lines) == 1, lines
        assert "build outcome NOT captured" in lines[0]
        assert "writer unreachable" in lines[0]
        assert "build result is unaffected" in lines[0]

    def test_writer_is_attempted_once_never_retried(self, orchestrator):
        writer = AsyncMock(side_effect=RuntimeError("writer unreachable"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            orchestrator._capture_build_outcome(
                "TASK-CAP-023",
                success=True,
                final_decision="approved",
                turn_history=[],
            )

        assert writer.await_count == 1

    def test_slow_writer_is_cut_off_and_does_not_hold_the_terminal(
        self, orchestrator, caplog, monkeypatch
    ):
        from guardkit.orchestrator import autobuild as autobuild_module

        monkeypatch.setattr(
            autobuild_module, "OUTCOME_CAPTURE_TIMEOUT_SECONDS", 0.05
        )

        async def _never_answers(**_kwargs) -> str:
            await asyncio.sleep(30)
            return "OUT-TOO-LATE"

        with caplog.at_level(logging.WARNING, logger=AUTOBUILD_LOGGER), \
             patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", _never_answers):
            result = orchestrator._capture_build_outcome(
                "TASK-CAP-024",
                success=True,
                final_decision="approved",
                turn_history=[],
            )

        assert result is None
        lines = [
            r.getMessage()
            for r in caplog.records
            if r.name == AUTOBUILD_LOGGER and r.levelno >= logging.WARNING
        ]
        assert len(lines) == 1, lines
        assert "build outcome NOT captured" in lines[0]


# ============================================================================
# The wiring: orchestrate() fires it at both terminals
# ============================================================================


def _run_orchestrate(orchestrator, final_decision: str, turns: list):
    """Drive orchestrate() to a terminal with all phases stubbed out."""
    mock_worktree = MagicMock()
    mock_worktree.task_id = "TASK-CAP-100"
    mock_worktree.path = orchestrator.repo_root / "worktree"

    with patch.object(orchestrator, "_setup_phase", return_value=mock_worktree), \
         patch.object(orchestrator, "_loop_phase", return_value=(turns, final_decision)), \
         patch.object(orchestrator, "_finalize_phase"), \
         patch(f"{AUTOBUILD_LOGGER}.TaskLoader") as mock_loader:
        mock_loader.load_task.return_value = {
            "frontmatter": {"title": "Capture wiring"},
            "requirements": "test",
            "acceptance_criteria": ["test"],
        }
        return orchestrator.orchestrate(
            task_id="TASK-CAP-100",
            requirements="build the thing",
            acceptance_criteria=["it works"],
        )


class TestOrchestrateFiresCapture:
    """Both terminals fire the write with no operator action."""

    def test_approved_terminal_fires_capture(self, orchestrator):
        turn = MagicMock()
        turn.decision = "approved"
        writer = AsyncMock(return_value="OUT-LIVE0001")

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            result = _run_orchestrate(orchestrator, "approved", [turn])

        assert result.success is True
        writer.assert_awaited_once()
        kwargs = writer.await_args.kwargs
        assert kwargs["outcome_type"] is OutcomeType.TASK_COMPLETED
        assert kwargs["task_id"] == "TASK-CAP-100"
        assert kwargs["task_title"] == "Capture wiring"
        assert kwargs["task_requirements"] == "build the thing"

    def test_failed_terminal_fires_capture(self, orchestrator):
        writer = AsyncMock(return_value="OUT-LIVE0002")

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            result = _run_orchestrate(orchestrator, "max_turns_exceeded", [])

        assert result.success is False
        writer.assert_awaited_once()
        kwargs = writer.await_args.kwargs
        assert kwargs["outcome_type"] is OutcomeType.TASK_FAILED
        assert kwargs["success"] is False
        assert kwargs["problems_encountered"]

    def test_writer_failure_at_the_terminal_does_not_change_the_result(
        self, orchestrator, caplog
    ):
        turn = MagicMock()
        turn.decision = "approved"
        writer = AsyncMock(side_effect=RuntimeError("store is down"))

        with caplog.at_level(logging.WARNING, logger=AUTOBUILD_LOGGER), \
             patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            result = _run_orchestrate(orchestrator, "approved", [turn])

        assert result.success is True
        assert result.final_decision == "approved"
        assert result.error is None
        assert any(
            "build outcome NOT captured" in r.getMessage()
            for r in caplog.records
        )

    def test_memory_off_at_the_terminal_does_not_change_the_result(
        self, orchestrator, caplog
    ):
        writer = AsyncMock(return_value="OUT-NEVER")

        with caplog.at_level(logging.WARNING, logger=AUTOBUILD_LOGGER), \
             patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=None), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome", writer):
            result = _run_orchestrate(orchestrator, "max_turns_exceeded", [])

        assert result.success is False
        assert result.final_decision == "max_turns_exceeded"
        writer.assert_not_awaited()
        assert any(
            "build outcome NOT captured" in r.getMessage()
            for r in caplog.records
        )
