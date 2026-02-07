---
paths: ["tests/**/*.ts", "**/*.test.ts"]
---

# Testing MCP Servers

## Unit Testing with Vitest

**Pattern**: Test tool implementation functions separately from MCP wrapper. Use `describe`/`it` structure with `beforeEach` setup. Test success cases, validation errors, and edge cases.

**See**: `agents/mcp-testing-specialist-ext.md` for complete Vitest configuration (lines 36-98), parametrized tests, mocking patterns, and coverage requirements.

### Test Fixtures

Create reusable test fixtures:

```typescript
// tests/fixtures/server.ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

export function createTestServer() {
  return new McpServer({
    name: "test-server",
    version: "0.0.1"
  });
}

export function createMockTransport() {
  return new StdioServerTransport();
}
```

### Mocking Patterns

Mock external dependencies:

```typescript
import { vi } from "vitest";

// Mock file system
vi.mock("fs/promises", () => ({
  readFile: vi.fn().mockResolvedValue("mock content"),
  writeFile: vi.fn().mockResolvedValue(undefined)
}));

// Mock API calls
vi.mock("node-fetch", () => ({
  default: vi.fn().mockResolvedValue({
    json: () => Promise.resolve({ data: "mock" })
  })
}));
```

## JSON-RPC Protocol Testing

Test the JSON-RPC protocol manually using a test script:

```typescript
// tests/protocol/manual-test.ts
import { spawn } from "child_process";

async function testProtocol() {
  const serverProcess = spawn("node", ["dist/index.js"], {
    stdio: ["pipe", "pipe", "inherit"]
  });

  // Send initialize request
  const initRequest = {
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "test-client", version: "1.0.0" }
    }
  };

  serverProcess.stdin.write(JSON.stringify(initRequest) + "\n");

  serverProcess.stdout.on("data", (data) => {
    const response = JSON.parse(data.toString());
    console.log("Response:", response);
  });
}

testProtocol();
```

## MCP Inspector Integration

Use the MCP Inspector for interactive testing:

```bash
# Install MCP Inspector globally
npm install -g @modelcontextprotocol/inspector

# Run inspector with your server
npx @modelcontextprotocol/inspector node dist/index.js
```

The inspector provides:
- Interactive tool testing
- Request/response inspection
- Protocol validation
- Real-time debugging

## Coverage Requirements

Maintain minimum coverage thresholds:

```json
{
  "test": {
    "coverage": {
      "provider": "v8",
      "reporter": ["text", "json", "html"],
      "lines": 80,
      "branches": 75,
      "functions": 80,
      "statements": 80
    }
  }
}
```

Run coverage:
```bash
npm test -- --coverage
```

### Coverage Targets

- **Line Coverage**: ≥80% (all executable lines)
- **Branch Coverage**: ≥75% (if/else, switch, ternary)
- **Function Coverage**: ≥80% (all functions called)
- **Statement Coverage**: ≥80% (all statements executed)

## Integration Testing

Test full server lifecycle:

```typescript
import { describe, it, expect } from "vitest";
import { spawn } from "child_process";

describe("Server Integration", () => {
  it("should start and respond to requests", async () => {
    const server = spawn("node", ["dist/index.js"], {
      stdio: ["pipe", "pipe", "inherit"]
    });

    const request = {
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "test", version: "1.0.0" }
      }
    };

    server.stdin.write(JSON.stringify(request) + "\n");

    await new Promise((resolve) => {
      server.stdout.once("data", (data) => {
        const response = JSON.parse(data.toString());
        expect(response.result).toBeDefined();
        expect(response.result.protocolVersion).toBe("2024-11-05");
        server.kill();
        resolve(undefined);
      });
    });
  });
});
```

## Error Testing

Test error handling:

```typescript
it("should handle invalid requests gracefully", async () => {
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    if (!request.params.arguments?.message) {
      return {
        content: [{
          type: "text",
          text: "Error: Missing required parameter 'message'"
        }],
        isError: true
      };
    }
  });

  const response = await server.request({
    method: "tools/call",
    params: { name: "echo", arguments: {} }
  });

  expect(response.isError).toBe(true);
  expect(response.content[0].text).toContain("Missing required parameter");
});
```

## Performance Testing

Benchmark tool execution:

```typescript
import { performance } from "perf_hooks";

it("should complete tool execution within time limit", async () => {
  const start = performance.now();

  await server.request({
    method: "tools/call",
    params: { name: "test", arguments: {} }
  });

  const duration = performance.now() - start;
  expect(duration).toBeLessThan(1000); // 1 second max
});
```
