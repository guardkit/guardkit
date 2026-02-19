---
id: TASK-REV-9745
title: Analyse TASK-DB-001 completion_promises stall regression introduced after 16:17 Feb 18
status: completed
created: 2026-02-18T21:30:00Z
updated: 2026-02-18T22:15:00Z
priority: high
task_type: review
tags: [autobuild, coach-validator, completion-promises, regression, stall]
complexity: 4
related_tasks:
  - TASK-FIX-0C22   # Last fix before the regression: postgresql+asyncpg:// dialect change
  - TASK-FIX-AE7E   # Cross-turn criteria memory (committed same batch)
  - TASK-FIX-4415   # psycopg2 specific feedback (committed same batch)
  - TASK-FIX-70F3   # accumulate test files across turns (committed same batch)
  - TASK-FIX-A7F1   # psycopg2 misclassification fix (committed same batch)
review_results:
  mode: decision
  depth: comprehensive
  score: 95
  findings_count: 7
  recommendations_count: 4
  decision: implement
  root_cause: "Stochastic agent behaviour — agent non-deterministically omits completion_promises. All fallbacks fail: TaskWorkStreamParser has no pattern for them, Fix 2 is agent-dependent, AE7E backward scan finds nothing when no prior turn had promises, Fix 5 silently fails because _find_task_file() does not search design_approved (where autobuild tasks always live). Initial hypothesis (TASK-FIX-0C22 → SDK turn exhaustion) was disproved: turns 2 and 3 in the failing run used only 42 and 18 turns respectively yet still produced no completion_promises."
  primary_fix: "Add design_approved to _find_task_file search dirs (trivial, 1 line). Strengthen autobuild_execution_protocol.md to make completion_promises mandatory."
  report_path: .claude/reviews/TASK-REV-9745-review-report.md
  completed_at: 2026-02-18T22:45:00Z
  revised_at: 2026-02-18T22:45:00Z
---

# Review: Analyse TASK-DB-001 completion_promises Stall Regression

## Context

The autobuild run captured in `docs/reviews/autobuild-fixes/first_task_now_fails.md` (run at ~21:17 Feb 18) shows TASK-DB-001 stalling in `UNRECOVERABLE_STALL` after 3 turns with `0/6 criteria passing` in every turn.

This is a **regression**. The run at `docs/reviews/autobuild-fixes/db_after_more_fiexes.md` (16:17 same day) passed TASK-DB-001 successfully in 2 turns, with `6/6 criteria passing` on turn 2.

## Evidence of Regression

### Failing run (21:17) — all 3 turns:
```
WARNING: Criteria verification 0/6 - diagnostic dump:
WARNING:   requirements_met: []
WARNING:   completion_promises: (not used)
WARNING:   matching_strategy: text
INFO: Criteria Progress (Turn N): 0/6 verified (0%)
```
No `Recovered X completion_promises` log appears in any turn.

### Successful run (16:17) — turn 2:
```
INFO: Recovered 6 completion_promises from agent-written player report for TASK-DB-001
INFO: Recovered 6 requirements_addressed from agent-written player report for TASK-DB-001
INFO: Criteria Progress (Turn 2): 6/6 verified (100%)
```

## Root Cause Hypothesis

The criteria matching path in `coach_validator.py` uses two strategies:
1. **ID-based matching** via `completion_promises` (preferred)
2. **Text matching** via `requirements_met` (fallback)

When `completion_promises` is absent from `task_work_results.json` AND from the agent-written `player_turn_N.json`, the fallback text-matcher runs against `requirements_met: []` — which always returns 0/6.

The `completion_promises: (not used)` diagnostic line (coach_validator.py ~line 1555) confirms the text-match strategy was used all 3 turns. The absence of any `Recovered X completion_promises` log (agent_invoker.py Fix 2, ~line 1620) means the agent-written `player_turn_N.json` either:
- (a) was not present before `_build_player_report_from_task_work_results()` overwrote it, or
- (b) was present but contained no `completion_promises`.

## Commits Introduced Between the Two Runs

All committed between 17:08 and 20:07 on Feb 18:

