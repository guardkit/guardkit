"""Drive the "what did not run" report — see tests/skip_report.py.

The point of that module is that a green tick must never quietly mean "green,
and some things did not run". These tests hold it to four promises:

  * a WHOLE FILE that stood down at import is reported (the kind that hid a real
    ``select_harness(cwd=)`` defect for eleven weeks, because it produces a
    COLLECTION report that the obvious hook never sees);
  * an ordinary skip inside a test is reported under its own heading;
  * a run with nothing skipped prints nothing at all;
  * the exit code is IDENTICAL with and without the report, in every case.

Most of these run a real pytest in a subprocess, because three of the four
claims are about the shape of a whole run — where the block lands in stdout, and
what the process exits with — and neither can be checked from inside the run
being described. ``sys.executable`` is used deliberately: this estate's boxes
have no bare ``python`` on PATH.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKIP_REPORT_PATH = REPO_ROOT / "tests" / "skip_report.py"

# The fleet-evals runners keep only the last 4,000 characters of a run's stdout
# (`proc.stdout[-4000:]`). A report that lands outside that window is invisible
# in the artefact people actually read, which is how the previous attempt at
# this idea was lost. See tests/skip_report.py for the measured offsets.
RECEIPT_TAIL_CHARS = 4000


# ---------------------------------------------------------------------------
# These tests describe DEFAULT behaviour, so they must not read the operator's
# environment. Without this, the module's own documented switches turned this
# very suite RED: GUARDKIT_SKIP_REPORT=off made pytest_unconfigure write
# nothing, and =full bypassed the size budget — each failing a test in the class
# literally named "the report can never turn a run red". Measured before the
# fix: `GUARDKIT_SKIP_REPORT=off pytest tests/unit/test_skip_report.py` gave
# 1 failed / 26 passed. CI never sets the variable, so the merge gate was safe;
# the first person to use the advertised escape hatch would have been the one to
# find this. A test that reads ambient configuration is not testing a default.
# Tests that deliberately exercise a switch set it themselves via monkeypatch.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _no_ambient_skip_report_setting(monkeypatch):
    monkeypatch.delenv("GUARDKIT_SKIP_REPORT", raising=False)


# ---------------------------------------------------------------------------
# A private copy of the module, so unit tests cannot pollute the live run
# ---------------------------------------------------------------------------
@pytest.fixture
def isolated_report():
    """Load a SECOND, private copy of tests/skip_report.py.

    The module keeps the session's skips in module-level state. The copy that
    ``tests/conftest.py`` imported is describing the very run these tests are
    part of, so feeding it fake reports would corrupt the real report printed at
    the end. A separately-loaded copy has its own state and its own hooks that
    pytest never sees.
    """
    spec = importlib.util.spec_from_file_location(
        "skip_report_under_test", SKIP_REPORT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeReport:
    """The two attributes the hooks read off a real pytest report."""

    def __init__(self, nodeid, reason, skipped=True, wasxfail=None):
        self.nodeid = nodeid
        self.skipped = skipped
        self.when = "call"
        self.longrepr = ("some/file.py", 1, reason)
        if wasxfail is not None:
            self.wasxfail = wasxfail


# ---------------------------------------------------------------------------
# Classification, checked directly
# ---------------------------------------------------------------------------
class TestClassification:
    def test_a_whole_file_that_could_not_import_is_its_own_category(
        self, isolated_report
    ):
        """The dangerous kind: nothing in the file was read, so nothing failed."""
        isolated_report.pytest_collectreport(
            _FakeReport(
                "tests/some_file.py",
                "Skipped: could not import 'guardkitfactory.harness': No module named 'guardkitfactory'",
            )
        )
        recorded = isolated_report._skips["tests/some_file.py"]
        assert recorded.category == isolated_report.FILE_PACKAGE_ABSENT

    def test_a_whole_file_skipped_for_a_written_reason_is_a_decision(
        self, isolated_report
    ):
        isolated_report.pytest_collectreport(
            _FakeReport("tests/other_file.py", "Skipped: R1 de-wire (Rich 08-14)")
        )
        recorded = isolated_report._skips["tests/other_file.py"]
        assert recorded.category == isolated_report.FILE_DECISION

    def test_a_quarantined_test_is_not_muddled_with_an_ordinary_skip(
        self, isolated_report
    ):
        isolated_report.pytest_runtest_logreport(
            _FakeReport(
                "tests/x.py::test_a",
                "Skipped: quarantined pre-existing failure — see tests/quarantine.txt",
            )
        )
        isolated_report.pytest_runtest_logreport(
            _FakeReport("tests/x.py::test_b", "Skipped: no widget on this machine")
        )
        assert (
            isolated_report._skips["tests/x.py::test_a"].category
            == isolated_report.QUARANTINED
        )
        assert (
            isolated_report._skips["tests/x.py::test_b"].category
            == isolated_report.ORDINARY
        )

    def test_an_expected_failure_is_not_counted_as_a_skip(self, isolated_report):
        """pytest gives an xfail a "skipped" report and then counts it as xfailed.

        Counting it here made the report disagree with the line printed directly
        above it — measured on the full suite as 1,391 against pytest's 1,390.
        """
        isolated_report.pytest_runtest_logreport(
            _FakeReport("tests/x.py::test_known_broken", "", wasxfail="known broken")
        )
        assert isolated_report._skips == {}

    def test_a_session_does_not_inherit_the_previous_one_s_skips(
        self, isolated_report
    ):
        isolated_report.pytest_runtest_logreport(
            _FakeReport("tests/x.py::test_a", "Skipped: something")
        )
        isolated_report.pytest_sessionstart(session=None)
        assert isolated_report._skips == {}

    def test_nothing_skipped_means_nothing_said(self, isolated_report):
        assert isolated_report.build_report_lines() == []


# ---------------------------------------------------------------------------
# The two text rules the classifier leans on, pinned against their real sources
# ---------------------------------------------------------------------------
class TestTheTextRulesAreStillTrue:
    """pytest records no structured reason for a skip, only free text.

    Two of the four categories are therefore matched on that text. A reword
    would not lose an item — it would move to another heading — but it would
    make the report less useful, so both rules are pinned to the thing they
    claim to describe rather than to a copy of it.
    """

    def test_importorskip_still_says_could_not_import(self, isolated_report):
        # ``pytest.raises(Exception)`` does NOT work here, and finding that out
        # was instructive: ``Skipped`` inherits from BaseException, so the first
        # version of this test let the skip escape and SKIPPED ITSELF — passing
        # by not running, which is the exact failure this whole lane exists to
        # make visible. Catch the skip explicitly, and fail loudly if none came.
        try:
            pytest.importorskip("a_package_that_certainly_is_not_installed_zzz")
        except pytest.skip.Exception as exc:
            message = str(exc)
        else:
            pytest.fail(
                "pytest.importorskip did not raise for a package that is not "
                "installed; this pin can no longer check anything."
            )
        assert message.lower().startswith(isolated_report.IMPORTORSKIP_PREFIX), (
            "pytest reworded importorskip; tests/skip_report.py would file these "
            f"whole-file skips under 'by decision' instead. Got: {message!r}"
        )

    def test_the_quarantine_still_names_the_file_this_report_looks_for(
        self, isolated_report
    ):
        """Ask guardkit's own quarantine hook what reason it attaches."""
        from tests import conftest as guardkit_conftest

        quarantined_nodeids = sorted(guardkit_conftest._QUARANTINE_EXACT)
        if not quarantined_nodeids:
            pytest.skip("tests/quarantine.txt has no exact entries to check")

        class _Item:
            def __init__(self, nodeid):
                self.nodeid = nodeid
                self.markers = []

            def add_marker(self, marker):
                self.markers.append(marker)

        class _PluginManager:
            def get_plugin(self, name):
                return None

        class _Config:
            pluginmanager = _PluginManager()

        item = _Item(quarantined_nodeids[0])
        previous = os.environ.pop("GUARDKIT_NO_QUARANTINE", None)
        try:
            guardkit_conftest.pytest_collection_modifyitems(_Config(), [item])
        finally:
            if previous is not None:
                os.environ["GUARDKIT_NO_QUARANTINE"] = previous

        assert item.markers, "the quarantine hook did not skip a quarantined node"
        reason = item.markers[0].kwargs["reason"]
        assert isolated_report.QUARANTINE_MARKER in reason, (
            "the quarantine reason no longer names "
            f"{isolated_report.QUARANTINE_MARKER!r}, so tests/skip_report.py "
            f"would file 345 quarantined tests under 'ordinary'. Got: {reason!r}"
        )


