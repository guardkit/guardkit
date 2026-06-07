---
id: TASK-FIX-LGACLOSE
title: Close LangGraphHarness.invoke async generator on cancel (aclose never awaited / Task destroyed pending)
status: completed
task_type: bug
created: 2026-06-07T13:00:00Z
updated: 2026-06-07T14:45:00Z
completed: 2026-06-07T14:45:00Z
previous_state: in_review
state_transition_reason: "task-complete — AC-1/2/3 done; 4 consumer sites + harness defensive finally; tests pass, zero new failures"
priority: medium
complexity: 3
effort_hours: 2
deadline: 2026-06-30
parent_review: TASK-REV-AOF-RUN9
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 4
implementation_mode: task-work
intensity: standard
related_tasks:
  - TASK-FIX-CTOUT01   # completed — cancels ainvoke task but does NOT close the generator (this is its surface)
surfaced_in: ../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md
tags:
  - autobuild
  - langgraph-migration
  - cancellation
  - resource-leak
falsifier: "After landing, a timeout-cancelled LangGraph harness invocation produces NO `coroutine method 'aclose' of 'LangGraphHarness.invoke' was never awaited` RuntimeWarning and NO `Task was destroyed but it is pending` asyncio error at interpreter shutdown. A unit test cancels a consumer mid-iteration of `LangGraphHarness.invoke` and asserts the generator is finalised (aclose awaited) with `self._ainvoke_task` cleared."
---

# Task: Close the LangGraph harness async generator on cancel (anomaly D / R3)

## Why this task exists

Run-9 ended (post-finalize) with:

```
ERROR:asyncio:Task was destroyed but it is pending!
task: <Task pending name='Task-2026' coro=<<async_generator_athrow without __name__>()>>
.../asyncio/base_events.py:744: RuntimeWarning: coroutine method 'aclose' of
  'LangGraphHarness.invoke' was never awaited
```

`LangGraphHarness.invoke` is an **async generator** (`yield` at
`src/guardkitfactory/harness/langgraph_harness.py:385/387/392`). `TASK-FIX-CTOUT01`
(completed) wraps `agent.ainvoke` in an `asyncio.Task` so `cancel()` propagates
`CancelledError` (lines 327-363) — **but it does not close the generator itself**.
When the consumer (guardkit `agent_invoker`) iterating the generator is cancelled
by the feature timeout, the generator is abandoned without `await gen.aclose()`,
leaving a pending `async_generator_athrow` task that the GC tries to close at
shutdown. CTOUT01 closed the cancellation gap but left this finalisation gap — its
own surface.

**Severity is low** (the review confirmed): it fires **only** on the
cancel/timeout path, **after** the run has already failed; the SDK subprocess is
already terminated by CTOUT01 (run-9 L475); the leaked athrow tasks die with the
process. No cross-run contamination — it is shutdown noise. Fix it to keep the
logs clean and to be correct on the cancel path. **Not a pre-run blocker.**

## What to do (cross-repo — primary fix is the consumer)

1. **Consumer (guardkit, primary):** wherever `agent_invoker` iterates
   `harness.invoke(...)`, wrap iteration so the generator is always finalised on
   cancel, e.g. `async with contextlib.aclosing(harness.invoke(...)) as stream:`
   (or an explicit `try/finally: await stream.aclose()`).
2. **Harness (guardkitfactory, defensive):** make `LangGraphHarness.invoke` handle
   `GeneratorExit` / `finally` around its yields so that, when closed mid-stream,
   it cancels/awaits `self._ainvoke_task` if still set and nulls the handle.

## Acceptance criteria

- [x] **AC-1:** Consumer finalises the harness generator on cancel (`aclosing`/
  `try-finally`). — **All four** `harness.invoke(...)` consumer iteration
  sites now wrap the generator in `contextlib.aclosing(...)` so it is
  finalised on every exit (normal / break / raise / cancellation):
  `agent_invoker._invoke_with_role` (specialist/Player/Coach) and
  `agent_invoker._invoke_task_work_implement` (task-work Player) — the two
  the task named — **plus** `quality_gates/coach_validator.py` (Coach
  independent test-exec, `coach_test` role) and
  `quality_gates/task_work_interface.py` (design phase, `design` role),
  which iterate the same async generator under their own `asyncio.timeout`
  and would leak identically. Fixing only the two named sites would leave
  the same latent leak in the other two.
- [x] **AC-2:** Harness `invoke` tolerates `GeneratorExit` and clears
  `self._ainvoke_task`. — `LangGraphHarness.invoke`
  (`guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py`) now
  wraps its whole body (incl. yields) in an outer `try/finally` that, on any
  exit, cancels a still-pending `_ainvoke_task` and nulls the handle.
- [x] **AC-3:** Regression test: cancel a consumer mid-iteration; assert no
  pending athrow task and no `aclose never awaited` warning. — Harness:
  `tests/harness/test_langgraph_harness.py::TestAcloseFinalisation` (3 tests,
  pass under `-W error::RuntimeWarning`). Consumer (call-site pinning, the
  discriminating guard): `tests/unit/test_generator_close_fix.py::TestHarnessInvokeAclosingOnCancel`
  (5 tests covering all four sites + the import; fail on the un-fixed
  consumer, pass after).

## Implementation notes (task-work outcome, 2026-06-07)

- **AC-2 is genuinely defensive** (as the task scoped it): the *old* harness
  already cleared `_ainvoke_task` in an inner `finally` right after the
  `await`, and asyncio's await-chain cancellation already cancelled the
  in-flight task on the consumer-cancel path — so the black-box harness
  tests pass on both old and new code. They pin the contract; the
  **discriminating** coverage is the AC-1 call-site introspection tests.
- The real orphan (`async_generator_athrow` / "aclose never awaited") is a
  **consumer-side** abandonment; AC-1 (`aclosing`) is the load-bearing fix.
- **Pre-existing test debt (out of scope):** `test_generator_close_fix.py`
  carries 8 stale failures from the TASK-HMIG-006 SDK→harness migration
  (they assert the removed `gen = query(...)` path in `_invoke_with_role`).
  Verified identical pass/fail with and without this change; not touched.
- Changes left uncommitted in both repos (guardkit on `main`,
  guardkitfactory on `fix/coachbudg01-lg-responses-api-reasoning`) — awaiting
  human review/commit.

## References

- Review (anomaly D / R3): `../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md`
- Harness: `guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py:249-396`
- CTOUT01 (completed): `tasks/completed/2026-06/TASK-FIX-CTOUT01-coach-cancellation-timeout-race.md`
- Run-9 log L475-476, L517-523
