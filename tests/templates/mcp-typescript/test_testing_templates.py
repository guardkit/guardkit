"""
Tests for MCP TypeScript testing templates.

These tests validate the testing/ subdirectory templates including:
- tool.test.ts.template - Vitest unit tests for MCP tools
- protocol.sh.template - JSON-RPC protocol test script
- vitest.config.ts.template - Vitest configuration
- setup.ts.template - Test setup file

Test Pattern: TDD RED Phase - All tests should FAIL initially
"""

import pytest
from pathlib import Path


@pytest.fixture
def templates_dir():
    """Path to mcp-typescript templates directory."""
    return Path(__file__).parent.parent.parent.parent / "installer" / "core" / "templates" / "mcp-typescript" / "templates"


@pytest.fixture
def testing_dir(templates_dir):
    """Path to testing templates subdirectory."""
    return templates_dir / "testing"


@pytest.fixture
def tool_test_template(testing_dir):
    """Load tool.test.ts.template content."""
    template_path = testing_dir / "tool.test.ts.template"
    if not template_path.exists():
        pytest.fail(f"Template not found: {template_path}")
    return template_path.read_text()


@pytest.fixture
def protocol_template(testing_dir):
    """Load protocol.sh.template content."""
    template_path = testing_dir / "protocol.sh.template"
    if not template_path.exists():
        pytest.fail(f"Template not found: {template_path}")
    return template_path.read_text()


@pytest.fixture
def vitest_config_template(testing_dir):
    """Load vitest.config.ts.template content."""
    template_path = testing_dir / "vitest.config.ts.template"
    if not template_path.exists():
        pytest.fail(f"Template not found: {template_path}")
    return template_path.read_text()


@pytest.fixture
def setup_template(testing_dir):
    """Load setup.ts.template content."""
    template_path = testing_dir / "setup.ts.template"
    if not template_path.exists():
        pytest.fail(f"Template not found: {template_path}")
    return template_path.read_text()


class TestTestingTemplatesExist:
    """Test that all testing template files exist."""

    def test_testing_directory_exists(self, testing_dir):
        """Testing templates directory should exist."""
        assert testing_dir.exists(), f"Testing templates directory not found: {testing_dir}"
        assert testing_dir.is_dir(), f"Testing templates path is not a directory: {testing_dir}"

    def test_tool_test_template_exists(self, testing_dir):
        """tool.test.ts.template should exist."""
        template_path = testing_dir / "tool.test.ts.template"
        assert template_path.exists(), f"Template not found: {template_path}"
        assert template_path.is_file(), f"Template path is not a file: {template_path}"

    def test_protocol_template_exists(self, testing_dir):
        """protocol.sh.template should exist."""
        template_path = testing_dir / "protocol.sh.template"
        assert template_path.exists(), f"Template not found: {template_path}"
        assert template_path.is_file(), f"Template path is not a file: {template_path}"

    def test_vitest_config_template_exists(self, testing_dir):
        """vitest.config.ts.template should exist."""
        template_path = testing_dir / "vitest.config.ts.template"
        assert template_path.exists(), f"Template not found: {template_path}"
        assert template_path.is_file(), f"Template path is not a file: {template_path}"

    def test_setup_template_exists(self, testing_dir):
        """setup.ts.template should exist."""
        template_path = testing_dir / "setup.ts.template"
        assert template_path.exists(), f"Template not found: {template_path}"
        assert template_path.is_file(), f"Template path is not a file: {template_path}"


