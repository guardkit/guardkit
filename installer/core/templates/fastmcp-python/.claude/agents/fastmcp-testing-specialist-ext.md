# fastmcp-testing-specialist - Extended Reference

This file contains detailed documentation for the `fastmcp-testing-specialist` agent.
Load this file when you need comprehensive examples and guidance for MCP server testing.

```bash
cat agents/fastmcp-testing-specialist-ext.md
```


## Quick Start

### 1. Set Up Test Environment

```bash
# Create test directory structure
mkdir -p tests/unit tests/integration tests/protocol

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Create pytest configuration
cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    protocol: MCP protocol tests (via stdin/stdout)
    unit: Unit tests (isolated tool logic)
    integration: Integration tests (with dependencies)
EOF
```

### 2. Create Basic Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_tools.py        # Tool logic tests
│   └── test_resources.py    # Resource tests
├── integration/
│   └── test_server.py       # Server integration tests
└── protocol/
    ├── test_init.py         # Protocol initialization
    ├── test_tools_list.py   # Tool discovery
    └── test_tools_call.py   # Tool execution
```


## Complete Pytest Fixtures for MCP Testing

### conftest.py - Shared Test Fixtures

```python
"""
Shared pytest fixtures for FastMCP testing.
"""
import pytest
import asyncio
import subprocess
import json
from typing import AsyncGenerator, Any
from pathlib import Path


# ============================================================================
# ASYNC FIXTURES
# ============================================================================

@pytest.fixture
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# MCP SERVER FIXTURES
# ============================================================================

@pytest.fixture
def mcp_server_path():
    """Path to MCP server module."""
    return Path(__file__).parent.parent / "src"


@pytest.fixture
def send_mcp_request(mcp_server_path):
    """Factory fixture to send JSON-RPC requests to MCP server."""
    def _send(request: dict) -> dict:
        """Send JSON-RPC request and return response."""
        result = subprocess.run(
            ["python", "-m", str(mcp_server_path)],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(f"Server error: {result.stderr}")
        return json.loads(result.stdout)
    return _send


@pytest.fixture
def mcp_initialize(send_mcp_request):
    """Initialize MCP session."""
    response = send_mcp_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "1.0",
            "capabilities": {},
            "clientInfo": {"name": "pytest"}
        }
    })
    assert "result" in response
    return response["result"]


@pytest.fixture
def mcp_tools_list(send_mcp_request, mcp_initialize):
    """Get list of available tools."""
    response = send_mcp_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    })
    assert "result" in response
    return response["result"]["tools"]


# ============================================================================
# TOOL TESTING FIXTURES
# ============================================================================

@pytest.fixture
def tool_caller(send_mcp_request, mcp_initialize):
    """Factory fixture to call MCP tools."""
    def _call(tool_name: str, arguments: dict) -> Any:
        """Call a tool and return result."""
        # Convert all arguments to strings (MCP protocol requirement)
        string_args = {k: str(v) for k, v in arguments.items()}

        response = send_mcp_request({
            "jsonrpc": "2.0",
            "id": 100,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": string_args
            }
        })

        if "error" in response:
            raise RuntimeError(f"Tool error: {response['error']}")

        return response["result"]
    return _call


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_external_api(mocker):
    """Mock external API calls."""
    mock = mocker.patch("httpx.AsyncClient.get")
    mock.return_value.__aenter__.return_value.json.return_value = {
        "status": "success",
        "data": "mocked"
    }
    return mock


@pytest.fixture
def mock_database(mocker):
    """Mock database connections."""
    mock = mocker.patch("src.database.get_connection")
    mock.return_value.__aenter__.return_value = mocker.MagicMock()
    return mock


# ============================================================================
# STREAMING TEST FIXTURES
# ============================================================================

@pytest.fixture
def collect_stream():
    """Fixture to collect streaming tool output."""
    async def _collect(stream: AsyncGenerator) -> list:
        """Collect all items from async generator."""
        items = []
        try:
            async for item in stream:
                items.append(item)
        except asyncio.CancelledError:
            pass  # Expected for cancellation tests
        return items
    return _collect


