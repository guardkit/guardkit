"""
Comprehensive Test Suite for Pipeline Data Loss Fixes (TASK-FIX-PIPELINE-DATA-LOSS)

Tests five critical fixes to prevent data loss in the Player-Coach pipeline:
1. _track_tool_call() tries multiple key names for file paths
2. Promise recovery in _create_player_report_from_task_work()
3. task_work_results.json update after enrichment
4. Filter spurious git entries ("**", "*", empty strings)
5. File-existence verification fallback when no agent promises

Coverage Target: >=85%
Test Count: 11 tests
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    TaskWorkStreamParser,
)
from guardkit.orchestrator.exceptions import TaskWorkResult
from guardkit.orchestrator.paths import TaskArtifactPaths


# ==================== Fixtures ====================


@pytest.fixture
def worktree_path(tmp_path):
    """Create temporary worktree directory."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return worktree


@pytest.fixture
def agent_invoker(worktree_path):
    """Create AgentInvoker instance."""
    return AgentInvoker(
        worktree_path=worktree_path,
        max_turns_per_agent=30,
        sdk_timeout_seconds=60,
    )


@pytest.fixture
def stream_parser():
    """Create TaskWorkStreamParser instance."""
    return TaskWorkStreamParser()


# ============================================================================
# Fix 1: _track_tool_call() with Multiple Key Names (5 tests)
# ============================================================================


def test_track_tool_call_with_file_path_key(stream_parser):
    """Test _track_tool_call works with standard file_path key."""
    stream_parser._track_tool_call("Write", {"file_path": "src/auth.py"})

    assert "src/auth.py" in stream_parser._files_created
    assert len(stream_parser._files_created) == 1


def test_track_tool_call_with_path_key(stream_parser):
    """Test _track_tool_call works with path key."""
    stream_parser._track_tool_call("Write", {"path": "src/database.py"})

    assert "src/database.py" in stream_parser._files_created
    assert len(stream_parser._files_created) == 1


def test_track_tool_call_with_file_key(stream_parser):
    """Test _track_tool_call works with file key."""
    stream_parser._track_tool_call("Write", {"file": "src/config.py"})

    assert "src/config.py" in stream_parser._files_created
    assert len(stream_parser._files_created) == 1


def test_track_tool_call_with_filePath_key(stream_parser):
    """Test _track_tool_call works with filePath key (camelCase)."""
    stream_parser._track_tool_call("Write", {"filePath": "src/utils.py"})

    assert "src/utils.py" in stream_parser._files_created
    assert len(stream_parser._files_created) == 1


def test_track_tool_call_no_matching_key(stream_parser):
    """Test _track_tool_call returns without error when no matching key."""
    # Should not raise exception
    stream_parser._track_tool_call("Write", {"content": "some code", "other_key": "value"})

    # Should not track any files
    assert len(stream_parser._files_created) == 0
    assert len(stream_parser._files_modified) == 0


# ============================================================================
# Fix 2: Promise Recovery in _create_player_report_from_task_work (1 test)
# ============================================================================


