"""Unit tests for TASK-FIX-7A02 player-invocation stall classification.

Covers the three summary-hint branches called out in AC5/AC6:

1. 3x Player SDK error (or synthetic recovery report) → ``player_invocation_stall``
   with env-blaming hint quoting the first-turn error.
2. 3x "SDK API error" substring in Coach feedback with real Player reports →
   existing ``unrecoverable_stall`` fallback hint (TASK-REV-8A08 behaviour preserved).
3. 3x real Coach rejection with 0/N criteria passing → ``unrecoverable_stall``
   generic task-blaming hint.

Plus a replay-shape test mirroring the FEAT-FORGE-002 transcripts
(docs/reviews/bdd-acceptance-wired-up/forge-run-[1-2].md) where the Player
failed at the SDK layer on every turn — the classifier should pick
``player_invocation_stall`` and NOT the generic task-blaming text.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.autobuild import TurnRecord


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------


def _make_orchestrator() -> AutoBuildOrchestrator:
    return AutoBuildOrchestrator(repo_root=Path.cwd(), max_turns=10)


def _player_error_result(turn: int, error: str) -> AgentInvocationResult:
    """Build a Player result representing a hard SDK failure with no recovery."""
    return AgentInvocationResult(
        task_id="TASK-TEST-7A02",
        turn=turn,
        agent_type="player",
        success=False,
        report={},
        duration_seconds=0.0,
        error=error,
    )


def _player_synthetic_result(
    turn: int,
    detection_method: str = "git_only",
    original_error: str = "SDK API error: 500",
) -> AgentInvocationResult:
    """Build a Player result representing a *recovered* synthetic report."""
    return AgentInvocationResult(
        task_id="TASK-TEST-7A02",
        turn=turn,
        agent_type="player",
        success=True,
        report={
            "_synthetic": True,
            "_recovery_metadata": {
                "detection_method": detection_method,
                "git_insertions": 0,
                "git_deletions": 0,
            },
            "implementation_notes": (
                f"[RECOVERED via {detection_method}] Original error: {original_error}"
            ),
        },
        duration_seconds=0.0,
        error=None,
    )


def _player_real_result(turn: int) -> AgentInvocationResult:
    """Build a Player result representing a real, successful-at-SDK-layer report."""
    return AgentInvocationResult(
        task_id="TASK-TEST-7A02",
        turn=turn,
        agent_type="player",
        success=True,
        report={
            "files_modified": ["src/feature.py"],
            "files_created": [],
            "tests_written": [{"name": "test_feature", "passes": False}],
            "tests_passed": False,
            "test_count": 1,
            "implementation_notes": "Attempted feature implementation",
            "concerns": [],
        },
        duration_seconds=0.0,
        error=None,
    )


def _turn_from_player_error(
    turn: int, error: str = "SDK API error: 500 Internal Server Error"
) -> TurnRecord:
    return TurnRecord(
        turn=turn,
        player_result=_player_error_result(turn, error),
        coach_result=None,
        decision="error",
        feedback=None,
        timestamp=f"2026-04-24T10:0{turn}:00Z",
    )


def _turn_from_synthetic(
    turn: int,
    detection_method: str = "git_only",
    original_error: str = "SDK API error: 500",
    coach_feedback: str = "0/5 acceptance criteria passing. Implementation incomplete.",
) -> TurnRecord:
    """A turn where the orchestrator rescued the Player via state recovery.

    The Player's report is synthetic; Coach still runs and rejects (synthetic
    reports fail every AC). This is the exact shape of the FEAT-FORGE-002
    regression.
    """
    coach_result = AgentInvocationResult(
        task_id="TASK-TEST-7A02",
        turn=turn,
        agent_type="coach",
        success=True,
        report={"decision": "feedback", "feedback": coach_feedback},
        duration_seconds=0.0,
        error=None,
    )
    return TurnRecord(
        turn=turn,
        player_result=_player_synthetic_result(turn, detection_method, original_error),
        coach_result=coach_result,
        decision="feedback",
        feedback=coach_feedback,
        timestamp=f"2026-04-24T10:0{turn}:00Z",
    )


def _turn_from_sdk_error_feedback(turn: int) -> TurnRecord:
    """A turn where Player succeeded but Coach feedback literally mentions 'SDK API error'.

    Preserves the TASK-REV-8A08 fallback: if Coach's feedback happens to
    include the "SDK API error" substring AND the Player report was real,
    the unrecoverable_stall branch should still render the SDK-env hint —
    NOT the new player_invocation_stall branch.
    """
    coach_feedback = (
        "Turn rejected: SDK API error detected in Player transcript. "
        "Please retry."
    )
    coach_result = AgentInvocationResult(
        task_id="TASK-TEST-7A02",
        turn=turn,
        agent_type="coach",
        success=True,
        report={"decision": "feedback", "feedback": coach_feedback},
        duration_seconds=0.0,
        error=None,
    )
    return TurnRecord(
        turn=turn,
        player_result=_player_real_result(turn),
        coach_result=coach_result,
        decision="feedback",
        feedback=coach_feedback,
        timestamp=f"2026-04-24T10:0{turn}:00Z",
    )


def _turn_from_real_coach_rejection(turn: int) -> TurnRecord:
    """A turn where Player produced a real report and Coach rejected on AC grounds.

    This is the "pure" coach-feedback stall: real Player output, identical
    feedback each turn, 0/N criteria passing. The generic task-blaming hint
    should fire.
    """
    coach_feedback = (
        "0/5 acceptance criteria passing. AC-001: tests not written. "
        "AC-002: implementation missing error handling."
    )
    coach_result = AgentInvocationResult(
        task_id="TASK-TEST-7A02",
        turn=turn,
        agent_type="coach",
        success=True,
        report={"decision": "feedback", "feedback": coach_feedback},
        duration_seconds=0.0,
        error=None,
    )
    return TurnRecord(
        turn=turn,
        player_result=_player_real_result(turn),
        coach_result=coach_result,
        decision="feedback",
        feedback=coach_feedback,
        timestamp=f"2026-04-24T10:0{turn}:00Z",
    )


# ---------------------------------------------------------------------------
# Detector: _is_player_invocation_failure / _is_player_invocation_stalled
# ---------------------------------------------------------------------------


class TestPlayerInvocationFailure:
    """Single-turn ``_is_player_invocation_failure`` classification."""

    def test_player_error_is_invocation_failure(self):
        orch = _make_orchestrator()
        turn = _turn_from_player_error(1)
        assert orch._is_player_invocation_failure(turn) is True

    def test_synthetic_report_is_invocation_failure(self):
        orch = _make_orchestrator()
        turn = _turn_from_synthetic(1)
        assert orch._is_player_invocation_failure(turn) is True

    def test_real_player_report_is_not_invocation_failure(self):
        orch = _make_orchestrator()
        turn = _turn_from_real_coach_rejection(1)
        assert orch._is_player_invocation_failure(turn) is False

    def test_sdk_error_in_coach_feedback_is_not_invocation_failure(self):
        """Coach-feedback string-matching must NOT mask a real Player report.

        TASK-REV-8A08 fallback: that branch cares about what Coach SAID,
        not whether the Player succeeded at the SDK layer.
        """
        orch = _make_orchestrator()
        turn = _turn_from_sdk_error_feedback(1)
        assert orch._is_player_invocation_failure(turn) is False


class TestPlayerInvocationStalled:
    """Multi-turn ``_is_player_invocation_stalled`` aggregate classification."""

    def test_three_player_errors_stall(self):
        orch = _make_orchestrator()
        history = [_turn_from_player_error(i) for i in range(1, 4)]
        assert orch._is_player_invocation_stalled(history) is True

    def test_three_synthetic_reports_stall(self):
        orch = _make_orchestrator()
        history = [_turn_from_synthetic(i) for i in range(1, 4)]
        assert orch._is_player_invocation_stalled(history) is True

    def test_mixed_synthetic_and_error_stalls(self):
        """Either signal counts — synthetic OR player_result.error."""
        orch = _make_orchestrator()
        history = [
            _turn_from_player_error(1),
            _turn_from_synthetic(2),
            _turn_from_player_error(3),
        ]
        assert orch._is_player_invocation_stalled(history) is True

    def test_below_threshold_does_not_stall(self):
        orch = _make_orchestrator()
        history = [_turn_from_player_error(1), _turn_from_player_error(2)]
        assert orch._is_player_invocation_stalled(history) is False

    def test_real_turn_breaks_stall(self):
        """A single real Player turn among the last N must reset the signal."""
        orch = _make_orchestrator()
        history = [
            _turn_from_player_error(1),
            _turn_from_real_coach_rejection(2),
            _turn_from_player_error(3),
        ]
        assert orch._is_player_invocation_stalled(history) is False

    def test_three_real_rejections_do_not_trigger_player_stall(self):
        """Pure coach-feedback stall must NOT be misclassified as player-invocation stall."""
        orch = _make_orchestrator()
        history = [_turn_from_real_coach_rejection(i) for i in range(1, 4)]
        assert orch._is_player_invocation_stalled(history) is False

    def test_three_sdk_error_feedback_do_not_trigger_player_stall(self):
        """Coach feedback containing 'SDK API error' on real Player reports is the
        TASK-REV-8A08 fallback — player-invocation detector must ignore it."""
        orch = _make_orchestrator()
        history = [_turn_from_sdk_error_feedback(i) for i in range(1, 4)]
        assert orch._is_player_invocation_stalled(history) is False


# ---------------------------------------------------------------------------
# Summary-hint rendering: _build_summary_details
# ---------------------------------------------------------------------------


class TestSummaryHintBranches:
    """AC5 — three distinct summary-hint branches must render correctly."""

    def test_player_invocation_stall_hint_quotes_first_turn_error(self):
        """AC2: quote the first-turn error; suggest env checks, not task changes."""
        orch = _make_orchestrator()
        original_error = "SDK API error: 500 Internal Server Error (turn 1)"
        history = [
            _turn_from_player_error(1, error=original_error),
            _turn_from_player_error(2, error="SDK API error: 500 Internal Server Error (turn 2)"),
            _turn_from_player_error(3, error="SDK API error: 500 Internal Server Error (turn 3)"),
        ]

        summary = orch._build_summary_details(history, "player_invocation_stall")

        # Names the classification
        assert "Player-invocation stall" in summary
        # Quotes first-turn underlying error (AC2)
        assert original_error in summary
        # Lists affected turns
        assert "turns: 1, 2, 3" in summary
        # Env-focused, not task-focused
        assert "claude auth status" in summary or "claude login" in summary
        assert "claude-agent-sdk" in summary
        # Crucially: does NOT task-blame (AC4 negative assertion)
        assert "Review task_type classification" not in summary

    def test_sdk_error_feedback_preserves_existing_fallback_hint(self):
        """AC3 + AC4: TASK-REV-8A08's SDK-feedback branch must keep working.

        Scenario: Player produced real reports; Coach feedback carries the
        'SDK API error' substring. The new player_invocation_stall detector
        does NOT fire (real reports), so classification falls through to
        unrecoverable_stall with the SDK-env fallback hint.
        """
        orch = _make_orchestrator()
        history = [_turn_from_sdk_error_feedback(i) for i in range(1, 4)]

        # Detector confirms this is NOT the new signal-based branch
        assert orch._is_player_invocation_stalled(history) is False

        # The existing unrecoverable_stall branch fires
        summary = orch._build_summary_details(history, "unrecoverable_stall")
        assert "SDK API errors" in summary or "SDK API error" in summary

    def test_real_coach_rejection_emits_task_blaming_hint_unchanged(self):
        """AC4: pure coach-feedback stall (real reports, 0/N) still gets the
        existing 'Review task_type classification...' hint."""
        orch = _make_orchestrator()
        history = [_turn_from_real_coach_rejection(i) for i in range(1, 4)]

        # Detector confirms this is NOT a player-invocation stall
        assert orch._is_player_invocation_stalled(history) is False

        summary = orch._build_summary_details(history, "unrecoverable_stall")
        assert "Review task_type classification" in summary


# ---------------------------------------------------------------------------
# AC6: Replay-shape regression — FEAT-FORGE-002 transcripts
# ---------------------------------------------------------------------------


class TestForgeTranscriptReplay:
    """AC6: replaying FEAT-FORGE-002 transcript shape must classify as
    ``player_invocation_stall``, not the previous misattribution.

    The saved transcripts in ``docs/reviews/bdd-acceptance-wired-up/``
    describe 3+ turns where the Player SDK invocation failed and the
    orchestrator fell back to a synthetic report on every turn. We
    reconstruct that shape in-memory — fidelity of field values isn't
    tested, only the classifier decision.
    """

    def test_forge_run_1_shape_classifies_as_player_invocation_stall(self):
        """Shape: 3 consecutive synthetic recovery reports (git_only detection)."""
        orch = _make_orchestrator()
        history = [
            _turn_from_synthetic(
                turn=1,
                detection_method="git_only",
                original_error="SDK API error: stream interrupted",
            ),
            _turn_from_synthetic(
                turn=2,
                detection_method="git_only",
                original_error="SDK API error: stream interrupted",
            ),
            _turn_from_synthetic(
                turn=3,
                detection_method="git_only",
                original_error="SDK API error: stream interrupted",
            ),
        ]

        assert orch._is_player_invocation_stalled(history) is True

        summary = orch._build_summary_details(history, "player_invocation_stall")
        assert "Player-invocation stall" in summary
        assert "Review task_type classification" not in summary

    def test_forge_run_2_shape_mixed_errors_and_synthetic_classifies_same(self):
        """Shape: mixed hard-error and synthetic-recovery turns."""
        orch = _make_orchestrator()
        history = [
            _turn_from_player_error(1, error="SDK stream closed unexpectedly"),
            _turn_from_synthetic(
                turn=2,
                detection_method="git_test_detection",
                original_error="SDK stream closed unexpectedly",
            ),
            _turn_from_player_error(3, error="SDK stream closed unexpectedly"),
        ]

        assert orch._is_player_invocation_stalled(history) is True

        summary = orch._build_summary_details(history, "player_invocation_stall")
        assert "Player-invocation stall" in summary
        # First-turn error should be quoted verbatim
        assert "SDK stream closed unexpectedly" in summary


# ---------------------------------------------------------------------------
# Constant wiring (FAILURE_CATEGORY_MAP + FinalStatus)
# ---------------------------------------------------------------------------


def test_failure_category_map_includes_new_decision():
    """The orchestrator's FailureCategory vocabulary must know about the new label."""
    from guardkit.orchestrator.autobuild import FAILURE_CATEGORY_MAP

    assert "player_invocation_stall" in FAILURE_CATEGORY_MAP
    # env_failure is the correct category — it is an SDK/auth/env problem,
    # not a task-content problem.
    assert FAILURE_CATEGORY_MAP["player_invocation_stall"] == "env_failure"


def test_progress_status_colors_includes_new_decision():
    """ProgressDisplay must have a color registered for the new final status."""
    from guardkit.orchestrator.progress import ProgressDisplay

    # ProgressDisplay builds the status_colors dict inline inside render_summary.
    # We verify via the rendered output by inspecting the method source — the
    # registration is a simple dict literal, so source-level assertion is
    # sufficient and doesn't require instantiating a Rich console.
    import inspect

    source = inspect.getsource(ProgressDisplay.render_summary)
    assert '"player_invocation_stall"' in source
