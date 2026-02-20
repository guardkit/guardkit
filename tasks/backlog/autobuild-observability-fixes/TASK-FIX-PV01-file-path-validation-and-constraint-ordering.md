---
id: TASK-FIX-PV01
title: Fix file path validation and documentation constraint ordering
status: backlog
created: 2026-02-20T00:00:00Z
updated: 2026-02-20T00:00:00Z
priority: high
tags: [autobuild, bugfix, file-detection, parser]
task_type: feature
complexity: 4
parent_review: TASK-REV-A515
feature_id: FEAT-AOF
wave: 1
implementation_mode: task-work
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Fix file path validation and documentation constraint ordering

## Description

Fix two related bugs in `guardkit/orchestrator/agent_invoker.py` that cause false-positive documentation constraint violation warnings:

1. **R1 — Spurious file path parsing:** The `TaskWorkStreamParser` regex patterns (`FILES_CREATED_PATTERN`, `TOOL_RESULT_CREATED_PATTERN`) match natural language fragments like `'house'` and `'**'` as file paths. Add path validation that rejects entries without `/` or `.` characters.

2. **R3 — Filter/validate ordering:** The `_validate_file_count_constraint()` runs in `_write_task_work_results()` BEFORE the `_is_valid_path` filter runs in `_create_player_report_from_task_work()`. Move filtering before validation.

These are the same pipeline and should be fixed together.

## Source

- Review report: `.claude/reviews/TASK-REV-A515-review-report.md` (Findings 1 and 3)
- Evidence: TASK-RK01-011 reported `'house'`, TASK-RK01-012 reported `'**'` as created files

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py`

## Implementation Plan

### Step 1: Add `_is_valid_file_path` method to `TaskWorkStreamParser`

Add a method that validates file path strings:
```python
def _is_valid_file_path(self, path: str) -> bool:
    """Validate that a string looks like a file path."""
    if not path or len(path) < 3:
        return False
    if path in ("*", "**", "***"):
        return False
    if path.startswith("*"):
        return False
    # Must contain a path separator or file extension
    return "/" in path or "\\" in path or "." in path
```

### Step 2: Apply validation in `_track_tool_call` and `parse_message`

Guard all `_files_created.add()` and `_files_modified.add()` calls with the validation.

### Step 3: Tighten `FILES_CREATED_PATTERN` regex

Change from:
```python
FILES_CREATED_PATTERN = re.compile(r"(?:Created|Added):\s*([^\s,]+)")
```
To require path-like strings:
```python
FILES_CREATED_PATTERN = re.compile(r"(?:Created|Added):\s*([^\s,]+(?:\.[a-zA-Z]+|/))")
```

Similarly tighten `FILES_MODIFIED_PATTERN`.

### Step 4: Move filtering into `_write_task_work_results`

Add path filtering BEFORE `_validate_file_count_constraint()` at line ~4115:
```python
# Filter invalid path entries before validation
results["files_created"] = [f for f in results["files_created"] if self._is_valid_file_path_static(f)]
results["files_modified"] = [f for f in results["files_modified"] if self._is_valid_file_path_static(f)]

# Validate file count constraint
self._validate_file_count_constraint(...)
```

### Step 5: Consolidate `_is_valid_path` in `_create_player_report_from_task_work`

Replace the inline `_is_valid_path` function with a call to the new centralised validation method.

## Acceptance Criteria

- [ ] `TaskWorkStreamParser` rejects non-path strings (no `/` or `.`)
- [ ] `'house'` and `'**'` would not appear in `files_created`
- [ ] `_validate_file_count_constraint` operates on filtered file list
- [ ] Existing valid file paths still pass validation
- [ ] Unit tests cover edge cases: `'house'`, `'**'`, `'*'`, `''`, valid paths
- [ ] `_is_valid_path` in `_create_player_report_from_task_work` uses shared validation
