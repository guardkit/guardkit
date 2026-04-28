---
id: TASK-ABSR-MAXT
title: Complexity-scale TASK_WORK_SDK_MAX_TURNS analogously to sdk_timeout
status: backlog
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
priority: medium
tags: [autobuild, sdk-budget, complexity-scaling, FEAT-ABSR-9C6E, R4]
parent_review: TASK-REV-9D13
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
task_type: feature
wave: 4
complexity: 4
depends_on:
  - TASK-ABSR-CEIL
  - TASK-ABSR-WALL
test_results:
  status: pending
  coverage: null
  last_run: null
---

# TASK-ABSR-MAXT — Complexity-scale `TASK_WORK_SDK_MAX_TURNS`

## Description

Add `_calculate_sdk_max_turns(task_id)` on `AgentInvoker`, mirroring the existing `_calculate_sdk_timeout` complexity-scaling at `agent_invoker.py:3795-3877`. Currently `TASK_WORK_SDK_MAX_TURNS = 100` is a hardcoded constant at `agent_invoker.py:301`. Successful complexity-5 tasks in FEAT-J004-702C run-2 used 91 (J004-011) and 92 (J004-012) SDK turns — within ceiling-adjacency. Complexity-6 J004-013 needed >100 and hit the ceiling.

**SDK time budget already complexity-scales** (formula `1.0 + complexity/10` at agent_invoker.py:3853, multiplied by mode and backend); SDK turn budget does not. This asymmetry is the actual binding constraint for complex tasks: the Player has plenty of wall time but runs out of conversation turns.

**Targets**: Bug F in TASK-REV-9D13 v2 §0. **MED priority — reduces ceiling-hit rate independently of R1+R2.**

## Acceptance Criteria

- [ ] AC-001: New private method `_calculate_sdk_max_turns(self, task_id: str) -> int` on `AgentInvoker`. Behaviour: if `_SDK_MAX_TURNS_IS_OVERRIDE` (env-var override) returns `TASK_WORK_SDK_MAX_TURNS` unchanged (env-var-wins semantics, matches `_calculate_sdk_timeout`). Else load complexity from task frontmatter via `TaskLoader.load_task(task_id, self.worktree_path)`, clamp to `[1, 10]`, default 5 on error. Compute `multiplier = 1.0 + (complexity / 10.0)` matching the existing `_calculate_sdk_timeout` formula. Return `int(TASK_WORK_SDK_MAX_TURNS * multiplier)`.
- [ ] AC-002: At the SDK invocation site that currently uses `self._effective_sdk_max_turns` for `task-work` invocations, replace with `self._calculate_sdk_max_turns(task_id)`. Locate via grep for `_effective_sdk_max_turns` in `agent_invoker.py`; current value-set logic at lines 954-964 should remain (handles local-backend auto-reduction).
- [ ] AC-003: Log line at SDK invocation start should report effective max_turns alongside SDK timeout: `logger.info(f"[{task_id}] Max turns: {effective_max_turns} (base={base}, complexity={complexity} x{multiplier:.1f})")`.
- [ ] AC-004: Env var `GUARDKIT_SDK_MAX_TURNS` continues to take precedence (current behaviour at agent_invoker.py:301-302). When set explicitly via env var, complexity scaling does NOT apply (matches `_calculate_sdk_timeout` for `_sdk_timeout_is_override`).
- [ ] AC-005: Update existing tests in `tests/unit/test_agent_invoker_sdk_turn_budget.py`: `test_default_sdk_max_turns_is_100` continues to pass (asserts the **base constant**, not the effective value). Add new tests: `test_complexity_scaling_at_complexity_1` (expects ~110), `test_complexity_scaling_at_complexity_5` (expects ~150), `test_complexity_scaling_at_complexity_6` (expects ~160), `test_complexity_scaling_at_complexity_10` (expects ~200), `test_env_var_override_skips_complexity_scaling` (env var set → returns 100 ignoring complexity).
- [ ] AC-006: Test for missing/malformed task frontmatter: `test_complexity_defaults_to_5_on_load_error` — patch TaskLoader to raise; expect default complexity-5 multiplier (1.5x, returns 150).
- [ ] AC-007: Existing 5 tests in `tests/unit/test_agent_invoker_sdk_turn_budget.py` continue to pass without modification (they pin the base constant + env-override semantics).
- [ ] AC-008: Local-backend auto-reduction at `agent_invoker.py:954-964` (`min(TASK_WORK_SDK_MAX_TURNS, 100)`) remains functional — that branch is presently a no-op (both args equal); not touching it is fine. Document in code comment that the `_effective_sdk_max_turns` field is now used only for legacy direct-mode path; task-work path uses `_calculate_sdk_max_turns(task_id)`.
- [ ] AC-009: `pytest tests/unit/test_agent_invoker_sdk_turn_budget.py tests/integration/test_autobuild_phase_4_5_orchestration.py -v` passes.
- [ ] AC-010: `mypy guardkit/orchestrator/agent_invoker.py` strict-clean.
- [ ] AC-011: Lint/format pass.

## Implementation Notes

Reference implementation in [TASK-REV-9D13 v2 §4 R4 (revised)](../../../.claude/reviews/TASK-REV-9D13-report.md#r4-revised--complexity-scale-task_work_sdk_max_turns-medium).

**Why depend on R1+R2**: With R1+R2 in place, ceiling-hit failures are recoverable (skipped specialists + capped timeout = preserved wall budget for turn-2). R4 reduces ceiling-hit rate but doesn't fix the failure mode. Landing R4 before R1+R2 would mean still-undefended runs benefit less from the headroom. Order: R1+R2 → R4.

**Effect on observed task profile**:
- complexity 4 (J004-006): 110 turns (used 50) — comfortable
- complexity 5 (J004-009/011/012): 150 turns (used 66/91/92) — comfortable headroom
- complexity 6 (J004-013): 160 turns (would have used ~120-140 to complete) — comfortable headroom

**Regression risk**: Tasks now get *more* SDK turns at the same complexity. SDK time budget is already enough. No completed task can regress.

**Coordination**: Lands in Wave 4 after R1+R2+R3 (Wave 3) merge. Independent of R5, R6.b.
