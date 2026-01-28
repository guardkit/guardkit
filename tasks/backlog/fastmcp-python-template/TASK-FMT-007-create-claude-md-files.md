---
id: TASK-FMT-007
title: Create CLAUDE.md files for fastmcp-python template
status: in_review
task_type: documentation
created: 2026-01-24 14:30:00+00:00
updated: 2026-01-24 14:30:00+00:00
priority: medium
tags:
- template
- mcp
- fastmcp
- documentation
complexity: 3
parent_review: TASK-REV-A7F3
feature_id: FEAT-FMT
wave: 3
parallel_group: wave3
implementation_mode: direct
conductor_workspace: null
dependencies:
- TASK-FMT-003
- TASK-FMT-004
- TASK-FMT-005
- TASK-FMT-006
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-FMT
  base_branch: main
  started_at: '2026-01-28T07:28:23.352867'
  last_updated: '2026-01-28T07:35:19.842148'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-01-28T07:28:23.352867'
    player_summary: 'Created three CLAUDE.md documentation files for fastmcp-python
      template:


      1. Top-level CLAUDE.md (5.8KB): Complete template reference with all 10 critical
      MCP patterns, architecture overview, technology stack, quick start, and quality
      scores.


      2. .claude/CLAUDE.md (5.1KB): Project-specific quick reference with development
      workflow, pattern summaries, anti-patterns, and stack-specific guidance.


      3. README.md (9.2KB): User-facing documentation with installation instructions,
      examples, directory st'
    player_success: true
    coach_success: true
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
