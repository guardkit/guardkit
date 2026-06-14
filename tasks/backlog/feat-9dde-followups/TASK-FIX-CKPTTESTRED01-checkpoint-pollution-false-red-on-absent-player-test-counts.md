---
id: TASK-FIX-CKPTTESTRED01
title: Checkpoint pollution detector false-reds on absent Player test-counts (tests_run=None read as "tests failed" → false unrecoverable_stall)
status: backlog
task_type: fix
created: 2026-06-14T09:00:00Z
updated: 2026-06-14T09:00:00Z
priority: high
complexity: 4
related: [TASK-FIX-SPECINVOKE01, TASK-FIX-COACHREASON01, TASK-AB-FIX-INVAB1, FEAT-9DDE]
implementation_mode: task-work
tags: [autobuild, checkpoints, pollution-detection, false-red, absence-of-failure, coach]
---

# Task: Checkpoint pollution detector false-reds on absent Player test-counts

## Why this task exists

FEAT-9DDE **run 5** (2026-06-13; Player=qwen3-coder-30b, Coach=gemma4-coach +
`DISABLE_THINKING=1`) ended `unrecoverable_stall` at turn 3 with:

```
worktree_checkpoints: Creating checkpoint for TASK-TSJ-001 turn 1 (tests: fail, count: 0)
worktree_checkpoints: Creating checkpoint for TASK-TSJ-001 turn 2 (tests: fail, count: 0)
worktree_checkpoints: Creating checkpoint for TASK-TSJ-001 turn 3 (tests: fail, count: 0)
worktree_checkpoints: Context pollution detected: 3 consecutive test failures in turns [1, 2, 3]
worktree_checkpoints: No passing checkpoints found in history
autobuild: Unrecoverable stall detected ... context pollution detected but no passing checkpoint exists.
```

**This was a false-red, not a real failure.** On the same turns the Coach
quality gate reported `tests=True` (turns 2–3, `ALL_PASSED=True`), the unit test
file existed at the correct path
(`tests/unit/commands/test_task_status_json.py`), and the Coach actually ran it
(`Running independent tests via subprocess: pytest tests/unit/commands/test_task_status_json.py`).

Root cause: `WorktreeCheckpointManager.create_checkpoint(tests_passed, test_count)`
is fed from the **Player's self-reported** `task_work_results.json`, where
`tests_run=None` / `tests_passed=None` (qwen3-coder-30b did not populate test
counts). `None` collapses to `tests_passed=False, test_count=0`, so every turn
is recorded `tests: fail` even though tests exist and pass. After 3 such turns
the pollution detector fires "3 consecutive test failures" and, finding no
passing checkpoint (the Coach legitimately gave feedback all 3 turns), declares
an unrecoverable stall.

This is the **`absence-of-failure-is-not-success` family, inverted into a
false-red, in the checkpoint layer**: an *absent* self-reported counter
(`tests_run=None`) is read as a *negative* signal (tests failed) instead of
*unknown*. It was masked until now because run 3's lenient/slow gemma4-31b Coach
**approved at turn 2**, exiting the loop before the pollution counter reached 3.
The faster, stricter gemma4-coach (runs the full turn budget) exposed it.

## Symptom

- `unrecoverable_stall` with rationale "context pollution detected but no passing
  checkpoint exists" on a task whose Coach gate shows `tests=True` and whose test
  file exists and passes on disk.
- Checkpoint log shows `tests: fail, count: 0` for every turn while
  `coach_validator` logs `Quality gate evaluation complete: tests=True`.
- The Player's `task_work_results.json` has `tests_run: null` / `tests_passed: null`.
- Surfaces only when the Coach does NOT approve within the first 1–2 turns (a
  strict Coach, or a genuinely incomplete deliverable that nonetheless has
  passing tests).

## Detection recipe

```bash
# 1. Checkpoint test-status source: does it read the Player self-report or a real signal?
rg -n "create_checkpoint|tests_passed|test_count|consecutive test failures|No passing checkpoints" \
   guardkit/orchestrator/worktree_checkpoints.py
# 2. The call site — what does autobuild pass for tests_passed / test_count?
rg -n "create_checkpoint\(" guardkit/orchestrator/autobuild.py
rg -n "tests_run|tests_passed|task_work_results" guardkit/orchestrator/autobuild.py
# 3. Confirm the discrepancy: Coach gate tests=True vs checkpoint tests:fail,count:0
rg -n "tests=True|tests: (pass|fail), count" .guardkit/autobuild/FEAT-9DDE-run5-stdout.log
```

## Remediation recipe

1. **Stop deriving checkpoint `tests_passed` from the Player's self-report.** Use
   a *real* signal: the Coach quality-gate result (`tests=True`), or the Coach's
   independent-test run result, or run a count at checkpoint time. The Player's
   `tests_run`/`tests_passed` are advisory, not authoritative (TASK-AB-FIX-INVAB1
   already established "verify on disk, not on Player report").
2. **Treat absent counts as UNKNOWN, never FAILURE.** `tests_run=None` must not
   collapse to `tests_passed=False`. An unknown test signal must not increment the
   consecutive-failure pollution counter (pair the boolean with a "did a test
   oracle actually run?" precondition — the absence-of-failure remediation).
3. **Reconcile the 3-layer test-signal split.** Run 5 had `coach gate tests=True`
   + `coach AC-verification "test signal absent"` + `checkpoint tests:fail/0` for
   the same turn. The three layers must read one consistent test oracle.
4. **Regression test:** a synthetic turn sequence where the Player reports
   `tests_run=None` but the Coach gate is `tests=True` (and/or the test file
   passes on disk) must NOT accumulate pollution / must NOT
   `unrecoverable_stall`.

## Acceptance Criteria

- [ ] Checkpoint pollution detection no longer counts a turn as a "test failure"
      solely because the Player report's `tests_run`/`tests_passed` is `None`/absent.
- [ ] Checkpoint `tests_passed` is sourced from an authoritative signal (Coach
      gate result or an independent run), not the Player self-report — or absent
      counts are treated as `unknown` and excluded from the consecutive-failure tally.
- [ ] A turn where the Coach gate is `tests=True` is never recorded as `tests: fail`.
- [ ] Regression test reproduces the run-5 false-red (Player `tests_run=None` +
      Coach `tests=True`, N turns of Coach feedback) and asserts no
      `unrecoverable_stall` from pollution.
- [ ] No change to the *genuine* pollution case (real consecutive test failures
      with a real failing oracle still stall as designed).

## Evidence
- Run log: `.guardkit/autobuild/FEAT-9DDE-run5-stdout.log` (checkpoint lines 234/416/591; stall 594–596; Coach gate `tests=True` 219/395/570; independent test run 398/573).
- Preserved artifacts: `docs/retro/run5-evidence/` (coach_turn_{1,2,3}.json, checkpoints.json, task_work_results.json with `tests_run=null`).
- Result writeup: `docs/retro/coder-player-experiment-RESULT-2026-06-13.md` §"Runs 4–5".
- Sibling rule: `.claude/rules/absence-of-failure-is-not-success.md` (this is its checkpoint-layer, false-red instance).
</content>
