---
id: TASK-FIX-70F3
title: Accumulate known test files across autobuild turns
status: completed
task_type: implementation
created: 2026-02-18T16:00:00Z
updated: 2026-02-18T17:30:00Z
completed: 2026-02-18T17:30:00Z
completed_location: tasks/completed/TASK-FIX-70F3/
priority: normal
tags: [autobuild, coach-validator, test-detection, shared-worktree]
complexity: 4
parent_review: TASK-REV-7EB05
feature_id: FEAT-REV7EB05-fixes
wave: 2
implementation_mode: task-work
related_tasks:
  - TASK-REV-7EB05
  - TASK-FIX-AE7E
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-18T17:00:00Z
---

# Task: Accumulate known test files across autobuild turns

## Description

`_detect_test_command` finds test files by scanning `files_created` / `files_modified` in the current turn's `task_work_results`. On iterative fix turns, the Player modifies source code but doesn't re-create or re-modify the test file — so `files_created` contains no test files, and independent test verification is skipped.

The fallback glob `tests/**/test_{task_prefix}*.py` doesn't help when the test file was named semantically (e.g., `tests/users/test_users.py`) rather than by task ID.

The cumulative git diff fallback (tertiary) should find committed test files, but in a shared worktree where TASK-DB-002 and TASK-DB-003 execute concurrently, `_find_first_checkpoint_parent()` may not correctly isolate the target task's commits.

**Source**: Finding F5 from TASK-REV-7EB05 review report.

## Acceptance Criteria

- [x] Test files detected on turn 1 are remembered and used on subsequent turns for the same task
- [x] On turns 2+ where no new test files appear in `files_created`/`files_modified`, the accumulated set from prior turns is used as the test target
- [x] Accumulated test files are only valid if they still exist on disk (existence check before use)
- [x] Accumulation is per-task (does not bleed between tasks sharing a worktree)
- [x] Existing test detection priority order is preserved (current-turn detection takes precedence over accumulated)
- [x] New tests cover: turn 1 detects test file → turn 2 reuses it for independent verification

## Implementation Notes

**Option A — Player report accumulation** (recommended):

In `_detect_test_command`, after all fallbacks fail, scan prior `player_turn_N.json` files (same as Fix 1 in TASK-FIX-AE7E) for test files:

```python
# Quaternary+ fallback: scan prior player reports for test files
if task_work_results and self.task_id:
    for prev_turn in range((turn or 1) - 1, 0, -1):
        prev_path = (
            self.worktree_path
            / ".guardkit" / "autobuild" / self.task_id
            / f"player_turn_{prev_turn}.json"
        )
        if prev_path.exists():
            prior_results = json.loads(prev_path.read_text())
            cmd = self._detect_tests_from_results(prior_results)
            if cmd:
                logger.info(
                    "Test files found via player_turn_%d.json for %s",
                    prev_turn, self.task_id
                )
                return cmd
```

**Option B — Cumulative diff fix**:

Investigate why `_find_first_checkpoint_parent()` doesn't find TASK-DB-003's turn 1 test file (`tests/users/test_users.py`) in the shared worktree with TASK-DB-002. The checkpoint commit hash for turn 1 was `3659ea3f`. If the diff from that commit to HEAD includes `tests/users/test_users.py`, the tertiary fallback should already work. Determine whether it's a timing issue (checkpoint not yet committed when diff runs) or a shared-worktree isolation issue.

Start with Option A as a reliable fallback; fix Option B if the root cause is identified.
