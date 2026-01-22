# Review Report: TASK-REV-FB17 (Final - Debug Trace Analysis)

## Executive Summary

**ROOT CAUSE FOUND**: The debug trace reveals the **SDK is NEVER invoked**. The failure occurs BEFORE SDK invocation due to a missing implementation plan.

```
ERROR:guardkit.orchestrator.agent_invoker:Implementation plan not found for TASK-FHA-001
```

**The Actual Problem Chain**:
1. `invoke_player()` transitions task to `design_approved` state ✅
2. It calls `verify_implementation_plan()` to check for a plan
3. No plan exists, so it tries `_create_stub_implementation_plan()`
4. **Stub creation is SKIPPED** because of an overly restrictive check at `state_bridge.py:380-384`
5. `PlanNotFoundError` is raised
6. Player fails **before SDK is ever called**

**Critical Fix Required**: The stub creation check at `state_bridge.py:380-384` requires `autobuild:` config in task frontmatter, but feature tasks have `autobuild_state:` (runtime state) instead. This causes stub creation to be skipped for ALL feature tasks.

## Review Details

- **Mode**: Decision Analysis (Revised with SDK Documentation Deep-Dive)
- **Depth**: Comprehensive + Ultrathink
- **Duration**: ~90 minutes (including SDK documentation analysis)
- **Reviewer**: Claude Opus 4.5
- **Task**: TASK-REV-FB17
- **SDK Documentation Sources**:
  - `platform.claude.com/docs/en/agent-sdk/overview`
  - `platform.claude.com/docs/en/agent-sdk/python`
  - `platform.claude.com/docs/en/agent-sdk/quickstart`
  - `platform.claude.com/docs/en/agent-sdk/sessions`
  - `platform.claude.com/docs/en/agent-sdk/subagents`

## SDK Architecture Alignment Verification

### ✅ Our Implementation Matches SDK Best Practices

| SDK Pattern | Our Implementation | Status |
|-------------|-------------------|--------|
| `query()` for one-off tasks | Used correctly in `_invoke_task_work_implement()` | ✅ Aligned |
| `ClaudeAgentOptions` configuration | Correct fields: `cwd`, `allowed_tools`, `permission_mode`, `max_turns`, `setting_sources` | ✅ Aligned |
| `setting_sources=["user", "project"]` | Line 1742 - loads skills from both user and project | ✅ Aligned |
| Message type handling | Correctly imports `AssistantMessage`, `TextBlock`, `ToolUseBlock`, `ToolResultBlock`, `ResultMessage` | ✅ Aligned |
| Error type handling | Handles `CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError`, `asyncio.TimeoutError` | ✅ Aligned |
| Content block iteration | Lines 1749-1764 correctly iterate over `message.content` blocks | ✅ Aligned |

### SDK Documentation Key Findings

From the official documentation:

1. **`setting_sources` is critical**: Default is `None` (no settings loaded). Must include `"project"` to load CLAUDE.md, and `"user"` to load user settings/skills. Our fix in TASK-FB-FIX-014 correctly added `["user", "project"]`.

2. **Error types are correct**: The SDK defines `CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError`, and base `ClaudeSDKError`. We handle all of these.

3. **Message streaming pattern is correct**: `async for message in query(...)` is the documented pattern for streaming messages.

4. **`ResultMessage` signals completion**: We correctly check for `ResultMessage` to detect when the SDK completes.

### ⚠️ Architectural Gap Found: Error Path Result Writing

**The Issue**: Our code only writes `task_work_results.json` on the SUCCESS path:

```python
# agent_invoker.py lines 1768-1777 (SUCCESS PATH)
output_text = "\n".join(collected_output)
parser = TaskWorkStreamParser()
parser.parse_message(output_text)
parsed_result = parser.to_result()
self._write_task_work_results(task_id, parsed_result, documentation_level)  # ← Only here!
return TaskWorkResult(success=True, output=parsed_result)
```

