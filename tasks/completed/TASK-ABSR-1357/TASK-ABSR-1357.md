---
id: TASK-ABSR-1357
title: Suppress agent-invocations Phase-3 advisory for declarative tasks
status: completed
task_type: feature
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T13:00:00Z
completed: 2026-04-27T13:00:00Z
completed_location: tasks/completed/TASK-ABSR-1357/
previous_state: in_review
state_transition_reason: "All ACs met, 12 new tests pass + 443 existing agent_invocations / coach_validator tests pass with zero regressions"
priority: medium
tags: [autobuild, coach, agent-invocations, declarative]
parent_review: TASK-REV-FA04
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
wave: 2
conductor_workspace: autobuild-stall-resilience-wave2-declarative-phase3
complexity: 3
depends_on: []
---

# TASK-ABSR-1357 — Suppress agent-invocations Phase-3 advisory for declarative tasks

## Description

The agent-invocations validator at [`installer/core/commands/lib/agent_invocation_validator.py`](../../../installer/core/commands/lib/agent_invocation_validator.py) hard-codes `get_expected_phases("implement-only") == 3` and `get_expected_phase_list("implement-only") == ['3', '4', '5']`. For `task_type=declarative` (Pydantic models, DTOs, settings, constants — see [`models/task_types.py:24-54`](../../../guardkit/models/task_types.py#L24-L54)), the schema *is* the implementation; there's no meaningful Phase-3 stack-specific specialist to invoke. The advisory currently fires non-blockingly but pollutes Coach feedback strings with a "missing Phase 3" line that the Player has no way to act on.

This task makes the validator task-type-aware so declarative tasks expect 2 phases (`['4', '5']`) in `implement-only` mode.

## Acceptance Criteria

- [x] [`get_expected_phases`](../../../installer/core/commands/lib/agent_invocation_validator.py#L29-L67) accepts an optional `task_type` parameter and returns:
  - `2` when `workflow_mode == "implement-only"` AND `task_type == "declarative"`.
  - The existing values for all other combinations.
- [x] [`get_expected_phase_list`](../../../installer/core/commands/lib/agent_invocation_validator.py#L70-L96) accepts the same parameter and returns:
  - `['4', '5']` when `workflow_mode == "implement-only"` AND `task_type == "declarative"`.
  - The existing list for all other combinations.
- [x] [`identify_missing_phases`](../../../installer/core/commands/lib/agent_invocation_validator.py#L99) and [`validate_agent_invocations`](../../../installer/core/commands/lib/agent_invocation_validator.py#L256) accept and propagate `task_type` through.
- [x] [`_compute_agent_invocations_validation`](../../../guardkit/orchestrator/agent_invoker.py#L5562-L5656) extracts `task_type` from the results dict (or its parent task context) and passes it to the validator.
- [x] The Coach advisory at [`coach_validator.py:675-752`](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L675-L752) continues to fire only when the validator reports a real violation (not just missing Phase 3 for a declarative task).
- [x] Aliases in [`models/task_types.py:266-275`](../../../guardkit/models/task_types.py#L266-L275) (`config`, `dto` → `declarative`) are honored — passing `task_type="config"` should behave like `task_type="declarative"`.
- [x] **New tests** (all in `tests/unit/test_agent_invocation_validator_declarative.py`):
  - `test_get_expected_phases_declarative_implement_only_returns_two`
  - `test_get_expected_phase_list_declarative_implement_only_returns_two_phases`
  - `test_get_expected_phases_other_combinations_unchanged`
  - `test_advisory_silent_for_declarative_task_with_phase_4_and_5_only`
  - `test_advisory_still_fires_for_declarative_task_missing_phase_4`
  - `test_alias_config_treated_as_declarative_in_validator` (parametrized over `config`, `dto`)
- [x] Existing validator tests continue to pass without changes (backward-compat: when `task_type` is None or omitted, behavior matches today). 443 existing agent-invocations / coach-validator tests pass alongside 12 new tests.

## Implementation Notes

- The cleanest signature is `get_expected_phases(workflow_mode: str, task_type: Optional[str] = None) -> int`. Default-None preserves all current call sites until each one is updated.
- Don't change other declarative-mode policies in this task (e.g. `tests_required=True` should remain — those are correct; an unimported module is still a real failure to surface).
- This task does NOT depend on TASK-ABSR-A1B2 or TASK-ABSR-C3D4 — it's an independent quality-of-life improvement.

## Out of Scope

- Changes to `tests_required` or other quality-gate-profile fields for declarative tasks.
- Changes to `direct` mode (which already expects 1 phase — that's correct).
- Cross-stack changes to template-specific Phase-3 specialist resolution at [`phase_specialists.py`](../../../guardkit/orchestrator/phase_specialists.py).

## References

- Review: [TASK-REV-FA04 report](../../../.claude/reviews/TASK-REV-FA04-report.md) §F5, §R4, "Regression Analysis — R4"
- Validator: [`installer/core/commands/lib/agent_invocation_validator.py`](../../../installer/core/commands/lib/agent_invocation_validator.py)
- Profile policy: [`guardkit/models/task_types.py:250-259`](../../../guardkit/models/task_types.py#L250-L259) (DECLARATIVE profile)
