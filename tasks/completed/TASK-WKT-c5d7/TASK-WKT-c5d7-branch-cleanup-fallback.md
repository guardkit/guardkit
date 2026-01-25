---
id: TASK-WKT-c5d7
title: Add branch cleanup fallback when worktree creation fails
status: completed
created: 2026-01-08T12:07:00Z
updated: 2026-01-08T14:30:00Z
completed: 2026-01-08T14:30:00Z
priority: medium
tags: [worktree, branch-cleanup, autobuild, error-handling]
parent_task: TASK-REV-9AC5
complexity: 4
estimated_effort: 3-4 hours
review_recommendation: R3
related_findings: [Finding-3]
depends_on: [TASK-WKT-b2c4]
---

# Task: Add branch cleanup fallback when worktree creation fails

## Context

**From Review**: TASK-REV-9AC5 Finding 3 (MEDIUM severity)

After worktree cleanup fails, branch creation also fails:
```
fatal: a branch named 'autobuild/FEAT-119C' already exists
```

**Root Cause**: `WorktreeManager.create()` doesn't have fallback logic to clean up orphaned branches when worktree creation fails.

## Acceptance Criteria

- [x] Enhance `WorktreeManager.create()` to detect "branch already exists" errors
- [x] Implement fallback: `git branch -D <branch>` then retry worktree creation
- [x] Add comprehensive error handling with user-friendly messages
- [x] Add unit tests for branch cleanup fallback logic
- [ ] Add integration test for complete recovery flow
- [x] Update error messages to guide manual cleanup if automated cleanup fails

## Implementation Notes

**File to Modify**:
- `guardkit/worktrees/manager.py:354-364` (in `create()` method)

**Implementation Strategy**:
```python
try:
    self._run_git([
        "worktree", "add",
        "-b", branch_name,
        str(worktree_path),
        base_branch
    ])
except WorktreeError as e:
    if "already exists" in str(e):
        logger.warning(
            f"Branch {branch_name} exists, attempting cleanup and retry"
        )
        try:
            # Force delete the orphaned branch
            self._run_git(["branch", "-D", branch_name])
            logger.info(f"Deleted orphaned branch: {branch_name}")

            # Retry worktree creation
            self._run_git([
                "worktree", "add",
                "-b", branch_name,
                str(worktree_path),
                base_branch
            ])
            logger.info(f"Successfully created worktree after branch cleanup")

        except WorktreeError as retry_error:
            # Both attempts failed - provide manual cleanup guidance
            raise WorktreeCreationError(
                f"Failed to create worktree for {task_id} even after branch cleanup.\n"
                f"Manual cleanup required:\n"
                f"  1. git worktree prune\n"
                f"  2. git branch -D {branch_name}\n"
                f"  3. Retry the command\n"
                f"Original error: {retry_error}"
            ) from retry_error
    else:
        # Different error - re-raise with context
        raise WorktreeCreationError(
            f"Failed to create worktree for {task_id}: {str(e)}"
        ) from e
```

## Testing Strategy

**Unit Tests**:
```python
def test_create_with_existing_branch_cleanup():
    """Verify branch cleanup fallback works."""
    manager = WorktreeManager(...)

    # Simulate "branch already exists" error on first attempt
    with patch.object(manager, '_run_git') as mock_git:
        mock_git.side_effect = [
            WorktreeError("fatal: a branch named 'autobuild/TEST' already exists"),
            None,  # branch -D succeeds
            None,  # worktree add retry succeeds
        ]

        # Should succeed via fallback
        result = manager.create(
            task_id="TASK-TEST",
            base_branch="main"
        )

        # Verify git branch -D was called
        assert mock_git.call_count == 3
        assert ["branch", "-D", "autobuild/TEST"] in [
            call.args[0] for call in mock_git.call_args_list
        ]


def test_create_with_unrecoverable_error():
    """Verify unrecoverable errors provide manual cleanup guidance."""
    manager = WorktreeManager(...)

    with patch.object(manager, '_run_git') as mock_git:
        mock_git.side_effect = [
            WorktreeError("fatal: a branch named 'autobuild/TEST' already exists"),
            None,  # branch -D succeeds
            WorktreeError("fatal: some other error"),  # retry fails
        ]

        with pytest.raises(WorktreeCreationError) as exc_info:
            manager.create(task_id="TASK-TEST", base_branch="main")

        # Verify manual cleanup guidance in error message
        assert "Manual cleanup required" in str(exc_info.value)
        assert "git worktree prune" in str(exc_info.value)
```

**Integration Test**:
```bash
# 1. Create worktree
guardkit autobuild task TASK-TEST

# 2. Manually delete worktree directory but leave branch
rm -rf .guardkit/worktrees/TASK-TEST

# 3. Verify automatic recovery
guardkit autobuild task TASK-TEST --fresh
# Should automatically clean up orphaned branch and succeed
```

## Dependencies

**TASK-WKT-b2c4** (R2): Should be completed first to ensure worktree cleanup works reliably. This task handles the branch cleanup fallback.

## Estimated Complexity: 4/10

**Breakdown**:
- Error detection logic: 1/10 (straightforward)
- Branch cleanup implementation: 2/10 (simple git command)
- Retry logic: 2/10 (moderate)
- Error message improvements: 1/10 (simple)
- Testing (2 scenarios): 2/10 (moderate)

## Priority Justification

**MEDIUM**: Less common than R2 (force cleanup) but still causes manual intervention when it occurs. Improves user experience and reduces friction in `--fresh` workflow.

## References

- Review Report: `.claude/reviews/TASK-REV-9AC5-review-report.md`
- Finding 3: Branch Cleanup Gap on Fresh Start
- Recommendation R3: Lines 665-690
- Location: guardkit/worktrees/manager.py:354-364
