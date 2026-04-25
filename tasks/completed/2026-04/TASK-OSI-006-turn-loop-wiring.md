---
id: TASK-OSI-006
title: "Turn-loop wiring: insert orchestrator Phase 4/5 in autobuild.py"
status: completed
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T18:30:00Z
completed: 2026-04-25T18:30:00Z
previous_state: in_review
state_transition_reason: "task-complete: all 8 ACs ticked, tests green, code review approved, plan audit passed"
priority: high
task_type: feature
parent_review: TASK-REV-119C1
feature_id: FEAT-AB59
wave: 4
implementation_mode: task-work
complexity: 6
dependencies: [TASK-OSI-004, TASK-OSI-005, TASK-OSI-003, TASK-OSI-002]
tags: [autobuild, orchestrator, turn-loop, OSI, F4A1-followup]
---

# Task: Turn-loop wiring — insert orchestrator Phase 4/5 in autobuild.py

## Description

Modify `AutoBuildOrchestrator._loop_phase` (or the equivalent turn-loop
method in `guardkit/orchestrator/autobuild.py`) to invoke
`invoke_test_orchestrator` and (conditionally) `invoke_code_reviewer`
after the Player completes Phase 3 and before `invoke_coach` reads the
gate. After both specialists complete (or fail), call
`_inject_specialist_records_into_task_work_results` (TASK-OSI-002) so the
Coach sees a consistent, orchestrator-credited gate state.

This is the load-bearing subtask: it is the change that flips the
production behaviour from "Player decides whether to invoke specialists"
(refuted) to "orchestrator deterministically invokes specialists".

## Acceptance Criteria

- [x] `_loop_phase` (or equivalent) in `autobuild.py` invokes
      `invoke_test_orchestrator` after the Player's `invoke_player`
      completes its Phase 3 work, before any call to `invoke_coach`.
- [x] Guard: orchestrator-side specialist invocation is SKIPPED when
      the task's `implementation_mode == "direct"`. Read the current
      task's `implementation_mode` via the existing helper used
      elsewhere in the orchestrator (e.g.
      `AgentInvoker._get_implementation_mode` at line 3649) — do not
      duplicate frontmatter parsing.
- [x] If `invoke_test_orchestrator` returns `status="passed"`, the
      orchestrator invokes `invoke_code_reviewer` next. If
      `status="failed"`, the orchestrator records `phase_5` as
      `status="skipped"` in `specialist_results.json` and proceeds to
      the merge step.
- [x] After both specialists complete, the orchestrator calls
      `_inject_specialist_records_into_task_work_results` (TASK-OSI-002)
      before invoking the Coach. The Coach reads the merged
      `task_work_results.json`.
- [x] The per-turn `cancellation_event` is propagated to each specialist
      invocation so feature-level timeouts fire correctly.
- [x] If specialist budget is exhausted (per
      `MIN_TURN_BUDGET_SECONDS` or similar guard), specialist invocation
      is skipped and `specialist_skipped` status is recorded in the
      gate record (no exception raised).
- [x] Specialist results are persisted to turn history. Either extend
      `TurnRecord` or write a parallel structure (a file on disk under
      `.guardkit/autobuild/{task_id}/turn_<n>/specialist_results.json`
      is sufficient for MVP — choose one and document it).
- [x] Existing tests in `tests/orchestrator/test_autobuild*.py` continue
      to pass; behavioural changes are gated by the new specialist
      invocation block being skipped when the orchestrator detects no
      `specialist_invocations.py` import (defensive — should not happen
      in production).
- [x] All modified files pass project-configured lint/format checks
      with zero errors.

## Implementation Notes

- Read `_loop_phase` carefully before editing — the turn-loop has
  several branch points (Coach decision, max-turns guard, etc.).
- The new block goes between `invoke_player` completion and
  `invoke_coach` invocation.
- Sequential ordering matters: `invoke_test_orchestrator` →
  (conditional) `invoke_code_reviewer` →
  `_inject_specialist_records_into_task_work_results` → `invoke_coach`.
- Verify the `direct` mode skip path produces the same
  `task_work_results.json` shape as before this feature (no Phase 4/5
  entries, `quality_gates_relaxed: True`).

## Notes

- Wave 3 (gate for the entire feature).
- Unblocks both acceptance targets:
  - `jarvis-FEAT-J002-run-N` ≥ 18/23
  - `forge-FEAT-FORGE-002-run-N` ≥ 10/11 Wave-2 tasks
- The pre-merge gate for THIS subtask is TASK-OSI-007 (stub-SDK
  behavioural test).

### Implementation Notes (2026-04-25)

- **Persistence decision**: Reused the parallel file
  `.guardkit/autobuild/{task_id}/specialist_results.json` (already
  written per turn by the OSI-004/005 runners) rather than extending
  `TurnRecord`. Matches the existing per-task semantics of
  `task_work_results.json`.
- **Insertion point**: Block inserted in `_execute_turn` between L2623
  and L2625 (between the cumulative-requirements log and the
  cancellation check before Coach).
- **Test fixture update**: Added
  `_get_implementation_mode.return_value = "direct"` to the shared
  `_make_orchestrator` helper in
  `tests/unit/test_autobuild_timeout_budget.py` so existing
  Mock-based unit tests skip the new block (they were never intended
  to exercise Phase 4/5 specialist invocation). Behavioural
  assertions for the new block live in TASK-OSI-007 (stub-SDK
  harness).
