"""Unit tests for worktree checkpoint and rollback manager.

This test module verifies the checkpoint/rollback mechanism for AutoBuild worktrees,
ensuring proper git operations, pollution detection, and state persistence.

Test Coverage:
    - Checkpoint creation with git commits
    - Rollback to previous checkpoints
    - Context pollution detection
    - Checkpoint persistence (JSON)
    - Error handling for git operations
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from guardkit.orchestrator.worktree_checkpoints import (
    Checkpoint,
    GitCommandExecutor,
    SubprocessGitExecutor,
    WorktreeCheckpointManager,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_git_executor():
    """Create mock git executor for testing."""
    executor = Mock(spec=GitCommandExecutor)

    # Default successful git command results
    executor.execute.return_value = Mock(
        returncode=0,
        stdout="abc123def456\n",
        stderr="",
    )

    return executor


@pytest.fixture
def temp_worktree(tmp_path):
    """Create temporary worktree directory structure."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()

    # Create .guardkit directory structure
    autobuild_dir = worktree_path / ".guardkit" / "autobuild" / "TASK-001"
    autobuild_dir.mkdir(parents=True)

    return worktree_path


@pytest.fixture
def checkpoint_manager(temp_worktree, mock_git_executor):
    """Create checkpoint manager with mock git executor."""
    return WorktreeCheckpointManager(
        worktree_path=temp_worktree,
        task_id="TASK-001",
        git_executor=mock_git_executor,
    )


# ============================================================================
# Checkpoint Creation Tests
# ============================================================================


def test_create_checkpoint_success(checkpoint_manager, mock_git_executor):
    """Test successful checkpoint creation."""
    # Act
    checkpoint = checkpoint_manager.create_checkpoint(
        turn=1,
        tests_passed=True,
        test_count=15,
    )

    # Assert: Verify git commands executed
    assert mock_git_executor.execute.call_count == 3

    # git add -A
    add_call = mock_git_executor.execute.call_args_list[0]
    assert add_call[0][0] == ["git", "add", "-A"]

    # git commit
    commit_call = mock_git_executor.execute.call_args_list[1]
    assert commit_call[0][0][0] == "git"
    assert commit_call[0][0][1] == "commit"
    assert commit_call[0][0][2] == "-m"
    assert "[guardkit-checkpoint] Turn 1 complete (tests: pass)" in commit_call[0][0][3]

    # git rev-parse HEAD
    revparse_call = mock_git_executor.execute.call_args_list[2]
    assert revparse_call[0][0] == ["git", "rev-parse", "HEAD"]

    # Assert: Checkpoint record created
    assert checkpoint.turn == 1
    assert checkpoint.tests_passed is True
    assert checkpoint.test_count == 15
    assert checkpoint.commit_hash == "abc123def456"
    assert len(checkpoint_manager.checkpoints) == 1


def test_create_checkpoint_with_failing_tests(checkpoint_manager, mock_git_executor):
    """Test checkpoint creation when tests fail."""
    # Act
    checkpoint = checkpoint_manager.create_checkpoint(
        turn=2,
        tests_passed=False,
        test_count=15,
    )

    # Assert: Commit message reflects test failure
    commit_call = mock_git_executor.execute.call_args_list[1]
    assert "[guardkit-checkpoint] Turn 2 complete (tests: fail)" in commit_call[0][0][3]

    assert checkpoint.tests_passed is False


def test_create_checkpoint_multiple_turns(checkpoint_manager, mock_git_executor):
    """Test creating multiple checkpoints across turns."""
    # Setup: Different commit hashes for each turn
    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # git add
        Mock(returncode=0, stdout="", stderr=""),  # git commit
        Mock(returncode=0, stdout="commit1\n", stderr=""),  # git rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # git add
        Mock(returncode=0, stdout="", stderr=""),  # git commit
        Mock(returncode=0, stdout="commit2\n", stderr=""),  # git rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # git add
        Mock(returncode=0, stdout="", stderr=""),  # git commit
        Mock(returncode=0, stdout="commit3\n", stderr=""),  # git rev-parse
    ]

    # Act
    cp1 = checkpoint_manager.create_checkpoint(1, True, 10)
    cp2 = checkpoint_manager.create_checkpoint(2, False, 12)
    cp3 = checkpoint_manager.create_checkpoint(3, True, 15)

    # Assert
    assert len(checkpoint_manager.checkpoints) == 3
    assert cp1.commit_hash == "commit1"
    assert cp2.commit_hash == "commit2"
    assert cp3.commit_hash == "commit3"


