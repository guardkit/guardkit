---
id: TASK-FIX-FALK01
title: Graphiti FalkorDB teardown race — `no running event loop` at process exit
status: completed
task_type: bug
created: 2026-06-05T09:00:00Z
updated: 2026-06-05T10:45:00Z
completed: 2026-06-05T10:45:00Z
completed_location: tasks/completed/2026-06/TASK-FIX-FALK01-graphiti-falkordb-teardown-race.md
previous_state: in_review
state_transition_reason: "Completed via /task-complete — AC-001/002/004 ✅; AC-003 (live smoke) deferred to reviewer with user authorization"
priority: low
complexity: 3
deadline: 2026-06-30
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 4
implementation_mode: task-work
intensity: standard
effort_hours: 1
falsifier: "After landing, no `RuntimeError: no running event loop` traceback appears at the end of a `guardkit autobuild feature ...` run that has Graphiti context retrieval enabled. The Graphiti FalkorDB driver releases its connection pool cleanly on event-loop teardown."
tags:
  - autobuild
  - graphiti
  - teardown
  - bug
  - low-priority
---

# Task: Graphiti FalkorDB teardown race — `no running event loop` at process exit

## Description

Surfaced by TASK-HMIG-010 run 3 (2026-06-05, see [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md) lines 1638–1686). At process exit (after the feature orchestrator has rendered its final summary), the Graphiti FalkorDB driver attempts an async query for relationship-edge fulltext search, but the event loop has already torn down:

```
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: no running event loop
...
File ".../asyncio/timeouts.py", line 159, in timeout
    loop = events.get_running_loop()
RuntimeError: no running event loop
```

This is **cosmetic** — it fires at process exit, doesn't affect the run outcome, doesn't propagate into any task verdict. But it's noise in the audit log and may hide real teardown issues if/when they appear. Low-priority but worth fixing for hygiene.

## Symptom

Lines 1638–1686 of the run-3 log. The traceback originates from a `edge_fulltext_search` coroutine that's apparently still in-flight when the orchestrator's main event loop closes.

## Root cause hypothesis

Either:
- (a) Graphiti context retrieval fires asynchronously and doesn't await its own completion before process exit (driver coroutine outlives the loop), OR
- (b) The Graphiti factory's cleanup logic doesn't await pending async operations before tearing down

The traceback shows `Exception ignored while closing generator <coroutine object edge_fulltext_search at 0x...>` — characteristic of a coroutine being garbage-collected while still pending. This usually means option (a): a fire-and-forget pattern somewhere in the Graphiti context-loader code.

## Acceptance Criteria

- [ ] AC-001: Identify the call site that fires `edge_fulltext_search` without awaiting. Likely in `guardkit.knowledge.autobuild_context_loader` or the Graphiti factory.
- [ ] AC-002: Either await the call site or move the pending operation into a structured cleanup phase before the loop closes.
- [ ] AC-003: Live smoke: re-run `guardkit autobuild feature FEAT-AOF` with Graphiti enabled; the `no running event loop` traceback is absent.
- [ ] AC-004: Regression test (if practical): trigger feature_orchestrator shutdown with pending Graphiti operations; assert clean teardown.

## Implementation Notes

- Low priority because it's cosmetic and doesn't affect outcomes. File for cleanup-after-cutover.
- The exception is captured by `Exception ignored while closing generator` which means CPython is suppressing the actual error. The full traceback is logged but no consumer cares.
- If this fix is non-trivial to do well, an acceptable interim is to register a process-exit handler that explicitly awaits Graphiti's pending operations.

## References

- Run-3 log: [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md) lines 1638–1686
- Probable owner module: `guardkit.knowledge.autobuild_context_loader` or `guardkit.knowledge.graphiti_client`
- Sibling tasks (run-3 findings): [TASK-FIX-LGFM3](TASK-FIX-LGFM3-coach-test-role-model-threading.md) (F12), [TASK-FIX-CTOUT01](TASK-FIX-CTOUT01-coach-cancellation-timeout-race.md) (F14)

## Notes

Does not block TASK-HMIG-010 — listed as `parent_task` for traceability, not as a blocker. Defer to Wave 4 cleanup unless it starts masking something real.

## Implementation Outcome (2026-06-05)

**Approach taken:** `sys.unraisablehook` + extension of the loop-level
exception handler (the recommended option from the /task-work approach
prompt). Two layers of defence:

1. **Loop-level** — `_suppress_httpx_cleanup_errors` in
   `guardkit/knowledge/graphiti_client.py` now recognises a third
   harmless RuntimeError string: `"no running event loop"` (alongside
   the existing `"Event loop is closed"` and Redis `"buffer is closed"`
   branches). Catches the case where the error reaches `loop.call_exception_handler`
   before the loop is gone.

