"""
TDD RED PHASE: Tests for mcp-typescript template .claude/rules/ files

These tests will FAIL initially because the rules files do not exist yet.
They define the expected structure and content for the mcp-typescript template
rules files following GuardKit's modular rules structure conventions.

Reference:
- installer/core/templates/react-typescript/.claude/rules/*.md
- .claude/reviews/TASK-REV-4371-review-report.md (Section 4.2)

Task: TASK-MTS-008 - Create .claude/rules/ files for MCP TypeScript template

Coverage Target: 100% (12 tests)
Test Count: 12 tests
"""

import pytest
from pathlib import Path
import re


# Template base path
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "installer" / "core" / "templates" / "mcp-typescript"

# Rules file paths (these will NOT exist yet - tests will fail)
RULES_DIR = TEMPLATE_DIR / ".claude" / "rules"
MCP_PATTERNS_PATH = RULES_DIR / "mcp-patterns.md"
TESTING_PATH = RULES_DIR / "testing.md"
TRANSPORT_PATH = RULES_DIR / "transport.md"
CONFIGURATION_PATH = RULES_DIR / "configuration.md"


# ============================================================================
# 1. File Existence Tests (4 tests)
# ============================================================================

class TestRulesFilesExist:
    """Test that all 4 required rules files exist at the correct paths."""

    def test_mcp_patterns_file_exists(self):
        """Test that mcp-patterns.md exists."""
        assert MCP_PATTERNS_PATH.exists(), \
            f"mcp-patterns.md not found at {MCP_PATTERNS_PATH}"

    def test_testing_file_exists(self):
        """Test that testing.md exists."""
        assert TESTING_PATH.exists(), \
            f"testing.md not found at {TESTING_PATH}"

    def test_transport_file_exists(self):
        """Test that transport.md exists."""
        assert TRANSPORT_PATH.exists(), \
            f"transport.md not found at {TRANSPORT_PATH}"

    def test_configuration_file_exists(self):
        """Test that configuration.md exists."""
        assert CONFIGURATION_PATH.exists(), \
            f"configuration.md not found at {CONFIGURATION_PATH}"


# ============================================================================
# 2. YAML Frontmatter Validation Tests (4 tests)
# ============================================================================

class TestRulesFrontmatter:
    """Test that all rules files have valid YAML frontmatter with 'paths' field."""

    def _extract_frontmatter(self, file_path: Path) -> dict:
        """Extract YAML frontmatter from markdown file."""
        content = file_path.read_text()

        # Match frontmatter pattern: --- ... ---
        match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if not match:
            return {}

        frontmatter_text = match.group(1)

        # Parse YAML manually (simple case for paths field)
        result = {}
        for line in frontmatter_text.split('\n'):
            if line.strip().startswith('paths:'):
                # Extract paths array
                paths_match = re.search(r'paths:\s*\[(.*?)\]', line)
                if paths_match:
                    paths_str = paths_match.group(1)
                    # Split by comma and clean quotes
                    paths = [p.strip().strip('"').strip("'") for p in paths_str.split(',')]
                    result['paths'] = paths

        return result

    def test_mcp_patterns_has_valid_frontmatter(self):
        """Test that mcp-patterns.md has valid YAML frontmatter with paths field."""
        frontmatter = self._extract_frontmatter(MCP_PATTERNS_PATH)

        assert 'paths' in frontmatter, \
            "mcp-patterns.md must have 'paths' field in frontmatter"
        assert isinstance(frontmatter['paths'], list), \
            "paths field must be a list"
        assert len(frontmatter['paths']) > 0, \
            "paths list cannot be empty"
        # Should target TypeScript source files
        assert any('src/**/*.ts' in p or '*.ts' in p for p in frontmatter['paths']), \
            "mcp-patterns.md should target TypeScript source files (src/**/*.ts)"

    def test_testing_has_valid_frontmatter(self):
        """Test that testing.md has valid YAML frontmatter with paths field."""
        frontmatter = self._extract_frontmatter(TESTING_PATH)

        assert 'paths' in frontmatter, \
            "testing.md must have 'paths' field in frontmatter"
        assert isinstance(frontmatter['paths'], list), \
            "paths field must be a list"
        assert len(frontmatter['paths']) > 0, \
            "paths list cannot be empty"
        # Should target test files
        assert any('test' in p.lower() for p in frontmatter['paths']), \
            "testing.md should target test files"

    def test_transport_has_valid_frontmatter(self):
        """Test that transport.md has valid YAML frontmatter with paths field."""
        frontmatter = self._extract_frontmatter(TRANSPORT_PATH)

        assert 'paths' in frontmatter, \
            "transport.md must have 'paths' field in frontmatter"
        assert isinstance(frontmatter['paths'], list), \
            "paths field must be a list"
        assert len(frontmatter['paths']) > 0, \
            "paths list cannot be empty"
        # Should target entry point and config
        assert any('index.ts' in p or 'config' in p.lower() for p in frontmatter['paths']), \
            "transport.md should target index.ts and config files"

    def test_configuration_has_valid_frontmatter(self):
        """Test that configuration.md has valid YAML frontmatter with paths field."""
        frontmatter = self._extract_frontmatter(CONFIGURATION_PATH)

        assert 'paths' in frontmatter, \
            "configuration.md must have 'paths' field in frontmatter"
        assert isinstance(frontmatter['paths'], list), \
            "paths field must be a list"
        assert len(frontmatter['paths']) > 0, \
            "paths list cannot be empty"
        # Should target config files
        assert any('config' in p.lower() or '*.json' in p for p in frontmatter['paths']), \
            "configuration.md should target config files"


