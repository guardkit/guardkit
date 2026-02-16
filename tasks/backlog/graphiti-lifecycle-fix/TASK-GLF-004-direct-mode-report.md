---
id: TASK-GLF-004
title: Fix direct mode Player report generation
task_type: fix
parent_review: TASK-REV-50E1
feature_id: FEAT-408A
wave: 2
implementation_mode: task-work
complexity: 5
dependencies:
  - TASK-GLF-001
  - TASK-GLF-002
status: pending
priority: medium
tags: [autobuild, direct-mode, player-report, agent-invoker]
---

# Task: Fix direct mode Player report generation

## Description

Direct mode SDK invocations don't produce `player_turn_N.json`. The `_retry_with_backoff` correctly fails to find the file, triggering state recovery and wasting a turn. This affected TASK-SFT-010 in Run 4.

## Root Cause (from TASK-REV-50E1 Finding 3)

**File**: `guardkit/orchestrator/agent_invoker.py`, lines 2493-2555

Sequence:
1. SDK invoked via `_invoke_with_role()` (line 2493) — SDK does NOT write `player_turn_N.json`
2. 0.1s sleep (line 2504)
3. `_retry_with_backoff` tries to load report (line 2509) — 3 retries, ALL FAIL
4. `PlayerReportNotFoundError` raised and caught (line 2537)
5. Error handler writes minimal error report (lines 2542-2555): `{"task_id": "...", "turn": 1}`
6. State recovery loads this empty error report (0 files, 0 tests)
7. Coach requests another turn — **1 wasted turn**

The writes at run log lines 1977-1978 are from the ERROR HANDLER, not from the SDK.

## Acceptance Criteria

- [ ] AC-001: Direct mode SDK invocation produces a valid `player_turn_N.json` before `_load_agent_report` is called
- [ ] AC-002: The report contains meaningful data about what the SDK actually did (files modified, tests run, etc.)
- [ ] AC-003: `_retry_with_backoff` succeeds on first attempt for direct mode tasks
- [ ] AC-004: State recovery is NOT triggered for successful direct mode completions
- [ ] AC-005: Direct mode tasks complete in 1 turn (no wasted recovery turns)
- [ ] AC-006: Task-work delegation path remains unaffected
- [ ] AC-007: Test verifies direct mode produces a valid Player report

## Implementation Approach

After `_invoke_with_role()` completes (line 2499), extract results from the SDK response and write the report BEFORE attempting `_load_agent_report`:

```python
# After _invoke_with_role() (line 2499):
# 1. Extract SDK results from conversation output
sdk_report = self._extract_report_from_sdk_response(sdk_result)

# 2. Write player_turn_N.json from SDK results
if sdk_report:
    self._write_player_report_for_direct_mode(task_id, turn, sdk_report, success=True)

# 3. Now load it (will succeed immediately)
report = self._load_agent_report(task_id, turn, "player")
```

Alternative: Include instructions in the direct mode prompt for the SDK to write its own `player_turn_N.json`.

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/agent_invoker.py` | Extract SDK results, write report before load attempt |

## Test Scope

`tests/**/test_*agent_invoker*direct*` or `tests/**/test_*direct_mode*`

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| SDK response format varies | Validate extracted fields, fall back to existing retry if extraction fails |
| Breaking task-work delegation path | Only modify direct mode code path (lines 2493-2535) |
