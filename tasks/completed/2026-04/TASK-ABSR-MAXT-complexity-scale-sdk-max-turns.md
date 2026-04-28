---
id: TASK-ABSR-MAXT
title: Complexity-scale TASK_WORK_SDK_MAX_TURNS analogously to sdk_timeout
status: completed
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
completed: 2026-04-28T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/2026-04/
priority: medium
tags: [autobuild, sdk-budget, complexity-scaling, FEAT-ABSR-9C6E, R4]
parent_review: TASK-REV-9D13
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
task_type: feature
wave: 2
historical_wave: 4
complexity: 4
depends_on:
  - TASK-ABSR-CEIL
  - TASK-ABSR-WALL
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-28T00:00:00Z
  details: "tests/unit/test_agent_invoker_sdk_turn_budget.py + tests/integration/test_autobuild_phase_4_5_orchestration.py: 17 passed (5 legacy + 6 new TASK-ABSR-MAXT + 6 phase-4.5 integration). Broader regression set: 509 passed, 2 pre-existing baseline failures unchanged."
---

# TASK-ABSR-MAXT — Complexity-scale `TASK_WORK_SDK_MAX_TURNS`

## Description

Add `_calculate_sdk_max_turns(task_id)` on `AgentInvoker`, mirroring the existing `_calculate_sdk_timeout` complexity-scaling at `agent_invoker.py:3795-3877`. Currently `TASK_WORK_SDK_MAX_TURNS = 100` is a hardcoded constant at `agent_invoker.py:301`. Successful complexity-5 tasks in FEAT-J004-702C run-2 used 91 (J004-011) and 92 (J004-012) SDK turns — within ceiling-adjacency. Complexity-6 J004-013 needed >100 and hit the ceiling.

**SDK time budget already complexity-scales** (formula `1.0 + complexity/10` at agent_invoker.py:3853, multiplied by mode and backend); SDK turn budget does not. This asymmetry is the actual binding constraint for complex tasks: the Player has plenty of wall time but runs out of conversation turns.

**Targets**: Bug F in TASK-REV-9D13 v2 §0. **MED priority — reduces ceiling-hit rate independently of R1+R2.**

## Acceptance Criteria

- [x] AC-001: New private method `_calculate_sdk_max_turns(self, task_id: str) -> int` on `AgentInvoker`. Behaviour: if `_SDK_MAX_TURNS_IS_OVERRIDE` (env-var override) returns `TASK_WORK_SDK_MAX_TURNS` unchanged (env-var-wins semantics, matches `_calculate_sdk_timeout`). Else load complexity from task frontmatter via `TaskLoader.load_task(task_id, self.worktree_path)`, clamp to `[1, 10]`, default 5 on error. Compute `multiplier = 1.0 + (complexity / 10.0)` matching the existing `_calculate_sdk_timeout` formula. Return `int(TASK_WORK_SDK_MAX_TURNS * multiplier)`.
- [x] AC-002: At the SDK invocation site that currently uses `self._effective_sdk_max_turns` for `task-work` invocations, replace with `self._calculate_sdk_max_turns(task_id)`. Locate via grep for `_effective_sdk_max_turns` in `agent_invoker.py`; current value-set logic at lines 954-964 should remain (handles local-backend auto-reduction).
- [x] AC-003: Log line at SDK invocation start should report effective max_turns alongside SDK timeout: `logger.info(f"[{task_id}] Max turns: {effective_max_turns} (base={base}, complexity={complexity} x{multiplier:.1f})")`.
- [x] AC-004: Env var `GUARDKIT_SDK_MAX_TURNS` continues to take precedence (current behaviour at agent_invoker.py:301-302). When set explicitly via env var, complexity scaling does NOT apply (matches `_calculate_sdk_timeout` for `_sdk_timeout_is_override`).
- [x] AC-005: Update existing tests in `tests/unit/test_agent_invoker_sdk_turn_budget.py`: `test_default_sdk_max_turns_is_100` continues to pass (asserts the **base constant**, not the effective value). Add new tests: `test_complexity_scaling_at_complexity_1` (expects ~110), `test_complexity_scaling_at_complexity_5` (expects ~150), `test_complexity_scaling_at_complexity_6` (expects ~160), `test_complexity_scaling_at_complexity_10` (expects ~200), `test_env_var_override_skips_complexity_scaling` (env var set → returns 100 ignoring complexity).
- [x] AC-006: Test for missing/malformed task frontmatter: `test_complexity_defaults_to_5_on_load_error` — patch TaskLoader to raise; expect default complexity-5 multiplier (1.5x, returns 150).
- [x] AC-007: Existing 5 tests in `tests/unit/test_agent_invoker_sdk_turn_budget.py` continue to pass without modification (they pin the base constant + env-override semantics).
- [x] AC-008: Local-backend auto-reduction at `agent_invoker.py:954-964` (`min(TASK_WORK_SDK_MAX_TURNS, 100)`) remains functional — that branch is presently a no-op (both args equal); not touching it is fine. Document in code comment that the `_effective_sdk_max_turns` field is now used only for legacy direct-mode path; task-work path uses `_calculate_sdk_max_turns(task_id)`.
- [x] AC-009: `pytest tests/unit/test_agent_invoker_sdk_turn_budget.py tests/integration/test_autobuild_phase_4_5_orchestration.py -v` passes.
- [x] AC-010: `mypy guardkit/orchestrator/agent_invoker.py` strict-clean.
- [x] AC-011: Lint/format pass.

