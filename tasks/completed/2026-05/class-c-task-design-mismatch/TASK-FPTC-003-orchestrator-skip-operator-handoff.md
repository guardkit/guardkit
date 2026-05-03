---
id: TASK-FPTC-003
title: "Feature orchestrator skips operator_handoff tasks; reports as DEFERRED"
status: completed
created: 2026-05-03T12:00:00Z
updated: 2026-05-03T13:30:00Z
completed: 2026-05-03T13:30:00Z
previous_state: in_review
state_transition_reason: "All 5 ACs satisfied; 12/12 new tests pass; 323 regression tests green"
completed_location: tasks/completed/2026-05/class-c-task-design-mismatch/
priority: high
task_type: feature
implementation_mode: task-work
tags:
  - feature-orchestrator
  - operator-handoff
  - skip-logic
  - deferred-state
  - class-c
  - feature-plan-defects
complexity: 5
estimated_minutes: 120
parent_review: TASK-REV-AUTM
feature_id: FEAT-AUTM
parent_feature: feature-plan-defects
wave: 2
conductor_workspace: feature-plan-defects-wave2-1
dependencies:
  - TASK-FPTC-002
---

# Task: Orchestrator skips operator_handoff tasks

## Description

When the feature orchestrator encounters a task with
`task_type: operator_handoff`, it must NOT enter the Player↔Coach
loop. Instead it marks the task as deferred, records the reason
"operator follow-up — runtime verification required", and continues
the wave. The deferred state is terminal-but-not-failed — the
overall feature run does not report failure on operator-handoff
deferrals.

## Acceptance Criteria

- [x] **AC-FPTC-003-01** —
      `guardkit/orchestrator/feature_orchestrator.py` contains an
      explicit branch (recognisable by `task_type == TaskType.OPERATOR_HANDOFF`
      or equivalent string comparison) that short-circuits dispatch:
      no Player invocation, no Coach invocation, no SDK budget burn.
- [x] **AC-FPTC-003-02** — A task-status enumeration (or
      `TurnState`/`TaskOutcome` equivalent — discover the existing
      shape during implementation) gains a `DEFERRED` value or an
      equivalent mechanism. The deferred outcome is terminal and
      distinct from `BLOCKED`/`FAILED`/`COMPLETED`.
- [x] **AC-FPTC-003-03** — Wave-summary output (whichever surface
      `feature_orchestrator` already uses — stdout banner, JSON
      report, or progress log) includes a deferred-task entry with:
      - task ID
      - task title
      - reason string `"operator follow-up — runtime verification required"`
- [x] **AC-FPTC-003-04** — Unit test in
      `tests/unit/orchestrator/test_feature_orchestrator_skip.py`
      asserts that a fixture task with `task_type=operator_handoff`
      is reported as deferred WITHOUT invoking the Player or Coach
      mock.
- [x] **AC-FPTC-003-05** — Integration test using a fixture feature
      with one `feature` task and one `operator_handoff` task: the
      `feature` task runs through the Player↔Coach mock loop, the
      `operator_handoff` task is reported as deferred, and the run
      returns success (not failure).

## Implementation Notes

- Read `feature_orchestrator.py` to find the dispatch site (likely
  near where Player is invoked). The skip branch should be the
  earliest possible check — before any worktree setup, before any
  SDK call.
- The deferred state needs to round-trip into whatever progress
  log / state file the orchestrator writes, so `/feature-complete`
  (TASK-FPTC-005) can find it.

## Cross-component contract

**Consumes** TASK-FPTC-002:
- `from guardkit.models.task_types import TaskType`
- Branch on `task.task_type == TaskType.OPERATOR_HANDOFF`

**Produces** for downstream tasks:
- The deferred outcome must be readable by TASK-FPTC-005's
  feature-complete summary — keep the field name and shape stable
  in whatever progress log / outcome record this task writes.
  Suggested shape:
  ```python
  {
      "task_id": "TASK-XXX",
      "outcome": "deferred",
      "reason": "operator follow-up — runtime verification required",
  }
  ```

## Files

- `guardkit/orchestrator/feature_orchestrator.py` (edit)
- Possibly `guardkit/orchestrator/protocol.py` or `schemas.py` if a
  new outcome value needs to be declared in a shared schema.
- `tests/unit/orchestrator/test_feature_orchestrator_skip.py` (new)
- `tests/integration/orchestrator/test_feature_orchestrator_deferred.py`
  (new — for AC-FPTC-003-05)

## Out of Scope

- Coach validator awareness (TASK-FPTC-004).
- Feature-complete merge summary surface (TASK-FPTC-005).
- Backwards compatibility with existing in-flight features (none
  currently — see parent-review AC-AUTM-04).

