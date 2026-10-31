"""FEAT-10AC run-2 regression: sibling tests never run under the caller's venv.

Reproduces TASK-FIX-SIBTESTENV01 AC-1 with a REAL ``python -m venv`` sibling
repo: a dependency injected into the sibling venv's site-packages is
importable only under ``<sibling>/.venv/bin/python``. Pre-fix, the sibling
``test_command`` was pinned to the CALLER's (guardkit worktree) interpreter
— which cannot import the sibling's dependency set — producing a
guaranteed-broken exit-2 "ran and failed" verdict in the wrong environment
(the FEAT-10AC run-2 kill mechanism). Since 31 October 2026 nothing is
pinned at all: the declared command runs exactly as written, so a sibling
that needs its own venv names it in its ``test_command``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from guardkit.orchestrator import evidence_repos as ev


@pytest.fixture(scope="module")
def sibling_repo(tmp_path_factory) -> Path:
    """A sibling repo with its own real venv carrying a private dependency.

    ``--without-pip`` keeps venv creation fast; the injected module is
    dropped straight into site-packages, so nothing in the venv needs pip.
    """
    root = tmp_path_factory.mktemp("sibling")
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(root / ".venv")],
        check=True,
        capture_output=True,
    )
    site_packages = next((root / ".venv" / "lib").glob("python*/site-packages"))
    (site_packages / "sibling_only_dep.py").write_text("MARKER = 'sibling'\n")
    # The FEAT-10AC shape: a bare `python`-headed test_command running a
    # check that only works inside the sibling's own environment.
    (root / "check_env.py").write_text(
        "import sibling_only_dep\n"
        "assert sibling_only_dep.MARKER == 'sibling'\n"
    )
    return root


def _run_sibling(repo: "ev.EvidenceRepo", tmp_path: Path):
    from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator

    worktree = tmp_path / "worktree"
    worktree.mkdir(exist_ok=True)
    return CoachValidator(str(worktree), evidence_repos=[repo])._run_sibling_tests(repo)


class TestSiblingVenvInterpreterRegression:
    # 31 October 2026: the bare-`python` command is no longer rewritten to
    # the sibling's ``.venv`` (a hidden Python default, removed). The sibling
    # names its interpreter in its command, and that one runs; the caller's
    # interpreter is still never used.

    def test_sibling_command_passes_under_the_venv_it_names(
        self, sibling_repo, tmp_path
    ):
        """AC-1: the command naming the sibling's venv runs under it.

        Control first: the caller's interpreter (what the pre-fix code
        pinned to) CANNOT import the sibling-only dependency — proving that
        the pass below can only come from the sibling's own interpreter.
        """
        control = subprocess.run(
            [sys.executable, "-c", "import sibling_only_dep"],
            capture_output=True,
        )
        assert control.returncode != 0, (
            "precondition: sibling_only_dep must NOT be importable by the "
            "caller interpreter"
        )

        repo = ev.EvidenceRepo(
            name="sibling",
            root=sibling_repo,
            test_command=".venv/bin/python check_env.py",
        )
        result = _run_sibling(repo, tmp_path)
        assert result.check_could_not_run is False
        assert result.tests_passed is True
        assert result.exit_code == 0

    def test_a_bare_python_command_is_not_moved_into_the_sibling_venv(
        self, sibling_repo, tmp_path
    ):
        """Replaces the check that the sibling's venv was resolved: a bare
        ``python`` is whatever ``python`` the command's PATH holds, never the
        sibling's ``.venv`` found behind the declaration's back."""
        repo = ev.EvidenceRepo(
            name="sibling",
            root=sibling_repo,
            test_command="python check_env.py",
        )
        result = _run_sibling(repo, tmp_path)
        assert result.tests_passed is False
        assert not hasattr(ev, "_resolve_repo_interpreter")
