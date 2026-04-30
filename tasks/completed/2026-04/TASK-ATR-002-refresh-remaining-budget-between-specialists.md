---
id: TASK-ATR-002
title: Refresh remaining_budget between Phase 4 and Phase 5 specialists
task_type: bugfix
parent_review: TASK-REV-E73C
parent_review_repo: jarvis
feature_id: FEAT-ATR
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
priority: medium
status: completed
completed: 2026-04-30
updated: 2026-04-30
previous_state: in_review
completed_location: tasks/completed/2026-04/
tags: [autobuild, specialist, latent-bug, FEAT-ATR]
---

## Implementation Summary

Fixed latent bug at `guardkit/orchestrator/autobuild.py:2880-2918`: the
per-turn specialist pipeline now refreshes `remaining_budget` between
Phase 4 (test-orchestrator) and Phase 5 (code-reviewer) to reflect wall
consumed by Phase 4. Previously both calls passed the same start-of-turn
`remaining_budget` to `_cap_specialist_timeout`, which over-allocated
Phase 5 time and risked post-specialist Coach overrun of the feature
`task_timeout`.

**Diff (~15 LoC)**: capture `_phase4_start = time.monotonic()` before
Phase 4; after Phase 4 returns, compute
`phase5_remaining = max(0.0, remaining_budget - phase4_elapsed)` (or
`None` when `remaining_budget is None`); pass that to Phase 5's
`_cap_specialist_timeout` call.

**Tests added** (`tests/unit/test_autobuild_timeout_budget.py`,
`TestSpecialistBudgetRefresh` class):
- `test_phase5_cap_input_refreshed_after_phase4_wall`: Phase 4 takes
  200s wall → Phase 5 cap input is `start_budget − 200` ± 5s.
- `test_phase5_remaining_is_none_when_remaining_budget_is_none`: None
  propagates to Phase 5 (no double-default to base wall).
- `test_phase5_remaining_floored_at_zero_when_phase4_overruns`:
  pathological case where Phase 4 overruns the budget floors at 0.0,
  not negative.

All 11 tests in `TestSpecialistBudgetRefresh`,
`TestPostPlayerBudgetRefresh`, and `TestCapSpecialistTimeout` pass. The 3
pre-existing failures in `TestFeatureOrchestratorBudgetPropagation` and
`TestCoachValidatorPathConstruction` were verified to exist on `main`
before this change and are unrelated.

## Lessons

- The orchestrator-side specialist pipeline maintains its own per-phase
  budget independently of the Player-side pipeline. The cap-input
  staleness here was the same class-of-defect as TASK-ABSR-FRSH (refresh
  `remaining_budget` post-Player) — both arose from threading a
  start-of-turn value through to a later phase that runs after wall has
  been consumed. The fix shape is the same: capture `time.monotonic()`
  at phase-start, recompute remaining at phase-end.
- The misleading comment at the former line 2895 ("Phase 4 may have
  consumed wall — that's correct") was inverse to the actual behaviour:
  the code did NOT account for that consumption. Comments asserting
  "this is correct" are an invariant claim and should be verified during
  review.

# TASK-ATR-002 — Refresh `remaining_budget` between Phase 4 and Phase 5 specialists

## Description

Latent bug discovered during TASK-REV-E73C review of FEAT-J005-946D timeout.
At [`guardkit/orchestrator/autobuild.py:2880–2909`](../../../guardkit/orchestrator/autobuild.py#L2880-L2909),
the per-turn specialist pipeline invokes `test-orchestrator` (Phase 4) and
then `code-reviewer` (Phase 5) sequentially. Each invocation's `sdk_timeout`
is computed by `_cap_specialist_timeout(remaining_budget=remaining_budget)` —
**but `remaining_budget` is the same value for both calls.** Phase 5's cap
does not reflect Phase 4's wall consumption.

For TASK-J005-005 turn 2 it didn't bite hard (Phase 4 = 390s, Phase 5 = 390s,
roughly balanced inside ~1041s post-Player budget). For tasks where Phase 4
takes most of the wall and Phase 5 has little left, Phase 5 receives a cap
that *over-allocates* time it doesn't actually have, which can cause the
post-specialist Coach validation to overrun the feature `task_timeout`
(the actual race we observed in FEAT-J005-946D).

## Root Cause Addressed

The comment at `autobuild.py:2895` says "Phase 4 may have consumed wall —
that's correct" — but the implementation is inconsistent with the comment.
The cap input must be refreshed.

## Files to Modify

1. `guardkit/orchestrator/autobuild.py` — between lines ~2880 and ~2909:
   capture `time.monotonic()` before Phase 4, compute
   `phase5_remaining = remaining_budget - phase4_elapsed` after, pass that
   to the Phase 5 `_cap_specialist_timeout()` call. Update the misleading
   comment.
2. `tests/unit/test_autobuild.py` — add `TestSpecialistBudgetRefresh` class:
   - mock `_cap_specialist_timeout` to capture the input
   - mock `invoke_test_orchestrator` to spend 200s wall (sleep or
     `time.monotonic` patch)
   - assert Phase 5 receives `remaining - 200` (within tolerance)

## Acceptance Criteria

- [ ] After Phase 4 returns, a fresh `phase5_remaining` is computed from
      `remaining_budget - phase4_elapsed`, floored at 0.0.
- [ ] Phase 5's `_cap_specialist_timeout` call uses `phase5_remaining`,
      NOT the original `remaining_budget`.
- [ ] When `remaining_budget is None` (no feature-level budget), Phase 5
      also receives None (no double-default).
- [ ] Comment at line 2895 updated to reflect the fix.
- [ ] Unit test verifies: Phase 4 takes 200s wall → Phase 5 cap input is
      `remaining_budget - 200` ± 5s.
- [ ] No regression in `tests/unit/test_autobuild.py::Test*` (full file passes).
- [ ] No regression in `tests/integration/test_specialist_*.py`.

## Test Requirements

- pytest unit tests in `tests/unit/test_autobuild.py`
- All existing autobuild specialist tests pass

## Implementation Notes

Diff-shaped change (~15 LoC):

```python
# Before:
phase4_result = _loop.run_until_complete(
    _si.invoke_test_orchestrator(
        worktree_path=worktree.path,
        task_id=task_id,
        sdk_timeout=self._cap_specialist_timeout(remaining_budget=remaining_budget),
        ...
    )
)
if phase4_result.status == "passed":
    _loop.run_until_complete(
        _si.invoke_code_reviewer(
            ...,
            sdk_timeout=self._cap_specialist_timeout(remaining_budget=remaining_budget),  # stale
            ...
        )
    )

# After:
_phase4_start = time.monotonic()
phase4_result = _loop.run_until_complete(
    _si.invoke_test_orchestrator(
        worktree_path=worktree.path,
        task_id=task_id,
        sdk_timeout=self._cap_specialist_timeout(remaining_budget=remaining_budget),
        ...
    )
)

# Refresh budget post-Phase-4 so Phase 5 cap reflects actual wall consumption
if remaining_budget is not None:
    _phase4_elapsed = time.monotonic() - _phase4_start
    phase5_remaining: Optional[float] = max(0.0, remaining_budget - _phase4_elapsed)
else:
    phase5_remaining = None

if phase4_result.status == "passed":
    _loop.run_until_complete(
        _si.invoke_code_reviewer(
            ...,
            sdk_timeout=self._cap_specialist_timeout(remaining_budget=phase5_remaining),
            ...
        )
    )
```

This is the lowest-risk task in FEAT-ATR and a good warm-up.