def test_create_checkpoint_git_failure(checkpoint_manager, mock_git_executor):
    """Test checkpoint creation when git command fails."""
    # Setup: git commit fails
    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # git add succeeds
        subprocess.CalledProcessError(1, "git commit", stderr="error"),  # git commit fails
    ]

    # Act & Assert
    with pytest.raises(subprocess.CalledProcessError):
        checkpoint_manager.create_checkpoint(1, True, 10)

    # Verify no checkpoint was added
    assert len(checkpoint_manager.checkpoints) == 0


# ============================================================================
# Rollback Tests
# ============================================================================


def test_rollback_to_existing_checkpoint(checkpoint_manager, mock_git_executor):
    """Test rollback to an existing checkpoint."""
    # Setup: Create checkpoints
    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit2\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit3\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # git reset --hard
    ]

    checkpoint_manager.create_checkpoint(1, True, 10)
    checkpoint_manager.create_checkpoint(2, False, 12)
    checkpoint_manager.create_checkpoint(3, False, 15)

    # Act: Rollback to turn 1
    success = checkpoint_manager.rollback_to(1)

    # Assert: Rollback succeeded
    assert success is True

    # Verify git reset command
    reset_call = mock_git_executor.execute.call_args_list[-1]
    assert reset_call[0][0] == ["git", "reset", "--hard", "commit1"]

    # Verify checkpoints after turn 1 were removed
    assert len(checkpoint_manager.checkpoints) == 1
    assert checkpoint_manager.checkpoints[0].turn == 1


def test_rollback_to_nonexistent_checkpoint(checkpoint_manager):
    """Test rollback to a checkpoint that doesn't exist."""
    # Act
    success = checkpoint_manager.rollback_to(99)

    # Assert
    assert success is False


def test_rollback_git_failure(checkpoint_manager, mock_git_executor):
    """Test rollback when git reset fails."""
    # Setup: Create checkpoint, then fail on reset
    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
        subprocess.CalledProcessError(1, "git reset", stderr="error"),  # reset fails
    ]

    checkpoint_manager.create_checkpoint(1, True, 10)

    # Act & Assert
    with pytest.raises(subprocess.CalledProcessError):
        checkpoint_manager.rollback_to(1)


# ============================================================================
# Pollution Detection Tests
# ============================================================================


def test_should_rollback_no_pollution(checkpoint_manager, mock_git_executor):
    """Test pollution detection with no consecutive failures."""
    # Setup: Create checkpoints with mixed results
    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit2\n", stderr=""),  # rev-parse
    ]

    checkpoint_manager.create_checkpoint(1, True, 10)
    checkpoint_manager.create_checkpoint(2, True, 12)

    # Act
    should_rollback = checkpoint_manager.should_rollback()

    # Assert
    assert should_rollback is False


def test_should_rollback_two_consecutive_failures(checkpoint_manager, mock_git_executor):
    """Test pollution detection with 2 consecutive failures (default threshold)."""
    # Setup: Create checkpoints with consecutive failures
    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit2\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit3\n", stderr=""),  # rev-parse
    ]

    checkpoint_manager.create_checkpoint(1, True, 10)
    checkpoint_manager.create_checkpoint(2, False, 12)
    checkpoint_manager.create_checkpoint(3, False, 15)

    # Act
    should_rollback = checkpoint_manager.should_rollback(consecutive_failures=2)

    # Assert
    assert should_rollback is True


def test_should_rollback_custom_threshold(checkpoint_manager, mock_git_executor):
    """Test pollution detection with custom failure threshold."""
    # Setup: Create 3 consecutive failures
    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit2\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit3\n", stderr=""),  # rev-parse
    ]

    checkpoint_manager.create_checkpoint(1, False, 10)
    checkpoint_manager.create_checkpoint(2, False, 12)
    checkpoint_manager.create_checkpoint(3, False, 15)

    # Act: Require 3 consecutive failures
    should_rollback_3 = checkpoint_manager.should_rollback(consecutive_failures=3)
    should_rollback_2 = checkpoint_manager.should_rollback(consecutive_failures=2)

    # Assert
    assert should_rollback_3 is True
    assert should_rollback_2 is True


