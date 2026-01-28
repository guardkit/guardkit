"""
TDD RED PHASE: Tests for fastmcp-python template manifest.json

These tests will FAIL initially because the manifest.json does not exist yet.
They define the expected structure and content for the fastmcp-python template.

Reference: installer/core/templates/fastapi-python/manifest.json
Task: TASK-FMT-001 - Create manifest.json for fastmcp-python template
"""

import json
import pytest
from pathlib import Path


# Path to the manifest file (does not exist yet - will fail)
MANIFEST_PATH = Path(__file__).parent.parent.parent / "installer" / "core" / "templates" / "fastmcp-python" / "manifest.json"


class TestManifestFileExists:
    """Test that the manifest.json file exists at the correct location."""

    def test_manifest_file_exists(self):
        """Test manifest.json exists at expected path."""
        assert MANIFEST_PATH.exists(), f"Manifest file not found at {MANIFEST_PATH}"

    def test_manifest_is_file(self):
        """Test that manifest path points to a file, not a directory."""
        assert MANIFEST_PATH.is_file(), f"Manifest path exists but is not a file: {MANIFEST_PATH}"


class TestManifestJsonStructure:
    """Test the JSON structure and validity of manifest.json."""

    @pytest.fixture
    def manifest_data(self):
        """Load manifest JSON data."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    def test_valid_json(self):
        """Test that manifest.json is valid JSON."""
        try:
            with open(MANIFEST_PATH, 'r') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Manifest is not valid JSON: {e}")

    def test_is_dict(self, manifest_data):
        """Test that manifest root is a dictionary."""
        assert isinstance(manifest_data, dict), "Manifest root should be a dictionary"


class TestManifestSchemaVersion:
    """Test schema_version field."""

    @pytest.fixture
    def manifest_data(self):
        """Load manifest JSON data."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    def test_schema_version_exists(self, manifest_data):
        """Test that schema_version field exists."""
        assert "schema_version" in manifest_data, "schema_version field is required"

    def test_schema_version_is_1_0_0(self, manifest_data):
        """Test that schema_version is '1.0.0'."""
        assert manifest_data["schema_version"] == "1.0.0", \
            f"Expected schema_version '1.0.0', got '{manifest_data.get('schema_version')}'"


class TestManifestBasicFields:
    """Test basic required fields in manifest."""

    @pytest.fixture
    def manifest_data(self):
        """Load manifest JSON data."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    def test_name_field(self, manifest_data):
        """Test that name is 'fastmcp-python'."""
        assert manifest_data.get("name") == "fastmcp-python", \
            f"Expected name 'fastmcp-python', got '{manifest_data.get('name')}'"

    def test_display_name_field(self, manifest_data):
        """Test that display_name is 'FastMCP Python Server'."""
        assert manifest_data.get("display_name") == "FastMCP Python Server", \
            f"Expected display_name 'FastMCP Python Server', got '{manifest_data.get('display_name')}'"

    def test_description_field(self, manifest_data):
        """Test that description field exists and is not empty."""
        assert "description" in manifest_data, "description field is required"
        assert isinstance(manifest_data["description"], str), "description must be a string"
        assert len(manifest_data["description"]) > 0, "description cannot be empty"
        assert "FastMCP" in manifest_data["description"], "description should mention FastMCP"

    def test_language_field(self, manifest_data):
        """Test that language is 'Python'."""
        assert manifest_data.get("language") == "Python", \
            f"Expected language 'Python', got '{manifest_data.get('language')}'"

    def test_language_version_field(self, manifest_data):
        """Test that language_version is '>=3.10'."""
        assert manifest_data.get("language_version") == ">=3.10", \
            f"Expected language_version '>=3.10', got '{manifest_data.get('language_version')}'"


class TestManifestFrameworks:
    """Test frameworks array in manifest."""

    @pytest.fixture
    def manifest_data(self):
        """Load manifest JSON data."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    def test_frameworks_exists(self, manifest_data):
        """Test that frameworks field exists."""
        assert "frameworks" in manifest_data, "frameworks field is required"

    def test_frameworks_is_list(self, manifest_data):
        """Test that frameworks is a list."""
        assert isinstance(manifest_data["frameworks"], list), "frameworks must be a list"

    def test_frameworks_not_empty(self, manifest_data):
        """Test that frameworks list is not empty."""
        assert len(manifest_data["frameworks"]) > 0, "frameworks list cannot be empty"

    def test_fastmcp_in_frameworks(self, manifest_data):
        """Test that FastMCP is in frameworks list."""
        framework_names = [f["name"] for f in manifest_data["frameworks"]]
        assert "FastMCP" in framework_names or "fastmcp" in framework_names, \
            f"FastMCP not found in frameworks: {framework_names}"

    def test_mcp_in_frameworks(self, manifest_data):
        """Test that mcp is in frameworks list."""
        framework_names = [f["name"] for f in manifest_data["frameworks"]]
        assert "mcp" in framework_names, f"mcp not found in frameworks: {framework_names}"

    def test_pytest_in_frameworks(self, manifest_data):
        """Test that pytest is in frameworks list."""
        framework_names = [f["name"] for f in manifest_data["frameworks"]]
        assert "pytest" in framework_names, f"pytest not found in frameworks: {framework_names}"

    def test_pytest_asyncio_in_frameworks(self, manifest_data):
        """Test that pytest-asyncio is in frameworks list."""
        framework_names = [f["name"] for f in manifest_data["frameworks"]]
        assert "pytest-asyncio" in framework_names, \
            f"pytest-asyncio not found in frameworks: {framework_names}"

    def test_framework_structure(self, manifest_data):
        """Test that each framework has required fields."""
        for framework in manifest_data["frameworks"]:
            assert "name" in framework, "Each framework must have 'name' field"
            assert "version" in framework, "Each framework must have 'version' field"
            assert "purpose" in framework, "Each framework must have 'purpose' field"


