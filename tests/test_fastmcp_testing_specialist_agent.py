"""
TDD RED Phase Tests for TASK-FMT-004: fastmcp-testing-specialist agent

These tests will FAIL initially because the agent files don't exist yet.
They verify the structure and content of the fastmcp-testing-specialist agent files.
"""

import os
import re
import pytest
import yaml
from pathlib import Path


# Test fixtures
@pytest.fixture
def agent_core_path():
    """Path to core agent file."""
    return Path("installer/core/templates/fastmcp-python/agents/fastmcp-testing-specialist.md")


@pytest.fixture
def agent_ext_path():
    """Path to extended agent file."""
    return Path("installer/core/templates/fastmcp-python/agents/fastmcp-testing-specialist-ext.md")


@pytest.fixture
def agent_core_content(agent_core_path):
    """Load core agent file content."""
    with open(agent_core_path, 'r', encoding='utf-8') as f:
        return f.read()


@pytest.fixture
def agent_ext_content(agent_ext_path):
    """Load extended agent file content."""
    with open(agent_ext_path, 'r', encoding='utf-8') as f:
        return f.read()


@pytest.fixture
def agent_core_frontmatter(agent_core_content):
    """Extract YAML frontmatter from core agent file."""
    # Extract frontmatter between --- markers
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', agent_core_content, re.DOTALL)
    if not match:
        pytest.fail("No frontmatter found in core agent file")
    return yaml.safe_load(match.group(1))


# File Existence Tests
class TestFileExistence:
    """Verify that agent files exist."""

    def test_core_agent_file_exists(self, agent_core_path):
        """Core agent file must exist."""
        assert agent_core_path.exists(), \
            f"Core agent file not found: {agent_core_path}"

    def test_extended_agent_file_exists(self, agent_ext_path):
        """Extended agent file must exist."""
        assert agent_ext_path.exists(), \
            f"Extended agent file not found: {agent_ext_path}"


# Frontmatter Validation Tests
class TestCoreFrontmatter:
    """Validate YAML frontmatter structure and content."""

    def test_frontmatter_exists(self, agent_core_content):
        """Core agent must have valid YAML frontmatter."""
        assert agent_core_content.startswith('---\n'), \
            "Core agent must start with YAML frontmatter (---)"

        # Check for closing ---
        lines = agent_core_content.split('\n')
        closing_found = False
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == '---':
                closing_found = True
                break

        assert closing_found, "Frontmatter must have closing --- marker"

    def test_name_field(self, agent_core_frontmatter):
        """Frontmatter must have correct name field."""
        assert 'name' in agent_core_frontmatter, \
            "Frontmatter must have 'name' field"
        assert agent_core_frontmatter['name'] == 'fastmcp-testing-specialist', \
            "Agent name must be 'fastmcp-testing-specialist'"

    def test_stack_field(self, agent_core_frontmatter):
        """Frontmatter must have correct stack field."""
        assert 'stack' in agent_core_frontmatter, \
            "Frontmatter must have 'stack' field"

        stack = agent_core_frontmatter['stack']
        assert isinstance(stack, list), "Stack must be a list"

        required_stack = {'python', 'mcp', 'fastmcp', 'pytest'}
        actual_stack = set(stack)

        assert required_stack.issubset(actual_stack), \
            f"Stack must include {required_stack}, got {actual_stack}"

    def test_phase_field(self, agent_core_frontmatter):
        """Frontmatter must have phase field set to 'testing'."""
        assert 'phase' in agent_core_frontmatter, \
            "Frontmatter must have 'phase' field"
        assert agent_core_frontmatter['phase'] == 'testing', \
            "Phase must be 'testing'"

    def test_capabilities_field(self, agent_core_frontmatter):
        """Frontmatter must have capabilities field."""
        assert 'capabilities' in agent_core_frontmatter, \
            "Frontmatter must have 'capabilities' field"

        capabilities = agent_core_frontmatter['capabilities']
        assert isinstance(capabilities, list), "Capabilities must be a list"
        assert len(capabilities) > 0, "Capabilities list cannot be empty"

    def test_keywords_field(self, agent_core_frontmatter):
        """Frontmatter must have correct keywords."""
        assert 'keywords' in agent_core_frontmatter, \
            "Frontmatter must have 'keywords' field"

        keywords = agent_core_frontmatter['keywords']
        assert isinstance(keywords, list), "Keywords must be a list"

        required_keywords = {'testing', 'pytest', 'protocol', 'json-rpc', 'mcp'}
        actual_keywords = set(keywords)

        assert required_keywords.issubset(actual_keywords), \
            f"Keywords must include {required_keywords}, got {actual_keywords}"

    def test_collaborates_with_field(self, agent_core_frontmatter):
        """Frontmatter must list collaboration with fastmcp-specialist."""
        assert 'collaborates_with' in agent_core_frontmatter, \
            "Frontmatter must have 'collaborates_with' field"

        collaborates = agent_core_frontmatter['collaborates_with']
        assert isinstance(collaborates, list), "collaborates_with must be a list"
        assert 'fastmcp-specialist' in collaborates, \
            "Must collaborate with 'fastmcp-specialist'"