def test_find_last_passing_checkpoint(checkpoint_manager, mock_git_executor):
    """Test finding the last passing checkpoint."""
    # Setup: Create checkpoints with failures at end
    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit2\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit3\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit4\n", stderr=""),  # rev-parse
    ]

    checkpoint_manager.create_checkpoint(1, True, 10)
    checkpoint_manager.create_checkpoint(2, True, 12)
    checkpoint_manager.create_checkpoint(3, False, 15)
    checkpoint_manager.create_checkpoint(4, False, 18)

    # Act
    last_passing = checkpoint_manager.find_last_passing_checkpoint()

    # Assert
    assert last_passing == 2


def test_find_last_passing_checkpoint_none_passing(checkpoint_manager, mock_git_executor):
    """Test finding last passing checkpoint when none pass."""
    # Setup: All checkpoints failing
    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit2\n", stderr=""),  # rev-parse
    ]

    checkpoint_manager.create_checkpoint(1, False, 10)
    checkpoint_manager.create_checkpoint(2, False, 12)

    # Act
    last_passing = checkpoint_manager.find_last_passing_checkpoint()

    # Assert
    assert last_passing is None


# ============================================================================
# Persistence Tests
# ============================================================================


def test_checkpoint_persistence(temp_worktree, mock_git_executor):
    """Test checkpoint history saved to JSON file."""
    # Setup
    manager = WorktreeCheckpointManager(
        worktree_path=temp_worktree,
        task_id="TASK-001",
        git_executor=mock_git_executor,
    )

    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit2\n", stderr=""),  # rev-parse
    ]

    # Act: Create checkpoints
    manager.create_checkpoint(1, True, 10)
    manager.create_checkpoint(2, False, 12)

    # Assert: Verify JSON file created
    checkpoints_file = temp_worktree / ".guardkit" / "autobuild" / "TASK-001" / "checkpoints.json"
    assert checkpoints_file.exists()

    # Verify JSON content
    with open(checkpoints_file, "r") as f:
        data = json.load(f)

    assert data["task_id"] == "TASK-001"
    assert len(data["checkpoints"]) == 2
    assert data["checkpoints"][0]["turn"] == 1
    assert data["checkpoints"][0]["tests_passed"] is True
    assert data["checkpoints"][1]["turn"] == 2
    assert data["checkpoints"][1]["tests_passed"] is False


def test_checkpoint_loading(temp_worktree, mock_git_executor):
    """Test loading existing checkpoints from JSON file."""
    # Setup: Create checkpoints file manually
    checkpoints_file = temp_worktree / ".guardkit" / "autobuild" / "TASK-001" / "checkpoints.json"
    checkpoints_file.parent.mkdir(parents=True, exist_ok=True)

    checkpoint_data = {
        "task_id": "TASK-001",
        "checkpoints": [
            {
                "turn": 1,
                "commit_hash": "abc123",
                "timestamp": "2025-01-24T10:00:00Z",
                "tests_passed": True,
                "test_count": 10,
                "message": "[guardkit-checkpoint] Turn 1 complete (tests: pass)",
            },
            {
                "turn": 2,
                "commit_hash": "def456",
                "timestamp": "2025-01-24T10:05:00Z",
                "tests_passed": False,
                "test_count": 12,
                "message": "[guardkit-checkpoint] Turn 2 complete (tests: fail)",
            },
        ],
        "last_updated": "2025-01-24T10:05:00Z",
    }

    with open(checkpoints_file, "w") as f:
        json.dump(checkpoint_data, f)

    # Act: Initialize manager (should load existing checkpoints)
    manager = WorktreeCheckpointManager(
        worktree_path=temp_worktree,
        task_id="TASK-001",
        git_executor=mock_git_executor,
    )

    # Assert
    assert len(manager.checkpoints) == 2
    assert manager.checkpoints[0].turn == 1
    assert manager.checkpoints[0].commit_hash == "abc123"
    assert manager.checkpoints[1].turn == 2
    assert manager.checkpoints[1].commit_hash == "def456"


