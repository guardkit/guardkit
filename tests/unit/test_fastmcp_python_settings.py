"""
Tests for fastmcp-python template settings.json

TDD RED PHASE: These tests should FAIL until settings.json is created.
"""

import json
from pathlib import Path

import pytest


# Fixture to get the settings file path
@pytest.fixture
def settings_path() -> Path:
    """Return path to fastmcp-python settings.json"""
    return Path(__file__).parent.parent.parent / "installer" / "core" / "templates" / "fastmcp-python" / "settings.json"


@pytest.fixture
def settings_data(settings_path: Path) -> dict:
    """Load and parse settings.json"""
    if not settings_path.exists():
        pytest.skip(f"Settings file not found: {settings_path}")
    with open(settings_path) as f:
        return json.load(f)


class TestSettingsFileExists:
    """Test that settings file exists at correct location."""

    def test_settings_file_exists(self, settings_path: Path):
        """File must exist at installer/core/templates/fastmcp-python/settings.json"""
        assert settings_path.exists(), f"Settings file not found at {settings_path}"

    def test_settings_is_file(self, settings_path: Path):
        """Must be a file, not a directory"""
        assert settings_path.is_file(), f"{settings_path} is not a file"


class TestJSONStructure:
    """Test JSON validity and schema version."""

    def test_valid_json(self, settings_path: Path):
        """File must be valid JSON"""
        with open(settings_path) as f:
            data = json.load(f)
        assert isinstance(data, dict), "Settings must be a JSON object"

    def test_schema_version_exists(self, settings_data: dict):
        """Must have schema_version field"""
        assert "schema_version" in settings_data, "Missing schema_version field"

    def test_schema_version_value(self, settings_data: dict):
        """schema_version must be '1.0.0'"""
        assert settings_data["schema_version"] == "1.0.0", \
            f"Expected schema_version '1.0.0', got '{settings_data.get('schema_version')}'"


class TestNamingConventions:
    """Test naming conventions section for MCP-specific patterns."""

    def test_naming_conventions_exists(self, settings_data: dict):
        """Must have naming_conventions section"""
        assert "naming_conventions" in settings_data, "Missing naming_conventions section"

    def test_tool_convention(self, settings_data: dict):
        """tool must use snake_case"""
        nc = settings_data["naming_conventions"]
        assert "tool" in nc, "Missing 'tool' naming convention"
        assert nc["tool"]["case_style"] == "snake_case", \
            f"tool case_style must be 'snake_case', got '{nc['tool'].get('case_style')}'"

    def test_server_convention(self, settings_data: dict):
        """server must use kebab-case"""
        nc = settings_data["naming_conventions"]
        assert "server" in nc, "Missing 'server' naming convention"
        assert nc["server"]["case_style"] == "kebab-case", \
            f"server case_style must be 'kebab-case', got '{nc['server'].get('case_style')}'"

    def test_resource_convention(self, settings_data: dict):
        """resource must use snake_case"""
        nc = settings_data["naming_conventions"]
        assert "resource" in nc, "Missing 'resource' naming convention"
        assert nc["resource"]["case_style"] == "snake_case", \
            f"resource case_style must be 'snake_case', got '{nc['resource'].get('case_style')}'"

    def test_test_file_convention(self, settings_data: dict):
        """test_file must have pattern test_{{feature}}.py"""
        nc = settings_data["naming_conventions"]
        assert "test_file" in nc, "Missing 'test_file' naming convention"
        assert nc["test_file"]["pattern"] == "test_{{feature}}.py", \
            f"test_file pattern must be 'test_{{{{feature}}}}.py', got '{nc['test_file'].get('pattern')}'"

    def test_test_function_convention(self, settings_data: dict):
        """test_function must have pattern test_{{action}}_{{entity}}"""
        nc = settings_data["naming_conventions"]
        assert "test_function" in nc, "Missing 'test_function' naming convention"
        assert nc["test_function"]["pattern"] == "test_{{action}}_{{entity}}", \
            f"test_function pattern must be 'test_{{{{action}}}}_{{{{entity}}}}', got '{nc['test_function'].get('pattern')}'"

    def test_mcp_parameter_convention(self, settings_data: dict):
        """mcp_parameter must use camelCase per MCP protocol spec"""
        nc = settings_data["naming_conventions"]
        assert "mcp_parameter" in nc, "Missing 'mcp_parameter' naming convention"
        assert nc["mcp_parameter"]["case_style"] == "camelCase", \
            f"mcp_parameter case_style must be 'camelCase', got '{nc['mcp_parameter'].get('case_style')}'"


