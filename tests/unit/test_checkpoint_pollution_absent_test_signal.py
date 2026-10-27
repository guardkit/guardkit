"""
Regression tests for TASK-FIX-CKPTTESTRED01.

Checkpoint pollution detector false-reds on absent Player/Coach test signals.

FEAT-9DDE run 5 ended ``unrecoverable_stall`` at turn 3 with "3 consecutive
test failures in turns [1, 2, 3]" even though the Coach quality gate reported
``tests=True`` on every turn and the unit test file existed and passed on disk.

Root cause (the checkpoint-layer instance of the absence-of-failure rule):
the default LLM Coach's ``coach_result.report`` carries only
``{decision, issues, criteria_verification, rationale}`` — it does NOT carry
``validation_results.quality_gates``. ``_extract_tests_passed`` collapsed that
absent signal to ``False``, so every LLM-Coach feedback turn recorded
``tests: fail``; after 3 such turns the pollution detector fired and, finding
no passing checkpoint, declared an unrecoverable stall.

The fix makes the test signal tri-state (True / False / None=UNKNOWN) and
excludes UNKNOWN from the consecutive-failure tally. A genuine
``tests_passed is False`` (oracle ran and failed) still stalls as designed.

27 October 2026 cull: the pollution detector and its rollback are deleted,
so the stall tests went with them. The tri-state extraction and the
checkpoint's "unknown" rendering stay and are tested here.

See:
- .claude/rules/absence-of-failure-is-not-success.md (this is its
  checkpoint-layer, false-red instance)
- docs/retro/run5-evidence/ (coach_turn_*.json, checkpoints.json,
  task_work_results.json with tests_run=null)

Coverage Target: >=85%
"""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.worktree_checkpoints import (
    WorktreeCheckpointManager,
    format_test_status,
)
from tests.task_scope_fixtures import admitted_task, init_checkout


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def orchestrator():
    """AutoBuildOrchestrator for exercising _extract_tests_passed."""
    return AutoBuildOrchestrator(repo_root=Path.cwd(), max_turns=5)


@pytest.fixture
def checkpoint_manager(tmp_path):
    """Checkpoint manager on a real checkout with its admitted task scope."""
    worktree_path = init_checkout(tmp_path / "worktree")
    with admitted_task(worktree_path, "TASK-TSJ-001", register=True) as (_, scope):
        (worktree_path / ".guardkit" / "autobuild" / "TASK-TSJ-001").mkdir(
            parents=True
        )
        yield WorktreeCheckpointManager(
            worktree_path=worktree_path,
            task_id="TASK-TSJ-001",
            task_work_scope=scope,
        )


def _llm_coach_feedback_turn_record() -> Mock:
    """A turn record mirroring FEAT-9DDE run-5's LLM-Coach feedback turns.

    The report shape matches docs/retro/run5-evidence/coach_turn_2.json exactly:
    decision/issues/criteria_verification/rationale, with NO validation_results.
    """
    turn_record = Mock()
    turn_record.coach_result = Mock()
    turn_record.coach_result.success = True
    turn_record.coach_result.report = {
        "task_id": "TASK-TSJ-001",
        "turn": 2,
        "decision": "feedback",
        "issues": [
            {"category": None, "severity": "critical",
             "description": "AC-005 missing-field handling not implemented."},
        ],
        "criteria_verification": [
            {"criterion_id": "AC-001", "result": "verified", "notes": "ok"},
            {"criterion_id": "AC-005", "result": "rejected", "notes": "missing"},
        ],
        "rationale": "Covers basic scanning but not all robustness requirements.",
    }
    return turn_record


# ============================================================================
# AC: absent test signal extracted as UNKNOWN (None), never failure
# ============================================================================


class TestExtractTestsPassedTriState:
    def test_llm_coach_feedback_turn_is_unknown_not_failure(self, orchestrator):
        """Run-5 reproducer: LLM-Coach report (no validation_results) → None."""
        turn_record = _llm_coach_feedback_turn_record()
        assert orchestrator._extract_tests_passed(turn_record) is None

    def test_signal_absent_independent_test_is_unknown(self, orchestrator):
        """An explicitly-absent independent-test signal → None (UNKNOWN)."""
        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "independent_tests": {"signal_absent": True, "tests_passed": False},
                "quality_gates": {"tests_passed": True},
            },
        }
        assert orchestrator._extract_tests_passed(turn_record) is None

    def test_coach_gate_tests_true_recorded_as_pass(self, orchestrator):
        """AC: a turn whose Coach gate is tests=True is True (never fail)."""
        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {"quality_gates": {"tests_passed": True}},
        }
        assert orchestrator._extract_tests_passed(turn_record) is True

    def test_genuine_failure_recorded_as_false(self, orchestrator):
        """A real ran-and-failed gate result remains False."""
        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {"quality_gates": {"tests_passed": False}},
        }
        assert orchestrator._extract_tests_passed(turn_record) is False


# ============================================================================
# AC: an UNKNOWN checkpoint is recorded as unknown, never as a failure
# ============================================================================


class TestCheckpointRecordsUnknown:
    def test_checkpoint_records_unknown_status_string(self, checkpoint_manager):
        """An UNKNOWN checkpoint renders 'unknown', never 'fail'."""
        cp = checkpoint_manager.create_checkpoint(turn=1, tests_passed=None)
        assert cp.tests_passed is None
        assert "unknown" in cp.message
        assert "fail" not in cp.message


# ============================================================================
# format_test_status helper
# ============================================================================


class TestFormatTestStatus:
    @pytest.mark.parametrize(
        "value,expected",
        [(True, "pass"), (False, "fail"), (None, "unknown")],
    )
    def test_tri_state_rendering(self, value, expected):
        assert format_test_status(value) == expected
