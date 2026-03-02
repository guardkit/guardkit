# FEAT-CF57 Unblock: Fix Dual Alias Table and Resume Freshness

## Problem Statement

FEAT-CF57 run_2 failed with `Invalid task_type value: enhancement` on TASK-INST-012 despite all 9 FEAT-CD4C (ABFIX) fixes being completed on main. Two root causes were identified:

1. **Dual alias table**: `coach_validator.py` maintains its own `TASK_TYPE_ALIASES` missing `enhancement`, while `task_types.py` has it
2. **Worktree staleness**: The resume path has no mechanism to incorporate main branch changes

## Solution Approach

Fix the immediate blocking bug (dual alias table), then add preventive measures.

## Tasks

| Task | Title | Priority | Complexity | Wave |
|------|-------|----------|------------|------|
| TASK-FIX-7531 | Consolidate coach_validator alias table | Critical | 2 | 1 |
| TASK-FIX-7532 | Fix TASK-INST-012 task_type to `feature` | Critical | 1 | 1 |
| TASK-FIX-7533 | Add `--refresh` flag for rebase-on-resume | Medium | 5 | 2 |
| TASK-FIX-7534 | Feature planner task_type validation guard | Low | 3 | 2 |

## Execution Strategy

**Wave 1** (Critical — unblocks FEAT-CF57): TASK-FIX-7531 + TASK-FIX-7532 (sequential, ~30 min)
**Wave 2** (Preventive): TASK-FIX-7533 + TASK-FIX-7534 (sequential, ~2-3 hours)

After Wave 1, recreate the FEAT-CF57 worktree with `--fresh` and resume execution.

## Parent Review

[TASK-REV-7530 Review Report](../../../.claude/reviews/TASK-REV-7530-review-report.md)
