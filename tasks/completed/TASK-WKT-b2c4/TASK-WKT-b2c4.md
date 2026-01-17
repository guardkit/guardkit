---
id: TASK-WKT-b2c4
title: Force worktree cleanup with --force flag
status: completed
created: 2026-01-08T12:06:00Z
updated: 2026-01-08T14:50:00Z
completed: 2026-01-08T14:50:00Z
priority: high
tags: [worktree, cleanup, autobuild, feature-build, fresh-mode]
parent_task: TASK-REV-9AC5
complexity: 1
estimated_effort: 30 minutes
actual_effort: 8 minutes
review_recommendation: R2
related_findings: [Finding-2]
previous_state: in_review
state_transition_reason: "Task completed - all quality gates passed"
architectural_review_score: 95
code_review_status: approved
tests_passing: true
completed_location: tasks/completed/TASK-WKT-b2c4/
organized_files: [TASK-WKT-b2c4.md, completion-report.md]
---

# Task: Force worktree cleanup with --force flag

## Context

**From Review**: TASK-REV-9AC5 Finding 2 (MEDIUM severity)

The `--fresh` flag fails to clean up existing worktrees when they contain untracked files:
```
fatal: '.../worktrees/FEAT-119C' contains modified or untracked files, use --force to delete it
```

**Root Cause**: `FeatureOrchestrator._clean_state()` doesn't pass `force=True` to `WorktreeManager.cleanup()` at line 632.

## Acceptance Criteria

- [x] Update `_clean_state()` to pass `force=True` when called from `--fresh` mode
- [x] Verify `WorktreeManager.cleanup()` already supports `force` parameter
- [x] Add unit test for force cleanup behavior
- [x] Verify `--fresh` flag now successfully cleans up worktrees with untracked files
- [x] Add integration test for end-to-end `--fresh` workflow

## Implementation Summary

### Production Code Change
**File**: `guardkit/orchestrator/feature_orchestrator.py:636`
```python
# Before
self._worktree_manager.cleanup(worktree_to_cleanup)

# After
self._worktree_manager.cleanup(worktree_to_cleanup, force=True)
```

### Unit Tests Added
**File**: `tests/unit/test_feature_orchestrator.py`
- `test_clean_state_uses_force_cleanup` - Verifies force=True is passed
- `test_clean_state_handles_missing_worktree` - Verifies graceful handling
- `test_clean_state_resets_feature_state` - Verifies state reset

### Integration Tests Created
**File**: `tests/integration/test_autobuild_fresh_cleanup.py` (new)
- `test_fresh_cleanup_removes_worktree_with_untracked_files`
- `test_fresh_cleanup_handles_cleanup_errors_gracefully`
- `test_fresh_cleanup_with_missing_worktree_path`
- `test_fresh_cleanup_force_flag_in_cleanup_call`

## Test Results

- **Compilation**: ✅ SUCCESS
- **Unit Tests**: 3/3 PASSED
- **Integration Tests**: 4/4 PASSED
- **Regression Tests**: 21/21 PASSED

## Quality Gate Results

| Gate | Result |
|------|--------|
| Compilation | ✅ 100% |
| Tests Passing | ✅ 100% (7/7 target, 21/21 regression) |
| Architectural Review | ✅ 95/100 (AUTO-APPROVED) |
| Code Review | ✅ APPROVED |
| Plan Audit | ✅ LOW severity (auto-approved) |

## References

- Review Report: `.claude/reviews/TASK-REV-9AC5-review-report.md`
- Finding 2: Worktree Cleanup Missing Force Flag
- Recommendation R2: Lines 654-663
- Location: guardkit/orchestrator/feature_orchestrator.py:636
