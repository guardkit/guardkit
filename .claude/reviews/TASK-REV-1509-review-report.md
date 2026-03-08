# Review Report: TASK-REV-1509 (Revised)

## Executive Summary

vLLM Run 2 on Dell ProMax GB10 completed 6/7 tasks (vs 6/7 in Run 1), taking **4h 42m** — a **60% regression** from Run 1's 2h 58m. The VPT-001 changes (`max_parallel=1`, `sdk_max_turns=75`, `timeout_multiplier=3.0`) successfully eliminated the parallel throughput penalty but introduced new problems: SDK turn ceiling hits (33% of invocations) and insufficient timeout budget for complex tasks. TASK-FBP-007 failed in both runs.

**Graphiti Root Cause (REVISED)**: This is a **code bug**, not an environment issue. FalkorDB is running on the Synology NAS "whitestocks" and is correctly configured in the vllm-profiling project's `.guardkit/graphiti.yaml`. The bug is an **execution order defect** in `feature_orchestrator.py:1195`: `_preflight_check()` calls `get_factory()` (which does NOT trigger lazy initialization) before `_pre_init_graphiti()` has a chance to call `get_graphiti()` (which DOES trigger lazy initialization). The factory is always `None` at preflight time, so context gets disabled for the entire run. The `guardkit graphiti seed` command works because it bypasses the factory pattern entirely.

The Anthropic API run completed all 7/7 tasks in **28 minutes** — a **10x speed advantage** over vLLM.

## Review Details

- **Mode**: Decision Analysis (Revised — deeper investigation)
- **Depth**: Standard → Comprehensive (revised depth)
- **Task**: TASK-REV-1509
- **Reviewer**: Opus 4.6 decision analysis
- **Revision**: R1 — corrected Graphiti root cause from "environment" to "code bug"

---

## Objective 1: Performance Impact of VPT-001 Changes

### Configuration Comparison

| Parameter | Run 1 | Run 2 | Change |
|-----------|-------|-------|--------|
| max_parallel | 2 | 1 | Reduced to eliminate GPU contention |
| sdk_max_turns | 50 | 75 | Increased for headroom |
| timeout_multiplier | 4.0x | 3.0x | Reduced |
| task_timeout | 9600s | 7200s | Reduced (consequence of lower multiplier) |

### Per-Task Duration Comparison

| Task | Run 1 Duration | Run 2 Duration | Delta | Notes |
|------|---------------|----------------|-------|-------|
| FBP-001 | 19m 23s | 16m 18s | -16% | Improved |
| FBP-002 | 34m 35s* | 38m 9s* | +10% | Run 1 parallel, Run 2 sequential |
| FBP-004 | 34m 35s* | 38m 9s* | +10% | SDK ceiling hit (78 turns) |
| FBP-003 | 9m 17s | 11m 40s | +26% | Slightly slower |
| FBP-005 | 28m 42s | 77m 23s | +170% | Major regression: 2 turns, ceiling hit |
| FBP-006 | 85m 49s* | 26m 32s | -69% | Improved (was 2 turns in Run 1) |
| FBP-007 | 85m 49s* (crashed) | 138m (budget exhausted) | +61% | Failed in both |

*Wave 2 and Wave 5 ran tasks in parallel; durations are wall-clock for the wave.

### Per-Turn Throughput

| Metric | Run 1 | Run 2 | Anthropic |
|--------|-------|-------|-----------|
| Sequential throughput | ~20-24s/turn | ~20s/turn (FBP-001) | ~5-7s/turn |
| Parallel throughput | ~87s/turn (2 tasks) | N/A (max_parallel=1) | ~5-7s/turn |
| SDK ceiling hit rate | 0/6 (0%) | 2/6 (33%) | 0/6 (0%) |
| Tasks needing >1 AutoBuild turn | 3/7 | 2/7 | 0/7 |

### Key Finding: SDK Turn Ceiling Is Now the Bottleneck

