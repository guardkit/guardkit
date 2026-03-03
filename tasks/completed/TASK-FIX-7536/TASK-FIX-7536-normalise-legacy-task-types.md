---
id: TASK-FIX-7536
title: Normalise legacy task_type values in backlog task files
task_type: refactor
parent_review: TASK-REV-7535
feature_id: FEAT-CF57
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
status: completed
completed: 2026-03-03T00:00:00Z
completed_location: tasks/completed/TASK-FIX-7536/
organized_files:
  - TASK-FIX-7536-normalise-legacy-task-types.md
autobuild:
  enabled: true
  max_turns: 3
  mode: standard
---

# Task: Normalise Legacy task_type Values in Backlog Task Files

## Description

17 task files in `tasks/backlog/` use `task_type: implementation`, which is a legacy alias that maps to `feature` at runtime via `TASK_TYPE_ALIASES`. While the alias table handles this correctly, these should be normalised to the canonical `feature` value to:

- Eliminate log noise (`Using task_type alias: 'implementation' -> 'feature'`)
- Reduce confusion when reading task frontmatter
- Align with the canonical `TaskType` enum values

## Requirements

1. Find all task files in `tasks/backlog/` with `task_type: implementation`
2. Replace with `task_type: feature`
3. Do NOT modify files in `tasks/completed/` or `tasks/review_complete/` (immutable history)

## Affected Files

Files identified by TASK-REV-7535 analysis:
- `tasks/backlog/vllm-autobuild-run2-fixes/TASK-FIX-DF01-*.md`
- `tasks/backlog/autobuild-synthetic-pipeline-fix/TASK-FIX-ASPF-001-*.md`
- `tasks/backlog/text-matching-semantic-fix/TASK-FIX-TM03-*.md`
- `tasks/backlog/progressive-disclosure/TASK-IMP-674A*.md`
- Plus ~13 others (run grep to get full list)

## Acceptance Criteria

- [x] All `task_type: implementation` values in `tasks/backlog/` changed to `task_type: feature`
- [x] No files in `tasks/completed/` or `tasks/review_complete/` modified
- [x] grep confirms zero remaining `task_type: implementation` in backlog
