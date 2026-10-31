"""After each task: the tests of the parts the task changed (31 October 2026).

The after-task check redesign. A task's parts come from the files it changed
since its starting commit; each changed part's declared ``test`` runs once in
its own folder; the results combine so that a failure wins over a part that
could not run, which wins over a pass. A task that changed no part has
nothing to run, and that is never recorded as a pass. GuardKit never guesses
a command.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
    combine_part_results,
)
from guardkit.orchestrator.quality_gates.required_suite import (
    required_suite_override,
)
from guardkit.orchestrator.toolchain_declaration import (
    DeclaredPart,
    parse_toolchain_block,
    parts_for_files,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def _write(root: Path, rel: str, text: str = "x\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _recorder(marker: Path, exit_code: int = 0) -> str:
    """A declared command that records the folder it ran in."""
    script = (
        "import os, sys; "
        f"open({json.dumps(str(marker))}, 'a').write(os.getcwd() + '\\n'); "
        f"print('ran'); sys.exit({exit_code})"
    )
    return f'"{sys.executable}" -c {json.dumps(script)}'


# ---------------------------------------------------------------------------
# Which part a file belongs to
# ---------------------------------------------------------------------------

STUDY_TUTOR = {
    "test": "uv run --no-sync python -m pytest -q",
    "components": {"app": {"cwd": "app", "test": "flutter test"}},
}


class TestFilesToParts:
    def _names(self, toolchain, tree: Path, files: List[str]) -> List[str]:
        declaration = parse_toolchain_block(toolchain) if toolchain else None
        return [p.name for p in parts_for_files(declaration, tree, files)]

    def test_a_file_under_no_component_is_the_root_part(self, tmp_path: Path):
        assert self._names({"test": "t"}, tmp_path, ["src/a.go"]) == ["root"]

    def test_the_study_tutor_keeps_both_its_root_and_its_app(self, tmp_path: Path):
        assert self._names(STUDY_TUTOR, tmp_path, ["backend/x.py"]) == ["root"]
        assert self._names(STUDY_TUTOR, tmp_path, ["app/lib/a.dart"]) == ["app"]
        assert self._names(
            STUDY_TUTOR, tmp_path, ["app/lib/a.dart", "backend/x.py"]
        ) == ["root", "app"]

    def test_a_pattern_part_is_a_folder_holding_the_marker(self, tmp_path: Path):
        _write(tmp_path, "apps/web/package.json", "{}")
        toolchain = {"parts": [{"under": "apps", "marker": "package.json", "test": "npm test"}]}
        declaration = parse_toolchain_block(toolchain)
        [part] = parts_for_files(declaration, tmp_path, ["apps/web/src/a.ts"])
        assert (part.name, part.cwd, part.test) == ("apps/web", "apps/web", "npm test")
        # A folder without the marker is not a part; with no root test the
        # file is in no part at all.
        _write(tmp_path, "apps/notes/readme.md")
        assert parts_for_files(declaration, tmp_path, ["apps/notes/readme.md"]) == []

    def test_the_deepest_folder_wins(self, tmp_path: Path):
        _write(tmp_path, "apps/web/package.json", "{}")
        toolchain = {
            "test": "root",
            "components": {
                "packages": {"cwd": "packages", "test": "outer"},
                "agent": {"cwd": "packages/agent", "test": "inner"},
            },
            "parts": [{"under": "apps", "marker": "package.json", "test": "npm test"}],
        }
        assert self._names(toolchain, tmp_path, ["packages/agent/a.go"]) == ["agent"]
        assert self._names(toolchain, tmp_path, ["packages/other/b.go"]) == ["packages"]
        assert self._names(toolchain, tmp_path, ["apps/web/x.ts"]) == ["apps/web"]

    def test_a_named_component_wins_over_a_pattern_at_the_same_folder(
        self, tmp_path: Path
    ):
        _write(tmp_path, "apps/web/package.json", "{}")
        toolchain = {
            "components": {"web": {"cwd": "apps/web", "test": "named"}},
            "parts": [{"under": "apps", "marker": "package.json", "test": "pattern"}],
        }
        [part] = parts_for_files(
            parse_toolchain_block(toolchain), tmp_path, ["apps/web/x.ts"]
        )
        assert (part.name, part.test) == ("web", "named")

    def test_a_folder_made_during_the_task_is_a_part_at_once(self, tmp_path: Path):
        declaration = parse_toolchain_block(
            {"parts": [{"under": "apps", "marker": "package.json", "test": "npm test"}]}
        )
        assert parts_for_files(declaration, tmp_path, ["apps/new/src/a.ts"]) == []
        _write(tmp_path, "apps/new/package.json", "{}")
        [part] = parts_for_files(declaration, tmp_path, ["apps/new/src/a.ts"])
        assert part.cwd == "apps/new"

    def test_documentation_outside_every_part_is_in_no_part(self, tmp_path: Path):
        toolchain = {"components": {"app": {"cwd": "app", "test": "x"}}}
        assert self._names(toolchain, tmp_path, ["docs/guide.md"]) == []

    def test_nothing_declared_is_the_root_part_with_no_command(self, tmp_path: Path):
        [part] = parts_for_files(None, tmp_path, ["tests/test_a.py"])
        assert (part.name, part.test) == ("root", None)
        # Even with nothing changed: an undeclared project cannot be checked.
        assert [p.test for p in parts_for_files(None, tmp_path, [])] == [None]

    def test_a_marker_is_a_plain_file_name(self):
        with pytest.raises(ValueError):
            parse_toolchain_block(
                {"parts": [{"under": "apps", "marker": "x/package.json", "test": "t"}]}
            )
        with pytest.raises(ValueError):
            parse_toolchain_block(
                {"parts": [{"under": "../apps", "marker": "package.json", "test": "t"}]}
            )


# ---------------------------------------------------------------------------
# Combining the parts' results
# ---------------------------------------------------------------------------


def _part(name: str) -> DeclaredPart:
    return DeclaredPart(name=name, cwd=name, test=f"test-{name}")


def _passed(name: str) -> IndependentTestResult:
    return IndependentTestResult.from_run(
        tests_passed=True, test_command=f"test-{name}", test_output_summary="ok",
        duration_seconds=1.0, output="ok", resolved_interpreter=None, exit_code=0,
    )


def _failed(name: str) -> IndependentTestResult:
    return IndependentTestResult.from_run(
        tests_passed=False, test_command=f"test-{name}",
        test_output_summary="1 failure", duration_seconds=1.0,
        output=f"FAIL in {name}", resolved_interpreter=None, exit_code=1,
    )


def _no_signal(name: str) -> IndependentTestResult:
    return IndependentTestResult.absent(
        test_command=f"test-{name}", test_output_summary="no test ran",
        duration_seconds=1.0,
    )


class TestCombiningParts:
    def test_a_failure_wins_over_a_part_that_could_not_run(self):
        result = combine_part_results(
            [(_part("a"), _no_signal("a")), (_part("b"), _failed("b"))]
        )
        assert result.tests_passed is False
        assert result.signal_absent is False
        assert result.failure_receipt() is not None
        assert "FAIL in b" in result.raw_output
        assert [r["outcome"] for r in result.parts] == ["could not run", "failed"]

    def test_could_not_run_wins_over_a_pass_and_names_part_and_command(self):
        result = combine_part_results(
            [(_part("a"), _passed("a")), (_part("b"), _no_signal("b"))]
        )
        assert result.tests_passed is False
        assert result.check_could_not_run is True
        assert result.check_could_not_run_detail.startswith("The check could not run")
        assert "part b (`test-b` in b)" in result.check_could_not_run_detail
        assert "no test ran" in result.check_could_not_run_detail

    def test_passes_only_when_every_part_ran_and_passed(self):
        result = combine_part_results(
            [(_part("a"), _passed("a")), (_part("b"), _passed("b"))]
        )
        assert result.tests_passed is True
        assert result.signal_absent is False
        assert result.test_command == "test-a (in a) ; test-b (in b)"

    def test_two_failures_are_both_in_the_output(self):
        result = combine_part_results(
            [(_part("a"), _failed("a")), (_part("b"), _failed("b"))]
        )
        assert "FAIL in a" in result.raw_output and "FAIL in b" in result.raw_output
        assert result.exit_code == 1


def test_nothing_to_run_is_never_a_pass():
    skipped = IndependentTestResult.skipped(test_output_summary="no part changed")
    assert skipped.tests_passed is False
    assert skipped.signal_absent is True
    assert skipped.check_could_not_run is False


# ---------------------------------------------------------------------------
# The check on a real worktree
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "wt"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@t.t")
    _git(root, "config", "user.name", "t")
    _write(root, "README.md", "readme\n")
    _write(root, "app/pubspec.yaml", "name: app\n")
    _write(root, "backend/main.py", "print(1)\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "start")
    return root


def _validator(root: Path, toolchain) -> CoachValidator:
    return CoachValidator(
        str(root),
        task_id="TASK-PARTS-001",
        toolchain=parse_toolchain_block(toolchain) if toolchain else None,
        baseline_commit=_git(root, "rev-parse", "HEAD"),
    )


class TestTheCheckOnAWorktree:
    def test_root_and_component_each_run_once_in_their_folder(
        self, repo: Path, tmp_path: Path
    ):
        marker = tmp_path / "ran.txt"
        validator = _validator(
            repo,
            {
                "test": _recorder(marker),
                "components": {"app": {"cwd": "app", "test": _recorder(marker)}},
            },
        )
        _write(repo, "backend/main.py", "print(2)\n")
        _write(repo, "app/lib/new.dart", "void main() {}\n")

        result = validator.run_changed_parts()

        assert result.tests_passed is True, result.test_output_summary
        ran = marker.read_text().splitlines()
        assert [Path(p).name for p in ran] == ["wt", "app"]
        assert [r["part"] for r in result.parts] == ["root", "app"]

    def test_only_the_changed_part_runs(self, repo: Path, tmp_path: Path):
        marker = tmp_path / "ran.txt"
        validator = _validator(
            repo,
            {
                "test": _recorder(marker),
                "components": {"app": {"cwd": "app", "test": _recorder(marker)}},
            },
        )
        _write(repo, "app/lib/new.dart", "void main() {}\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "a checkpoint since the start")

        result = validator.run_changed_parts()

        assert result.tests_passed is True
        assert [Path(p).name for p in marker.read_text().splitlines()] == ["app"]

    def test_a_failing_part_is_a_failure_to_send_back(self, repo: Path, tmp_path: Path):
        validator = _validator(
            repo,
            {"components": {"app": {"cwd": "app", "test": _recorder(tmp_path / "m", 1)}}},
        )
        _write(repo, "app/lib/new.dart", "void main() {}\n")

        result = validator.run_changed_parts()

        assert result.tests_passed is False and result.signal_absent is False
        override = required_suite_override(
            task_type="scaffolding", independent_tests=result, failure_class=None
        )
        assert override is not None

    def test_a_documentation_only_task_has_nothing_to_run(
        self, repo: Path, tmp_path: Path
    ):
        marker = tmp_path / "ran.txt"
        validator = _validator(
            repo, {"components": {"app": {"cwd": "app", "test": _recorder(marker)}}}
        )
        _write(repo, "README.md", "more words\n")

        result = validator.run_changed_parts()

        assert not marker.exists()
        assert result.test_command == "skipped"
        assert result.tests_passed is False
        assert result.check_could_not_run is False
        # Approved as before: nothing sends it back and nothing stops it.
        assert required_suite_override(
            task_type="documentation", independent_tests=result, failure_class=None
        ) is None
        bundle = CoachEvidenceBundle(independent_tests=result)
        orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        assert orch._check_could_not_run_stop(bundle, "TASK-PARTS-001", 1, 0.0) is None

    def test_nothing_declared_runs_no_guess_and_could_not_run(
        self, repo: Path, tmp_path: Path
    ):
        """A Python-looking worktree with no declaration: GuardKit runs no
        ``pytest`` for it; the check could not run, and the task stops."""
        _write(repo, "pyproject.toml", "[project]\nname='x'\n")
        _write(repo, "tests/test_a.py", "def test_a():\n    assert False\n")
        validator = _validator(repo, None)

        result = validator.run_changed_parts()

        assert result.check_could_not_run is True
        assert "nothing declared" in result.check_could_not_run_detail
        assert result.test_command == "<nothing declared>"
        bundle = CoachEvidenceBundle(independent_tests=result)
        orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        stop = orch._check_could_not_run_stop(bundle, "TASK-PARTS-001", 1, 0.0)
        assert stop is not None and stop.success is False
        assert stop.error.startswith("The check could not run")

    def test_a_part_that_times_out_failed_and_goes_back_to_the_builder(
        self, repo: Path, tmp_path: Path
    ):
        """TASK-C2C7-002 (27 October 2026): the tests started and did not
        finish within their limit; the builder made them finish on the next
        turn. A timeout is a failure sent back, naming the part, the command
        and the limit; it does not stop the task."""
        validator = _validator(
            repo,
            {"components": {"app": {
                "cwd": "app", "test": "sleep 5", "test_timeout": 1,
            }}},
        )
        _write(repo, "app/lib/new.dart", "void main() {}\n")

        result = validator.run_changed_parts()

        assert result.tests_passed is False
        assert result.signal_absent is False
        assert result.check_could_not_run is False
        assert "part app (in app)" in result.test_output_summary
        assert "`sleep 5`" in result.test_output_summary
        assert "1-second limit" in result.test_output_summary
        assert result.failure_receipt() is not None
        assert required_suite_override(
            task_type="feature", independent_tests=result, failure_class=None
        ) is not None
        bundle = CoachEvidenceBundle(independent_tests=result)
        orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        assert orch._check_could_not_run_stop(bundle, "TASK-PARTS-001", 1, 0.0) is None

    def test_a_component_with_no_test_could_not_run(self, repo: Path):
        validator = _validator(
            repo, {"test": "true", "components": {"app": {"cwd": "app"}}}
        )
        _write(repo, "app/lib/new.dart", "void main() {}\n")

        result = validator.run_changed_parts()

        assert result.check_could_not_run is True
        assert "part app" in result.check_could_not_run_detail

    def test_a_scaffolding_task_that_changes_a_part_runs_its_tests(
        self, repo: Path, tmp_path: Path
    ):
        """TASK-8BB4-001 wrote a test and was approved with its check skipped
        for its task type. Task type no longer skips anything."""
        marker = tmp_path / "ran.txt"
        validator = _validator(
            repo, {"components": {"app": {"cwd": "app", "test": _recorder(marker)}}}
        )
        _write(repo, "app/test/placeholder_test.dart", "void main() {}\n")

        bundle = validator.gather_evidence(
            "TASK-PARTS-001", 1, {"task_type": "scaffolding"}
        )

        assert marker.exists()
        assert bundle.independent_tests.tests_passed is True
        assert bundle.independent_tests.test_command != "skipped"

    def test_an_operator_handoff_task_that_changes_a_part_runs_its_tests(
        self, repo: Path, tmp_path: Path
    ):
        """An operator hand-over used to skip the check entirely, so a part
        it changed went untested. Its changed parts are tested like any
        other task's (31 October 2026)."""
        marker = tmp_path / "ran.txt"
        validator = _validator(
            repo, {"components": {"app": {"cwd": "app", "test": _recorder(marker)}}}
        )
        _write(repo, "app/lib/new.dart", "void main() {}\n")

        bundle = validator.gather_evidence(
            "TASK-PARTS-001", 1, {"task_type": "operator_handoff"}
        )

        assert marker.exists()
        assert bundle.independent_tests.tests_passed is True

    def test_an_exception_while_testing_is_the_check_not_running(
        self, repo: Path, monkeypatch
    ):
        """It used to be recorded as no result, which nothing stopped on,
        and the task could be approved untested."""
        validator = _validator(repo, {"test": "true"})

        def boom(**_kwargs):
            raise RuntimeError("the part could not be read")

        monkeypatch.setattr(validator, "run_changed_parts", boom)
        bundle = validator.gather_evidence("TASK-PARTS-001", 1, {})

        result = bundle.independent_tests
        assert result.check_could_not_run is True
        assert "RuntimeError: the part could not be read" in result.check_could_not_run_detail
        orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        stop = orch._check_could_not_run_stop(bundle, "TASK-PARTS-001", 1, 0.0)
        assert stop is not None and stop.success is False
        assert "the part could not be read" in stop.error

    def test_no_bundle_or_no_test_result_stops_the_task(self):
        orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        stop = orch._check_could_not_run_stop(
            None, "TASK-PARTS-001", 1, 0.0, gather_error="OSError: disk gone"
        )
        assert stop is not None and stop.success is False
        assert stop.error.startswith("The check could not run")
        assert "OSError: disk gone" in stop.error
        stop = orch._check_could_not_run_stop(
            CoachEvidenceBundle(), "TASK-PARTS-001", 1, 0.0
        )
        assert stop is not None and stop.success is False
        assert "no result of the changed parts' tests" in stop.error

    def test_the_builders_report_is_only_the_fallback(self, repo: Path, tmp_path: Path):
        marker = tmp_path / "ran.txt"
        validator = CoachValidator(
            str(repo),
            task_id="TASK-PARTS-001",
            toolchain=parse_toolchain_block(
                {"components": {"app": {"cwd": "app", "test": _recorder(marker)}}}
            ),
        )
        result = validator.run_changed_parts(
            task_work_results={"files_modified": [str(repo / "app" / "lib" / "a.dart")]}
        )
        assert result.tests_passed is True
        assert [Path(p).name for p in marker.read_text().splitlines()] == ["app"]