def test_create_player_report_preserves_agent_promises(agent_invoker, worktree_path, tmp_path):
    """Test that promises written by agent are preserved when creating player report."""
    task_id = "TASK-TEST-001"
    turn = 1

    # Setup autobuild directory
    autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)

    # Create task_work_results.json with NO promises
    task_work_results = {
        "files_modified": ["src/app.py"],
        "files_created": ["tests/test_app.py"],
        "tests_info": {
            "tests_run": True,
            "tests_passed": True,
            "output_summary": "5 passed",
        }
    }
    task_work_results_path = autobuild_dir / "task_work_results.json"
    task_work_results_path.write_text(json.dumps(task_work_results, indent=2))

    # Create player report with agent-written promises (simulating agent writing first)
    agent_written_promises = [
        {
            "criterion_id": "AC-001",
            "status": "completed",
            "evidence": "Implemented authentication flow",
            "evidence_type": "implementation"
        },
        {
            "criterion_id": "AC-002",
            "status": "partial",
            "evidence": "Created tests, need edge cases",
            "evidence_type": "testing"
        }
    ]
    agent_written_report = {
        "task_id": task_id,
        "turn": turn,
        "files_modified": ["src/app.py"],
        "files_created": ["tests/test_app.py"],
        "completion_promises": agent_written_promises,
        "requirements_addressed": ["OAuth2 authentication"],
        "requirements_remaining": ["Token refresh"]
    }
    player_report_path = TaskArtifactPaths.player_report_path(task_id, turn, worktree_path)
    player_report_path.write_text(json.dumps(agent_written_report, indent=2))

    # Create TaskWorkResult with correct signature
    task_work_result = TaskWorkResult(
        success=True,
        output={}
    )

    # Call method - should preserve agent promises
    agent_invoker._create_player_report_from_task_work(task_id, turn, task_work_result)

    # Read back the player report
    final_report = json.loads(player_report_path.read_text())

    # Verify promises were preserved
    assert "completion_promises" in final_report
    assert len(final_report["completion_promises"]) == 2
    assert final_report["completion_promises"][0]["criterion_id"] == "AC-001"
    assert final_report["completion_promises"][1]["status"] == "partial"

    # Verify requirements were preserved
    assert final_report["requirements_addressed"] == ["OAuth2 authentication"]
    assert final_report["requirements_remaining"] == ["Token refresh"]


# ============================================================================
# Fix 3: task_work_results.json Update After Enrichment (1 test)
# ============================================================================


def test_create_player_report_updates_task_work_results(agent_invoker, worktree_path):
    """Test that task_work_results.json is updated with enriched data after git detection."""
    task_id = "TASK-TEST-002"
    turn = 1

    # Setup autobuild directory
    autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)

    # Create task_work_results.json with minimal data
    task_work_results = {
        "files_modified": [],  # Empty - git will detect more
        "files_created": [],   # Empty - git will detect more
    }
    task_work_results_path = autobuild_dir / "task_work_results.json"
    task_work_results_path.write_text(json.dumps(task_work_results, indent=2))

    # Mock git detection to return files
    mock_git_changes = {
        "modified": ["src/auth.py", "src/config.py"],
        "created": ["tests/test_auth.py"]
    }

    # Create TaskWorkResult with correct signature
    task_work_result = TaskWorkResult(
        success=True,
        output={}
    )

    # Patch _detect_git_changes
    with patch.object(agent_invoker, '_detect_git_changes', return_value=mock_git_changes):
        agent_invoker._create_player_report_from_task_work(task_id, turn, task_work_result)

    # Read back task_work_results.json - should be enriched
    enriched_data = json.loads(task_work_results_path.read_text())

    # Verify enrichment
    assert len(enriched_data["files_modified"]) == 2
    assert "src/auth.py" in enriched_data["files_modified"]
    assert "src/config.py" in enriched_data["files_modified"]
    assert len(enriched_data["files_created"]) == 1
    assert "tests/test_auth.py" in enriched_data["files_created"]


# ============================================================================
# Fix 4: Filter Spurious Git Entries (1 test)
# ============================================================================


