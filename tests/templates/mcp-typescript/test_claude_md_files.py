"""
TDD RED Phase Tests for TASK-MTS-010: Create CLAUDE.md files for mcp-typescript template.

These tests validate the existence and content of three documentation files:
1. CLAUDE.md (template root)
2. .claude/CLAUDE.md (nested)
3. README.md (template README)

All tests should FAIL initially until the implementation is complete.
"""

import pytest
from pathlib import Path


# Base path to template (4 levels up from test file to project root)
TEMPLATE_ROOT = Path(__file__).parent.parent.parent.parent / "installer" / "core" / "templates" / "mcp-typescript"


class TestFileExistence:
    """Test that all required documentation files exist."""

    def test_root_claude_md_exists(self):
        """Verify CLAUDE.md exists at template root."""
        claude_md = TEMPLATE_ROOT / "CLAUDE.md"
        assert claude_md.exists(), f"CLAUDE.md not found at {claude_md}"
        assert claude_md.is_file(), f"{claude_md} is not a file"

    def test_nested_claude_md_exists(self):
        """Verify .claude/CLAUDE.md exists in nested location."""
        nested_claude_md = TEMPLATE_ROOT / ".claude" / "CLAUDE.md"
        assert nested_claude_md.exists(), f".claude/CLAUDE.md not found at {nested_claude_md}"
        assert nested_claude_md.is_file(), f"{nested_claude_md} is not a file"

    def test_readme_md_exists(self):
        """Verify README.md exists at template root."""
        readme = TEMPLATE_ROOT / "README.md"
        assert readme.exists(), f"README.md not found at {readme}"
        assert readme.is_file(), f"{readme} is not a file"


class TestRootClaudeMdContent:
    """Test content validation for CLAUDE.md at template root."""

    @pytest.fixture
    def root_claude_content(self):
        """Load root CLAUDE.md content."""
        claude_md = TEMPLATE_ROOT / "CLAUDE.md"
        if not claude_md.exists():
            pytest.skip("CLAUDE.md does not exist yet")
        return claude_md.read_text()

    def test_contains_never_use_console_log(self, root_claude_content):
        """Verify CLAUDE.md contains critical rule about console.log()."""
        assert "NEVER use console.log()" in root_claude_content, \
            "Missing critical rule: 'NEVER use console.log()'"

    def test_contains_register_before_connect_warning(self, root_claude_content):
        """Verify CLAUDE.md contains tool registration warning."""
        content_lower = root_claude_content.lower()
        assert "register" in content_lower and "before" in content_lower and "connect()" in content_lower, \
            "Missing warning about registering tools before connect()"

    def test_contains_absolute_paths_requirement(self, root_claude_content):
        """Verify CLAUDE.md contains absolute paths requirement."""
        content_upper = root_claude_content.upper()
        assert "ABSOLUTE PATHS" in content_upper or "ABSOLUTE PATH" in content_upper, \
            "Missing ABSOLUTE PATHS requirement"

    @pytest.mark.parametrize("command", [
        "npm run dev",
        "npm test",
        "npm run build",
        "npm start",
    ])
    def test_contains_npm_commands(self, root_claude_content, command):
        """Verify CLAUDE.md contains essential npm commands."""
        assert command in root_claude_content, \
            f"Missing npm command: {command}"

    def test_contains_npm_run_test_protocol(self, root_claude_content):
        """Verify CLAUDE.md contains protocol test command."""
        assert "npm run test:protocol" in root_claude_content, \
            "Missing protocol test command: npm run test:protocol"

    def test_contains_project_structure_src_dir(self, root_claude_content):
        """Verify CLAUDE.md shows src/ directory in project structure."""
        assert "src/" in root_claude_content, \
            "Project structure missing src/ directory"

    def test_contains_project_structure_tests_dir(self, root_claude_content):
        """Verify CLAUDE.md shows tests/ directory in project structure."""
        assert "tests/" in root_claude_content, \
            "Project structure missing tests/ directory"

    def test_contains_quality_gates_section(self, root_claude_content):
        """Verify CLAUDE.md contains quality gates section."""
        content_lower = root_claude_content.lower()
        assert "quality gates" in content_lower or "quality gate" in content_lower, \
            "Missing quality gates section"

    def test_contains_all_tests_pass_gate(self, root_claude_content):
        """Verify CLAUDE.md lists 'All tests pass' quality gate."""
        content_lower = root_claude_content.lower()
        assert "all tests pass" in content_lower or "tests pass" in content_lower, \
            "Missing quality gate: All tests pass"

    def test_contains_no_console_log_gate(self, root_claude_content):
        """Verify CLAUDE.md lists 'No console.log' quality gate."""
        content_lower = root_claude_content.lower()
        assert "no console.log" in content_lower, \
            "Missing quality gate: No console.log statements"

    def test_contains_coverage_gate(self, root_claude_content):
        """Verify CLAUDE.md mentions coverage requirement."""
        content_lower = root_claude_content.lower()
        assert "coverage" in content_lower and ("80%" in content_lower or "≥80%" in content_lower), \
            "Missing quality gate: Coverage ≥80%"