# ---------------------------------------------------------------------------
# What the project declares "no tests ran" looks like (31 October 2026)
# ---------------------------------------------------------------------------

#: The shipped react-go-monorepo template's ``api`` marker, as declared.
GO_RAN_MARKER = r"(?ms)\A(?!.*^ok\s+\S+\s+\(cached\))(?=.*^\s*--- PASS: \S+)"
GO_NO_TEST_FILES = "?   \texample.com/probe/notests\t[no test files]\n"
GO_NO_TESTS_TO_RUN = (
    "testing: warning: no tests to run\n"
    "PASS\n"
    "ok  \texample.com/probe/mixed\t1.009s [no tests to run]\n"
)
GO_PASSED = (
    "=== RUN   TestPasses\n"
    "--- PASS: TestPasses (0.00s)\n"
    "PASS\n"
    "ok  \texample.com/probe/mixed\t1.013s\n"
)


def _printer(text: str, exit_code: int = 0) -> str:
    """A declared command that prints ``text`` and exits ``exit_code``."""
    script = f"import sys; sys.stdout.write({text!r}); sys.exit({exit_code})"
    return f'"{sys.executable}" -c {json.dumps(script)}'


def _api(test: str, **markers) -> dict:
    return {"components": {"app": {"cwd": "app", "test": test, **markers}}}


