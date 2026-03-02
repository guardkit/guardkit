---
id: TASK-INST-005b
title: "Emit LLM call events from _invoke_with_role"
task_type: feature
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 3
implementation_mode: task-work
complexity: 4
dependencies:
  - TASK-INST-001
  - TASK-INST-002
  - TASK-INST-005a
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
consumer_context:
  - task: TASK-INST-002
    consumes: EVENT_EMITTER
    framework: "EventEmitter protocol (async)"
    driver: "guardkit.orchestrator.instrumentation.emitter"
    format_note: "EventEmitter injected via constructor; call await emitter.emit(event)"
---

# Task: Emit LLM Call Events from _invoke_with_role

## Description

Add `llm.call` event emission to `AgentInvoker._invoke_with_role()`. Uses the helper functions from TASK-INST-005a and the EventEmitter from TASK-INST-002. This is the highest-value instrumentation point — it captures token usage, latency, and prompt profiles for every SDK invocation.

## Scope

This task ONLY modifies `_invoke_with_role()` (lines 1786-1919 of `agent_invoker.py`). It does NOT touch tool execution tracking.

## Requirements

### EventEmitter Injection

- Add optional `emitter: Optional[EventEmitter]` parameter to `AgentInvoker.__init__()`
- Default to `NullEmitter()` when not provided (zero behaviour change for existing callers)
- Store as `self._emitter`

### LLM Call Event Emission

Wrap the SDK `query()` call in `_invoke_with_role()` with instrumentation:

```python
from guardkit.orchestrator.instrumentation.llm_instrumentation import (
    detect_provider, extract_token_usage, measure_latency, classify_error
)

# Before the query() call:
with measure_latency() as latency:
    try:
        async for message in query(prompt=prompt, options=options):
            # ... existing message handling ...
        status = "ok"
        error_type = None
    except Exception as e:
        status = "error"
        error_type = classify_error(e)
        raise  # Re-raise after recording

# After (in finally block):
input_tokens, output_tokens = extract_token_usage(...)
event = LLMCallEvent(
    run_id=self._run_id,
    task_id=self._current_task_id,
    agent_role=agent_type,
    attempt=self._current_attempt,
    provider=detect_provider(self._base_url, model),
    model=model or "default",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    latency_ms=latency.ms,
    prompt_profile=self._prompt_profile,
    status=status,
    error_type=error_type,
)
asyncio.create_task(self._emitter.emit(event))
```

### Non-Blocking Emission

- Event emission via `asyncio.create_task()` — fire-and-forget
- The LLM call MUST NOT wait for event delivery confirmation
- If emission fails, log a warning but do not propagate the error

### Failed Calls Still Emit

- Timeout, API errors, process errors: all MUST still emit an event
- `status = "error"` with appropriate `error_type`
- `latency_ms` captures time until failure

### Multiple Calls Per Turn

- Each invocation of `_invoke_with_role()` produces exactly one `llm.call` event
- Multiple calls within a turn have distinct timestamps (guaranteed by `datetime.now().isoformat()`)

### Prompt Profile

- Read from `self._prompt_profile` (set during prompt assembly)
- If not set, default to `"digest+rules_bundle"` (Phase 1 baseline)

## Acceptance Criteria

- [ ] `llm.call` event emitted for every successful SDK invocation
- [ ] `llm.call` event emitted for failed SDK invocations (timeout, API error)
- [ ] Event includes all required fields: run_id, task_id, agent_role, provider, model, tokens, latency, prompt_profile, status
- [ ] Event emission is non-blocking (asyncio.create_task)
- [ ] Emission failure does not propagate to caller
- [ ] NullEmitter default preserves existing behaviour (no event emission when emitter not injected)
- [ ] Multiple calls in same turn produce distinct events
- [ ] Existing tests in test_agent_invoker.py still pass (zero regression)
- [ ] New tests cover: successful emission, error emission, non-blocking behaviour, NullEmitter default

## File Location

Changes to:
- `guardkit/orchestrator/agent_invoker.py` (`__init__` and `_invoke_with_role` only)

## Test Location

`tests/orchestrator/instrumentation/test_llm_call_events.py`
