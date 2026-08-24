"""Tests for the optional ``message`` kwarg on ``WorktreeManager.merge``.

The contract (make-merge-work spec, 2026-08-24): ``message=None`` keeps the
historical ``"Merge {task_id} from AutoBuild"`` commit message byte-
identically; a provided message is used verbatim. No other behavior change.

Real git in tmp_path — no mocks of git.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from guardkit.worktrees.manager import (
    Worktree,
    WorktreeManager,
    WorktreeMergeError,
)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


@pytest.fixture
def repo_with_branch(tmp_path: Path):
    """A repo on main with a clean-merging autobuild/TASK-M branch.

    Returns (repo, worktree). The worktree's path deliberately does not
    exist — ``merge`` reads only task_id/branch_name (the _find_worktree
    reconstruction pattern).
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "checkout", "-q", "-b", "autobuild/TASK-M")
    (repo / "work.txt").write_text("work\n", encoding="utf-8")
    _git(repo, "add", "work.txt")
    _git(repo, "commit", "-q", "-m", "task work")
    _git(repo, "checkout", "-q", "main")

    worktree = Worktree(
        task_id="TASK-M",
        branch_name="autobuild/TASK-M",
        path=repo / ".guardkit" / "worktrees" / "TASK-M",
        base_branch="main",
    )
    return repo, worktree


class TestDefaultMessage:
    def test_none_keeps_the_historical_message_byte_identically(
        self, repo_with_branch
    ):
        repo, worktree = repo_with_branch
        manager = WorktreeManager(repo_root=repo)

        manager.merge(worktree, target_branch="main")

        # %B is the raw body; strip only the trailing newline git appends.
        message = _git(repo, "log", "-1", "--format=%B", "main").strip()
        assert message == "Merge TASK-M from AutoBuild"

    def test_omitting_the_kwarg_is_the_none_path(self, repo_with_branch):
        repo, worktree = repo_with_branch
        manager = WorktreeManager(repo_root=repo)

        # Positional call exactly as existing callers make it.
        manager.merge(worktree, "main")

        message = _git(repo, "log", "-1", "--format=%s", "main")
        assert message == "Merge TASK-M from AutoBuild"


class TestProvidedMessage:
    def test_message_is_used_verbatim_including_body(self, repo_with_branch):
        repo, worktree = repo_with_branch
        manager = WorktreeManager(repo_root=repo)
        custom = (
            "merge(TASK-M): merged on the merge word\n\n"
            "abc123def456..fed654cba321 — branch autobuild/TASK-M retained "
            "as the rollback path"
        )

        manager.merge(worktree, target_branch="main", message=custom)

        message = _git(repo, "log", "-1", "--format=%B", "main").strip()
        assert message == custom


class TestNoOtherBehaviorChange:
    def test_conflict_still_raises_worktree_merge_error(self, tmp_path: Path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "t@t.t")
        _git(repo, "config", "user.name", "t")
        (repo / "shared.txt").write_text("base\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "base")
        _git(repo, "checkout", "-q", "-b", "autobuild/TASK-M")
        (repo / "shared.txt").write_text("branch\n", encoding="utf-8")
        _git(repo, "commit", "-aqm", "branch edit")
        _git(repo, "checkout", "-q", "main")
        (repo / "shared.txt").write_text("main\n", encoding="utf-8")
        _git(repo, "commit", "-aqm", "main edit")

        worktree = Worktree(
            task_id="TASK-M",
            branch_name="autobuild/TASK-M",
            path=repo / ".guardkit" / "worktrees" / "TASK-M",
            base_branch="main",
        )
        manager = WorktreeManager(repo_root=repo)

        with pytest.raises(WorktreeMergeError):
            manager.merge(worktree, target_branch="main", message="custom")

        # Leave the fixture tidy (mirrors the executor's abort discipline).
        subprocess.run(
            ["git", "merge", "--abort"], cwd=str(repo), capture_output=True
        )