class TestNestedClaudeMdContent:
    """Test content validation for .claude/CLAUDE.md (nested)."""

    @pytest.fixture
    def nested_claude_content(self):
        """Load nested .claude/CLAUDE.md content."""
        nested_claude_md = TEMPLATE_ROOT / ".claude" / "CLAUDE.md"
        if not nested_claude_md.exists():
            pytest.skip(".claude/CLAUDE.md does not exist yet")
        return nested_claude_md.read_text()

    def test_contains_10_critical_patterns_section(self, nested_claude_content):
        """Verify .claude/CLAUDE.md contains 10 Critical MCP Patterns section."""
        assert "10 Critical MCP Patterns" in nested_claude_content, \
            "Missing '10 Critical MCP Patterns' section"

    @pytest.mark.parametrize("pattern_keyword", [
        "McpServer",
        "Register before connect",
        "stderr logging",
        "Streaming",
        "Error handling",
        "Zod validation",
        "Absolute paths",
        "ISO timestamps",
        "Protocol testing",
        "Docker non-root",
    ])
    def test_contains_all_10_pattern_keywords(self, nested_claude_content, pattern_keyword):
        """Verify .claude/CLAUDE.md contains all 10 pattern keywords."""
        assert pattern_keyword in nested_claude_content or pattern_keyword.lower() in nested_claude_content.lower(), \
            f"Missing pattern keyword: {pattern_keyword}"

    def test_contains_troubleshooting_section(self, nested_claude_content):
        """Verify .claude/CLAUDE.md contains troubleshooting section."""
        content_lower = nested_claude_content.lower()
        assert "troubleshooting" in content_lower or "troubleshoot" in content_lower, \
            "Missing troubleshooting section"

    def test_contains_tools_not_discovered_troubleshooting(self, nested_claude_content):
        """Verify .claude/CLAUDE.md contains 'Tools not discovered' troubleshooting."""
        content_lower = nested_claude_content.lower()
        assert "tools not discovered" in content_lower or "tool" in content_lower and "not discovered" in content_lower, \
            "Missing troubleshooting: Tools not discovered"

    def test_contains_protocol_corruption_troubleshooting(self, nested_claude_content):
        """Verify .claude/CLAUDE.md contains 'Protocol corruption' troubleshooting."""
        content_lower = nested_claude_content.lower()
        assert "protocol corruption" in content_lower or "protocol" in content_lower and "corrupt" in content_lower, \
            "Missing troubleshooting: Protocol corruption"

    def test_contains_extended_rules_reference(self, nested_claude_content):
        """Verify .claude/CLAUDE.md contains reference to extended rules."""
        content_lower = nested_claude_content.lower()
        assert "extended rules" in content_lower or ".claude/rules" in content_lower, \
            "Missing reference to extended rules"


class TestReadmeMdContent:
    """Test content validation for README.md (template README)."""

    @pytest.fixture
    def readme_content(self):
        """Load README.md content."""
        readme = TEMPLATE_ROOT / "README.md"
        if not readme.exists():
            pytest.skip("README.md does not exist yet")
        return readme.read_text()

    def test_contains_quick_start_section(self, readme_content):
        """Verify README.md contains Quick Start section."""
        content_lower = readme_content.lower()
        assert "quick start" in content_lower or "quickstart" in content_lower, \
            "Missing Quick Start section"

    def test_contains_guardkit_init_command(self, readme_content):
        """Verify README.md contains guardkit init command."""
        assert "guardkit init" in readme_content, \
            "Missing guardkit init command"

    def test_contains_mcp_typescript_template_name(self, readme_content):
        """Verify README.md contains mcp-typescript template name."""
        assert "mcp-typescript" in readme_content, \
            "Missing template name: mcp-typescript"

    def test_contains_features_table(self, readme_content):
        """Verify README.md contains features table."""
        # Check for table markers (markdown table syntax)
        assert "|" in readme_content and "---" in readme_content, \
            "Missing features table (markdown table syntax not found)"

    def test_contains_features_heading(self, readme_content):
        """Verify README.md contains Features section heading."""
        content_lower = readme_content.lower()
        assert "features" in content_lower or "## features" in content_lower or "# features" in content_lower, \
            "Missing Features section heading"

    def test_contains_claude_desktop_configuration(self, readme_content):
        """Verify README.md contains Claude Desktop configuration section."""
        content_lower = readme_content.lower()
        assert "claude desktop" in content_lower, \
            "Missing Claude Desktop configuration section"

    def test_contains_mcp_servers_config_example(self, readme_content):
        """Verify README.md contains mcpServers configuration example."""
        assert "mcpServers" in readme_content, \
            "Missing mcpServers configuration example"

    def test_contains_absolute_path_in_config(self, readme_content):
        """Verify README.md shows absolute paths in configuration example."""
        content_lower = readme_content.lower()
        assert "absolute" in content_lower and "path" in content_lower, \
            "Configuration example should emphasize absolute paths"

    @pytest.mark.parametrize("reference", [
        "modelcontextprotocol.io",
        "MCP Specification",
        "TypeScript SDK",
    ])
    def test_contains_mcp_documentation_references(self, readme_content, reference):
        """Verify README.md contains references to MCP documentation."""
        assert reference in readme_content or reference.lower() in readme_content.lower(), \
            f"Missing reference to: {reference}"


