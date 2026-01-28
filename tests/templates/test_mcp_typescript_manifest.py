"""
TDD RED Phase: Tests for mcp-typescript template manifest.json

These tests validate the manifest.json structure and content.
Initially FAIL because manifest.json does not exist yet.
"""

import json
import pytest
from pathlib import Path


# Path to the manifest file
MANIFEST_PATH = Path(__file__).parent.parent.parent / "installer/core/templates/mcp-typescript/manifest.json"


class TestManifestExists:
    """Test that the manifest.json file exists in the correct location."""

    def test_manifest_file_exists(self):
        """Verify manifest.json exists at the expected path."""
        assert MANIFEST_PATH.exists(), f"manifest.json not found at {MANIFEST_PATH}"


class TestManifestStructure:
    """Test the basic structure and required fields of manifest.json."""

    @pytest.fixture
    def manifest_data(self):
        """Load and parse the manifest.json file."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    def test_valid_json_format(self, manifest_data):
        """Verify manifest.json is valid JSON."""
        assert isinstance(manifest_data, dict), "Manifest must be a JSON object"

    def test_schema_version(self, manifest_data):
        """Verify schema_version is 1.0.0."""
        assert manifest_data.get("schema_version") == "1.0.0", "schema_version must be 1.0.0"

    def test_name_field(self, manifest_data):
        """Verify name is 'mcp-typescript'."""
        assert manifest_data.get("name") == "mcp-typescript", "name must be 'mcp-typescript'"

    def test_display_name_field(self, manifest_data):
        """Verify display_name is 'MCP TypeScript Server'."""
        assert manifest_data.get("display_name") == "MCP TypeScript Server", \
            "display_name must be 'MCP TypeScript Server'"

    def test_description_field(self, manifest_data):
        """Verify description exists and mentions critical patterns."""
        description = manifest_data.get("description", "")
        assert len(description) > 50, "description must be comprehensive"
        assert "MCP" in description or "Model Context Protocol" in description, \
            "description must mention MCP"

    def test_language_field(self, manifest_data):
        """Verify language is 'TypeScript'."""
        assert manifest_data.get("language") == "TypeScript", "language must be 'TypeScript'"

    def test_language_version_field(self, manifest_data):
        """Verify language_version is '5.0+' or higher."""
        version = manifest_data.get("language_version")
        assert version is not None, "language_version must be specified"
        assert "5.0" in version or "5." in version, "language_version must be 5.0 or higher"

    def test_category_field(self, manifest_data):
        """Verify category is 'integration'."""
        assert manifest_data.get("category") == "integration", "category must be 'integration'"

    def test_complexity_field(self, manifest_data):
        """Verify complexity is set to 5."""
        assert manifest_data.get("complexity") == 5, "complexity must be 5"


class TestFrameworks:
    """Test the frameworks array contains all required frameworks."""

    @pytest.fixture
    def manifest_data(self):
        """Load and parse the manifest.json file."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    @pytest.fixture
    def frameworks(self, manifest_data):
        """Extract frameworks array."""
        return manifest_data.get("frameworks", [])

    def test_frameworks_is_array(self, frameworks):
        """Verify frameworks is an array."""
        assert isinstance(frameworks, list), "frameworks must be an array"

    def test_frameworks_not_empty(self, frameworks):
        """Verify frameworks array is not empty."""
        assert len(frameworks) > 0, "frameworks array must not be empty"

    def test_mcp_sdk_framework(self, frameworks):
        """Verify @modelcontextprotocol/sdk is included."""
        framework_names = [f.get("name") for f in frameworks]
        assert "@modelcontextprotocol/sdk" in framework_names, \
            "@modelcontextprotocol/sdk must be in frameworks"

        # Verify purpose
        mcp_sdk = next(f for f in frameworks if f.get("name") == "@modelcontextprotocol/sdk")
        assert "mcp_server" in mcp_sdk.get("purpose", "").lower() or \
               "mcp server" in mcp_sdk.get("purpose", "").lower(), \
            "@modelcontextprotocol/sdk purpose must mention MCP server"

    def test_zod_framework(self, frameworks):
        """Verify Zod is included for validation."""
        framework_names = [f.get("name") for f in frameworks]
        assert "zod" in framework_names, "Zod must be in frameworks"

        # Verify purpose
        zod = next(f for f in frameworks if f.get("name") == "zod")
        assert "validation" in zod.get("purpose", "").lower(), \
            "Zod purpose must mention validation"

    def test_vitest_framework(self, frameworks):
        """Verify Vitest is included for testing."""
        framework_names = [f.get("name") for f in frameworks]
        assert "vitest" in framework_names, "Vitest must be in frameworks"

        # Verify purpose
        vitest = next(f for f in frameworks if f.get("name") == "vitest")
        assert "test" in vitest.get("purpose", "").lower(), \
            "Vitest purpose must mention testing"

    def test_tsx_framework(self, frameworks):
        """Verify tsx is included for development."""
        framework_names = [f.get("name") for f in frameworks]
        assert "tsx" in framework_names, "tsx must be in frameworks"

        # Verify purpose
        tsx = next(f for f in frameworks if f.get("name") == "tsx")
        assert "development" in tsx.get("purpose", "").lower() or \
               "dev" in tsx.get("purpose", "").lower(), \
            "tsx purpose must mention development"

    def test_esbuild_framework(self, frameworks):
        """Verify esbuild is included for build."""
        framework_names = [f.get("name") for f in frameworks]
        assert "esbuild" in framework_names, "esbuild must be in frameworks"

        # Verify purpose
        esbuild = next(f for f in frameworks if f.get("name") == "esbuild")
        assert "build" in esbuild.get("purpose", "").lower(), \
            "esbuild purpose must mention build"