# ---------------------------------------------------------------------------
# Whole real runs, in a subprocess
# ---------------------------------------------------------------------------
_MIXED_FILES = {
    "test_whole_file_needs_a_package.py": (
        "import pytest\n"
        "pytest.importorskip('a_package_that_certainly_is_not_installed_zzz')\n"
        "\n"
        "def test_this_never_runs():\n"
        "    raise AssertionError('collected after all')\n"
    ),
    "test_whole_file_stood_down_on_purpose.py": (
        "import pytest\n"
        "pytest.skip('de-wired on purpose, the thing it tested was removed',\n"
        "            allow_module_level=True)\n"
        "\n"
        "def test_this_never_runs():\n"
        "    raise AssertionError('collected after all')\n"
    ),
    "test_ordinary.py": (
        "import pytest\n"
        "\n"
        "@pytest.mark.skipif(True, reason='this machine has no widget')\n"
        "def test_needs_a_widget():\n"
        "    pass\n"
        "\n"
        "def test_steps_aside_halfway():\n"
        "    pytest.skip('nothing to look at here')\n"
        "\n"
        "@pytest.mark.skip(reason='quarantined pre-existing failure — see "
        "tests/quarantine.txt (TASK-INFRA-CIGREEN)')\n"
        "def test_is_quarantined():\n"
        "    pass\n"
        "\n"
        "@pytest.mark.xfail(reason='known broken')\n"
        "def test_is_expected_to_fail():\n"
        "    raise AssertionError('as expected')\n"
        "\n"
        "def test_passes():\n"
        "    pass\n"
    ),
}

