---
id: TASK-FB-FIX-001
title: "Fix TaskWorkInterface to invoke SDK"
status: completed
completed: 2026-01-10T15:00:00Z
created: 2026-01-10T11:45:00Z
updated: 2026-01-10T15:00:00Z
priority: high
implementation_mode: task-work
wave: 1
conductor_workspace: fb-fix-wave1-1
complexity: 6
parent_task: TASK-REV-FB04
tags:
  - feature-build
  - pre-loop
  - sdk-integration
  - critical-fix
---

# TASK-FB-FIX-001: Fix TaskWorkInterface to Invoke SDK

## Summary

Fix `TaskWorkInterface.execute_design_phase()` to actually invoke `/task-work --design-only` via Claude Agent SDK instead of returning mock data.

## Problem

Currently, `execute_design_phase()` returns hardcoded mock data:
- `complexity=5`
- `arch_score=80`
- `plan_path=None`

This means no implementation plan is ever created, causing the Player agent to fail.

## Target File

`guardkit/orchestrator/quality_gates/task_work_interface.py`

## Requirements

1. Modify `execute_design_phase()` to invoke SDK with `/task-work {task_id} --design-only`
2. Pass appropriate flags for automation:
   - `--no-questions` - Skip clarification
   - `--defaults` - Use default answers
3. Parse SDK response to extract:
   - Implementation plan content
   - Plan file path
   - Complexity score
   - Architectural review score
4. Return actual results in `DesignPhaseResult`

## Acceptance Criteria

- [x] `execute_design_phase()` invokes SDK with correct prompt
- [x] Implementation plan file is created at expected path
- [x] `DesignPhaseResult.plan_path` contains valid path to created plan
- [x] Complexity and architectural scores are extracted from actual execution
- [x] Timeout handling matches orchestrator configuration
- [x] Unit tests pass with mocked SDK

## Implementation Notes

### SDK Invocation Pattern

Follow the pattern used in `AgentInvoker._invoke_task_work_implement()`:

```python
from claude_code_sdk import ClaudeCodeSession

async def execute_design_phase(self, task_id: str, options: Dict) -> DesignPhaseResult:
    async with ClaudeCodeSession(
        working_directory=str(self.worktree_path),
        permission_mode="default",
    ) as session:
        prompt = self._build_design_prompt(task_id, options)
        result = await session.query(prompt)
        return self._parse_design_result(task_id, result)
```

### Prompt Construction

```python
def _build_design_prompt(self, task_id: str, options: Dict) -> str:
    parts = [f"/task-work {task_id} --design-only"]

    if options.get("no_questions"):
        parts.append("--no-questions")
    elif options.get("defaults"):
        parts.append("--defaults")

    return " ".join(parts)
```

### Result Parsing

Parse the SDK output to find:
1. Plan file path (from "Plan saved to:" message)
2. Complexity score (from Phase 2.7 output)
3. Architectural score (from Phase 2.5B output)
4. Checkpoint result (from Phase 2.8 output)

## Test Strategy

1. **Unit Tests**: Mock SDK client, verify prompt construction and result parsing
2. **Integration Tests**: Run with test worktree, verify plan file created

## Dependencies

- Claude Agent SDK (`claude-code-sdk`)
- Existing `TaskWorkStreamParser` for output parsing

## Estimated Effort

2-4 hours
