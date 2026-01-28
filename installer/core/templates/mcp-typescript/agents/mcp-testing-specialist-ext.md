# mcp-testing-specialist - Extended Reference

This file contains detailed documentation for the `mcp-testing-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/mcp-testing-specialist-ext.md
```


## Related Templates

### Primary Templates

1. **templates/testing/tool.test.ts.template**
   - Demonstrates Vitest test patterns for MCP tools
   - Shows mocking patterns for external dependencies
   - Includes parametrized tests for validation
   - Relevance: PRIMARY - Foundation for all MCP tool testing

2. **templates/testing/protocol.sh.template**
   - Manual JSON-RPC protocol testing scripts
   - Tests initialize, tools/list, tools/call sequences
   - Verifies protocol compliance
   - Relevance: PRIMARY - Protocol testing is mandatory for MCP

3. **templates/server/index.ts.template**
   - Production server code that tests should validate
   - Shows tool registration patterns
   - Demonstrates proper MCP server structure
   - Relevance: SECONDARY - Understanding server structure improves test design


## Extended Documentation

### 1. Complete Vitest Configuration

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    // Enable global test functions (describe, it, expect)
    globals: true,

    // Use Node.js environment for MCP servers
    environment: 'node',

    // Test file patterns
    include: ['tests/**/*.test.ts', 'tests/**/*.spec.ts'],
    exclude: ['tests/protocol/**', 'node_modules/**'],

    // Setup files run before each test file
    setupFiles: ['tests/setup.ts'],

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],

      // Coverage thresholds
      thresholds: {
        lines: 80,
        branches: 75,
        functions: 80,
        statements: 80
      },

      // Include/exclude patterns
      include: ['src/**/*.ts'],
      exclude: [
        'src/index.ts',       // Entry point (minimal logic)
        'src/**/*.d.ts',      // Type definitions
        'src/**/__mocks__/**' // Mock files
      ]
    },

    // Timeout for async tests
    testTimeout: 10000,

    // Run tests in parallel
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false
      }
    }
  },

  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  }
});
```

### 2. Test Setup File

```typescript
// tests/setup.ts
import { beforeAll, afterAll, vi } from 'vitest';

// Suppress console.log warnings (MCP uses stderr)
beforeAll(() => {
  vi.spyOn(console, 'log').mockImplementation(() => {
    throw new Error('console.log is forbidden in MCP tests - use console.error');
  });
});

afterAll(() => {
  vi.restoreAllMocks();
});

// Global test utilities
declare global {
  function createMockResponse<T>(data: T): { json: () => Promise<T> };
}

globalThis.createMockResponse = <T>(data: T) => ({
  json: () => Promise.resolve(data)
});
```


## Detailed Code Examples

### 1. Unit Testing Tool Implementations

**DO**: Test the implementation function separately from MCP wrapper

```typescript
// tests/unit/tools/search-patterns.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { searchPatterns, SearchPatternsArgs } from '../../../src/tools/search-patterns.js';

describe('searchPatterns', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('successful searches', () => {
    it('should return matching patterns for valid query', async () => {
      const args: SearchPatternsArgs = {
        query: 'singleton',
        maxResults: 5
      };

      const result = await searchPatterns(args);

      expect(result).toBeDefined();
      expect(result.patterns).toBeInstanceOf(Array);
      expect(result.patterns.length).toBeLessThanOrEqual(5);
      expect(result.patterns[0]).toHaveProperty('name');
      expect(result.patterns[0]).toHaveProperty('description');
    });

    it('should limit results to maxResults parameter', async () => {
      const args: SearchPatternsArgs = {
        query: 'design pattern',
        maxResults: 3
      };

      const result = await searchPatterns(args);

      expect(result.patterns.length).toBeLessThanOrEqual(3);
    });

    it('should return empty array for no matches', async () => {
      const args: SearchPatternsArgs = {
        query: 'nonexistent-pattern-xyz123',
        maxResults: 5
      };

      const result = await searchPatterns(args);

      expect(result.patterns).toEqual([]);
    });
  });

  describe('input validation', () => {
    it('should reject empty query', async () => {
      const args: SearchPatternsArgs = {
        query: '',
        maxResults: 5
      };

      await expect(searchPatterns(args))
        .rejects.toThrow('Query cannot be empty');
    });

    it('should reject negative maxResults', async () => {
      const args: SearchPatternsArgs = {
        query: 'singleton',
        maxResults: -1
      };

      await expect(searchPatterns(args))
        .rejects.toThrow('maxResults must be positive');
    });

    it('should use default maxResults when not provided', async () => {
      const args = { query: 'factory' };

      const result = await searchPatterns(args as SearchPatternsArgs);

      expect(result.patterns.length).toBeLessThanOrEqual(10); // Default
    });
  });

  describe('edge cases', () => {
    it('should handle special characters in query', async () => {
      const args: SearchPatternsArgs = {
        query: 'factory (abstract)',
        maxResults: 5
      };

      // Should not throw
      const result = await searchPatterns(args);
      expect(result).toBeDefined();
    });

    it('should handle very long queries', async () => {
      const args: SearchPatternsArgs = {
        query: 'a'.repeat(1000),
        maxResults: 5
      };

      // Should handle gracefully (either return results or throw validation error)
      await expect(searchPatterns(args)).resolves.toBeDefined();
    });
  });
});
```

**DON'T**: Test the MCP wrapper directly in unit tests

```typescript
// BAD - Testing MCP wrapper instead of implementation
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';

