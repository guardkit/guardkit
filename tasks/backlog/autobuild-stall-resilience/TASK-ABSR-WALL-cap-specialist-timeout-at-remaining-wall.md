---
id: TASK-ABSR-WALL
title: Cap orchestrator-invoked specialist sdk_timeout at remaining wall budget
status: backlog
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
priority: high
tags: [autobuild, specialist-invocation, timeout, FEAT-ABSR-9C6E, R2, critical]
parent_review: TASK-REV-9D13
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
task_type: feature
wave: 3
complexity: 4
depends_on: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# TASK-ABSR-WALL — Cap specialist sdk_timeout at remaining wall budget

## Description

Add a `_cap_specialist_timeout(remaining_budget)` helper on `AutoBuildOrchestrator` and route specialist invocations at `autobuild.py:2778-2800` through it. Currently `invoke_test_orchestrator(sdk_timeout=self.sdk_timeout)` and `invoke_code_reviewer(sdk_timeout=self.sdk_timeout)` pass the bare 1200 s default; the cap-at-remaining-wall logic exists for the Player path (`_calculate_sdk_timeout` at `agent_invoker.py:3866-3867`) but is bypassed for specialists.

**Failure mode this prevents** (per [TASK-REV-9D13 v2 §1.3](../../../.claude/reviews/TASK-REV-9D13-report.md)): when wall budget remaining is less than `self.sdk_timeout`, a single specialist can consume the entire remaining wall (as Phase-4 specialist did for J004-013 — 1200 s of ~1242 s remaining). With this cap in place, the specialist fails fast within the wall budget rather than burning it all.

**Targets**: Bug B in TASK-REV-9D13 v2 §0. **Critical, defence in depth against R1 misses.**

## Acceptance Criteria

- [ ] AC-001: New private method `_cap_specialist_timeout(self, remaining_budget: Optional[float]) -> int` on `AutoBuildOrchestrator` (located in `guardkit/orchestrator/autobuild.py` near other helpers). Behaviour: if `remaining_budget is None` return `self.sdk_timeout or 1200`; else compute `reserved = remaining_budget - COACH_GRACE_PERIOD_SECONDS` (= 120 s, existing constant at autobuild.py:188), `cap = max(60, int(reserved))`, return `min(self.sdk_timeout or 1200, cap)`. Floor of 60 s prevents pathologically-low values from blocking specialists entirely.
- [ ] AC-002: `autobuild.py:2778-2786` (`invoke_test_orchestrator` call) replaces `sdk_timeout=self.sdk_timeout` with `sdk_timeout=self._cap_specialist_timeout(remaining_budget=remaining_budget)`.
- [ ] AC-003: `autobuild.py:2790-2800` (`invoke_code_reviewer` call) replaces `sdk_timeout=self.sdk_timeout` with `sdk_timeout=self._cap_specialist_timeout(remaining_budget=remaining_budget)`. Note: the cap may differ between Phase 4 and Phase 5 invocations because Phase 4 may have consumed wall — that's correct behaviour, not a bug.
- [ ] AC-004: When env var `GUARDKIT_SPECIALIST_TIMEOUT_CAP=disable` is set, `_cap_specialist_timeout` short-circuits to `self.sdk_timeout or 1200` without applying the cap. Circuit breaker for emergency backout.
- [ ] AC-005: New tests in `tests/unit/test_autobuild_orchestrator.py` (or appropriate existing test file): `test_cap_specialist_timeout_uses_full_when_ample_remaining` (ample remaining → returns base), `test_cap_specialist_timeout_caps_when_low_remaining` (e.g., remaining=800 with COACH_GRACE_PERIOD=120 → returns 680), `test_cap_specialist_timeout_floor_at_60s` (remaining=100 → returns 60), `test_cap_specialist_timeout_no_budget_passes_base` (remaining_budget=None → returns base), `test_cap_specialist_timeout_circuit_breaker_env_var` (env var set → returns base regardless).
- [ ] AC-006: Existing tests in `tests/integration/test_autobuild_phase_4_5_orchestration.py` continue to pass. The integration helper `_drive_orchestrator_phase_4_5` should be invoked with `remaining_budget` ≥ 2400 s in those tests (matches default `task_timeout=2400` minus negligible setup), so cap returns base = 1200 — no behaviour change.
- [ ] AC-007: Existing tests in `tests/unit/orchestrator/test_specialist_invocations.py` (11 tests) continue to pass without modification (they pass `sdk_timeout` directly to `invoke_test_orchestrator` and don't exercise the cap helper).
- [ ] AC-008: `pytest tests/integration/test_autobuild_phase_4_5_orchestration.py tests/unit/orchestrator/test_specialist_invocations.py tests/unit/test_autobuild_orchestrator.py tests/unit/test_autobuild_timeout_budget.py -v` passes locally.
- [ ] AC-009: `mypy guardkit/orchestrator/autobuild.py` strict-clean.
- [ ] AC-010: Lint/format pass.

## Implementation Notes

Exact code in [TASK-REV-9D13 v2 §4 R2](../../../.claude/reviews/TASK-REV-9D13-report.md#r2--cap-orchestrator-invoked-specialist-sdk_timeout-at-remaining-wall-critical--second).

`COACH_GRACE_PERIOD_SECONDS = 120` is already defined at `autobuild.py:188`. Reuse, don't re-declare.

The `remaining_budget` parameter passed to `_execute_turn` is the start-of-turn value (see TASK-ABSR-FRSH for the post-Player refresh; until that lands, the cap will be slightly optimistic but still correct in the most-failing case).

**Regression risk**: The cap is monotonic-non-increasing — specialists get ≤ what they would have under current code. Successful runs (where wall is ample) see no change.

**Coordination with TASK-ABSR-CEIL (R1)**: R1+R2 are designed to land together. R1 short-circuits before specialist invocation when ceiling-hit; R2 caps the timeout when specialists DO run. Order doesn't matter; both can be parallel-developed in separate Conductor workspaces.
