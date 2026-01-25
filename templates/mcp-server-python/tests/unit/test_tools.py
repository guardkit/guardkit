"""Unit Tests for MCP Tools.

CRITICAL PATTERN #9: Unit tests passing ≠ MCP integration working
Always run protocol tests in addition to unit tests.

These tests verify tool logic in isolation.
"""

import pytest
from datetime import datetime, UTC


@pytest.mark.asyncio
async def test_example_tool_basic():
    """Test basic tool functionality."""
    from src.__main__ import example_tool

    result = await example_tool(param="test")

    assert "param" in result
    assert result["param"] == "test"
    assert "items" in result
    assert len(result["items"]) == 10  # default count


@pytest.mark.asyncio
async def test_example_tool_with_count():
    """Test tool with custom count parameter."""
    from src.__main__ import example_tool

    result = await example_tool(param="test", count=5)

    assert len(result["items"]) == 5
    assert result["count"] == 5


@pytest.mark.asyncio
async def test_example_tool_string_type_conversion():
    """Test CRITICAL PATTERN #6: MCP clients send ALL parameters as strings.

    This test verifies that the tool properly converts string parameters
    to their expected types.
    """
    from src.__main__ import example_tool

    # MCP clients send count as string
    result = await example_tool(param="test", count="5")

    assert result["count"] == 5
    assert len(result["items"]) == 5


@pytest.mark.asyncio
async def test_example_tool_boolean_string_conversion():
    """Test boolean string conversion from MCP clients."""
    from src.__main__ import example_tool

    # MCP clients send booleans as strings
    result = await example_tool(param="test", include_metadata="true")

    assert "metadata" in result
    assert "timestamp" in result["metadata"]


@pytest.mark.asyncio
async def test_example_tool_with_metadata():
    """Test tool with metadata flag."""
    from src.__main__ import example_tool

    result = await example_tool(param="test", include_metadata=True)

    assert "metadata" in result
    assert "timestamp" in result["metadata"]
    assert "version" in result["metadata"]


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint."""
    from src.__main__ import health_check

    result = await health_check()

    assert result["status"] == "healthy"
    assert "timestamp" in result
    assert "server" in result


@pytest.mark.asyncio
async def test_advanced_tool_basic():
    """Test advanced tool functionality."""
    from src.tools.example_tools import advanced_tool

    result = await advanced_tool(query="test query")

    assert result["query"] == "test query"
    assert "results" in result
    assert len(result["results"]) <= 5  # default max_results


@pytest.mark.asyncio
async def test_advanced_tool_string_conversion():
    """Test advanced tool with string parameter conversion."""
    from src.tools.example_tools import advanced_tool

    # MCP sends max_results as string
    result = await advanced_tool(query="test", max_results="3")

    assert len(result["results"]) == 3
    assert result["metadata"]["max_results"] == 3


@pytest.mark.asyncio
async def test_advanced_tool_with_filters():
    """Test advanced tool with JSON filters."""
    import json
    from src.tools.example_tools import advanced_tool

    filters = json.dumps({"category": "docs", "status": "active"})
    result = await advanced_tool(query="test", filters=filters)

    assert result["filters_applied"]["category"] == "docs"
    assert result["filters_applied"]["status"] == "active"


@pytest.mark.asyncio
async def test_streaming_wrapper_tool():
    """Test streaming tool wrapper collects all events."""
    from src.tools.example_tools import streaming_wrapper_tool

    result = await streaming_wrapper_tool(input_data='{"test": "data"}')

    assert result["status"] == "completed"
    assert "events" in result
    assert len(result["events"]) > 0

    # Check event types
    event_types = [e["event"] for e in result["events"]]
    assert "start" in event_types
    assert "complete" in event_types


@pytest.mark.asyncio
async def test_streaming_wrapper_tool_string_input():
    """Test streaming tool with plain string input."""
    from src.tools.example_tools import streaming_wrapper_tool

    result = await streaming_wrapper_tool(input_data="simple string")

    assert result["status"] == "completed"
    assert result["events"][0]["data"]["value"] == "simple string"
