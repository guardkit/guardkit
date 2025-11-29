"""
Integration tests for task completion in Conductor workspaces.

Tests verify that task completion works correctly in both:
1. Main repository (standard workflow)
2. Conductor worktrees (git worktree with symlinks)

Part of TASK-COND-FE76: Fix /task-complete Conductor workspace inconsistencies

Author: Claude (Anthropic)
Created: 2025-11-27
"""

import pytest
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import tempfile

# Add lib directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "installer" / "global" / "commands" / "lib"))

from task_completion_helper import (
    find_task_file,
    archive_task_documents,
    move_task_to_completed,
    complete_task
)
from task_utils import create_task_frontmatter, write_task_frontmatter


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git repo
    os.chdir(repo_dir)
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)

    # Create directory structure
    (repo_dir / "tasks" / "backlog").mkdir(parents=True)
    (repo_dir / "tasks" / "in_progress").mkdir(parents=True)
    (repo_dir / "tasks" / "in_review").mkdir(parents=True)
    (repo_dir / "tasks" / "completed").mkdir(parents=True)
    (repo_dir / ".claude" / "task-plans").mkdir(parents=True)

    # Initial commit
    (repo_dir / "README.md").write_text("Test repository")
    subprocess.run(["git", "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], check=True, capture_output=True)

    return repo_dir


@pytest.fixture
def sample_task(temp_git_repo):
    """Create a sample task file in backlog."""
    task_id = "TASK-TEST-001"
    task_data = create_task_frontmatter(
        task_id=task_id,
        title="Test task for completion",
        priority="medium",
        tags=["test", "integration"]
    )
    task_body = """
## Description
This is a test task for integration testing.

## Acceptance Criteria
- [ ] Task can be found by ID
- [ ] Task can be moved to completed
- [ ] Metadata is updated correctly
"""

    task_content = write_task_frontmatter(task_data, task_body)
    task_file = temp_git_repo / "tasks" / "backlog" / f"{task_id}.md"
    task_file.write_text(task_content)

    return task_file, task_id


# ============================================================================
# Test 1: find_task_file() with relative paths
# ============================================================================

def test_find_task_by_id_in_main_repo(sample_task, temp_git_repo):
    """Test finding task by ID in main repository."""
    os.chdir(temp_git_repo)
    task_file, task_id = sample_task

    # Should find task by ID
    found = find_task_file(task_id)
    assert found is not None
    assert found.name == f"{task_id}.md"
    assert "backlog" in str(found)


def test_find_task_with_full_path(sample_task, temp_git_repo):
    """Test finding task with full absolute path."""
    os.chdir(temp_git_repo)
    task_file, task_id = sample_task

    # Should find task by full path
    found = find_task_file(str(task_file))
    assert found is not None
    assert found == task_file


def test_find_task_not_found_raises_error(temp_git_repo):
    """Test that finding non-existent task raises clear error."""
    os.chdir(temp_git_repo)

    with pytest.raises(FileNotFoundError) as exc_info:
        find_task_file("TASK-NONEXISTENT-999")

    # Check error message is helpful
    assert "TASK-NONEXISTENT-999" in str(exc_info.value)
    assert "Searched in" in str(exc_info.value)


# ============================================================================
# Test 2: Document archival (plans only)
# ============================================================================

def test_archive_implementation_plan(sample_task, temp_git_repo):
    """Test archiving implementation plan only."""
    os.chdir(temp_git_repo)
    task_file, task_id = sample_task

    # Create implementation plan
    plan_dir = temp_git_repo / ".claude" / "task-plans"
    plan_file = plan_dir / f"{task_id}-implementation-plan.md"
    plan_file.write_text("# Implementation Plan\n\nTest plan content")

    # Archive to completed directory
    completed_dir = temp_git_repo / "tasks" / "completed" / "2025-11"
    completed_dir.mkdir(parents=True, exist_ok=True)

    archived_count = archive_task_documents(task_id, completed_dir)

    # Verify plan moved
    assert archived_count == 1
    assert not plan_file.exists()
    assert (completed_dir / f"{task_id}-implementation-plan.md").exists()


# ============================================================================
# Test 3: Document archival (summary only)
# ============================================================================

def test_archive_implementation_summary(sample_task, temp_git_repo):
    """Test archiving implementation summary from root directory."""
    os.chdir(temp_git_repo)
    task_file, task_id = sample_task

    # Create implementation summary in root directory
    summary_file = temp_git_repo / f"{task_id}-IMPLEMENTATION-SUMMARY.md"
    summary_file.write_text("# Implementation Summary\n\nTest summary content")

    # Archive to completed directory
    completed_dir = temp_git_repo / "tasks" / "completed" / "2025-11"
    completed_dir.mkdir(parents=True, exist_ok=True)

    archived_count = archive_task_documents(task_id, completed_dir)

    # Verify summary moved
    assert archived_count == 1
    assert not summary_file.exists()
    assert (completed_dir / f"{task_id}-IMPLEMENTATION-SUMMARY.md").exists()


# ============================================================================
# Test 4: Document archival (plan + summary)
# ============================================================================

def test_archive_all_documents(sample_task, temp_git_repo):
    """Test archiving all document types together."""
    os.chdir(temp_git_repo)
    task_file, task_id = sample_task

    # Create multiple documents
    plan_file = temp_git_repo / ".claude" / "task-plans" / f"{task_id}-implementation-plan.md"
    plan_file.write_text("# Plan")

    summary_file = temp_git_repo / f"{task_id}-IMPLEMENTATION-SUMMARY.md"
    summary_file.write_text("# Summary")

    report_file = temp_git_repo / f"{task_id}-COMPLETION-REPORT.md"
    report_file.write_text("# Report")

    # Archive to completed directory
    completed_dir = temp_git_repo / "tasks" / "completed" / "2025-11"
    completed_dir.mkdir(parents=True, exist_ok=True)

    archived_count = archive_task_documents(task_id, completed_dir)

    # Verify all documents moved
    assert archived_count == 3
    assert not plan_file.exists()
    assert not summary_file.exists()
    assert not report_file.exists()
    assert (completed_dir / f"{task_id}-implementation-plan.md").exists()
    assert (completed_dir / f"{task_id}-IMPLEMENTATION-SUMMARY.md").exists()
    assert (completed_dir / f"{task_id}-COMPLETION-REPORT.md").exists()


# ============================================================================
# Test 5: Document archival without documents (edge case)
# ============================================================================

def test_archive_without_documents(sample_task, temp_git_repo):
    """Test task completion when no documents exist."""
    os.chdir(temp_git_repo)
    task_file, task_id = sample_task

    # No documents created
    completed_dir = temp_git_repo / "tasks" / "completed" / "2025-11"
    completed_dir.mkdir(parents=True, exist_ok=True)

    archived_count = archive_task_documents(task_id, completed_dir)

    # Should complete without error (archived_count = 0)
    assert archived_count == 0


# ============================================================================
# Test 6: Case-insensitive summary archival
# ============================================================================

def test_case_insensitive_summary_archival(sample_task, temp_git_repo):
    """Test archiving summaries with different case variations."""
    os.chdir(temp_git_repo)
    task_file, task_id = sample_task

    # Create files with different casing
    lowercase_file = temp_git_repo / f"{task_id}-implementation-summary.md"
    lowercase_file.write_text("# Lowercase")

    uppercase_file = temp_git_repo / f"{task_id}-COMPLETION-REPORT.md"
    uppercase_file.write_text("# Uppercase")

    # Archive to completed directory
    completed_dir = temp_git_repo / "tasks" / "completed" / "2025-11"
    completed_dir.mkdir(parents=True, exist_ok=True)

    archived_count = archive_task_documents(task_id, completed_dir)

    # Both should be archived
    assert archived_count == 2
    assert (completed_dir / f"{task_id}-implementation-summary.md").exists()
    assert (completed_dir / f"{task_id}-COMPLETION-REPORT.md").exists()


# ============================================================================
# Test 7: move_task_to_completed()
# ============================================================================

def test_move_task_to_completed_with_month_subfolder(sample_task, temp_git_repo):
    """Test moving task to completed directory with month organization."""
    os.chdir(temp_git_repo)
    task_file, task_id = sample_task

    new_path, completed_dir = move_task_to_completed(task_file, month_subfolder=True)

    # Verify task moved
    assert not task_file.exists()
    assert new_path.exists()
    assert new_path.parent.name == datetime.now().strftime("%Y-%m")
    assert "completed" in str(new_path)


# ============================================================================
# Test 8: complete_task() full workflow
# ============================================================================

def test_complete_task_full_workflow(sample_task, temp_git_repo):
    """Test complete task workflow with all steps."""
    os.chdir(temp_git_repo)
    task_file, task_id = sample_task

    # Create documents
    plan_file = temp_git_repo / ".claude" / "task-plans" / f"{task_id}-implementation-plan.md"
    plan_file.write_text("# Plan")

    summary_file = temp_git_repo / f"{task_id}-IMPLEMENTATION-SUMMARY.md"
    summary_file.write_text("# Summary")

    # Complete task
    result = complete_task(task_id)

    # Verify result
    assert result['task_id'] == task_id
    assert result['documents_archived'] == 2
    assert 'completed' in result['new_path']

    # Verify task moved
    assert not task_file.exists()
    assert Path(result['new_path']).exists()

    # Verify documents archived
    completed_dir = Path(result['completed_dir'])
    assert (completed_dir / f"{task_id}-implementation-plan.md").exists()
    assert (completed_dir / f"{task_id}-IMPLEMENTATION-SUMMARY.md").exists()


# ============================================================================
# Test 9: complete_task() with full path
# ============================================================================

def test_complete_task_with_full_path(sample_task, temp_git_repo):
    """Test completing task using full path."""
    os.chdir(temp_git_repo)
    task_file, task_id = sample_task

    # Complete using full path
    result = complete_task(str(task_file))

    # Should work the same as using task ID
    assert result['task_id'] == task_id
    assert not task_file.exists()
    assert Path(result['new_path']).exists()


# ============================================================================
# Test 10: Conductor worktree simulation
# ============================================================================

def test_complete_task_in_simulated_worktree(sample_task, temp_git_repo):
    """
    Test task completion from a subdirectory (simulates Conductor worktree).

    This test simulates the Conductor scenario where:
    - Commands run from .conductor/carthage/ subdirectory
    - Tasks should still be found in main repo's tasks/ directory
    """
    os.chdir(temp_git_repo)
    task_file, task_id = sample_task

    # Create a subdirectory to simulate Conductor worktree
    worktree_sim = temp_git_repo / ".conductor" / "carthage"
    worktree_sim.mkdir(parents=True)

    # Change to worktree directory
    os.chdir(worktree_sim)

    # Should still find task in main repo
    found = find_task_file(task_id)
    assert found is not None
    assert task_id in found.name

    # Complete task from worktree directory
    result = complete_task(task_id)

    # Verify task completed in main repo
    assert result['task_id'] == task_id
    assert not task_file.exists()
    assert Path(result['new_path']).exists()
    # Verify path is in main repo, not worktree
    assert ".conductor" not in result['new_path']


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
