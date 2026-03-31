# FEAT-STUB-QG: Stub Quality Gate Fixes

## Problem Statement

A 70-line stub file (`guardkit/planning/system_plan.py`) with only `pass` in its primary function body passed all AutoBuild quality gates, received Coach approval on turn 1, and moved to `in_review` — with 0 of 15 acceptance criteria verified.

Root cause analysis (TASK-REV-STUB) revealed a **critical wiring bug**: `_execute_turn()` never passes `acceptance_criteria` to the Coach. This means acceptance criteria verification has been completely non-functional since AutoBuild launch — every `coach_turn_*.json` shows `criteria_total: 0`.

## Solution Approach

**Four-task fix plan** across two waves:

1. **Wave 1 (P0)**: Wire the acceptance criteria through to the Coach (3-line fix) + create anti-stub rule
2. **Wave 2 (P1)**: Fix test discovery data gap in task-work delegation + update feature plan template

## Subtask Summary

| Task | Title | Wave | Mode | Priority |
|------|-------|------|------|----------|
| TASK-FIX-STUB-A | Wire acceptance_criteria through _execute_turn() to Coach | 1 | task-work | Critical |
| TASK-FIX-STUB-B | Create anti-stub quality rule | 1 | direct | High |
| TASK-FIX-STUB-C | Populate files_created/files_modified in delegation results | 2 | task-work | High |
| TASK-FIX-STUB-D | Add anti-stub criteria to feature plan template | 2 | direct | Medium |

## Review Provenance

- **Parent review**: TASK-REV-STUB
- **Review report**: `.claude/reviews/TASK-REV-STUB-review-report.md`
- **Review depth**: Standard (revised to comprehensive after deep-dive)
