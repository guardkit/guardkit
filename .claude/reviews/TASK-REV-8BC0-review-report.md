# Review Report: TASK-REV-8BC0

## Executive Summary

AutoBuild feature FEAT-5606 failed after 57m 34s, completing 2/5 tasks. The root causes are:

1. **Player cancellation** is caused by the SDK async generator cleanup race condition (TASK-RFX-8332), not SDK timeout
2. **TASK-DC-002 timeout** is a genuine 40-minute task_timeout expiry with no diagnostic visibility
3. **Synthetic report false negatives** are a known limitation of `direct` mode — file-existence verification cannot verify semantic acceptance criteria
4. **Async event loop errors** are cosmetic (instrumentation-only) but indicate a real architectural flaw in `JSONLFileBackend`
5. **Direct vs task-work mode disparity** is significant — task-work mode is structurally more reliable

## Review Details
- **Mode**: Architectural / Root Cause Analysis
- **Depth**: Standard
- **Task**: TASK-REV-8BC0
- **Subject**: FEAT-5606 run_1 in agentic-dataset-factory

---

## Finding 1: Player Cancellation Pattern (TASK-DC-001)

**Root Cause: SDK async generator cleanup race condition, NOT SDK timeout**

### Evidence

- All 3 Player invocations were cancelled after ~330s, ~180s, and ~210s respectively
- SDK timeout was 1560s (base 1200s x 1.3 complexity multiplier) — none of the invocations came close to this
- Error signature: `Cancelled via cancel scope XXXXXXX by <Task pending name='Task-NNN' coro=<<async_generator_athrow without __name__>()>>`
- The `async_generator_athrow` in the coro name is the smoking gun — this is AnyIO's cancel scope trying to close the SDK's `query()` async generator from a different asyncio Task

### Mechanism

