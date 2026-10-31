"""The merge's full check (after-task check redesign, 31 October 2026).

The merge runs the project's declared full check once on the joined result:
the root ``test`` plus every component's and pattern part's ``test``, each in
its own folder within its own ``test_timeout``, whether or not a
``feature_check`` is declared. ``verify_ok``
is true only when it ran and passed. There is no known-failure baseline, a
declared script that exits 127 failed (FEAT-8BB4), and GuardKit never chooses
a command a project did not declare.

Every case drives ``execute_merge`` on a real repository.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest

from tests.self_contained_python import self_contained_python
from guardkit.orchestrator.completion_verification import (
    NOTHING_DECLARED,
    resolve_verify_command,
    run_completion_verification,
)
from guardkit.orchestrator.project_command_env import remove_short_tmpdir
from guardkit.orchestrator.merge_executor import (
    OUTCOME_MERGED,
    OUTCOME_REFUSED,
    execute_merge,
    resolve_verify_command_on_target,
)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def declared_command(python: Optional[str] = None) -> str:
    """The repository's declared test command, run by a named interpreter
    that does not depend on the real HOME (the merge runs with a private
    one)."""
    if python is None:
        python = self_contained_python()
    return f'"{python}" -m pytest -q -p no:cacheprovider tests/'


def _write_config(repo: Path, toolchain: Optional[dict]) -> None:
    config = repo / ".guardkit" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    text = "" if toolchain is None else "toolchain: " + json.dumps(toolchain) + "\n"
    config.write_text(text or "# nothing declared\n", encoding="utf-8")


def _base_repo(tmp_path: Path, toolchain: Optional[dict]) -> Path:
    """main: a green suite and the given declaration."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    (repo / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.pytest_cache/\n", encoding="utf-8"
    )
    (repo / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "test_green.py").write_text(
        "def test_green():\n    assert True\n", encoding="utf-8"
    )
    _write_config(repo, toolchain)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "the repository as it already stands")
    return repo


def _branch_adding(repo: Path, feature_id: str, path: str, body: str) -> None:
    _git(repo, "checkout", "-q", "-b", f"autobuild/{feature_id}")
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"{feature_id} work")
    _git(repo, "checkout", "-q", "main")


GREEN = "def test_new_green():\n    assert True\n"
RED = "def test_new_red():\n    assert False, 'this merge broke it'\n"


def _marker_command(marker: Path, exit_code: int = 0) -> str:
    """A real command that records that it ran (and in which folder)."""
    script = (
        "import os, sys; "
        f"open({json.dumps(str(marker))}, 'a').write(os.getcwd() + '\\n'); "
        f"sys.exit({exit_code})"
    )
    return f'"{sys.executable}" -c {json.dumps(script)}'


