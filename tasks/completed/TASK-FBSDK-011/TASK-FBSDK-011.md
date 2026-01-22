---
id: TASK-FBSDK-011
title: Add verbose SDK invocation logging to AgentInvoker
status: completed
created: 2026-01-19T18:30:00Z
updated: 2026-01-19T20:30:00Z
completed: 2026-01-19T20:30:00Z
priority: high
tags: [feature-build, sdk-integration, logging, diagnostics]
complexity: 3
parent_review: TASK-REV-FB17
wave: 2
implementation_mode: task-work
depends_on:
  - TASK-FBSDK-010
completed_location: tasks/completed/TASK-FBSDK-011/
---

# TASK-FBSDK-011: Add Verbose SDK Invocation Logging

## Problem Statement

The test trace from feature-build shows a 27,703-character truncation that hides the actual SDK error. When the SDK fails, we don't have enough diagnostic information to understand why. The "Duration: 1s" for 5 turns suggests immediate failure, but the error is not captured in logs.

## Solution

Add structured logging BEFORE, DURING, and AFTER SDK invocations to capture:
1. SDK configuration used
2. Message count and types during streaming
3. Exact error details on failure

## Implementation

### Step 1: Add Pre-Invocation Logging

At the start of `_invoke_task_work_implement()` (after options creation, around line 1744):

```python
# Log SDK configuration BEFORE invocation
logger.info(f"[{task_id}] SDK invocation starting")
logger.info(f"[{task_id}] Working directory: {self.worktree_path}")
logger.info(f"[{task_id}] Tools: {options.allowed_tools}")
logger.info(f"[{task_id}] Setting sources: {options.setting_sources}")
logger.info(f"[{task_id}] Permission mode: {options.permission_mode}")
logger.info(f"[{task_id}] Max turns: {options.max_turns}")
logger.info(f"[{task_id}] Timeout: {self.sdk_timeout_seconds}s")
logger.debug(f"[{task_id}] Prompt (first 500 chars): {prompt[:500]}...")
```

### Step 2: Add Message Counting During Streaming

Update the message processing loop (lines 1748-1766):

```python
collected_output: List[str] = []
message_count = 0
assistant_count = 0
tool_count = 0
result_count = 0

async with asyncio.timeout(self.sdk_timeout_seconds):
    async with async_heartbeat(task_id, "task-work implementation"):
        async for message in query(prompt=prompt, options=options):
            message_count += 1

            if isinstance(message, AssistantMessage):
                assistant_count += 1
                for block in message.content:
                    if isinstance(block, TextBlock):
                        collected_output.append(block.text)
                        if "Phase" in block.text or "test" in block.text.lower():
                            logger.debug(f"[{task_id}] Progress: {block.text[:100]}...")
                    elif isinstance(block, ToolUseBlock):
                        tool_count += 1
                        logger.debug(f"[{task_id}] Tool invoked: {block.name}")
                    elif isinstance(block, ToolResultBlock):
                        if block.content:
                            collected_output.append(str(block.content))
            elif isinstance(message, ResultMessage):
                result_count += 1
                logger.info(f"[{task_id}] SDK completed: turns={message.num_turns}")

logger.info(f"[{task_id}] Message summary: total={message_count}, assistant={assistant_count}, tools={tool_count}, results={result_count}")
```

### Step 3: Add Enhanced Error Logging

Update exception handlers to log full context:

```python
except asyncio.TimeoutError:
    error_msg = f"task-work execution exceeded {self.sdk_timeout_seconds}s timeout"
    logger.error(f"[{task_id}] SDK TIMEOUT: {error_msg}")
    logger.error(f"[{task_id}] Messages processed before timeout: {message_count}")
    logger.error(f"[{task_id}] Last output (500 chars): {' '.join(collected_output)[-500:]}")
    # ... rest of handler

except ProcessError as e:
    error_msg = f"SDK process failed (exit {e.exit_code}): {e.stderr}"
    logger.error(f"[{task_id}] SDK PROCESS ERROR: {error_msg}")
    logger.error(f"[{task_id}] Exit code: {e.exit_code}")
    logger.error(f"[{task_id}] Stderr: {e.stderr}")
    logger.error(f"[{task_id}] Messages processed: {message_count}")
    # ... rest of handler

except Exception as e:
    logger.error(f"[{task_id}] SDK UNEXPECTED ERROR: {type(e).__name__}: {e}")
    logger.error(f"[{task_id}] Messages processed: {message_count}")
    logger.exception(f"[{task_id}] Full traceback:")
    # ... rest of handler
```

## Acceptance Criteria

- [x] Pre-invocation logging shows SDK configuration
- [x] Message counting tracks assistant/tool/result messages
- [x] Post-invocation logging shows message summary
- [x] Error logging includes message count and last output
- [x] Log level respects `GUARDKIT_LOG_LEVEL` environment variable
- [x] DEBUG level shows full prompt and individual tool calls
- [x] INFO level shows summary without noise

## Test Plan

1. **Manual Test**: Run with `GUARDKIT_LOG_LEVEL=DEBUG` and verify logs appear
2. **Unit Test**: Mock SDK, verify logging calls are made
3. **Integration Test**: Run feature-build with logging, verify truncated section is captured

## Files to Modify

| File | Changes |
|------|---------|
| `guardkit/orchestrator/agent_invoker.py` | Add logging in `_invoke_task_work_implement()` |

## Notes

- Diagnostic task to capture errors hidden in truncated traces
- Should run after TASK-FBSDK-010 so failure results are also written
- Log format includes task_id for multi-task feature builds