Raising `sdk_max_turns` from 50 to 75 was insufficient. Two tasks hit the ceiling:
- **FBP-004**: 78 turns (ceiling hit at 75, plus 3 overflow)
- **FBP-005**: Turn 1 hit 76 turns, Turn 2 hit 51 turns

The Qwen3 model consumes **2-3x more SDK turns** than Claude for equivalent tasks:
- FBP-001: 49 turns (vLLM) vs 47 turns (Anthropic) — comparable
- FBP-004: 78 turns (vLLM) vs 38 turns (Anthropic) — 2x more
- FBP-005: 76+51=127 turns (vLLM) vs 50 turns (Anthropic) — 2.5x more

### Verdict on VPT-001 Changes

| Change | Intended Effect | Actual Effect | Assessment |
|--------|----------------|---------------|------------|
| max_parallel=1 | Eliminate GPU contention | Eliminated 4.3x penalty | **SUCCESS** |
| sdk_max_turns=75 | Provide headroom | Still hit ceiling (33%) | **INSUFFICIENT** |
| timeout_multiplier=3.0 | Reduce from 4.0x | Reduced task_timeout to 7200s, caused FBP-007 budget exhaustion | **REGRESSION** |

**Recommendation**: Keep `max_parallel=1`. Increase `sdk_max_turns` to 100. Restore `timeout_multiplier` to 4.0x (or at minimum set `task_timeout` explicitly to 9600s).

---

## Objective 2: Graphiti Failure Root Cause (REVISED)

### The Failure

All three runs (vLLM Run 1, vLLM Run 2, Anthropic Run 2) show:
```
INFO:guardkit.orchestrator.feature_orchestrator:Graphiti factory not available or disabled, disabling context loading
⚠ Graphiti not available — context loading disabled for this run
```

### Environment Status: CONFIRMED WORKING

- FalkorDB runs on Synology NAS "whitestocks" (Tailscale hostname, DS918+)
- Config exists at `vllm-profiling/.guardkit/graphiti.yaml` with `falkordb_host: whitestocks`, `falkordb_port: 6379`
- `guardkit graphiti seed` works correctly from the same machine
- `guardkit graphiti search` works correctly
- The Graphiti seeding workflow was debugged and fixed over the past week

### Root Cause: Execution Order Bug in `_preflight_check()`

**File**: `guardkit/orchestrator/feature_orchestrator.py:1195`

The bug is a **call-order defect** between two methods in `_wave_phase()`:

```python
# feature_orchestrator.py, lines 1285-1293
def _wave_phase(self, feature, worktree):
    ...
    # Step 1: Preflight check (BROKEN — calls get_factory() which is non-lazy)
    self._preflight_check()        # ← get_factory() returns None → disables context

    # Step 2: Pre-init (CORRECT — calls get_graphiti() which IS lazy)
    self._pre_init_graphiti()      # ← but enable_context already False → returns immediately
```

**`get_factory()`** (line 2173) returns the module-level `_factory` variable directly:
```python
def get_factory() -> Optional[GraphitiClientFactory]:
    """Does NOT trigger lazy initialization — use get_graphiti() for that."""
    return _factory    # Always None if init_graphiti() never called
```

**`get_graphiti()`** (line 2146) triggers lazy initialization:
```python
def get_graphiti() -> Optional[GraphitiClient]:
    if _factory is not None:
        return _factory.get_thread_client()
    if not _factory_init_attempted:
        return _try_lazy_init()    # ← Would load config, create factory, connect
    return None
```

### C4 Sequence Diagram: Current (Broken) Flow

