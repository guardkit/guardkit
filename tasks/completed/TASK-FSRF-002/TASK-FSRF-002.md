---
id: TASK-FSRF-002
title: "Fix write_outputs to pass detected stack to summary generator"
status: completed
completed: 2026-02-22T14:05:00Z
task_type: feature
parent_review: TASK-REV-FCA5
feature_id: FEAT-FSRF
created: 2026-02-22T12:00:00Z
updated: 2026-02-22T14:00:00Z
priority: low
tags: [feature-spec, bug-fix, summary]
complexity: 2
wave: 1
implementation_mode: task-work
dependencies: []
tests_required: true
---

# Task: Fix write_outputs to pass detected stack to summary generator

## Description

In `guardkit/commands/feature_spec.py`, the `write_outputs()` function hardcodes `{"stack": "generic"}` when calling `_generate_summary_md()` (line 283). The actual detected stack is available in `FeatureSpecCommand.execute()` but not passed through to `write_outputs()`.

This means the `_summary.md` file always shows `generic` for the stack field, regardless of the detected stack.

## Fix

Add a `stack` parameter to `write_outputs()` and pass it through to `_generate_summary_md()`.

```python
def write_outputs(
    feature_content: str,
    assumptions: list[dict],
    source: str,
    output_dir: Path,
    stack: dict | None = None,  # NEW
) -> dict[str, Path]:
    ...
    stack_info = stack or {"stack": "generic", "bdd_runner": None}
    summary_content = _generate_summary_md(feature_name, feature_content, assumptions, stack_info)
```

Update `FeatureSpecCommand.execute()` to pass the detected stack:

```python
paths = write_outputs(
    feature_content=input_text,
    assumptions=assumptions,
    source=source,
    output_dir=output_dir,
    stack=stack,  # NEW
)
```

## Acceptance Criteria

- [x] `write_outputs()` accepts optional `stack` parameter
- [x] `FeatureSpecCommand.execute()` passes detected stack to `write_outputs()`
- [x] `_summary.md` shows correct detected stack (not always "generic")
- [x] Existing tests updated to verify stack passthrough
- [x] Backwards compatibility maintained (stack defaults to generic if not provided)

## Files to Change

- `guardkit/commands/feature_spec.py`
- `tests/unit/commands/test_feature_spec.py`
