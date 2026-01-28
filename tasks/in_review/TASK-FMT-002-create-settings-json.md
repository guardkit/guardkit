---
autobuild_state:
  base_branch: main
  current_turn: 5
  last_updated: '2026-01-25T22:19:01.774439'
  max_turns: 5
  started_at: '2026-01-25T22:07:18.583572'
  turns:
  - coach_success: true
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-01-25T22:07:18.583572'
    turn: 1
  - coach_success: true
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-01-25T22:13:27.670544'
    turn: 2
  - coach_success: true
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-01-25T22:15:46.354758'
    turn: 3
  - coach_success: true
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-01-25T22:16:49.094441'
    turn: 4
  - coach_success: true
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-01-25T22:18:09.102721'
    turn: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-FMT
complexity: 4
conductor_workspace: fastmcp-wave1-2
created: 2026-01-24 14:30:00+00:00
dependencies: []
feature_id: FEAT-FMT
id: TASK-FMT-002
implementation_mode: task-work
parallel_group: wave1
parent_review: TASK-REV-A7F3
priority: high
status: in_review
tags:
- template
- mcp
- fastmcp
- settings
- conventions
task_type: scaffolding
title: Create settings.json for fastmcp-python template
updated: 2026-01-24 14:30:00+00:00
wave: 1
---

# Task: Create settings.json for fastmcp-python template

## Description

Create the `settings.json` file for the `fastmcp-python` template. This file defines naming conventions, file organization, layer mappings, and code style specific to MCP server development.

## Reference

Use `installer/core/templates/fastapi-python/settings.json` as structural reference.

## Acceptance Criteria

- [x] File created at `installer/core/templates/fastmcp-python/settings.json`
- [x] Valid JSON with schema_version "1.0.0"
- [x] naming_conventions section includes:
  - `tool`: snake_case functions (search_patterns, get_details)
  - `server`: kebab-case names (design-patterns-server)
  - `resource`: snake_case (patterns_list)
  - `test_file`: test_{feature}.py
  - `test_function`: test_{action}_{entity}
- [x] file_organization section defines:
  - by_feature: false (simple flat structure for MCP)
  - test_location: separate
- [x] layer_mappings section defines:
  - tools: src/tools/
  - resources: src/resources/
  - server: src/
- [x] code_style section defines:
  - async_preferred: true
  - type_hints: required
  - logging_target: stderr (CRITICAL for MCP)
- [x] testing section defines:
  - framework: pytest
  - async_support: pytest-asyncio
  - protocol_testing: true

## MCP-Specific Conventions

```json
{
  "naming_conventions": {
    "tool": {
      "pattern": "{{name}}",
      "case_style": "snake_case",
      "examples": ["search_patterns", "get_pattern_details", "count_patterns"]
    },
    "server": {
      "pattern": "{{name}}-server",
      "case_style": "kebab-case",
      "examples": ["design-patterns-server", "requirements-server"]
    },
    "mcp_parameter": {
      "pattern": "{{name}}",
      "case_style": "camelCase",
      "description": "MCP parameters use camelCase per protocol spec"
    }
  },
  "mcp_specific": {
    "stdout_reserved": true,
    "logging_target": "stderr",
    "parameter_types": "all_strings",
    "path_format": "absolute"
  }
}
```

## Test Execution Log

**Date**: 2026-01-28
**Mode**: TDD (Test-Driven Development)
**Workflow**: implement-only

### TDD RED Phase
- Created test file: `tests/unit/test_fastmcp_python_settings.py`
- Tests: 35 tests covering all acceptance criteria
- Result: All tests FAILED (file did not exist)

### TDD GREEN Phase
- Created: `installer/core/templates/fastmcp-python/settings.json`
- Result: All 35 tests PASSED

### Test Results
```
35 passed in 1.16s
```

### Files Created
1. `installer/core/templates/fastmcp-python/settings.json` (152 lines)
2. `tests/unit/test_fastmcp_python_settings.py` (285 lines)

### Code Review
- **Status**: APPROVED
- **Quality Score**: 9.5/10
- **MCP Protocol Compliance**: 5/5 critical requirements
- **Pattern Consistency**: 95% with fastapi-python template
- **Security**: No vulnerabilities