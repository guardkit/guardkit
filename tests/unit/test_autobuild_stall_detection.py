"""
Unit tests for AutoBuild stall detection mechanisms (TASK-AB-SD01).

Tests cover both stall detection mechanisms:
1. No-passing-checkpoint exit: When should_rollback() fires but no passing checkpoint exists
2. Repeated identical feedback exit: When Coach gives identical feedback N turns with 0% progress

Coverage Target: >=85%
Test Count: 14 tests
"""

import json
import logging

import pytest
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, MagicMock, patch, AsyncMock

import sys

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.evidence_repos import EvidenceTestResult
from guardkit.orchestrator.progress import FinalStatus

# Import worktree components
from guardkit.worktrees import Worktree


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree():
    """Create mock Worktree instance."""
    worktree = Mock(spec=Worktree)
    worktree.task_id = "TASK-SD-001"
    worktree.path = Path("/tmp/worktrees/TASK-SD-001")
    worktree.branch_name = "autobuild/TASK-SD-001"
    worktree.base_branch = "main"
    return worktree


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    """Create mock WorktreeManager."""
    manager = Mock()
    manager.create.return_value = mock_worktree
    manager.preserve_on_failure.return_value = None
    manager.worktrees_dir = Path("/tmp/worktrees")
    return manager


@pytest.fixture
def mock_agent_invoker():
    """Create mock AgentInvoker."""
    invoker = Mock()
    invoker.invoke_player = AsyncMock()
    invoker.invoke_coach = AsyncMock()
    return invoker


@pytest.fixture
def mock_progress_display():
    """Create mock ProgressDisplay."""
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.render_summary = Mock()
    display.render_blocked_report = Mock()
    display.console = Mock()
    return display


@pytest.fixture
def mock_checkpoint_manager():
    """Create mock WorktreeCheckpointManager."""
    manager = Mock()
    manager.create_checkpoint.return_value = Mock(commit_hash="abc12345")
    return manager


@pytest.fixture
def mock_pre_loop_gates():
    """Create mock PreLoopQualityGates."""
    gates = MagicMock()
    from guardkit.orchestrator.quality_gates.pre_loop import PreLoopResult

    async def mock_execute(*args, **kwargs):
        return PreLoopResult(
            plan={"steps": ["Step 1"]},
            plan_path="/tmp/plan.md",
            complexity=5,
            max_turns=5,
            checkpoint_passed=True,
            architectural_score=85,
            clarifications={},
        )

    gates.execute = mock_execute
    return gates


@pytest.fixture
def mock_coach_validator():
    """Patch CoachValidator to force SDK fallback."""
    with patch(
        "guardkit.orchestrator.autobuild.CoachValidator"
    ) as mock_validator_class:
        mock_instance = MagicMock()
        mock_instance.validate.side_effect = Exception("Force SDK fallback for test")
        mock_validator_class.return_value = mock_instance
        yield mock_validator_class


def make_player_result(
    task_id: str = "TASK-SD-001",
    turn: int = 1,
    success: bool = True,
    tests_passed: bool = True,
) -> AgentInvocationResult:
    """Helper to create Player AgentInvocationResult."""
    report = {
        "task_id": task_id,
        "turn": turn,
        "files_modified": ["src/file.py"],
        "files_created": ["src/new.py"],
        "tests_written": ["tests/test_file.py"],
        "tests_run": True,
        "tests_passed": tests_passed,
        "implementation_notes": "Implementation attempt",
        "concerns": [],
        "requirements_addressed": [],
        "requirements_remaining": [],
    }
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=success,
        report=report,
        duration_seconds=10.0,
        error=None,
    )


def make_coach_result(
    task_id: str = "TASK-SD-001",
    turn: int = 1,
    decision: str = "feedback",
    feedback_text: str = "Fix type hints in user.py",
    criteria_results: Optional[list] = None,
    criteria_met: int = 0,
    criteria_total: int = 0,
) -> AgentInvocationResult:
    """Helper to create Coach AgentInvocationResult with feedback.

    TASK-CRV-90FB: Includes both validation_results.requirements (authoritative)
    and acceptance_criteria_verification (legacy) to match real Coach output.
    """
    cr = criteria_results or []
    report = {
        "task_id": task_id,
        "turn": turn,
        "decision": decision,
        "acceptance_criteria_verification": {
            "criteria_results": cr,
        },
        "validation_results": {
            "requirements": {
                "criteria_total": criteria_total,
                "criteria_met": criteria_met,
                "all_criteria_met": criteria_met == criteria_total and criteria_total > 0,
                "missing": [],
            },
        },
    }
    if decision == "feedback":
        report["issues"] = [
            {
                "type": "missing_requirement",
                "severity": "major",
                "description": feedback_text,
                "suggestion": feedback_text,
            }
        ]
        report["rationale"] = feedback_text
    elif decision == "approve":
        report["validation_results"]["tests_run"] = True
        report["validation_results"]["tests_passed"] = True
        report["rationale"] = "All requirements met"

    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report=report,
        duration_seconds=5.0,
        error=None,
    )


