"""Test CLAUDE.md contains the surviving system context command reference.

/system-overview and /impact-analysis were retired (FEAT-MEM-09 / W1b 60ebde5d,
"pure-graphiti-reader CLI commands"); only /context-switch remains a live
system-context command, so CLAUDE.md should reference just that one.
"""

from pathlib import Path


def test_claude_md_exists():
    """Test that CLAUDE.md exists."""
    claude_md = Path("CLAUDE.md")
    assert claude_md.exists(), "CLAUDE.md not found"


def test_system_context_commands_section():
    """Test that CLAUDE.md contains the System Context Commands section with /context-switch."""
    content = Path("CLAUDE.md").read_text()

    assert "### System Context Commands" in content, "System Context Commands section missing"
    assert "/context-switch" in content, "/context-switch command reference missing"


def test_system_context_command_descriptions():
    """Test that /context-switch has a description."""
    content = Path("CLAUDE.md").read_text()

    assert "Multi-project navigation" in content, "/context-switch description missing"


def test_key_references_table():
    """Test that CLAUDE.md Key References table includes the context-switch guide."""
    content = Path("CLAUDE.md").read_text()

    assert "## Key References" in content, "Key References section missing"
    assert "System Context" in content, "System Context reference missing from Key References"
    assert "context-switch-guide.md" in content, "context-switch-guide.md reference missing"


def test_command_syntax_examples():
    """Test that /context-switch has a syntax example."""
    content = Path("CLAUDE.md").read_text()

    assert "[project-name]" in content, "project-name argument missing from /context-switch"