describe('MCP Server', () => {
  it('should handle search-patterns tool', async () => {
    const server = new McpServer({ name: 'test', version: '1.0' });
    // This tests MCP SDK, not your code!
    // Protocol testing should be separate
  });
});
```

### 2. Parametrized Tests for Validation

```typescript
// tests/unit/schemas/validation.test.ts
import { describe, it, expect } from 'vitest';
import { SearchPatternsSchema, GetPatternDetailsSchema } from '../../../src/schemas.js';

describe('SearchPatternsSchema', () => {
  const validCases = [
    { query: 'singleton', maxResults: 5 },
    { query: 'factory', maxResults: 10 },
    { query: 'a', maxResults: 1 },
    { query: 'design pattern with spaces' }
  ];

  const invalidCases = [
    { input: { query: '' }, error: 'Query cannot be empty' },
    { input: { query: 'x', maxResults: -1 }, error: 'must be positive' },
    { input: { query: 'x', maxResults: 0 }, error: 'must be positive' },
    { input: { maxResults: 5 }, error: 'Required' }
  ];

  describe.each(validCases)('valid input: %o', (input) => {
    it('should parse successfully', () => {
      expect(() => SearchPatternsSchema.parse(input)).not.toThrow();
    });
  });

  describe.each(invalidCases)('invalid input: %o', ({ input, error }) => {
    it(`should reject with error containing "${error}"`, () => {
      expect(() => SearchPatternsSchema.parse(input))
        .toThrow(expect.objectContaining({ message: expect.stringContaining(error) }));
    });
  });
});
```

### 3. Mocking External Dependencies

```typescript
// tests/unit/tools/file-reader.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as fs from 'fs/promises';
import { readConfigFile } from '../../../src/tools/file-reader.js';

// Mock the fs/promises module
vi.mock('fs/promises');

describe('readConfigFile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should read and parse JSON config file', async () => {
    const mockConfig = { database: { host: 'localhost', port: 5432 } };

    vi.mocked(fs.readFile).mockResolvedValue(JSON.stringify(mockConfig));

    const result = await readConfigFile('/path/to/config.json');

    expect(fs.readFile).toHaveBeenCalledWith('/path/to/config.json', 'utf-8');
    expect(result).toEqual(mockConfig);
  });

  it('should handle file not found error', async () => {
    const error = new Error('ENOENT: no such file or directory');
    (error as NodeJS.ErrnoException).code = 'ENOENT';

    vi.mocked(fs.readFile).mockRejectedValue(error);

    await expect(readConfigFile('/nonexistent/config.json'))
      .rejects.toThrow('Config file not found');
  });

  it('should handle invalid JSON', async () => {
    vi.mocked(fs.readFile).mockResolvedValue('{ invalid json }');

    await expect(readConfigFile('/path/to/config.json'))
      .rejects.toThrow('Invalid JSON in config file');
  });
});
```

### 4. Mocking API Calls

```typescript
// tests/unit/tools/api-client.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

import { fetchPatternData } from '../../../src/tools/api-client.js';

describe('fetchPatternData', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  it('should fetch and return pattern data', async () => {
    const mockData = {
      id: 'singleton',
      name: 'Singleton Pattern',
      description: 'Ensures a class has only one instance'
    };

    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockData)
    });

    const result = await fetchPatternData('singleton');

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/patterns/singleton'),
      expect.any(Object)
    );
    expect(result).toEqual(mockData);
  });

  it('should handle 404 errors', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found'
    });

    await expect(fetchPatternData('nonexistent'))
      .rejects.toThrow('Pattern not found');
  });

  it('should handle network errors', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));

    await expect(fetchPatternData('singleton'))
      .rejects.toThrow('Failed to fetch pattern data');
  });
});
```

### 5. Testing Error Responses

```typescript
// tests/unit/tools/error-handling.test.ts
import { describe, it, expect } from 'vitest';
import { handleToolError, McpToolError } from '../../../src/utils/error-handler.js';

