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


class TestTheBaselineDiffSaysWhyItDidNotAct:
    """Every way out of the diff names itself (2026-09-13).

    FEAT-19C4 stalled for five turns on six failures the ledger already
    forgave. Which of the four early returns was taken could not be answered
    from the build's receipt, because only the suppressing path ever spoke —
    a build where the diff never fired read exactly like one where it was
    never reached. These pin that each exit says what it did. The verdicts
    themselves are unchanged; the tests above still own those.
    """

    def test_it_names_the_failures_it_charged_and_the_files_it_blamed(
        self, tmp_path, caplog
    ):
        """A re-charged inherited failure says so, and names the file."""
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))
        result = _failed_result("FAILED tests/slice.py::test_home - stale\n")

        with caplog.at_level("INFO"):
            out = cv._apply_baseline_diff(
                result, {"files_modified": ["tests/slice.py"]}
            )

        assert out.tests_passed is False  # unchanged: the task touched it
        said = caplog.text
        assert "baseline diff: NOT applied" in said
        assert "re-charged because this task touched their test file" in said
        assert "tests/slice.py::test_home" in said
        assert "tests/slice.py" in said

    def test_it_says_when_no_failing_id_could_be_read(self, tmp_path, caplog):
        """Unparseable output is named as such, not passed over in silence."""
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))
        result = _failed_result("the suite exploded before it could report\n")

        with caplog.at_level("INFO"):
            out = cv._apply_baseline_diff(result, {})

        assert out.tests_passed is False
        assert "could not read a single failing test id" in caplog.text

    def test_it_says_when_there_is_no_red_base_on_record(self, tmp_path, caplog):
        """With nothing known about the base, it says the diff is inert."""
        cv = CoachValidator(str(tmp_path))  # no baseline written, no ledger
        result = _failed_result("FAILED tests/slice.py::test_home - real\n")

        with caplog.at_level("INFO"):
            out = cv._apply_baseline_diff(result, {})

        assert out.tests_passed is False
        assert "baseline diff: INERT" in caplog.text
        assert "no red base on record" in caplog.text

    def test_it_says_when_there_was_nothing_to_forgive(self, tmp_path, caplog):
        """An absent signal is named, never silently left to look like a choice."""
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))
        absent = IndependentTestResult.absent(
            test_command="pytest -q",
            test_output_summary="timeout",
            duration_seconds=1.0,
            raw_output=None,
        )

        with caplog.at_level("INFO"):
            out = cv._apply_baseline_diff(absent, {})

        assert out.tests_passed is False
        assert "baseline diff: not applicable" in caplog.text


class TestTheSuppressedRunExplainsItself:
    """A pass beside a red output must say why both are true.

    FEAT-C2BA, 2026-09-13: the diff flipped the verdict and left the run's
    output untouched, so the bundle carried "tests_passed=true" next to
    "12 failed" with nothing joining them. The reviewer refused on exactly
    that wording, twice, on turns where the builder had done everything asked
    of it — and 0 of 4 acceptance criteria were verified either time.
    """

    def test_the_output_keeps_every_byte_and_gains_an_explanation(self, tmp_path):
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))
        original = "FAILED tests/slice.py::test_home - stale\n1 failed, 99 passed\n"
        result = _failed_result(original)

        out = cv._apply_baseline_diff(result, {"files_modified": ["src/other.py"]})

        assert out.tests_passed is True
        assert original in out.raw_output, "the forensic output must survive intact"
        assert "NOTE FOR THE REVIEWER" in out.raw_output
        assert "ALREADY failing on this branch's base" in out.raw_output
        assert "nothing in them for the builder to fix" in out.raw_output

    def test_a_run_that_is_not_suppressed_is_untouched(self, tmp_path):
        """A genuine regression's output gains nothing — no note, no edit."""
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))
        original = (
            "FAILED tests/slice.py::test_home - stale\n"
            "FAILED tests/new.py::test_regression - real\n"
        )
        out = cv._apply_baseline_diff(_failed_result(original), {"files_modified": []})

        assert out.tests_passed is False
        assert out.raw_output == original
        assert "NOTE FOR THE REVIEWER" not in out.raw_output


class TestAnUnmeasuredBaseline:
    """Reliability repair 2 (12 October 2026). A baseline that did not pass
    and named no failing test measured nothing: it excuses nothing, and every
    comparison says no baseline comparison was possible — never "new failures
    against the measured baseline"."""

    def test_the_diff_is_inert_and_says_no_comparison_was_possible(
        self, tmp_path, caplog
    ):
        _write_baseline(tmp_path, [])  # red, naming nothing: unmeasured
        cv = CoachValidator(str(tmp_path))
        result = _failed_result(
            "FAILED tests/test_url.py::test_database_url - real\n"
            "1 failed, 871 passed in 9.0s\n"
        )
        with caplog.at_level("INFO"):
            out = cv._apply_baseline_diff(result, {})

        assert out.tests_passed is False
        assert "baseline diff: INERT" in caplog.text
        assert "no baseline comparison was possible" in caplog.text

    def test_the_work_leg_base_is_not_known(self, tmp_path):
        _write_baseline(tmp_path, [])
        cv = CoachValidator(str(tmp_path))

        known, ids, source = cv.base_failing_tests()

        assert known is False
        assert ids == []
        assert source.startswith("no baseline comparison was possible")
        assert "measured baseline" not in source
        assert cv.compare_suite_against_base(
            _failed_result(
                "FAILED tests/test_url.py::test_database_url - real\n"
                "1 failed, 871 passed in 9.0s\n"
            )
        ) is None

    def test_a_ledger_beside_it_is_the_only_source_named(self, tmp_path):
        _write_baseline(tmp_path, [])
        (tmp_path / "qa").mkdir()
        (tmp_path / "qa" / "known-failures.yaml").write_text(
            "known_failures:\n  - test_id: tests/test_url.py::test_old\n"
        )
        cv = CoachValidator(str(tmp_path))

        known, ids, source = cv.base_failing_tests()

        assert known is True
        assert ids == ["tests/test_url.py::test_old"]
        assert "measured baseline" not in source
        assert "known-failure ledger" in source

    def test_a_measured_red_base_still_compares(self, tmp_path):
        """Control: named failures from a measured baseline still count."""
        _write_baseline(tmp_path, ["tests/slice.py::test_home"])
        cv = CoachValidator(str(tmp_path))

        known, ids, source = cv.base_failing_tests()

        assert known is True
        assert ids == ["tests/slice.py::test_home"]
        assert "measured baseline" in source
