# Prefer a narrow `sys.unraisablehook` over a teardown refactor for cosmetic async-GC noise

> **Source**: Seeded by TASK-FIX-FALK01 (commit `83b0d1a6d`, 2026-06-05).
> The task file is
> [`tasks/completed/2026-06/TASK-FIX-FALK01-graphiti-falkordb-teardown-race.md`](../../tasks/completed/2026-06/TASK-FIX-FALK01-graphiti-falkordb-teardown-race.md).

## The rule

When an orphaned async coroutine outlives the event loop it was scheduled on and
CPython garbage-collects it at process exit, producing a **cosmetic** traceback
(`Exception ignored while closing generator` → `RuntimeError("no running event
loop")`), the remediation is a **narrow, filtered `sys.unraisablehook`** — not a
restructuring of the orchestrator's teardown plumbing to await the pending
operation before the loop closes.

The `sys.unraisablehook` must be:

1. **Narrowly filtered** — match on BOTH the exact exception string AND the
   garbage-collected coroutine's source-file provenance, so it cannot mask any
   unrelated unraisable error.
2. **Idempotent** — installed at most once per process via a module-level
   sentinel, so any entry path that installs it is safe.
3. **Delegating** — every non-matching unraisable is handed to the
   previously-installed hook, preserving default behaviour.

Reach for the teardown refactor ONLY if the noise is masking a real teardown bug
(i.e. the orphaned coroutine's non-completion has a side effect on the run
outcome). For pure cosmetic exit-time noise from an upstream async library, that
refactor is a larger surface with more failure modes and no offsetting benefit.

## Why this rule exists

TASK-HMIG-010 run 3 (2026-06-05) surfaced this traceback at process exit, after
the feature orchestrator had already rendered its final summary:

```
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: no running event loop
...
File ".../asyncio/timeouts.py", line 159, in timeout
    loop = events.get_running_loop()
RuntimeError: no running event loop
```

Root cause (AC-001): graphiti-core's `edge_fulltext_search` (fanned out via an
internal `asyncio.gather`) stayed pending when the autobuild orchestrator's
**thread-local** event loop closed. The considered alternative — making
`_cancel_pending_background_tasks` await the pending task before loop close —
does not work here: the autobuild path can close on a **fresh `asyncio.run()`
loop** (`_cleanup_thread_loaders`), so `asyncio.all_tasks()` returns zero pending
tasks from the *original* loop. By the time CPython GCs the orphaned coroutine,
the original loop is unrecoverable. `sys.unraisablehook` is the correct hook for
the "Exception ignored while closing generator" surface — the loop-level
`call_exception_handler` cannot fire because the loop is already gone.

The fix landed as two layers of defence:

- **Loop-level** — `_suppress_httpx_cleanup_errors`
  ([`guardkit/knowledge/graphiti_client.py:2141`](../../guardkit/knowledge/graphiti_client.py))
  now recognises a third harmless `RuntimeError` string via
  `_is_no_running_loop_error` (`:2210`), alongside the pre-existing
  `"Event loop is closed"` (httpx) and Redis `"buffer is closed"` branches.
- **GC-time** — `_install_graphiti_unraisable_hook`
  ([`graphiti_client.py:2277`](../../guardkit/knowledge/graphiti_client.py))
  installs a process-wide `sys.unraisablehook` whose predicate
  `_is_graphiti_unraisable` (`:2233`) suppresses ONLY when the exception is
  `RuntimeError("no running event loop")` AND the GC'd coroutine's
  `co_filename` matches one of `graphiti_core`, `falkordb`, `redis/asyncio`,
  `asyncio/timeouts` (with Windows-separator variants). Idempotency is guarded by
  the module-level sentinel `_unraisable_hook_installed` (`:2230`). It is wired
  into `AutoBuildOrchestrator.__init__`
  ([`guardkit/orchestrator/autobuild.py:1231`](../../guardkit/orchestrator/autobuild.py),
  imported at `:153`) right after the `max_turns` validation, so every
  orchestrator entry path covers the process lifetime.

The design deliberately mirrors the existing `_suppress_httpx_cleanup_errors`
convention — cosmetic shutdown noise from upstream async libraries is an
established, filtered-suppression pattern in this codebase, not a new one.

## Symptom

- A `RuntimeError: no running event loop` (or `Exception ignored while closing
  generator <coroutine object ...>`) traceback appears at **process exit**,
  after the run's final summary, with no effect on any task verdict.
- The originating coroutine lives in an upstream async DB/driver library
  (`graphiti_core`, `falkordb`, `redis.asyncio`), not in GuardKit's own code —
  every `await` in GuardKit is honoured (AC-001).
