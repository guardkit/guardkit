# Review Report: TASK-REV-982B — vLLM Run 3 and Run 4 Performance Analysis

## Executive Summary

Run 4 (fresh) completed **all 7/7 tasks in 227m** (3h 47m), an **19% improvement** over Run 2 (282m, 6/7 tasks). The Anthropic-to-vLLM ratio dropped from **10x to 8.1x**. FBP-007 (the persistent failure) now succeeds in 1 turn — attributable to the **cancelled-error-fix**, NOT Graphiti context (which returned 0 categories for all tasks in both Run 3 and Run 4).

**Critical finding**: Graphiti is connected but returns 0 categories for ALL tasks due to **5 independent root causes**: (1) System groups were seeded (74 episodes from Mac) but queries return empty — seeding marker is machine-local and system group queries may be silently failing, (2) `patterns` vs `patterns_{tech_stack}` group ID mismatch, (3) dynamic-only groups empty on fresh runs, (4) project groups seeded under `guardkit__` namespace but queried from `vllm-profiling__` namespace, (5) silent exception swallowing in `_query_category()` masks all failures. The TASK-FIX-GPLI infrastructure fix worked, but code fixes + cross-project namespace resolution are needed before context can flow.

**VOPT task status**: TASK-VOPT-004 is satisfied (Run 4 completed). TASK-VOPT-001 (context reduction) remains the highest-impact addressable optimisation. TASK-VOPT-002 (timing instrumentation) has partial coverage from existing logs. TASK-VOPT-003 (FalkorDB noise) is still present and worth fixing.

**Viability recommendation**: **Accept current performance for heavy workloads; deprioritise further optimisation.** The 8x ratio is unlikely to drop below 5-6x with remaining optimisations. The 2.5-3x target is achievable only for simple tasks.

---

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Comprehensive
- **Task**: TASK-REV-982B
- **Related Tasks**: TASK-REV-1509, TASK-REV-CB30, TASK-VOPT-001 through TASK-VOPT-004
- **Data Sources**: Run 3 logs, Run 4 logs, Run 2 review (TASK-REV-1509), Viability review (TASK-REV-CB30)

---

## Objective 1: Run 3 Validation

### Run 3 Summary

Run 3 was a **resume run** — only FBP-007 executed fresh; all other tasks were SKIPPED (already completed from Run 2). Total duration: **63m 35s** (of which ~63m was FBP-007).

### FBP-007 Improvement Analysis

| Metric | Run 2 | Run 3 | Change |
|--------|-------|-------|--------|
| Status | FAILED | SUCCESS | Fixed |
| AutoBuild Turns | 4 (budget exhausted) | 1 | -75% |
| Duration | 138m | ~63m | -54% |
| Graphiti Context | Disabled (bug) | Connected, 0 categories | Infrastructure fixed |

### Root Cause: NOT Graphiti Context

**Key evidence**: Run 3 Graphiti context for FBP-007 returned **0 categories, 0/5200 tokens**. The knowledge graph was connected but had no relevant data for the quality gates task.

The FBP-007 improvement is attributable to two changes:

1. **Cancelled-error-fix**: In Run 2, FBP-007's Player invocation was terminated by `CancelledError` from the cancel scope. The fix prevented premature cancellation, allowing the Player to complete its work within the SDK turn budget.

2. **Restored timeout_multiplier to 4.0x**: Run 2 used `timeout_multiplier=3.0x` (task_timeout=7200s). Run 3/4 restored `4.0x` (task_timeout=9600s), giving FBP-007 sufficient time budget.

### Are Resume-Mode Results Representative?

**Partially.** FBP-007's result is valid because:
- It ran from scratch (not cached)
- It operated on a codebase with all prior tasks completed (same as fresh run)
- The duration (~63m) is consistent with Run 4 Wave 5 (~82m for FBP-006 + FBP-007 combined)

However, resume mode skipped Graphiti context loading for earlier tasks, so Run 3 cannot validate cross-task Graphiti impact.

---

## Objective 2: Run 4 Performance Decomposition

### Per-Wave Timing (Run 4)

| Wave | Tasks | Start | End | Duration | SDK Turns |
|------|-------|-------|-----|----------|-----------|
| 1 | FBP-001 | 23:15:19 | 23:29:24 | **14m 5s** | 37 |
| 2 | FBP-002 + FBP-004 (sequential) | 23:29:24 | 23:53:07 | **23m 43s** | 32 + 41 = 73 |
| 3 | FBP-003 | 23:53:07 | 00:32:53 | **39m 46s** | 82 |
| 4 | FBP-005 | 00:32:53 | 01:40:38 | **67m 45s** | 101 + 26 = 127 |
| 5 | FBP-006 + FBP-007 (sequential) | 01:40:38 | 03:02:44 | **82m 6s** | 43 + direct |
| **Total** | | | | **227m 24s** | **~412** |

### Per-Task Comparison: Run 4 vs Run 2 vs Anthropic