class TestOnlyAPassIsOk:
    def test_a_clean_branch_passes(self, tmp_path: Path):
        repo = _base_repo(tmp_path, {"test": declared_command()})
        _branch_adding(repo, "FEAT-CLEAN", "tests/test_new_green.py", GREEN)

        report = execute_merge(repo, "FEAT-CLEAN")

        assert report.outcome == OUTCOME_MERGED
        assert report.verify_status == "passed"
        assert report.verify_ran is True
        assert report.verify_ok is True

    def test_a_new_failure_fails_the_merge(self, tmp_path: Path):
        repo = _base_repo(tmp_path, {"test": declared_command()})
        _branch_adding(repo, "FEAT-RED", "tests/test_new_red.py", RED)

        report = execute_merge(repo, "FEAT-RED")

        assert report.verify_status == "failed"
        assert report.verify_ok is False
        assert "this merge broke it" in report.verify_output_tail

    def test_nothing_declared_is_not_ok_and_runs_no_guess(self, tmp_path: Path):
        """A Python-looking repository (pytest.ini, tests/) with nothing
        declared: no ``pytest`` is chosen for it; the check could not run."""
        repo = _base_repo(tmp_path, None)
        _branch_adding(repo, "FEAT-CLEAN", "tests/test_new_green.py", GREEN)

        report = execute_merge(repo, "FEAT-CLEAN")

        assert report.verify_command is None
        assert report.verify_status == "unverified"
        assert report.verify_ran is False
        assert report.verify_ok is False
        assert NOTHING_DECLARED in report.verify_detail

    def test_a_script_that_exits_127_failed(self, tmp_path: Path):
        """FEAT-8BB4: the declared script ran, a program inside it was
        missing, and it exited 127. That is a failure, not "could not run"."""
        repo = _base_repo(tmp_path, {"test": "bash scripts/check.sh"})
        _git(repo, "checkout", "-q", "-b", "with-script")
        script = repo / "scripts" / "check.sh"
        script.parent.mkdir()
        script.write_text("echo linting\neslint-is-not-installed .\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "script")
        _git(repo, "checkout", "-q", "main")
        _git(repo, "merge", "-q", "with-script")
        _branch_adding(repo, "FEAT-CLEAN", "tests/test_new_green.py", GREEN)

        report = execute_merge(repo, "FEAT-CLEAN")

        assert report.verify_status == "failed"
        assert report.verify_ok is False
        assert "exit 127" in report.verify_detail


class TestTheFullCheckRunsEveryPart:
    def test_root_components_and_pattern_parts_each_run_in_their_folder(
        self, tmp_path: Path
    ):
        marker = tmp_path / "ran.txt"
        repo = _base_repo(
            tmp_path,
            {
                "test": _marker_command(marker),
                "components": {"app": {"cwd": "app", "test": _marker_command(marker)}},
                "parts": [
                    {"under": "apps", "marker": "package.json", "test": _marker_command(marker)}
                ],
            },
        )
        (repo / "app").mkdir()
        (repo / "app" / "keep.txt").write_text("app\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "app")
        # The branch adds a new pattern part: it is checked at the merge.
        _branch_adding(repo, "FEAT-WEB", "apps/web/package.json", "{}\n")

        report = execute_merge(repo, "FEAT-WEB")

        assert report.verify_status == "passed", report.verify_detail
        folders = [Path(line).name for line in marker.read_text().splitlines()]
        assert folders == ["repo", "app", "web"]
        assert "(in app)" in report.verify_command
        assert "(in each folder under apps holding package.json)" in report.verify_command

    def test_a_failing_component_fails_the_merge(self, tmp_path: Path):
        """The study tutor's shape: a root backend and a Flutter app. Both are
        checked; a failure in the app is not hidden by a green root."""
        marker = tmp_path / "ran.txt"
        repo = _base_repo(
            tmp_path,
            {
                "test": declared_command(),
                "components": {"app": {"cwd": "app", "test": _marker_command(marker, 1)}},
            },
        )
        (repo / "app").mkdir()
        (repo / "app" / "keep.txt").write_text("app\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "app")
        _branch_adding(repo, "FEAT-CLEAN", "tests/test_new_green.py", GREEN)

        report = execute_merge(repo, "FEAT-CLEAN")

        assert report.verify_status == "failed"
        assert report.verify_ok is False
        assert marker.read_text().strip().endswith("app")
        assert "app (in app)" in report.verify_detail

    def test_a_declared_feature_check_does_not_replace_the_parts(
        self, tmp_path: Path
    ):
        """A notes-style declaration (the shape of notes-private-fixture): a
        root check, two components and a ``feature_check`` journey. The merge
        runs the root and both components, each in its folder, and not the
        journey; dropping the root (the reference check, lint, the Go and
        TypeScript tests) for the journey was the reviewer's first defect."""
        ran = tmp_path / "ran.txt"
        journey = tmp_path / "journey.txt"
        repo = _base_repo(
            tmp_path,
            {
                "install": "true",
                "test": _marker_command(ran),
                "test_timeout": 1800,
                "feature_check": _marker_command(journey),
                "feature_check_timeout": 1800,
                "components": {
                    "web": {"cwd": "apps/web", "test": _marker_command(ran)},
                    "api": {"cwd": "apps/api", "test": _marker_command(ran)},
                },
            },
        )
        for folder in ("apps/web", "apps/api"):
            (repo / folder).mkdir(parents=True)
            (repo / folder / "keep.txt").write_text("part\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "parts")
        _branch_adding(repo, "FEAT-CLEAN", "tests/test_new_green.py", GREEN)

        report = execute_merge(repo, "FEAT-CLEAN")

        assert report.verify_status == "passed", report.verify_detail
        assert report.verify_source == "repository toolchain declaration"
        folders = sorted(Path(line).name for line in ran.read_text().splitlines())
        assert folders == ["api", "repo", "web"]
        assert not journey.exists()

    def test_each_part_runs_within_its_own_declared_limit(self, tmp_path: Path):
        """The root declares 30 seconds and takes two; the component declares
        one second and takes five. The merge's own limit (one second here)
        bounds only installs: the root passes, the component times out."""
        sleep = f'"{sys.executable}" -c "import time; time.sleep({{}})"'
        repo = _base_repo(
            tmp_path,
            {
                "test": sleep.format(2),
                "test_timeout": 30,
                "components": {
                    "app": {"cwd": "app", "test": sleep.format(5), "test_timeout": 1}
                },
            },
        )
        (repo / "app").mkdir()
        (repo / "app" / "keep.txt").write_text("app\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "app")
        _branch_adding(repo, "FEAT-CLEAN", "tests/test_new_green.py", GREEN)

        report = execute_merge(repo, "FEAT-CLEAN", verify_timeout=1)

        assert report.verify_status == "failed"
        assert "app (in app)" in report.verify_detail
        assert "timed out after 1s" in report.verify_detail
        assert "root" not in report.verify_detail


class TestTheReceiptSaysWhetherTheTestsRan:
    def test_a_check_that_never_ran_does_not_claim_it_did(self, tmp_path: Path):
        marker = tmp_path / "ran.txt"
        repo = _base_repo(
            tmp_path,
            {"components": {"app": {"cwd": "app"}}, "parts": [
                {"under": "apps", "marker": "package.json", "test": _marker_command(marker)}
            ]},
        )
        _branch_adding(repo, "FEAT-CLEAN", "tests/test_new_green.py", GREEN)

        report = execute_merge(repo, "FEAT-CLEAN")
        receipt = "\n".join(report.receipt_lines())

        assert report.verify_status == "unverified"
        assert report.verify_ok is False
        assert "nothing declared for part app" in report.verify_detail
        assert "The tests would have been run with:" in receipt
        assert "The tests were run with:" not in receipt

    def test_a_check_that_did_run_still_says_so(self, tmp_path: Path):
        repo = _base_repo(tmp_path, {"test": declared_command()})
        _branch_adding(repo, "FEAT-CLEAN", "tests/test_new_green.py", GREEN)
        report = execute_merge(repo, "FEAT-CLEAN")
        receipt = "\n".join(report.receipt_lines())
        assert "The tests were run with:" in receipt
        assert "would have been run" not in receipt

    def test_verification_turned_off_reads_differently(self, tmp_path: Path):
        repo = _base_repo(tmp_path, {"test": declared_command()})
        _branch_adding(repo, "FEAT-CLEAN", "tests/test_new_green.py", GREEN)
        report = execute_merge(repo, "FEAT-CLEAN", verify=False)
        assert report.verify_ran is False
        assert report.verify_status is None
        assert report.verify_ok is False
        assert "turned off for this run" in "\n".join(report.receipt_lines())


class TestARefusalTouchesNothing:
    def test_an_unresolvable_target_refuses_before_any_test_runs(
        self, tmp_path: Path
    ):
        marker = tmp_path / "the-suite-ran"
        repo = _base_repo(tmp_path, {"test": _marker_command(marker)})
        _branch_adding(repo, "FEAT-CLEAN", "tests/test_new_green.py", GREEN)
        _git(repo, "checkout", "-q", "-b", "somewhere-else")

        report = execute_merge(repo, "FEAT-CLEAN", target_branch="no-such-branch")

        assert report.outcome == OUTCOME_REFUSED
        assert "could not resolve" in report.refusal_reason
        assert not marker.exists()
        assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "somewhere-else"
        assert report.notes == ()


# ---------------------------------------------------------------------------
# Rule 11 — a branch never chooses the command that judges it
# ---------------------------------------------------------------------------

SELF_JUDGE = "FEAT-SELFJUDGE"


def _repo_with_a_branch_that_rewrites_the_command(tmp_path: Path) -> Path:
    """main declares a real pytest run; the branch declares ``true`` and adds
    a failing test."""
    repo = _base_repo(tmp_path, {"test": declared_command()})
    _git(repo, "checkout", "-q", "-b", f"autobuild/{SELF_JUDGE}")
    _write_config(repo, {"test": "true"})
    (repo / "tests" / "test_new_red.py").write_text(RED, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"{SELF_JUDGE} greens itself")
    _git(repo, "checkout", "-q", "main")
    return repo


class TestTheBranchCannotChooseItsOwnJudge:
    def test_the_fixture_really_would_green_itself(self, tmp_path: Path):
        repo = _repo_with_a_branch_that_rewrites_the_command(tmp_path)
        assert resolve_verify_command(repo)[0] == declared_command()

        execute_merge(repo, SELF_JUDGE, verify=False)

        command, source, declaration = resolve_verify_command(repo)
        assert command == "true"
        after = run_completion_verification(
            repo, command, source, declaration=declaration
        )
        assert after.status == "passed"

    def test_the_target_branchs_command_runs(self, tmp_path: Path):
        repo = _repo_with_a_branch_that_rewrites_the_command(tmp_path)

        report = execute_merge(repo, SELF_JUDGE)

        assert report.outcome == OUTCOME_MERGED
        assert report.verify_command == declared_command()
        assert report.verify_source == "repository toolchain declaration"
        assert report.verify_status == "failed"
        assert report.verify_ok is False


class TestResolveVerifyCommandOnTarget:
    def test_it_reads_the_target_branch_not_wherever_head_is(
        self, tmp_path: Path
    ):
        repo = _repo_with_a_branch_that_rewrites_the_command(tmp_path)
        _git(repo, "checkout", "-q", f"autobuild/{SELF_JUDGE}")

        (command, source, _declaration), problem = (
            resolve_verify_command_on_target(repo, "main")
        )

        assert problem is None
        assert command == declared_command()
        assert source == "repository toolchain declaration"
        assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"

    def test_a_target_it_cannot_reach_is_reported_never_guessed(
        self, tmp_path: Path
    ):
        repo = _base_repo(tmp_path, {"test": declared_command()})
        _resolution, problem = resolve_verify_command_on_target(
            repo, "no-such-branch"
        )
        assert problem is not None
        assert "could not switch to branch no-such-branch" in problem


@pytest.mark.parametrize("returncode", [126, 127])
def test_a_declared_command_exiting_126_or_127_is_failed(
    tmp_path: Path, returncode: int
):
    result = run_completion_verification(
        tmp_path, f"exit {returncode}", "repository toolchain declaration"
    )
    assert result.status == "failed"


@pytest.mark.real_project_scratch
def test_the_full_check_by_hand_runs_each_part_in_its_folder(tmp_path: Path):
    """``guardkit autobuild complete --verify`` builds the environment itself
    (the merge hands one in). A part's folder is not a git checkout of its
    own, so the environment is built once for the repository and given to
    every part (31 October 2026: each part's command could not start)."""
    marker = tmp_path / "ran.txt"
    repo = _base_repo(
        tmp_path,
        {
            "test": _marker_command(marker),
            "components": {"app": {"cwd": "app", "test": _marker_command(marker)}},
        },
    )
    (repo / "app").mkdir()
    command, source, declaration = resolve_verify_command(repo)

    try:
        result = run_completion_verification(
            repo, command, source, declaration=declaration, timeout=60
        )
    finally:
        remove_short_tmpdir(repo)

    assert result.status == "passed", result.detail
    assert [Path(p).name for p in marker.read_text().splitlines()] == ["repo", "app"]


# ---------------------------------------------------------------------------
# What the project declares "no tests ran" looks like (31 October 2026)
# ---------------------------------------------------------------------------

#: The shipped react-go-monorepo template's ``api`` marker, as declared.
GO_RAN_MARKER = r"(?ms)\A(?!.*^ok\s+\S+\s+\(cached\))(?=.*^\s*--- PASS: \S+)"
GO_NO_TEST_FILES = "?   \texample.com/probe/notests\t[no test files]\n"
GO_PASSED = (
    "=== RUN   TestPasses\n--- PASS: TestPasses (0.00s)\nPASS\n"
    "ok  \texample.com/probe/mixed\t1.013s\n"
)


def _printer(text: str, exit_code: int = 0) -> str:
    script = f"import sys; sys.stdout.write({text!r}); sys.exit({exit_code})"
    return f'"{sys.executable}" -c {json.dumps(script)}'


def _repo_with_api(tmp_path: Path, api: dict) -> Path:
    repo = _base_repo(
        tmp_path,
        {"test": declared_command(), "components": {"api": {"cwd": "api", **api}}},
    )
    (repo / "api").mkdir()
    (repo / "api" / "go.mod").write_text("module example.com/api\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "api")
    _branch_adding(repo, "FEAT-API", "tests/test_new_green.py", GREEN)
    return repo


class TestDeclaredNoTestsRan:
    def test_a_component_that_ran_no_tests_fails_the_merge(self, tmp_path: Path):
        command = _printer(GO_NO_TEST_FILES)
        repo = _repo_with_api(
            tmp_path,
            {"test": command, "requires_ran_marker": True,
             "ran_marker_regex": GO_RAN_MARKER},
        )

        report = execute_merge(repo, "FEAT-API")

        assert report.verify_status == "failed", report.verify_detail
        assert report.verify_ok is False
        assert (
            f"no tests ran in part api ({command}): "
            f"no line matched {GO_RAN_MARKER}"
        ) in report.verify_detail

    def test_a_component_whose_tests_ran_passes(self, tmp_path: Path):
        repo = _repo_with_api(
            tmp_path,
            {"test": _printer(GO_PASSED), "requires_ran_marker": True,
             "ran_marker_regex": GO_RAN_MARKER},
        )

        report = execute_merge(repo, "FEAT-API")

        assert report.verify_status == "passed", report.verify_detail

    def test_a_declared_absence_text_on_the_root_fails(self, tmp_path: Path):
        command = _printer("No tests found, exiting with code 0\n")
        repo = _base_repo(
            tmp_path, {"test": command, "absent_substrings": ["No tests found"]}
        )
        _branch_adding(repo, "FEAT-ROOT", "tests/test_new_green.py", GREEN)

        report = execute_merge(repo, "FEAT-ROOT")

        assert report.verify_status == "failed", report.verify_detail
        assert 'the output contains "No tests found"' in report.verify_detail

    def test_nothing_declared_leaves_the_exit_code_to_decide(self, tmp_path: Path):
        repo = _repo_with_api(tmp_path, {"test": _printer(GO_NO_TEST_FILES)})

        report = execute_merge(repo, "FEAT-API")

        assert report.verify_status == "passed", report.verify_detail

    def test_a_marker_required_but_not_named_is_unverified(self, tmp_path: Path):
        marker = tmp_path / "ran.txt"
        repo = _repo_with_api(
            tmp_path,
            {"test": _marker_command(marker), "requires_ran_marker": True},
        )

        report = execute_merge(repo, "FEAT-API")

        assert report.verify_status == "unverified", report.verify_detail
        assert report.verify_ok is False
        assert "no `ran_marker_regex`" in report.verify_detail
        assert not marker.exists(), "the command must not run"
