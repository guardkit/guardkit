---
id: TASK-MTS-002
title: Create settings.json for mcp-typescript template
status: backlog
task_type: scaffolding
created: 2026-01-24T16:45:00Z
updated: 2026-01-24T16:45:00Z
priority: high
tags: [template, mcp, typescript, settings]
complexity: 3
parent_review: TASK-REV-4371
feature_id: FEAT-MTS
wave: 1
parallel_group: wave1
implementation_mode: task-work
conductor_workspace: mcp-ts-wave1-2
dependencies: []
---

# Task: Create settings.json for mcp-typescript template

## Description

Create the `settings.json` file for the `mcp-typescript` template defining naming conventions, file organization, and code style specific to MCP server development.

## Reference

Use `installer/core/templates/react-typescript/settings.json` as structural reference.
Use `.claude/reviews/TASK-REV-4371-review-report.md` Section 4.4 for MCP-specific content.

## Acceptance Criteria

- [ ] File created at `installer/core/templates/mcp-typescript/settings.json`
- [ ] Valid JSON with schema_version "1.0.0"
- [ ] Naming conventions defined for:
  - `tool`: kebab-case (search-patterns, get-details)
  - `resource`: protocol://path format (config://app, data://{id})
  - `prompt`: kebab-case (code-review, summarize-docs)
  - `server`: kebab-case with -server suffix
  - `test_file`: *.test.ts pattern
- [ ] File organization: by_layer = true, by_feature = false
- [ ] Layer mappings for: tools, resources, prompts, server
- [ ] Code style: 2-space indent, semicolons, single quotes
- [ ] Import aliases: @/ maps to src/
- [ ] Generation options: include_tests, include_docker, include_protocol_tests

## Template Fields

```json
{
  "schema_version": "1.0.0",
  "naming_conventions": {
    "tool": {
      "pattern": "{{toolName}}",
      "case_style": "kebab-case",
      "examples": ["search-patterns", "get-details", "count-items"]
    },
    "resource": {
      "pattern": "{{protocol}}://{{path}}",
      "examples": ["config://app", "data://{id}/profile"]
    },
    "prompt": {
      "pattern": "{{promptName}}",
      "case_style": "kebab-case",
      "examples": ["code-review", "summarize-docs"]
    },
    "server": {
      "pattern": "{{name}}-server",
      "case_style": "kebab-case",
      "examples": ["design-patterns-server", "requirements-server"]
    },
    "test_file": {
      "pattern": "{{feature}}.test.ts",
      "case_style": "kebab-case",
      "examples": ["tools.test.ts", "resources.test.ts"]
    }
  },
  "file_organization": {...},
  "layer_mappings": {...},
  "code_style": {...},
  "import_aliases": {...},
  "generation_options": {...}
}
```

## Test Execution Log

[Automatically populated by /task-work]