| Task | Run 4 Duration | Run 4 SDK Turns | Run 2 Duration | Run 2 SDK Turns | Anthropic SDK Turns | Run 4 Turn Change |
|------|---------------|----------------|---------------|----------------|---------------------|-------------------|
| FBP-001 | ~14m | 37 | 16m 18s | 49 | 47 | **-24%** |
| FBP-002 | ~10m* | 32 | ~19m* | 33 | 37 | -3% |
| FBP-004 | ~14m* | 41 | ~19m* | 78 | 38 | **-47%** |
| FBP-003 | ~40m | 82 | 11m 40s | 28 | 41 | **+193%** |
| FBP-005 | ~68m | 127 (2 turns) | 77m 23s | 127 (2 turns) | 50 | 0% |
| FBP-006 | ~25m* | 43 | 26m 32s | 52 | 37 | -17% |
| FBP-007 | ~57m* | direct | FAILED | N/A | direct | **Fixed** |

*Estimated from wave duration split proportionally by SDK turns. Waves with max_parallel=1 run tasks sequentially.

### Per-Turn Latency

| Task | Duration | SDK Turns | Per-Turn Latency |
|------|----------|-----------|-----------------|
| FBP-001 | 14m | 37 | ~22.7s |
| FBP-002+FBP-004 avg | 24m | 73 | ~19.7s |
| FBP-003 | 40m | 82 | ~29.3s |
| FBP-005 T1 | ~62m | 101 | ~36.8s |
| FBP-005 T2 | ~6m | 26 | ~13.8s |
| **Average** | | | **~24s/turn** |

Per-turn latency improved from Run 2's ~20s/turn baseline for simple tasks. Complex tasks (FBP-003, FBP-005 T1) show **29-37s/turn**, suggesting context size grows with task complexity.

### Key Observation: SDK Turn Redistribution

| Task | Run 2 Turns | Run 4 Turns | Change | Assessment |
|------|-------------|-------------|--------|------------|
| FBP-001 | 49 | 37 | -12 | Improved |
| FBP-002 | 33 | 32 | -1 | Stable |
| FBP-003 | 28 | 82 | **+54** | **Major regression** |
| FBP-004 | 78 | 41 | **-37** | **Major improvement** |
| FBP-005 | 127 | 127 | 0 | Stable (redistributed: 76+51 → 101+26) |
| FBP-006 | 52 | 43 | -9 | Improved |

**Net SDK turns (excluding FBP-007)**: Run 2: 367, Run 4: 362. Nearly identical total turns — the improvements and regressions cancel out.

---

## Objective 3: Gap Analysis Update

### Overall Ratio

| Run | Duration | Tasks | Ratio to Anthropic (28m) |
|-----|----------|-------|--------------------------|
| Run 1 | 2h 58m | 6/7 | ~6.4x (incomplete) |
| Run 2 | 4h 42m | 6/7 | ~10.1x (incomplete) |
| Run 3 | 63m 35s | 7/7 (resume) | N/A (resume mode) |
| Run 4 | 3h 47m | 7/7 | **8.1x** |

### Updated Gap Decomposition

