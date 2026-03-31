# TASK-REV-D4B1: Analyse MAX_TURNS_EXCEEDED Failures in FEAT-CR01 AutoBuild

---
task_id: TASK-REV-D4B1
title: "Analyse MAX_TURNS_EXCEEDED failures for TASK-CR-007 and TASK-CR-008 in FEAT-CR01"
status: review_complete
priority: high
task_type: review
created: 2026-02-05
feature: FEAT-CR01
related_tasks:
  - TASK-REV-AB04
  - TASK-CR-007
  - TASK-CR-008
  - TASK-CR-009
tags:
  - autobuild
  - max-turns-exceeded
  - coach-validation
  - test-detection
review_results:
  mode: architectural
  depth: standard
  findings_count: 5
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-D4B1-review-report.md
  completed_at: 2026-02-05
---

## Description

Analyse why the AutoBuild feature build for FEAT-CR01 ("Context Reduction via Graphiti Migration") is failing with MAX_TURNS_EXCEEDED on TASK-CR-007 and TASK-CR-008 despite running 30+ total turns across two separate runs.

The full error log is at: `docs/reviews/graphiti_enhancement/max_turns_exceeded.md`

## Context

### Feature Overview
- **Feature**: FEAT-CR01 - Context Reduction via Graphiti Migration
- **Total tasks**: 10 tasks across 4 waves
- **Wave 1**: PASSED (TASK-CR-001, CR-002, CR-003 all succeeded)
- **Wave 2**: PASSED (TASK-CR-004, CR-005, CR-006 all succeeded)
- **Wave 3**: FAILED - TASK-CR-009 succeeded (2 turns), but TASK-CR-007 and TASK-CR-008 both hit MAX_TURNS_EXCEEDED
- **Wave 4**: Never reached

### Two Runs Documented
1. **First run**: max_turns=5, 19 total turns, 32m 30s — CR-007 and CR-008 failed
2. **Second run** (resumed): max_turns=25, 59 total turns, 21m 26s — same tasks failed again

### Key Observations
- The `_ensure_design_approved_state` fix from TASK-REV-AB04 IS working (successful state transitions visible in logs)
- Coach feedback on EVERY turn for CR-007/CR-008: **"Tests did not pass during task-work execution"**
- Criteria Progress always **0% verified** across all turns for failing tasks
- Tests consistently showing **"0 tests (failing)"** for CR-007 and CR-008
- TASK-CR-009 (same wave) succeeded in just 2 turns — suggesting task-specific issue, not infrastructure

### Previous Fix Confirmed Working
- TASK-REV-AB04 identified and fixed a class scope break in `agent_invoker.py`
- The fix restored 15 orphaned methods including `_ensure_design_approved_state`
- This MAX_TURNS_EXCEEDED issue is a DIFFERENT problem from the AttributeError

## Investigation Areas

1. **Test Detection Failure**: Why does Coach consistently report "0 tests (failing)" for CR-007 and CR-008? Are the tasks expected to have tests? Is the test detection mechanism failing to find relevant tests?

2. **Coach Validation Loop**: Why does Coach always give "Tests did not pass during task-work execution" feedback? Is this the correct feedback for tasks that may not require tests (e.g., documentation trimming tasks)?

3. **Task Nature Mismatch**: TASK-CR-007 is "trim-orchestrators-md" and TASK-CR-008 is "trim-dataclass-pydantic-patterns" — these appear to be documentation/content reduction tasks. Should Coach require passing tests for documentation-only changes?

4. **Criteria Verification**: Why does criteria progress stay at 0% across 30+ turns? Is Player implementing changes that Coach cannot verify?

5. **Player-Coach Feedback Loop**: Is Player receiving and acting on Coach feedback effectively, or is it stuck in a loop making the same changes repeatedly?

6. **Quality Gate Configuration**: Are the quality gates (test requirements) appropriately configured for documentation-trimming tasks?

## Acceptance Criteria

- [x] Root cause identified for why TASK-CR-007 fails with MAX_TURNS_EXCEEDED
- [x] Root cause identified for why TASK-CR-008 fails with MAX_TURNS_EXCEEDED
- [x] Explanation of why TASK-CR-009 (same wave) succeeds while CR-007/CR-008 fail
- [x] Assessment of whether Coach validation criteria are appropriate for these task types
- [x] Recommendations for fix (Coach logic, task definition, or quality gate config)
- [x] Analysis of Player behaviour across turns (is it making progress or looping?)

## Error Log Reference

Full log: `docs/reviews/graphiti_enhancement/max_turns_exceeded.md` (3929 lines, 545.7KB)

Key sections:
- Lines 1-100: Feature overview, wave structure, initial state transitions
- Lines ~1325-1424: First run summary + second run start
- Lines ~3890-3929: Second run final summary
- Search for "TASK-CR-007" and "TASK-CR-008" for task-specific turn details
