import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to sys.path so we can import our module
sys.path.insert(0, str(Path(__file__).parent.parent))

from installer.core.commands.lib.task_status_json import (
    scan_tasks,
    get_task_summary,
    sort_tasks,
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