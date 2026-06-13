import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add the project root to sys.path so we can import our module
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from installer.core.commands.lib.task_status_json import (
    scan_tasks,
    get_task_summary,
    sort_tasks,
    build_task_json,
    main
)


def test_scan_tasks_empty():
    """Test scanning tasks when there are no tasks."""
    # Mock an empty directory
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pathlib.Path.glob', return_value=[]):
            tasks = scan_tasks(Path("."))
            assert tasks == []


def test_get_task_summary():
    """Test task summary calculation."""
    tasks = [
        {"id": "TASK-001", "status": "backlog"},
        {"id": "TASK-002", "status": "in_progress"},
        {"id": "TASK-003", "status": "completed"},
        {"id": "TASK-004", "status": "in_review"},
        {"id": "TASK-005", "status": "blocked"},
        {"id": "TASK-006", "status": "backlog"},
    ]
    
    summary = get_task_summary(tasks)
    expected = {
        "backlog": 2,
        "in_progress": 1,
        "in_review": 1,
        "blocked": 1,
        "completed": 1,
        "total": 6
    }
    
    assert summary == expected


def test_get_task_summary_with_parse_errors():
    """Test task summary calculation with parse errors."""
    tasks = [
        {"id": "TASK-001", "status": "backlog"},
        {"id": "TASK-002", "status": "in_progress", "parse_error": True},
        {"id": "TASK-003", "status": "completed"},
    ]
    
    summary = get_task_summary(tasks)
    expected = {
        "backlog": 1,
        "in_progress": 0,  # parse error tasks are not counted
        "in_review": 0,
        "blocked": 0,
        "completed": 1,
        "total": 2  # only non-parse-error tasks count
    }
    
    assert summary == expected


def test_sort_tasks():
    """Test task sorting by status and ID."""
    tasks = [
        {"id": "TASK-003", "status": "completed"},
        {"id": "TASK-001", "status": "backlog"},
        {"id": "TASK-002", "status": "in_progress"},
        {"id": "TASK-004", "status": "backlog"},
    ]
    
    sorted_tasks = sort_tasks(tasks)
    
    # Should be sorted by status (backlog, in_progress, completed) then by ID
    expected_ids = ["TASK-001", "TASK-004", "TASK-002", "TASK-003"]
    actual_ids = [task["id"] for task in sorted_tasks]
    
    assert actual_ids == expected_ids


def test_sort_tasks_with_unknown_status():
    """Test task sorting with unknown status."""
    tasks = [
        {"id": "TASK-001", "status": "unknown_status"},
        {"id": "TASK-002", "status": "backlog"},
    ]
    
    sorted_tasks = sort_tasks(tasks)
    
    # Unknown status should be sorted last
    expected_ids = ["TASK-002", "TASK-001"]
    actual_ids = [task["id"] for task in sorted_tasks]
    
    assert actual_ids == expected_ids


def test_build_task_json_schema_compliance():
    """Test that build_task_json produces schema-compliant output."""
    task_data = {
        "id": "TASK-001",
        "title": "Test Task",
        "status": "backlog",
        "priority": "high",
        "task_type": "feature",
        "complexity": 4,
        "tags": ["tag1", "tag2"],
        "created": "2023-01-01",
        "updated": "2023-01-02",
        "epic": "EPIC-001",
        "feature": "FEAT-001",
        "parent_review": "TASK-REV-001",
        "feature_id": "FEAT-001",
        "file_path": "tasks/backlog/TASK-001.md",
        "external_ids": {"jira": "PROJ-123"},
        "legacy_id": "OLD-123"
    }
    
    result = build_task_json(task_data)
    
    # All fields should be present, even if None
    expected_fields = [
        "id", "title", "status", "priority", "task_type", "complexity", "tags",
        "created", "updated", "epic", "feature", "parent_review", "feature_id",
        "file_path", "parse_error", "external_ids", "legacy_id"
    ]
    
    for field in expected_fields:
        assert field in result
    
    # Verify specific values
    assert result["id"] == "TASK-001"
    assert result["title"] == "Test Task"
    assert result["status"] == "backlog"
    assert result["file_path"] == "tasks/backlog/TASK-001.md"
    assert result["external_ids"] == {"jira": "PROJ-123"}
    assert result["legacy_id"] == "OLD-123"


def test_build_task_json_missing_fields():
    """Test that build_task_json handles missing fields gracefully."""
    task_data = {
        "id": "TASK-001",
        "title": "Test Task"
        # Missing many fields
    }
    
    result = build_task_json(task_data)
    
    # Missing fields should be None
    assert result["status"] is None
    assert result["priority"] is None
    assert result["task_type"] is None
    assert result["complexity"] is None
    assert result["tags"] is None
    assert result["created"] is None
    assert result["updated"] is None
    assert result["epic"] is None
    assert result["feature"] is None
    assert result["parent_review"] is None
    assert result["feature_id"] is None
    assert result["file_path"] is None
    assert result["parse_error"] is None
    assert result["external_ids"] is None
    assert result["legacy_id"] is None


def test_build_task_json_parse_error():
    """Test that build_task_json handles parse error tasks."""
    task_data = {
        "id": "TASK-001",
        "parse_error": True,
        "file_path": "tasks/backlog/TASK-001.md"
    }
    
    result = build_task_json(task_data)
    
    assert result["id"] == "TASK-001"
    assert result["parse_error"] is True
    assert result["file_path"] == "tasks/backlog/TASK-001.md"