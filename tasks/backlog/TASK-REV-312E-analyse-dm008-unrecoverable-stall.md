---
id: TASK-REV-312E
title: Analyse TASK-DM-008 unrecoverable stall after TASK-FIX-CKPT fixes
status: review_complete
created: 2026-02-08T00:00:00Z
updated: 2026-02-08T00:00:00Z
priority: high
tags: [autobuild, stall-detection, debugging, FEAT-D4CE]
task_type: review
complexity: 5
dependencies: []
related_tasks:
  - TASK-REV-AB01  # Original review that found JSON path + ordering bugs
  - TASK-FIX-CKPT  # Fix that was applied (JSON path + approval ordering)
  - TASK-AB-SD01   # Original stall detection implementation
feature: FEAT-D4CE
---

# Analyse TASK-DM-008 Unrecoverable Stall (Post TASK-FIX-CKPT)

## Description

FEAT-D4CE (Design mode for Player-Coach loops) was re-run after applying the TASK-FIX-CKPT fixes (commit `bc96d95b`). Waves 1-2 now succeed (7 tasks pass including the previously-stalling TASK-DM-002), confirming those fixes work. However, TASK-DM-008 ("Add design change detection") in Wave 3 hits UNRECOVERABLE_STALL after 2 turns.

This review must determine whether TASK-DM-008's stall is:
1. A **new/different bug** in the orchestrator (regression or edge case not covered by TASK-FIX-CKPT)
2. A **legitimate stall** where the Player genuinely cannot make tests pass for this task
3. A **task definition issue** (task too complex, missing prerequisites, wrong task_type)

### Critical constraint: Do NOT undo TASK-FIX-CKPT or TASK-AB-SD01 architecture

The prior fixes and stall detection mechanisms are architecturally sound and confirmed working for other tasks. Any recommendations must preserve:
- `_extract_tests_passed()` nested JSON path lookup (TASK-FIX-CKPT)
- Approval-before-stall-detection ordering (TASK-FIX-CKPT)
- Two-mechanism stall detection: no-passing-checkpoint + repeated-feedback (TASK-AB-SD01)
- Checkpoint rollback-on-pollution behavior

## Context

### Timeline of FEAT-D4CE attempts

1. **Attempt 1** (`error_output.md`): Failed at feature validation - doubled path bug (`design-mode-player-coach/design-mode-player-coach/...`). Fixed by FEAT-FPP.
2. **Attempt 2** (`still_failing_after_TASK_FIX_CKPT.md`): Fresh start. TASK-DM-001 + DM-002 succeeded. Run continued. Some tasks passed.
3. **Attempt 3** (`revised_paths_output.md`): Fresh start after path fixes. TASK-DM-002 hit false positive stall. Led to TASK-REV-AB01.
4. **TASK-REV-AB01**: Root cause analysis found JSON path mismatch + approval ordering bug.
5. **TASK-FIX-CKPT** (commit `bc96d95b`): Applied fixes for both bugs.
6. **Attempt 4** (`unrecoverable_stall_output.md`): Resume after fixes. Waves 1-2 pass (5 tasks). Wave 3: TASK-DM-005 approved (1 turn), TASK-DM-008 stalls after 2 turns. Feature fails.

### What the TASK-DM-008 stall log shows

- **Turn 1**: Player creates 2 files, modifies 3. Tests report as "0 tests (failing)".
  - Coach: `tests_passed=None`, `all_gates_passed=False` -> feedback: "Tests did not pass"
  - Checkpoint: `tests: fail, count: 0`
- **Turn 2**: Player creates 3 files, modifies 4. Tests still "0 tests (failing)".
  - Coach: `tests_passed=None`, `all_gates_passed=False` -> feedback: "Tests did not pass"
  - Checkpoint: `tests: fail, count: 0`
  - Stall detection: 2 consecutive failures, no passing checkpoint -> UNRECOVERABLE_STALL

### Key difference from TASK-DM-002 false positive

