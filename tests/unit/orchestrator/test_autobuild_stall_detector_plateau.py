"""
Unit tests for the plateau-tolerant branch of ``_is_feedback_stalled``
(TASK-GK-COACH-001).

Closes the 0 → N then plateau blind spot surfaced by FEAT-PEBR run-2
(TASK-REV-PEBR-002, AC-5). The standard 3-turn check and the strict
extended-uniformity (TASK-REV-E719 Fix 3) check are both preserved
unchanged; the new branch fires only when:

  - len(history) >= 5
  - all 5 signatures match
  - the trailing 4 counts (ext_counts[1:]) are uniform AND non-zero
  - the trailing 4 counts differ from ext_counts[0]

Coverage Target: >=85%
"""

from pathlib import Path

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator


def _new_orchestrator(max_turns: int = 10) -> AutoBuildOrchestrator:
    return AutoBuildOrchestrator(repo_root=Path.cwd(), max_turns=max_turns)


class TestPartialProgressPlateauStall:
    """AC-2 / AC-3 — new plateau-tolerant branch."""

    def test_plateau_pattern_0_then_7_stalls_at_turn_5(self):
        """AC-2: counts [0, 7, 7, 7, 7] with constant signature → stall at turn 5.

        Reproduces FEAT-PEBR run-2 fingerprint. MUST FAIL on main and PASS
        with the plateau-tolerant branch.
        """
        orchestrator = _new_orchestrator()
        feedback = "plan_audit must_fix: missing files"

        assert orchestrator._is_feedback_stalled(feedback, 0) is False  # turn 1
        assert orchestrator._is_feedback_stalled(feedback, 7) is False  # turn 2
        assert orchestrator._is_feedback_stalled(feedback, 7) is False  # turn 3
        assert orchestrator._is_feedback_stalled(feedback, 7) is False  # turn 4
        assert orchestrator._is_feedback_stalled(feedback, 7) is True   # turn 5

    def test_legitimate_progress_does_not_stall(self):
        """AC-3: counts [0, 3, 5, 7, 7] — Player still climbing → MUST NOT stall.

        Trailing pair (7, 7) is uniform but the inner counts (3, 5)
        prove progress is still happening; the standard 3-window check
        never fires (counts not equal), and the new plateau branch
        requires the trailing 4 counts to be uniform.
        """
        orchestrator = _new_orchestrator()
        feedback = "Same gate failing"

        assert orchestrator._is_feedback_stalled(feedback, 0) is False  # turn 1
        assert orchestrator._is_feedback_stalled(feedback, 3) is False  # turn 2
        assert orchestrator._is_feedback_stalled(feedback, 5) is False  # turn 3
        assert orchestrator._is_feedback_stalled(feedback, 7) is False  # turn 4
        assert orchestrator._is_feedback_stalled(feedback, 7) is False  # turn 5


class TestExistingStallPathsUnchanged:
    """AC-4 / AC-5 / AC-6 — guard the pre-existing branches against regression."""

    def test_zero_zero_zero_stalls_at_turn_3(self):
        """AC-4: counts [0, 0, 0] with constant signature → stall at turn 3.

        Standard zero-progress threshold check (line 3992 of autobuild.py).
        """
        orchestrator = _new_orchestrator()
        feedback = "Nothing implemented yet"

        assert orchestrator._is_feedback_stalled(feedback, 0) is False  # turn 1
        assert orchestrator._is_feedback_stalled(feedback, 0) is False  # turn 2
        assert orchestrator._is_feedback_stalled(feedback, 0) is True   # turn 3

    def test_uniform_nonzero_stalls_at_extended_threshold(self):
        """AC-5: counts [7, 7, 7, 7, 7] with constant signature → stall at turn 5.

        Strict extended-uniformity branch (TASK-REV-E719 Fix 3). My new
        plateau branch must not pre-empt or skip this — the strict branch
        still owns the all-equal case.
        """
        orchestrator = _new_orchestrator()
        feedback = "Same partial-progress feedback"

        assert orchestrator._is_feedback_stalled(feedback, 7) is False  # turn 1
        assert orchestrator._is_feedback_stalled(feedback, 7) is False  # turn 2
        assert orchestrator._is_feedback_stalled(feedback, 7) is False  # turn 3
        assert orchestrator._is_feedback_stalled(feedback, 7) is False  # turn 4
        assert orchestrator._is_feedback_stalled(feedback, 7) is True   # turn 5

    def test_signature_change_breaks_stall(self):
        """AC-6: counts [7, 7, 7, 7, 7] but signatures vary → MUST NOT stall.

        Signature uniformity is the load-bearing precondition for both
        the strict and plateau branches; this test ensures the new branch
        respects it (it inherits the ``len(ext_sigs) == 1`` outer guard).
        """
        orchestrator = _new_orchestrator()

        feedbacks = [
            "Feedback A",  # turn 1
            "Feedback A",  # turn 2
            "Feedback B",  # turn 3 — signature change
            "Feedback A",  # turn 4
            "Feedback A",  # turn 5
        ]
        results = [
            orchestrator._is_feedback_stalled(fb, 7) for fb in feedbacks
        ]
        assert results == [False, False, False, False, False]