# Content Section Tests
class TestCoreContentSections:
    """Validate required content sections in core agent file."""

    def test_role_section_exists(self, agent_core_content):
        """Core agent must have a Role section."""
        assert re.search(r'^##?\s+Role\s*$', agent_core_content, re.MULTILINE), \
            "Core agent must have a '## Role' or '# Role' section"

    def test_role_describes_mcp_testing(self, agent_core_content):
        """Role section must describe MCP testing specialization."""
        # Extract Role section content
        role_match = re.search(
            r'^##?\s+Role\s*$(.*?)(?=^##?\s+|\Z)',
            agent_core_content,
            re.MULTILINE | re.DOTALL
        )
        assert role_match, "Could not extract Role section"

        role_text = role_match.group(1).lower()

        # Check for MCP testing-related terms
        required_terms = ['mcp', 'testing', 'protocol']
        for term in required_terms:
            assert term in role_text, \
                f"Role section must mention '{term}'"

    def test_boundaries_section_exists(self, agent_core_content):
        """Core agent must have a Boundaries section."""
        assert re.search(r'^##?\s+Boundaries\s*$', agent_core_content, re.MULTILINE), \
            "Core agent must have a '## Boundaries' section"

    def test_boundaries_always_section(self, agent_core_content):
        """Boundaries must have ALWAYS subsection with required items."""
        boundaries_section = self._extract_boundaries_section(agent_core_content)

        # Check for ALWAYS subsection
        assert re.search(r'###\s+ALWAYS', boundaries_section), \
            "Boundaries must have '### ALWAYS' subsection"

        # Check for required ALWAYS items
        required_always_items = [
            'test both unit and protocol levels',
            'string parameter type conversion tests',
            'streaming tool cancellation handling',
            'tools are discoverable via tools/list'
        ]

        always_section = self._extract_always_section(boundaries_section)

        for item in required_always_items:
            assert any(item in line.lower() for line in always_section.split('\n')), \
                f"ALWAYS section must include: '{item}'"

    def test_boundaries_never_section(self, agent_core_content):
        """Boundaries must have NEVER subsection with required warnings."""
        boundaries_section = self._extract_boundaries_section(agent_core_content)

        # Check for NEVER subsection
        assert re.search(r'###\s+NEVER', boundaries_section), \
            "Boundaries must have '### NEVER' subsection"

        # Check for required NEVER items
        required_never_items = [
            'never assume unit tests passing = mcp integration working',
            'never skip protocol-level json-rpc tests'
        ]

        never_section = self._extract_never_section(boundaries_section)

        for item in required_never_items:
            assert any(item in line.lower() for line in never_section.split('\n')), \
                f"NEVER section must include: '{item}'"

    def test_boundaries_ask_section(self, agent_core_content):
        """Boundaries must have ASK subsection."""
        boundaries_section = self._extract_boundaries_section(agent_core_content)

        # Check for ASK subsection
        assert re.search(r'###\s+ASK', boundaries_section), \
            "Boundaries must have '### ASK' subsection"

        # Check for required ASK items
        required_ask_items = [
            'mocking strategy',
            'integration test database'
        ]

        ask_section = self._extract_ask_section(boundaries_section)

        for item in required_ask_items:
            assert any(item in line.lower() for line in ask_section.split('\n')), \
                f"ASK section must include: '{item}'"

    def test_capabilities_section_exists(self, agent_core_content):
        """Core agent must have a Capabilities section."""
        assert re.search(r'^##?\s+Capabilities\s*$', agent_core_content, re.MULTILINE), \
            "Core agent must have a '## Capabilities' section"

    def test_capabilities_required_items(self, agent_core_content):
        """Capabilities section must list all required testing capabilities."""
        capabilities_section = self._extract_capabilities_section(agent_core_content)

        required_capabilities = [
            'unit testing with pytest-asyncio',
            'protocol testing with json-rpc',
            'streaming tool testing',
            'parameter conversion testing',
            'tool discovery testing',
            'error response testing'
        ]

        capabilities_lower = capabilities_section.lower()

        for capability in required_capabilities:
            assert capability in capabilities_lower, \
                f"Capabilities must include: '{capability}'"

    # Helper methods for section extraction
    def _extract_boundaries_section(self, content):
        """Extract Boundaries section content."""
        match = re.search(
            r'^##?\s+Boundaries\s*$(.*?)(?=^##?\s+|\Z)',
            content,
            re.MULTILINE | re.DOTALL
        )
        assert match, "Could not extract Boundaries section"
        return match.group(1)

    def _extract_always_section(self, boundaries_content):
        """Extract ALWAYS subsection from Boundaries."""
        match = re.search(
            r'###\s+ALWAYS(.*?)(?=###\s+|\Z)',
            boundaries_content,
            re.DOTALL
        )
        assert match, "Could not extract ALWAYS subsection"
        return match.group(1)

    def _extract_never_section(self, boundaries_content):
        """Extract NEVER subsection from Boundaries."""
        match = re.search(
            r'###\s+NEVER(.*?)(?=###\s+|\Z)',
            boundaries_content,
            re.DOTALL
        )
        assert match, "Could not extract NEVER subsection"
        return match.group(1)

    def _extract_ask_section(self, boundaries_content):
        """Extract ASK subsection from Boundaries."""
        match = re.search(
            r'###\s+ASK(.*?)(?=###\s+|\Z)',
            boundaries_content,
            re.DOTALL
        )
        assert match, "Could not extract ASK subsection"
        return match.group(1)

    def _extract_capabilities_section(self, content):
        """Extract Capabilities section content."""
        match = re.search(
            r'^##?\s+Capabilities\s*$(.*?)(?=^##?\s+|\Z)',
            content,
            re.MULTILINE | re.DOTALL
        )
        assert match, "Could not extract Capabilities section"
        return match.group(1)


