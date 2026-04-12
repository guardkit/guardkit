---
id: TASK-AC-002
title: "Extend feature-complete Step 5 with artifact cleanup"
status: completed
created: 2026-04-12T08:30:00Z
updated: 2026-04-12T09:15:00Z
completed: 2026-04-12T09:15:00Z
completed_location: tasks/completed/TASK-AC-002/
priority: high
tags: [autobuild, feature-complete, cleanup, command-spec]
parent_review: TASK-REV-CLEANUP
feature_id: autobuild-cleanup
implementation_mode: task-work
wave: 2
complexity: 4
depends_on:
  - TASK-AC-001
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met, command spec updated with artifact cleanup"
test_results:
  status: n/a
  coverage: null
  last_run: null
---

# Extend feature-complete Step 5 with artifact cleanup

## Description

Update the `feature-complete` command spec (`installer/core/commands/feature-complete.md`) to add artifact cleanup operations after the existing worktree cleanup in Step 5. Add local-only (gitignored) archiving of feature state before deletion.

## Acceptance Criteria

- [x] Step 5 in `feature-complete.md` includes deletion of `.guardkit/autobuild/TASK-*/` for merged tasks
- [x] Step 5 includes deletion of `.guardkit/autobuild/FEAT-*/` for the completed feature
- [x] Step 5 archives `.guardkit/features/FEAT-*.yaml` to `.guardkit/archive/FEAT-*/` before deletion
- [x] Step 5 deletes `.guardkit/features/FEAT-*.yaml` after archiving
- [x] Step 5 moves completed task files from `tasks/backlog/` to `tasks/completed/`
- [x] `--no-archive` flag documented for skipping archive step
- [x] Cleanup summary displayed to user (files deleted, bytes freed)
- [x] Command spec is internally consistent (all references updated)

## Implementation Notes

- Archive is gitignored (TASK-AC-001 adds `.guardkit/archive/` to `.gitignore`)
- No TTL pruning for archives — users can manually delete `.guardkit/archive/` when desired
- The cleanup should be idempotent — running on already-cleaned feature should be a no-op
- File: `installer/core/commands/feature-complete.md`, Step 5 starts at line ~640
- Update the "After successful merge" directory tree diagram (line ~366) to show cleanup result
