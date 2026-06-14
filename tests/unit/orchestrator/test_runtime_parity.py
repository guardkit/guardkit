"""Unit tests for the per-task Coach runtime-parity check (TASK-AB-COACHRUNPARITY01, arm b).

Covers:
1. ``CoachValidator._gather_runtime_parity`` — runs the deliverable's runtime
   entry point on single-task waves, skips (absent signal) otherwise.
2. ``AgentInvoker._apply_runtime_parity_guard`` — deterministic backstop that
   overrides an ``approve`` to ``feedback`` when the entry point ran and failed,
   and is a no-op for absent / passing signals (absence-of-failure safety).

Coverage Target: >=85%
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
    RuntimeParityResult,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


# ============================================================================
# 1. RuntimeParityResult serialises into the bundle
# ============================================================================


def test_runtime_parity_result_serialises_into_bundle():
    rp = RuntimeParityResult(
        ran=True, passed=False, command="python3 mod.py", exit_code=1,
        expected_exit=0, stderr_tail="ModuleNotFoundError",
    )
    bundle = CoachEvidenceBundle(honesty=None, runtime_parity=rp)
    d = bundle.to_dict()
    assert d["runtime_parity"]["ran"] is True
    assert d["runtime_parity"]["passed"] is False
    assert d["runtime_parity"]["command"] == "python3 mod.py"


def test_bundle_runtime_parity_defaults_none():
    assert CoachEvidenceBundle(honesty=None).runtime_parity is None


# ============================================================================
# 2. CoachValidator._gather_runtime_parity
# ============================================================================


def _validator(tmp_path, smoke_command, wave_size=1, expected_exit=0) -> CoachValidator:
    return CoachValidator(
        str(tmp_path),
        task_id="TASK-TSJ-001",
        smoke_command=smoke_command,
        wave_size=wave_size,
        smoke_expected_exit=expected_exit,
    )


def test_no_smoke_command_returns_none(tmp_path):
    v = _validator(tmp_path, smoke_command=None)
    assert v._gather_runtime_parity() is None


def test_parallel_wave_is_absent_not_a_pass(tmp_path):
    """A multi-task wave skips the check (the deliverable may need peers)."""
    v = _validator(tmp_path, smoke_command="exit 0", wave_size=2)
    result = v._gather_runtime_parity()
    assert result is not None
    assert result.ran is False
    assert result.passed is False
    assert result.skipped_reason == "parallel_wave"


def test_runtime_entry_point_runs_clean(tmp_path):
    v = _validator(tmp_path, smoke_command="exit 0")
    result = v._gather_runtime_parity()
    assert result.ran is True
    assert result.passed is True
    assert result.exit_code == 0


def test_runtime_entry_point_fails(tmp_path):
    v = _validator(tmp_path, smoke_command="echo 'ModuleNotFoundError' >&2; exit 1")
    result = v._gather_runtime_parity()
    assert result.ran is True
    assert result.passed is False
    assert result.exit_code == 1
    assert "ModuleNotFoundError" in result.stderr_tail


def test_respects_non_default_expected_exit(tmp_path):
    """A non-zero feature expected_exit is honoured (Phase 5 review finding 2).

    A deliverable that exits with the configured expected_exit passes; one
    that exits 0 (when expected is 2) fails — the per-task check agrees with
    the post-wave gate instead of hardcoding 0.
    """
    v_pass = _validator(tmp_path, smoke_command="exit 2", expected_exit=2)
    result_pass = v_pass._gather_runtime_parity()
    assert result_pass.ran is True
    assert result_pass.passed is True
    assert result_pass.expected_exit == 2

    v_fail = _validator(tmp_path, smoke_command="exit 0", expected_exit=2)
    result_fail = v_fail._gather_runtime_parity()
    assert result_fail.ran is True
    assert result_fail.passed is False


def test_timeout_is_ran_and_failed(tmp_path):
    """A TimeoutExpired is a ran-and-failed runtime signal (timed_out=True)."""
    import subprocess

    v = _validator(tmp_path, smoke_command="sleep 99")
    with patch(
        "guardkit.orchestrator.quality_gates.coach_validator.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="sleep 99", timeout=5, stderr=b"partial"),
    ):
        result = v._gather_runtime_parity()
    assert result.ran is True
    assert result.passed is False
    assert result.timed_out is True
    assert "partial" in result.stderr_tail


def test_runner_error_is_absent_not_fail(tmp_path):
    """A runner-side exception is ABSENT (ran=False), never a ran-and-failed."""
    v = _validator(tmp_path, smoke_command="exit 1")
    with patch(
        "guardkit.orchestrator.quality_gates.coach_validator.subprocess.run",
        side_effect=OSError("boom"),
    ):
        result = v._gather_runtime_parity()
    assert result.ran is False
    assert result.passed is False
    assert result.skipped_reason is not None
    assert result.skipped_reason.startswith("runner_error:")


# ============================================================================
# 3. AgentInvoker._apply_runtime_parity_guard
# ============================================================================


def _guard(decision: dict, runtime_parity, tmp_path) -> dict:
    """Invoke the guard against a fresh, un-__init__'d AgentInvoker."""
    inv = AgentInvoker.__new__(AgentInvoker)
    bundle = (
        CoachEvidenceBundle(honesty=None, runtime_parity=runtime_parity)
        if runtime_parity is not None
        else CoachEvidenceBundle(honesty=None)
    )
    coach_path = tmp_path / "coach_turn_1.json"
    coach_path.write_text(json.dumps(decision))
    inv._apply_runtime_parity_guard(
        decision=decision,
        evidence_bundle=bundle,
        task_id="TASK-TSJ-001",
        turn=1,
        coach_output_path=coach_path,
    )
    return decision


