# FastMCP Python Server - MCP Development

## Project Context

This is an **MCP (Model Context Protocol) server** built with FastMCP. MCP servers provide tools and resources to LLMs like Claude Code, enabling enhanced capabilities through protocol-compliant integrations.

For detailed patterns and architecture, see the root CLAUDE.md file.

## Core Principles

1. **Protocol Compliance**: stdout exclusively for MCP JSON-RPC messages
2. **Async-First**: All I/O operations use async/await
3. **Type Safety**: Pydantic validation for all tool parameters
4. **Error Boundaries**: Structured error responses with clear categories
5. **Testing Required**: MCP protocol compliance and tool behavior verification

## System Philosophy

- **stdio Transport**: MCP communication via stdin/stdout
- **stderr Logging**: All debug/info logs to stderr only
- **String Parameters**: All MCP tool parameters arrive as strings
- **FastMCP Framework**: Never implement custom Server classes
- **Module-Level Registration**: Tools registered at module level in __main__.py

## Quick Start

### Running the Server

```bash
# Install dependencies
pip install -e ".[dev]"

# Run MCP server (stdio mode)
python -m src

# Test with MCP client
mcp-client --server "python -m src"
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term

# Run protocol compliance tests
pytest tests/test_protocol.py -v
```

### Adding a New Tool

```python
# In src/__main__.py

@mcp.tool()
async def my_new_tool(param: str) -> dict:
    """
    Description for Claude Code tool discovery.

    Args:
        param: Description of parameter

    Returns:
        dict: Structured response
    """
    logger.info(f"Processing: {param}")

    try:
        result = await process_data(param)
        return {"result": result}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "error": {
                "category": "server_error",
                "message": str(e)
            }
        }
```

## Critical Patterns Summary

1. **Tool Registration**: Module-level in `__main__.py`
2. **Logging**: `stream=sys.stderr` ONLY
3. **Streaming**: Two-layer async generator pattern
4. **Cancellation**: Catch CancelledError, log, re-raise
5. **Parameters**: All strings, convert to types explicitly
6. **DateTime**: Use `datetime.now(timezone.utc)`, not `utcnow()`
7. **Framework**: FastMCP only, no custom Server
8. **Errors**: Structured responses with category/code/message
9. **Resources**: URI patterns (`data://{id}`)
10. **Context**: Async context managers for resources

**See**: `.claude/rules/mcp-patterns.md` for complete pattern documentation with examples.

## Stack-Specific Guidance

### FastMCP
- **Agent**: `fastmcp-specialist` (tools, resources, protocol)
- **Patterns**: `.claude/rules/mcp-patterns.md`
- **Use for**: Tool implementation, error handling, streaming

### Testing
- **Agent**: `fastmcp-testing-specialist` (protocol tests, async fixtures)
- **Patterns**: `.claude/rules/testing.md`
- **Use for**: MCP compliance tests, tool behavior tests

### Configuration
- **Patterns**: `.claude/rules/config.md`
- **Use for**: Environment variables, server settings

### Security
- **Patterns**: `.claude/rules/security.md`
- **Use for**: Input validation, resource limits

### Docker
- **Patterns**: `.claude/rules/docker.md`
- **Use for**: Container deployment, multi-stage builds

## Development Workflow

### 1. Define Tool
```python
@mcp.tool()
async def search_data(query: str, limit: str = "20") -> dict:
    """Search data with pagination."""
    pass
```

### 2. Add Pydantic Models (Optional)
```python
# src/models/tool_params.py
from pydantic import BaseModel, Field

class SearchParams(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(ge=1, le=100)
```

### 3. Write Tests
```python
# tests/test_tools.py
@pytest.mark.asyncio
async def test_search_data():
    result = await mcp_server.call_tool("search_data", query="test", limit="10")
    assert "result" in result
```

### 4. Run Quality Checks
```bash
ruff check src/ tests/
mypy src/
pytest tests/ --cov=src
```

## Common Patterns

### Idempotent Operations
```python
@mcp.tool()
async def create_resource(data: str, request_id: str = None) -> dict:
    if request_id:
        cached = await cache.get(f"request:{request_id}")
        if cached:
            return cached

    result = await create(data)

    if request_id:
        await cache.set(f"request:{request_id}", result, ttl=3600)

    return result
```

### Cursor-Based Pagination
```python
@mcp.tool()
async def list_items(cursor: str = None, limit: str = "20") -> dict:
    limit_int = min(int(limit), 100)
    items, next_cursor = await fetch_items(cursor, limit_int)

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": next_cursor is not None
    }
```

### Structured Responses
```python
@mcp.tool()
async def analyze(input: str) -> dict:
    result = await perform_analysis(input)

    return {
        "content": [
            {"type": "text", "text": f"Analysis: {result.summary}"}
        ],
        "structuredContent": {
            "schema": "analysis_result",
            "data": result.to_dict()
        }
    }
```

## Anti-Patterns to Avoid

❌ **Never print to stdout**
```python
print("Debug info")  # BREAKS MCP PROTOCOL
```

❌ **Never register tools in functions**
```python
def setup():
    @mcp.tool()  # Won't be discovered
    async def tool():
        pass
```

❌ **Never swallow CancelledError**
```python
try:
    await long_task()
except asyncio.CancelledError:
    pass  # WRONG - must re-raise
```

❌ **Never use naive datetime**
```python
timestamp = datetime.utcnow()  # Deprecated
```

❌ **Never create custom Server classes**
```python
class MyServer(Server):  # Use FastMCP instead
    pass
```

## Quality Standards

### Test Coverage
- **Minimum Line Coverage**: 80%
- **Protocol Compliance**: 100% (all tools/resources tested)
- **Test Categories**: Unit tests, protocol tests, integration tests

### Type Checking
- **Tool**: mypy
- **Mode**: Strict
- **Coverage**: 100% of tool signatures annotated

### Linting
- **Tool**: ruff
- **Rules**: Default + MCP-specific
- **Formatting**: ruff format

## Resources

- **Patterns**: See `.claude/rules/mcp-patterns.md` for all 10 critical patterns
- **Testing**: See `.claude/rules/testing.md` for MCP test strategies
- **Config**: See `.claude/rules/config.md` for environment setup
- **Security**: See `.claude/rules/security.md` for input validation
- **Docker**: See `.claude/rules/docker.md` for containerization

## Getting Help

Run `/task-create` to create implementation tasks with automatic:
- Pattern compliance checking
- MCP protocol validation
- Test coverage requirements
- Code quality gates

Use agents `fastmcp-specialist` and `fastmcp-testing-specialist` for specialized guidance.
