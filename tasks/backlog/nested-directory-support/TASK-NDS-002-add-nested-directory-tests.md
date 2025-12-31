---
id: TASK-NDS-002
title: Add comprehensive tests for nested directory task discovery
status: backlog
created: 2025-12-31T12:00:00Z
updated: 2025-12-31T12:00:00Z
priority: medium
tags: [nested-directory-support, testing, task-loader]
complexity: 3
implementation_mode: task-work
parallel_group: 2
conductor_workspace: nested-dir-wave2-1
parent_review: TASK-REV-C675
dependencies: [TASK-NDS-001]
---

# Add Comprehensive Tests for Nested Directory Task Discovery

## Description

Add unit tests to `tests/unit/test_task_loader.py` to verify the new recursive search functionality works correctly for tasks in feature subfolders.

## Requirements

1. Test loading tasks from nested directories
2. Test extended filename matching
3. Test search order with nested directories
4. Test error message improvements
5. Ensure backward compatibility tests still pass

## Acceptance Criteria

- [ ] `test_load_task_from_nested_backlog` - Task in `tasks/backlog/feature-slug/`
- [ ] `test_load_task_with_extended_filename` - Task named `TASK-XXX-descriptive-name.md`
- [ ] `test_load_task_deep_nesting` - Task in multiple nesting levels
- [ ] `test_load_task_nested_search_order` - Backlog preferred over in_progress for nested
- [ ] All existing tests continue to pass (backward compatibility)
- [ ] Test coverage for `_find_task_file()` at 100%

## Files to Modify

- `tests/unit/test_task_loader.py` - Add new test cases

## Implementation Details

Execute with `/task-work TASK-NDS-002` for full quality gates (architecture review, tests, code review).

### Test Cases to Add

```python
def test_load_task_from_nested_backlog(tmp_path):
    """Test loading task from nested feature directory in backlog."""
    # Create nested task file
    task_file = tmp_path / "tasks" / "backlog" / "feature-slug" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("""---
id: TASK-AB-001
title: Nested Task
---

## Requirements
Implement feature in nested directory
""")

    # Load task
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify found in nested directory
    assert task_data["task_id"] == "TASK-AB-001"
    assert "feature-slug" in str(task_data["file_path"])


def test_load_task_with_extended_filename(tmp_path):
    """Test loading task with descriptive filename extension."""
    # Create task with extended filename
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001-create-auth-service.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("""---
id: TASK-AB-001
title: Create Auth Service
---

## Requirements
Create authentication service
""")

    # Load by ID only (without extension)
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify found with extended filename
    assert task_data["task_id"] == "TASK-AB-001"
    assert "create-auth-service" in str(task_data["file_path"])


def test_load_task_deep_nesting(tmp_path):
    """Test loading task from deeply nested directory."""
    # Create deeply nested task
    task_file = tmp_path / "tasks" / "backlog" / "epic" / "feature" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("""---
id: TASK-AB-001
---
Requirements
""")

    # Load task
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify found
    assert task_data["task_id"] == "TASK-AB-001"
```

## Dependencies

- TASK-NDS-001 (TaskLoader changes must be implemented first)

## Notes

Auto-generated from TASK-REV-C675 recommendations.
Tests validate the recursive search functionality works as expected.
