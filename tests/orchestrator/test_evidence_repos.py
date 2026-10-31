"""Unit tests for the cross-repo evidence contract (TASK-AB-XREPOEV01).

Covers the single-source-of-truth module that lets the autobuild evidence
loop widen its boundary to declared sibling repos:

- repo-qualified path scheme (qualify / split_qualified / resolve)
- declaration parsing & resolution (string and mapping forms; AC-003)
- per-repo git baseline + diff (real temp git repos)
- independent per-repo tests (AC-002; absent-signal vs pass/fail)
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from guardkit.orchestrator import evidence_repos as ev

# An absolute interpreter: a machine need not have a bare ``python`` on PATH
# (this one has only ``python3``), and these tests are about exit codes.
_PY = shlex.quote(sys.executable)


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


def _run_sibling(repo: "ev.EvidenceRepo", tmp_path: Path):
    """Run one sibling repository's tests the way the reviewer's check does:
    through the validator's shared declared-command path (31 October 2026;
    ``evidence_repos.run_repo_tests`` was removed with its own launch)."""
    from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator

    worktree = tmp_path / "worktree"
    worktree.mkdir(exist_ok=True)
    return CoachValidator(str(worktree), evidence_repos=[repo])._run_sibling_tests(repo)


class TestRunRepoTests:
    # The sibling's run now returns the same result as the task's own parts
    # (31 October 2026), so these read ``check_could_not_run`` /
    # ``tests_passed`` / ``exit_code`` where they read ``ran`` / ``passed`` /
    # ``returncode``; what each case expects is unchanged.

    def test_no_command_is_absent_not_pass(self, tmp_path):
        repo = ev.EvidenceRepo(name="r", root=tmp_path)
        result = _run_sibling(repo, tmp_path)
        assert result.check_could_not_run is True
        assert result.tests_passed is False  # absent signal != pass
        # Was "UNVERIFIED": the sentence now says what is missing, in the
        # words the task's own parts use.
        assert "nothing declared" in result.test_output_summary

    def test_passing_command(self, tmp_path):
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command=f"{_PY} -c 'import sys; sys.exit(0)'"
        )
        result = _run_sibling(repo, tmp_path)
        assert result.check_could_not_run is False
        assert result.tests_passed is True
        assert result.exit_code == 0

    def test_failing_command(self, tmp_path):
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command=f"{_PY} -c 'import sys; sys.exit(1)'"
        )
        result = _run_sibling(repo, tmp_path)
        assert result.check_could_not_run is False
        assert result.tests_passed is False
        assert result.exit_code == 1

    def test_command_runs_in_repo_root(self, tmp_path):
        marker = tmp_path / "marker.txt"
        marker.write_text("hi\n")
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command="test -f marker.txt"
        )
        result = _run_sibling(repo, tmp_path)
        assert result.tests_passed is True

    def test_a_compound_command_runs_through_the_shell(self, tmp_path):
        # Replaces test_pytest_command_pinned_to_resolved_interpreter and
        # test_non_pytest_command_runs_via_shell (31 October 2026): the
        # command is no longer split into an argument list and rewritten,
        # so shell syntax means what it says.
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path,
            test_command="true && echo compound > compound.txt",
        )
        result = _run_sibling(repo, tmp_path)
        assert result.tests_passed is True
        assert (tmp_path / "compound.txt").read_text().strip() == "compound"

    def test_a_missing_program_is_could_not_run(self, tmp_path):
        # The same missing-program look-up as the task's own parts.
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command="no-such-program-7f3a --run"
        )
        result = _run_sibling(repo, tmp_path)
        assert result.check_could_not_run is True
        assert "no-such-program-7f3a" in result.check_could_not_run_detail
        assert "sibling repository r" in result.check_could_not_run_detail

    def test_the_short_private_tmpdir_is_given(self, tmp_path):
        # The same environment rules as the task's own parts: a TMPDIR of the
        # short private gk-<hex> form under the short root (a socket path
        # must fit).
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command='echo "$TMPDIR" > tmpdir.txt'
        )
        result = _run_sibling(repo, tmp_path)
        assert result.tests_passed is True
        from guardkit.orchestrator import project_command_env

        tmpdir = Path((tmp_path / "tmpdir.txt").read_text().strip())
        assert tmpdir.parent == Path(project_command_env.SHORT_TMP_ROOT), tmpdir
        assert tmpdir.name.startswith("gk-"), tmpdir


# ---------------------------------------------------------------------------
# No interpreter is looked for or put first (31 October 2026)
# ---------------------------------------------------------------------------


def _make_fake_interpreter(path: Path, marker_line: str = "pinned") -> Path:
    """Create an executable shell script standing in for a program.

    When executed with ``cwd=repo.root`` it writes ``ran_by.txt`` naming
    itself, so tests can assert WHICH program actually ran.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'#!/bin/sh\necho "{marker_line} $0" > ran_by.txt\nexit 0\n')
    path.chmod(0o755)
    return path


