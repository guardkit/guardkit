---
id: TASK-IMP-D4A0
title: "Add DECLARATIVE task type with quality gate profile"
status: completed
created: 2026-03-08T14:30:00Z
updated: 2026-03-08T15:00:00Z
completed: 2026-03-08T16:00:00Z
completed_location: tasks/completed/TASK-IMP-D4A0/
priority: high
tags: [quality-gates, task-types, coach-validator, profile-expansion]
complexity: 3
task_type: feature
parent_review: TASK-REV-A00F
related: [TASK-REV-FB22, TASK-REV-CSC1, TASK-FBSDK-025, TASK-FIX-ARIMPL, TASK-TT-001, TASK-FIX-93C1]
---

# Task: Add DECLARATIVE Task Type with Quality Gate Profile

## Background

Review TASK-REV-A00F identified a remaining 10-20% quality gate gap where trivial declarative code (Pydantic models, DTOs, Settings classes, constants, app init) tagged as `task_type: feature` fails arch review (score 0 < 60) and coverage gates (80% for untestable code). This task adds a single `TaskType.DECLARATIVE` to close that gap.

## Acceptance Criteria

### Code Changes
- [x] Add `TaskType.DECLARATIVE = "declarative"` to `TaskType` enum in `guardkit/models/task_types.py`
- [x] Add `QualityGateProfile` for DECLARATIVE to `DEFAULT_PROFILES` with these exact values:
  - `arch_review_required=False, arch_review_threshold=0`
  - `coverage_required=False, coverage_threshold=0.0`
  - `tests_required=True` (catch import errors)
  - `plan_audit_required=True` (verify completeness)
  - `zero_test_blocking=False`
  - `seam_tests_recommended=False`
- [x] Optionally add aliases to `TASK_TYPE_ALIASES`: `"config" → DECLARATIVE`, `"dto" → DECLARATIVE`

### Test Changes
- [x] Update `TestTaskTypeEnum.test_task_type_enum_has_seven_values` assertion from 7 to 8
- [x] Add `test_task_type_declarative_value` confirming `TaskType.DECLARATIVE.value == "declarative"`
- [x] Add `test_default_profiles_declarative_configuration` confirming all profile field values
- [x] Add `test_get_profile_with_declarative` confirming correct profile returned
- [x] Add `test_for_type_returns_declarative_profile` confirming class method works
- [x] Add `test_normalise_task_type_declarative` confirming canonical value passthrough
- [x] Add `test_declarative_profile_differs_from_feature` (less strict)
- [x] Add `test_declarative_profile_differs_from_scaffolding` (tests still required)
- [x] Add `test_workflow_declarative_task` integration test

### Command Spec Changes
- [x] `installer/core/commands/feature-plan.md`: Add `declarative` to Task Type Assignment Rules table, Pattern Matching section, and Example Detection
- [x] `installer/core/commands/task-review.md`: Add `declarative` to valid task_type values in [I]mplement flow documentation
- [x] `installer/core/commands/task-create.md`: Add `declarative` as valid task_type parameter value

### Pattern Matching Rules (for feature-plan and task-review)
- [x] Title contains "Pydantic", "model", "DTO", "schema" → `declarative`
- [x] Title contains "Settings class", "constants", "enums" → `declarative`
- [x] Title contains "app init", "data model", "type definitions" → `declarative`

### Refinement: Single Source of Truth (user feedback)
- [x] Add DECLARATIVE keywords to `guardkit/lib/task_type_detector.py` KEYWORD_MAPPINGS
- [x] Add DECLARATIVE to detection priority order in `task_type_detector.py`
- [x] Add DECLARATIVE to `get_task_type_summary()` in `task_type_detector.py`
- [x] Replace partial alias copy in `guardkit/orchestrator/autobuild.py` with canonical `TASK_TYPE_ALIASES` import
- [x] Add DECLARATIVE detection tests to `tests/unit/test_task_type_detector.py`
- [x] Add DECLARATIVE priority tests to `tests/unit/test_task_type_detector.py`
- [x] Add DECLARATIVE keyword mapping tests to `tests/unit/test_task_type_detector.py`

## Files Modified

| File | Change Type |
|------|------------|
| `guardkit/models/task_types.py` | Add enum value, profile, aliases |
| `guardkit/lib/task_type_detector.py` | Add keywords, detection, summary |
| `guardkit/orchestrator/autobuild.py` | Use canonical TASK_TYPE_ALIASES |
| `tests/unit/test_task_types.py` | Add 9 new tests, update 1 existing |
| `tests/unit/test_task_type_detector.py` | Add 15 new tests across 4 classes |
| `installer/core/commands/feature-plan.md` | Add declarative patterns |
| `installer/core/commands/task-review.md` | Add declarative to [I]mplement flow |
| `installer/core/commands/task-create.md` | Add declarative to valid values |

## Test Execution Log

- 215/215 tests pass (113 task_types + 102 detector)
- All acceptance criteria verified programmatically