# ============================================================================
# Test _is_feedback_stalled (Mechanism 2)
# ============================================================================


class TestIsFeedbackStalled:
    """Test the _is_feedback_stalled method for repeated feedback detection."""

    def test_no_stall_below_threshold(self):
        """First two turns with identical feedback should not trigger stall."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False

    def test_stall_on_3_identical_feedback_zero_progress(self):
        """3 identical feedback turns with 0 criteria passed triggers stall."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is True

    def test_no_stall_when_criteria_progress(self):
        """Identical feedback with criteria progress should not stall."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 1) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 1) is False

    def test_no_stall_when_feedback_changes(self):
        """Different feedback each turn should not stall."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Add error handling", 0) is False
        assert orchestrator._is_feedback_stalled("Missing tests", 0) is False

    def test_stall_case_insensitive(self):
        """Feedback comparison should be case-insensitive."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator._is_feedback_stalled("Fix Type Hints", 0) is False
        assert orchestrator._is_feedback_stalled("fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("FIX TYPE HINTS", 0) is True

    def test_stall_whitespace_normalized(self):
        """Feedback comparison should normalize whitespace."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator._is_feedback_stalled("  Fix type hints  ", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled(" Fix type hints ", 0) is True

    def test_custom_threshold(self):
        """Custom threshold should be respected."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )

        for i in range(4):
            result = orchestrator._is_feedback_stalled("Fix hints", 0, threshold=5)
            assert result is False

        assert orchestrator._is_feedback_stalled("Fix hints", 0, threshold=5) is True

    def test_stall_resets_on_different_feedback(self):
        """After 2 identical then a different one, counter resets."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        orchestrator._is_feedback_stalled("Fix type hints", 0)
        orchestrator._is_feedback_stalled("Fix type hints", 0)
        # Different feedback breaks the streak
        orchestrator._is_feedback_stalled("Add docstrings", 0)
        # Resume same feedback - need 3 more consecutive
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is True


# ============================================================================
# Test absent sibling-repo signal immunity (TASK-FIX-SIBTESTENV01 AC-3)
# ============================================================================


class TestAbsentEvidenceRepoSignalImmunity:
    """A turn blocked by a pure-ABSENT evidence_repos signal (environment
    problem — e.g. a collection ImportError from a mis-resolved interpreter)
    must be excluded from the feedback-stall tally entirely, so it can never
    stack into ``unrecoverable_stall`` (the FEAT-10AC run-2 kill mechanism).
    Bounded termination is preserved by ``max_turns``.
    """

    _FEEDBACK = (
        "Sibling-repo (evidence_repos) independent tests did not pass:\n"
        "- guardkitfactory: declared sibling-repo tests could NOT run "
        "(`python -m pytest tests/wiring -q`)"
    )

    def _turn_record_with_report(self, report: dict) -> Mock:
        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.report = report
        return turn_record

    def test_absent_marker_feedback_never_stalls(self):
        """Identical absent-marker feedback across 3+ turns never stalls."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )
        turn_record = self._turn_record_with_report(
            {
                "decision": "feedback",
                "coach_primary_synthetic_feedback": True,
                "evidence_repo_signal_absent": True,
            }
        )

        for _ in range(5):
            assert (
                orchestrator._is_feedback_stalled(
                    self._FEEDBACK, 0, turn_record=turn_record
                )
                is False
            )
        # Excluded from the tally entirely: the history window never grew.
        assert orchestrator._feedback_history == []

    def test_ran_and_failed_sibling_feedback_still_stalls_at_3(self):
        """Control: a genuine ran-and-failed sibling suite still stalls."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )
        turn_record = self._turn_record_with_report(
            {
                "decision": "feedback",
                "coach_primary_synthetic_feedback": True,
                "evidence_repo_signal_absent": False,
            }
        )

        feedback = (
            "Sibling-repo (evidence_repos) independent tests did not pass:\n"
            "- guardkitfactory: sibling-repo tests FAILED (exit 1)"
        )
        assert orchestrator._is_feedback_stalled(feedback, 0, turn_record=turn_record) is False
        assert orchestrator._is_feedback_stalled(feedback, 0, turn_record=turn_record) is False
        assert orchestrator._is_feedback_stalled(feedback, 0, turn_record=turn_record) is True

    def test_marker_nested_in_issues_does_not_trigger_immunity(self):
        """CRITICAL-1 pin: the marker is read from the TOP-LEVEL report key.

        A marker nested inside ``issues`` must NOT trigger immunity — if the
        producer ever moved the key into ``issues``, the extractor would
        silently never fire and the stall would return. This test fails loud
        in the opposite direction: nested-only markers still stall.
        """
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )
        turn_record = self._turn_record_with_report(
            {
                "decision": "feedback",
                "coach_primary_synthetic_feedback": True,
                # NOT at top level — nested inside issues only.
                "issues": [
                    {
                        "severity": "must_fix",
                        "category": "coach_primary_exception",
                        "evidence_repo_signal_absent": True,
                        "description": self._FEEDBACK,
                    }
                ],
            }
        )

        assert orchestrator._is_feedback_stalled(self._FEEDBACK, 0, turn_record=turn_record) is False
        assert orchestrator._is_feedback_stalled(self._FEEDBACK, 0, turn_record=turn_record) is False
        assert orchestrator._is_feedback_stalled(self._FEEDBACK, 0, turn_record=turn_record) is True


