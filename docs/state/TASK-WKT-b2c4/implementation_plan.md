# Implementation Plan: TASK-WKT-b2c4

## Task
Force worktree cleanup with --force flag

## Files to Modify
1. `guardkit/orchestrator/feature_orchestrator.py` - Add `force=True` parameter (1 line)

## Files to Create
1. `tests/integration/test_autobuild_fresh_mode.py` - Integration test (~40 LOC)

## Files to Extend
1. `tests/unit/test_feature_orchestrator.py` - Add unit test method (~15 LOC)

## Change Summary
```python
# Line 636: Before
self._worktree_manager.cleanup(worktree_to_cleanup)

# Line 636: After
self._worktree_manager.cleanup(worktree_to_cleanup, force=True)
```

## Estimates
- Duration: 40 minutes
- LOC Added: ~55 lines (1 prod + 54 test)
- LOC Modified: 1 line
- Complexity: 1/10

## External Dependencies
None

## Architectural Review
- Overall Score: 95/100
- Status: AUTO-APPROVED
- SOLID: 96/100
- DRY: 100/100
- YAGNI: 88/100

## Complexity Evaluation
- Score: 1/10
- Review Mode: AUTO_PROCEED
- Force Triggers: None
