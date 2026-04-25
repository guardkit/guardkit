---
id: TASK-FIX-BDDM-1
title: 'BDD runner: synthesise blocker when tagged scenarios exist + pytest-bdd absent (R1+R2)'
status: completed
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T21:24:32Z'
completed: '2026-04-25T21:24:32Z'
completed_location: tasks/completed/2026-04/
previous_state: in_review
state_transition_reason: "Task complete; all quality gates green"
priority: high
complexity: 5
task_type: bugfix
tags: [bdd, autobuild, quality-gates, silent-bypass, regression-fix]
parent_review: TASK-REV-BDDM
feature_id: FEAT-BDDM
implementation_mode: task-work
wave: 1
conductor_workspace: bdd-fix-wave1-1
depends_on: []
test_results:
  status: passed
  coverage: '85% module / ~99% on run_bdd_for_task (line + branch)'
  last_run: '2026-04-25T21:24:32Z'
  tests_run: 51
  tests_passed: 51
  affected_test_files:
    - tests/unit/orchestrator/quality_gates/test_bdd_runner.py
    - tests/unit/orchestrator/quality_gates/test_coach_validator.py
    - tests/integration/autobuild/test_bdd_end_to_end.py
    - tests/integration/autobuild/test_bdd_scope_boundary.py
    - tests/integration/task_work/test_bdd_integration.py
    - tests/integration/autobuild/test_smoke_gate_bdd_integration.py
---

# Task: BDD runner — synthesise blocker on pytest-bdd absence (R1 + R2)

## Description

