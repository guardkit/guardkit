---
autobuild_state:
  base_branch: main
  current_turn: 5
  last_updated: '2026-01-25T22:21:55.593010'
  max_turns: 5
  started_at: '2026-01-25T22:07:18.584115'
  turns:
  - coach_success: true
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-01-25T22:07:18.584115'
    turn: 1
  - coach_success: true
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-01-25T22:13:47.279220'
    turn: 2
  - coach_success: true
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-01-25T22:14:48.249031'
    turn: 3
  - coach_success: true
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-01-25T22:19:07.047122'
    turn: 4
  - coach_success: true
    decision: feedback
    feedback: '- Invalid task_type value: implementation. Must be one of: scaffolding,
      feature, infrastructure, documentation, testing, refactor'
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-01-25T22:20:49.095087'
    turn: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-FMT
complexity: 3
conductor_workspace: fastmcp-wave1-1
created: 2026-01-24 14:30:00+00:00
dependencies: []
feature_id: FEAT-FMT
id: TASK-FMT-001
implementation_mode: task-work
parallel_group: wave1
parent_review: TASK-REV-A7F3
priority: high
status: design_approved
tags:
- template
- mcp
- fastmcp
- manifest
task_type: scaffolding
title: Create manifest.json for fastmcp-python template
updated: 2026-01-24 14:30:00+00:00
wave: 1
---

# Task: Create manifest.json for fastmcp-python template

## Description

Create the `manifest.json` file for the `fastmcp-python` template following GuardKit template conventions. This file defines the template's identity, frameworks, patterns, and quality scores.

## Reference

Use `installer/core/templates/fastapi-python/manifest.json` as structural reference.

## Acceptance Criteria

- [ ] File created at `installer/core/templates/fastmcp-python/manifest.json`
- [ ] Valid JSON with schema_version "1.0.0"
- [ ] All required fields populated:
  - `name`: "fastmcp-python"
  - `display_name`: "FastMCP Python Server"
  - `description`: Full description mentioning 10 critical patterns
  - `language`: "Python"
  - `language_version`: ">=3.10"
- [ ] Frameworks array includes:
  - FastMCP (mcp_server purpose)
  - mcp (protocol purpose)
  - pytest (testing purpose)
  - pytest-asyncio (async_testing purpose)
- [ ] Patterns array includes all 10 critical MCP patterns
- [ ] Placeholders defined: ServerName, ToolName, ResourceName, Description
- [ ] Tags include: python, mcp, fastmcp, claude-code, async
- [ ] Category: "integration"
- [ ] Complexity: 5
- [ ] Quality scores defined (target: SOLID 85, DRY 85, YAGNI 90)

## Template Fields

```json
{
  "schema_version": "1.0.0",
  "name": "fastmcp-python",
  "display_name": "FastMCP Python Server",
  "description": "Production-ready FastMCP template for building MCP servers...",
  "version": "1.0.0",
  "author": "GuardKit",
  "source": "https://modelcontextprotocol.io/",
  "language": "Python",
  "language_version": ">=3.10",
  "frameworks": [...],
  "architecture": "MCP Server Pattern",
  "patterns": [
    "Tool Registration in __main__.py",
    "Logging to stderr",
    "Streaming Two-Layer Architecture",
    "String Parameter Conversion",
    "Absolute Path Configuration",
    "Protocol Testing",
    "Docker Non-Root Deployment"
  ],
  "layers": ["tools", "resources", "server"],
  "placeholders": {...},
  "tags": [...],
  "category": "integration",
  "complexity": 5,
  "quality_scores": {...}
}
```

## Test Execution Log

[Automatically populated by /task-work]