```
┌──────────────────┐  ┌───────────────┐  ┌────────────────────┐  ┌──────────────┐  ┌─────────────┐
│FeatureOrchestrator│  │graphiti_client│  │  _factory (module)  │  │ config.py    │  │ whitestocks │
│ (_wave_phase)     │  │   .py         │  │  = None             │  │              │  │ :6379       │
└────────┬─────────┘  └──────┬────────┘  └─────────┬──────────┘  └──────┬───────┘  └──────┬──────┘
         │                    │                      │                    │                  │
         │ 1. _preflight_check()                     │                    │                  │
         │────────────────────>                       │                    │                  │
         │                    │                       │                    │                  │
         │ 2. get_factory()   │                       │                    │                  │
         │────────────────────>                       │                    │                  │
         │                    │  3. return _factory    │                    │                  │
         │                    │<──────────────────────│                    │                  │
         │  4. returns None   │                       │                    │                  │
         │<───────────────────│                       │                    │                  │
         │                    │                       │                    │                  │
         │ 5. factory is None │                       │                    │                  │
         │    → "Graphiti factory not available"       │                    │                  │
         │    → self.enable_context = False            │                    │                  │
         │    → return False  │                       │                    │                  │
         │                    │                       │                    │                  │
         │ 6. _pre_init_graphiti()                    │                    │                  │
         │    → if not self.enable_context: return    │                    │                  │
         │    → NO-OP (context already disabled)      │                    │                  │
         │                    │                       │                    │                  │
         │ 7. All tasks run with enable_context=False  │                    │                  │
         │    → No Graphiti context loaded             │                    │                  │
         │    → No connection to whitestocks attempted │                    │                  │
         │                    │                       │                    │                  │
    ╔════╧════════════════════╧═══════════════════════╧════════════════════╧══════════════════╧══════╗
    ║ RESULT: Graphiti silently disabled. Config never read. FalkorDB never contacted.               ║
    ║ No error — graceful degradation masks the bug.                                                ║
    ╚═══════════════════════════════════════════════════════════════════════════════════════════════╝
```

### C4 Sequence Diagram: Fixed Flow (Proposed)

```
┌──────────────────┐  ┌───────────────┐  ┌────────────────────┐  ┌──────────────┐  ┌─────────────┐
│FeatureOrchestrator│  │graphiti_client│  │  _factory (module)  │  │ config.py    │  │ whitestocks │
│ (_wave_phase)     │  │   .py         │  │  = None             │  │              │  │ :6379       │
└────────┬─────────┘  └──────┬────────┘  └─────────┬──────────┘  └──────┬───────┘  └──────┬──────┘
         │                    │                      │                    │                  │
         │ 1. _preflight_check()                     │                    │                  │
         │────────────────────>                       │                    │                  │
         │                    │                       │                    │                  │
         │ 2. get_factory()   │                       │                    │                  │
         │────────────────────>                       │                    │                  │
         │  3. returns None   │                       │                    │                  │
         │<───────────────────│                       │                    │                  │
         │                    │                       │                    │                  │
         │ 4. factory is None — try lazy init         │                    │                  │
         │                    │                       │                    │                  │
         │ 5. get_graphiti()  │                       │                    │                  │
         │────────────────────>                       │                    │                  │
         │                    │ 6. _try_lazy_init()   │                    │                  │
         │                    │──────────────────────>│                    │                  │
         │                    │                       │ 7. load_dotenv()   │                  │
         │                    │                       │ 8. load_graphiti_config()             │
         │                    │                       │───────────────────>│                  │
         │                    │                       │  9. reads .guardkit/graphiti.yaml     │
         │                    │                       │  falkordb_host=whitestocks            │
         │                    │                       │  falkordb_port=6379                   │
         │                    │                       │<──────────────────│                   │
         │                    │                       │                    │                  │
         │                    │ 10. GraphitiConfig(host=whitestocks,port=6379)                │
         │                    │ 11. _factory = GraphitiClientFactory(config)                  │
         │                    │ 12. _factory.get_thread_client()                              │
         │                    │<─────────────────────│                    │                  │
         │  13. returns factory                      │                    │                  │
         │<───────────────────│                       │                    │                  │
         │                    │                       │                    │                  │
         │ 14. factory.check_connectivity()           │                    │                  │
         │──────────────────────────────────────────────────────────────────────────────────>│
         │                    │                       │                    │   15. TCP SYN    │
         │                    │                       │                    │   to :6379       │
         │                    │                       │                    │   16. SYN-ACK    │
         │<─────────────────────────────────────────────────────────────────────────────────│
         │                    │                       │                    │                  │
         │ 17. TCP check passed!                      │                    │                  │
         │    → "FalkorDB pre-flight TCP check passed"│                    │                  │
         │    → enable_context remains True            │                    │                  │
         │    → return True   │                       │                    │                  │
         │                    │                       │                    │                  │
         │ 18. _pre_init_graphiti()                   │                    │                  │
         │    → get_graphiti() → factory already exists → returns client   │                  │
         │    → "Pre-initialized Graphiti factory for parallel execution"  │                  │
         │                    │                       │                    │                  │
         │ 19. All tasks run with enable_context=True  │                    │                  │
         │    → Graphiti context loaded per task        │                    │                  │
         │                    │                       │                    │                  │
    ╔════╧════════════════════╧═══════════════════════╧════════════════════╧══════════════════╧══════╗
    ║ RESULT: Graphiti initialized from config, FalkorDB on whitestocks contacted,                  ║
    ║ context loaded for all tasks.                                                                 ║
    ╚═══════════════════════════════════════════════════════════════════════════════════════════════╝
```

