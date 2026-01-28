# MCP TypeScript Template

Production-ready template for building MCP servers with TypeScript.

## Features

| Component | Description |
|-----------|-------------|
| Tools | Custom tool implementations with Zod validation |
| Resources | File and data resource providers |
| Prompts | Reusable prompt templates |
| Testing | Unit tests (Vitest) + Protocol tests |
| Docker | Production-ready containerization |

## Quick Start

Initialize a new project with GuardKit:

```bash
guardkit init mcp-typescript
```

Install dependencies and start development:

```bash
npm install
npm run dev
```

## What's Included

| File/Directory | Purpose |
|----------------|---------|
| `src/index.ts` | Server entry point with McpServer setup |
| `src/tools/` | Tool implementations |
| `src/resources/` | Resource providers |
| `src/prompts/` | Prompt templates |
| `tests/unit/` | Vitest unit tests |
| `tests/protocol/` | JSON-RPC protocol tests |
| `docker/` | Dockerfile and compose configuration |

## Configuration

### Claude Desktop

Add your server to Claude Desktop's configuration file.

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "node",
      "args": ["/Users/you/projects/my-mcp-server/dist/index.js"]
    }
  }
}
```

**Important**: Use absolute paths in the configuration. Relative paths will not work.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_LOG_LEVEL` | `info` | Logging level (debug, info, warn, error) |
| `MCP_TRANSPORT` | `stdio` | Transport type (stdio, sse) |

## Development

Run in development mode with watch:
```bash
npm run dev
```

Run tests:
```bash
npm test
npm run test:protocol
```

Build and run production:
```bash
npm run build
npm start
```

## Project Structure

```
.
├── src/
│   ├── index.ts          # Server entry point
│   ├── tools/            # Tool implementations
│   ├── resources/        # Resource providers
│   └── prompts/          # Prompt templates
├── tests/
│   ├── unit/             # Vitest unit tests
│   └── protocol/         # Protocol tests
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── package.json
├── tsconfig.json
└── vitest.config.ts
```

## References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [GuardKit Documentation](https://github.com/appmilla/guardkit)
