---
id: TASK-FIX-SPECINVOKE01
title: Root-cause the deterministic test-orchestrator specialist zero-activity hang under the LangGraph harness
status: completed
task_type: fix
created: 2026-06-13T12:40:00Z
updated: 2026-06-13T14:20:00Z
completed: 2026-06-13T14:20:00Z
previous_state: in_review
completed_location: tasks/completed/2026-06/
state_transition_reason: "All quality gates passed: root cause fixed, tests green (723 across both repos), SPECVIOL01 invariant intact"
priority: medium
complexity: 6
related: [TASK-FIX-SPECHANG, TASK-FIX-SPECVIOL01, FEAT-9DDE]
implementation_mode: task-work
tags: [autobuild, harness, specialist, test-orchestrator, hang, langgraph]
---

# Task: Root-cause the test-orchestrator specialist zero-activity hang

## Why this task exists

FEAT-9DDE run 3 (2026-06-13) confirmed the specialist-invocation hang is
**deterministic, not intermittent, and independent of the Player model**: the
stronger qwen3-coder-30b Player still saw `run_specialist(test-orchestrator)`
hang on **both** turns of TASK-TSJ-001 with **zero model activity**:

```
[TASK-TSJ-001] test-orchestrator sdk_timeout capped 3299s -> 600s (TASK-FIX-SPECHANG)
[TASK-TSJ-001] specialist:test-orchestrator invocation in progress... (30s..150s elapsed)
run_specialist(test-orchestrator): hang detected (no model activity for 150s)
  — terminating before the 600s duration cap
```

The improved hang detector (terminate at 150s of no activity, vs run-2's 700s+)
works correctly and the build still converged — so this is a **cleanup /
efficiency** item, not a build blocker — but every turn wastes ~150s and injects
a `validation=violation` specialist record. The detector treats the symptom; this
task is to find why the `test-orchestrator` specialist sub-invocation produces
**no model activity at all** under the LangGraph harness (no HTTP request reaches
`:9000`), and fix the invocation path so the specialist actually runs (or is
cleanly skipped when not applicable) instead of hanging.

## Acceptance Criteria

- [x] Root cause identified: see "Root cause" below. The premise was wrong —
      the specialist does NOT issue zero LLM calls. The watchdog's activity
      *signal* is substrate-blind under LangGraph.
- [x] The specialist (a) runs and produces real activity: the no-model-activity
      watchdog now measures real LLM/tool progress via a substrate callback, so
      a live specialist is no longer false-killed at 150s.
- [x] Redundancy documented (see "Why fix rather than gate off"): we chose to
      FIX the watchdog signal rather than gate the specialist off, so the
      Phase-4 `phase_4_summary.json` gate-credit is retained. Coach's
      independent run remains the authoritative pass bar.
- [x] Regression tests exercising the branch (callback keeps a buffered
      LangGraph run alive; genuine hang still killed): see "Tests".
- [x] The SPECVIOL01 invariant continues to hold — no change to the specialist
      `validation=violation` → non-honesty mapping;
      `tests/orchestrator/test_specialist_violation_attribution.py` stays green.

## Root cause (TASK-FIX-SPECINVOKE01, 2026-06-13)

The framing ("zero model activity / no HTTP reaches `:9000`") is **wrong**.
Run-3 [`FEAT-9DDE-run3-stdout.log:211-221`] shows ~18 successful
`POST :9000/v1/responses "200 OK"` calls *during* the invocation — the model
was working — yet the orchestrator logged `Extracted partial data from 0 events`.

Mechanism (deterministic, LangGraph-only, model-independent):

1. The no-activity watchdog (`specialist_invocations._run_specialist_with_watchdog`)
   keys on `AgentInvoker._last_activity_monotonic`.
2. That clock is bumped **only inside the `async for event in _harness_stream`
   loop** (`agent_invoker.py:3829`) — i.e. once per *yielded* harness event.
3. But `LangGraphHarness.invoke()` does `result = await self._ainvoke_task`
   (`langgraph_harness.py`) — it awaits the **entire** multi-turn
   `agent.ainvoke()` before yielding *any* event. So during the whole run zero
   events reach the consumer, the clock freezes at its seed value, the gap
   grows unconditionally, and the watchdog kills a live, model-active
   specialist at 150s.

The SDK harness streams per-message, so its clock stays fresh and the watchdog
never misfires there — which is exactly why this never reproduced on SDK. This
is a sibling of `.claude/rules/harness-cancellation-contract.md`: a
substrate-agnostic oracle (harness-event arrival) that silently breaks on a
substrate (LangGraph buffered `ainvoke`) it wasn't written for.

## Fix (substrate-aware activity signal)

- `guardkitfactory` `LangGraphHarness`: new `on_model_activity` ctor param +
  `_ModelActivityCallbackHandler` (a LangChain `BaseCallbackHandler`) threaded
  into `agent.ainvoke(..., config={"callbacks": [...]})` (and `invoke_synthesis`).
  It pings the sink on every LLM/tool boundary.
- `guardkit` `selector.py`: pops `on_model_activity` and forwards it to the
  LangGraph branch only (drop-with-WARNING on a stale factory); the SDK harness
  never sees it (it already streams).
- `guardkit` `agent_invoker.py`: `_bump_activity()` refreshes
  `_last_activity_monotonic`; passed as `on_model_activity` at the
  `_invoke_with_role` `select_harness` call.

Net: the watchdog now measures *real* model activity. A genuine hang (run-9:
httpx stops entirely → no callbacks → clock freezes → trips, as intended) stays
caught; a healthy buffered run (run-3: callbacks fire steadily) no longer
false-trips. No event-streaming semantics change → minimal blast radius.

### Why fix rather than gate off (AC-3)

Gating the specialist off under LangGraph (AC-2b) would lose the Phase-4
`phase_4_summary.json` gate-credit the specialist produces. Fixing the signal
keeps that capability while eliminating the 150s grind + `validation=violation`.
Coach's independent pytest run remains the authoritative pass bar regardless.

### Tests

- `guardkitfactory/tests/harness/test_langgraph_harness.py::TestModelActivityCallback`
  — callback threaded into `ainvoke` config + fires the sink; sink exceptions
  swallowed; default keeps single-arg `ainvoke`.
- `tests/unit/orchestrator/test_specialist_invocations.py::test_run_specialist_watchdog_survives_buffered_langgraph_run`
  — buffered run (0 events, callback-only activity) is NOT killed; contrasts
  with the existing `..._terminates_hung_specialist` (no pings → still killed).
- `tests/orchestrator/harness/test_selector.py` — selector forwards
  `on_model_activity` to LangGraph, pops it for SDK.
- `tests/orchestrator/harness/test_xrepo_contract_seam.py::...test_langgraph_harness_init_accepts_on_model_activity`
  — cross-repo seam guard: fails loud if a stale guardkitfactory drops the param.

## Evidence
- Result writeup: `docs/retro/coder-player-experiment-RESULT-2026-06-13.md` §"Finding 3".
- Run log: `.guardkit/autobuild/FEAT-9DDE-run3-stdout.log` (httpx 200s during the
  "hang"; `Extracted partial data from 0 events`).
- Specialist records: `.guardkit/worktrees/FEAT-9DDE/.guardkit/autobuild/TASK-TSJ-001/specialist_results.json`.
</content>