class TestEvidenceRepoGateSignalAbsentFlag:
    """_evidence_repo_gate sets evidence_repo_signal_absent ONLY when no
    result is ran-and-failed (pure-absent sets; mixed sets stay
    stall-stackable). TASK-FIX-SIBTESTENV01.
    """

    def _run_gate(self, tmp_path, results):
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )
        validator = Mock()
        validator.run_evidence_repo_tests.return_value = results
        worktree = Mock(spec=Worktree)
        worktree.path = tmp_path
        return orchestrator._evidence_repo_gate(
            validator,
            "TASK-FIX-SIBTESTENV01",
            1,
            worktree,
            0.0,
        )

    def test_pure_absent_results_set_flag_true(self, tmp_path):
        results = [
            EvidenceTestResult(
                repo_name="guardkitfactory",
                command="python -m pytest tests/wiring -q",
                ran=False,
                passed=False,
                returncode=2,
                output_summary="collection failed with an import error",
            )
        ]
        gate_result = self._run_gate(tmp_path, results)
        assert gate_result is not None
        assert gate_result.report["decision"] == "feedback"
        # Top-level key (CRITICAL-1), True for the pure-absent shape.
        assert gate_result.report["evidence_repo_signal_absent"] is True

    def test_mixed_results_with_ran_and_failed_set_flag_false(self, tmp_path):
        results = [
            EvidenceTestResult(
                repo_name="guardkitfactory",
                command="python -m pytest tests/wiring -q",
                ran=False,
                passed=False,
                returncode=2,
                output_summary="collection failed with an import error",
            ),
            EvidenceTestResult(
                repo_name="other",
                command="pytest -q",
                ran=True,
                passed=False,
                returncode=1,
                output_summary="1 failed",
            ),
        ]
        gate_result = self._run_gate(tmp_path, results)
        assert gate_result is not None
        assert gate_result.report["decision"] == "feedback"
        # A genuine ran-and-failed suite is present: stays stall-stackable.
        assert gate_result.report["evidence_repo_signal_absent"] is False


# ============================================================================
# Test _count_criteria_passed
# ============================================================================


class TestCountCriteriaPassed:
    """Test _count_criteria_passed helper method.

    TASK-CRV-90FB: Sources criteria count from Coach's validation_results.requirements.criteria_met
    (authoritative) with fallback to acceptance_criteria_verification counting (legacy).
    """

    def test_count_from_coach_validation_results(self):
        """Should use Coach's criteria_met from validation_results (TASK-CRV-90FB)."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.report = {
            "validation_results": {
                "requirements": {
                    "criteria_total": 3,
                    "criteria_met": 2,
                    "all_criteria_met": False,
                    "missing": ["criterion 3"],
                }
            },
            "acceptance_criteria_verification": {
                "criteria_results": [
                    {"criterion_id": "c1", "status": "verified"},
                    {"criterion_id": "c2", "status": "not_started"},
                    {"criterion_id": "c3", "status": "verified"},
                ]
            },
        }

        assert orchestrator._count_criteria_passed(turn_record) == 2

    def test_count_prefers_coach_over_legacy(self):
        """When Coach reports 0 but legacy criteria_results show 2, use Coach's 0 (TASK-CRV-90FB)."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.report = {
            "validation_results": {
                "requirements": {
                    "criteria_total": 3,
                    "criteria_met": 0,
                    "all_criteria_met": False,
                    "missing": ["c1", "c2", "c3"],
                }
            },
            # Legacy path would count 2 verified, but Coach says 0
            "acceptance_criteria_verification": {
                "criteria_results": [
                    {"criterion_id": "c1", "status": "verified"},
                    {"criterion_id": "c2", "status": "verified"},
                    {"criterion_id": "c3", "status": "not_started"},
                ]
            },
        }

        # Coach's authoritative count (0) takes precedence
        assert orchestrator._count_criteria_passed(turn_record) == 0

    def test_count_fallback_to_legacy_criteria_results(self):
        """Should fall back to counting criteria_results when validation_results absent."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.report = {
            "acceptance_criteria_verification": {
                "criteria_results": [
                    {"criterion_id": "c1", "status": "verified"},
                    {"criterion_id": "c2", "status": "not_started"},
                    {"criterion_id": "c3", "status": "verified"},
                ]
            }
        }

        assert orchestrator._count_criteria_passed(turn_record) == 2

    def test_count_with_no_coach_result(self):
        """Should return 0 when no coach result exists."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = None

        assert orchestrator._count_criteria_passed(turn_record) == 0

    def test_count_with_empty_criteria(self):
        """Should return 0 when no criteria results in report."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.report = {}

        assert orchestrator._count_criteria_passed(turn_record) == 0

    def test_count_with_none_requirements(self):
        """Should fall back to legacy when requirements is None (TASK-CRV-90FB)."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.report = {
            "validation_results": {
                "requirements": None,
            },
            "acceptance_criteria_verification": {
                "criteria_results": [
                    {"criterion_id": "c1", "status": "verified"},
                ]
            },
        }

        assert orchestrator._count_criteria_passed(turn_record) == 1


