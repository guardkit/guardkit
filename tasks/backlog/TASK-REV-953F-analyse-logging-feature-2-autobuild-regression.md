---
id: TASK-REV-953F
title: Analyse logging_feature_2 autobuild failure for regressions from DMCP fixes
status: completed
task_type: review
created: 2026-02-24T22:00:00Z
updated: 2026-02-24T23:15:00Z
priority: critical
tags: [autobuild, regression-analysis, direct-mode, criteria-pipeline, review]
complexity: 5
parent_review: TASK-REV-CECA
decision_required: false
review_results:
  mode: decision
  depth: comprehensive
  findings_count: 8
  recommendations_count: 7
  report_path: .claude/reviews/TASK-REV-953F-review-report.md
  verdict: no-regressions-different-root-cause
  decision: implement
  implementation_feature: FEAT-ASPF
  implementation_path: tasks/backlog/autobuild-synthetic-pipeline-fix/
---

# Task: Analyse logging_feature_2 autobuild failure for regressions from DMCP fixes

## Description

The second autobuild run of FEAT-3CC2 (Structured JSON Logging) on `api_test` — captured in `docs/reviews/gb10_local_autobuild/logging_feature_2.md` — failed with the **same UNRECOVERABLE_STALL** pattern as the first run (`logging_feature_1.md`), despite the four DMCP bug fixes (TASK-FIX-DMCP-001 through 004) being applied to the codebase.

The diagnostic output from the second run is nearly identical to the first:
- `requirements_met: []`
- `_synthetic: False`
- `matching_strategy: text`
- All 7 criteria rejected: "Not found in Player requirements_met"

This suggests either:
1. The fixes were NOT active in the runtime environment (e.g., not installed/reloaded)
2. The fixes were applied but introduce regressions or don't address the full causal chain
3. Additional bugs exist that weren't identified in TASK-REV-CECA

Additionally, the second run introduced a **new failure mode**: TASK-LOG-001 timed out (2400s task timeout) during Turn 3, with the Player subprocess continuing to run after the feature orchestrator declared failure — indicating a potential concurrency/cancellation issue.

## Context

### First Run (logging_feature_1.md)
- **Outcome**: UNRECOVERABLE_STALL after 3 turns on TASK-LOG-001
- **Root cause identified**: Coach could not read Player's requirements data due to:
  - `_write_direct_mode_results` dropping `requirements_addressed` (P1)
  - Coach text matching using wrong field name `requirements_met` vs `requirements_addressed` (P2)
  - `_synthetic` flag not propagated (P3)
  - Acceptance criteria loading from YAML-only parser (P4)

### Fixes Applied (TASK-FIX-DMCP-001 through 004)
- **DMCP-001**: Copy `requirements_addressed` to `task_work_results.json` — agent_invoker.py
- **DMCP-002**: Fix Coach text matching to check `requirements_addressed` first — coach_validator.py
- **DMCP-003**: Propagate `_synthetic` flag in `_write_player_report_for_direct_mode` — agent_invoker.py
- **DMCP-004**: Fix synthetic report acceptance criteria loading — agent_invoker.py

### Second Run (logging_feature_2.md)
- **Outcome**: FAILED — TASK-LOG-001 timed out after 45 minutes
- **Turn 1**: Player completed (~720s), created 12 files, modified 19, 11 tests (failing). Coach rejected 0/7 criteria — **same diagnostic output as pre-fix run**
- **Turn 2**: Player SDK timeout after 1440s. State recovery found 67 tests (failing). Coach gave timeout feedback
- **Turn 3**: Player invocation started but task-level timeout (2400s) fired. Player continued running in background. Feature orchestrator declared FAILED. Eventually Player completed (2 files created) but orchestrator had already moved on — cancellation race condition

## Pre-Review Finding: Fixes ARE Active

**CONFIRMED**: The guardkit-py package is installed as an **editable install** (`pip show guardkit-py` → `Editable project location: /home/richardwoollcott/Projects/appmilla_github/guardkit`). The `guardkit-py` CLI (`~/.local/bin/guardkit-py`) uses `/usr/bin/python3` which loads from `~/.local/lib/python3.12/site-packages` — this IS the editable install. Therefore all four DMCP source changes are active at runtime.

**This eliminates the "fixes not installed" hypothesis and shifts focus to: why do the fixes not prevent the stall?**

The `--fresh` flag in Run 2 means it started from scratch — no leftover state from Run 1.

## Review Questions

1. **Why does the Coach still show `requirements_met: []` despite DMCP-001?** The fix adds `requirements_addressed` and `requirements_met` to `task_work_results.json` from the Player report. But in Run 2, the Coach diagnostic STILL shows `requirements_met: []`. Is the Player report empty? Or is there a code path where `_write_direct_mode_results` is not reached?

2. **Is the Player report structure different in Run 2?** Run 2 used `--fresh`, so it started a clean worktree. The vLLM Player may have produced a different report structure. What does the actual `player_turn_1.json` from Run 2 contain?

3. **Is there a code path that bypasses the fixed `_write_direct_mode_results`?** The synthetic report path and the normal report path have different flows. Which path was taken on Turn 1 of Run 2? (Turn 1 was NOT synthetic — it completed normally)

4. **Did the Coach validator actually execute the fixed text matching path?** The diagnostic shows `matching_strategy: text` but `requirements_met: []`. With DMCP-002, the text matching path should check `requirements_addressed` first. Is the fix at the correct line? Does the code path actually reach the fixed line?

5. **What caused the timeout escalation?** Run 1 had UNRECOVERABLE_STALL (fast exit at 3 identical feedback turns). Run 2 hit SDK timeout on Turn 2 (1440s) and task timeout on Turn 3 (2400s). Is the model taking longer? Is the feedback loop different?

6. **Is there a cancellation/cleanup issue?** Turn 3's Player continued running after the feature orchestrator timed out and declared failure. Log line 277 shows Player still logging progress at 540s after the feature result was already printed.

7. **Were any existing tests broken by the DMCP fixes?** Verify current test state.

## Acceptance Criteria

1. Determine whether the DMCP fixes are active in the runtime environment
2. Identify any regressions introduced by the four fix tasks
3. Explain why the diagnostic output is unchanged between runs
4. Analyse the new timeout/cancellation failure mode in Run 2
5. Provide actionable recommendations with evidence

## Artifacts to Inspect

- `docs/reviews/gb10_local_autobuild/logging_feature_1.md` — First run log
- `docs/reviews/gb10_local_autobuild/logging_feature_2.md` — Second run log
- `.claude/reviews/TASK-REV-CECA-review-report.md` — Original review with findings
- `guardkit/orchestrator/agent_invoker.py` — Current state (staged changes from DMCP-001, 003, 004)
- `guardkit/orchestrator/quality_gates/coach_validator.py` — Current state (staged changes from DMCP-002)
- `tests/unit/test_agent_invoker.py` — Test changes
- `tasks/completed/TASK-FIX-DMCP-001/` through `TASK-FIX-DMCP-004/` — Fix task documentation

## Suggested Review Approach

1. **Verify fix presence**: Read current source of agent_invoker.py and coach_validator.py, confirm DMCP fix changes are present at expected locations
2. **Check installation**: Determine if the autobuild CLI used the modified source or an installed package
3. **Compare diagnostics**: Line-by-line comparison of Coach validator logs between Run 1 and Run 2
4. **Inspect test state**: Run current tests to check for regressions
5. **Analyse timeout chain**: Trace the timeout escalation from SDK timeout to task timeout to feature timeout
6. **Recommend fixes**: Provide specific, evidence-based recommendations
