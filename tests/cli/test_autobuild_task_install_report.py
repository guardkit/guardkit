"""``guardkit autobuild task`` says when the project declares no install.

Installs come only from the project's declaration (1 November 2026). A feature
build and the work leg say "no install declared; nothing installed" once per
build. A standalone ``guardkit autobuild task`` makes its own worktree and has
neither of those steps, and the per-turn install check stays quiet when
nothing is declared, so the standalone command never said it (Codex review of
the change, finding R2). It now says it once, during setup.

These tests drive the real command through click on a real git repository:
the worktree, the task file and the declaration are real. Only the
Player/Coach loop (``_orchestrate_owned``) is replaced, because it needs a
model.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import List

import pytest
import yaml
from click.testing import CliRunner

from guardkit.cli.main import cli
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, OrchestrationResult
from guardkit.orchestrator.environment_bootstrap import NO_INSTALL_DECLARED

TASK_ID = "TASK-NI-001"

TASK_FILE = f"""---
id: {TASK_ID}
title: Add a greeting
status: backlog
---

# Add a greeting

## Requirements
Add a greeting function.

## Acceptance Criteria
- [ ] greet() returns "hello"
"""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repository with one backlog task; the command runs from its root."""
    root = tmp_path / "repo"
    (root / "tasks" / "backlog").mkdir(parents=True)
    (root / "tasks" / "backlog" / f"{TASK_ID}.md").write_text(TASK_FILE, encoding="utf-8")
    (root / "app.py").write_text("x = 1\n", encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "start")
    monkeypatch.chdir(root)
    return root


def _declare_install(root: Path) -> None:
    (root / ".guardkit").mkdir(exist_ok=True)
    (root / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": {"install": "true", "test": "true"}}),
        encoding="utf-8",
    )
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "declare an install")


@pytest.fixture
def worktrees_seen(monkeypatch: pytest.MonkeyPatch) -> List[Path]:
    """Replace the Player/Coach loop with an approval; record its worktree."""
    seen: List[Path] = []

    def _approved(self, task_id, requirements, acceptance_criteria, base_branch, **kwargs):
        seen.append(Path(self._existing_worktree.path))
        return OrchestrationResult(
            task_id=task_id,
            success=True,
            total_turns=1,
            final_decision="approved",
            turn_history=[],
            worktree=self._existing_worktree,
        )

    monkeypatch.setattr(AutoBuildOrchestrator, "_orchestrate_owned", _approved)
    return seen


def _run_task(caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.INFO, logger="guardkit"):
        return CliRunner().invoke(
            cli, ["autobuild", "task", TASK_ID, "--no-checkpoints"], catch_exceptions=False
        )


def _said(caplog: pytest.LogCaptureFixture) -> List[str]:
    return [r.getMessage() for r in caplog.records if NO_INSTALL_DECLARED in r.getMessage()]


def test_a_standalone_task_says_once_that_nothing_is_installed(
    repo: Path, worktrees_seen: List[Path], caplog: pytest.LogCaptureFixture
) -> None:
    result = _run_task(caplog)

    assert result.exit_code == 0, result.output
    assert len(worktrees_seen) == 1
    # The worktree is the build's own, not the checkout the command ran in.
    assert worktrees_seen[0] != repo
    assert _said(caplog) == [f"Environment: {NO_INSTALL_DECLARED}"]
    assert not (worktrees_seen[0] / ".venv").exists()


def test_a_standalone_task_with_a_declared_install_does_not_say_it(
    repo: Path, worktrees_seen: List[Path], caplog: pytest.LogCaptureFixture
) -> None:
    _declare_install(repo)

    result = _run_task(caplog)

    assert result.exit_code == 0, result.output
    assert len(worktrees_seen) == 1
    assert _said(caplog) == []
