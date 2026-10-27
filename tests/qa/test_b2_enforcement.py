"""WS2-B2 gate: tier-1 QA enforcement refusals FIRE, and a correctly-formatted
repo PASSES.

Covers the two remaining refusals (both flag-gated on ``qa.enforce_tier1``,
default OFF):

1. Known-failure ledger sweep at completion (F2): only a test that ran and
   failed and is not in the ledger fails it.
2. Plan-time ledger-authorship reject-lint (F2).

Both fixture repos' committed exemplar instances (lpa-platform-poc, study-tutor)
are exercised as the "correctly-formatted repo passes" bar. An ST-05 mutation
tripwire proves the ledger diff is load-bearing: break the diff and reds appear.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from guardkit.qa.enforcement import (
    ENFORCE_ENV,
    LEDGER_RELPATH,
    check_plan_does_not_author_ledger,
    diff_failures_against_ledger,
    git_changed_paths,
    is_tier1_enforced,
    parse_pytest_outcome,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "qa_formats"
LPA = FIXTURES / "lpa-platform-poc"
STUDY = FIXTURES / "study-tutor"


# ---------------------------------------------------------------------------
# Flag reader
# ---------------------------------------------------------------------------


class TestFlagReader:
    def test_default_off_no_config(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ENFORCE_ENV, raising=False)
        assert is_tier1_enforced(tmp_path) is False

    def test_config_on(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ENFORCE_ENV, raising=False)
        cfg = tmp_path / ".guardkit" / "config.yaml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("qa:\n  enforce_tier1: true\n")
        assert is_tier1_enforced(tmp_path) is True

    def test_config_off_explicit(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ENFORCE_ENV, raising=False)
        cfg = tmp_path / ".guardkit" / "config.yaml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("qa:\n  enforce_tier1: false\n")
        assert is_tier1_enforced(tmp_path) is False

    def test_env_truthy_wins_over_absent_config(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENFORCE_ENV, "1")
        assert is_tier1_enforced(tmp_path) is True

    def test_env_falsy_wins_over_config_on(self, tmp_path, monkeypatch):
        cfg = tmp_path / ".guardkit" / "config.yaml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("qa:\n  enforce_tier1: true\n")
        monkeypatch.setenv(ENFORCE_ENV, "0")
        assert is_tier1_enforced(tmp_path) is False


# ---------------------------------------------------------------------------
# 1. Ledger sweep at completion (F2)
# ---------------------------------------------------------------------------


class TestPytestParsing:
    def test_parses_failed_and_error_and_counts(self):
        out = (
            "FAILED tests/a.py::test_x - AssertionError\n"
            "ERROR tests/b.py::test_y - ImportError\n"
            "2 failed, 10 passed, 1 error in 3s\n"
        )
        o = parse_pytest_outcome(out)
        assert o.ran is True
        assert set(o.failing_ids) == {"tests/a.py::test_x", "tests/b.py::test_y"}
        assert o.passed == 10 and o.failed == 2 and o.errored == 1

    def test_no_summary_is_not_ran(self):
        assert parse_pytest_outcome("nothing here").ran is False


class TestLedgerSweep:
    def _ledger(self, tmp_path, entries: str) -> Path:
        p = tmp_path / "known-failures.yaml"
        p.write_text(
            "format_version: \"1.0\"\n"
            "suite_id: s\nframework: pytest\nlanguage: python\n"
            "expected:\n  passed: 100\n"
            "known_failures:\n" + entries
        )
        return p

    def test_unledgered_failure_fails(self, tmp_path):
        ledger = self._ledger(tmp_path, "  []\n")
        out = "FAILED tests/a.py::test_x - boom\n1 failed, 5 passed\n"
        res = diff_failures_against_ledger(parse_pytest_outcome(out), ledger)
        assert res.status == "fail"
        assert res.unledgered_failures == ("tests/a.py::test_x",)

    def test_ledgered_failure_passes(self, tmp_path):
        ledger = self._ledger(
            tmp_path,
            "  - test_id: tests/a.py::test_x\n"
            "    reason: known flake\n"
            "    since: {date: \"2026-07-01\", sha: abcd}\n"
            "    owner: rich\n    review_by: \"2026-08-01\"\n",
        )
        out = "FAILED tests/a.py::test_x - boom\n1 failed, 5 passed\n"
        res = diff_failures_against_ledger(parse_pytest_outcome(out), ledger)
        assert res.status == "pass", res.detail

    def test_stale_unconditional_entry_does_not_fail(self, tmp_path):
        # An unconditional known-failure that did NOT fail this green run: no
        # test failed, so nothing refuses (the cull, 27 October 2026).
        ledger = self._ledger(
            tmp_path,
            "  - test_id: tests/a.py::test_x\n"
            "    reason: was flaky\n"
            "    since: {date: \"2026-07-01\", sha: abcd}\n"
            "    owner: rich\n    review_by: \"2026-08-01\"\n",
        )
        out = "120 passed in 3s\n"
        res = diff_failures_against_ledger(parse_pytest_outcome(out), ledger)
        assert res.status == "pass", res.detail

    def test_env_conditional_entry_not_stale(self, tmp_path):
        # An env-conditional entry passing on another env is expected, not stale.
        ledger = self._ledger(
            tmp_path,
            "  - test_id: tests/a.py::test_x\n"
            "    reason: local only\n"
            "    env_condition: local dev env only\n"
            "    since: {date: \"2026-07-01\", sha: abcd}\n"
            "    owner: rich\n    review_by: \"2026-08-01\"\n",
        )
        out = "120 passed in 3s\n"
        res = diff_failures_against_ledger(parse_pytest_outcome(out), ledger)
        assert res.status == "pass", res.detail

    def test_absent_signal_is_unverified_never_fail(self, tmp_path):
        ledger = self._ledger(tmp_path, "  []\n")
        res = diff_failures_against_ledger(parse_pytest_outcome("no summary"), ledger)
        assert res.status == "unverified"

    def test_malformed_ledger_is_read_as_empty(self, tmp_path):
        # An unreadable ledger excuses nothing: a real failure still fails,
        # a green run passes (the cull, 27 October 2026).
        p = tmp_path / "known-failures.yaml"
        p.write_text("format_version: \"1.0\"\nsuite_id: s\n")  # missing required
        out = "1 failed, 5 passed\nFAILED tests/a.py::test_x - boom\n"
        res = diff_failures_against_ledger(parse_pytest_outcome(out), p)
        assert res.status == "fail"
        assert res.unledgered_failures == ("tests/a.py::test_x",)
        green = diff_failures_against_ledger(parse_pytest_outcome("5 passed\n"), p)
        assert green.status == "pass"

    def test_missing_ledger_is_empty_ledger(self, tmp_path):
        missing = tmp_path / "known-failures.yaml"
        green = diff_failures_against_ledger(parse_pytest_outcome("50 passed\n"), missing)
        assert green.status == "pass"
        red = diff_failures_against_ledger(
            parse_pytest_outcome("FAILED t.py::x - boom\n1 failed, 5 passed\n"), missing
        )
        assert red.status == "fail"

    def test_unattributable_failure_fails(self, tmp_path):
        # A summary says something failed but no node id surfaced (truncated /
        # collection error) — cannot be excused.
        ledger = self._ledger(tmp_path, "  []\n")
        res = diff_failures_against_ledger(
            parse_pytest_outcome("2 failed, 5 passed in 1s\n"), ledger
        )
        assert res.status == "fail"

    def test_st05_mutation_tripwire(self, tmp_path):
        """ST-05: this pins that the diff is load-bearing. If the un-ledgered
        branch were mutated to treat un-ledgered failures as pass, this test
        goes red — the failure IS un-ledgered and MUST fail."""
        ledger = self._ledger(tmp_path, "  []\n")
        out = "FAILED tests/only.py::test_unknown - boom\n1 failed\n"
        res = diff_failures_against_ledger(parse_pytest_outcome(out), ledger)
        assert res.passed is False
        assert "un-ledgered" in res.detail


class TestLedgerSweepAgainstFixtures:
    @pytest.mark.parametrize("repo", [LPA, STUDY])
    def test_committed_ledger_greens_the_expected_suite(self, repo):
        """A run reporting exactly the ledger's expected outcome passes the
        sweep for both fixture repos' committed instances."""
        ledger = repo / "known-failures.yaml"
        import yaml

        data = yaml.safe_load(ledger.read_text())
        expected = data["expected"]["passed"]
        # Green-ish run: expected passed, only the ledgered (env-conditional /
        # none) failures. Study-tutor ledger is empty; lpa's are env-conditional.
        failing_lines = "".join(
            f"FAILED {e['test_id']} - env\n" for e in data.get("known_failures", [])
        )
        out = f"{failing_lines}{len(data.get('known_failures', []))} failed, {expected} passed in 5s\n"
        res = diff_failures_against_ledger(parse_pytest_outcome(out), ledger)
        assert res.status == "pass", res.detail

    def test_lpa_new_unledgered_failure_fails(self):
        ledger = LPA / "known-failures.yaml"
        out = (
            "FAILED tests/new/test_regression.py::test_boom - AssertionError\n"
            "1 failed, 1021 passed in 5s\n"
        )
        res = diff_failures_against_ledger(parse_pytest_outcome(out), ledger)
        assert res.status == "fail"
        assert "tests/new/test_regression.py::test_boom" in res.unledgered_failures