class TestNoInterpreterIsLookedFor:
    # TestResolveRepoInterpreter and TestRunRepoTestsInterpreterResolution
    # kept the implicit choice of a sibling's ``.venv`` and the rewriting of
    # ``python`` and ``pytest`` commands. Both were removed on 31 October 2026
    # (no hidden Python defaults): a declared command means what it says,
    # whatever folders the sibling holds. These replace them.

    def test_a_sibling_venv_is_not_put_in_front_of_a_bare_command(
        self, tmp_path, monkeypatch
    ):
        # Was test_probes_sibling_venv_when_no_explicit and
        # test_bare_python_command_runs_under_sibling_venv: the sibling's
        # .venv was found and the bare command ran under it.
        _make_fake_interpreter(tmp_path / ".venv" / "bin" / "pytest", "venv")
        _make_fake_interpreter(tmp_path / ".venv" / "bin" / "python", "venv")
        bin_dir = tmp_path / "on-path"
        _make_fake_interpreter(bin_dir / "pytest", "path")
        monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
        repo = ev.EvidenceRepo(name="r", root=tmp_path, test_command="pytest -q")
        result = _run_sibling(repo, tmp_path)
        assert result.tests_passed is True
        ran_by = (tmp_path / "ran_by.txt").read_text()
        assert ran_by.startswith("path "), ran_by
        assert ".venv" not in ran_by

    def test_an_interpreter_the_command_names_is_the_one_that_runs(self, tmp_path):
        # Choosing an interpreter is the declaration's job: named in the
        # command, it runs, exactly as declared.
        _make_fake_interpreter(tmp_path / ".venv" / "bin" / "python", "venv")
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command=".venv/bin/python -m pytest -q"
        )
        result = _run_sibling(repo, tmp_path)
        assert result.tests_passed is True
        assert (tmp_path / "ran_by.txt").read_text().startswith("venv ")

    def test_a_declared_interpreter_field_is_reported_not_applied(self, tmp_path):
        # Was test_explicit_*: an ``interpreter:`` field rewrote the command.
        # It is no longer applied, and a repo that still declares one is told
        # so instead of running under an interpreter it did not ask for.
        interp = _make_fake_interpreter(tmp_path / "custom" / "python")
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command="python -m pytest -q",
            interpreter=str(interp),
        )
        result = _run_sibling(repo, tmp_path)
        assert result.check_could_not_run is True
        assert "interpreter" in result.check_could_not_run_detail
        assert not (tmp_path / "ran_by.txt").exists()

    def test_the_interpreter_helpers_are_gone(self):
        assert not hasattr(ev, "_resolve_repo_interpreter")
        assert not hasattr(ev, "_build_repo_test_argv")
        assert not hasattr(ev, "probe_worktree_venv")


# ---------------------------------------------------------------------------
# A sibling's exit code is its verdict (31 October 2026: pytest's collection
# import-error output is no longer read as "never ran")
# ---------------------------------------------------------------------------


class TestASiblingsExitCodeIsItsVerdict:
    def test_exit2_with_an_import_error_is_ran_and_failed(self, tmp_path):
        script = tmp_path / "fail_collect.py"
        script.write_text(
            "import sys\n"
            "sys.stderr.write(\"ModuleNotFoundError: No module named 'x'\\n\")\n"
            "sys.exit(2)\n"
        )
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command=f"{_PY} fail_collect.py"
        )
        result = _run_sibling(repo, tmp_path)
        assert result.check_could_not_run is False
        assert result.tests_passed is False
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# A sibling the task changed is judged like a part (31 October 2026)
# ---------------------------------------------------------------------------
#
# TestBlockingReason tested ``evidence_repo_tests_blocking_reason``, the
# separate sibling gate, which was removed: it let a timeout and a check that
# could not run through to the reviewer and approval
# (test_declared_but_unrunnable_does_not_block and test_no_command_does_not_block
# kept exactly that). A sibling the task changed is now one more part of the
# task's check, combined with its own parts: a failure or a timeout goes back
# to the builder, a check that could not run stops the task, and only a pass
# allows approval. A sibling the task did not change runs nothing, as a part
# the task did not change runs nothing.


