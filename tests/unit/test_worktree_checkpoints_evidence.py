"""Evidence-repo checkpointing tests (TASK-AB-XREPOEV01 AC-004).

Verifies that ``WorktreeCheckpointManager`` commits and rolls back declared
sibling repos alongside the worktree, closing the BDDW-002 hazard (approved
sibling-repo work that was never versioned anywhere).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from guardkit.orchestrator.evidence_repos import EvidenceRepo
from guardkit.orchestrator.worktree_checkpoints import (
    Checkpoint,
    GitCommandExecutor,
    WorktreeCheckpointManager,
)


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "t@t"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "t"],
        check=True,
        capture_output=True,
    )
    (path / ".keep").write_text("x\n")
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", "init"],
        check=True,
        capture_output=True,
    )


def _head(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def worktree_and_sibling(tmp_path):
    worktree = tmp_path / "worktree"
    sibling = tmp_path / "guardkitfactory"
    _init_repo(worktree)
    _init_repo(sibling)
    return worktree, sibling


class TestEvidenceRepoCheckpoint:
    def test_checkpoint_commits_sibling_repo_work(self, worktree_and_sibling):
        worktree, sibling = worktree_and_sibling
        repo = EvidenceRepo(name="guardkitfactory", root=sibling)
        manager = WorktreeCheckpointManager(
            worktree_path=worktree, task_id="TASK-X", evidence_repos=[repo]
        )

        # Player writes only in the sibling repo.
        (sibling / "src").mkdir()
        (sibling / "src" / "deliverable.py").write_text("def f(): return 1\n")
        sibling_head_before = _head(sibling)

        cp = manager.create_checkpoint(turn=1, tests_passed=True, test_count=3)

        # Sibling work is now committed and recorded on the checkpoint.
        assert "guardkitfactory" in cp.evidence_commits
        assert cp.evidence_commits["guardkitfactory"] == _head(sibling)
        assert _head(sibling) != sibling_head_before
        # The deliverable is versioned (tracked, clean tree).
        status = subprocess.run(
            ["git", "-C", str(sibling), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        assert status.stdout.strip() == ""

    def test_rollback_resets_sibling_repo(self, worktree_and_sibling):
        worktree, sibling = worktree_and_sibling
        repo = EvidenceRepo(name="guardkitfactory", root=sibling)
        manager = WorktreeCheckpointManager(
            worktree_path=worktree, task_id="TASK-X", evidence_repos=[repo]
        )

        # Turn 1: good sibling work, checkpoint.
        (sibling / "good.py").write_text("ok = True\n")
        manager.create_checkpoint(turn=1, tests_passed=True)
        good_head = _head(sibling)

        # Turn 2: polluted sibling work, checkpoint.
        (sibling / "bad.py").write_text("broken = True\n")
        manager.create_checkpoint(turn=2, tests_passed=False)
        assert (sibling / "bad.py").exists()

        # Roll back to turn 1.
        assert manager.rollback_to(1) is True
        assert _head(sibling) == good_head
        assert (sibling / "good.py").exists()
        assert not (sibling / "bad.py").exists()  # polluted work discarded

    def test_no_evidence_repos_is_unchanged_behaviour(self, worktree_and_sibling):
        worktree, _ = worktree_and_sibling
        manager = WorktreeCheckpointManager(worktree_path=worktree, task_id="TASK-X")
        cp = manager.create_checkpoint(turn=1, tests_passed=True)
        assert cp.evidence_commits == {}

    def test_hung_sibling_commit_times_out_and_does_not_deadlock(self, tmp_path):
        # HIGH review fix: a hung git in the sibling repo must time out (it
        # holds a cross-process lock), return None, and not abort the worktree
        # checkpoint. The evidence repo's commits raise TimeoutExpired; the
        # worktree commits succeed.
        worktree = tmp_path / "worktree"
        _init_repo(worktree)
        factory = tmp_path / "guardkitfactory"
        factory.mkdir()
        repo = EvidenceRepo(name="guardkitfactory", root=factory)

        ok = Mock(returncode=0, stdout="abc123\n", stderr="")

        def fake_execute(command, cwd, check=True, timeout=None):
            if Path(cwd) == factory:
                raise subprocess.TimeoutExpired(cmd=command, timeout=timeout or 0)
            return ok

        executor = Mock(spec=GitCommandExecutor)
        executor.execute.side_effect = fake_execute

        manager = WorktreeCheckpointManager(
            worktree_path=worktree,
            task_id="TASK-X",
            git_executor=executor,
            evidence_repos=[repo],
        )
        cp = manager.create_checkpoint(turn=1, tests_passed=True)
        assert cp.commit_hash == "abc123"  # worktree checkpoint still landed
        assert "guardkitfactory" not in cp.evidence_commits  # timed out -> unversioned

    def test_failed_sibling_commit_does_not_abort_checkpoint(self, tmp_path):
        # Sibling path is not a git repo -> per-repo commit returns None, but
        # the worktree checkpoint still succeeds (best-effort).
        worktree = tmp_path / "worktree"
        _init_repo(worktree)
        not_a_repo = tmp_path / "plain"
        not_a_repo.mkdir()
        repo = EvidenceRepo(name="plain", root=not_a_repo)
        manager = WorktreeCheckpointManager(
            worktree_path=worktree, task_id="TASK-X", evidence_repos=[repo]
        )
        cp = manager.create_checkpoint(turn=1, tests_passed=True)
        assert cp.commit_hash  # worktree checkpoint landed
        assert "plain" not in cp.evidence_commits


class TestCheckpointBackwardCompat:
    def test_old_checkpoint_json_without_evidence_commits(self):
        # checkpoints.json written before evidence support has no
        # evidence_commits key; Checkpoint(**data) must still deserialise.
        old = {
            "turn": 1,
            "commit_hash": "abc123",
            "timestamp": "2026-01-01T00:00:00",
            "tests_passed": True,
            "test_count": 5,
            "message": "old",
            "from_prior_run": False,
        }
        cp = Checkpoint.from_dict(old)
        assert cp.evidence_commits == {}

    def test_roundtrip_with_evidence_commits(self):
        cp = Checkpoint(
            turn=2,
            commit_hash="def456",
            timestamp="2026-01-01T00:00:00",
            tests_passed=True,
            evidence_commits={"guardkitfactory": "sha999"},
        )
        restored = Checkpoint.from_dict(cp.to_dict())
        assert restored.evidence_commits == {"guardkitfactory": "sha999"}
