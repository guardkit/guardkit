"""``guardkit autobuild task TASK-ID --resume`` goes on in the saved checkout.

Step 2 (26-27 October 2026): the single-task resume refusal was deleted, but
``orchestrate`` still asked the worktree manager for a fresh checkout, which
refuses an existing one ("Existing checkout or branch ... is preserved"), so
the resume path was never reached. A resumed build now reuses the checkout it
left, under the same exclusive lease.

This drives the real CLI command against a real git repository and a real
saved checkout made by ``WorktreeManager.create``. Only the SDK presence check
is stubbed, and the run is stopped just after the resume step hands back the
checkout it will continue in.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from guardkit.cli.autobuild import task
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.worktrees import WorktreeManager

TASK_ID = "TASK-RS-001"


class _Stop(Exception):
    """Ends the run once the resume step has returned."""


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=cwd, check=True, capture_output=True,
    )


def test_resume_reuses_the_saved_checkout(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    task_file = repo / "tasks" / "in_progress" / f"{TASK_ID}-resume-me.md"
    task_file.parent.mkdir(parents=True)
    task_file.write_text(
        f"---\nid: {TASK_ID}\ntitle: Resume me\nstatus: in_progress\n"
        "task_type: feature\n---\n\n# Resume me\n\n"
        "## Acceptance Criteria\n\n- [ ] It resumes\n",
        encoding="utf-8",
    )
    (repo / ".gitignore").write_text(".guardkit/\n", encoding="utf-8")
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "start", cwd=repo)
    saved = WorktreeManager(repo_root=repo).create(task_id=TASK_ID, base_branch="main")
    (saved.path / "work-so-far.txt").write_text("from the interrupted run\n", encoding="utf-8")

    reached = {}
    real_resume = AutoBuildOrchestrator._resume_from_state

    def _resume_then_stop(self, task_id, task_file_path):
        worktree, start_turn = real_resume(self, task_id, task_file_path)
        reached["path"] = Path(worktree.path).resolve()
        raise _Stop()

    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "guardkit.cli.autobuild._require_sdk_for_selected_harness", lambda: None
    )
    monkeypatch.setattr(AutoBuildOrchestrator, "_resume_from_state", _resume_then_stop)

    result = CliRunner().invoke(task, [TASK_ID, "--resume"], catch_exceptions=True)

    assert "Existing checkout or branch" not in result.output, result.output
    assert reached.get("path") == saved.path.resolve(), result.output
    # The interrupted run's work is still there to continue from.
    assert (saved.path / "work-so-far.txt").exists()
