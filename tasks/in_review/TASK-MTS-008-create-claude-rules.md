---
complexity: 4
conductor_workspace: mcp-ts-wave3-2
created: 2026-01-24 16:45:00+00:00
dependencies:
- TASK-MTS-003
feature_id: FEAT-MTS
id: TASK-MTS-008
implementation_mode: task-work
parallel_group: wave3
parent_review: TASK-REV-4371
priority: medium
status: in_review
tags:
- template
- mcp
- typescript
- rules
task_type: documentation
title: Create .claude/rules/ files
updated: 2026-01-28T19:15:00+00:00
wave: 3
---

# Task: Create .claude/rules/ files

## Description

Create Claude Code rules files for the MCP TypeScript template. These provide path-specific guidance loaded conditionally based on file patterns.

## Reference

Use `installer/core/templates/react-typescript/.claude/rules/` as structural reference.
Use `.claude/reviews/TASK-REV-4371-review-report.md` for MCP-specific patterns.

## Deliverables

### 1. .claude/rules/mcp-patterns.md

Core MCP development patterns (loaded for all src/**/*.ts files)

```markdown
---
paths: src/**/*.ts
---

# MCP Development Patterns

## Critical Rules

### 1. Server Initialization
- Use McpServer class, not raw Server
- Register all tools/resources/prompts BEFORE connect()

### 2. Logging
- ALWAYS use console.error() for all logging
- NEVER use console.log() - corrupts MCP protocol

### 3. Tool Registration
[Pattern examples]

### 4. Response Format
[Content array examples]

### 5. Type Safety
[Zod schema examples]
```

### 2. .claude/rules/testing.md

Testing patterns (loaded for tests/**/*.ts files)

```markdown
---
paths: tests/**/*.ts, **/*.test.ts
---

# MCP Testing Patterns

## Unit Testing with Vitest

### Tool Implementation Tests
[Examples]

### Schema Validation Tests
[Examples]

## Protocol Testing

### JSON-RPC Test Script
[Examples]

### Common Test Cases
[Examples]
```

### 3. .claude/rules/transport.md

Transport selection and configuration (loaded for config and server files)

```markdown
---
paths: src/index.ts, config/**/*
---

# MCP Transport Configuration

## Transport Options

### STDIO (Default)
- Best for: Claude Desktop, local development
- Configuration pattern

### Streamable HTTP
- Best for: Production, networked servers
- Express/Hono middleware patterns

## Configuration Patterns

### Claude Desktop
- ABSOLUTE paths required
- Environment variables
```

### 4. .claude/rules/configuration.md

Configuration patterns (loaded for config files)

```markdown
---
paths: config/**/*.json, *.json, package.json, tsconfig.json
---

# MCP Configuration Patterns

## package.json
- Required scripts
- Dependencies

## tsconfig.json
- Module settings for ESM
- Path aliases

## Claude Desktop Config
- ABSOLUTE PATH requirement (critical!)
- Environment variables
```

## Acceptance Criteria

- [x] mcp-patterns.md created with path: src/**/*.ts
- [x] testing.md created with path: tests/**/*.ts, **/*.test.ts
- [x] transport.md created with path: src/index.ts, config/**/*
- [x] configuration.md created with path: config/**/*.json
- [x] All files have valid YAML frontmatter with paths
- [x] All files document critical patterns from review report
- [x] All files follow GuardKit rules structure conventions

## Test Execution Log

**Executed**: 2026-01-28T19:15:00Z
**Mode**: TDD (--mode=tdd --implement-only)
**Result**: ✅ PASS (12/12 tests)

### TDD RED Phase
```
12 tests created in tests/templates/test_mcp_typescript_rules.py
All 12 tests FAILED (expected - files don't exist yet)
```

### TDD GREEN Phase
```
Created 4 rules files:
- installer/core/templates/mcp-typescript/.claude/rules/mcp-patterns.md (229 lines)
- installer/core/templates/mcp-typescript/.claude/rules/testing.md (258 lines)
- installer/core/templates/mcp-typescript/.claude/rules/transport.md (255 lines)
- installer/core/templates/mcp-typescript/.claude/rules/configuration.md (311 lines)
```

### Test Results
```
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2
collected 12 items

tests/templates/test_mcp_typescript_rules.py::TestRulesFilesExist::test_mcp_patterns_file_exists PASSED
tests/templates/test_mcp_typescript_rules.py::TestRulesFilesExist::test_testing_file_exists PASSED
tests/templates/test_mcp_typescript_rules.py::TestRulesFilesExist::test_transport_file_exists PASSED
tests/templates/test_mcp_typescript_rules.py::TestRulesFilesExist::test_configuration_file_exists PASSED
tests/templates/test_mcp_typescript_rules.py::TestRulesFrontmatter::test_mcp_patterns_has_valid_frontmatter PASSED
tests/templates/test_mcp_typescript_rules.py::TestRulesFrontmatter::test_testing_has_valid_frontmatter PASSED
tests/templates/test_mcp_typescript_rules.py::TestRulesFrontmatter::test_transport_has_valid_frontmatter PASSED
tests/templates/test_mcp_typescript_rules.py::TestRulesFrontmatter::test_configuration_has_valid_frontmatter PASSED
tests/templates/test_mcp_typescript_rules.py::TestRulesContent::test_mcp_patterns_has_required_sections PASSED
tests/templates/test_mcp_typescript_rules.py::TestRulesContent::test_testing_has_required_sections PASSED
tests/templates/test_mcp_typescript_rules.py::TestRulesContent::test_transport_has_required_sections PASSED
tests/templates/test_mcp_typescript_rules.py::TestRulesContent::test_configuration_has_required_sections PASSED

============================== 12 passed in 1.19s ==============================
```

### Code Review
- **Reviewer**: code-reviewer agent
- **Status**: ✅ APPROVED
- **Files reviewed**: 5 files (1,310 lines)
- **Issues found**: None