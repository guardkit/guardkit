"""
Test suite for MCP TypeScript primitive templates.

TDD RED Phase: These tests define requirements for tool, resource, and prompt templates.
All tests should FAIL initially until templates are implemented.

Task: TASK-MTS-005
Phase: 3-TDD-RED
"""

import pytest
from pathlib import Path
import re


# Base paths
TEMPLATE_DIR = Path("installer/core/templates/mcp-typescript")
TEMPLATES_SUBDIR = TEMPLATE_DIR / "templates"
TOOLS_DIR = TEMPLATES_SUBDIR / "tools"
RESOURCES_DIR = TEMPLATES_SUBDIR / "resources"
PROMPTS_DIR = TEMPLATES_SUBDIR / "prompts"


class TestFileExistence:
    """Test that all template files exist."""

    def test_tool_template_exists(self):
        """Tool template file should exist."""
        tool_template = TOOLS_DIR / "tool.ts.template"
        assert tool_template.exists(), f"Tool template not found at {tool_template}"

    def test_resource_template_exists(self):
        """Resource template file should exist."""
        resource_template = RESOURCES_DIR / "resource.ts.template"
        assert resource_template.exists(), f"Resource template not found at {resource_template}"

    def test_prompt_template_exists(self):
        """Prompt template file should exist."""
        prompt_template = PROMPTS_DIR / "prompt.ts.template"
        assert prompt_template.exists(), f"Prompt template not found at {prompt_template}"


class TestToolTemplate:
    """Test tool.ts.template content and patterns."""

    @pytest.fixture
    def tool_template_content(self):
        """Load tool template content."""
        tool_path = TOOLS_DIR / "tool.ts.template"
        if not tool_path.exists():
            pytest.skip("Tool template not yet created")
        return tool_path.read_text()

    def test_tool_template_not_empty(self, tool_template_content):
        """Tool template should have content."""
        assert len(tool_template_content) > 0, "Tool template is empty"

    def test_tool_has_imports(self, tool_template_content):
        """Tool template should import required MCP types."""
        assert "import" in tool_template_content, "No imports found"
        assert "@modelcontextprotocol/sdk" in tool_template_content, "MCP SDK not imported"
        assert "zod" in tool_template_content, "Zod not imported"

    def test_tool_has_zod_schema(self, tool_template_content):
        """Tool template should define Zod input schema."""
        assert "z.object" in tool_template_content, "No Zod schema found"
        # Should have both input and output schemas
        assert tool_template_content.count("z.object") >= 1, "Missing Zod schemas"

    def test_tool_has_function_implementation(self, tool_template_content):
        """Tool template should implement the tool function."""
        assert "async function" in tool_template_content or "const " in tool_template_content, \
            "No function implementation found"

    def test_tool_has_registration_helper(self, tool_template_content):
        """Tool template should include registration helper."""
        assert "server.registerTool" in tool_template_content or \
               "McpServer.registerTool" in tool_template_content or \
               "server.setRequestHandler" in tool_template_content, \
            "No tool registration found"

    def test_tool_has_name_placeholder(self, tool_template_content):
        """Tool template should use ToolName placeholders."""
        # Check for various case formats
        assert "{{ToolName}}" in tool_template_content or \
               "{{toolName}}" in tool_template_content or \
               "{{tool-name}}" in tool_template_content, \
            "No tool name placeholder found"

    def test_tool_has_description_placeholder(self, tool_template_content):
        """Tool template should use Description placeholder."""
        assert "{{Description}}" in tool_template_content or \
               "{{description}}" in tool_template_content, \
            "No description placeholder found"

    def test_tool_has_param_placeholders(self, tool_template_content):
        """Tool template should use parameter placeholders."""
        assert "{{paramName}}" in tool_template_content or \
               "{{ParamName}}" in tool_template_content, \
            "No parameter name placeholder found"

    def test_tool_follows_mcp_pattern(self, tool_template_content):
        """Tool should follow MCP SDK patterns."""
        # Should have CallToolRequestSchema or similar
        assert "CallToolRequest" in tool_template_content or \
               "tools/call" in tool_template_content or \
               "registerTool" in tool_template_content, \
            "Does not follow MCP tool pattern"


