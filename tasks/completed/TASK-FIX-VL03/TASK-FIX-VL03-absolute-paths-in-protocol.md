---
id: TASK-FIX-VL03
title: Use absolute paths in execution protocol for player report
status: completed
created: 2026-02-26T13:00:00Z
updated: 2026-02-26T18:00:00Z
completed: 2026-02-26T18:00:00Z
completed_location: tasks/completed/TASK-FIX-VL03/
priority: high
tags: [autobuild, vllm, bug-fix, execution-protocol, path-anchoring]
complexity: 2
task_type: bug-fix
parent_review: TASK-REV-8A94
feature_id: FEAT-VL01
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Use absolute paths in execution protocol for player report

## Description

The execution protocol (`autobuild_execution_protocol.md`) instructs the agent to write `player_turn_N.json` using a **relative path** (`.guardkit/autobuild/{task_id}/player_turn_{turn}.json`). While the SDK agent's working directory is set to the worktree, less instruction-following models (like Qwen3 via vLLM) may resolve the relative path against the repo root instead.

**Prevention**: Using absolute paths eliminates path ambiguity regardless of model quality.

## Requirements

Add a `{worktree_path}` placeholder to the execution protocol and substitute it alongside `{task_id}` and `{turn}` in the protocol builder.

## Acceptance Criteria

- Protocol instructs agent to write to `{worktree_path}/.guardkit/autobuild/{task_id}/player_turn_{turn}.json`
- `{worktree_path}` is substituted with the absolute worktree path before sending to the agent
- Anthropic models continue to work correctly with absolute paths
- Protocol builder in `agent_invoker.py` handles the new placeholder
- Existing relative path format kept as fallback comment for documentation

## Files to Modify

- `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` (player report path instruction)
- `guardkit/orchestrator/agent_invoker.py` (protocol builder, around line 3321-3325)

## Implementation Notes

```python
# In protocol builder (agent_invoker.py ~line 3322):
protocol_content = protocol_content.replace("{task_id}", task_id)
protocol_content = protocol_content.replace("{turn}", str(turn))
protocol_content = protocol_content.replace("{worktree_path}", str(self.worktree_path))
```
