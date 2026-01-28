"""
Comprehensive tests for fastmcp-python templates.

These tests validate that all templates exist and contain the required patterns
for creating production-ready MCP servers with FastMCP.

Test Strategy (TDD Red-Green-Refactor):
1. RED: These tests should fail initially (templates don't exist yet)
2. GREEN: Create templates that pass all tests
3. REFACTOR: Improve template quality while keeping tests green

Location: installer/core/templates/fastmcp-python/templates/
"""

import pytest
from pathlib import Path

# Base path for all templates
TEMPLATE_BASE = Path("installer/core/templates/fastmcp-python/templates")


class TestServerMainTemplate:
    """Tests for server/__main__.py.template - Main entry point."""

    @pytest.fixture
    def template_path(self):
        """Path to the server __main__.py template."""
        return TEMPLATE_BASE / "server" / "__main__.py.template"

    @pytest.fixture
    def template_content(self, template_path):
        """Load template content."""
        assert template_path.exists(), f"Template not found: {template_path}"
        return template_path.read_text()

    def test_template_exists(self, template_path):
        """Template file should exist."""
        assert template_path.exists(), (
            f"Server __main__.py template missing: {template_path}"
        )

    def test_has_fastmcp_import(self, template_content):
        """Should import FastMCP from mcp.server."""
        assert "from mcp.server import FastMCP" in template_content, (
            "Missing required import: from mcp.server import FastMCP"
        )

    def test_has_stderr_logging(self, template_content):
        """Logging must be configured to stderr, NOT stdout."""
        assert "logging.basicConfig" in template_content, (
            "Missing logging configuration"
        )
        assert "sys.stderr" in template_content or "stderr" in template_content, (
            "Logging must be configured to stderr (NOT stdout) to avoid "
            "interfering with stdio transport"
        )

    def test_has_mcp_initialization(self, template_content):
        """Should have FastMCP initialization with ServerName placeholder."""
        assert "mcp = FastMCP(" in template_content, (
            "Missing FastMCP initialization: mcp = FastMCP(...)"
        )
        assert '{{ServerName}}' in template_content or 'name=' in template_content, (
            "Missing ServerName placeholder or name parameter in FastMCP init"
        )

    def test_has_tool_decorator(self, template_content):
        """Should have @mcp.tool() decorator pattern."""
        assert "@mcp.tool()" in template_content, (
            "Missing tool decorator pattern: @mcp.tool()"
        )

    def test_has_stdio_transport(self, template_content):
        """Should have mcp.run(transport='stdio') in __main__."""
        assert 'mcp.run(' in template_content, (
            "Missing mcp.run() call"
        )
        assert 'transport="stdio"' in template_content or "transport='stdio'" in template_content, (
            "Missing stdio transport configuration in mcp.run()"
        )
        assert 'if __name__ == "__main__"' in template_content, (
            "Missing __main__ block"
        )

    def test_has_server_description_placeholder(self, template_content):
        """Should have ServerDescription placeholder."""
        assert '{{ServerDescription}}' in template_content, (
            "Missing {{ServerDescription}} placeholder"
        )

    def test_has_tool_description_placeholder(self, template_content):
        """Should have ToolDescription placeholder."""
        assert '{{ToolDescription}}' in template_content, (
            "Missing {{ToolDescription}} placeholder"
        )


class TestServerPyTemplate:
    """Tests for server/server.py.template - Server configuration."""

    @pytest.fixture
    def template_path(self):
        """Path to the server.py template."""
        return TEMPLATE_BASE / "server" / "server.py.template"

    @pytest.fixture
    def template_content(self, template_path):
        """Load template content."""
        assert template_path.exists(), f"Template not found: {template_path}"
        return template_path.read_text()

    def test_template_exists(self, template_path):
        """Template file should exist."""
        assert template_path.exists(), (
            f"Server server.py template missing: {template_path}"
        )

    def test_has_fastmcp_import(self, template_content):
        """Should import FastMCP."""
        assert "from mcp.server import FastMCP" in template_content or "import FastMCP" in template_content, (
            "Missing FastMCP import"
        )

    def test_has_server_name_placeholder(self, template_content):
        """Should have ServerName placeholder."""
        assert '{{ServerName}}' in template_content, (
            "Missing {{ServerName}} placeholder"
        )


