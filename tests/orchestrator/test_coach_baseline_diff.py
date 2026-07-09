"""CoachValidator baseline-diff behaviour (red-baseline retro, L12 item 2).

The measured baseline is an artefact the wave-0 probe writes to
``<worktree>/.guardkit/autobuild/<feature>/baseline.json``. CoachValidator
reads it and suppresses a ran-and-failed independent verdict whose failures
are ALL pre-existing (baseline ∪ F2 ledger). It NEVER flips an absent signal,
NEVER a genuine regression, and is inert when no red baseline exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.orchestrator.baseline import BaselineResult, feature_baseline_path, write_baseline
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)


def _write_baseline(worktree: Path, failing_ids, passed=False):
    write_baseline(
        feature_baseline_path(worktree, "FEAT-X"),
        BaselineResult(
            command="pytest -q",
            expected_exit=0,
            passed=passed,
            exit_code=0 if passed else 1,
            failing_node_ids=list(failing_ids),
            failing_count=len(failing_ids),
            timestamp="2026-07-09T00:00:00",
        ),
    )


def _failed_result(raw_output):
    return IndependentTestResult.from_run(
        tests_passed=False,
        test_command="pytest -q",
        test_output_summary="1 failed",
        duration_seconds=0.1,
        output=raw_output,
        resolved_interpreter=None,
    )


class TestApplyBaselineDiff:
    def test_all_failures_baseline_flip_to_pass(self, tmp_path):
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))
        result = _failed_result("FAILED tests/slice.py::test_home - stale\n")

        out = cv._apply_baseline_diff(result, {"files_modified": ["src/other.py"]})
        assert out.tests_passed is True
        assert "attributed to the measured baseline" in out.test_output_summary

    def test_regression_left_standing(self, tmp_path):
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))
        result = _failed_result(
            "FAILED tests/slice.py::test_home - stale\n"
            "FAILED tests/new.py::test_regression - real\n"
        )
        out = cv._apply_baseline_diff(result, {"files_modified": []})
        assert out.tests_passed is False  # a genuine regression remains

    def test_absent_signal_never_flipped(self, tmp_path):
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))
        absent = IndependentTestResult.absent(
            test_command="pytest -q",
            test_output_summary="timeout",
            duration_seconds=1.0,
            raw_output=None,
        )
        out = cv._apply_baseline_diff(absent, {})
        assert out.tests_passed is False
        assert out.signal_absent is True

    def test_authored_baseline_test_recharged(self, tmp_path):
        """A baseline-red test the task authored is NOT excused."""
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))
        result = _failed_result("FAILED tests/slice.py::test_home - stale\n")
        out = cv._apply_baseline_diff(
            result, {"files_modified": ["tests/slice.py"]}
        )
        assert out.tests_passed is False  # task owns the file → charged

    def test_unparseable_output_fails_closed(self, tmp_path):
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))
        # flutter-shaped output: no pytest FAILED lines → cannot attribute.
        result = _failed_result("00:01 +209 -1: some flutter test [E]\n")
        out = cv._apply_baseline_diff(result, {})
        assert out.tests_passed is False

    def test_no_baseline_is_inert(self, tmp_path):
        cv = CoachValidator(str(tmp_path))  # no baseline.json written
        result = _failed_result("FAILED tests/x.py::test_y - boom\n")
        out = cv._apply_baseline_diff(result, {})
        assert out.tests_passed is False  # unchanged

    def test_green_baseline_is_inert(self, tmp_path):
        _write_baseline(tmp_path, [], passed=True)
        cv = CoachValidator(str(tmp_path))
        result = _failed_result("FAILED tests/x.py::test_y - boom\n")
        out = cv._apply_baseline_diff(result, {})
        assert out.tests_passed is False  # unchanged

    def test_kill_switch_disables(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_BASELINE_DIFF", "0")
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))
        result = _failed_result("FAILED tests/slice.py::test_home - stale\n")
        out = cv._apply_baseline_diff(result, {})
        assert out.tests_passed is False  # flag off → inert


class TestDeterministicGateDefer:
    def test_defers_test_gate_when_baseline_active(self, tmp_path):
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))
        gates = cv.verify_quality_gates(
            {"quality_gates": {"tests_failed": 1, "all_passed": False}}
        )
        # The count-based gate defers to the independent run (tests_passed True).
        assert gates.tests_passed is True

    def test_no_baseline_gate_still_fails(self, tmp_path):
        cv = CoachValidator(str(tmp_path))
        gates = cv.verify_quality_gates(
            {"quality_gates": {"tests_failed": 1, "all_passed": False}}
        )
        assert gates.tests_passed is False  # inert without a baseline

    def test_green_baseline_gate_still_fails(self, tmp_path):
        _write_baseline(tmp_path, [], passed=True)
        cv = CoachValidator(str(tmp_path))
        gates = cv.verify_quality_gates(
            {"quality_gates": {"tests_failed": 1, "all_passed": False}}
        )
        assert gates.tests_passed is False
