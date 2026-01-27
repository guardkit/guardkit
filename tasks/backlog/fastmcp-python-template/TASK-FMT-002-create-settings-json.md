---
id: TASK-FMT-002
title: Create settings.json for fastmcp-python template
status: backlog
task_type: scaffolding
created: 2026-01-24T14:30:00Z
updated: 2026-01-24T14:30:00Z
priority: high
tags:
- template
- mcp
- fastmcp
- settings
- conventions
complexity: 4
parent_review: TASK-REV-A7F3
feature_id: FEAT-FMT
wave: 1
parallel_group: wave1
implementation_mode: task-work
conductor_workspace: fastmcp-wave1-2
dependencies: []
autobuild_state:
  current_turn: 5
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-FMT
  base_branch: main
  started_at: '2026-01-25T22:07:18.583572'
  last_updated: '2026-01-25T22:19:01.774439'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    timestamp: '2026-01-25T22:07:18.583572'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    timestamp: '2026-01-25T22:13:27.670544'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    timestamp: '2026-01-25T22:15:46.354758'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 4
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    timestamp: '2026-01-25T22:16:49.094441'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 5
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    timestamp: '2026-01-25T22:18:09.102721'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Create settings.json for fastmcp-python template

## Description

Create the `settings.json` file for the `fastmcp-python` template. This file defines naming conventions, file organization, layer mappings, and code style specific to MCP server development.

## Reference

Use `installer/core/templates/fastapi-python/settings.json` as structural reference.

## Acceptance Criteria

- [ ] File created at `installer/core/templates/fastmcp-python/settings.json`
- [ ] Valid JSON with schema_version "1.0.0"
- [ ] naming_conventions section includes:
  - `tool`: snake_case functions (search_patterns, get_details)
  - `server`: kebab-case names (design-patterns-server)
  - `resource`: snake_case (patterns_list)
  - `test_file`: test_{feature}.py
  - `test_function`: test_{action}_{entity}
- [ ] file_organization section defines:
  - by_feature: false (simple flat structure for MCP)
  - test_location: separate
- [ ] layer_mappings section defines:
  - tools: src/tools/
  - resources: src/resources/
  - server: src/
- [ ] code_style section defines:
  - async_preferred: true
  - type_hints: required
  - logging_target: stderr (CRITICAL for MCP)
- [ ] testing section defines:
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

[Automatically populated by /task-work]
