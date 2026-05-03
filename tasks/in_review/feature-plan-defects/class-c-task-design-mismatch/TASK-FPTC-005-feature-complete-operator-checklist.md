---
id: TASK-FPTC-005
title: "/feature-complete surfaces operator follow-up checklist for deferred tasks"
status: in_review
created: 2026-05-03T12:00:00Z
updated: 2026-05-03T15:30:00Z
previous_state: in_progress
state_transition_reason: "All 5 ACs satisfied; 12/12 new unit tests pass; 191/191 orchestrator regression tests green"
priority: high
task_type: feature
implementation_mode: task-work
tags:
  - feature-complete
  - operator-handoff
  - merge-summary
  - class-c
  - feature-plan-defects
complexity: 4
estimated_minutes: 90
parent_review: TASK-REV-AUTM
feature_id: FEAT-AUTM
parent_feature: feature-plan-defects
wave: 3
conductor_workspace: feature-plan-defects-wave3-1
dependencies:
  - TASK-FPTC-003
---

# Task: feature-complete operator follow-up checklist

## Description

When a feature with deferred operator-handoff tasks is merged via
`/feature-complete`, the operator must see a clear, actionable
checklist of what they still need to do manually. This task wires
the deferred-task records produced by TASK-FPTC-003 through to the
merge summary surface.

A parallel surface (`/feature-plan` plan summary) shows the deferred
count up-front so the user knows how much manual work the feature
implies before approving the plan.

## Acceptance Criteria

- [x] **AC-FPTC-005-01** —
      `installer/core/commands/feature-complete.md` contains a new
      section titled "Required operator follow-up" describing how
      deferred tasks are surfaced in the merge summary.
- [x] **AC-FPTC-005-02** — The merge-summary code path (likely
      `guardkit/orchestrator/feature_complete.py` —
      discover the existing site during implementation) emits a
      "Required operator follow-up" subsection in its output when
      one or more tasks were deferred. Each entry includes:
      - task ID
      - task title
      - the runtime-shaped ACs from the task body, verbatim
- [x] **AC-FPTC-005-03** —
      `installer/core/commands/feature-plan.md` plan-summary section
      (the post-Step-8 summary the agent shows the user) shows a
      `Operator follow-up tasks: N` line when the plan contains any
      tasks with `task_type: operator_handoff`.
- [x] **AC-FPTC-005-04** — Unit test asserts that a fixture feature
      with 2 deferred tasks produces a merge summary containing both
      task IDs and both titles in the "Required operator follow-up"
      subsection.
- [x] **AC-FPTC-005-05** — Unit test asserts that a fixture feature
      with 0 deferred tasks does NOT include the operator-follow-up
      subsection at all (no empty headers).

## Implementation Notes

- Read `feature_complete.py` (or whatever module owns the merge
  summary output) before assuming the surface shape. The deferred
  records should already be readable per TASK-FPTC-003's contract.
- For AC-FPTC-005-03 this is a prompt-template edit, not Python.
  Match the style of existing summary lines in feature-plan.md.

## Cross-component contract

**Consumes** TASK-FPTC-003:
- The deferred-outcome record shape (`task_id`, `outcome=deferred`,
  `reason`). Read the actual shape from TASK-FPTC-003's
  implementation, not from this task's suggestion.

## Files

- `installer/core/commands/feature-complete.md` (edit)
- `installer/core/commands/feature-plan.md` (edit — plan-summary
  section only)
- `guardkit/orchestrator/feature_complete.py` (edit — discover exact
  module during implementation)
- `tests/unit/orchestrator/test_feature_complete_operator_summary.py`
  (new)

## Out of Scope

- The detector itself (TASK-FPTC-001).
- Per-task UX during autobuild execution (TASK-FPTC-003 handles the
  in-run reporting).
