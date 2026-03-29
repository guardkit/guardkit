---
id: TASK-TI-019
title: Fix player.py.template — switch from create_deep_agent to create_agent
status: completed
created: 2026-03-29T23:30:00Z
updated: 2026-03-30T00:20:00Z
completed: 2026-03-30T00:20:00Z
completed_location: tasks/completed/TASK-TI-019/
priority: p0
tags: [template, fix, factory, adversarial, sdk-alignment]
complexity: 3
parent_review: TASK-REV-32D2
feature_id: FEAT-TI
wave: 0
implementation_mode: task-work
depends_on: []
test_results:
  status: passed
  coverage: 100
  last_run: 2026-03-30T00:15:00Z
  tests_passed: 21
  tests_failed: 0
---

# Task: Fix player.py.template — Switch to create_agent()

## Description

TASK-REV-32D2 Finding F1: `player.py.template` uses `create_deep_agent()` which unconditionally injects `FilesystemMiddleware` (adding `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `execute` tools) and `SubAgentMiddleware` (adding `task` tool). This gives the Player 10 unwanted tools including `write_file` and `edit_file`, completely bypassing the orchestrator-gated writes invariant.

The fix is proven in production — `agentic-dataset-factory/agents/player.py` has been running successfully for 7+ hours in a 26-hour production run using the correct pattern.

## Proven Pattern (from agentic-dataset-factory)

```python
from deepagents.backends import FilesystemBackend
from deepagents.middleware import MemoryMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from langchain.agents import create_agent
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware

def create_player(model, tools, system_prompt, memory):
    backend = FilesystemBackend(root_dir=".")
    middleware = [
        MemoryMiddleware(backend=backend, sources=memory),
        PatchToolCallsMiddleware(),
        AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
    ]
    return create_agent(
        model=model, tools=tools,
        system_prompt=system_prompt, middleware=middleware,
    )
```

Key points:
- Uses `create_agent()` NOT `create_deep_agent()` — prevents FilesystemMiddleware injection
- `MemoryMiddleware` with `FilesystemBackend` handles AGENTS.md loading — backend is for memory file reading only
- NO `TodoListMiddleware`, NO `SubAgentMiddleware`, NO `FilesystemMiddleware` in middleware list

## What to Change

Rewrite `installer/core/templates/langchain-deepagents/templates/other/agents/player.py.template` to match the proven exemplar pattern, with `{{ProjectName}}` placeholders.

## Acceptance Criteria

- [x] `player.py.template` uses `create_agent()` not `create_deep_agent()`
- [x] `MemoryMiddleware` handles AGENTS.md injection via `FilesystemBackend`
- [x] No `FilesystemMiddleware` in middleware stack
- [x] Player receives ONLY domain tools (e.g., `search_data`)
- [x] Existing tests updated to verify new factory pattern
- [x] `validate_player_tools()` call retained for additional safety

## Effort Estimate

30 minutes