The code at [agent_invoker.py:2088-2099](guardkit/orchestrator/agent_invoker.py#L2088-L2099) documents this exact problem (TASK-RFX-8332):

> "Explicitly close the query() async generator to prevent GC finalization from scheduling athrow(GeneratorExit) in a wrong asyncio Task (causes CancelledError on 40% of direct-mode invocations)."

The fix (explicit `gen.aclose()` with a 5s timeout in the `finally` block) is already in place, but it's not fully effective. The `query()` generator is being garbage-collected or closed from a different task context before the explicit `aclose()` runs, likely because:

1. The `async for message in gen` loop exits when `ResultMessage` is received (line 2062: `break`)
2. The generator is not yet closed at that point
3. Between the `break` and reaching the `finally` block, something triggers GC or AnyIO cleanup
4. AnyIO's cancel scope attempts to exit in the wrong task, raising `CancelledError`

### Impact

- **Mitigated by state recovery**: All 3 turns recovered work successfully (203 tests passing each time)
- **Performance cost**: Each cancellation + recovery + Coach validation adds ~60-90s overhead
- **Reliability**: The 40% failure rate on direct-mode invocations (per the code comment) means every direct-mode task will likely waste 1-2 turns

### Severity: MEDIUM

Work is preserved via state recovery, but the overhead is significant and the failure rate is high.

---

## Finding 2: TASK-DC-002 Timeout (40 min)

**Root Cause: Feature-level task_timeout (2400s) expired with zero diagnostic visibility**

### Evidence

- TASK-DC-002 was running in parallel with TASK-DC-003 in Wave 2
- TASK-DC-003 (task-work mode, complexity 5) completed successfully in 471s (1 turn, 38 SDK turns)
- TASK-DC-002 produced no progress logs between its start and the timeout
- The log shows: `TIMEOUT (feature-level): task_timeout=2400s expired for TASK-DC-002. SDK timeout budget was 1200s per invocation.`

### Analysis

The timeout chain is:
1. `asyncio.wait_for(asyncio.to_thread(...), timeout=2400)` in [feature_orchestrator.py:1485-1494](guardkit/orchestrator/feature_orchestrator.py#L1485-L1494)
2. Inside the thread, `AutoBuildOrchestrator` runs with SDK timeout of 1200s per invocation
3. The task_budget passed to the orchestrator was `2400 - elapsed_at_queue` seconds

**Most likely scenario**: TASK-DC-002's first Player invocation (direct mode, given it would have the same implementation_mode routing as other tasks in the feature) either:
- Got stuck in the SDK subprocess (no heartbeat logs visible)
- Hit the same cancel scope issue as TASK-DC-001 but without successful state recovery
- The SDK timeout (1200s) fired, but the thread then spent the remaining budget on recovery + retry before the outer 2400s timeout killed it

**Key gap**: There are NO progress logs for TASK-DC-002 in the run log. The parallel execution with TASK-DC-003 means their logs are interleaved, but TASK-DC-002 has zero entries after the initial "Starting orchestration" line. This suggests the AutoBuildOrchestrator for DC-002 never made it past Phase 1 setup, or its logs were lost.

### Severity: HIGH

Complete task failure with no diagnostic information. The timeout mechanism works but provides no insight into why the task stalled.

---

## Finding 3: Synthetic Report / Promise Matching False Negatives

**Assessment: Known limitation causing wasted turns, not a reliability issue**

### Evidence

- Coach turns 1 and 2 for TASK-DC-001 both reported: `Requirements not met for TASK-DC-001: missing ['All 5 Pydantic models match the API contract field types exactly', ...]`
- The log explicitly warns: `Promise matching will fail — falling through to text matching`
- Criteria progress stayed at 4/9 (44%) for turns 1 and 2
- Turn 3 jumped to 9/9 (100%) — but the log shows `(0%)` display which is likely a display formatting bug

### Mechanism

When the Player is cancelled (direct mode), the system:
1. Recovers work state via git diff + test detection
2. Builds a synthetic report with git-analysis promises
3. Passes to Coach, which falls through to file-existence verification

The problem is that file-existence verification cannot check semantic criteria like "models match API contract field types exactly" or "mode constrained to Literal[...]". These require reading file contents and understanding code semantics.

### Why Turn 3 Passed

Turn 3 used an expanded Coach context (2789/7892 tokens vs 1978/5200 tokens on turns 1-2). The larger context window likely gave the Coach enough information to verify the criteria via text matching rather than promise matching. Additionally, the perspective reset at turn 3 may have changed the Coach's verification approach.

### Severity: MEDIUM

Causes 1-2 wasted turns per task when combined with Player cancellation. The Coach eventually reaches the right decision, but the path is inefficient.

---

## Finding 4: Async Event Loop / Threading Issues

**Assessment: Cosmetic (instrumentation-only), but real architectural flaw**

### Evidence

Four distinct error instances in the log:
```
Backend JSONLFileBackend failed during flush: <asyncio.locks.Lock object at 0x114250050 [unlocked, waiters:1]> is bound to a different event loop
Backend JSONLFileBackend failed during emit: ... is bound to a different event loop. Other backends are unaffected.
RuntimeWarning: The executor did not finishing joining its threads within 300 seconds.
Backend JSONLFileBackend failed during close: ... is bound to a different event loop
```

### Root Cause

`JSONLFileBackend` uses an `asyncio.Lock` for thread-safe writes ([emitter.py:17](guardkit/orchestrator/instrumentation/emitter.py#L17)). When parallel wave execution uses `asyncio.to_thread()`, each thread gets its own event loop. The `asyncio.Lock` created in the main event loop cannot be used from worker threads — it's bound to the creating loop.

### Impact

- **No data loss for orchestration**: The errors are caught and logged as warnings. The "Other backends are unaffected" message confirms only JSONL persistence fails.
- **Telemetry data loss**: JSONL event files may be incomplete for parallel tasks.
- **Thread join warning**: The 300-second executor join timeout is concerning but appears to be a symptom of the same cross-loop issue — cleanup routines waiting on locks they can never acquire.

### Severity: LOW

No impact on orchestration logic or task execution. Telemetry is degraded but not critical.

---

## Finding 5: Direct vs Task-Work Mode Disparity

**Assessment: Task-work mode is structurally more reliable; direct mode has fundamental disadvantages**

### Evidence

| Aspect | Direct Mode (DC-001) | Task-Work Mode (DC-003) |
|--------|----------------------|-------------------------|
| SDK Timeout | 1560s (1200 x 1.0 x 1.3) | 2399s (1200 x 1.5 x 1.5, capped) |
| Turns to Complete | 3 (all Player cancelled) | 1 (clean completion) |
| Player Report | Synthetic (git-analysis promises) | Agent-written (13 completion_promises) |
| Coach Verification | File-existence fallback | Promise matching (13/13 verified) |
| Total Duration | ~12.5 min (3 turns) | ~8 min (1 turn) |
| SDK Turns | Not tracked (direct mode) | 38 |
| Tool Use Logging | None | Write, Edit visible in log |

### Structural Advantages of Task-Work Mode

1. **Higher timeout budget**: 1.5x mode multiplier gives more room for complex tasks
2. **Real player reports**: Agent writes structured `task_work_results.json` with completion_promises that Coach can match directly
3. **No synthetic report**: Eliminates the promise-matching false negative problem entirely
4. **State bridge**: Moves task through design_approved state, creating implementation plan stub
5. **Inline protocol**: 19KB implementation protocol gives the SDK comprehensive instructions
6. **Cancel scope immunity**: Task-work delegates to a full SDK session with `acceptEdits` permission mode, which runs as a subprocess with proper lifecycle management

### When Direct Mode Might Be Preferred

- Very simple, low-complexity tasks where overhead of task-work setup isn't justified
- Tasks that only need file creation (scaffolding) where file-existence verification suffices

### Severity: MEDIUM-HIGH

The mode routing decision significantly affects reliability. Direct mode's 40% cancellation rate (per code comments) combined with synthetic report limitations makes it the wrong choice for non-trivial tasks.

---

## Recommendations

### R1: Fix Generator Cleanup Race Condition (HIGH PRIORITY)

**Problem**: The `gen.aclose()` in the `finally` block at [agent_invoker.py:2093-2099](guardkit/orchestrator/agent_invoker.py#L2093-L2099) isn't reached before AnyIO's cancel scope triggers.

**Proposed fix**: Close the generator immediately after breaking from the `async for` loop, rather than deferring to `finally`:

```python
# After line 2062 (break on ResultMessage)
async for message in gen:
    ...
    if isinstance(message, ResultMessage):
        self._last_session_id = getattr(message, "session_id", None)
        # Close generator immediately to prevent GC race
        with suppress(Exception):
            async with asyncio.timeout(5):
                await gen.aclose()
        gen = None  # Prevent double-close in finally
        break
```

**Expected impact**: Eliminate the 40% direct-mode cancellation rate.

### R2: Add Progress Heartbeats for Parallel Tasks (HIGH PRIORITY)

**Problem**: TASK-DC-002 timed out with zero diagnostic information.

**Proposed fix**:
- Add periodic state snapshots during SDK invocation (every 60s) showing: elapsed time, last tool use, files changed so far
- When a task times out via `asyncio.wait_for`, capture and log the thread's stack trace before cleanup
- Add a `--task-progress-interval` flag to feature orchestrator

**Expected impact**: Diagnosable timeout failures instead of black-box timeouts.

### R3: Prefer Task-Work Mode for Non-Trivial Tasks (MEDIUM PRIORITY)

**Problem**: Direct mode has structural disadvantages for complexity >= 3.

**Proposed fix**: Update the implementation_mode routing logic to default to `task-work` for tasks with complexity >= 3 or when the task type is `feature` or `declarative`. Reserve `direct` mode only for `scaffolding` tasks or complexity 1-2.

**Expected impact**: Fewer wasted turns, better Coach verification accuracy.

### R4: Fix JSONLFileBackend Cross-Loop Issue (LOW PRIORITY)

**Problem**: `asyncio.Lock` bound to wrong event loop in parallel execution.

**Proposed fix**: Replace `asyncio.Lock` with `threading.Lock` in `JSONLFileBackend`, since the backend is used across threads. Alternatively, use a thread-local event loop or make the backend synchronous (file writes are fast).

**Expected impact**: Complete telemetry in parallel execution. Eliminates thread join timeout warning.

### R5: Improve Synthetic Report Semantic Verification (LOW PRIORITY)

**Problem**: File-existence verification cannot check semantic acceptance criteria.

**Proposed fix**: When synthetic reports are generated, add a lightweight code-reading step that extracts key patterns (class names, type annotations, constraint decorators) from changed files and includes them as evidence in the report. This gives Coach enough context for text-matching without requiring a full SDK invocation.

**Expected impact**: Reduce false negatives from synthetic reports, fewer wasted Coach turns.

---

## Decision Matrix

| # | Recommendation | Effort | Impact | Risk | Priority |
|---|---------------|--------|--------|------|----------|
| R1 | Fix generator cleanup race | Low (10 lines) | High (eliminates 40% failure rate) | Low | **P0** |
| R2 | Add progress heartbeats | Medium (new feature) | High (diagnosable timeouts) | Low | **P1** |
| R3 | Prefer task-work routing | Low (config change) | Medium-High (fewer wasted turns) | Low | **P1** |
| R4 | Fix JSONLFileBackend | Low (lock type change) | Low (telemetry only) | Low | **P2** |
| R5 | Improve synthetic reports | Medium (new feature) | Medium (fewer false negatives) | Medium | **P2** |

---

## Appendix: Timeline Reconstruction

```
10:54:46  Wave 1 starts: TASK-DC-001 (direct mode)
10:54:46  Turn 1 Player starts (SDK timeout: 1560s)
11:00:20  Turn 1 Player CANCELLED after ~334s (cancel scope race)
11:00:21  State recovery: 4 files, 203 tests passing
11:00:31  Turn 1 Coach: 4/9 criteria (synthetic report false negative)
11:00:31  Turn 2 Player starts
11:03:32  Turn 2 Player CANCELLED after ~181s
11:03:33  State recovery: 1 file modified, 203 tests
11:03:41  Turn 2 Coach: 4/9 criteria (same false negatives)
11:03:41  Turn 3 Player starts (perspective reset)
11:07:09  Turn 3 Player CANCELLED after ~208s
11:07:10  State recovery: 0 new files, 203 tests
11:07:21  Turn 3 Coach: 9/9 APPROVED (larger context window)
11:07:21  Wave 1 PASSED

11:07:21  Wave 2 starts: TASK-DC-002 + TASK-DC-003 (parallel)
11:07:21  DC-003 Turn 1 Player starts (task-work mode, SDK timeout: 2399s)
11:15:13  DC-003 Turn 1 Player completed: 471s, 38 SDK turns, 10 files
11:15:21  DC-003 Turn 1 Coach: 13/13 APPROVED
11:47:21  DC-002 TIMEOUT after 2400s (no progress logs)
11:52:21  Wave 2 FAILED (DC-002 timeout, DC-003 success)

11:52:21  Feature FAILED: stop_on_failure=True
          Total duration: 57m 34s, 2/5 tasks completed
```
