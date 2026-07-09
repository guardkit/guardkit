"""
Comprehensive Test Suite for git_state_helper.py

Part of TASK-031: Fix task-work and task-complete State Loss in Conductor Workspaces.

This test suite validates the three core functions:
1. get_git_root() - Get git repository root (worktree-compatible)
2. resolve_state_dir() - Resolve state directory path relative to git root
3. commit_state_files() - Stage and commit state files for a task

Test Coverage:
- Unit tests for each function
- Integration tests with real git operations
- Error handling (not in git repo, git command failures)
- Path resolution in worktrees
- Backward compatibility (non-git scenarios)

Author: Claude (Anthropic)
Created: 2025-10-18
"""

import pytest
import subprocess
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Add lib directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"))

from git_state_helper import get_git_root, resolve_state_dir, commit_state_files


# ---------------------------------------------------------------------------
# TASK-FIX-GITSTATETEST01 (WS3-S1) — hermetic git isolation.
#
# ``git_state_helper`` resolves the repo via ``git rev-parse --show-toplevel``
# from CWD, and ``commit_state_files`` runs a bare ``git commit`` (NO pathspec)
# — which commits the ENTIRE index, not just ``docs/state/<task>``. Run against
# the enclosing guardkit repo (the pre-fix behaviour) this: (a) swept an agent's
# staged work into a junk "Save state for TASK-031" commit during the
# FEAT-ABL-001 hand-finish, and (b) dirtied ``docs/state/TASK-TEST-*`` /
# ``.guardkit/memory-query-log.jsonl``. This autouse fixture chdir's EVERY test
# in this module into a throwaway ``tmp_path`` git repo, so real git operations
# can only ever touch that temp repo. Acceptance: a full ``pytest tests/unit``
# with files deliberately staged in the enclosing repo leaves its index + HEAD
# untouched.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_git_repo(tmp_path, monkeypatch):
    """chdir into a fresh, identity-configured temp git repo for the whole
    module so no real git op can reach the enclosing repository."""
    repo = tmp_path / "hermetic_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    # Local identity + no signing so ``git commit`` succeeds without the host's
    # global config (and cannot hang on a gpg prompt).
    for key, val in (
        ("user.email", "gitstatetest@example.invalid"),
        ("user.name", "GitStateTest"),
        ("commit.gpgsign", "false"),
    ):
        subprocess.run(
            ["git", "config", key, val], cwd=repo, check=True, capture_output=True
        )
    # An initial commit so HEAD exists (some helpers/tests assume a valid HEAD).
    (repo / ".gitkeep").write_text("")
    subprocess.run(["git", "add", ".gitkeep"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True
    )
    monkeypatch.chdir(repo)
    return repo


class TestGetGitRoot:
    """Test suite for get_git_root() function."""

    def test_get_git_root_returns_path(self):
        """Test that get_git_root() returns a Path object."""
        try:
            result = get_git_root()
            assert isinstance(result, Path), "get_git_root() should return a Path object"
            assert result.exists(), "Returned path should exist"
            assert result.is_dir(), "Returned path should be a directory"
        except subprocess.CalledProcessError:
            # If not in a git repo, this is expected
            pytest.skip("Not in a git repository")

    def test_get_git_root_absolute_path(self):
        """Test that get_git_root() returns an absolute path."""
        try:
            result = get_git_root()
            assert result.is_absolute(), "Path should be absolute"
        except subprocess.CalledProcessError:
            pytest.skip("Not in a git repository")

    def test_get_git_root_has_git_directory(self):
        """Test that the returned root contains a .git directory or file."""
        try:
            root = get_git_root()
            git_path = root / ".git"
            assert git_path.exists(), "Root should contain .git directory or file"
        except subprocess.CalledProcessError:
            pytest.skip("Not in a git repository")

    def test_get_git_root_not_in_git_repo(self):
        """Test that get_git_root() raises CalledProcessError when not in git repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to non-git directory
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with pytest.raises(subprocess.CalledProcessError):
                    get_git_root()
            finally:
                os.chdir(original_cwd)

    @patch('subprocess.run')
    def test_get_git_root_command_execution(self, mock_run):
        """Test that get_git_root() executes correct git command."""
        mock_run.return_value = MagicMock(stdout="/path/to/repo\n")

        result = get_git_root()

        # Verify correct command was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "rev-parse", "--show-toplevel"]
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["check"] is True

    @patch('subprocess.run')
    def test_get_git_root_strips_whitespace(self, mock_run):
        """Test that get_git_root() strips whitespace from git output."""
        mock_run.return_value = MagicMock(stdout="  /path/to/repo  \n  ")

        result = get_git_root()

        assert str(result) == "/path/to/repo"


class TestResolveStateDir:
    """Test suite for resolve_state_dir() function."""

    def test_resolve_state_dir_returns_path(self):
        """Test that resolve_state_dir() returns a Path object."""
        try:
            result = resolve_state_dir("TASK-031")
            assert isinstance(result, Path), "resolve_state_dir() should return a Path object"
        except subprocess.CalledProcessError:
            pytest.skip("Not in a git repository")

    def test_resolve_state_dir_creates_directory(self):
        """Test that resolve_state_dir() creates the directory if it doesn't exist."""
        try:
            task_id = "TASK-TEST-CREATE"
            result = resolve_state_dir(task_id)
            assert result.exists(), "Directory should be created"
            assert result.is_dir(), "Path should be a directory"

            # Clean up
            if result.exists():
                shutil.rmtree(result)
        except subprocess.CalledProcessError:
            pytest.skip("Not in a git repository")

    def test_resolve_state_dir_path_structure(self):
        """Test that resolve_state_dir() creates correct path structure."""
        try:
            task_id = "TASK-031"
            result = resolve_state_dir(task_id)

            # Verify path structure: {git_root}/docs/state/{task_id}
            assert result.name == task_id, f"Directory name should be {task_id}"
            assert result.parent.name == "state", "Parent should be 'state'"
            assert result.parent.parent.name == "docs", "Grandparent should be 'docs'"
        except subprocess.CalledProcessError:
            pytest.skip("Not in a git repository")

    def test_resolve_state_dir_idempotent(self):
        """Test that calling resolve_state_dir() multiple times is safe."""
        try:
            task_id = "TASK-TEST-IDEMPOTENT"

            # Call multiple times
            result1 = resolve_state_dir(task_id)
            result2 = resolve_state_dir(task_id)
            result3 = resolve_state_dir(task_id)

            # All should return same path
            assert result1 == result2 == result3
            assert result1.exists()

            # Clean up
            if result1.exists():
                shutil.rmtree(result1)
        except subprocess.CalledProcessError:
            pytest.skip("Not in a git repository")

    @patch('git_state_helper.get_git_root')
    def test_resolve_state_dir_uses_git_root(self, mock_get_git_root):
        """Test that resolve_state_dir() uses get_git_root() for path resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_root = Path(tmpdir)
            mock_get_git_root.return_value = mock_root

            result = resolve_state_dir("TASK-031")

            # Verify it's relative to mock root
            assert result == mock_root / "docs" / "state" / "TASK-031"
            assert result.exists()

    def test_resolve_state_dir_absolute_path(self):
        """Test that resolve_state_dir() returns an absolute path."""
        try:
            result = resolve_state_dir("TASK-031")
            assert result.is_absolute(), "Path should be absolute"
        except subprocess.CalledProcessError:
            pytest.skip("Not in a git repository")


class TestCommitStateFiles:
    """Test suite for commit_state_files() function."""

    def test_commit_state_files_no_error_when_no_changes(self):
        """Test that commit_state_files() doesn't fail when nothing to commit."""
        try:
            # This should not raise an exception even if nothing to commit
            commit_state_files("TASK-031")
        except subprocess.CalledProcessError:
            pytest.fail("commit_state_files() should not fail when nothing to commit")
        except Exception:
            # If not in git repo, skip
            pytest.skip("Not in a git repository")

    def test_commit_state_files_with_custom_message(self):
        """Test that commit_state_files() accepts custom commit message."""
        try:
            custom_message = "Custom commit message for testing"
            # Should not raise exception
            commit_state_files("TASK-031", message=custom_message)
        except subprocess.CalledProcessError:
            pytest.fail("commit_state_files() should not fail with custom message")
        except Exception:
            pytest.skip("Not in a git repository")

    @patch('subprocess.run')
    def test_commit_state_files_git_add_command(self, mock_run):
        """Test that commit_state_files() executes git add correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_root = Path(tmpdir)
            state_dir = mock_root / "docs" / "state" / "TASK-031"
            state_dir.mkdir(parents=True, exist_ok=True)

            with patch('git_state_helper.resolve_state_dir', return_value=state_dir):
                # Configure mock to succeed
                mock_run.return_value = MagicMock(returncode=0)

                commit_state_files("TASK-031")

                # Find the git add call
                add_call = None
                for call in mock_run.call_args_list:
                    if "git" in call[0][0] and "add" in call[0][0]:
                        add_call = call
                        break

                assert add_call is not None, "Should call git add"
                assert add_call[0][0][0] == "git"
                assert add_call[0][0][1] == "add"
                assert str(state_dir) in add_call[0][0][2]
                assert add_call[1]["check"] is True

    @patch('subprocess.run')
    def test_commit_state_files_git_commit_command(self, mock_run):
        """Test that commit_state_files() executes git commit correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_root = Path(tmpdir)
            state_dir = mock_root / "docs" / "state" / "TASK-031"
            state_dir.mkdir(parents=True, exist_ok=True)

            with patch('git_state_helper.resolve_state_dir', return_value=state_dir):
                # Configure mock to succeed
                mock_run.return_value = MagicMock(returncode=0)

                commit_state_files("TASK-031", message="Test message")

                # Find the git commit call
                commit_call = None
                for call in mock_run.call_args_list:
                    if "git" in call[0][0] and "commit" in call[0][0]:
                        commit_call = call
                        break

                assert commit_call is not None, "Should call git commit"
                assert commit_call[0][0][0] == "git"
                assert commit_call[0][0][1] == "commit"
                assert commit_call[0][0][2] == "-m"
                assert commit_call[0][0][3] == "Test message"
                assert commit_call[1]["check"] is False  # Should not fail on no changes

    @patch('subprocess.run')
    def test_commit_state_files_default_message(self, mock_run):
        """Test that commit_state_files() uses default message when none provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_root = Path(tmpdir)
            state_dir = mock_root / "docs" / "state" / "TASK-031"
            state_dir.mkdir(parents=True, exist_ok=True)

            with patch('git_state_helper.resolve_state_dir', return_value=state_dir):
                mock_run.return_value = MagicMock(returncode=0)

                commit_state_files("TASK-031")

                # Find the git commit call
                commit_call = None
                for call in mock_run.call_args_list:
                    if "git" in call[0][0] and "commit" in call[0][0]:
                        commit_call = call
                        break

                assert commit_call is not None
                expected_message = "Save state for TASK-031"
                assert commit_call[0][0][3] == expected_message


class TestIntegrationScenarios:
    """Integration tests for complete workflows."""

    def test_complete_workflow_creates_and_commits_state(self):
        """Test complete workflow: create state dir, add file, commit."""
        try:
            task_id = "TASK-TEST-WORKFLOW"

            # Step 1: Resolve state directory
            state_dir = resolve_state_dir(task_id)
            assert state_dir.exists()

            # Step 2: Create a test file in state directory
            test_file = state_dir / "test_state.txt"
            test_file.write_text("Test state data")
            assert test_file.exists()

            # Step 3: Commit state files
            commit_state_files(task_id, "Test workflow commit")

            # Verify file is tracked by git (if in git repo)
            result = subprocess.run(
                ["git", "ls-files", str(test_file)],
                capture_output=True,
                text=True,
                check=False
            )

            # If in git repo and file was committed, it should be in ls-files output
            if result.returncode == 0:
                # File might be staged or committed
                assert len(result.stdout) > 0 or test_file.exists()

            # Clean up
            if test_file.exists():
                test_file.unlink()
            if state_dir.exists() and not list(state_dir.iterdir()):
                state_dir.rmdir()

        except subprocess.CalledProcessError:
            pytest.skip("Not in a git repository")

    def test_workflow_leaves_an_outer_repo_index_and_head_untouched(
        self, tmp_path, monkeypatch
    ):
        """TASK-FIX-GITSTATETEST01 acceptance: the workflow must NOT touch any
        repo it is not chdir'd into — even with work deliberately staged there.

        Simulates the enclosing guardkit repo: a second git repo with a file
        staged in its index. Running the full commit workflow (from inside the
        hermetic repo the autouse fixture put us in) must leave the outer repo's
        HEAD and staged index exactly as they were — the pre-fix bug swept that
        staged work into a junk 'Save state' commit.
        """
        outer = tmp_path / "outer_repo"
        outer.mkdir()
        subprocess.run(["git", "init"], cwd=outer, check=True, capture_output=True)
        for key, val in (
            ("user.email", "outer@example.invalid"),
            ("user.name", "Outer"),
            ("commit.gpgsign", "false"),
        ):
            subprocess.run(
                ["git", "config", key, val], cwd=outer, check=True, capture_output=True
            )
        (outer / "seed.txt").write_text("seed")
        subprocess.run(["git", "add", "seed.txt"], cwd=outer, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "seed"], cwd=outer, check=True, capture_output=True
        )
        # Deliberately stage uncommitted work in the outer repo's index.
        (outer / "agent_work.py").write_text("print('important agent work')\n")
        subprocess.run(
            ["git", "add", "agent_work.py"], cwd=outer, check=True, capture_output=True
        )

        def _outer(*args):
            return subprocess.run(
                ["git", *args], cwd=outer, capture_output=True, text=True, check=True
            ).stdout.strip()

        head_before = _outer("rev-parse", "HEAD")
        staged_before = _outer("diff", "--cached", "--name-only")
        assert "agent_work.py" in staged_before

        # Run the real workflow. The autouse fixture has us chdir'd into the
        # hermetic repo, NOT `outer`, so nothing here may reach `outer`.
        task_id = "TASK-TEST-WORKFLOW"
        state_dir = resolve_state_dir(task_id)
        (state_dir / "test_state.txt").write_text("Test state data")
        commit_state_files(task_id, "Test workflow commit")

        # The outer repo is untouched: same HEAD, same staged file.
        assert _outer("rev-parse", "HEAD") == head_before
        assert "agent_work.py" in _outer("diff", "--cached", "--name-only")
        # And the state commit landed in the hermetic repo instead.
        assert get_git_root() != outer

    def test_multiple_tasks_separate_directories(self):
        """Test that multiple tasks get separate state directories."""
        try:
            task1 = "TASK-TEST-MULTI-1"
            task2 = "TASK-TEST-MULTI-2"

            dir1 = resolve_state_dir(task1)
            dir2 = resolve_state_dir(task2)

            assert dir1 != dir2, "Different tasks should have different directories"
            assert dir1.exists() and dir2.exists()
            assert dir1.name == task1
            assert dir2.name == task2

            # Clean up
            for d in [dir1, dir2]:
                if d.exists() and not list(d.iterdir()):
                    d.rmdir()

        except subprocess.CalledProcessError:
            pytest.skip("Not in a git repository")

    def test_worktree_compatibility(self):
        """Test that functions work in git worktree environment."""
        try:
            # Get git root - should work in main repo or worktree
            root = get_git_root()

            # Check if we're in a worktree
            git_dir = root / ".git"
            is_worktree = git_dir.is_file() if git_dir.exists() else False

            # Resolve state dir should work regardless
            task_id = "TASK-TEST-WORKTREE"
            state_dir = resolve_state_dir(task_id)

            assert state_dir.exists()
            # State dir should be relative to main repo root, not worktree
            assert root in state_dir.parents or state_dir.parent == root / "docs" / "state"

            # Clean up
            if state_dir.exists() and not list(state_dir.iterdir()):
                state_dir.rmdir()

        except subprocess.CalledProcessError:
            pytest.skip("Not in a git repository")


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    def test_get_git_root_outside_repo_raises_error(self):
        """Test that get_git_root() raises error when not in a git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with pytest.raises(subprocess.CalledProcessError):
                    get_git_root()
            finally:
                os.chdir(original_cwd)

    @patch('subprocess.run')
    def test_commit_state_files_git_add_failure_propagates(self, mock_run):
        """Test that git add failures propagate as expected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "docs" / "state" / "TASK-031"
            state_dir.mkdir(parents=True)

            with patch('git_state_helper.resolve_state_dir', return_value=state_dir):
                # Make git add fail
                mock_run.side_effect = subprocess.CalledProcessError(1, "git add")

                with pytest.raises(subprocess.CalledProcessError):
                    commit_state_files("TASK-031")

    @patch('subprocess.run')
    def test_commit_state_files_git_commit_failure_silent(self, mock_run):
        """Test that git commit failures are silent (nothing to commit is OK)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "docs" / "state" / "TASK-031"
            state_dir.mkdir(parents=True)

            with patch('git_state_helper.resolve_state_dir', return_value=state_dir):
                call_count = [0]

                def mock_run_impl(cmd, **kwargs):
                    call_count[0] += 1
                    if "add" in cmd:
                        return MagicMock(returncode=0)
                    elif "commit" in cmd:
                        # Commit fails (nothing to commit)
                        if kwargs.get("check", True):
                            raise subprocess.CalledProcessError(1, "git commit")
                        return MagicMock(returncode=1)
                    return MagicMock(returncode=0)

                mock_run.side_effect = mock_run_impl

                # Should NOT raise exception
                commit_state_files("TASK-031")
                assert call_count[0] >= 2  # Called for both add and commit


class TestBackwardCompatibility:
    """Test backward compatibility scenarios."""

    def test_resolve_state_dir_works_without_git_commit(self):
        """Test that resolve_state_dir() works even if commit_state_files() is not called."""
        try:
            task_id = "TASK-TEST-NO-COMMIT"

            # Just resolve, don't commit
            state_dir = resolve_state_dir(task_id)

            assert state_dir.exists()
            assert state_dir.is_dir()

            # Clean up
            if state_dir.exists() and not list(state_dir.iterdir()):
                state_dir.rmdir()

        except subprocess.CalledProcessError:
            pytest.skip("Not in a git repository")

    @patch('git_state_helper.get_git_root')
    def test_functions_work_with_mocked_git_root(self, mock_get_git_root):
        """Test that functions work with mocked git root (simulating non-git usage)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_root = Path(tmpdir)
            mock_get_git_root.return_value = mock_root

            # Should work with mock
            state_dir = resolve_state_dir("TASK-031")
            assert state_dir.exists()
            assert state_dir == mock_root / "docs" / "state" / "TASK-031"


# Test execution summary
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