class TestManifestPatterns:
    """Test patterns array in manifest."""

    @pytest.fixture
    def manifest_data(self):
        """Load manifest JSON data."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    def test_patterns_exists(self, manifest_data):
        """Test that patterns field exists."""
        assert "patterns" in manifest_data, "patterns field is required"

    def test_patterns_is_list(self, manifest_data):
        """Test that patterns is a list."""
        assert isinstance(manifest_data["patterns"], list), "patterns must be a list"

    def test_patterns_count(self, manifest_data):
        """Test that patterns has approximately 10 critical MCP patterns."""
        assert len(manifest_data["patterns"]) >= 8, \
            f"Expected at least 8 patterns, got {len(manifest_data['patterns'])}"

    def test_patterns_are_strings(self, manifest_data):
        """Test that all patterns are strings."""
        for pattern in manifest_data["patterns"]:
            assert isinstance(pattern, str), f"Pattern must be string, got {type(pattern)}: {pattern}"

    def test_key_mcp_patterns_present(self, manifest_data):
        """Test that key MCP patterns are present."""
        patterns = manifest_data["patterns"]
        patterns_lower = [p.lower() for p in patterns]

        # Check for key MCP concepts (case-insensitive)
        expected_concepts = [
            "tool",      # Tool registration/implementation
            "resource",  # Resource management
            "async",     # Async patterns
        ]

        for concept in expected_concepts:
            assert any(concept in p for p in patterns_lower), \
                f"Expected pattern containing '{concept}' not found in: {patterns}"


class TestManifestPlaceholders:
    """Test placeholders in manifest."""

    @pytest.fixture
    def manifest_data(self):
        """Load manifest JSON data."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    def test_placeholders_exists(self, manifest_data):
        """Test that placeholders field exists."""
        assert "placeholders" in manifest_data, "placeholders field is required"

    def test_placeholders_is_dict(self, manifest_data):
        """Test that placeholders is a dictionary."""
        assert isinstance(manifest_data["placeholders"], dict), "placeholders must be a dictionary"

    def test_server_name_placeholder(self, manifest_data):
        """Test that ServerName placeholder exists."""
        assert "ServerName" in manifest_data["placeholders"], \
            "ServerName placeholder is required for MCP server templates"

    def test_tool_name_placeholder(self, manifest_data):
        """Test that ToolName placeholder exists."""
        assert "ToolName" in manifest_data["placeholders"], \
            "ToolName placeholder is required for MCP tool development"

    def test_resource_name_placeholder(self, manifest_data):
        """Test that ResourceName placeholder exists."""
        assert "ResourceName" in manifest_data["placeholders"], \
            "ResourceName placeholder is required for MCP resource development"

    def test_description_placeholder(self, manifest_data):
        """Test that Description placeholder exists."""
        assert "Description" in manifest_data["placeholders"], \
            "Description placeholder is required"

    def test_placeholder_structure(self, manifest_data):
        """Test that each placeholder has required fields."""
        for key, placeholder in manifest_data["placeholders"].items():
            assert "name" in placeholder, f"Placeholder {key} must have 'name' field"
            assert "description" in placeholder, f"Placeholder {key} must have 'description' field"
            assert "required" in placeholder, f"Placeholder {key} must have 'required' field"


class TestManifestTags:
    """Test tags array in manifest."""

    @pytest.fixture
    def manifest_data(self):
        """Load manifest JSON data."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    def test_tags_exists(self, manifest_data):
        """Test that tags field exists."""
        assert "tags" in manifest_data, "tags field is required"

    def test_tags_is_list(self, manifest_data):
        """Test that tags is a list."""
        assert isinstance(manifest_data["tags"], list), "tags must be a list"

    def test_python_tag(self, manifest_data):
        """Test that 'python' tag is present."""
        assert "python" in manifest_data["tags"], \
            f"'python' tag missing from: {manifest_data['tags']}"

    def test_mcp_tag(self, manifest_data):
        """Test that 'mcp' tag is present."""
        assert "mcp" in manifest_data["tags"], \
            f"'mcp' tag missing from: {manifest_data['tags']}"

    def test_fastmcp_tag(self, manifest_data):
        """Test that 'fastmcp' tag is present."""
        assert "fastmcp" in manifest_data["tags"], \
            f"'fastmcp' tag missing from: {manifest_data['tags']}"

    def test_claude_code_tag(self, manifest_data):
        """Test that 'claude-code' tag is present."""
        assert "claude-code" in manifest_data["tags"], \
            f"'claude-code' tag missing from: {manifest_data['tags']}"

    def test_async_tag(self, manifest_data):
        """Test that 'async' tag is present."""
        assert "async" in manifest_data["tags"], \
            f"'async' tag missing from: {manifest_data['tags']}"


class TestManifestCategory:
    """Test category field in manifest."""

    @pytest.fixture
    def manifest_data(self):
        """Load manifest JSON data."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    def test_category_exists(self, manifest_data):
        """Test that category field exists."""
        assert "category" in manifest_data, "category field is required"

    def test_category_is_integration(self, manifest_data):
        """Test that category is 'integration'."""
        assert manifest_data["category"] == "integration", \
            f"Expected category 'integration', got '{manifest_data.get('category')}'"