class TestBasicToolTemplate:
    """Tests for tools/tool.py.template - Basic tool template."""

    @pytest.fixture
    def template_path(self):
        """Path to the basic tool template."""
        return TEMPLATE_BASE / "tools" / "tool.py.template"

    @pytest.fixture
    def template_content(self, template_path):
        """Load template content."""
        assert template_path.exists(), f"Template not found: {template_path}"
        return template_path.read_text()

    def test_template_exists(self, template_path):
        """Template file should exist."""
        assert template_path.exists(), (
            f"Basic tool template missing: {template_path}"
        )

    def test_has_async_function(self, template_content):
        """Should have async def structure."""
        assert "async def" in template_content, (
            "Missing async function definition"
        )

    def test_has_error_handling(self, template_content):
        """Should have try/except error handling."""
        assert "try:" in template_content, (
            "Missing try block for error handling"
        )
        assert "except" in template_content, (
            "Missing except block for error handling"
        )

    def test_has_type_conversion_pattern(self, template_content):
        """Should demonstrate parameter type conversion."""
        # Should show at least one of these patterns
        has_int_conversion = "int(" in template_content
        has_float_conversion = "float(" in template_content
        has_bool_conversion = "bool(" in template_content
        has_str_conversion = "str(" in template_content

        assert any([has_int_conversion, has_float_conversion, has_bool_conversion, has_str_conversion]), (
            "Missing parameter type conversion pattern (int(), float(), bool(), or str())"
        )

    def test_has_docstring(self, template_content):
        """Should have docstring documentation."""
        assert '"""' in template_content or "'''" in template_content, (
            "Missing docstring documentation"
        )

    def test_has_tool_name_placeholder(self, template_content):
        """Should have ToolName placeholder."""
        assert '{{ToolName}}' in template_content, (
            "Missing {{ToolName}} placeholder"
        )


class TestStreamingToolTemplate:
    """Tests for tools/streaming_tool.py.template - Two-layer streaming pattern."""

    @pytest.fixture
    def template_path(self):
        """Path to the streaming tool template."""
        return TEMPLATE_BASE / "tools" / "streaming_tool.py.template"

    @pytest.fixture
    def template_content(self, template_path):
        """Load template content."""
        assert template_path.exists(), f"Template not found: {template_path}"
        return template_path.read_text()

    def test_template_exists(self, template_path):
        """Template file should exist."""
        assert template_path.exists(), (
            f"Streaming tool template missing: {template_path}"
        )

    def test_has_two_layer_pattern(self, template_content):
        """Should have implementation + wrapper layers."""
        # Implementation layer (typically ends with _impl)
        assert "_impl" in template_content or "# Implementation layer" in template_content, (
            "Missing implementation layer (typically named with _impl suffix)"
        )
        # Wrapper layer
        function_count = template_content.count("async def")
        assert function_count >= 2, (
            f"Expected at least 2 async functions (implementation + wrapper), found {function_count}"
        )

    def test_has_asyncgenerator(self, template_content):
        """Should use AsyncGenerator for streaming."""
        assert "AsyncGenerator" in template_content, (
            "Missing AsyncGenerator type hint for streaming"
        )
        assert "yield" in template_content, (
            "Missing yield statement for async generator"
        )

    def test_has_cancelled_error_handling(self, template_content):
        """Should handle CancelledError properly."""
        assert "CancelledError" in template_content or "asyncio.CancelledError" in template_content, (
            "Missing CancelledError handling for stream cancellation"
        )
        assert "except" in template_content, (
            "Missing except block for error handling"
        )

    def test_has_finally_cleanup(self, template_content):
        """Should have cleanup in finally block."""
        assert "finally:" in template_content, (
            "Missing finally block for cleanup"
        )

    def test_has_async_for_pattern(self, template_content):
        """Should demonstrate async for pattern for consuming streams."""
        assert "async for" in template_content, (
            "Missing 'async for' pattern for consuming async generator"
        )