@pytest.fixture
def timeout_cancel():
    """Fixture to cancel task after timeout."""
    async def _cancel(task: asyncio.Task, delay: float = 0.1):
        """Cancel task after delay."""
        await asyncio.sleep(delay)
        task.cancel()
    return _cancel
```


## Protocol Testing Script Examples

### Complete Protocol Test Script

```bash
#!/bin/bash
# test_protocol.sh - Comprehensive MCP protocol testing
#
# Usage: ./test_protocol.sh
# Exit: 0 on success, 1 on failure

set -e

SERVER_MODULE="src"
PASSED=0
FAILED=0

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

test_request() {
    local name="$1"
    local request="$2"
    local expected="$3"

    echo -n "Testing: $name... "

    response=$(echo "$request" | python -m "$SERVER_MODULE" 2>/dev/null)

    if echo "$response" | grep -q "$expected"; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        echo "  Expected: $expected"
        echo "  Got: $response"
        ((FAILED++))
    fi
}

echo "======================================"
echo "MCP Protocol Tests"
echo "======================================"

# Test 1: Initialize
test_request "initialize" \
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"1.0","capabilities":{},"clientInfo":{"name":"test"}}}' \
    '"result"'

# Test 2: Tools list
test_request "tools/list" \
    '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
    '"tools"'

# Test 3: Tool call (adjust tool name for your server)
test_request "tools/call search_patterns" \
    '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_patterns","arguments":{"query":"factory"}}}' \
    '"result"'

# Test 4: Invalid method
test_request "invalid method error" \
    '{"jsonrpc":"2.0","id":4,"method":"invalid/method"}' \
    '"error"'

# Test 5: Missing params
test_request "missing params error" \
    '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{}}' \
    '"error"'

echo "======================================"
echo "Results: $PASSED passed, $FAILED failed"
echo "======================================"

[ $FAILED -eq 0 ] && exit 0 || exit 1
```

### Python Protocol Test Module

```python
"""
Protocol-level MCP tests using subprocess.

These tests verify the MCP server works correctly when accessed
via the stdio transport (the real deployment scenario).
"""
import pytest
import subprocess
import json
from typing import Dict, Any


class TestMCPProtocol:
    """Test MCP protocol compliance via stdin/stdout."""

    @pytest.fixture
    def send_request(self):
        """Send JSON-RPC request to server."""
        def _send(request: Dict[str, Any]) -> Dict[str, Any]:
            result = subprocess.run(
                ["python", "-m", "src"],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=30
            )
            assert result.returncode == 0, f"Server failed: {result.stderr}"
            return json.loads(result.stdout)
        return _send

    @pytest.mark.protocol
    def test_initialize(self, send_request):
        """Test MCP initialization handshake."""
        response = send_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {"name": "pytest-protocol"}
            }
        })

        assert "result" in response
        assert "protocolVersion" in response["result"]
        assert "capabilities" in response["result"]
        assert "serverInfo" in response["result"]

    @pytest.mark.protocol
    def test_tools_list(self, send_request):
        """Test tools/list returns registered tools."""
        # Initialize first
        send_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {"name": "pytest-protocol"}
            }
        })

        # Then list tools
        response = send_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        })

        assert "result" in response
        assert "tools" in response["result"]
        assert isinstance(response["result"]["tools"], list)
        assert len(response["result"]["tools"]) > 0

    @pytest.mark.protocol
    def test_tools_call_with_string_params(self, send_request):
        """Test tools/call with string parameters (MCP protocol sends strings)."""
        # Initialize
        send_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {"name": "pytest-protocol"}
            }
        })

        # Call tool with STRING parameters (critical!)
        response = send_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search_patterns",  # Adjust to your tool
                "arguments": {
                    "query": "factory",
                    "max_results": "5"  # STRING, not int!
                }
            }
        })

        assert "result" in response
        # Tool should handle string-to-int conversion internally

    @pytest.mark.protocol
    def test_invalid_method_returns_error(self, send_request):
        """Test that invalid methods return proper JSON-RPC error."""
        response = send_request({
            "jsonrpc": "2.0",
            "id": 99,
            "method": "invalid/nonexistent"
        })

        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found

    @pytest.mark.protocol
    def test_missing_params_returns_error(self, send_request):
        """Test that missing required params return error."""
        response = send_request({
            "jsonrpc": "2.0",
            "id": 100,
            "method": "tools/call",
            "params": {
                "name": "search_patterns"
                # Missing "arguments"
            }
        })

        assert "error" in response
