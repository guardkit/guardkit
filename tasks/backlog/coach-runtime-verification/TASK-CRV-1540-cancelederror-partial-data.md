---
id: TASK-CRV-1540
title: Extract partial data from response_messages in CancelledError handler
status: backlog
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
priority: high
tags: [cancelederror, state-recovery, agent-invoker, reliability]
task_type: feature
parent_review: TASK-REV-3F40
feature_id: FEAT-8290
wave: 2
implementation_mode: task-work
complexity: 4
dependencies: []
---

# Task: Extract partial data from response_messages in CancelledError handler

## Description

When CancelledError fires at `agent_invoker.py:1951`, the handler immediately re-raises without extracting partial data from `response_messages`, which has been accumulating `AssistantMessage` objects throughout the query loop. This loses valuable information (text blocks, tool calls, file modifications) that could improve state recovery.

Modify the CancelledError handler to extract partial data from `response_messages` before re-raising, and attach it to the exception for state recovery to use.

## Acceptance Criteria

- [ ] CancelledError handler at `agent_invoker.py:~1951` extracts partial data from `response_messages` before re-raising
- [ ] Extracted data includes: text block count, tool call count, file modifications list, last 3 text blocks
- [ ] Partial data stored as invoker instance attribute (`self._last_partial_report`) before re-raising — preferred over exception attribute for cleaner API
- [ ] State recovery in `autobuild.py:_attempt_state_recovery()` reads `invoker._last_partial_report` when available
- [ ] Partial report data used to enrich synthetic report when available
- [ ] Extraction is defensive (handles empty/malformed messages gracefully)
- [ ] Existing CancelledError behavior preserved (still re-raises)
- [ ] New tests for partial data extraction from mock response_messages

## Implementation Notes

Key code path in `agent_invoker.py`:

```python
# Line ~1939-1956 current:
async with asyncio.timeout(self.sdk_timeout_seconds):
    async for message in query(prompt=prompt, options=options):
        response_messages.append(message)  # Accumulates
        ...
except asyncio.CancelledError as exc:
    logger.warning(f"CancelledError caught: {exc}")
    raise  # ← Loses partial data

# PROPOSED: Store as instance attribute before re-raising
except asyncio.CancelledError as exc:
    logger.warning(f"CancelledError caught: {exc}")
    self._last_partial_report = _extract_partial_from_messages(response_messages)
    raise
```

### Design Note

Storing partial data as an instance attribute on the invoker (rather than attaching to the exception object) is preferred because:
- Cleaner API — callers read `invoker._last_partial_report` rather than inspecting exception attributes
- Standard Python pattern — instance state is the normal way to communicate between method calls
- Safely additive — this only enriches data that was previously being discarded, it cannot make things worse

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` (CancelledError handler + new extraction function)
- `guardkit/orchestrator/autobuild.py` (`_attempt_state_recovery()` to use partial data)
- `tests/unit/test_agent_invoker.py` (partial data extraction tests)
