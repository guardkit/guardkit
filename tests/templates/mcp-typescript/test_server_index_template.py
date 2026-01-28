"""
TDD RED Phase: Tests for mcp-typescript server/index.ts.template

These tests validate the server index template structure and content.
Initially FAIL because the template does not exist yet.

Coverage Target: >=85%
Test Count: 15+ tests
"""

import pytest
from pathlib import Path


# Path to the template file
TEMPLATE_PATH = Path(__file__).parent.parent.parent.parent / "installer/core/templates/mcp-typescript/templates/server/index.ts.template"


class TestTemplateExists:
    """Test that the index.ts.template file exists in the correct location."""

    def test_template_file_exists(self):
        """Verify index.ts.template exists at the expected path."""
        assert TEMPLATE_PATH.exists(), f"index.ts.template not found at {TEMPLATE_PATH}"

    def test_template_file_not_empty(self):
        """Verify the template file is not empty."""
        assert TEMPLATE_PATH.exists(), f"Template file must exist first"
        content = TEMPLATE_PATH.read_text()
        assert len(content) > 0, "Template file must not be empty"


class TestRequiredImports:
    """Test that the template contains all required imports."""

    @pytest.fixture
    def template_content(self):
        """Load the template file content."""
        return TEMPLATE_PATH.read_text()

    def test_imports_mcp_server(self, template_content):
        """Verify template imports McpServer from @modelcontextprotocol/sdk/server/mcp.js."""
        assert "import { McpServer }" in template_content or \
               "import {McpServer}" in template_content, \
            "Template must import McpServer"
        assert "@modelcontextprotocol/sdk/server/mcp.js" in template_content, \
            "McpServer import must be from @modelcontextprotocol/sdk/server/mcp.js"

    def test_imports_stdio_transport(self, template_content):
        """Verify template imports StdioServerTransport from @modelcontextprotocol/sdk/server/stdio.js."""
        assert "StdioServerTransport" in template_content, \
            "Template must import StdioServerTransport"
        assert "@modelcontextprotocol/sdk/server/stdio.js" in template_content, \
            "StdioServerTransport import must be from @modelcontextprotocol/sdk/server/stdio.js"

    def test_imports_zod(self, template_content):
        """Verify template imports Zod for schema validation."""
        # Check for Zod import (can be import * as z or import { z })
        has_zod_import = (
            "import * as z from 'zod'" in template_content or
            "import * as z from \"zod\"" in template_content or
            "import { z } from 'zod'" in template_content or
            "import { z } from \"zod\"" in template_content or
            "from 'zod'" in template_content or
            "from \"zod\"" in template_content
        )
        assert has_zod_import, "Template must import Zod for schema validation"


class TestRequiredPlaceholders:
    """Test that the template contains all required placeholders."""

    @pytest.fixture
    def template_content(self):
        """Load the template file content."""
        return TEMPLATE_PATH.read_text()

    def test_servername_placeholder(self, template_content):
        """Verify template contains {{ServerName}} placeholder."""
        assert "{{ServerName}}" in template_content, \
            "Template must contain {{ServerName}} placeholder"

    def test_serverversion_placeholder(self, template_content):
        """Verify template contains {{ServerVersion}} placeholder."""
        assert "{{ServerVersion}}" in template_content, \
            "Template must contain {{ServerVersion}} placeholder"

    def test_description_placeholder(self, template_content):
        """Verify template contains {{Description}} placeholder."""
        assert "{{Description}}" in template_content, \
            "Template must contain {{Description}} placeholder"

    def test_servername_used_in_constructor(self, template_content):
        """Verify {{ServerName}} is used in McpServer constructor."""
        # Should be used as: name: '{{ServerName}}'
        assert "name:" in template_content and "{{ServerName}}" in template_content, \
            "{{ServerName}} must be used in McpServer constructor"

    def test_serverversion_used_in_constructor(self, template_content):
        """Verify {{ServerVersion}} is used in McpServer constructor."""
        # Should be used as: version: '{{ServerVersion}}'
        assert "version:" in template_content and "{{ServerVersion}}" in template_content, \
            "{{ServerVersion}} must be used in McpServer constructor"


