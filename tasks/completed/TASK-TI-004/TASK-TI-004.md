---
id: TASK-TI-004
title: Factory tool allowlisting with assertions
status: completed
created: 2026-03-27T22:00:00Z
updated: 2026-03-29T12:00:00Z
completed: 2026-03-29T12:00:00Z
priority: p1
tags: [template, factory, security, base-template]
complexity: 4
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 2
implementation_mode: task-work
depends_on: []
completed_location: tasks/completed/TASK-TI-004/
test_results:
  status: passed
  coverage: 85
  last_run: 2026-03-29T12:00:00Z
  tests_passed: 28
  tests_total: 28
---

# Task: Factory Tool Allowlisting with Assertions

## Description

Create factory guard utilities for the `langchain-deepagents` base template that enforce tool allowlisting and prevent the tool leakage bugs that dominated runs 1-6.

## What to Build

### 1. `assert_tool_inventory(agent, expected_tools: set[str])`
- Post-factory assertion: `assert set(t.name for t in agent.tools) == expected_tools`
- Raises `ToolLeakageError` with diff showing unexpected/missing tools
- Called at factory exit, not just in tests

### 2. `create_restricted_agent()` wrapper
- Bypasses `create_deep_agent()` for agents that must NOT have filesystem tools
- Uses `create_agent()` directly with explicit middleware stack
- Inline docstring warnings:
  ```
  # WARNING: create_deep_agent() unconditionally injects FilesystemMiddleware
  # (8 tools: ls, read_file, write_file, edit_file, glob, grep, execute, write_todos)
  # Use create_restricted_agent() for agents that must have curated tool access.
  ```
  ```
  # WARNING: create_agent() unconditionally prepends system_prompt to messages
  # on every ainvoke() call (langchain/agents/factory.py:1270-1271).
  # NEVER pass system role messages in ainvoke() input — the framework owns
  # system message injection. Additional instructions must use user role.
  # Violation causes dual system messages → vLLM 400 Bad Request.
  # See: TASK-REV-R2A1 root cause analysis.
  ```

### 3. `ainvoke()` message contract documentation
- Document the `ainvoke()` input contract as part of factory guards
- **Rule**: Input messages dict must only contain `user` and `assistant` role messages
- **Reason**: `create_agent()` always prepends its `system_prompt` (via `system_message`)
  at invocation time (`factory.py:1270-1271`). Passing a `system` message in input
  creates duplicate system messages that vLLM and other providers reject
- **Source**: Confirmed from installed package source; caused pipeline crash in
  factory-run-2 (TASK-REV-R2A1)
- Add a runtime guard utility:
  ```python
  def assert_no_system_messages(input_data: dict) -> None:
      """Validate ainvoke() input has no system messages.

      create_agent() unconditionally prepends its system_prompt.
      Passing system messages in input causes duplication.
      See TASK-REV-R2A1 for root cause analysis.
      """
      for msg in input_data.get("messages", []):
          role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
          if role == "system":
              raise ValueError(
                  "ainvoke() input must not contain system messages. "
                  "create_agent() prepends system_prompt automatically. "
                  "Use 'user' role for additional instructions."
              )
  ```

### 3. Factory template (`agent_factory.py.j2`)
- Jinja2 template generating factory functions with tool allowlists baked in
- Each agent role gets explicit `allowed_tools` parameter
- Generated code includes the assertion at factory exit

## Fixes Prevented

TRF-003, TRF-012, TRF-016, TRF-017, TASK-OR-006 (dual system message crash)

## Target Location

`lib/factory_guards.py` + `scaffold/agent_factory.py.template` (in the template output)

## Acceptance Criteria

- [x] `assert_tool_inventory()` raises on unexpected tools
- [x] `create_restricted_agent()` bypasses FilesystemMiddleware
- [x] Inline SDK warnings in docstrings (tool leakage + system message contract)
- [x] `assert_no_system_messages()` guard utility for ainvoke() input validation
- [x] Factory template generates allowlisted factories
- [x] Unit tests for leakage detection
- [x] Unit test: `assert_no_system_messages` raises on system role in input
- [x] Unit test: `assert_no_system_messages` passes on user-only input
- [x] Regression test: create_deep_agent + backend=None still leaks (documents the SDK behaviour)
- [x] Regression test: ainvoke with system message in input causes dual system messages (documents the SDK behaviour)

## Effort Estimate

1 day
