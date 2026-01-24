"""Example Tool Implementations.

CRITICAL PATTERNS IMPLEMENTED:
4. Streaming tools two-layer architecture - FastMCP doesn't handle AsyncGenerators directly
5. Error handling for streaming - Must handle asyncio.CancelledError properly

These tools demonstrate advanced patterns for production MCP servers.
"""

import asyncio
import logging
from typing import AsyncGenerator
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


# =============================================================================
# CRITICAL PATTERN #4: Streaming Tools Two-Layer Architecture
# FastMCP doesn't handle AsyncGenerators directly - requires wrapper pattern
# =============================================================================

async def _streaming_implementation(data: dict) -> AsyncGenerator[dict, None]:
    """Layer 1: Streaming Implementation.

    This is the actual streaming logic that yields events.
    Separated from MCP wrapper to enable proper async handling.

    Args:
        data: Input data to process

    Yields:
        Event dictionaries as processing progresses
    """
    try:
        # Start event
        yield {
            "event": "start",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data
        }

        # Simulate processing with intermediate events
        for i in range(3):
            await asyncio.sleep(0.5)  # Simulate work
            yield {
                "event": "progress",
                "timestamp": datetime.now(UTC).isoformat(),
                "progress": (i + 1) / 3 * 100,
                "message": f"Processing step {i + 1}/3"
            }

        # Completion event
        yield {
            "event": "complete",
            "timestamp": datetime.now(UTC).isoformat(),
            "result": {"status": "success", "input": data}
        }

    except asyncio.CancelledError:
        # CRITICAL PATTERN #5: Error handling for streaming
        # Must yield error event, then re-raise for proper async semantics
        logger.warning("Streaming operation cancelled")
        yield {
            "event": "error",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": "Operation cancelled"
        }
        raise  # Re-raise for proper async cleanup

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield {
            "event": "error",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e)
        }

    finally:
        logger.debug("Streaming cleanup complete")


async def streaming_wrapper_tool(input_data: str) -> dict:
    """Layer 2: FastMCP Wrapper for Streaming Tool.

    FastMCP cannot return AsyncGenerators directly.
    This wrapper collects all events and returns them as a list.

    Args:
        input_data: JSON string of input data

    Returns:
        Dictionary containing all collected events and final status
    """
    import json

    # Parse input (handle string conversion from MCP)
    try:
        if isinstance(input_data, str):
            data = json.loads(input_data) if input_data.startswith("{") else {"value": input_data}
        else:
            data = input_data
    except json.JSONDecodeError:
        data = {"value": input_data}

    try:
        events = []
        async for event in _streaming_implementation(data):
            events.append(event)
            logger.debug(f"Collected event: {event['event']}")

        return {
            "events": events,
            "event_count": len(events),
            "status": "completed"
        }

    except asyncio.CancelledError:
        return {
            "events": events if 'events' in dir() else [],
            "status": "cancelled"
        }


async def advanced_tool(
    query: str,
    max_results: int = 5,
    filters: str = None
) -> dict:
    """Advanced tool with complex parameter handling.

    Demonstrates proper parameter type conversion and validation
    for production MCP tools.

    Args:
        query: Search query string
        max_results: Maximum number of results to return
        filters: Optional JSON string of filters

    Returns:
        Dictionary containing search results
    """
    import json

    # CRITICAL: Type conversion for MCP string parameters
    if isinstance(max_results, str):
        max_results = int(max_results)

    # Parse optional JSON filters
    parsed_filters = {}
    if filters:
        try:
            if isinstance(filters, str):
                parsed_filters = json.loads(filters)
            else:
                parsed_filters = filters
        except json.JSONDecodeError:
            logger.warning(f"Invalid filters JSON: {filters}")

    logger.info(f"Advanced search: query={query}, max={max_results}, filters={parsed_filters}")

    # Simulate search results
    results = [
        {
            "id": i,
            "title": f"Result {i} for '{query}'",
            "score": 1.0 - (i * 0.1),
            "timestamp": datetime.now(UTC).isoformat()
        }
        for i in range(min(max_results, 10))
    ]

    return {
        "query": query,
        "total_results": len(results),
        "results": results,
        "filters_applied": parsed_filters,
        "metadata": {
            "max_results": max_results,
            "execution_time_ms": 42
        }
    }
