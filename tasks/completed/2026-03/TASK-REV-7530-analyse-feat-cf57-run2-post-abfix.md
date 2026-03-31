---
id: TASK-REV-7530
title: Analyse FEAT-CF57 run_2 failure post FEAT-CD4C fixes
task_type: review
parent_review: TASK-REV-A17A
feature_id: FEAT-CD4C
status: review_complete
created: 2026-03-02T20:30:00Z
updated: 2026-03-02T21:30:00Z
priority: high
complexity: 4
tags: [autobuild, orchestrator, post-mortem, regression, worktree]
decision_required: true
review_results:
  mode: diagnostic
  depth: standard
  findings_count: 6
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-7530-review-report.md
  implementation_tasks:
    - TASK-FIX-7531
    - TASK-FIX-7532
    - TASK-FIX-7533
    - TASK-FIX-7534
  completed_at: 2026-03-02T21:30:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse FEAT-CF57 run_2 Failure Post FEAT-CD4C Fixes

## Context

**Feature under test:** FEAT-CF57 — AutoBuild Instrumentation and Context Reduction (14 tasks, 6 waves)
**Failed task:** TASK-INST-012 — Enrich system seeding with actual template markdown content
**Error:** `Invalid task_type value: enhancement` (CONFIGURATION_ERROR)
**Run log:** `docs/reviews/reduce-static-markdown/run_2.md`

**Parent review:** TASK-REV-A17A — the original analysis that identified the `enhancement` alias gap and other failure modes
**Fix feature:** FEAT-CD4C — AutoBuild Orchestrator Failure Fixes (9 tasks, all completed)

### The Paradox

FEAT-CD4C was created specifically to fix the failures found in TASK-REV-A17A. All 9 ABFIX tasks are marked completed on main:
- TASK-ABFIX-001: Added `enhancement` as alias for `feature` in `TaskType` aliases
- TASK-ABFIX-002: Added task_type validation at feature load time (fail-fast)
- TASK-ABFIX-003: Config error flag and fast-exit
- TASK-ABFIX-004: Per-turn timeout budgeting with Coach grace period
- TASK-ABFIX-005: Coach test isolation for parallel waves
- TASK-ABFIX-006: Timeout vs cancelled logging reconciliation
- TASK-ABFIX-007: Feature validate pre-flight CLI command
- TASK-ABFIX-008: Doc level false positives and bootstrap fixture exclusion
- TASK-ABFIX-009: Integration tests for all the above

**Yet run_2 of FEAT-CF57 still fails with the exact same `enhancement` task_type error.** The fix exists at `guardkit/models/task_types.py:257` on main, but the FEAT-CF57 worktree at `.guardkit/worktrees/FEAT-CF57` apparently did not contain it.

## Review Objectives

### 1. Root Cause: Worktree Staleness
- **Hypothesis:** The FEAT-CF57 worktree was created before FEAT-CD4C fixes landed on main, and `--resume` reused the stale worktree without rebasing/merging main.
- Confirm whether the worktree branch `autobuild/FEAT-CF57` has the ABFIX commits.
- Determine if the feature orchestrator's `--resume` path skips rebase/merge of main.

### 2. Worktree Freshness Gap Analysis
- Does the feature orchestrator ever rebase/merge main into a resumed worktree?
- Should it? What are the trade-offs (merge conflicts vs stale code)?
- Is there a `--refresh` or `--rebase` flag, or should one be added?

### 3. FEAT-CD4C Fix Validation
- Are ALL 9 ABFIX fixes present on main and functioning correctly?
- Does `guardkit/models/task_types.py` alias table include `enhancement`?
- Does `coach_validator.py` use the centralised alias table (not a separate copy)?
- Does the feature loader validate task_type at load time (TASK-ABFIX-002)?

### 4. TASK-INST-012 Task File Issue
- The task file has `task_type: enhancement` — should this be changed to `feature` regardless?
- Should the feature planner avoid generating non-canonical task_type values?

### 5. Remaining FEAT-CF57 Risk Assessment
- 8 tasks remain pending (TASK-INST-004 through TASK-INST-009, TASK-INST-005a/b/c)
- With ABFIX fixes applied, would a fresh run succeed?
- Are there any other task files with non-canonical task_type values?

## Acceptance Criteria

- [ ] Root cause of worktree staleness confirmed with evidence (git log, commit check)
- [ ] Gap identified: resume path does/doesn't rebase main
- [ ] All 9 ABFIX fixes verified present on main
- [ ] Recommendation: fix TASK-INST-012 task_type OR ensure worktree freshness
- [ ] Risk assessment for remaining 8 FEAT-CF57 tasks
- [ ] Actionable recommendations (fix task file, add rebase-on-resume, or both)

## Key Files to Examine

- `docs/reviews/reduce-static-markdown/run_2.md` — Full run log
- `.guardkit/features/FEAT-CF57.yaml` — Feature definition and execution state
- `.guardkit/features/FEAT-CD4C.yaml` — Fix feature (all tasks completed)
- `tasks/backlog/autobuild-instrumentation/TASK-INST-012-enrich-system-seeding.md` — Failed task
- `guardkit/models/task_types.py` — TaskType enum and alias table
- `guardkit/orchestrator/quality_gates/coach_validator.py` — Coach validation (error source)
- `guardkit/orchestrator/feature_orchestrator.py` — Feature orchestration and worktree management
- `guardkit/orchestrator/autobuild.py` — AutoBuild orchestrator
- `tasks/completed/TASK-ABFIX-001/TASK-ABFIX-001-add-enhancement-alias.md` — The specific fix

## Review Mode

This is a **diagnostic review** — analyse the gap between "fixes landed on main" and "fixes not present in worktree at runtime". The outcome should be actionable recommendations, not implementation.
