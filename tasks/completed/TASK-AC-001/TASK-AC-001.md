---
id: TASK-AC-001
title: "Gitignore autobuild artifacts and one-time cleanup"
status: completed
created: 2026-04-12T08:30:00Z
updated: 2026-04-12T09:05:00Z
completed: 2026-04-12T09:05:00Z
previous_state: in_review
state_transition_reason: "All acceptance criteria verified"
completed_location: tasks/completed/TASK-AC-001/
priority: high
tags: [autobuild, cleanup, gitignore]
parent_review: TASK-REV-CLEANUP
feature_id: autobuild-cleanup
implementation_mode: task-work
wave: 1
complexity: 2
depends_on: []
test_results:
  status: n/a
  coverage: null
  last_run: null
---

# Gitignore autobuild artifacts and one-time cleanup

## Description

Add `.guardkit/autobuild/` and `.guardkit/archive/` to `.gitignore`, then untrack the existing 241 TASK directories (6.7MB) and prune completed feature YAML files from `.guardkit/features/`.

## Acceptance Criteria

- [x] `.guardkit/autobuild/` added to `.gitignore`
- [x] `.guardkit/archive/` added to `.gitignore`
- [x] Existing `.guardkit/autobuild/` files untracked via `git rm -r --cached` (1,417 files)
- [x] Completed feature YAML files in `.guardkit/features/` removed from tracking (15 files)
- [x] Local `.guardkit/autobuild/` directory still exists (not deleted from disk)
- [x] `feature-build` and `feature-complete` commands still function correctly
- [x] Single cleanup commit on main

## Implementation Notes

- Use `git rm -r --cached .guardkit/autobuild/` to untrack without deleting local files
- Check each `.guardkit/features/FEAT-*.yaml` — remove from git if status is `merged` or feature has no active tasks in `tasks/backlog/` or `tasks/in_progress/`
- Keep feature YAMLs for any features with active/in-progress tasks
- Place `.gitignore` entries after existing `.guardkit/worktrees/` entry (line 80)