### C4 Sequence Diagram: Why `guardkit graphiti seed` Works

```
┌──────────────┐  ┌────────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐
│  CLI command  │  │ cli/graphiti.py│  │ config.py    │  │GraphitiClient│  │ whitestocks │
│ $ guardkit    │  │                │  │              │  │ (direct)     │  │ :6379       │
│   graphiti    │  │                │  │              │  │              │  │             │
│   seed        │  │                │  │              │  │              │  │             │
└──────┬───────┘  └──────┬─────────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘
       │                  │                    │                  │                  │
       │ 1. seed()        │                    │                  │                  │
       │─────────────────>│                    │                  │                  │
       │                  │                    │                  │                  │
       │                  │ 2. _get_client_and_config()           │                  │
       │                  │                    │                  │                  │
       │                  │ 3. load_graphiti_config()             │                  │
       │                  │───────────────────>│                  │                  │
       │                  │  4. reads .guardkit/graphiti.yaml     │                  │
       │                  │  5. returns settings                  │                  │
       │                  │<──────────────────│                   │                  │
       │                  │                    │                  │                  │
       │                  │ 6. GraphitiClient(config)             │                  │
       │                  │  *** BYPASSES FACTORY ENTIRELY ***    │                  │
       │                  │─────────────────────────────────────>│                  │
       │                  │                    │                  │                  │
       │                  │ 7. await client.initialize()         │                  │
       │                  │─────────────────────────────────────>│                  │
       │                  │                    │                  │ 8. FalkorDriver  │
       │                  │                    │                  │    (whitestocks  │
       │                  │                    │                  │     :6379)       │
       │                  │                    │                  │────────────────>│
       │                  │                    │                  │  9. Connected!  │
       │                  │                    │                  │<───────────────│
       │                  │                    │                  │                  │
       │                  │ 10. seed_all_system_context()         │                  │
       │                  │─────────────────────────────────────>│                  │
       │                  │                    │                  │ 11. Episodes    │
       │                  │                    │                  │────────────────>│
       │                  │                    │                  │  12. Stored!    │
       │                  │                    │                  │<───────────────│
       │                  │                    │                  │                  │
    ╔══╧══════════════════╧════════════════════╧══════════════════╧══════════════════╧══════╗
    ║ RESULT: Works because it DIRECTLY constructs GraphitiClient — never touches the       ║
    ║ factory pattern, get_factory(), get_graphiti(), or any module-level state.             ║
    ╚══════════════════════════════════════════════════════════════════════════════════════╝
```

