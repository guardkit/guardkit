# MCP Server Setup Guide

This guide walks through setting up and configuring your MCP server for use with Claude Code.

## Prerequisites

- Python 3.10 or higher
- Claude Code CLI installed
- (Optional) Docker for containerized deployment

## Installation

### Local Development

```bash
# Navigate to your MCP server directory
cd my-mcp-server

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"

# Verify installation
python -m src --help
```

### Docker Installation

```bash
# Build the Docker image
docker build -t my-mcp-server -f docker/Dockerfile .

# Verify it starts correctly
docker run --rm my-mcp-server python -c "print('OK')"
```

## Claude Code Configuration

### CRITICAL: Absolute Paths Required

Claude Code requires **absolute paths** in `.mcp.json`. Relative paths will not work.

### Option 1: Local Python

Create/edit `~/.config/claude-code/.mcp.json` (or your Claude Code config location):

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "/Users/yourname/projects/my-mcp-server/.venv/bin/python",
      "args": ["-m", "src"],
      "cwd": "/Users/yourname/projects/my-mcp-server",
      "env": {
        "PYTHONPATH": "/Users/yourname/projects/my-mcp-server",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Option 2: Docker

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "my-mcp-server:latest"],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Option 3: HTTP/SSE Transport with OAuth

For remote MCP servers:

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "url": "https://mcp.example.com",
      "auth": {
        "type": "oauth2",
        "issuer": "https://auth.example.com",
        "clientId": "your-client-id",
        "scopes": ["mcp:read", "mcp:tools"]
      }
    }
  }
}
```

## Verification

### 1. Test Tool Discovery

After configuring, Claude Code should discover your tools:

```
claude> What tools are available?
```

Expected output should include your registered tools.

### 2. Run Protocol Tests

```bash
# Make executable
chmod +x tests/protocol/test_mcp_protocol.sh

# Run tests
./tests/protocol/test_mcp_protocol.sh
```

All tests should pass:
- Initialize: ✅
- Tools List: ✅
- Tool Call: ✅
- Health Check: ✅
- Error Handling: ✅

### 3. Manual JSON-RPC Test

```bash
# Test initialization
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python -m src

# Test tool listing
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | python -m src
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `PYTHONPATH` | Yes* | - | Path to project root (*for local Python) |
| `OAUTH_ISSUER` | No** | - | OAuth issuer URL (**required for HTTP transport) |
| `OAUTH_AUDIENCE` | No** | - | OAuth audience (**required for HTTP transport) |
| `MCP_RESOURCE_INDICATOR` | No** | - | RFC 8707 resource indicator |

## Logging

All logs go to **stderr** (Pattern #3). stdout is reserved for MCP protocol.

View logs:

```bash
# Local development
python -m src 2>server.log

# Docker
docker logs -f my-mcp-server-container

# Or redirect stderr
docker run -i my-mcp-server 2>server.log
```

## OAuth 2.1 Setup (HTTP Transport Only)

If using HTTP/SSE transport (not STDIO), OAuth 2.1 with PKCE is mandatory.

### 1. Install OAuth Dependencies

```bash
pip install -e ".[auth]"
```

### 2. Configure Identity Provider

Set up your IdP (Auth0, Keycloak, Okta, etc.) with:

- Authorization Code flow with PKCE
- Resource Indicators (RFC 8707)
- Scopes: `mcp:read`, `mcp:tools` (or your custom scopes)

### 3. Set Environment Variables

```bash
export OAUTH_ISSUER="https://your-idp.example.com"
export OAUTH_AUDIENCE="https://your-mcp-server.example.com"
export MCP_RESOURCE_INDICATOR="https://your-mcp-server.example.com"
```

### 4. Token Requirements

- **Lifetime**: 15-60 minutes (recommended)
- **PKCE**: Required (code_challenge_method: S256)
- **Resource Indicator**: Must match MCP_RESOURCE_INDICATOR

## Troubleshooting

### "No tools found"

1. Check tool registration in `__main__.py`
2. Verify PYTHONPATH is set correctly
3. Ensure all imports work: `python -c "from src.__main__ import mcp; print(mcp)"`

### "Connection refused" / Server not starting

1. Check Python path is absolute
2. Verify virtual environment activation
3. Check for import errors: `python -m src`

### Logging not visible

1. Remember: logs go to stderr, not stdout
2. Redirect stderr: `python -m src 2>&1 | tee server.log`

### OAuth errors (HTTP transport)

1. Verify JWKS endpoint is accessible
2. Check token expiration
3. Ensure Resource Indicator matches audience claim

## Next Steps

1. Add your custom tools in `src/tools/`
2. Register tools in `__main__.py`
3. Add unit tests in `tests/unit/`
4. Run protocol tests to verify MCP integration
5. Deploy with Docker for production
