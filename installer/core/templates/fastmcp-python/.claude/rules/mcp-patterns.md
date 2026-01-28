---
paths: src/**/*.py, **/__main__.py
---

# MCP Development Patterns

This document contains the 10 critical patterns for FastMCP server development. Violations of these patterns cause common MCP failures.

## Critical Pattern 1: Tool Registration in __main__.py

Tools MUST be registered at module level in `__main__.py`. This ensures MCP discovery works correctly.

```python
# src/__main__.py - CORRECT
import sys
import logging
from mcp.server.fastmcp import FastMCP

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(name="my-server", version="1.0.0")

# Tools registered at module level (CORRECT)
@mcp.tool()
async def my_tool(param: str) -> dict:
    """Tool description for LLM discovery."""
    return {"result": param}

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

```python
# WRONG - tools registered inside function won't be discovered
def setup_tools():
    @mcp.tool()  # This won't work!
    async def my_tool(param: str) -> dict:
        return {"result": param}
```

## Critical Pattern 2: Logging to stderr

stdout is reserved for MCP protocol communication. ALL logging MUST go to stderr.

```python
# CORRECT - stderr logging
import sys
import logging

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Processing request")  # Goes to stderr
```

```python
# WRONG - breaks MCP protocol completely
print("Processing request")  # stdout corrupts JSON-RPC
logging.basicConfig()  # Defaults to stdout!
```

## Critical Pattern 3: Streaming Two-Layer Architecture

For streaming tools, use a two-layer pattern: inner async generator for streaming logic, outer function to collect results.

```python
async def _stream_data_inner():
    """Inner generator - yields items progressively."""
    for item in data_source:
        yield process_item(item)
        await asyncio.sleep(0)  # Allow cancellation

@mcp.tool()
async def stream_data() -> list:
    """Outer function - collects streaming results for FastMCP."""
    results = []
    try:
        async for item in _stream_data_inner():
            results.append(item)
    except asyncio.CancelledError:
        logger.info("Stream cancelled, returning partial results")
        raise
    return results
```

## Critical Pattern 4: CancelledError Handling

Properly handle asyncio.CancelledError - catch, log, and re-raise. Never swallow cancellation.

```python
@mcp.tool()
async def long_running_tool(data: str) -> dict:
    """Tool with proper cancellation handling."""
    try:
        result = await process_data(data)
        return {"result": result}
    except asyncio.CancelledError:
        logger.info("Operation cancelled by client")
        raise  # MUST re-raise for proper cleanup
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return {"error": str(e)}
```

## Critical Pattern 5: String Parameter Conversion

All MCP parameters arrive as strings. Convert explicitly to appropriate types.

```python
@mcp.tool()
async def process_items(
    count: str,      # MCP sends "10" not 10
    price: str,      # MCP sends "99.99" not 99.99
    enabled: str     # MCP sends "true" not True
) -> dict:
    """Tool with explicit parameter conversion."""
    # Convert string parameters to typed values
    count_int = int(count)
    price_float = float(price)
    enabled_bool = enabled.lower() in ("true", "1", "yes")

    return {
        "count": count_int,
        "price": price_float,
        "enabled": enabled_bool
    }
```

## Critical Pattern 6: DateTime with UTC

Use timezone-aware datetime objects. Naive datetime is deprecated.

```python
from datetime import datetime, timezone

# CORRECT - timezone-aware
timestamp = datetime.now(timezone.utc)
```

```python
# WRONG - deprecated, causes warnings
timestamp = datetime.utcnow()  # Returns naive datetime
timestamp = datetime.now()     # Local time, ambiguous
```

## Critical Pattern 7: FastMCP Not Custom

Always use FastMCP framework. Never implement custom MCP Server classes.

```python
# CORRECT - use FastMCP
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="my-server", version="1.0.0")

@mcp.tool()
async def my_tool(param: str) -> dict:
    return {"result": param}
```

```python
# WRONG - custom Server class
from mcp.server import Server

class MyServer(Server):  # Don't do this!
    pass
```

## Critical Pattern 8: Error Propagation Boundaries

Define clear error boundaries with structured error responses.

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class ErrorCategory(Enum):
    CLIENT_ERROR = "client_error"    # 4xx - Client's fault
    SERVER_ERROR = "server_error"    # 5xx - Our fault
    EXTERNAL_ERROR = "external_error" # 502/503 - Dependency fault

@dataclass
class MCPError:
    category: ErrorCategory
    code: str
    message: str
    details: Optional[dict] = None
    retry_after: Optional[int] = None

@mcp.tool()
async def risky_operation(data: str) -> dict:
    """Tool with structured error handling."""
    try:
        result = await external_service.call(data)
        return {"result": result}
    except ValidationError as e:
        return {
            "error": MCPError(
                category=ErrorCategory.CLIENT_ERROR,
                code="INVALID_INPUT",
                message=str(e)
            ).__dict__
        }
    except ExternalServiceError as e:
        return {
            "error": MCPError(
                category=ErrorCategory.EXTERNAL_ERROR,
                code="SERVICE_UNAVAILABLE",
                message=str(e),
                retry_after=60
            ).__dict__
        }
```

## Critical Pattern 9: Resource URI Patterns

Follow MCP resource URI conventions for consistent discovery.

```python
# Resources use URI templates
@mcp.resource("data://{id}")
async def get_data(id: str) -> str:
    """Get data by ID."""
    return await fetch_data(id)

@mcp.resource("config://settings/{section}")
async def get_config(section: str) -> dict:
    """Get configuration section."""
    return config.get_section(section)

# Use meaningful URI schemes
# data:// - for data records
# config:// - for configuration
# file:// - for file system resources
# cache:// - for cached data
```

## Critical Pattern 10: Async Context Injection

Use async context managers for proper resource management.

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def get_db_connection() -> AsyncIterator[Connection]:
    """Async context manager for database connections."""
    conn = await create_connection()
    try:
        yield conn
    finally:
        await conn.close()

@mcp.tool()
async def query_database(sql: str) -> dict:
    """Tool using async context manager."""
    async with get_db_connection() as conn:
        result = await conn.execute(sql)
        return {"rows": result.fetchall()}
```

## Additional Patterns

### Idempotent Operations with Request IDs

Accept client-generated request IDs for idempotent operations.

```python
@mcp.tool()
async def create_resource(
    data: str,
    request_id: str = None  # Client-provided ID for idempotency
) -> dict:
    """Idempotent resource creation."""
    if request_id:
        # Check if request was already processed
        existing = await cache.get(f"request:{request_id}")
        if existing:
            logger.info(f"Returning cached result for request {request_id}")
            return existing

    result = await create_resource_impl(data)

    if request_id:
        await cache.set(f"request:{request_id}", result, ttl=3600)

    return result
```

### Cursor-Based Pagination

Use cursor-based pagination for list operations returning >20 items.

```python
@mcp.tool()
async def list_items(
    cursor: str = None,
    limit: str = "20"  # Remember: MCP sends strings
) -> dict:
    """Paginated list operation."""
    limit_int = min(int(limit), 100)  # Cap at 100

    items, next_cursor = await fetch_items(cursor, limit_int)

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": next_cursor is not None
    }
```

### Structured Content Responses

Return structured content with both text and JSON for dual parsing.

```python
@mcp.tool()
async def analyze_data(input: str) -> dict:
    """Tool returning structured content."""
    result = await perform_analysis(input)

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

## References

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
