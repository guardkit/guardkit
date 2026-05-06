"""Integration regression test for the b9a45694 _record_honesty crash
(TASK-FIX-7E3F AC-9).

This is **the gate that would have caught the b9a45694 regression**.

The full producer→consumer integration path:

  1. Drive ``CoachValidator.validate()`` to a feedback decision (quality
     gates failed).
  2. Convert via ``to_dict()`` and wrap in an ``AgentInvocationResult`` with
     ``success=True``.
  3. Wrap in a ``TurnRecord`` and call
     ``AutoBuildOrchestrator._record_honesty(turn_record)``.
  4. Assert no exception.
  5. Assert ``_honesty_history`` was updated with a real score (post-Layer-C
     producer threading).

Step (4) is the consumer-side correctness gate; step (5) is the
observability gate that proves Layer C did not silently undo
TASK-AB-FIX-INVAB1's gain.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, TurnRecord
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.quality_gates import CoachValidator


@pytest.fixture
def tmp_worktree(tmp_path: Path) -> Path:
    worktree = tmp_path / "worktrees" / "TASK-FIX-7E3F"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def task_work_results_dir(tmp_worktree: Path) -> Path:
    results_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-FIX-7E3F"
    results_dir.mkdir(parents=True)
    return results_dir


def _failing_gates_results() -> Dict[str, Any]:
    """Quality-gate-failure shape that drives `_feedback_from_gates`."""
    return {
        "quality_gates": {
            "tests_passing": False,
            "tests_passed": 0,
            "tests_failed": 5,
            "coverage": 50,
            "coverage_met": False,
            "all_passed": False,
        },
        "code_review": {"score": 50, "solid": 50, "dry": 50, "yagni": 50},
        "plan_audit": {"status": "skipped", "violations": 0},
        "files_created": [],
        "files_modified": [],
        "tests_written": [],
        "tests_run": True,
        "test_output_summary": "5 failed in 0.1s",
        "completion_promises": [],
        "requirements_addressed": [],
        "requirements_met": [],
    }


def _write_results(results_dir: Path, results: Dict[str, Any]) -> Path:
    path = results_dir / "task_work_results.json"
    path.write_text(json.dumps(results, indent=2))
    return path


def _wrap_in_turn_record(coach_report: Dict[str, Any]) -> TurnRecord:
    """Build the TurnRecord shape autobuild._record_honesty consumes."""
    coach_result = AgentInvocationResult(
        task_id="TASK-FIX-7E3F",
        turn=1,
        agent_type="coach",
        success=True,
        report=coach_report,
        duration_seconds=0.5,
    )
    player_result = AgentInvocationResult(
        task_id="TASK-FIX-7E3F",
        turn=1,
        agent_type="player",
        success=True,
        report={},
        duration_seconds=0.1,
    )
    return TurnRecord(
        turn=1,
        player_result=player_result,
        coach_result=coach_result,
        decision="feedback",
        feedback=None,
        timestamp="2026-05-06T18:00:00Z",
    )


def _make_orchestrator() -> AutoBuildOrchestrator:
    """Minimal AutoBuildOrchestrator that has just enough state for
    ``_record_honesty``. Bypassing __init__ keeps the test free of
    git-repo / worktree-manager scaffolding."""
    orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    orch._honesty_history = []
    return orch


def test_validate_to_dict_record_honesty_does_not_crash(
    tmp_worktree: Path, task_work_results_dir: Path
) -> None:
    """End-to-end: CoachValidator.validate() → to_dict() → _record_honesty.

    This integration test drives the *deterministic-Coach primary path*
    introduced by Option D (TASK-REV-0414) and broken by b9a45694.
    Pre-fix, this test would crash at the consumer with::

        AttributeError: 'NoneType' object has no attribute 'get'

    Post-fix:
      - The producer (Layer C) writes a real ``honesty_verification`` dict.
      - The consumer (Layer B) survives even when the dict is absent.
    """
    # 1. Seed task_work_results.json with a quality-gate failure shape so
    #    validate(...) flows through `_feedback_from_gates` (the AC-4 / 1054
    #    caller post-_verify_honesty).
    _write_results(task_work_results_dir, _failing_gates_results())

    # 2. Drive validate(). Patch subprocess.run so the independent-test
    #    pytest invocation doesn't escape into the host environment.
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="0 passed", stderr=""
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate(
            "TASK-FIX-7E3F", 1, {"acceptance_criteria": ["AC-001"]}
        )

    # Sanity: validation routed to feedback, NOT operator-handoff or
    # invalid-task-type (which would short-circuit before _verify_honesty).
    assert result.decision == "feedback", (
        f"Expected feedback decision, got {result.decision}. "
        f"Issues: {result.issues}"
    )

    # Producer-side observability check (Layer C):
    # honesty_verification must be a real HonestyVerification dataclass,
    # NOT None. If this fails, Layer C is incomplete on this code path.
    assert result.honesty_verification is not None, (
        "Layer C regression: _feedback_from_gates did not thread "
        "honesty_verification through to CoachValidationResult."
    )

    # 3. Convert via to_dict() — same path autobuild orchestration uses.
    coach_report = result.to_dict()
    assert coach_report["honesty_verification"] is not None, (
        "to_dict() lost honesty_verification — producer regression."
    )

    # 4. Wrap in TurnRecord and call _record_honesty. Must NOT crash.
    turn_record = _wrap_in_turn_record(coach_report)
    orch = _make_orchestrator()
    orch._record_honesty(turn_record)  # pre-fix: AttributeError

    # 5. Observability gate: history must have grown by exactly one entry
    #    with a real score (1.0 for an honest no-discrepancy run, lower if
    #    the verifier surfaced any).
    assert len(orch._honesty_history) == 1, (
        f"Layer C regression: _honesty_history did not grow on the "
        f"deterministic-Coach primary path. History: {orch._honesty_history}"
    )
    score = orch._honesty_history[0]
    assert 0.0 <= score <= 1.0, f"Honesty score out of range: {score}"


def test_record_honesty_survives_pre_verify_honesty_short_circuit(
    tmp_worktree: Path, task_work_results_dir: Path
) -> None:
    """Companion to AC-9: pre-_verify_honesty short-circuit (missing
    task_work_results.json) must produce ``honesty_verification: None``,
    and the consumer guard must early-return without crashing.

    Drives the line-828 short-circuit (missing results path).
    """
    # Do NOT write results — drives the "missing_results" feedback at
    # coach_validator.py:828, which is BEFORE _verify_honesty runs.
    validator = CoachValidator(str(tmp_worktree))
    result = validator.validate(
        "TASK-FIX-7E3F", 1, {"acceptance_criteria": ["AC-001"]}
    )

    assert result.decision == "feedback"
    # AC-6 asserts: this short-circuit legitimately produces None.
    assert result.honesty_verification is None
    coach_report = result.to_dict()
    assert coach_report["honesty_verification"] is None

    # Consumer guard must early-return.
    turn_record = _wrap_in_turn_record(coach_report)
    orch = _make_orchestrator()
    orch._record_honesty(turn_record)
    assert orch._honesty_history == []
