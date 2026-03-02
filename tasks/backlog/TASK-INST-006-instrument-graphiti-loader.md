---
id: TASK-INST-006
title: "Instrument Graphiti context loader"
task_type: feature
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 3
implementation_mode: task-work
complexity: 3
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
    framework: "EventEmitter protocol (async)"
    driver: "guardkit.orchestrator.instrumentation.emitter"
    format_note: "EventEmitter injected via constructor; call await emitter.emit(event) for each Graphiti query"
---

# Task: Instrument Graphiti Context Loader

## Description

Add structured event emission to the Graphiti context loader for every context retrieval operation. This enables measuring retrieval cost and token budget impact.

## Requirements

### Graphiti Query Events

1. Emit `graphiti.query` event for every context retrieval:
   - `query_type`: context_loader, nearest_neighbours, or adr_lookup
   - `items_returned`: Number of items retrieved
   - `tokens_injected`: Estimated token count of injected context
   - `latency_ms`: Retrieval duration
   - `status`: "ok" or "error"

2. Graphiti unavailability handling:
   - Emit event with `status = "error"` when Graphiti is unreachable
   - Log warning about Graphiti fallback
   - Run continues with digest-only context (no crash)

### Integration Points

- Identify the Graphiti context loader in `guardkit/integrations/graphiti/`
- Inject EventEmitter into the loader
- Emit events at each retrieval point

## Acceptance Criteria

- [ ] graphiti.query event emitted for every context retrieval
- [ ] query_type correctly identifies the retrieval type
- [ ] tokens_injected estimated for retrieved context
- [ ] Graphiti unavailability emits error event and falls back gracefully
- [ ] Warning logged on Graphiti fallback
- [ ] Run continues with digest-only context when Graphiti unavailable
- [ ] Unit tests cover successful queries, error paths, and fallback

## Seam Tests

```python
"""Seam test: verify EVENT_EMITTER contract from TASK-INST-002."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("EVENT_EMITTER")
def test_event_emitter_accepts_graphiti_events():
    """Verify EventEmitter can emit GraphitiQueryEvent.

    Contract: EventEmitter injected via constructor; call await emitter.emit(event)
    Producer: TASK-INST-002
    """
    from guardkit.orchestrator.instrumentation.emitter import NullEmitter
    from guardkit.orchestrator.instrumentation.schemas import GraphitiQueryEvent

    emitter = NullEmitter(capture=True)
    event = GraphitiQueryEvent(
        run_id="test",
        task_id="TASK-001",
        agent_role="player",
        attempt=1,
        timestamp="2026-03-01T00:00:00Z",
        query_type="context_loader",
        items_returned=5,
        tokens_injected=1200,
        latency_ms=350.0,
        status="ok",
    )
    import asyncio
    asyncio.run(emitter.emit(event))
    assert len(emitter.captured) == 1
```

## File Location

Changes to:
- `guardkit/integrations/graphiti/` (context loader modules)

## Test Location

`tests/orchestrator/instrumentation/test_graphiti_events.py`
