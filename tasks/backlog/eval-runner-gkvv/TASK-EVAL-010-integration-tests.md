---
id: TASK-EVAL-010
title: "Implement integration tests covering BDD smoke scenarios"
task_type: testing
parent_review: TASK-REV-EAE8
feature_id: FEAT-GKVV
status: pending
created: 2026-03-01T00:00:00Z
priority: high
tags: [eval-runner, testing, bdd, integration]
complexity: 5
wave: 4
implementation_mode: task-work
dependencies:
  - TASK-EVAL-007
  - TASK-EVAL-008
  - TASK-EVAL-009
---

# Task: Implement Integration Tests Covering BDD Smoke Scenarios

## Description

Implement integration tests that validate the end-to-end eval runner pipeline against the 3 BDD smoke scenarios plus key boundary and edge case scenarios. Tests use mocked agent invocations to avoid actual API calls.

## Acceptance Criteria

- [ ] Smoke test: End-to-end eval with text input produces scored comparison result with per-criterion deltas
- [ ] Smoke test: Workspaces provisioned independently — GuardKit has CLAUDE.md/.guardkit/, vanilla does not
- [ ] Smoke test: Judge scores criteria as deltas (1.0 = GK wins, 0.5 = tie, 0.0 = vanilla wins)
- [ ] Boundary test: Weighted score 0.65 → PASSED, 0.64 → FAILED
- [ ] Boundary test: Weighted score 0.40 → FAILED (not escalated), 0.39 → ESCALATED
- [ ] Boundary test: Perfect tie → 0.5
- [ ] Boundary test: Per-arm timeout derived correctly (total/2 * multiplier)
- [ ] Edge case test: GuardKit arm failure does not abort vanilla arm
- [ ] Edge case test: Vanilla workspace isolation (no GuardKit config)
- [ ] Edge case test: Missing evidence files → not-measurable (not error)
- [ ] Negative test: Unknown input source → InputResolutionError
- [ ] Negative test: Both arms failing still produces result
- [ ] All tests use mocked `EvalAgentInvoker` — no actual Claude API calls
- [ ] Test fixtures provide pre-built evidence files for deterministic scoring
- [ ] Tests follow `pytest` conventions with `@pytest.mark.integration` markers
- [ ] Coverage report for `guardkit/eval/` module ≥ 80%

## Technical Context

- Location: `tests/integration/eval/` (new test directory)
- BDD scenarios: `features/eval-runner-gkvv/eval-runner-gkvv.feature` (32 scenarios, prioritize @smoke)
- Test patterns: `tests/` directory structure (unit, integration, seam markers)
- Mocking: Mock `EvalAgentInvoker._invoke_sdk()` to return pre-built trajectories
- Fixtures: Pre-built evidence files for both arms in `tests/fixtures/eval/`

## BDD Scenario Coverage

All 3 @smoke scenarios (mandatory):
- End-to-end eval with text input
- Workspaces provisioned from respective templates
- Judge scores as deltas

Priority @boundary scenarios:
- Pass/fail/escalate thresholds
- Per-arm timeout
- Missing evidence files
- Perfect tie

Priority @edge-case scenarios:
- Arm failure isolation
- Vanilla workspace isolation

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
