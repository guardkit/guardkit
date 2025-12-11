"""
Unit tests for agent markdown formatter.

Tests YAML frontmatter formatting and markdown body generation.
"""

import pytest
import yaml

# Import from agent_generator directory
from installer.core.lib.agent_generator.markdown_formatter import format_agent_markdown


def test_format_agent_markdown_basic():
    """Test basic agent formatting with all required fields."""
    agent = {
        "name": "test-specialist",
        "description": "Test description for specialist agent",
        "reason": "Test reason for agent existence",
        "technologies": ["Python", "pytest", "FastAPI"],
        "priority": 8
    }

    result = format_agent_markdown(agent)

    # Verify structure
    assert result.startswith("---\n"), "Should start with YAML frontmatter delimiter"
    assert "---\n\n#" in result, "Should have frontmatter followed by markdown body"

    # Verify frontmatter fields
    assert "name: test-specialist" in result
    assert "description: Test description for specialist agent" in result
    assert "priority: 8" in result

    # Verify YAML list syntax (NOT comma-separated)
    assert "  - Python" in result, "Should use YAML list syntax with dash"
    assert "  - pytest" in result
    assert "  - FastAPI" in result
    assert "Python, pytest" not in result, "Should NOT use comma-separated format"

    # Verify markdown sections
    assert "# Test Specialist" in result
    assert "## Purpose" in result
    assert "## Why This Agent Exists" in result
    assert "## Technologies" in result
    assert "## Usage" in result


def test_format_agent_markdown_yaml_parseable():
    """Test that generated YAML frontmatter is valid and parseable."""
    agent = {
        "name": "api-specialist",
        "description": "API development specialist",
        "reason": "Project needs API expertise",
        "technologies": ["Python", "FastAPI", "Pydantic"],
        "priority": 9
    }

    result = format_agent_markdown(agent)

    # Extract YAML frontmatter
    lines = result.split('\n')
    assert lines[0] == "---", "Should start with ---"

    # Find end of frontmatter
    frontmatter_end = None
    for i, line in enumerate(lines[1:], start=1):
        if line == "---":
            frontmatter_end = i
            break

    assert frontmatter_end is not None, "Should have closing ---"

    # Parse YAML
    yaml_content = '\n'.join(lines[1:frontmatter_end])
    parsed = yaml.safe_load(yaml_content)

    # Verify parsed structure
    assert parsed['name'] == 'api-specialist'
    assert parsed['description'] == 'API development specialist'
    assert parsed['priority'] == 9
    assert isinstance(parsed['technologies'], list), "technologies should be parsed as list"
    assert parsed['technologies'] == ['Python', 'FastAPI', 'Pydantic']


def test_format_agent_markdown_missing_fields():
    """Test handling of missing optional fields."""
    agent = {
        "name": "minimal-agent"
        # Missing description, reason, technologies, priority
    }

    result = format_agent_markdown(agent)

    # Should still generate valid structure
    assert result.startswith("---\n")
    assert "name: minimal-agent" in result
    assert "description: " in result  # Empty but present
    assert "priority: 5" in result  # Default value
    assert "technologies:" in result  # Empty list


def test_format_agent_markdown_empty_technologies():
    """Test formatting with empty technologies list."""
    agent = {
        "name": "test-agent",
        "description": "Test agent",
        "reason": "Test reason",
        "technologies": [],
        "priority": 5
    }

    result = format_agent_markdown(agent)

    # Should have technologies field but no items
    assert "technologies:" in result
    # Should not have any technology items
    assert "  -" not in result or result.count("  -") == 0


def test_format_agent_markdown_special_characters():
    """Test formatting with special characters in fields."""
    agent = {
        "name": "special-agent",
        "description": "Agent with: special, characters & symbols",
        "reason": "Reason with 'quotes' and \"double quotes\"",
        "technologies": ["C#", ".NET", "ASP.NET Core"],
        "priority": 7
    }

    result = format_agent_markdown(agent)

    # Should handle special characters in YAML
    assert "name: special-agent" in result
    assert "C#" in result
    assert ".NET" in result
    assert "ASP.NET Core" in result


def test_format_agent_markdown_hyphenated_name():
    """Test that hyphenated names are converted to title case in headers."""
    agent = {
        "name": "maui-viewmodel-specialist",
        "description": "MAUI ViewModel specialist",
        "reason": "MVVM pattern support",
        "technologies": ["C#", "MAUI", "MVVM"],
        "priority": 10
    }

    result = format_agent_markdown(agent)

    # Verify title formatting
    assert "# Maui Viewmodel Specialist" in result
    assert "## Purpose" in result


def test_format_agent_markdown_high_priority():
    """Test formatting with high priority agent."""
    agent = {
        "name": "critical-agent",
        "description": "Critical system agent",
        "reason": "Core functionality",
        "technologies": ["TypeScript", "React", "Next.js"],
        "priority": 10
    }

    result = format_agent_markdown(agent)

    assert "priority: 10" in result
    assert "TypeScript" in result
    assert "React" in result
    assert "Next.js" in result


def test_format_agent_markdown_usage_section():
    """Test that usage section includes agent name."""
    agent = {
        "name": "test-framework-specialist",
        "description": "Testing framework specialist",
        "reason": "Test automation needs",
        "technologies": ["pytest", "unittest"],
        "priority": 6
    }

    result = format_agent_markdown(agent)

    # Usage section should mention the agent name
    assert "## Usage" in result
    assert "test framework specialist" in result.lower()
    assert "/task-work" in result


def test_format_agent_markdown_technologies_section():
    """Test that technologies are listed in both frontmatter and body."""
    agent = {
        "name": "database-specialist",
        "description": "Database specialist",
        "reason": "Database operations",
        "technologies": ["PostgreSQL", "SQLAlchemy", "Alembic"],
        "priority": 8
    }

    result = format_agent_markdown(agent)

    # Frontmatter should have YAML list format
    assert "technologies:\n  - PostgreSQL\n  - SQLAlchemy\n  - Alembic" in result

    # Body should have markdown bullet list
    assert "## Technologies" in result
    assert "- PostgreSQL" in result
    assert "- SQLAlchemy" in result
    assert "- Alembic" in result