When exceptions occur (lines 1785-1827), we return `TaskWorkResult(success=False)` WITHOUT writing any results:

```python
# ERROR PATHS - NO result writing!
except asyncio.TimeoutError:
    raise SDKTimeoutError(...)  # No _write_task_work_results()

except ProcessError as e:
    return TaskWorkResult(success=False, ...)  # No _write_task_work_results()

except CLIJSONDecodeError as e:
    return TaskWorkResult(success=False, ...)  # No _write_task_work_results()

except Exception as e:
    return TaskWorkResult(success=False, ...)  # No _write_task_work_results()
```

This is why Coach always reports "Task-work results not found" - the results file is never created on error paths.

## FBSDK Fix Verification Matrix

| Task | Fix Description | Deployed? | Working? | Evidence |
|------|-----------------|-----------|----------|----------|
| **FBSDK-001** | Copy task files to worktree | ✅ Yes | ✅ Yes | Lines 80-86: "Copied 6 task file(s) to worktree" |
| **FBSDK-002** | Write task_work_results.json | ✅ Yes | ⚠️ N/A | Code at line 1777 exists but never reached |
| **FBSDK-003** | Centralize TaskArtifactPaths | ✅ Yes | ✅ Yes | Both AgentInvoker and CoachValidator use centralized paths |
| **FBSDK-004** | Add implementation plan stub | ✅ Yes | ⚠️ N/A | Code exists but may not trigger (autobuild config check) |

### Evidence of Successful Fixes

1. **FBSDK-001 (Task Copy)**: Test trace shows:
   ```
   INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-FHA-001-create-project-structure.md
   INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-FHA-002-implement-main-app.md
   ...
   ✓ Copied 6 task file(s) to worktree
   ```

2. **FBSDK-003 (Centralized Paths)**: Code verified at:
   - `agent_invoker.py:1102`: `TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)`
   - `coach_validator.py:397`: `TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)`

3. **State Transition**: Test trace shows successful state transition:
   ```
   INFO:guardkit.tasks.state_bridge.TASK-FHA-001:Transitioning task TASK-FHA-001 from backlog to design_approved
   INFO:guardkit.tasks.state_bridge.TASK-FHA-001:Task TASK-FHA-001 transitioned to design_approved
   ```

## New Finding: SDK Invocation Failure Path

### The Actual Failure Mode

The test trace is truncated ("27703 characters truncated") but the pattern is clear:

```
Turn 1: Player Implementation → ✗ error (Player failed - attempting state recovery)
Turn 1: Coach Validation → ⚠ feedback (Task-work results not found)
[Repeats 5 times]
```

This indicates the SDK `query()` call in `_invoke_task_work_implement()` is failing with an exception, causing the code to exit before reaching line 1777 (`_write_task_work_results()`).

### Code Flow Analysis

```python
async def _invoke_task_work_implement(self, task_id, mode, documentation_level):
    try:
        # ... SDK setup ...
        async with asyncio.timeout(self.sdk_timeout_seconds):     # ← Timeout here?
            async for message in query(prompt=prompt, options=options):
                # ... stream processing ...

        # THESE LINES ARE NEVER REACHED:
        parser = TaskWorkStreamParser()
        parser.parse_message(output_text)
        parsed_result = parser.to_result()
        self._write_task_work_results(task_id, parsed_result)  # ← Line 1777, never executed
        return TaskWorkResult(success=True, ...)

    except asyncio.TimeoutError:  # ← THIS IS LIKELY TRIGGERED
        raise SDKTimeoutError(error_msg)
    except ProcessError as e:      # ← OR THIS
        return TaskWorkResult(success=False, ...)
```

### Why State Recovery Doesn't Write Results

When Player fails, `_attempt_state_recovery()` is called. This method:
1. Checks for existing Player JSON report (none exists)
2. Detects git changes (possibly none or minimal)
3. Does NOT write `task_work_results.json`