### The Divergence: Two Completely Different Init Paths

```
                        Graphiti Initialization
                    ┌────────────┴────────────┐
                    │                          │
            CLI Commands                  Autobuild
         (seed/search/capture)      (feature orchestrator)
                    │                          │
        _get_client_and_config()       _preflight_check()
                    │                          │
          load_graphiti_config()         get_factory()
          GraphitiClient(config)              │
          await client.initialize()      returns _factory
                    │                    (always None!)
                ✅ WORKS                       │
                                      "factory not available"
                                      enable_context = False
                                               │
                                      _pre_init_graphiti()
                                      → skipped (no-op)
                                               │
                                          ❌ BROKEN
```

### This Is NOT the GCW6 Issue

| Aspect | GCW6 Issue | This Issue |
|--------|-----------|------------|
| **What** | `init_graphiti()` never called | `get_factory()` called before lazy init |
| **Where** | Module-level singleton was None | Module-level `_factory` is None |
| **Fix applied** | Added lazy-init to `get_graphiti()` | N/A — never reaches `get_graphiti()` |
| **Why fix doesn't help** | N/A | `_preflight_check` calls `get_factory()` not `get_graphiti()` |
| **Root cause** | No caller invoked init | Correct caller exists (`_pre_init_graphiti`) but runs AFTER preflight already disabled context |

### The Fix (3 options, any one is sufficient)

**Option A (Minimal — recommended)**: In `_preflight_check()`, if `get_factory()` returns None, try lazy init before concluding unavailable:

```python
# feature_orchestrator.py, _preflight_check(), line 1195
factory = get_factory()
if factory is None:
    # Trigger lazy init before concluding unavailable
    from guardkit.knowledge.graphiti_client import get_graphiti
    get_graphiti()  # triggers _try_lazy_init() → sets _factory
    factory = get_factory()  # retry after lazy init

if factory is None or not factory.config.enabled:
    # NOW we can legitimately conclude it's unavailable
    ...
```

**Option B (Swap call order)**: Move `_pre_init_graphiti()` before `_preflight_check()` in `_wave_phase()`. This ensures `get_graphiti()` (lazy-init) runs first, populating `_factory` before `get_factory()` reads it. Requires adjusting `_pre_init_graphiti()` to not short-circuit on `enable_context`.

**Option C (Replace get_factory)**: Change `_preflight_check()` to use `get_graphiti()` instead of `get_factory()`. This is the most direct fix but changes the non-lazy intent of the preflight check (the comment says it was intentionally non-lazy to avoid Lock contamination — but that concern was resolved by GLF-003/005).

---

## Objective 3: Anthropic vs vLLM Run 2 Comparison

### High-Level Comparison

| Metric | vLLM Run 2 | Anthropic Run 2 | Delta |
|--------|-----------|-----------------|-------|
| **Total duration** | 4h 42m | 28m | **10x slower** |
| **Tasks completed** | 6/7 (86%) | 7/7 (100%) | -14% |
| **Final status** | FAILED | SUCCESS | |
| **AutoBuild turns (total)** | 11 | 7 | +57% |
| **First-pass approval rate** | 5/7 (71%) | 7/7 (100%) | -29% |
| **SDK ceiling hits** | 2/6 (33%) | 0/6 (0%) | +33% |
| **State recoveries** | 1 | 1 | Same |
| **Graphiti available** | No | No | Same (same bug) |

### Per-Task Comparison