# ============================================================================
# Test criteria accumulation across turns (TASK-FIX-AE7E Fix 2)
# ============================================================================


class TestCriteriaAccumulationAcrossTurns:
    """Test that orchestrator accumulates peak criteria count across feedback turns.

    When the Player's turn 1 output verified criteria but subsequent turns show 0
    verified criteria (because completion_promises are absent), the stall detector
    should use the peak historical count — NOT the current turn's count — to
    prevent false UNRECOVERABLE_STALL exits.
    """

    def test_max_criteria_initialised_to_zero(self):
        """_max_criteria_passed starts at 0 on a fresh orchestrator."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )
        assert orchestrator._max_criteria_passed == 0

    def test_peak_count_preserved_when_subsequent_turn_drops_to_zero(self):
        """Peak criteria from turn 1 prevents stall even when turn 2-4 show 0 criteria.

        Scenario: turn 1 verified 6 criteria (promises present), turns 2-4
        verify 0 criteria (promises absent). Without accumulation the stall
        detector would fire on turn 4 (0 criteria × 3 identical feedback turns).
        With accumulation, _max_criteria_passed stays 6, which extends the
        stall threshold and avoids a false positive.
        """
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )

        feedback = "Tests are failing in auth module"

        # Simulate: turn 1 counted 6 criteria → update peak
        orchestrator._max_criteria_passed = max(6, orchestrator._max_criteria_passed)
        # Turn 1 feedback (6 criteria peak, not a stall yet)
        assert orchestrator._is_feedback_stalled(feedback, orchestrator._max_criteria_passed) is False

        # Turns 2-4: current turn shows 0 criteria, but peak stays 6
        for _ in range(3):
            orchestrator._max_criteria_passed = max(0, orchestrator._max_criteria_passed)
            result = orchestrator._is_feedback_stalled(feedback, orchestrator._max_criteria_passed)
            # With partial-progress (6 > 0), extended threshold of 5 applies, so no stall yet
            assert result is False, "Should not stall when prior-turn peak shows criteria progress"

    def test_zero_peak_still_stalls_at_threshold(self):
        """If no turn ever verified criteria, stall fires at normal threshold."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        feedback = "Tests are failing"

        # Three turns with 0 criteria — should stall
        for i in range(2):
            orchestrator._max_criteria_passed = max(0, orchestrator._max_criteria_passed)
            assert orchestrator._is_feedback_stalled(feedback, orchestrator._max_criteria_passed) is False

        orchestrator._max_criteria_passed = max(0, orchestrator._max_criteria_passed)
        assert orchestrator._is_feedback_stalled(feedback, orchestrator._max_criteria_passed) is True


# ============================================================================
# Test No-Passing-Checkpoint Stall (Mechanism 1) in _loop_phase
# ============================================================================


