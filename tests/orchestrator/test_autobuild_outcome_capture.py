"""Tests for automatic build-outcome capture at every autobuild terminal.

The memory flywheel only turns if finished builds write themselves down.
Before this seam existed, the factory path read priors on every build but
never wrote an outcome back — only the CLI completion path did.

Covers:
- the approved terminal writes a TASK_COMPLETED outcome
- a failed terminal writes a TASK_FAILED outcome (a failed build is exactly
  the prior a future gate wants)
- a build that crashed or could not even set up is recorded too
- memory OFF: one plain log line, no write, no raise
- writer unreachable / failing: one plain log line, no raise
- a write that publishes NOTHING is not claimed as a capture
- writer slower than the ceiling: one plain log line naming the failure type
- every one of the seven orchestrate() terminals fires the write
- orchestrate() reaches its normal result even when the writer blows up

The memory writer is faked in every test — no broker, no store, no network.
This module opts out of the autouse live-memory fence in tests/conftest.py
(``allow_memory_capture``) because the capture seam is its subject; the writer
underneath it is faked in every single test here.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.knowledge.entities.outcome import OutcomeType
from guardkit.knowledge.outcome_manager import OutcomeCapture

AUTOBUILD_LOGGER = "guardkit.orchestrator.autobuild"

#: This file drives the real capture seam, so it opts out of the autouse fence.
pytestmark = pytest.mark.allow_memory_capture


def _stored(
    outcome_id: str, episode_key: str = "build_outcome:guardkit:TASK"
) -> OutcomeCapture:
    """A capture result that says the episode really landed."""
    return OutcomeCapture(outcome_id, episode_key)


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
        writer = AsyncMock(return_value=_stored("OUT-ABCD1234"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
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
        writer = AsyncMock(return_value=_stored("OUT-1"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
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
        writer = AsyncMock(return_value=_stored("OUT-2"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
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
        writer = AsyncMock(return_value=_stored("OUT-FAIL0001"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
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
        writer = AsyncMock(return_value=_stored("OUT-3"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
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
        writer = AsyncMock(return_value=_stored("OUT-NEVER"))

        with caplog.at_level(logging.WARNING, logger=AUTOBUILD_LOGGER), \
             patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=None), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
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
        writer = AsyncMock(return_value=_stored("OUT-NEVER"))

        with caplog.at_level(logging.WARNING, logger=AUTOBUILD_LOGGER), \
             patch(
                 f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_off()
             ), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
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
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
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
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
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

        async def _never_answers(**_kwargs) -> OutcomeCapture:
            await asyncio.sleep(30)
            return _stored("OUT-TOO-LATE")

        with caplog.at_level(logging.WARNING, logger=AUTOBUILD_LOGGER), \
             patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", _never_answers):
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
        # str(TimeoutError()) is EMPTY, so without the type name the line reads
        # "did not complete ()" and an operator cannot tell a timeout from any
        # other failure. Name the failure.
        assert "TimeoutError" in lines[0]
        assert "()" not in lines[0]


# ============================================================================
# The write must actually land before it is called a capture
# ============================================================================


class TestCaptureIsOnlyClaimedWhenTheEpisodeLands:
    """Everything under this seam is fail-open, so silence is not success.

    ``FleetMemoryClient.add_episode`` catches every error and returns ``None``,
    and the outcome id is minted before any publish is attempted. A caller that
    reads only "did it raise?" prints a green line about an episode that was
    never stored — a false green in exactly the lane whose job is to make
    memory truthful. These tests drive the real writer function with only the
    store call faked.
    """

    def _client_that_publishes(self, episode_key):
        client = MagicMock()
        client.enabled = True
        client.add_episode = AsyncMock(return_value=episode_key)
        return client

    def test_write_that_publishes_nothing_is_not_claimed_as_captured(
        self, orchestrator, caplog
    ):
        # The broker being unreachable, or the writer credential absent,
        # surfaces exactly like this: no exception, no episode key.
        client = self._client_that_publishes(None)

        with caplog.at_level(logging.DEBUG), \
             patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=client), \
             patch(
                 "guardkit.knowledge.outcome_manager.get_memory_client",
                 return_value=client,
             ):
            result = orchestrator._capture_build_outcome(
                "TASK-CAP-030",
                success=True,
                final_decision="approved",
                turn_history=[MagicMock()],
                task_title="A build nobody stored",
                requirements="Do the thing",
            )

        assert result is None
        client.add_episode.assert_awaited_once()

        autobuild_lines = [
            r for r in caplog.records if r.name == AUTOBUILD_LOGGER
        ]
        warnings = [
            r.getMessage()
            for r in autobuild_lines
            if r.levelno >= logging.WARNING
        ]
        assert len(warnings) == 1, warnings
        assert "build outcome NOT captured" in warnings[0]
        assert "TASK-CAP-030" in warnings[0]
        # And critically: NOT one word claiming a capture happened.
        assert not [
            r.getMessage()
            for r in autobuild_lines
            if r.levelno == logging.INFO and "captured for" in r.getMessage()
        ]

    def test_write_that_lands_is_claimed_with_the_store_key(
        self, orchestrator, caplog
    ):
        client = self._client_that_publishes("build_outcome:guardkit:TASK_CAP_031")

        with caplog.at_level(logging.DEBUG), \
             patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=client), \
             patch(
                 "guardkit.knowledge.outcome_manager.get_memory_client",
                 return_value=client,
             ):
            result = orchestrator._capture_build_outcome(
                "TASK-CAP-031",
                success=True,
                final_decision="approved",
                turn_history=[MagicMock()],
            )

        assert result is not None
        assert result.startswith("OUT-")
        infos = [
            r.getMessage()
            for r in caplog.records
            if r.name == AUTOBUILD_LOGGER and r.levelno == logging.INFO
        ]
        assert any("captured for TASK-CAP-031" in line for line in infos), infos
        assert any(
            "build_outcome:guardkit:TASK_CAP_031" in line for line in infos
        ), infos

    def test_a_write_that_did_not_land_still_leaves_the_build_alone(
        self, orchestrator
    ):
        client = self._client_that_publishes(None)
        turn = MagicMock()
        turn.decision = "approved"

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=client), \
             patch(
                 "guardkit.knowledge.outcome_manager.get_memory_client",
                 return_value=client,
             ):
            result = _run_orchestrate(orchestrator, "approved", [turn])

        assert result.success is True
        assert result.final_decision == "approved"


# ============================================================================
# The wiring: orchestrate() fires it at every terminal
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
        writer = AsyncMock(return_value=_stored("OUT-LIVE0001"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
            result = _run_orchestrate(orchestrator, "approved", [turn])

        assert result.success is True
        writer.assert_awaited_once()
        kwargs = writer.await_args.kwargs
        assert kwargs["outcome_type"] is OutcomeType.TASK_COMPLETED
        assert kwargs["task_id"] == "TASK-CAP-100"
        assert kwargs["task_title"] == "Capture wiring"
        assert kwargs["task_requirements"] == "build the thing"

    def test_failed_terminal_fires_capture(self, orchestrator):
        writer = AsyncMock(return_value=_stored("OUT-LIVE0002"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
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
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
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
        writer = AsyncMock(return_value=_stored("OUT-NEVER"))

        with caplog.at_level(logging.WARNING, logger=AUTOBUILD_LOGGER), \
             patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=None), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
            result = _run_orchestrate(orchestrator, "max_turns_exceeded", [])

        assert result.success is False
        assert result.final_decision == "max_turns_exceeded"
        writer.assert_not_awaited()
        assert any(
            "build outcome NOT captured" in r.getMessage()
            for r in caplog.records
        )


# ============================================================================
# The other five terminals: every early exit fires the write too
# ============================================================================
#
# The loop terminal above is the easy one. The early exits — blocked by the QA
# pass bar, blocked at the pre-loop gate (two ways), stopped by a rate limit,
# and the two ways a build can die outright — are where a deleted or
# mis-argumented call would otherwise go unnoticed, because nothing else in the
# suite drives them.


def _drive_orchestrate(orchestrator, **phase_overrides):
    """Drive orchestrate() with the scaffolding stubbed and phases overridden.

    ``phase_overrides`` maps an orchestrator method name to the kwargs for
    ``patch.object`` (``return_value=`` or ``side_effect=``), applied on top of
    the defaults so a test can send any single phase down any path it likes.
    """
    from contextlib import ExitStack

    mock_worktree = MagicMock()
    mock_worktree.task_id = "TASK-CAP-100"
    mock_worktree.path = orchestrator.repo_root / "worktree"

    defaults = {
        "_setup_phase": {"return_value": mock_worktree},
        "_finalize_phase": {},
        "_snapshot_spec_conformance": {},
        "_snapshot_toolchain_declaration": {},
        "_check_qa_pass_bar_precondition": {"return_value": None},
        "_loop_phase": {"return_value": ([], "approved")},
    }

    with ExitStack() as stack:
        for name, kwargs in defaults.items():
            stack.enter_context(patch.object(orchestrator, name, **kwargs))
        loader = stack.enter_context(patch(f"{AUTOBUILD_LOGGER}.TaskLoader"))
        loader.load_task.return_value = {
            "frontmatter": {"title": "Capture wiring"},
            "requirements": "test",
            "acceptance_criteria": ["test"],
        }
        # Applied last so a test's own patch wins over the default.
        for name, kwargs in phase_overrides.items():
            stack.enter_context(patch.object(orchestrator, name, **kwargs))
        return orchestrator.orchestrate(
            task_id="TASK-CAP-100",
            requirements="build the thing",
            acceptance_criteria=["it works"],
        )


def _blocked_pass_bar():
    """A QA pass-bar precondition that refuses the task start."""
    precondition = MagicMock()
    precondition.passed = False
    precondition.detail = "no pinned pass bar for this task"
    return precondition


class TestEveryEarlyTerminalFiresCapture:
    """Each early exit records its outcome without any operator action."""

    def test_qa_precondition_blocked_fires_capture(self, orchestrator):
        writer = AsyncMock(return_value=_stored("OUT-QA"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
            result = _drive_orchestrate(
                orchestrator,
                _check_qa_pass_bar_precondition={
                    "return_value": _blocked_pass_bar()
                },
            )

        assert result.final_decision == "qa_precondition_blocked"
        writer.assert_awaited_once()
        kwargs = writer.await_args.kwargs
        assert kwargs["outcome_type"] is OutcomeType.TASK_FAILED
        assert kwargs["task_id"] == "TASK-CAP-100"
        assert "qa_precondition_blocked" in kwargs["summary"]

    def test_pre_loop_checkpoint_rejection_fires_capture(self, orchestrator):
        orchestrator.enable_pre_loop = True
        writer = AsyncMock(return_value=_stored("OUT-PL1"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
            result = _drive_orchestrate(
                orchestrator,
                _pre_loop_phase={"return_value": {"checkpoint_passed": False}},
            )

        assert result.final_decision == "pre_loop_blocked"
        writer.assert_awaited_once()
        kwargs = writer.await_args.kwargs
        assert kwargs["outcome_type"] is OutcomeType.TASK_FAILED
        assert "pre_loop_blocked" in kwargs["summary"]

    def test_pre_loop_quality_gate_block_fires_capture(self, orchestrator):
        from guardkit.orchestrator import autobuild as autobuild_module

        orchestrator.enable_pre_loop = True
        writer = AsyncMock(return_value=_stored("OUT-PL2"))
        blocked = autobuild_module.QualityGateBlocked("architecture review said no")

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
            result = _drive_orchestrate(
                orchestrator, _pre_loop_phase={"side_effect": blocked}
            )

        assert result.final_decision == "pre_loop_blocked"
        writer.assert_awaited_once()
        assert "architecture review said no" in writer.await_args.kwargs["summary"]

    def test_rate_limited_fires_capture(self, orchestrator):
        from guardkit.orchestrator import autobuild as autobuild_module

        writer = AsyncMock(return_value=_stored("OUT-RL"))
        limited = autobuild_module.RateLimitExceededError(
            "rate limit hit", reset_time="10:00"
        )

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer):
            result = _drive_orchestrate(
                orchestrator, _loop_phase={"side_effect": limited}
            )

        # The result itself is the regression guard: the rate limit fired
        # before Phase 3 ever assigned the local turn history, so a handler
        # that read the local name raised UnboundLocalError instead of
        # returning a result.
        assert result.final_decision == "rate_limited"
        assert result.total_turns == 0
        assert result.turn_history == []

        writer.assert_awaited_once()
        kwargs = writer.await_args.kwargs
        assert kwargs["outcome_type"] is OutcomeType.TASK_FAILED
        assert "rate_limited" in kwargs["summary"]

    def test_setup_failure_fires_capture_then_still_raises(self, orchestrator):
        from guardkit.orchestrator import autobuild as autobuild_module

        writer = AsyncMock(return_value=_stored("OUT-SETUP"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer), \
             pytest.raises(autobuild_module.SetupPhaseError):
            _drive_orchestrate(
                orchestrator,
                _setup_phase={
                    "side_effect": autobuild_module.SetupPhaseError(
                        "worktree creation failed"
                    )
                },
            )

        writer.assert_awaited_once()
        kwargs = writer.await_args.kwargs
        assert kwargs["outcome_type"] is OutcomeType.TASK_FAILED
        assert "setup_failed" in kwargs["summary"]
        assert "worktree creation failed" in kwargs["summary"]

    def test_crash_fires_capture_then_still_raises(self, orchestrator):
        from guardkit.orchestrator import autobuild as autobuild_module

        writer = AsyncMock(return_value=_stored("OUT-CRASH"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer), \
             pytest.raises(autobuild_module.OrchestrationError):
            _drive_orchestrate(
                orchestrator,
                _loop_phase={"side_effect": RuntimeError("the player died")},
            )

        # A build that died mid-flight is the case a future gate most wants to
        # read back, so it must be written down like any other terminal.
        writer.assert_awaited_once()
        kwargs = writer.await_args.kwargs
        assert kwargs["outcome_type"] is OutcomeType.TASK_FAILED
        assert "crashed" in kwargs["summary"]
        assert "RuntimeError" in kwargs["summary"]

    def test_a_broken_writer_never_masks_the_original_crash(self, orchestrator):
        from guardkit.orchestrator import autobuild as autobuild_module

        writer = AsyncMock(side_effect=RuntimeError("store is down"))

        with patch(f"{AUTOBUILD_LOGGER}.get_memory_client", return_value=_memory_on()), \
             patch(f"{AUTOBUILD_LOGGER}.capture_task_outcome_verified", writer), \
             pytest.raises(autobuild_module.OrchestrationError) as excinfo:
            _drive_orchestrate(
                orchestrator,
                _loop_phase={"side_effect": RuntimeError("the player died")},
            )

        assert "the player died" in str(excinfo.value)