describe('handleToolError', () => {
  it('should format validation errors correctly', () => {
    const error = new McpToolError('Validation failed', 'INVALID_PARAMS');

    const result = handleToolError(error);

    expect(result).toEqual({
      content: [{
        type: 'text',
        text: expect.stringContaining('Validation failed')
      }],
      isError: true
    });
  });

  it('should include error code in response', () => {
    const error = new McpToolError('Not found', 'NOT_FOUND');

    const result = handleToolError(error);

    expect(result.content[0].text).toContain('NOT_FOUND');
  });

  it('should handle unknown errors gracefully', () => {
    const error = new Error('Unexpected error');

    const result = handleToolError(error);

    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain('Internal error');
    // Should NOT expose internal details
    expect(result.content[0].text).not.toContain('Unexpected error');
  });
});
```


## Protocol Testing Scripts

### 1. Complete Protocol Test Script

```bash
#!/bin/bash
# tests/protocol/test-protocol.sh
#
# Manual JSON-RPC protocol tests for MCP server
# Usage: bash tests/protocol/test-protocol.sh

set -e

SERVER_CMD="npx tsx src/index.ts"
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_test() {
  echo -e "${YELLOW}[TEST]${NC} $1"
}

log_pass() {
  echo -e "${GREEN}[PASS]${NC} $1"
}

log_fail() {
  echo -e "${RED}[FAIL]${NC} $1"
}

# Test 1: Initialize
log_test "Initialize handshake"
INIT_RESPONSE=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0.0"}}}' | $SERVER_CMD 2>/dev/null)

if echo "$INIT_RESPONSE" | grep -q '"protocolVersion"'; then
  log_pass "Initialize returned protocol version"
else
  log_fail "Initialize failed: $INIT_RESPONSE"
  exit 1
fi

# Test 2: List Tools
log_test "List tools"
TOOLS_RESPONSE=$(echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | $SERVER_CMD 2>/dev/null)

if echo "$TOOLS_RESPONSE" | grep -q '"tools"'; then
  log_pass "Tools list returned"
  TOOL_COUNT=$(echo "$TOOLS_RESPONSE" | grep -o '"name"' | wc -l)
  echo "  Found $TOOL_COUNT tools"
else
  log_fail "Tools list failed: $TOOLS_RESPONSE"
  exit 1
fi