_MIXED_WITH_A_FAILURE = dict(
    _MIXED_FILES,
    **{"test_fails.py": "def test_fails():\n    raise AssertionError('a real failure')\n"},
)

_NO_SKIPS_AT_ALL = {
    "test_all_green.py": "def test_one():\n    pass\n\ndef test_two():\n    pass\n"
}


def _write(directory: Path, files: "dict[str, str]") -> None:
    for name, body in files.items():
        (directory / name).write_text(body, encoding="utf-8")


def _run_pytest(directory: Path, *, with_report: bool, env_extra=None):
    """Run a real pytest over `directory`, with or without the report plugin."""
    args = [
        sys.executable,
        "-m",
        "pytest",
        str(directory),
        "-p",
        "no:cacheprovider",
        "-q",
        "-rfE",
    ]
    if with_report:
        args[3:3] = ["-p", "tests.skip_report"]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    # Never let the outer run's options leak into the inner one.
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("GUARDKIT_SKIP_REPORT", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        args, capture_output=True, text=True, env=env, cwd=str(directory), timeout=180
    )


@pytest.fixture(scope="module")
def mixed_run(tmp_path_factory):
    """One run with every kind of skip this suite actually produces, plus a failure."""
    directory = tmp_path_factory.mktemp("mixed")
    _write(directory, _MIXED_WITH_A_FAILURE)
    return directory, _run_pytest(directory, with_report=True)


class TestARealRun:
    def test_a_whole_file_skipped_at_import_is_reported(self, mixed_run):
        """The category that matters most, and the one the obvious hook misses.

        ``pytest.importorskip`` at the top of a file produces a COLLECTION
        report, not a runtest one, so ``pytest_runtest_logreport`` never fires
        for it. Without the collection hook the file vanishes without trace.
        """
        _, proc = mixed_run
        assert "test_whole_file_needs_a_package.py" in proc.stdout
        assert "a package they need is not installed" in proc.stdout

    def test_a_whole_file_stood_down_on_purpose_is_reported_separately(
        self, mixed_run
    ):
        _, proc = mixed_run
        assert "by a decision written into the file" in proc.stdout
        assert "test_whole_file_stood_down_on_purpose.py" in proc.stdout

    def test_an_ordinary_skip_is_reported_in_its_own_category(self, mixed_run):
        _, proc = mixed_run
        assert "SINGLE TESTS THAT STEPPED ASIDE" in proc.stdout
        assert "this machine has no widget" in proc.stdout
        assert "nothing to look at here" in proc.stdout

    def test_a_quarantined_test_is_counted_apart_from_the_ordinary_ones(
        self, mixed_run
    ):
        _, proc = mixed_run
        assert "TESTS HELD BACK as known failures" in proc.stdout
        assert "1 quarantined, 2 single tests" in proc.stdout

    def test_an_expected_failure_is_not_called_a_skip(self, mixed_run):
        _, proc = mixed_run
        assert "test_is_expected_to_fail" not in proc.stdout.split(
            "WHAT DID NOT RUN"
        )[-1]
        # pytest's own count and the report's count must agree.
        assert "5 skips in total" in proc.stdout
        assert "5 skipped" in proc.stdout

    def test_the_report_is_the_very_last_thing_printed(self, mixed_run):
        """Being last is the whole point — a receipt keeps only the tail.

        pytest prints the ``FAILED ...`` short-summary lines and the final
        ``N failed, N passed`` stats line AFTER every ``pytest_terminal_summary``
        hook. This run contains a real failure precisely so that ordering is
        exercised rather than assumed.
        """
        _, proc = mixed_run
        stdout = proc.stdout
        assert stdout.rstrip().endswith("=" * 78)
        block_start = stdout.index("WHAT DID NOT RUN")
        assert stdout.index("FAILED ") < block_start, "the FAILED lines must come first"
        assert stdout.index("1 failed") < block_start, "the stats line must come first"

    def test_the_report_survives_a_four_thousand_character_tail(self, mixed_run):
        _, proc = mixed_run
        tail = proc.stdout[-RECEIPT_TAIL_CHARS:]
        assert "WHAT DID NOT RUN" in tail
        assert "a package they need is not installed" in tail
        assert "IN ONE LINE:" in tail

    def test_the_exit_code_is_not_changed_by_the_report(self, mixed_run):
        directory, proc = mixed_run
        control = _run_pytest(directory, with_report=False)
        assert proc.returncode == control.returncode == 1
        assert "WHAT DID NOT RUN" not in control.stdout


