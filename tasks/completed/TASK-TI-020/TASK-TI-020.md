---
id: TASK-TI-020
title: Fix factory_guards.py — handle memory via MemoryMiddleware not kwarg
status: completed
created: 2026-03-29T23:30:00Z
updated: 2026-03-30T00:00:00Z
completed: 2026-03-30T00:00:00Z
priority: p0
tags: [template, fix, factory, sdk-alignment, runtime-bug]
complexity: 3
parent_review: TASK-REV-32D2
feature_id: FEAT-TI
wave: 0
implementation_mode: task-work
depends_on: []
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-30T00:00:00Z
  tests_passed: 29
  tests_failed: 0
completed_location: tasks/completed/TASK-TI-020/
---

# Task: Fix factory_guards.py — Handle memory via MemoryMiddleware

## Description

TASK-REV-32D2 Finding F5: `create_restricted_agent()` in `factory_guards.py` passes `memory` as a keyword argument to `create_agent()`, but `create_agent()` does NOT accept a `memory` parameter. This causes a `TypeError` at runtime.

**SDK source verified**: `create_agent()` signature has no `memory` parameter (confirmed from `langchain/agents/factory.py`).

The `memory` parameter exists only on `create_deep_agent()` which handles it internally by adding `MemoryMiddleware` to the middleware stack.

## Proven Pattern (from agentic-dataset-factory)

The exemplar handles memory via `MemoryMiddleware` added to the middleware list:

```python
from deepagents.backends import FilesystemBackend
from deepagents.middleware import MemoryMiddleware

backend = FilesystemBackend(root_dir=".")
middleware = [
    MemoryMiddleware(backend=backend, sources=memory),
    PatchToolCallsMiddleware(),
    AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
]
return create_agent(model=model, tools=tools, system_prompt=system_prompt, middleware=middleware)
```

## What Was Changed

1. **`factory_guards.py`** (lines 88-102): Removed `memory` from kwargs passed to `create_agent()`. When `memory` is provided, creates `MemoryMiddleware(backend=FilesystemBackend(root_dir="."), sources=memory)` and passes it via `middleware` kwarg instead. Imports are lazy.

2. **`test_factory_guards.py`**: Replaced `test_passes_memory_when_provided` with:
   - `test_memory_not_passed_as_kwarg_to_create_agent` — verifies `memory` is NOT in kwargs
   - `test_memory_adds_middleware_to_create_agent` — verifies MemoryMiddleware construction
   - Updated `test_omits_middleware_when_memory_none` to also assert no `middleware` kwarg

## Acceptance Criteria

- [x] `create_restricted_agent()` does NOT pass `memory` kwarg to `create_agent()`
- [x] When `memory` is provided, `MemoryMiddleware` is added to middleware list
- [x] `MemoryMiddleware` uses `FilesystemBackend(root_dir=".")` for file reading
- [x] `assert_tool_inventory()` still works after the change
- [x] Existing tests pass
- [x] New test verifies no `TypeError` when `memory` is provided

## Effort Estimate

1 hour
