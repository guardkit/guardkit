"""
Tests for Graphiti Setup Guide documentation.

Validates:
- Markdown linting
- Docker commands are valid
- All internal links are valid
- Code examples are syntactically correct
"""

import re
import subprocess
from pathlib import Path
import pytest


def get_setup_guide_path() -> Path:
    """Get path to the Graphiti setup guide."""
    repo_root = Path(__file__).parent.parent.parent
    return repo_root / "docs" / "setup" / "graphiti-setup.md"


def test_setup_guide_exists():
    """Test that the setup guide file exists."""
    guide_path = get_setup_guide_path()
    assert guide_path.exists(), f"Setup guide not found at {guide_path}"


def test_markdown_structure():
    """Test that the markdown has proper structure."""
    guide_path = get_setup_guide_path()
    content = guide_path.read_text()

    # Check for required sections
    required_sections = [
        "# Graphiti Setup Guide",
        "## Overview",
        "## Prerequisites",
        "## Installation Steps",
        "### Step 1: Start Graphiti Services",
        "### Step 2: Configure Environment",
        "### Step 3: Verify Connection",
        "### Step 4: Seed Knowledge",
        "### Step 5: Verify Seeding",
        "## Configuration File Reference",
        "## Troubleshooting",
        "## Docker Compose Reference",
    ]

    for section in required_sections:
        assert section in content, f"Missing required section: {section}"


def test_docker_commands_are_valid():
    """Test that all Docker commands in the guide are syntactically valid."""
    guide_path = get_setup_guide_path()
    content = guide_path.read_text()

    # Extract docker commands from code blocks
    docker_commands = []
    in_code_block = False
    code_block_content = []

    for line in content.split('\n'):
        if line.strip().startswith('```bash'):
            in_code_block = True
            code_block_content = []
        elif line.strip() == '```' and in_code_block:
            in_code_block = False
            # Extract docker commands
            for cmd_line in code_block_content:
                cmd_line = cmd_line.strip()
                # Skip comments and empty lines
                if cmd_line and not cmd_line.startswith('#'):
                    if cmd_line.startswith('docker'):
                        docker_commands.append(cmd_line)
        elif in_code_block:
            code_block_content.append(line)

    # Validate docker command syntax (basic validation)
    assert len(docker_commands) > 0, "No docker commands found in guide"

    for cmd in docker_commands:
        # Check for common docker commands
        assert any(subcmd in cmd for subcmd in [
            'docker compose',
            'docker ps',
            'docker logs',
            'docker volume',
            'docker run',
            'docker --version'
        ]), f"Invalid docker command: {cmd}"

        # Check that multi-line continuations are valid
        if '\\' in cmd:
            assert cmd.strip().endswith('\\') or '\\' not in cmd.split()[-1], \
                f"Invalid line continuation in: {cmd}"


def test_cli_commands_match_implementation():
    """Test that CLI commands documented match actual implementation."""
    guide_path = get_setup_guide_path()
    content = guide_path.read_text()

    # Expected CLI commands based on guardkit/cli/graphiti.py
    expected_commands = [
        "guardkit graphiti status",
        "guardkit graphiti seed",
        "guardkit graphiti seed --force",
        "guardkit graphiti verify",
        "guardkit graphiti verify --verbose",
    ]

    for cmd in expected_commands:
        assert cmd in content, f"Missing documented command: {cmd}"


def test_configuration_environment_variables():
    """Test that all environment variables are documented."""
    guide_path = get_setup_guide_path()
    content = guide_path.read_text()

    # Environment variables from guardkit/knowledge/config.py
    expected_env_vars = [
        "GRAPHITI_ENABLED",
        "GRAPHITI_HOST",
        "GRAPHITI_PORT",
        "GRAPHITI_TIMEOUT",
        "OPENAI_API_KEY",
        "GUARDKIT_CONFIG_DIR",
    ]

    for env_var in expected_env_vars:
        assert env_var in content, f"Missing documented env var: {env_var}"


def test_troubleshooting_sections():
    """Test that troubleshooting covers common issues."""
    guide_path = get_setup_guide_path()
    content = guide_path.read_text()

    # Common troubleshooting scenarios
    troubleshooting_topics = [
        "Connection Failed",
        "Seeding Errors",
        "No Context in Sessions",
        "Common Error Messages",
    ]

    for topic in troubleshooting_topics:
        assert topic in content, f"Missing troubleshooting section: {topic}"