# ============================================================================
# 3. Content Section Tests (4 tests)
# ============================================================================

class TestRulesContent:
    """Test that all rules files have appropriate MCP-specific content sections."""

    def test_mcp_patterns_has_required_sections(self):
        """Test that mcp-patterns.md has MCP-specific pattern sections."""
        content = MCP_PATTERNS_PATH.read_text()

        # Check for key MCP pattern sections
        required_sections = [
            "Tool Registration",  # Pattern 2: Registration before connect
            "stderr",            # Pattern 3: Logging to stderr
            "Streaming",         # Pattern 4: Streaming architecture
            "McpServer"          # Pattern 1: Use McpServer API
        ]

        for section in required_sections:
            assert section in content, \
                f"mcp-patterns.md should contain '{section}' section"

        # Check for critical warnings
        assert "console.log" in content or "NEVER" in content, \
            "mcp-patterns.md should warn about console.log usage"

    def test_testing_has_required_sections(self):
        """Test that testing.md has testing-specific sections."""
        content = TESTING_PATH.read_text()

        # Check for testing sections
        required_sections = [
            "Unit Test",        # Unit testing with Vitest
            "Protocol Test",    # JSON-RPC protocol testing
            "Coverage",         # Coverage requirements
        ]

        for section in required_sections:
            assert section in content, \
                f"testing.md should contain '{section}' section"

        # Check for test framework references
        assert "Vitest" in content or "test" in content.lower(), \
            "testing.md should reference Vitest or testing patterns"

    def test_transport_has_required_sections(self):
        """Test that transport.md has transport-specific sections."""
        content = TRANSPORT_PATH.read_text()

        # Check for transport sections
        required_sections = [
            "STDIO",            # STDIO transport
            "HTTP" or "Streamable",  # HTTP transport
            "Transport",        # General transport discussion
        ]

        found_count = sum(1 for section in required_sections if section in content)
        assert found_count >= 2, \
            "transport.md should contain at least 2 transport-related sections"

        # Check for transport classes
        assert "StdioServerTransport" in content or "Transport" in content, \
            "transport.md should reference transport classes"

    def test_configuration_has_required_sections(self):
        """Test that configuration.md has configuration-specific sections."""
        content = CONFIGURATION_PATH.read_text()

        # Check for configuration sections
        required_sections = [
            "claude_desktop_config" or "Claude Desktop",  # Claude Desktop config
            "absolute path" or "Absolute Path",           # Absolute path requirement
            "package.json",                               # Package configuration
        ]

        found_count = sum(1 for section in required_sections if any(s in content for s in section.split(" or ")) for section in required_sections)
        assert found_count >= 2, \
            "configuration.md should contain configuration-related sections"

        # Check for critical absolute path warning
        assert "absolute" in content.lower(), \
            "configuration.md should emphasize absolute paths"


# ============================================================================
# Test Summary
# ============================================================================
"""
Test Breakdown:
- File Existence Tests: 4 tests (mcp-patterns, testing, transport, configuration)
- YAML Frontmatter Tests: 4 tests (paths field validation for each file)
- Content Section Tests: 4 tests (MCP-specific content for each file)

Total: 12 tests

All tests will FAIL initially (RED phase) because:
1. Rules files do not exist yet
2. Frontmatter not defined
3. Content not written

GREEN phase (TASK-MTS-008 implementation) will:
1. Create all 4 rules files
2. Add valid YAML frontmatter with paths field
3. Write MCP-specific content sections
"""
