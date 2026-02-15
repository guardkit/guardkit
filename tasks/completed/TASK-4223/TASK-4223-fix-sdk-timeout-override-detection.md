---
id: TASK-4223
title: "Fix _calculate_sdk_timeout() override detection using sentinel pattern"
status: completed
created: 2026-02-15T14:00:00Z
updated: 2026-02-15T15:00:00Z
completed: 2026-02-15T15:05:00Z
priority: low
tags: [autobuild, sdk-timeout, bug-fix]
task_type: implementation
complexity: 2
parent_review: TASK-A5D6
previous_state: in_review
state_transition_reason: "All acceptance criteria met, tests passing"
completed_location: tasks/completed/TASK-4223/
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-15T15:00:00Z
---

# Task: Fix _calculate_sdk_timeout() override detection using sentinel pattern

## Description

The `_calculate_sdk_timeout()` method in `AgentInvoker` uses value comparison against `DEFAULT_SDK_TIMEOUT` (1200) to detect whether the user explicitly set a timeout via CLI. This is fragile: if a user explicitly passes `--sdk-timeout 1200`, the method incorrectly treats it as "not overridden" and applies dynamic multipliers (up to 3x), potentially producing a timeout of 3600s instead of the intended 1200s.

**Root cause**: Comparing the current value against a constant cannot distinguish "user explicitly set this value" from "this is the default".

**Fix**: Use a boolean sentinel flag set at construction time to track whether the timeout was explicitly provided.

## Acceptance Criteria

- [x] AC-001: `AgentInvoker.__init__()` sets `self._sdk_timeout_is_override` boolean based on whether `sdk_timeout_seconds` differs from `DEFAULT_SDK_TIMEOUT`
- [x] AC-002: `_calculate_sdk_timeout()` checks `self._sdk_timeout_is_override` instead of `self.sdk_timeout_seconds != DEFAULT_SDK_TIMEOUT`
- [x] AC-003: Existing `TestCalculateSDKTimeout` tests continue to pass
- [x] AC-004: New test verifies that explicitly passing `DEFAULT_SDK_TIMEOUT` value (1200) still triggers dynamic calculation (documenting current behavior, since we can't distinguish it without protocol changes)
- [x] AC-005: No changes to `AutoBuildOrchestrator` or `FeatureOrchestrator` — fix is contained in `AgentInvoker`

## Changes Made

- `guardkit/orchestrator/agent_invoker.py:594` — Added `_sdk_timeout_is_override` sentinel in `__init__()`
- `guardkit/orchestrator/agent_invoker.py:2143` — Changed override check to use sentinel flag
- `tests/unit/test_agent_invoker.py` — Added 3 new tests to `TestCalculateSDKTimeout`

## Evidence

- Review: TASK-A5D6 (SDK timeout passthrough investigation)
- Analysis: `docs/reviews/autobuild-fixes/run_1_analysis.md`