class _Task:
    """A worktree whose own root declares a passing test, and one sibling
    repository, both real git repositories with a starting commit."""

    def __init__(self, tmp_path: Path, test_command, *, timeout=None, changed=True):
        self.worktree = tmp_path / "worktree"
        _init_repo(self.worktree)
        (self.worktree / "README.md").write_text("product\n")
        self.base = _commit_all(self.worktree)
        self.sibling = tmp_path / "sibling"
        _init_repo(self.sibling)
        (self.sibling / "lib.txt").write_text("v1\n")
        self.sibling_base = _commit_all(self.sibling)
        if changed:
            (self.sibling / "lib.txt").write_text("v2\n")
        self.repo = ev.EvidenceRepo(
            name="sibling", root=self.sibling.resolve(), test_command=test_command
        )
        self.timeout = timeout

    def validator(self, baselines=True, toolchain_test="true"):
        from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
        from guardkit.orchestrator.toolchain_declaration import ToolchainDeclaration

        return CoachValidator(
            str(self.worktree),
            test_timeout=self.timeout,
            evidence_repos=[self.repo],
            toolchain=ToolchainDeclaration(test=toolchain_test),
            baseline_commit=self.base,
            evidence_baselines=(
                {str(self.sibling): self.sibling_base} if baselines else None
            ),
        )

    def check(self, **kw):
        return self.validator(**kw).run_changed_parts()


class TestASiblingIsJudgedLikeAPart:
    def test_a_passing_sibling_allows_approval(self, tmp_path):
        result = _Task(tmp_path, "true").check()
        assert result.tests_passed is True
        assert result.signal_absent is False
        assert result.parts == [
            {
                "part": "sibling repository sibling",
                "folder": str((tmp_path / "sibling").resolve()),
                "command": "true",
                "outcome": "passed",
                "repository": "sibling",
            }
        ]

    def test_a_failing_sibling_goes_back_to_the_builder(self, tmp_path):
        # Was test_ran_and_failed_blocks: still a failure the builder is sent.
        result = _Task(tmp_path, "exit 3").check()
        assert result.tests_passed is False
        assert result.check_could_not_run is False
        assert result.failure_receipt() is not None
        assert result.exit_code == 3

    def test_a_timeout_is_a_failure_sent_to_the_builder(self, tmp_path):
        # Was "timed out ... ran=False", which sent nothing back.
        result = _Task(tmp_path, "sleep 10", timeout=1).check()
        assert result.tests_passed is False
        assert result.check_could_not_run is False
        assert result.signal_absent is False
        assert "timed out" in result.test_output_summary
        assert "sibling repository sibling" in result.test_output_summary
        assert result.failure_receipt() is not None

    def test_nothing_declared_stops_the_task(self, tmp_path):
        # Was test_no_command_does_not_block.
        result = _Task(tmp_path, None).check()
        assert result.check_could_not_run is True
        assert "nothing declared" in result.check_could_not_run_detail
        assert "sibling" in result.check_could_not_run_detail

    def test_a_program_that_is_not_there_stops_the_task(self, tmp_path):
        # Was test_declared_but_unrunnable_does_not_block.
        result = _Task(tmp_path, "no-such-program-7f3a").check()
        assert result.check_could_not_run is True
        assert "no-such-program-7f3a" in result.check_could_not_run_detail

    def test_a_failure_anywhere_wins_over_a_sibling_that_could_not_run(
        self, tmp_path
    ):
        task = _Task(tmp_path, None)
        (task.worktree / "README.md").write_text("changed\n")
        result = task.check(toolchain_test="exit 1")
        assert result.tests_passed is False
        assert result.check_could_not_run is False
        outcomes = {r["part"]: r["outcome"] for r in result.parts}
        assert outcomes == {
            "root": "failed",
            "sibling repository sibling": "could not run",
        }

    def test_a_sibling_the_task_did_not_change_runs_nothing(self, tmp_path):
        # Even one with nothing declared: it is not part of this task.
        result = _Task(tmp_path, None, changed=False).check()
        assert result.check_could_not_run is False
        assert result.tests_passed is False
        assert result.signal_absent is True
        assert result.test_command == "skipped"

    def test_a_commit_since_the_start_counts_as_a_change(self, tmp_path):
        task = _Task(tmp_path, "exit 1", changed=False)
        (task.sibling / "lib.txt").write_text("v3\n")
        _commit_all(task.sibling)
        result = task.check()
        assert result.failure_receipt() is not None

    def test_an_unknown_starting_commit_is_tested(self, tmp_path):
        # Without its starting commit the sibling cannot be shown unchanged.
        result = _Task(tmp_path, "exit 1", changed=False).check(baselines=False)
        assert result.failure_receipt() is not None

    def test_the_separate_gate_is_gone(self):
        assert not hasattr(ev, "evidence_repo_tests_blocking_reason")
        assert not hasattr(ev, "EvidenceTestResult")
        assert not hasattr(ev, "run_repo_tests")
