"""``guardkit autobuild task`` says when the project declares no install.

Installs come only from the project's declaration (1 November 2026). A feature
build and the work leg say "no install declared; nothing installed" once per
build. A standalone ``guardkit autobuild task`` makes its own worktree and has
neither of those steps, and the per-turn install check stays quiet when
nothing is declared, so the standalone command never said it (Codex review of
the change, finding R2). It now says it once, during setup.

A declared install ran, in a standalone build, only from the per-turn check,
after the first builder turn, while a feature build runs it before the agents
start. Since 1 November 2026 the standalone build runs it at setup, before the
first turn.

These tests drive the real command through click on a real git repository:
the worktree, the task file and the declaration are real. Only the
Player/Coach loop (``_orchestrate_owned``) is replaced, because it needs a
model.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
from pathlib import Path
from typing import List

import pytest
import yaml
from click.testing import CliRunner

from guardkit.cli.main import cli
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, OrchestrationResult
from guardkit.orchestrator.environment_bootstrap import (
    NO_INSTALL_DECLARED,
    rerun_declared_install_if_due,
)

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


def _declare_install(root: Path, install: str = "true") -> None:
    (root / ".guardkit").mkdir(exist_ok=True)
    (root / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": {"install": install, "test": "true"}}),
        encoding="utf-8",
    )
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "declare an install")


installed_before_first_turn: List[bool] = []


@pytest.fixture
def worktrees_seen(monkeypatch: pytest.MonkeyPatch) -> List[Path]:
    """Replace the Player/Coach loop with an approval; record its worktree,
    and whether the declared install's marker was there when it started."""
    seen: List[Path] = []
    installed_before_first_turn.clear()

    def _approved(self, task_id, requirements, acceptance_criteria, base_branch, **kwargs):
        worktree = Path(self._existing_worktree.path)
        seen.append(worktree)
        # What the first turn would find: did the declared install run yet?
        installed_before_first_turn.append((worktree / "installed.txt").exists())
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


def _run_task(caplog: pytest.LogCaptureFixture, *extra: str):
    with caplog.at_level(logging.INFO, logger="guardkit"):
        return CliRunner().invoke(
            cli, ["autobuild", "task", TASK_ID, "--no-checkpoints", *extra],
            catch_exceptions=False,
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


def test_a_standalone_task_runs_the_declared_install_before_the_first_turn(
    repo: Path, worktrees_seen: List[Path], caplog: pytest.LogCaptureFixture
) -> None:
    _declare_install(repo, install="touch installed.txt")

    result = _run_task(caplog)

    assert result.exit_code == 0, result.output
    assert len(worktrees_seen) == 1
    worktree = worktrees_seen[0]
    # The install ran in the build's worktree, before the first turn began.
    assert installed_before_first_turn == [True]
    assert not (repo / "installed.txt").exists()
    messages = [r.getMessage() for r in caplog.records]
    assert "Environment: the declared install `touch installed.txt` ran and succeeded" in messages
    # The first turn's own check finds it already done for these files.
    again = rerun_declared_install_if_due(worktree)
    assert again is not None and again.skipped and again.success


# Holds the checkout's writer lease in another process until a line arrives
# on stdin, the way a still-running build holds it.
_HOLD_LEASE = """
import sys
from guardkit.orchestrator.task_work_scope import checkout_lease
with checkout_lease(sys.argv[1]):
    print("held", flush=True)
    sys.stdin.readline()
"""


def test_a_resume_installs_only_once_it_holds_the_checkout_lease(
    repo: Path, worktrees_seen: List[Path], caplog: pytest.LogCaptureFixture
) -> None:
    """A ``--resume`` started while another build still owns the worktree
    waits for the writer lease before it installs (Codex review R1,
    1 November 2026): it never installs under that build's builder or
    tests."""
    first = _run_task(caplog)
    assert first.exit_code == 0, first.output
    worktree = worktrees_seen[0]
    marker = worktree / "installed.txt"
    # A declared install that is due when the build resumes.
    (worktree / ".guardkit").mkdir(exist_ok=True)
    (worktree / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": {"install": "touch installed.txt", "test": "true"}}),
        encoding="utf-8",
    )

    holder = subprocess.Popen(
        [sys.executable, "-c", _HOLD_LEASE, str(worktree)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    try:
        assert holder.stdout.readline().strip() == "held"
        seen_while_held: List[bool] = []

        def _release_later() -> None:
            # Long enough for the resume to reach the lease and wait on it.
            threading.Event().wait(2.0)
            seen_while_held.append(marker.exists())
            holder.stdin.write("release\n")
            holder.stdin.flush()

        releaser = threading.Thread(target=_release_later)
        releaser.start()
        resumed = _run_task(caplog, "--resume")
        releaser.join(timeout=30)
    finally:
        if holder.poll() is None:
            holder.kill()
        holder.wait(timeout=30)

    assert resumed.exit_code == 0, resumed.output
    assert len(worktrees_seen) == 2 and worktrees_seen[1] == worktree
    # Not installed while the other build held the lease; installed after.
    assert seen_while_held == [False]
    assert marker.exists()
