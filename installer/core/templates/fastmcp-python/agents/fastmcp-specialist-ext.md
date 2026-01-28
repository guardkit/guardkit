# fastmcp-specialist - Extended Reference

This file contains detailed documentation for the `fastmcp-specialist` agent.
Load this file when you need comprehensive examples and guidance.

## When to Use This Agent

Use the fastmcp-specialist agent when:
- Implementing MCP tools for Claude Desktop integration
- Building streaming tools with FastMCP
- Defining resources for data exposure to Claude
- Configuring MCP server protocol communication
- Handling async operations and error recovery
- Implementing idempotent operations with request IDs
- Designing pagination for large result sets

## Code Examples

### 1. Basic Tool Registration

```python
# __main__.py - Register tools at module level
import sys
from fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
async def get_data(query: str) -> str:
    """Fetch data based on query.

    Args:
        query: Search query string

    Returns:
        JSON string with results
    """
    print(f"Processing query: {query}", file=sys.stderr)  # Log to stderr!

    # Implementation
    results = await fetch_results(query)
    return json.dumps({"data": results})

if __name__ == "__main__":
    mcp.run()
```

### 2. Streaming Two-Layer Pattern

```python
import asyncio
import sys
import json
from fastmcp import FastMCP

mcp = FastMCP("streaming-server")

async def _stream_impl(query: str):
    """Inner async generator - actual streaming logic.

    This is the worker that yields chunks progressively.
    """
    for i in range(10):
        chunk_data = {"index": i, "data": f"chunk {i}"}
        yield chunk_data
        await asyncio.sleep(0.1)  # Simulate async work

@mcp.tool()
async def stream_data(query: str) -> str:
    """Outer tool function - handles errors and collects results.

    This is what FastMCP calls. It collects results from the inner generator.

    Args:
        query: Search query

    Returns:
        JSON string with all collected results
    """
    results = []
    try:
        async for chunk in _stream_impl(query):
            print(f"Streaming chunk: {chunk}", file=sys.stderr)  # Log to stderr!
            results.append(chunk)
    except asyncio.CancelledError:
        print("Stream cancelled by client", file=sys.stderr)
        raise  # Always re-raise CancelledError
    except Exception as e:
        print(f"Stream error: {e}", file=sys.stderr)
        return json.dumps({"error": str(e)})

    return json.dumps({"results": results, "count": len(results)})
```

### 3. Parameter Type Conversion

```python
import json
from fastmcp import FastMCP

mcp = FastMCP("conversion-server")

@mcp.tool()
async def get_items(count: str, offset: str = "0", include_metadata: str = "false") -> str:
    """Get items with pagination.

    Note: MCP sends all parameters as strings. You must convert explicitly.

    Args:
        count: Number of items to fetch (as string)
        offset: Starting offset (as string, default "0")
        include_metadata: Whether to include metadata (as string, default "false")

    Returns:
        JSON string with items
    """
    # ALWAYS convert explicitly
    count_int = int(count)
    offset_int = int(offset)
    include_meta = include_metadata.lower() == "true"

    items = await fetch_items(limit=count_int, offset=offset_int)

    response = {"items": items}
    if include_meta:
        response["metadata"] = {"total": len(items), "offset": offset_int}

    return json.dumps(response)
```

### 4. Error Handling Pattern

```python
import asyncio
import json
import sys
from fastmcp import FastMCP

mcp = FastMCP("safe-server")

@mcp.tool()
async def safe_operation(data: str) -> str:
    """Operation with proper error handling.

    Demonstrates structured error responses and proper exception handling.

    Args:
        data: Input data to process

    Returns:
        JSON string with success/error status
    """
    try:
        result = await process_data(data)
        return json.dumps({
            "success": True,
            "data": result
        })
    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return json.dumps({
            "success": False,
            "error": "validation_error",
            "message": str(e)
        })
    except asyncio.CancelledError:
        print("Operation cancelled", file=sys.stderr)
        raise  # Always re-raise CancelledError
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return json.dumps({
            "success": False,
            "error": "internal_error",
            "message": "An unexpected error occurred"
        })
```

