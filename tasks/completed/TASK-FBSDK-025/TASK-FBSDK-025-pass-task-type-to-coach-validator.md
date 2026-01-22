---
id: TASK-FBSDK-025
title: Pass task_type to CoachValidator from task frontmatter
status: completed
created: 2025-01-22T21:30:00Z
updated: 2025-01-22T22:45:00Z
completed: 2025-01-22T22:45:00Z
priority: high
tags: [feature-build, autobuild, quality-gates, coach-validator, integration-fix]
complexity: 4
task_type: feature
implementation_mode: task-work
parent_review: TASK-REV-FB20
feature_id: FEAT-ARCH-SCORE-FIX
wave: 1
dependencies: []
previous_state: in_review
state_transition_reason: "All quality gates passed, tests passing (71/71)"
completed_location: tasks/completed/TASK-FBSDK-025/
quality_gates:
  tests_passed: true
  test_count: 71
  test_pass_rate: 100%
  compilation: passed
  code_review: passed
---

# Pass task_type to CoachValidator from task frontmatter

## Description

Fix the integration gap where `task_type` from task frontmatter is not passed to CoachValidator, causing all tasks to default to `TaskType.FEATURE` and require architectural review regardless of their actual type.

**Root Cause**: `autobuild.py:1590` passes only `{"acceptance_criteria": [...]}` to `CoachValidator.validate()`, omitting the `task_type` field that would allow scaffolding tasks to skip architectural review.

**Impact**: Scaffolding tasks (project setup, configuration) fail architectural review because they're treated as feature tasks requiring 60+ score.

## Acceptance Criteria

- [x] CoachValidator receives `task_type` from task frontmatter when available
- [x] Scaffolding tasks (`task_type: scaffolding`) skip architectural review
- [x] Feature tasks (`task_type: feature`) still require architectural review
- [x] Tasks without `task_type` default to feature (backward compatible)
- [x] Unit tests verify task_type is passed correctly
- [x] Integration test confirms end-to-end flow works

## Files to Modify

| File | Change | LOC |
|------|--------|-----|
| `guardkit/orchestrator/autobuild.py` | Pass task_type in `_invoke_coach_safely()` | +5 |
| `guardkit/orchestrator/autobuild.py` | Update `_run_loop()` to accept task_data | +10 |
| `guardkit/orchestrator/autobuild.py` | Update `orchestrate()` to load and pass task_data | +15 |
| `tests/unit/test_autobuild_task_type.py` | New test file for task_type passing | +80 |

## Implementation Details

### Step 1: Update `_invoke_coach_safely()` to accept task_type

```python
def _invoke_coach_safely(
    self,
    task_id: str,
    turn: int,
    requirements: str,
    player_report: Dict[str, Any],
    worktree: Worktree,
    acceptance_criteria: Optional[List[str]] = None,
    task_type: Optional[str] = None,  # NEW
) -> AgentInvocationResult:
```

### Step 2: Pass task_type to CoachValidator

Current (line 1590):
```python
task={"acceptance_criteria": acceptance_criteria or []}
```

Fix:
```python
task={
    "acceptance_criteria": acceptance_criteria or [],
    "task_type": task_type,
}
```

### Step 3: Thread task_type through call chain

The task_type needs to be passed from:
1. `orchestrate()` - load from task file via TaskLoader
2. `_run_loop()` - pass to turn execution
3. `_invoke_coach_safely()` - pass to CoachValidator

### Step 4: Load task_type from TaskLoader

In `orchestrate()` or setup phase:
```python
task_data = TaskLoader.load_task(task_id, self.repo_root)
task_type = task_data.get("frontmatter", {}).get("task_type")
```

## Test Cases

1. **Test scaffolding task skips arch review**
   - Create task with `task_type: scaffolding`
   - Run CoachValidator
   - Assert `arch_review_required=False` in profile

2. **Test feature task requires arch review**
   - Create task with `task_type: feature`
   - Run CoachValidator
   - Assert `arch_review_required=True` in profile

3. **Test missing task_type defaults to feature**
   - Create task without `task_type`
   - Run CoachValidator
   - Assert defaults to FEATURE profile

4. **Test task_type passed through call chain**
   - Mock TaskLoader to return specific task_type
   - Verify CoachValidator receives it

## Dependencies

None - this is a standalone fix.

## Notes

- This is the primary fix for the architectural review failure identified in TASK-REV-FB20
- The CoachValidator already correctly handles task_type when provided (TASK-FBSDK-021)
- The task type profiles are already correctly defined (TASK-FBSDK-020)
- This fix closes the integration gap between task file and CoachValidator

## Related Tasks

- TASK-REV-FB20: Review that identified this issue
- TASK-FBSDK-020: Task type schema (profiles are correct)
- TASK-FBSDK-021: CoachValidator profiles (handles task_type correctly)
- TASK-FBSDK-026: Verify feature-plan generates task_type
