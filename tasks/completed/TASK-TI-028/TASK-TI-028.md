---
id: TASK-TI-028
title: Remove duplicated settings.json from weighted-evaluation extension
status: completed
created: 2026-03-30T12:00:00Z
updated: 2026-03-30T18:00:00Z
completed: 2026-03-30T18:00:00Z
completed_location: tasks/completed/TASK-TI-028/
priority: low
tags: [template, weighted-evaluation, extends, cleanup]
task_type: implementation
complexity: 2
parent_review: TASK-REV-4F71
feature_id: FEAT-TI
implementation_mode: direct
wave: 5
depends_on: []
---

# Task: Remove Duplicated settings.json from Weighted-Evaluation Extension

## Description

The `langchain-deepagents-weighted-evaluation` template includes a full `settings.json` that is nearly identical to the base template's `settings.json`. The only addition is the "Hooks" layer mapping. With the extends mechanism (TASK-TI-027) now supporting file overlay and manifest merging, this duplication is unnecessary.

## Finding Reference

TASK-REV-4F71, Finding F1 (LOW severity).

## What to Do

1. Verify the extends overlay mechanism correctly inherits `settings.json` from the base template when the extension doesn't provide one
2. If the "Hooks" layer needs to be added, determine the correct approach:
   - Option A: Add "Hooks" to the base `settings.json` (it's used by both templates)
   - Option B: Create a minimal extension `settings.json` that only defines the delta
   - Option A is preferred since `lib/checkpoint_hooks.py` and `lib/sprint_contract.py` already exist in the base
3. Delete the duplicated `settings.json` from `installer/core/templates/langchain-deepagents-weighted-evaluation/`
4. Verify installation works correctly with `guardkit init langchain-deepagents-weighted-evaluation`

## Acceptance Criteria

- [x] Extension template no longer contains a full duplicate `settings.json`
- [x] "Hooks" layer is accessible in projects using either template
- [x] `guardkit init langchain-deepagents-weighted-evaluation` still works correctly
- [x] Existing tests pass
