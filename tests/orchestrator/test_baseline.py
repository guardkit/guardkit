"""Unit tests for the baseline-green probe + baseline-diff module (L12 items 1-2).

Red-baseline retro 2026-07-08. Covers node-id normalisation, the charged-
failures diff (baseline ∪ ledger, with authored-file re-charge), baseline.json
round-trip, the F2-ledger read (READ-ONLY / fail-open), and the wave-0 warning.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from guardkit.orchestrator.baseline import (
    BaselineResult,
    baseline_diff_enabled,
    baseline_measured_here,
    compute_charged_failures,
    failing_node_ids,
    feature_baseline_path,
    load_known_failure_ids,
    load_baseline_file,
    probe_baseline_result,
    read_baseline_from_worktree,
    worktree_identity,
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


class TestARecordNobodyCanRead:
    """A baseline.json that is not a JSON object is "no record", never a crash.

    Every reader of this file — the probe, the Coach's diff, finalize's
    machine-verify — comes through here, so the guard belongs here. Before it,
    a file holding ``[]`` reached ``BaselineResult.from_dict``, which asked a
    list for ``.get``: an AttributeError before wave 1 on a report-only probe.
    """

    SHAPES = [
        ("a JSON list", "[]"),
        ("a bare JSON string", '"nope"'),
        ("a JSON number", "3"),
        ("JSON null", "null"),
        ("not JSON at all", "definitely { not json"),
    ]

    @pytest.mark.parametrize(
        "shape,content", SHAPES, ids=[s for s, _ in SHAPES]
    )
    def test_reads_as_no_record_with_one_warning(
        self, tmp_path, caplog, shape, content
    ):
        path = feature_baseline_path(tmp_path, "FEAT-X")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            assert read_baseline_from_worktree(tmp_path) is None

        warnings = [
            r for r in caplog.records if "could not be read" in r.getMessage()
        ]
        assert len(warnings) == 1, f"{shape}: expected exactly one warning"

    @pytest.mark.parametrize(
        "shape,content", SHAPES, ids=[s for s, _ in SHAPES]
    )
    def test_one_file_reads_as_no_record(self, tmp_path, shape, content):
        path = tmp_path / "baseline.json"
        path.write_text(content, encoding="utf-8")
        assert load_baseline_file(path) is None

    def test_a_file_that_is_not_there_says_nothing_at_all(self, tmp_path, caplog):
        with caplog.at_level(logging.WARNING):
            assert load_baseline_file(tmp_path / "baseline.json") is None
        assert caplog.records == []

    def test_a_readable_record_beside_an_unreadable_one_is_still_found(
        self, tmp_path
    ):
        broken = feature_baseline_path(tmp_path, "FEAT-AAA")
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_text("[]", encoding="utf-8")
        write_baseline(
            feature_baseline_path(tmp_path, "FEAT-BBB"),
            BaselineResult("pytest -q", 0, True, 0),
        )
        found = read_baseline_from_worktree(tmp_path)
        assert found is not None
        assert found.command == "pytest -q"


class TestWhichRecordThisBuildMeasured:
    """Told apart by the directory that was measured, not by the file's path.

    A committed baseline.json sits at the feature's own path and reads word for
    word like a measured one, so the stamp is a fact about the directory it was
    written in — one a commit cannot carry.
    """

    def _stamped_in(self, worktree: Path, directory: Path, feature: str):
        record = probe_baseline_result(
            command="pytest -q",
            expected_exit=0,
            passed=True,
            exit_code=0,
            output="1 passed",
            timestamp="2026-09-10T10:00:00",
            measured_in=worktree_identity(directory),
        )
        write_baseline(feature_baseline_path(worktree, feature), record)
        return record

    def test_a_record_stamped_here_is_ours(self, tmp_path):
        record = self._stamped_in(tmp_path, tmp_path, "FEAT-X")
        assert baseline_measured_here(record, tmp_path) is True

    def test_a_record_stamped_in_another_directory_is_not(self, tmp_path):
        other = tmp_path / "another-worktree"
        other.mkdir()
        record = self._stamped_in(tmp_path, other, "FEAT-X")
        assert baseline_measured_here(record, tmp_path) is False

    def test_a_record_with_no_stamp_is_not_ours(self, tmp_path):
        assert baseline_measured_here(
            BaselineResult("pytest -q", 0, True, 0), tmp_path
        ) is False

    def test_a_directory_that_is_not_there_matches_nothing(self, tmp_path):
        record = self._stamped_in(tmp_path, tmp_path, "FEAT-X")
        assert baseline_measured_here(record, tmp_path / "gone") is False

    def test_the_stamp_survives_a_round_trip_through_the_file(self, tmp_path):
        self._stamped_in(tmp_path, tmp_path, "FEAT-X")
        loaded = read_baseline_from_worktree(tmp_path)
        assert loaded is not None
        assert baseline_measured_here(loaded, tmp_path) is True
        on_disk = json.loads(
            feature_baseline_path(tmp_path, "FEAT-X").read_text(encoding="utf-8")
        )
        assert on_disk["measured_in"]["worktree"] == str(tmp_path)

    def test_our_measurement_beats_a_record_that_came_with_the_code(
        self, tmp_path
    ):
        """The forge case: the tracked record sorts first, ours still wins."""
        write_baseline(
            feature_baseline_path(tmp_path, "FEAT-AUTH-002"),
            BaselineResult("the July command", 0, True, 0),
        )
        self._stamped_in(tmp_path, tmp_path, "FEAT-X")
        found = read_baseline_from_worktree(tmp_path)
        assert found is not None
        assert found.command == "pytest -q"

    def test_with_nothing_stamped_the_first_record_is_returned_as_before(
        self, tmp_path
    ):
        write_baseline(
            feature_baseline_path(tmp_path, "FEAT-AAA"),
            BaselineResult("first", 0, True, 0),
        )
        write_baseline(
            feature_baseline_path(tmp_path, "FEAT-BBB"),
            BaselineResult("second", 0, True, 0),
        )
        found = read_baseline_from_worktree(tmp_path)
        assert found is not None
        assert found.command == "first"
