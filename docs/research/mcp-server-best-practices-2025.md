# MCP Server Best Practices Research (January 2025)

**Date**: 2025-01-24
**Purpose**: Research findings on best practices, frameworks, and templates for building MCP servers
**Context**: Supporting guardkit template creation for Brandon collaboration MCPs

---

## Executive Summary

The Model Context Protocol (MCP) has matured significantly since its November 2024 announcement by Anthropic. As of January 2025, it has been adopted by major AI providers including OpenAI and Google DeepMind, and was donated to the Agentic AI Foundation (under the Linux Foundation) in December 2025. This research synthesizes current best practices from the official specification, community templates, and production implementations.

---

## Current MCP Landscape

### Official SDKs

| SDK | Package | Status | Best For |
|-----|---------|--------|----------|
| **TypeScript** | `@modelcontextprotocol/sdk` | Most mature | Node.js/React projects, Express/Hono middleware |
| **Python** | `mcp` (FastMCP) | Production-ready | Python projects, rapid prototyping |
| **Java** | Spring AI MCP | Enterprise | Spring Boot applications |
| **Kotlin** | `io.modelcontextprotocol:kotlin-sdk` | Stable | Android/JVM projects |
| **C#** | `ModelContextProtocol` | Stable | .NET applications |
| **Rust** | `rmcp` | Stable | High-performance servers |

### Key Protocol Updates (2025)

**June 2025 Specification Changes:**
- OAuth 2.1 is now **mandatory** for HTTP-based transports (March 2025 update)
- SSE transport **deprecated**, replaced by Streamable HTTP
- MCP servers officially classified as OAuth Resource Servers
- Resource Indicators (RFC 8707) required to prevent token mis-redemption
- Structured content with JSON schemas for model + content blocks for users

**Core Primitives:**
1. **Resources**: File-like data (read-only, like GET endpoints)
2. **Tools**: Functions for actions/computation (like POST/PUT endpoints)
3. **Prompts**: Reusable templates for LLM interactions

---

## Best Practices Summary

### 1. Architecture Principles

**Single Responsibility**
Each MCP server should have one clear, well-defined purpose. Avoid creating monolithic servers that handle multiple unrelated domains.

**Idempotent Operations**
Tool calls should be idempotent—returning deterministic results for the same inputs. Accept client-generated request IDs and support retry logic.

**Pagination**
Use pagination tokens and cursors for list operations to keep responses small and predictable.

```python
# Good: Paginated response
@mcp.tool()
async def list_items(cursor: str = None, limit: int = 20) -> dict:
    items, next_cursor = await fetch_items(cursor, limit)
    return {"items": items, "next_cursor": next_cursor}
```

### 2. Transport Selection

| Transport | Use Case | Client Compatibility |
|-----------|----------|---------------------|
| **STDIO** | Local development, CLI tools | Maximum compatibility |
| **Streamable HTTP** | Networked, scalable servers | Modern clients |
| **HTTP + Polling** | Legacy compatibility | Broader support |

**Recommendation**: Support STDIO for development and Streamable HTTP for production deployment. The SSE transport is deprecated.

### 3. Security First (OAuth 2.1)

**Mandatory Requirements:**
- PKCE (Proof Key for Code Exchange) for all clients
- Short-lived access tokens (15-60 minutes)
- Refresh token rotation
- Scope-based access control
- Never echo secrets in tool results or elicitation messages

**Configuration Example:**
```json
{
  "security": {
    "auth_required": true,
    "rate_limit": 1000,
    "token_ttl": 3600
  }
}
```

### 4. Logging Critical Rule

**⚠️ CRITICAL**: For STDIO-based servers, NEVER write to stdout. This corrupts JSON-RPC messages.

```python
# ❌ WRONG - breaks MCP protocol
print("Processing request")
logging.basicConfig()  # Defaults to stdout

# ✅ CORRECT - use stderr
import sys
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logging.info("Processing request")
```

```typescript
// ❌ WRONG
console.log("Server started");

// ✅ CORRECT
console.error("Server started");
```

### 5. Structured Content Pattern

Responses must be both LLM-parsable AND human-readable:

