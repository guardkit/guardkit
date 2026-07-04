# Retro: AutoBuild changed a class signature + its tests but not the production call sites

**Date:** 2026-07-04
**Feature / task:** study-tutor `FEAT-SMP-003` (durable session CRUD, W3) — `TASK-SMP3-06` (MCP adapter cutover)
**Tool:** `guardkit autobuild feature` (SDK harness, `GUARDKIT_HARNESS=sdk`)
**Severity:** High (a **production entrypoint crash** — `serve` died on startup — shipped Coach-approved; caught only in the operator's independent on-main verification, pre-merge)
**Status:** Resolved (two-line `cli/main.py` fix by hand before merge)
**Tags:** autobuild, guardkit, coach, api-signature, call-sites, dependency-injection, smoke-gate, boot-latency
**Related:** [Coach missed an undefined BDD step](./2026-07-04-autobuild-coach-missed-undefined-bdd-step.md); the sibling study-tutor retros (`study-tutor/docs/retros/`): [self-defeating boundary tests](../../../study-tutor/docs/retros/2026-07-03-autobuild-self-defeating-boundary-tests.md), [parallel-wave worktree pollution](../../../study-tutor/docs/retros/2026-07-03-autobuild-parallel-wave-worktree-pollution.md).

## Summary

`TASK-SMP3-06` cut the MCP adapter over from an in-memory session store to the durable `SessionService`. It correctly changed `MCPAdapter.__init__` — dropping `store` / `write_helper` / `graphiti_client`, adding `session_service` — and updated the **unit** test that builds the adapter. But it **left the two PRODUCTION call sites** in `cli/main.py` (`serve` and `_build_nats_runtime`) still passing the retired kwargs:

```python
# cli/main.py serve() — unchanged by the cutover, now wrong:
adapter = MCPAdapter(
    role_config=role_config,
    orchestrator_factory=orchestrator_factory,
    write_helper=write_helper,      # <- removed from __init__
    event_bus=event_bus,
    graphiti_client=wrapper,        # <- removed from __init__
)
```

Result: **`serve` — the actual MCP server entrypoint — raised `TypeError: MCPAdapter.__init__() got an unexpected keyword argument 'write_helper'` on startup.** The task was Coach-approved and the feature reported 7/7 green. It surfaced only when the operator ran the full suite on the merged `main` tree, where the `serve`-boot smoke test finally tripped.

Fix: update both call sites to `session_service=get_session_service()` and drop the retired kwargs (the `write_helper` / `wrapper` locals stay — they are still used for the shutdown drain + logging). Two lines of intent, plus one import.

## Root cause

Two compounding gaps:

1. **The signature change didn't sweep its call sites.** The Player updated the class and the unit test that *directly instantiates it* (`tests/unit/mcp/test_adapter.py`), but not the production wiring. Crucially, that unit test **injects `SessionService` itself and never boots through `cli/main.py`** (`grep -c 'cli.main' test_adapter.py` → 0) — so a green `test_adapter.py` gives **false confidence about production wiring**. An injected-dependency unit test validates the *class contract*, never the *call sites*. The Coach's per-task gate (task-specific tests + `pytest tests/unit`) is built from exactly those, so nothing in scope constructed the adapter the way production does.

2. **The one test that DOES boot the real entrypoint has a startup-window design that MASKED the late crash.** `tests/unit/mcp/test_stdio_discipline.py::test_serve_writes_zero_bytes_to_stdout_during_idle_startup` subprocess-launches `serve`, waits `STARTUP_WINDOW_SECONDS = 3.0`, then terminates it — and **accepts `rc in (0, -15, None)`**, where `-15` is its own `SIGTERM`. The crash is at `main.py:385`, *after* an async Graphiti healthcheck at `main.py:371` (`asyncio.run(get_client(config))`). In the autobuild **worktree** (no `.env`, Graphiti/FalkorDB unreachable) that healthcheck almost certainly **blocked past the 3-second window**, so `serve` never reached line 385 → the test SIGTERM'd a still-"starting" process → `rc=-15` → **pass**. On `main` (with `.env`/DSN, deps resolving fast) `serve` reached line 385 within the window → `TypeError` → `rc=1` → **fail**. The bug is unconditional; whether the smoke test *observes* it depends on boot latency of an unrelated dependency. (The worktree was cleaned up post-merge, so this timing is inferred — but it is the only explanation consistent with a no-`skipif`, always-run test passing in one env and failing in the other on identical code.)

## Evidence

```
# operator independent run, on main, DSN present:
FAILED tests/unit/mcp/test_stdio_discipline.py::test_serve_writes_zero_bytes_to_stdout_during_idle_startup
  AssertionError: serve exited with unexpected rc=1. stderr-tail=
    '...cli/main.py", line 385, in serve\n    adapter = MCPAdapter(\n'
    'TypeError: MCPAdapter.__init__() got an unexpected keyword argument 'write_helper''

# the new signature (post-cutover):
MCPAdapter.__init__(self, role_config, session_service=None, orchestrator_factory=None, event_bus=None)

# the Coach's unit gate never boots via main.py:
$ grep -c 'cli.main' tests/unit/mcp/test_adapter.py
0
```

The autobuild worktree's `pytest tests/unit` reported `1049 passed, 3 skipped, 0 failed` — `test_stdio_discipline` has **no `skipif`**, so it ran-and-passed (or was one of the 3 "skipped" via an early spawn bail); either way it did not block. On main the identical file gave `1 failed`.

## Impact

High in principle — a Coach-approved feature whose **server would not start**. Caught pre-merge because the operator's verification (per the prior retros) runs the whole suite on the *merged main tree with `.env` present*, not just the worktree. Cost: a two-line hand-fix. Had the merge trusted Coach-green (or run only the worktree, DSN-less), `serve` would have been dead on `main`.

This is a distinct failure class from the sibling retros: not a stale test (self-defeating), not an undefined BDD step, but a **real production defect the test suite structurally could not catch in the Coach's environment** — the injected-dependency unit tests bypass the call sites, and the one entrypoint-boot test was masked by dependency latency.

## Resolution

```python
# cli/main.py, both serve() and _build_nats_runtime():
from study_tutor.session.provider import get_session_service
...
adapter = MCPAdapter(
    role_config=role_config,
    session_service=get_session_service(),
    orchestrator_factory=orchestrator_factory,
    event_bus=event_bus,
)
```

Re-verified: `serve` boots byte-clean (`test_stdio_discipline` passes), full unit `1049 passed`, full `tests/` minus the 3 pre-existing NATS-smoke `1252 passed / 0 errors`. No product logic changed beyond the two call sites. Merged as study-tutor `main` @ `ea7c135`.

## Prevention / action items

- [ ] **A task that changes a shared class/function signature MUST sweep every call site.** Add to the Player protocol (and a Coach check) for `refactor`/`feature` tasks that touch a public `__init__`/signature: `grep` the repo for the old kwarg names and fail if any remain. "Updated the class + its unit test" is necessary, not sufficient.
- [ ] **Injected-dependency unit tests do not validate production wiring.** When the Coach's evidence is a unit test that *constructs the changed component with hand-injected deps*, it should NOT be treated as coverage of the `cli/main.py` (or equivalent) call sites. Flag tasks whose only adapter/entrypoint coverage bypasses the real boot path.
- [ ] **The entrypoint-boot smoke must assert READY, not merely "quiet for N seconds".** `test_stdio_discipline` accepting `SIGTERM (-15)` as success means a *hang* reads as a pass. A boot-smoke should wait for a positive readiness signal (handshake / log line / port) and fail on timeout — otherwise slow-dependency latency silently moves a startup crash outside the observation window.
- [ ] **Run a production-representative boot before merge.** The worktree's missing `.env` + unreachable Graphiti changed boot timing enough to hide the crash. The final wave (or the independent verification) should boot the real entrypoint in an environment with the production config present.
- [ ] **Operator practice reaffirmed:** independent full-suite verification on the *merged* tree (with real config) before merge — the same conclusion as every retro in this family, and the only reason this one didn't reach `main`.

## Links

- Merged feature: study-tutor `main` @ `ea7c135` (squash of `autobuild/FEAT-SMP-003`, incl. the two-line `cli/main.py` fix).
- Sibling retros: the undefined-BDD-step retro (guardkit), self-defeating boundary tests + parallel-wave pollution (study-tutor). Together they map the "Coach-green but not mergeable" surface for autobuild features: stale tests, undefined steps, call-site drift.
