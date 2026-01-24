---
id: TASK-FTF-002
title: Add test count extraction from pytest output
status: in_review
created: 2026-01-24T12:00:00Z
updated: 2026-01-24T16:30:00Z
priority: low
complexity: 3
tags: [autobuild, agent-invoker, test-tracking, display]
task_type: feature
implementation_mode: direct
parent_review: TASK-REV-BRF
feature_id: file-tracking-fix
wave: 1
dependencies: []
quality_gates:
  tests_passed: 250
  tests_failed: 0
  new_tests: 16
---

# Task: Add test count extraction from pytest output

## Description

Improve the test count display in AutoBuild progress output by extracting actual test counts from pytest execution output or by tracking test file creation.

## Context

Currently, the "0 tests" display appears even when tests are written and passing. This creates confusion about whether tests were actually created.

## Acceptance Criteria

1. [x] Test file creation is tracked (files matching `test_*.py` or `*_test.py`)
2. [x] Pytest output is parsed for test counts when available
3. [x] Progress display shows accurate test counts
4. [x] Falls back gracefully when pytest output unavailable

## Implementation Summary

### Changes Made

**File: `guardkit/orchestrator/agent_invoker.py`**

1. Added new regex patterns (lines 186-193):
   - `PYTEST_SUMMARY_PATTERN` - Full pytest summary parsing (`===== 15 passed, 2 failed =====`)
   - `PYTEST_SIMPLE_PATTERN` - Simple pattern (`5 passed in 0.23s`)

2. Added new attribute in `__init__`:
   - `self._test_files_created: set = set()` - Tracks test files created

3. Added new method `_is_test_file(file_path)`:
   - Detects test files using naming conventions (`test_*.py`, `*_test.py`)
   - Handles both Unix and Windows path separators

4. Updated `_track_tool_call()`:
   - Now tracks test files separately when Write tool creates a test file

5. Updated `parse_message()`:
   - Parses pytest summary output for test counts
   - Uses higher count logic to avoid overwriting with lower values

6. Updated `to_result()`:
   - Returns `test_files_created` list in result dictionary

7. Updated `reset()`:
   - Clears `_test_files_created` set

**File: `tests/unit/test_agent_invoker.py`**

Added 16 new tests covering:
- `_is_test_file()` detection logic (4 tests)
- Test file tracking via `_track_tool_call()` (5 tests)
- Reset behavior for test files (1 test)
- Pytest summary pattern parsing (6 tests)

### Test Results

- 250 total tests pass (all tests including 16 new)
- No regressions in existing functionality

## Technical Approach

### Track Test File Creation

```python
def _is_test_file(self, file_path: str) -> bool:
    """Check if a file path is a test file."""
    if not file_path:
        return False
    name = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
    name = name.rsplit("\\", 1)[-1] if "\\" in name else name
    return name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py")
```

### Parse Pytest Output

```python
# Full pytest summary: "===== 15 passed, 2 failed ====="
PYTEST_SUMMARY_PATTERN = re.compile(
    r"[=]+\s*(?:(\d+)\s+passed)?(?:,?\s*(\d+)\s+failed)?(?:,?\s*(\d+)\s+skipped)?.*?[=]+"
)

# Simple pattern: "5 passed in 0.23s"
PYTEST_SIMPLE_PATTERN = re.compile(r"(\d+)\s+passed(?:\s+in\s+[\d.]+s)?")
```

## Files Modified

- `guardkit/orchestrator/agent_invoker.py` - TaskWorkStreamParser class
- `tests/unit/test_agent_invoker.py` - Added 16 new tests

## Definition of Done

- [x] Test file tracking implemented
- [x] Pytest output parsing added
- [x] Display shows accurate test counts
- [x] Unit tests added
