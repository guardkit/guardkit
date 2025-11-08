---
id: TASK-047
title: Add ID validation and collision detection
status: backlog
created: 2025-01-08T00:00:00Z
updated: 2025-01-08T00:00:00Z
priority: high
tags: [infrastructure, hash-ids, validation]
complexity: 4
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add ID validation and collision detection

## Description

Implement comprehensive validation and collision detection for task IDs to prevent duplicates from ever being created. This includes pre-creation checks, format validation, and a registry of existing IDs.

## Acceptance Criteria

- [ ] Validate ID format matches pattern: `TASK-([A-Z0-9]{2,4}-)?[a-f0-9]{4,6}(\.\d+)?`
- [ ] Check for duplicates across all task directories (backlog, in_progress, in_review, blocked, completed)
- [ ] Support subtask validation (dot notation: `TASK-E01-b2c4.1`)
- [ ] Clear error messages when duplicate detected
- [ ] Performance: Validate 1,000 IDs in <100ms
- [ ] Thread-safe validation for concurrent creation
- [ ] Registry caching for performance (refresh on miss)

## Test Requirements

- [ ] Unit tests for format validation (valid and invalid patterns)
- [ ] Unit tests for duplicate detection
- [ ] Unit tests for subtask notation validation
- [ ] Integration tests checking all task directories
- [ ] Performance tests (1,000 validations in <100ms)
- [ ] Concurrent validation tests (10 simultaneous checks)
- [ ] Test coverage ≥85%

## Implementation Notes

### File Location
Add to: `installer/global/lib/id_generator.py`

### Key Functions
```python
def validate_task_id(task_id: str) -> bool:
    """Validate task ID format."""

def check_duplicate(task_id: str) -> Optional[str]:
    """Check if task ID exists. Returns path if duplicate, None otherwise."""

def build_id_registry() -> Set[str]:
    """Build registry of all existing task IDs."""

def is_valid_prefix(prefix: str) -> bool:
    """Validate prefix format (2-4 uppercase alphanumeric)."""
```

### Validation Rules
1. **Format**: `TASK-{hash}` or `TASK-{prefix}-{hash}` or `TASK-{prefix}-{hash}.{subtask}`
2. **Prefix**: 2-4 uppercase alphanumeric characters (optional)
3. **Hash**: 4-6 lowercase hexadecimal characters
4. **Subtask**: Dot followed by 1-3 digits (optional)

### Search Paths
```python
TASK_DIRECTORIES = [
    "tasks/backlog/",
    "tasks/in_progress/",
    "tasks/in_review/",
    "tasks/blocked/",
    "tasks/completed/",
]
```

### Error Messages
```python
ERROR_DUPLICATE = "❌ ERROR: Duplicate task ID: {task_id}\n   Existing file: {path}"
ERROR_INVALID_FORMAT = "❌ ERROR: Invalid task ID format: {task_id}\n   Expected: TASK-{hash} or TASK-{prefix}-{hash}"
ERROR_INVALID_PREFIX = "❌ ERROR: Invalid prefix: {prefix}\n   Expected: 2-4 uppercase alphanumeric characters"
```

## Dependencies

- TASK-046: Core hash ID generator (must be completed first)

## Related Tasks

- TASK-046: Hash ID generator
- TASK-048: Update /task-create command
- TASK-052: Migration script

## Test Execution Log

[Automatically populated by /task-work]
