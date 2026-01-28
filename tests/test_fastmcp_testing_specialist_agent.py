"""
TDD Tests for TASK-FMT-004: Create fastmcp-testing-specialist agent

RED PHASE: These tests validate the acceptance criteria for the
fastmcp-testing-specialist agent files.

Files to validate:
1. installer/core/templates/fastmcp-python/agents/fastmcp-testing-specialist.md (core)
2. installer/core/templates/fastmcp-python/agents/fastmcp-testing-specialist-ext.md (extended)
"""

import pytest
import re
from pathlib import Path

# Base paths
WORKTREE_ROOT = Path(__file__).parent.parent
AGENT_DIR = WORKTREE_ROOT / "installer" / "core" / "templates" / "fastmcp-python" / "agents"
CORE_AGENT = AGENT_DIR / "fastmcp-testing-specialist.md"
EXT_AGENT = AGENT_DIR / "fastmcp-testing-specialist-ext.md"


class TestFileExistence:
    """Test that required files exist."""

    def test_core_agent_file_exists(self):
        """Core agent file must exist."""
        assert CORE_AGENT.exists(), f"Core agent file missing: {CORE_AGENT}"

    def test_extended_agent_file_exists(self):
        """Extended agent file must exist."""
        assert EXT_AGENT.exists(), f"Extended agent file missing: {EXT_AGENT}"


class TestCoreFrontmatter:
    """Test YAML frontmatter structure in core agent file."""

    @pytest.fixture
    def core_content(self):
        """Load core agent content."""
        if not CORE_AGENT.exists():
            pytest.skip("Core agent file does not exist")
        return CORE_AGENT.read_text()

    @pytest.fixture
    def frontmatter(self, core_content):
        """Extract frontmatter from core content."""
        match = re.match(r'^---\n(.*?)\n---', core_content, re.DOTALL)
        assert match, "Frontmatter not found (must start with ---)"
        return match.group(1)

    def test_frontmatter_has_valid_format(self, core_content):
        """Frontmatter must have valid YAML format with --- markers."""
        assert core_content.startswith('---'), "File must start with ---"
        assert '\n---' in core_content[3:], "Missing closing --- for frontmatter"

    def test_frontmatter_has_name(self, frontmatter):
        """Frontmatter must have correct name."""
        assert 'name: fastmcp-testing-specialist' in frontmatter, \
            "name must be 'fastmcp-testing-specialist'"

    def test_frontmatter_has_stack(self, frontmatter):
        """Frontmatter must have required stack values."""
        # Check for stack field with required values
        assert 'stack:' in frontmatter, "Missing stack field"
        stack_match = re.search(r'stack:\s*\[(.*?)\]', frontmatter, re.DOTALL)
        if stack_match:
            stack_content = stack_match.group(1).lower()
            assert 'python' in stack_content, "Stack must include 'python'"
            assert 'mcp' in stack_content, "Stack must include 'mcp'"
            assert 'fastmcp' in stack_content, "Stack must include 'fastmcp'"
            assert 'pytest' in stack_content, "Stack must include 'pytest'"

    def test_frontmatter_has_phase(self, frontmatter):
        """Frontmatter must have phase: testing."""
        assert 'phase: testing' in frontmatter, "phase must be 'testing'"

    def test_frontmatter_has_capabilities(self, frontmatter):
        """Frontmatter must have capabilities list."""
        assert 'capabilities:' in frontmatter, "Missing capabilities field"

    def test_frontmatter_has_keywords(self, frontmatter):
        """Frontmatter must have required keywords."""
        assert 'keywords:' in frontmatter, "Missing keywords field"
        keywords_match = re.search(r'keywords:\s*\[(.*?)\]', frontmatter, re.DOTALL)
        if keywords_match:
            keywords_content = keywords_match.group(1).lower()
            assert 'testing' in keywords_content, "Keywords must include 'testing'"
            assert 'pytest' in keywords_content, "Keywords must include 'pytest'"
            assert 'protocol' in keywords_content, "Keywords must include 'protocol'"
            assert 'json-rpc' in keywords_content, "Keywords must include 'json-rpc'"
            assert 'mcp' in keywords_content, "Keywords must include 'mcp'"

    def test_frontmatter_has_collaborates_with(self, frontmatter):
        """Frontmatter must have collaborates_with including fastmcp-specialist."""
        assert 'collaborates_with:' in frontmatter, "Missing collaborates_with field"
        assert 'fastmcp-specialist' in frontmatter, \
            "collaborates_with must include 'fastmcp-specialist'"


