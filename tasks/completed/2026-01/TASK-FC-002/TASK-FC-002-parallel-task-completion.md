---
id: TASK-FC-002
title: Implement parallel task completion
status: completed
created: 2026-01-24T12:00:00Z
updated: 2026-01-24T18:20:00Z
completed: 2026-01-24T18:20:00Z
priority: high
tags: [feature-complete, task-completion, asyncio, parallel]
complexity: 3
parent_review: TASK-REV-FC01
feature_id: FEAT-FC-001
implementation_mode: task-work
wave: 1
dependencies: []
estimated_minutes: 60
actual_minutes: 120
previous_state: in_review
state_transition_reason: "Task completed successfully"
completed_location: tasks/completed/2026-01/TASK-FC-002/
organized_files:
  - TASK-FC-002-parallel-task-completion.md
  - test-results.md
quality_gates:
  compilation: pass
  tests_passing: pass (27/27)
  line_coverage: pass (100%)
  branch_coverage: pass (100%)
  code_review: approved
plan_audit:
  status: approved
  loc_variance: +368.5%
  extra_files: 1 (test_feature_complete_parallel.py)
  auto_approved: true
---

# Task: Implement parallel task completion

## Description

Implement the Phase 2 logic in `FeatureCompleteOrchestrator` that runs `/task-complete` for all tasks in a feature in parallel using asyncio.

## Requirements

1. Add `_complete_tasks_phase()` method to `FeatureCompleteOrchestrator`:
   - Load all tasks from feature
   - Filter to only tasks that need completion (status != completed)
   - Execute task completion in parallel using `asyncio.gather()`
   - Handle individual task failures gracefully (log, continue, report)

2. Reuse existing task completion logic:
   - Integrate with `/task-complete` command logic
   - Move task files to `tasks/completed/FEAT-XXX/` subfolder (per feature)

3. Progress display:
   - Show progress as each task completes
   - Summary at end with pass/fail counts

## Acceptance Criteria

- [x] `_complete_tasks_phase()` method implemented
- [x] All tasks complete in parallel (not sequential)
- [x] Individual task failure doesn't block others
- [x] Task files moved to `tasks/completed/{date}/{feature-slug}/`
- [x] Progress displayed during execution
- [x] Final summary shows completed/failed counts
- [x] Unit tests for parallel completion logic

## Implementation Summary

### Files Created/Modified
1. **guardkit/orchestrator/feature_complete.py** (564 lines)
   - FeatureCompleteOrchestrator with three-phase execution
   - Async parallel task completion using asyncio.gather()
   - Error isolation with return_exceptions=True
   - Feature-specific file organization

2. **tests/orchestrator/test_feature_complete_tasks.py** (701 lines)
   - 27 comprehensive test cases
   - 100% line coverage
   - 100% branch coverage

### Quality Metrics
- Tests: 27/27 passing (100%)
- Line Coverage: 100% (exceeds 80% target)
- Branch Coverage: 100% (exceeds 75% target)
- Code Quality: 90/100 (excellent)
- Architectural Review: 85/100 (approved)

## Technical Notes

```python
async def _complete_tasks_phase(self, feature: Feature) -> List[TaskCompleteResult]:
    """Complete all tasks in parallel."""
    pending_tasks = [t for t in feature.tasks if t.status != "completed"]

    console.print(f"\n[bold]Completing {len(pending_tasks)} tasks...[/bold]")

    # Create completion coroutines
    tasks = [
        asyncio.to_thread(self._complete_single_task, task, feature)
        for task in pending_tasks
    ]

    # Execute in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    completed = sum(1 for r in results if not isinstance(r, Exception) and r.success)
    failed = len(results) - completed

    console.print(f"  ✓ {completed} completed, ✗ {failed} failed")

    return results

def _complete_single_task(self, task: FeatureTask, feature: Feature) -> TaskCompleteResult:
    """Complete a single task (runs in thread)."""
    try:
        # Use existing task completion logic
        # Move to tasks/completed/{date}/{feature-slug}/
        ...
        return TaskCompleteResult(task_id=task.id, success=True)
    except Exception as e:
        return TaskCompleteResult(task_id=task.id, success=False, error=str(e))
```

## Files to Modify

- **Modify**: `guardkit/orchestrator/feature_complete.py`
- **Reference**: `installer/core/commands/task-complete.md` (reuse logic)
- **Create**: `tests/orchestrator/test_feature_complete_tasks.py`

## Edge Cases

1. **Already completed tasks**: Skip, don't re-complete ✅
2. **Task file not found**: Log warning, continue ✅
3. **Git operations fail**: Log error, mark task as failed, continue ✅
4. **Empty feature**: Handle gracefully, display "No tasks to complete" ✅