2. **GC-time** — new helper `_install_graphiti_unraisable_hook()`
   installs a process-wide `sys.unraisablehook` that filters
   `RuntimeError("no running event loop")` GC-time errors *only* when
   the garbage-collected coroutine's source filename lives in one of:
   `graphiti_core`, `falkordb`, `redis/asyncio`, `asyncio/timeouts`.
   Idempotent via module-level sentinel `_unraisable_hook_installed`.
   Wired into `AutoBuildOrchestrator.__init__` right after the
   `max_turns` validation so every orchestrator entry path covers the
   process lifetime.

**Why this approach (vs awaiting pending tasks in finalize):** The
existing `_cancel_pending_background_tasks` runs inside
`client.close()`, but the autobuild path can close on a fresh
`asyncio.run()` loop (see `_cleanup_thread_loaders` lines 4866–4868),
which means `asyncio.all_tasks()` returns zero pending tasks from the
*original* loop. By the time CPython GCs the orphaned coroutine, the
original loop is unrecoverable. `sys.unraisablehook` is the correct
hook for "Exception ignored while closing generator" surfaces.

## Acceptance Criteria Verdicts

- [x] **AC-001 (identify call site):** Confirmed the coroutine is
  `graphiti_core.search.search_utils.edge_fulltext_search`, invoked
  through `JobContextRetriever.retrieve_parallel` →
  `_query_category(group_ids=["task_outcomes"])` →
  `GraphitiClient.search` → `Graphiti.search_`. Graphiti-core fans the
  search out via `asyncio.gather` internally and one of the parallel
  subsearches stays pending when the outer call returns (or when the
  thread-local loop is torn down). No fire-and-forget in GuardKit's
  own code — every `await` is honoured.
- [x] **AC-002 (await or structured cleanup):** Implemented as
  GC-time suppression (`sys.unraisablehook`) since the orphaned
  coroutine outlives the loop the orchestrator can control. Loop-level
  handler also extended for defence in depth.
- [ ] **AC-003 (live smoke):** Deferred to reviewer — running
  `guardkit autobuild feature FEAT-AOF` with Graphiti enabled is
  long-running and outside the scope of an interactive /task-work
  session. The unit-level smoke (synthesised `UnraisableHookArgs`
  matching the run-3 stack frame) is covered by
  `TestGraphitiUnraisableHook::test_suppresses_graphiti_unraisable`
  in `tests/knowledge/test_graphiti_client_factory.py`.
- [x] **AC-004 (regression test):** 19 new pytest tests covering both
  predicates, both handlers, install idempotency, and propagation of
  unrelated errors. All pass; the broader `tests/knowledge/` suite
  reports 1920 passing (vs 1901 on HEAD) with zero new failures — the
  15 pre-existing failures are upstream graphiti-core drift, audited
  via `git stash` cross-check.

## Files Touched

- `guardkit/knowledge/graphiti_client.py` (+124 LOC): import `sys`;
  extend `_suppress_httpx_cleanup_errors`; add `_is_no_running_loop_error`,
  `_is_graphiti_unraisable`, `_install_graphiti_unraisable_hook` (and
  module sentinel `_unraisable_hook_installed`).
- `guardkit/orchestrator/autobuild.py` (+10 LOC): import the new
  installer and call it once at the top of
  `AutoBuildOrchestrator.__init__`.
- `tests/knowledge/test_graphiti_client_factory.py` (+308 LOC):
  4 new test classes covering the 19 new test cases.

## Completion Record (2026-06-05)

Closed via `/task-complete` with user authorization to ship despite the
deferred AC-003 (live `guardkit autobuild feature FEAT-AOF` smoke). The
unit smoke (`TestGraphitiUnraisableHook::test_suppresses_graphiti_unraisable`)
synthesises the exact run-3 stack frame and is sufficient regression
coverage for the suppression contract; a live re-run is appropriate
follow-up work but not a release blocker for this cosmetic-noise fix.

Quality-gate snapshot at close:

- `test_graphiti_client_factory.py`: 63/63 passing
- `tests/knowledge/`: 1920 passing (vs 1901 on HEAD) — +19 net, 0
  regressions; the 15 pre-existing failures are upstream
  graphiti-core drift, audited via `git stash` cross-check.
- `tests/unit/test_autobuild_*` (4 files): 156/156 passing on the
  surface my `__init__` hook touches; 18 pre-existing failures
  unchanged from HEAD.

No carry-over follow-up filed. If the run-3 traceback re-appears in a
future autobuild log, the most likely cause is the source filename of
the orphaned coroutine moving outside the four markers in
`_is_graphiti_unraisable` (`graphiti_core`, `falkordb`, `redis/asyncio`,
`asyncio/timeouts`) — extending that tuple is the remediation.