class TestNoPassingCheckpointStall:
    """Test stall detection when should_rollback fires but no passing checkpoint."""

    def test_stall_on_no_passing_checkpoint(
        self,
        mock_worktree,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
        mock_checkpoint_manager,
    ):
        """When should_rollback=True and find_last_passing=None, exit with unrecoverable_stall."""
        # Configure checkpoint manager to trigger stall
        mock_checkpoint_manager.should_rollback.return_value = True
        mock_checkpoint_manager.find_last_passing_checkpoint.return_value = None

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
            enable_checkpoints=True,
            rollback_on_pollution=True,
        )
        orchestrator._checkpoint_manager = mock_checkpoint_manager

        # Mock Player and Coach to produce feedback (not approve) so loop continues
        player_result = make_player_result(tests_passed=False)
        coach_result = make_coach_result(decision="feedback")

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.return_value = coach_result

        turn_history, final_decision = orchestrator._loop_phase(
            task_id="TASK-SD-001",
            requirements="Test requirements",
            acceptance_criteria=["criterion 1"],
            worktree=mock_worktree,
        )

        assert final_decision == "unrecoverable_stall"
        # Should exit early, not run all max_turns
        assert len(turn_history) <= 2  # at most 2 turns (need 2 consecutive failures)

    def test_normal_rollback_when_checkpoint_exists(
        self,
        mock_worktree,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
        mock_checkpoint_manager,
    ):
        """When should_rollback=True and checkpoint exists, rollback normally (no stall).

        Updated for TASK-FIX-CKPT: approval is now checked before stall detection,
        so the test uses feedback on turn 1 (where rollback triggers) and approve
        on the subsequent turn after rollback.
        """
        # Turn 1: should_rollback=True with passing checkpoint → rollback
        # After rollback, loop continues from rollback point
        # Turn 2 (post-rollback): should_rollback=False
        mock_checkpoint_manager.should_rollback.side_effect = [True, False, False, False, False]
        mock_checkpoint_manager.find_last_passing_checkpoint.return_value = 1
        mock_checkpoint_manager.rollback_to.return_value = True

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=3,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
            enable_checkpoints=True,
            rollback_on_pollution=True,
        )
        orchestrator._checkpoint_manager = mock_checkpoint_manager

        player_result = make_player_result(tests_passed=True)
        # Turn 1: feedback (rollback triggers), Turn 2: approve (after rollback)
        coach_feedback = make_coach_result(decision="feedback", feedback_text="Fix issues")
        coach_approve = make_coach_result(decision="approve")

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.side_effect = [coach_feedback, coach_approve]

        turn_history, final_decision = orchestrator._loop_phase(
            task_id="TASK-SD-001",
            requirements="Test requirements",
            acceptance_criteria=["criterion 1"],
            worktree=mock_worktree,
        )

        # Should NOT be unrecoverable_stall since rollback succeeded
        assert final_decision != "unrecoverable_stall"
        assert final_decision == "approved"
        mock_checkpoint_manager.rollback_to.assert_called_once_with(1)

    def test_rollback_clears_player_session(
        self,
        mock_worktree,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
        mock_checkpoint_manager,
    ):
        """TASK-FIX-RBSS AC-2: rollback clears the Player SDK resume session.

        After ``rollback_to(target_turn)`` fires, the orchestrator must call
        ``AgentInvoker.set_player_resume_session(None)`` before the next
        loop iteration so the next Player turn does not resume the prior
        turn's polluted cumulative-authoring memory of files the rollback
        just deleted. The call must be ordered AFTER ``rollback_to`` and
        AFTER the per-turn ``set_player_resume_session(<live id>)`` write
        at the end of the just-completed turn (so the live id does not
        clobber the reset).
        """
        # Turn 1 triggers rollback; turn 2 (post-rollback) approves.
        mock_checkpoint_manager.should_rollback.side_effect = [True, False, False]
        mock_checkpoint_manager.find_last_passing_checkpoint.return_value = 1
        mock_checkpoint_manager.rollback_to.return_value = True

        # Wire a parent mock so cross-mock call ordering is observable.
        order_witness = Mock()
        order_witness.attach_mock(mock_checkpoint_manager.rollback_to, "rollback_to")
        order_witness.attach_mock(
            mock_agent_invoker.set_player_resume_session,
            "set_player_resume_session",
        )

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=3,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
            enable_checkpoints=True,
            rollback_on_pollution=True,
        )
        orchestrator._checkpoint_manager = mock_checkpoint_manager

        player_result = make_player_result(tests_passed=True)
        # Give it a session_id so the per-turn end-of-loop set_player_resume_session
        # call also fires — the test then pins that the rollback-side reset
        # follows it (i.e. the rollback's None overrides the live id).
        player_result.session_id = "live-session-abc"
        coach_feedback = make_coach_result(decision="feedback", feedback_text="Fix issues")
        coach_approve = make_coach_result(decision="approve")

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.side_effect = [coach_feedback, coach_approve]

        turn_history, final_decision = orchestrator._loop_phase(
            task_id="TASK-SD-001",
            requirements="Test requirements",
            acceptance_criteria=["criterion 1"],
            worktree=mock_worktree,
        )

        # The rollback path executed.
        mock_checkpoint_manager.rollback_to.assert_called_once_with(1)
        # AC-2 core assertion: the SDK resume session was cleared with None.
        mock_agent_invoker.set_player_resume_session.assert_any_call(None)

        # Pin ordering: the None reset comes AFTER rollback_to, AND the None
        # reset comes AFTER any preceding live-session write (so the rollback
        # outcome wins for the next turn).
        recorded_calls = order_witness.method_calls
        rollback_idx = next(
            (i for i, c in enumerate(recorded_calls) if c[0] == "rollback_to"),
            None,
        )
        assert rollback_idx is not None, "rollback_to must have been called"
        # The first set_player_resume_session(None) at or after rollback_idx.
        post_rollback_resets = [
            c for c in recorded_calls[rollback_idx:]
            if c[0] == "set_player_resume_session" and c.args == (None,)
        ]
        assert post_rollback_resets, (
            "set_player_resume_session(None) must be called after rollback_to "
            "(AC-1 ordering)"
        )

        # Sanity: loop did not stall.
        assert final_decision != "unrecoverable_stall"
        assert final_decision == "approved"


