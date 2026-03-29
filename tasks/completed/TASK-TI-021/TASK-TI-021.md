---
id: TASK-TI-021
title: Fix coach.py.template — switch from create_deep_agent to create_agent
status: completed
created: 2026-03-29T23:30:00Z
updated: 2026-03-30T00:00:00Z
completed: 2026-03-30T00:00:00Z
priority: p0
tags: [template, fix, factory, adversarial, sdk-alignment, d5-invariant]
complexity: 3
parent_review: TASK-REV-32D2
feature_id: FEAT-TI
wave: 0
implementation_mode: task-work
depends_on: []
test_results:
  status: passed
  coverage: 100
  last_run: 2026-03-30T00:00:00Z
---

# Task: Fix coach.py.template — Switch to create_agent()

## Description

TASK-REV-32D2 Finding F2: `coach.py.template` uses `create_deep_agent(tools=[])` which still injects 9 tools via `FilesystemMiddleware` and `SubAgentMiddleware`, violating the D5 invariant ("Coach has NO tools ever"). Also uses hardcoded `from deepagents import create_deep_agent` instead of `{{ProjectName}}` placeholder.

The fix is proven in production — `agentic-dataset-factory/agents/coach.py` enforces D5 at the factory level by:
1. Using `create_agent()` not `create_deep_agent()`
2. Having NO `tools` parameter in the function signature
3. Always passing `tools=[]` to `create_agent()`
4. No `FilesystemMiddleware` in the middleware stack

## Proven Pattern (from agentic-dataset-factory)

```python
from deepagents.backends import FilesystemBackend
from deepagents.middleware import MemoryMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from langchain.agents import create_agent
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware

def create_coach(model_config, system_prompt, memory):
    """Coach has NO tools parameter — D5 invariant enforced by signature."""
    model = create_model(model_config)
    backend = FilesystemBackend(root_dir=".")
    middleware = [
        MemoryMiddleware(backend=backend, sources=memory),
        PatchToolCallsMiddleware(),
        AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
    ]
    return create_agent(
        model=model, tools=[],
        system_prompt=system_prompt, middleware=middleware,
    )
```

## What to Change

Rewrite `installer/core/templates/langchain-deepagents/templates/other/agents/coach.py.template`:
- Replace `from deepagents import create_deep_agent` with proper imports using `{{ProjectName}}` placeholders
- Use `create_agent()` with curated middleware (MemoryMiddleware + PatchToolCallsMiddleware + AnthropicPromptCachingMiddleware)
- Remove `tools` parameter from function signature (D5: Coach NEVER has tools)
- Always pass `tools=[]` to `create_agent()`

## Acceptance Criteria

- [x] `coach.py.template` uses `create_agent()` not `create_deep_agent()`
- [x] No `tools` parameter in `create_coach()` function signature
- [x] `tools=[]` always passed to `create_agent()`
- [x] `MemoryMiddleware` handles AGENTS.md via `FilesystemBackend`
- [x] No `FilesystemMiddleware` in middleware stack
- [x] Uses `{{ProjectName}}` placeholders, not hardcoded `deepagents`
- [x] Tests verify Coach has exactly zero tools

## Effort Estimate

30 minutes