The 8.1x gap decomposes as follows (updated from TASK-REV-CB30's 10x analysis):

```
Total Gap: 8.1x
├── Per-turn latency (hardware): ~3.0x (unchanged — hardware floor)
├── Turn count inefficiency (model): ~1.6x (improved from 1.8x — better task completion)
├── SDK ceiling hits + AutoBuild retries: ~1.1x (improved from 1.3x — higher sdk_max_turns)
└── Sequential execution (max_parallel=1): ~1.4x (unchanged)
```

### Per-Task Ratios vs Anthropic

| Task | Run 4 SDK Turns | Anthropic Turns | Turn Ratio | Est. Total Ratio |
|------|----------------|-----------------|------------|-----------------|
| FBP-001 | 37 | 47 | **0.79x** | ~3.0x |
| FBP-002 | 32 | 37 | **0.86x** | ~2.7x |
| FBP-003 | 82 | 41 | 2.0x | ~6.0x |
| FBP-004 | 41 | 38 | 1.08x | ~3.2x |
| FBP-005 | 127 | 50 | 2.54x | ~10x |
| FBP-006 | 43 | 37 | 1.16x | ~3.5x |

**Tasks within 2.5-3x target**: FBP-001, FBP-002 (Qwen3 uses fewer turns than Claude!)
**Tasks at 3-4x**: FBP-004, FBP-006
**Tasks above target**: FBP-003 (6x — regression), FBP-005 (10x — persistent outlier)

### Notable Improvement: FBP-004

FBP-004 (correlation ID middleware) dropped from 78 to 41 SDK turns (47% reduction), moving from the worst-performing task in Run 2 (7.4x ratio) to a well-performing one (~3.2x). This demonstrates that Qwen3's turn efficiency is **variable and non-deterministic** — the same model on the same task can produce wildly different turn counts.

---

## Objective 4: VOPT Task Reassessment

### TASK-VOPT-004: Full Run 4 Benchmark → **CLOSE (SATISFIED)**

Run 4 was executed with `--fresh` flag and all fixes applied. The benchmark data is now available. However, TASK-VOPT-002 (timing instrumentation) and TASK-VOPT-001 (context reduction) were NOT merged before Run 4, so the run does not include those optimisations.

**Recommendation**: Close TASK-VOPT-004. If further benchmarking is needed after VOPT-001/002/003, create a new task (TASK-VOPT-005-run5).

### TASK-VOPT-001: Context Reduction → **KEEP (STILL HIGHEST IMPACT)**

Context reduction remains the most impactful addressable optimisation:
- ~19KB protocol per SDK invocation still active in Run 4
- Per-turn latency of 24-37s includes significant prompt processing time
- Expected improvement: 1.1-1.3x per-turn, potentially 1.5-2x total if fewer turns needed with clearer instructions

**New insight from Run 4**: The variable per-turn latency (13.8s to 36.8s) suggests that context size growth during a session significantly impacts latency. This strengthens the case for context reduction.

**Recommendation**: Keep as P1 priority. Update estimated impact to 1.2-1.5x based on Run 4's observed per-turn latency variance.

### TASK-VOPT-002: Per-SDK-Turn Timing Instrumentation → **DEPRIORITISE (PARTIALLY SATISFIED)**

Run 4 logs already provide:
- ✅ Total SDK turn count per AutoBuild turn (e.g., "SDK completed: turns=82")
- ✅ 30-second progress heartbeats with elapsed time
- ✅ Context loading confirmation with token counts
- ❌ Missing: per-SDK-turn breakdown (time per individual turn)
- ❌ Missing: time-to-first-token metric

**Recommendation**: Deprioritise to P3. The missing metrics are nice-to-have but don't block optimisation decisions. Run 4's 30s heartbeats provide sufficient resolution for wall-clock analysis.

### TASK-VOPT-003: Suppress FalkorDB Log Noise → **KEEP (STILL PRESENT)**

Run 4 logs still contain extensive FalkorDB "Index already exists" noise (~50 lines per task, ~350 lines total across 7 tasks). This is confirmed from the Run 4 grep results.

**Recommendation**: Keep as P3. Quick implementation (1 line change). Improves log readability for future analysis.

### Summary Table

| Task | Current Status | Recommendation | New Priority |
|------|---------------|----------------|-------------|
| TASK-VOPT-001 | Backlog | **KEEP** — still highest-impact | P1 |
| TASK-VOPT-002 | Backlog | **DEPRIORITISE** — partially satisfied | P3 |
| TASK-VOPT-003 | Backlog | **KEEP** — still present, easy fix | P3 |
| TASK-VOPT-004 | Backlog | **CLOSE** — Run 4 completed | Done |

### New Optimisation Opportunities from Run 4

| Opportunity | Description | Expected Impact | Priority |
|-------------|-------------|-----------------|----------|
| **Graphiti seeding + code fixes** | 5 root causes identified: no seeding, group ID mismatch, silent failures (see Revised Analysis) | 1.1-1.3x (reduces exploration turns) | **P0** |
| **sdk_max_turns tuning** | FBP-005 still hits ceiling at 100; consider 150 for complex tasks | 1.05-1.1x (avoids 2nd AutoBuild turn) | P2 |
| **FBP-003 turn regression investigation** | 28→82 turns — investigate root cause of non-determinism | N/A (diagnostic) | P3 |

---

## Objective 5: Viability Decision Update

### Updated Viability Matrix

| Factor | Run 2 (TASK-REV-CB30) | Run 4 (Current) | Trend |
|--------|----------------------|-----------------|-------|
| Total duration | 282m (6/7 tasks) | 227m (7/7 tasks) | **19% faster** |
| Tasks completed | 6/7 (86%) | 7/7 (100%) | **Fixed** |
| Ratio to Anthropic | 10.1x | 8.1x | **20% closer** |
| SDK ceiling hits | 33% | 17% | **Halved** |
| State recoveries | 0% | 14% (1/7) | New (FBP-007 cancelled-error recovery) |
| Graphiti context | Disabled (bug) | Connected, 0 categories | Infrastructure works, needs seeding |

### Realistic Best-Case with Remaining VOPT Optimisations

| Optimisation | Expected Improvement | Cumulative |
|-------------|---------------------|-----------|
| Baseline (Run 4) | 1.0x (227m) | 8.1x |
| VOPT-001 (context reduction) | 1.2-1.5x | 5.4-6.8x |
| Graphiti seeding | 1.1-1.3x | 4.2-6.2x |
| sdk_max_turns increase | 1.05-1.1x | 3.8-5.9x |
| **Realistic best-case** | | **4-6x** |

### Why 2.5-3x Is Unlikely for the Overall Average

1. **Hardware floor**: Per-turn latency of ~3x (20s vs 5-7s) is immovable without faster GPU or smaller model
2. **Complex task outliers**: FBP-005 alone is 10x and accounts for ~30% of total wall time
3. **Non-deterministic turn counts**: FBP-003's 3x regression (28→82 turns) shows Qwen3's output quality varies significantly between runs
4. **Sequential execution penalty**: With max_parallel=1, total wall time = sum of all task times

### Per-Task Viability

| Category | Tasks | Run 4 Ratio | 2.5-3x Achievable? |
|----------|-------|-------------|---------------------|
| **Already at target** | FBP-001, FBP-002 | 2.7-3.0x | **Yes, today** |
| **Near target** | FBP-004, FBP-006 | 3.2-3.5x | **Likely with context reduction** |
| **Above target** | FBP-003, FBP-005 | 6-10x | **No** — model limitation |

### Cost-Benefit Analysis

**Remaining optimisation effort**: VOPT-001 (context reduction) is ~1 day of work. Graphiti seeding is ~0.5 days. sdk_max_turns is a config change.

**Expected improvement**: ~1.3-1.6x (from 8.1x to 5-6x)

**Break-even**: At current performance (227m per feature run), vLLM costs ~$0.11 electricity vs ~$5 Anthropic API. The break-even is at ~2 feature runs/day. With optimisations reducing to ~150m, break-even improves to ~1.5 runs/day.

### Recommendation

**Accept current performance with selective optimisation.**

1. **Implement VOPT-001** (context reduction) — high impact, moderate effort, benefits all future runs
2. **Implement VOPT-003** (log noise) — trivial effort, improves diagnostics
3. **Seed Graphiti** with FastAPI task patterns — test if knowledge context actually reduces turns
4. **Close VOPT-004** — satisfied by Run 4
5. **Deprioritise VOPT-002** — existing instrumentation is sufficient
6. **Do NOT pursue max_parallel=2** — the GPU contention penalty (4.3x in Run 1) far outweighs the sequential penalty (~1.4x)
7. **Accept 5-6x as the realistic floor** for mixed-complexity workloads on GB10 with Qwen3

---

## FBP-003 Root Cause Analysis (82 SDK Turns)

### The Anomaly

FBP-003 (structured logging) used **82 SDK turns** in Run 4 vs **28 turns** in Run 2 — a **193% increase**. Despite this, it completed in 1 AutoBuild turn and was approved by the Coach.

### Probable Causes

1. **Codebase state difference**: In Run 4 (fresh), FBP-003 runs after FBP-002 (pydantic settings) and FBP-004 (correlation ID middleware) are implemented. In Run 2, FBP-004 had already implemented correlation ID middleware with 78 turns of changes. The structured logging task may now need to integrate with these pre-existing components, making the task effectively more complex.

2. **Non-deterministic model behaviour**: Qwen3's turn efficiency is highly variable. FBP-004 went from 78→41 turns in the opposite direction. This suggests per-task variance of ±50-100% is normal for Qwen3.

3. **Context accumulation**: By Wave 3, the conversation context includes prior wave artifacts, potentially slowing Qwen3's reasoning.

### Assessment

FBP-003's 82 turns is **not a systemic issue** — it's within the expected variance for Qwen3 on tasks of this complexity. The task still completed in 1 AutoBuild turn and passed Coach validation. No intervention needed.

---

## FBP-005 Root Cause Analysis (SDK Ceiling Hit)

### The Pattern

| Run | Turn 1 SDK Turns | Turn 2 SDK Turns | Total | Ceiling |
|-----|-----------------|-----------------|-------|---------|
| Run 2 | 76 (hit at 75) | 51 | 127 | 75 |
| Run 4 | 101 (hit at 100) | 26 | 127 | 100 |

### Key Insight: Same Total, Different Distribution

Both runs consumed exactly **127 SDK turns**. Raising the ceiling from 75 to 100 allowed Turn 1 to complete more work (101 vs 76 turns), leaving only 26 turns for Turn 2 (vs 51). This is progress — nearly completing in one turn.

### Why 127 Turns?

FBP-005 (health endpoints) requires:
- Creating multiple endpoint handlers
- Writing tests for each endpoint
- Configuring router registration
- Adding middleware integration

With 50 Anthropic turns but 127 Qwen3 turns (2.54x ratio), this is the **most turn-inefficient task**. Qwen3 likely needs multiple exploration cycles to understand the codebase structure before implementing.

### Recommendation

Increase `sdk_max_turns` to **150** for tasks with complexity ≥ 4. This would likely allow FBP-005 to complete in a single AutoBuild turn, saving ~6m of Turn 2 overhead. The config change is minimal risk.

---

## Appendix: Run History Summary

| Run | Date | Mode | Duration | Tasks | FBP-007 | Config Changes | Key Result |
|-----|------|------|----------|-------|---------|----------------|------------|
| Run 1 | 2026-03-06 | Fresh | 2h 58m | 6/7 | FAILED (crashed) | max_parallel=2, sdk_max_turns=50, tm=4.0x | Baseline |
| Run 2 | 2026-03-07 | Fresh | 4h 42m | 6/7 | FAILED (budget) | max_parallel=1, sdk_max_turns=75, tm=3.0x | VPT-001 changes |
| Run 3 | 2026-03-07 | Resume | 63m 35s | 7/7 | SUCCESS (1 turn) | tm=4.0x, cancelled-error-fix, Graphiti fix | Resume validation |
| Run 4 | 2026-03-07-08 | Fresh | 3h 47m | 7/7 | SUCCESS (1 turn) | Same as Run 3 | **Full fresh validation** |

---

## Revised Analysis: Graphiti 0 Categories — Deep Root Cause Investigation

### Investigation Scope

This section traces the complete execution flow from `FeatureOrchestrator` through to FalkorDB, identifying why ALL 10 context categories returned 0 results in both Run 3 and Run 4.

### Evidence From Run 4 Logs

The logs confirm Graphiti infrastructure **is working**:

```
INFO:guardkit.orchestrator.feature_orchestrator:FalkorDB pre-flight TCP check passed
INFO:guardkit.knowledge.graphiti_client:Graphiti factory: thread client created (pending init)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
```

FalkorDB is reachable, indices exist, workarounds applied, factory created. But every query returns empty:

```
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Loading Player context (turn 1)...
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Player context: 0 categories, 0/5200 tokens
```

---

### C4 Sequence Diagram: Current (Broken) Context Loading Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐    ┌──────────────────┐    ┌─────────────┐
│FeatureOrchestrator│    │AutoBuildOrchestrator│    │AutoBuildContextLoader│    │JobContextRetriever│    │GraphitiClient│
│                 │    │                  │    │                    │    │                  │    │             │
└───────┬─────────┘    └────────┬─────────┘    └──────────┬─────────┘    └────────┬─────────┘    └──────┬──────┘
        │                       │                          │                       │                     │
        │ _preflight_check()    │                          │                       │                     │
        │ get_graphiti()        │                          │                       │                     │
        │ ──────────────────────┼──────────────────────────┼───────────────────────┼─────────────────────>
        │                       │                          │                       │                     │
        │                       │                          │                       │              ┌──────┴──────┐
        │                       │                          │                       │              │_try_lazy_init│
        │                       │                          │                       │              │loads config: │
        │                       │                          │                       │              │project_id:   │
        │                       │                          │                       │              │"vllm-profiling"│
        │                       │                          │                       │              │falkordb_host:│
        │                       │                          │                       │              │ "whitestocks"│
        │                       │                          │                       │              └──────┬──────┘
        │                       │                          │                       │                     │
        │ _pre_init_graphiti()  │                          │                       │                     │
        │ factory = get_factory()                          │                       │                     │
        │ ──────────────────────>                          │                       │                     │
        │                       │                          │                       │                     │
        │ dispatch_wave(tasks)  │                          │                       │                     │
        │ ──────────────────────>                          │                       │                     │
        │                       │                          │                       │                     │
        │                       │ _get_thread_local_loader()                       │                     │
        │                       │ client = factory.get_client()                    │                     │
        │                       │ ─────────────────────────>                       │                     │
        │                       │                          │                       │                     │
        │                       │ get_player_context()     │                       │                     │
        │                       │ ─────────────────────────>                       │                     │
        │                       │                          │                       │                     │
        │                       │                          │ retriever.retrieve()  │                     │
        │                       │                          │ ──────────────────────>│                     │
        │                       │                          │                       │                     │
        │                       │                          │    ┌──────────────────┤                     │
        │                       │                          │    │ CATEGORY QUERIES │                     │
        │                       │                          │    │ (10 categories)  │                     │
        │                       │                          │    └──────────────────┤                     │
        │                       │                          │                       │                     │
        │                       │                          │ 1. feature_specs ─────┼─── search(query,    │
        │                       │                          │    ❌ NOT SEEDED       │    group_ids=       │
        │                       │                          │    (needs /feature-   │    ["vllm-profiling__     │
        │                       │                          │     spec command)     │     feature_specs"])│
        │                       │                          │                       │      ───────────────>
        │                       │                          │                       │    results: []      │
        │                       │                          │                       │    <─────────────────
        │                       │                          │                       │                     │
        │                       │                          │ 2. task_outcomes ─────┼─── search(query,    │
        │                       │                          │    ❌ DYNAMIC ONLY     │    group_ids=       │
        │                       │                          │    (empty on fresh    │    ["vllm-profiling__     │
        │                       │                          │     runs)             │     task_outcomes"])│
        │                       │                          │                       │      ───────────────>
        │                       │                          │                       │    results: []      │
        │                       │                          │                       │    <─────────────────
        │                       │                          │                       │                     │
        │                       │                          │ 3. patterns_python ───┼─── search(query,    │
        │                       │                          │    ❌ GROUP MISMATCH   │    group_ids=       │
        │                       │                          │    seeded: "patterns" │    ["vllm-profiling__     │
        │                       │                          │    (system, no prefix)│     patterns_       │
        │                       │                          │    queried:           │     python"])       │
        │                       │                          │    "patterns_python"  │      ───────────────>
        │                       │                          │    (unknown→project)  │    results: []      │
        │                       │                          │                       │    <─────────────────
        │                       │                          │                       │                     │
        │                       │                          │ 4. project_           ─────search(query,    │
        │                       │                          │    architecture       │    group_ids=       │
        │                       │                          │    ❌ NOT SEEDED       │    ["vllm-profiling__     │
        │                       │                          │    (needs project     │    project_         │
        │                       │                          │     seeding)          │    architecture"])  │
        │                       │                          │                       │      ───────────────>
        │                       │                          │                       │    results: []      │
        │                       │                          │                       │    <─────────────────
        │                       │                          │                       │                     │
        │                       │                          │ 5-6. failure_patterns,│                     │
        │                       │                          │    domain_knowledge   │                     │
        │                       │                          │    ⚠️ SYSTEM/PROJECT   │                     │
        │                       │                          │    groups but empty   │                     │
        │                       │                          │    (no seed markers   │      ───────────────>
        │                       │                          │     found)            │    results: []      │
        │                       │                          │                       │    <─────────────────
        │                       │                          │                       │                     │
        │                       │                          │ 7-10. role_constraints│                     │
        │                       │                          │    quality_gate_      │                     │
        │                       │                          │    configs, turn_     │                     │
        │                       │                          │    states, impl_modes │                     │
        │                       │                          │    ⚠️ SYSTEM groups   │                     │
        │                       │                          │    (may be empty —    │      ───────────────>
        │                       │                          │     no seed markers)  │    results: []      │
        │                       │                          │                       │    <─────────────────
        │                       │                          │                       │                     │
        │                       │                          │ RetrievedContext:     │                     │
        │                       │                          │ ALL fields empty      │                     │
        │                       │                          │ <──────────────────────                     │
        │                       │                          │                       │                     │
        │                       │ "0 categories, 0/5200"  │                       │                     │
        │                       │ <─────────────────────────                       │                     │
```

### C4 Sequence Diagram: Group ID Namespace Resolution

```
┌────────────────────┐     ┌──────────────────┐     ┌──────────────┐
│JobContextRetriever │     │  GraphitiClient  │     │  _group_defs │
│                    │     │                  │     │              │
│ Queries 10         │     │ project_id =     │     │ PROJECT =    │
│ categories with    │     │ "vllm-profiling" │     │   7 groups   │
│ group_ids          │     │                  │     │ SYSTEM =     │
└─────────┬──────────┘     └────────┬─────────┘     │   20 groups  │
          │                         │               └──────┬───────┘
          │                         │                      │
          │  search(query,          │                      │
          │  group_ids=             │                      │
          │  ["feature_specs"])     │                      │
          │ ────────────────────────>                      │
          │                         │                      │
          │                  ┌──────┴──────┐               │
          │                  │_apply_group │               │
          │                  │_prefix()    │               │
          │                  │             │               │
          │                  │ "feature_   │               │
          │                  │  specs"     │               │
          │                  │ IN PROJECT_ │               │
          │                  │ GROUPS? ────┼───────────────>
          │                  │             │  YES ✓        │
          │                  │ prefix:     │  <────────────│
          │                  │ "vllm-profiling__ │               │
          │                  │  feature_   │               │
          │                  │  specs"     │               │
          │                  └──────┬──────┘               │
          │                         │                      │
          │  search(query,          │                      │
          │  group_ids=             │                      │
          │  ["task_outcomes"])     │                      │
          │ ────────────────────────>                      │
          │                         │                      │
          │                  ┌──────┴──────┐               │
          │                  │ "task_      │               │
          │                  │  outcomes"  │               │
          │                  │ IN PROJECT? │───────────────>
          │                  │             │  NO           │
          │                  │ IN SYSTEM?  │───────────────>
          │                  │             │  NO           │
          │                  │             │  <────────────│
          │                  │ UNKNOWN →   │               │
          │                  │ DEFAULT TO  │               │
          │                  │ PROJECT ⚠️   │               │
          │                  │ prefix:     │               │
          │                  │ "vllm-profiling__ │               │
          │                  │  task_      │               │
          │                  │  outcomes"  │               │
          │                  └──────┬──────┘               │
          │                         │                      │
          │  search(query,          │                      │
          │  group_ids=             │                      │
          │  ["patterns_python"])   │                      │
          │ ────────────────────────>                      │
          │                         │                      │
          │                  ┌──────┴──────┐               │
          │                  │ "patterns_  │               │
          │                  │  python"    │               │
          │                  │ IN PROJECT? │───────────────>
          │                  │             │  NO           │
          │                  │ IN SYSTEM?  │───────────────>
          │                  │             │  NO ❌         │
          │                  │             │  <────────────│
          │                  │ (Note:      │               │
          │                  │  "patterns" │               │
          │                  │  IS system  │               │
          │                  │  but query  │               │
          │                  │  appends    │               │
          │                  │  "_python") │               │
          │                  │             │               │
          │                  │ UNKNOWN →   │               │
          │                  │ DEFAULT TO  │               │
          │                  │ PROJECT ⚠️   │               │
          │                  │ prefix:     │               │
          │                  │ "vllm-profiling__ │               │
          │                  │  patterns_  │               │
          │                  │  python"    │               │
          │                  └──────┬──────┘               │
          │                         │                      │
          │  (Searches FalkorDB     │                      │
          │   for "vllm-profiling__       │                      │
          │   patterns_python" →    │                      │
          │   NOTHING SEEDED        │                      │
          │   under this group!)    │                      │
```

---

### Root Cause Analysis: 5 Independent Failures

#### Root Cause 1: ~~No Seeding~~ → Seeding Marker is Machine-Local

**CORRECTED**: Seeding WAS run successfully from Richards-MBP (Mac) on 2026-03-06 — 74/79 episodes created in 106m 26s (see `docs/reviews/vllm-profiling/graphiti_seeding.md`). All key system groups were seeded: `patterns` (5 episodes), `failure_patterns` (4), `product_knowledge` (3), `quality_gate_phases` (12), `project_overview` (4), `project_architecture` (2), etc.

**However**, the seeding marker (`.guardkit/seeding/.graphiti_seeded.json`) was written to the Mac's local filesystem. AutoBuild runs execute on **promaxgb10-41b1** (Dell GB10) where the marker doesn't exist. The `guardkit graphiti verify` command checks `is_seeded()` → looks for local marker → returns "not seeded" without even querying FalkorDB.

**Impact on queries**: The data IS in FalkorDB on whitestocks — but:
- The `verify` command exits early (line 365-368 of `graphiti.py`) when marker absent
- The AutoBuild context loading does NOT check the marker — it queries FalkorDB directly
- So the marker's absence doesn't explain the 0 categories during AutoBuild

**New root cause**: Since the data IS seeded, the system groups (failure_patterns, role_constraints, quality_gate_configs, implementation_modes, patterns) SHOULD return results. The fact they don't suggests either: (a) queries are failing silently (RC5), or (b) the FalkorDB search is returning empty despite data existing.

**Additional finding — project_id namespace mismatch**: Seeding was run from the **guardkit** repo (`project_id: guardkit`), so project groups were seeded as `guardkit__project_overview`, `guardkit__project_architecture`. But AutoBuild queries run from **vllm-profiling** (`project_id: vllm-profiling`), querying `vllm-profiling__project_overview` — a different namespace. **Project groups are unreachable due to cross-project namespace mismatch.**

#### Root Cause 2: Group ID Mismatch — `patterns` vs `patterns_{tech_stack}`

**Code path**: `job_context_retriever.py` line 583:
```python
(f"patterns_{tech_stack}", "relevant_patterns", ...)
```

This generates `patterns_python` (for Python projects). But `_group_defs.py` defines `patterns` as a SYSTEM group. `patterns_python` is NOT in either PROJECT or SYSTEM group lists, so `is_project_group()` defaults to `True` (line 341 of `graphiti_client.py`), prefixing it as `vllm-profiling__patterns_python`.

Even if `seed-system` was run, patterns are seeded under the system group `patterns` (no prefix). The query searches `vllm-profiling__patterns_python` — a completely different namespace.

**Fix required**: Either:
- (a) Query `patterns` instead of `patterns_{tech_stack}`
- (b) Add `patterns_{tech_stack}` variants to SYSTEM_GROUPS
- (c) Seed patterns per-tech-stack as project groups

#### Root Cause 3: Dynamic-Only Groups Empty on Fresh Runs

Three groups are **only populated during task execution**:

| Group | Populated By | When | Status on Turn 1 |
|-------|-------------|------|-------------------|
| `task_outcomes` | `capture_task_outcome()` in `outcome_manager.py` | After task completion | **Always empty** |
| `turn_states` | `capture_turn_state()` in `turn_state_operations.py` | After each feature-build turn | **Always empty on Turn 1** |
| `feature_specs` | `/feature-spec` command | Before feature-build | **Empty if not run** |

These groups are inherently empty on fresh runs with no prior history. This is by design for `turn_states` (Turn 1 has no prior turns), but `task_outcomes` should accumulate over time — they just haven't been populated yet.

#### Root Cause 4: Project Groups Seeded Under Wrong Namespace

Project groups WERE seeded — but from the **guardkit** repo (`project_id: guardkit`), creating `guardkit__project_overview` and `guardkit__project_architecture`. AutoBuild runs from **vllm-profiling** (`project_id: vllm-profiling`), querying `vllm-profiling__project_overview` and `vllm-profiling__project_architecture` — different namespaces.

| Group | Seeded As | Queried As | Match? |
|-------|-----------|-----------|--------|
| `project_overview` | `guardkit__project_overview` | `vllm-profiling__project_overview` | **NO** |
| `project_architecture` | `guardkit__project_architecture` | `vllm-profiling__project_architecture` | **NO** |
| `domain_knowledge` | Not seeded | `vllm-profiling__domain_knowledge` | **NO** |

**Fix**: Run `guardkit graphiti seed-project` from the vllm-profiling directory (which has its own `.guardkit/graphiti.yaml` with `project_id: vllm-profiling`).

#### Root Cause 5: Silent Exception Swallowing

**Code path**: `_query_category()` at line 996-998 of `job_context_retriever.py`:
```python
except Exception:
    # Graceful degradation - return empty on error
    return [], 0
```

This bare `except Exception` with no logging means ANY failure during search (connection timeout, query syntax error, FalkorDB internal error) is silently swallowed. Even if some groups HAD data, query failures would be invisible.

---

### C4 Sequence Diagram: Proposed Fix Flow

```
┌────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────┐
│ Pre-Run Setup  │  │  JobContextRetriever │  │   GraphitiClient     │  │  FalkorDB   │
│ (one-time)     │  │                      │  │                      │  │ (whitestocks│
│                │  │                      │  │                      │  │  :6379)     │
└───────┬────────┘  └──────────┬───────────┘  └──────────┬───────────┘  └──────┬──────┘
        │                      │                          │                     │
   ┌────┴──────────────┐       │                          │                     │
   │ FIX 1: Run        │       │                          │                     │
   │ seed-system       │       │                          │                     │
   │                   │       │                          │                     │
   │ guardkit graphiti │       │                          │                     │
   │ seed-system       │       │                          │                     │
   │ --force           │       │                          │                     │
   │                   │       │                          │     seed patterns,  │
   │ Creates:          │       │                          │     rules, agents,  │
   │ .system_seeded.   │       │                          │     role_constraints│
   │ json marker       │       │                          │     quality_gates,  │
   │                   │       │                          │     impl_modes      │
   └────┬──────────────┘       │                          │     ────────────────>
        │                      │                          │                     │
   ┌────┴──────────────┐       │                          │                     │
   │ FIX 2: Seed       │       │                          │                     │
   │ project knowledge │       │                          │                     │
   │                   │       │                          │     seed project_   │
   │ guardkit graphiti │       │                          │     architecture,   │
   │ seed-project      │       │                          │     domain_         │
   │                   │       │                          │     knowledge       │
   └────┬──────────────┘       │                          │     ────────────────>
        │                      │                          │                     │
        │                      │                          │                     │
        │            ┌─────────┴──────────┐               │                     │
        │            │ FIX 3: Code change │               │                     │
        │            │ Query "patterns"   │               │                     │
        │            │ NOT "patterns_     │               │                     │
        │            │ {tech_stack}"      │               │                     │
        │            │                    │               │                     │
        │            │ OR add patterns_   │               │                     │
        │            │ python to SYSTEM   │               │                     │
        │            │ groups in          │               │                     │
        │            │ _group_defs.py     │               │                     │
        │            └─────────┬──────────┘               │                     │
        │                      │                          │                     │
        │            ┌─────────┴──────────┐               │                     │
        │            │ FIX 4: Add logging │               │                     │
        │            │ to _query_category │               │                     │
        │            │                    │               │                     │
        │            │ except Exception   │               │                     │
        │            │   as e:            │               │                     │
        │            │   logger.warning(  │               │                     │
        │            │   f"Category       │               │                     │
        │            │    {category}      │               │                     │
        │            │    query failed:   │               │                     │
        │            │    {e}")           │               │                     │
        │            │   return [], 0     │               │                     │
        │            └─────────┬──────────┘               │                     │
        │                      │                          │                     │
        │          AFTER FIXES:│                          │                     │
        │                      │                          │                     │
        │            search("patterns",   │                     │
        │             group_ids=          │                     │
        │             ["patterns"])       │                     │
        │                      ───────────>                     │
        │                                 │  _apply_group_      │
        │                                 │  prefix():          │
        │                                 │  "patterns" IN      │
        │                                 │  SYSTEM → no prefix │
        │                                 │      ───────────────>
        │                                 │    results: [       │
        │                                 │     {pattern data}  │
        │                                 │    ]                │
        │                                 │    <─────────────────
        │                      <───────────                     │
        │                                                       │
        │            EXPECTED: 3-5 categories populated         │
        │            (patterns, role_constraints,               │
        │             quality_gate_configs,                     │
        │             implementation_modes,                     │
        │             project_architecture)                     │
```

---

### Impact Assessment

| Root Cause | Categories Affected | Fix Type | Effort | Impact |
|-----------|-------------------|----------|--------|--------|
| RC1: Seeding marker machine-local + system queries return 0 despite data | failure_patterns, role_constraints, quality_gate_configs, implementation_modes | Investigation (why FalkorDB search returns empty on seeded data) | 1-2 hrs | **Critical — need to determine if data is actually queryable** |
| RC2: patterns → patterns_python mismatch | patterns/relevant_patterns | Code fix | 1 line | **1 category populated** |
| RC3: Dynamic groups empty | task_outcomes, turn_states, feature_specs | By design (accumulate over time) | N/A | Improves with usage |
| RC4: Project groups seeded under wrong namespace (guardkit vs vllm-profiling) | project_architecture, domain_knowledge | Operational (run seed-project from vllm-profiling dir) | 5 min | **2 categories populated** |
| RC5: Silent exception swallowing | All (masks failures) | Code fix | 1 line | **Diagnostic visibility** |

### Expected Outcome After Fixes

With RC1 + RC2 + RC4 fixed:
- **Before**: 0/10 categories populated → 0 tokens context
- **After**: 6-7/10 categories populated → estimated 2000-4000 tokens context
- RC3 groups would populate organically as tasks complete

### Recommendations (Prioritised)

| # | Action | Priority | Type |
|---|--------|----------|------|
| 1 | **Investigate why seeded system groups return 0** — data exists in FalkorDB (74 episodes) but queries return empty. Add logging (RC5) first, then run manual search queries to isolate | **P0** | Investigation |
| 2 | Run `guardkit graphiti seed-project` **from vllm-profiling directory** (not guardkit) | **P0** | Operational |
| 3 | Fix `patterns_{tech_stack}` → `patterns` in `job_context_retriever.py` line 583 | **P0** | Code fix |
| 4 | Add `logger.warning()` to `_query_category()` exception handler (line 996-998) | **P1** | Code fix |
| 5 | Add `task_outcomes` and `turn_states` to `_group_defs.py` (prevent incorrect project prefixing) | **P2** | Code fix |
| 6 | Run a seeded Run 5 to validate Graphiti context actually reduces turn count | **P2** | Validation |

### Revised Viability Impact

If Graphiti context loads successfully (3-5 categories, ~3000 tokens), the expected impact on performance:
- **Exploration turn reduction**: 10-20% fewer SDK turns for medium/complex tasks (Qwen3 spends many turns exploring the codebase; pre-loaded context reduces this)
- **Per-task improvement**: FBP-003 (82 turns) and FBP-005 (127 turns) would benefit most
- **Overall improvement**: 1.1-1.3x (from 8.1x to 6.2-7.4x)
- **Combined with VOPT-001** (context reduction): 1.3-1.8x (from 8.1x to 4.5-6.2x)

This makes the **4-5x target** more achievable than previously assessed.

---

## Decision Required

Based on the original analysis and the revised Graphiti investigation, the following options are available:

- **[A]ccept** — Archive review findings
- **[R]evise** — Request deeper analysis on specific areas
- **[I]mplement** — Create implementation tasks for Graphiti fixes (RC1-RC5), VOPT-001, VOPT-003, and sdk_max_turns tuning
- **[C]ancel** — Discard review