- TASK-DM-002 (prior bug): Coach **approved** but stall detector overrode it (false positive)
- TASK-DM-008 (this case): Coach gives **feedback** (not approval) on both turns. `tests_passed=None` (not `true`). The stall detector is responding to genuine consecutive failures.

## Acceptance Criteria

- [ ] Root cause of TASK-DM-008 stall identified (orchestrator bug vs legitimate failure vs task issue)
- [ ] Determine why `tests_passed=None` on both turns (Player not writing/running tests? Tests failing? Wrong test detection?)
- [ ] Review task_work_results.json for TASK-DM-008 turns 1 and 2 to see what Player actually did
- [ ] Check if TASK-DM-008 task definition has appropriate acceptance criteria and is achievable in autobuild
- [ ] Assess whether stall detection threshold (2 consecutive failures) is too aggressive for tasks that need >2 turns
- [ ] Determine if any code changes are needed vs task definition changes vs configuration changes
- [ ] Verify all recommendations preserve TASK-FIX-CKPT and TASK-AB-SD01 architecture
- [ ] Provide actionable next steps to unblock FEAT-D4CE Wave 3+

## Investigation Checklist

### 1. Examine TASK-DM-008 Player Reports
- [ ] Read `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-008/player_turn_1.json`
- [ ] Read `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-008/player_turn_2.json`
- [ ] Read `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-008/task_work_results.json`
- [ ] Check `tests_passing`, `coverage`, `files_created` in Player self-report

### 2. Examine TASK-DM-008 Coach Reports
- [ ] Read `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-008/coach_turn_1.json`
- [ ] Read `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-008/coach_turn_2.json`
- [ ] Check `quality_gates.tests_passed` path (is it `null`/`None` or `false`?)
- [ ] Verify `_extract_tests_passed()` is correctly handling `None` vs `false`

### 3. Compare with Successful Tasks
- [ ] How did TASK-DM-005 (same wave) pass on turn 1 with "0 tests (failing)"?
- [ ] Was TASK-DM-005 using a different task_type/quality profile?
- [ ] What's the difference in Coach evaluation between DM-005 and DM-008?

### 4. Stall Detection Threshold Analysis
- [ ] Is 2 consecutive failures appropriate for feature-type tasks in TDD mode?
- [ ] Should the threshold be configurable per task or per wave?
- [ ] Should first-turn failures be excluded from stall counting (Player may need a "warm-up" turn)?

### 5. Task Definition Review
- [ ] Read TASK-DM-008 task definition for clarity and achievability
- [ ] Are dependencies on DM-005 properly wired (both in Wave 3)?
- [ ] Is the task scope appropriate for single-session autobuild?

## Evidence Files

| File | Purpose |
|------|---------|
| `docs/reviews/ux_design_mode/unrecoverable_stall_output.md` | Full output of attempt 4 (the stall under review) |
| `docs/reviews/ux_design_mode/still_failing_after_TASK_FIX_CKPT.md` | Earlier attempt output for comparison |
| `docs/reviews/ux_design_mode/error_output.md` | First attempt (path bug) |
| `docs/reviews/ux_design_mode/revised_paths_output.md` | Second attempt (DM-002 false positive stall) |
| `docs/reviews/ux_design_mode/feature_plan_summary.md` | Feature plan and wave structure |
| `.claude/reviews/TASK-REV-AB01-review-report.md` | Prior review: JSON path + ordering bug analysis |
| `tasks/completed/TASK-FIX-CKPT/TASK-FIX-CKPT.md` | Fix task for JSON path + ordering |
| `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-008/` | Player/Coach reports (if worktree still exists) |
| `guardkit/orchestrator/autobuild.py` | Orchestrator source (stall detection, checkpoint logic) |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Coach validation logic |

## Scope Boundaries

**In scope:**
- Root cause analysis of TASK-DM-008 stall
- Assessment of stall detection thresholds
- Task definition quality review
- Recommendations to unblock FEAT-D4CE

**Out of scope:**
- Rewriting stall detection architecture (TASK-AB-SD01 is sound)
- Reverting TASK-FIX-CKPT fixes
- Broad autobuild refactoring
- Other FEAT-D4CE tasks (they are passing)