```python
@mcp.tool()
async def analyze_data(input: str) -> dict:
    result = perform_analysis(input)
    return {
        "content": [
            {"type": "text", "text": f"Analysis complete: {result.summary}"}
        ],
        "structuredContent": {
            "schema": "analysis_result",
            "data": result.to_dict()
        }
    }
```

### 6. Error Handling

Implement structured error handling with proper classification:

```python
from enum import Enum
from dataclasses import dataclass

class ErrorCategory(Enum):
    CLIENT_ERROR = "client_error"    # 4xx - Client's fault
    SERVER_ERROR = "server_error"    # 5xx - Our fault
    EXTERNAL_ERROR = "external_error" # 502/503 - Dependency fault

@dataclass
class MCPError:
    category: ErrorCategory
    code: str
    message: str
    details: dict = None
    retry_after: int = None
```

Use circuit breaker patterns for external dependencies:
- Open after 3 consecutive failures
- Reset attempt after 60 seconds

---

## Recommended Template Structure

Based on community templates and production patterns:

```
mcp-server-template/
├── src/
│   ├── __main__.py              # Entry point (Python)
│   ├── index.ts                 # Entry point (TypeScript)
│   ├── tools/                   # Tool implementations
│   │   ├── __init__.py
│   │   └── example_tool.py
│   ├── resources/               # Resource providers
│   │   └── __init__.py
│   └── prompts/                 # Reusable prompt templates
│       └── __init__.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── config/
│   └── mcp-config.json          # Claude desktop config example
├── CLAUDE.md                    # Project context for Claude
├── pyproject.toml               # or package.json
├── Dockerfile                   # Container deployment
└── README.md
```

### Python Template (FastMCP)

```python
# src/__main__.py
import sys
import logging
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr (CRITICAL!)
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(name="my-server", version="1.0.0")

@mcp.tool()
async def my_tool(param: str) -> dict:
    """Tool description for LLM discovery.
    
    Args:
        param: Description of parameter
    """
    logger.info(f"Processing: {param}")
    return {"result": param, "status": "success"}

@mcp.resource("data://{id}")
async def get_data(id: str) -> str:
    """Get data by ID."""
    return f"Data for {id}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### TypeScript Template

```typescript
// src/index.ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "my-server",
  version: "1.0.0",
});