class TestFileOrganization:
    """Test file organization section for MCP flat structure."""

    def test_file_organization_exists(self, settings_data: dict):
        """Must have file_organization section"""
        assert "file_organization" in settings_data, "Missing file_organization section"

    def test_by_feature_false(self, settings_data: dict):
        """by_feature must be false for MCP's flat structure"""
        fo = settings_data["file_organization"]
        assert "by_feature" in fo, "Missing 'by_feature' field"
        assert fo["by_feature"] is False, \
            f"by_feature must be false for MCP, got {fo['by_feature']}"

    def test_test_location_separate(self, settings_data: dict):
        """test_location must be 'separate'"""
        fo = settings_data["file_organization"]
        assert "test_location" in fo, "Missing 'test_location' field"
        assert fo["test_location"] == "separate", \
            f"test_location must be 'separate', got '{fo.get('test_location')}'"


class TestLayerMappings:
    """Test layer mappings for MCP server structure."""

    def test_layer_mappings_exists(self, settings_data: dict):
        """Must have layer_mappings section"""
        assert "layer_mappings" in settings_data, "Missing layer_mappings section"

    def test_tools_layer(self, settings_data: dict):
        """tools layer must map to src/tools/"""
        lm = settings_data["layer_mappings"]
        assert "tools" in lm, "Missing 'tools' layer mapping"
        assert lm["tools"]["directory"] == "src/tools/", \
            f"tools directory must be 'src/tools/', got '{lm['tools'].get('directory')}'"

    def test_resources_layer(self, settings_data: dict):
        """resources layer must map to src/resources/"""
        lm = settings_data["layer_mappings"]
        assert "resources" in lm, "Missing 'resources' layer mapping"
        assert lm["resources"]["directory"] == "src/resources/", \
            f"resources directory must be 'src/resources/', got '{lm['resources'].get('directory')}'"

    def test_server_layer(self, settings_data: dict):
        """server layer must map to src/"""
        lm = settings_data["layer_mappings"]
        assert "server" in lm, "Missing 'server' layer mapping"
        assert lm["server"]["directory"] == "src/", \
            f"server directory must be 'src/', got '{lm['server'].get('directory')}'"


class TestCodeStyle:
    """Test code style section for MCP-specific requirements."""

    def test_code_style_exists(self, settings_data: dict):
        """Must have code_style section"""
        assert "code_style" in settings_data, "Missing code_style section"

    def test_async_preferred(self, settings_data: dict):
        """async_preferred must be true"""
        cs = settings_data["code_style"]
        assert "async_preferred" in cs, "Missing 'async_preferred' field"
        assert cs["async_preferred"] is True, \
            f"async_preferred must be true, got {cs['async_preferred']}"

    def test_type_hints_required(self, settings_data: dict):
        """type_hints must be 'required'"""
        cs = settings_data["code_style"]
        assert "type_hints" in cs, "Missing 'type_hints' field"
        assert cs["type_hints"] == "required", \
            f"type_hints must be 'required', got '{cs.get('type_hints')}'"

    def test_logging_target_stderr(self, settings_data: dict):
        """CRITICAL: logging_target must be 'stderr' - stdout reserved for MCP protocol"""
        cs = settings_data["code_style"]
        assert "logging_target" in cs, "Missing 'logging_target' field - CRITICAL for MCP!"
        assert cs["logging_target"] == "stderr", \
            f"logging_target MUST be 'stderr' (stdout reserved for MCP protocol), got '{cs.get('logging_target')}'"


