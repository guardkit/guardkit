---
complexity: 6
dependencies:
- TASK-SFT-001
feature_id: FEAT-AC1A
id: TASK-SFT-004
implementation_mode: task-work
parent_review: TASK-REV-AC1A
priority: high
status: design_approved
task_type: testing
title: Seam tests S6 — AutoBuild-to-Coach wiring
wave: 2
---

# Seam Tests S6: AutoBuild → Coach Agent Wiring

## Objective

Write seam tests verifying that the AutoBuild orchestrator actually passes acceptance criteria to the Coach validator — catching the historical bug where `_execute_turn()` never passed criteria to `_invoke_coach_safely()`.

## Seam Definition

**Layer A**: AutoBuild orchestrator (`_execute_turn()`, turn loop)
**Layer B**: Coach validation (`CoachValidator.validate()`, `_invoke_coach_safely()`)

## Acceptance Criteria

- [ ] `tests/seam/test_autobuild_coach.py` created
- [ ] Test: acceptance_criteria from task file reaches `CoachValidator.validate()` parameter
- [ ] Test: CoachValidator receives real `QualityGateStatus` (not empty/default)
- [ ] Test: Player task-work results file is actually read by Coach (not mocked away)
- [ ] Test: Coach feedback is propagated back to the turn loop (not silently dropped)
- [ ] Test: Zero-test anomaly detection fires when task has no test files
- [ ] Tests use real `CoachValidator` instance with mocked agent invocation (mock the Claude API call, not the validator logic)
- [ ] All tests pass with `pytest tests/seam/test_autobuild_coach.py -v`

## Historical Context

From failure pattern FP-002: Player self-report unreliability. In the g3 ablation study, removing Coach made output non-functional despite Player claiming success. This seam test ensures the Coach actually receives the data it needs to validate independently.

## Implementation Notes

- Study `guardkit/orchestrator/autobuild.py` for the turn loop structure
- Study `guardkit/orchestrator/quality_gates/coach_validator.py` for validation interface
- The key seam is between `_execute_turn()` and `CoachValidator` — data must flow, not be lost