# Extended Agent File Tests
class TestExtendedContent:
    """Validate extended agent file content."""

    def test_protocol_testing_script_example(self, agent_ext_content):
        """Extended file must include protocol testing script example."""
        ext_lower = agent_ext_content.lower()

        # Check for protocol testing script elements
        assert 'protocol' in ext_lower and 'testing' in ext_lower, \
            "Extended file must discuss protocol testing"

        # Check for JSON-RPC method examples
        required_methods = ['initialize', 'tools/list', 'tools/call']
        for method in required_methods:
            assert method in ext_lower, \
                f"Extended file must include example for '{method}' method"

    def test_pytest_fixtures_for_mcp(self, agent_ext_content):
        """Extended file must include pytest fixtures for MCP testing."""
        ext_lower = agent_ext_content.lower()

        assert 'pytest' in ext_lower and 'fixture' in ext_lower, \
            "Extended file must include pytest fixtures"

        # Check for MCP-specific fixture patterns
        assert 'mcp' in ext_lower or 'protocol' in ext_lower, \
            "Fixtures must be related to MCP testing"

    def test_mocking_patterns(self, agent_ext_content):
        """Extended file must include mocking patterns."""
        ext_lower = agent_ext_content.lower()

        assert 'mock' in ext_lower or 'mocking' in ext_lower, \
            "Extended file must include mocking patterns"

    def test_ci_cd_testing_configuration(self, agent_ext_content):
        """Extended file must include CI/CD testing configuration."""
        ext_lower = agent_ext_content.lower()

        ci_cd_keywords = ['ci/cd', 'ci', 'github actions', 'gitlab ci', 'continuous integration']

        assert any(keyword in ext_lower for keyword in ci_cd_keywords), \
            "Extended file must include CI/CD testing configuration"

    def test_code_examples_exist(self, agent_ext_content):
        """Extended file must include code examples."""
        # Check for code blocks (```python or ```)
        code_blocks = re.findall(r'```(\w+)?\n', agent_ext_content)

        assert len(code_blocks) >= 3, \
            f"Extended file must include at least 3 code examples, found {len(code_blocks)}"

    def test_string_parameter_test_example(self, agent_ext_content):
        """Extended file must include string parameter type conversion test example."""
        ext_lower = agent_ext_content.lower()

        # Check for key concepts from the task specification
        assert 'string' in ext_lower and 'parameter' in ext_lower, \
            "Extended file must discuss string parameter handling"

        assert 'conversion' in ext_lower or 'type' in ext_lower, \
            "Extended file must discuss type conversion"


