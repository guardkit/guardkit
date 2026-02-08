---
id: TASK-FPP-005
title: Add post-creation path validation to feature-plan
status: completed
created: 2026-02-07T20:00:00Z
updated: 2026-02-07T21:00:00Z
completed: 2026-02-07T21:00:00Z
priority: medium
tags: [fix-feature-plan-paths, validation]
complexity: 4
task_type: feature
implementation_mode: task-work
parallel_group: 2
parent_review: TASK-REV-FP01
feature_id: FEAT-FPP
dependencies:
  - TASK-FPP-002
  - TASK-FPP-003
---

# Add post-creation path validation to feature-plan

## Description

After generating the feature YAML, the `/feature-plan` command should validate that each `file_path` in the YAML resolves to an actual file on disk. Currently, this validation only happens when `feature-build` runs, which is too late - the user has already moved on.

## Acceptance Criteria

- [x] After YAML generation, all `file_path` values are verified against disk
- [x] If any path is invalid, a clear error is displayed with the expected vs actual path
- [x] Validation runs automatically (no flag needed)
- [x] Existing `validate_feature()` in feature_loader.py can optionally be reused
- [x] Unit test covers the validation logic

## Files to Modify

- `installer/core/commands/lib/generate_feature_yaml.py` - add validation after YAML write
- `installer/core/commands/feature-plan.md` - document validation step
- New test file or extend `tests/unit/test_generate_feature_yaml.py`

## Implementation Details

Add a validation function to `generate_feature_yaml.py`:

```python
def validate_task_paths(feature: FeatureFile, base_dir: Path) -> list[str]:
    """Validate that all task file_path values resolve to actual files."""
    errors = []
    for task in feature.tasks:
        if task.file_path:
            full_path = base_dir / task.file_path
            if not full_path.exists():
                errors.append(f"Task {task.id}: file not found at {task.file_path}")
    return errors
```

Call this after `write_yaml()` in `main()`.

Alternatively, update the `feature-plan.md` spec to instruct Claude to verify paths after Step 10.

## Notes

Auto-generated from TASK-REV-FP01 recommendations (R4: Add Validation).
