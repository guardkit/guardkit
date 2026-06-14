---
id: TASK-FIX-TBXMSG01
title: TIMEOUT_BUDGET_EXHAUSTED summary box renders misleading "Unknown error occurred"
status: completed
task_type: fix
created: 2026-06-14T11:10:00Z
updated: 2026-06-14T13:00:00Z
completed: 2026-06-14T13:00:00Z
previous_state: in_review
state_transition_reason: "Task complete — all acceptance criteria met, quality gates passed"
completed_location: tasks/completed/TASK-FIX-TBXMSG01/
priority: low
complexity: 2
related: [TASK-PERF-SPECLAT01, FEAT-9DDE]
implementation_mode: task-work
tags: [autobuild, ux, summary, messaging, timeout-budget]
---

# Task: fix misleading summary message for timeout_budget_exhausted

## Why this task exists

When an autobuild task ends with decision `timeout_budget_exhausted`, the
final summary panel renders:

```
╭─ AutoBuild Summary (TIMEOUT_BUDGET_EXHAUSTED) ─╮
│ Status: TIMEOUT_BUDGET_EXHAUSTED               │
│ Unknown error occurred. Worktree preserved ... │
╰────────────────────────────────────────────────╯
```

The decision is a **clean, well-classified budget exhaustion** (the log is
explicit: `Timeout budget exhausted for TASK-XXX at turn N: remaining=<X>s <
min=600s`). Labelling it "Unknown error occurred" sends an operator chasing a
non-existent crash. The message should state that the task ran out of its time
budget and how (turns used, remaining vs minimum).

## Symptom

- Summary box for `timeout_budget_exhausted` shows the generic
  "Unknown error occurred. Worktree preserved for inspection."
- The structured log line one step earlier is precise
  (`Timeout budget exhausted ... remaining=397.4s < min=600s`), so the box
  message is purely a template/mapping gap.

## Evidence (run 6)
- `.guardkit/autobuild/FEAT-9DDE-run6-stdout.log` L580 (precise budget line)
  vs L613-615 (the misleading "Unknown error occurred" box).
- Preserved: `docs/retro/run6-evidence/FEAT-9DDE-run6-stdout.log`.

## Acceptance Criteria

- [x] The summary panel for decision `timeout_budget_exhausted` shows a
      message that names the cause (time budget exhausted) and includes
      turns-used and remaining-vs-minimum, not "Unknown error occurred".
- [x] Genuine unknown-error decisions still render the generic message.
- [x] A unit test asserts the `timeout_budget_exhausted` decision maps to the
      budget message (and the unknown-error path is unchanged).

## Detection recipe
```bash
rg -n "Unknown error occurred" guardkit/orchestrator/
rg -n "timeout_budget_exhausted|TIMEOUT_BUDGET_EXHAUSTED" guardkit/orchestrator/ guardkit/cli/
```

## Implementation (2026-06-14)

Root cause: `AutoBuildOrchestrator._build_summary_details` (the rendered
summary panel) and `_build_error_message` (the `OrchestrationResult.error`
field) both lacked a `timeout_budget_exhausted` branch, so the decision fell
through to the generic `else: # error` fallback — "Unknown error occurred." —
in the panel and to an empty `""` in the error field (a `success=False`
result with no error text).

Changes in `guardkit/orchestrator/autobuild.py`:
- `__init__`: initialise `self._timeout_budget_remaining: Optional[float] = None`.
- `_loop_phase`: capture `self._timeout_budget_remaining = remaining_budget`
  at the instant the per-turn budget check fails, so the finalize-phase
  builders can report the precise `remaining=<X>s` value.
- `_build_summary_details`: new `elif final_decision == "timeout_budget_exhausted"`
  branch (inserted before the `else: # error` fallback) that names the cause,
  quotes turns-used and `remaining=<X>s < min=<MIN>s`, and states it is a
  clean budget exit, not a crash. Reads the captured value via
  `getattr(self, "_timeout_budget_remaining", None)` with a
  "remaining budget unknown" fallback.
- `_build_error_message`: matching branch so the error field is a meaningful
  budget message instead of `""`.
- Added `"timeout_budget_exhausted"` to both builders' `Literal` type hints
  (the `_loop_phase` return type already declared it).

Tests: `tests/unit/test_autobuild_timeout_budget_messaging.py` (6 tests, all
passing) — covers both builders' budget message (with and without a captured
remaining value) and asserts the unknown-error fallback is unchanged. Placed
in a **dedicated module** rather than the existing
`tests/unit/test_autobuild_timeout_budget.py` because a concurrent in-tree
task (TASK-PERF-SPECLAT01) was actively editing that file.

> **Coordination note:** TASK-PERF-SPECLAT01 (the `related` task) was being
> implemented concurrently in this same working tree and also has uncommitted
> edits to `guardkit/orchestrator/autobuild.py` (the `SPECIALIST_BUDGET_FRACTION`
> constant + `_cap_specialist_timeout`) and `specialist_invocations.py`. Those
> edits are in regions disjoint from this task's. No commit was made — the two
> tasks' changes will need to be committed separately/carefully.