# ============================================================================
# Checkpoint Dataclass Tests
# ============================================================================


def test_checkpoint_to_dict():
    """Test Checkpoint serialization to dictionary."""
    checkpoint = Checkpoint(
        turn=1,
        commit_hash="abc123def456",
        timestamp="2025-01-24T10:00:00Z",
        tests_passed=True,
        test_count=15,
        message="[guardkit-checkpoint] Turn 1 complete (tests: pass)",
    )

    data = checkpoint.to_dict()

    assert data["turn"] == 1
    assert data["commit_hash"] == "abc123def456"
    assert data["tests_passed"] is True
    assert data["test_count"] == 15


def test_checkpoint_from_dict():
    """Test Checkpoint deserialization from dictionary."""
    data = {
        "turn": 2,
        "commit_hash": "def456abc789",
        "timestamp": "2025-01-24T10:05:00Z",
        "tests_passed": False,
        "test_count": 12,
        "message": "[guardkit-checkpoint] Turn 2 complete (tests: fail)",
    }

    checkpoint = Checkpoint.from_dict(data)

    assert checkpoint.turn == 2
    assert checkpoint.commit_hash == "def456abc789"
    assert checkpoint.tests_passed is False
    assert checkpoint.test_count == 12


# ============================================================================
# Utility Methods Tests
# ============================================================================


def test_get_checkpoint(checkpoint_manager, mock_git_executor):
    """Test retrieving checkpoint by turn number."""
    # Setup
    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
    ]

    checkpoint_manager.create_checkpoint(1, True, 10)

    # Act
    retrieved = checkpoint_manager.get_checkpoint(1)

    # Assert
    assert retrieved is not None
    assert retrieved.turn == 1
    assert retrieved.commit_hash == "commit1"


def test_get_checkpoint_not_found(checkpoint_manager):
    """Test retrieving non-existent checkpoint."""
    checkpoint = checkpoint_manager.get_checkpoint(99)
    assert checkpoint is None


def test_get_checkpoint_count(checkpoint_manager, mock_git_executor):
    """Test getting total checkpoint count."""
    # Setup
    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit2\n", stderr=""),  # rev-parse
    ]

    checkpoint_manager.create_checkpoint(1, True, 10)
    checkpoint_manager.create_checkpoint(2, False, 12)

    # Act
    count = checkpoint_manager.get_checkpoint_count()

    # Assert
    assert count == 2


def test_clear_checkpoints(checkpoint_manager, mock_git_executor, temp_worktree):
    """Test clearing all checkpoints."""
    # Setup
    mock_git_executor.execute.side_effect = [
        Mock(returncode=0, stdout="", stderr=""),  # add
        Mock(returncode=0, stdout="", stderr=""),  # commit
        Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
    ]

    checkpoint_manager.create_checkpoint(1, True, 10)

    # Act
    checkpoint_manager.clear_checkpoints()

    # Assert
    assert len(checkpoint_manager.checkpoints) == 0

    # Verify JSON file updated
    checkpoints_file = temp_worktree / ".guardkit" / "autobuild" / "TASK-001" / "checkpoints.json"
    with open(checkpoints_file, "r") as f:
        data = json.load(f)

    assert len(data["checkpoints"]) == 0


# ============================================================================
# SubprocessGitExecutor Tests
# ============================================================================


def test_subprocess_git_executor_success(tmp_path):
    """Test SubprocessGitExecutor with successful command."""
    executor = SubprocessGitExecutor()

    # Create a temporary git repo
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
    )

    # Act: Execute git command
    result = executor.execute(
        ["git", "status"],
        cwd=repo_path,
    )

    # Assert
    assert result.returncode == 0
    assert "On branch" in result.stdout


def test_subprocess_git_executor_failure():
    """Test SubprocessGitExecutor with failing command."""
    executor = SubprocessGitExecutor()

    # Act & Assert
    with pytest.raises(subprocess.CalledProcessError):
        executor.execute(
            ["git", "invalid-command"],
            cwd=Path("/tmp"),
        )
