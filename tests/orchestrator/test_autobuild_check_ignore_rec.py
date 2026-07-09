"""Tests for ``AutoBuildOrchestrator._git_check_ignore_rec`` negation guard.

Red-baseline retro (2026-07-08, L12 item 6): the best-effort operator
recommendation appended to a claim-audit top claim must NOT report a
``!``-negation re-include as "Path matches a .gitignore rule". Pre-fix, a
tracked file under ``!app/lib/**`` produced a phantom gitignore
recommendation that steered the Player off the real failure.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git("init", "--initial-branch=main", cwd=tmp_path)
    _git("config", "user.email", "t@e.com", cwd=tmp_path)
    _git("config", "user.name", "T", cwd=tmp_path)
    return tmp_path


def test_negation_reinclude_produces_no_recommendation(repo: Path) -> None:
    (repo / ".gitignore").write_text("lib/\n!app/lib/\n!app/lib/**\n")
    src = repo / "app" / "lib" / "ui"
    src.mkdir(parents=True)
    (src / "session_screen.dart").write_text("class S {}\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-m", "re-included file", cwd=repo)

    rec = AutoBuildOrchestrator._git_check_ignore_rec(
        "app/lib/ui/session_screen.dart", repo
    )
    assert rec is None


def test_plain_ignore_still_produces_recommendation(repo: Path) -> None:
    (repo / ".gitignore").write_text("build/\n")
    rec = AutoBuildOrchestrator._git_check_ignore_rec("build/out.txt", repo)
    assert rec is not None
    assert "build/" in rec