class TestSkipsButNoFailures:
    def test_a_run_that_only_skips_still_exits_zero(self, tmp_path):
        """The deliberate difference from fleet-evals: this REPORTS, it does not gate."""
        _write(tmp_path, _MIXED_FILES)
        proc = _run_pytest(tmp_path, with_report=True)
        control = _run_pytest(tmp_path, with_report=False)
        assert proc.returncode == control.returncode == 0
        assert "WHAT DID NOT RUN" in proc.stdout
        assert "it does not change" in proc.stdout


class TestSilenceWhenThereIsNothingToSay:
    def test_a_run_with_no_skips_prints_no_report(self, tmp_path):
        _write(tmp_path, _NO_SKIPS_AT_ALL)
        proc = _run_pytest(tmp_path, with_report=True)
        control = _run_pytest(tmp_path, with_report=False)
        assert proc.returncode == control.returncode == 0
        assert "WHAT DID NOT RUN" not in proc.stdout
        assert proc.stdout.rstrip().endswith(control.stdout.rstrip().splitlines()[-1])


class TestTheOffSwitch:
    def test_the_report_can_be_silenced_without_changing_the_exit_code(
        self, tmp_path
    ):
        _write(tmp_path, _MIXED_WITH_A_FAILURE)
        proc = _run_pytest(
            tmp_path, with_report=True, env_extra={"GUARDKIT_SKIP_REPORT": "off"}
        )
        assert "WHAT DID NOT RUN" not in proc.stdout
        assert proc.returncode == 1


