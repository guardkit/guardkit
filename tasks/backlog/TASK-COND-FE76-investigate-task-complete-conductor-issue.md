---
id: TASK-COND-FE76
title: Investigate /task-complete inconsistent behavior in Conductor workspaces
status: backlog
created: 2025-11-27T18:10:00Z
updated: 2025-11-27T18:10:00Z
priority: high
tags: [conductor, task-complete, bug, phase-0, investigation]
task_type: implementation
epic: null
feature: null
requirements: []
dependencies: []
complexity: 5
effort_estimate: 2-3 hours
related_to: TASK-ENF-P0-1, TASK-ENF-P0-2, TASK-ENF-P0-4
---

# TASK-COND-FE76: Investigate /task-complete Inconsistent Behavior in Conductor Workspaces

## Context

During the completion of Phase 0 foundation tasks (TASK-ENF-P0-1, TASK-ENF-P0-2, TASK-ENF-P0-4) in a Conductor workspace, only TASK-ENF-P0-3 was automatically marked as completed and moved to `tasks/completed/2025-11/`. The other three tasks remained in `tasks/backlog/agent-invocation-enforcement/` despite being completed in the same workspace.

**Evidence**:
- Workspace output shows all tasks were worked on and completed
- Git commits show implementation was merged (b3e7500, 6ab2a8e, 301eb68)
- Only TASK-ENF-P0-3 moved to completed folder
- TASK-ENF-P0-1, TASK-ENF-P0-2, TASK-ENF-P0-4 remained in backlog with `status: backlog`

**User Report**:
> "I've implemented these tasks and completed them in a single Conductor workspace but they are still showing in the task/backlog"

## Problem Statement

### Current Behavior (BROKEN)

When using `/task-work` in Conductor workspaces:
- Implementation completes successfully
- Git commits are created
- Changes are merged to main
- **BUT**: Task files are not always moved to completed folder
- **AND**: Task metadata is not always updated to `status: completed`

### Expected Behavior (FIXED)

When `/task-work` completes successfully:
1. Implementation code is written
2. Tests pass (100%)
3. Git commit is created
4. Task file is moved from `tasks/backlog/` to `tasks/completed/YYYY-MM/`
5. Task metadata is updated: `status: completed`, `completed: <timestamp>`
6. Changes are committed to git

**All 6 steps should happen consistently, regardless of Conductor workspace.**

## Objective

Investigate and fix the `/task-complete` command (or the completion logic in `/task-work`) to ensure:
1. Task files are consistently moved to completed folder
2. Task metadata is consistently updated
3. Behavior is identical in Conductor workspaces and main repo
4. State changes are persisted across Conductor worktree boundaries

## Scope

### In Scope

**Investigation**:
- Review `/task-complete` command implementation
- Review `/task-work` Phase 5.5 completion logic
- Analyze Conductor symlink architecture impact
- Check state persistence mechanisms
- Identify why TASK-ENF-P0-3 succeeded but others failed

**Files to Review**:
- `installer/global/commands/task-complete` (if exists as Python script)
- `installer/global/commands/task-complete.md` (command specification)
- `installer/global/commands/task-work` (Phase 5.5 completion logic)
- `installer/global/commands/lib/state_manager.py` (if exists)
- `.claude/state/` directory structure (symlink target)

**Root Cause Analysis**:
- Timing issues (async completion?)
- File locking conflicts
- Symlink resolution failures
- Missing error handling
- Conductor-specific path resolution bugs

### Out of Scope

- Redesigning entire state management system (unless necessary)
- Changes to Conductor architecture
- Migration of existing tasks (separate cleanup task)

## Requirements

### FR1: Identify Root Cause

**Priority**: P0 (Critical)

**Requirement**: Determine why task completion is inconsistent in Conductor workspaces

**Investigation Steps**:
1. Review workspace output for error messages (none visible in provided log)
2. Check if `/task-complete` was called explicitly or implicitly
3. Analyze TASK-ENF-P0-3 vs TASK-ENF-P0-1/2/4 differences
4. Test task completion in Conductor workspace vs main repo
5. Check for silent failures in file operations

**Acceptance Criteria**:
- [ ] Root cause identified and documented
- [ ] Reproducible test case created
- [ ] Difference between working (P0-3) and failing (P0-1/2/4) cases understood

---

### FR2: Fix Task Completion Logic

**Priority**: P0 (Critical)

**Requirement**: Ensure task files are moved and metadata is updated consistently

**Implementation**:
- Fix file move operation to handle Conductor symlinks
- Add error handling with clear logging
- Ensure metadata updates are atomic
- Verify git commits include task file moves