class TestToolTestTemplate:
    """Test tool.test.ts.template structure and content."""

    def test_has_vitest_imports(self, tool_test_template):
        """Should import core Vitest functions."""
        required_imports = [
            'describe',
            'it',
            'expect',
            'beforeEach',
            'vi'
        ]

        for import_name in required_imports:
            assert import_name in tool_test_template, \
                f"Missing required Vitest import: {import_name}"

        assert "from 'vitest'" in tool_test_template, \
            "Missing vitest import statement"

    def test_has_tool_imports(self, tool_test_template):
        """Should import tool implementation and schema."""
        assert "{{toolName}}Impl" in tool_test_template, \
            "Missing {{toolName}}Impl import placeholder"
        assert "{{toolName}}Schema" in tool_test_template, \
            "Missing {{toolName}}Schema import placeholder"
        assert "from '../src/tools/{{tool-name}}.js'" in tool_test_template, \
            "Missing tool import path"

    def test_has_describe_blocks(self, tool_test_template):
        """Should have describe blocks for organizing tests."""
        assert "describe('{{ToolName}}'" in tool_test_template, \
            "Missing main describe block with {{ToolName}} placeholder"
        assert "describe('{{toolName}}Impl'" in tool_test_template, \
            "Missing implementation describe block"
        assert "describe('schema validation'" in tool_test_template, \
            "Missing schema validation describe block"

    def test_has_implementation_tests(self, tool_test_template):
        """Should have tests for tool implementation."""
        # Valid input test
        assert "it('should process valid input'" in tool_test_template, \
            "Missing valid input test case"
        assert "await {{toolName}}Impl" in tool_test_template, \
            "Missing async tool invocation"
        assert "{{paramName}}: 'test-value'" in tool_test_template, \
            "Missing parameter placeholder in test"
        assert "expect(result).toBeDefined()" in tool_test_template, \
            "Missing result defined assertion"

        # Empty input test
        assert "it('should handle empty input'" in tool_test_template, \
            "Missing empty input test case"
        assert "{{paramName}}: ''" in tool_test_template, \
            "Missing empty string test"

    def test_has_schema_validation_tests(self, tool_test_template):
        """Should have schema validation tests."""
        # Valid input validation
        assert "it('should validate correct input'" in tool_test_template, \
            "Missing correct input validation test"
        assert "{{toolName}}Schema.{{paramName}}.parse" in tool_test_template, \
            "Missing schema parse call"

        # Invalid input validation
        assert "it('should reject invalid input'" in tool_test_template, \
            "Missing invalid input validation test"
        assert "expect(() => {" in tool_test_template, \
            "Missing expect function wrapper for error test"
        assert "}).toThrow()" in tool_test_template, \
            "Missing toThrow() assertion"

    def test_has_all_placeholders(self, tool_test_template):
        """Should have all required placeholders."""
        required_placeholders = [
            '{{ToolName}}',      # PascalCase for class/type names
            '{{toolName}}',      # camelCase for variables/functions
            '{{tool-name}}',     # kebab-case for file names
            '{{paramName}}'      # camelCase for parameters
        ]

        for placeholder in required_placeholders:
            assert placeholder in tool_test_template, \
                f"Missing required placeholder: {placeholder}"

    def test_has_doc_comment(self, tool_test_template):
        """Should have documentation comment."""
        assert "/**" in tool_test_template, \
            "Missing JSDoc comment start"
        assert "* Tests for {{ToolName}}" in tool_test_template, \
            "Missing test description comment"
        assert "*/" in tool_test_template, \
            "Missing JSDoc comment end"


