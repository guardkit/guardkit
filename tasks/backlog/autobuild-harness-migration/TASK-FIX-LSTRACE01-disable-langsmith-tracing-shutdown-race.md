---
id: TASK-FIX-LSTRACE01
title: Make LangSmith tracing executor-teardown-safe — kills the "cannot schedule new futures after shutdown" crash on task_timeout teardown
status: completed
task_type: fix
created: 2026-06-12T10:00:00Z
updated: 2026-06-12T11:00:00Z
completed: 2026-06-12T11:00:00Z
state_transition_reason: "Implemented + unit-verified: LangSmith aio_to_thread inline override (load-bearing) + tracing-off hygiene; 4 new regression tests incl. a crash control, 34 existing harness tests green. End-to-end confirmation on the next FEAT-E2CB re-run."
priority: high
complexity: 3
related: [TASK-FIX-CTOUT01, TASK-HMIG-BDDWIRE, TASK-OPS-COACHMOE01]
implementation_mode: task-work
tags: [autobuild, harness, langsmith, cancellation, shutdown-race, harness-cancellation-contract]
---

# Task: Disable LangSmith tracing in the autobuild harness

## Why this task exists

FEAT-E2CB run 1 (2026-06-12, first BDDWIRE/generalization autobuild) **failed
with `decision=timeout`** when the feature-level `task_timeout=4800s` fired on
turn 3 of TASK-BDDW-001. The proximate crash was **not** a Coach/Player quality
problem — it was a harness shutdown race in **LangSmith tracing**:

```
deepagents/middleware/summarization.py:1086 awrap_model_call
→ langchain/agents/factory.py:378 inner_handler
→ langsmith/run_helpers.py:661 async_wrapper
→ langsmith/_internal/_aiter.py:363/376 aio_to_thread → loop.run_in_executor(None, func_call)
→ concurrent/futures/thread.py:170 submit
→ RuntimeError: cannot schedule new futures after shutdown
```

LangSmith tracing dispatches its background work via `loop.run_in_executor(None,
...)` — the asyncio loop's **default** `ThreadPoolExecutor`. When the
`task_timeout` teardown shuts that executor down (Layer-1 of the cancellation
taxonomy — `asyncio.wait_for(asyncio.to_thread(...))`), in-flight / retrying
LangSmith trace submissions crash with `cannot schedule new futures after
shutdown` (and `... after interpreter shutdown` for the Coach), cascading
through the deepagents summarization middleware so **both** `player` and `coach`
`agent.ainvoke` fail. The run then reports `timeout`.

Autobuild does not need LangSmith tracing; it is pure overhead **and** a crash
vector. This is a sibling of `.claude/rules/harness-cancellation-contract.md`
(TASK-FIX-CTOUT01) — a cancellation/shutdown path that crashes instead of
aborting cleanly.

## The fix (implemented 2026-06-12)

**Corrected root cause (investigation finding):** disabling tracing is **NOT
sufficient**. `langsmith.run_helpers.async_wrapper` dispatches its run-tree
setup/teardown (`_setup_run` / `_on_run_end`) via `loop.run_in_executor(None, ...)`
**unconditionally** (run_helpers.py:607, *before* any tracing-enabled check — the
tracing decision is made inside `_setup_run`, which runs *in* the dispatched
thread). So the crash fires regardless of tracing state. Verified: this env's
`tracing_is_enabled()` is already `False`, yet the run crashed in langsmith.

1. **(LOAD-BEARING) Register a LangSmith runtime override that runs `aio_to_thread`
   INLINE** instead of on the loop's default executor — via the public
   `langsmith.set_runtime_overrides(aio_to_thread=...)` hook (the same pattern as
   LangSmith's own Temporal example, which has the identical "no `run_in_executor`"
   constraint). `_setup_run`/`_on_run_end` are cheap, so inlining is safe and a
   torn-down executor can never crash the invoke.
2. **(hygiene) Force tracing off** unless `GUARDKIT_KEEP_LANGSMITH` is set —
   autobuild has no LangSmith project.

Implemented in
[`guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py`](../../../../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py)
(`_install_langsmith_executor_guard()`, run at module import). Regression test:
`guardkitfactory/tests/harness/test_langgraph_harness_lstrace.py`.

## Acceptance criteria

- [x] **AC-1:** the autobuild harness forces LangSmith tracing off by default
  (`test_guard_disables_tracing_by_default`) with a `GUARDKIT_KEEP_LANGSMITH`
  escape hatch (`test_guard_respects_keep_optout`).
- [x] **AC-2 (unit-verified; end-to-end pending re-run):** with the override
  installed, a torn-down default executor no longer raises `cannot schedule new
  futures after shutdown` (`test_aio_to_thread_survives_dead_default_executor`),
  so the `task_timeout` path is reported cleanly rather than as a Player/Coach
  `error`. End-to-end confirmation comes from the next FEAT-E2CB autobuild run.
- [x] **AC-3 (reproducer + control):** `test_default_impl_crashes_without_override`
  proves the default path **does** raise on a dead executor (red), and
  `test_aio_to_thread_survives_dead_default_executor` proves the override fixes it
  (green). 4/4 new tests pass; 34 existing harness tests green.
- [x] All modified files pass lint/format (trailing-whitespace clean; no new lint).

## Notes

- The build failure was **not** a false-green: the Coach correctly returned
  `feedback` on turns 1-2 with **populated** `criteria_verification` (6/6 ACs,
  0 verified) and accurate rationales ("no implementation evidenced"; "integration
  tests could not be verified due to a missing pytest dependency" → absence-of-
  failure → feedback, not pass). The oracle behaved honestly; the harness crashed.
- Secondary finding (separate task if it recurs): the worktree venv bootstrap had
  a **missing pytest dependency** on early turns (Coach could not run independent
  tests turns 1-2; they passed by turn 3 in 4.4s) — a bootstrap timing / interpreter-
  pinning gap worth its own investigation if it reproduces.
