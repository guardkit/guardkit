---
id: TASK-REV-FP01
title: "Review: feature-plan generates invalid task paths causing feature validation failure"
status: review_complete
created: 2026-02-07T19:30:00Z
updated: 2026-02-07T20:00:00Z
review_results:
  mode: root-cause-analysis
  depth: standard
  findings_count: 4
  recommendations_count: 5
  report_path: .claude/reviews/TASK-REV-FP01-path-generation-review-report.md
priority: high
tags: [bug, feature-plan, validation, path-generation, root-cause]
task_type: review
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review feature-plan path generation bug

## Description

The `/feature-plan` command generates feature YAML files with **invalid task file paths**, causing `feature-build` (and `guardkit autobuild feature`) to fail validation immediately. This was observed with FEAT-D4CE (Design mode for Player-Coach loops) but is likely a systemic issue in the feature-plan path construction logic.

## Observed Symptoms

### 1. Duplicated directory segment in YAML paths
The feature YAML (`FEAT-D4CE.yaml`) records task paths with the subfolder name doubled:
```
# YAML records (WRONG):
tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-001-extend-task-frontmatter-for-design-urls.md

# Actual file location (CORRECT):
tasks/backlog/design-mode-player-coach/TASK-DM-001-extend-task-frontmatter-design-urls.md
```

### 2. Filename mismatch between YAML and actual files
Even ignoring the doubled directory, the filenames don't match:
```
# YAML filename:    TASK-DM-001-extend-task-frontmatter-for-design-urls.md
# Actual filename:  TASK-DM-001-extend-task-frontmatter-design-urls.md
```
The YAML uses longer, more verbose slugs than the actual files created on disk.

### 3. Validation failure
All 8 tasks fail validation with "Task file not found", making the entire feature unrunnable via `feature-build`.

## Root Cause Analysis Required

### Primary Investigation: Path construction in feature-plan
- Where does `/feature-plan` construct the `file_path` values written to the feature YAML?
- Is the subfolder path being concatenated twice (once as base path, once as part of the file path)?
- Are the filenames in the YAML generated independently from the actual file creation, causing drift?

### Secondary Investigation: Filename slug generation
- The YAML filenames use different word-separation than the actual files (e.g., "for-design-urls" vs "design-urls")
- Are two different slug generators being used — one for creating the actual markdown files and another for recording paths in the YAML?

### Tertiary Investigation: Validation gap
- Why doesn't `/feature-plan` validate that the paths it writes to YAML actually exist on disk before completing?
- Should there be a post-creation validation step?

## Evidence Files

- Feature plan summary: `docs/reviews/ux_design_mode/feature_plan_summary.md`
- Error output: `docs/reviews/ux_design_mode/error_output.md`
- Feature YAML: `.guardkit/features/FEAT-D4CE.yaml`
- Actual task files: `tasks/backlog/design-mode-player-coach/TASK-DM-*.md`

## Scope

### In scope
1. **Root cause**: Fix the path generation logic in `/feature-plan` so future features generate correct paths
2. **Immediate fix**: Correct the FEAT-D4CE.yaml paths so the existing feature can be built
3. **Validation**: Add post-creation validation to prevent this class of bug
4. **Test coverage**: Ensure the fix is covered by tests

### Out of scope
- Changes to the design-mode feature tasks themselves
- Feature orchestrator changes (it correctly rejects invalid paths)

## Acceptance Criteria

- [ ] Root cause identified in feature-plan path construction code
- [ ] Path generation logic fixed so subfolder is not duplicated
- [ ] Filename generation is consistent between file creation and YAML recording
- [ ] FEAT-D4CE.yaml corrected with valid paths matching actual files
- [ ] Post-creation validation added (paths in YAML resolve to real files)
- [ ] `guardkit autobuild feature FEAT-D4CE` passes validation (no "Task file not found" errors)
- [ ] Unit tests cover the path generation fix

## Implementation Notes

Key areas to investigate:
- `installer/core/commands/feature-plan.md` — the command spec
- Feature plan orchestrator / YAML generation code
- Task file creation logic vs YAML path recording logic
- Slug generation utilities
