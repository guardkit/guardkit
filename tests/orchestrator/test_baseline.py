"""Unit tests for the baseline-green probe + baseline-diff module (L12 items 1-2).

Red-baseline retro 2026-07-08. Covers node-id normalisation, the charged-
failures diff (baseline ∪ ledger, with authored-file re-charge), baseline.json
round-trip, the F2-ledger read (READ-ONLY / fail-open), and the wave-0 warning.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.orchestrator.baseline import (
    BaselineResult,
    baseline_diff_enabled,
    compute_charged_failures,
    failing_node_ids,
    feature_baseline_path,
    load_known_failure_ids,
    probe_baseline_result,
    read_baseline_from_worktree,
    to_node_id,
    wave0_baseline_warning,
    write_baseline,
)


class TestNodeIdParsing:
    def test_strips_verdict_word(self):
        assert to_node_id("FAILED tests/a.py::test_x") == "tests/a.py::test_x"
        assert to_node_id("ERROR tests/a.py") == "tests/a.py"

    def test_failing_node_ids_from_pytest_output(self):
        out = (
            "tests/a.py::test_x FAILED\n"
            "FAILED tests/a.py::test_x - AssertionError\n"
            "FAILED tests/b.py::test_y - ValueError\n"
            "ERROR tests/c.py\n"
        )
        assert failing_node_ids(out) == [
            "tests/a.py::test_x",
            "tests/b.py::test_y",
            "tests/c.py",
        ]

    def test_empty_output_yields_no_ids(self):
        assert failing_node_ids("") == []
        assert failing_node_ids(None) == []


class TestChargedFailures:
    def test_regression_is_charged_baseline_is_not(self):
        charged = compute_charged_failures(
            observed_node_ids=["t/a.py::t1", "t/b.py::t2"],
            baseline_node_ids=["t/a.py::t1"],
            ledger_ids=set(),
        )
        assert charged == ["t/b.py::t2"]

    def test_all_baseline_yields_no_charge(self):
        charged = compute_charged_failures(
            observed_node_ids=["t/a.py::t1"],
            baseline_node_ids=["t/a.py::t1"],
            ledger_ids=set(),
        )
        assert charged == []

    def test_ledger_excuses_failure(self):
        charged = compute_charged_failures(
            observed_node_ids=["t/a.py::t1"],
            baseline_node_ids=[],
            ledger_ids={"t/a.py::t1"},
        )
        assert charged == []

    def test_authored_file_recharges_baseline_failure(self):
        """A baseline-red test the task authored IS charged (fixed-then-still-red)."""
        charged = compute_charged_failures(
            observed_node_ids=["t/a.py::t1"],
            baseline_node_ids=["t/a.py::t1"],
            ledger_ids=set(),
            authored_test_files=["t/a.py"],
        )
        assert charged == ["t/a.py::t1"]

    def test_dedup_preserves_order(self):
        charged = compute_charged_failures(
            observed_node_ids=["t/b.py::t2", "t/b.py::t2", "t/c.py::t3"],
            baseline_node_ids=[],
            ledger_ids=set(),
        )
        assert charged == ["t/b.py::t2", "t/c.py::t3"]


class TestBaselineRoundTrip:
    def test_write_and_read(self, tmp_path):
        result = BaselineResult(
            command="pytest -q",
            expected_exit=0,
            passed=False,
            exit_code=1,
            failing_node_ids=["t/a.py::t1"],
            failing_count=1,
            timestamp="2026-07-09T00:00:00",
        )
        path = feature_baseline_path(tmp_path, "FEAT-X")
        write_baseline(path, result)
        assert path.exists()

        loaded = read_baseline_from_worktree(tmp_path)
        assert loaded is not None
        assert loaded.passed is False
        assert loaded.failing_node_ids == ["t/a.py::t1"]
        # The persisted file loudly marks itself NOT the ledger (LPA-09).
        assert "NOT the qa/known-failures.yaml" in path.read_text()

    def test_read_absent_returns_none(self, tmp_path):
        assert read_baseline_from_worktree(tmp_path) is None


class TestKnownFailureLedgerRead:
    def test_reads_test_ids(self, tmp_path):
        (tmp_path / "qa").mkdir()
        (tmp_path / "qa" / "known-failures.yaml").write_text(
            "suite_id: s\nframework: pytest\nlanguage: python\n"
            "known_failures:\n"
            "  - test_id: tests/x.py::test_flaky\n    reason: r\n"
        )
        ids = load_known_failure_ids(tmp_path)
        assert "tests/x.py::test_flaky" in ids

    def test_missing_ledger_is_empty_set(self, tmp_path):
        assert load_known_failure_ids(tmp_path) == set()

    def test_malformed_ledger_fails_open(self, tmp_path):
        (tmp_path / "qa").mkdir()
        (tmp_path / "qa" / "known-failures.yaml").write_text(":::not yaml:::[")
        assert load_known_failure_ids(tmp_path) == set()


class TestWave0Warning:
    def test_green_baseline_no_warning(self):
        r = BaselineResult("pytest", 0, True, 0)
        assert wave0_baseline_warning(r) is None

    def test_red_baseline_lists_failures(self):
        r = probe_baseline_result(
            command="pytest -q",
            expected_exit=0,
            passed=False,
            exit_code=1,
            output="FAILED tests/a.py::test_x - boom\n",
            timestamp="2026-07-09T00:00:00",
        )
        msg = wave0_baseline_warning(r)
        assert "pre-existing test failure" in msg
        assert "not attributable to any task" in msg
        assert "tests/a.py::test_x" in msg

    def test_red_baseline_unparseable_ids_still_warns(self):
        r = BaselineResult("flutter test", 0, False, 1, [], 0)
        msg = wave0_baseline_warning(r)
        assert "not attributable to any task" in msg
        assert "not parseable" in msg


class TestDiffEnabledFlag:
    def test_default_on(self, monkeypatch):
        monkeypatch.delenv("GUARDKIT_AUTOBUILD_BASELINE_DIFF", raising=False)
        assert baseline_diff_enabled() is True

    @pytest.mark.parametrize("val", ["0", "false", "off", "no", "FALSE"])
    def test_kill_switch(self, monkeypatch, val):
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_BASELINE_DIFF", val)
        assert baseline_diff_enabled() is False