class TestHealthCheckTemplate:
    """Tests for tools/health_check_tool.py.template - Health check endpoint."""

    @pytest.fixture
    def template_path(self):
        """Path to the health check tool template."""
        return TEMPLATE_BASE / "tools" / "health_check_tool.py.template"

    @pytest.fixture
    def template_content(self, template_path):
        """Load template content."""
        assert template_path.exists(), f"Template not found: {template_path}"
        return template_path.read_text()

    def test_template_exists(self, template_path):
        """Template file should exist."""
        assert template_path.exists(), (
            f"Health check tool template missing: {template_path}"
        )

    def test_has_uptime_tracking(self, template_content):
        """Should track uptime with _start_time."""
        assert "_start_time" in template_content or "start_time" in template_content, (
            "Missing uptime tracking variable (_start_time or start_time)"
        )
        assert "uptime" in template_content.lower(), (
            "Missing uptime calculation or reporting"
        )

    def test_has_memory_monitoring(self, template_content):
        """Should use psutil for memory monitoring."""
        assert "psutil" in template_content, (
            "Missing psutil import for memory monitoring"
        )
        assert "memory" in template_content.lower(), (
            "Missing memory monitoring code"
        )

    def test_has_utc_datetime(self, template_content):
        """Should use timezone-aware UTC datetime."""
        assert "datetime" in template_content, (
            "Missing datetime usage"
        )
        assert "UTC" in template_content or "utc" in template_content or "timezone.utc" in template_content, (
            "Missing UTC timezone specification (should use timezone-aware datetime)"
        )

    def test_has_dependency_health_checks(self, template_content):
        """Should include dependency health check patterns."""
        assert "dependencies" in template_content.lower() or "services" in template_content.lower(), (
            "Missing dependency/service health check pattern"
        )

    def test_has_status_reporting(self, template_content):
        """Should report health status."""
        assert "status" in template_content.lower(), (
            "Missing status reporting"
        )


class TestPaginatedToolTemplate:
    """Tests for tools/paginated_tool.py.template - Cursor-based pagination."""

    @pytest.fixture
    def template_path(self):
        """Path to the paginated tool template."""
        return TEMPLATE_BASE / "tools" / "paginated_tool.py.template"

    @pytest.fixture
    def template_content(self, template_path):
        """Load template content."""
        assert template_path.exists(), f"Template not found: {template_path}"
        return template_path.read_text()

    def test_template_exists(self, template_path):
        """Template file should exist."""
        assert template_path.exists(), (
            f"Paginated tool template missing: {template_path}"
        )

    def test_has_cursor_parameter(self, template_content):
        """Should have optional cursor parameter."""
        assert "cursor" in template_content, (
            "Missing cursor parameter"
        )
        assert "Optional" in template_content or "None" in template_content, (
            "Cursor should be optional (Optional[str] or default None)"
        )

    def test_has_limit_bounds(self, template_content):
        """Should validate limit between 1-100."""
        assert "limit" in template_content, (
            "Missing limit parameter"
        )
        # Check for validation logic
        has_min_check = "1" in template_content and ("<" in template_content or ">" in template_content)
        has_max_check = "100" in template_content
        assert has_min_check or has_max_check, (
            "Missing limit bounds validation (should be between 1-100)"
        )

    def test_has_next_cursor_response(self, template_content):
        """Should return next_cursor in response."""
        assert "next_cursor" in template_content, (
            "Missing next_cursor in response"
        )

    def test_has_has_more_indicator(self, template_content):
        """Should return has_more indicator."""
        assert "has_more" in template_content, (
            "Missing has_more indicator in response"
        )

    def test_has_items_in_response(self, template_content):
        """Should return items/results in response."""
        assert "items" in template_content or "results" in template_content, (
            "Missing items/results list in response"
        )


