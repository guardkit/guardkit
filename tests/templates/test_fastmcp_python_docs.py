"""
Tests for fastmcp-python template CLAUDE.md documentation quality.
"""
import os
import pytest
from pathlib import Path


class TestFastMCPPythonDocs:
    """Test suite for fastmcp-python template documentation."""

    @pytest.fixture
    def template_dir(self):
        """Get template directory path."""
        return Path("installer/core/templates/fastmcp-python")

    @pytest.fixture
    def top_level_claude_md(self, template_dir):
        """Get top-level CLAUDE.md path."""
        return template_dir / "CLAUDE.md"

    @pytest.fixture
    def nested_claude_md(self, template_dir):
        """Get .claude/CLAUDE.md path."""
        return template_dir / ".claude" / "CLAUDE.md"

    @pytest.fixture
    def readme_md(self, template_dir):
        """Get README.md path."""
        return template_dir / "README.md"

    def test_top_level_claude_md_exists(self, top_level_claude_md):
        """AC-001: Top-level CLAUDE.md file exists."""
        assert top_level_claude_md.exists(), "Top-level CLAUDE.md must exist"

    def test_nested_claude_md_exists(self, nested_claude_md):
        """AC-002: .claude/CLAUDE.md file exists."""
        assert nested_claude_md.exists(), ".claude/CLAUDE.md must exist"

    def test_readme_md_exists(self, readme_md):
        """AC-003: README.md file exists."""
        assert readme_md.exists(), "README.md must exist"

    def test_top_level_has_template_overview(self, top_level_claude_md):
        """AC-004: Top-level CLAUDE.md has template overview and purpose."""
        content = top_level_claude_md.read_text()
        assert "FastMCP Python Server Template" in content
        assert "Project Context" in content
        assert "MCP" in content or "Model Context Protocol" in content

    def test_top_level_has_quick_start(self, top_level_claude_md):
        """AC-005: Top-level CLAUDE.md has quick start guide."""
        content = top_level_claude_md.read_text()
        assert "Getting Started" in content or "Quick Start" in content
        assert "guardkit init" in content or "Initialize" in content

    def test_top_level_has_10_critical_patterns(self, top_level_claude_md):
        """AC-006: Top-level CLAUDE.md links to 10 critical patterns."""
        content = top_level_claude_md.read_text()
        assert "10 Critical Patterns" in content or "Critical Pattern" in content
        # Verify key patterns mentioned
        assert "Tool Registration" in content
        assert "Logging to stderr" in content or "stderr" in content
        assert "Streaming" in content or "Stream" in content
        assert "CancelledError" in content
        assert "String Parameter" in content or "Parameter Conversion" in content

    def test_top_level_has_agent_discovery_keywords(self, top_level_claude_md):
        """AC-007: Top-level CLAUDE.md has agent discovery keywords."""
        content = top_level_claude_md.read_text()
        assert "Specialized Agents" in content or "agents" in content.lower()
        assert "fastmcp-specialist" in content or "fastmcp" in content

    def test_top_level_has_common_commands(self, top_level_claude_md):
        """AC-008: Top-level CLAUDE.md has common commands."""
        content = top_level_claude_md.read_text()
        assert "pytest" in content
        assert "python -m src" in content or "Run" in content

    def test_nested_has_project_context(self, nested_claude_md):
        """AC-009: .claude/CLAUDE.md has project context."""
        content = nested_claude_md.read_text()
        assert "Project Context" in content
        assert "MCP" in content or "Model Context Protocol" in content

    def test_nested_has_core_principles(self, nested_claude_md):
        """AC-010: .claude/CLAUDE.md has core principles."""
        content = nested_claude_md.read_text()
        assert "Core Principles" in content or "Principles" in content
        # Check for MCP-specific principles
        assert "protocol" in content.lower() or "Protocol" in content
        assert "async" in content.lower() or "Async" in content
        assert "testing" in content.lower() or "Testing" in content

    def test_nested_has_patterns_reference(self, nested_claude_md):
        """AC-011: .claude/CLAUDE.md has quick reference to patterns."""
        content = nested_claude_md.read_text()
        assert "Pattern" in content
        assert ".claude/rules/mcp-patterns.md" in content or "mcp-patterns" in content

    def test_nested_has_agent_links(self, nested_claude_md):
        """AC-012: .claude/CLAUDE.md links to agents and rules."""
        content = nested_claude_md.read_text()
        assert "agent" in content.lower() or "Agent" in content
        assert "rules" in content.lower() or ".claude/rules" in content

    def test_readme_has_description(self, readme_md):
        """AC-013: README.md has template description."""
        content = readme_md.read_text()
        assert "FastMCP" in content
        assert "MCP" in content or "Model Context Protocol" in content
        assert "template" in content.lower() or "Template" in content

    def test_readme_has_installation(self, readme_md):
        """AC-014: README.md has installation instructions."""
        content = readme_md.read_text()
        assert "Installation" in content or "Install" in content
        assert "guardkit init fastmcp-python" in content

    def test_readme_has_directory_structure(self, readme_md):
        """AC-015: README.md has directory structure explanation."""
        content = readme_md.read_text()
        assert "Directory Structure" in content or "Structure" in content
        assert "src/" in content
        assert "tests/" in content

    def test_readme_has_getting_started(self, readme_md):
        """AC-016: README.md has getting started guide."""
        content = readme_md.read_text()
        assert "Getting Started" in content or "Quick Start" in content
        assert "python" in content or "pytest" in content

    def test_readme_has_mcp_docs_links(self, readme_md):
        """AC-017: README.md has links to MCP documentation."""
        content = readme_md.read_text()
        assert "modelcontextprotocol.io" in content or "fastmcp" in content.lower()
        assert "Documentation" in content or "Resources" in content

    def test_readme_has_quality_scores(self, readme_md):
        """AC-018: README.md has quality scores and complexity rating."""
        content = readme_md.read_text()
        assert "Quality" in content
        assert "SOLID" in content or "DRY" in content or "YAGNI" in content
        assert "Complexity" in content or "complexity" in content

    def test_top_level_has_architecture_overview(self, top_level_claude_md):
        """AC-019: Top-level CLAUDE.md has architecture overview."""
        content = top_level_claude_md.read_text()
        assert "Architecture" in content
        assert "src/" in content
        assert "__main__.py" in content

    def test_top_level_has_technology_stack(self, top_level_claude_md):
        """AC-020: Top-level CLAUDE.md has technology stack."""
        content = top_level_claude_md.read_text()
        assert "Technology Stack" in content or "Stack" in content
        assert "FastMCP" in content
        assert "Pydantic" in content
        assert "pytest" in content

    def test_all_files_have_minimum_content(self, top_level_claude_md, nested_claude_md, readme_md):
        """AC-021: All files have substantial content (>1000 chars)."""
        assert len(top_level_claude_md.read_text()) > 1000, "Top-level CLAUDE.md too short"
        assert len(nested_claude_md.read_text()) > 1000, ".claude/CLAUDE.md too short"
        assert len(readme_md.read_text()) > 1000, "README.md too short"

    def test_files_mention_10_patterns(self, top_level_claude_md):
        """AC-022: Documentation mentions all 10 critical patterns."""
        content = top_level_claude_md.read_text()

        patterns = [
            "Tool Registration",
            "stderr",
            "Streaming",
            "CancelledError",
            "String Parameter",
            "DateTime",
            "FastMCP",
            "Error",
            "Resource URI",
            "Async Context"
        ]

        for pattern in patterns:
            assert pattern in content, f"Missing critical pattern: {pattern}"

    def test_consistent_naming_conventions(self, top_level_claude_md):
        """AC-023: Documentation shows consistent naming conventions."""
        content = top_level_claude_md.read_text()
        assert "snake_case" in content
        assert "camelCase" in content
        assert "kebab-case" in content or "kebab" in content

    def test_code_examples_present(self, top_level_claude_md, nested_claude_md, readme_md):
        """AC-024: All docs have code examples."""
        for file_path in [top_level_claude_md, nested_claude_md, readme_md]:
            content = file_path.read_text()
            # Check for Python code blocks
            assert "```python" in content, f"{file_path.name} missing Python code examples"
            # Check for MCP-specific examples
            assert "@mcp.tool()" in content or "mcp" in content.lower()

    def test_references_to_rules(self, top_level_claude_md, nested_claude_md):
        """AC-025: Documentation references .claude/rules/ files."""
        for file_path in [top_level_claude_md, nested_claude_md]:
            content = file_path.read_text()
            assert ".claude/rules" in content or "rules/" in content

    def test_agent_response_format_mentioned(self, top_level_claude_md):
        """AC-026: Top-level CLAUDE.md mentions agent response format."""
        content = top_level_claude_md.read_text()
        assert "Agent Response Format" in content or ".agent-response.json" in content
