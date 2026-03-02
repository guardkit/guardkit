---
id: TASK-ABFIX-009
title: Integration tests for timeout, config error, and parallel wave scenarios
task_type: testing
parent_review: TASK-REV-A17A
feature_id: FEAT-CD4C
wave: 4
implementation_mode: task-work
complexity: 6
dependencies: [TASK-ABFIX-003, TASK-ABFIX-004, TASK-ABFIX-005]
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
status: backlog
priority: high
tags: [autobuild, orchestrator, testing, integration]
---

# Task: Integration tests for timeout, config error, and parallel wave scenarios

## Description

Create integration tests that verify the end-to-end behavior of the fixes from Waves 1-2. These tests should exercise the actual integration seams identified in the TASK-REV-A17A review: Feature Orchestrator → AutoBuild → Agent Invoker → Coach Validator → Worktree Checkpoints.

## Review Reference

Cross-cutting requirement from TASK-REV-A17A findings 1-3, 7. The review identified that each component works correctly in isolation but failures occur at integration boundaries. Integration tests are needed to verify the seams.

## Requirements

1. **Timeout budget integration test**:
   - Simulate a multi-turn task where turn 1 consumes ~60% of budget
   - Verify turn 2 receives correct remaining budget
   - Verify Coach grace period is granted when Player succeeds near boundary
   - Verify SDK timeout is capped at remaining budget
2. **Configuration error integration test**:
   - Create a feature with a task having `task_type: enhancement`
   - Verify the task is caught at feature validation (if TASK-ABFIX-002 is done)
   - If validation is bypassed, verify the AutoBuild loop exits immediately (not 3-turn stall)
   - Verify pollution detection is not triggered
3. **Parallel wave isolation test**:
   - Simulate 2+ tasks in a parallel wave
   - Verify Coach tests are isolated from concurrent mutations
   - Verify `parallel_contention` classification works
   - Verify conditional approval for `code` failures in parallel waves
4. **Cancellation timing test**:
   - Simulate Player completing near timeout boundary
   - Verify Coach is still invoked with grace period
   - Verify cancellation vs timeout distinction in final decision

## Files to Create

- `tests/integration/test_timeout_budget.py`
- `tests/integration/test_config_error_fast_exit.py`
- `tests/integration/test_parallel_wave_isolation.py`
- `tests/integration/test_cancellation_timing.py`

## Acceptance Criteria

- [ ] All 4 integration test files created with meaningful scenarios
- [ ] Tests exercise actual integration seams (not just unit mocks)
- [ ] Tests verify the specific failure modes from TASK-REV-A17A findings
- [ ] All tests pass
- [ ] Coverage for the new code paths >=80%
