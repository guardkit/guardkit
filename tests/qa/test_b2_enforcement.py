"""WS2-B2 gate: tier-1 QA enforcement refusals FIRE, and a correctly-formatted
repo PASSES.

Covers the three B2 refusals (all flag-gated on ``qa.enforce_tier1``, default
OFF):

1. Post-merge known-failure ledger sweep (F2).
2. Coach task-start pinned-pass-bar precondition (F1).
3. feature-complete runtime-surface / registered-green-gate refusal (F1 + F4).

Both fixture repos' committed exemplar instances (lpa-platform-poc, study-tutor)
are exercised as the "correctly-formatted repo passes" bar. An ST-05 mutation
tripwire proves the ledger diff is load-bearing: break the diff and reds appear.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from guardkit.qa.enforcement import (
    ENFORCE_ENV,
    LEDGER_RELPATH,
    check_pass_bar_precondition,
    check_plan_does_not_author_ledger,
    check_runtime_surface_gate,
    diff_failures_against_ledger,
    git_changed_paths,
    is_tier1_enforced,
    parse_pytest_outcome,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "qa_formats"
LPA = FIXTURES / "lpa-platform-poc"
STUDY = FIXTURES / "study-tutor"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    (path / "seed.txt").write_text("seed\n")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "seed")
    return path


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _write_pass_bar(path: Path, task_id: str, sha: str, *, auth: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if auth:
        neg = [
            "wrong_credential",
            "anonymous_deep_link",
            "post_logout_401",
            "unauthorized_403_ui",
            "dependency_down_degradation",
        ]
        evidence = "screenshot"
    else:
        neg = ["dependency_down_degradation"]
        evidence = "json"
    neg_block = "\n".join(f"  - {p}" for p in neg)
    path.write_text(
        f"""format_version: "2.0"
task_id: {task_id}
registered_at:
  sha: {sha}
  date: "2026-07-08"
auth_surface_bearing: {"true" if auth else "false"}
preconditions:
  - suite_green_vs_ledger
criteria:
  - id: AC-1
    text: "does the thing"
    class: machine
    evidence_kind: {evidence}