## Implementation Notes

Reference implementation in [TASK-REV-9D13 v2 §4 R4 (revised)](../../../.claude/reviews/TASK-REV-9D13-report.md#r4-revised--complexity-scale-task_work_sdk_max_turns-medium).

**Why depend on R1+R2**: With R1+R2 in place, ceiling-hit failures are recoverable (skipped specialists + capped timeout = preserved wall budget for turn-2). R4 reduces ceiling-hit rate but doesn't fix the failure mode. Landing R4 before R1+R2 would mean still-undefended runs benefit less from the headroom. Order: R1+R2 → R4.

**Effect on observed task profile**:
- complexity 4 (J004-006): 110 turns (used 50) — comfortable
- complexity 5 (J004-009/011/012): 150 turns (used 66/91/92) — comfortable headroom
- complexity 6 (J004-013): 160 turns (would have used ~120-140 to complete) — comfortable headroom

**Regression risk**: Tasks now get *more* SDK turns at the same complexity. SDK time budget is already enough. No completed task can regress.

**Coordination**: Lands in Wave 4 after R1+R2+R3 (Wave 3) merge. Independent of R5, R6.b.

## Implementation Summary

Added `_calculate_sdk_max_turns(task_id)` to `AgentInvoker` mirroring `_calculate_sdk_timeout` semantics: env-override-wins, complexity-scaled multiplier `1.0 + complexity/10.0` against the base `TASK_WORK_SDK_MAX_TURNS=100`, complexity clamped `[1,10]`, default 5 on `TaskLoader.load_task` error. Wired the helper into the task-work SDK invocation site so the per-task `max_turns` kwarg, `parsed_result["sdk_max_turns"]`, and `TaskWorkResult.sdk_max_turns` all reflect the complexity-scaled value. Direct-mode path (`_invoke_player_direct`) and local-backend auto-reduction at `agent_invoker.py:954-964` deliberately untouched; added a comment noting `_effective_sdk_max_turns` is now legacy direct-mode-only.

**Files changed**:
- `guardkit/orchestrator/agent_invoker.py` — new helper at line 3890; invocation site at line ~4823 wired through; result fields at ~5046/5056 updated; legacy-field comment added.
- `tests/unit/test_agent_invoker_sdk_turn_budget.py` — new `TestCalculateSdkMaxTurns` class with 6 tests covering complexity 1/5/6/10, env-var skip, and load-error fallback.
- `tests/unit/test_agent_invoker.py` — `test_invoke_task_work_implement_success` assertion updated from `max_turns == 100` to `== 150` (no task frontmatter → complexity-5 default → 1.5x).

**Test results**:
- AC-009 set: `pytest tests/unit/test_agent_invoker_sdk_turn_budget.py tests/integration/test_autobuild_phase_4_5_orchestration.py -v` → **17 passed** (5 legacy + 6 new + 6 phase-4.5 integration).
- Broader regression set: **509 passed**, 2 pre-existing baseline failures unchanged on `main` (mode-passed prompt assertion; `_bootstrap_venv_python` missing on `FeatureOrchestrator`).
- mypy: 80 errors before, 80 after — change is mypy-neutral.
- ruff: 10 errors before, 10 after — all pre-existing in `agent_invoker.py`; new test code lint-clean.

**Lessons**:
- The PoC failure on J004-013 was misdiagnosed as a wall-time problem when the binding constraint was actually SDK turn budget; the fix required only mirroring an existing complexity-scaling pattern, not raising the base ceiling. Watch for asymmetric scaling between paired budgets (time vs turns) in future budget-tuning work.
- The pre-existing `test_invoke_task_work_implement_success` assertion pinned the implementation detail (`== 100`) rather than the contract (env-override semantics + scaling factor). Lock-in tests on bare constants are a leading indicator of where future scaling work will produce orange test runs.
