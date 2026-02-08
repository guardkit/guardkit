---
id: TASK-FPP-004
title: Simplify --task argument to 4-field format in feature-plan spec
status: completed
created: 2026-02-07T20:00:00Z
updated: 2026-02-07T21:00:00Z
completed: 2026-02-07T21:00:00Z
priority: medium
tags: [fix-feature-plan-paths, documentation]
complexity: 2
task_type: documentation
implementation_mode: direct
parallel_group: 2
parent_review: TASK-REV-FP01
feature_id: FEAT-FPP
dependencies:
  - TASK-FPP-003
---

# Simplify --task argument to 4-field format in feature-plan spec

## Description

The command spec (`feature-plan.md` Step 10) documents a 5-field format `ID:NAME:FILE_PATH:COMPLEXITY:DEPS` but `parse_task_string()` only handles 4 fields (`ID:NAME:COMPLEXITY:DEPS`). The FILE_PATH field is silently ignored when passed. This creates confusion for Claude when following the spec.

Remove the FILE_PATH field from the spec and rely on `--feature-slug` for path derivation.

## Acceptance Criteria

- [x] Step 10 in `feature-plan.md` uses 4-field format: `ID:NAME:COMPLEXITY:DEPS`
- [x] All examples updated to remove FILE_PATH from --task arguments
- [x] Comment added noting that file paths are derived automatically from `--feature-slug`
- [x] No code changes needed (parser already handles 4 fields)

## Files to Modify

- `installer/core/commands/feature-plan.md` (lines 1592-1622)

## Implementation Details

Update the Step 10 documentation from:
```bash
--task "ID:NAME:FILE_PATH:COMPLEXITY:DEPS"
```
To:
```bash
--task "ID:NAME:COMPLEXITY:DEPS"
```

And update all examples accordingly. Add a note:
```
Note: Task file paths are derived automatically from --feature-slug.
Do not include FILE_PATH in the --task argument.
```

## Notes

Auto-generated from TASK-REV-FP01 recommendations (R3: Simplify Format).
