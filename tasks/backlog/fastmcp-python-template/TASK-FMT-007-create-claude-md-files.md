---
id: TASK-FMT-007
title: Create CLAUDE.md files for fastmcp-python template
status: backlog
task_type: implementation
created: 2026-01-24T14:30:00Z
updated: 2026-01-24T14:30:00Z
priority: medium
tags: [template, mcp, fastmcp, documentation]
complexity: 3
parent_review: TASK-REV-A7F3
feature_id: FEAT-FMT
wave: 3
parallel_group: wave3
implementation_mode: direct
conductor_workspace: null
dependencies: [TASK-FMT-003, TASK-FMT-004, TASK-FMT-005, TASK-FMT-006]
---

# Task: Create CLAUDE.md files for fastmcp-python template

## Description

Create the CLAUDE.md documentation files for the `fastmcp-python` template. These files provide top-level guidance for Claude Code when working with MCP server projects.

## Files to Create

1. `installer/core/templates/fastmcp-python/CLAUDE.md` (top-level)
2. `installer/core/templates/fastmcp-python/.claude/CLAUDE.md` (nested)
3. `installer/core/templates/fastmcp-python/README.md` (template docs)

## Acceptance Criteria

### Top-level CLAUDE.md

- [ ] Template overview and purpose
- [ ] Quick start guide for MCP development
- [ ] Link to 10 critical patterns
- [ ] Agent discovery keywords
- [ ] Common commands (testing, running)

### .claude/CLAUDE.md

- [ ] Project context (MCP server development)
- [ ] Core principles (protocol-first, async, testing)
- [ ] Quick reference to patterns
- [ ] Link to agents and rules

### README.md

- [ ] Template description
- [ ] Installation instructions (`guardkit init fastmcp-python`)
- [ ] Directory structure explanation
- [ ] Getting started guide
- [ ] Links to MCP documentation
- [ ] Quality scores and complexity rating

## Content Outline

### CLAUDE.md (top-level)

```markdown
# FastMCP Python Server Template

## Overview
Production-ready template for MCP server development with FastMCP.

## Critical Patterns
This template embeds 10 critical production patterns:
1. Tool Registration in __main__.py
2. Logging to stderr
...

## Getting Started
1. Initialize: `guardkit init fastmcp-python`
2. Configure tools in src/__main__.py
3. Run tests: `pytest tests/`
4. Run server: `python -m src`

## Quality Scores
- SOLID: 85/100
- DRY: 85/100
- YAGNI: 90/100
- Complexity: 5/10
```

## Reference

Use `installer/core/templates/fastapi-python/CLAUDE.md` as structural reference.

## Test Execution Log

[Direct implementation - no /task-work quality gates]
