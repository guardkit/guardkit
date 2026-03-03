---
id: TASK-INST-009
title: Integration tests for instrumentation pipeline
task_type: testing
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 4
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-INST-004
- TASK-INST-005
- TASK-INST-006
- TASK-INST-007
- TASK-INST-008
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CF57
  base_branch: main
  started_at: '2026-03-02T23:11:38.504302'
  last_updated: '2026-03-02T23:17:00.013695'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-03-02T23:11:38.504302'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Integration Tests for Instrumentation Pipeline

## Description

Create end-to-end integration tests that verify the complete instrumentation pipeline works correctly across all components. Tests validate event flow from emission through backends, NATS fallback behaviour, concurrent worker safety, A/B profile comparison data, and digest validation.

## Requirements

### Test Scenarios (from BDD spec)

1. **End-to-end event stream**: An AutoBuild run produces complete event stream (task.started → llm.call(s) → tool.exec(s) → task.completed/failed)

2. **NATS fallback**: Events written to local JSONL when NATS is not configured
   - Each event is valid JSON on its own line
   - NATS connection lost mid-run: subsequent events fall back to JSONL
   - No events silently dropped
   - Warning logged about NATS fallback

3. **Concurrent worker safety**: 3 parallel workers emit independent events without data corruption
   - Each event has correct task_id for its worker
   - No event contains fields from a different worker's execution

4. **A/B comparison data**: Same task under different profiles produces comparable instrumentation
   - Both runs produce task.completed events with same task_id
   - input_tokens available for both runs
   - latency_ms values available for p50/p95 comparison

5. **Digest validation boundary**: Digest at exactly 700 tokens accepted, 701 triggers warning

6. **Phase 1 migration preservation**: Full rules bundle injected alongside digest, prompt_profile tagged as digest+rules_bundle

7. **Non-blocking emission**: Event emission does not block LLM call critical path (async fire-and-forget verified)

### Test Infrastructure

- Use NullEmitter with capture for assertion
- Use temporary JSONL files for backend tests
- Mock NATS connection for fallback tests
- Use threading/asyncio for concurrent worker tests

## Acceptance Criteria

- [ ] End-to-end test verifies complete event stream for successful task
- [ ] End-to-end test verifies event stream for failed task
- [ ] NATS unavailable: all events written to local JSONL
- [ ] NATS drops mid-run: seamless fallback with warning
- [ ] No events silently dropped in any failure scenario
- [ ] Concurrent workers produce independent, non-corrupted events
- [ ] A/B data: same task produces comparable metrics under different profiles
- [ ] Digest boundary: 700 tokens accepted, 701 warned
- [ ] Phase 1: rules bundle + digest coexist
- [ ] Async emission verified non-blocking

## File Location

`tests/orchestrator/instrumentation/test_integration.py`

## Test Location

Same as file location (this task IS the tests)
