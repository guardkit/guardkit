---
id: TASK-FMT-001
title: Create manifest.json for fastmcp-python template
status: backlog
task_type: scaffolding
created: 2026-01-24T14:30:00Z
updated: 2026-01-24T14:30:00Z
priority: high
tags: [template, mcp, fastmcp, manifest]
complexity: 3
parent_review: TASK-REV-A7F3
feature_id: FEAT-FMT
wave: 1
parallel_group: wave1
implementation_mode: task-work
conductor_workspace: fastmcp-wave1-1
dependencies: []
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
