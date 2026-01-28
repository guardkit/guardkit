---
paths: tests/**/*.py, **/conftest.py
---

# MCP Testing Patterns

Testing patterns for FastMCP server implementations, including protocol testing, async patterns, and MCP client testing.

## Protocol Testing Patterns

Test that tools conform to MCP protocol requirements.

### Basic Tool Protocol Test

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_tool_returns_valid_response():
    """Verify tool returns MCP-compliant response structure."""
    from src.__main__ import my_tool

    result = await my_tool("test_input")

    # MCP requires dict response with expected keys
    assert isinstance(result, dict)
    assert "result" in result or "error" in result
```

### Testing Error Response Structure

```python
@pytest.mark.asyncio
async def test_tool_error_response_structure():
    """Verify error responses follow MCP error structure."""
    from src.__main__ import risky_tool

    result = await risky_tool("invalid_input")

    if "error" in result:
        error = result["error"]
        assert "category" in error
        assert "code" in error
        assert "message" in error
        assert error["category"] in ["client_error", "server_error", "external_error"]
```

## String Parameter Test Patterns

All MCP parameters arrive as strings. Test string-to-type conversion.

### Testing Parameter Conversion

```python
@pytest.mark.asyncio
async def test_string_parameter_conversion():
    """Verify string parameters are converted correctly."""
    from src.__main__ import process_items

    # MCP sends all parameters as strings
    result = await process_items(
        count="10",      # Not int
        price="99.99",   # Not float
        enabled="true"   # Not bool
    )

    assert result["count"] == 10
    assert result["price"] == 99.99
    assert result["enabled"] is True

@pytest.mark.asyncio
async def test_parameter_conversion_edge_cases():
    """Test edge cases in parameter conversion."""
    from src.__main__ import process_items

    # Test various boolean string formats
    for true_value in ["true", "True", "TRUE", "1", "yes", "Yes"]:
        result = await process_items(count="1", price="0", enabled=true_value)
        assert result["enabled"] is True

    for false_value in ["false", "False", "0", "no", "No"]:
        result = await process_items(count="1", price="0", enabled=false_value)
        assert result["enabled"] is False
```

### Testing Invalid Parameter Handling

```python
@pytest.mark.asyncio
async def test_invalid_parameter_handling():
    """Verify graceful handling of invalid parameter values."""
    from src.__main__ import process_items

    # Non-numeric string for count
    with pytest.raises(ValueError):
        await process_items(count="not_a_number", price="10.0", enabled="true")
```

## Async Test Patterns

Patterns for testing async MCP tools with pytest-asyncio.

### Basic Async Test Setup

```python
# conftest.py
import pytest
import asyncio

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mcp_server():
    """Fixture providing initialized MCP server."""
    from src.__main__ import mcp
    yield mcp
```

### Testing Async Context Managers

```python
@pytest.mark.asyncio
async def test_database_tool_with_context():
    """Test tool using async context manager."""
    from src.__main__ import query_database

    with patch('src.__main__.get_db_connection') as mock_conn:
        mock_conn.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_conn.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await query_database("SELECT * FROM users")

        assert "rows" in result
```

### Testing Cancellation Handling

```python
@pytest.mark.asyncio
async def test_tool_handles_cancellation():
    """Verify tool properly handles asyncio.CancelledError."""
    from src.__main__ import long_running_tool

    async def cancel_after_delay():
        await asyncio.sleep(0.1)
        raise asyncio.CancelledError()

    task = asyncio.create_task(long_running_tool("test"))

    # Cancel after short delay
    await asyncio.sleep(0.05)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
```

## MCP Client Testing Patterns

Testing tools from the perspective of an MCP client.

### Mock MCP Client Fixture

```python
# conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for integration testing."""
    client = MagicMock()
    client.call_tool = AsyncMock()
    client.read_resource = AsyncMock()
    return client
```

### Testing Tool Discovery

```python
@pytest.mark.asyncio
async def test_tools_are_discoverable(mcp_server):
    """Verify all tools are registered and discoverable."""
    # Get registered tools
    tools = mcp_server.list_tools()

    expected_tools = ["my_tool", "process_items", "query_database"]

    for tool_name in expected_tools:
        assert any(t.name == tool_name for t in tools), \
            f"Tool {tool_name} not found in registered tools"
```

### Testing Resource Discovery

```python
@pytest.mark.asyncio
async def test_resources_are_discoverable(mcp_server):
    """Verify resources are registered with correct URI templates."""
    resources = mcp_server.list_resources()

    # Check URI patterns
    uri_patterns = [r.uri_template for r in resources]

    assert "data://{id}" in uri_patterns
    assert "config://settings/{section}" in uri_patterns
```

## Fixture Examples

### Database Fixture with Cleanup

```python
@pytest.fixture
async def test_db():
    """Create test database with automatic cleanup."""
    import aiosqlite

    db = await aiosqlite.connect(":memory:")
    await db.execute("""
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value REAL
        )
    """)
    await db.commit()

    yield db

    await db.close()

@pytest.fixture
def override_db(test_db):
    """Override database dependency for tests."""
    with patch('src.__main__.get_db_connection') as mock:
        mock.return_value.__aenter__ = AsyncMock(return_value=test_db)
        mock.return_value.__aexit__ = AsyncMock(return_value=None)
        yield
```

### External Service Mock Fixture

```python
@pytest.fixture
def mock_external_service():
    """Mock external service for isolated testing."""
    with patch('src.services.external_api') as mock:
        mock.call = AsyncMock(return_value={"status": "success"})
        mock.health_check = AsyncMock(return_value=True)
        yield mock
```

### Logging Capture Fixture

```python
@pytest.fixture
def capture_logs(capfd):
    """Capture stderr logs for verification."""
    def get_logs():
        _, err = capfd.readouterr()
        return err
    return get_logs

@pytest.mark.asyncio
async def test_tool_logs_to_stderr(capture_logs):
    """Verify tool logs to stderr, not stdout."""
    from src.__main__ import my_tool

    await my_tool("test")

    logs = capture_logs()
    assert "Processing" in logs  # Log message appears in stderr
```

## Integration Testing with MCP Inspector

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_protocol_compliance():
    """Test full MCP protocol compliance using inspector patterns."""
    import subprocess
    import json

    # Start server process
    proc = subprocess.Popen(
        ["python", "-m", "src"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        # Send initialize request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }

        proc.stdin.write(json.dumps(request).encode() + b"\n")
        proc.stdin.flush()

        response = json.loads(proc.stdout.readline())

        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert "capabilities" in response["result"]

    finally:
        proc.terminate()
        proc.wait()
```

## Coverage Requirements

MCP server tests should achieve:
- **Line coverage**: >= 80%
- **Branch coverage**: >= 75%
- **Tool coverage**: 100% of registered tools tested

```bash
# Run tests with coverage
pytest tests/ -v --cov=src --cov-report=term --cov-report=html

# Run only async tests
pytest tests/ -v -m asyncio

# Run protocol compliance tests
pytest tests/ -v -m integration
```

## References

- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [MCP Testing Best Practices](https://modelcontextprotocol.io/docs/develop/testing)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