class TestDeclaredNoTestsRan:
    """The project's own ``absent_substrings`` and ``ran_marker_regex`` are
    honoured: a clean exit with no test run is a failure sent back to the
    builder, never a pass and never "the check could not run"."""

    @pytest.mark.parametrize("output", [GO_NO_TEST_FILES, GO_NO_TESTS_TO_RUN])
    def test_a_clean_exit_with_no_marker_is_a_failure_to_send_back(
        self, repo: Path, output: str
    ):
        command = _printer(output)
        validator = _validator(
            repo,
            _api(command, requires_ran_marker=True, ran_marker_regex=GO_RAN_MARKER),
        )
        _write(repo, "app/lib/new.go", "package app\n")

        result = validator.run_changed_parts()

        assert result.tests_passed is False
        assert result.signal_absent is False
        assert result.check_could_not_run is False
        assert result.exit_code == 0
        expected = (
            f"no tests ran in part app ({command}): no line matched {GO_RAN_MARKER}"
        )
        assert result.no_tests_ran == expected
        assert expected[1:] in result.test_output_summary
        receipt = result.failure_receipt()
        assert receipt is not None and receipt["failing_lines"][0] == expected
        assert [(r["part"], r["outcome"]) for r in result.parts] == [("app", "failed")]
        assert result.parts[0]["no_tests_ran"] == expected
        assert required_suite_override(
            task_type="feature", independent_tests=result, failure_class=None
        ) is not None
        bundle = CoachEvidenceBundle(independent_tests=result)
        orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        assert orch._check_could_not_run_stop(bundle, "TASK-PARTS-001", 1, 0.0) is None

    def test_a_real_passing_run_matches_and_passes(self, repo: Path):
        validator = _validator(
            repo,
            _api(
                _printer(GO_PASSED),
                requires_ran_marker=True,
                ran_marker_regex=GO_RAN_MARKER,
            ),
        )
        _write(repo, "app/lib/new.go", "package app\n")

        result = validator.run_changed_parts()

        assert result.tests_passed is True, result.test_output_summary
        assert result.no_tests_ran is None

    def test_a_declared_absence_text_is_a_failure_on_the_root(self, repo: Path):
        command = _printer("No tests found, exiting with code 0\n")
        validator = _validator(
            repo, {"test": command, "absent_substrings": ["no tests found"]}
        )
        _write(repo, "backend/main.py", "print(2)\n")

        result = validator.run_changed_parts()

        assert result.tests_passed is False and result.signal_absent is False
        assert result.no_tests_ran == (
            f'no tests ran in part root ({command}): the output contains '
            '"no tests found"'
        )

    def test_a_pattern_part_uses_its_own_declaration(
        self, repo: Path, tmp_path: Path
    ):
        _write(repo, "apps/web/package.json", "{}")
        validator = _validator(
            repo,
            {
                "test": _printer("root ran\n"),
                "parts": [{
                    "under": "apps",
                    "marker": "package.json",
                    "test": _printer("Test Files  1 skipped (1)\n"),
                    "ran_marker_regex": r"Tests\b[^\n]*?[1-9][0-9]* passed",
                }],
            },
        )
        _write(repo, "apps/web/src/a.ts", "export {}\n")
        _write(repo, "backend/main.py", "print(2)\n")

        result = validator.run_changed_parts()

        assert result.tests_passed is False
        outcomes = {r["part"]: r["outcome"] for r in result.parts}
        assert outcomes == {"root": "passed", "apps/web": "failed"}
        assert result.no_tests_ran.startswith("no tests ran in part apps/web (")

    def test_a_failing_run_stays_a_failure_with_its_own_output(self, repo: Path):
        validator = _validator(
            repo,
            _api(
                _printer("--- FAIL: TestFails (0.00s)\nFAIL\n", 1),
                requires_ran_marker=True,
                ran_marker_regex=GO_RAN_MARKER,
            ),
        )
        _write(repo, "app/lib/new.go", "package app\n")

        result = validator.run_changed_parts()

        assert result.tests_passed is False and result.exit_code == 1
        assert result.no_tests_ran is None

    def test_marker_turned_off_leaves_the_exit_code_to_decide(self, repo: Path):
        validator = _validator(
            repo,
            _api(
                _printer(GO_NO_TEST_FILES),
                requires_ran_marker=False,
                ran_marker_regex=GO_RAN_MARKER,
            ),
        )
        _write(repo, "app/lib/new.go", "package app\n")

        assert validator.run_changed_parts().tests_passed is True

    def test_nothing_declared_leaves_the_exit_code_to_decide(self, repo: Path):
        validator = _validator(repo, _api(_printer(GO_NO_TEST_FILES)))
        _write(repo, "app/lib/new.go", "package app\n")

        assert validator.run_changed_parts().tests_passed is True

    def test_a_marker_required_but_not_named_could_not_run(
        self, repo: Path, tmp_path: Path
    ):
        marker = tmp_path / "ran.txt"
        validator = _validator(
            repo, _api(_recorder(marker), requires_ran_marker=True)
        )
        _write(repo, "app/lib/new.go", "package app\n")

        result = validator.run_changed_parts()

        assert result.check_could_not_run is True
        assert "part app" in result.check_could_not_run_detail
        assert "no `ran_marker_regex`" in result.check_could_not_run_detail
        assert not marker.exists(), "the command must not run"

    def test_a_caller_supplied_command_is_not_judged_by_the_declaration(
        self, repo: Path
    ):
        validator = CoachValidator(
            str(repo),
            task_id="TASK-PARTS-001",
            test_command=_printer(GO_NO_TEST_FILES),
            toolchain=parse_toolchain_block(
                {"test": "x", "requires_ran_marker": True,
                 "ran_marker_regex": GO_RAN_MARKER}
            ),
            baseline_commit=_git(repo, "rev-parse", "HEAD"),
        )

        assert validator.run_changed_parts().tests_passed is True

    def test_two_parts_that_ran_nothing_are_both_named(self):
        first = IndependentTestResult(
            tests_passed=False, test_command="a", test_output_summary="s",
            duration_seconds=0.0, raw_output="out a", exit_code=0,
            no_tests_ran="no tests ran in part a (a): no line matched x",
        )
        second = IndependentTestResult(
            tests_passed=False, test_command="b", test_output_summary="s",
            duration_seconds=0.0, raw_output="out b", exit_code=0,
            no_tests_ran="no tests ran in part b (b): no line matched y",
        )
        result = combine_part_results(
            [(DeclaredPart(name="a", cwd="a", test="a"), first),
             (DeclaredPart(name="b", cwd="b", test="b"), second)]
        )
        assert result.tests_passed is False
        assert "part a (a)" in result.no_tests_ran
        assert "part b (b)" in result.no_tests_ran
        assert result.failure_receipt()["failing_lines"][0] == result.no_tests_ran