class TestProtocolTemplate:
    """Test protocol.sh.template structure and content."""

    def test_has_bash_shebang(self, protocol_template):
        """Should start with bash shebang."""
        assert protocol_template.startswith("#!/bin/bash"), \
            "Missing bash shebang at start of file"

    def test_has_error_handling(self, protocol_template):
        """Should have set -e for error handling."""
        assert "set -e" in protocol_template, \
            "Missing 'set -e' error handling"

    def test_has_server_command(self, protocol_template):
        """Should define SERVER_CMD variable."""
        assert 'SERVER_CMD=' in protocol_template, \
            "Missing SERVER_CMD variable definition"
        assert 'npx tsx src/index.ts' in protocol_template, \
            "Missing npx tsx command"

    def test_has_header_comment(self, protocol_template):
        """Should have header with server name placeholder."""
        assert "Protocol tests for {{ServerName}}" in protocol_template, \
            "Missing protocol tests header"
        assert "=== MCP Protocol Tests for {{ServerName}} ===" in protocol_template, \
            "Missing test suite header"

    def test_has_initialize_test(self, protocol_template):
        """Should test MCP initialize method."""
        assert "Test 1: Initialize" in protocol_template, \
            "Missing initialize test header"
        assert '"method":"initialize"' in protocol_template, \
            "Missing initialize method"
        assert '"protocolVersion":"2024-11-05"' in protocol_template, \
            "Missing protocol version"
        assert '"clientInfo"' in protocol_template, \
            "Missing client info"

    def test_has_tools_list_test(self, protocol_template):
        """Should test tools/list method."""
        assert "Test 2: List Tools" in protocol_template, \
            "Missing list tools test header"
        assert '"method":"tools/list"' in protocol_template, \
            "Missing tools/list method"

    def test_has_tools_call_test(self, protocol_template):
        """Should test tools/call method."""
        assert "Test 3: Call Tool" in protocol_template, \
            "Missing call tool test header"
        assert '"method":"tools/call"' in protocol_template, \
            "Missing tools/call method"
        assert '"name":"{{tool-name}}"' in protocol_template, \
            "Missing tool name placeholder"
        assert '"arguments":{' in protocol_template, \
            "Missing arguments object"
        assert '"{{paramName}}"' in protocol_template, \
            "Missing parameter name placeholder"

    def test_has_resources_list_test(self, protocol_template):
        """Should test resources/list method."""
        assert "Test 4: List Resources" in protocol_template, \
            "Missing list resources test header"
        assert '"method":"resources/list"' in protocol_template, \
            "Missing resources/list method"

    def test_has_error_handling_test(self, protocol_template):
        """Should test error handling with invalid tool."""
        assert "Test 5: Invalid Tool" in protocol_template, \
            "Missing error handling test header"
        assert "expect error" in protocol_template.lower(), \
            "Missing error expectation comment"
        assert '"name":"nonexistent-tool"' in protocol_template, \
            "Missing nonexistent tool name"
        assert "|| true" in protocol_template, \
            "Missing error suppression for expected failure"

    def test_has_completion_message(self, protocol_template):
        """Should have test completion message."""
        assert "Protocol Tests Complete" in protocol_template, \
            "Missing completion message"

    def test_has_all_placeholders(self, protocol_template):
        """Should have all required placeholders."""
        required_placeholders = [
            '{{ServerName}}',    # PascalCase for server name
            '{{tool-name}}',     # kebab-case for tool name
            '{{paramName}}'      # camelCase for parameter
        ]

        for placeholder in required_placeholders:
            assert placeholder in protocol_template, \
                f"Missing required placeholder: {placeholder}"


class TestVitestConfigTemplate:
    """Test vitest.config.ts.template structure and content."""

    def test_has_vitest_import(self, vitest_config_template):
        """Should import defineConfig from vitest/config."""
        assert "import { defineConfig }" in vitest_config_template, \
            "Missing defineConfig import"
        assert "from 'vitest/config'" in vitest_config_template, \
            "Missing vitest/config import path"

    def test_has_export_default(self, vitest_config_template):
        """Should export default config."""
        assert "export default defineConfig" in vitest_config_template, \
            "Missing export default defineConfig"

    def test_has_test_config(self, vitest_config_template):
        """Should have test configuration object."""
        assert "test: {" in vitest_config_template, \
            "Missing test config object"

    def test_has_globals_enabled(self, vitest_config_template):
        """Should enable globals."""
        assert "globals: true" in vitest_config_template, \
            "Missing globals: true setting"

    def test_has_node_environment(self, vitest_config_template):
        """Should use node environment."""
        assert "environment: 'node'" in vitest_config_template, \
            "Missing node environment setting"

    def test_has_include_pattern(self, vitest_config_template):
        """Should include tests/**/*.test.ts pattern."""
        assert "include:" in vitest_config_template, \
            "Missing include config"
        assert "tests/**/*.test.ts" in vitest_config_template, \
            "Missing test file pattern"

    def test_has_coverage_config(self, vitest_config_template):
        """Should have coverage configuration."""
        assert "coverage: {" in vitest_config_template, \
            "Missing coverage config object"

    def test_has_v8_provider(self, vitest_config_template):
        """Should use v8 coverage provider."""
        assert "provider: 'v8'" in vitest_config_template, \
            "Missing v8 coverage provider"

    def test_has_coverage_reporters(self, vitest_config_template):
        """Should configure coverage reporters."""
        assert "reporter:" in vitest_config_template, \
            "Missing reporter config"
        assert "'text'" in vitest_config_template, \
            "Missing text reporter"
        assert "'json'" in vitest_config_template, \
            "Missing json reporter"
        assert "'html'" in vitest_config_template, \
            "Missing html reporter"

    def test_has_coverage_include(self, vitest_config_template):
        """Should include src/**/*.ts in coverage."""
        assert "include:" in vitest_config_template, \
            "Missing coverage include"
        assert "src/**/*.ts" in vitest_config_template, \
            "Missing src file pattern"

    def test_has_coverage_exclude(self, vitest_config_template):
        """Should exclude entry point from coverage."""
        assert "exclude:" in vitest_config_template, \
            "Missing coverage exclude"
        assert "src/index.ts" in vitest_config_template, \
            "Missing index.ts exclusion"

    def test_has_coverage_thresholds(self, vitest_config_template):
        """Should have 80% coverage thresholds."""
        assert "thresholds: {" in vitest_config_template, \
            "Missing thresholds config"
        assert "lines: 80" in vitest_config_template, \
            "Missing or incorrect lines threshold (should be 80)"
        assert "branches: 75" in vitest_config_template, \
            "Missing or incorrect branches threshold (should be 75)"
        assert "functions: 80" in vitest_config_template, \
            "Missing or incorrect functions threshold (should be 80)"
        assert "statements: 80" in vitest_config_template, \
            "Missing or incorrect statements threshold (should be 80)"

    def test_has_setup_files(self, vitest_config_template):
        """Should reference setup file."""
        assert "setupFiles:" in vitest_config_template, \
            "Missing setupFiles config"
        assert "./tests/setup.ts" in vitest_config_template, \
            "Missing setup.ts reference"