- The orchestrator closed on a fresh `asyncio.run()` loop, so the pending task
  is invisible to `asyncio.all_tasks()` on the loop the cleanup code controls.

## Detection recipe

```bash
# 1. The two suppression layers must both exist.
rg -n "_install_graphiti_unraisable_hook|_is_graphiti_unraisable|_is_no_running_loop_error" \
   guardkit/knowledge/graphiti_client.py

# 2. The loop-level handler must recognise the "no running event loop" string.
rg -n "no running event loop|Event loop is closed|buffer is closed" \
   guardkit/knowledge/graphiti_client.py

# 3. The hook must be installed idempotently at an orchestrator entry point.
rg -n "_install_graphiti_unraisable_hook|_unraisable_hook_installed" \
   guardkit/orchestrator/autobuild.py guardkit/knowledge/graphiti_client.py

# 4. The narrow source-filename marker tuple (extend here if the coroutine moves).
rg -n "graphiti_core|falkordb|redis/asyncio|asyncio/timeouts" \
   guardkit/knowledge/graphiti_client.py
```

## Remediation

1. **Extend the filter, don't re-architect.** If the traceback re-appears, the
   most likely cause is the orphaned coroutine's source filename moving outside
   the four-marker tuple in `_is_graphiti_unraisable` (e.g. graphiti-core
   relocates `edge_fulltext_search`). The remediation is a one-line tuple
   extension, not a teardown rewrite.
2. **Keep the filter narrow.** Match on the exact `RuntimeError` string AND the
   coroutine's `co_filename` provenance. A broad hook that swallows any
   unraisable would mask real teardown bugs — the exact thing this cosmetic-fix
   posture is only justified because AC-002 ruled out.
3. **Keep it idempotent and delegating.** Guard install with the module-level
   sentinel; hand every non-matching unraisable to the previously-installed hook.
4. **Only refactor teardown if the noise masks a real bug.** If the pending
   coroutine's non-completion has an observable side effect on the run outcome,
   the suppression is wrong and structured cleanup (thread the per-task loop
   reference through `_cleanup_thread_loaders`) is warranted. Absent that, prefer
   the hook.

## Grep-able signature (for next agent)

```bash
# Suppression-present fingerprint (MUST MATCH; absence = the fix regressed).
rg -n "def _install_graphiti_unraisable_hook" guardkit/knowledge/graphiti_client.py   # -> 2277
rg -n "def _is_graphiti_unraisable"           guardkit/knowledge/graphiti_client.py   # -> 2233
rg -n "_install_graphiti_unraisable_hook\(\)" guardkit/orchestrator/autobuild.py      # -> 1231

# Regression test fingerprint.
rg -n "TestGraphitiUnraisableHook|test_suppresses_graphiti_unraisable" \
   tests/knowledge/test_graphiti_client_factory.py                                    # -> 948, 997
```

## When this rule triggers

- Before restructuring orchestrator teardown / event-loop cleanup to chase a
  cosmetic exit-time async traceback from an upstream library.
- Before adding a new upstream async dependency (DB driver, HTTP client) whose
  connection-pool teardown may outlive the orchestrator's thread-local loop.
- During any diagnostic session investigating a process-exit `no running event
  loop` / `Exception ignored while closing generator` traceback that has no
  effect on the run outcome.

## What it does NOT cover

- **Teardown races that affect the run outcome.** If the orphaned coroutine's
  non-completion drops data or corrupts state, suppression is wrong — fix the
  teardown ordering instead.
- **Broadly matching unraisable errors.** Only the narrow `RuntimeError("no
  running event loop")` + graphiti/FalkorDB/redis/asyncio-timeouts provenance is
  in scope; all other unraisable exceptions must continue to reach stderr.
- **Non-async-GC noise.** This is specifically for coroutines garbage-collected
  after their loop closes. Synchronous shutdown errors are a different surface.

## Related

- **Loop-level sibling convention**: `_suppress_httpx_cleanup_errors`
  ([`graphiti_client.py:2141`](../../guardkit/knowledge/graphiti_client.py)) —
  the established filtered-suppression pattern this fix extends.
- **Regression coverage**:
  [`tests/knowledge/test_graphiti_client_factory.py`](../../tests/knowledge/test_graphiti_client_factory.py)
  `TestGraphitiUnraisableHook` (`:948`), including
  `test_suppresses_graphiti_unraisable` (`:997`) which synthesises the exact
  run-3 `UnraisableHookArgs` stack frame.
- **Loop-substrate context**: the same thread-local vs fresh-`asyncio.run()` loop
  asymmetry underlies
  [`harness-cancellation-contract.md`](harness-cancellation-contract.md) (the
  four-layer autobuild event-loop / cancellation taxonomy).
