---
id: TASK-AC-003
title: "Full worktree lifecycle ownership in feature-complete"
status: completed
created: 2026-04-12T08:30:00Z
updated: 2026-04-12T10:05:00Z
completed: 2026-04-12T10:05:00Z
completed_location: tasks/completed/TASK-AC-003/
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met, command spec updated with Step 0 worktree lifecycle"
priority: medium
tags: [autobuild, feature-complete, worktree, merge, command-spec]
parent_review: TASK-REV-CLEANUP
feature_id: autobuild-cleanup
implementation_mode: task-work
wave: 3
complexity: 5
depends_on:
  - TASK-AC-002
test_results:
  status: n/a
  coverage: null
  last_run: null
---

# Full worktree lifecycle ownership in feature-complete

## Description

Extend `feature-complete` to own the entire worktree lifecycle: verify completion, stage/commit remaining changes, merge to main, delete branch, then run artifact cleanup (from TASK-AC-002). This replaces the manual Claude Code orchestration currently required before `feature-complete`.

## Acceptance Criteria

- [x] New "Step 0: Worktree Merge" added before existing Step 1 in `feature-complete.md`
- [x] Step 0 verifies autobuild completion (coach approved status)
- [x] Step 0 stages and commits any remaining uncommitted changes in worktree
- [x] Step 0 merges worktree branch to main (fast-forward preferred)
- [x] Step 0 deletes the worktree branch after merge
- [x] Merge conflicts halt execution with clear error message (no auto-resolve)
- [x] `--dry-run` previews merge without executing
- [x] `--no-merge` flag skips Step 0 for cases where merge was already done manually
- [x] Existing steps (1-5) continue to function unchanged after Step 0
- [x] End-to-end flow: single `/feature-complete FEAT-XXX` takes completed feature from worktree to fully cleaned up

## Implementation Notes

- Fast-forward merge preferred for cleaner history; merge commit as fallback
- If worktree has uncommitted changes, commit them with message: `chore: final changes for {TASK-ID}`
- If merge conflict: print conflicting files, suggest manual resolution, exit with clear instructions
- `--no-merge` is important for backwards compatibility — existing workflow can still do manual merge then run `feature-complete`
- File: `installer/core/commands/feature-complete.md`
- Consider: should `--force` also skip merge confirmation, or only `--force --no-merge`?
