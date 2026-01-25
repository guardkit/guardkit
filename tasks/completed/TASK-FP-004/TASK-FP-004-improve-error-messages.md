---
id: TASK-FP-004
title: Improve FeatureLoader error messages with schema hints
status: completed
created: 2026-01-06T09:15:00Z
updated: 2026-01-07T10:30:00Z
completed: 2026-01-07T10:30:00Z
priority: low
complexity: 2
tags: [error-handling, ux, feature-loader]
parent_review: TASK-REV-66B4
wave: 2
dependencies:
  - TASK-FP-001
implementation_mode: direct
testing_mode: standard
workspace: fp-schema-wave2-errors
completed_location: tasks/completed/TASK-FP-004/
---

# Task: Improve FeatureLoader error messages with schema hints

## Description

Enhance error messages in `FeatureLoader` to provide actionable guidance when schema parsing fails. Currently, errors like `KeyError: 'file_path'` don't tell users what the correct schema should be.

## Current Error Message

```
Invalid feature structure: FEAT-1682
Error: 'file_path'
```

## Expected Error Message

```
Invalid feature structure: FEAT-1682

Missing required field: 'file_path' in task entry

Expected task format:
  - id: TASK-XXX
    name: "Task Name"
    file_path: "tasks/backlog/.../TASK-XXX.md"  # <-- missing
    status: pending
    complexity: 5
    dependencies: []

Your task entry:
  - id: TASK-INFRA-001
    name: "Project Setup"
    wave: 1  # <-- not expected
    dependencies: []

Fix: Re-run /feature-plan to regenerate with correct schema
     Or manually add 'file_path' to each task entry
```

## Acceptance Criteria

- [x] Catch `KeyError` and show which field is missing
- [x] Show expected schema format for the missing section
- [x] Show the actual data that caused the error (truncated if long)
- [x] Provide actionable fix suggestions
- [x] Apply to both task parsing and orchestration parsing errors

## Files to Modify

- `guardkit/orchestrator/feature_loader.py`

## Implementation Notes

```python
@staticmethod
def _parse_task(task_data: Dict[str, Any]) -> FeatureTask:
    """Parse task with improved error handling."""
    required_fields = ["id", "file_path"]

    for field in required_fields:
        if field not in task_data:
            raise FeatureParseError(
                f"Missing required field: '{field}' in task entry\n\n"
                f"Expected task format:\n"
                f"  - id: TASK-XXX\n"
                f"    name: \"Task Name\"\n"
                f"    file_path: \"tasks/backlog/.../TASK-XXX.md\"\n"
                f"    status: pending\n"
                f"    ...\n\n"
                f"Your task entry:\n"
                f"  {yaml.dump(task_data, default_flow_style=False, indent=2)}\n\n"
                f"Fix: Re-run /feature-plan to regenerate with correct schema"
            )

    # ... existing parsing logic
```

## Test Cases

1. Missing `file_path` → shows expected format
2. Missing `id` → shows expected format
3. Invalid `orchestration` structure → shows parallel_groups format
4. Valid task → no error (regression test)