def test_guard_overrides_approve_when_ran_and_failed(tmp_path):
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    rp = RuntimeParityResult(
        ran=True, passed=False, command="python3 mod.py", exit_code=1,
        stderr_tail="ModuleNotFoundError: No module named 'installer'",
    )
    out = _guard(decision, rp, tmp_path)
    assert out["decision"] == "feedback"
    assert out["issues"][0]["category"] == "runtime_parity"
    assert out["issues"][0]["severity"] == "must_fix"
    assert "python3 mod.py" in out["rationale"]
    # Re-persisted to disk.
    persisted = json.loads((tmp_path / "coach_turn_1.json").read_text())
    assert persisted["decision"] == "feedback"


def test_guard_noop_when_ran_and_passed(tmp_path):
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    rp = RuntimeParityResult(ran=True, passed=True, command="python3 mod.py", exit_code=0)
    out = _guard(decision, rp, tmp_path)
    assert out["decision"] == "approve"


def test_guard_noop_when_absent(tmp_path):
    """ran=False (parallel wave / runner error) is absent — never blocks."""
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    rp = RuntimeParityResult(
        ran=False, passed=False, command="python3 mod.py",
        skipped_reason="parallel_wave",
    )
    out = _guard(decision, rp, tmp_path)
    assert out["decision"] == "approve"


def test_guard_noop_when_runtime_parity_none(tmp_path):
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    out = _guard(decision, None, tmp_path)
    assert out["decision"] == "approve"


def test_guard_leaves_feedback_verdict_untouched(tmp_path):
    """A pre-existing feedback verdict is not modified (only approve is overridden)."""
    decision = {"decision": "feedback", "issues": [{"x": 1}], "rationale": "already feedback"}
    rp = RuntimeParityResult(ran=True, passed=False, command="python3 mod.py", exit_code=1)
    out = _guard(decision, rp, tmp_path)
    assert out["decision"] == "feedback"
    assert out["rationale"] == "already feedback"
    assert out["issues"] == [{"x": 1}]
