---
id: TASK-FIX-SPECCOCH01
title: Decouple specialist-hang detection from task-level cancellation_event so Coach grace-period only fires on real task-timeout boundary
status: backlog
task_type: fix
created: 2026-06-07T10:30:00Z
updated: 2026-06-07T10:30:00Z
priority: high
complexity: 3
effort_hours: 2
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: direct
intensity: standard
blocker: true
surfaced_in: docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md
falsifier: "After landing: run 11 of `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse --coach-model gemma4:26b` under `GUARDKIT_HARNESS=langgraph` with `--reasoning auto` configured on gemma4-coach: Coach LLM produces ≥1 text block (verdict-emission attempt is actually exercised), regardless of fenced-JSON outcome. The grace-period cascade no longer fires on SPECHANG hang-detection."
---

# Task: Decouple specialist-hang detection from task-level cancellation_event

## Why this task exists

Run 10 ([autobuild-FEAT-AOF-run-10.md](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md))
surfaced a code-side cascade defect (F22, recorded as
[I-011](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md))
between two independently-correct defensive features:

1. **SPECHANG hang-watchdog** ([`specialist_invocations.py:113`](../../../guardkit/orchestrator/specialist_invocations.py)) — when a specialist invocation goes 150s without model activity (no httpx response), the watchdog terminates the specialist via the shared `cancellation_event`. This is correct for CTOUT01's in-flight LangGraph cleanup contract (`.claude/rules/harness-cancellation-contract.md`).
2. **TASK-ABFIX-004 Coach grace-period** ([`autobuild.py:3077-3087`](../../../guardkit/orchestrator/autobuild.py)) — when `cancellation_event` is set between Player success and Coach validation, the orchestrator infers "task budget exhausted but Player did good work; let Coach validate inside a grace window". The grace window is `COACH_GRACE_PERIOD_SECONDS = 120` ([`autobuild.py:191`](../../../guardkit/orchestrator/autobuild.py)).

Each mechanism is correct in isolation. The bug is that they share the same signal (`cancellation_event`) and the grace constant (120s) is structurally insufficient given run-9's empirical evidence (gemma4 Coach turn 1 = 944s under `--reasoning off`).

**Symptom in run 10** ([run-10:214-253](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L214-L253)):

```
Line 214: hang detected (no model activity for 150s) — terminating before the 600s duration cap
Line 218: Cancellation detected ... Player succeeded — granting Coach grace period (120s)
Line 250: SDK timeout: 120s (budget_cap=120s)
Line 252: TASK-FIX-CTOUT01: Cancellation event detected during coach invocation
Line 253: Extracted partial data from 0 events: 0 text blocks
```

Coach never produced output. AC-009 / `--reasoning auto` was deliberately
configured but never actually exercised. AC-006 evaluation blocked.

## What to do

**Shape A (primary)**: Decouple specialist-hang detection from the
task-level `cancellation_event`.