class TestLoggingPattern:
    """Test that the template uses correct logging pattern (console.error only)."""

    @pytest.fixture
    def template_content(self):
        """Load the template file content."""
        return TEMPLATE_PATH.read_text()

    def test_uses_console_error(self, template_content):
        """Verify template uses console.error for logging."""
        assert "console.error" in template_content, \
            "Template must use console.error for logging (stdout is MCP protocol)"

    def test_does_not_use_console_log(self, template_content):
        """Verify template does NOT use console.log (would corrupt MCP protocol)."""
        # Check for console.log but exclude comments
        lines = template_content.split('\n')
        for line in lines:
            stripped = line.strip()
            # Skip comment lines
            if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*'):
                continue
            # Check for console.log in non-comment code
            if 'console.log' in stripped:
                assert False, f"Template must NOT use console.log (found: {stripped}). Use console.error instead."


class TestToolRegistrationOrder:
    """Test that the template registers tools BEFORE server.connect()."""

    @pytest.fixture
    def template_content(self):
        """Load the template file content."""
        return TEMPLATE_PATH.read_text()

    def test_tool_registration_before_connect(self, template_content):
        """Verify tool registration appears before server.connect()."""
        register_pos = template_content.find("registerTool")
        connect_pos = template_content.find("server.connect")

        assert register_pos != -1, "Template must contain registerTool call"
        assert connect_pos != -1, "Template must contain server.connect call"
        assert register_pos < connect_pos, \
            "Tool registration MUST appear BEFORE server.connect() (critical MCP pattern)"

    def test_has_example_tool_registration(self, template_content):
        """Verify template includes an example tool registration."""
        assert "registerTool" in template_content, \
            "Template must include example tool registration"
        # Should have a tool name (kebab-case)
        assert "hello-world" in template_content or \
               "example" in template_content.lower(), \
            "Template should include a named example tool"


class TestAsyncMainFunction:
    """Test that the template has proper async main() with error handling."""

    @pytest.fixture
    def template_content(self):
        """Load the template file content."""
        return TEMPLATE_PATH.read_text()

    def test_has_async_main_function(self, template_content):
        """Verify template has async main function."""
        assert "async function main()" in template_content, \
            "Template must have async function main()"

    def test_main_creates_stdio_transport(self, template_content):
        """Verify main() creates StdioServerTransport."""
        assert "new StdioServerTransport()" in template_content, \
            "main() must create StdioServerTransport"

    def test_main_calls_server_connect(self, template_content):
        """Verify main() calls server.connect with transport."""
        assert "server.connect" in template_content, \
            "main() must call server.connect"
        assert "await server.connect" in template_content, \
            "server.connect must be awaited"

    def test_main_invoked_with_catch(self, template_content):
        """Verify main() is invoked with .catch() for error handling."""
        assert "main().catch" in template_content or \
               "main()\n.catch" in template_content or \
               "main().catch" in template_content.replace('\n', ''), \
            "main() must be invoked with .catch() for error handling"

    def test_error_handler_exits_process(self, template_content):
        """Verify error handler calls process.exit(1)."""
        assert "process.exit(1)" in template_content, \
            "Error handler must call process.exit(1)"


class TestTypeScriptPatterns:
    """Test that the template follows TypeScript best practices."""

    @pytest.fixture
    def template_content(self):
        """Load the template file content."""
        return TEMPLATE_PATH.read_text()

    def test_uses_const_for_server(self, template_content):
        """Verify server instance is declared with const."""
        assert "const server" in template_content, \
            "Server instance should be declared with const"

    def test_uses_const_for_transport(self, template_content):
        """Verify transport instance is declared with const."""
        assert "const transport" in template_content, \
            "Transport instance should be declared with const"

    def test_has_proper_file_header(self, template_content):
        """Verify template has a proper file header comment."""
        # Should start with a comment block
        assert template_content.strip().startswith("/**") or \
               template_content.strip().startswith("//"), \
            "Template should start with a comment header"
        # Should mention the server name placeholder
        assert "{{ServerName}}" in template_content[:500], \
            "File header should reference {{ServerName}}"


class TestZodSchemaUsage:
    """Test that the template demonstrates proper Zod schema usage."""

    @pytest.fixture
    def template_content(self):
        """Load the template file content."""
        return TEMPLATE_PATH.read_text()

    def test_zod_schema_in_tool(self, template_content):
        """Verify Zod schema is used in tool registration."""
        # Should have z.string(), z.number(), z.object(), etc.
        has_zod_schema = (
            "z.string()" in template_content or
            "z.number()" in template_content or
            "z.object(" in template_content or
            "z.boolean()" in template_content
        )
        assert has_zod_schema, \
            "Template should demonstrate Zod schema usage in tool registration"

    def test_zod_describe_method(self, template_content):
        """Verify Zod schemas use .describe() for documentation."""
        assert ".describe(" in template_content, \
            "Zod schemas should use .describe() method for parameter documentation"
