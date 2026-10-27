"""A checkpoint lookup in a repair round prefers this round's checkpoint.

When a gate re-opens an approved task, the repair round numbers its turns from
1 again and appends to the same ``checkpoints.json``, so one task's list reads
``[1, 2, 1, 2, 3, 4]`` (20 October 2026). A lookup by turn number returns the
latest matching checkpoint, which is this round's.

(27 October 2026 cull: the context-pollution rollback these tests also drove
is deleted; the lookup stays.) Driven on a real git repository through the
real ``WorktreeCheckpointManager``; every file here is invented.
"""

from __future__ import annotations

import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import List

import pytest

from guardkit.orchestrator.worktree_checkpoints import WorktreeCheckpointManager
from guardkit.orchestrator.task_work_scope import (
    checkout_lease, register_fresh_checkout,
)

TASK_ID = "TASK-CKPT-001"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "autobuild/FEAT-CKPT")
    _git(root, "config", "user.email", "factory@example.invalid")
    _git(root, "config", "user.name", "Factory Test")
    _git(root, "config", "commit.gpgsign", "false")
    (root / "base.txt").write_text("base\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    register_fresh_checkout(root, _git(root, "rev-parse", "HEAD"))
    return root


def _turn(manager: WorktreeCheckpointManager, root: Path, name: str, turn: int, passed):
    (root / f"{name}.txt").write_text(f"{name}\n")
    return manager.create_checkpoint(turn, passed)


@contextmanager
def _manager(repo: Path, round_number: str = "initial"):
    with checkout_lease(repo) as lease:
        scope = lease.admit(TASK_ID, round_id=round_number)
        yield WorktreeCheckpointManager(repo, TASK_ID, task_work_scope=scope)


@contextmanager
def _two_rounds(repo: Path, round_two: List):
    """An approved first scope, then a separately admitted repair scope."""
    with _manager(repo) as first:
        _turn(first, repo, "round1-turn1", 1, True)
        _turn(first, repo, "round1-turn2-approved", 2, True)
    with _manager(repo, "2") as second:
        for turn, passed in enumerate(round_two, start=1):
            _turn(second, repo, f"round2-turn{turn}", turn, passed)
        yield second


class TestARepairRoundLooksUpItsOwnCheckpoint:
    def test_a_lookup_prefers_this_rounds_checkpoint(self, repo: Path) -> None:
        with _two_rounds(repo, [True, False]) as manager:
            assert manager.get_checkpoint(2) is manager.checkpoints[3]
            # A reader may still find an earlier round's turn by number.
            manager.checkpoints = manager.checkpoints[:3]
            assert manager.get_checkpoint(2) is manager.checkpoints[1]

