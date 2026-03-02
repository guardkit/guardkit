---
id: TASK-INST-005
title: "Instrument Agent Invoker with LLM and tool events"
task_type: feature
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 3
implementation_mode: task-work
complexity: 6
dependencies:
  - TASK-INST-001
  - TASK-INST-002
  - TASK-INST-003
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
consumer_context:
  - task: TASK-INST-002
    consumes: EVENT_EMITTER
    framework: "EventEmitter protocol (async)"
    driver: "guardkit.orchestrator.instrumentation.emitter"
    format_note: "EventEmitter injected via constructor; call await emitter.emit(event) for each LLM/tool event"
  - task: TASK-INST-003
    consumes: REDACTION_PIPELINE
    framework: "redact_secrets() function"
    driver: "guardkit.orchestrator.instrumentation.redaction"
    format_note: "Call redact_secrets(text) on cmd, stdout_tail, stderr_tail before constructing ToolExecEvent"
---

# Task: Instrument Agent Invoker with LLM and Tool Events

## Description

Add structured event emission to AgentInvoker for every LLM call and tool execution. This is the highest-value instrumentation point as it captures token usage, latency, and prompt profiles.

### Architecture Note

The Player agent uses an **inline prompt builder pattern** (TASK-ACO-002), NOT subprocess delegation to `/task-work`. The method `_build_autobuild_implementation_prompt()` loads `autobuild_execution_protocol.md` and injects task context directly into the SDK prompt. The Coach uses `_build_coach_prompt()`. Both invoke the Claude Agent SDK via `claude_agent_sdk.query()`.

Key instrumentation points:
- `_invoke_task_work_implement()` — Player SDK invocation (wraps `query()`)
- `_invoke_with_role()` — Generic SDK invocation (used by Coach, legacy Player)
- `_build_autobuild_implementation_prompt()` — Player prompt assembly (where `prompt_profile` is determined)
- `_build_coach_prompt()` — Coach prompt assembly

## Requirements

### LLM Call Events

1. Emit `llm.call` event around SDK `query()` calls in `_invoke_task_work_implement()` and `_invoke_with_role()`:
   - `provider`: Detect from base URL (anthropic/openai/local-vllm)
   - `model`: From SDK response or configuration
   - `input_tokens`, `output_tokens`: From SDK usage response
   - `latency_ms`: Wall clock time of the invocation
   - `ttft_ms`: Time to first token (if available from streaming response)
   - `prompt_profile`: From current prompt configuration
   - `agent_role`: player/coach from invocation context
   - `status`: "ok" or "error"
   - `error_type`: If status is "error", classify as rate_limited/timeout/tool_error/other

2. Failed LLM calls (timeout, error) MUST still emit an event:
   - `status` = "error"
   - `latency_ms` = time spent before failure
   - `error_type` populated

3. Prefix cache hit estimation for vLLM:
   - Check vLLM response headers for cache hit indicator
   - If not directly provided, set `prefix_cache_hit` with `prefix_cache_estimated = True`

4. Multiple LLM calls within a single turn produce distinct events:
   - Each event has distinct timestamp
   - Both share same run_id and attempt
   - input_tokens reflects each call independently

### Tool Execution Events

1. Emit `tool.exec` event for every shell command execution:
   - `tool_name`: Sanitised (no shell metacharacters)
   - `cmd`: Redacted via secret redaction pipeline
   - `exit_code`: From command result
   - `latency_ms`: Command execution duration
   - `stdout_tail`: Last N chars, redacted
   - `stderr_tail`: Last N chars, redacted

2. Secret redaction applied before event construction:
   - Call `redact_secrets()` on cmd, stdout_tail, stderr_tail
   - Tool name sanitised against injection

### Prompt Profile Tagging

- Every `llm.call` event MUST include `prompt_profile`
- Profile determined by current configuration (digest_only, digest+graphiti, etc.)
- Profile must be consistent across all events in a run

### Non-Blocking

- Event emission MUST be async and non-blocking
- LLM call MUST NOT wait for event delivery confirmation before proceeding

## Acceptance Criteria

- [ ] llm.call event emitted for every SDK invocation with all required fields
- [ ] Failed LLM calls still emit events with status=error and error_type
- [ ] Prefix cache hit from vLLM flagged as estimated when not directly provided
- [ ] Multiple LLM calls in same turn produce distinct events with distinct timestamps
- [ ] tool.exec event emitted for every shell execution with redacted fields
- [ ] Secret redaction applied to cmd, stdout_tail, stderr_tail
- [ ] Tool names sanitised against shell metacharacters
- [ ] prompt_profile tag present on every llm.call event
- [ ] Event emission does not block LLM call critical path
- [ ] Unit tests cover all event types, error paths, and redaction

## Seam Tests

```python
"""Seam test: verify REDACTION_PIPELINE contract from TASK-INST-003."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("REDACTION_PIPELINE")
def test_redaction_pipeline_format():
    """Verify redact_secrets() sanitises secrets from text.

    Contract: Call redact_secrets(text) on cmd, stdout_tail, stderr_tail
    Producer: TASK-INST-003
    """
    from guardkit.orchestrator.instrumentation.redaction import redact_secrets

    result = redact_secrets("curl -H 'Authorization: Bearer eyJhbGciOi...' https://api.example.com")
    assert "eyJhbGciOi" not in result
    assert "[REDACTED]" in result
```

## File Location

Changes to:
- `guardkit/orchestrator/agent_invoker.py` (AgentInvoker)

New file:
- `guardkit/orchestrator/instrumentation/llm_instrumentation.py` (helper functions)

## Test Location

`tests/orchestrator/instrumentation/test_agent_invoker_events.py`
