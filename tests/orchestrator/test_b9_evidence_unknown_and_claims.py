"""B9 Lane C — evidence that is unknown stays unknown, and a promise is a claim.

Three seams, each with the negative control that motivated it and a positive
control that the existing valid path is unchanged:

1. **Coverage.** A required coverage with nothing measured is UNKNOWN and
   cannot approve (it used to be coerced to a pass). A project may declare its
   OWN coverage command (``toolchain.coverage``); the Coach runs it itself,
   after its own independent test run, and its EXIT CODE is the verdict.
   Direct mode is the one named relaxation: ``coverage_met: null`` plus
   ``quality_gates_relaxed: true`` from the writer, and the Coach records
   ``coverage_relaxed_by: direct_mode`` without ever inventing a measurement.

2. **Promises are claims.** ``_match_by_promises`` records ``claimed``; only
   ``corroborate_claims`` can raise that to ``verified``, and a machine-class
   pass-bar criterion needs a bound verifier receipt, never a green generic
   suite. The per-turn arithmetic is untouched: a claim still counts as met.

3. A non-Python fixture (a shell coverage command in a ``Makefile`` project)
   drives the declared-coverage path, because nothing here may assume Python.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from guardkit.models.task_types import TaskType, get_profile
from guardkit.orchestrator.quality_gates.coach_validator import (
    CLAIMED,
    VERIFIED,
    CoachValidator,
    IndependentTestResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(
    worktree: Path, toolchain: Dict[str, Any], task_id: str = "TASK-B9C"
) -> None:
    """Declare a toolchain block AND pin it as the task's pre-turn-1 snapshot.

    The Coach reads only the snapshot, never the live worktree config (that
    file sits inside the tree the Player edits) — so a fixture that wants the
    Coach to see a declaration has to pin it the way a real build does.
    """
    from guardkit.orchestrator.toolchain_declaration import (
        snapshot_task_toolchain,
    )

    cfg = worktree / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    lines = ["toolchain:"]
    for key, value in toolchain.items():
        lines.append(f"  {key}: {value!r}" if isinstance(value, str) else f"  {key}: {value}")
    (cfg / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert snapshot_task_toolchain(task_id, worktree, worktree) is not None


def _results(**overrides: Any) -> Dict[str, Any]:
    """A task-work results block whose every gate but coverage passes."""
    results: Dict[str, Any] = {
        "task_id": "TASK-B9C",
        "completed": True,
        "quality_gates": {"all_passed": True, "tests_failed": 0},
        "code_review": {"score": 95},
        "plan_audit": {"status": "passed", "violations": 0},
    }
    results.update(overrides)
    return results


def _validator(worktree: Path, task_id: str = "TASK-B9C") -> CoachValidator:
    return CoachValidator(str(worktree), task_id=task_id)


def _honesty(verified: bool):
    from guardkit.orchestrator.coach_verification import HonestyVerification

    return HonestyVerification(verified=verified)


def _passing_run() -> IndependentTestResult:
    return IndependentTestResult(
        tests_passed=True,
        test_command="declared",
        test_output_summary="3 passed",
        duration_seconds=0.1,
    )


def _absent_run() -> IndependentTestResult:
    return IndependentTestResult(
        tests_passed=True,
        test_command="declared",
        test_output_summary="no verdict",
        duration_seconds=0.1,
        signal_absent=True,
    )


# ---------------------------------------------------------------------------
# 1. Coverage: unknown stays unknown
# ---------------------------------------------------------------------------


class TestCoverageUnknown:
    def test_required_coverage_with_no_measurement_is_unknown_and_cannot_approve(
        self, tmp_path
    ):
        """NEGATIVE CONTROL — the B9 false green itself."""
        v = _validator(tmp_path)
        gates = v.verify_quality_gates(
            _results(), profile=get_profile(TaskType.FEATURE)
        )
        assert gates.coverage_required is True
        assert gates.coverage_met is None, "unmeasured coverage must stay UNKNOWN"
        assert gates.all_gates_passed is False
        assert gates.coverage_relaxed_by is None

    def test_measured_coverage_true_still_passes(self, tmp_path):
        """POSITIVE CONTROL — a real measurement is untouched."""
        v = _validator(tmp_path)
        gates = v.verify_quality_gates(
            _results(quality_gates={"all_passed": True, "coverage_met": True}),
            profile=get_profile(TaskType.FEATURE),
        )
        assert gates.coverage_met is True
        assert gates.all_gates_passed is True

    def test_measured_coverage_false_still_fails(self, tmp_path):
        v = _validator(tmp_path)
        gates = v.verify_quality_gates(
            _results(quality_gates={"all_passed": True, "coverage_met": False}),
            profile=get_profile(TaskType.FEATURE),
        )
        assert gates.coverage_met is False
        assert gates.all_gates_passed is False

    def test_coverage_not_required_is_untouched(self, tmp_path):
        v = _validator(tmp_path)
        gates = v.verify_quality_gates(
            _results(), profile=get_profile(TaskType.DOCUMENTATION)
        )
        assert gates.coverage_met is True

    def test_unknown_coverage_feedback_names_the_two_missing_sources(self, tmp_path):
        v = _validator(tmp_path)
        gates = v.verify_quality_gates(
            _results(), profile=get_profile(TaskType.FEATURE)
        )
        result = v._feedback_from_gates(
            "TASK-B9C", 1, gates, _results(), task_type="feature"
        )
        issue = next(
            i for i in result.issues if i["category"] == "coverage_unknown"
        )
        text = issue["description"]
        assert "UNKNOWN" in text
        assert "feature tasks" in text
        assert "coverage_met" in text  # the Player report
        assert "toolchain.coverage" in text  # the project declaration
        assert issue["details"]["coverage_met"] is None


class TestDirectModeRelaxation:
    def test_direct_mode_relaxes_without_inventing_a_measurement(self, tmp_path):
        """POSITIVE CONTROL for the one named relaxation."""
        v = _validator(tmp_path)
        gates = v.verify_quality_gates(
            _results(
                implementation_mode="direct",
                quality_gates={
                    "all_passed": True,
                    "coverage_met": None,
                    "quality_gates_relaxed": True,
                },
            ),
            profile=get_profile(TaskType.FEATURE),
        )
        assert gates.coverage_relaxed_by == "direct_mode"
        assert gates.all_gates_passed is True

    def test_the_relaxed_flag_alone_does_not_relax(self, tmp_path):
        """NEGATIVE CONTROL — the flag is a consequence of the mode, not proof
        of it. Only ``implementation_mode: direct`` turns the gate off."""
        v = _validator(tmp_path)
        gates = v.verify_quality_gates(
            _results(
                quality_gates={
                    "all_passed": True,
                    "coverage_met": None,
                    "quality_gates_relaxed": True,
                }
            ),
            profile=get_profile(TaskType.FEATURE),
        )
        assert gates.coverage_relaxed_by is None
        assert gates.coverage_met is None
        assert gates.all_gates_passed is False

    def test_direct_mode_writer_emits_null_not_true(self):
        """The writer half: direct mode measures nothing, so it says nothing."""
        import inspect

        from guardkit.orchestrator import agent_invoker

        src = inspect.getsource(agent_invoker.AgentInvoker._write_direct_mode_results)
        assert '"coverage_met": None' in src
        assert '"quality_gates_relaxed": True' in src


# ---------------------------------------------------------------------------
# 2. The project's own declared coverage command (non-Python fixture)
# ---------------------------------------------------------------------------


def _make_shell_project(tmp_path: Path, exit_code: int) -> Path:
    """A Makefile project whose coverage command is a shell script.

    Deliberately not Python: the factory is language-agnostic and the exit code
    is the whole verdict.
    """
    worktree = tmp_path / "shellproj"
    worktree.mkdir()
    (worktree / "Makefile").write_text("all:\n\t@echo build\n", encoding="utf-8")
    script = worktree / "coverage.sh"
    script.write_text(
        "#!/bin/sh\n"
        'echo "lines covered: reported by the project itself"\n'
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    _write_config(worktree, {"test": "make test", "coverage": "./coverage.sh"})
    return worktree


class TestDeclaredCoverageCommand:
    def test_declared_command_exit_zero_decides_coverage_met(self, tmp_path):
        worktree = _make_shell_project(tmp_path, exit_code=0)
        v = _validator(worktree)
        gates = v.verify_quality_gates(
            _results(), profile=get_profile(TaskType.FEATURE)
        )
        assert gates.coverage_met is None
        resolved = v.apply_declared_coverage(gates)
        assert resolved.coverage_met is True
        assert resolved.all_gates_passed is True
        receipt = resolved.coverage_receipt
        assert receipt["command"] == "./coverage.sh"
        assert receipt["exit_code"] == 0
        assert receipt["duration_seconds"] >= 0
        assert "reported by the project itself" in receipt["output_tail"]
        assert receipt["timed_out"] is False

    def test_declared_command_exit_one_does_not_approve(self, tmp_path):
        worktree = _make_shell_project(tmp_path, exit_code=1)
        v = _validator(worktree)
        gates = v.verify_quality_gates(
            _results(), profile=get_profile(TaskType.FEATURE)
        )
        resolved = v.apply_declared_coverage(gates)
        assert resolved.coverage_met is False
        assert resolved.all_gates_passed is False
        assert resolved.coverage_receipt["exit_code"] == 1

    def test_no_declaration_leaves_the_gate_unknown(self, tmp_path):
        worktree = tmp_path / "plain"
        worktree.mkdir()
        v = _validator(worktree)
        gates = v.verify_quality_gates(
            _results(), profile=get_profile(TaskType.FEATURE)
        )
        resolved = v.apply_declared_coverage(gates)
        assert resolved.coverage_met is None
        assert resolved.coverage_receipt is None

    def test_a_measured_value_is_never_overwritten_by_the_command(self, tmp_path):
        worktree = _make_shell_project(tmp_path, exit_code=1)
        v = _validator(worktree)
        gates = v.verify_quality_gates(
            _results(quality_gates={"all_passed": True, "coverage_met": True}),
            profile=get_profile(TaskType.FEATURE),
        )
        resolved = v.apply_declared_coverage(gates)
        assert resolved.coverage_met is True
        assert resolved.coverage_receipt is None

    def test_timeout_is_unknown_not_a_pass(self, tmp_path):
        worktree = tmp_path / "slow"
        worktree.mkdir()
        _write_config(worktree, {"coverage": "sleep 5", "coverage_timeout": 1})
        v = _validator(worktree)
        receipt = v.run_declared_coverage()
        assert receipt["timed_out"] is True
        assert receipt["coverage_met"] is None
        assert "timed out" in receipt["output_tail"]

    def test_a_command_that_cannot_launch_is_unknown_not_a_pass(self, tmp_path):
        """NEGATIVE CONTROL (B9 repair pass) — a declared command that never
        ran measured nothing, so the gate stays UNKNOWN and cannot approve."""
        worktree = tmp_path / "broken"
        worktree.mkdir()
        _write_config(worktree, {"coverage": "./no-such-command-here"})
        v = _validator(worktree)
        receipt = v.run_declared_coverage()
        assert receipt["coverage_met"] is not True
        gates = v.verify_quality_gates(
            _results(), profile=get_profile(TaskType.FEATURE)
        )
        resolved = v.apply_declared_coverage(gates)
        assert resolved.coverage_met is not True
        assert resolved.all_gates_passed is False

    def test_the_command_runs_in_the_worktree_with_the_project_environment(
        self, tmp_path
    ):
        """The Coach runs the project's own command in the project's own tree
        (B9 repair pass: this subprocess path driven end to end, not read)."""
        worktree = tmp_path / "cwdproj"
        worktree.mkdir()
        (worktree / "Makefile").write_text("all:\n\t@echo build\n", encoding="utf-8")
        script = worktree / "coverage.sh"
        script.write_text(
            "#!/bin/sh\n"
            'printf "cwd=%s\\n" "$PWD"\n'
            'printf "path_set=%s\\n" "${PATH:+yes}"\n'
            "exit 0\n",
            encoding="utf-8",
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        _write_config(worktree, {"coverage": "./coverage.sh"})
        receipt = _validator(worktree).run_declared_coverage()
        assert receipt["exit_code"] == 0
        assert receipt["coverage_met"] is True
        assert str(worktree.resolve()) in receipt["output_tail"]
        assert "path_set=yes" in receipt["output_tail"]
        assert receipt["timed_out"] is False
        assert isinstance(receipt["duration_seconds"], float)

    def test_the_receipt_reaches_the_serialised_turn_record(self, tmp_path):
        """The receipt is not a local variable: it is on the turn record the
        coordinator and the repair loop read."""
        worktree = _make_shell_project(tmp_path, exit_code=0)
        v = _validator(worktree)
        gates = v.apply_declared_coverage(
            v.verify_quality_gates(_results(), profile=get_profile(TaskType.FEATURE))
        )
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidationResult,
        )

        record = CoachValidationResult(
            task_id="TASK-B9C",
            turn=1,
            decision="approve",
            quality_gates=gates,
        ).to_dict()
        serialised = record["validation_results"]["quality_gates"]
        assert serialised["coverage_met"] is True
        assert serialised["coverage_receipt"]["exit_code"] == 0
        assert serialised["coverage_relaxed_by"] is None

    def test_the_toolchain_schema_accepts_coverage_and_rejects_typos(self, tmp_path):
        from guardkit.orchestrator.toolchain_declaration import (
            parse_toolchain_block,
        )

        decl = parse_toolchain_block({"test": "make test", "coverage": "./c.sh"})
        assert decl.coverage == "./c.sh"
        assert decl.coverage_timeout == 300
        with pytest.raises(Exception):
            parse_toolchain_block({"coverages": "./c.sh"})


# ---------------------------------------------------------------------------
# 3. Promises are claims
# ---------------------------------------------------------------------------


def _task_with_promises(status: str = "complete") -> Dict[str, Any]:
    return {
        "task_id": "TASK-B9C",
        "acceptance_criteria": ["AC-001: the endpoint answers"],
        "task_type": "feature",
    }, {
        "task_id": "TASK-B9C",
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "status": status,
                "evidence": "implemented in app/routes.py",
            }
        ],
    }


class TestPromisesAreClaims:
    def test_a_complete_promise_alone_is_claimed_not_verified(self, tmp_path):
        """NEGATIVE CONTROL — the Player's word is not the Coach's verdict."""
        task, results = _task_with_promises()
        v = _validator(tmp_path)
        validation = v.validate_requirements(task, results, turn=1)
        (cr,) = validation.criteria_results
        assert cr.result == CLAIMED
        assert cr.status == CLAIMED
        assert "Claimed by the Player" in cr.evidence

    def test_the_turn_arithmetic_is_unchanged_for_a_claim(self, tmp_path):
        """POSITIVE CONTROL — no new block on a task turn."""
        task, results = _task_with_promises()
        v = _validator(tmp_path)
        validation = v.validate_requirements(task, results, turn=1)
        assert validation.criteria_met == 1
        assert validation.all_criteria_met is True
        assert validation.missing == []

    def test_a_missing_promise_is_still_rejected(self, tmp_path):
        task, results = _task_with_promises()
        results["completion_promises"] = []
        v = _validator(tmp_path)
        validation = v.validate_requirements(task, results, turn=1)
        (cr,) = validation.criteria_results
        assert cr.result == "rejected"
        assert validation.all_criteria_met is False

    def test_corroboration_raises_a_claim_to_verified(self, tmp_path):
        task, results = _task_with_promises()
        v = _validator(tmp_path)
        validation = v.validate_requirements(task, results, turn=1)
        corroborated = v.corroborate_claims(
            validation,
            independent_tests=_passing_run(),
            honesty_verification=_honesty(True),
        )
        (cr,) = corroborated.criteria_results
        assert cr.result == VERIFIED
        assert "Corroborated by" in cr.evidence
        assert corroborated.criteria_met == validation.criteria_met

    def test_an_absent_test_signal_does_not_corroborate(self, tmp_path):
        task, results = _task_with_promises()
        v = _validator(tmp_path)
        validation = v.validate_requirements(task, results, turn=1)
        corroborated = v.corroborate_claims(
            validation,
            independent_tests=_absent_run(),
            honesty_verification=_honesty(True),
        )
        assert corroborated.criteria_results[0].result == CLAIMED

    def test_a_failed_honesty_check_does_not_corroborate(self, tmp_path):
        task, results = _task_with_promises()
        v = _validator(tmp_path)
        validation = v.validate_requirements(task, results, turn=1)
        corroborated = v.corroborate_claims(
            validation,
            independent_tests=_passing_run(),
            honesty_verification=_honesty(False),
        )
        assert corroborated.criteria_results[0].result == CLAIMED


def _write_machine_pass_bar(worktree: Path, task_id: str, criterion_id: str) -> None:
    qa = worktree / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / f"pass-bar-{task_id}.yaml").write_text(
        'format_version: "2.0"\n'
        f"task_id: {task_id}\n"
        'registered_at: {sha: abcd, date: "2026-09-19"}\n'
        "auth_surface_bearing: false\n"
        "preconditions: [suite_green_vs_ledger]\n"
        "criteria:\n"
        f"  - id: {criterion_id}\n"
        "    text: the endpoint answers\n"
        "    class: machine\n"
        "    evidence_kind: json\n"
        "negative_paths: [dependency_down_degradation]\n",
        encoding="utf-8",
    )


class TestMachineClassNeedsABoundReceipt:
    def test_a_green_generic_suite_leaves_a_machine_criterion_claimed(
        self, tmp_path
    ):
        """NEGATIVE CONTROL — exactly the B9 walk-through: a correct helper and
        a passing suite, while the endpoint the person asked for is wrong."""
        _write_machine_pass_bar(tmp_path, "TASK-B9C", "AC-001")
        task, results = _task_with_promises()
        v = _validator(tmp_path)
        validation = v.validate_requirements(task, results, turn=1)
        corroborated = v.corroborate_claims(
            validation,
            independent_tests=_passing_run(),
            honesty_verification=_honesty(True),
        )
        assert corroborated.criteria_results[0].result == CLAIMED

    def test_a_bound_verifier_receipt_verifies_it(self, tmp_path):
        _write_machine_pass_bar(tmp_path, "TASK-B9C", "AC-001")
        private = tmp_path / ".guardkit" / "autobuild-private"
        private.mkdir(parents=True)
        (private / "feature_check.json").write_text(
            json.dumps({"status": "pass", "scenarios_covered": ["AC-001"]}),
            encoding="utf-8",
        )
        task, results = _task_with_promises()
        v = _validator(tmp_path)
        validation = v.validate_requirements(task, results, turn=1)
        corroborated = v.corroborate_claims(
            validation,
            independent_tests=_passing_run(),
            honesty_verification=_honesty(True),
        )
        assert corroborated.criteria_results[0].result == VERIFIED

    def test_a_failed_verifier_receipt_corroborates_nothing(self, tmp_path):
        _write_machine_pass_bar(tmp_path, "TASK-B9C", "AC-001")
        private = tmp_path / ".guardkit" / "autobuild-private"
        private.mkdir(parents=True)
        (private / "feature_check.json").write_text(
            json.dumps({"status": "fail", "scenarios_covered": ["AC-001"]}),
            encoding="utf-8",
        )
        task, results = _task_with_promises()
        v = _validator(tmp_path)
        validation = v.validate_requirements(task, results, turn=1)
        corroborated = v.corroborate_claims(
            validation,
            independent_tests=_passing_run(),
            honesty_verification=_honesty(True),
        )
        assert corroborated.criteria_results[0].result == CLAIMED

    def test_an_absent_receipt_is_read_defensively(self, tmp_path):
        """No file, unreadable file, wrong shape: no corroboration, no crash."""
        v = _validator(tmp_path)
        assert v._feature_check_covered_ids() == set()
        private = tmp_path / ".guardkit" / "autobuild-private"
        private.mkdir(parents=True)
        (private / "feature_check.json").write_text("{not json", encoding="utf-8")
        assert v._feature_check_covered_ids() == set()
        (private / "feature_check.json").write_text("[]", encoding="utf-8")
        assert v._feature_check_covered_ids() == set()

    def test_a_bound_gate_result_also_verifies_it(self, tmp_path):
        _write_machine_pass_bar(tmp_path, "TASK-B9C", "AC-001")
        task, results = _task_with_promises()
        v = _validator(tmp_path)
        validation = v.validate_requirements(task, results, turn=1)
        corroborated = v.corroborate_claims(
            validation,
            independent_tests=_passing_run(),
            honesty_verification=_honesty(True),
            gate_verified_ids={"AC-001"},
        )
        assert corroborated.criteria_results[0].result == VERIFIED
