# Feature: SDK-Based Task-Work Delegation

## Overview

Replace the broken subprocess-based task-work delegation with SDK-based delegation using the Claude Agents SDK `query()` function.

## Problem Statement

The current implementation at `guardkit/orchestrator/agent_invoker.py:1428` attempts to call `guardkit task-work` via subprocess, but this CLI command does not exist. This causes all Player invocations to fail silently.

## Solution

Use the Claude Agents SDK to invoke `/task-work` directly via the `query()` function, then parse the message stream to extract quality gate results and write `task_work_results.json` for Coach validation.

## Architecture

```
Current (BROKEN):
AgentInvoker → subprocess("guardkit task-work") → COMMAND NOT FOUND

Proposed (Option B):
AgentInvoker → query("/task-work {task_id}") → Parse Stream → task_work_results.json
```

## Subtasks

| Task ID | Title | Mode | Wave |
|---------|-------|------|------|
| TASK-SDK-001 | Replace subprocess with SDK query | task-work | 1 |
| TASK-SDK-002 | Implement stream parser for quality gates | task-work | 1 |
| TASK-SDK-003 | Create task_work_results.json writer | task-work | 2 |
| TASK-SDK-004 | Integration testing | task-work | 3 |

## Dependencies

- Claude Agents SDK (`claude-agent-sdk`)
- Existing `_invoke_with_role` pattern in agent_invoker.py

## Acceptance Criteria

- [ ] Player successfully invokes task-work via SDK
- [ ] Quality gate results parsed from stream
- [ ] task_work_results.json created for Coach validation
- [ ] Coach can read and validate results
- [ ] All existing tests pass
- [ ] New integration tests for SDK delegation

## Related

- Review: TASK-REV-fb03 (root cause analysis)
- Caused by: TASK-FB-DEL1 (enabled broken delegation path)
- Research: `docs/research/guardkit-agent/Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md`
