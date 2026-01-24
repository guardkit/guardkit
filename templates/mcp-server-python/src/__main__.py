"""MCP Server Entry Point.

CRITICAL PATTERNS IMPLEMENTED:
1. FastMCP (not custom Server classes) - FastMCP handles full MCP protocol
2. Tool registration at module level in __main__.py - Required for Claude Code discovery
3. Logging to stderr - stdout is reserved for MCP protocol
6. Parameter type conversion - MCP clients send ALL parameters as strings

Usage:
    python -m src

For Claude Code integration, configure in .mcp.json with absolute paths.
"""

from mcp.server import FastMCP
import sys
import logging
from datetime import datetime, UTC

# CRITICAL PATTERN #3: Logging to stderr (stdout reserved for MCP protocol)
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
# CRITICAL PATTERN #1: Use FastMCP, NOT custom Server classes
mcp = FastMCP(name="mcp-server-template")


@mcp.tool()
async def example_tool(
    param: str,
    count: int = 10,
    include_metadata: bool = False
) -> dict:
    """Example tool demonstrating critical MCP patterns.

    Args:
        param: The input parameter to process
        count: Number of items to return (default: 10)
        include_metadata: Whether to include metadata in response

    Returns:
        Dictionary containing the processed result
    """
    # CRITICAL PATTERN #6: Parameter type conversion
    # MCP clients send ALL parameters as strings - explicit conversion required
    if isinstance(count, str):
        count = int(count)
    if isinstance(include_metadata, str):
        include_metadata = include_metadata.lower() == "true"

    logger.info(f"Processing example_tool with param={param}, count={count}")

    result = {
        "param": param,
        "count": count,
        "items": [f"item_{i}" for i in range(count)]
    }

    if include_metadata:
        # CRITICAL PATTERN #8: Timestamp best practices
        # Use datetime.now(UTC) not deprecated utcnow()
        result["metadata"] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "1.0.0"
        }

    return result


@mcp.tool()
async def health_check() -> dict:
    """Health check endpoint for monitoring.

    Returns:
        Dictionary with server health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "server": "mcp-server-template"
    }


# CRITICAL PATTERN #2: Tools MUST be registered at module level in __main__.py
# Registration in other files makes tools invisible to Claude Code
# Import additional tools here to register them
from src.tools.example_tools import (
    advanced_tool,
    streaming_wrapper_tool
)

# Register imported tools with the MCP server
mcp.tool()(advanced_tool)
mcp.tool()(streaming_wrapper_tool)


if __name__ == "__main__":
    logger.info("Starting MCP server...")
    # Run with stdio transport (default for Claude Code)
    mcp.run(transport="stdio")