# ---------------------------------------------------------------------------
# 2. Plan-time ledger-authorship reject-lint (F2 · K15 / LPA-09) — DIM5-F3
# ---------------------------------------------------------------------------


class TestPlanDoesNotAuthorLedger:
    def test_clean_plan_passes(self):
        res = check_plan_does_not_author_ledger(
            [
                ".guardkit/features/FEAT-XYZ.yaml",
                "tasks/backlog/TASK-XYZ-t1.md",
                "features/foo/foo.feature",
            ]
        )
        assert res.passed is True
        assert res.offending_paths == ()

    def test_empty_diff_passes(self):
        assert check_plan_does_not_author_ledger([]).passed is True

    def test_ledger_add_fails(self):
        res = check_plan_does_not_author_ledger(
            [".guardkit/features/FEAT-XYZ.yaml", LEDGER_RELPATH]
        )
        assert res.status == "fail"
        assert res.offending_paths == (LEDGER_RELPATH,)
        assert "human/Coach at triage only" in res.detail
        assert "qa.enforce_tier1 is on" in res.detail

    def test_ledger_leading_dot_slash_fails(self):
        res = check_plan_does_not_author_ledger(["./qa/known-failures.yaml"])
        assert res.status == "fail"
        assert res.offending_paths == (LEDGER_RELPATH,)

    def test_sibling_repo_ledger_fails(self):
        res = check_plan_does_not_author_ledger(
            ["../guardkitfactory/qa/known-failures.yaml"]
        )
        assert res.status == "fail"
        assert res.offending_paths == ("../guardkitfactory/qa/known-failures.yaml",)

    def test_repo_qualified_ledger_fails(self):
        # Evidence-repo qualifier <repo>:<path> resolves to the bare path.
        res = check_plan_does_not_author_ledger(["guardkit:qa/known-failures.yaml"])
        assert res.status == "fail"
        assert res.offending_paths == (LEDGER_RELPATH,)

    def test_similarly_named_file_does_not_fail(self):
        # A different file under qa/ is not the ledger.
        res = check_plan_does_not_author_ledger(
            ["qa/known-failures.yaml.bak", "qa/pass-bar-TASK-X.yaml", "docs/known-failures.md"]
        )
        assert res.passed is True