- Specialist invocation should abort the in-flight specialist using a
  *specialist-local* event (or by directly calling
  `harness.cancel()` on the specialist's harness handle), NOT by
  setting the shared task-level `cancellation_event`.
- Orchestrator continues normally after specialist failure — the
  specialist failure already injects `validation=violation` records
  via `_inject_specialist_records_into_task_work_results`
  ([run-10:217](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L217)),
  so downstream Coach validation sees a graceful failure not a
  missing record.
- Coach proceeds with normal SDK timeout (not grace-period-capped).

**Shape B (defensive backstop, land regardless)**: Make
`COACH_GRACE_PERIOD_SECONDS` env-tunable.

- New env var `GUARDKIT_COACH_GRACE_PERIOD_SECONDS`, same pattern as
  `GUARDKIT_TASK_TIMEOUT_SECONDS` from
  [TASK-FIX-AOFBUDG](../../completed/2026-06/TASK-FIX-AOFBUDG-raise-feat-aof-task-timeout-for-two-turn-run.md).
- Default raised from 120 to **1500** (covers run-9's 944s gemma4
  Coach + ~50% headroom for `--reasoning auto`'s richer reasoning
  channel).
- Reading: `COACH_GRACE_PERIOD_SECONDS = int(os.environ.get("GUARDKIT_COACH_GRACE_PERIOD_SECONDS", 1500))` at
  [`autobuild.py:191`](../../../guardkit/orchestrator/autobuild.py).

Both shapes together. Shape A is the architectural fix; Shape B is
belt-and-braces in case any other code path still ends up routing
through the grace branch.

## Acceptance criteria

- [ ] **AC-1 (Shape A — primary)**: SPECHANG hang-detection
  (`specialist_invocations.py:_watchdog_*`) aborts the in-flight
  specialist WITHOUT setting the shared task-level `cancellation_event`.
  Specialist-local cancellation mechanism (specialist-scoped event or
  direct `harness.cancel()` on the specialist's harness handle) is
  used instead. Verified by:
  - Regression test asserting that simulated specialist hang fires the
    watchdog AND the task's `cancellation_event` is NOT set after
    specialist termination.
  - Existing CTOUT01 cancellation tests still pass (the in-flight
    LangGraph cleanup contract is preserved on the actual task-level
    timeout path).

- [ ] **AC-2 (Shape B — defensive backstop)**: `COACH_GRACE_PERIOD_SECONDS`
  is read from `GUARDKIT_COACH_GRACE_PERIOD_SECONDS` env var with
  default raised from 120 to 1500. Verified by:
  - Unit test that the constant resolves to 1500 when env var is unset.
  - Unit test that the constant resolves to the env-var value when set
    to a numeric string.
  - Documented in
    [`docs/guides/autobuild-instrumentation-guide.md`](../../../docs/guides/autobuild-instrumentation-guide.md)
    alongside `GUARDKIT_TASK_TIMEOUT_SECONDS`.

- [ ] **AC-3 (regression test for the cascade)**: New integration test
  in `tests/integration/orchestrator/` that:
  - Simulates a Player success followed by a SPECHANG hang-detection.
  - Asserts the orchestrator does NOT take the Coach grace-period
    branch (i.e. `cancellation_event` not set after specialist abort).
  - Asserts Coach is invoked with its normal SDK timeout, not
    `budget_cap=120s`.

- [ ] **AC-4 (falsifier — downstream verification)**: Run 11 of
  `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse
  --coach-model gemma4:26b` (with `--reasoning auto` configured on
  gemma4-coach and `task_timeout=4800s`) produces a Coach turn 1 with
  ≥1 text block extracted (verdict-emission actually exercised),
  regardless of whether the fenced JSON parses cleanly. The grace-period
  cascade does not fire on SPECHANG. AC-009 / `--reasoning auto` is
  finally exercisable.

## Implementation notes

- **Shape A wiring**: The `cancellation_event` shared at the task
  level is currently being passed into specialist invocations as the
  abort signal. Either:
  - (a) Specialist invocations construct their own local
    `asyncio.Event` and pass that to the harness, then call
    `harness.cancel()` directly when the watchdog fires, OR
  - (b) The watchdog logic is moved out of the shared-event path and
    into a specialist-local termination primitive.
  - Option (a) is the cleaner separation. The shared task-level event
    remains exclusively the task-timeout / outer-orchestrator-cancel
    signal.

- **CTOUT01 compatibility**: The in-flight LangGraph cleanup contract
  (`.claude/rules/harness-cancellation-contract.md`) requires
  `harness.cancel()` to be called within `GUARDKIT_HARNESS_CANCEL_DEADLINE`
  (default 30s). Shape A preserves this — `harness.cancel()` is still
  called when the watchdog fires, just via the specialist-local path
  instead of the shared event.

- **Shape B placement**: One-line change at `autobuild.py:191`:
  ```python
  import os
  COACH_GRACE_PERIOD_SECONDS: int = int(os.environ.get("GUARDKIT_COACH_GRACE_PERIOD_SECONDS", 1500))
  ```
  Verify all read sites still work (currently 4 references per grep).

- **Test scope**: Heavy unit-test coverage on Shape A wiring; one
  integration test exercising the full Player→specialist-hang→Coach
  flow for AC-3. The falsifier (AC-4) is a downstream verification by
  the next FEAT-AOF run, not a CI test.

## Related

- **Surfaces**: F22 in [feature-run-analysis.md §6](../../../docs/state/TASK-REV-HMIG/feature-run-analysis.md)
- **Incident**: I-011 in [feature-run-incidents.md](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md)
- **Sibling defensive feature**:
  [TASK-FIX-AOFBUDG](../../completed/2026-06/TASK-FIX-AOFBUDG-raise-feat-aof-task-timeout-for-two-turn-run.md)
  — established the env-tunable-timeout pattern Shape B follows.
- **Sibling rule (harness cancellation contract)**:
  [`.claude/rules/harness-cancellation-contract.md`](../../../.claude/rules/harness-cancellation-contract.md)
  — the four-layer cancellation taxonomy; Shape A keeps CTOUT01
  Layer-3 contract intact while removing the specialist-watchdog's
  unintended cascade into Layer-4 reconciliation.
- **Blocks**: TASK-HMIG-010 (verdict-blocker for run 11), TASK-HMIG-013
  AC-006 + AC-009 (cannot be evaluated until run 11 produces a Coach
  text-block emission).
