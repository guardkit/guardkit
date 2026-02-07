---
id: TASK-FPP-001
title: Fix FEAT-D4CE.yaml with correct file paths
status: completed
created: 2026-02-07T20:00:00Z
updated: 2026-02-07T21:05:00Z
completed: 2026-02-07T21:05:00Z
priority: high
tags: [fix-feature-plan-paths, quick-fix]
complexity: 1
task_type: feature
implementation_mode: direct
parallel_group: 1
parent_review: TASK-REV-FP01
feature_id: FEAT-FPP
dependencies: []
---

# Fix FEAT-D4CE.yaml with correct file paths

## Description

Correct the 8 invalid `file_path` entries in `.guardkit/features/FEAT-D4CE.yaml` to match the actual task files on disk. This unblocks the existing FEAT-D4CE feature for `feature-build`.

## Acceptance Criteria

- [x] All 8 `file_path` values in FEAT-D4CE.yaml match actual files on disk
- [x] `guardkit autobuild feature FEAT-D4CE` passes validation (no "Task file not found")
- [x] No other fields in the YAML are modified

## Files to Modify

- `.guardkit/features/FEAT-D4CE.yaml`

## Implementation Details

Replace each `file_path` with the correct value:

| Task | Current (wrong) | Correct |
|------|-----------------|---------|
| DM-001 | `tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-001-extend-task-frontmatter-for-design-urls.md` | `tasks/backlog/design-mode-player-coach/TASK-DM-001-extend-task-frontmatter-design-urls.md` |
| DM-002 | `tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-002-implement-mcp-facade-for-design-extraction.md` | `tasks/backlog/design-mode-player-coach/TASK-DM-002-implement-mcp-facade-design-extraction.md` |
| DM-003 | `tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-003-implement-phase-0-design-extraction-in-autobuild.md` | `tasks/backlog/design-mode-player-coach/TASK-DM-003-implement-phase-0-design-extraction-autobuild.md` |
| DM-004 | `tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-004-generate-prohibition-checklist-from-design-data.md` | `tasks/backlog/design-mode-player-coach/TASK-DM-004-generate-prohibition-checklist.md` |
| DM-005 | `tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-005-implement-browserverifier-abstraction.md` | `tasks/backlog/design-mode-player-coach/TASK-DM-005-implement-browser-verifier-abstraction.md` |
| DM-006 | `tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-006-implement-ssim-comparison-pipeline.md` | `tasks/backlog/design-mode-player-coach/TASK-DM-006-implement-ssim-comparison-pipeline.md` |
| DM-007 | `tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-007-integrate-design-context-into-player-coach-prompts.md` | `tasks/backlog/design-mode-player-coach/TASK-DM-007-integrate-design-context-player-coach-prompts.md` |
| DM-008 | `tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-008-add-design-change-detection-and-state-aware-handling.md` | `tasks/backlog/design-mode-player-coach/TASK-DM-008-add-design-change-detection.md` |

Execute with direct edit. No tests needed - validation by running feature-build.

## Notes

Auto-generated from TASK-REV-FP01 recommendations (R5: Quick Fix).