class TestPatterns:
    """Test the patterns array contains expected MCP patterns."""

    @pytest.fixture
    def manifest_data(self):
        """Load and parse the manifest.json file."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    @pytest.fixture
    def patterns(self, manifest_data):
        """Extract patterns array."""
        return manifest_data.get("patterns", [])

    def test_patterns_is_array(self, patterns):
        """Verify patterns is an array."""
        assert isinstance(patterns, list), "patterns must be an array"

    def test_patterns_not_empty(self, patterns):
        """Verify patterns array is not empty."""
        assert len(patterns) > 0, "patterns array must not be empty"

    def test_patterns_include_mcp_specific(self, patterns):
        """Verify patterns include MCP-specific patterns."""
        pattern_lower = [p.lower() for p in patterns]

        # Check for key MCP patterns
        has_mcp_pattern = any(
            "mcp" in p or
            "tool" in p or
            "resource" in p or
            "prompt" in p or
            "server" in p
            for p in pattern_lower
        )
        assert has_mcp_pattern, "patterns must include MCP-specific patterns"


class TestPlaceholders:
    """Test the placeholders object has required structure."""

    @pytest.fixture
    def manifest_data(self):
        """Load and parse the manifest.json file."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    @pytest.fixture
    def placeholders(self, manifest_data):
        """Extract placeholders object."""
        return manifest_data.get("placeholders", {})

    def test_placeholders_is_object(self, placeholders):
        """Verify placeholders is an object."""
        assert isinstance(placeholders, dict), "placeholders must be an object"

    def test_placeholders_not_empty(self, placeholders):
        """Verify placeholders object is not empty."""
        assert len(placeholders) > 0, "placeholders must not be empty"

    def test_servername_placeholder(self, placeholders):
        """Verify ServerName placeholder exists."""
        assert "ServerName" in placeholders, "ServerName placeholder must be defined"

    def test_toolname_placeholder(self, placeholders):
        """Verify ToolName placeholder exists."""
        assert "ToolName" in placeholders, "ToolName placeholder must be defined"

    def test_resourcename_placeholder(self, placeholders):
        """Verify ResourceName placeholder exists."""
        assert "ResourceName" in placeholders, "ResourceName placeholder must be defined"

    def test_description_placeholder(self, placeholders):
        """Verify Description placeholder exists."""
        assert "Description" in placeholders, "Description placeholder must be defined"


class TestTags:
    """Test the tags array contains required values."""

    @pytest.fixture
    def manifest_data(self):
        """Load and parse the manifest.json file."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    @pytest.fixture
    def tags(self, manifest_data):
        """Extract tags array."""
        return manifest_data.get("tags", [])

    def test_tags_is_array(self, tags):
        """Verify tags is an array."""
        assert isinstance(tags, list), "tags must be an array"

    def test_tags_not_empty(self, tags):
        """Verify tags array is not empty."""
        assert len(tags) > 0, "tags array must not be empty"

    def test_required_tags_present(self, tags):
        """Verify all required tags are present."""
        tags_lower = [t.lower() for t in tags]

        required_tags = ["typescript", "mcp", "model-context-protocol", "claude-code", "zod"]
        for required_tag in required_tags:
            assert required_tag in tags_lower, f"Tag '{required_tag}' must be present in tags"


class TestQualityScores:
    """Test quality scores are defined."""

    @pytest.fixture
    def manifest_data(self):
        """Load and parse the manifest.json file."""
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)

    def test_quality_scores_exist(self, manifest_data):
        """Verify quality_scores object exists."""
        assert "quality_scores" in manifest_data, "quality_scores must be defined"

    def test_quality_scores_is_object(self, manifest_data):
        """Verify quality_scores is an object."""
        quality_scores = manifest_data.get("quality_scores", {})
        assert isinstance(quality_scores, dict), "quality_scores must be an object"

    def test_solid_score_defined(self, manifest_data):
        """Verify SOLID score is defined with target 85."""
        quality_scores = manifest_data.get("quality_scores", {})
        assert "SOLID" in quality_scores, "SOLID score must be defined"
        assert quality_scores["SOLID"] == 85, "SOLID target score must be 85"

    def test_dry_score_defined(self, manifest_data):
        """Verify DRY score is defined with target 85."""
        quality_scores = manifest_data.get("quality_scores", {})
        assert "DRY" in quality_scores, "DRY score must be defined"
        assert quality_scores["DRY"] == 85, "DRY target score must be 85"

    def test_yagni_score_defined(self, manifest_data):
        """Verify YAGNI score is defined with target 90."""
        quality_scores = manifest_data.get("quality_scores", {})
        assert "YAGNI" in quality_scores, "YAGNI score must be defined"
        assert quality_scores["YAGNI"] == 90, "YAGNI target score must be 90"
