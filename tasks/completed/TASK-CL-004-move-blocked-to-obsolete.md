---
id: TASK-CL-004
title: Move permanently blocked tasks to obsolete
status: completed
created: 2026-01-26T14:45:00Z
updated: 2026-01-26T14:45:00Z
priority: low
tags: [cleanup, housekeeping]
task_type: implementation
complexity: 1
parent_review: TASK-REV-BL01
feature_id: FEAT-CLEANUP
implementation_mode: direct
parallel_group: wave-2
---

# Task: Move permanently blocked tasks to obsolete

## Description

Move 2 tasks from `blocked/` to `obsolete/` as their blockers are permanent and cannot be resolved.

## Actions Required

```bash
git mv tasks/blocked/TASK-DOC-18F9-add-troubleshooting-sections.md tasks/obsolete/
git mv tasks/blocked/TASK-EXT-C7C1-create-extended-files-pwa-openai.md tasks/obsolete/
```

## Tasks Being Moved

| Task ID | Title | Blocker Reason |
|---------|-------|----------------|
| TASK-DOC-18F9 | Add troubleshooting sections | "Source files no longer exist - template directory deleted" |
| TASK-EXT-C7C1 | Create extended files for pwa-vite-specialist and openai-function-calling-specialist | "Source content does not exist - agents are stubs (~30 lines)" |

## Acceptance Criteria

- [x] Both tasks moved to tasks/obsolete/
- [x] Git history preserved via `git mv`
- [x] tasks/blocked/ is empty

## Notes

- These blockers are permanent (source files deleted/never existed)
- Obsolete directory preserves the task records for history
- Blocked directory should only contain tasks with resolvable blockers