class TestResourceTemplate:
    """Tests for resources/resource.py.template - Resource template."""

    @pytest.fixture
    def template_path(self):
        """Path to the resource template."""
        return TEMPLATE_BASE / "resources" / "resource.py.template"

    @pytest.fixture
    def template_content(self, template_path):
        """Load template content."""
        assert template_path.exists(), f"Template not found: {template_path}"
        return template_path.read_text()

    def test_template_exists(self, template_path):
        """Template file should exist."""
        assert template_path.exists(), (
            f"Resource template missing: {template_path}"
        )

    def test_has_resource_decorator(self, template_content):
        """Should have @mcp.resource() decorator pattern."""
        assert "@mcp.resource()" in template_content or "@resource" in template_content, (
            "Missing resource decorator pattern"
        )

    def test_has_uri_pattern(self, template_content):
        """Should have URI pattern for resource."""
        assert "uri" in template_content.lower(), (
            "Missing URI pattern for resource"
        )

    def test_has_async_function(self, template_content):
        """Should have async def structure."""
        assert "async def" in template_content, (
            "Missing async function definition"
        )


class TestDockerfileTemplate:
    """Tests for config/Dockerfile.template - Docker configuration."""

    @pytest.fixture
    def template_path(self):
        """Path to the Dockerfile template."""
        return TEMPLATE_BASE / "config" / "Dockerfile.template"

    @pytest.fixture
    def template_content(self, template_path):
        """Load template content."""
        assert template_path.exists(), f"Template not found: {template_path}"
        return template_path.read_text()

    def test_template_exists(self, template_path):
        """Template file should exist."""
        assert template_path.exists(), (
            f"Dockerfile template missing: {template_path}"
        )

    def test_has_python310_slim(self, template_content):
        """Should use python:3.10-slim base image."""
        assert "python:3.10" in template_content, (
            "Missing Python 3.10 base image"
        )
        assert "slim" in template_content, (
            "Should use slim variant for smaller image size"
        )

    def test_has_nonroot_user(self, template_content):
        """Should create and use non-root 'mcp' user."""
        assert "useradd" in template_content or "adduser" in template_content, (
            "Missing user creation"
        )
        assert "mcp" in template_content.lower(), (
            "Missing 'mcp' user reference"
        )
        assert "USER" in template_content, (
            "Missing USER directive to switch to non-root user"
        )

    def test_has_pythonunbuffered(self, template_content):
        """Should set PYTHONUNBUFFERED=1."""
        assert "PYTHONUNBUFFERED" in template_content, (
            "Missing PYTHONUNBUFFERED environment variable"
        )
        assert "PYTHONUNBUFFERED=1" in template_content or 'PYTHONUNBUFFERED="1"' in template_content, (
            "PYTHONUNBUFFERED should be set to 1"
        )

    def test_has_stdio_cmd(self, template_content):
        """Should have proper CMD for stdio transport."""
        assert "CMD" in template_content, (
            "Missing CMD directive"
        )
        assert "python" in template_content.lower(), (
            "CMD should run Python"
        )

    def test_has_workdir(self, template_content):
        """Should set WORKDIR."""
        assert "WORKDIR" in template_content, (
            "Missing WORKDIR directive"
        )