class TestCoreContentSections:
    """Test required content sections in core agent file."""

    @pytest.fixture
    def core_content(self):
        """Load core agent content."""
        if not CORE_AGENT.exists():
            pytest.skip("Core agent file does not exist")
        return CORE_AGENT.read_text()

    def test_has_role_section(self, core_content):
        """Core agent must have Role section."""
        assert '## Role' in core_content, "Missing '## Role' section"

    def test_has_boundaries_section(self, core_content):
        """Core agent must have Boundaries section."""
        assert '## Boundaries' in core_content or '## Boundary' in core_content, \
            "Missing '## Boundaries' section"

    def test_boundaries_has_always_items(self, core_content):
        """Boundaries must have ALWAYS items with required patterns."""
        content_lower = core_content.lower()

        # Check for ALWAYS section
        assert '### always' in content_lower or 'always' in content_lower, \
            "Missing ALWAYS section in Boundaries"

        # Required ALWAYS items
        assert 'test both unit and protocol' in content_lower, \
            "ALWAYS: Missing 'Test both unit and protocol levels'"
        assert 'string parameter' in content_lower or 'type conversion' in content_lower, \
            "ALWAYS: Missing 'string parameter type conversion tests'"
        assert 'streaming' in content_lower and 'cancell' in content_lower, \
            "ALWAYS: Missing 'streaming tool cancellation handling'"
        assert 'tools/list' in content_lower or 'discoverable' in content_lower, \
            "ALWAYS: Missing 'tools discoverable via tools/list'"

    def test_boundaries_has_never_items(self, core_content):
        """Boundaries must have NEVER items with required patterns."""
        content_lower = core_content.lower()

        # Check for NEVER section
        assert '### never' in content_lower or 'never' in content_lower, \
            "Missing NEVER section in Boundaries"

        # Required NEVER items
        assert 'unit tests' in content_lower and 'integration' in content_lower, \
            "NEVER: Missing 'unit tests passing != MCP integration working'"
        assert 'protocol' in content_lower and 'json-rpc' in content_lower, \
            "NEVER: Missing 'skip protocol-level JSON-RPC tests'"

    def test_boundaries_has_ask_items(self, core_content):
        """Boundaries must have ASK items."""
        content_lower = core_content.lower()

        # Check for ASK section
        assert '### ask' in content_lower or 'ask' in content_lower, \
            "Missing ASK section in Boundaries"

        # Required ASK items
        assert 'mock' in content_lower, \
            "ASK: Missing 'Mocking strategy for external services'"
        assert 'database' in content_lower or 'integration test' in content_lower, \
            "ASK: Missing 'Integration test database setup'"

    def test_has_capabilities_section(self, core_content):
        """Core agent must have Capabilities section with required items."""
        assert '## Capabilities' in core_content or '## Capability' in core_content, \
            "Missing '## Capabilities' section"

        content_lower = core_content.lower()

        # Required capabilities
        capabilities = [
            ('pytest-asyncio', 'unit testing with pytest-asyncio'),
            ('json-rpc', 'protocol testing with json-rpc'),
            ('streaming', 'streaming tool testing'),
            ('parameter', 'parameter conversion testing'),
            ('discovery', 'tool discovery testing'),
            ('error', 'error response testing'),
        ]

        for keyword, desc in capabilities:
            assert keyword in content_lower, \
                f"Capabilities: Missing capability related to '{desc}'"


