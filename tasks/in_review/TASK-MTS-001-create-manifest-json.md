---
complexity: 3
conductor_workspace: mcp-ts-wave1-1
created: 2026-01-24 16:45:00+00:00
dependencies: []
feature_id: FEAT-MTS
id: TASK-MTS-001
implementation_mode: task-work
parallel_group: wave1
parent_review: TASK-REV-4371
priority: high
status: in_review
tags:
- template
- mcp
- typescript
- manifest
task_type: scaffolding
title: Create manifest.json for mcp-typescript template
updated: 2026-01-24 16:45:00+00:00
wave: 1
---

# Task: Create manifest.json for mcp-typescript template

## Description

Create the `manifest.json` file for the `mcp-typescript` template following GuardKit template conventions. This file defines the template's identity, frameworks, patterns, and quality scores.

## Reference

Use `installer/core/templates/react-typescript/manifest.json` as structural reference.
Use `.claude/reviews/TASK-REV-4371-review-report.md` Section 4.3 for MCP-specific content.

## Acceptance Criteria

- [x] File created at `installer/core/templates/mcp-typescript/manifest.json`
- [x] Valid JSON with schema_version "1.0.0"
- [x] All required fields populated:
  - `name`: "mcp-typescript"
  - `display_name`: "MCP TypeScript Server"
  - `description`: Full description mentioning 10 critical patterns
  - `language`: "TypeScript"
  - `language_version`: "5.0+"
- [x] Frameworks array includes:
  - @modelcontextprotocol/sdk (mcp_server purpose)
  - Zod (validation purpose)
  - Vitest (testing purpose)
  - tsx (development purpose)
  - esbuild (build purpose)
- [x] Patterns array includes all MCP patterns from review
- [x] Placeholders defined: ServerName, ToolName, ResourceName, Description
- [x] Tags include: typescript, mcp, model-context-protocol, claude-code, zod
- [x] Category: "integration"
- [x] Complexity: 5
- [x] Quality scores defined (target: SOLID 85, DRY 85, YAGNI 90)

## Template Fields

```json
{
  "schema_version": "1.0.0",
  "name": "mcp-typescript",
  "display_name": "MCP TypeScript Server",
  "description": "Production-ready MCP server template using @modelcontextprotocol/sdk with TypeScript. Implements all 10 critical production patterns including stderr logging, tool registration, streaming architecture, Zod validation, and Docker deployment.",
  "version": "1.0.0",
  "author": "GuardKit",
  "source": "https://modelcontextprotocol.io/",
  "language": "TypeScript",
  "language_version": "5.0+",
  "frameworks": [...],
  "architecture": "MCP Server Pattern",
  "patterns": [...],
  "layers": ["tools", "resources", "prompts", "server"],
  "placeholders": {...},
  "tags": [...],
  "category": "integration",
  "complexity": 5,
  "quality_scores": {...}
}
```

## Test Execution Log

**Executed**: 2026-01-28
**Mode**: TDD (test-driven development)
**Test File**: `tests/templates/test_mcp_typescript_manifest.py`

### Results
- **Total Tests**: 34
- **Passed**: 34 ✅
- **Failed**: 0
- **Duration**: 1.19 seconds

### Test Categories
| Category | Tests | Status |
|----------|-------|--------|
| File Existence | 1 | ✅ |
| Manifest Structure | 9 | ✅ |
| Frameworks | 7 | ✅ |
| Patterns | 3 | ✅ |
| Placeholders | 6 | ✅ |
| Tags | 3 | ✅ |
| Quality Scores | 5 | ✅ |

### Code Review
- **Status**: APPROVED ✅
- **Reviewer**: code-reviewer agent
- **Issues Found**: None
- **Pattern Consistency**: Excellent (matches react-typescript template structure)