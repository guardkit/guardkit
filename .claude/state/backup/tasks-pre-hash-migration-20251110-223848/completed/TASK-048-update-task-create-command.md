---
id: TASK-048
title: Update /task-create to use hash-based IDs
status: completed
created: 2025-01-08T00:00:00Z
updated: 2025-11-10T19:21:00Z
completed_at: 2025-11-10T19:21:00Z
priority: high
tags: [infrastructure, hash-ids, commands]
complexity: 6
test_results:
  status: passed
  coverage: 100%
  last_run: 2025-11-10T19:21:00Z
  tests_total: 39
  tests_passed: 39
  tests_failed: 0
  test_file: tests/unit/test_task_create_hash_ids.py
completion_notes: |
  Implemented via Conductor workflow. All 39 tests passing (100%).
  Test categories: prefix parsing, ID generation, validation, duplicate detection,
  backward compatibility, concurrent generation, error messages.
---

# Task: Update /task-create to use hash-based IDs

## Description

Replace the current sequential ID generation in `/task-create` command with the new hash-based generator. Add support for prefix parameter and maintain backward compatibility for reading existing task formats.

## Acceptance Criteria

- [x] `/task-create` generates hash-based IDs by default
- [x] Support `prefix:` parameter for namespacing (e.g., `prefix:E01`, `prefix:DOC`)
- [x] Pre-creation validation prevents duplicates
- [x] Clear error messages if ID collision detected (rare)
- [x] Backward compatibility: Can still read old format tasks
- [x] Update task frontmatter template with new ID format
- [x] Update example output in command documentation
- [x] Success message shows generated ID format

## Test Requirements

- [x] Unit tests for ID generation in /task-create
- [x] Unit tests for prefix parameter parsing
- [x] Integration tests creating multiple tasks (no duplicates)
- [x] Integration tests with existing tasks (no conflicts)
- [x] Concurrent creation tests (10 simultaneous task creates)
- [x] Backward compatibility tests (read old format tasks)
- [x] Test coverage ≥80%

## Implementation Notes

### Files to Modify
1. `installer/global/commands/task-create.md` - Update documentation
2. Command implementation script (search for current ID generation logic)

### Changes Required

**Before (Sequential)**:
```bash
# Find highest task number
max_num=$(find tasks -name "TASK-*.md" | sed 's/.*TASK-\([0-9]*\).*/\1/' | sort -n | tail -1)
next_num=$((max_num + 1))
task_id="TASK-$(printf '%03d' $next_num)"
```

**After (Hash-based)**:
```python
from installer.global.lib.id_generator import generate_task_id, validate_task_id

# Parse prefix from args
prefix = parse_prefix_from_args(args)  # e.g., "E01", "DOC", None

# Generate ID
task_id = generate_task_id(prefix=prefix)

# Validate (redundant but safe)
if not validate_task_id(task_id):
    raise ValueError(f"Generated invalid task ID: {task_id}")
```

### Prefix Parameter Syntax
```bash
# Simple task (no prefix)
/task-create "Fix login bug"
# Generated: TASK-a3f8

# With epic prefix
/task-create "Add authentication" prefix:E01
# Generated: TASK-E01-b2c4

# With domain prefix
/task-create "Update installation guide" prefix:DOC
# Generated: TASK-DOC-f1a3
```

### Output Format Update
```
✅ Task Created: TASK-E01-b2c4

📋 Task Details
Title: Add user authentication
Priority: high
Status: backlog
Tags: [auth, security]

📁 File Location
tasks/backlog/TASK-E01-b2c4-add-user-authentication.md

Next Steps:
1. Review task details
2. When ready: /task-work TASK-E01-b2c4
```

### Backward Compatibility
- Can read old format: TASK-004, TASK-004A, TASK-030B-1
- Old IDs stored in `legacy_id` field if migrating
- New tasks always use hash format

## Dependencies

- TASK-046: Hash ID generator (must be completed)
- TASK-047: ID validation (must be completed)

## Related Tasks

- TASK-046: Core generator
- TASK-047: Validation
- TASK-054: Add prefix support and inference

## Test Execution Log

**Test Run: 2025-11-10T19:21:00Z**
- Test file: tests/unit/test_task_create_hash_ids.py
- Total tests: 39
- Passed: 39 (100%)
- Coverage: 100%
- All test categories validated successfully
