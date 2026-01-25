---
id: TASK-FB-FIX-012
title: Integrate _write_task_work_results() call in _invoke_task_work_implement()
status: completed
task_type: implementation
created: 2026-01-12T14:45:00Z
completed: 2026-01-12T15:30:00Z
priority: critical
tags: [feature-build, autobuild, task-work-results, coach-validator, integration-fix]
complexity: 2
parent_review: TASK-REV-FB09
depends_on: []
blocks: [feature-build-functionality]
completed_location: tasks/completed/TASK-FB-FIX-012/
---

# Integrate _write_task_work_results() Call

## Description

Add the missing call to `_write_task_work_results()` in the `_invoke_task_work_implement()` method. This is a critical integration fix identified in TASK-REV-FB09 architectural review.

**Root Cause**: TASK-SDK-003 implemented the `_write_task_work_results()` method but never integrated it into the execution flow. The method exists at `agent_invoker.py:2012-2091` but has zero callers.

## Problem Statement

When `_invoke_task_work_implement()` successfully executes task-work:
1. ✅ Task-work runs and completes
2. ✅ Output is collected and parsed
3. ❌ `task_work_results.json` is NOT written
4. ❌ Coach validation fails ("Task-work results not found")
5. ❌ Feature-build loops until MAX_TURNS_EXCEEDED

## Target Implementation

**File**: `guardkit/orchestrator/agent_invoker.py`

**Location**: Inside `_invoke_task_work_implement()`, after line 1670 (after output collection)

**Change**:

```python
# Current code (around line 1668-1676):
# Join collected output for parsing
output_text = "\n".join(collected_output)

logger.info(f"task-work completed successfully for {task_id}")
return TaskWorkResult(
    success=True,
    output=self._parse_task_work_output(output_text),
)

# New code:
# Join collected output for parsing
output_text = "\n".join(collected_output)

# Parse output using stream parser for structured data
parser = TaskWorkStreamParser()
parser.parse_message(output_text)
parsed_result = parser.to_result()

# Write task_work_results.json for Coach validation
self._write_task_work_results(task_id, parsed_result)

logger.info(f"task-work completed successfully for {task_id}")
return TaskWorkResult(
    success=True,
    output=parsed_result,  # Use parsed result
)
```

## Secondary Fix: Update Misleading Comment

**Location**: `agent_invoker.py:435-437`

**Current**:
```python
# Create Player report from task-work results
# task-work creates task_work_results.json, but orchestrator expects
# player_turn_{turn}.json - this bridges the gap
```

**New**:
```python
# Create Player report from task-work results
# AgentInvoker._invoke_task_work_implement() writes task_work_results.json
# after parsing task-work output. This method transforms it to
# player_turn_{turn}.json format expected by the orchestrator.
```

## Acceptance Criteria

- [x] `_write_task_work_results()` is called after successful task-work completion
- [x] `task_work_results.json` is created at `.guardkit/autobuild/{task_id}/task_work_results.json`
- [x] Coach validator can read and validate the results file
- [x] Misleading comment is updated
- [x] Unit test verifies results file is written in actual flow
- [x] Integration test confirms Coach validation succeeds

## Test Strategy

### Unit Test

```python
# tests/unit/test_agent_invoker.py

@pytest.mark.asyncio
async def test_invoke_task_work_implement_writes_results_file(
    invoker_with_worktree, worktree_path
):
    """_invoke_task_work_implement writes task_work_results.json after success."""
    # Mock SDK query to return successful output
    with patch("guardkit.orchestrator.agent_invoker.query") as mock_query:
        mock_query.return_value = mock_successful_task_work_stream()

        result = await invoker_with_worktree._invoke_task_work_implement(
            task_id="TASK-001",
            mode="tdd"
        )

    assert result.success

    # Verify results file was written
    results_path = worktree_path / ".guardkit" / "autobuild" / "TASK-001" / "task_work_results.json"
    assert results_path.exists(), "task_work_results.json should be written after successful invocation"

    # Verify content has required fields
    content = json.loads(results_path.read_text())
    assert "task_id" in content
    assert "quality_gates" in content
    assert "timestamp" in content
```

### Integration Test

```python
# tests/integration/test_sdk_delegation.py

async def test_full_flow_creates_results_for_coach():
    """Full delegation flow creates results file that Coach can validate."""
    # ... setup ...

    result = await invoker._invoke_task_work_implement("TASK-001", mode="tdd")
    assert result.success

    # Verify Coach can read results
    validator = CoachValidator(worktree_path)
    results = validator.read_quality_gate_results("TASK-001")

    assert "error" not in results, f"Coach should find results: {results.get('error')}"
    assert results.get("quality_gates") is not None
```

## Files to Modify

| File | Change Type | Lines |
|------|-------------|-------|
| `guardkit/orchestrator/agent_invoker.py` | Add integration call | ~8 |
| `guardkit/orchestrator/agent_invoker.py` | Fix comment | ~4 |
| `tests/unit/test_agent_invoker.py` | Add unit test | ~25 |
| `tests/integration/test_sdk_delegation.py` | Add integration test | ~20 |

**Total estimated lines**: ~57

## Risk Assessment

**Risk Level**: Low

- Simple integration fix
- No new logic required (method already implemented and tested)
- Clear success criteria
- Easy to verify

## Related

- **Parent Review**: TASK-REV-FB09 (architectural analysis)
- **Created Method**: TASK-SDK-003 (implemented `_write_task_work_results()`)
- **Integration Tests**: TASK-SDK-004 (should have caught this)
- **Blocks**: Feature-build functionality

## Notes

This fix will unblock the feature-build Player-Coach loop by ensuring Coach can validate quality gate results from task-work execution.
