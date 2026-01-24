# MCP Server Template

A production-ready Python MCP (Model Context Protocol) server template implementing all 10 critical patterns from real-world implementations.

## Features

- **FastMCP Framework**: Uses FastMCP for automatic MCP protocol handling
- **10 Critical Patterns**: All production-tested patterns implemented
- **OAuth 2.1 Support**: RFC 8707 Resource Indicators for HTTP/SSE transport
- **Streaming Tools**: Two-layer architecture for async generators
- **Docker Ready**: Production Dockerfile with security best practices
- **Comprehensive Tests**: Unit, integration, and protocol tests

## Quick Start

### 1. Clone and Setup

```bash
# Copy template to your project
cp -r templates/mcp-server-python my-mcp-server
cd my-mcp-server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"
```

### 2. Configure Claude Code

Create `.mcp.json` in your Claude Code config directory with **absolute paths**:

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "src"],
      "cwd": "/absolute/path/to/my-mcp-server",
      "env": {
        "PYTHONPATH": "/absolute/path/to/my-mcp-server",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 3. Run Tests

```bash
# Unit tests
pytest tests/unit -v

# Protocol tests (CRITICAL - unit tests passing ≠ MCP works)
chmod +x tests/protocol/test_mcp_protocol.sh
./tests/protocol/test_mcp_protocol.sh
```

## 10 Critical Production Patterns

This template implements all 10 patterns from production MCP deployments:

| # | Pattern | Location |
|---|---------|----------|
| 1 | Use FastMCP, not custom Server classes | `src/__main__.py` |
| 2 | Tool registration in `__main__.py` | `src/__main__.py` |
| 3 | Logging to stderr (stdout = MCP protocol) | `src/__main__.py` |
| 4 | Streaming tools two-layer architecture | `src/tools/example_tools.py` |
| 5 | Error handling for streaming | `src/tools/example_tools.py` |
| 6 | Parameter type conversion (strings!) | `src/__main__.py`, `src/tools/` |
| 7 | Configuration with absolute paths | `.mcp.json.template` |
| 8 | Timestamp best practices (`UTC`) | `src/__main__.py` |
| 9 | Protocol testing commands | `tests/protocol/` |
| 10 | Docker deployment patterns | `docker/` |

## OAuth 2.1 Support (HTTP/SSE Transport)

For remote MCP servers using HTTP/SSE transport, OAuth 2.1 with PKCE is required:

```bash
# Install OAuth dependencies
pip install -e ".[auth]"

# Set environment variables
export OAUTH_ISSUER="https://auth.example.com"
export OAUTH_AUDIENCE="https://mcp.example.com"
export MCP_RESOURCE_INDICATOR="https://mcp.example.com"
```

See `src/auth/` for implementation details.

> **Note**: STDIO transport (local MCP) doesn't require OAuth - it inherits host process credentials.

## Project Structure

```
mcp-server-python/
├── src/
│   ├── __init__.py
│   ├── __main__.py          # Entry point + tool registration (CRITICAL)
│   ├── tools/               # Tool implementations
│   │   ├── __init__.py
│   │   └── example_tools.py
│   ├── resources/           # Resource definitions (optional)
│   └── auth/                # OAuth 2.1 middleware (HTTP transport)
│       ├── __init__.py
│       ├── oauth.py
│       └── resource_indicators.py
├── tests/
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── protocol/           # MCP protocol tests (CRITICAL)
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/
│   └── setup.md
├── pyproject.toml
├── requirements.txt
├── .mcp.json.template      # Claude Code config template
└── README.md
```

## Adding New Tools

1. **Implement tool** in `src/tools/your_tool.py`:

```python
async def your_tool(param: str, count: int = 10) -> dict:
    # CRITICAL: Type conversion for MCP string params
    if isinstance(count, str):
        count = int(count)

    return {"result": param, "count": count}
```

2. **Register in `__main__.py`**:

```python
from src.tools.your_tool import your_tool

# Register with MCP
mcp.tool()(your_tool)
```

3. **Add tests** in `tests/unit/test_your_tool.py`

4. **Run protocol tests** to verify MCP integration

## Docker Deployment

```bash
# Build image
docker build -t my-mcp-server -f docker/Dockerfile .

# Run with STDIO transport
docker run -i --rm my-mcp-server

# Or use docker-compose
docker-compose -f docker/docker-compose.yml up -d
```

Configure Claude Code for Docker:

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "my-mcp-server:latest"]
    }
  }
}
```

## Troubleshooting

### Tools not visible in Claude Code

- Ensure tools are registered in `__main__.py` (Pattern #2)
- Check that `PYTHONPATH` is set correctly
- Verify absolute paths in `.mcp.json`

### Protocol errors

- Run protocol tests: `./tests/protocol/test_mcp_protocol.sh`
- Check stderr for logging output (Pattern #3)
- Ensure no `print()` statements to stdout

### Type errors

- Remember: MCP sends ALL parameters as strings (Pattern #6)
- Add explicit type conversion in tool functions

## References

- [MCP Specification](https://modelcontextprotocol.io/docs)
- [FastMCP Documentation](https://github.com/anthropics/mcp)
- [OAuth 2.1 for MCP](https://oauth.net/2.1/)
- [RFC 8707 Resource Indicators](https://datatracker.ietf.org/doc/html/rfc8707)

## License

MIT License - See LICENSE file
