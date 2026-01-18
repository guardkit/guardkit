---
id: TASK-FBSDK-002
title: Write task_work_results.json after SDK parse in AgentInvoker
status: backlog
created: 2026-01-18T12:15:00Z
updated: 2026-01-18T12:15:00Z
priority: critical
tags: [feature-build, agent-invoker, coach-validator, sdk-coordination]
complexity: 5
parent_review: TASK-REV-F6CB
feature_id: FEAT-FBSDK
implementation_mode: task-work
wave: 1
conductor_workspace: feature-build-sdk-wave1-2
depends_on: []
---

# Task: Write task_work_results.json after SDK parse in AgentInvoker

## Description

When `AgentInvoker.invoke_player()` delegates to task-work via SDK, it parses the stream output using `TaskWorkStreamParser` but never persists the parsed results to disk. The `CoachValidator` expects to read quality gate results from `.guardkit/autobuild/{task_id}/task_work_results.json`, but this file is never created.

## Root Cause

The current code flow:
1. `_invoke_task_work_implement()` streams SDK output
2. `TaskWorkStreamParser.to_result()` extracts quality gate data
3. `_create_player_report_from_task_work()` creates `player_turn_{turn}.json`
4. **MISSING**: No `task_work_results.json` is written

The `TaskWorkResult` dataclass holds the parsed data in memory, but it's never persisted.

## Implementation

Add result persistence to `AgentInvoker._invoke_task_work_implement()`:

```python
async def _invoke_task_work_implement(
    self,
    task_id: str,
    mode: str,
    documentation_level: str,
) -> TaskWorkResult:
    """Invoke task-work --implement-only via SDK."""
    # ... existing SDK streaming code ...

    # Parse results from stream
    result_data = parser.to_result()

    # NEW: Persist results for CoachValidator
    results_path = self._get_task_work_results_path(task_id)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, 'w') as f:
        json.dump(result_data, f, indent=2)
    logger.info(f"Wrote task-work results to {results_path}")

    return TaskWorkResult(
        success=True,
        data=result_data,
        error=None,
    )

def _get_task_work_results_path(self, task_id: str) -> Path:
    """Get path for task-work results JSON."""
    return self.worktree_path / ".guardkit" / "autobuild" / task_id / "task_work_results.json"
```

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py`
  - Add `_get_task_work_results_path()` method
  - Modify `_invoke_task_work_implement()` to persist results

## Acceptance Criteria

- [ ] `task_work_results.json` is created after successful SDK execution
- [ ] `task_work_results.json` contains quality gate data (tests, coverage, arch review)
- [ ] CoachValidator can read and parse the results file
- [ ] File is created even on timeout (with partial data)
- [ ] Unit tests verify file creation
- [ ] Integration test confirms Coach validation succeeds

## Testing Strategy

1. **Unit Test**: Mock SDK stream, verify JSON file created with expected structure
2. **Integration Test**: Run feature-build, verify Coach validation reads file
3. **Edge Case**: Timeout should still write partial results

## Schema for task_work_results.json

```json
{
  "test_results": {
    "all_passed": true,
    "failed": 0,
    "total": 15
  },
  "coverage": {
    "line": 85.5,
    "branch": 75.0,
    "threshold_met": true
  },
  "code_review": {
    "score": 82
  },
  "plan_audit": {
    "violations": 0
  },
  "requirements_met": ["criterion 1", "criterion 2"],
  "phases": {
    "phase_3": {"detected": true, "completed": true},
    "phase_4": {"detected": true, "completed": true},
    "phase_4.5": {"detected": true, "completed": true}
  },
  "files_modified": ["src/main.py"],
  "files_created": ["tests/test_main.py"]
}
```

## Related Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` - Consumer of results
- `guardkit/orchestrator/paths.py` - Should add centralized path method

## Notes

This is a P0 blocking fix. Without this file, Coach always returns "feedback" and feature-build fails after max_turns.