class TestPyprojectTemplate:
    """Tests for config/pyproject.toml.template - Project configuration."""

    @pytest.fixture
    def template_path(self):
        """Path to the pyproject.toml template."""
        return TEMPLATE_BASE / "config" / "pyproject.toml.template"

    @pytest.fixture
    def template_content(self, template_path):
        """Load template content."""
        assert template_path.exists(), f"Template not found: {template_path}"
        return template_path.read_text()

    def test_template_exists(self, template_path):
        """Template file should exist."""
        assert template_path.exists(), (
            f"pyproject.toml template missing: {template_path}"
        )

    def test_has_python310_requirement(self, template_content):
        """Should require Python >=3.10."""
        assert "python" in template_content.lower(), (
            "Missing Python version requirement"
        )
        assert "3.10" in template_content, (
            "Should require Python 3.10 or higher"
        )
        assert ">=" in template_content or "^" in template_content, (
            "Should use >= or ^ for version specification"
        )

    def test_has_mcp_dependency(self, template_content):
        """Should include mcp[cli] dependency."""
        assert "mcp" in template_content, (
            "Missing mcp dependency"
        )
        # Should have either mcp[cli] or separate mcp and cli entries
        assert "[cli]" in template_content or "mcp-cli" in template_content, (
            "Should include CLI extras for mcp (mcp[cli])"
        )

    def test_has_pytest_asyncio(self, template_content):
        """Should include pytest-asyncio in dev deps."""
        assert "pytest-asyncio" in template_content, (
            "Missing pytest-asyncio in dev dependencies"
        )

    def test_has_asyncio_mode_auto(self, template_content):
        """Should configure asyncio_mode = 'auto'."""
        assert "asyncio_mode" in template_content, (
            "Missing asyncio_mode configuration"
        )
        assert '"auto"' in template_content or "'auto'" in template_content, (
            "asyncio_mode should be set to 'auto'"
        )

    def test_has_pytest_section(self, template_content):
        """Should have pytest configuration section."""
        assert "[tool.pytest" in template_content, (
            "Missing pytest configuration section"
        )

    def test_has_project_name_placeholder(self, template_content):
        """Should have project name placeholder."""
        assert "{{" in template_content and "}}" in template_content, (
            "Missing template placeholders ({{...}})"
        )


class TestConftestTemplate:
    """Tests for testing/conftest.py.template - pytest fixtures."""

    @pytest.fixture
    def template_path(self):
        """Path to the conftest.py template."""
        return TEMPLATE_BASE / "testing" / "conftest.py.template"

    @pytest.fixture
    def template_content(self, template_path):
        """Load template content."""
        assert template_path.exists(), f"Template not found: {template_path}"
        return template_path.read_text()

    def test_template_exists(self, template_path):
        """Template file should exist."""
        assert template_path.exists(), (
            f"conftest.py template missing: {template_path}"
        )

    def test_has_pytest_imports(self, template_content):
        """Should import pytest and pytest-asyncio markers."""
        assert "import pytest" in template_content, (
            "Missing pytest import"
        )

    def test_has_mcp_client_fixture(self, template_content):
        """Should have MCP client test fixture."""
        assert "@pytest.fixture" in template_content, (
            "Missing pytest fixture decorator"
        )
        assert "mcp" in template_content.lower(), (
            "Should include MCP-related test fixture"
        )

    def test_has_async_fixture(self, template_content):
        """Should demonstrate async fixture pattern."""
        assert "async" in template_content or "asyncio" in template_content, (
            "Should include async fixture pattern"
        )


class TestTestToolTemplate:
    """Tests for testing/test_tool.py.template - Test template."""

    @pytest.fixture
    def template_path(self):
        """Path to the test_tool.py template."""
        return TEMPLATE_BASE / "testing" / "test_tool.py.template"

    @pytest.fixture
    def template_content(self, template_path):
        """Load template content."""
        assert template_path.exists(), f"Template not found: {template_path}"
        return template_path.read_text()

    def test_template_exists(self, template_path):
        """Template file should exist."""
        assert template_path.exists(), (
            f"test_tool.py template missing: {template_path}"
        )

    def test_has_asyncio_markers(self, template_content):
        """Should have pytest.mark.asyncio markers."""
        assert "@pytest.mark.asyncio" in template_content, (
            "Missing @pytest.mark.asyncio marker for async tests"
        )

    def test_has_basic_test_structure(self, template_content):
        """Should have basic test function structure."""
        assert "async def test_" in template_content, (
            "Missing async test function (should start with 'test_')"
        )
        assert "assert" in template_content, (
            "Missing assertion in test"
        )

    def test_has_pytest_import(self, template_content):
        """Should import pytest."""
        assert "import pytest" in template_content, (
            "Missing pytest import"
        )

    def test_has_tool_test_example(self, template_content):
        """Should demonstrate tool testing pattern."""
        assert "tool" in template_content.lower(), (
            "Should include tool testing example"
        )


