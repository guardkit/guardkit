---
id: TASK-FIX-7534
title: Add task_type validation guard to feature planner output
task_type: feature
parent_review: TASK-REV-7530
feature_id: FEAT-CF57
wave: 2
implementation_mode: task-work
complexity: 3
priority: low
dependencies:
  - TASK-FIX-7531
status: completed
completed: 2026-03-02T12:00:00Z
completed_location: tasks/completed/TASK-FIX-7534/
tags: [autobuild, feature-planner, validation, task-type]
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-02T12:00:00Z
  tests_passed: 160
  tests_failed: 0
---

# Task: Add task_type Validation Guard to Feature Planner

## Context

The feature planner (used by `/feature-plan`) generates task files with `task_type` values. FEAT-CF57's TASK-INST-012 was generated with `task_type: enhancement` — a valid alias but not a canonical enum value. This created a latent failure that only manifested during Coach validation due to the dual alias table bug (TASK-FIX-7531).

## Problem

The feature planner does not validate generated task_type values against the canonical `TaskType` enum. It should either:
- **Option A**: Reject non-canonical values and require the LLM to use enum values
- **Option B**: Auto-normalise aliases to their canonical form before writing task files

## Implementation

### Preferred Approach: Option B (Auto-normalise)

After the LLM generates task metadata, validate and normalise `task_type`:

```python
from guardkit.models.task_types import TaskType, TASK_TYPE_ALIASES

def normalise_task_type(raw_type: str) -> str:
    """Normalise task_type to canonical enum value."""
    # Already canonical?
    try:
        return TaskType(raw_type).value
    except ValueError:
        pass
    # Known alias?
    if raw_type in TASK_TYPE_ALIASES:
        return TASK_TYPE_ALIASES[raw_type].value
    # Unknown - default to feature with warning
    logger.warning(f"Unknown task_type '{raw_type}', defaulting to 'feature'")
    return TaskType.FEATURE.value
```

### Files to Modify

- Identify the feature planner module that generates task YAML frontmatter
- Add normalisation step before writing task files
- Add tests for normalisation behaviour

### Expected Interface

The feature planner should output task files with canonical `task_type` values only: `scaffolding`, `feature`, `infrastructure`, `integration`, `documentation`, `testing`, `refactor`.

## Acceptance Criteria

- [x] Feature planner normalises task_type values to canonical enum values
- [x] Aliases are resolved transparently (with info log)
- [x] Unknown values fall back to `feature` with warning
- [x] Generated task files only contain canonical task_type values
- [x] Tests cover normalisation of aliases and unknown values

## Completion Summary

### Changes Made

1. **`guardkit/models/task_types.py`** - Added `normalise_task_type()` function with three-tier resolution: canonical passthrough, alias resolution (with info log), unknown fallback to feature (with warning log)
2. **`guardkit/models/__init__.py`** - Exported `normalise_task_type` from models package
3. **`guardkit/planning/task_metadata.py`** - Integrated `normalise_task_type()` into `_build_frontmatter()` so all rendered task YAML uses canonical values
4. **`tests/unit/test_task_types.py`** - Added 18 tests in `TestNormaliseTaskType` class covering canonical passthrough, alias resolution, unknown fallback, and logging behaviour
5. **`tests/unit/test_task_metadata.py`** - Added 8 integration tests in `TestTaskTypeNormalisationInFrontmatter` verifying end-to-end normalisation in rendered markdown; fixed 1 existing test assertion updated from "implementation" to "feature"

### Test Results

- 160/160 tests passed
- 0 failures
- 26 new tests added (18 unit + 8 integration)
