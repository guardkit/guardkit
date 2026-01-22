---
id: TASK-FBSDK-010
title: Add _write_failure_results() method to AgentInvoker
status: completed
created: 2026-01-19T18:30:00Z
updated: 2026-01-19T19:30:00Z
completed: 2026-01-19T20:15:00Z
priority: high
tags: [feature-build, sdk-integration, error-handling, critical-fix]
complexity: 4
parent_review: TASK-REV-FB17
wave: 1
implementation_mode: task-work
depends_on: []
completed_location: tasks/completed/TASK-FBSDK-010/
---

# TASK-FBSDK-010: Add `_write_failure_results()` Method

## Problem Statement

The `_invoke_task_work_implement()` method in `agent_invoker.py` only writes `task_work_results.json` on the **success path** (line 1777). When exceptions occur (`asyncio.TimeoutError`, `ProcessError`, `CLIJSONDecodeError`, or generic `Exception`), the error handlers return `TaskWorkResult(success=False)` **without writing any results file**.

This causes Coach to always report "Task-work results not found" on Player failures, hiding the actual error information that would enable intelligent feedback.

## Root Cause Analysis

From TASK-REV-FB17 review:

```python
# SUCCESS PATH - Results ARE written (line 1777)
self._write_task_work_results(task_id, parsed_result, documentation_level)
return TaskWorkResult(success=True, output=parsed_result)

# ERROR PATHS - Results are NOT written (lines 1785-1827)
except asyncio.TimeoutError:
    raise SDKTimeoutError(...)  # No results written

except ProcessError as e:
    return TaskWorkResult(success=False, ...)  # No results written

except CLIJSONDecodeError as e:
    return TaskWorkResult(success=False, ...)  # No results written

except Exception as e:
    return TaskWorkResult(success=False, ...)  # No results written
```

## Solution

Add a new `_write_failure_results()` method and call it from ALL exception handlers before returning/raising.

## Implementation

### Step 1: Add `_write_failure_results()` Method

Add after `_write_task_work_results()` (around line 2212):

```python
def _write_failure_results(
    self,
    task_id: str,
    error: str,
    error_type: str,
    partial_output: Optional[List[str]] = None,
) -> None:
    """Write task_work_results.json with failure status.

    Called on ALL error paths to ensure Coach receives actionable information
    instead of "results not found".

    Args:
        task_id: Task identifier (e.g., "TASK-001")
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

### Step 2: Update Exception Handlers

Update `_invoke_task_work_implement()` exception handlers (lines 1785-1827):

```python
except asyncio.TimeoutError:
    error_msg = f"task-work execution exceeded {self.sdk_timeout_seconds}s timeout"
    logger.error(error_msg)
    self._write_failure_results(task_id, error_msg, "TimeoutError", collected_output)
    raise SDKTimeoutError(error_msg)

except CLINotFoundError as e:
    error_msg = (
        "Claude Code CLI not installed. "
        "Run: npm install -g @anthropic-ai/claude-code"
    )
    logger.error(error_msg)
    self._write_failure_results(task_id, error_msg, "CLINotFoundError", collected_output)
    return TaskWorkResult(
        success=False,
        output={},
        error=error_msg,
    )

except ProcessError as e:
    error_msg = f"SDK process failed (exit {e.exit_code}): {e.stderr}"
    logger.error(error_msg)
    self._write_failure_results(task_id, error_msg, "ProcessError", collected_output)
    return TaskWorkResult(
        success=False,
        output={},
        error=error_msg,
    )

except CLIJSONDecodeError as e:
    error_msg = f"Failed to parse SDK response: {e}"
    logger.error(error_msg)
    self._write_failure_results(task_id, error_msg, "CLIJSONDecodeError", collected_output)
    return TaskWorkResult(
        success=False,
        output={},
        error=error_msg,
    )

except Exception as e:
    error_msg = f"Unexpected error executing task-work: {str(e)}"
    logger.exception(error_msg)
    self._write_failure_results(task_id, error_msg, type(e).__name__, collected_output)
    return TaskWorkResult(
        success=False,
        output={},
        error=error_msg,
    )
```

### Step 3: Add Import

Ensure `datetime` is imported at the top of `agent_invoker.py`:

```python
from datetime import datetime
```

## Acceptance Criteria

- [x] `_write_failure_results()` method added to `AgentInvoker` class
- [x] All 5 exception handlers in `_invoke_task_work_implement()` call `_write_failure_results()`
- [x] `datetime` import added at module level
- [x] Results file includes: `task_id`, `timestamp`, `completed=False`, `success=False`, `error`, `error_type`, `partial_output`
- [x] Coach can read failure results and provide specific feedback based on error type
- [x] Unit test: Simulate `ProcessError`, verify results file is written with correct error details
- [x] Unit test: Simulate `TimeoutError`, verify results file is written before exception re-raised

## Test Plan

1. **Unit Test - ProcessError**:
   ```python
   def test_write_failure_results_on_process_error():
       # Mock SDK to raise ProcessError
       # Call _invoke_task_work_implement()
       # Assert task_work_results.json exists
       # Assert results contain error_type="ProcessError"
   ```

2. **Unit Test - TimeoutError**:
   ```python
   def test_write_failure_results_on_timeout():
       # Mock SDK to timeout
       # Call _invoke_task_work_implement()
       # Assert task_work_results.json exists before SDKTimeoutError raised
       # Assert results contain error_type="TimeoutError"
   ```

3. **Integration Test - Coach Reads Error**:
   ```python
   def test_coach_receives_error_details():
       # Create failure results file manually
       # Run Coach validation
       # Assert Coach feedback includes specific error message
   ```

## Files to Modify

| File | Changes |
|------|---------|
| `guardkit/orchestrator/agent_invoker.py` | Add `_write_failure_results()`, update exception handlers |

## Notes

- This is the **critical fix** identified in TASK-REV-FB17
- Enables Coach to provide intelligent feedback based on actual errors
- Partial output is preserved for debugging even on failure
- Results file schema matches existing `_write_task_work_results()` format for consistency

## Completion Summary

**Completed**: 2026-01-19T20:15:00Z

### Implementation Verified

| Component | Status | Location |
|-----------|--------|----------|
| `_write_failure_results()` method | ✅ | Lines 2219-2290 in `agent_invoker.py` |
| TimeoutError handler | ✅ | Line 1789 |
| CLINotFoundError handler | ✅ | Line 1798 |
| ProcessError handler | ✅ | Line 1808 |
| CLIJSONDecodeError handler | ✅ | Line 1818 |
| Generic Exception handler | ✅ | Line 1828 |
| `datetime` import | ✅ | Line 10 |

### Test Results

- **74 tests passed** in `test_agent_invoker_task_work_results.py`
- **28 tests passed** in `test_state_bridge.py`
- All acceptance criteria verified

### Impact

This fix enables Coach to provide intelligent, error-specific feedback when Player encounters SDK failures, replacing the generic "Task-work results not found" message with actionable error information.