| Commit | Time | Task | Description |
|--------|------|------|-------------|
| edb5fd18 | 17:22 | TASK-FIX-AE7E | Cross-turn criteria memory — added backward scan in `_load_completion_promises` |
| 22c32d91 | 17:23 | TASK-FIX-A7F1 | psycopg2 misclassification fix in coach_validator |
| 7f15c9ff | 17:44 | TASK-FIX-70F3 | Accumulate test files across turns in coach_validator |
| 4fe1a14b | 17:43 | TASK-FIX-4415 | Specific feedback for psycopg2 error in asyncpg projects |
| 5adba2f3 | 20:07 | TASK-FIX-0C22 | `postgresql+asyncpg://` dialect in docker_fixtures DATABASE_URL |

The earliest suspects are **TASK-FIX-AE7E** and **TASK-FIX-0C22** since one touches the exact criteria-matching path and the other changes the DATABASE_URL the Player agent works with (potentially altering its behavior).

## Review Scope

### Question 1 — Did TASK-FIX-0C22 change Player behavior?

The `DATABASE_URL` in the docker fixture now reads `postgresql+asyncpg://...`. The Player is writing files using this URL. Does this cause the Player to skip writing `completion_promises` to `task_work_results.json` or `player_turn_N.json`? Compare `task_work_results.json` from a preserved worktree of the failing run vs. the passing run. Specifically inspect:
- Does `task_work_results.json` have a non-empty `completion_promises` array?
- Does `player_turn_1.json` (agent-written) exist before `_build_player_report_from_task_work_results()` runs?

### Question 2 — Did TASK-FIX-AE7E introduce a bug in `_load_completion_promises`?

The fix added backward scanning through prior `player_turn_N.json` files. Could it have introduced a logic error that prevents the current turn's promises from being read correctly? Examine `coach_validator.py _load_completion_promises()` after edb5fd18. Check:
- Is there an off-by-one that reads turn N-1 when turn N has promises?
- Does the backward scan overwrite a valid current-turn result with an empty prior-turn result?

### Question 3 — Is the File-Existence Fallback (Fix 5) also failing?

In `agent_invoker.py` ~line 1656, if no `completion_promises` are recovered, a file-existence check generates synthetic promises. This also produced nothing in the failing run. Why?
- Is `_find_task_file()` failing to locate the task file?
- Are `acceptance_criteria` empty in the task metadata?
- Is `_generate_file_existence_promises()` producing an empty list?

### Question 4 — Are the TASK-FIX-4415 / TASK-FIX-70F3 changes affecting scaffold task type classification?

TASK-DB-001 uses `task_type: scaffolding`. TASK-FIX-4415 added psycopg2-specific feedback logic. Could this have introduced a side effect in the scaffolding path (e.g., incorrectly classifying TASK-DB-001 as an infrastructure failure and overriding the criteria check)?

## Files to Examine

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_load_completion_promises()`, `_verify_requirements()`, psycopg2 feedback
- `guardkit/orchestrator/agent_invoker.py` — Fix 2 recovery (~line 1620), Fix 5 file-existence fallback (~line 1656)
- `guardkit/orchestrator/docker_fixtures.py` — TASK-FIX-0C22 change
- Preserved worktree: `/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/fastapi/.guardkit/worktrees/FEAT-BA28/`
  - `.guardkit/autobuild/TASK-DB-001/task_work_results.json`
  - `.guardkit/autobuild/TASK-DB-001/player_turn_1.json`
  - `.guardkit/autobuild/TASK-DB-001/coach_turn_1.json`

## Acceptance Criteria

- [ ] Root cause identified: which commit(s) introduced the regression, and which specific code path broke
- [ ] A proposed fix or next `/task-work` task is produced
- [ ] The fix does NOT regress the psycopg2 error detection added in TASK-FIX-4415
- [ ] The fix does NOT regress the cross-turn criteria memory added in TASK-FIX-AE7E

## Next Steps After Review

Use `/task-review TASK-REV-9745` to execute this review. The decision point will be:
- **[I]mplement** — create a fix task (`TASK-FIX-XXXX`) targeting the identified root cause
- **[R]evise** — if more evidence is needed from a fresh `--fresh` run with additional logging