def test_git_detection_filters_wildcards(agent_invoker, worktree_path):
    """Test that wildcard entries like '**' and '*' are filtered from file lists."""
    task_id = "TASK-TEST-003"
    turn = 1

    # Setup autobuild directory
    autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)

    # Create task_work_results.json
    task_work_results = {
        "files_modified": [],
        "files_created": [],
    }
    task_work_results_path = autobuild_dir / "task_work_results.json"
    task_work_results_path.write_text(json.dumps(task_work_results, indent=2))

    # Mock git detection to return spurious entries
    mock_git_changes = {
        "modified": ["src/auth.py", "**", "*", "", "   ", "***", "*test.py"],  # Mix of valid and invalid
        "created": ["tests/test_auth.py", "**"]  # One valid, one invalid
    }

    # Create TaskWorkResult with correct signature
    task_work_result = TaskWorkResult(
        success=True,
        output={}
    )

    # Patch _detect_git_changes
    with patch.object(agent_invoker, '_detect_git_changes', return_value=mock_git_changes):
        agent_invoker._create_player_report_from_task_work(task_id, turn, task_work_result)

    # Read back player report
    player_report_path = TaskArtifactPaths.player_report_path(task_id, turn, worktree_path)
    report = json.loads(player_report_path.read_text())

    # Verify filtering - only valid files should remain
    assert "**" not in report["files_modified"]
    assert "*" not in report["files_modified"]
    assert "***" not in report["files_modified"]
    assert "*test.py" not in report["files_modified"]
    assert "" not in report["files_modified"]
    assert "src/auth.py" in report["files_modified"]  # Valid file kept

    assert "**" not in report["files_created"]
    assert "tests/test_auth.py" in report["files_created"]  # Valid file kept


# ============================================================================
# Fix 5: File-Existence Verification Fallback (3 tests)
# ============================================================================


def test_file_existence_promises_generated_when_no_agent_promises(agent_invoker, worktree_path, tmp_path):
    """Test that file-existence promises are generated when agent provides no promises."""
    task_id = "TASK-TEST-004"
    turn = 1

    # Create task file with acceptance criteria
    tasks_backlog = worktree_path / "tasks" / "backlog"
    tasks_backlog.mkdir(parents=True)
    task_file = tasks_backlog / f"{task_id}.md"
    task_content = """---
id: TASK-TEST-004
title: Test Task
acceptance_criteria:
  - Create `src/auth.py` with authentication logic
  - Create `tests/test_auth.py` with test coverage
  - Update `README.md` with usage instructions
---

Task description here.
"""
    task_file.write_text(task_content)

    # Setup autobuild directory
    autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)

    # Create task_work_results.json with NO promises
    task_work_results = {
        "files_modified": ["README.md"],
        "files_created": ["src/auth.py", "tests/test_auth.py"],
    }
    task_work_results_path = autobuild_dir / "task_work_results.json"
    task_work_results_path.write_text(json.dumps(task_work_results, indent=2))

    # Create actual files in worktree
    (worktree_path / "src").mkdir(parents=True, exist_ok=True)
    (worktree_path / "src" / "auth.py").write_text("# auth code")
    (worktree_path / "tests").mkdir(parents=True, exist_ok=True)
    (worktree_path / "tests" / "test_auth.py").write_text("# test code")
    (worktree_path / "README.md").write_text("# readme")

    # Create TaskWorkResult with correct signature
    task_work_result = TaskWorkResult(
        success=True,
        output={}
    )

    # Patch _detect_git_changes to return empty
    with patch.object(agent_invoker, '_detect_git_changes', return_value={}):
        agent_invoker._create_player_report_from_task_work(task_id, turn, task_work_result)

    # Read back player report
    player_report_path = TaskArtifactPaths.player_report_path(task_id, turn, worktree_path)
    report = json.loads(player_report_path.read_text())

    # Verify synthetic promises were generated
    assert "completion_promises" in report
    assert len(report["completion_promises"]) == 3  # One per AC

    # Verify promise structure
    promise1 = report["completion_promises"][0]
    assert promise1["criterion_id"] == "AC-001"
    assert promise1["evidence_type"] == "file_existence"
    assert promise1["status"] in ["partial", "incomplete"]
    assert "src/auth.py" in promise1["evidence"] or "No file references" in promise1["evidence"]


