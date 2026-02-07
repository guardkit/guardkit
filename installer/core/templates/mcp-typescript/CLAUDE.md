# MCP TypeScript Server

## Overview

This is a **Model Context Protocol (MCP) server** built with TypeScript and the `@modelcontextprotocol/sdk`. MCP servers extend AI assistants like Claude with custom tools, resources, and prompts.

## Critical Rules

**NEVER use console.log()** - It corrupts the MCP protocol. All server output goes through stdin/stdout for JSON-RPC communication. Use `console.error()` for debugging (goes to stderr).

Register all tools, resources, and prompts **BEFORE** calling `server.connect()` - The server must know about all capabilities before the connection is established. Registering after connect will result in tools not being discovered.

Use **ABSOLUTE PATHS** in Claude Desktop configuration - Relative paths will fail. Always specify the full path to your server's entry point.

## Commands

Development:
```bash
npm run dev          # Run with tsx watch
```

Testing:
```bash
npm test             # Run unit tests
npm run test:protocol  # Run protocol tests
```

Production:
```bash
npm run build        # Build for production
npm start            # Run production build
```

## Project Structure

```
src/
├── index.ts              # Server entry point
├── tools/                # Tool implementations
│   └── *.ts
├── resources/            # Resource providers
│   └── *.ts
└── prompts/              # Prompt templates
    └── *.ts

tests/
├── unit/                 # Unit tests (Vitest)
│   └── *.test.ts
└── protocol/             # Protocol tests (JSON-RPC)
    └── *.sh
```

## Adding a New Tool

**Tool Registration**: Register tools using `server.tool()` with Zod schema validation before calling `server.connect()`. Tools must include input schema, handler function, and return content array format.

**See**: `.claude/rules/mcp-patterns.md` for registration patterns and `agents/mcp-typescript-specialist-ext.md` for complete examples with Zod validation, resource registration, and streaming patterns.

## Quality Gates

Before completing any task, verify:

- ✅ All tests pass
- ✅ No console.log statements in source code
- ✅ Protocol tests succeed
- ✅ Coverage ≥80%

## Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["/absolute/path/to/dist/index.js"]
    }
  }
}
```

### Environment Variables

Create `.env` file for development:

```bash
MCP_LOG_LEVEL=debug  # debug | info | warn | error
```

## Debugging

View server logs (stderr only):

```bash
# Run server with visible stderr
npm run dev 2>&1 | tee server.log
```

Check Claude Desktop logs:

```bash
# macOS
tail -f ~/Library/Logs/Claude/mcp*.log

# Windows
type %APPDATA%\Claude\logs\mcp*.log
```

## Resources

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [TypeScript SDK Documentation](https://github.com/modelcontextprotocol/typescript-sdk)
- [GuardKit Documentation](https://github.com/appmilla/guardkit)
