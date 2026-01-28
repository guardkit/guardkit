---
complexity: 4
conductor_workspace: fastmcp-wave2-2
created: 2026-01-24 14:30:00+00:00
dependencies:
- TASK-FMT-002
feature_id: FEAT-FMT
id: TASK-FMT-004
implementation_mode: task-work
parallel_group: wave2
parent_review: TASK-REV-A7F3
priority: high
status: in_review
tags:
- template
- mcp
- fastmcp
- agent
- testing
task_type: documentation
title: Create fastmcp-testing-specialist agent
updated: 2026-01-28T07:30:00Z
wave: 2
implementation_completed: 2026-01-28T07:30:00Z
code_review_score: 97.6
---

# Task: Create fastmcp-testing-specialist agent

## Description

Create the `fastmcp-testing-specialist` agent for the `fastmcp-python` template. This agent specializes in MCP protocol testing, including unit tests, integration tests, and manual JSON-RPC protocol verification.

## Reference

Use `installer/core/templates/fastapi-python/agents/fastapi-testing-specialist.md` as structural reference.

## Files Created

1. `installer/core/templates/fastmcp-python/agents/fastmcp-testing-specialist.md` (core)
2. `installer/core/templates/fastmcp-python/agents/fastmcp-testing-specialist-ext.md` (extended)
3. `tests/test_fastmcp_testing_specialist_agent.py` (validation tests)

## Acceptance Criteria

### Core Agent File

- [x] Valid frontmatter with:
  - name: fastmcp-testing-specialist
  - stack: [python, mcp, fastmcp, pytest]
  - phase: testing
  - capabilities: Testing-specific capabilities
  - keywords: [testing, pytest, protocol, json-rpc, mcp]
  - collaborates_with: [fastmcp-specialist]

- [x] Role section describing MCP testing specialist
- [x] Boundaries section:

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

- [x] Capabilities section:
  1. Unit Testing with pytest-asyncio
  2. Protocol Testing with JSON-RPC
  3. Streaming Tool Testing
  4. Parameter Conversion Testing
  5. Tool Discovery Testing
  6. Error Response Testing

### Extended Agent File

- [x] Protocol testing script examples
- [x] pytest fixtures for MCP testing
- [x] Mocking patterns
- [x] CI/CD testing configuration

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

### TDD Mode Execution - 2026-01-28

**Phase: RED (Generate Tests)**
- Created 27 validation tests in `tests/test_fastmcp_testing_specialist_agent.py`
- Tests covered: file existence, frontmatter, content sections, extended content, integration, quality

**Phase: GREEN (Implementation)**
- Created core agent: `fastmcp-testing-specialist.md` (~6KB)
- Created extended agent: `fastmcp-testing-specialist-ext.md` (~10KB)
- All 27 tests passed (100%)

**Phase: Code Review**
- Quality Score: 97.6/100 (EXCELLENT)
- Acceptance Criteria: 100% met
- Pattern Consistency: 95% with fastapi-testing-specialist
- MCP Pattern Correctness: 100%
- Recommendation: APPROVED

**Test Results Summary**:
```
tests/test_fastmcp_testing_specialist_agent.py::TestFileExistence::test_core_agent_file_exists PASSED
tests/test_fastmcp_testing_specialist_agent.py::TestFileExistence::test_extended_agent_file_exists PASSED
tests/test_fastmcp_testing_specialist_agent.py::TestCoreFrontmatter::* (7 tests) PASSED
tests/test_fastmcp_testing_specialist_agent.py::TestCoreContentSections::* (6 tests) PASSED
tests/test_fastmcp_testing_specialist_agent.py::TestExtendedContent::* (7 tests) PASSED
tests/test_fastmcp_testing_specialist_agent.py::TestAgentIntegration::* (2 tests) PASSED
tests/test_fastmcp_testing_specialist_agent.py::TestContentQuality::* (3 tests) PASSED

Total: 27 passed, 0 failed, 0 skipped
```