def test_file_existence_promises_skipped_when_agent_promises_exist(agent_invoker, worktree_path):
    """Test that file-existence fallback doesn't overwrite real agent promises."""
    task_id = "TASK-TEST-005"
    turn = 1

    # Create task file with acceptance criteria
    tasks_backlog = worktree_path / "tasks" / "backlog"
    tasks_backlog.mkdir(parents=True)
    task_file = tasks_backlog / f"{task_id}.md"
    task_content = """---
id: TASK-TEST-005
title: Test Task
acceptance_criteria:
  - Create authentication module
---

Task description.
"""
    task_file.write_text(task_content)

    # Setup autobuild directory
    autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)

    # Create task_work_results.json WITH agent promises
    agent_promises = [
        {
            "criterion_id": "AC-001",
            "status": "completed",
            "evidence": "Implemented OAuth2 authentication with JWT tokens",
            "evidence_type": "implementation"
        }
    ]
    task_work_results = {
        "files_created": ["src/auth.py"],
        "completion_promises": agent_promises  # Agent provided real promises
    }
    task_work_results_path = autobuild_dir / "task_work_results.json"
    task_work_results_path.write_text(json.dumps(task_work_results, indent=2))

    # Create TaskWorkResult with correct signature
    task_work_result = TaskWorkResult(
        success=True,
        output={}
    )

    # Patch _detect_git_changes
    with patch.object(agent_invoker, '_detect_git_changes', return_value={}):
        agent_invoker._create_player_report_from_task_work(task_id, turn, task_work_result)

    # Read back player report
    player_report_path = TaskArtifactPaths.player_report_path(task_id, turn, worktree_path)
    report = json.loads(player_report_path.read_text())

    # Verify agent promises were preserved (not replaced by file-existence)
    assert "completion_promises" in report
    assert len(report["completion_promises"]) == 1
    assert report["completion_promises"][0]["evidence_type"] == "implementation"  # NOT file_existence
    assert "OAuth2 authentication" in report["completion_promises"][0]["evidence"]


def test_file_existence_promises_extracts_backtick_paths(agent_invoker, worktree_path):
    """Test that file paths in backticks are correctly extracted from acceptance criteria."""
    task_id = "TASK-TEST-006"
    turn = 1

    # Create task file with various backtick patterns
    tasks_backlog = worktree_path / "tasks" / "backlog"
    tasks_backlog.mkdir(parents=True)
    task_file = tasks_backlog / f"{task_id}.md"
    task_content = """---
id: TASK-TEST-006
title: Test Task
acceptance_criteria:
  - Create `src/database.py` with connection logic
  - Implement tests in `tests/seam/` directory
  - Update config in `config.yaml` file
---

Task description.
"""
    task_file.write_text(task_content)

    # Setup autobuild directory
    autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)

    # Create task_work_results.json with NO promises
    task_work_results = {
        "files_created": ["src/database.py", "config.yaml"],
    }
    task_work_results_path = autobuild_dir / "task_work_results.json"
    task_work_results_path.write_text(json.dumps(task_work_results, indent=2))

    # Create actual files/dirs in worktree
    (worktree_path / "src").mkdir(parents=True, exist_ok=True)
    (worktree_path / "src" / "database.py").write_text("# db code")
    (worktree_path / "tests" / "seam").mkdir(parents=True, exist_ok=True)
    (worktree_path / "config.yaml").write_text("# config")

    # Create TaskWorkResult with correct signature
    task_work_result = TaskWorkResult(
        success=True,
        output={}
    )

    # Patch _detect_git_changes
    with patch.object(agent_invoker, '_detect_git_changes', return_value={}):
        agent_invoker._create_player_report_from_task_work(task_id, turn, task_work_result)

    # Read back player report
    player_report_path = TaskArtifactPaths.player_report_path(task_id, turn, worktree_path)
    report = json.loads(player_report_path.read_text())

    # Verify promises were generated with backtick extraction
    assert "completion_promises" in report
    assert len(report["completion_promises"]) == 3

    # Check that backtick-referenced files were detected
    evidences = [p["evidence"] for p in report["completion_promises"]]
    combined_evidence = " ".join(evidences)

    # At least some files/dirs should be mentioned
    assert "database.py" in combined_evidence or "config.yaml" in combined_evidence or "seam" in combined_evidence