[bdd_runner.run_bdd_for_task()](../../../guardkit/orchestrator/quality_gates/bdd_runner.py#L466-L473) currently returns `None` when tagged feature files exist (`@task:<TASK-ID>`) AND `pytest_bdd` is not importable in the worktree env. The Coach silently approves on `scenarios_failed == 0` — vacuously true with no result. Empirical proof: 10 occurrences in jarvis's `autobuild-FEAT-J002-history.md`, 11 in `autobuild-FEAT-J003-history-cancelled.md`. Every tagged J002/J003 task ran AutoBuild with **zero BDD verification**.

This is the same meta-class as TASK-FIX-F584 (pytest runner-error surfacing), but on a different code path — F584 covered "pytest invoked → exit ≠ 0/5"; this task covers "pytest-bdd not even importable".

## Acceptance Criteria

- [ ] Replace `return None` at `bdd_runner.py:466-473` with construction of a synthetic `BDDResult(scenarios_failed=1)` carrying a `FailureDetail` whose `scenario_name="pytest_bdd_not_importable"` and `reason` includes both the task ID and a clear "add pytest-bdd to pyproject" remediation hint.
- [ ] The log at `bdd_runner.py:467-471` is promoted from `INFO` to `WARNING`.
- [ ] Existing test `test_pytest_bdd_unavailable_returns_none` (test_bdd_runner.py:389-398) is renamed to `test_pytest_bdd_unavailable_with_tags_returns_synthetic_blocker` and rewritten to assert the new contract.
- [ ] New test `test_pytest_bdd_unavailable_no_tags_still_skips` confirms the legitimate-skip path at line 458 is unchanged (no false positive when `find_feature_files_with_tag` returns empty).
- [ ] New test `test_synthetic_blocker_routes_through_coach_validator` confirms the synthetic blocker reaches Coach as `category=bdd_failure` (e2e through `_check_bdd_results`).
- [ ] All other tests in `test_bdd_runner.py`, `test_bdd_end_to_end.py`, `test_bdd_scope_boundary.py`, `test_bdd_integration.py` still pass.
- [ ] Coverage on `bdd_runner.run_bdd_for_task` ≥ 90% (line + branch).

## Implementation Notes

**Patch sketch** (full version in [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) §B.4):

Replace at `bdd_runner.py:466-473`:

```python
if not has_pytest_bdd(python_executable=python_executable):
    logger.warning(
        "BDD runner: pytest-bdd not importable but %d candidate "
        "feature file(s) for %s exist; surfacing as synthetic failure "
        "so Coach blocks. Add pytest-bdd to the project's pyproject.toml.",
        len(matching), task_id,
    )
    reason = (
        "pytest_bdd_not_importable: tagged feature files exist for "
        f"{task_id} but pytest-bdd is not installed in the worktree "
        "environment. Add 'pytest-bdd>=8.1,<9' (or compatible) to the "
        "project's pyproject.toml dependencies and reinstall."
    )
    return BDDResult(
        scenarios_passed=0,
        scenarios_failed=1,
        scenarios_pending=0,
        failures=[FailureDetail(
            feature_file=str(matching[0].relative_to(worktree_path)),
            scenario_name="pytest_bdd_not_importable",
            failing_step="",
            reason=reason,
        )],
        pending=[],
        feature_files=[str(p.relative_to(worktree_path)) for p in matching],
        tag=tag,
        raw_output="",
    )
```

**Regression-safety bound (from review §F):** the change has been line-level analysed; only **1 existing test** is affected (the `_returns_none` test renamed above). Player retry storms are bounded by `autobuild.py:3707` (TASK-AB-SD01 stall-detector) to 3 turns. JSON shape is identical to F584's existing `pytest_runner_error` synthetic-blocker shape — already round-trip tested.

**Pair with TASK-FIX-BDDM-2** to keep cost-efficiency neutral. Without the env preflight (R3), this fix burns 3 SDK turns per misconfigured task before stall-detection.

## Notes

- Architecture decision recorded in: [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md)
- Sibling Graphiti rule: *"runner without producer anti-pattern"* (uuid `184731b0-3cb6-4eb2-a310-883421767dbf`)
- F584 precedent in same file: `bdd_runner.py:323-350` (`_synthesise_runner_error_failure`), `:507-530` (call site)

## Implementation Summary

Replaced the silent `return None` at `bdd_runner.py:466-473` with construction of a synthetic `BDDResult(scenarios_failed=1)` carrying a `FailureDetail(scenario_name="pytest_bdd_not_importable", reason=...)` whose reason string names both the task ID and the pyproject remediation step. Promoted the surrounding log from INFO to WARNING. Updated the public `run_bdd_for_task` docstring to reflect the new contract. The legitimate-skip path at L458 (no tagged feature files) is preserved unchanged — pytest-bdd absence only synthesises a blocker when tagged files actually exist.

In tests: renamed `test_pytest_bdd_unavailable_returns_none` → `test_pytest_bdd_unavailable_with_tags_returns_synthetic_blocker` and rewrote it to assert the new contract plus the WARNING log promotion. Added `test_pytest_bdd_unavailable_no_tags_still_skips` (regression-safety on the legitimate-skip path) and `test_synthetic_blocker_routes_through_coach_validator` (e2e: synthetic BDDResult → `to_dict()` → `_check_bdd_results` → `category=bdd_failure` `must_fix`).

51/51 tests pass across the affected surface (test_bdd_runner, test_coach_validator, test_bdd_end_to_end, test_bdd_scope_boundary, test_bdd_integration, test_smoke_gate_bdd_integration). Coverage on `run_bdd_for_task` ~99% line+branch (≥90% AC met); module 85% (uncovered lines are pre-existing real-subprocess seams patched out in tests).

Approach mirrors the F584 sibling (`_synthesise_runner_error_failure` at `bdd_runner.py:323-350`): same JSON shape, same Coach consumption path, same producer-runs-gate principle from the *"runner without producer anti-pattern"* Graphiti rule.

## Lessons Learned

- The "runner without producer anti-pattern" rule applies to vacuously-true Coach approval rules in general: any `count == 0` rule combined with an early-`None`-return path is a silent-bypass waiting to happen. F584 fixed it for `pytest_runner_error`; this fix closes the `pytest_bdd_not_importable` sibling on the same code path.
- Empirical proof from jarvis history (10 occurrences in `autobuild-FEAT-J002-history.md`, 11 in `autobuild-FEAT-J003-history-cancelled.md`) was decisive — the bug's blast radius motivated treating it as a regression-fix, not an enhancement.
- Pair this fix with TASK-FIX-BDDM-2 (env preflight). Without preflight, every misconfigured task burns 3 SDK turns before stall-detection bounds it. Cost-efficiency is neutral only when the two ship together.