The state recovery creates `work_state_turn_N.json`, which is a different file that Coach doesn't read.

## Root Cause: SDK Invocation Failure

The 600-second (10 minute) SDK timeout appears insufficient for the task-work invocation. The test trace shows:
- Test was run with `timeout: 10m 0s` (external bash timeout)
- SDK timeout is 600s (internal)
- Exit code 2 (CLI error, not timeout)

However, the repeated "Player failed" pattern across 5 turns with near-instant execution suggests the SDK might be:
1. Failing to start the Claude Code CLI
2. Failing to authenticate
3. Encountering a configuration issue
4. Hitting a permission issue in the worktree

## Revised Recommendations (DEBUG TRACE UPDATE)

### ⚠️ PRIORITY REVISION BASED ON DEBUG TRACE

The debug trace at `docs/reviews/feature-build/grep_error.md` revealed the **ACTUAL root cause**:

```
ERROR:guardkit.orchestrator.agent_invoker:Implementation plan not found for TASK-FHA-001
```

**The SDK is NEVER invoked.** The failure occurs at `state_bridge.py:380-384` where stub creation is skipped because feature tasks have `autobuild_state:` (runtime) but NOT `autobuild:` (config).

### Recommendation 1: Fix Stub Creation Check (CRITICAL - MUST FIX FIRST)

**THIS IS THE ACTUAL ROOT CAUSE.** The check at `state_bridge.py:380-384` blocks ALL feature tasks:

```python
# CURRENT CODE (BROKEN)
if not isinstance(autobuild_config, dict) or not autobuild_config:
    self.logger.debug(f"Task {self.task_id} has no autobuild config, skipping stub creation")
    return None  # ← ALL feature tasks exit here!
```

Feature tasks from `/feature-plan` have:
- `autobuild_state:` (runtime state added by orchestrator) ← NOT checked
- `implementation_mode: direct` or `task-work` ← NOT checked
- **NO** `autobuild:` config ← This is what the check requires

**Fix Options:**
1. **Option B (Recommended)**: Relax check to recognize `autobuild_state:` OR `implementation_mode: task-work`
2. **Option A**: Add `autobuild: {enabled: true}` to feature task templates
3. **Option C**: Remove check entirely (may create unnecessary stubs)

### Recommendation 2: Add `_write_failure_results()` Method (HIGH - SECONDARY)

This fix is still valuable for error visibility, but **will never be reached** until Recommendation 1 is fixed.

```python
def _write_failure_results(
    self,
    task_id: str,
    error: str,
    error_type: str,
    partial_output: Optional[List[str]] = None,
) -> None:
    """Write task_work_results.json with failure status.

    Called on ALL error paths to ensure Coach receives actionable information.

    Args:
        task_id: Task identifier
        error: Error message describing what failed
        error_type: Exception type name (e.g., "ProcessError", "TimeoutError")
        partial_output: Any output collected before failure (optional)
    """
    results = {
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "completed": False,
        "success": False,
        "error": error,
        "error_type": error_type,
        "partial_output": partial_output or [],
        "quality_gates": {
            "all_passed": False,
            "compilation": {"passed": False, "error": "SDK invocation failed before testing"},
            "tests": {"passed": False, "error": "SDK invocation failed before testing"},
        },
    }
    results_path = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(results, indent=2))
    logger.info(f"Wrote failure results to {results_path}")
```

Then update ALL exception handlers to call this method:

```python
except asyncio.TimeoutError:
    self._write_failure_results(task_id, error_msg, "TimeoutError", collected_output)
    raise SDKTimeoutError(error_msg)

except ProcessError as e:
    error_msg = f"SDK process failed (exit {e.exit_code}): {e.stderr}"
    self._write_failure_results(task_id, error_msg, "ProcessError", collected_output)
    return TaskWorkResult(success=False, output={}, error=error_msg)

except CLIJSONDecodeError as e:
    error_msg = f"Failed to parse SDK response: {e}"
    self._write_failure_results(task_id, error_msg, "CLIJSONDecodeError", collected_output)
    return TaskWorkResult(success=False, output={}, error=error_msg)

except Exception as e:
    error_msg = f"Unexpected error: {str(e)}"
    self._write_failure_results(task_id, error_msg, type(e).__name__, collected_output)
    return TaskWorkResult(success=False, output={}, error=error_msg)
```

