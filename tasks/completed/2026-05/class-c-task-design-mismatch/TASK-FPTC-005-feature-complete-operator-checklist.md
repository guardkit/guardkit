---
id: TASK-FPTC-005
title: "/feature-complete surfaces operator follow-up checklist for deferred tasks"
status: completed
created: 2026-05-03T12:00:00Z
updated: 2026-05-03T15:45:00Z
completed: 2026-05-03T15:45:00Z
previous_state: in_review
state_transition_reason: "All 5 ACs satisfied; 12/12 new unit tests pass; 191/191 orchestrator regression tests green"
completed_location: tasks/completed/2026-05/class-c-task-design-mismatch/
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

## Implementation Summary

Wired the operator follow-up checklist into `/feature-complete`'s
existing Phase 4 handoff surface and added a corresponding plan-summary
indicator to `/feature-plan`. Three pure helpers in
`guardkit/orchestrator/feature_complete.py` consume the deferred-record
shape that TASK-FPTC-003 produces (`task.status == "deferred"` plus
`task.result["deferred_reason"]`) and read the runtime ACs verbatim
from the task body's `## Required operator follow-up` block (the
template `/feature-plan` writes when the operator answers `Y` to the
operator_handoff prompt).

### Approach

- **`guardkit/orchestrator/feature_complete.py`**:
  - `_extract_operator_followup_acs(task_file)`: scans a task md file
    for the `## Required operator follow-up` heading and collects the
    bullet lines verbatim until the next top-level heading. Returns
    `[]` on missing files / missing sections so a stale
    `FeatureTask.file_path` never crashes the merge summary.
  - `_collect_deferred_tasks(feature, repo_root)`: filters
    `feature.tasks` to `status == "deferred"`, anchors any relative
    `file_path` against `repo_root`, and returns
    `(task, ac_bullets)` pairs.
  - `render_operator_followup_panel(deferred)`: emits a yellow Rich
    Panel titled "📋 Required operator follow-up" listing each
    deferred task's ID, title, and AC bullets. Returns `None` when
    `deferred` is empty so callers can suppress the section entirely
    (AC-FPTC-005-05 — no empty headers).
  - `FeatureCompleteOrchestrator._handoff_phase` calls a new
    `_display_operator_followup` helper after the merge instructions
    panel; the operator follow-up panel renders regardless of whether
    a worktree is still present (the operator's manual ACs are
    independent of the merge mechanics).
  - Exported `render_operator_followup_panel` via `__all__` so the
    rendering can be imported and tested directly.
- **`installer/core/commands/feature-complete.md`**: added a new
  top-level section "Required operator follow-up" describing the
  surface, reproducing the rendered panel, and pointing back to the
  helper functions in `feature_complete.py`.
- **`installer/core/commands/feature-plan.md`**: extended the post-
  Step-10 summary block with an `Operator follow-up tasks: N` line and
  added the conditional-emission instruction (only emit when N ≥ 1; no
  `Operator follow-up tasks: 0` line in plans that don't need a
  handoff).

### Cross-component contract consumed

**Consumed from TASK-FPTC-003** (verified against the implementation
summary on the completed task file):

- `FeatureTask.status == "deferred"` is the marker for deferred tasks.
- `FeatureTask.result` carries
  `{"total_turns": 0, "final_decision": "deferred", "error": None,
  "deferred_reason": "operator follow-up — runtime verification required"}`.
- `FeatureTask.file_path` resolves to the on-disk markdown body that
  carries the `## Required operator follow-up` AC block (authored by
  `/feature-plan` per TASK-FPTC-001's template).

This task only consumes the `status` field and `file_path` (to read the
AC block); it does not consume `deferred_reason` directly because the
canonical reason is stable and comes from the task body bullets — which
the planner emits verbatim from the operator-handoff detector prompt.

### Result

- 12 new tests under
  `tests/unit/orchestrator/test_feature_complete_operator_summary.py`
  covering the three helpers (4 + 3 + 4 cases) plus an end-to-end
  `_handoff_phase` integration that exercises the full wiring (rendered
  panel captured via `capsys`).
- All 12 pass.
- Orchestrator regression sweep (191 tests across `tests/unit/orchestrator/`
  and `tests/orchestrator/test_feature_complete.py`) green; 0 failed.
- Broader unit-suite failures (41 in
  `tests/orchestrator/test_design_context_integration.py`) confirmed
  pre-existing on clean main — unrelated to this task's diff.
- All 5 ACs (AC-FPTC-005-01 through -05) verified both structurally
  (file/section presence) and behaviourally (panel content + omission).

### Lessons

- The `feature_complete.py` orchestrator is currently a skeleton
  (Phase 2 / Phase 3 are placeholders for TASK-FC-002 / TASK-FC-003) —
  the only real surface today is `_handoff_phase`. Wiring into
  `_handoff_phase` rather than the markdown command spec's detailed
  step plan was the right choice: the markdown spec's "Phase 0/1/2/3/5"
  steps are aspirational and the live Python path is the one users
  will see today.
- The deferred-record shape that TASK-FPTC-003 settled on
  (`task.status == "deferred"` + body-side AC block) means TASK-FPTC-005
  doesn't need to read `task.result.deferred_reason` at all — the
  canonical reason text comes from the task body, not the orchestrator
  state. That keeps the consumer / producer surface narrow and survives
  future shape changes to `TaskExecutionResult`.
- Rich's `Panel` is easy to test in isolation by capturing output via a
  `Console(file=io.StringIO(), force_terminal=False)`. The integration
  test additionally uses `capsys` to assert the rendered panel actually
  reaches stdout when `_handoff_phase` runs end-to-end.

### Files Changed

- `guardkit/orchestrator/feature_complete.py` — three new helpers +
  `_display_operator_followup` wired into `_handoff_phase`.
- `installer/core/commands/feature-complete.md` — new "Required
  operator follow-up" section.
- `installer/core/commands/feature-plan.md` — `Operator follow-up
  tasks: N` line + conditional-emission instruction.
- `tests/unit/orchestrator/test_feature_complete_operator_summary.py`
  (new) — 12 tests covering all three helpers plus orchestrator
  integration.

### Related

- TASK-FPTC-001 — emits the `## Required operator follow-up` template
  in task bodies (the producer of the AC block this task reads).
- TASK-FPTC-002 — `OPERATOR_HANDOFF` enum + skip-everything profile.
- TASK-FPTC-003 — orchestrator skip + `task.status == "deferred"` (the
  producer of the deferred records this task surfaces).
- TASK-FPTC-004 — Coach validator awareness for operator_handoff.
