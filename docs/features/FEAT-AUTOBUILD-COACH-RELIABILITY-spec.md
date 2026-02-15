# Feature Specification: AutoBuild Coach Reliability and Graphiti Connection Resilience

## Overview

Fix two compounding failures that make AutoBuild unreliable: (F2) Coach criteria verification always returns 0/10 because Player output format doesn't match what `coach_validator.py` expects, and (F3) FalkorDB/Graphiti asyncio corruption during parallel task execution causes connection errors that degrade context loading and block shutdown cleanup.

These failures interact in a doom loop: F3 slows context loading → Player times out (F1) → synthetic report has no completion_promises → F2 returns 0/10 → identical feedback → Player retries with degraded Graphiti → repeat until UNRECOVERABLE_STALL.

## Problem Statement

### F2: Criteria Verification Always 0/10

**Observed**: Across ALL turns in 3 separate autobuild runs of FEAT-AC1A, criteria progress showed `0/10 verified` with evidence `AC-001: Not found in Player requirements_met`.

**Root Cause Chain**:

`CoachValidator.validate_requirements()` uses two matching strategies in priority order:

1. **Strategy 1 (`_match_by_promises`)**: Looks for `completion_promises` in `task_work_results.json` or `player_turn_N.json`. Each promise needs `criterion_id` (e.g. `AC-001`) and `status: "complete"`.

2. **Strategy 2 (`_match_by_text`)**: Falls back to exact text matching between `acceptance_criteria` list and `requirements_met` list in `task_work_results.json`. Uses normalized lowercase comparison.

**Why both fail**:

- **Promises path**: The Player SDK session running `/task-work TASK-XXX --implement-only` outputs a report, but the `task_work_results_writer.py` doesn't extract `completion_promises` from the Player's output. The Player report (`player_turn_N.json`) may contain promises, but `_load_completion_promises()` can't find them because:
  - `task_work_results.json` doesn't include a `completion_promises` key (writer doesn't copy it)
  - The `task_id` field in `task_work_results` may be empty (set to `""` by synthetic report builder), so `_load_completion_promises()` can't locate the player report file on disk
  - The Player may not output `completion_promises` at all when running via SDK `task-work` mode

- **Text matching path**: `requirements_met` in `task_work_results.json` is either empty `[]` or contains text that doesn't exactly match the acceptance criteria text from the task markdown. Even minor differences (whitespace, punctuation, rephrasing) cause `_match_by_text()` to reject.

- **Synthetic reports** (timeout recovery): When Player times out, `_build_synthetic_report()` sets `_synthetic: True` and has no `completion_promises` (unless scaffolding task with file-existence matching). `validate_requirements()` detects `_synthetic` flag and calls `_build_all_unmet()` → instant 0/10.

**Evidence**: Turn 5 of Run 1 showed "Code review passed (88/100)" with all files verified, yet Coach still reported 0/10 criteria met. The Player completed the work successfully but the system couldn't recognize success.

### F3: FalkorDB/Graphiti Asyncio Corruption

**Observed**: Three error patterns during parallel autobuild execution:

- **Pattern A**: 43 connection errors after 45min of operation (connections work initially then degrade)
- **Pattern B**: `RuntimeError: no running event loop` during shutdown cleanup in `_cleanup_thread_loaders()`
- **Pattern C**: `asyncio.locks.Lock is bound to a different event loop` — async primitives created in one thread's event loop used from another thread

**Root Cause**: The autobuild orchestrator creates per-thread event loops for parallel task execution, but:

1. `_cleanup_thread_loaders()` (line ~2894) runs on the main thread and tries to close Graphiti clients that were created on worker threads with different event loops. It creates a new event loop via `asyncio.new_event_loop()` and calls `loop.run_until_complete(loader.graphiti.close())` — but the underlying Neo4j/FalkorDB driver has asyncio locks bound to the original worker thread's loop.

2. `_capture_turn_state()` (line ~2628) uses `asyncio.get_event_loop()` which may return a stale or dead loop when called after the worker thread's loop has been cleaned up.

3. Long-running parallel sessions (>30min) exhaust FalkorDB's connection pool because connections aren't properly returned when asyncio context switches between threads.

4. No health check or reconnection logic exists — once a Graphiti client's connections degrade, every subsequent context retrieval fails with connection errors, adding latency to every turn without providing value.

## Scope

### In Scope

**F2 Fixes**:
- Ensure `task_work_results_writer.py` propagates `completion_promises` from Player report to `task_work_results.json`
- Add fuzzy/semantic matching fallback when exact text matching fails in `_match_by_text()`
- Ensure `task_id` is correctly set in `task_work_results.json` so `_load_completion_promises()` can locate player reports
- Improve synthetic report promise generation for non-scaffolding task types using git diff analysis
- Add diagnostic logging when criteria matching produces 0/N results to aid future debugging