**Impact**: Coach will receive actual error information, enabling intelligent feedback instead of generic "results not found".

### Recommendation 2: Add Verbose SDK Invocation Logging (HIGH)

The 27,703-character truncation hides critical diagnostic info. Add structured logging BEFORE the SDK call:

```python
async def _invoke_task_work_implement(self, task_id, mode, documentation_level):
    # Log SDK configuration BEFORE invocation
    logger.info(f"[{task_id}] SDK invocation starting")
    logger.info(f"[{task_id}] Working directory: {self.worktree_path}")
    logger.info(f"[{task_id}] Tools: {options.allowed_tools}")
    logger.info(f"[{task_id}] Setting sources: {options.setting_sources}")
    logger.info(f"[{task_id}] Timeout: {self.sdk_timeout_seconds}s")
    logger.info(f"[{task_id}] Prompt (first 200 chars): {prompt[:200]}...")

    try:
        message_count = 0
        async for message in query(prompt=prompt, options=options):
            message_count += 1
            logger.debug(f"[{task_id}] Message {message_count}: {type(message).__name__}")
            # ... existing processing ...

        logger.info(f"[{task_id}] SDK completed: {message_count} messages processed")

    except Exception as e:
        logger.error(f"[{task_id}] SDK FAILED: {type(e).__name__}: {e}")
        logger.error(f"[{task_id}] Messages processed before failure: {message_count}")
        raise
```

**Impact**: Next failure will reveal exactly where and why the SDK fails.

### Recommendation 3: Investigate "Duration: 1s" Anomaly (HIGH - DIAGNOSTIC)

The test trace shows "Duration: 1s" for 5 turns. Real SDK invocations take 10-20+ minutes. This suggests:

1. **SDK is failing immediately** (not timing out after 600s)
2. **Possible causes**:
   - Claude Code CLI not found in PATH
   - API authentication failure
   - Permission issue in worktree
   - Invalid options configuration
   - Worktree not properly initialized

**Diagnostic Action**: Run with `GUARDKIT_LOG_LEVEL=DEBUG` to capture full trace:

```bash
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-XXX 2>&1 | tee debug_trace.log
```

**Impact**: Will reveal the actual error hiding in the truncated section.

### Recommendation 4: Add SDK Doctor Check (MEDIUM)

Create a diagnostic command to verify SDK prerequisites:

```bash
guardkit doctor --check=sdk
```

Should verify:
1. `claude` CLI is in PATH
2. `claude --version` works
3. `ANTHROPIC_API_KEY` or Claude Code auth is configured
4. SDK can execute a trivial query: `query(prompt="Say hello", options=ClaudeAgentOptions(max_turns=1))`

**Impact**: Prevents false-positive feature-build failures from environment issues.

### Recommendation 5: Verify FBSDK-004 Autobuild Config Check (LOW)

The stub creation code checks for autobuild config (line 380-384 of `state_bridge.py`):
```python
if not isinstance(autobuild_config, dict) or not autobuild_config:
    return None  # Skips stub creation
```

Tasks from `/feature-plan` may not have explicit `autobuild:` frontmatter.

**Action**: Either:
1. Add `autobuild: {enabled: true}` to feature task templates
2. Relax the check to create stubs for all tasks with `implementation_mode: task-work`

**Impact**: Ensures implementation plan stubs are created for feature tasks.

## Revised Decision Matrix (POST-DEBUG TRACE)