class TestGitChangedPaths:
    def _stub_git(self, porcelain: str, returncode: int = 0):
        def _run(args):
            return subprocess.CompletedProcess(args, returncode, stdout=porcelain, stderr="")

        return _run

    def test_parses_modified_staged_and_untracked(self, tmp_path):
        porcelain = (
            " M qa/known-failures.yaml\n"
            "A  .guardkit/features/FEAT-X.yaml\n"
            "?? tasks/backlog/TASK-X-t1.md\n"
        )
        paths = git_changed_paths(tmp_path, git_run=self._stub_git(porcelain))
        assert set(paths) == {
            "qa/known-failures.yaml",
            ".guardkit/features/FEAT-X.yaml",
            "tasks/backlog/TASK-X-t1.md",
        }

    def test_rename_takes_destination(self, tmp_path):
        porcelain = "R  qa/old.yaml -> qa/known-failures.yaml\n"
        paths = git_changed_paths(tmp_path, git_run=self._stub_git(porcelain))
        assert paths == ("qa/known-failures.yaml",)

    def test_git_failure_returns_empty(self, tmp_path):
        paths = git_changed_paths(tmp_path, git_run=self._stub_git("", returncode=128))
        assert paths == ()

    def test_git_unavailable_returns_empty(self, tmp_path):
        def _boom(args):
            raise OSError("git not found")

        assert git_changed_paths(tmp_path, git_run=_boom) == ()

    def test_end_to_end_ledger_edit_is_refused(self, tmp_path):
        # git_changed_paths → check_plan_does_not_author_ledger composition.
        porcelain = " M qa/known-failures.yaml\nA  .guardkit/features/FEAT-X.yaml\n"
        res = check_plan_does_not_author_ledger(
            git_changed_paths(tmp_path, git_run=self._stub_git(porcelain))
        )
        assert res.status == "fail"
        assert res.offending_paths == ("qa/known-failures.yaml",)


# ---------------------------------------------------------------------------
# B9 repair pass (2026-09-19): the caller names the candidate, and pass-bar
# references that begin with a dot are compared whole.
# ---------------------------------------------------------------------------