class TestSetupTemplate:
    """Test setup.ts.template structure and content."""

    def test_has_doc_comment(self, setup_template):
        """Should have documentation comment."""
        assert "/**" in setup_template, \
            "Missing JSDoc comment start"
        assert "* Vitest setup file" in setup_template, \
            "Missing setup file description"
        assert "*/" in setup_template, \
            "Missing JSDoc comment end"

    def test_has_vitest_import(self, setup_template):
        """Should import vi from vitest."""
        assert "import { vi }" in setup_template, \
            "Missing vi import"
        assert "from 'vitest'" in setup_template, \
            "Missing vitest import path"

    def test_has_console_log_mock(self, setup_template):
        """Should mock console.log with warning."""
        assert "console.log = " in setup_template, \
            "Missing console.log mock"
        assert "console.error('WARNING: console.log detected!" in setup_template, \
            "Missing console.log warning"
        assert "Use console.error for MCP servers" in setup_template, \
            "Missing MCP protocol guidance"

    def test_preserves_original_log(self, setup_template):
        """Should preserve original console.log."""
        assert "const originalLog = console.log" in setup_template, \
            "Missing originalLog preservation"
        assert "originalLog(...args)" in setup_template, \
            "Missing call to original console.log"

    def test_has_global_setup_comment(self, setup_template):
        """Should have comment about global setup."""
        assert "Add any global test setup here" in setup_template, \
            "Missing global setup comment"

    def test_has_mcp_protocol_warning(self, setup_template):
        """Should warn about console.log breaking MCP protocol."""
        assert "console.log breaks MCP protocol" in setup_template, \
            "Missing MCP protocol warning comment"


class TestTemplatesIntegration:
    """Test integration between testing templates."""

    def test_tool_test_imports_match_structure(self, tool_test_template):
        """Tool test imports should match project structure."""
        # Should import from ../src/tools/ (relative path)
        assert "from '../src/tools/" in tool_test_template, \
            "Tool test import path doesn't match expected structure"

    def test_vitest_config_references_setup(self, vitest_config_template):
        """Vitest config should reference setup file."""
        assert "./tests/setup.ts" in vitest_config_template, \
            "Setup file reference missing from vitest config"

    def test_protocol_script_uses_correct_entry(self, protocol_template):
        """Protocol script should use correct entry point."""
        assert "src/index.ts" in protocol_template, \
            "Protocol script doesn't reference correct entry point"

    def test_coverage_thresholds_match_guardkit_standards(self, vitest_config_template):
        """Coverage thresholds should match GuardKit standards."""
        # GuardKit standard is 80% for most metrics
        assert "lines: 80" in vitest_config_template, \
            "Line coverage should be 80% per GuardKit standards"
        assert "functions: 80" in vitest_config_template, \
            "Function coverage should be 80% per GuardKit standards"
        assert "statements: 80" in vitest_config_template, \
            "Statement coverage should be 80% per GuardKit standards"
        # Branch coverage is typically lower
        assert "branches: 75" in vitest_config_template, \
            "Branch coverage should be 75% per GuardKit standards"
