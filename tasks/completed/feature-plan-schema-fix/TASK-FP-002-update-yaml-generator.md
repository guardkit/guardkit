---
id: TASK-FP-002
title: Update generate-feature-yaml script output format
status: completed
created: 2026-01-06T09:15:00Z
updated: 2026-01-07T10:30:00Z
completed: 2026-01-07T10:30:00Z
priority: high
complexity: 5
tags: [cli, schema, python, feature-plan]
parent_review: TASK-REV-66B4
wave: 1
dependencies: []
implementation_mode: task-work
testing_mode: tdd
workspace: fp-schema-wave1-generator
---

# Task: Update generate-feature-yaml script output format

## Description

Update the `generate-feature-yaml` script to output the schema format that `FeatureLoader` expects. This is the primary fix for the schema mismatch issue.

## Current Output

The script generates:
```yaml
tasks:
  - id: TASK-XXX
    name: "Task Name"
    wave: 1
    dependencies: []
    implementation_mode: task-work
    testing_mode: tdd

task_files:
  - path: "tasks/backlog/.../TASK-XXX.md"

execution_groups:
  - wave: 1
    name: "Foundation"
    strategy: sequential
    tasks: [TASK-XXX]
```

## Expected Output

```yaml
tasks:
  - id: TASK-XXX
    name: "Task Name"
    file_path: "tasks/backlog/.../TASK-XXX.md"
    status: pending
    complexity: 5
    dependencies: []
    implementation_mode: task-work
    estimated_minutes: 30

orchestration:
  parallel_groups:
    - - TASK-XXX
    - - TASK-YYY
      - TASK-ZZZ
  estimated_duration_minutes: 180
  recommended_parallel: 3
```

## Acceptance Criteria

- [x] `file_path` embedded in each task entry (derived from task ID and base path)
- [x] `status: pending` added to each task
- [x] `complexity` field included (from --task argument)
- [x] `estimated_minutes` calculated from complexity
- [x] `task_files` section removed (redundant)
- [x] `execution_groups` replaced with `orchestration.parallel_groups`
- [x] `parallel_groups` is list of lists format
- [x] Backward compatibility: script still accepts same CLI arguments
- [x] Unit tests pass for new output format

## Files Modified

- `installer/core/commands/lib/generate_feature_yaml.py` - Updated TaskSpec, added file_path support
- `tests/unit/test_generate_feature_yaml.py` - New test file with 29 tests

## Implementation Summary

### Changes Made

1. **Added `file_path` field to TaskSpec dataclass** (line 39)
   - New field with empty string default for backward compatibility
   - Included in `to_dict()` output for FeatureLoader compatibility

2. **Added `build_task_file_path()` helper function** (lines 119-147)
   - Centralized path construction for DRY compliance
   - Handles both feature slug and flat structure cases

3. **Updated `parse_task_string()` signature** (lines 149-197)
   - Added `feature_slug` and `task_base_path` optional parameters
   - Uses `build_task_file_path()` for path derivation

4. **Added CLI arguments** (lines 326-337)
   - `--feature-slug`: Feature directory name for file path derivation
   - `--task-base-path`: Base path for task files (default: tasks/backlog)

5. **Updated JSON parsing** (lines 361-380)
   - Also derives file_path when feature_slug is provided

### Test Coverage

- 29 unit tests passing
- 8 test classes covering all functionality:
  - TaskSpec dataclass tests
  - File path construction tests
  - Parse task string tests
  - Parallel groups (wave detection) tests
  - Feature file output tests
  - Duration estimation tests
  - Schema compatibility integration tests
  - Backward compatibility tests

## Technical Notes

- Task argument format remains: `ID:NAME:COMPLEXITY:DEPS`
- Derive `file_path` from feature slug + task ID
- Group tasks into waves based on dependency analysis
- `estimated_minutes` = `complexity * 15` (rough heuristic via exponential scaling)

## Test Cases

1. Single task with no dependencies → single wave ✅
2. Multiple independent tasks → parallel in same wave ✅
3. Task with dependency → separate waves ✅
4. Circular dependency detection → error ✅

## Code Review Summary

- **Code Quality Score**: 92/100
- **Status**: APPROVED
- **Blockers**: None
- **Recommendations**: 3 optional enhancements (low priority)
