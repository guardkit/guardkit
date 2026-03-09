---
id: TASK-CRV-1540
title: Extract partial data from response_messages in CancelledError handler
status: completed
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T12:00:00Z
completed: 2026-03-09T12:00:00Z
priority: high
tags: [cancelederror, state-recovery, agent-invoker, reliability]
task_type: feature
parent_review: TASK-REV-3F40
feature_id: FEAT-8290
wave: 2
implementation_mode: task-work
complexity: 4
dependencies: []
previous_state: in_review
state_transition_reason: "All acceptance criteria satisfied, quality gates passed"
completed_location: tasks/completed/TASK-CRV-1540/
---

# Task: Extract partial data from response_messages in CancelledError handler

## Description

When CancelledError fires at `agent_invoker.py:1951`, the handler immediately re-raises without extracting partial data from `response_messages`, which has been accumulating `AssistantMessage` objects throughout the query loop. This loses valuable information (text blocks, tool calls, file modifications) that could improve state recovery.

Modify the CancelledError handler to extract partial data from `response_messages` before re-raising, and attach it to the exception for state recovery to use.

## Acceptance Criteria

- [x] CancelledError handler at `agent_invoker.py:~1951` extracts partial data from `response_messages` before re-raising
- [x] Extracted data includes: text block count, tool call count, file modifications list, last 3 text blocks
- [x] Partial data stored as invoker instance attribute (`self._last_partial_report`) before re-raising — preferred over exception attribute for cleaner API
- [x] State recovery in `autobuild.py:_attempt_state_recovery()` reads `invoker._last_partial_report` when available
- [x] Partial report data used to enrich synthetic report when available
- [x] Extraction is defensive (handles empty/malformed messages gracefully)
- [x] Existing CancelledError behavior preserved (still re-raises)
- [x] New tests for partial data extraction from mock response_messages

## Implementation Summary

### Files Modified
- `guardkit/orchestrator/agent_invoker.py` — Added `_extract_partial_from_messages()` function and wired into CancelledError handler
- `guardkit/orchestrator/autobuild.py` — `_attempt_state_recovery()` reads and injects partial data into synthetic report

### Files Created
- `tests/unit/test_partial_data_extraction.py` — 15 tests covering extraction function and init attribute

### Test Results
- 15/15 new tests PASSED
- 439 existing agent_invoker tests PASSED (no regressions)
- 13 autobuild command execution tests PASSED (no regressions)
