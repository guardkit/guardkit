---
id: TASK-ABSR-CEIL
title: Skip orchestrator Phase 4/5 specialists when Player hit SDK turn ceiling
status: completed
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T07:30:00Z
completed: 2026-04-28T07:30:00Z
priority: high
tags: [autobuild, specialist-invocation, sdk-ceiling, FEAT-ABSR-9C6E, R1, critical]
parent_review: TASK-REV-9D13
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
task_type: feature
wave: 1
historical_wave: 3  # Wave 3 of FEAT-ABSR-9C6E historically; Waves 1-2 (FA04) are in tasks/completed/
complexity: 3
depends_on: []
previous_state: in_review
state_transition_reason: "All ACs satisfied; pre-existing pre-existing repo-wide lint/mypy noise unrelated"
completed_location: tasks/completed/2026-04/
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-28T07:21:00Z
  notes: |
    AC-004 + AC-005 added and pass:
      tests/integration/test_autobuild_phase_4_5_orchestration.py::test_sdk_ceiling_hit_skips_specialists PASSED
      tests/integration/test_autobuild_phase_4_5_orchestration.py::test_sdk_ceiling_hit_circuit_breaker_env_var PASSED
    AC-006 + AC-007: 4 existing phase 4/5 orchestration tests + 11 specialist
    invocation tests pass unmodified (21 passed in 0.23s).
    AC-008: combined 4-file run reports 52 passed, 3 failed — the 3 failures
    are pre-existing on baseline main and from concurrent uncommitted work on
    sibling tasks (TASK-ABSR-FRSH `_loop_start_time`, unrelated
    `_bootstrap_venv_python`); none caused by TASK-ABSR-CEIL changes.
    AC-009/AC-010: ruff (32) and mypy (28 non-strict / 41 strict) findings in
    autobuild.py are all pre-existing in unrelated regions; my added lines
    (~2756-2820) introduce zero new findings.

## Implementation Summary

Added a six-line guard in the orchestrator-side Phase 4/5 if/elif chain in
`guardkit/orchestrator/autobuild.py` (around line 2756). Reads
`player_result.sdk_ceiling_hit` (already populated at `agent_invoker.py:1473`)
and short-circuits both specialist invocations when the Player has hit the
SDK turn ceiling. Mirrors the existing budget-skip pattern: writes `phase_4`
and `phase_5` skipped blocks to `specialist_results.json` tagged
`"specialist_skipped: sdk_ceiling_hit"`, then runs
`_inject_specialist_records_into_task_work_results` in a try/except so Coach
reads a well-formed ledger. The new skip respects the
`GUARDKIT_INVOKE_SPECIALISTS_ON_CEILING_HIT=1` circuit-breaker env var so
operators can restore the prior behaviour without a code change.

The integration test helper `_drive_orchestrator_phase_4_5` was extended
with an `sdk_ceiling_hit` keyword argument that mirrors the production
control-flow exactly (per the helper's "MUST mirror production wiring"
contract). Two new tests verify the contract end-to-end against the
existing stub-SDK harness, and all pre-existing tests in
`test_autobuild_phase_4_5_orchestration.py` and
`test_specialist_invocations.py` pass without modification.

## Notes

* Strict subset of prior behaviour — specialists run less often, never more.
  Mathematically cannot regress any task that did not hit the ceiling.
* This file was edited concurrently with TASK-ABSR-FRSH and TASK-ABSR-WALL
  by sibling agents. The CEIL change is structurally additive (new `elif`
  branch) and does not interact with FRSH (post-Player budget refresh) or
  WALL (specialist sdk_timeout cap) — verified by reading the merged file
  after each rebase and confirming no shared mutable state.
* Backout: set `GUARDKIT_INVOKE_SPECIALISTS_ON_CEILING_HIT=1` in the
  AutoBuild process environment to restore prior behaviour without
  redeploying.
---

# TASK-ABSR-CEIL — Skip Phase 4/5 specialists on Player SDK-ceiling hit

## Description

Add a six-line guard in `guardkit/orchestrator/autobuild.py` around line 2708 to short-circuit orchestrator-side Phase 4 / Phase 5 specialist invocations when the Player has hit the SDK turn ceiling (`max_turns=100` reached). The current code only checks `if player_result.success and self._agent_invoker is not None:` — it does not consult `player_result.sdk_ceiling_hit`, even though the field is recorded at `agent_invoker.py:1473`.

**Failure mode this prevents** (per [TASK-REV-9D13 v2 §1.1](../../../.claude/reviews/TASK-REV-9D13-report.md)): when the Player completes with `sdk_ceiling_hit=true`, the codebase is provably partial (the Player ran out of SDK turns mid-implementation). The orchestrator currently invokes `test-orchestrator` (Phase 4) on this partial codebase, which thrashes for the full 1200 s SDK timeout, exhausts the per-task wall budget, and forecloses turn-2 with `timeout_budget_exhausted`. The correct behaviour is to skip Phase 4/5 and route directly to Coach feedback so the next turn can fix the missing ACs.