server.registerTool(
  "my_tool",
  {
    description: "Tool description for LLM discovery",
    inputSchema: {
      param: z.string().describe("Description of parameter"),
    },
  },
  async ({ param }) => {
    console.error(`Processing: ${param}`); // stderr!
    return {
      content: [{ type: "text", text: `Result: ${param}` }],
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "my-server": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "src"],
      "cwd": "/absolute/path/to/project",
      "env": {
        "PYTHONPATH": "/absolute/path/to/project",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Critical Configuration Notes:**
- ⚠️ Use **absolute paths** for command and cwd
- ⚠️ Set PYTHONPATH environment variable
- ⚠️ Never use relative paths or just `"python"`

---

## Production Implementation Patterns

### Testing Strategy

1. **Unit Tests**: Validate individual tool behavior with Jest/pytest
2. **Integration Tests**: Use MCP Inspector for protocol compliance
3. **Behavioral Tests**: Ensure AI models can effectively use exposed tools

```python
# tests/test_tools.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_tool():
    from src.tools.example_tool import my_tool
    result = await my_tool("test_input")
    assert result["status"] == "success"
    assert "result" in result
```

### Health Checks and Observability

```python
@mcp.tool()
async def health_check() -> dict:
    """Health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "uptime": get_uptime(),
        "memory_mb": get_memory_usage(),
        "dependencies": await check_dependencies()
    }
```

### Containerization

```dockerfile
FROM python:3.11-alpine

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install .

# Copy source
COPY src/ ./src/

# Run as non-root user
RUN adduser -D mcpuser
USER mcpuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import src; print('healthy')"

CMD ["python", "-m", "src"]
```

---

## Existing Assets in ai-engineer Repository

Your ai-engineer repo already has excellent MCP foundations:

| Asset | Location | Status |
|-------|----------|--------|
| Python MCP Specialist Agent | `installer/global/agents/python-mcp-specialist.md` | ✅ Production-ready (22KB) |
| MCP Architecture Research | `docs/research/Architecting_MCP-servers_for_team_scale_agentec_development.md` | ✅ Comprehensive |
| Python Template | `installer/global/templates/python/` | ✅ Has MCP specialist |
| TypeScript Template | `installer/global/templates/typescript-api/` | ⚠️ No MCP specialist |

**Key Patterns Already Captured in python-mcp-specialist:**
- FastMCP requirement (not custom Server classes)
- Tool registration at module level (`__main__.py`)
- stderr logging requirement
- Two-layer architecture for streaming tools
- MCP parameter type conversion (strings → typed)
- Absolute paths in `.mcp.json`
- Timestamp best practices (timezone-aware)

---

## Guardkit MCP Template Recommendation

### Proposed Structure

```
installer/global/templates/mcp-server/
├── CLAUDE.md                           # MCP-specific project context
├── agents/
│   ├── python-mcp-specialist.md        # (copy from existing)
│   └── typescript-mcp-specialist.md    # NEW - mirror Python patterns
├── templates/
│   ├── python/
│   │   ├── __main__.py.template
│   │   ├── tool.py.template
│   │   ├── resource.py.template
│   │   ├── pyproject.toml.template
│   │   └── conftest.py.template
│   ├── typescript/
│   │   ├── index.ts.template
│   │   ├── tool.ts.template
│   │   ├── package.json.template
│   │   └── tsconfig.json.template
│   └── shared/
│       ├── mcp-config.json.template
│       ├── Dockerfile.template
│       └── README.md.template
└── rules/
    └── mcp-development.md              # MCP-specific development rules
```

### Guardkit Integration Points

1. **`template-create mcp-server`**: Creates base MCP server structure
2. **`feature-plan`**: Generates tool/resource specifications
3. **`feature-build`**: Scaffolds tool implementations from plans

### Key Template Features

- FastMCP (Python) / @modelcontextprotocol/sdk (TypeScript) pre-configured
- STDIO transport ready (with HTTP option)
- Zod schemas (TS) / Pydantic (Python) for input validation
- Built-in test scaffolding with MCP Inspector integration
- Claude Desktop config auto-generation
- stderr logging pre-configured
- Error handling patterns included

---

## Key Sources Referenced

1. **Official Specification**: https://modelcontextprotocol.io/specification/2025-11-25
2. **TypeScript SDK**: https://github.com/modelcontextprotocol/typescript-sdk
3. **Python SDK**: https://github.com/modelcontextprotocol/python-sdk
4. **FastMCP Standalone**: https://github.com/jlowin/fastmcp
5. **Official Servers Repository**: https://github.com/modelcontextprotocol/servers
6. **Build Server Guide**: https://modelcontextprotocol.io/docs/develop/build-server
7. **Security Best Practices**: https://modelcontextprotocol.io/specification/2025-11-25 (Security section)
8. **June 2025 Spec Updates**: https://auth0.com/blog/mcp-specs-update-all-about-auth/

---

## Next Steps

1. **Create TypeScript MCP Specialist Agent**: Mirror the Python patterns in a TypeScript-focused agent
2. **Draft MCP Template CLAUDE.md**: Include guardkit-specific workflow instructions
3. **Create Template Files**: Python and TypeScript scaffolding with all critical patterns
4. **Test with Brandon Collaboration**: Use the template to build first collaboration MCPs
5. **Document Template Usage**: Add to guardkit documentation

---

## Appendix: Critical Gotchas Summary

| Gotcha | Impact | Solution |
|--------|--------|----------|
| Logging to stdout | Breaks MCP protocol completely | Always use stderr |
| Relative paths in config | Server won't start | Use absolute paths |
| Missing PYTHONPATH | Import errors | Set in env config |
| Tool registration in wrong file | Tools not discovered | Register in `__main__.py` |
| Naive datetime objects | Deprecation warnings | Use `datetime.now(UTC)` |
| No parameter type conversion | Type errors at runtime | Explicit string→type conversion |
| Streaming without wrapper | FastMCP compatibility issues | Two-layer architecture |
| Missing cwd in config | Path resolution failures | Always set cwd |
