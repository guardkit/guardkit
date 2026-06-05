---
id: TASK-FIX-FALK01
title: Graphiti FalkorDB teardown race — `no running event loop` at process exit
status: backlog
task_type: bug
created: 2026-06-05T09:00:00Z
updated: 2026-06-05T09:00:00Z
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