class TestExtendedContent:
    """Test extended agent file content."""

    @pytest.fixture
    def ext_content(self):
        """Load extended agent content."""
        if not EXT_AGENT.exists():
            pytest.skip("Extended agent file does not exist")
        return EXT_AGENT.read_text()

    def test_has_protocol_testing_script(self, ext_content):
        """Extended file must have protocol testing script examples."""
        content_lower = ext_content.lower()

        # Must have JSON-RPC testing examples
        assert 'jsonrpc' in content_lower or 'json-rpc' in content_lower, \
            "Missing JSON-RPC protocol testing examples"
        assert 'initialize' in content_lower, \
            "Missing MCP initialize protocol example"
        assert 'tools/list' in content_lower or 'tools_list' in content_lower, \
            "Missing tools/list protocol example"
        assert 'tools/call' in content_lower or 'tools_call' in content_lower, \
            "Missing tools/call protocol example"

    def test_has_pytest_fixtures(self, ext_content):
        """Extended file must have pytest fixtures for MCP testing."""
        assert '@pytest.fixture' in ext_content or 'pytest.fixture' in ext_content, \
            "Missing pytest fixture examples"
        assert 'conftest' in ext_content.lower() or 'fixture' in ext_content.lower(), \
            "Missing fixture/conftest examples"

    def test_has_mocking_patterns(self, ext_content):
        """Extended file must have mocking patterns."""
        content_lower = ext_content.lower()
        assert 'mock' in content_lower or 'patch' in content_lower, \
            "Missing mocking patterns"

    def test_has_cicd_configuration(self, ext_content):
        """Extended file must have CI/CD testing configuration."""
        content_lower = ext_content.lower()
        assert 'ci' in content_lower or 'cd' in content_lower or \
               'github action' in content_lower or 'pipeline' in content_lower or \
               'pytest.ini' in content_lower or 'pyproject' in content_lower, \
            "Missing CI/CD testing configuration"

    def test_has_code_examples(self, ext_content):
        """Extended file must have at least 3 code examples."""
        code_blocks = re.findall(r'```python', ext_content)
        assert len(code_blocks) >= 3, \
            f"Extended file must have at least 3 Python code examples, found {len(code_blocks)}"

    def test_has_string_param_test_example(self, ext_content):
        """Extended file must have string parameter type conversion test example."""
        content_lower = ext_content.lower()
        # Look for the specific pattern from acceptance criteria
        assert ('string' in content_lower and 'type' in content_lower) or \
               'count="5"' in ext_content or 'int(count)' in ext_content, \
            "Missing string parameter type conversion test example"

    def test_has_bash_protocol_test_script(self, ext_content):
        """Extended file must have bash protocol testing script."""
        assert '```bash' in ext_content or '#!/bin/bash' in ext_content, \
            "Missing bash protocol testing script example"


class TestAgentIntegration:
    """Test integration between core and extended files."""

    @pytest.fixture
    def core_content(self):
        """Load core agent content."""
        if not CORE_AGENT.exists():
            pytest.skip("Core agent file does not exist")
        return CORE_AGENT.read_text()

    @pytest.fixture
    def ext_content(self):
        """Load extended agent content."""
        if not EXT_AGENT.exists():
            pytest.skip("Extended agent file does not exist")
        return EXT_AGENT.read_text()

    def test_extended_references_core(self, ext_content):
        """Extended file should reference core agent concepts."""
        assert 'fastmcp-testing-specialist' in ext_content.lower() or \
               'testing specialist' in ext_content.lower(), \
            "Extended file should reference the core agent"

    def test_extended_has_no_duplicate_frontmatter(self, ext_content):
        """Extended file should not have full YAML frontmatter (it's optional)."""
        # Extended files typically don't have frontmatter, or have minimal
        # This test ensures if frontmatter exists, it doesn't duplicate core fields
        if ext_content.startswith('---'):
            # Has frontmatter - ensure it's minimal
            match = re.match(r'^---\n(.*?)\n---', ext_content, re.DOTALL)
            if match:
                frontmatter = match.group(1)
                # Should not have full agent metadata
                assert 'stack:' not in frontmatter or 'phase:' not in frontmatter, \
                    "Extended file should not duplicate core frontmatter fields"


class TestContentQuality:
    """Test content quality standards."""

    @pytest.fixture
    def core_content(self):
        """Load core agent content."""
        if not CORE_AGENT.exists():
            pytest.skip("Core agent file does not exist")
        return CORE_AGENT.read_text()

    @pytest.fixture
    def ext_content(self):
        """Load extended agent content."""
        if not EXT_AGENT.exists():
            pytest.skip("Extended agent file does not exist")
        return EXT_AGENT.read_text()

    def test_no_placeholder_content(self, core_content, ext_content):
        """Files should not have placeholder content."""
        all_content = core_content + ext_content
        placeholders = ['TODO', 'TBD', 'FIXME', 'XXX', 'PLACEHOLDER']
        for placeholder in placeholders:
            assert placeholder not in all_content.upper() or \
                   all_content.upper().count(placeholder) <= 1, \
                f"Found placeholder content: {placeholder}"

    def test_minimum_content_length(self, core_content, ext_content):
        """Files should have substantial content."""
        assert len(core_content) >= 2000, \
            f"Core agent content too short: {len(core_content)} chars (min 2000)"
        assert len(ext_content) >= 3000, \
            f"Extended agent content too short: {len(ext_content)} chars (min 3000)"

    def test_proper_markdown_formatting(self, core_content):
        """Core file should have proper markdown heading hierarchy."""
        # Should have ## sections (level 2 headings)
        h2_count = len(re.findall(r'^## ', core_content, re.MULTILINE))
        assert h2_count >= 3, \
            f"Core file should have at least 3 level-2 headings, found {h2_count}"