| Task | vLLM Duration | vLLM Turns | Anthropic Duration | Anthropic Turns | vLLM/Anthropic Ratio |
|------|--------------|------------|-------------------|----------------|---------------------|
| FBP-001 | 16m 18s | 1 (49 SDK) | 4m 21s | 1 (47 SDK) | 3.7x |
| FBP-002 | 8m* | 1 (33 SDK) | 3m 16s | 1 (37 SDK) | 2.4x |
| FBP-004 | 30m* | 1 (78 SDK) | 4m 3s | 1 (38 SDK) | 7.4x |
| FBP-003 | 11m 40s | 1 (28 SDK) | 4m 53s | 1 (41 SDK) | 2.4x |
| FBP-005 | 77m 23s | 2 (76+51 SDK) | 5m 21s | 1 (50 SDK) | 14.4x |
| FBP-006 | 26m 32s | 1 (52 SDK) | 6m 7s | 1 (37 SDK) | 4.3x |
| FBP-007 | FAILED | 4 (all cancelled) | 8m 31s (recovered) | 1 | N/A |

### Quality Comparison

| Quality Metric | vLLM (Qwen3) | Anthropic (Claude) |
|---------------|-------------|-------------------|
| Code generation per SDK turn | ~20s | ~5-7s |
| Tool use density | Similar | Similar |
| Coach approval on first try | 71% | 100% |
| FBP-007 completion | Failed (4 turns, all cancelled) | Succeeded (recovered from cancel) |
| Tests passing at submission | Variable | Consistent |

### Key Insight: FBP-007 Divergence

Both runs experienced a `CancelledError` on TASK-FBP-007. The difference:
- **Anthropic**: Player produced enough valid work before cancellation that Coach approved 9/9 criteria from recovered state
- **vLLM**: Player produced partial work across 4 cancellation cycles, with criteria progressively degrading (89% → 44%), ultimately exhausting the timeout budget

This suggests Qwen3 needs more time to produce complete, coherent output for complex configuration tasks.

---

## Objective 4: Graphiti Integration Gap Analysis (REVISED)

### Fix Chain Summary (Chronological)

| Fix | Date | What It Fixed | Status |
|-----|------|--------------|--------|
| GC-72AF | Pre-Feb | Migrate to graphiti-core library | Completed |
| GCW1-5 | 2026-02-08 | Wire context pipeline end-to-end | Completed |
| REV-0E58 | 2026-02-08 | Verify GCW1-5, identify startup gap | Completed |
| GCW6 | 2026-02-08 | Lazy-init for get_graphiti() | Completed |
| GCI0 | 2026-02-08 | Fix 3 bugs from GCW6 lazy-init | Completed |
| GTP1 | 2026-02-09 | Thread-safe factory (threading.local) | Completed |
| GLF-001 | 2026-02-16 | enable_context guard in _capture_turn_state | Completed |
| GLF-002 | 2026-02-16 | Shutdown cleanup noise | Completed |
| GLF-003 | 2026-02-16 | Defer init to consumer's event loop | Completed |
| GLF-004 | 2026-02-16 | Direct-mode synthetic report | Completed |
| GLF-005 | 2026-02-16 | Lightweight health ping (no Lock creation) | Completed |
| **NEW** | TBD | Fix `_preflight_check()` lazy-init ordering | **NOT DONE** |

### Revised Assessment: One Remaining Code Bug

The 11 completed fixes addressed all issues EXCEPT the call-order defect:

```
Layer 1: Pipeline not wired (GCW1-5) → Fixed
Layer 2: Singleton never initialized (GCW6) → Fixed
Layer 3: Async/sync mismatch (GCI0) → Fixed
Layer 4: Thread safety (GTP1) → Fixed
Layer 5: Event loop contamination (GLF-001-005) → Fixed
Layer 6: _preflight_check() bypasses lazy-init → NOT FIXED ← THIS IS THE BUG
```

The GLF-005 fix inadvertently introduced this regression: when `_check_health()` was replaced with `check_connectivity()`, the method was moved to `GraphitiClientFactory` (requiring a factory instance). The preflight was changed to call `get_factory()` to obtain the factory instance, but `get_factory()` was explicitly designed as non-lazy (its docstring says: "Does NOT trigger lazy initialization — use get_graphiti() for that"). At the time, this seemed correct because GLF-003/005 wanted to avoid creating asyncio objects at preflight. But the side effect is that the factory is never populated.

