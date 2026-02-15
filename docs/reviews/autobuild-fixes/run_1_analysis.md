# AutoBuild Run 1 Analysis — FEAT-AC1A Seam-First Testing

**Date**: 2026-02-15  
**Feature**: FEAT-AC1A (11 tasks, 3 waves)  
**Outcome**: FAILED — 1/11 tasks completed across 3 attempts  
**Fixes already applied**: TASK-POF-001–004, ASF-002–008, diagram output enhancements

---

## Executive Summary

The run contained **3 separate execution attempts** in one log file. TASK-SFT-002 (ADR writing, `implementation_mode: direct`) succeeded every time (1 turn in run 1, 3 turns in run 3). TASK-SFT-001 (scaffolding, `implementation_mode: task-work`) failed consistently across all attempts with an `UNRECOVERABLE_STALL` exit.

There are **3 distinct failure modes** compounding against each other, all hitting TASK-SFT-001:

| # | Failure | Severity | Category |
|---|---------|----------|----------|
| F1 | SDK timeout kills Player mid-success | Critical | Autobuild orchestration |
| F2 | Criteria verification always reads 0/10 | Critical | Coach/criteria matching |
| F3 | Graphiti/FalkorDB asyncio event loop corruption | High | Infrastructure/threading |

---

## Failure F1: SDK Timeout (1800s) on task-work Delegation

### What happened

TASK-SFT-001 uses `implementation_mode: task-work` which delegates to `/task-work TASK-SFT-001 --implement-only --mode=tdd`. This path timed out at 1800s on turns 2, 4, and 5 of the first run.

The most telling evidence is **turn 5**:
- 107 messages were processed before timeout
- The last output showed "Code review passed (88/100)" with all files verified ✅
- The Player had transitioned state to IN_REVIEW and was about to complete
- **The timeout killed it during final output serialization**

By contrast, TASK-SFT-002 used `implementation_mode: direct` and completed in ~180 seconds on turn 1.

### Root cause

The task-work delegation mode wraps the Claude SDK call inside a subprocess-like pattern with a hard 1800s timeout. For a complexity-2 scaffolding task, this should be more than enough — but the task-work command appears to be doing significant context loading, reading the full task specification, potentially loading Graphiti context, and running quality gates internally before the actual implementation work even starts.

On turns 2 and 4, "Messages processed before timeout: 0" means the SDK call hung during initialization/context loading and never even started streaming output.

### Recommended fixes

1. **Increase `sdk_timeout` for task-work mode** or make it configurable per-task. A complexity-2 task shouldn't need 30 minutes, but the overhead of task-work delegation is eating the budget.

2. **Add a "first message" watchdog**: If no messages are received within 120s of SDK invocation, consider it a stalled connection and retry rather than waiting the full 1800s.

3. **Consider forcing `direct` mode for low-complexity tasks** (complexity ≤ 3). The task-work delegation adds overhead that only pays off for complex multi-file implementations.

---

## Failure F2: Criteria Verification Permanently at 0/10

### What happened

Across ALL 8+ turns in run 1 and ALL 3 turns in run 3, the Coach's criteria progress was **0/10 verified**, even on turns where the Player successfully created files and made meaningful changes.

The log consistently shows:
```
Criteria Progress (Turn N): 0/10 verified (0%)
Criteria: 0 verified, 10 rejected, 0 pending
  AC-001: Not found in Player requirements_met
  AC-002: Not found in Player requirements_met
```

This means the criteria matching mechanism is looking for `requirements_met` in the Player's output/report, and never finding it.

### Root cause

This is the **synthetic report problem** identified in the diagnostic diagrams. When the Player succeeds, it should output a structured report with `requirements_met` listing which acceptance criteria were satisfied. But:

- On timeout turns (2, 4, 5): state recovery creates a synthetic report with `{tests: 0, req: []}` — no requirements listed
- On "successful" turns (1, 3, 6, 7, 8): the Player appears to complete but its output isn't being parsed correctly by the criteria matcher — `requirements_met` is either missing from the output format or not being extracted from the streaming response

The Coach's `_match_by_promises()` and `_match_by_text()` methods (from `coach_validator.py`) both fail to match any criteria, suggesting the Player's output structure doesn't contain the expected fields.

### Recommended fixes

1. **Audit the Player→Coach handoff format**: Check what the Player actually outputs at the end of a successful turn vs what `coach_validator.py` expects in `validate_requirements()`. The `requirements_met` field may have been renamed or restructured.

2. **Fall back to text-based criteria matching**: If `_match_by_promises()` finds nothing, `_match_by_text()` should scan the git diff and file contents against the acceptance criteria text. The fact that both fail suggests the text matcher may not be operating on the right data.

