---
id: TASK-INST-005c
title: Emit tool execution events with secret redaction
task_type: feature
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 3
implementation_mode: task-work
complexity: 3
dependencies:
- TASK-INST-001
- TASK-INST-002
- TASK-INST-003
- TASK-INST-005a
- TASK-INST-005b
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
consumer_context:
- task: TASK-INST-002
  consumes: EVENT_EMITTER
  framework: EventEmitter protocol (async)
  driver: guardkit.orchestrator.instrumentation.emitter
  format_note: Reuse self._emitter already injected by TASK-INST-005b
- task: TASK-INST-003
  consumes: REDACTION_PIPELINE
  framework: redact_secrets() function
  driver: guardkit.orchestrator.instrumentation.redaction
  format_note: Call redact_secrets(text) on cmd, stdout_tail, stderr_tail before constructing
    ToolExecEvent
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CF57
  base_branch: main
  started_at: '2026-03-02T23:04:54.589806'
  last_updated: '2026-03-02T23:11:34.207324'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-03-02T23:04:54.589806'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Emit Tool Execution Events with Secret Redaction

## Description

Add `tool.exec` event emission when AgentInvoker processes tool invocation messages from the SDK stream. Uses the redaction pipeline from TASK-INST-003, the sanitisation helper from TASK-INST-005a, and the emitter already injected by TASK-INST-005b.

## Scope

This task modifies tool tracking methods in `agent_invoker.py` — specifically `_track_tool_call()` and `_parse_tool_invocations()`. It does NOT touch `_invoke_with_role()` (that was TASK-INST-005b).

## Requirements

### Tool Execution Event Emission

When a tool invocation is detected in the SDK message stream, emit a `ToolExecEvent`:

```python
from guardkit.orchestrator.instrumentation.redaction import redact_secrets
from guardkit.orchestrator.instrumentation.llm_instrumentation import sanitise_tool_name

event = ToolExecEvent(
    run_id=self._run_id,
    task_id=self._current_task_id,
    agent_role=self._current_agent_role,
    attempt=self._current_attempt,
    tool_name=sanitise_tool_name(tool_name),
    cmd=redact_secrets(cmd_text),
    exit_code=exit_code,
    latency_ms=tool_latency_ms,
    stdout_tail=redact_secrets(stdout_tail[-500:]),
    stderr_tail=redact_secrets(stderr_tail[-500:]),
)
asyncio.create_task(self._emitter.emit(event))
```

### Secret Redaction

- `cmd`: Redacted before event construction
- `stdout_tail`: Last 500 chars, redacted
- `stderr_tail`: Last 500 chars, redacted
- Tool name: sanitised (no shell metacharacters)

### Non-Blocking

- Same pattern as TASK-INST-005b: `asyncio.create_task()` for fire-and-forget
- Emission failure logged but not propagated

### SDK Message Stream Parsing

The current `_parse_tool_invocations()` detects tool calls from SDK stream messages. Enhance it to:
- Extract `cmd` from Bash tool invocations
- Extract `exit_code` from tool result messages
- Capture `stdout_tail` and `stderr_tail` from result content
- Note: Not all tools have cmd/exit_code (Write, Edit, etc.) — only emit `tool.exec` events for Bash-type tool invocations that have shell command semantics

### Seam Test

```python
@pytest.mark.seam
@pytest.mark.integration_contract("REDACTION_PIPELINE")
def test_redaction_pipeline_format():
    from guardkit.orchestrator.instrumentation.redaction import redact_secrets
    result = redact_secrets("curl -H 'Authorization: Bearer eyJhbGciOi...' https://api.example.com")
    assert "eyJhbGciOi" not in result
    assert "[REDACTED]" in result
```

## Acceptance Criteria

- [ ] `tool.exec` event emitted for Bash tool invocations in SDK stream
- [ ] Secret redaction applied to cmd, stdout_tail, stderr_tail
- [ ] Tool names sanitised against shell metacharacters
- [ ] Event emission is non-blocking
- [ ] Non-Bash tools (Write, Edit, Glob) do NOT emit tool.exec events
- [ ] stdout_tail and stderr_tail truncated to last 500 chars
- [ ] Existing tool tracking in _track_tool_call still works (file tracking unchanged)
- [ ] Seam test validates redaction contract
- [ ] Unit tests cover: Bash tool event, non-Bash tool ignored, redaction applied, sanitisation

## File Location

Changes to:
- `guardkit/orchestrator/agent_invoker.py` (`_track_tool_call`, `_parse_tool_invocations`)

## Test Location

`tests/orchestrator/instrumentation/test_tool_exec_events.py`
