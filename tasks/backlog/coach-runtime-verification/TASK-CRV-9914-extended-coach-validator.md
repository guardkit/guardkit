---
id: TASK-CRV-9914
title: Extend CoachValidator with runtime verification methods
status: backlog
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
priority: medium
tags: [coach, runtime-verification, architecture, refactor]
task_type: feature
parent_review: TASK-REV-3F40
feature_id: FEAT-8290
wave: 3
implementation_mode: task-work
complexity: 6
dependencies: [TASK-CRV-412F, TASK-CRV-537E]
---

# Task: Extend CoachValidator with runtime verification methods

## Description

Move runtime verification from the orchestrator (TASK-CRV-537E) into the CoachValidator class for cleaner architecture. The Coach already runs test commands via `subprocess.run()` — extend this to support arbitrary command_execution criteria.

This replaces the orchestrator-level execution (Wave 1 workaround) with a proper Coach-level verification path (Path D).

## Acceptance Criteria

- [ ] `CoachValidator` has `verify_runtime_criteria()` method accepting `List[ClassifiedCriterion]`
- [ ] Method executes `extracted_command` for each `command_execution` criterion in worktree
- [ ] Results returned as `Dict[str, bool]` (criterion text → pass/fail)
- [ ] Timeout protection: 60s per command, configurable via `runtime_timeout` parameter
- [ ] Safety: only executes commands matching accepted patterns from criteria classifier
- [ ] `validate_requirements()` calls `verify_runtime_criteria()` for Path D criteria
- [ ] Orchestrator-level execution from CRV-537E can be deprecated/removed
- [ ] Comprehensive tests including timeout, failure, and success scenarios

## Implementation Notes

Extends the existing test execution infrastructure in `coach_validator.py`:

```python
async def verify_runtime_criteria(
    self,
    criteria: List[ClassifiedCriterion],
) -> Dict[str, bool]:
    """Verify command_execution criteria by running extracted commands."""
    results = {}
    for criterion in criteria:
        if criterion.criterion_type != CriterionType.COMMAND_EXECUTION:
            continue
        if not criterion.extracted_command:
            results[criterion.text] = False
            continue
        results[criterion.text] = await self._execute_criterion(criterion)
    return results
```

## Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py` (add runtime verification)
- `guardkit/orchestrator/autobuild.py` (remove orchestrator-level execution if integrated)
- `tests/unit/test_coach_validator.py` (comprehensive runtime verification tests)
