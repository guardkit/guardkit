---
id: TASK-SDK-001
title: Replace subprocess with SDK query for task-work delegation
status: completed
task_type: implementation
created: 2026-01-10T11:00:00Z
updated: 2026-01-10T12:45:00Z
completed: 2026-01-10T12:45:00Z
priority: critical
tags: [sdk-delegation, agent-invoker, feature-build, critical-fix]
complexity: 5
wave: 1
parent_feature: sdk-delegation-fix
depends_on: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met, tests passing"
completed_location: tasks/completed/sdk-delegation-fix/
---

# Replace subprocess with SDK query for task-work delegation

## Description

Replace the broken subprocess call to `guardkit task-work` with a direct SDK `query()` call to invoke the `/task-work` slash command. This is the core fix for the task-work delegation failure.

## Current State (Broken) - FIXED ✅

`guardkit/orchestrator/agent_invoker.py:1428-1431`:

```python
# OLD CODE (removed)
proc = await asyncio.create_subprocess_exec(
    "guardkit",
    "task-work",  # THIS COMMAND DOESN'T EXIST
    *args,
    ...
)
```

## Target State - IMPLEMENTED ✅

```python
async def _invoke_task_work_implement(self, task_id: str, mode: str) -> TaskWorkResult:
    options = ClaudeAgentOptions(
        cwd=str(self.worktree_path),
        allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
        permission_mode="acceptEdits",
        max_turns=50,
        setting_sources=["project"],
    )

    async with asyncio.timeout(self.sdk_timeout_seconds):
        async for message in query(
            prompt=f"/task-work {task_id} --implement-only --mode={mode}",
            options=options
        ):
            # Stream processing handled by TASK-SDK-002
            pass

    return TaskWorkResult(success=True, output={})
```

## Acceptance Criteria

- [x] `_invoke_task_work_implement` uses SDK `query()` instead of subprocess
- [x] `ClaudeAgentOptions` configured with correct `cwd` (worktree path)
- [x] `allowed_tools` includes all tools needed by task-work
- [x] `permission_mode` set to "acceptEdits"
- [x] Timeout handling uses existing `sdk_timeout_seconds`
- [x] Existing tests updated/passing
- [x] New unit tests for SDK invocation path

## Implementation Summary

### Changes Made

**guardkit/orchestrator/agent_invoker.py** (lines 1398-1524):
- Replaced `asyncio.create_subprocess_exec` with Claude Agent SDK `query()` invocation
- Configured `ClaudeAgentOptions` with appropriate tools and permissions
- Added proper error handling for SDK-specific exceptions
- Collects message content for parsing

**tests/unit/test_agent_invoker.py** (TestInvokeTaskWorkImplement class):
- Updated all 8 tests to mock SDK `query()` instead of subprocess
- Added comprehensive tests for error handling scenarios

### Test Results

```
tests/unit/test_agent_invoker.py: 118 passed ✅
```

8 tests for SDK invocation:
- test_invoke_task_work_implement_success
- test_invoke_task_work_implement_sdk_process_error
- test_invoke_task_work_implement_timeout
- test_invoke_task_work_implement_cli_not_found
- test_invoke_task_work_implement_sdk_import_error
- test_invoke_task_work_implement_mode_passed
- test_invoke_task_work_implement_json_decode_error
- test_invoke_task_work_implement_collects_output

## Related

- TASK-SDK-002: Stream parser (parallel, same wave)
- Reference: `_invoke_with_role` method in same file
