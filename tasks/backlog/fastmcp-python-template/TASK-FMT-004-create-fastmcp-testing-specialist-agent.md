---
id: TASK-FMT-004
title: Create fastmcp-testing-specialist agent
status: in_review
task_type: documentation
created: 2026-01-24 14:30:00+00:00
updated: 2026-01-24 14:30:00+00:00
priority: high
tags:
- template
- mcp
- fastmcp
- agent
- testing
complexity: 4
parent_review: TASK-REV-A7F3
feature_id: FEAT-FMT
wave: 2
parallel_group: wave2
implementation_mode: task-work
conductor_workspace: fastmcp-wave2-2
dependencies:
- TASK-FMT-002
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-FMT
  base_branch: main
  started_at: '2026-01-28T06:57:32.151632'
  last_updated: '2026-01-28T07:25:45.504761'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-01-28T06:57:32.151632'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Create fastmcp-testing-specialist agent

## Description

Create the `fastmcp-testing-specialist` agent for the `fastmcp-python` template. This agent specializes in MCP protocol testing, including unit tests, integration tests, and manual JSON-RPC protocol verification.

## Reference

Use `installer/core/templates/fastapi-python/agents/fastapi-testing-specialist.md` as structural reference.

## Files to Create

1. `installer/core/templates/fastmcp-python/agents/fastmcp-testing-specialist.md` (core)
2. `installer/core/templates/fastmcp-python/agents/fastmcp-testing-specialist-ext.md` (extended)

## Acceptance Criteria

### Core Agent File

- [ ] Valid frontmatter with:
  - name: fastmcp-testing-specialist
  - stack: [python, mcp, fastmcp, pytest]
  - phase: testing
  - capabilities: Testing-specific capabilities
  - keywords: [testing, pytest, protocol, json-rpc, mcp]
  - collaborates_with: [fastmcp-specialist]

- [ ] Role section describing MCP testing specialist
- [ ] Boundaries section:

**ALWAYS**:
- ✅ Test both unit and protocol levels
- ✅ Include string parameter type conversion tests
- ✅ Test streaming tool cancellation handling
- ✅ Verify tools are discoverable via tools/list

**NEVER**:
- ❌ Never assume unit tests passing = MCP integration working
- ❌ Never skip protocol-level JSON-RPC tests

**ASK**:
- ⚠️ Mocking strategy for external services
- ⚠️ Integration test database setup

- [ ] Capabilities section:
  1. Unit Testing with pytest-asyncio
  2. Protocol Testing with JSON-RPC
  3. Streaming Tool Testing
  4. Parameter Conversion Testing
  5. Tool Discovery Testing
  6. Error Response Testing

### Extended Agent File

- [ ] Protocol testing script examples
- [ ] pytest fixtures for MCP testing
- [ ] Mocking patterns
- [ ] CI/CD testing configuration

## Key Testing Patterns (from TASK-REV-MCP)

**Protocol Testing Script**:
```bash
#!/bin/bash
# Test initialization
echo '{"jsonrpc":"2.0","id":1,"method":"initialize",...}' | python -m src

# Test tools/list
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | python -m src

# Test tools/call
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call",...}' | python -m src
```

**String Parameter Test**:
```python
@pytest.mark.asyncio
async def test_tool_string_type_conversion():
    result = await my_tool(param="test", count="5")  # String!
    assert result["count"] == 5
```

## Test Execution Log

[Automatically populated by /task-work]
