# Review Report: TASK-REV-7972

## Executive Summary

FEAT-FP-002 (Two-Phase Feature Plan Enhancements) completed successfully: 11/11 tasks approved on turn 1, 45m 16s total, 100% clean execution across 5 waves. **No hangs, no timeouts, no stalls, no task failures.** The FD limit fix (TASK-FIX-FD01), per-thread Graphiti clients (TASK-FIX-GTP1/GTP2), and defensive task timeouts (TASK-FIX-GTP4) are all validated in production.

However, **two systemic AutoBuild issues from TASK-REV-6F11 persist unchanged**:

1. **Zero acceptance criteria verified** — All 11 tasks show `Criteria: 0 verified, 0 rejected, 1 pending`. Coach approves based on quality gates alone.
2. **Zero tests detected across all 11 tasks** — Every Player summary shows `0 tests`. One task (TASK-FP002-002) triggered the zero-test anomaly warning.

These are **not regressions** — they are pre-existing systemic gaps in the AutoBuild Coach validation pipeline. The infrastructure fixes from FEAT-6EDD are working correctly.

**Overall Assessment: PASS** — No blocking issues. Two known systemic gaps documented below.

---

## Review Details

- **Mode**: AutoBuild Execution Quality Review
- **Depth**: Standard (targeted log analysis + pattern comparison)
- **Feature**: FEAT-FP-002 — Two-Phase Feature Plan Enhancements
- **Branch**: `autobuild/FEAT-FP-002`
- **Worktree**: `.guardkit/worktrees/FEAT-FP-002`
- **Execution**: 11/11 tasks completed, 11 turns, 45m 16s, 100% clean
- **Prior Review**: TASK-REV-6F11 (FEAT-SC-001, found 2 critical bugs + systemic issues)

---

## AC1: Quality Gate Legitimacy — All 11 Tasks

| Task | Type | Quality Gates | ALL_PASSED | Tests Required | Tests Found | Coverage Required | Anomaly |
|------|------|--------------|------------|----------------|-------------|-------------------|---------|
| FP002-001 | feature | tests=True, coverage=True, audit=True | True | Yes | 0 | Yes | No |
| FP002-002 | feature | tests=True, coverage=True, audit=True | True | Yes | 0 | Yes | **Zero-test** |
| FP002-003 | feature | tests=True, coverage=True, audit=True | True | Yes | 0 | Yes | No |
| FP002-004 | feature | tests=True, coverage=True, audit=True | True | Yes | 0 | Yes | No |
| FP002-005 | feature | tests=True, coverage=True, audit=True | True | Yes | 0 | Yes | No |
| FP002-006 | feature | tests=True, coverage=True, audit=True | True | Yes | 0 | Yes | No |
| FP002-007 | feature | tests=True, coverage=True, audit=True | True | Yes | 0 | Yes | No |
| FP002-008 | documentation | tests=True (req=False), coverage=True (req=False) | True | No | 0 | No | No |
| FP002-009 | documentation | tests=True (req=False), coverage=True (req=False) | True | No | 0 | No | No |
| FP002-010 | documentation | tests=True (req=False), coverage=True (req=False) | True | No | 0 | No | No |
| FP002-011 | testing | tests=True (req=False), audit=True (req=True) | True | No | 0 | No | No |

**Analysis**: All 11 tasks report `ALL_PASSED=True`. For the 7 feature-type tasks, tests and coverage are marked as `required=True` yet `tests=True` passes despite 0 tests being detected. This means the Player's self-reported quality gate status (`all_passed=true`) is being trusted without independent verification of actual test execution.

**Key distinction**: The Coach validator correctly flagged one zero-test anomaly (FP002-002) but still approved the task. For the other 6 feature tasks, the anomaly wasn't triggered — suggesting the Player reported non-zero test data in its results even though the orchestrator's summary shows `0 tests`.

**Legitimacy verdict**: The quality gates are **technically passing** based on the Player's self-report, but **substantively weak** for feature tasks because independent test verification found no task-specific tests in any case.

---

## AC2: Acceptance Criteria Verification Pattern

**Status: UNCHANGED FROM TASK-REV-6F11 — Still Zero**

All 11 tasks show identical criteria tracking:
```
Criteria Progress (Turn 1): 0/1 verified (0%)
Criteria: 0 verified, 0 rejected, 1 pending
```

The Coach is approving tasks without verifying ANY acceptance criteria. This is the same pattern identified in TASK-REV-6F11 FINDING-3.

