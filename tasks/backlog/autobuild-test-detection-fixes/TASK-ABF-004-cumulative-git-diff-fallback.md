---
id: TASK-ABF-004
title: Add cumulative git diff fallback for test detection
status: backlog
created: 2026-02-16T00:00:00Z
updated: 2026-02-16T00:00:00Z
priority: medium
tags: [autobuild, enhancement, test-detection, coach-validator]
task_type: feature
complexity: 5
parent_review: TASK-REV-F3BE
feature_id: FEAT-ABF
wave: 2
implementation_mode: task-work
dependencies: [TASK-ABF-001, TASK-ABF-002]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add cumulative git diff fallback for test detection

## Description

Add a tertiary fallback in `coach_validator.py`'s `_detect_test_command` method that uses a cumulative git diff (from the task's first checkpoint parent to HEAD) to find test files created during the current task's lifetime. This handles the case where checkpoint commits make test files invisible to both the primary detection (from `task_work_results`) and the fallback glob pattern.

## Context

From review TASK-REV-F3BE (Rec 1): After each turn, `git add -A && git commit` commits all files including tests. On subsequent turns, `git diff --name-only HEAD` only shows changes since the LAST checkpoint, not since the task started. The cumulative diff looks across ALL checkpoints for the current task, finding test files that were created in any previous turn.

**IMPORTANT**: Do NOT use a broad `glob("tests/**/test_*.py")` approach. In shared worktrees (feature mode), multiple tasks run in the same worktree. A broad glob would pick up test files from OTHER parallel tasks with unresolved dependencies. This concern is documented at `coach_validator.py:1557-1560`. The cumulative diff is safe because it only finds files changed during the current task's turns.

## Acceptance Criteria

- [ ] Tertiary fallback activates only when primary detection AND task-ID glob both fail
- [ ] Uses `git diff --name-only <first-checkpoint-parent> HEAD` to find all changed files
- [ ] Filters to test files matching `test_*.py` or `*_test.py` patterns
- [ ] Verifies test files still exist in the worktree (not deleted)
- [ ] Returns `pytest <files> -v --tb=short` command if test files found
- [ ] Does NOT find test files from other tasks in shared worktrees
- [ ] Handles missing checkpoint gracefully (returns None, falls through)
- [ ] New test: finds test files across checkpoint boundaries
- [ ] New test: does NOT find test files from pre-task commits
- [ ] New test: handles no checkpoint commits gracefully
- [ ] Existing tests pass without modification

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` (lines 1544-1611) - `_detect_test_command`, insert after line 1611
- `guardkit/orchestrator/quality_gates/coach_validator.py` (lines 1557-1560) - Shared worktree concern documentation
- `guardkit/orchestrator/worktree_checkpoints.py` (lines 378-427) - Checkpoint commit format
- `tests/unit/test_coach_validator.py` - Existing test patterns for `_detect_test_command`

## Implementation Guidance

```python
# In _detect_test_command, after line 1611 (before returning None):
# Tertiary fallback: find test files created during this task's lifetime
try:
    first_checkpoint = self._find_first_checkpoint_parent()
    if first_checkpoint:
        result = subprocess.run(
            ["git", "diff", "--name-only", first_checkpoint, "HEAD"],
            cwd=str(self.worktree_path),
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            changed_files = result.stdout.strip().split("\n")
            test_files = [
                f for f in changed_files
                if f.strip() and (
                    Path(f).name.startswith("test_") and f.endswith(".py")
                    or f.endswith("_test.py")
                ) and (self.worktree_path / f).exists()
            ]
            if test_files:
                files_str = " ".join(sorted(test_files))
                logger.info(
                    f"Found test files via cumulative diff for {task_id}: "
                    f"{len(test_files)} file(s)"
                )
                return f"pytest {files_str} -v --tb=short"
except Exception as e:
    logger.debug(f"Cumulative diff fallback failed: {e}")
```

The `_find_first_checkpoint_parent` helper needs to find the git commit before the first autobuild checkpoint for this task. Checkpoint commits have messages like `autobuild: checkpoint <task_id> turn <N>` — use `git log --oneline --grep` to find the earliest one, then reference its parent (`<commit>~1`).

## Test Execution Log
[Automatically populated by /task-work]
