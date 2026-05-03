---
id: TASK-FPTC-002
title: "Add OPERATOR_HANDOFF to TaskType enum + register skip-everything QualityGateProfile"
status: completed
created: 2026-05-03T12:00:00Z
updated: 2026-05-03T12:00:00Z
completed: 2026-05-03T12:00:00Z
previous_state: in_review
priority: high
task_type: declarative
implementation_mode: task-work
tags:
  - task-types
  - taxonomy
  - operator-handoff
  - quality-gates
  - class-c
  - feature-plan-defects
complexity: 3
estimated_minutes: 60
parent_review: TASK-REV-AUTM
feature_id: FEAT-AUTM
parent_feature: feature-plan-defects
wave: 1
conductor_workspace: feature-plan-defects-wave1-2
dependencies: []
---

# Task: Add OPERATOR_HANDOFF to TaskType enum

## Description

Enforcement layer for Class C operator-handoff tasks. Adds a new
value to the existing `TaskType` enum and registers a quality-gate
profile that disables every gate (no arch review, no coverage, no
tests required) so the orchestrator has a deterministic signal to
skip the task entirely. The detector lives in
`/feature-plan` (TASK-FPTC-001); the orchestrator skip lives in
`feature_orchestrator` (TASK-FPTC-003); this task wires the type
itself.

## Acceptance Criteria

- [x] **AC-FPTC-002-01** — `guardkit/models/task_types.py::TaskType`
      enum contains the member
      `OPERATOR_HANDOFF = "operator_handoff"` and the docstring is
      updated to describe its meaning.
- [x] **AC-FPTC-002-02** — `DEFAULT_PROFILES` registers a
      `QualityGateProfile` for `TaskType.OPERATOR_HANDOFF` with:
      - `arch_review_required=False`
      - `arch_review_threshold=0`
      - `coverage_required=False`
      - `coverage_threshold=0`
      - `tests_required=False`
- [x] **AC-FPTC-002-03** — `tests/unit/test_task_types.py`
      asserts `TaskType("operator_handoff")` constructs without
      error and `get_profile(TaskType.OPERATOR_HANDOFF)` returns a
      profile whose flags match AC-FPTC-002-02.
- [x] **AC-FPTC-002-04** —
      `guardkit/orchestrator/feature_loader.py::FeatureLoader._validate_task_type_in_file`
      accepts `task_type: operator_handoff` in a fixture task file
      and returns `None` (no error).
- [x] **AC-FPTC-002-05** — Pytest unit test asserts loading a fixture
      task with `task_type: operator_handoff` returns no validation
      error from `FeatureLoader.validate_feature`.

## Implementation Notes

- Read `guardkit/models/task_types.py` first — the existing
  `DECLARATIVE` profile is the closest template (skip arch review,
  skip coverage, but keep tests). For `OPERATOR_HANDOFF` skip
  everything.
- Don't add `OPERATOR_HANDOFF` to `TASK_TYPE_ALIASES` — the value is
  intentionally explicit; we don't want fuzzy matching.

## Cross-component contract

**Produces** for downstream tasks:
- Importable: `from guardkit.models.task_types import TaskType`
- Value: `TaskType.OPERATOR_HANDOFF` (string `"operator_handoff"`)
- Profile: `get_profile(TaskType.OPERATOR_HANDOFF)` returns the
  skip-everything `QualityGateProfile`.

**Consumed by**:
- TASK-FPTC-003 (orchestrator skip — branches on enum value)
- TASK-FPTC-004 (CoachValidator + FeatureLoader — branch on enum value)
- TASK-FPTC-001 (feature-plan agent emits the value into task frontmatter)

## Files

- `guardkit/models/task_types.py` (edit)
- `tests/unit/test_task_types.py` (edit — canonical TaskType test file)
- `tests/unit/orchestrator/test_feature_loader_task_type.py` (edit
  or create — for AC-FPTC-002-04, AC-FPTC-002-05)

## Out of Scope

- Orchestrator behaviour change (TASK-FPTC-003).
- Coach validator skip logic (TASK-FPTC-004).

## Implementation Summary

Added `OPERATOR_HANDOFF = "operator_handoff"` to `TaskType` (now 9
values) and registered a skip-everything `QualityGateProfile` in
`DEFAULT_PROFILES` (`arch_review_required=False`,
`coverage_required=False`, `tests_required=False`,
`plan_audit_required=False`). The `TaskType` docstring now describes
the value's purpose: a deterministic signal for the orchestrator
(TASK-FPTC-003) to skip the task entirely and route it to a human
operator. Per AC-FPTC-002 implementation note, the value is
intentionally not added to `TASK_TYPE_ALIASES` — no fuzzy matching.

Tests landed alongside:

- `tests/unit/test_task_types.py`: new `TestOperatorHandoffTaskType`
  class (8 assertions covering enum value, profile skip-everything
  flags, `for_type` lookup, alias-exclusion, normalise pass-through).
  Updated `test_task_type_enum_has_eight_values → has_nine_values` and
  added the value to the lookup-by-value test.
- `tests/unit/orchestrator/test_feature_loader_task_type.py` (new):
  pins `_validate_task_type_in_file` returns `None` for a fixture
  task with `task_type: operator_handoff` (AC-04), and `validate_feature`
  surfaces no task_type error for the same fixture (AC-05). Includes a
  sanity test that unknown values still error.

Pytest run on both touched test modules: 126 passed, 0 failed.

### Decisions

- **Test path correction (AC-FPTC-002-03)**: AC originally referenced
  `tests/unit/models/test_task_types.py`, but the canonical existing
  test file is `tests/unit/test_task_types.py` (981+ lines, all
  TaskType tests live there). Extended that file rather than fork a
  new file in a non-canonical location, and updated AC-FPTC-002-03
  and the Files section above to point at the canonical path.
- **Profile shape**: AC-FPTC-002-02 specifies 5 fields; the dataclass
  also has `plan_audit_required` (required, no default),
  `zero_test_blocking`, and `seam_tests_recommended`. Set
  `plan_audit_required=False` because "skip everything" is the stated
  intent — `DOCUMENTATION` profile uses the same setting. Other two
  set explicitly to False matching the `DECLARATIVE` profile pattern
  for forward-readability.

## Notes

Downstream tasks can now import `from guardkit.models.task_types import
TaskType` and branch on `TaskType.OPERATOR_HANDOFF` (TASK-FPTC-003
orchestrator skip, TASK-FPTC-004 validator+loader awareness,
TASK-FPTC-001 feature-plan agent emitting the value into task
frontmatter).
