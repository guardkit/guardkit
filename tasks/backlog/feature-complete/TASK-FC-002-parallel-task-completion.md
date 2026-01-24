---
id: TASK-FC-002
title: Implement parallel task completion
status: backlog
created: 2026-01-24T12:00:00Z
updated: 2026-01-24T12:00:00Z
priority: high
tags: [feature-complete, task-completion, asyncio, parallel]
complexity: 3
parent_review: TASK-REV-FC01
feature_id: FEAT-FC-001
implementation_mode: task-work
wave: 1
dependencies: []
estimated_minutes: 60
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

- [ ] `_complete_tasks_phase()` method implemented
- [ ] All tasks complete in parallel (not sequential)
- [ ] Individual task failure doesn't block others
- [ ] Task files moved to `tasks/completed/{date}/{feature-slug}/`
- [ ] Progress displayed during execution
- [ ] Final summary shows completed/failed counts
- [ ] Unit tests for parallel completion logic

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

1. **Already completed tasks**: Skip, don't re-complete
2. **Task file not found**: Log warning, continue
3. **Git operations fail**: Log error, mark task as failed, continue
4. **Empty feature**: Handle gracefully, display "No tasks to complete"
