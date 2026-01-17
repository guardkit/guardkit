"""
Unit tests for WorktreeManager class.

These tests use a mock CommandExecutor to avoid creating real git worktrees,
ensuring fast, isolated, and deterministic test execution.

Test coverage targets:
- Worktree dataclass validation
- WorktreeManager initialization and validation
- Worktree creation with various scenarios
- Merge operations including conflict detection
- Cleanup operations with force flag
- Preserve on failure behavior
- Error handling for all failure modes
"""

import subprocess
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, call

import pytest

from lib.orchestrator.worktrees import (
    CommandExecutor,
    Worktree,
    WorktreeError,
    WorktreeCreationError,
    WorktreeManager,
    WorktreeMergeError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


class MockCommandExecutor:
    """
    Mock implementation of CommandExecutor for testing.

    This mock tracks all git commands executed and allows tests to simulate
    success/failure scenarios without running actual git commands.
    """

    def __init__(self):
        """Initialize mock with empty call history."""
        self.calls: list[tuple[list[str], Optional[Path]]] = []
        self.should_fail: bool = False
        self.fail_on_command: Optional[str] = None
        self.return_stdout: str = ""

    def run(
        self,
        args: list[str],
        cwd: Optional[Path] = None,
        check: bool = True,
        capture_output: bool = True,
        text: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Mock command execution.

        Tracks the call and either succeeds or fails based on configuration.
        """
        self.calls.append((args, cwd))

        # Simulate failure if configured
        if self.should_fail:
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=args,
                stderr="Mock git error",
            )

        # Simulate failure for specific command
        if self.fail_on_command and self.fail_on_command in " ".join(args):
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=args,
                stderr=f"Mock error for {self.fail_on_command}",
            )

        # Return success
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=self.return_stdout,
            stderr="",
        )


@pytest.fixture
def mock_executor():
    """Provide a fresh MockCommandExecutor for each test."""
    return MockCommandExecutor()


@pytest.fixture
def temp_repo_root(tmp_path):
    """Provide a temporary directory as mock repo root."""
    return tmp_path / "test_repo"


@pytest.fixture
def manager(temp_repo_root, mock_executor):
    """
    Provide a WorktreeManager instance with mock executor.

    This fixture creates a manager that won't execute real git commands.
    """
    # Create the repo directory
    temp_repo_root.mkdir(parents=True, exist_ok=True)

    # Create manager with mock executor
    return WorktreeManager(
        repo_root=temp_repo_root,
        executor=mock_executor,
    )


# ============================================================================
# Worktree Dataclass Tests
# ============================================================================


class TestWorktreeDataclass:
    """Test Worktree dataclass behavior."""

    def test_worktree_creation_success(self):
        """Test successful worktree instance creation."""
        worktree = Worktree(
            task_id="TASK-AB-001",
            branch_name="autobuild/TASK-AB-001",
            path=Path("/tmp/worktree"),
            base_branch="main",
        )

        assert worktree.task_id == "TASK-AB-001"
        assert worktree.branch_name == "autobuild/TASK-AB-001"
        assert worktree.path == Path("/tmp/worktree")
        assert worktree.base_branch == "main"

    def test_worktree_is_immutable(self):
        """Test that Worktree is frozen (immutable)."""
        worktree = Worktree(
            task_id="TASK-AB-001",
            branch_name="autobuild/TASK-AB-001",
            path=Path("/tmp/worktree"),
            base_branch="main",
        )

        with pytest.raises(AttributeError):
            worktree.task_id = "TASK-AB-002"

    def test_worktree_validates_task_id(self):
        """Test validation of empty task_id."""
        with pytest.raises(ValueError, match="task_id cannot be empty"):
            Worktree(
                task_id="",
                branch_name="autobuild/test",
                path=Path("/tmp/worktree"),
                base_branch="main",
            )

    def test_worktree_validates_branch_name(self):
        """Test validation of empty branch_name."""
        with pytest.raises(ValueError, match="branch_name cannot be empty"):
            Worktree(
                task_id="TASK-AB-001",
                branch_name="",
                path=Path("/tmp/worktree"),
                base_branch="main",
            )

    def test_worktree_validates_path_type(self):
        """Test validation of path type."""
        with pytest.raises(ValueError, match="path must be a Path instance"):
            Worktree(
                task_id="TASK-AB-001",
                branch_name="autobuild/TASK-AB-001",
                path="/tmp/worktree",  # type: ignore
                base_branch="main",
            )

    def test_worktree_validates_base_branch(self):
        """Test validation of empty base_branch."""
        with pytest.raises(ValueError, match="base_branch cannot be empty"):
            Worktree(
                task_id="TASK-AB-001",
                branch_name="autobuild/TASK-AB-001",
                path=Path("/tmp/worktree"),
                base_branch="",
            )


# ============================================================================
# WorktreeManager Initialization Tests
# ============================================================================


class TestWorktreeManagerInit:
    """Test WorktreeManager initialization and validation."""

    def test_manager_initialization_success(self, temp_repo_root, mock_executor):
        """Test successful manager initialization."""
        manager = WorktreeManager(
            repo_root=temp_repo_root,
            executor=mock_executor,
        )

        assert manager.repo_root == temp_repo_root.resolve()
        assert manager.worktrees_dir == temp_repo_root / ".guardkit" / "worktrees"
        assert manager.executor == mock_executor

    def test_manager_validates_git_repo(self, temp_repo_root, mock_executor):
        """Test that manager validates git repository on init."""
        # Mock executor should be called with rev-parse
        manager = WorktreeManager(
            repo_root=temp_repo_root,
            executor=mock_executor,
        )

        # Check that git rev-parse was called
        assert len(mock_executor.calls) == 1
        assert mock_executor.calls[0][0] == ["git", "rev-parse", "--git-dir"]

    def test_manager_fails_on_invalid_repo(self, temp_repo_root):
        """Test initialization fails if not a git repository."""
        # Create executor that fails on rev-parse
        executor = MockCommandExecutor()
        executor.should_fail = True

        with pytest.raises(WorktreeError, match="Git command failed"):
            WorktreeManager(
                repo_root=temp_repo_root,
                executor=executor,
            )

    def test_manager_uses_default_executor(self, temp_repo_root, mock_executor):
        """Test that manager can use default SubprocessExecutor."""
        # This test verifies the default parameter works
        # We still use mock to avoid actual git commands
        manager = WorktreeManager(
            repo_root=temp_repo_root,
            executor=mock_executor,  # In real usage, this would be None
        )

        assert manager.executor is not None


# ============================================================================
# Worktree Creation Tests
# ============================================================================


class TestWorktreeCreate:
    """Test worktree creation functionality."""

    def test_create_worktree_success(self, manager, mock_executor, temp_repo_root):
        """Test successful worktree creation."""
        worktree = manager.create("TASK-AB-001", base_branch="main")

        # Verify worktree properties
        assert worktree.task_id == "TASK-AB-001"
        assert worktree.branch_name == "autobuild/TASK-AB-001"
        assert worktree.path == temp_repo_root / ".guardkit" / "worktrees" / "TASK-AB-001"
        assert worktree.base_branch == "main"

        # Verify git commands were called correctly
        git_calls = [call[0] for call in mock_executor.calls]
        assert ["git", "rev-parse", "--git-dir"] in git_calls
        assert [
            "git", "worktree", "add",
            str(temp_repo_root / ".guardkit" / "worktrees" / "TASK-AB-001"),
            "-b", "autobuild/TASK-AB-001",
            "main"
        ] in git_calls

    def test_create_worktree_custom_base_branch(self, manager, mock_executor):
        """Test worktree creation with custom base branch."""
        worktree = manager.create("TASK-AB-002", base_branch="develop")

        assert worktree.base_branch == "develop"

        # Verify git command used correct base branch
        git_calls = [call[0] for call in mock_executor.calls]
        assert any("develop" in call for call in git_calls)

    def test_create_worktree_creates_directory(self, manager, temp_repo_root):
        """Test that worktrees directory is created."""
        manager.create("TASK-AB-001")

        worktrees_dir = temp_repo_root / ".guardkit" / "worktrees"
        assert worktrees_dir.exists()
        assert worktrees_dir.is_dir()

    def test_create_worktree_fails_on_git_error(self, manager):
        """Test worktree creation failure handling."""
        # Configure mock to fail on worktree add
        manager.executor.fail_on_command = "worktree add"

        with pytest.raises(WorktreeCreationError, match="Failed to create worktree"):
            manager.create("TASK-AB-001")

    def test_build_branch_name_helper(self, manager):
        """Test _build_branch_name helper method."""
        branch_name = manager._build_branch_name("TASK-AB-001")
        assert branch_name == "autobuild/TASK-AB-001"

        branch_name = manager._build_branch_name("TASK-XYZ-999")
        assert branch_name == "autobuild/TASK-XYZ-999"


# ============================================================================
# Repository State Checks Tests
# ============================================================================


class TestRepositoryStateChecks:
    """Test repository state validation methods."""

    def test_is_empty_repo_true(self, manager):
        """Test _is_empty_repo returns True for empty repo."""
        manager.executor.fail_on_command = "rev-parse HEAD"
        assert manager._is_empty_repo() is True

    def test_is_empty_repo_false(self, manager):
        """Test _is_empty_repo returns False for non-empty repo."""
        # Default mock succeeds, so repo is not empty
        assert manager._is_empty_repo() is False

    def test_branch_exists_true(self, manager):
        """Test _branch_exists returns True for existing branch."""
        assert manager._branch_exists("main") is True

    def test_branch_exists_false(self, manager):
        """Test _branch_exists returns False for missing branch."""
        manager.executor.fail_on_command = "rev-parse --verify"
        assert manager._branch_exists("nonexistent") is False

    def test_list_branches(self, manager):
        """Test _list_branches returns parsed list."""
        manager.executor.return_stdout = "main\ndevelop\nfeature-x\n"
        branches = manager._list_branches()
        assert branches == ["main", "develop", "feature-x"]

    def test_list_branches_empty(self, manager):
        """Test _list_branches returns empty list on error."""
        manager.executor.fail_on_command = "branch"
        branches = manager._list_branches()
        assert branches == []

    def test_create_fails_on_empty_repo(self, manager):
        """Test create() fails with helpful message on empty repo."""
        # Simulate: branch doesn't exist AND repo is empty
        def mock_run(args, cwd=None, check=True, capture_output=True, text=True):
            manager.executor.calls.append((args, cwd))
            cmd_str = " ".join(args)
            # rev-parse --git-dir succeeds (valid repo)
            if "rev-parse --git-dir" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "", "")
            # rev-parse --verify fails (branch doesn't exist)
            if "rev-parse --verify" in cmd_str:
                raise subprocess.CalledProcessError(1, args, stderr="unknown revision")
            # rev-parse HEAD fails (empty repo)
            if "rev-parse HEAD" in cmd_str:
                raise subprocess.CalledProcessError(1, args, stderr="bad revision")
            return subprocess.CompletedProcess(args, 0, "", "")

        manager.executor.run = mock_run

        with pytest.raises(WorktreeCreationError) as exc_info:
            manager.create("TASK-001")

        assert "repository has no commits" in str(exc_info.value)
        assert "git add . && git commit" in str(exc_info.value)

    def test_create_fails_on_missing_branch(self, manager):
        """Test create() fails listing available branches when branch missing."""
        # Simulate: branch doesn't exist BUT repo has commits
        def mock_run(args, cwd=None, check=True, capture_output=True, text=True):
            manager.executor.calls.append((args, cwd))
            cmd_str = " ".join(args)
            # rev-parse --git-dir succeeds
            if "rev-parse --git-dir" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "", "")
            # rev-parse --verify fails (branch doesn't exist)
            if "rev-parse --verify" in cmd_str:
                raise subprocess.CalledProcessError(1, args, stderr="unknown revision")
            # rev-parse HEAD succeeds (repo has commits)
            if "rev-parse HEAD" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "abc123", "")
            # branch --format returns available branches
            if "branch --format" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "develop\nfeature-x\n", "")
            return subprocess.CompletedProcess(args, 0, "", "")

        manager.executor.run = mock_run

        with pytest.raises(WorktreeCreationError) as exc_info:
            manager.create("TASK-001", base_branch="main")

        assert "does not exist" in str(exc_info.value)
        assert "Available branches:" in str(exc_info.value)
        assert "develop" in str(exc_info.value)


# ============================================================================
# Worktree Merge Tests
# ============================================================================


class TestWorktreeMerge:
    """Test worktree merge functionality."""

    def test_merge_success(self, manager, mock_executor):
        """Test successful worktree merge."""
        worktree = Worktree(
            task_id="TASK-AB-001",
            branch_name="autobuild/TASK-AB-001",
            path=Path("/tmp/worktree"),
            base_branch="main",
        )

        manager.merge(worktree, target_branch="main")

        # Verify git commands
        git_calls = [call[0] for call in mock_executor.calls]

        # Should checkout target branch
        assert ["git", "checkout", "main"] in git_calls

        # Should merge with --no-ff
        merge_call = [
            "git", "merge", "--no-ff",
            "-m", "Merge TASK-AB-001 from AutoBuild",
            "autobuild/TASK-AB-001"
        ]
        assert merge_call in git_calls

    def test_merge_custom_target_branch(self, manager, mock_executor):
        """Test merge to custom target branch."""
        worktree = Worktree(
            task_id="TASK-AB-001",
            branch_name="autobuild/TASK-AB-001",
            path=Path("/tmp/worktree"),
            base_branch="main",
        )

        manager.merge(worktree, target_branch="develop")

        # Verify checkout to develop
        git_calls = [call[0] for call in mock_executor.calls]
        assert ["git", "checkout", "develop"] in git_calls

    def test_merge_checkout_failure(self, manager):
        """Test merge failure when checkout fails."""
        worktree = Worktree(
            task_id="TASK-AB-001",
            branch_name="autobuild/TASK-AB-001",
            path=Path("/tmp/worktree"),
            base_branch="main",
        )

        # Configure mock to fail on checkout
        manager.executor.fail_on_command = "checkout"

        with pytest.raises(WorktreeMergeError, match="Failed to checkout"):
            manager.merge(worktree)

    def test_merge_conflict_detection(self, manager, temp_repo_root):
        """Test merge conflict detection."""
        worktree = Worktree(
            task_id="TASK-AB-001",
            branch_name="autobuild/TASK-AB-001",
            path=Path("/tmp/worktree"),
            base_branch="main",
        )

        # Create a new mock executor that simulates merge conflict scenario
        class ConflictMockExecutor:
            def __init__(self):
                self.calls = []
                self.merge_failed = False

            def run(self, args, cwd=None, check=True, capture_output=True, text=True):
                self.calls.append((args, cwd))

                # Succeed on rev-parse (initialization)
                if "rev-parse" in args:
                    return subprocess.CompletedProcess(
                        args=args, returncode=0, stdout="", stderr=""
                    )

                # Succeed on checkout
                if "checkout" in args:
                    return subprocess.CompletedProcess(
                        args=args, returncode=0, stdout="", stderr=""
                    )

                # Fail on merge command (first time)
                if "merge" in args and not self.merge_failed:
                    self.merge_failed = True
                    raise subprocess.CalledProcessError(
                        returncode=1, cmd=args, stderr="Merge conflict"
                    )

                # Succeed on status with conflict markers
                if "status" in args:
                    return subprocess.CompletedProcess(
                        args=args,
                        returncode=0,
                        stdout="UU conflict.txt\n",
                        stderr="",
                    )

                # Default success
                return subprocess.CompletedProcess(
                    args=args, returncode=0, stdout="", stderr=""
                )

        # Replace executor
        manager.executor = ConflictMockExecutor()

        # Should detect conflicts from status output
        with pytest.raises(WorktreeMergeError) as exc_info:
            manager.merge(worktree)

        # Verify error message mentions conflicts
        assert "Merge conflicts" in str(exc_info.value) or "conflict" in str(exc_info.value).lower()

    def test_merge_generic_failure(self, manager):
        """Test generic merge failure handling."""
        worktree = Worktree(
            task_id="TASK-AB-001",
            branch_name="autobuild/TASK-AB-001",
            path=Path("/tmp/worktree"),
            base_branch="main",
        )

        # Configure mock to fail on merge without conflicts
        manager.executor.fail_on_command = "merge"
        manager.executor.return_stdout = "clean"

        with pytest.raises(WorktreeMergeError, match="Merge failed"):
            manager.merge(worktree)


# ============================================================================
# Worktree Cleanup Tests
# ============================================================================


class TestWorktreeCleanup:
    """Test worktree cleanup functionality."""

    def test_cleanup_success(self, manager, mock_executor):
        """Test successful worktree cleanup."""
        worktree = Worktree(
            task_id="TASK-AB-001",
            branch_name="autobuild/TASK-AB-001",
            path=Path("/tmp/worktree"),
            base_branch="main",
        )

        manager.cleanup(worktree)

        # Verify git commands
        git_calls = [call[0] for call in mock_executor.calls]

        # Should remove worktree
        assert ["git", "worktree", "remove", "/tmp/worktree"] in git_calls

        # Should delete branch with -d
        assert ["git", "branch", "-d", "autobuild/TASK-AB-001"] in git_calls

    def test_cleanup_with_force(self, manager, mock_executor):
        """Test cleanup with force flag."""
        worktree = Worktree(
            task_id="TASK-AB-001",
            branch_name="autobuild/TASK-AB-001",
            path=Path("/tmp/worktree"),
            base_branch="main",
        )

        manager.cleanup(worktree, force=True)

        # Verify git commands use force flags
        git_calls = [call[0] for call in mock_executor.calls]

        # Should remove worktree with --force
        assert ["git", "worktree", "remove", "/tmp/worktree", "--force"] in git_calls

        # Should delete branch with -D
        assert ["git", "branch", "-D", "autobuild/TASK-AB-001"] in git_calls

    def test_cleanup_worktree_removal_failure(self, manager):
        """Test cleanup failure when worktree removal fails."""
        worktree = Worktree(
            task_id="TASK-AB-001",
            branch_name="autobuild/TASK-AB-001",
            path=Path("/tmp/worktree"),
            base_branch="main",
        )

        # Configure mock to fail on worktree remove
        manager.executor.fail_on_command = "worktree remove"

        with pytest.raises(WorktreeError, match="Failed to remove worktree"):
            manager.cleanup(worktree)

    def test_cleanup_branch_deletion_failure(self, manager):
        """Test cleanup failure when branch deletion fails."""
        worktree = Worktree(
            task_id="TASK-AB-001",
            branch_name="autobuild/TASK-AB-001",
            path=Path("/tmp/worktree"),
            base_branch="main",
        )

        # Configure mock to fail on branch delete
        manager.executor.fail_on_command = "branch"

        with pytest.raises(WorktreeError, match="Failed to delete branch"):
            manager.cleanup(worktree)


# ============================================================================
# Worktree Preserve Tests
# ============================================================================


class TestWorktreePreserve:
    """Test worktree preservation functionality."""

    def test_preserve_on_failure(self, manager, mock_executor):
        """Test that preserve_on_failure doesn't remove worktree."""
        worktree = Worktree(
            task_id="TASK-AB-001",
            branch_name="autobuild/TASK-AB-001",
            path=Path("/tmp/worktree"),
            base_branch="main",
        )

        # Get initial call count
        initial_calls = len(mock_executor.calls)

        # Preserve should not make any git calls
        manager.preserve_on_failure(worktree)

        # Verify no additional git commands were executed
        assert len(mock_executor.calls) == initial_calls

    def test_preserve_workflow(self, manager, temp_repo_root):
        """Test typical preserve workflow after merge failure."""
        # Create worktree
        worktree = manager.create("TASK-AB-001")

        # Simulate merge failure
        manager.executor.fail_on_command = "merge"

        with pytest.raises(WorktreeMergeError):
            manager.merge(worktree)

        # Preserve for manual inspection
        manager.preserve_on_failure(worktree)

        # Worktree directory should still exist (we created it in test)
        # In real usage, the directory would be created by git
        assert manager.worktrees_dir.exists()


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling across all operations."""

    def test_run_git_captures_stderr(self, manager):
        """Test that _run_git captures git stderr in exceptions."""
        manager.executor.should_fail = True

        with pytest.raises(WorktreeError, match="Mock git error"):
            manager._run_git(["status"])

    def test_run_git_includes_command_in_error(self, manager):
        """Test that _run_git includes failed command in error."""
        manager.executor.should_fail = True

        with pytest.raises(WorktreeError, match="git status"):
            manager._run_git(["status"])

    def test_exception_hierarchy(self):
        """Test exception hierarchy is correct."""
        assert issubclass(WorktreeCreationError, WorktreeError)
        assert issubclass(WorktreeMergeError, WorktreeError)

    def test_worktree_error_message(self):
        """Test WorktreeError can be created with custom message."""
        error = WorktreeError("Custom error message")
        assert str(error) == "Custom error message"

    def test_creation_error_message(self):
        """Test WorktreeCreationError message."""
        error = WorktreeCreationError("Failed to create")
        assert str(error) == "Failed to create"

    def test_merge_error_message(self):
        """Test WorktreeMergeError message."""
        error = WorktreeMergeError("Merge conflict")
        assert str(error) == "Merge conflict"


# ============================================================================
# Integration-Style Tests
# ============================================================================


class TestWorktreeWorkflows:
    """Test complete workflows combining multiple operations."""

    def test_complete_success_workflow(self, manager, mock_executor):
        """Test complete workflow: create → work → merge → cleanup."""
        # Create worktree
        worktree = manager.create("TASK-AB-001", base_branch="main")
        assert worktree.task_id == "TASK-AB-001"

        # Simulate work (no actual git commands, just verify creation worked)
        assert worktree.path.name == "TASK-AB-001"

        # Merge
        manager.merge(worktree, target_branch="main")

        # Verify merge commands were executed
        git_calls = [call[0] for call in mock_executor.calls]
        assert any("merge" in str(call) for call in git_calls)

    def test_complete_failure_workflow(self, manager):
        """Test complete workflow: create → work → merge fails → preserve."""
        # Create worktree
        worktree = manager.create("TASK-AB-002")

        # Configure merge to fail
        manager.executor.fail_on_command = "merge"

        # Try to merge
        with pytest.raises(WorktreeMergeError):
            manager.merge(worktree)

        # Preserve for manual inspection
        manager.preserve_on_failure(worktree)

        # Verify worktree not cleaned up (no additional commands after preserve)
        # The preserve call should not trigger any git operations

    def test_manual_cleanup_after_preserve(self, manager):
        """Test manual cleanup after preservation."""
        # Create and preserve
        worktree = manager.create("TASK-AB-003")
        manager.preserve_on_failure(worktree)

        # Later, manually clean up
        manager.cleanup(worktree, force=True)

        # Verify cleanup commands executed
        git_calls = [call[0] for call in manager.executor.calls]
        # Check for worktree remove command
        assert any("worktree" in call and "remove" in call for call in git_calls)
        # Check for branch delete command
        assert any("branch" in call for call in git_calls)


# ============================================================================
# Branch Cleanup Fallback Tests
# ============================================================================


class TestBranchCleanupFallback:
    """Test automatic branch cleanup when worktree creation fails."""

    def test_is_branch_exists_error_true(self, manager):
        """Test _is_branch_exists_error returns True for 'already exists' error."""
        error = WorktreeError("fatal: A branch named 'autobuild/TASK-001' already exists.")
        assert manager._is_branch_exists_error(error) is True

    def test_is_branch_exists_error_false(self, manager):
        """Test _is_branch_exists_error returns False for other errors."""
        error = WorktreeError("fatal: No space left on device")
        assert manager._is_branch_exists_error(error) is False

    def test_is_branch_exists_error_case_insensitive(self, manager):
        """Test error detection is case insensitive."""
        error = WorktreeError("fatal: A branch named 'autobuild/TASK-001' ALREADY EXISTS.")
        assert manager._is_branch_exists_error(error) is True

    def test_build_worktree_add_cmd(self, manager, temp_repo_root):
        """Test _build_worktree_add_cmd builds correct command."""
        worktree_path = temp_repo_root / ".guardkit" / "worktrees" / "TASK-001"
        cmd = manager._build_worktree_add_cmd(worktree_path, "autobuild/TASK-001", "main")
        assert cmd == [
            "worktree", "add",
            str(worktree_path),
            "-b", "autobuild/TASK-001",
            "main"
        ]

    def test_create_with_branch_cleanup_success(self, manager):
        """Test successful creation after branch cleanup."""
        # Track worktree add calls to fail first time, succeed second
        worktree_add_calls = [0]

        def mock_run(args, cwd=None, check=True, capture_output=True, text=True):
            manager.executor.calls.append((args, cwd))
            cmd_str = " ".join(args)

            if "rev-parse --git-dir" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "", "")
            if "rev-parse --verify" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "abc123", "")
            if "worktree add" in cmd_str:
                worktree_add_calls[0] += 1
                if worktree_add_calls[0] == 1:
                    raise subprocess.CalledProcessError(
                        1, args, stderr="fatal: A branch named 'autobuild/TASK-001' already exists."
                    )
                return subprocess.CompletedProcess(args, 0, "", "")
            if "branch" in cmd_str and "-D" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "", "")
            return subprocess.CompletedProcess(args, 0, "", "")

        manager.executor.run = mock_run

        worktree = manager.create("TASK-001")

        assert worktree.task_id == "TASK-001"
        assert worktree.branch_name == "autobuild/TASK-001"

        # Verify branch -D was called
        git_calls = [" ".join(call[0]) for call in manager.executor.calls]
        assert any("branch" in call and "-D" in call for call in git_calls)

        # Verify worktree add was called twice
        assert sum(1 for call in git_calls if "worktree add" in call) == 2

    def test_create_fails_when_branch_cleanup_fails(self, manager):
        """Test error with manual guidance when branch cleanup fails."""
        def mock_run(args, cwd=None, check=True, capture_output=True, text=True):
            manager.executor.calls.append((args, cwd))
            cmd_str = " ".join(args)

            if "rev-parse --git-dir" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "", "")
            if "rev-parse --verify" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "abc123", "")
            if "worktree add" in cmd_str:
                raise subprocess.CalledProcessError(
                    1, args, stderr="fatal: A branch named 'autobuild/TASK-001' already exists."
                )
            if "branch" in cmd_str and "-D" in cmd_str:
                raise subprocess.CalledProcessError(
                    1, args, stderr="error: Cannot delete branch - checked out elsewhere"
                )
            return subprocess.CompletedProcess(args, 0, "", "")

        manager.executor.run = mock_run

        with pytest.raises(WorktreeCreationError) as exc_info:
            manager.create("TASK-001")

        error_msg = str(exc_info.value)
        assert "Manual cleanup steps:" in error_msg
        assert "git branch -D autobuild/TASK-001" in error_msg

    def test_create_fails_when_retry_fails(self, manager):
        """Test error with manual guidance when retry after cleanup fails."""
        # Track worktree add calls - both should fail
        def mock_run(args, cwd=None, check=True, capture_output=True, text=True):
            manager.executor.calls.append((args, cwd))
            cmd_str = " ".join(args)

            if "rev-parse --git-dir" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "", "")
            if "rev-parse --verify" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "abc123", "")
            if "worktree add" in cmd_str:
                raise subprocess.CalledProcessError(
                    1, args, stderr="fatal: A branch named 'autobuild/TASK-001' already exists."
                )
            if "branch" in cmd_str and "-D" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "", "")  # Cleanup succeeds
            return subprocess.CompletedProcess(args, 0, "", "")

        manager.executor.run = mock_run

        with pytest.raises(WorktreeCreationError) as exc_info:
            manager.create("TASK-001")

        error_msg = str(exc_info.value)
        assert "after branch cleanup" in error_msg
        assert "Manual cleanup steps:" in error_msg

    def test_create_non_branch_error_not_caught(self, manager):
        """Test that non-branch errors are not caught by fallback logic."""
        def mock_run(args, cwd=None, check=True, capture_output=True, text=True):
            manager.executor.calls.append((args, cwd))
            cmd_str = " ".join(args)

            if "rev-parse --git-dir" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "", "")
            if "rev-parse --verify" in cmd_str:
                return subprocess.CompletedProcess(args, 0, "abc123", "")
            if "worktree add" in cmd_str:
                raise subprocess.CalledProcessError(
                    1, args, stderr="fatal: unable to create file: No space left on device"
                )
            return subprocess.CompletedProcess(args, 0, "", "")

        manager.executor.run = mock_run

        with pytest.raises(WorktreeCreationError) as exc_info:
            manager.create("TASK-001")

        error_msg = str(exc_info.value)
        assert "No space left on device" in error_msg
        assert "Manual cleanup steps:" not in error_msg

        # Verify branch -D was NOT attempted
        git_calls = [" ".join(call[0]) for call in manager.executor.calls]
        assert not any("branch" in call and "-D" in call for call in git_calls)