### Why CLI Commands Work But Autobuild Doesn't

| Aspect | CLI (`guardkit graphiti seed/search`) | Autobuild (`guardkit autobuild feature`) |
|--------|--------------------------------------|------------------------------------------|
| **Init method** | `_get_client_and_config()` — direct construction | `get_factory()` → module-level `_factory` |
| **Uses factory?** | No — creates fresh `GraphitiClient(config)` | Yes — requires `_factory` to be set |
| **Loads config?** | Yes — `load_graphiti_config()` explicitly | Never reaches config loading |
| **Connects to FalkorDB?** | Yes — `await client.initialize()` | Never attempts connection |
| **Result** | Works | Silent failure, context disabled |

### Specific Fix Recommendation

**Create task**: Fix `_preflight_check()` to trigger lazy initialization when factory is None.

**Exact change** (Option A — minimal, ~5 lines):

```python
# feature_orchestrator.py:1194-1196, in _preflight_check()
from guardkit.knowledge.graphiti_client import get_factory
factory = get_factory()
+ if factory is None:
+     from guardkit.knowledge.graphiti_client import get_graphiti
+     get_graphiti()  # Trigger lazy-init
+     factory = get_factory()  # Retry
if factory is None or not factory.config.enabled:
```

**Risk**: Low. `get_graphiti()` → `_try_lazy_init()` is synchronous, creates the factory from config without starting any async operations or creating event loops. The `get_thread_client()` call inside `_try_lazy_init()` creates a thread client stub with `pending_init=True` (per GLF-003), so no Lock contamination occurs.

**Test plan**:
1. Unit test: Mock `get_factory()` returning None, verify `get_graphiti()` is called
2. Unit test: After lazy init, verify `get_factory()` returns valid factory
3. Integration test: Run `guardkit autobuild feature` with FalkorDB on whitestocks, verify "FalkorDB pre-flight TCP check passed" appears
4. Regression test: Verify no asyncio Lock contamination (GLF-003/005 concern)

---

## Decision Matrix (REVISED)

| Option | Impact | Effort | Risk | Recommendation |
|--------|--------|--------|------|----------------|
| **A: Fix `_preflight_check()` lazy-init** | **Critical** | **Very Low (5 lines)** | Low | **P0 — Fix immediately** |
| B: Fix VPT-001 params (sdk_max_turns=100, timeout_multiplier=4.0) | Medium | Low | Low | **P0 — Fix for Run 3** |
| C: Investigate FBP-007 failure pattern | Medium | Medium | Low | P2 — Defer |
| D: Add automated preflight checks command | Medium | Medium | Low | P2 — Defer |

### Recommended Actions for Run 3

**P0 (Must do before Run 3)**:
1. **Fix `_preflight_check()` lazy-init ordering** — the 5-line code fix above
2. Set `sdk_max_turns=100` (from 75)
3. Set `timeout_multiplier=4.0` (restore from 3.0) or explicitly set `task_timeout=9600`
4. Keep `max_parallel=1`

**P1 (Should do)**:
5. Verify FalkorDB on whitestocks is accessible from GB10: `redis-cli -h whitestocks -p 6379 ping`
6. After fix, verify log shows "FalkorDB pre-flight TCP check passed" instead of "Graphiti factory not available"
7. Monitor Graphiti context loading in task logs

**P2 (Nice to have)**:
8. Investigate FBP-007 failure pattern (is it fundamentally too complex for Qwen3?)

---

## Updated Pre-Run Checklist for Run 3

