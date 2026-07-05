"""FEAT-10AC run-2 regression: sibling test_command pins to the sibling venv.

Reproduces TASK-FIX-SIBTESTENV01 AC-1 with a REAL ``python -m venv`` sibling
repo: a dependency injected into the sibling venv's site-packages is
importable only under ``<sibling>/.venv/bin/python``. Pre-fix, the sibling
``test_command`` was pinned to the CALLER's (guardkit worktree) interpreter
— which cannot import the sibling's dependency set — producing a
guaranteed-broken exit-2 "ran and failed" verdict in the wrong environment
(the FEAT-10AC run-2 kill mechanism). Post-fix, per-repo interpreter
resolution pins the command to the sibling's own venv and the suite passes.
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


class TestSiblingVenvInterpreterRegression:
    def test_sibling_command_passes_under_sibling_venv(self, sibling_repo):
        """AC-1: the bare-`python` test_command runs under the sibling venv.

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
            test_command="python check_env.py",
        )
        result = ev.run_repo_tests(repo)
        assert result.ran is True
        assert result.passed is True
        assert result.returncode == 0

    def test_resolved_interpreter_is_the_sibling_venv_python(self, sibling_repo):
        """REC-3: pin the mechanism, not just the outcome — the resolved
        interpreter must BE the sibling's ``.venv/bin/python``."""
        repo = ev.EvidenceRepo(name="sibling", root=sibling_repo)
        resolved = ev._resolve_repo_interpreter(repo)
        assert resolved is not None
        assert Path(resolved) == sibling_repo / ".venv" / "bin" / "python"