```


## Mocking Patterns for MCP Testing

### Mocking External APIs

```python
"""Examples of mocking external services in MCP tool tests."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_tool_with_mocked_api():
    """Test tool that calls external API."""
    from src.tools import fetch_data_tool

    # Mock the external API call
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "mocked"}
        mock_response.status_code = 200

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await fetch_data_tool(url="https://api.example.com/data")

        assert result["data"] == "mocked"


@pytest.mark.asyncio
async def test_tool_handles_api_failure():
    """Test tool handles external API failures gracefully."""
    from src.tools import fetch_data_tool

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        result = await fetch_data_tool(url="https://api.example.com/data")

        assert "error" in result
        assert "Connection failed" in result["error"]


class TestToolWithDatabaseMock:
    """Test tools that use database."""

    @pytest.fixture
    def mock_db(self, mocker):
        """Mock database connection."""
        mock_conn = mocker.MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            {"id": 1, "name": "test"}
        ]
        mocker.patch("src.database.get_connection", return_value=mock_conn)
        return mock_conn

    @pytest.mark.asyncio
    async def test_query_tool_with_mock_db(self, mock_db):
        """Test database query tool with mocked database."""
        from src.tools import query_tool

        result = await query_tool(table="users", limit="10")

        assert len(result["rows"]) == 1
        assert result["rows"][0]["name"] == "test"
        mock_db.execute.assert_called_once()
```

### Mocking Time for Streaming Tests

```python
"""Mocking time-based operations in streaming tool tests."""
import pytest
import asyncio
from unittest.mock import patch


@pytest.mark.asyncio
async def test_streaming_with_mocked_time():
    """Test streaming tool with mocked delays."""
    from src.tools import long_running_tool

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_sleep.return_value = None  # Skip actual delays

        results = []
        async for item in long_running_tool(iterations="5"):
            results.append(item)

        assert len(results) == 5
        # Verify sleep was called but didn't actually wait
        assert mock_sleep.call_count == 5


@pytest.mark.asyncio
async def test_streaming_cancellation():
    """Test streaming tool cancellation handling."""
    from src.tools import long_running_tool

    async def cancel_after(task, delay):
        await asyncio.sleep(delay)
        task.cancel()

    task = asyncio.create_task(
        consume_stream(long_running_tool(iterations="100"))
    )
    asyncio.create_task(cancel_after(task, 0.05))

    try:
        await task
        pytest.fail("Expected CancelledError")
    except asyncio.CancelledError:
        pass  # Expected - tool should handle gracefully


async def consume_stream(stream):
    """Helper to consume async generator."""
    async for _ in stream:
        pass
```


## CI/CD Testing Configuration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: MCP Server Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run unit tests
        run: |
          pytest tests/unit -v --cov=src --cov-report=xml

      - name: Run protocol tests
        run: |
          pytest tests/protocol -v -m protocol

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  protocol-test:
    runs-on: ubuntu-latest
    needs: test

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -e .

      - name: Run protocol verification
        run: |
          chmod +x scripts/test_protocol.sh
          ./scripts/test_protocol.sh
```

### pytest.ini Configuration

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

# Markers for test categorization
markers =
    unit: Unit tests (isolated tool logic)
    protocol: MCP protocol tests (via stdin/stdout)
    integration: Integration tests (with dependencies)
    slow: Tests that take > 5 seconds

# Coverage configuration
addopts =
    -v
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=80

# Timeout for slow tests (streaming, etc.)
timeout = 30

# Async configuration
asyncio_default_fixture_loop_scope = function
```

### pyproject.toml Test Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "unit: Unit tests",
    "protocol: Protocol tests",
    "integration: Integration tests",
    "slow: Slow tests"
]

[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "**/__main__.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
fail_under = 80
```


## Troubleshooting Common MCP Testing Issues

### Issue 1: Protocol Tests Pass But Unit Tests Fail (or Vice Versa)

**Symptom**: Unit tests pass but protocol tests fail, or protocol tests pass but unit tests fail.

**Cause**: Unit tests test isolated logic; protocol tests test MCP integration. They test different things.

**Solution**: Both test types are necessary:
- Unit tests: Fast, test logic in isolation
- Protocol tests: Slower, test real MCP server behavior

```python
# Unit test - tests logic directly
@pytest.mark.asyncio
async def test_search_logic():
    from src.tools.search import search_function
    result = await search_function(query="test", max_results=5)
    assert len(result) <= 5

# Protocol test - tests MCP integration
@pytest.mark.protocol
def test_search_via_protocol(send_request):
    response = send_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "search",
            "arguments": {"query": "test", "max_results": "5"}  # STRINGS!
        }
    })
    assert "result" in response
```

### Issue 2: Tests Fail with "Tool Not Found"

**Symptom**: `tools/call` returns error -32601 or "tool not found"

**Cause**: Tool not registered in `__main__.py` at module level

**Solution**: Ensure tools are registered at module scope:

```python
# src/__main__.py
from fastmcp import FastMCP

mcp = FastMCP("my-server")

# CORRECT: Register at module level
@mcp.tool()
async def my_tool(query: str) -> dict:
    return {"result": query}

# WRONG: Don't register inside functions or if blocks
def setup():
    @mcp.tool()  # Won't be discovered!
    async def hidden_tool():
        pass
```

### Issue 3: String Parameter Conversion Failures

**Symptom**: Tests fail with type errors when passing parameters

**Cause**: MCP protocol sends ALL parameters as strings

**Solution**: Always convert parameters explicitly in tools:

```python
# CORRECT: Convert strings explicitly
@mcp.tool()
async def process(count: str, enabled: str) -> dict:
    count_int = int(count)  # Convert from string
    enabled_bool = enabled.lower() == "true"
    return {"count": count_int, "enabled": enabled_bool}

# WRONG: Don't expect typed parameters
@mcp.tool()
async def process(count: int, enabled: bool) -> dict:  # Will fail!
    return {"count": count}
```

### Issue 4: Streaming Tests Hang

**Symptom**: Streaming tool tests hang indefinitely

**Cause**: Missing cancellation handling or no timeout

**Solution**: Always handle `asyncio.CancelledError` and use timeouts:

```python
@pytest.mark.asyncio
@pytest.mark.timeout(10)  # Fail test if takes > 10s
async def test_streaming_with_timeout():
    """Test streaming with timeout to prevent hanging."""
    results = []
    try:
        async with asyncio.timeout(5):  # Cancel after 5s
            async for item in my_streaming_tool(max_items="100"):
                results.append(item)
    except asyncio.TimeoutError:
        pass  # Expected for long streams

    assert len(results) > 0
```


## Related Templates

### Primary Templates

1. **templates/testing/conftest.py.template**
   - Comprehensive pytest fixture architecture for MCP
   - Async test setup with pytest-asyncio
   - Protocol test helpers via subprocess
   - Factory fixtures for MCP requests

2. **templates/testing/test_protocol.py.template**
   - Complete protocol test suite examples
   - JSON-RPC request/response validation
   - Tool discovery verification
   - Error handling tests

### Supporting Templates

3. **templates/server/__main__.py.template**
   - Server code that tests validate
   - Tool registration patterns
   - Understanding server structure improves test design

4. **templates/tools/tool.py.template**
   - Tool implementations to test
   - Parameter handling patterns
   - Streaming tool architecture


## Extended Documentation

For the core agent guidance, see:

```bash
cat agents/fastmcp-testing-specialist.md
```

The core file includes:
- Role and responsibilities
- Boundaries (ALWAYS/NEVER/ASK)
- Capability overview
- Quick reference patterns