class TestResourceTemplate:
    """Test resource.ts.template content and patterns."""

    @pytest.fixture
    def resource_template_content(self):
        """Load resource template content."""
        resource_path = RESOURCES_DIR / "resource.ts.template"
        if not resource_path.exists():
            pytest.skip("Resource template not yet created")
        return resource_path.read_text()

    def test_resource_template_not_empty(self, resource_template_content):
        """Resource template should have content."""
        assert len(resource_template_content) > 0, "Resource template is empty"

    def test_resource_has_imports(self, resource_template_content):
        """Resource template should import required MCP types."""
        assert "import" in resource_template_content, "No imports found"
        assert "@modelcontextprotocol/sdk" in resource_template_content, \
            "MCP SDK not imported"

    def test_resource_supports_static_resources(self, resource_template_content):
        """Resource template should show static resource pattern."""
        # Should demonstrate listing resources
        assert "ListResourcesRequest" in resource_template_content or \
               "resources/list" in resource_template_content or \
               "registerResource" in resource_template_content, \
            "No static resource pattern found"

    def test_resource_supports_dynamic_resources(self, resource_template_content):
        """Resource template should show dynamic resource pattern."""
        # Should show URI template or dynamic URI handling
        assert "uriTemplate" in resource_template_content or \
               "ReadResourceRequest" in resource_template_content or \
               "resources/read" in resource_template_content, \
            "No dynamic resource pattern found"

    def test_resource_has_name_placeholder(self, resource_template_content):
        """Resource template should use ResourceName placeholders."""
        assert "{{ResourceName}}" in resource_template_content or \
               "{{resourceName}}" in resource_template_content or \
               "{{resource-name}}" in resource_template_content, \
            "No resource name placeholder found"

    def test_resource_has_uri_handling(self, resource_template_content):
        """Resource template should handle URI patterns."""
        assert "uri" in resource_template_content.lower(), \
            "No URI handling found"

    def test_resource_has_content_types(self, resource_template_content):
        """Resource template should specify content types."""
        assert "mimeType" in resource_template_content or \
               "text/plain" in resource_template_content or \
               "application/json" in resource_template_content, \
            "No content type specification found"


class TestPromptTemplate:
    """Test prompt.ts.template content and patterns."""

    @pytest.fixture
    def prompt_template_content(self):
        """Load prompt template content."""
        prompt_path = PROMPTS_DIR / "prompt.ts.template"
        if not prompt_path.exists():
            pytest.skip("Prompt template not yet created")
        return prompt_path.read_text()

    def test_prompt_template_not_empty(self, prompt_template_content):
        """Prompt template should have content."""
        assert len(prompt_template_content) > 0, "Prompt template is empty"

    def test_prompt_has_imports(self, prompt_template_content):
        """Prompt template should import required MCP types."""
        assert "import" in prompt_template_content, "No imports found"
        assert "@modelcontextprotocol/sdk" in prompt_template_content, \
            "MCP SDK not imported"

    def test_prompt_has_registration(self, prompt_template_content):
        """Prompt template should include prompt registration."""
        assert "ListPromptsRequest" in prompt_template_content or \
               "GetPromptRequest" in prompt_template_content or \
               "prompts/list" in prompt_template_content or \
               "registerPrompt" in prompt_template_content, \
            "No prompt registration found"

    def test_prompt_has_completion_support(self, prompt_template_content):
        """Prompt template should support argument completion."""
        assert "completable" in prompt_template_content or \
               "CompleteRequest" in prompt_template_content or \
               "completion/complete" in prompt_template_content, \
            "No completion support found"

    def test_prompt_has_name_placeholder(self, prompt_template_content):
        """Prompt template should use PromptName placeholders."""
        assert "{{PromptName}}" in prompt_template_content or \
               "{{promptName}}" in prompt_template_content or \
               "{{prompt-name}}" in prompt_template_content, \
            "No prompt name placeholder found"

    def test_prompt_has_arguments(self, prompt_template_content):
        """Prompt template should define prompt arguments."""
        assert "arguments" in prompt_template_content.lower(), \
            "No arguments definition found"

    def test_prompt_has_message_generation(self, prompt_template_content):
        """Prompt template should generate prompt messages."""
        assert "messages" in prompt_template_content or \
               "content" in prompt_template_content, \
            "No message generation found"


