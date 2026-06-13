"""Unit tests for the cross-repo evidence contract (TASK-AB-XREPOEV01).

Covers the single-source-of-truth module that lets the autobuild evidence
loop widen its boundary to declared sibling repos:

- repo-qualified path scheme (qualify / split_qualified / resolve)
- declaration parsing & resolution (string and mapping forms; AC-003)
- per-repo git baseline + diff (real temp git repos)
- independent per-repo tests (AC-002; absent-signal vs pass/fail)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator import evidence_repos as ev


# ---------------------------------------------------------------------------
# git fixture helpers
# ---------------------------------------------------------------------------


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "t@t"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "t"],
        check=True,
        capture_output=True,
    )


def _commit_all(path: Path, message: str = "c") -> str:
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", message, "--allow-empty"],
        check=True,
        capture_output=True,
    )
    out = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


# ---------------------------------------------------------------------------
# repo-qualified path scheme
# ---------------------------------------------------------------------------


class TestQualifiedPathScheme:
    def test_qualify_roundtrip(self):
        q = ev.qualify("guardkitfactory", "src/foo.py")
        assert q == "guardkitfactory:src/foo.py"
        assert ev.split_qualified(q) == ("guardkitfactory", "src/foo.py")

    def test_qualify_normalises_leading_dot_slash_and_backslashes(self):
        assert ev.qualify("repo", "./a/b.py") == "repo:a/b.py"
        assert ev.qualify("repo", "a\\b.py") == "repo:a/b.py"

    def test_qualify_rejects_bad_repo_name(self):
        with pytest.raises(ValueError):
            ev.qualify("bad/name", "x.py")

    def test_split_returns_none_for_ordinary_path(self):
        assert ev.split_qualified("src/foo.py") is None
        assert ev.split_qualified("foo.py") is None

    def test_split_does_not_misfire_on_colon_after_separator(self):
        # The colon is past a path separator, so the prefix is not a bare token.
        assert ev.split_qualified("dir/weird:name.py") is None

    def test_split_requires_nonempty_halves(self):
        assert ev.split_qualified(":x") is None
        assert ev.split_qualified("repo:") is None

    def test_is_qualified(self):
        assert ev.is_qualified("guardkitfactory:src/a.py") is True
        assert ev.is_qualified("src/a.py") is False

    def test_resolve_qualified_path_known_repo(self, tmp_path):
        repo = ev.EvidenceRepo(name="guardkitfactory", root=tmp_path / "gkf")
        resolved = ev.resolve_qualified_path("guardkitfactory:src/a.py", [repo])
        assert resolved == tmp_path / "gkf" / "src/a.py"

    def test_resolve_qualified_path_unknown_repo_is_fail_open(self, tmp_path):
        # path-string-mismatch rule: unknown repo -> None (caller fails open),
        # never a fabricated path / false-red.
        repo = ev.EvidenceRepo(name="guardkitfactory", root=tmp_path / "gkf")
        assert ev.resolve_qualified_path("otherrepo:src/a.py", [repo]) is None

    def test_resolve_qualified_path_ordinary_path(self, tmp_path):
        repo = ev.EvidenceRepo(name="guardkitfactory", root=tmp_path / "gkf")
        assert ev.resolve_qualified_path("src/a.py", [repo]) is None


# ---------------------------------------------------------------------------
# declaration parsing & resolution (AC-003)
# ---------------------------------------------------------------------------


class TestResolveEvidenceRepos:
    def test_empty_declaration_yields_empty(self, tmp_path):
        assert ev.resolve_evidence_repos(None, tmp_path) == []
        assert ev.resolve_evidence_repos([], tmp_path) == []

    def test_relative_string_resolves_against_base(self, tmp_path):
        base = tmp_path / "guardkit"
        base.mkdir()
        sibling = tmp_path / "guardkitfactory"
        sibling.mkdir()

        repos = ev.resolve_evidence_repos(["../guardkitfactory"], base)
        assert len(repos) == 1
        assert repos[0].name == "guardkitfactory"
        assert repos[0].root == sibling.resolve()
        assert repos[0].test_command is None

    def test_mapping_form_carries_test_command(self, tmp_path):
        base = tmp_path / "guardkit"
        base.mkdir()
        sibling = tmp_path / "guardkitfactory"
        sibling.mkdir()

        repos = ev.resolve_evidence_repos(
            [{"path": "../guardkitfactory", "test_command": "pytest -q tests/"}],
            base,
        )
        assert len(repos) == 1
        assert repos[0].test_command == "pytest -q tests/"

    def test_missing_path_is_skipped_not_invented(self, tmp_path):
        # AC-003: a declared path that does not exist is dropped (absent),
        # never synthesised into a phantom repo.
        base = tmp_path / "guardkit"
        base.mkdir()
        repos = ev.resolve_evidence_repos(["../does-not-exist"], base)
        assert repos == []

    def test_malformed_entry_is_ignored(self, tmp_path):
        base = tmp_path / "guardkit"
        base.mkdir()
        repos = ev.resolve_evidence_repos([123, {"no_path": "x"}], base)
        assert repos == []

    def test_duplicate_roots_deduplicated(self, tmp_path):
        base = tmp_path / "guardkit"
        base.mkdir()
        sibling = tmp_path / "guardkitfactory"
        sibling.mkdir()
        repos = ev.resolve_evidence_repos(
            ["../guardkitfactory", "../guardkitfactory"], base
        )
        assert len(repos) == 1

    def test_absolute_path_is_honoured(self, tmp_path):
        base = tmp_path / "guardkit"
        base.mkdir()
        sibling = tmp_path / "guardkitfactory"
        sibling.mkdir()
        repos = ev.resolve_evidence_repos([str(sibling)], base)
        assert len(repos) == 1
        assert repos[0].root == sibling.resolve()


# ---------------------------------------------------------------------------
# per-repo git baseline + diff
# ---------------------------------------------------------------------------


class TestRepoGitEvidence:
    def test_baseline_and_diff_detects_modified_and_created(self, tmp_path):
        repo_root = tmp_path / "guardkitfactory"
        _init_repo(repo_root)
        (repo_root / "src").mkdir()
        (repo_root / "src" / "existing.py").write_text("x = 1\n")
        _commit_all(repo_root)

        repo = ev.EvidenceRepo(name="guardkitfactory", root=repo_root)
        baseline = ev.record_repo_baseline(repo)
        assert baseline is not None and len(baseline) == 40

        # Modify a tracked file and create a new untracked one.
        (repo_root / "src" / "existing.py").write_text("x = 2\n")
        (repo_root / "src" / "new.py").write_text("y = 3\n")

        changes = ev.detect_repo_changes(repo, baseline)
        assert "guardkitfactory:src/existing.py" in changes.modified
        assert "guardkitfactory:src/new.py" in changes.created
        assert set(changes.all_qualified) == {
            "guardkitfactory:src/existing.py",
            "guardkitfactory:src/new.py",
        }

    def test_baseline_excludes_pre_existing_commits(self, tmp_path):
        # A task that touches nothing in the repo yields no changes even though
        # the repo has prior history (per-task attribution, AC-003-adjacent).
        repo_root = tmp_path / "guardkitfactory"
        _init_repo(repo_root)
        (repo_root / "a.py").write_text("1\n")
        _commit_all(repo_root)
        repo = ev.EvidenceRepo(name="guardkitfactory", root=repo_root)
        baseline = ev.record_repo_baseline(repo)

        changes = ev.detect_repo_changes(repo, baseline)
        assert changes.modified == []
        assert changes.created == []

    def test_non_git_dir_yields_empty_changes(self, tmp_path):
        repo_root = tmp_path / "plain"
        repo_root.mkdir()
        repo = ev.EvidenceRepo(name="plain", root=repo_root)
        assert ev.record_repo_baseline(repo) is None
        changes = ev.detect_repo_changes(repo, None)
        assert changes.modified == []
        assert changes.created == []

    def test_detect_all_and_flatten(self, tmp_path):
        repo_root = tmp_path / "guardkitfactory"
        _init_repo(repo_root)
        (repo_root / "a.py").write_text("1\n")
        _commit_all(repo_root)
        repo = ev.EvidenceRepo(name="guardkitfactory", root=repo_root)
        baselines = ev.record_repo_baselines([repo])
        (repo_root / "b.py").write_text("2\n")

        all_changes = ev.detect_all_repo_changes([repo], baselines)
        modified, created = ev.qualified_paths_for_changes(all_changes)
        assert created == ["guardkitfactory:b.py"]
        assert modified == []


# ---------------------------------------------------------------------------
# independent per-repo tests (AC-002)
# ---------------------------------------------------------------------------


class TestRunRepoTests:
    def test_no_command_is_absent_not_pass(self, tmp_path):
        repo = ev.EvidenceRepo(name="r", root=tmp_path)
        result = ev.run_repo_tests(repo)
        assert result.ran is False
        assert result.passed is False  # absent signal != pass
        assert "UNVERIFIED" in result.output_summary

    def test_passing_command(self, tmp_path):
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command="python -c 'import sys; sys.exit(0)'"
        )
        result = ev.run_repo_tests(repo)
        assert result.ran is True
        assert result.passed is True
        assert result.returncode == 0

    def test_failing_command(self, tmp_path):
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command="python -c 'import sys; sys.exit(1)'"
        )
        result = ev.run_repo_tests(repo)
        assert result.ran is True
        assert result.passed is False
        assert result.returncode == 1

    def test_command_runs_in_repo_root(self, tmp_path):
        marker = tmp_path / "marker.txt"
        marker.write_text("hi\n")
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command="test -f marker.txt"
        )
        result = ev.run_repo_tests(repo)
        assert result.passed is True

    def test_pytest_command_pinned_to_venv_python(self, tmp_path):
        # When venv_python is given and command is bare pytest, argv is pinned.
        argv, shell = ev._build_repo_test_argv("pytest -q tests/", "/venv/bin/python")
        assert shell is False
        assert argv == ["/venv/bin/python", "-m", "pytest", "-q", "tests/"]

    def test_non_pytest_command_runs_via_shell(self, tmp_path):
        argv, shell = ev._build_repo_test_argv("make test", "/venv/bin/python")
        assert shell is True
        assert argv == "make test"

    def test_result_to_dict_shape(self, tmp_path):
        repo = ev.EvidenceRepo(name="r", root=tmp_path, test_command="true")
        d = ev.run_repo_tests(repo).to_dict()
        assert set(d) == {
            "repo_name",
            "command",
            "ran",
            "passed",
            "returncode",
            "output_summary",
        }


# ---------------------------------------------------------------------------
# blocking classifier (AC-002 gate semantics)
# ---------------------------------------------------------------------------


class TestBlockingReason:
    def _result(self, **kw):
        base = dict(
            repo_name="r", command="pytest", ran=True, passed=True, returncode=0,
            output_summary="",
        )
        base.update(kw)
        return ev.EvidenceTestResult(**base)

    def test_all_passing_does_not_block(self):
        results = [self._result(passed=True)]
        assert ev.evidence_repo_tests_blocking_reason(results) is None

    def test_ran_and_failed_blocks(self):
        results = [self._result(passed=False, returncode=1)]
        reason = ev.evidence_repo_tests_blocking_reason(results)
        assert reason is not None
        assert "FAILED" in reason
        assert "r:" in reason

    def test_declared_but_unrunnable_blocks(self):
        # absence-of-failure: a declared command that could not run is NOT a
        # silent pass.
        results = [self._result(ran=False, passed=False, returncode=None,
                                 output_summary="boom")]
        reason = ev.evidence_repo_tests_blocking_reason(results)
        assert reason is not None
        assert "could NOT run" in reason

    def test_no_command_does_not_block(self):
        # A repo with no declared command is out of scope, not a failure.
        results = [self._result(command=None, ran=False, passed=False,
                                 returncode=None)]
        assert ev.evidence_repo_tests_blocking_reason(results) is None

    def test_empty_results_do_not_block(self):
        assert ev.evidence_repo_tests_blocking_reason([]) is None