### 5. Idempotent Operation with Request ID

```python
import json
import sys
from fastmcp import FastMCP

mcp = FastMCP("idempotent-server")

@mcp.tool()
async def create_resource(
    name: str,
    description: str = "",
    request_id: str = ""
) -> str:
    """Create resource idempotently.

    Accepts client-provided request ID to ensure idempotent operations.
    If the same request_id is received, returns the existing resource.

    Args:
        name: Resource name
        description: Optional resource description
        request_id: Client-provided ID for idempotency tracking

    Returns:
        JSON string with resource details
    """
    if request_id:
        print(f"Request ID: {request_id}", file=sys.stderr)

        # Check if already processed
        existing = await get_by_request_id(request_id)
        if existing:
            print(f"Returning existing resource for request {request_id}", file=sys.stderr)
            return json.dumps({
                "success": True,
                "resource": existing,
                "created": False
            })

    # Create new resource
    resource = await create_new_resource(name, description, request_id)

    return json.dumps({
        "success": True,
        "resource": resource,
        "created": True
    })
```

### 6. Cursor-based Pagination

```python
import json
import sys
from typing import Tuple, List, Dict
from fastmcp import FastMCP

mcp = FastMCP("pagination-server")

@mcp.tool()
async def list_items(
    cursor: str = "",
    limit: str = "20"
) -> str:
    """List items with cursor-based pagination.

    Returns items and next_cursor for continuation. Use cursor-based pagination
    for any list operation that could return >20 items.

    Args:
        cursor: Continuation cursor from previous call (empty for first page)
        limit: Maximum items to return (as string, max 100)

    Returns:
        JSON string with items, next_cursor, and has_more flag
    """
    # Convert and cap limit
    limit_int = min(int(limit), 100)

    print(f"Fetching page: cursor={cursor or 'start'}, limit={limit_int}", file=sys.stderr)

    # Fetch page of items
    items, next_cursor = await fetch_page(cursor, limit_int)

    response = {
        "items": items,
        "next_cursor": next_cursor,  # Empty string if no more items
        "has_more": bool(next_cursor),
        "page_size": len(items)
    }

    return json.dumps(response)

async def fetch_page(cursor: str, limit: int) -> Tuple[List[Dict], str]:
    """Fetch a page of items.

    Returns:
        Tuple of (items, next_cursor)
    """
    # Implementation would fetch from database using cursor
    # This is a simplified example
    items = await db.fetch_items(cursor=cursor, limit=limit)

    # Generate next cursor if there are more items
    if len(items) == limit:
        # Last item's ID becomes the next cursor
        next_cursor = str(items[-1]["id"])
    else:
        next_cursor = ""  # No more items

    return items, next_cursor
```

### 7. Structured Content Response

```python
import json
from fastmcp import FastMCP

mcp = FastMCP("structured-server")

@mcp.tool()
async def get_report(query: str) -> str:
    """Get report with structured content.

    Returns both human-readable text and structured JSON for LLM parsing.

    Args:
        query: Report query

    Returns:
        JSON string with content and structuredContent fields
    """
    # Generate report data
    data = await generate_report(query)

    # Human-readable text
    content_text = f"""
Report: {data['title']}
Generated: {data['timestamp']}

Summary: {data['summary']}

Total items: {data['total']}
"""

    # Structured data for LLM
    structured = {
        "title": data['title'],
        "timestamp": data['timestamp'],
        "summary": data['summary'],
        "total": data['total'],
        "items": data['items']
    }

    return json.dumps({
        "content": content_text.strip(),
        "structuredContent": structured
    })
```

### 8. Circuit Breaker Pattern