**Root cause (unchanged)**: The Coach validation flow in `coach_validator.py` evaluates quality gates (compilation, tests, coverage) but does NOT cross-reference the task's acceptance criteria. The `_loop_phase()` bookkeeping records criteria as verified only when the Coach explicitly marks them, but the Coach prompt/validator has no mechanism to do so.

---

## AC3: Test Detection and Execution Status

**Status: PERVASIVE "0 TESTS" PATTERN — Same as TASK-REV-6F11**

Every Player summary across all 11 tasks shows `0 tests`:

| Task | Player Summary | Test Status |
|------|---------------|-------------|
| FP002-001 | 1 files created, 0 modified, **0 tests (passing)** | No tests detected |
| FP002-002 | 20 files created, 1 modified, **0 tests (failing)** | No tests detected |
| FP002-003 | 22 files created, 4 modified, **0 tests (passing)** | No tests detected |
| FP002-004 | 3 files created, 1 modified, **0 tests (passing)** | No tests detected |
| FP002-005 | 3 files created, 2 modified, **0 tests (passing)** | No tests detected |
| FP002-006 | 9 files created, 1 modified, **0 tests (passing)** | No tests detected |
| FP002-007 | 12 files created, 8 modified, **0 tests (passing)** | No tests detected |
| FP002-008 | 1 files created, 2 modified, **0 tests (failing)** | No tests detected |
| FP002-009 | 1 files created, 3 modified, **0 tests (failing)** | No tests detected |
| FP002-010 | 1 files created, 2 modified, **0 tests (failing)** | No tests detected |
| FP002-011 | 1 files created, 8 modified, **0 tests (passing)** | No tests detected |

Additionally, the Coach's independent test verification shows:
- 7 feature tasks: `No task-specific tests found for TASK-FP002-XXX, skipping independent verification`
- 4 non-feature tasks (docs/testing): `Independent test verification skipped (tests_required=False)`

**Zero-test anomaly**: Only triggered once (FP002-002, line 387). The other 6 feature tasks did NOT trigger it, suggesting differences in how the Player reports quality gate data. All 7 feature tasks have `tests_passed=0` based on the orchestrator's extraction, yet only FP002-002 triggered the anomaly warning.

**Note on FEAT-FP-002 task nature**: Many of these tasks generate markdown documentation, YAML files, and seed scripts — they're not traditional code tasks. Tasks 001 (spec parser research), 008-010 (documentation), and 011 (integration tests) have limited scope for automated testing. However, tasks 003-007 (ADR generator, quality gate YAML generator, task metadata enricher, warnings extractor, feature plan integration) should have had unit tests.

---

## AC4: Parallel Wave Execution Correctness

**Status: WORKING CORRECTLY**

| Wave | Tasks | Parallel | Status | Turns |
|------|-------|----------|--------|-------|
| 1 | FP002-001, FP002-002 | 2 | PASS | 2 |
| 2 | FP002-003, FP002-004, FP002-005, FP002-010 | 4 | PASS | 4 |
| 3 | FP002-006 | 1 | PASS | 1 |
| 4 | FP002-007, FP002-011 | 2 | PASS | 2 |
| 5 | FP002-008, FP002-009 | 2 | PASS | 2 |

