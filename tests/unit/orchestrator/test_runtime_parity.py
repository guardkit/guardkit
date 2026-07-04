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


# ============================================================================
# 4. Evidence surfacing + conditional framing + stale-test attribution
#    (TASK-AB-STALEATTRIB01)
# ============================================================================


_FAILED_LINE = (
    "FAILED tests/unit/test_boundary.py::test_transient_state - AssertionError"
)
_PYTEST_STDERR_TAIL = (
    "=== short test summary info ===\n"
    f"{_FAILED_LINE}\n"
    "1 failed, 33 passed in 0.18s"
)


def test_override_issue_carries_test_output_with_failing_node_ids(tmp_path):
    """The override issue's test_output carries the stderr tail AND the
    parsed FAILED node IDs; _extract_feedback delivers it to the Player."""
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    rp = RuntimeParityResult(
        ran=True, passed=False, command="pytest tests/unit -q", exit_code=1,
        stderr_tail=_PYTEST_STDERR_TAIL,
    )
    out = _guard(decision, rp, tmp_path)

    issue = out["issues"][0]
    # The parity issue stays FIRST (issues[:3] truncation cannot drop it).
    assert issue["category"] == "runtime_parity"
    assert issue["severity"] == "must_fix"
    assert "FAILED tests/unit/test_boundary.py::test_transient_state" in issue["test_output"]
    assert "1 failed, 33 passed" in issue["test_output"]

    # _extract_feedback (autobuild.py) carries test_output verbatim — the
    # Player finally sees the failing test's name.
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    feedback = orch._extract_feedback(out)
    assert "tests/unit/test_boundary.py::test_transient_state" in feedback

    # The re-persist to disk survives the payload change
    # (deterministic-verdict-override-must-persist-to-disk).
    persisted = json.loads((tmp_path / "coach_turn_1.json").read_text())
    assert persisted["decision"] == "feedback"
    assert persisted["issues"][0]["test_output"] == issue["test_output"]


def test_test_runner_command_gets_smoke_suite_rationale(tmp_path):
    """pytest-shaped smoke command -> 'test in the feature smoke suite' framing."""
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    rp = RuntimeParityResult(
        ran=True, passed=False, command="pytest tests/unit -q", exit_code=1,
        stderr_tail=_PYTEST_STDERR_TAIL,
    )
    out = _guard(decision, rp, tmp_path)
    assert out["decision"] == "feedback"
    assert (
        "a test in the feature smoke suite FAILED under this task's changes"
        in out["rationale"]
    )
    assert "runs standalone" not in out["rationale"]
    assert "pytest tests/unit -q" in out["rationale"]


def test_non_test_command_keeps_standalone_rationale(tmp_path):
    """Non-test-runner smoke command keeps the runs-standalone import framing."""
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    rp = RuntimeParityResult(
        ran=True, passed=False, command="python3 mod.py", exit_code=1,
        stderr_tail="ModuleNotFoundError: No module named 'installer'",
    )
    out = _guard(decision, rp, tmp_path)
    assert out["decision"] == "feedback"
    assert "fix the deliverable so it runs standalone" in out["rationale"]
    assert "smoke suite" not in out["rationale"]


def _write_authored_record(worktree_root: Path, task_id: str, files) -> None:
    task_dir = worktree_root / ".guardkit" / "autobuild" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "task_work_results.json").write_text(
        json.dumps({"files_authored": list(files)})
    )


def _guard_with_worktree(decision: dict, runtime_parity, tmp_path) -> dict:
    """Like _guard, but with a worktree_path set (authorship-join surface)."""
    inv = AgentInvoker.__new__(AgentInvoker)
    inv.worktree_path = tmp_path
    bundle = CoachEvidenceBundle(honesty=None, runtime_parity=runtime_parity)
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