negative_paths:
{neg_block}
"""
    )


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
# 1. Ledger sweep (F2)
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

    def test_stale_unconditional_entry_fails(self, tmp_path):
        # An unconditional known-failure that did NOT fail this green run.
        ledger = self._ledger(
            tmp_path,
            "  - test_id: tests/a.py::test_x\n"
            "    reason: was flaky\n"
            "    since: {date: \"2026-07-01\", sha: abcd}\n"
            "    owner: rich\n    review_by: \"2026-08-01\"\n",
        )
        out = "120 passed in 3s\n"
        res = diff_failures_against_ledger(parse_pytest_outcome(out), ledger)
        assert res.status == "fail"
        assert res.stale_ledger_entries == ("tests/a.py::test_x",)

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

    def test_malformed_ledger_is_error(self, tmp_path):
        p = tmp_path / "known-failures.yaml"
        p.write_text("format_version: \"1.0\"\nsuite_id: s\n")  # missing required
        out = "1 failed, 5 passed\nFAILED tests/a.py::test_x - boom\n"
        res = diff_failures_against_ledger(parse_pytest_outcome(out), p)
        assert res.status == "error"

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
# 2. Coach task-start precondition (F1)
# ---------------------------------------------------------------------------


class TestPassBarPrecondition:
    def test_missing_bar_refuses(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        res = check_pass_bar_precondition(repo, "TASK-XYZ")
        assert res.passed is False
        assert "no pinned F1 pass bar" in res.detail

    def test_valid_bar_predating_head_passes(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        pinned_sha = _head(repo)  # commit that predates implementation
        _write_pass_bar(
            repo / "qa" / "pass-bar-TASK-XYZ.yaml", "TASK-XYZ", pinned_sha
        )
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "pin pass bar")
        # Now some later "implementation" commit.
        (repo / "impl.py").write_text("x = 1\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "impl")
        res = check_pass_bar_precondition(repo, "TASK-XYZ")
        assert res.passed is True, res.detail

    def test_sha_not_ancestor_refuses(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        # A syntactically valid sha that is not in this repo's history.
        _write_pass_bar(
            repo / "qa" / "pass-bar-TASK-XYZ.yaml",
            "TASK-XYZ",
            "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        )
        res = check_pass_bar_precondition(repo, "TASK-XYZ")
        assert res.passed is False
        assert "not a commit" in res.detail

    def test_future_sha_not_ancestor_refuses(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        _write_pass_bar(repo / "qa" / "pass-bar-TASK-XYZ.yaml", "TASK-XYZ", "PLACEHOLD")
        # Make a NEW commit that the bar will point at (registered AFTER impl).
        (repo / "later.py").write_text("y = 2\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "later")
        later = _head(repo)
        # Now rewrite the bar to point at `later`, but check against an earlier
        # HEAD by making the current HEAD a sibling (detach to seed).
        _write_pass_bar(repo / "qa" / "pass-bar-TASK-XYZ.yaml", "TASK-XYZ", later)
        # Reset HEAD back before `later` so `later` is NOT an ancestor of HEAD.
        _git(repo, "reset", "-q", "--hard", "HEAD~1")
        res = check_pass_bar_precondition(repo, "TASK-XYZ")
        assert res.passed is False
        assert "ancestor" in res.detail

    def test_task_id_mismatch_refuses(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        sha = _head(repo)
        _write_pass_bar(repo / "qa" / "pass-bar-TASK-XYZ.yaml", "TASK-OTHER", sha)
        res = check_pass_bar_precondition(repo, "TASK-XYZ")
        assert res.passed is False
        assert "mismatched" in res.detail or "task_id" in res.detail

    def test_invalid_bar_refuses(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        bad = repo / "qa" / "pass-bar-TASK-XYZ.yaml"
        bad.parent.mkdir(parents=True)
        bad.write_text("format_version: \"2.0\"\ntask_id: TASK-XYZ\n")  # missing fields
        res = check_pass_bar_precondition(repo, "TASK-XYZ")
        assert res.passed is False
        assert "invalid" in res.detail


# ---------------------------------------------------------------------------
# 3. feature-complete runtime-surface refusal (F1 + F4)
# ---------------------------------------------------------------------------


class TestRuntimeSurfaceGate:
    def _repo_with_registry(self, tmp_path, green: bool) -> Path:
        repo = tmp_path / "repo"
        (repo / "qa" / "gates").mkdir(parents=True)
        last_green = "\n    last_green: {date: \"2026-07-05\", sha: abcd123}" if green else ""
        (repo / "qa" / "gates" / "registry.yaml").write_text(
            "format_version: \"1.0\"\ngates:\n"
            "  - id: live-suite\n"
            "    path: app/test_live\n"
            "    target: {base_url_env: API_BASE_URL, environment_id: env1}\n"
            "    pass_bar_ref: qa/pass-bar-TASK-RT.yaml\n"
            "    evidence_dir_pattern: qa/ev-{date}" + last_green + "\n"
        )
        return repo

    def test_runtime_surface_with_green_gate_passes(self, tmp_path):
        repo = self._repo_with_registry(tmp_path, green=True)
        _write_pass_bar(repo / "qa" / "pass-bar-TASK-RT.yaml", "TASK-RT", "abcd", auth=True)
        res = check_runtime_surface_gate(repo, ["TASK-RT"])
        assert res.passed is True and res.runtime_surface is True

    def test_runtime_surface_without_green_gate_refuses(self, tmp_path):
        repo = self._repo_with_registry(tmp_path, green=False)
        _write_pass_bar(repo / "qa" / "pass-bar-TASK-RT.yaml", "TASK-RT", "abcd", auth=True)
        res = check_runtime_surface_gate(repo, ["TASK-RT"])
        assert res.passed is False and res.runtime_surface is True
        assert "no green gate" in res.detail

    def test_runtime_surface_without_registry_refuses(self, tmp_path):
        repo = tmp_path / "repo"
        _write_pass_bar(repo / "qa" / "pass-bar-TASK-RT.yaml", "TASK-RT", "abcd", auth=True)
        res = check_runtime_surface_gate(repo, ["TASK-RT"])
        assert res.passed is False
        assert "no F4 gate registry" in res.detail

    def test_authless_feature_is_not_applicable(self, tmp_path):
        repo = tmp_path / "repo"
        _write_pass_bar(
            repo / "qa" / "pass-bar-TASK-CLI.yaml", "TASK-CLI", "abcd", auth=False
        )
        res = check_runtime_surface_gate(repo, ["TASK-CLI"])
        assert res.status == "not_applicable"
        assert res.passed is True and res.runtime_surface is False

    def test_no_pass_bar_is_not_applicable(self, tmp_path):
        repo = tmp_path / "repo"
        (repo / "qa").mkdir(parents=True)
        res = check_runtime_surface_gate(repo, ["TASK-NONE"])
        assert res.status == "not_applicable"

    def test_walk_bearing_pass_bar_is_runtime_surface(self, tmp_path):
        repo = self._repo_with_registry(tmp_path, green=True)
        bar = repo / "qa" / "pass-bar-TASK-RT.yaml"
        bar.write_text(
            "format_version: \"2.0\"\ntask_id: TASK-RT\n"
            "registered_at: {sha: abcd, date: \"2026-07-08\"}\n"
            "auth_surface_bearing: false\n"
            "checkpoint_list_ref: qa/walk.yaml\n"
            "preconditions: [suite_green_vs_ledger]\n"
            "criteria:\n  - id: A\n    text: t\n    class: machine\n    evidence_kind: json\n"
            "negative_paths: [dependency_down_degradation]\n"
        )
        res = check_runtime_surface_gate(repo, ["TASK-RT"])
        assert res.runtime_surface is True and res.passed is True

    @pytest.mark.parametrize(
        "src,task_id",
        [
            (LPA, "FEAT-POC-DEMO-0705"),
            (STUDY, "p2-wave-7"),
        ],
    )
    def test_committed_fixture_repo_passes(self, tmp_path, src, task_id):
        """Both fixture repos are correctly formatted: an auth-surface-bearing
        pass bar backed by a registry with green gates PASSES."""
        repo = tmp_path / "repo"
        (repo / "qa" / "gates").mkdir(parents=True)
        # Copy the committed instances into their canonical repo-local paths.
        shutil.copy(src / f"pass-bar-{task_id}.yaml", repo / "qa" / f"pass-bar-{task_id}.yaml")
        shutil.copy(src / "gates-registry.yaml", repo / "qa" / "gates" / "registry.yaml")
        res = check_runtime_surface_gate(repo, [task_id])
        assert res.passed is True, res.detail
        assert res.runtime_surface is True


# ---------------------------------------------------------------------------
# 4. Plan-time ledger-authorship reject-lint (F2 · K15 / LPA-09) — DIM5-F3
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
