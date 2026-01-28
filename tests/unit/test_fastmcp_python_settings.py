"""
TDD RED PHASE: Tests for fastmcp-python template settings.json

These tests MUST FAIL initially since the settings.json file doesn't exist yet.
They verify the FastMCP-specific configuration requirements.
"""

import json
from pathlib import Path
import pytest


@pytest.fixture
def settings_file_path():
    """Path to the fastmcp-python settings.json file."""
    return Path("installer/core/templates/fastmcp-python/settings.json")


@pytest.fixture
def settings_data(settings_file_path):
    """Load and parse the settings.json file."""
    with open(settings_file_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestSettingsFileExists:
    """Test that the settings.json file exists at the correct location."""

    def test_settings_file_exists(self, settings_file_path):
        """FAIL: Settings file should exist at installer/core/templates/fastmcp-python/settings.json"""
        assert settings_file_path.exists(), f"Settings file not found at {settings_file_path}"

    def test_settings_file_is_file(self, settings_file_path):
        """FAIL: Settings path should be a file, not a directory"""
        assert settings_file_path.is_file(), f"{settings_file_path} is not a file"


class TestJSONStructure:
    """Test that the JSON is valid and properly structured."""

    def test_json_is_valid(self, settings_file_path):
        """FAIL: JSON should be valid and parseable"""
        try:
            with open(settings_file_path, "r", encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON: {e}")

    def test_schema_version_exists(self, settings_data):
        """FAIL: Settings should have a schema_version field"""
        assert "schema_version" in settings_data, "Missing schema_version field"

    def test_schema_version_value(self, settings_data):
        """FAIL: schema_version should be '1.0.0'"""
        assert settings_data["schema_version"] == "1.0.0", \
            f"Expected schema_version '1.0.0', got '{settings_data.get('schema_version')}'"


class TestNamingConventions:
    """Test MCP-specific naming conventions."""

    def test_naming_conventions_exists(self, settings_data):
        """FAIL: Settings should have naming_conventions section"""
        assert "naming_conventions" in settings_data, "Missing naming_conventions section"

    def test_tool_naming_convention(self, settings_data):
        """FAIL: Should have 'tool' naming convention with snake_case"""
        naming = settings_data.get("naming_conventions", {})
        assert "tool" in naming, "Missing 'tool' naming convention"
        assert naming["tool"]["case_style"] == "snake_case", \
            "Tool naming should use snake_case"

    def test_server_naming_convention(self, settings_data):
        """FAIL: Should have 'server' naming convention with kebab-case"""
        naming = settings_data.get("naming_conventions", {})
        assert "server" in naming, "Missing 'server' naming convention"
        assert naming["server"]["case_style"] == "kebab-case", \
            "Server naming should use kebab-case"

    def test_resource_naming_convention(self, settings_data):
        """FAIL: Should have 'resource' naming convention with snake_case"""
        naming = settings_data.get("naming_conventions", {})
        assert "resource" in naming, "Missing 'resource' naming convention"
        assert naming["resource"]["case_style"] == "snake_case", \
            "Resource naming should use snake_case"

    def test_test_file_naming_convention(self, settings_data):
        """FAIL: Should have 'test_file' naming convention with pattern 'test_{{feature}}.py'"""
        naming = settings_data.get("naming_conventions", {})
        assert "test_file" in naming, "Missing 'test_file' naming convention"
        assert naming["test_file"]["pattern"] == "test_{{feature}}.py", \
            "Test file pattern should be 'test_{{feature}}.py'"
        assert naming["test_file"]["prefix"] == "test_", \
            "Test files should have 'test_' prefix"

    def test_test_function_naming_convention(self, settings_data):
        """FAIL: Should have 'test_function' naming convention with pattern 'test_{{action}}_{{entity}}'"""
        naming = settings_data.get("naming_conventions", {})
        assert "test_function" in naming, "Missing 'test_function' naming convention"
        assert naming["test_function"]["pattern"] == "test_{{action}}_{{entity}}", \
            "Test function pattern should be 'test_{{action}}_{{entity}}'"


class TestFileOrganization:
    """Test file organization structure."""

    def test_file_organization_exists(self, settings_data):
        """FAIL: Settings should have file_organization section"""
        assert "file_organization" in settings_data, "Missing file_organization section"

    def test_by_feature_is_false(self, settings_data):
        """FAIL: FastMCP uses flat structure, by_feature should be false"""
        file_org = settings_data.get("file_organization", {})
        assert file_org.get("by_feature") is False, \
            "FastMCP uses flat structure, by_feature should be false"

    def test_test_location_is_separate(self, settings_data):
        """FAIL: Test location should be 'separate' (tests/ directory)"""
        file_org = settings_data.get("file_organization", {})
        assert file_org.get("test_location") == "separate", \
            "Test location should be 'separate'"


class TestLayerMappings:
    """Test MCP-specific layer mappings."""

    def test_layer_mappings_exists(self, settings_data):
        """FAIL: Settings should have layer_mappings section"""
        assert "layer_mappings" in settings_data, "Missing layer_mappings section"

    def test_tools_layer_mapping(self, settings_data):
        """FAIL: Should have 'tools' layer mapping to 'src/tools/'"""
        layers = settings_data.get("layer_mappings", {})
        assert "tools" in layers, "Missing 'tools' layer mapping"
        assert layers["tools"]["directory"] == "src/tools/", \
            "Tools should be in 'src/tools/' directory"

    def test_resources_layer_mapping(self, settings_data):
        """FAIL: Should have 'resources' layer mapping to 'src/resources/'"""
        layers = settings_data.get("layer_mappings", {})
        assert "resources" in layers, "Missing 'resources' layer mapping"
        assert layers["resources"]["directory"] == "src/resources/", \
            "Resources should be in 'src/resources/' directory"

    def test_server_layer_mapping(self, settings_data):
        """FAIL: Should have 'server' layer mapping to 'src/'"""
        layers = settings_data.get("layer_mappings", {})
        assert "server" in layers, "Missing 'server' layer mapping"
        assert layers["server"]["directory"] == "src/", \
            "Server files should be in 'src/' directory"


class TestCodeStyle:
    """Test MCP-specific code style requirements."""

    def test_code_style_exists(self, settings_data):
        """FAIL: Settings should have code_style section"""
        assert "code_style" in settings_data, "Missing code_style section"

    def test_async_preferred(self, settings_data):
        """FAIL: async_preferred should be true for MCP"""
        code_style = settings_data.get("code_style", {})
        assert code_style.get("async_preferred") is True, \
            "FastMCP requires async_preferred: true"

    def test_type_hints_required(self, settings_data):
        """FAIL: type_hints should be 'required' for MCP protocol compliance"""
        code_style = settings_data.get("code_style", {})
        assert code_style.get("type_hints") == "required", \
            "FastMCP requires type_hints: required"

    def test_logging_target_stderr(self, settings_data):
        """FAIL: logging_target MUST be 'stderr' (CRITICAL for MCP - stdout is reserved)"""
        code_style = settings_data.get("code_style", {})
        assert code_style.get("logging_target") == "stderr", \
            "CRITICAL: logging_target must be 'stderr' for MCP (stdout reserved for protocol)"


class TestTesting:
    """Test testing framework configuration."""

    def test_testing_section_exists(self, settings_data):
        """FAIL: Settings should have testing section"""
        assert "testing" in settings_data, "Missing testing section"

    def test_framework_is_pytest(self, settings_data):
        """FAIL: Testing framework should be pytest"""
        testing = settings_data.get("testing", {})
        assert testing.get("framework") == "pytest", \
            "Testing framework should be 'pytest'"

    def test_async_support_pytest_asyncio(self, settings_data):
        """FAIL: Async support should use pytest-asyncio"""
        testing = settings_data.get("testing", {})
        assert testing.get("async_support") == "pytest-asyncio", \
            "Async support should be 'pytest-asyncio'"

    def test_protocol_testing_enabled(self, settings_data):
        """FAIL: protocol_testing should be true for MCP"""
        testing = settings_data.get("testing", {})
        assert testing.get("protocol_testing") is True, \
            "FastMCP requires protocol_testing: true"


class TestMCPSpecific:
    """Test MCP-specific configuration section."""

    def test_mcp_specific_section_exists(self, settings_data):
        """FAIL: Settings should have mcp_specific section"""
        assert "mcp_specific" in settings_data, "Missing mcp_specific section"

    def test_stdout_reserved(self, settings_data):
        """FAIL: stdout_reserved should be true (critical MCP requirement)"""
        mcp = settings_data.get("mcp_specific", {})
        assert mcp.get("stdout_reserved") is True, \
            "stdout_reserved must be true for MCP protocol compliance"

    def test_parameter_types_all_strings(self, settings_data):
        """FAIL: parameter_types should be 'all_strings' for MCP"""
        mcp = settings_data.get("mcp_specific", {})
        assert mcp.get("parameter_types") == "all_strings", \
            "parameter_types should be 'all_strings' for MCP protocol"


class TestCompleteness:
    """Test overall configuration completeness."""

    def test_has_all_required_sections(self, settings_data):
        """FAIL: Settings should have all required top-level sections"""
        required_sections = [
            "schema_version",
            "naming_conventions",
            "file_organization",
            "layer_mappings",
            "code_style",
            "testing",
            "mcp_specific"
        ]

        for section in required_sections:
            assert section in settings_data, f"Missing required section: {section}"

    def test_naming_conventions_complete(self, settings_data):
        """FAIL: naming_conventions should have all MCP-specific entries"""
        required_conventions = ["tool", "server", "resource", "test_file", "test_function"]
        naming = settings_data.get("naming_conventions", {})

        for convention in required_conventions:
            assert convention in naming, f"Missing naming convention: {convention}"

    def test_layer_mappings_complete(self, settings_data):
        """FAIL: layer_mappings should have all MCP-specific layers"""
        required_layers = ["tools", "resources", "server"]
        layers = settings_data.get("layer_mappings", {})

        for layer in required_layers:
            assert layer in layers, f"Missing layer mapping: {layer}"