def test_authorship_join_names_earlier_task_and_grants_permission(tmp_path):
    """Failing file authored by another task -> the note names it + the
    narrowly-scoped stale-assertion permission, while the red stays red."""
    _write_authored_record(
        tmp_path, "TASK-TSJ-000", ["tests/unit/test_boundary.py"]
    )
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    rp = RuntimeParityResult(
        ran=True, passed=False, command="pytest tests/unit -q", exit_code=1,
        stderr_tail=_PYTEST_STDERR_TAIL,
    )
    out = _guard_with_worktree(decision, rp, tmp_path)

    assert out["decision"] == "feedback"
    assert out["issues"][0]["severity"] == "must_fix"
    assert "TASK-TSJ-000" in out["rationale"]
    assert (
        "you may amend or delete that specific stale assertion in "
        "tests/unit/test_boundary.py only if it pins transient "
        "point-in-time scaffold state" in out["rationale"].lower()
    )
    assert "change nothing else in that file" in out["rationale"].lower()
    # The permission never licenses deleting a genuine regression guard.
    assert (
        "fix your implementation instead — do not delete it"
        in out["rationale"].lower()
    )


# ============================================================================
# 5. output_tail — pytest FAILED summaries live on STDOUT (2026-07-04 review)
# ============================================================================


def test_output_tail_combines_stdout_and_stderr_stdout_first(tmp_path):
    """The ran-and-failed branch carries a combined stdout+stderr tail
    (stdout first); stderr_tail keeps its stderr-only semantics."""
    v = _validator(
        tmp_path, smoke_command="echo 'OUT-LINE'; echo 'ERR-LINE' >&2; exit 1"
    )
    result = v._gather_runtime_parity()
    assert result.ran is True
    assert result.passed is False
    assert "OUT-LINE" in result.output_tail
    assert "ERR-LINE" in result.output_tail
    assert result.output_tail.index("OUT-LINE") < result.output_tail.index(
        "ERR-LINE"
    )
    # stderr_tail semantics untouched (additive-only contract).
    assert "OUT-LINE" not in result.stderr_tail
    assert "ERR-LINE" in result.stderr_tail


def test_output_tail_populated_on_pass_and_serialises(tmp_path):
    """Trivially populated on a passing run too, and survives asdict()."""
    v = _validator(tmp_path, smoke_command="echo 'ok'; exit 0")
    result = v._gather_runtime_parity()
    assert result.passed is True
    assert "ok" in result.output_tail
    bundle = CoachEvidenceBundle(honesty=None, runtime_parity=result)
    assert bundle.to_dict()["runtime_parity"]["output_tail"] == result.output_tail


def test_timeout_branch_carries_output_tail_verdict_unchanged(tmp_path):
    """The timeout branch stays ran=True/timed_out=True (operator-pinned,
    TASK-AB-COACHRUNPARITY01) — output_tail is additive evidence only."""
    import subprocess

    v = _validator(tmp_path, smoke_command="sleep 99")
    with patch(
        "guardkit.orchestrator.quality_gates.coach_validator.subprocess.run",
        side_effect=subprocess.TimeoutExpired(
            cmd="sleep 99", timeout=5, output=b"stdout-part", stderr=b"stderr-part"
        ),
    ):
        result = v._gather_runtime_parity()
    assert result.ran is True
    assert result.passed is False
    assert result.timed_out is True
    assert "stderr-part" in result.stderr_tail
    assert "stdout-part" in result.output_tail
    assert "stderr-part" in result.output_tail


def test_guard_parses_failing_lines_from_stdout_output_tail(tmp_path):
    """A pytest-shaped parity failure whose FAILED summary is on STDOUT
    (stderr empty) now yields test_output naming the failing node IDs —
    the per-task mirror of _build_smoke_feedback's stdout+stderr join."""
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    rp = RuntimeParityResult(
        ran=True, passed=False, command="pytest tests/unit -q", exit_code=1,
        stderr_tail="",
        output_tail=_PYTEST_STDERR_TAIL,
    )
    out = _guard(decision, rp, tmp_path)
    assert out["decision"] == "feedback"
    issue = out["issues"][0]
    assert (
        "FAILED tests/unit/test_boundary.py::test_transient_state"
        in issue["test_output"]
    )
    assert "output (tail):" in issue["test_output"]
    assert issue["details"]["output_tail"] == _PYTEST_STDERR_TAIL


