---
paths: ["src/index.ts", "config/**/*"]
---

# MCP Transport Layers

## STDIO Transport (Development & Claude Desktop)

Use `StdioServerTransport` for Claude Desktop integration and local development:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new McpServer({
  name: "my-mcp-server",
  version: "1.0.0"
});

// Register handlers...
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [...]
}));

// Connect via STDIO
const transport = new StdioServerTransport();
await server.connect(transport);

console.error("[Server] MCP server running on stdio");
```

### STDIO Characteristics

- **Communication**: stdin/stdout for JSON-RPC
- **Logging**: stderr only (console.error)
- **Use Cases**: Claude Desktop, CLI tools, local development
- **Limitations**: Single connection, no concurrent clients

## HTTP/SSE Transport (Production)

Use SSE (Server-Sent Events) transport for production deployments with HTTP:

```typescript
import express from "express";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";

const app = express();
const server = new McpServer({
  name: "my-mcp-server",
  version: "1.0.0"
});

// Register handlers...
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [...]
}));

// SSE endpoint
app.get("/sse", async (req, res) => {
  const transport = new SSEServerTransport("/message", res);
  await server.connect(transport);
});

// Message endpoint
app.post("/message", express.json(), async (req, res) => {
  // Handle incoming messages
  await server.handleMessage(req.body);
  res.sendStatus(200);
});

app.listen(3000, () => {
  console.error("[Server] HTTP server running on port 3000");
});
```

## Streamable HTTP (Alternative)

For frameworks that support streaming responses (Express, Hono, Fastify):

```typescript
import { createServer } from "http";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/http.js";

const server = new McpServer({
  name: "my-mcp-server",
  version: "1.0.0"
});

// Register handlers...

const httpServer = createServer(async (req, res) => {
  if (req.url === "/mcp" && req.method === "POST") {
    const transport = new StreamableHTTPServerTransport(req, res);
    await server.connect(transport);
  } else {
    res.writeHead(404);
    res.end("Not Found");
  }
});

httpServer.listen(3000, () => {
  console.error("[Server] Streamable HTTP server on port 3000");
});
```

## Express Middleware Pattern

Create reusable middleware:

```typescript
import express from "express";

function createMcpMiddleware(server: McpServer) {
  return async (req: express.Request, res: express.Response) => {
    const transport = new SSEServerTransport("/message", res);
    await server.connect(transport);
  };
}

const app = express();
const mcpServer = new McpServer({ name: "server", version: "1.0.0" });

app.get("/mcp", createMcpMiddleware(mcpServer));
app.listen(3000);
```

## Hono Framework Integration

For edge deployments (Cloudflare Workers, Deno Deploy):

```typescript
import { Hono } from "hono";
import { stream } from "hono/streaming";

const app = new Hono();
const server = new McpServer({
  name: "my-mcp-server",
  version: "1.0.0"
});

app.post("/mcp", async (c) => {
  return stream(c, async (stream) => {
    const transport = new StreamableHTTPServerTransport(
      c.req.raw,
      stream
    );
    await server.connect(transport);
  });
});

export default app;
```

## Transport Selection Guide

Choose transport based on deployment:

### STDIO
- **Use for**: Claude Desktop, CLI tools, local dev
- **Pros**: Simple, built-in, no network overhead
- **Cons**: Single connection, no concurrency

### SSE (Server-Sent Events)
- **Use for**: Web apps, multi-client, production
- **Pros**: Multiple clients, standard HTTP, firewall-friendly
- **Cons**: Requires HTTP server, more complex setup

### Streamable HTTP
- **Use for**: Modern frameworks (Express 5+, Hono, Fastify)
- **Pros**: Bidirectional streaming, efficient, framework-native
- **Cons**: Framework-specific, newer standard

## Transport Configuration

Configure transport via environment variables:

```typescript
const TRANSPORT = process.env.MCP_TRANSPORT || "stdio";
const PORT = parseInt(process.env.PORT || "3000");

if (TRANSPORT === "stdio") {
  const transport = new StdioServerTransport();
  await server.connect(transport);
} else if (TRANSPORT === "http") {
  const app = express();
  app.post("/mcp", async (req, res) => {
    const transport = new StreamableHTTPServerTransport(req, res);
    await server.connect(transport);
  });
  app.listen(PORT);
}
```

## Transport Error Handling

Handle transport errors gracefully:

```typescript
const transport = new StdioServerTransport();

transport.onerror = (error) => {
  console.error("[Transport] Error:", error);
  process.exit(1);
};

transport.onclose = () => {
  console.error("[Transport] Connection closed");
};

await server.connect(transport);
```

## Health Checks (HTTP Transport)

Add health check endpoint for monitoring:

```typescript
const app = express();

app.get("/health", (req, res) => {
  res.json({
    status: "healthy",
    server: server.serverInfo.name,
    version: server.serverInfo.version,
    uptime: process.uptime()
  });
});

app.post("/mcp", async (req, res) => {
  // MCP transport...
});

app.listen(3000);
```

## CORS Configuration (HTTP Transport)

Enable CORS for web clients:

```typescript
import cors from "cors";

const app = express();

app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(",") || "*",
  methods: ["GET", "POST"],
  credentials: true
}));

app.post("/mcp", async (req, res) => {
  // MCP transport...
});
```
