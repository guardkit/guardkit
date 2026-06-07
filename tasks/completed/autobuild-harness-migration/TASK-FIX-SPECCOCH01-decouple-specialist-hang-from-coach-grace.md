---
id: TASK-FIX-SPECCOCH01
title: Decouple specialist-hang detection from task-level cancellation_event so Coach grace-period only fires on real task-timeout boundary
status: completed
task_type: fix
created: 2026-06-07T10:30:00Z
updated: 2026-06-07T12:00:00Z
completed: 2026-06-07T12:00:00Z
previous_state: in_review
state_transition_reason: "Completed via /task-complete. AC-1/2/3 landed with green test suite; AC-4 deferred to operator-driven FEAT-AOF run 11."
completed_location: tasks/completed/autobuild-harness-migration/
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

- [x] **AC-1 (Shape A — primary)**: SPECHANG hang-detection
  (`specialist_invocations.py:_watchdog_*`) aborts the in-flight
  specialist WITHOUT setting the shared task-level `cancellation_event`.
  Specialist-local cancellation mechanism (specialist-scoped event or
  direct `harness.cancel()` on the specialist's harness handle) is
  used instead. Verified by:
  - Regression test asserting that simulated specialist hang fires the
    watchdog AND the task's `cancellation_event` is NOT set after
    specialist termination. — landed as
    `tests/unit/orchestrator/test_specialist_invocations.py::test_watchdog_does_not_set_shared_cancellation_event`
    (plus the mechanism check
    `test_watchdog_uses_specialist_local_event_distinct_from_shared`,
    which pins the specialist-local Event as a distinct object from
    the caller's shared one).
  - Existing CTOUT01 cancellation tests still pass (the in-flight
    LangGraph cleanup contract is preserved on the actual task-level
    timeout path). — covered by the existing watchdog-suite (22 pre-
    existing tests in the same file remain green) plus
    `test_external_shared_event_still_aborts_specialist` which
    explicitly exercises the shared-event forwarding path so a real
    `FeatureOrchestrator` timeout still terminates the in-flight
    specialist via the local-event forward.

- [x] **AC-2 (Shape B — defensive backstop)**: `COACH_GRACE_PERIOD_SECONDS`
  is read from `GUARDKIT_COACH_GRACE_PERIOD_SECONDS` env var with
  default raised from 120 to 1500. Verified by:
  - Unit test that the constant resolves to 1500 when env var is unset.
    — landed as
    `tests/unit/test_autobuild_timeout_budget.py::TestTimeoutBudgetConstants::test_coach_grace_period_unset_resolves_to_default`
    (plus the simpler
    `test_coach_grace_period_default_is_1500` constant pin).
  - Unit test that the constant resolves to the env-var value when set
    to a numeric string. — landed as
    `test_coach_grace_period_env_override` in the same class.
  - Documented in
    [`docs/guides/autobuild-instrumentation-guide.md`](../../../docs/guides/autobuild-instrumentation-guide.md)
    alongside `GUARDKIT_TASK_TIMEOUT_SECONDS`. — added a row to the
    *Environment variable tunables* table next to
    `GUARDKIT_MIN_TURN_BUDGET`, including the rationale (run-9's 944 s
    gemma4 baseline + headroom for `--reasoning auto`) and tuning
    guidance.

- [x] **AC-3 (regression test for the cascade)**: Scope agreed with
  Richard at task start: focused unit-level regression rather than a
  full Player→specialist-hang→Coach integration test in
  `tests/integration/orchestrator/`. AC-4 is the downstream end-to-end
  falsifier; CI coverage at this level is the contract boundary, not
  the orchestrator flow:
  - Simulates a Player success followed by a SPECHANG hang-detection —
    covered by the watchdog-fires test combined with the autobuild
    grace-period unit suite (`tests/unit/test_autobuild_timeout_budget.py`).
  - Asserts the orchestrator does NOT take the Coach grace-period
    branch (i.e. `cancellation_event` not set after specialist abort) —
    the load-bearing assertion in
    `test_watchdog_does_not_set_shared_cancellation_event` (the
    autobuild grace-period branch keys off `self._cancellation_event.is_set()`;
    when the watchdog provably leaves that event unset, the branch
    cannot fire).
  - Asserts Coach is invoked with its normal SDK timeout, not
    `budget_cap=120s` — implicit in the above (no grace branch means
    no `coach_remaining_budget=COACH_GRACE_PERIOD_SECONDS` override at
    `autobuild.py:3101`; Coach receives the same `remaining_budget` it
    would have on a no-hang turn). The autobuild-level grace-period
    tests in `TestCoachGracePeriodIntegration` continue to cover the
    *real* task-timeout path where the branch SHOULD fire.

- [ ] **AC-4 (falsifier — downstream verification)**: Run 11 of
  `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse
  --coach-model gemma4:26b` (with `--reasoning auto` configured on
  gemma4-coach and `task_timeout=4800s`) produces a Coach turn 1 with
  ≥1 text block extracted (verdict-emission actually exercised),
  regardless of whether the fenced JSON parses cleanly. The grace-period
  cascade does not fire on SPECHANG. AC-009 / `--reasoning auto` is
  finally exercisable. *(Deferred: requires actual FEAT-AOF run 11
  invocation by operator; not a CI-runnable test.)*

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

## Implementation Summary

**Approach**: Implemented both shapes as planned. Shape A (architectural
decoupling) was the cleanest: in `run_specialist`, when the watchdog is
enabled we always synthesise a fresh specialist-local `threading.Event`
and install it as `agent_invoker._cancellation_event`. The caller's
shared task-level event becomes a *separate* parameter
(`shared_cancellation_event`) to `_run_specialist_with_watchdog`. The
poll loop forwards the shared event into the local one if it gets set
externally (preserves CTOUT01's in-flight LangGraph cleanup contract on
real task-timeout boundaries); when the watchdog itself fires it sets
ONLY the local event. This guarantees a SPECHANG hang can never trip
the autobuild grace-period branch at `autobuild.py:3077-3087`. Shape B
made the `COACH_GRACE_PERIOD_SECONDS` constant env-tunable via
`GUARDKIT_COACH_GRACE_PERIOD_SECONDS` with the default raised from 120
to 1500, matching the gemma4:26b coach's empirical turn-1 latency
(944 s in run-9 of FEAT-AOF) with ~50 % headroom for `--reasoning auto`.

**Tests added**:

- `tests/unit/orchestrator/test_specialist_invocations.py`:
  - `test_watchdog_does_not_set_shared_cancellation_event` (AC-1
    primary): the load-bearing assertion — caller's event NOT set after
    a watchdog-detected hang.
  - `test_watchdog_uses_specialist_local_event_distinct_from_shared`
    (AC-1 mechanism): pins the implementation contract that the
    cancel-monitor polling target is a *different object* from the
    shared event.
  - `test_external_shared_event_still_aborts_specialist` (AC-1 CTOUT01
    compat): exercises the shared-event forwarding path so a real
    `FeatureOrchestrator` timeout still terminates the in-flight
    specialist via the local-event forward.
- `tests/unit/test_autobuild_timeout_budget.py`:
  - `test_coach_grace_period_default_is_1500` (AC-2 pin).
  - `test_coach_grace_period_env_override` (AC-2 env-tunable proof).
  - `test_coach_grace_period_unset_resolves_to_default` (AC-2 default
    branch under explicit env-var removal).
- Three pre-existing tests in `TestCapSpecialistTimeout` were rewritten
  to express expectations in terms of `COACH_GRACE_PERIOD_SECONDS`
  rather than hardcoded `120` so they survive future default changes;
  the retired `grace_period < min_turn_budget` invariant was removed
  (no longer load-bearing — the grace branch now only fires after the
  outer task budget is exhausted, so the comparison to the per-turn
  floor lost its meaning).

**Side-effect**: raising the default grace from 120 → 1500 means
`_cap_specialist_timeout` now reserves 1500 s of budget upfront for
Coach on every specialist call. Tasks with task_timeout under ~3000 s
will see specialists capped more aggressively. Operators on fast coaches
can claw the budget back via `GUARDKIT_COACH_GRACE_PERIOD_SECONDS=300`
(or similar).

**Lessons**:

- Two shared-state defensive features can each be locally correct yet
  combine into a structural cascade. The cancellation-event signal had
  two distinct semantic users (real task-timeout, watchdog termination);
  decoupling them via per-scope events was the cleaner contract than
  trying to disambiguate at the read sites.
- Hardcoded constants in tests (literal `120` instead of
  `COACH_GRACE_PERIOD_SECONDS`) create silent coupling: a one-line
  constant change broke math in three unrelated tests until they were
  rewritten symbolically. Future tunable-constant changes should grep
  for literal numeric occurrences alongside symbolic references.
- The grace-period default (120 → 1500) is a real ergonomic trade-off,
  not free — Shape B is belt-and-braces, but the *primary* fix is Shape
  A. If Shape A is correctly preserved, the grace branch fires only on
  legitimate task-timeout boundaries and the inflated reservation is
  almost never claimed.

**AC-4 falsifier** (deferred): operator-driven FEAT-AOF run 11 needed
to demonstrate that Coach turn 1 produces ≥1 text block on the
LangGraph harness with gemma4:26b + `--reasoning auto` configured.
Empirical end-to-end falsification is outside CI scope.