# Integration Tests
class TestAgentIntegration:
    """Test integration between core and extended files."""

    def test_extended_references_core_concepts(self, agent_core_content, agent_ext_content):
        """Extended file should reference concepts from core file."""
        # Extract key concepts from core (capabilities)
        capabilities_match = re.search(
            r'^##?\s+Capabilities\s*$(.*?)(?=^##?\s+|\Z)',
            agent_core_content,
            re.MULTILINE | re.DOTALL
        )

        if capabilities_match:
            capabilities = capabilities_match.group(1).lower()
            ext_lower = agent_ext_content.lower()

            # At least some capabilities should be expanded in extended file
            referenced_capabilities = 0
            capability_keywords = ['protocol', 'streaming', 'parameter', 'discovery']

            for keyword in capability_keywords:
                if keyword in capabilities and keyword in ext_lower:
                    referenced_capabilities += 1

            assert referenced_capabilities >= 2, \
                "Extended file should expand on at least 2 core capabilities"

    def test_no_duplicate_frontmatter_in_extended(self, agent_ext_content):
        """Extended file should not have YAML frontmatter."""
        # Extended files should not start with ---
        assert not agent_ext_content.startswith('---\n'), \
            "Extended file should not have YAML frontmatter (only core file has it)"


# Quality Tests
class TestContentQuality:
    """Validate content quality standards."""

    def test_no_placeholder_content(self, agent_core_content, agent_ext_content):
        """Files must not contain placeholder content."""
        combined = (agent_core_content + agent_ext_content).lower()

        placeholders = ['todo', 'tbd', 'fixme', 'placeholder', 'xxx']

        for placeholder in placeholders:
            assert placeholder not in combined, \
                f"Files must not contain placeholder text: '{placeholder}'"

    def test_minimum_content_length(self, agent_core_content, agent_ext_content):
        """Files must have substantial content."""
        # Core file should be at least 2KB
        assert len(agent_core_content) >= 2000, \
            f"Core file too short: {len(agent_core_content)} bytes (minimum 2000)"

        # Extended file should be at least 3KB
        assert len(agent_ext_content) >= 3000, \
            f"Extended file too short: {len(agent_ext_content)} bytes (minimum 3000)"

    def test_proper_markdown_formatting(self, agent_core_content):
        """Core file must use proper markdown formatting."""
        # Check for proper heading hierarchy
        headings = re.findall(r'^(#{1,6})\s+(.+)$', agent_core_content, re.MULTILINE)

        assert len(headings) >= 3, \
            "Core file must have at least 3 headings"

        # First heading should be # (h1)
        assert headings[0][0] == '#', \
            "First heading should be h1 (#)"