# Test 3: Call Tool - Success Case
log_test "Call tool (success case)"
CALL_RESPONSE=$(echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search-patterns","arguments":{"query":"singleton"}}}' | $SERVER_CMD 2>/dev/null)

if echo "$CALL_RESPONSE" | grep -q '"content"'; then
  log_pass "Tool call returned content"
else
  log_fail "Tool call failed: $CALL_RESPONSE"
  exit 1
fi

# Test 4: Call Tool - Error Case
log_test "Call tool (error case - empty query)"
ERROR_RESPONSE=$(echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search-patterns","arguments":{"query":""}}}' | $SERVER_CMD 2>/dev/null)

if echo "$ERROR_RESPONSE" | grep -q '"isError":true\|"error"'; then
  log_pass "Tool returned error for invalid input"
else
  log_fail "Tool should have returned error: $ERROR_RESPONSE"
  exit 1
fi

# Test 5: Invalid Method
log_test "Invalid method"
INVALID_RESPONSE=$(echo '{"jsonrpc":"2.0","id":5,"method":"invalid/method"}' | $SERVER_CMD 2>/dev/null)

if echo "$INVALID_RESPONSE" | grep -q '"error"'; then
  log_pass "Server returned error for invalid method"
else
  log_fail "Server should have returned error: $INVALID_RESPONSE"
  exit 1
fi

# Test 6: Verify stderr doesn't corrupt stdout
log_test "Verify stderr logging"
OUTPUT=$($SERVER_CMD <<< '{"jsonrpc":"2.0","id":6,"method":"tools/list"}' 2>$TEMP_DIR/stderr.log)

if echo "$OUTPUT" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
  log_pass "stdout is valid JSON (stderr logging works correctly)"
else
  log_fail "stdout is corrupted by logging"
  echo "stdout: $OUTPUT"
  echo "stderr: $(cat $TEMP_DIR/stderr.log)"
  exit 1
fi

echo ""
echo -e "${GREEN}All protocol tests passed!${NC}"
```

### 2. Individual Tool Protocol Test

```bash
#!/bin/bash
# tests/protocol/test-tool.sh
#
# Test a specific tool with various inputs
# Usage: bash tests/protocol/test-tool.sh <tool-name>

TOOL_NAME=${1:-"search-patterns"}
SERVER_CMD="npx tsx src/index.ts"

echo "Testing tool: $TOOL_NAME"
echo "================================"

# Test with valid input
echo -e "\n--- Valid input ---"
echo "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$TOOL_NAME\",\"arguments\":{\"query\":\"singleton\"}}}" | $SERVER_CMD 2>/dev/null | python3 -m json.tool

# Test with missing required parameter
echo -e "\n--- Missing required parameter ---"
echo "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"$TOOL_NAME\",\"arguments\":{}}}" | $SERVER_CMD 2>/dev/null | python3 -m json.tool

# Test with invalid parameter type
echo -e "\n--- Invalid parameter type ---"
echo "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"$TOOL_NAME\",\"arguments\":{\"query\":123}}}" | $SERVER_CMD 2>/dev/null | python3 -m json.tool
```


## Integration Testing Patterns

### 1. Full Server Lifecycle Test

```typescript
// tests/integration/server.test.ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { spawn, ChildProcess } from 'child_process';
import { resolve } from 'path';

describe('MCP Server Integration', () => {
  let serverProcess: ChildProcess;
  let stdout: string = '';
  let stderr: string = '';

  const sendRequest = (request: object): Promise<object> => {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Request timeout'));
      }, 5000);

      serverProcess.stdin!.write(JSON.stringify(request) + '\n');

      const handler = (data: Buffer) => {
        clearTimeout(timeout);
        try {
          const response = JSON.parse(data.toString());
          serverProcess.stdout!.off('data', handler);
          resolve(response);
        } catch (e) {
          // Partial data, wait for more
        }
      };

      serverProcess.stdout!.on('data', handler);
    });
  };

  beforeAll(async () => {
    serverProcess = spawn('npx', ['tsx', 'src/index.ts'], {
      cwd: resolve(__dirname, '../..'),
      stdio: ['pipe', 'pipe', 'pipe']
    });

    serverProcess.stderr!.on('data', (data) => {
      stderr += data.toString();
    });

    // Wait for server to start
    await new Promise(resolve => setTimeout(resolve, 1000));
  });

  afterAll(() => {
    serverProcess.kill();
  });

  it('should complete initialize handshake', async () => {
    const response = await sendRequest({
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'test', version: '1.0.0' }
      }
    });

    expect(response).toHaveProperty('result');
    expect((response as any).result.protocolVersion).toBe('2024-11-05');
  });

  it('should list available tools', async () => {
    const response = await sendRequest({
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/list'
    });

    expect(response).toHaveProperty('result');
    expect((response as any).result.tools).toBeInstanceOf(Array);
    expect((response as any).result.tools.length).toBeGreaterThan(0);
  });

  it('should execute tool successfully', async () => {
    const response = await sendRequest({
      jsonrpc: '2.0',
      id: 3,
      method: 'tools/call',
      params: {
        name: 'search-patterns',
        arguments: { query: 'singleton' }
      }
    });

    expect(response).toHaveProperty('result');
    expect((response as any).result.content).toBeInstanceOf(Array);
  });

  it('should not log to stdout', () => {
    // Verify stderr has logs, stdout is clean JSON only
    expect(stderr.length).toBeGreaterThan(0);
    // stdout should only contain valid JSON responses
    // (verified by successful parsing in sendRequest)
  });
});
```

### 2. MCP Inspector Test Guide

```typescript
// tests/integration/inspector-guide.ts
/**
 * MCP Inspector Integration Testing Guide
 *
 * MCP Inspector provides interactive testing capabilities.
 * Use it for debugging and exploratory testing.
 *
 * Installation:
 *   npm install -g @modelcontextprotocol/inspector
 *
 * Usage:
 *   npx @modelcontextprotocol/inspector npx tsx src/index.ts
 *
 * Test Checklist with Inspector:
 * 1. [ ] Server initializes successfully
 * 2. [ ] All tools are listed
 * 3. [ ] Each tool can be called with valid inputs
 * 4. [ ] Each tool returns proper error for invalid inputs
 * 5. [ ] Resources are listed (if applicable)
 * 6. [ ] Prompts are listed (if applicable)
 * 7. [ ] No stdout pollution from logging
 */