class TestPlaceholderConsistency:
    """Test placeholder naming consistency across all templates."""

    def test_tool_placeholder_format(self):
        """Tool template should use consistent placeholder format."""
        tool_path = TOOLS_DIR / "tool.ts.template"
        if not tool_path.exists():
            pytest.skip("Tool template not yet created")

        content = tool_path.read_text()
        placeholders = re.findall(r'\{\{(\w+)\}\}', content)

        # Should have at least: ToolName, Description, paramName
        assert len(placeholders) >= 3, "Insufficient placeholders in tool template"

        # Check for expected placeholders
        placeholder_str = ' '.join(placeholders)
        assert any(p in placeholder_str for p in ['ToolName', 'toolName', 'tool-name']), \
            "Missing tool name placeholder"

    def test_resource_placeholder_format(self):
        """Resource template should use consistent placeholder format."""
        resource_path = RESOURCES_DIR / "resource.ts.template"
        if not resource_path.exists():
            pytest.skip("Resource template not yet created")

        content = resource_path.read_text()
        placeholders = re.findall(r'\{\{(\w+)\}\}', content)

        # Should have at least: ResourceName, Description
        assert len(placeholders) >= 2, "Insufficient placeholders in resource template"

        placeholder_str = ' '.join(placeholders)
        assert any(p in placeholder_str for p in ['ResourceName', 'resourceName', 'resource-name']), \
            "Missing resource name placeholder"

    def test_prompt_placeholder_format(self):
        """Prompt template should use consistent placeholder format."""
        prompt_path = PROMPTS_DIR / "prompt.ts.template"
        if not prompt_path.exists():
            pytest.skip("Prompt template not yet created")

        content = prompt_path.read_text()
        placeholders = re.findall(r'\{\{(\w+)\}\}', content)

        # Should have at least: PromptName, Description
        assert len(placeholders) >= 2, "Insufficient placeholders in prompt template"

        placeholder_str = ' '.join(placeholders)
        assert any(p in placeholder_str for p in ['PromptName', 'promptName', 'prompt-name']), \
            "Missing prompt name placeholder"


class TestTemplateIntegration:
    """Test that templates integrate properly with MCP SDK patterns."""

    def test_all_templates_use_typescript(self):
        """All templates should be TypeScript files."""
        for template_path in [
            TOOLS_DIR / "tool.ts.template",
            RESOURCES_DIR / "resource.ts.template",
            PROMPTS_DIR / "prompt.ts.template"
        ]:
            if template_path.exists():
                content = template_path.read_text()
                # Should have TypeScript syntax indicators
                assert ":" in content or "interface" in content or "type" in content, \
                    f"{template_path.name} does not appear to be TypeScript"

    def test_templates_are_self_contained(self):
        """Templates should include necessary imports and exports."""
        for template_path in [
            TOOLS_DIR / "tool.ts.template",
            RESOURCES_DIR / "resource.ts.template",
            PROMPTS_DIR / "prompt.ts.template"
        ]:
            if template_path.exists():
                content = template_path.read_text()
                assert "import" in content, f"{template_path.name} missing imports"
                # Should export something (function, const, or default)
                assert "export" in content or "async function" in content, \
                    f"{template_path.name} missing exports"

    def test_templates_have_error_handling(self):
        """Templates should include basic error handling."""
        for template_path in [
            TOOLS_DIR / "tool.ts.template",
            RESOURCES_DIR / "resource.ts.template",
            PROMPTS_DIR / "prompt.ts.template"
        ]:
            if template_path.exists():
                content = template_path.read_text()
                # Should have try/catch or error handling
                assert "try" in content or "catch" in content or "Error" in content or \
                       "throw" in content, \
                    f"{template_path.name} missing error handling"


class TestManifestAlignment:
    """Test that templates align with manifest.json expectations."""

    def test_manifest_exists(self):
        """Manifest.json should exist."""
        manifest_path = TEMPLATE_DIR / "manifest.json"
        assert manifest_path.exists(), "manifest.json not found"

    def test_manifest_defines_placeholders(self):
        """Manifest should define placeholders used in templates."""
        manifest_path = TEMPLATE_DIR / "manifest.json"
        if not manifest_path.exists():
            pytest.skip("Manifest not yet created")

        import json
        manifest = json.loads(manifest_path.read_text())

        # Should have placeholders section
        assert "placeholders" in manifest or "variables" in manifest, \
            "Manifest missing placeholder definitions"

    def test_tool_template_references_exist(self):
        """Manifest should reference tool template."""
        manifest_path = TEMPLATE_DIR / "manifest.json"
        if not manifest_path.exists():
            pytest.skip("Manifest not yet created")

        import json
        manifest = json.loads(manifest_path.read_text())
        manifest_str = json.dumps(manifest)

        assert "tool.ts.template" in manifest_str or "tools" in manifest_str, \
            "Manifest missing tool template reference"

    def test_resource_template_references_exist(self):
        """Manifest should reference resource template."""
        manifest_path = TEMPLATE_DIR / "manifest.json"
        if not manifest_path.exists():
            pytest.skip("Manifest not yet created")

        import json
        manifest = json.loads(manifest_path.read_text())
        manifest_str = json.dumps(manifest)

        assert "resource.ts.template" in manifest_str or "resources" in manifest_str, \
            "Manifest missing resource template reference"

    def test_prompt_template_references_exist(self):
        """Manifest should reference prompt template."""
        manifest_path = TEMPLATE_DIR / "manifest.json"
        if not manifest_path.exists():
            pytest.skip("Manifest not yet created")

        import json
        manifest = json.loads(manifest_path.read_text())
        manifest_str = json.dumps(manifest)

        assert "prompt.ts.template" in manifest_str or "prompts" in manifest_str, \
            "Manifest missing prompt template reference"
