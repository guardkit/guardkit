"""Test CLAUDE.md contains system context command references."""

from pathlib import Path


def test_claude_md_exists():
    """Test that CLAUDE.md exists."""
    claude_md = Path("CLAUDE.md")
    assert claude_md.exists(), "CLAUDE.md not found"


def test_system_context_commands_section():
    """Test that CLAUDE.md contains System Context Commands section."""
    claude_md = Path("CLAUDE.md")

    with open(claude_md) as f:
        content = f.read()

    # Check for the System Context Commands section
    assert "### System Context Commands" in content, "System Context Commands section missing"

    # Check for the three commands
    assert "/system-overview" in content, "/system-overview command reference missing"
    assert "/impact-analysis" in content, "/impact-analysis command reference missing"
    assert "/context-switch" in content, "/context-switch command reference missing"


def test_system_context_command_descriptions():
    """Test that system context commands have descriptions."""
    claude_md = Path("CLAUDE.md")

    with open(claude_md) as f:
        content = f.read()

    # Check for command descriptions
    assert "Architecture summary" in content, "/system-overview description missing"
    assert "Pre-task validation" in content, "/impact-analysis description missing"
    assert "Multi-project navigation" in content, "/context-switch description missing"


def test_key_references_table():
    """Test that CLAUDE.md Key References table includes system context guides."""
    claude_md = Path("CLAUDE.md")

    with open(claude_md) as f:
        content = f.read()

    # Check for Key References section
    assert "## Key References" in content, "Key References section missing"

    # Check for System Context entry in the table
    assert "System Context" in content, "System Context reference missing from Key References"
    assert "system-overview-guide.md" in content, "system-overview-guide.md reference missing"
    assert "impact-analysis-guide.md" in content, "impact-analysis-guide.md reference missing"
    assert "context-switch-guide.md" in content, "context-switch-guide.md reference missing"


def test_command_syntax_examples():
    """Test that system context commands have syntax examples."""
    claude_md = Path("CLAUDE.md")

    with open(claude_md) as f:
        content = f.read()

    # Check for command flags and arguments
    assert "[--verbose]" in content, "--verbose flag missing from /system-overview"
    assert "[--section=SECTION]" in content, "--section flag missing from /system-overview"
    assert "TASK-XXX" in content, "TASK-XXX argument missing from /impact-analysis"
    assert "[--depth=DEPTH]" in content, "--depth flag missing from /impact-analysis"
    assert "[project-name]" in content, "project-name argument missing from /context-switch"
