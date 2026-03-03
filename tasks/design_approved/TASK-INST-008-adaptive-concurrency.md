---
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
complexity: 5
consumer_context:
- consumes: EVENT_EMITTER
  driver: guardkit.orchestrator.instrumentation.emitter
  format_note: EventEmitter injected; wave.completed events consumed for concurrency
    decisions
  framework: EventEmitter protocol (async)
  task: TASK-INST-002
dependencies:
- TASK-INST-001
- TASK-INST-002
feature_id: FEAT-INST
id: TASK-INST-008
implementation_mode: task-work
parent_review: TASK-REV-2FE2
status: design_approved
task_type: feature
title: Implement adaptive concurrency controller
wave: 3
---

# Task: Implement Adaptive Concurrency Controller

## Description

Create an adaptive concurrency controller that monitors wave completion events and adjusts worker count based on rate limits and latency trends. Integrates with FeatureOrchestrator wave execution.

## Requirements

### Concurrency Adaptation Policy

1. **Rate limit reduction**: If `rate_limit_count > 0` in a wave, reduce concurrency by 50%
   - Any rate limit triggers reduction (boundary: count of 1 triggers reduction)
   - Minimum concurrency: 1 worker

2. **Latency-based reduction**: If p95 latency exceeds configurable threshold above baseline
   - Default threshold: 2x baseline (100% increase)
   - Baseline established from first wave
   - Just below threshold (e.g., 9999ms when threshold is 10000ms): no action
   - Just above threshold (e.g., 10001ms): reduce concurrency

3. **Recovery increase**: After stability period with no rate limits
   - Default stability window: 5 minutes
   - Increase by +1 worker
   - Maximum concurrency: original configured value

4. **Zero rate limits**: Wave with no rate limit events reports `rate_limit_count = 0`, no adaptation triggered

### ConcurrencyController Class

```python
class ConcurrencyController:
    def __init__(self, initial_workers: int, p95_threshold_pct: float = 100.0, stability_minutes: float = 5.0):
        ...

    def on_wave_completed(self, event: WaveCompletedEvent) -> ConcurrencyDecision:
        """Process wave completion and return concurrency decision."""
        ...

    @property
    def current_workers(self) -> int:
        ...
```

### Integration with FeatureOrchestrator

- ConcurrencyController injected into FeatureOrchestrator
- After each wave, controller consulted for next wave's worker count
- Decisions logged for observability

### ConcurrencyDecision

```python
@dataclass
class ConcurrencyDecision:
    action: Literal["maintain", "reduce", "increase"]
    new_workers: int
    reason: str
```

## Acceptance Criteria

- [ ] Rate limit count > 0 triggers 50% concurrency reduction
- [ ] p95 latency above threshold triggers concurrency reduction
- [ ] p95 just below threshold (e.g., 9999 vs 10000) does not trigger reduction
- [ ] Recovery increases by +1 after 5 minutes stability
- [ ] Zero rate limit count reports 0 and triggers no adaptation
- [ ] Minimum concurrency is 1 worker
- [ ] Maximum concurrency is original configured value
- [ ] ConcurrencyController integrates with FeatureOrchestrator
- [ ] Concurrency decisions logged
- [ ] Unit tests cover all boundary conditions from BDD spec

## File Location

`guardkit/orchestrator/instrumentation/concurrency.py`

## Test Location

`tests/orchestrator/instrumentation/test_concurrency.py`