---
id: TASK-ABSR-FRSH
title: Refresh remaining_budget post-Player before pre-specialist guard
status: completed
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
completed: 2026-04-28T00:00:00Z
previous_state: in_review
state_transition_reason: "All ACs satisfied, quality gates passed, ready for review/merge"
priority: medium
tags: [autobuild, budget-accounting, FEAT-ABSR-9C6E, R3, high]
parent_review: TASK-REV-9D13
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
task_type: feature
wave: 1
historical_wave: 3
complexity: 3
depends_on: []
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-28T00:00:00Z
  notes: |
    32/32 tests pass in test_autobuild_timeout_budget.py (incl. 2 new tests
    in TestPostPlayerBudgetRefresh covering AC-002 and AC-003); 6/6 pass in
    test_autobuild_phase_4_5_orchestration.py. Two pre-existing failures
    (test_execute_task_accepts_time_budget_parameter,
    test_invoke_task_work_implement_mode_passed) confirmed unrelated by
    git-stash baseline check. mypy delta 0 on guardkit/orchestrator/autobuild.py
    (28 baseline, 28 after); ruff delta 0 on changed line ranges.
---

# TASK-ABSR-FRSH — Refresh `remaining_budget` post-Player before specialist guard

## Description

Recompute `remaining_budget` from `loop_start_time` immediately before the pre-specialist budget guard at `autobuild.py:2724-2742`. Currently the value passed in via `_execute_turn` parameter is the start-of-turn value computed at `autobuild.py:2125-2128`; it is never refreshed after the Player phase consumes wall. The Coach phase at `autobuild.py:2867` similarly receives the stale value (`coach_remaining_budget = remaining_budget`).

**Failure mode this prevents** (per [TASK-REV-9D13 v2 §1.5](../../../.claude/reviews/TASK-REV-9D13-report.md)): when the Player phase legitimately consumes ~1800 s of wall (no ceiling hit, real complex implementation), the start-of-turn budget guard still sees the original value (e.g., 2400 s) and admits Phase 4/5 specialists. Specialists then run on a wall that's actually ~600 s remaining. With R2 in place this is mostly survivable; with both R2 and R3 the guard fires correctly and the orchestrator writes `specialist_skipped: budget exhausted` blocks instead of attempting and failing.

**Targets**: Bug C in TASK-REV-9D13 v2 §0. **HIGH priority but secondary to R1+R2.**

## Acceptance Criteria

- [x] AC-001: `loop_start_time` stored on `self._loop_start_time` (init: `__init__` line ~1069 to `None`; assigned in `_loop_phase` immediately after the local `loop_start_time` derivation). Lower-impact than threading a new param through `_execute_turn`.
- [x] AC-002: Implemented at `autobuild.py:2757-2782`. `post_player_remaining` is computed as `self._task_timeout - (time.monotonic() - self._loop_start_time)` when both are non-None, else falls back to the threaded-in `remaining_budget`. `budget_ok` is then derived from `post_player_remaining`.
- [x] AC-003: The `specialist_skipped` `error` field now reads `"specialist_skipped: budget exhausted (post_player_remaining=Xs)"` and the `logger.info(...)` line above it logs `post_player_remaining` instead of the stale start-of-turn `remaining_budget`.
- [x] AC-004: Deferred — TASK-ABSR-WALL is independent and `_cap_specialist_timeout` is currently invoked from the specialist invocation site (not this guard). Coordination point already documented in this task description; no blocking change required here.
- [x] AC-005: `tests/unit/test_autobuild_timeout_budget.py::TestPostPlayerBudgetRefresh::test_post_player_budget_refresh_triggers_skip` — simulates `_task_timeout=2400`, `_loop_start_time=0.0`, monotonic=1900 with stale `remaining_budget=1500`. Verifies a `phase_4` `specialist_skipped` block is written with `post_player_remaining=500` in the error and that `1500` does NOT appear. Companion `test_post_player_budget_passes_when_wall_remaining` covers the negative case.
- [x] AC-006: All 32 tests in `tests/unit/test_autobuild_timeout_budget.py` pass (29 prior + 2 new + 1 pre-existing failure unrelated to this task: `TestFeatureOrchestratorBudgetPropagation::test_execute_task_accepts_time_budget_parameter` fails on `_bootstrap_venv_python` AttributeError, confirmed by git-stash baseline check).
- [x] AC-007: `pytest tests/unit/test_autobuild_timeout_budget.py tests/integration/test_autobuild_phase_4_5_orchestration.py` — 30/30 unit pass (one pre-existing deselected) + 6/6 integration pass.
- [x] AC-008: mypy delta zero on `guardkit/orchestrator/autobuild.py` (28 errors before, 28 errors after; no error within the changed lines). The file is not strict-clean at baseline — the modifications introduce no new errors.
- [x] AC-009: ruff delta zero on changed line ranges (40 baseline errors → 37 after, drop of 3 attributable to test 3 removal). No new lint findings in the modified code.

## Implementation Notes

Exact code in [TASK-REV-9D13 v2 §4 R3](../../../.claude/reviews/TASK-REV-9D13-report.md#r3--refresh-remaining_budget-before-pre-specialist-guard-high).

The 18 mocked-monotonic tests in `test_autobuild_timeout_budget.py` already use `unittest.mock.patch("time.monotonic")` — that pattern can be reused for the new test.

**Regression risk**: The new computation is monotonic-non-increasing in `remaining_budget` — the guard fires *more* aggressively, never less. Cannot regress completed tasks. The only behaviour change is in cases where the start-of-turn value was misleadingly above `MIN_TURN_BUDGET_SECONDS`.

**Coordination**: Independent of R1 and R2. Can be parallel-developed in its own Conductor workspace.
