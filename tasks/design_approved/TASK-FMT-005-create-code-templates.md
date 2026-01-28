---
complexity: 6
conductor_workspace: fastmcp-wave2-3
created: 2026-01-24 14:30:00+00:00
dependencies:
- TASK-FMT-002
feature_id: FEAT-FMT
id: TASK-FMT-005
implementation_mode: task-work
parallel_group: wave2
parent_review: TASK-REV-A7F3
priority: high
status: design_approved
tags:
- template
- mcp
- fastmcp
- scaffolding
task_type: scaffolding
title: Create code templates for fastmcp-python
updated: 2026-01-24 14:30:00+00:00
wave: 2
---

# Task: Create code templates for fastmcp-python

## Description

Create code scaffolding templates for the `fastmcp-python` template. These templates enable developers to quickly generate MCP server boilerplate with all critical patterns embedded.

## Reference

Use `installer/core/templates/fastapi-python/templates/` as structural reference.

## Files to Create

```
installer/core/templates/fastmcp-python/templates/
├── server/
│   ├── __main__.py.template
│   └── server.py.template
├── tools/
│   └── tool.py.template
├── resources/
│   └── resource.py.template
├── config/
│   ├── pyproject.toml.template
│   └── Dockerfile.template
└── testing/
    ├── conftest.py.template
    └── test_tool.py.template
```

## Acceptance Criteria

### server/__main__.py.template (CRITICAL)

- [ ] Tool registration at module level
- [ ] Logging to stderr configuration
- [ ] FastMCP initialization
- [ ] Placeholders: {{ServerName}}, {{ServerDescription}}

```python
from mcp.server import FastMCP
import sys
import logging

# CRITICAL: Logging to stderr (stdout reserved for MCP)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(name="{{ServerName}}")

# Tools registered here - CRITICAL for Claude Code discovery
@mcp.tool()
async def example_tool(param: str) -> dict:
    """{{ToolDescription}}"""
    return {"result": param}

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### tools/tool.py.template

- [ ] Parameter type conversion pattern
- [ ] Async function structure
- [ ] Error handling
- [ ] Placeholders: {{ToolName}}, {{ToolDescription}}, {{Parameters}}

### tools/streaming_tool.py.template (Two-Layer Pattern)

- [ ] Implementation layer (AsyncGenerator)
- [ ] FastMCP wrapper layer
- [ ] CancelledError handling
- [ ] Cleanup in finally block

### config/Dockerfile.template

- [ ] Python 3.10-slim base
- [ ] Non-root user (mcp)
- [ ] PYTHONUNBUFFERED=1
- [ ] Proper CMD for stdio transport

### testing/test_tool.py.template

- [ ] pytest-asyncio markers
- [ ] String parameter conversion tests
- [ ] Basic functionality tests

## Placeholder Definitions

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{ServerName}}` | MCP server name (kebab-case) | design-patterns-server |
| `{{ServerDescription}}` | Server description | Design patterns recommendation server |
| `{{ToolName}}` | Tool function name (snake_case) | search_patterns |
| `{{ToolDescription}}` | Tool docstring | Search patterns by query |
| `{{ResourceName}}` | Resource name | patterns_list |

## Critical Patterns to Embed

1. **__main__.py**: Tool registration at module level
2. **Logging**: stderr only
3. **Parameters**: String conversion with `int()`, `float()`, `bool()`
4. **Streaming**: Two-layer architecture
5. **Docker**: Non-root, PYTHONUNBUFFERED

## Gap Analysis Additions (TASK-REV-A7F9)

The following templates were identified in gap analysis and MUST be included:

### Additional Templates to Create

#### tools/health_check_tool.py.template (GAP-2: Critical)

Production health check endpoint for load balancers and Kubernetes probes:

```python
"""Health check tool for production monitoring."""
import sys
import time
from datetime import datetime, UTC

_start_time = time.time()

@mcp.tool()
async def health_check() -> dict:
    """Health check endpoint for load balancers and monitoring.

    Returns server health status including uptime, memory usage,
    and dependency health for production observability.
    """
    import psutil

    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    uptime_seconds = time.time() - _start_time

    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": round(uptime_seconds, 2),
        "memory_mb": round(memory_mb, 2),
        "dependencies": await _check_dependencies()
    }

async def _check_dependencies() -> dict:
    """Check health of external dependencies."""
    # {{DependencyChecks}}
    return {"database": "healthy", "external_api": "healthy"}
```

- [ ] Includes uptime tracking
- [ ] Includes memory monitoring
- [ ] Includes dependency health checks
- [ ] Uses timezone-aware datetime

#### tools/paginated_tool.py.template (GAP-4: Major)

Cursor-based pagination for large result sets:

```python
"""Paginated tool template with cursor-based pagination."""
from typing import Optional

@mcp.tool()
async def {{ToolName}}(
    cursor: Optional[str] = None,
    limit: int = 20
) -> dict:
    """{{ToolDescription}}

    Args:
        cursor: Pagination cursor from previous response (optional)
        limit: Maximum items to return (default: 20, max: 100)

    Returns:
        Dict with items array and next_cursor for pagination
    """
    # Validate limit
    limit = min(max(1, int(limit)), 100)

    # Fetch items with cursor
    items, next_cursor = await _fetch_items(cursor, limit)

    return {
        "items": items,
        "next_cursor": next_cursor,  # None if no more results
        "has_more": next_cursor is not None,
        "count": len(items)
    }

async def _fetch_items(cursor: Optional[str], limit: int):
    """Fetch paginated items from data source."""
    # {{FetchImplementation}}
    return [], None
```

- [ ] Cursor-based pagination pattern
- [ ] Limit parameter with bounds (1-100)
- [ ] next_cursor in response
- [ ] has_more indicator

### Updated File Structure

```
installer/core/templates/fastmcp-python/templates/
├── server/
│   ├── __main__.py.template
│   └── server.py.template
├── tools/
│   ├── tool.py.template
│   ├── streaming_tool.py.template
│   ├── health_check_tool.py.template    # NEW (GAP-2)
│   └── paginated_tool.py.template       # NEW (GAP-4)
├── resources/
│   └── resource.py.template
├── config/
│   ├── pyproject.toml.template
│   └── Dockerfile.template
└── testing/
    ├── conftest.py.template
    └── test_tool.py.template
```

### Source

These additions address gaps identified in TASK-REV-A7F9 gap analysis:
- GAP-2: Health checks and observability (Critical)
- GAP-4: Pagination with cursors (Major)

## Test Execution Log

[Automatically populated by /task-work]
