---
id: TASK-FSRF-005
title: "Extend _read_input_files extension support"
status: completed
completed: 2026-02-22T16:30:00Z
completed_location: tasks/completed/TASK-FSRF-005/
task_type: feature
parent_review: TASK-REV-FCA5
feature_id: FEAT-FSRF
created: 2026-02-22T12:00:00Z
updated: 2026-02-22T12:00:00Z
priority: low
tags: [feature-spec, enhancement, input]
complexity: 2
wave: 2
implementation_mode: task-work
dependencies: [TASK-FSRF-002]
tests_required: true
---

# Task: Extend _read_input_files extension support

## Description

`_read_input_files()` currently only supports `.md` and `.txt` files. Feature descriptions could also come in `.yaml`, `.rst`, or `.json` formats. Unsupported files are silently skipped, which may confuse users.

## Fix

Extend the supported extensions list:

```python
SUPPORTED_EXTENSIONS = {".md", ".txt", ".yaml", ".yml", ".rst", ".json"}
```

For `.json` files, consider pretty-printing or extracting relevant text rather than dumping raw JSON.

## Acceptance Criteria

- [x] `.yaml`, `.yml`, `.rst` files are read and concatenated
- [x] `.json` files are read (content included as-is for v2 simplicity)
- [x] Warning message for unsupported extensions is clear about which extensions are supported
- [x] Tests cover each new extension type
- [x] Tests verify warning message includes supported extensions list

## Files to Change

- `guardkit/commands/feature_spec.py`
- `tests/unit/commands/test_feature_spec.py`
