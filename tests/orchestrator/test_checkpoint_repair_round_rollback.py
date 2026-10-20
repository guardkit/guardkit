"""A rollback in a repair round never lands on an earlier round's checkpoint.

When a gate re-opens an approved task, the repair round numbers its turns from
1 again and appends to the same ``checkpoints.json``, so one task's list reads
``[1, 2, 1, 2, 3, 4]`` (20 October 2026). A rollback looked a turn number up
and took the FIRST match, which is the earlier round's checkpoint: a
context-pollution rollback in the repair round reset the worktree to before
work that had already been approved.

Now a lookup prefers this round's checkpoints (the latest matching one), a
rollback only ever targets this round, and the list is cut by position.
Driven on a real git repository through the real ``WorktreeCheckpointManager``;
every file here is invented.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List

import pytest

from guardkit.orchestrator.worktree_checkpoints import WorktreeCheckpointManager

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
    return root


def _turn(manager: WorktreeCheckpointManager, root: Path, name: str, turn: int, passed):
    (root / f"{name}.txt").write_text(f"{name}\n")
    return manager.create_checkpoint(turn, passed)


def _two_rounds(repo: Path, round_two: List) -> WorktreeCheckpointManager:
    """Round 1 (approved: turns 1 and 2 pass), then a re-opened round 2."""
    first = WorktreeCheckpointManager(repo, TASK_ID)
    _turn(first, repo, "round1-turn1", 1, True)
    _turn(first, repo, "round1-turn2-approved", 2, True)
    # The repair round is a new orchestrator session on the same task.
    second = WorktreeCheckpointManager(repo, TASK_ID)
    for turn, passed in enumerate(round_two, start=1):
        _turn(second, repo, f"round2-turn{turn}", turn, passed)
    return second


class TestARepairRoundRollsBackWithinItself:
    def test_pollution_rollback_keeps_the_approved_round(self, repo: Path) -> None:
        manager = _two_rounds(repo, [True, False, False, False])
        assert [cp.turn for cp in manager.checkpoints] == [1, 2, 1, 2, 3, 4]
        assert manager.should_rollback()

        target = manager.find_last_passing_checkpoint()
        assert target == 1
        assert manager.rollback_to(target) is True

        round_two_turn_one = manager.checkpoints[-1]
        assert _git(repo, "rev-parse", "HEAD") == round_two_turn_one.commit_hash
        # The approved round's work is still there; the polluted turns are gone.
        assert (repo / "round1-turn2-approved.txt").exists()
        assert (repo / "round2-turn1.txt").exists()
        assert not (repo / "round2-turn4.txt").exists()
        assert [cp.turn for cp in manager.checkpoints] == [1, 2, 1]

    def test_no_passing_turn_in_this_round_is_no_target(self, repo: Path) -> None:
        manager = _two_rounds(repo, [False, False, False])
        assert manager.find_last_passing_checkpoint() is None

    def test_a_turn_this_round_never_reached_is_not_rolled_back_to(self, repo: Path) -> None:
        manager = _two_rounds(repo, [True])
        head = _git(repo, "rev-parse", "HEAD")
        assert manager.rollback_to(2) is False
        assert _git(repo, "rev-parse", "HEAD") == head

    def test_a_lookup_prefers_this_rounds_checkpoint(self, repo: Path) -> None:
        manager = _two_rounds(repo, [True, False])
        assert manager.get_checkpoint(2) is manager.checkpoints[3]
        # A reader may still find an earlier round's turn by number.
        manager.checkpoints = manager.checkpoints[:3]
        assert manager.get_checkpoint(2) is manager.checkpoints[1]


class TestASingleRoundIsUnchanged:
    def test_rollback_in_the_only_round(self, repo: Path) -> None:
        manager = WorktreeCheckpointManager(repo, TASK_ID)
        commits = [
            _turn(manager, repo, f"turn{n}", n, n <= 2).commit_hash for n in (1, 2, 3, 4)
        ]
        assert manager.find_last_passing_checkpoint() == 2
        assert manager.rollback_to(2) is True
        assert _git(repo, "rev-parse", "HEAD") == commits[1]
        assert [cp.turn for cp in manager.checkpoints] == [1, 2]