class TestContentQuality:
    """Test overall content quality across all files."""

    @pytest.fixture
    def all_content(self):
        """Load content from all three documentation files."""
        files = {
            "root_claude": TEMPLATE_ROOT / "CLAUDE.md",
            "nested_claude": TEMPLATE_ROOT / ".claude" / "CLAUDE.md",
            "readme": TEMPLATE_ROOT / "README.md",
        }

        content = {}
        for key, path in files.items():
            if not path.exists():
                pytest.skip(f"{path} does not exist yet")
            content[key] = path.read_text()

        return content

    def test_no_emojis_in_any_file(self, all_content):
        """Verify no emojis used unless explicitly requested (GuardKit convention)."""
        emoji_pattern = r'[\U0001F300-\U0001F9FF]'  # Unicode emoji range

        for filename, content in all_content.items():
            # Allow checkmarks (✅) as they're commonly used in quality gates
            # but flag other emojis
            problematic_emojis = [
                '🎉', '🚀', '💡', '⚡', '🔥', '✨', '🎯', '🛠️', '📦', '🔍'
            ]
            for emoji in problematic_emojis:
                assert emoji not in content, \
                    f"Found emoji '{emoji}' in {filename} - emojis should not be used unless explicitly requested"

    def test_all_code_examples_use_bash_fences(self, all_content):
        """Verify all command examples use proper markdown code fences."""
        for filename, content in all_content.items():
            # If content contains npm commands, they should be in code blocks
            if "npm " in content:
                # Simple heuristic: check that npm commands appear after ```
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if "npm " in line and not line.strip().startswith('#'):
                        # Check if there's a code fence above this line (within 3 lines)
                        has_fence = any('```' in lines[j] for j in range(max(0, i-3), i))
                        assert has_fence, \
                            f"npm command in {filename} not in code block: {line.strip()}"

    def test_consistent_heading_levels(self, all_content):
        """Verify markdown heading levels follow proper hierarchy."""
        for filename, content in all_content.items():
            lines = content.split('\n')
            headings = [line for line in lines if line.startswith('#')]

            # Check that we don't jump from # to ### (skipping ##)
            prev_level = 0
            for heading in headings:
                level = len(heading) - len(heading.lstrip('#'))
                if prev_level > 0:
                    assert level <= prev_level + 1, \
                        f"Inconsistent heading levels in {filename}: jumped from {'#' * prev_level} to {'#' * level}"
                prev_level = level


class TestGuardKitConventions:
    """Test adherence to GuardKit documentation conventions."""

    @pytest.fixture
    def root_claude_content(self):
        """Load root CLAUDE.md content."""
        claude_md = TEMPLATE_ROOT / "CLAUDE.md"
        if not claude_md.exists():
            pytest.skip("CLAUDE.md does not exist yet")
        return claude_md.read_text()

    def test_claude_md_starts_with_project_name(self, root_claude_content):
        """Verify CLAUDE.md starts with clear project identification."""
        first_heading = root_claude_content.split('\n')[0:5]
        first_heading_text = '\n'.join(first_heading)
        assert "MCP" in first_heading_text or "TypeScript" in first_heading_text, \
            "CLAUDE.md should start with clear project identification"

    def test_critical_rules_appear_early(self, root_claude_content):
        """Verify critical rules appear in first 30% of document."""
        lines = root_claude_content.split('\n')
        first_30_percent = '\n'.join(lines[:len(lines) // 3])

        assert "NEVER use console.log()" in first_30_percent, \
            "Critical rule about console.log() should appear early in document"

    def test_commands_section_uses_code_blocks(self, root_claude_content):
        """Verify commands section uses proper code blocks."""
        # Find the commands section
        if "## Commands" in root_claude_content or "## Development Commands" in root_claude_content:
            commands_section_start = max(
                root_claude_content.find("## Commands"),
                root_claude_content.find("## Development Commands")
            )
            # Check that there's a code fence after the commands heading
            section_after = root_claude_content[commands_section_start:commands_section_start + 500]
            assert "```" in section_after, \
                "Commands section should use code blocks for command examples"
