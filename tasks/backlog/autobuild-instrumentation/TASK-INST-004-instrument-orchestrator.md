---
id: TASK-INST-004
title: Instrument AutoBuild orchestrator with lifecycle events
task_type: feature
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 3
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-INST-001
- TASK-INST-002
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
consumer_context:
- task: TASK-INST-002
  consumes: EVENT_EMITTER
  framework: EventEmitter protocol (async)
  driver: guardkit.orchestrator.instrumentation.emitter
  format_note: EventEmitter injected via constructor; call await emitter.emit(event)
    for each lifecycle event
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CF57
  base_branch: main
  started_at: '2026-03-02T22:26:58.422309'
  last_updated: '2026-03-02T22:42:31.050623'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-03-02T22:26:58.422309'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Instrument AutoBuild Orchestrator with Lifecycle Events

## Description

Add structured event emission to AutoBuildOrchestrator and FeatureOrchestrator for task lifecycle and wave management events.

## Requirements

### AutoBuildOrchestrator Changes

1. Accept `EventEmitter` via constructor injection (optional, default NullEmitter)
2. Emit `task.started` when orchestrate() begins:
   - Include `attempt` field (1 for first run)
   - Include `prompt_profile` from configuration
3. Emit `task.completed` when orchestration succeeds:
   - Include `turn_count`, `diff_stats`, `verification_status`, `prompt_profile`
4. Emit `task.failed` when orchestration fails:
   - Include `failure_category` from controlled vocabulary
   - Categorise based on exit condition (test_failure, timeout, env_failure, etc.)
5. Call `emitter.flush()` in finalize phase
6. Call `emitter.close()` on orchestrator cleanup

### FeatureOrchestrator Changes

1. Accept `EventEmitter` via constructor injection (optional, default NullEmitter)
2. Emit `wave.completed` after each wave finishes:
   - Include `wave_id`, `worker_count`, `queue_depth_start`, `queue_depth_end`
   - Include `tasks_completed`, `task_failures`
   - Include `rate_limit_count` (count of rate limit responses in wave)
   - Include `p95_task_latency_ms` (calculated from task durations)
3. Each wave event has distinct `wave_id`

### Failure Category Mapping

Map existing exit conditions to controlled vocabulary:
- Coach approved → N/A (success)
- Max turns exceeded → `other`
- Test failures → `test_failure`
- SDK timeout → `timeout`
- Rate limit → `rate_limit`
- Plan not found → `context_missing`
- State validation → `env_failure`

## Acceptance Criteria

- [ ] EventEmitter injected into AutoBuildOrchestrator via constructor
- [ ] task.started emitted at orchestration begin with attempt field
- [ ] task.completed emitted on success with turn_count, diff_stats, verification_status
- [ ] task.failed emitted on failure with valid failure_category
- [ ] wave.completed emitted after each wave with independent wave_id
- [ ] rate_limit_count of 0 reported for waves with no rate limits
- [ ] emitter.flush() called in finalize phase
- [ ] NullEmitter used as default when no emitter provided
- [ ] Unit tests verify all lifecycle events and failure categories

## Seam Tests

The following seam test validates the integration contract with the producer task. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify EVENT_EMITTER contract from TASK-INST-002."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("EVENT_EMITTER")
def test_event_emitter_protocol_contract():
    """Verify EventEmitter can be injected and called.

    Contract: EventEmitter injected via constructor; call await emitter.emit(event)
    Producer: TASK-INST-002
    """
    from guardkit.orchestrator.instrumentation.emitter import NullEmitter
    from guardkit.orchestrator.instrumentation.schemas import TaskStartedEvent

    emitter = NullEmitter(capture=True)
    event = TaskStartedEvent(
        run_id="test",
        task_id="TASK-001",
        agent_role="player",
        attempt=1,
        timestamp="2026-03-01T00:00:00Z",
    )
    # Verify the emitter accepts BaseEvent subclasses
    import asyncio
    asyncio.run(emitter.emit(event))
    assert len(emitter.captured) == 1
```

## File Location

Changes to:
- `guardkit/orchestrator/autobuild.py` (AutoBuildOrchestrator)
- `guardkit/orchestrator/feature_orchestrator.py` (FeatureOrchestrator)

## Test Location

`tests/orchestrator/instrumentation/test_orchestrator_events.py`