export const inspectorTestCases = [
  {
    name: 'search-patterns',
    validInputs: [
      { query: 'singleton' },
      { query: 'factory', maxResults: 3 }
    ],
    invalidInputs: [
      { query: '' },
      { maxResults: -1 }
    ]
  },
  {
    name: 'get-pattern-details',
    validInputs: [
      { patternId: 'singleton' }
    ],
    invalidInputs: [
      { patternId: '' },
      {}
    ]
  }
];
```


## Best Practices

### 1. Test File Organization

```
tests/
├── setup.ts                    # Global test setup
├── fixtures/
│   ├── server.ts               # Server fixtures
│   ├── mocks.ts                # Mock factories
│   └── test-data.ts            # Test data factories
├── unit/
│   ├── tools/
│   │   ├── search-patterns.test.ts
│   │   └── get-details.test.ts
│   ├── schemas/
│   │   └── validation.test.ts
│   └── utils/
│       └── error-handler.test.ts
├── protocol/
│   ├── test-protocol.sh        # Main protocol test
│   └── test-tool.sh            # Individual tool test
└── integration/
    └── server.test.ts          # Full server tests
```

### 2. Test Naming Conventions

```typescript
describe('componentName', () => {
  describe('methodName', () => {
    it('should [expected behavior] when [condition]', () => {
      // ...
    });

    it('should throw [error type] when [error condition]', () => {
      // ...
    });
  });
});
```

### 3. Async Test Patterns

```typescript
// Always use async/await, never callbacks
it('should handle async operation', async () => {
  const result = await asyncOperation();
  expect(result).toBeDefined();
});

// Use expect().rejects for error testing
it('should reject with error', async () => {
  await expect(asyncOperation())
    .rejects.toThrow('Expected error message');
});

// Set appropriate timeouts for slow operations
it('should complete within timeout', async () => {
  const result = await slowOperation();
  expect(result).toBeDefined();
}, 10000); // 10 second timeout
```


## Anti-Patterns to Avoid

### 1. Testing Implementation Details

```typescript
// BAD - Testing internal state
it('should set internal flag', async () => {
  const tool = new SearchPatternsTool();
  await tool.search({ query: 'test' });
  expect(tool._internalState).toBe(true); // Don't test private state!
});

// GOOD - Testing behavior
it('should return results for valid query', async () => {
  const result = await searchPatterns({ query: 'test' });
  expect(result.patterns.length).toBeGreaterThan(0);
});
```

### 2. Shared State Between Tests

```typescript
// BAD - Tests depend on each other
let sharedData: any;

it('should create data', async () => {
  sharedData = await createData();
});

it('should use created data', async () => {
  expect(sharedData).toBeDefined(); // Fails if tests run in different order!
});

// GOOD - Each test is independent
it('should create and use data', async () => {
  const data = await createData();
  const result = await useData(data);
  expect(result).toBeDefined();
});
```

### 3. Not Cleaning Up Resources

```typescript
// BAD - Resource leak
let server: McpServer;

beforeAll(() => {
  server = createServer();
});

// Missing afterAll cleanup!

// GOOD - Proper cleanup
let server: McpServer;

beforeAll(() => {
  server = createServer();
});

afterAll(async () => {
  await server.close();
});
```


## Troubleshooting

### Test Failures

**Issue**: Tests pass locally but fail in CI

**Solution**:
1. Check for timing-dependent tests (use proper async/await)
2. Verify all file paths are relative or use path.resolve()
3. Ensure environment variables are set in CI
4. Check for hardcoded ports that may conflict

**Issue**: "console.log is forbidden" error

**Solution**:
1. Replace `console.log` with `console.error` in test files
2. Remove debug logging before committing
3. Use Vitest's `vi.spyOn(console, 'error')` if you need to verify logging

**Issue**: Protocol tests fail with "invalid JSON"

**Solution**:
1. Check for console.log statements in server code
2. Verify server uses console.error exclusively
3. Run with `2>/dev/null` to verify stdout is clean JSON

### Coverage Issues

**Issue**: Coverage below threshold

**Solution**:
1. Add tests for uncovered branches (if/else, try/catch)
2. Check for dead code that can be removed
3. Add error case tests for validation logic

**Issue**: Coverage report shows wrong files

**Solution**:
1. Update `coverage.include` in vitest.config.ts
2. Ensure source maps are enabled
3. Clear coverage cache: `rm -rf coverage/`
