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

    def test_pytest_command_pinned_to_resolved_interpreter(self, tmp_path):
        # TASK-FIX-SIBTESTENV01: when a per-repo interpreter resolved and the
        # command is bare pytest, argv is pinned to THAT interpreter (the
        # sibling's own environment, never the guardkit worktree venv).
        argv, shell = ev._build_repo_test_argv(
            "pytest -q tests/", "/sibling/.venv/bin/python"
        )
        assert shell is False
        assert argv == ["/sibling/.venv/bin/python", "-m", "pytest", "-q", "tests/"]

    def test_non_pytest_command_runs_via_shell(self, tmp_path):
        # A non-bare-head command runs verbatim via shell even when a
        # per-repo interpreter resolved (TASK-FIX-SIBTESTENV01).
        argv, shell = ev._build_repo_test_argv("make test", "/sibling/.venv/bin/python")
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
# per-repo interpreter resolution (TASK-FIX-SIBTESTENV01)
# ---------------------------------------------------------------------------


def _make_fake_interpreter(path: Path, marker_line: str = "pinned") -> Path:
    """Create an executable shell script standing in for a Python interpreter.

    When executed with ``cwd=repo.root`` it writes ``ran_by.txt`` naming
    itself, so tests can assert WHICH interpreter actually ran.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'#!/bin/sh\necho "{marker_line} $0" > ran_by.txt\nexit 0\n')
    path.chmod(0o755)
    return path


class TestResolveRepoInterpreter:
    def test_explicit_absolute_interpreter_wins(self, tmp_path):
        interp = tmp_path / "custom" / "python"
        _make_fake_interpreter(interp)
        repo = ev.EvidenceRepo(name="r", root=tmp_path, interpreter=str(interp))
        assert ev._resolve_repo_interpreter(repo) == str(interp)

    def test_explicit_relative_resolves_against_repo_root(self, tmp_path):
        interp = tmp_path / "tools" / "python"
        _make_fake_interpreter(interp)
        repo = ev.EvidenceRepo(name="r", root=tmp_path, interpreter="tools/python")
        assert ev._resolve_repo_interpreter(repo) == str(interp)

    def test_explicit_precedes_probed_sibling_venv(self, tmp_path):
        # REC-2: a stale sibling .venv must not silently override an operator
        # declaration — explicit beats discovery.
        venv_interp = _make_fake_interpreter(tmp_path / ".venv" / "bin" / "python")
        explicit = _make_fake_interpreter(tmp_path / "custom" / "python")
        repo = ev.EvidenceRepo(name="r", root=tmp_path, interpreter=str(explicit))
        resolved = ev._resolve_repo_interpreter(repo)
        assert resolved == str(explicit)
        assert resolved != str(venv_interp)

    def test_missing_explicit_warns_and_falls_through_to_probe(
        self, tmp_path, caplog
    ):
        venv_interp = _make_fake_interpreter(tmp_path / ".venv" / "bin" / "python")
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, interpreter="/does/not/exist/python"
        )
        with caplog.at_level("WARNING"):
            resolved = ev._resolve_repo_interpreter(repo)
        assert resolved == str(venv_interp)
        assert any(
            "does not exist" in rec.message for rec in caplog.records
        ), "missing explicit interpreter must warn loudly before falling through"

    def test_probes_sibling_venv_when_no_explicit(self, tmp_path):
        venv_interp = _make_fake_interpreter(tmp_path / ".venv" / "bin" / "python")
        repo = ev.EvidenceRepo(name="r", root=tmp_path)
        assert ev._resolve_repo_interpreter(repo) == str(venv_interp)

    def test_returns_none_when_nothing_resolves(self, tmp_path):
        repo = ev.EvidenceRepo(name="r", root=tmp_path)
        assert ev._resolve_repo_interpreter(repo) is None


class TestRunRepoTestsInterpreterResolution:
    def test_bare_python_command_runs_under_sibling_venv(self, tmp_path):
        # AC-1 shape: bare `python`-headed command pins to repo.root/.venv.
        _make_fake_interpreter(tmp_path / ".venv" / "bin" / "python")
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command="python -m pytest -q"
        )
        result = ev.run_repo_tests(repo)
        assert result.ran is True
        assert result.passed is True
        ran_by = (tmp_path / "ran_by.txt").read_text()
        assert str(tmp_path / ".venv" / "bin" / "python") in ran_by

    def test_no_sibling_venv_runs_verbatim_via_shell(self, tmp_path, monkeypatch):
        # AC-2: with no sibling venv the command runs verbatim via shell —
        # NEVER pinned to any caller-side interpreter.
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            captured["shell"] = kwargs.get("shell")
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

        monkeypatch.setattr(ev.subprocess, "run", fake_run)
        repo = ev.EvidenceRepo(name="r", root=tmp_path, test_command="pytest -q")
        result = ev.run_repo_tests(repo)
        assert result.passed is True
        assert captured["shell"] is True
        assert captured["argv"] == "pytest -q"

    def test_worktree_venv_structurally_unreachable(self):
        # AC-2 (structural): the caller can no longer thread its own venv —
        # the parameter is GONE, so the FEAT-10AC mis-pin cannot recur.
        import inspect

        assert "venv_python" not in inspect.signature(ev.run_repo_tests).parameters
        assert (
            "venv_python" not in inspect.signature(ev.run_all_repo_tests).parameters
        )


# ---------------------------------------------------------------------------
# collection ImportError classification (TASK-FIX-SIBTESTENV01 AC-3)
# ---------------------------------------------------------------------------


class TestCollectionImportErrorAbsent:
    def test_real_exit2_collection_import_error_is_absent(self, tmp_path):
        # The FEAT-10AC run-2 shape: exit 2 + collection ImportError output
        # from a mis-environmented interpreter → ABSENT (ran=False), never
        # ran-and-failed.
        script = tmp_path / "fail_collect.py"
        script.write_text(
            "import sys\n"
            "sys.stderr.write(\n"
            "    'ImportError while importing test module '\n"
            "    \"'tests/wiring/test_analyzer.py'\\n\"\n"
            ")\n"
            "sys.stderr.write(\"ModuleNotFoundError: No module named "
            "'guardkitfactory'\\n\")\n"
            "sys.exit(2)\n"
        )
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command="python fail_collect.py"
        )
        result = ev.run_repo_tests(repo)
        assert result.ran is False
        assert result.passed is False
        assert result.returncode == 2  # preserved for diagnosis
        assert "NEVER ran" in result.output_summary
        assert "UNVERIFIED" in result.output_summary
        assert "ModuleNotFoundError" in result.output_summary

    def test_ambiguous_exit2_without_marker_stays_ran_and_failed(self, tmp_path):
        # Bias to failure: exit 2 with no ImportError signature is NOT
        # reclassified (bdd_runner precedent).
        script = tmp_path / "fail_plain.py"
        script.write_text(
            "import sys\nsys.stderr.write('something broke\\n')\nsys.exit(2)\n"
        )
        repo = ev.EvidenceRepo(
            name="r", root=tmp_path, test_command="python fail_plain.py"
        )
        result = ev.run_repo_tests(repo)
        assert result.ran is True
        assert result.passed is False
        assert result.returncode == 2

    def test_veto_when_tests_actually_ran(self):
        # "N passed/failed" proves the suite executed — a late import error
        # stays ran-and-failed regardless of the marker.
        output = (
            "collected 5 items\n"
            "ModuleNotFoundError: No module named 'late_dep'\n"
            "2 failed, 3 passed in 0.4s\n"
        )
        assert ev._is_collection_import_error(2, output) is False

    def test_exit_1_never_reclassified(self):
        # Exit 1 is pytest's ran-and-failed verdict; even with an
        # ImportError in the output it is a genuine failure.
        output = "ModuleNotFoundError: No module named 'x'\n"
        assert ev._is_collection_import_error(1, output) is False

    def test_absent_collection_error_still_blocks(self):
        # AC-3 gate outcome unchanged: absent still blocks the turn (it is
        # feedback / unverified, never a silent pass).
        result = ev.EvidenceTestResult(
            repo_name="r",
            command="python -m pytest tests/wiring -q",
            ran=False,
            passed=False,
            returncode=2,
            output_summary=(
                "Evidence-repo test collection failed with an import error "
                "(exit 2) -- the suite NEVER ran, so sibling-repo work is "
                "UNVERIFIED (absent signal, not a test failure)."
            ),
        )
        reason = ev.evidence_repo_tests_blocking_reason([result])
        assert reason is not None
        assert "could NOT run" in reason


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