class TestTestingSection:
    """Test testing configuration section."""

    def test_testing_exists(self, settings_data: dict):
        """Must have testing section"""
        assert "testing" in settings_data, "Missing testing section"

    def test_framework_pytest(self, settings_data: dict):
        """framework must be 'pytest'"""
        ts = settings_data["testing"]
        assert "framework" in ts, "Missing 'framework' field"
        assert ts["framework"] == "pytest", \
            f"framework must be 'pytest', got '{ts.get('framework')}'"

    def test_async_support(self, settings_data: dict):
        """async_support must be 'pytest-asyncio'"""
        ts = settings_data["testing"]
        assert "async_support" in ts, "Missing 'async_support' field"
        assert ts["async_support"] == "pytest-asyncio", \
            f"async_support must be 'pytest-asyncio', got '{ts.get('async_support')}'"

    def test_protocol_testing(self, settings_data: dict):
        """protocol_testing must be true"""
        ts = settings_data["testing"]
        assert "protocol_testing" in ts, "Missing 'protocol_testing' field"
        assert ts["protocol_testing"] is True, \
            f"protocol_testing must be true, got {ts['protocol_testing']}"


class TestMCPSpecific:
    """Test MCP-specific configuration section."""

    def test_mcp_specific_exists(self, settings_data: dict):
        """Must have mcp_specific section"""
        assert "mcp_specific" in settings_data, "Missing mcp_specific section"

    def test_stdout_reserved(self, settings_data: dict):
        """stdout_reserved must be true"""
        mcp = settings_data["mcp_specific"]
        assert "stdout_reserved" in mcp, "Missing 'stdout_reserved' field"
        assert mcp["stdout_reserved"] is True, \
            f"stdout_reserved must be true, got {mcp['stdout_reserved']}"

    def test_parameter_types(self, settings_data: dict):
        """parameter_types must be 'all_strings' per MCP protocol"""
        mcp = settings_data["mcp_specific"]
        assert "parameter_types" in mcp, "Missing 'parameter_types' field"
        assert mcp["parameter_types"] == "all_strings", \
            f"parameter_types must be 'all_strings', got '{mcp.get('parameter_types')}'"

    def test_path_format(self, settings_data: dict):
        """path_format must be 'absolute'"""
        mcp = settings_data["mcp_specific"]
        assert "path_format" in mcp, "Missing 'path_format' field"
        assert mcp["path_format"] == "absolute", \
            f"path_format must be 'absolute', got '{mcp.get('path_format')}'"

    def test_logging_target_in_mcp_specific(self, settings_data: dict):
        """logging_target must be 'stderr' in mcp_specific section too"""
        mcp = settings_data["mcp_specific"]
        assert "logging_target" in mcp, "Missing 'logging_target' in mcp_specific"
        assert mcp["logging_target"] == "stderr", \
            f"logging_target must be 'stderr', got '{mcp.get('logging_target')}'"


class TestCompleteness:
    """Test that all required sections and fields are present."""

    def test_all_required_sections_present(self, settings_data: dict):
        """All required top-level sections must be present"""
        required_sections = [
            "schema_version",
            "naming_conventions",
            "file_organization",
            "layer_mappings",
            "code_style",
            "testing",
            "mcp_specific",
        ]
        missing = [s for s in required_sections if s not in settings_data]
        assert not missing, f"Missing required sections: {missing}"

    def test_all_naming_conventions_complete(self, settings_data: dict):
        """All required naming conventions must be present"""
        required_conventions = ["tool", "server", "resource", "test_file", "test_function", "mcp_parameter"]
        nc = settings_data.get("naming_conventions", {})
        missing = [c for c in required_conventions if c not in nc]
        assert not missing, f"Missing naming conventions: {missing}"

    def test_all_layer_mappings_complete(self, settings_data: dict):
        """All required layer mappings must be present"""
        required_layers = ["tools", "resources", "server"]
        lm = settings_data.get("layer_mappings", {})
        missing = [l for l in required_layers if l not in lm]
        assert not missing, f"Missing layer mappings: {missing}"
