---
id: TASK-INST-002
title: Implement EventEmitter protocol and backends
task_type: feature
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 2
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-INST-001
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
consumer_context:
- task: TASK-INST-001
  consumes: EVENT_SCHEMAS
  framework: Pydantic v2 BaseModel
  driver: pydantic
  format_note: All event objects are Pydantic BaseEvent subclasses with model_dump()
    for serialization
status: blocked
autobuild_state:
  current_turn: 2
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CF57
  base_branch: main
  started_at: '2026-03-02T13:36:04.687103'
  last_updated: '2026-03-02T14:20:05.221860'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Independent test verification failed:\n  Error detail:\n===========================\
      \ short test summary info ============================\nFAILED tests/knowledge/test_seed_enrichment.py::TestMissingFileHandling::test_missing_manifest_handled_gracefully\
      \ - AssertionError: test-template not found in episodes: ['template_test_template']\n\
      assert False\n +  where False = any(<generator object TestMissingFileHandling.test_missing_manifest_handled_gracefully.<locals>.<genexpr>\
      \ at 0x110084790>)\n============= 1 failed, 270 passed, 2 skipped, 1 warning\
      \ in 2.71s ==============\nResult:\nFAILED tests/knowledge/test_seed_enrichment.py::TestMissingFileHandling::test_missing_manifest_handled_gracefully\
      \ - AssertionError: test-template not found in episodes: ['template_test_template']\n\
      ============= 1 failed, 270 passed, 2 skipped, 1 warning in 2.71s =============="
    timestamp: '2026-03-02T13:36:04.687103'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: error
    feedback: null
    timestamp: '2026-03-02T13:41:19.868782'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: false
---

# Task: Implement EventEmitter Protocol and Backends

## Description

Create the EventEmitter protocol and pluggable backend implementations for event delivery. The emitter is the core abstraction injected into all AutoBuild components.

## Requirements

### EventEmitter Protocol

```python
class EventEmitter(Protocol):
    async def emit(self, event: BaseEvent) -> None: ...
    async def flush(self) -> None: ...
    async def close(self) -> None: ...
```

### Backend Implementations

1. **JSONLFileBackend** (always-on):
   - Append-only JSONL to `.guardkit/autobuild/{task_id}/events.jsonl`
   - Each event is a valid JSON object on its own line
   - Thread-safe writes (file lock or queue)
   - Create parent directories if needed

2. **NATSBackend** (optional):
   - Async NATS publish to configurable subject
   - Connection management with reconnect on failure
   - Graceful degradation: log warning and continue if NATS unavailable
   - Mid-run connection loss: failover logged, no events dropped

3. **CompositeBackend** (fan-out):
   - Emits to ALL registered backends
   - If one backend fails, continue with others
   - JSONL backend always registered (guaranteed local persistence)
   - NATS backend optionally registered based on configuration

4. **NullEmitter** (testing):
   - No-op implementation for unit tests
   - Optionally captures events in memory for assertion

### Non-Blocking Emission

- `emit()` MUST be async and non-blocking
- Event emission MUST NOT block the LLM call critical path
- Use asyncio queue or fire-and-forget pattern

## Acceptance Criteria

- [ ] EventEmitter protocol defined with emit/flush/close methods
- [ ] JSONLFileBackend writes valid JSONL, one event per line
- [ ] NATSBackend publishes async, handles connection failure gracefully
- [ ] CompositeBackend fans out to all backends, tolerates individual failures
- [ ] NullEmitter captures events in memory for test assertions
- [ ] NATS connection loss mid-run falls back to JSONL with warning logged
- [ ] Event emission does not block calling code (async fire-and-forget)
- [ ] Thread-safe concurrent writes from multiple workers
- [ ] Unit tests cover all backends and failure modes

## Seam Tests

The following seam test validates the integration contract with the producer task. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify EVENT_SCHEMAS contract from TASK-INST-001."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("EVENT_SCHEMAS")
def test_event_schemas_serialization():
    """Verify event models produce valid JSON for backend consumption.

    Contract: All event objects are Pydantic BaseEvent subclasses with model_dump()
    Producer: TASK-INST-001
    """
    from guardkit.orchestrator.instrumentation.schemas import LLMCallEvent

    event = LLMCallEvent(
        run_id="test-run",
        task_id="TASK-001",
        agent_role="player",
        attempt=1,
        timestamp="2026-03-01T00:00:00Z",
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        input_tokens=100,
        output_tokens=50,
        latency_ms=1500.0,
        prompt_profile="digest_only",
        status="ok",
    )
    data = event.model_dump()
    assert isinstance(data, dict)
    assert "run_id" in data
    assert "schema_version" in data
```

## File Location

`guardkit/orchestrator/instrumentation/emitter.py`

## Test Location

`tests/orchestrator/instrumentation/test_emitter.py`
