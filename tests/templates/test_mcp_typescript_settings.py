import json
import pytest
from pathlib import Path


class TestMCPTypeScriptSettings:
    @pytest.fixture
    def settings_path(self):
        return Path("installer/core/templates/mcp-typescript/settings.json")

    @pytest.fixture
    def settings(self, settings_path):
        with open(settings_path) as f:
            return json.load(f)

    def test_file_exists(self, settings_path):
        assert settings_path.exists(), f"settings.json not found at {settings_path}"

    def test_valid_json(self, settings_path):
        with open(settings_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_schema_version(self, settings):
        assert settings.get("schema_version") == "1.0.0"

    def test_naming_conventions_tool(self, settings):
        naming = settings.get("naming_conventions", {})
        tool = naming.get("tool", {})
        # Check case_style instead of pattern
        assert tool.get("case_style") == "kebab-case"
        assert "search-patterns" in tool.get("examples", [])
        assert "get-details" in tool.get("examples", [])

    def test_naming_conventions_resource(self, settings):
        naming = settings.get("naming_conventions", {})
        resource = naming.get("resource", {})
        # Check pattern contains protocol format
        pattern = resource.get("pattern", "")
        assert "://" in pattern
        assert "config://app" in resource.get("examples", [])

    def test_naming_conventions_prompt(self, settings):
        naming = settings.get("naming_conventions", {})
        prompt = naming.get("prompt", {})
        # Check case_style instead of pattern
        assert prompt.get("case_style") == "kebab-case"
        assert "code-review" in prompt.get("examples", [])
        assert "summarize-docs" in prompt.get("examples", [])

    def test_naming_conventions_server(self, settings):
        naming = settings.get("naming_conventions", {})
        server = naming.get("server", {})
        # Check pattern contains -server suffix
        pattern = server.get("pattern", "")
        assert "-server" in pattern
        examples = server.get("examples", [])
        assert any("-server" in ex for ex in examples)

    def test_naming_conventions_test_file(self, settings):
        naming = settings.get("naming_conventions", {})
        test_file = naming.get("test_file", {})
        # Check pattern ends with .test.ts
        pattern = test_file.get("pattern", "")
        assert pattern.endswith(".test.ts")

    def test_file_organization_by_layer(self, settings):
        org = settings.get("file_organization", {})
        assert org.get("by_layer") is True

    def test_file_organization_by_feature(self, settings):
        org = settings.get("file_organization", {})
        assert org.get("by_feature") is False

    def test_layer_mappings_tools(self, settings):
        layers = settings.get("layer_mappings", {})
        assert "tools" in layers
        # Check for dict instead of str
        assert isinstance(layers["tools"], dict)

    def test_layer_mappings_resources(self, settings):
        layers = settings.get("layer_mappings", {})
        assert "resources" in layers
        # Check for dict instead of str
        assert isinstance(layers["resources"], dict)

    def test_layer_mappings_prompts(self, settings):
        layers = settings.get("layer_mappings", {})
        assert "prompts" in layers
        # Check for dict instead of str
        assert isinstance(layers["prompts"], dict)

    def test_layer_mappings_server(self, settings):
        layers = settings.get("layer_mappings", {})
        assert "server" in layers
        # Check for dict instead of str
        assert isinstance(layers["server"], dict)

    def test_code_style_indent(self, settings):
        style = settings.get("code_style", {})
        assert style.get("indent_size") == 2

    def test_code_style_semicolons(self, settings):
        style = settings.get("code_style", {})
        assert style.get("use_semicolons") is True

    def test_code_style_quotes(self, settings):
        style = settings.get("code_style", {})
        assert style.get("quote_style") == "single"

    def test_import_aliases(self, settings):
        aliases = settings.get("import_aliases", {})
        assert "@/" in aliases
        assert aliases["@/"] == "src/"

    def test_generation_options_tests(self, settings):
        gen = settings.get("generation_options", {})
        assert "include_tests" in gen
        assert isinstance(gen["include_tests"], bool)

    def test_generation_options_docker(self, settings):
        gen = settings.get("generation_options", {})
        assert "include_docker" in gen
        assert isinstance(gen["include_docker"], bool)

    def test_generation_options_protocol_tests(self, settings):
        gen = settings.get("generation_options", {})
        assert "include_protocol_tests" in gen
        assert isinstance(gen["include_protocol_tests"], bool)
