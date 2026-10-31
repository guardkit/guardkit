"""A part's declared install runs before its tests (31 October 2026).

Rich approved it: a component's or ``parts:`` entry's ``install`` runs in the
part's folder before the part's tests, the first time the part is tested in a
worktree and again only when the files directly in the part's folder have
changed. A failed install is "the check could not run" for that part. The
merge runs it before the part's command in the full check.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from guardkit.orchestrator.completion_verification import (
    resolve_verify_command_with_declaration,
    run_completion_verification,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.toolchain_declaration import parse_toolchain_block


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def _recorder(marker: Path, word: str, exit_code: int = 0) -> str:
    """A declared command (an argument list, no shell) that appends ``word``."""
    script = (
        "import sys; "
        f"open({json.dumps(str(marker))}, 'a').write({json.dumps(word)} + '\\n'); "
        f"sys.exit({exit_code})"
    )
    return f"{sys.executable} -c {json.dumps(script)}"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "wt"
    (root / "apps" / "web" / "src").mkdir(parents=True)
    (root / "apps" / "web" / "part.yaml").write_text('name: web\n')
    (root / "apps" / "web" / "src" / "a.ts").write_text("export const a = 1;\n")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@t.t")
    _git(root, "config", "user.name", "t")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "start")
    return root


def _validator(root: Path, marker: Path, install_exit: int = 0) -> CoachValidator:
    toolchain = parse_toolchain_block(
        {
            "parts": [
                {
                    "under": "apps",
                    "marker": "part.yaml",
                    "install": _recorder(marker, "install", install_exit),
                    "test": _recorder(marker, "test"),
                }
            ]
        }
    )
    return CoachValidator(
        str(root),
        task_id="TASK-INST-001",
        toolchain=toolchain,
        baseline_commit=_git(root, "rev-parse", "HEAD"),
    )


def _ran(marker: Path) -> list:
    return marker.read_text().splitlines() if marker.exists() else []


class TestThePartInstall:
    def test_the_first_run_installs_before_the_tests(self, repo: Path, tmp_path: Path):
        marker = tmp_path / "ran.txt"
        (repo / "apps" / "web" / "src" / "a.ts").write_text("export const a = 2;\n")

        result = _validator(repo, marker).run_changed_parts()

        assert result.tests_passed is True, result.test_output_summary
        assert _ran(marker) == ["install", "test"]

    def test_unchanged_dependency_files_skip_the_install(
        self, repo: Path, tmp_path: Path
    ):
        marker = tmp_path / "ran.txt"
        (repo / "apps" / "web" / "src" / "a.ts").write_text("export const a = 2;\n")
        _validator(repo, marker).run_changed_parts()
        # A later turn changes source below the part's folder only.
        (repo / "apps" / "web" / "src" / "a.ts").write_text("export const a = 3;\n")

        _validator(repo, marker).run_changed_parts()

        assert _ran(marker) == ["install", "test", "test"]

    def test_a_changed_manifest_reinstalls(self, repo: Path, tmp_path: Path):
        marker = tmp_path / "ran.txt"
        (repo / "apps" / "web" / "src" / "a.ts").write_text("export const a = 2;\n")
        _validator(repo, marker).run_changed_parts()
        (repo / "apps" / "web" / "part.yaml").write_text(
            "name: web\ndepends: [left-pad]\n"
        )

        _validator(repo, marker).run_changed_parts()

        assert _ran(marker) == ["install", "test", "install", "test"]

    def test_build_and_test_outputs_do_not_reinstall(
        self, repo: Path, tmp_path: Path
    ):
        """Only files git tracks count (31 October 2026): what a build or a
        test run leaves in the part's folder (a tsbuildinfo, a JUnit or
        coverage file) does not make the install due again."""
        marker = tmp_path / "ran.txt"
        (repo / "apps" / "web" / "src" / "a.ts").write_text("export const a = 2;\n")
        _validator(repo, marker).run_changed_parts()
        (repo / "apps" / "web" / "tsconfig.tsbuildinfo").write_text("{}\n")
        (repo / "apps" / "web" / "junit.xml").write_text("<testsuites/>\n")

        _validator(repo, marker).run_changed_parts()

        assert _ran(marker) == ["install", "test", "test"]

    def test_a_failed_install_is_could_not_run_and_runs_no_tests(
        self, repo: Path, tmp_path: Path
    ):
        marker = tmp_path / "ran.txt"
        (repo / "apps" / "web" / "src" / "a.ts").write_text("export const a = 2;\n")

        result = _validator(repo, marker, install_exit=3).run_changed_parts()

        assert _ran(marker) == ["install"]
        assert result.check_could_not_run is True
        assert result.tests_passed is False
        detail = result.check_could_not_run_detail
        assert detail.startswith("The check could not run")
        assert "part apps/web" in detail
        assert "the declared install" in detail and "exit 3" in detail
        # It is not remembered as installed: the next run tries again.
        _validator(repo, marker, install_exit=3).run_changed_parts()
        assert _ran(marker) == ["install", "install"]

    def test_an_install_that_cannot_start_is_could_not_run(
        self, repo: Path, tmp_path: Path
    ):
        toolchain = parse_toolchain_block(
            {"components": {"web": {
                "cwd": "apps/web",
                "install": "no-such-installer-7f3a ci",
                "test": "true",
            }}}
        )
        validator = CoachValidator(
            str(repo), task_id="TASK-INST-001", toolchain=toolchain,
            baseline_commit=_git(repo, "rev-parse", "HEAD"),
        )
        (repo / "apps" / "web" / "src" / "a.ts").write_text("export const a = 2;\n")

        result = validator.run_changed_parts()

        assert result.check_could_not_run is True
        assert "could not start" in result.check_could_not_run_detail

    def test_a_part_without_an_install_just_runs_its_tests(
        self, repo: Path, tmp_path: Path
    ):
        marker = tmp_path / "ran.txt"
        toolchain = parse_toolchain_block(
            {"components": {"web": {"cwd": "apps/web", "test": _recorder(marker, "test")}}}
        )
        validator = CoachValidator(
            str(repo), task_id="TASK-INST-001", toolchain=toolchain,
            baseline_commit=_git(repo, "rev-parse", "HEAD"),
        )
        (repo / "apps" / "web" / "src" / "a.ts").write_text("export const a = 2;\n")

        assert validator.run_changed_parts().tests_passed is True
        assert _ran(marker) == ["test"]


class TestTheMergeInstallsEachPart:
    def test_the_install_runs_before_the_parts_command(self, repo: Path, tmp_path: Path):
        marker = tmp_path / "ran.txt"
        declaration = parse_toolchain_block(
            {"parts": [{
                "under": "apps", "marker": "part.yaml",
                "install": _recorder(marker, "install"),
                "test": _recorder(marker, "test"),
            }]}
        )
        command, source, decl = resolve_verify_command_with_declaration(repo, declaration)

        result = run_completion_verification(repo, command, source, declaration=decl)

        assert result.status == "passed", result.detail
        assert _ran(marker) == ["install", "test"]

    def test_a_failed_install_is_unverified_and_runs_no_tests(
        self, repo: Path, tmp_path: Path
    ):
        marker = tmp_path / "ran.txt"
        declaration = parse_toolchain_block(
            {"parts": [{
                "under": "apps", "marker": "part.yaml",
                "install": _recorder(marker, "install", 2),
                "test": _recorder(marker, "test"),
            }]}
        )
        command, source, decl = resolve_verify_command_with_declaration(repo, declaration)

        result = run_completion_verification(repo, command, source, declaration=decl)

        assert result.status == "unverified"
        assert "the declared install" in result.detail and "exit 2" in result.detail
        assert _ran(marker) == ["install"]