| Option | Effort | Risk | Impact | Recommendation |
|--------|--------|------|--------|----------------|
| **A: Fix stub creation check (FBSDK-013)** | Low (0.25 day) | Low | **CRITICAL - ROOT CAUSE** | ✅ **MUST FIX FIRST** |
| **B: Add `_write_failure_results()`** | Low (0.5 day) | Low | High | ✅ Implement (secondary) |
| **C: Add verbose SDK logging** | Low (0.25 day) | Low | Medium | ✅ Implement (diagnostic) |
| **D: Add SDK doctor check** | Low (0.5 day) | Low | Medium | ✅ Implement |
| **E: Investigate "Duration: 1s"** | N/A | N/A | **RESOLVED** | ✅ Debug trace showed root cause |
| **F: Increase SDK timeout** | Trivial | Low | **None** | ❌ Not root cause |

## Revised Implementation Tasks (POST-DEBUG TRACE)

### ⚠️ WAVE RESTRUCTURE BASED ON DEBUG TRACE FINDINGS

The debug trace at `docs/reviews/feature-build/grep_error.md` revealed the **actual error sequence**:
1. Task transitions to `design_approved` ✅
2. `verify_implementation_plan()` called
3. No plan exists → tries `_create_stub_implementation_plan()`
4. **Stub creation SKIPPED** (autobuild config check fails)
5. `PlanNotFoundError` raised
6. **SDK is NEVER called**

This means TASK-FBSDK-013 (previously Wave 3, LOW priority) is the **CRITICAL FIX**.

### Wave 1 (CRITICAL FIX - 0.25 day)
1. **TASK-FBSDK-013**: Fix stub creation autobuild config check
   - **Location**: `state_bridge.py:380-384`
   - **Problem**: Checks for `autobuild:` config, but feature tasks have `autobuild_state:` (runtime)
   - **Fix**: Relax check to recognize `autobuild_state:` presence OR `implementation_mode: task-work`
   - **Test**: Create feature task, verify stub is created, verify feature-build proceeds to SDK

### Wave 2 (Error Visibility - 0.5 day)
2. **TASK-FBSDK-010**: Add `_write_failure_results()` method
   - Add the method to `agent_invoker.py`
   - Update ALL exception handlers to call it
   - Write failure results with error details
   - Note: Only reached AFTER Wave 1 fix allows SDK invocation

3. **TASK-FBSDK-011**: Add verbose SDK invocation logging
   - Log SDK configuration BEFORE invocation
   - Log message count during streaming
   - Log exact error on failure

### Wave 3 (Preventive - 0.5 day)
4. **TASK-FBSDK-012**: Add `guardkit doctor --check=sdk` command
   - Verify Claude Code CLI in PATH
   - Test SDK authentication
   - Run trivial query to verify SDK works

**Total estimated effort**: 1.25 days (reduced from 1.5 days - Wave 0 diagnostic no longer needed)

## Revised Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SDK failing due to environment issue | **High** | High | Wave 0 diagnostic will confirm |
| Error hidden in truncated trace | **Confirmed** | High | Verbose logging will capture |
| Result writing never happens on error | **Confirmed** | High | `_write_failure_results()` fix |
| Autobuild config check too restrictive | Medium | Low | Verify and relax if needed |

## Conclusion

### Architecture Verification: ✅ SOUND

After deep-diving into the Claude Agent SDK documentation, I can confirm our architectural approach is **fundamentally correct**:

1. ✅ `query()` function usage (correct for one-off tasks)
2. ✅ `ClaudeAgentOptions` configuration (all fields correct)
3. ✅ `setting_sources=["user", "project"]` (loads skills correctly)
4. ✅ Message type handling (AssistantMessage, TextBlock, ResultMessage, etc.)
5. ✅ Error type handling (all SDK exceptions covered)
6. ✅ Content block iteration pattern

### Confirmed Root Cause

The SDK invocation is failing with an exception that occurs BEFORE the success path. Because `_write_task_work_results()` is only called on success (line 1777), error paths never write results. Coach then reports "Task-work results not found".