**Acceptance Criteria**:
- [ ] Task files always moved to `tasks/completed/YYYY-MM/`
- [ ] Metadata always updated: `status: completed`, `completed: <timestamp>`
- [ ] Works identically in Conductor workspaces and main repo
- [ ] Error messages are clear and actionable

---

### FR3: Add State Persistence Validation

**Priority**: P1 (High)

**Requirement**: Verify state changes persist across Conductor worktree boundaries

**Implementation**:
```python
def validate_task_completion(task_id):
    """Verify task completion persisted correctly"""
    # Check file moved
    completed_path = find_task_in_completed(task_id)
    if not completed_path:
        raise ValueError(f"Task {task_id} not found in completed folder")

    # Check metadata updated
    task_data = parse_task(completed_path)
    if task_data['status'] != 'completed':
        raise ValueError(f"Task {task_id} status not updated to completed")

    if 'completed' not in task_data:
        raise ValueError(f"Task {task_id} missing completed timestamp")

    # Check git commit includes move
    git_log = subprocess.run(['git', 'log', '-1', '--name-status'], capture_output=True)
    if f'tasks/completed/' not in git_log.stdout.decode():
        logger.warning(f"Task {task_id} move not committed to git")

    return True
```

**Acceptance Criteria**:
- [ ] Validation runs after task completion
- [ ] Fails loudly if state not persisted
- [ ] Provides actionable error messages

---

### FR4: Add Integration Tests

**Priority**: P1 (High)

**Requirement**: Test task completion in Conductor workspace scenarios

**Test Cases**:

1. **Test Completion in Main Repo**
   ```python
   def test_task_completion_main_repo():
       # Given: Task in backlog
       task_id = create_test_task()

       # When: Task completed via /task-work
       run_command(f"/task-work {task_id}")

       # Then: Task moved and metadata updated
       assert task_in_completed(task_id)
       assert task_status(task_id) == "completed"
   ```

2. **Test Completion in Conductor Workspace**
   ```python
   def test_task_completion_conductor_workspace():
       # Given: Task in backlog, working in Conductor worktree
       task_id = create_test_task()
       worktree_path = create_conductor_worktree()

       # When: Task completed in worktree
       os.chdir(worktree_path)
       run_command(f"/task-work {task_id}")

       # Then: Task moved in main repo (via symlink)
       os.chdir(main_repo_path)
       assert task_in_completed(task_id)
       assert task_status(task_id) == "completed"
   ```

3. **Test Explicit /task-complete**
   ```python
   def test_explicit_task_complete():
       # Given: Task in IN_REVIEW state
       task_id = create_test_task(status="in_review")

       # When: /task-complete called
       run_command(f"/task-complete {task_id}")

       # Then: Task moved and metadata updated
       assert task_in_completed(task_id)
       assert task_metadata(task_id)['completed'] is not None
   ```

**Acceptance Criteria**:
- [ ] All 3 test cases pass
- [ ] Tests run in CI/CD pipeline
- [ ] Tests cover both implicit (Phase 5.5) and explicit (/task-complete) completion

---

## Implementation Plan

### Phase 1: Investigation (1 hour)

**Step 1.1: Review Workspace Output**
- Analyze provided workspace log for completion attempts
- Check for error messages or warnings
- Identify which command was used (implicit vs explicit)

**Step 1.2: Reproduce Issue**
- Create test task in Conductor workspace
- Run `/task-work` to completion
- Verify if task file moves and metadata updates
- Document exact failure mode

**Step 1.3: Compare Working vs Failing Cases**
- Review TASK-ENF-P0-3 (worked) vs TASK-ENF-P0-1/2/4 (failed)
- Check git history for differences
- Analyze file structure and paths

**Step 1.4: Identify Root Cause**
- Review `/task-complete` implementation
- Check symlink resolution in Conductor
- Identify missing error handling

---

### Phase 2: Fix Implementation (1-1.5 hours)

**Step 2.1: Update Task Completion Logic**
- Fix file move operation (handle symlinks)
- Add atomic metadata updates
- Improve error handling and logging

**Step 2.2: Add Validation**
- Implement post-completion validation
- Verify state persistence
- Add git commit verification

**Step 2.3: Test in Conductor**
- Run fix in Conductor workspace
- Verify state propagates to main repo
- Ensure no regressions

---

### Phase 3: Testing (0.5-1 hour)

**Step 3.1: Create Integration Tests**
- Implement 3 test cases
- Run tests in both environments
- Verify all pass