```python
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from fastmcp import FastMCP

@dataclass
class CircuitBreaker:
    """Circuit breaker for failing external services."""
    failures: int = 0
    last_failure: datetime | None = None
    state: str = "closed"  # closed, open, half-open

    def record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failures += 1
        self.last_failure = datetime.now(UTC)
        if self.failures >= 3:
            self.state = "open"
            print(f"Circuit breaker OPEN after {self.failures} failures", file=sys.stderr)

    def record_success(self):
        """Record a success and reset the circuit."""
        self.failures = 0
        self.state = "closed"
        print("Circuit breaker CLOSED", file=sys.stderr)

    def can_attempt(self) -> bool:
        """Check if we can attempt a request."""
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if enough time has passed to try again
            if self.last_failure and datetime.now(UTC) - self.last_failure > timedelta(seconds=60):
                self.state = "half-open"
                print("Circuit breaker HALF-OPEN", file=sys.stderr)
                return True
            return False

        # half-open allows one attempt
        return True

mcp = FastMCP("resilient-server")
circuit = CircuitBreaker()

@mcp.tool()
async def call_external_service(endpoint: str, data: str) -> str:
    """Call external service with circuit breaker protection.

    Args:
        endpoint: Service endpoint
        data: Data to send

    Returns:
        JSON string with result or error
    """
    if not circuit.can_attempt():
        return json.dumps({
            "success": False,
            "error": "circuit_open",
            "message": "Service temporarily unavailable"
        })

    try:
        result = await make_external_call(endpoint, data)
        circuit.record_success()
        return json.dumps({"success": True, "result": result})
    except Exception as e:
        circuit.record_failure()
        print(f"External service error: {e}", file=sys.stderr)
        return json.dumps({
            "success": False,
            "error": "service_error",
            "message": str(e)
        })
```

### 9. Resource Definition

```python
import sys
from fastmcp import FastMCP

mcp = FastMCP("resource-server")

@mcp.resource("config://app/settings")
async def get_settings() -> str:
    """Expose application settings as an MCP resource.

    Resources are data that Claude can read but not modify.
    Use URI format: protocol://path

    Returns:
        JSON string with settings
    """
    settings = await load_settings()
    print("Settings resource accessed", file=sys.stderr)
    return json.dumps(settings)

@mcp.resource("data://users/{user_id}")
async def get_user(user_id: str) -> str:
    """Expose user data as parameterized resource.

    Args:
        user_id: User ID from URI path

    Returns:
        JSON string with user data
    """
    user = await fetch_user(user_id)
    print(f"User resource accessed: {user_id}", file=sys.stderr)
    return json.dumps(user)
```

### 10. Configuration File (.mcp.json)