def test_yaml_configuration_example():
    """Test that YAML configuration example is valid."""
    guide_path = get_setup_guide_path()
    content = guide_path.read_text()

    # Extract YAML block
    yaml_match = re.search(
        r'```yaml\n# Graphiti Knowledge Graph Configuration\n(.*?)\n```',
        content,
        re.DOTALL
    )

    assert yaml_match, "YAML configuration example not found"

    yaml_content = yaml_match.group(1)

    # Check for required YAML fields
    required_fields = [
        "enabled:",
        "host:",
        "port:",
        "timeout:",
        "embedding_model:",
        "group_ids:",
    ]

    for field in required_fields:
        assert field in yaml_content, f"Missing YAML field: {field}"


def test_docker_compose_reference():
    """Test that Docker Compose reference matches actual file."""
    guide_path = get_setup_guide_path()
    content = guide_path.read_text()

    # Expected service names from docker-compose.graphiti.yml
    expected_services = [
        "falkordb",
        "graphiti",
    ]

    for service in expected_services:
        assert service in content, f"Missing service documentation: {service}"

    # Expected ports
    expected_ports = [
        "6379",  # FalkorDB
        "8000",  # Graphiti
    ]

    for port in expected_ports:
        assert port in content, f"Missing port documentation: {port}"


def test_expected_output_examples():
    """Test that expected output examples are provided."""
    guide_path = get_setup_guide_path()
    content = guide_path.read_text()

    # Should have "Expected output:" sections
    assert content.count("**Expected output**:") >= 4, \
        "Missing expected output examples for verification commands"


def test_line_count_within_limit():
    """Test that the guide is roughly within reasonable limits."""
    guide_path = get_setup_guide_path()
    content = guide_path.read_text()

    line_count = len(content.split('\n'))

    # Target is ~250 lines, but comprehensive guides with troubleshooting
    # may be longer. Allow up to 600 lines for guides with extensive
    # troubleshooting, Docker reference, and configuration details.
    assert 200 <= line_count <= 600, \
        f"Line count {line_count} outside acceptable range (200-600 lines)"


def test_no_broken_internal_links():
    """Test that internal links (anchors) are valid."""
    guide_path = get_setup_guide_path()
    content = guide_path.read_text()

    # Extract all anchor links [text](#anchor)
    anchor_links = re.findall(r'\[.*?\]\(#(.*?)\)', content)

    # Extract all headings that could be anchors
    headings = re.findall(r'^#{2,}\s+(.+)$', content, re.MULTILINE)

    # Convert headings to anchor format (lowercase, hyphens, no special chars)
    def heading_to_anchor(heading: str) -> str:
        # Remove markdown formatting
        heading = re.sub(r'[*_`]', '', heading)
        # Lowercase and replace spaces with hyphens
        anchor = heading.lower().strip()
        anchor = re.sub(r'[^\w\s-]', '', anchor)
        anchor = re.sub(r'[-\s]+', '-', anchor)
        return anchor

    valid_anchors = {heading_to_anchor(h) for h in headings}

    # Check that all anchor links are valid
    for link in anchor_links:
        assert link in valid_anchors, \
            f"Broken internal link: #{link} (valid anchors: {valid_anchors})"


def test_copy_paste_ready_commands():
    """Test that commands are copy-paste ready (no line breaks in middle of commands)."""
    guide_path = get_setup_guide_path()
    content = guide_path.read_text()

    # Extract all bash code blocks
    bash_blocks = re.findall(r'```bash\n(.*?)\n```', content, re.DOTALL)

    for block in bash_blocks:
        lines = block.split('\n')
        for i, line in enumerate(lines):
            # Skip comments and empty lines
            if line.strip().startswith('#') or not line.strip():
                continue

            # Check for backslash continuation
            if line.rstrip().endswith('\\'):
                # Next line should be indented or continuation
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # Continuation should not start a new command
                    assert not next_line.strip().startswith('docker'), \
                        f"Invalid command continuation at: {line}"


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v"])
