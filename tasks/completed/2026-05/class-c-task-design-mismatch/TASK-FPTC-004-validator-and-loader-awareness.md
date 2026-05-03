---
id: TASK-FPTC-004
title: "CoachValidator + FeatureLoader treat operator_handoff tasks as deferred-without-validation"
status: completed
created: 2026-05-03T12:00:00Z
updated: 2026-05-03T13:30:00Z
completed: 2026-05-03T13:30:00Z
previous_state: in_review
state_transition_reason: "All ACs satisfied, 17 new tests pass, 452 regression tests pass"
completed_location: tasks/completed/2026-05/class-c-task-design-mismatch/
priority: high
task_type: feature
implementation_mode: task-work
tags:
  - coach-validator
  - feature-loader
  - operator-handoff
  - quality-gates
  - class-c
  - feature-plan-defects
complexity: 4
estimated_minutes: 90
parent_review: TASK-REV-AUTM
feature_id: FEAT-AUTM
parent_feature: feature-plan-defects
wave: 2
conductor_workspace: feature-plan-defects-wave2-2
dependencies:
  - TASK-FPTC-002
---

# Task: Validator + Loader awareness of operator_handoff

## Description

CoachValidator and FeatureLoader currently expect every task to have
coach-verifiable ACs. An operator-handoff task by definition has
runtime-shaped ACs that no automated check can verify — so the
validator must short-circuit cleanly (not "fail because no ACs are
verifiable") and the loader must accept the task at parse time
without complaint.

## Acceptance Criteria

- [ ] **AC-FPTC-004-01** —
      `guardkit/orchestrator/quality_gates/coach_validator.py`
      contains an explicit branch on `task_type == "operator_handoff"`
      (or `TaskType.OPERATOR_HANDOFF`) at the start of the validation
      entry point that returns a `deferred` / `skip` outcome WITHOUT
      attempting AC matching.
- [ ] **AC-FPTC-004-02** —
      `guardkit/orchestrator/feature_loader.py::FeatureLoader._parse_feature`
      (and any AC-presence checks it performs) does NOT raise or
      record an error when an operator_handoff task has
      runtime-shaped ACs that wouldn't otherwise be coach-verifiable.
- [ ] **AC-FPTC-004-03** — Test fixture: a task with
      `task_type: operator_handoff` and 7 of 8 runtime-shaped ACs
      modelled on TASK-GR-SEED loads cleanly via
      `FeatureLoader.validate_feature` returning no errors.
- [ ] **AC-FPTC-004-04** — Unit test asserts CoachValidator's
      response for an operator_handoff task is a `deferred` /
      `skip` outcome (matching whatever shape TASK-FPTC-003 produces),
      and that no AC-matching machinery (regex, prompt text parser)
      is exercised.
- [ ] **AC-FPTC-004-05** — Existing CoachValidator tests for
      non-operator-handoff task types continue to pass (regression
      guard — strong-signal that the new branch doesn't change
      semantics for the other 8 task types).

## Implementation Notes

- The CoachValidator entry point varies — read the file to find
  whichever method `feature_orchestrator` calls into. The skip branch
  should sit at the top of that method.
- `FeatureLoader._parse_feature` may already accept tasks without
  enforcing AC presence — verify by reading the existing parser
  before assuming an edit is needed. If it already accepts, AC-FPTC-004-02
  is a no-op and the test in AC-FPTC-004-03 is the only deliverable.

## Cross-component contract

**Consumes** TASK-FPTC-002:
- `TaskType.OPERATOR_HANDOFF` enum value
- `get_profile(TaskType.OPERATOR_HANDOFF)` profile (the skip-everything
  flags simplify the validator-side branch logic)

**Aligns with** TASK-FPTC-003:
- The "deferred" outcome shape used here must match what
  feature_orchestrator records (per TASK-FPTC-003's contract block).
  If the two diverge, the feature-complete summary (TASK-FPTC-005)
  won't see consistent records.

## Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` (edit)
- `guardkit/orchestrator/feature_loader.py` (edit, possibly no-op)
- `tests/unit/orchestrator/test_coach_validator_operator_handoff.py`
  (new)
- `tests/unit/orchestrator/test_feature_loader_operator_handoff.py`
  (new — for AC-FPTC-004-03)

## Out of Scope

- Orchestrator dispatch logic (TASK-FPTC-003).
- Feature-complete operator checklist surface (TASK-FPTC-005).

## Implementation Summary

Added a defensive `OPERATOR_HANDOFF` skip branch at the top of
`CoachValidator.validate()` (immediately after `_resolve_task_type`),
which returns a `decision="deferred"` `CoachValidationResult` with
rationale `"operator follow-up — runtime verification required"` —
before any AC-matching machinery runs, before
`read_quality_gate_results`, and before profile lookup. Extended
`CoachValidationResult.decision` Literal to include `"deferred"`
alongside the existing `"approve"` / `"feedback"` values; downstream
consumers that compare against specific strings remain unaffected
because none currently match `"deferred"`. The orchestrator-side skip
(TASK-FPTC-003) is the primary defence; this branch is the paranoid
second line.

`FeatureLoader._parse_feature` and `validate_feature` already accept
operator-handoff tasks with runtime-shaped acceptance criteria — the
loader does not parse AC bodies, so AC-FPTC-004-02 is structurally a
no-op. AC-FPTC-004-03 is pinned by a new test that loads a fixture
with 7 runtime-shaped ACs modelled on TASK-GR-SEED.

## Notes

### Lessons

- The `decision: Literal["approve", "feedback"]` Literal was widely
  consumed via exact string equality across `autobuild.py`, `display.py`,
  `feature_orchestrator.py`. Extending the Literal with `"deferred"` was
  safe because no consumer uses inequality logic that would silently
  catch the new value — every check is `== "approve"` /
  `== "feedback"` / `== "error"`. Future Literal extensions on this
  field need the same audit: the safety property is "no consumer
  accidentally matches the new value", not "no consumer references the
  field".

- The defensive Coach branch is intentionally redundant with
  TASK-FPTC-003's orchestrator-level skip. If both layers ever fire in
  production logs, that's a strong signal the orchestrator-level skip
  has regressed and TASK-FPTC-003's contract is broken — worth a
  follow-up investigation rather than treating Coach's deferred return
  as the new normal.

### Related ADR

- parent_review: TASK-REV-AUTM (recommended this Class-C remediation)
- feature: FEAT-AUTM (feature-plan-defects rollup)