# ============================================================================
# Test Repeated Feedback Stall (Mechanism 2) in _loop_phase
# ============================================================================


class TestRepeatedFeedbackStallInLoop:
    """Test that repeated feedback stall exits the loop."""

    def test_stall_exits_loop_on_identical_feedback(
        self,
        mock_worktree,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
    ):
        """3 turns with identical Coach feedback and 0% criteria progress exits loop."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
            enable_checkpoints=False,  # Disable to isolate feedback stall test
        )

        # Player always succeeds
        player_result = make_player_result(tests_passed=True)
        mock_agent_invoker.invoke_player.return_value = player_result

        # Coach always gives identical feedback with 0 criteria verified
        coach_feedback = make_coach_result(
            decision="feedback",
            feedback_text="Fix type hints in user.py",
            criteria_results=[
                {"criterion_id": "c1", "status": "not_started"},
            ],
        )
        mock_agent_invoker.invoke_coach.return_value = coach_feedback

        turn_history, final_decision = orchestrator._loop_phase(
            task_id="TASK-SD-001",
            requirements="Test requirements",
            acceptance_criteria=["criterion 1"],
            worktree=mock_worktree,
        )

        assert final_decision == "unrecoverable_stall"
        # Should exit at turn 3 (not run all 10)
        assert len(turn_history) == 3


# ============================================================================
# Test Status Propagation
# ============================================================================


class TestStallStatusPropagation:
    """Test that unrecoverable_stall status propagates correctly."""

    def test_build_summary_details_stall(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
    ):
        """_build_summary_details includes stall information."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
        )

        summary = orchestrator._build_summary_details([], "unrecoverable_stall")
        assert "Unrecoverable stall" in summary
        assert "cannot make forward progress" in summary.lower()

    def test_build_error_message_stall(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
    ):
        """_build_error_message includes stall context."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
        )

        error_msg = orchestrator._build_error_message("unrecoverable_stall", [])
        assert "stall" in error_msg.lower()
        assert "cannot make forward progress" in error_msg.lower()

    def test_finalize_phase_handles_stall(
        self,
        mock_worktree,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
    ):
        """_finalize_phase preserves worktree and renders summary for stall."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
        )

        orchestrator._finalize_phase(
            worktree=mock_worktree,
            final_decision="unrecoverable_stall",
            turn_history=[],
        )

        # Worktree should be preserved
        mock_worktree_manager.preserve_on_failure.assert_called_once_with(mock_worktree)
        # Summary should be rendered
        mock_progress_display.render_summary.assert_called_once()


# ============================================================================
# Test FinalStatus Type in progress.py
# ============================================================================


class TestProgressDisplayStallStatus:
    """Test that progress.py FinalStatus type includes unrecoverable_stall."""

    def test_final_status_includes_stall(self):
        """FinalStatus type alias should accept 'unrecoverable_stall'."""
        # This test validates that the Literal type was extended.
        # If the type doesn't include 'unrecoverable_stall', mypy would catch it.
        status: FinalStatus = "unrecoverable_stall"
        assert status == "unrecoverable_stall"


# ============================================================================
# Test SDK API error stall hint message (TASK-FIX-d5e6)
# ============================================================================


