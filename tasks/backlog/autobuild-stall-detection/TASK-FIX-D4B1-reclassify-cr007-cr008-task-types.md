---
id: TASK-FIX-D4B1
title: "Reclassify CR-007 and CR-008 task types from refactor to documentation"
status: completed
priority: critical
task_type: documentation
complexity: 1
parent_review: TASK-REV-D4B1
feature_id: FEAT-CR01
wave: 1
implementation_mode: direct
tags:
  - autobuild
  - task-type-fix
  - quick-fix
---

## Description

Change `task_type: refactor` to `task_type: documentation` in TASK-CR-007 and TASK-CR-008 task definitions. These are markdown content trimming tasks that were incorrectly classified, causing the Coach to require passing tests for documentation-only changes.

## Root Cause Reference

See [TASK-REV-D4B1 review report](.claude/reviews/TASK-REV-D4B1-review-report.md) Finding 1.

## Changes Required

1. Edit `tasks/backlog/context-reduction/TASK-CR-007-trim-orchestrators-md.md`:
   - Change `task_type: refactor` to `task_type: documentation`

2. Edit `tasks/backlog/context-reduction/TASK-CR-008-trim-dataclass-pydantic-patterns.md`:
   - Change `task_type: refactor` to `task_type: documentation`

## Acceptance Criteria

- [x] TASK-CR-007 has `task_type: documentation` in frontmatter
- [x] TASK-CR-008 has `task_type: documentation` in frontmatter
- [x] No other fields changed