**Step 3.2: Manual Testing**
- Complete real task in Conductor workspace
- Verify file moved
- Verify metadata updated
- Verify git commit includes changes

---

## Acceptance Criteria

### Functional Requirements

- [ ] Root cause identified and documented
- [ ] Task completion works consistently in Conductor workspaces
- [ ] Task files always moved to `tasks/completed/YYYY-MM/`
- [ ] Task metadata always updated (`status: completed`, `completed: <timestamp>`)
- [ ] State changes persist across worktree boundaries
- [ ] Error messages are clear and actionable

### Testing Requirements

- [ ] Integration tests pass (3 test cases)
- [ ] Manual testing in Conductor workspace succeeds
- [ ] No regressions in main repo completion
- [ ] All edge cases handled gracefully

### Code Quality

- [ ] Clear error handling with logging
- [ ] Atomic operations (file move + metadata update)
- [ ] Symlink-aware path resolution
- [ ] Git commit verification

---

## Testing Strategy

### Reproduction Test
```bash
# 1. Create Conductor worktree
cd ~/Projects/appmilla_github/taskwright
conductor create test-workspace

# 2. Create test task
cd test-workspace
/task-create "Test task completion" priority:high

# 3. Complete task
/task-work TASK-XXX

# 4. Verify completion (should succeed, currently may fail)
cd ~/Projects/appmilla_github/taskwright  # Main repo
ls tasks/completed/2025-11/TASK-XXX*.md  # Should exist

# 5. Check metadata
grep "^status:" tasks/completed/2025-11/TASK-XXX*.md  # Should show "completed"
```

### Unit Tests
```bash
pytest tests/test_task_completion.py -v
```

### Integration Tests
```bash
pytest tests/integration/test_conductor_task_completion.py -v
```

---

## Success Metrics

**Primary Metric**: Task completion success rate in Conductor workspaces
- Target: 100% (currently ~25% based on evidence: 1/4 tasks completed)

**Secondary Metrics**:
- Task file move success: 100%
- Metadata update success: 100%
- State persistence across worktrees: 100%
- Error message clarity: Subjective, validated via manual testing

---

## Dependencies

### Blocked By
- None (can start immediately)

### Blocks
- Any task using `/task-complete` or `/task-work` in Conductor workspaces
- Phase 0 foundation tasks (ENF series) - waiting for reliable completion

---

## Risks & Mitigation

### Risk 1: Symlink Resolution Complexity

**Probability**: High
**Impact**: High
**Mitigation**:
- Use absolute paths resolved via `os.path.realpath()`
- Test with both symlinked and non-symlinked paths
- Add verbose logging for path resolution

### Risk 2: Race Conditions

**Probability**: Medium
**Impact**: Medium
**Mitigation**:
- Use atomic file operations
- Add file locking if necessary
- Implement retry logic with exponential backoff

### Risk 3: Breaking Existing Workflows

**Probability**: Low
**Impact**: High
**Mitigation**:
- Extensive testing in main repo before deploying
- Keep backward compatibility
- Add feature flag for new completion logic

---

## Rollout Plan

### Stage 1: Investigation & Fix (2 hours)
- Identify root cause
- Implement fix
- Test in Conductor workspace

### Stage 2: Validation (1 hour)
- Run integration tests
- Manual testing in real scenario
- Verify no regressions

### Stage 3: Deployment (15 min)
- Merge to main
- Update documentation if needed
- Notify users of fix

---

## Follow-Up Tasks

After this task completes:

1. **Document Conductor Best Practices**: Add Conductor-specific guidance to CLAUDE.md
2. **Audit Other Commands**: Check if other commands have similar Conductor issues
3. **Add Conductor CI/CD Tests**: Ensure all future changes test Conductor compatibility

---

## References

- **User Report**: This task description (context section)
- **Related Tasks**: TASK-ENF-P0-1, TASK-ENF-P0-2, TASK-ENF-P0-3, TASK-ENF-P0-4
- **Conductor Docs**: (if available in repo)
- **State Management**: `.claude/state/` directory

---

## Notes

- **Critical Path**: This blocks reliable use of Taskwright in Conductor workspaces
- **Priority**: HIGH - Affects developer workflow and productivity
- **Effort**: 2-3 hours (investigation + fix + testing)
- **Risk**: Medium - Fix should be straightforward once root cause identified

---

**Created**: 2025-11-27T18:10:00Z
**Priority**: HIGH
**Effort**: 2-3 hours
**Related To**: TASK-ENF-P0-1, TASK-ENF-P0-2, TASK-ENF-P0-3, TASK-ENF-P0-4