class TestStallHintSdkApiError:
    """Test that stall termination shows targeted SDK API error message."""

    def _make_turn_record(self, turn: int, feedback: str) -> TurnRecord:
        """Helper to create a TurnRecord with feedback."""
        player_result = Mock(spec=AgentInvocationResult)
        coach_result = Mock(spec=AgentInvocationResult)
        return TurnRecord(
            turn=turn,
            player_result=player_result,
            coach_result=coach_result,
            decision="feedback",
            feedback=feedback,
            timestamp="2026-02-24T00:00:00Z",
        )

    def test_sdk_api_error_stall_shows_targeted_hint(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
    ):
        """When all recent feedback contains 'SDK API error', show targeted message."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
        )

        turn_history = [
            self._make_turn_record(1, "SDK API error: invalid_request — model not found"),
            self._make_turn_record(2, "SDK API error: invalid_request — model not found"),
            self._make_turn_record(3, "SDK API error: invalid_request — model not found"),
        ]

        message = orchestrator._build_summary_details(turn_history, "unrecoverable_stall")

        assert "SDK API errors" in message
        assert "ANTHROPIC_BASE_URL" in message
        assert "SERVED_MODEL_NAME" in message

    def test_non_sdk_stall_shows_generic_hint(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
    ):
        """When feedback is not SDK API errors, show generic stall hint."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
        )

        turn_history = [
            self._make_turn_record(1, "Tests are failing due to assertion errors"),
            self._make_turn_record(2, "Tests are failing due to assertion errors"),
            self._make_turn_record(3, "Tests are failing due to assertion errors"),
        ]

        message = orchestrator._build_summary_details(turn_history, "unrecoverable_stall")

        assert "Review task_type classification" in message
        assert "SDK API errors" not in message

    def test_mixed_feedback_shows_generic_hint(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
    ):
        """When feedback is mixed (not all SDK API errors), show generic hint."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
        )

        turn_history = [
            self._make_turn_record(1, "SDK API error: invalid_request"),
            self._make_turn_record(2, "Tests are failing due to assertion errors"),
            self._make_turn_record(3, "SDK API error: invalid_request"),
        ]

        message = orchestrator._build_summary_details(turn_history, "unrecoverable_stall")

        assert "Review task_type classification" in message
        assert "SDK API errors" not in message


# ============================================================================
# close-the-loop lane, 2026-08-14 — CURE 2 (effect) and CURE 3 (naming)
# ============================================================================


class TestHonestCountChangesTheStallBranch:
    """A truthful non-zero count routes to the extended threshold.

    ``_is_feedback_stalled`` and ``_count_criteria_passed`` are NOT edited by
    this lane. Their behaviour changes only because the direct-mode gate now
    feeds them the count it had already measured. The r3 arm-B receipts logged
    ``identical feedback (sig=...) for 3 turns with 0 criteria passing`` while
    the gate's own ``req_validation`` said 4 of 6 — the leg died at 3 turns on
    the "true zero progress — unrecoverable" branch instead of taking the +2
    extended runway.

    Bound: this is still capped by ``max_turns``. Under the production
    ``leg_max_turns: 3`` the work leg's observable behaviour is unchanged —
    the cap binds first; the leg exits with the honest ``max_turns_exceeded``
    label rather than a false ``unrecoverable_stall``.
    """

    _FEEDBACK = (
        "Direct mode: 2/6 acceptance criteria have no matching completion "
        "promise (unmet: ['AC-ANTISTUB-1', 'AC-ANTISTUB-2'])."
    )

    def _orch(self):
        return AutoBuildOrchestrator(repo_root=Path.cwd(), max_turns=10)

    def test_zero_count_still_stalls_at_three(self):
        """Unchanged behaviour when the count really is zero."""
        orch = self._orch()
        assert orch._is_feedback_stalled(self._FEEDBACK, 0) is False
        assert orch._is_feedback_stalled(self._FEEDBACK, 0) is False
        assert orch._is_feedback_stalled(self._FEEDBACK, 0) is True

    def test_count_of_four_survives_three_turns_and_stalls_at_five(self):
        """The honest count buys the +2 extended runway, then still stops."""
        orch = self._orch()
        for _ in range(3):
            assert orch._is_feedback_stalled(self._FEEDBACK, 4) is False
        assert orch._is_feedback_stalled(self._FEEDBACK, 4) is False
        # Fifth identical turn at the same non-zero count: stall, honestly.
        assert orch._is_feedback_stalled(self._FEEDBACK, 4) is True

    def test_extended_branch_names_the_count_it_held(self, caplog):
        orch = self._orch()
        with caplog.at_level(logging.WARNING):
            for _ in range(5):
                orch._is_feedback_stalled(self._FEEDBACK, 4)
        assert "criteria-passed count held at 4" in caplog.text

    def test_zero_branch_names_what_it_consulted(self, caplog):
        """CURE 3: the warning states both quantities and why 0 can be a lie."""
        orch = self._orch()
        with caplog.at_level(logging.WARNING):
            for _ in range(3):
                orch._is_feedback_stalled(self._FEEDBACK, 0)
        assert "feedback signature" in caplog.text
        assert "criteria-passed count read 0" in caplog.text
        assert "a report with no requirements block reads as 0" in caplog.text


class TestDirectModeGateReportsWhatItMeasured:
    """End-to-end through the real gate, on disk, mocks only (no broker)."""

    _AC = [
        "- [ ] Implementation complete",
        "- [ ] AC-ANTISTUB-1: All primary deliverable functions contain "
        "meaningful implementation logic (no stubs, pass-only bodies, or TODOs)",
    ]

    def _worktree(self, tmp_path: Path) -> Path:
        import subprocess

        subprocess.run(
            ["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True
        )
        return tmp_path

    def _write_results(self, worktree: Path, promises) -> None:
        results = {
            "task_id": "TASK-CTL-002",
            "implementation_mode": "direct",
            "completed": True,
            "success": True,
            "quality_gates": {
                "all_passed": True,
                "tests_passing": True,
                "quality_gates_relaxed": True,
            },
            "files_created": [],
            "files_modified": [],
            "tests_written": [],
            "completion_promises": promises,
            "requirements_addressed": [],
        }
        d = worktree / ".guardkit" / "autobuild" / "TASK-CTL-002"
        d.mkdir(parents=True, exist_ok=True)
        (d / "task_work_results.json").write_text(json.dumps(results))

    def _run(self, worktree: Path):
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        orch = AutoBuildOrchestrator(
            repo_root=worktree, max_turns=5, enable_pre_loop=False
        )
        validator = CoachValidator(str(worktree), task_id="TASK-CTL-002")
        fake_worktree = Mock()
        fake_worktree.path = worktree
        return orch._direct_mode_evidence_gate(
            validator,
            "TASK-CTL-002",
            2,
            fake_worktree,
            0.0,
            acceptance_criteria=self._AC,
            task_type="feature",
        )

    def test_blocking_verdict_carries_the_real_measurement(self, tmp_path):
        """The r3 shape, minus the CURE-1 recovery: 1 of 2 verified."""
        worktree = self._worktree(tmp_path)
        self._write_results(
            worktree,
            [
                {"criterion_id": "AC-001", "status": "complete"},
                {
                    "criterion_id": "AC-002",
                    # No criterion_text, so no fallback can rescue this one —
                    # it is genuinely unmatched, and the gate must block.
                    "status": "complete",
                },
            ],
        )

        result = self._run(worktree)

        assert result is not None
        report = result.report
        assert report["decision"] == "feedback"
        # CURE 2: what the gate measured now reaches the report.
        assert report["validation_results"]["requirements"] == {
            "criteria_total": 2,
            "criteria_met": 1,
            "all_criteria_met": False,
            "missing": [self._AC[1]],
        }
        assert (
            len(report["acceptance_criteria_verification"]["criteria_results"])
            == 2
        )
        # CURE 2: the blocker is named for what it is.
        assert report["issues"][0]["category"] == "direct_mode_gate"
        # CURE 2: the message says what the check actually did.
        assert "no matching completion promise" in report["rationale"]
        assert "no disk evidence" not in report["rationale"]

    def test_gate_verdict_is_no_longer_counted_as_zero_progress(self, tmp_path):
        worktree = self._worktree(tmp_path)
        self._write_results(
            worktree,
            [
                {"criterion_id": "AC-001", "status": "complete"},
                {"criterion_id": "AC-002", "status": "complete"},
            ],
        )

        result = self._run(worktree)
        orch = AutoBuildOrchestrator(repo_root=worktree, max_turns=5)
        turn_record = Mock()
        turn_record.coach_result = result

        assert orch._count_criteria_passed(turn_record) == 1

    def test_cure1_recovery_lets_the_gate_pass(self, tmp_path):
        """With the bare-checkbox promise text, the gate no longer blocks.

        This is the r3 failure end to end: the same promises, but with the
        Player's real half-stripped ``criterion_text``. Before CURE 1 the
        gate blocked; now it returns None and the LLM Coach gets to judge.
        """
        worktree = self._worktree(tmp_path)
        self._write_results(
            worktree,
            [
                {"criterion_id": "AC-001", "status": "complete"},
                {
                    "criterion_id": "AC-005",
                    "criterion_text": "[ ] " + self._AC[1][6:],
                    "status": "complete",
                    "evidence": "real implementation present",
                },
            ],
        )

        assert self._run(worktree) is None


class TestTerminalStallMessageNamesTheBlocker:
    """CURE 3: the terminal says what it measured and who blocked.

    Pinned prior (2), the guardkit ADR
    ``Player_invocation_stall_misnamed_at_final_summary_layer``, one layer
    deeper: here the misnaming is not ``player_result.error`` (genuinely
    ``None`` — every r3 Player succeeded) but the terminal describing the
    Player when the Player was never the blocker.
    """

    def _turn_record(self, *, synthetic: bool):
        report = {"decision": "feedback"}
        if synthetic:
            report["coach_primary_synthetic_feedback"] = True
        turn_record = Mock()
        turn_record.decision = "feedback"
        turn_record.feedback = "identical blocking feedback"
        turn_record.coach_result = Mock()
        turn_record.coach_result.report = report
        return turn_record

    def _emit_terminal(self, caplog, *, synthetic: bool) -> str:
        """Drive the terminal log line via the real loop-phase code path."""
        orch = AutoBuildOrchestrator(repo_root=Path.cwd(), max_turns=10)
        turn_record = self._turn_record(synthetic=synthetic)
        with caplog.at_level(logging.ERROR):
            for _ in range(3):
                if orch._is_feedback_stalled(
                    turn_record.feedback, 0, turn_record=turn_record
                ):
                    logging.getLogger(
                        "guardkit.orchestrator.autobuild"
                    ).error(
                        orch._feedback_stall_terminal_message(
                            "TASK-CTL-003", turn_record, 0
                        )
                    )
        return caplog.text

    def test_synthetic_blocker_is_named(self, caplog):
        text = self._emit_terminal(caplog, synthetic=True)
        assert "criteria-passed count did not move" in text
        assert "the LLM Coach was not invoked" in text

    def test_real_coach_stall_does_not_claim_a_synthetic_blocker(self, caplog):
        text = self._emit_terminal(caplog, synthetic=False)
        assert "criteria-passed count did not move" in text
        assert "the LLM Coach was not invoked" not in text
