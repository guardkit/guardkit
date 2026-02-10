---
id: TASK-FIX-FP04
title: Require --feature-slug in generate_feature_yaml.py
status: completed
created: 2026-02-10T12:00:00Z
updated: 2026-02-10T12:00:00Z
completed: 2026-02-10T13:00:00Z
priority: medium
tags: [bug-fix, input-validation, defensive]
task_type: feature
parent_review: TASK-REV-1BE3
feature_id: FEAT-FP-FIX
wave: 1
implementation_mode: task-work
complexity: 2
dependencies: []
completed_location: tasks/completed/TASK-FIX-FP04/
---

# Task: Require --feature-slug in generate_feature_yaml.py

## Description

`generate_feature_yaml.py` allows `--feature-slug` to be empty, which produces `file_path: ""` for all tasks. Since `FeatureLoader` requires `file_path` to be a valid path, empty values are always wrong and should be rejected at generation time.

## Changes Required

**File**: `installer/core/commands/lib/generate_feature_yaml.py`

1. Make `--feature-slug` required (or validate it's non-empty when tasks are provided)
2. Add a clear error message when it's missing

```python
parser.add_argument(
    "--feature-slug",
    required=True,
    help="Feature slug for deriving task file paths (e.g., 'dark-mode', 'oauth2')"
)
```

Or if backwards compatibility is needed, validate after parsing:

```python
if not args.feature_slug:
    print("Error: --feature-slug is required for correct task file_path generation.", file=sys.stderr)
    print("Example: --feature-slug 'my-feature'", file=sys.stderr)
    sys.exit(1)
```

3. Update existing tests to include `--feature-slug` where needed.

## Acceptance Criteria

- [x] `generate_feature_yaml.py` rejects missing/empty `--feature-slug` with clear error
- [x] Error message suggests the correct usage
- [x] All generated YAML files have non-empty `file_path` values
- [x] Existing tests updated to pass `--feature-slug`
- [x] New test verifies error on missing `--feature-slug`

## Evidence

- `generate_feature_yaml.py:204-207`: `file_path` stays empty when `feature_slug` is empty
- `generate_feature_yaml.py:371-376`: `--feature-slug` is optional with default `""`

## Implementation Summary

**Files Modified**:
- `installer/core/commands/lib/generate_feature_yaml.py` (line 436-446): Added validation rejecting empty `--feature-slug` after tasks are parsed
- `tests/unit/test_generate_feature_yaml.py`: Added `TestFeatureSlugValidation` class with 4 new tests

**Test Results**: 52/52 passing (48 existing + 4 new), zero regressions