The "Duration: 1s" for 5 turns indicates the SDK is failing almost **immediately**, not after 600s timeout. This points to an environment/configuration issue rather than a timeout.

### Recommended Next Steps

1. **DIAGNOSTIC FIRST**: Run Wave 0 debug trace to capture the actual error
2. **CRITICAL FIX**: Implement `_write_failure_results()` for all error paths
3. **PREVENTIVE**: Add verbose logging and SDK doctor check

This is a **new finding** from deeper analysis - the SDK integration is correct, but error handling doesn't persist results for Coach to analyze.

## Appendix

### A. Code Locations

| Component | File | Key Methods |
|-----------|------|-------------|
| SDK Invocation | `agent_invoker.py:1665-1818` | `_invoke_task_work_implement()` |
| Result Writing (SUCCESS) | `agent_invoker.py:1777` | `_write_task_work_results()` |
| Error Handlers (NO WRITING) | `agent_invoker.py:1785-1827` | Exception handlers |
| Coach Validation | `coach_validator.py:297-313` | `validate()` error path |
| Stub Creation | `state_bridge.py:325-385` | `_create_stub_implementation_plan()` |

### B. Test Trace Key Points

| Line | Event | Status |
|------|-------|--------|
| 56 | CLI exit code 2 | ⚠️ Non-zero exit |
| 80-86 | Task files copied to worktree | ✅ Success |
| 109-116 | State transition to design_approved | ✅ Success |
| 117-118 | **27,703 characters TRUNCATED** | 🔍 Error hidden here |
| 120-149 | Player failed, Coach feedback (5 turns) | ❌ Failed |
| 179 | Duration: 1s (abnormally fast) | ⚠️ Suggests immediate failure |

### C. SDK Documentation References

| Document | URL | Key Findings |
|----------|-----|--------------|
| Overview | `platform.claude.com/docs/en/agent-sdk/overview` | SDK architecture, ClaudeSDKClient vs query() |
| Python SDK | `platform.claude.com/docs/en/agent-sdk/python` | ClaudeAgentOptions, setting_sources, error types |
| Quickstart | `platform.claude.com/docs/en/agent-sdk/quickstart` | Message handling, streaming pattern |
| Sessions | `platform.claude.com/docs/en/agent-sdk/sessions` | Session IDs, resume functionality |
| Subagents | `platform.claude.com/docs/en/agent-sdk/subagents` | Task tool, agent definitions |

### D. SDK Architecture Alignment

| Our Code | SDK Documentation | Status |
|----------|-------------------|--------|
| `query()` for one-off | "use `query()` for single tasks" | ✅ Aligned |
| `ClaudeAgentOptions` | All documented fields used | ✅ Aligned |
| `setting_sources=["user", "project"]` | Required for skills/CLAUDE.md | ✅ Aligned |
| `permission_mode="acceptEdits"` | "Auto-approves file edits" | ✅ Aligned |
| `AssistantMessage`, `ResultMessage` | Documented message types | ✅ Aligned |
| `ProcessError`, `CLINotFoundError` | Documented error types | ✅ Aligned |

### E. Prior Review References

- **TASK-REV-F6CB**: Root cause analysis identifying 4 gaps (all fixed - but success path only)
- **TASK-REV-FB07**: Comprehensive feature-build analysis
- **TASK-REV-FB15**: Phase 2 documentation timing (performance)
- **TASK-REV-FB16**: Provenance-aware intensity (workflow optimization)

### F. Key Insight: Success Path vs Error Path

```
SUCCESS PATH (current):
  SDK query() → iterate messages → parse → _write_task_work_results() → return success
                                            ↑
                                            Results written here

ERROR PATH (current):
  SDK query() → exception → handler → return TaskWorkResult(success=False)
                                       ↑
                                       NO results written!

ERROR PATH (fixed):
  SDK query() → exception → _write_failure_results() → handler → return
                            ↑
                            Results written with error details
```