class TestTheBlockFitsWhatAReceiptKeeps:
    """The block must stay inside the 4,000 characters a receipt keeps.

    Measured on the real suite (1,390 skips, 2026-08-23): the first draft came
    to 4,716 characters, so its headline and its most important section fell
    outside the window — invisible in exactly the artefact people read. The
    module now fits the block to a budget instead of hoping it is short enough,
    and these tests hold it to that under far worse conditions than the real
    suite produces.
    """

    @staticmethod
    def _flood(report_module, files=200, reasons=400, per_reason=7):
        for n in range(files):
            report_module.pytest_collectreport(
                _FakeReport(
                    f"tests/a/very/long/path/that/goes/on/test_module_{n:04d}.py",
                    f"Skipped: could not import 'package_number_{n:04d}': "
                    "No module named 'something quite long indeed'",
                )
            )
            report_module.pytest_collectreport(
                _FakeReport(
                    f"tests/b/another/long/path/test_decided_{n:04d}.py",
                    "Skipped: a written decision with a long explanation attached "
                    f"to it, number {n}, going on at some length",
                )
            )
        for r in range(reasons):
            for t in range(per_reason):
                report_module.pytest_runtest_logreport(
                    _FakeReport(
                        f"tests/c/test_thing_{r:04d}.py::test_case_{t}",
                        f"Skipped: reason number {r} which is fairly long and "
                        "descriptive so it eats into the budget nicely",
                    )
                )

    def test_a_huge_number_of_skips_still_fits_the_receipt_window(
        self, isolated_report
    ):
        self._flood(isolated_report)
        block = "\n".join(isolated_report.build_report_lines())
        assert len(block) <= isolated_report.TAIL_BUDGET_CHARS, (
            f"the block grew to {len(block)} characters, past the "
            f"{isolated_report.TAIL_BUDGET_CHARS} budget, so a 4,000-character "
            "receipt would cut the top off it"
        )

    def test_the_totals_are_the_last_thing_in_the_block_whatever_is_dropped(
        self, isolated_report
    ):
        """Even a brutal truncation must leave a reader the counts."""
        self._flood(isolated_report)
        lines = isolated_report.build_report_lines()
        assert lines[-1].startswith("=")
        assert "in total. Exit code unchanged." in lines[-2]
        assert lines[-3].startswith("IN ONE LINE:")

    def test_detail_is_given_up_in_order_reasons_before_whole_files(
        self, isolated_report
    ):
        """A file that never ran at all outranks the tail of a reason list.

        Whole-file skips are the category that hid the ``select_harness(cwd=)``
        defect for eleven weeks, so they are the last thing the fitter drops.
        """
        self._flood(isolated_report)
        block = "\n".join(isolated_report.build_report_lines())
        assert "more reasons" in block, "the reason list should have been trimmed"
        assert "is not installed" in block, "whole-file skips must survive trimming"

    def test_full_mode_prints_everything_and_ignores_the_budget(
        self, isolated_report, monkeypatch
    ):
        self._flood(isolated_report)
        monkeypatch.setenv("GUARDKIT_SKIP_REPORT", "full")
        block = "\n".join(isolated_report.build_report_lines())

        # "Bigger than the budget" is NOT the claim. The docstring promises
        # every file and every reason, and the old assertion passed happily
        # while 360 of 400 reasons were silently dropped — the block was over
        # budget AND truncated at the same time. `full` exists for the person
        # working through the list, which is precisely when a silent cap is
        # worst. Assert the ABSENCE of any "and N more", which is the only
        # thing that distinguishes complete from merely long.
        assert len(block) > isolated_report.TAIL_BUDGET_CHARS
        assert "more reasons" not in block, (
            "full mode dropped reasons:\n" + block[-600:]
        )
        assert "more file" not in block, (
            "full mode dropped files:\n" + block[-600:]
        )


class TestFilesAreGroupedByThePackageTheyWereWaitingFor:
    def test_four_files_waiting_on_one_package_are_named_together(
        self, isolated_report
    ):
        for name in ("alpha", "beta", "gamma", "delta"):
            isolated_report.pytest_collectreport(
                _FakeReport(
                    f"tests/orchestrator/test_{name}.py",
                    "Skipped: could not import 'claude_agent_sdk': No module "
                    "named 'mcp.types'",
                )
            )
        block = "\n".join(isolated_report.build_report_lines())
        assert "claude_agent_sdk is not installed — 4 files did not run:" in block

    def test_an_unrecognised_wording_still_names_the_files(self, isolated_report):
        """If pytest rewords importorskip, nothing disappears — it reads worse."""
        isolated_report.pytest_collectreport(
            _FakeReport("tests/test_x.py", "Skipped: could not import wibble")
        )
        block = "\n".join(isolated_report.build_report_lines())
        assert "tests/test_x.py" in block


class TestTheReportCanNeverTurnARunRed:
    """An exception out of ``pytest_unconfigure`` is an INTERNALERROR — exit 3.

    That would mean a bug in a REPORT could fail a passing run, which is the one
    thing this module must not be able to do.
    """

    class _RefusesUnicode:
        def __init__(self):
            self.written = []

        def write(self, text):
            if any(ord(ch) > 127 for ch in text):
                raise UnicodeEncodeError("ascii", text, 0, 1, "not me")
            self.written.append(text)

        def flush(self):
            pass

    class _RefusesEverything:
        def write(self, text):
            raise ValueError("this stream is closed")

        def flush(self):
            pass

    def test_a_terminal_that_cannot_take_em_dashes_still_gets_the_report(
        self, isolated_report, monkeypatch
    ):
        isolated_report.pytest_runtest_logreport(
            _FakeReport("tests/x.py::test_a", "Skipped: no widget here")
        )
        stream = self._RefusesUnicode()
        monkeypatch.setattr(isolated_report.sys, "stdout", stream)
        isolated_report.pytest_unconfigure(config=None)
        printed = "".join(stream.written)
        assert "WHAT DID NOT RUN" in printed
        assert "no widget here" in printed

    def test_a_stream_that_refuses_everything_raises_nothing(
        self, isolated_report, monkeypatch
    ):
        isolated_report.pytest_runtest_logreport(
            _FakeReport("tests/x.py::test_a", "Skipped: no widget here")
        )
        monkeypatch.setattr(
            isolated_report.sys, "stdout", self._RefusesEverything()
        )
        isolated_report.pytest_unconfigure(config=None)  # must not raise