def test_stale_attribution_fires_from_stdout_only_failure(tmp_path):
    """The authorship join / stale-assertion note works off the stdout-borne
    FAILED lines too (the motivating pytest-shaped smoke-command case)."""
    _write_authored_record(
        tmp_path, "TASK-TSJ-000", ["tests/unit/test_boundary.py"]
    )
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    rp = RuntimeParityResult(
        ran=True, passed=False, command="pytest tests/unit -q", exit_code=1,
        stderr_tail="",
        output_tail=_PYTEST_STDERR_TAIL,
    )
    out = _guard_with_worktree(decision, rp, tmp_path)
    assert out["decision"] == "feedback"
    assert "STALE-TEST ATTRIBUTION" in out["rationale"]
    assert "TASK-TSJ-000" in out["rationale"]


def test_guard_falls_back_to_stderr_tail_for_older_records(tmp_path):
    """Older RuntimeParityResult records (output_tail=None) keep the
    stderr-based parse and the original label."""
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    rp = RuntimeParityResult(
        ran=True, passed=False, command="pytest tests/unit -q", exit_code=1,
        stderr_tail=_PYTEST_STDERR_TAIL,
    )
    assert rp.output_tail is None
    out = _guard(decision, rp, tmp_path)
    issue = out["issues"][0]
    assert (
        "FAILED tests/unit/test_boundary.py::test_transient_state"
        in issue["test_output"]
    )
    assert "stderr (tail):" in issue["test_output"]
    assert issue["details"]["output_tail"] is None


def test_gather_then_guard_names_stdout_failed_lines_end_to_end(tmp_path):
    """End-to-end on the real seam: a smoke command printing its FAILED
    summary to stdout produces Player-facing test_output with the node ID."""
    v = _validator(
        tmp_path,
        smoke_command=(
            "echo 'FAILED tests/unit/test_boundary.py::test_transient_state"
            " - AssertionError'; exit 1"
        ),
    )
    result = v._gather_runtime_parity()
    assert result.ran is True
    assert result.passed is False

    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    out = _guard(decision, result, tmp_path)
    assert out["decision"] == "feedback"
    assert (
        "FAILED tests/unit/test_boundary.py::test_transient_state"
        in out["issues"][0]["test_output"]
    )


def test_authorship_join_fails_open(tmp_path):
    """Unmatched / ambiguous / current-task-authored -> unchanged framing."""
    rp = RuntimeParityResult(
        ran=True, passed=False, command="pytest tests/unit -q", exit_code=1,
        stderr_tail=_PYTEST_STDERR_TAIL,
    )

    # (a) No authored-files records on disk.
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    out = _guard_with_worktree(decision, rp, tmp_path)
    assert out["decision"] == "feedback"
    assert "STALE-TEST ATTRIBUTION" not in out["rationale"]

    # (b) Ambiguous: two other tasks authored the failing file.
    _write_authored_record(tmp_path, "TASK-TSJ-000", ["tests/unit/test_boundary.py"])
    _write_authored_record(tmp_path, "TASK-TSJ-002", ["tests/unit/test_boundary.py"])
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    out = _guard_with_worktree(decision, rp, tmp_path)
    assert "STALE-TEST ATTRIBUTION" not in out["rationale"]

    # (c) Authored by the current task itself: its own framing stands.
    import shutil

    shutil.rmtree(tmp_path / ".guardkit")
    _write_authored_record(tmp_path, "TASK-TSJ-001", ["tests/unit/test_boundary.py"])
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    out = _guard_with_worktree(decision, rp, tmp_path)
    assert "STALE-TEST ATTRIBUTION" not in out["rationale"]
    # The red signal itself is untouched in every fail-open case.
    assert out["decision"] == "feedback"
