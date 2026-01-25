# Review Report: TASK-REV-C4D7

## Executive Summary

The TASK-REV-BB80 fix for the SDK `max_turns` regression was **incomplete**. While it correctly fixed the `_invoke_task_work_implement` path (task-work delegation), it did not fix the `_invoke_with_role` path used by direct mode tasks.

**Root Cause Confirmed**: Direct mode tasks fail because `_invoke_with_role` uses `self.max_turns_per_agent` (which is 15 when `--max-turns 15` is passed), not the required 50 turns for implementation.

**The "Player Report Missing" Paradox Explained**: The file IS being written - but in the error handler path. The SDK completes with insufficient turns, fails to generate a Player report, the exception handler writes a minimal failure report, but then state recovery fails because no real work was done.

---

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard
- **Task ID**: TASK-REV-C4D7
- **Related Task**: TASK-REV-BB80

---

## Findings

### Finding 1: Confirmed Root Cause - `_invoke_with_role` Uses Wrong `max_turns`

**Location**: [agent_invoker.py:1217-1224](guardkit/orchestrator/agent_invoker.py#L1217-L1224)

```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=allowed_tools,
    permission_mode=permission_mode,
    max_turns=self.max_turns_per_agent,  # BUG: Uses orchestrator's adversarial turns (15)
    model=model,
    setting_sources=["project"],
)
```

**Evidence from logs**:
- Working (task-work delegation): `Max turns: 50` (uses `TASK_WORK_SDK_MAX_TURNS`)
- Broken (direct mode): No explicit log but uses `self.max_turns_per_agent` = 15

**Impact**: Direct mode tasks get only 15 SDK turns instead of the ~50 needed for implementation.

---

### Finding 2: The "Player Report Missing" Paradox Explained

**Sequence of events in direct mode failure**:

1. `_invoke_player_direct` calls `_invoke_with_role` with `max_turns=15`
2. SDK completes in ~54 seconds (vs 49 minutes for working feature)
3. The SDK agent runs out of turns before completing implementation
4. `_load_agent_report()` looks for a Player report at line 1883 - **file doesn't exist**
5. `PlayerReportNotFoundError` is raised
6. Exception handler at lines 1904-1921 writes failure artifacts:
   - `_write_direct_mode_results()` writes `task_work_results.json` (line 1909)
   - `_write_player_report_for_direct_mode()` writes `player_turn_1.json` (line 1916)
7. These writes log "Wrote direct mode player report" BEFORE the orchestrator reports "Player report missing"
8. State recovery attempts to load the report but finds a failure report with no real work

**Log evidence** (from FEAT-F392):
```
INFO: Wrote direct mode player report to .../player_turn_1.json
⚠ Player report missing - attempting state recovery
...
INFO: Loaded Player report from .../player_turn_1.json  # Recovery finds it
INFO: No work detected  # But it's a failure report with no implementation
```

The file exists after the error handler writes it, but it contains no actual work.

---

### Finding 3: Different Invocation Paths - Complete Analysis

| Aspect | Task-Work Delegation (Working) | Direct Mode (Broken) |
|--------|--------------------------------|----------------------|
| **Method** | `_invoke_task_work_implement` | `_invoke_with_role` |
| **SDK max_turns** | `TASK_WORK_SDK_MAX_TURNS = 50` | `self.max_turns_per_agent` (15) |
| **Report Creation** | task-work creates report via phases | SDK agent must write report |
| **Report Location** | Written by `_create_player_report_from_task_work` | Expected at `player_turn_N.json` |
| **Duration** | ~49 minutes for 2 tasks | ~54 seconds for 3 tasks (failure) |
| **Message Counts** | total=139-223, assistant=72-116, tools=61-101 | Not logged (immediate failure) |

---

### Finding 4: SDK Invocation Path Analysis

Three SDK invocation paths exist in `agent_invoker.py`:

| Path | Method | Line | `max_turns` Used | Status |
|------|--------|------|------------------|--------|
| Task-work delegation | `_invoke_task_work_implement` | 2268 | `TASK_WORK_SDK_MAX_TURNS` (50) | **FIXED** |
| Direct mode Player | `_invoke_with_role` | 1221 | `self.max_turns_per_agent` (15) | **BROKEN** |
| Coach validation | `_invoke_with_role` | 1221 | `self.max_turns_per_agent` (15) | OK (Coach needs fewer turns) |

---

### Finding 5: AgentInvoker Initialization

**Location**: [autobuild.py:712-717](guardkit/orchestrator/autobuild.py#L712-L717)

```python
self._agent_invoker = AgentInvoker(
    worktree_path=worktree.path,
    max_turns_per_agent=self.max_turns,  # Passes orchestrator's adversarial turns
    development_mode=self.development_mode,
    sdk_timeout_seconds=self.sdk_timeout,
    use_task_work_delegation=True,
)
```

When `--max-turns 15` is passed, `max_turns_per_agent=15`. This is correct for adversarial loop turns but wrong for SDK invocation.

---

## Root Cause Summary

The TASK-REV-BB80 fix introduced `TASK_WORK_SDK_MAX_TURNS = 50` constant but only applied it to `_invoke_task_work_implement`. The `_invoke_with_role` method (used by direct mode) was not updated.

**Conceptual Bug**: The variable `max_turns_per_agent` conflates two different concepts:
1. **Orchestrator adversarial turns** (how many Player-Coach rounds): 5-15
2. **SDK internal turns** (how many API calls within one SDK session): ~50

The fix addressed this for task-work delegation but not for direct mode.

---

## Recommendations

### Recommendation 1: Apply TASK_WORK_SDK_MAX_TURNS to Direct Mode (CRITICAL)

**Fix at** [agent_invoker.py:1221](guardkit/orchestrator/agent_invoker.py#L1221):

```python
# Before (broken):
max_turns=self.max_turns_per_agent,

# After (fixed):
max_turns=TASK_WORK_SDK_MAX_TURNS,  # Direct mode also needs ~50 internal turns
```

**Rationale**: Direct mode tasks need the same number of internal SDK turns as task-work delegation because they're performing the same implementation work.

**Risk**: Low - this matches the fix already applied to task-work delegation.

---

### Recommendation 2: Consider a Dedicated Direct Mode Constant

For clarity and future flexibility:

```python
# Constants for SDK invocations (NOT adversarial turns)
TASK_WORK_SDK_MAX_TURNS = 50    # For task-work delegation
DIRECT_MODE_SDK_MAX_TURNS = 50  # For direct mode (initially same value)
```

This allows independent tuning if direct mode tasks are found to need different turn counts.

**Rationale**: Explicit is better than implicit. Currently `TASK_WORK_SDK_MAX_TURNS` would be used for direct mode, which is semantically confusing.

---

### Recommendation 3: Rename `max_turns_per_agent` for Clarity

Consider renaming the parameter to avoid conflation:

```python
# Current (confusing):
max_turns_per_agent: int = 30

# Proposed (clear):
orchestrator_max_turns: int = 15  # Adversarial loop rounds
```

And add:
```python
# In ClaudeAgentOptions:
sdk_max_turns: int = 50  # Internal SDK turns (separate concept)
```

**Rationale**: The current name `max_turns_per_agent` doesn't clearly indicate it's for orchestrator adversarial turns vs SDK internal turns.

---

### Recommendation 4: Add Logging to `_invoke_with_role`

For debugging future issues:

```python
# After line 1223, add:
logger.info(f"[{heartbeat_task_id}] Direct mode SDK invocation")
logger.info(f"[{heartbeat_task_id}] Max turns: {options.max_turns}")
logger.info(f"[{heartbeat_task_id}] Timeout: {self.sdk_timeout_seconds}s")
```

**Rationale**: The working path logs these values; the broken path doesn't. This made diagnosis harder.

---

## Decision Matrix

| Option | Effort | Risk | Impact | Recommendation |
|--------|--------|------|--------|----------------|
| Apply existing constant to `_invoke_with_role` | Low (1 line change) | Low | High - fixes direct mode | **RECOMMENDED** |
| Create separate `DIRECT_MODE_SDK_MAX_TURNS` constant | Low (2 line changes) | Low | Medium - adds clarity | Optional |
| Rename `max_turns_per_agent` | Medium (refactor) | Low | Medium - prevents future confusion | Future consideration |
| Add logging | Low | None | Medium - aids debugging | Recommended |

---

## Verification Criteria

After implementing the fix:

1. **Re-run FEAT-F392 (OpenAPI Documentation)**
   - All 6 tasks should complete (vs 0 currently)
   - Wave 1 parallel tasks (TASK-DOC-001, 002, 005) should pass
   - Duration should be ~30-60 minutes (vs 54 seconds)

2. **Check SDK logs for direct mode**
   - Should show `Max turns: 50` (matching task-work delegation)
   - Should show multi-minute execution times
   - Should NOT show "Player report missing" followed by state recovery

3. **Verify no regression in task-work delegation**
   - Re-run FEAT-FHE (App Infrastructure) to confirm still working

---

## Acceptance Criteria Status

| Criteria | Status | Notes |
|----------|--------|-------|
| Confirm `max_turns` in `_invoke_with_role` is root cause | **VERIFIED** | Line 1221 uses `self.max_turns_per_agent` (15 vs 50 needed) |
| Verify message/tool counts for direct vs task-work | **VERIFIED** | Working: 139-223 messages; Broken: immediate failure |
| Analyze "Player report missing" paradox | **VERIFIED** | File written in error handler, not main flow |
| Determine if direct mode should use `TASK_WORK_SDK_MAX_TURNS` | **YES** | Same implementation work, same turns needed |
| Recommend fix | **COMPLETE** | Change line 1221 to use constant |
| Check other code paths using `self.max_turns_per_agent` | **VERIFIED** | Only Coach uses it, which is OK (fewer turns needed) |

---

## Appendix

### A. Evidence File References

- Working feature log: `docs/reviews/feature-build/app_infrastructure_after_SDK_MAX_TURNS_regression_fix.md`
- Broken feature log: `docs/reviews/feature-build/open_api_docs_after_SDK_MAX_TURNS_regression_fix.md`
- Previous review: `tasks/completed/TASK-REV-BB80-feature-build-regression-analysis.md`

### B. Code Locations

| File | Line Range | Description |
|------|------------|-------------|
| [agent_invoker.py:1170-1261](guardkit/orchestrator/agent_invoker.py#L1170-L1261) | `_invoke_with_role` method (BUG) |
| [agent_invoker.py:1833-1931](guardkit/orchestrator/agent_invoker.py#L1833-L1931) | `_invoke_player_direct` method |
| [agent_invoker.py:2191-2340](guardkit/orchestrator/agent_invoker.py#L2191-L2340) | `_invoke_task_work_implement` (FIXED) |
| [agent_invoker.py:100-102](guardkit/orchestrator/agent_invoker.py#L100-L102) | `TASK_WORK_SDK_MAX_TURNS` constant |

### C. Implementation Commit Diff

The fix is a single-line change:

```diff
--- a/guardkit/orchestrator/agent_invoker.py
+++ b/guardkit/orchestrator/agent_invoker.py
@@ -1218,7 +1218,8 @@ class AgentInvoker:
             options = ClaudeAgentOptions(
                 cwd=str(self.worktree_path),
                 allowed_tools=allowed_tools,
                 permission_mode=permission_mode,
-                max_turns=self.max_turns_per_agent,
+                # TASK-REV-C4D7: Direct mode also needs ~50 internal turns
+                max_turns=TASK_WORK_SDK_MAX_TURNS,
                 model=model,
                 setting_sources=["project"],
             )
```

---

**Review completed**: 2026-01-25
**Reviewer**: architectural-reviewer (via /task-review)
**Status**: REVIEW_COMPLETE
