---
paths: ["src/**/*.ts"]
---

# MCP Development Patterns

## Tool Registration

Tools, resources, and prompts must be registered BEFORE calling `server.connect()`:

```typescript
// Correct - register before connect
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{ name: "echo", description: "Echo input", inputSchema: EchoArgsSchema }]
}));
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  // Tool implementation
});
await server.connect(transport);

// Wrong - registering after connect will fail
await server.connect(transport);
server.setRequestHandler(ListToolsRequestSchema, ...); // Too late!
```

## McpServer Class (Recommended)

Use the `McpServer` class from `@modelcontextprotocol/sdk/server/mcp.js` instead of the raw `Server` class:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

const server = new McpServer({
  name: "my-mcp-server",
  version: "1.0.0"
});
```

Benefits:
- Built-in error handling
- Automatic request/response validation
- Better TypeScript integration
- Simplified server lifecycle management

## Logging to stderr ONLY

MCP servers use stdout for JSON-RPC protocol communication. ALL logging must go to stderr:

```typescript
// Correct - use console.error for logging
console.error("[Server] Starting MCP server...");
console.error("[Tool] Processing request:", request);

// WRONG - console.log breaks JSON-RPC protocol
console.log("This will corrupt stdout!"); // NEVER USE THIS
```

**WARNING**: Using `console.log()` will corrupt the JSON-RPC protocol and cause connection failures.

## Streaming Two-Layer Architecture

**Pattern**: Separate implementation (async generator) from MCP wrapper (collects output). Implementation yields events, wrapper accumulates and returns as structured content.

**Error Handling**: Wrap async generators with try/catch/finally. Log errors to stderr, re-throw for proper async semantics, return `isError: true` in tool responses.

**See**: `agents/mcp-typescript-specialist-ext.md` (lines 137-221) for complete streaming implementation with event generation, MCP wrapper integration, and error handling patterns.

## Zod Schema Validation

Use Zod for all input validation:

```typescript
import { z } from "zod";

const EchoArgsSchema = z.object({
  message: z.string().min(1, "Message cannot be empty"),
  count: z.number().int().positive().optional()
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  // Validate with parse (throws on error)
  const args = EchoArgsSchema.parse(request.params.arguments);

  // Or use safeParse for custom error handling
  const result = EchoArgsSchema.safeParse(request.params.arguments);
  if (!result.success) {
    return {
      content: [{
        type: "text",
        text: `Validation error: ${result.error.message}`
      }],
      isError: true
    };
  }
});
```

## Response Format (Content Array)

All tool responses must use the content array format:

```typescript
// Correct - content array with type
return {
  content: [{
    type: "text",
    text: "Response message"
  }]
};

// Also correct - multiple content items
return {
  content: [
    { type: "text", text: "Part 1" },
    { type: "text", text: "Part 2" }
  ]
};

// Wrong - raw string
return "Response message"; // Invalid!

// Wrong - missing type
return {
  content: [{ text: "Message" }] // Missing type field!
};
```

## Type Safety Patterns

Leverage TypeScript for type safety:

```typescript
import { Tool } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

// Define schema
const ArgsSchema = z.object({
  input: z.string()
});

// Infer TypeScript type from Zod schema
type Args = z.infer<typeof ArgsSchema>;

// Type-safe tool definition
const tool: Tool = {
  name: "my-tool",
  description: "My tool description",
  inputSchema: {
    type: "object",
    properties: {
      input: { type: "string" }
    },
    required: ["input"]
  }
};

// Type-safe handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const args: Args = ArgsSchema.parse(request.params.arguments);
  // args.input is type-safe (string)
});
```