**F3 Fixes**:
- Fix `_cleanup_thread_loaders()` to close clients on their original event loops (or handle cross-loop gracefully)
- Add connection health check before each Graphiti operation with automatic reconnection
- Add graceful degradation flag: when Graphiti connections fail N times consecutively, disable for remainder of the run rather than retrying broken connections
- Fix `_capture_turn_state()` event loop handling for post-cleanup calls
- Add per-thread connection pool isolation to prevent cross-thread contamination

### Out of Scope

- Replacing FalkorDB with a different graph database
- Changing the Player↔Coach adversarial protocol
- SDK timeout fixes (addressed by FEAT-AUTOBUILD-CONTEXT-OPT)
- Changes to interactive `/task-work` behaviour

## Technical Requirements

### 1. Fix Task Work Results Writer — Propagate Completion Promises

**File**: `guardkit/orchestrator/quality_gates/task_work_results_writer.py` (or equivalent)

The writer that produces `task_work_results.json` must:
- Read `completion_promises` from the Player's report output and include it in the results JSON
- Ensure `task_id` is always populated (never empty string)
- Preserve the `criterion_id` and `status` fields that `_match_by_promises()` expects

### 2. Add Fuzzy Text Matching Fallback

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`

Enhance `_match_by_text()` with a secondary matching strategy when exact normalized matching fails:

- Strip common prefixes like checkbox markers (`- [ ]`, `- [x]`, `* `)
- Use substring containment: if the requirement text contains the criterion text (or vice versa), count as matched
- Use keyword overlap: extract significant keywords from both strings and match if overlap exceeds threshold (e.g. 70%)
- Log which strategy produced the match for observability

This must NOT weaken matching to the point of false positives. The fuzzy match should only trigger when exact match fails, and should require substantial overlap.

### 3. Improve Synthetic Report Promise Generation

**File**: `guardkit/orchestrator/autobuild.py` — `_build_synthetic_report()`

Currently, promise generation only works for `task_type == "scaffolding"`. Extend to feature/implementation tasks:

- When git diff shows files were created/modified matching patterns in acceptance criteria, generate partial promises
- Use the existing `_generate_file_existence_promises()` pattern but extend matching to code patterns (function names, class names, test file existence)
- Mark promises generated from git analysis with `evidence_type: "git_analysis"` so Coach knows the confidence level

### 4. Add Criteria Matching Diagnostics

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`

When `validate_requirements()` produces 0/N results, log at WARNING level:
- The acceptance criteria text (first 100 chars each)
- The `requirements_met` list contents
- The `completion_promises` list contents (or "empty")
- Which matching strategy was attempted
- Whether synthetic report flag was set

This enables rapid diagnosis of future matching failures without needing full debug logs.

### 5. Fix Thread-Safe Graphiti Client Cleanup

**File**: `guardkit/orchestrator/autobuild.py` — `_cleanup_thread_loaders()`

Replace the current cleanup that creates new event loops with a pattern that:
- Stores a reference to each thread's event loop alongside its loader in `_thread_loaders`
- Uses the original loop for cleanup if it's still running
- If the original loop is closed, uses `asyncio.run()` (Python 3.10+) which creates and manages its own loop
- Catches and suppresses `RuntimeError` for already-closed loops without blocking other cleanups
- Adds a timeout to prevent cleanup from hanging indefinitely

### 6. Add Graphiti Connection Health Check and Circuit Breaker

**File**: `guardkit/knowledge/graphiti_client.py` (or new `guardkit/knowledge/graphiti_health.py`)

Implement a circuit breaker pattern:

- Before each Graphiti operation, run a lightweight health check (e.g. `RETURN 1` Cypher query)
- Track consecutive failures per client instance
- After N consecutive failures (default: 3), trip the circuit breaker and disable the client for the remainder of the run
- Log clearly when circuit breaker trips: "Graphiti disabled after N consecutive failures — continuing without knowledge graph context"
- Expose `is_healthy` property for callers to check before attempting operations

### 7. Fix Event Loop Handling in Turn State Capture

**File**: `guardkit/orchestrator/autobuild.py` — `_capture_turn_state()`

Replace the fragile `asyncio.get_event_loop()` pattern with:
- Use the thread-local loader's stored loop reference if available
- If no loop available, create a fresh one with `asyncio.new_event_loop()` scoped to just this operation
- Always clean up the temporary loop after use
- Add timeout (30s) to prevent turn state capture from blocking the main loop