## Implementation Summary

Implemented the orchestrator skip branch + DEFERRED outcome shape across
three files. The skip fires at the earliest possible point — before any
worktree setup, before timeout resolution, before AutoBuildOrchestrator
construction, before any SDK budget burns.

### Approach

- **`guardkit/orchestrator/feature_loader.py`**: Added `"deferred"` as a
  value of the `FeatureTask.status` Literal, so the deferred state
  round-trips through saved feature YAML and is distinct from
  `pending/in_progress/completed/failed/skipped`.
- **`guardkit/orchestrator/feature_orchestrator.py`**:
  - Imported `TaskType, normalise_task_type` from
    `guardkit.models.task_types`.
  - Added `deferred_reason: Optional[str]` to the `TaskExecutionResult`
    dataclass so the canonical reason string round-trips into wave
    summaries and the persisted task result.
  - Inserted an explicit short-circuit in `_execute_wave_parallel`,
    immediately after the dependency-satisfied check, via a new
    `_maybe_defer_operator_handoff` helper. The helper consults
    `_read_task_type_from_frontmatter` (also new) to load the
    on-disk `task_type` value, normalises aliases, and returns a
    deferred `TaskExecutionResult` when the task is operator_handoff.
    The helper falls through to normal dispatch on loader errors so a
    missing/corrupt task file never breaks the orchestrator.
  - Extended `_update_feature` so a result with
    `final_decision == "deferred"` persists `task.status = "deferred"`
    rather than `completed`/`failed`, and stores the
    `deferred_reason` alongside `final_decision` in `task.result`.

### Wave-summary surface

The deferred entry is surfaced on the existing wave-summary surfaces:

- **Stdout fallback** (`console.print` path): yellow banner of the
  shape `⏸ Deferred {task_id}: {title} — {reason}`, satisfying
  AC-FPTC-003-03.
- **Wave display** (`WaveProgressDisplay.update_task_status`): receives
  a `"skipped"` status with the details `"DEFERRED — {reason}"` so the
  task panel reflects the outcome without needing a new icon.
- **Persisted feature YAML**: the task's `result` dict carries
  `final_decision: "deferred"` and `deferred_reason`, so
  `/feature-complete` (TASK-FPTC-005) can render the deferred entry
  without re-loading task files.

### Result

- 12 new tests added under `tests/unit/orchestrator/test_feature_orchestrator_skip.py` (11)
  and `tests/integration/orchestrator/test_feature_orchestrator_deferred.py` (1).
- All 12 pass.
- Orchestrator regression sweep (323 unit tests across
  `tests/unit/orchestrator/`, `tests/unit/test_feature_orchestrator*.py`)
  green; 1 skipped, 0 failed.
- All 5 ACs (AC-FPTC-003-01 through -05) verified both structurally
  and behaviourally.

### Lessons

- The orchestrator already exposed three skip-shapes in
  `_execute_wave_parallel` (already-completed, dependency-failed); the
  operator_handoff skip slots in cleanly as a fourth case at the same
  call site, before timeout/worktree work begins. Adding the branch
  there — rather than inside `_execute_task` — was the cheapest way
  to satisfy "no SDK budget burn".
- `TaskExecutionResult.success=True` for the deferred case keeps the
  feature run reporting success per AC-FPTC-003-05, while
  `final_decision="deferred"` and the new `deferred_reason` field
  preserve the distinction from genuinely-completed tasks at the
  per-task level. The orchestrator's aggregate `tasks_completed`
  counter conflates the two — that's intentional and matches the
  AC's "terminal-but-not-failed" framing; the per-task data carries
  the distinction.
- Reusing `normalise_task_type` (TASK-FPTC-002) means the skip
  branch automatically picks up future aliases without further
  changes here.

### Cross-component contract delivered

**Produced** for TASK-FPTC-005 (feature-complete summary surface):

- `task.status == "deferred"` on the persisted FeatureTask.
- `task.result == {"total_turns": 0, "final_decision": "deferred",
  "error": None, "deferred_reason": "operator follow-up — runtime
  verification required"}`.
- The wave-level `TaskExecutionResult` carries the same shape with
  `success=True`, `total_turns=0`, `error=None`,
  `deferred_reason=...`.

### Related ADRs / Tasks

- TASK-REV-AUTM (parent review) — Shape D decision.
- TASK-FPTC-002 (consumed) — `OPERATOR_HANDOFF` enum + skip-everything
  `QualityGateProfile`.
- TASK-FPTC-005 (next, consumes this) — feature-complete operator
  checklist surface.