class TestManifestComplexity:
    """Test complexity score in manifest."""

    @pytest.fixture
    def manifest_data(self):
        """Load manifest JSON data."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    def test_complexity_exists(self, manifest_data):
        """Test that complexity field exists."""
        assert "complexity" in manifest_data, "complexity field is required"

    def test_complexity_is_integer(self, manifest_data):
        """Test that complexity is an integer."""
        assert isinstance(manifest_data["complexity"], int), \
            f"complexity must be integer, got {type(manifest_data['complexity'])}"

    def test_complexity_is_5(self, manifest_data):
        """Test that complexity is 5."""
        assert manifest_data["complexity"] == 5, \
            f"Expected complexity 5, got {manifest_data.get('complexity')}"

    def test_complexity_in_range(self, manifest_data):
        """Test that complexity is in valid range 1-10."""
        complexity = manifest_data["complexity"]
        assert 1 <= complexity <= 10, \
            f"complexity must be between 1-10, got {complexity}"


class TestManifestQualityScores:
    """Test quality_scores in manifest."""

    @pytest.fixture
    def manifest_data(self):
        """Load manifest JSON data."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    def test_quality_scores_exists(self, manifest_data):
        """Test that quality_scores field exists."""
        assert "quality_scores" in manifest_data, "quality_scores field is required"

    def test_quality_scores_is_dict(self, manifest_data):
        """Test that quality_scores is a dictionary."""
        assert isinstance(manifest_data["quality_scores"], dict), \
            "quality_scores must be a dictionary"

    def test_solid_compliance_exists(self, manifest_data):
        """Test that solid_compliance field exists."""
        assert "solid_compliance" in manifest_data["quality_scores"], \
            "solid_compliance is required in quality_scores"

    def test_solid_compliance_value(self, manifest_data):
        """Test that solid_compliance is >= 85."""
        solid = manifest_data["quality_scores"]["solid_compliance"]
        assert solid >= 85, \
            f"Expected solid_compliance >= 85, got {solid}"

    def test_dry_compliance_exists(self, manifest_data):
        """Test that dry_compliance field exists."""
        assert "dry_compliance" in manifest_data["quality_scores"], \
            "dry_compliance is required in quality_scores"

    def test_dry_compliance_value(self, manifest_data):
        """Test that dry_compliance is >= 85."""
        dry = manifest_data["quality_scores"]["dry_compliance"]
        assert dry >= 85, \
            f"Expected dry_compliance >= 85, got {dry}"

    def test_yagni_compliance_exists(self, manifest_data):
        """Test that yagni_compliance field exists."""
        assert "yagni_compliance" in manifest_data["quality_scores"], \
            "yagni_compliance is required in quality_scores"

    def test_yagni_compliance_value(self, manifest_data):
        """Test that yagni_compliance is >= 90."""
        yagni = manifest_data["quality_scores"]["yagni_compliance"]
        assert yagni >= 90, \
            f"Expected yagni_compliance >= 90, got {yagni}"

    def test_quality_scores_in_range(self, manifest_data):
        """Test that all quality scores are in valid range 0-100."""
        for key, value in manifest_data["quality_scores"].items():
            assert 0 <= value <= 100, \
                f"quality_scores.{key} must be 0-100, got {value}"


# Summary of what we're testing:
# 1. File existence and structure (2 tests)
# 2. JSON validity (2 tests)
# 3. schema_version = "1.0.0" (2 tests)
# 4. Basic fields: name, display_name, description, language, language_version (5 tests)
# 5. Frameworks array with FastMCP, mcp, pytest, pytest-asyncio (8 tests)
# 6. Patterns array with ~10 MCP patterns (5 tests)
# 7. Placeholders: ServerName, ToolName, ResourceName, Description (6 tests)
# 8. Tags: python, mcp, fastmcp, claude-code, async (6 tests)
# 9. Category = "integration" (2 tests)
# 10. Complexity = 5 (4 tests)
# 11. Quality scores: SOLID >= 85, DRY >= 85, YAGNI >= 90 (7 tests)
#
# Total: 49 tests
# All will FAIL initially because manifest.json doesn't exist.