### 8. Store Event Loop Reference with Thread Loaders

**File**: `guardkit/orchestrator/autobuild.py` — `_get_thread_local_loader()`

Modify `_thread_loaders` storage to include the event loop:

```python
# Current: Dict[int, Optional[AutoBuildContextLoader]]
# New: Dict[int, Tuple[Optional[AutoBuildContextLoader], asyncio.AbstractEventLoop]]
```

This ensures cleanup and turn state capture can always use the correct loop for each thread's resources.

## Expected Impact

### F2 Fixes
- Criteria verification should show accurate progress (N/M) after each successful Player turn
- Synthetic reports from timeout recovery should show partial credit based on git analysis
- Coach feedback will contain actionable missing-criteria information instead of blanket "0/10"
- Stall detection will correctly identify progress vs. true stalls

### F3 Fixes
- No more `asyncio.locks.Lock is bound to a different event loop` errors
- Clean shutdown without `RuntimeError: no running event loop`
- Connection errors trigger circuit breaker rather than 43+ retry failures
- Parallel task execution remains stable beyond 45min sessions

### Combined Impact
- Breaking the doom loop: even if Player times out, git analysis provides partial criteria credit → different feedback → different approach on retry → eventual convergence
- Reduced wasted compute: accurate criteria tracking means stall detection can make informed decisions

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Fuzzy matching false positives (accepting unmet criteria) | Medium | Conservative thresholds; fuzzy only when exact fails; log strategy used |
| Circuit breaker too aggressive (disabling healthy Graphiti) | Low | Require 3+ consecutive failures; health check is lightweight |
| Git-based promise generation inaccurate | Medium | Mark with `evidence_type: "git_analysis"`; Coach can weight accordingly |
| Event loop storage increases memory per thread | Very Low | One loop reference per thread, negligible |
| task_work_results_writer changes break existing flow | Low | Additive change only (new field); existing consumers ignore unknown keys |

## Success Criteria

1. **Criteria progress > 0%**: After a successful Player turn that creates files and passes tests, criteria verification shows > 0/N
2. **No asyncio errors in logs**: Zero `RuntimeError: no running event loop` or `Lock is bound to a different event loop` errors during parallel execution
3. **Clean shutdown**: `_cleanup_thread_loaders()` completes without errors
4. **Circuit breaker activates**: When FalkorDB is unavailable, Graphiti disables after 3 failures and autobuild continues without it
5. **Doom loop broken**: TASK-SFT-001 (complexity 2) completes within 5 turns with criteria progress visible
6. **No false positives**: Criteria matching never marks unmet criteria as verified (verified by inspection of coach_turn_N.json)

## Files Modified

| File | Change |
|------|--------|
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Fuzzy matching fallback, diagnostic logging |
| `guardkit/orchestrator/quality_gates/task_work_results_writer.py` | Propagate completion_promises, ensure task_id populated |
| `guardkit/orchestrator/autobuild.py` | Thread loader loop storage, cleanup fix, turn state capture fix, synthetic report improvements |
| `guardkit/knowledge/graphiti_client.py` | Health check method, circuit breaker, is_healthy property |
| `tests/unit/test_coach_validator.py` | Tests for fuzzy matching, diagnostic logging, 0/N edge cases |
| `tests/unit/test_graphiti_health.py` | Tests for circuit breaker, health check, connection degradation |
| `tests/unit/test_autobuild_thread_cleanup.py` | Tests for cross-thread cleanup, event loop isolation |
| `tests/integration/test_autobuild_coach_reliability.py` | End-to-end: Player output → results writer → Coach validation → criteria progress |

## Relationship to Other Features

| Feature | Relationship |
|---------|-------------|
| FEAT-AUTOBUILD-CONTEXT-OPT (FEAT-BAE2) | Addresses F1 (timeout). This feature addresses F2 and F3. Together they fix all three failure modes. |
| FEAT-AC1A (Seam Testing) | Was the feature that exposed these bugs. Can be re-run as validation after this feature completes. |
| FEAT-ASF (Resilience Hardening) | Existing synthetic report work. This feature extends it with git-based promise generation. |

## Diagnostic Evidence

All evidence from run analysis documented in:
- `docs/reviews/autobuild-fixes/run_1_analysis.md`
- `docs/reviews/autobuild-fixes/run_1.md`

Key log patterns that should disappear after fix:
```
AC-001: Not found in Player requirements_met
criteria_verification: 0/10
RuntimeError: no running event loop
asyncio.locks.Lock is bound to a different event loop
Connection error (43 occurrences)
```
