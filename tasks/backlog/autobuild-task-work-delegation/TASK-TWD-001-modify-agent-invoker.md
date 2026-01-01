---
id: TASK-TWD-001
title: Modify AgentInvoker.invoke_player() for task-work delegation
status: backlog
task_type: implementation
created: 2025-12-31T14:00:00Z
priority: high
tags: [autobuild, task-work-delegation, agent-invoker, core-change]
complexity: 6
parent_feature: autobuild-task-work-delegation
wave: 1
implementation_mode: task-work
conductor_workspace: autobuild-twd-wave1-1
source_review: TASK-REV-RW01
---

# Task: Modify AgentInvoker.invoke_player() for task-work delegation

## Description

Replace the current direct SDK invocation in `AgentInvoker.invoke_player()` with delegation to `task-work --implement-only --mode=tdd`. This enables AutoBuild to leverage the full subagent infrastructure instead of using a generic prompt.

## Current Implementation

```python
# guardkit/orchestrator/agent_invoker.py

async def invoke_player(self, task_id, turn, requirements, feedback=None):
    prompt = self._build_player_prompt(task_id, turn, requirements, feedback)

    # Currently: Direct SDK invocation with generic prompt
    await self._invoke_with_role(
        prompt=prompt,
        agent_type="player",
        allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        permission_mode="acceptEdits",
        model=self.player_model,
    )

    # Load report from file
    report = self._load_agent_report(task_id, turn, "player")
    ...
```

## Target Implementation

```python
async def invoke_player(
    self,
    task_id: str,
    turn: int,
    requirements: str,
    feedback: Optional[str] = None,
    mode: str = "tdd",
) -> AgentInvocationResult:
    """Invoke Player via task-work --implement-only."""
    start_time = time.time()

    try:
        # Write feedback if present (for task-work to read)
        if feedback and turn > 1:
            self._write_coach_feedback(task_id, feedback)

        # Delegate to task-work
        result = await self._invoke_task_work_implement(
            task_id=task_id,
            mode=mode,
        )

        duration = time.time() - start_time

        return AgentInvocationResult(
            task_id=task_id,
            turn=turn,
            agent_type="player",
            success=result.success,
            report=result.output,
            duration_seconds=duration,
            error=result.error if not result.success else None,
        )

    except Exception as e:
        duration = time.time() - start_time
        return AgentInvocationResult(
            task_id=task_id,
            turn=turn,
            agent_type="player",
            success=False,
            report={},
            duration_seconds=duration,
            error=str(e),
        )

async def _invoke_task_work_implement(
    self,
    task_id: str,
    mode: str,
) -> TaskWorkResult:
    """Execute task-work --implement-only in worktree."""
    args = [task_id, "--implement-only", f"--mode={mode}"]

    proc = await asyncio.create_subprocess_exec(
        "guardkit", "task-work", *args,
        cwd=str(self.worktree_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await asyncio.wait_for(
        proc.communicate(),
        timeout=self.sdk_timeout_seconds,
    )

    return TaskWorkResult(
        success=proc.returncode == 0,
        output=self._parse_task_work_output(stdout.decode()),
        error=stderr.decode() if proc.returncode != 0 else None,
    )
```

## Acceptance Criteria

1. `invoke_player()` delegates to task-work instead of direct SDK call
2. Mode parameter (`tdd`, `standard`) is passed through correctly
3. Task-work executes in the worktree context
4. Timeout handling works (uses sdk_timeout_seconds)
5. Errors from task-work are captured and returned properly
6. Return format compatible with existing orchestrator expectations

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` - Main changes
- `guardkit/orchestrator/exceptions.py` - Add TaskWorkResult dataclass if needed

## Testing

1. Unit test: _invoke_task_work_implement() with mocked subprocess
2. Unit test: invoke_player() error handling paths
3. Integration test: Full delegation flow (requires running task-work)

## Notes

- Keep old implementation available behind feature flag for rollback
- Add logging for delegation start/end
- Consider what happens if task is not in design_approved state (TASK-TWD-002 handles this)