- All 5 waves completed without failures
- Wave 2 ran 4 tasks in parallel (highest parallelism) — no issues
- No cross-task file interference detected (shared worktree used correctly)
- FD limit raised successfully: `Raised file descriptor limit: 256 → 4096` (line 3)
- Task timeout set: 2400s (40 min) per task — no timeouts triggered
- No shared worktree file conflicts (unlike FEAT-6EDD where DM-005 created DM-008's files)

**Infrastructure validation**: All fixes from FEAT-6EDD are working:
- FD01 (raise FD limit): Validated (256 → 4096)
- FD02 (unified client storage): No dual-storage errors
- FD03 (pre-init Graphiti factory): `Pre-initialized Graphiti factory for parallel execution` (line 99)
- FD04 (coroutine cleanup): No coroutine errors during factory operations
- GTP1 (per-thread clients): `Stored Graphiti factory for per-thread context loading` seen per task
- GTP4 (task timeout): Set at 2400s, no tasks needed it

---

## AC5: Graphiti Integration Health

**Status: FUNCTIONAL WITH MINOR ISSUES**

### Positive indicators:
- Neo4j connected successfully (line 97): `Connected to Neo4j via graphiti-core at bolt://localhost:7687`
- Per-thread factory initialized: `Graphiti factory: thread client initialized successfully`
- Context retrieval working: All 22 Player/Coach invocations show `Context: retrieved (0 categories, 0/5200 tokens)`
  - 0 categories is expected for a new feature (no prior context indexed)
- Turn state capture working: `[Graphiti] Captured turn state: TURN-FEAT-UNKNOWN-1` seen across tasks
- No cross-loop hangs (the FEAT-6EDD BUG-1 is resolved)

### Issues found:

**1. "Task exception was never retrieved" errors (lines 2145-2212)**
Two identical `RuntimeError: Event loop is closed` errors from httpx `AsyncClient.aclose()`. These occur during Graphiti episode capture for Wave 4 tasks. The error chain:
```
httpx._client.AsyncClient.aclose() →
httpcore._async.connection_pool.aclose() →
anyio._backends._asyncio.SocketStream.aclose() →
asyncio.selector_events._SelectorTransport.close() →
RuntimeError: Event loop is closed
```

**Severity**: Low — These are cleanup errors that occur when the per-thread event loop is closed before httpx's async client finishes shutting down. They don't affect task execution (both Wave 4 tasks completed successfully) and are logged but never propagated.

**Root cause**: The `asyncio.run()` call in `get_thread_client()` creates a temporary event loop that is closed after execution. If the Graphiti `add_episode()` call spawns background tasks (via httpx's connection pooling), those tasks try to close connections on an already-closed loop during cleanup.

**2. graphiti-core LLM duplicate_facts warnings (lines 2214-2247)**
Seven warnings from `graphiti_core.utils.maintenance.edge_operations`:
```
WARNING: LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
```

**Severity**: Low — These are internal graphiti-core warnings about LLM output parsing during knowledge graph maintenance. They indicate the LLM (OpenAI) returned an index that graphiti-core considers invalid for deduplication. These don't affect task execution or Graphiti's core functionality (episode capture succeeds regardless).

**3. `TURN-FEAT-UNKNOWN` in turn state IDs**
All captured turn states use `TURN-FEAT-UNKNOWN-1` instead of `TURN-FEAT-FP002-1`. The feature ID is not being propagated to the turn state capture.

**Severity**: Low — Affects knowledge graph data quality (turn states can't be queried by feature ID) but doesn't impact AutoBuild execution.

---

## AC6: Comparison with TASK-REV-6F11 Findings

| TASK-REV-6F11 Finding | Severity | Status in FEAT-FP-002 | Resolution |
|----------------------|----------|----------------------|------------|
| FINDING-1: CLI async/sync mismatch | Critical | **N/A** | Feature-specific to FEAT-SC-001 (system_context.py). FEAT-FP-002 doesn't touch CLI commands. |
| FINDING-2: coach_context_builder parameter mismatch | Critical | **N/A** | Feature-specific to FEAT-SC-001 (impact_analysis path). Not exercised by FEAT-FP-002. |
| FINDING-3: Zero acceptance criteria verified | High | **PERSISTS** | 0/11 tasks verified any acceptance criteria. Same systemic gap. |
| FINDING-4: Zero-test anomaly | Medium | **PERSISTS** (1 occurrence) | FP002-002 triggered the anomaly. Same pattern as TASK-SC-010 in FEAT-SC-001. |
| Pervasive "0 tests" pattern | Medium | **PERSISTS** | 11/11 tasks show 0 tests in Player summaries. Same as FEAT-SC-001. |

**Summary**: The two critical bugs (FINDING-1 and FINDING-2) were feature-specific to FEAT-SC-001 and don't apply to FEAT-FP-002. The three systemic AutoBuild process issues (FINDING-3, FINDING-4, and the "0 tests" pattern) all persist unchanged.

---

## AC7: Remaining Issues with Severity Ratings

### ISSUE-1: Zero acceptance criteria verification (HIGH)

**Severity**: HIGH — Systemic
**Scope**: All AutoBuild runs (not specific to FEAT-FP-002)
**Evidence**: 11/11 tasks show `Criteria: 0 verified, 0 rejected, 1 pending`
**Impact**: Coach approves based on quality gates only, never checking if the implementation matches acceptance criteria. Functional correctness is unchecked.
**Since**: First identified in TASK-REV-6F11. Present in FEAT-6EDD, FEAT-SC-001, and now FEAT-FP-002.

### ISSUE-2: Zero test detection across all tasks (MEDIUM)

**Severity**: MEDIUM — Systemic
**Scope**: All AutoBuild runs
**Evidence**: 11/11 tasks show `0 tests` in Player summaries. Coach independent verification finds no task-specific tests for any task.
**Impact**: Quality gates trust the Player's self-reported `all_passed=true` without independent verification. The zero-test anomaly warning fires inconsistently (only 1 of 7 feature tasks triggered it).
**Note**: Some tasks in this feature are legitimately documentation/config tasks where testing may not apply. But tasks 003-007 (Python generators) should have tests.

### ISSUE-3: "Event loop is closed" cleanup errors (LOW)

**Severity**: LOW — Cosmetic
**Scope**: Per-thread Graphiti client cleanup
**Evidence**: 2 `ERROR:asyncio:Task exception was never retrieved` at lines 2145, 2179
**Impact**: None on execution. Cleanup timing issue with httpx async clients on closed event loops.
**Fix path**: Explicitly close httpx async client before closing event loop, or suppress the error during cleanup.

### ISSUE-4: graphiti-core duplicate_facts warnings (LOW)

**Severity**: LOW — External dependency
**Scope**: graphiti-core LLM output parsing
**Evidence**: 7 warnings about invalid `duplicate_facts` index values
**Impact**: None on execution. graphiti-core's knowledge graph deduplication may be slightly less effective.
**Fix path**: Upstream graphiti-core issue — not actionable in GuardKit.

### ISSUE-5: TURN-FEAT-UNKNOWN in turn state IDs (LOW)

**Severity**: LOW — Data quality
**Scope**: Turn state capture during AutoBuild
**Evidence**: All turn states captured as `TURN-FEAT-UNKNOWN-1` instead of `TURN-FEAT-FP002-1`
**Impact**: Turn states in Graphiti knowledge graph can't be queried by feature ID.
**Fix path**: Propagate feature ID to `_capture_turn_state()` in `autobuild.py`.

---

## AC8: Recommendations

### No Fixes Needed (Infrastructure)

The parallel execution infrastructure (FD limit, per-thread clients, timeouts, coroutine fixes) is working correctly. No action needed on these.

### Recommended Improvements (Priority Order)

1. **Coach acceptance criteria verification** (ISSUE-1, HIGH priority)
   - Add acceptance criteria cross-referencing to the Coach validation prompt
   - The Coach should check each AC item against the Player's implementation
   - This is the single most impactful improvement for AutoBuild quality

2. **Test detection improvement** (ISSUE-2, MEDIUM priority)
   - Investigate why the Player reports `0 tests` even when tests may exist
   - Consider adding independent test discovery (file glob for `test_*.py` / `*_test.py`)
   - Make zero-test anomaly detection more consistent (currently fires for some but not all zero-test cases)

3. **Feature ID propagation to turn state** (ISSUE-5, LOW priority)
   - Thread feature ID through to `_capture_turn_state()` to fix `TURN-FEAT-UNKNOWN` naming

4. **Event loop cleanup** (ISSUE-3, LOW priority)
   - Add explicit httpx async client cleanup before loop closure in per-thread Graphiti clients
   - Or suppress `RuntimeError: Event loop is closed` during cleanup phase

---

## Appendix: Task-by-Task Execution Log

| Task | Wave | Type | Files Created | Files Modified | Tests | Player Status | Coach Status | Checkpoint |
|------|------|------|:---:|:---:|:---:|---|---|---|
| FP002-001 | 1 | feature | 1 | 0 | 0 (passing) | success | approved | b2679a37 |
| FP002-002 | 1 | feature | 20 | 1 | 0 (failing) | success | approved* | a1772ac9 |
| FP002-003 | 2 | feature | 22 | 4 | 0 (passing) | success | approved | 3ca22a5e |
| FP002-004 | 2 | feature | 3 | 1 | 0 (passing) | success | approved | 9da28776 |
| FP002-005 | 2 | feature | 3 | 2 | 0 (passing) | success | approved | 9ee197a5 |
| FP002-006 | 3 | feature | 9 | 1 | 0 (passing) | success | approved | b2700fc7 |
| FP002-007 | 4 | feature | 12 | 8 | 0 (passing) | success | approved | 1ea863ca |
| FP002-008 | 5 | documentation | 1 | 2 | 0 (failing) | success | approved | 0ba87897 |
| FP002-009 | 5 | documentation | 1 | 3 | 0 (failing) | success | approved | 41b8c8f6 |
| FP002-010 | 2 | documentation | 1 | 2 | 0 (failing) | success | approved | 034f53cd |
| FP002-011 | 4 | testing | 1 | 8 | 0 (passing) | success | approved | 20cddaf9 |

*FP002-002: Zero-test anomaly warning triggered but still approved.

### Wave Timeline
- Wave 1: 2 tasks parallel → PASS
- Wave 2: 4 tasks parallel (peak parallelism) → PASS
- Wave 3: 1 task → PASS
- Wave 4: 2 tasks parallel → PASS (event loop cleanup errors here)
- Wave 5: 2 tasks parallel → PASS
- **Total**: 45m 16s, 11 turns, 0 failures, 0 retries
