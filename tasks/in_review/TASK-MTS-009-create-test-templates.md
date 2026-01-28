---
complexity: 3
conductor_workspace: mcp-ts-wave3-3
created: 2026-01-24 16:45:00+00:00
dependencies:
- TASK-MTS-005
feature_id: FEAT-MTS
id: TASK-MTS-009
implementation_mode: task-work
parallel_group: wave3
parent_review: TASK-REV-4371
priority: medium
status: in_review
tags:
- template
- mcp
- typescript
- testing
- vitest
task_type: testing
title: Create test templates
updated: 2026-01-24 16:45:00+00:00
wave: 3
---

# Task: Create test templates

## Description

Create test file templates for MCP TypeScript projects including Vitest unit tests, protocol test scripts, and configuration.

## Reference

Use `.claude/reviews/TASK-REV-4371-review-report.md` Section 7 for testing strategy.
Use `docs/research/mcp-server-best-practices-2025.md` for test examples.

## Deliverables

### 1. testing/tool.test.ts.template

```typescript
/**
 * Tests for {{ToolName}}
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { {{toolName}}Impl, {{toolName}}Schema } from '../src/tools/{{tool-name}}.js';

describe('{{ToolName}}', () => {
    describe('{{toolName}}Impl', () => {
        it('should process valid input', async () => {
            const result = await {{toolName}}Impl({
                {{paramName}}: 'test-value'
            });

            expect(result).toBeDefined();
            expect(result.result).toContain('test-value');
        });

        it('should handle empty input', async () => {
            const result = await {{toolName}}Impl({
                {{paramName}}: ''
            });

            expect(result).toBeDefined();
        });

        // Add more test cases for your specific tool
    });

    describe('schema validation', () => {
        it('should validate correct input', () => {
            const input = { {{paramName}}: 'valid-string' };
            const parsed = {{toolName}}Schema.{{paramName}}.parse(input.{{paramName}});
            expect(parsed).toBe('valid-string');
        });

        it('should reject invalid input', () => {
            expect(() => {
                {{toolName}}Schema.{{paramName}}.parse(123);
            }).toThrow();
        });
    });
});
```

### 2. testing/protocol.sh.template

```bash
#!/bin/bash
# Protocol tests for {{ServerName}}
# Run: ./tests/protocol/test-protocol.sh

set -e

SERVER_CMD="npx tsx src/index.ts"

echo "=== MCP Protocol Tests for {{ServerName}} ==="

# Test 1: Initialize
echo -e "\n--- Test 1: Initialize ---"
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0.0"}}}' | $SERVER_CMD

# Test 2: List Tools
echo -e "\n--- Test 2: List Tools ---"
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | $SERVER_CMD

# Test 3: Call Tool
echo -e "\n--- Test 3: Call Tool ---"
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"{{tool-name}}","arguments":{"{{paramName}}":"test-value"}}}' | $SERVER_CMD

# Test 4: List Resources (if applicable)
echo -e "\n--- Test 4: List Resources ---"
echo '{"jsonrpc":"2.0","id":4,"method":"resources/list"}' | $SERVER_CMD

# Test 5: Error handling - invalid tool
echo -e "\n--- Test 5: Invalid Tool (expect error) ---"
echo '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"nonexistent-tool","arguments":{}}}' | $SERVER_CMD || true

echo -e "\n=== Protocol Tests Complete ==="
```

### 3. testing/vitest.config.ts.template

```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
    test: {
        globals: true,
        environment: 'node',
        include: ['tests/**/*.test.ts'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            include: ['src/**/*.ts'],
            exclude: ['src/index.ts'], // Entry point has side effects
            thresholds: {
                lines: 80,
                branches: 75,
                functions: 80,
                statements: 80
            }
        },
        setupFiles: ['./tests/setup.ts']
    }
});
```

### 4. testing/setup.ts.template

```typescript
/**
 * Vitest setup file
 */

import { vi } from 'vitest';

// Mock console.log to catch accidental usage
// (console.log breaks MCP protocol!)
const originalLog = console.log;
console.log = (...args: any[]) => {
    console.error('WARNING: console.log detected! Use console.error for MCP servers.');
    originalLog(...args);
};

// Add any global test setup here
```

## Acceptance Criteria

- [x] testing/tool.test.ts.template created with impl and schema tests
- [x] testing/protocol.sh.template created with JSON-RPC test commands
- [x] testing/vitest.config.ts.template created with coverage thresholds
- [x] testing/setup.ts.template created with console.log warning
- [x] Protocol script is executable (chmod +x noted)
- [x] All templates use proper placeholders
- [x] Coverage thresholds match GuardKit standards (80%)

## Test Execution Log

### TDD Workflow Summary
- **Mode**: TDD (Red → Green → Refactor)
- **Date**: 2026-01-28

### RED Phase - Test Creation
Created `tests/templates/mcp-typescript/test_testing_templates.py` with 46 tests covering:
- TestTestingTemplatesExist (4 tests)
- TestToolTestTemplate (11 tests)
- TestProtocolTemplate (12 tests)
- TestVitestConfigTemplate (13 tests)
- TestSetupTemplate (6 tests)

### GREEN Phase - Implementation
Created 4 template files:
1. `templates/testing/tool.test.ts.template` (44 lines)
2. `templates/testing/protocol.sh.template` (32 lines)
3. `templates/testing/vitest.config.ts.template` (23 lines)
4. `templates/testing/setup.ts.template` (16 lines)

Updated `manifest.json` with testing templates section and placeholder definitions.

### Test Results
```
============================= 46 passed in 1.25s ==============================
```

### REFACTOR Phase - Code Review
- **Verdict**: APPROVED FOR MERGE
- **Quality Score**: 85/100 (Excellent)
- **Acceptance Criteria**: 7/7 (100%)
- **Test Coverage**: 46/46 tests passing (100%)
- **Security**: No vulnerabilities detected
- **Placeholder Consistency**: Verified across all templates

### Files Created
- `installer/core/templates/mcp-typescript/templates/testing/tool.test.ts.template`
- `installer/core/templates/mcp-typescript/templates/testing/protocol.sh.template`
- `installer/core/templates/mcp-typescript/templates/testing/vitest.config.ts.template`
- `installer/core/templates/mcp-typescript/templates/testing/setup.ts.template`
- `tests/templates/mcp-typescript/test_testing_templates.py`

### Files Modified
- `installer/core/templates/mcp-typescript/manifest.json` (added testing section)