"""A declared command whose own program does not exist could not run; a
program missing inside a script that started is the script failing
(31 October 2026). The same rule in the after-task check and at merge.

FEAT-8BB4 (29 October 2026): ``bash scripts/check.sh`` started and hit
"eslint: not found" inside, exit 127. That is a failure to repair. A
declared ``eslint .`` with no eslint on the PATH never started, and nothing
about the work was measured.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from guardkit.orchestrator.completion_verification import _run_one
from guardkit.orchestrator.project_command_env import missing_program
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.toolchain_declaration import parse_toolchain_block

PATH = {"PATH": os.environ.get("PATH", "")}
NO_SUCH = "guardkit-no-such-program-4f1c"


class TestMissingProgram:
    def test_a_program_on_the_path_is_found(self, tmp_path: Path):
        assert missing_program("sh -c 'exit 0'", tmp_path, PATH) is None

    def test_a_program_not_on_the_path_is_missing(self, tmp_path: Path):
        why = missing_program(f"{NO_SUCH} --check", tmp_path, PATH)
        assert why is not None and NO_SUCH in why

    def test_leading_settings_are_skipped(self, tmp_path: Path):
        assert missing_program("GOWORK=off GOFLAGS=-x sh -c true", tmp_path, PATH) is None
        assert missing_program(f"A=1 {NO_SUCH}", tmp_path, PATH) is not None

    def test_shell_words_are_never_looked_up(self, tmp_path: Path):
        assert missing_program(f"cd apps/web && {NO_SUCH}", tmp_path, PATH) is None
        assert missing_program("export A=1 && true", tmp_path, PATH) is None

    def test_a_path_is_looked_up_in_the_part_folder(self, tmp_path: Path):
        script = tmp_path / "qa" / "run.sh"
        script.parent.mkdir()
        assert missing_program("qa/run.sh", tmp_path, PATH) is not None
        script.write_text("#!/bin/sh\nexit 0\n")
        assert "not executable" in missing_program("qa/run.sh", tmp_path, PATH)
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        assert missing_program("qa/run.sh", tmp_path, PATH) is None


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "wt"
    root.mkdir()
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "t@t.t"],
        ["config", "user.name", "t"],
    ):
        subprocess.run(["git", *args], cwd=root, check=True)
    (root / "a.txt").write_text("a\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "start"], cwd=root, check=True)
    return root


def _validator(root: Path, test: str) -> CoachValidator:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True
    ).stdout.strip()
    return CoachValidator(
        str(root),
        task_id="TASK-MISSING-001",
        toolchain=parse_toolchain_block({"test": test}),
        baseline_commit=head,
    )


class TestAfterATask:
    def test_a_missing_declared_program_could_not_run(self, tmp_path: Path):
        root = _repo(tmp_path)
        (root / "a.txt").write_text("changed\n")
        result = _validator(root, f"{NO_SUCH} .").run_changed_parts()
        assert result.check_could_not_run is True
        assert NO_SUCH in result.check_could_not_run_detail

    def test_a_program_missing_inside_a_script_failed(self, tmp_path: Path):
        root = _repo(tmp_path)
        (root / "a.txt").write_text("changed\n")
        result = _validator(root, f"sh -c '{NO_SUCH} .'").run_changed_parts()
        assert result.check_could_not_run is False
        assert result.signal_absent is False
        assert result.tests_passed is False
        assert result.exit_code == 127
        assert result.failure_receipt() is not None


class TestAtMerge:
    def test_a_missing_declared_program_is_unverified(self, tmp_path: Path):
        root = _repo(tmp_path)
        result = _run_one(root, f"{NO_SUCH} .", "declared", 30, None, False)
        assert result.status == "unverified"
        assert NO_SUCH in result.detail

    def test_a_program_missing_inside_a_script_failed(self, tmp_path: Path):
        root = _repo(tmp_path)
        result = _run_one(root, f"sh -c '{NO_SUCH} .'", "declared", 30, None, False)
        assert result.status == "failed"
        assert result.returncode == 127