3. **Fix synthetic report generation**: When state recovery succeeds (detecting files changed via git), populate the synthetic report with at least partial `requirements_met` based on what files were created/modified vs what the acceptance criteria expect.

---

## Failure F3: Graphiti/FalkorDB Connection Degradation

### What happened

Three distinct FalkorDB error patterns appeared:

**Pattern A — Connection loss after sustained operation (Run 1, from turn 4 onwards):**
43 instances of `Search request failed: Connection error.` plus `Connection error communicating with OpenAI API` during Coach validation and episode creation. The initial connections at startup were fine (line 60, 142, 147), but degraded after ~45 minutes of operation.

**Pattern B — Event loop destroyed at shutdown (Run 1 and 3):**
`RuntimeError: no running event loop` during `FalkorDriver.build_indices_and_constraints()` and `edge_fulltext_search()`. These fire during cleanup when the asyncio event loop has been torn down while FalkorDB coroutines are still pending.

**Pattern C — Cross-thread event loop binding (Run 3):**
`<asyncio.locks.Lock object at 0x11699f550 [locked]> is bound to a different event loop` — This is the smoking gun. FalkorDB async objects created in one thread's event loop are being used from a different thread's event loop during parallel task execution.

### Root cause

The feature orchestrator runs tasks in parallel using `asyncio.to_thread()` for wave execution. Each thread gets its own per-thread Graphiti client (`Created per-thread context loader for thread 6166851584`), but the underlying FalkorDB driver's async primitives (locks, connections) are bound to the event loop in which they were created.

When Thread A creates a FalkorDB connection on Event Loop 1, then Thread B tries to use objects from that connection on Event Loop 2, you get Pattern C. Over time, this corrupts the connection pool, leading to Pattern A (general connection failures). Pattern B is the cleanup aftermath.

### Recommended fixes

1. **Ensure per-thread event loop isolation**: Each thread in the parallel executor needs its own completely independent FalkorDB connection and event loop. The Graphiti factory's thread client initialization should create a fresh `FalkorDriver` per thread, not share any async primitives.

2. **Add connection health checks**: Before each Coach validation or episode creation, ping FalkorDB. If the connection is dead, create a fresh one rather than retrying on a corrupted connection.

3. **Graceful degradation on Graphiti failure**: The `guardkit.knowledge.graphiti_client` already logs warnings when searches fail, but it should also mark the context loader as "degraded" so the Coach can still proceed with file-based validation rather than retrying Graphiti searches endlessly.

4. **Fix shutdown cleanup**: Ensure all pending coroutines are properly cancelled before the event loop is torn down. The `asyncio.Task was destroyed but it is pending` errors indicate missing cleanup in the factory's shutdown path.

---

## Interaction Between Failures

These three failures create a vicious feedback loop:

```
F1 (SDK Timeout) 
  → State Recovery creates synthetic report with empty requirements_met
    → F2 (Criteria matcher finds 0/10) 
      → Coach gives "not all criteria met" feedback
        → Player tries again, context loading includes Graphiti search
          → F3 (FalkorDB connection error) 
            → Context loading degrades or slows down
              → F1 (SDK timeout again)
```

The stall detection correctly identifies this as `UNRECOVERABLE_STALL` after 3 consecutive identical feedbacks — but the root cause isn't that the Player can't do the work. Turn 5 of run 1 proves it **completed the work successfully**. The system just can't recognize the success.

---

## Priority Order for Fixes

### P0 — Unblock autobuild immediately
1. **Fix criteria matching (F2)** — This is the most impactful fix. If the Coach can correctly verify criteria, many turns would have been approved rather than stalled.
2. **Fix the synthetic report to include requirements based on git state** — When the Player times out but created the right files, credit should be given.

### P1 — Reduce wasted compute
3. **Add first-message watchdog** (120s) to detect hung SDK connections early
4. **Default complexity ≤ 3 tasks to `direct` mode** to avoid task-work overhead

### P2 — Fix infrastructure reliability
5. **Fix FalkorDB per-thread event loop isolation** — Each parallel thread needs its own fresh driver
6. **Add Graphiti connection health check before each use**
7. **Fix asyncio cleanup on shutdown**

---

## Validation Plan

After applying fixes, re-run with:
```bash
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-AC1A --max-turns 30 --sdk-timeout 1800 --fresh
```

Expected outcomes:
- TASK-SFT-001 should complete within 3 turns
- Criteria progress should show >0% after successful Player turns  
- No `Connection error` from Graphiti during Coach validation
- No `no running event loop` errors at shutdown
