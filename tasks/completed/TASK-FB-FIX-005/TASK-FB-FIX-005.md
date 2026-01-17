---
id: TASK-FB-FIX-005
title: Fix SDK Message Parsing in TaskWorkInterface
status: completed
created: 2026-01-11T15:00:00Z
updated: 2026-01-11T17:30:00Z
completed: 2026-01-11T17:30:00Z
previous_state: in_review
state_transition_reason: "All acceptance criteria met, tests passing (53/53)"
priority: critical
tags: [feature-build, sdk, bug-fix, critical]
complexity: 4
parent_review: TASK-REV-FB05
implementation_mode: task-work
completed_location: tasks/completed/TASK-FB-FIX-005/
autobuild:
  enabled: false
---

# TASK-FB-FIX-005: Fix SDK Message Parsing in TaskWorkInterface

## Problem Statement

The `TaskWorkInterface._execute_via_sdk()` method incorrectly parses SDK messages, causing feature-build to fail with "Design phase did not return plan path".

**Root Cause** (from TASK-REV-FB05 review):

```python
# Current (Broken) - task_work_interface.py:346-347
async for message in query(prompt=prompt, options=options):
    if hasattr(message, 'content'):
        content = str(message.content)  # BUG: Converts list to string repr
        collected_output.append(content)
```

This produces output like `"[TextBlock(text='Phase 2 complete...'), ToolUseBlock(...)]"` instead of the actual text content, so regex patterns cannot find "Plan saved to:" or other expected patterns.

## Acceptance Criteria

- [x] Replace `str(message.content)` with proper ContentBlock iteration
- [x] Import required types from `claude_agent_sdk` (AssistantMessage, TextBlock, ToolResultBlock, ResultMessage)
- [x] Extract `block.text` from TextBlock instances
- [x] Handle ToolResultBlock content appropriately
- [x] Add debug logging for message types received
- [x] Verify plan path patterns are found in collected output
- [x] All existing tests pass (53/53 tests passing)
- [x] New unit test for message parsing with mock SDK messages (8 new tests added)

## Implementation Summary

### Changes Made

**File Modified**: `guardkit/orchestrator/quality_gates/task_work_interface.py`

**1. Updated SDK imports** (lines 311-323):
- Added `AssistantMessage`, `TextBlock`, `ToolUseBlock`, `ToolResultBlock`, `ResultMessage`

**2. Fixed message collection loop** (lines 349-366):
- Replaced `str(message.content)` with proper ContentBlock iteration
- Added `isinstance()` checks for message types
- Extract `block.text` from TextBlock instances
- Log ToolUseBlock invocations
- Handle ToolResultBlock content when present
- Log ResultMessage completion with turn count

### Tests Added

**File Modified**: `tests/unit/test_task_work_interface.py`

Added `TestSDKContentBlockParsing` class with 8 new tests:
1. `test_extracts_text_from_textblocks` - Verifies plan path extraction
2. `test_extracts_complexity_score_from_textblocks` - Verifies complexity parsing
3. `test_extracts_architectural_score_from_textblocks` - Verifies arch score parsing
4. `test_checkpoint_approved_detected_from_textblocks` - Verifies checkpoint detection
5. `test_handles_mixed_contentblock_types` - Tests TextBlock + ToolUseBlock mix
6. `test_handles_tool_result_block_content` - Tests ToolResultBlock extraction
7. `test_handles_result_message_gracefully` - Tests ResultMessage handling
8. `test_old_str_conversion_bug_produces_invalid_path` - Demonstrates bug fix

### Test Results

```
53 passed, 109 warnings in 1.29s
```

## Evidence

- Review report: `.claude/reviews/TASK-REV-FB05-review-report.md`
- SDK documentation confirms `message.content` is `list[ContentBlock]`
- Fixed code at `task_work_interface.py:349-366` properly iterates ContentBlocks

## Related Tasks

- TASK-REV-FB05 (parent review - completed)
- TASK-FB-FIX-001 through TASK-FB-FIX-004 (completed - prior fixes)

## Notes

This is a **P0 critical fix** - feature-build was completely broken without this change. The fix follows official SDK documentation.