```
□ 1. Code Fix (P0)
  □ Apply _preflight_check() lazy-init fix (feature_orchestrator.py:1194)
  □ Run unit tests for the fix
  □ pip install -e . (reinstall guardkit)

□ 2. Configuration
  □ max_parallel=1
  □ sdk_max_turns=100
  □ timeout_multiplier=4.0 (or task_timeout=9600)
  □ max_turns=30

□ 3. FalkorDB / Graphiti (on whitestocks NAS)
  □ FalkorDB container running: ssh whitestocks "docker ps | grep falkor"
  □ Reachable from GB10: redis-cli -h whitestocks -p 6379 ping → PONG
  □ Graphiti config in target project: cat <project>/.guardkit/graphiti.yaml
  □ End-to-end test: cd <project> && guardkit graphiti search "test"
  □ After fix: look for "FalkorDB pre-flight TCP check passed" in logs

□ 4. vLLM Backend
  □ vLLM server running on http://localhost:8000
  □ Model loaded (Qwen3-Coder-Next-FP8)
  □ Test: curl http://localhost:8000/v1/models → returns model info

□ 5. Environment
  □ ANTHROPIC_BASE_URL=http://localhost:8000
  □ ANTHROPIC_API_KEY=vllm-local
  □ File descriptor limit raised (ulimit -n 4096)

□ 6. Run Command
  guardkit autobuild feature FEAT-XXXX --max-turns 30 --verbose
```

---

## Appendix A: Raw Timing Data

### vLLM Run 2 Wave Timeline

```
12:23:01 ┬─ Wave 1: FBP-001 ────────────── 12:39:19 (16m)
         │
12:39:19 ┬─ Wave 2: FBP-002, FBP-004 ───── 13:17:28 (38m)
         │
13:17:28 ┬─ Wave 3: FBP-003 ────────────── 13:29:08 (12m)
         │
13:29:08 ┬─ Wave 4: FBP-005 ────────────── 14:46:30 (77m)
         │
14:46:30 ┬─ Wave 5: FBP-006 ──── 15:13:02 (27m) ✓
         └─ Wave 5: FBP-007 ──── 17:04:36 (138m) ✗ budget exhausted
```

### Anthropic Run 2 Wave Timeline

```
12:23:25 ┬─ Wave 1: FBP-001 ── 12:27:47 (4m)
         │
12:27:48 ┬─ Wave 2: FBP-002, FBP-004 ── 12:32:00 (4m)
         │
12:32:00 ┬─ Wave 3: FBP-003 ── 12:37:00 (5m)
         │
12:37:00 ┬─ Wave 4: FBP-005 ── 12:42:30 (5m)
         │
12:42:30 ┬─ Wave 5: FBP-006, FBP-007 ── 12:51:03 (9m)
```

## Appendix B: Code References

| File | Lines | What |
|------|-------|------|
| `guardkit/orchestrator/feature_orchestrator.py` | 1172-1233 | `_preflight_check()` — the bug location |
| `guardkit/orchestrator/feature_orchestrator.py` | 1235-1257 | `_pre_init_graphiti()` — correct but runs too late |
| `guardkit/orchestrator/feature_orchestrator.py` | 1285-1293 | `_wave_phase()` — call order: preflight then pre-init |
| `guardkit/knowledge/graphiti_client.py` | 2173-2182 | `get_factory()` — non-lazy, returns `_factory` directly |
| `guardkit/knowledge/graphiti_client.py` | 2146-2170 | `get_graphiti()` — lazy, triggers `_try_lazy_init()` |
| `guardkit/knowledge/graphiti_client.py` | 2089-2143 | `_try_lazy_init()` — loads config, creates factory |
| `guardkit/knowledge/graphiti_client.py` | 1998-2035 | `check_connectivity()` — TCP ping to FalkorDB |
| `guardkit/cli/graphiti.py` | 72-97 | `_get_client_and_config()` — direct client creation (CLI) |
| `guardkit/knowledge/config.py` | 202-249 | `get_config_path()` — config file resolution |
| `vllm-profiling/.guardkit/graphiti.yaml` | — | Config with `falkordb_host: whitestocks` |
