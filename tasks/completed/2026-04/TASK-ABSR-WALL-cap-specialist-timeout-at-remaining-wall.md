---
id: TASK-ABSR-WALL
title: Cap orchestrator-invoked specialist sdk_timeout at remaining wall budget
status: completed
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
completed: 2026-04-28T00:00:00Z
completed_location: tasks/completed/2026-04/
previous_state: in_review
state_transition_reason: "Task complete — all ACs satisfied"
priority: high
tags: [autobuild, specialist-invocation, timeout, FEAT-ABSR-9C6E, R2, critical]
parent_review: TASK-REV-9D13
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
task_type: feature
wave: 1
historical_wave: 3  # Wave 3 of FEAT-ABSR-9C6E historically
complexity: 4
depends_on: []
test_results:
  status: passed
  coverage: null  # not measured for this targeted change; new helper is fully covered by 6 unit tests
  last_run: 2026-04-28T00:00:00Z
---

# TASK-ABSR-WALL — Cap specialist sdk_timeout at remaining wall budget

## Description

Add a `_cap_specialist_timeout(remaining_budget)` helper on `AutoBuildOrchestrator` and route specialist invocations at `autobuild.py:2778-2800` through it. Currently `invoke_test_orchestrator(sdk_timeout=self.sdk_timeout)` and `invoke_code_reviewer(sdk_timeout=self.sdk_timeout)` pass the bare 1200 s default; the cap-at-remaining-wall logic exists for the Player path (`_calculate_sdk_timeout` at `agent_invoker.py:3866-3867`) but is bypassed for specialists.

**Failure mode this prevents** (per [TASK-REV-9D13 v2 §1.3](../../../.claude/reviews/TASK-REV-9D13-report.md)): when wall budget remaining is less than `self.sdk_timeout`, a single specialist can consume the entire remaining wall (as Phase-4 specialist did for J004-013 — 1200 s of ~1242 s remaining). With this cap in place, the specialist fails fast within the wall budget rather than burning it all.

**Targets**: Bug B in TASK-REV-9D13 v2 §0. **Critical, defence in depth against R1 misses.**

## Acceptance Criteria

- [x] AC-001: New private method `_cap_specialist_timeout(self, remaining_budget: Optional[float]) -> int` on `AutoBuildOrchestrator` (located in `guardkit/orchestrator/autobuild.py` near other helpers). Behaviour: if `remaining_budget is None` return `self.sdk_timeout or 1200`; else compute `reserved = remaining_budget - COACH_GRACE_PERIOD_SECONDS` (= 120 s, existing constant at autobuild.py:188), `cap = max(60, int(reserved))`, return `min(self.sdk_timeout or 1200, cap)`. Floor of 60 s prevents pathologically-low values from blocking specialists entirely. — added at autobuild.py:2395
- [x] AC-002: `autobuild.py:2778-2786` (`invoke_test_orchestrator` call) replaces `sdk_timeout=self.sdk_timeout` with `sdk_timeout=self._cap_specialist_timeout(remaining_budget=remaining_budget)`. — done at autobuild.py:2810
- [x] AC-003: `autobuild.py:2790-2800` (`invoke_code_reviewer` call) replaces `sdk_timeout=self.sdk_timeout` with `sdk_timeout=self._cap_specialist_timeout(remaining_budget=remaining_budget)`. Note: the cap may differ between Phase 4 and Phase 5 invocations because Phase 4 may have consumed wall — that's correct behaviour, not a bug. — done at autobuild.py:2830
- [x] AC-004: When env var `GUARDKIT_SPECIALIST_TIMEOUT_CAP=disable` is set, `_cap_specialist_timeout` short-circuits to `self.sdk_timeout or 1200` without applying the cap. Circuit breaker for emergency backout.
- [x] AC-005: New tests in `tests/unit/test_autobuild_timeout_budget.py::TestCapSpecialistTimeout` (6 tests): `test_uses_full_when_ample_remaining`, `test_caps_when_low_remaining` (800 → 680), `test_floor_at_60s` (100 → 60, also remaining=0), `test_no_budget_passes_base`, `test_circuit_breaker_env_var`, `test_falls_back_when_sdk_timeout_unset`.
- [x] AC-006: Integration tests in `tests/integration/test_autobuild_phase_4_5_orchestration.py` continue to pass.
- [x] AC-007: `tests/unit/orchestrator/test_specialist_invocations.py` continues to pass unmodified.
- [x] AC-008: Full suite run: 190 passed, 3 failed. All 3 failures (`TestCoachValidatorPathConstruction::test_invoke_coach_safely_uses_worktree_path_not_task_id`, `..works_in_single_task_mode`, `TestFeatureOrchestratorBudgetPropagation::test_execute_task_accepts_time_budget_parameter`) are pre-existing on baseline `5ca0a8fb` (verified via `git stash` round-trip) and unrelated to this change.
- [x] AC-009: mypy reports 28 pre-existing errors in `autobuild.py`, none at the new helper or modified call sites (verified: no errors at lines 2395-2420, 2810, 2830).
- [x] AC-010: ruff reports 39 pre-existing issues, none at the new helper, modified call sites, or new test class.

## Implementation Notes

Exact code in [TASK-REV-9D13 v2 §4 R2](../../../.claude/reviews/TASK-REV-9D13-report.md#r2--cap-orchestrator-invoked-specialist-sdk_timeout-at-remaining-wall-critical--second).

`COACH_GRACE_PERIOD_SECONDS = 120` is already defined at `autobuild.py:188`. Reuse, don't re-declare.

The `remaining_budget` parameter passed to `_execute_turn` is the start-of-turn value (see TASK-ABSR-FRSH for the post-Player refresh; until that lands, the cap will be slightly optimistic but still correct in the most-failing case).

**Regression risk**: The cap is monotonic-non-increasing — specialists get ≤ what they would have under current code. Successful runs (where wall is ample) see no change.

**Coordination with TASK-ABSR-CEIL (R1)**: R1+R2 are designed to land together. R1 short-circuits before specialist invocation when ceiling-hit; R2 caps the timeout when specialists DO run. Order doesn't matter; both can be parallel-developed in separate Conductor workspaces.