```json
{
  "mcpServers": {
    "my-server": {
      "command": "/usr/bin/python3",
      "args": [
        "/absolute/path/to/my_mcp_server/__main__.py"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/my_mcp_server",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Critical**: Always use absolute paths in .mcp.json. Relative paths fail when Claude Desktop starts the server from a different working directory.

## Best Practices

1. **Module-Level Tool Registration** - Always register tools at module level in `__main__.py`, not conditionally or inside functions. This ensures tools are discovered during MCP initialization.

2. **Stderr for Logging** - Use `sys.stderr` for all logging. Stdout is reserved for MCP protocol communication. Printing to stdout breaks the protocol.

3. **Explicit Type Conversion** - MCP sends all parameters as strings. Always convert explicitly: `int(count)`, `float(value)`, `bool(flag.lower() == "true")`.

4. **Two-Layer Streaming Pattern** - For streaming tools, use an inner async generator for logic and an outer collector function that handles errors and returns final results.

5. **CancelledError Handling** - Always catch `asyncio.CancelledError` in streaming operations, log it to stderr, and re-raise. This ensures clean shutdown when clients cancel operations.

6. **Modern Datetime API** - Use `datetime.now(UTC)` instead of deprecated `utcnow()` for timezone-aware timestamps.

7. **Absolute Paths in Config** - Use absolute paths in .mcp.json configuration files. Claude Desktop may start servers from different working directories.

8. **Structured Responses** - Return both `content` (human-readable text) and `structuredContent` (JSON) fields for LLM parsing and understanding.

9. **Idempotency Support** - Accept optional `request_id` parameters for operations that should be idempotent. Check existing records before creating new ones.

10. **Pagination for Large Sets** - Use cursor-based pagination for any list operation that could return >20 items. Return `next_cursor` and `has_more` fields.

## Anti-Patterns

1. **Printing to Stdout** ❌
   ```python
   # BAD - breaks MCP protocol
   print("Processing request")

   # GOOD - logs safely
   print("Processing request", file=sys.stderr)
   ```

2. **Relative Paths in .mcp.json** ❌
   ```json
   // BAD - fails when working directory changes
   "args": ["./my_server/__main__.py"]

   // GOOD - always works
   "args": ["/home/user/projects/my_server/__main__.py"]
   ```

3. **Returning AsyncGenerator Directly** ❌
   ```python
   # BAD - FastMCP can't handle AsyncGenerator
   @mcp.tool()
   async def stream_data(query: str):
       async for item in fetch_items(query):
           yield item

   # GOOD - collect results and return string
   @mcp.tool()
   async def stream_data(query: str) -> str:
       results = []
       async for item in fetch_items(query):
           results.append(item)
       return json.dumps(results)
   ```

4. **Ignoring CancelledError** ❌
   ```python
   # BAD - swallows cancellation
   try:
       async for item in stream():
           results.append(item)
   except Exception:
       return error_response()

   # GOOD - re-raises CancelledError
   try:
       async for item in stream():
           results.append(item)
   except asyncio.CancelledError:
       print("Cancelled", file=sys.stderr)
       raise
   except Exception as e:
       return error_response(e)
   ```

5. **Custom Server Classes** ❌
   ```python
   # BAD - unnecessary complexity
   class MyServer:
       def __init__(self):
           self.mcp = FastMCP("server")

       def register_tools(self):
           @self.mcp.tool()
           async def my_tool():
               pass

   # GOOD - use FastMCP directly
   mcp = FastMCP("server")

   @mcp.tool()
   async def my_tool():
       pass
   ```

## Troubleshooting

### Tool Not Found

**Symptom**: Claude Desktop reports "tool not found" or tools don't appear in the tools list.

**Solution**:
- Verify tool is registered at module level in `__main__.py`
- Check tool is registered before `mcp.run()` is called
- Ensure `@mcp.tool()` decorator is used correctly
- Restart Claude Desktop after configuration changes

### No Output from Tool

**Symptom**: Tool executes but returns no output or empty response.

**Solution**:
- Check you're not printing to stdout (use `sys.stderr`)
- Verify tool returns a string, not None
- Check for exceptions being silently caught
- Add stderr logging to trace execution

### Parameters Are Wrong Type

**Symptom**: Tool receives unexpected values or type errors occur.

**Solution**:
- Remember MCP sends all parameters as strings
- Add explicit type conversions: `int(param)`, `float(param)`
- Validate parameters before conversion
- Provide default values for optional parameters

### Streaming Tool Hangs

**Symptom**: Streaming tool never returns or appears stuck.

**Solution**:
- Verify two-layer pattern (inner generator + outer collector)
- Check `asyncio.CancelledError` is being caught and re-raised
- Ensure outer function returns a string, not AsyncGenerator
- Add stderr logging to track progress

### Configuration Not Loading

**Symptom**: Claude Desktop can't start the server or find the configuration.

**Solution**:
- Use absolute paths in .mcp.json for `command` and `args`
- Verify Python interpreter path is correct
- Check file permissions on server files
- Review Claude Desktop logs for startup errors

### Circuit Breaker Always Open

**Symptom**: Service reports "circuit_open" errors continuously.

**Solution**:
- Check external service is actually available
- Verify failure threshold isn't too low (increase from 3)
- Adjust timeout duration (increase from 60 seconds)
- Add manual circuit breaker reset endpoint
- Monitor stderr logs for failure patterns