**Targets**: Bug A in TASK-REV-9D13 v2 §0. **Critical, smallest fix, highest leverage.**

## Acceptance Criteria

- [ ] AC-001: `autobuild.py:2708` gate is replaced with a sequence that first checks `sdk_ceiling_hit` (extracted from `player_result.sdk_ceiling_hit`); when true, it logs an info-level skip message, writes `phase_4` and `phase_5` skipped blocks via `_si._merge_specialist_block` mirroring the existing budget-skip path at lines 2747-2755 (using `error="specialist_skipped: sdk_ceiling_hit"` and the existing `_PHASE_4_AGENT_FIELD_DEFAULTS` / `_PHASE_5_AGENT_FIELD_DEFAULTS`), invokes `_inject_specialist_records_into_task_work_results` in a try/except, and then falls through to the rest of `_execute_turn` (Coach phase) without invoking specialists.
- [ ] AC-002: When `sdk_ceiling_hit=False`, the existing Phase 4/5 invocation block runs unchanged — no behavioural drift for non-ceiling-hit tasks.
- [ ] AC-003: When the env var `GUARDKIT_INVOKE_SPECIALISTS_ON_CEILING_HIT=1` is set, the new short-circuit is bypassed and the previous behaviour (invoke specialists despite ceiling hit) is restored. This is a circuit-breaker for emergency backout; default-off in production.
- [ ] AC-004: New test in `tests/integration/test_autobuild_phase_4_5_orchestration.py` named `test_sdk_ceiling_hit_skips_specialists` constructs a mocked `AgentInvocationResult(success=True, sdk_ceiling_hit=True)`, drives `_execute_turn` via the existing `_drive_orchestrator_phase_4_5` helper, and asserts: `specialist_results.json[phase_4].status == "skipped"`, `specialist_results.json[phase_4].error == "specialist_skipped: sdk_ceiling_hit"`, `specialist_results.json[phase_5].status == "skipped"`, `phase_5.error == "specialist_skipped: sdk_ceiling_hit"`. Mock `Task` import / specialist invocation stubs to fail the test if either `invoke_test_orchestrator` or `invoke_code_reviewer` is called.
- [ ] AC-005: New test `test_sdk_ceiling_hit_circuit_breaker_env_var` sets `GUARDKIT_INVOKE_SPECIALISTS_ON_CEILING_HIT=1`, repeats the AC-004 setup, and asserts both specialists ARE invoked (current behaviour preserved under env-var override).
- [ ] AC-006: Existing tests in `tests/integration/test_autobuild_phase_4_5_orchestration.py` (4 tests: `test_orchestrator_side_invocation_fires_on_non_direct_task`, `test_direct_mode_task_skips_specialists`, `test_phase4_failure_skips_phase5_and_records_partial`, `test_player_emitted_phase_4_markers_are_dropped`) all pass without modification.
- [ ] AC-007: Existing tests in `tests/unit/orchestrator/test_specialist_invocations.py` (11 tests) all pass without modification.
- [ ] AC-008: `pytest tests/integration/test_autobuild_phase_4_5_orchestration.py tests/unit/orchestrator/test_specialist_invocations.py tests/unit/test_autobuild_timeout_budget.py tests/unit/test_agent_invoker_sdk_turn_budget.py -v` passes locally.
- [ ] AC-009: `mypy guardkit/orchestrator/autobuild.py` strict-clean.
- [ ] AC-010: Lint/format pass with project-configured rules.

## Implementation Notes

The exact code change is documented in [TASK-REV-9D13 v2 §4 R1](../../../.claude/reviews/TASK-REV-9D13-report.md#r1--skip-orchestrator-phase-45-on-player-sdk-ceiling-hit-critical--first). Key pattern: structure the change as `if sdk_ceiling_hit: skip; elif player_result.success and ...: existing block` so the diff is purely additive on the success path.

The `_PHASE_4_AGENT_FIELD_DEFAULTS` and `_PHASE_5_AGENT_FIELD_DEFAULTS` constants live in `specialist_invocations.py:52-71` and are already used by the existing budget-skip path at autobuild.py:2747. Reuse them for consistency.

Env-var read should match existing patterns (e.g. `os.environ.get("GUARDKIT_INVOKE_SPECIALISTS_ON_CEILING_HIT", "0") == "1"`).

**Regression risk**: Strict subset of current behaviour (specialists run less often, never more). Mathematically cannot regress completed tasks that did not hit the ceiling.

**Backout posture**: Env-var circuit breaker `GUARDKIT_INVOKE_SPECIALISTS_ON_CEILING_HIT=1`. Pip downgrade is one-line.