class TestTemplateDirectory:
    """Tests for overall template directory structure."""

    def test_templates_directory_exists(self):
        """Templates directory should exist."""
        assert TEMPLATE_BASE.exists(), (
            f"Templates directory missing: {TEMPLATE_BASE}"
        )

    def test_server_directory_exists(self):
        """Server directory should exist."""
        server_dir = TEMPLATE_BASE / "server"
        assert server_dir.exists(), (
            f"Server directory missing: {server_dir}"
        )

    def test_tools_directory_exists(self):
        """Tools directory should exist."""
        tools_dir = TEMPLATE_BASE / "tools"
        assert tools_dir.exists(), (
            f"Tools directory missing: {tools_dir}"
        )

    def test_resources_directory_exists(self):
        """Resources directory should exist."""
        resources_dir = TEMPLATE_BASE / "resources"
        assert resources_dir.exists(), (
            f"Resources directory missing: {resources_dir}"
        )

    def test_config_directory_exists(self):
        """Config directory should exist."""
        config_dir = TEMPLATE_BASE / "config"
        assert config_dir.exists(), (
            f"Config directory missing: {config_dir}"
        )

    def test_testing_directory_exists(self):
        """Testing directory should exist."""
        testing_dir = TEMPLATE_BASE / "testing"
        assert testing_dir.exists(), (
            f"Testing directory missing: {testing_dir}"
        )


class TestTemplateCompleteness:
    """Meta-tests to ensure all templates are covered."""

    def test_all_11_templates_have_tests(self):
        """Verify we have test classes for all 11 templates."""
        expected_templates = [
            "server/__main__.py.template",
            "server/server.py.template",
            "tools/tool.py.template",
            "tools/streaming_tool.py.template",
            "tools/health_check_tool.py.template",
            "tools/paginated_tool.py.template",
            "resources/resource.py.template",
            "config/Dockerfile.template",
            "config/pyproject.toml.template",
            "testing/conftest.py.template",
            "testing/test_tool.py.template",
        ]

        # Get all test classes in this module
        test_classes = [
            TestServerMainTemplate,
            TestServerPyTemplate,
            TestBasicToolTemplate,
            TestStreamingToolTemplate,
            TestHealthCheckTemplate,
            TestPaginatedToolTemplate,
            TestResourceTemplate,
            TestDockerfileTemplate,
            TestPyprojectTemplate,
            TestConftestTemplate,
            TestTestToolTemplate,
        ]

        assert len(test_classes) == len(expected_templates), (
            f"Expected {len(expected_templates)} test classes, found {len(test_classes)}"
        )

    def test_no_stdout_logging_in_any_template(self):
        """CRITICAL: No template should log to stdout (breaks stdio transport)."""
        if not TEMPLATE_BASE.exists():
            pytest.skip("Templates directory doesn't exist yet (RED phase)")

        violations = []
        for template_file in TEMPLATE_BASE.rglob("*.template"):
            content = template_file.read_text()
            if "stdout" in content.lower() and "logging" in content.lower():
                # Check if it's explicitly configured to stdout
                if "sys.stdout" in content or 'stream=stdout' in content:
                    violations.append(str(template_file.relative_to(TEMPLATE_BASE)))

        assert not violations, (
            f"Templates with stdout logging (breaks stdio transport): {violations}\n"
            "All logging MUST go to stderr to avoid interfering with MCP stdio protocol."
        )
