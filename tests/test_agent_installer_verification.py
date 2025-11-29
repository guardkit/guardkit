"""Unit tests for agent installer verification functionality (TASK-ENF-P0-3).

Tests the agent verification features added in TASK-ENF-P0-3:
- Agent metadata verification after copy
- Agent discovery testing
- Registered agent reporting
- Missing metadata handling (graceful warnings)
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from commands.lib.agentic_init.agent_installer import (
    install_template_agents,
    _verify_agent_metadata,
    _test_agent_discovery,
    _report_registered_agents
)
from commands.lib.agentic_init.template_discovery import TemplateInfo


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create temporary project directory."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # Create .claude/agents directory
    claude_dir = project_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True)

    return project_dir


@pytest.fixture
def sample_template(tmp_path):
    """Create sample template with agents."""
    template_dir = tmp_path / "test-template"
    template_dir.mkdir()

    # Create manifest
    manifest = {
        "name": "test-template",
        "version": "1.0.0",
        "description": "Test template for agent verification"
    }
    manifest_file = template_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2))

    # Create agents directory with sample agents
    agents_dir = template_dir / "agents"
    agents_dir.mkdir()

    # Agent with complete metadata
    complete_agent = """---
name: test-specialist
stack: [python]
phase: implementation
capabilities:
  - FastAPI endpoint development
  - Async/await patterns
  - Pydantic schema design
  - Dependency injection
  - Error handling
keywords: [fastapi, async, pydantic, api, endpoint]
---

# Test Specialist

Test agent with complete metadata.
"""
    (agents_dir / "test-specialist.md").write_text(complete_agent)

    # Agent with missing metadata
    incomplete_agent = """---
name: incomplete-agent
---

# Incomplete Agent

This agent is missing required discovery metadata.
"""
    (agents_dir / "incomplete-agent.md").write_text(incomplete_agent)

    # Return TemplateInfo
    return TemplateInfo(
        name="test-template",
        version="1.0.0",
        source="test",
        source_path=template_dir,
        description="Test template",
        language="Python",
        frameworks=["pytest"],
        architecture="Test"
    )


class TestAgentMetadataVerification:
    """Tests for agent metadata verification (TASK-ENF-P0-3: FR1)."""

    def test_verify_agent_metadata_all_valid(self, tmp_path, capsys):
        """Test verification when all agents have valid metadata."""
        # Create agent with valid metadata
        agent_file = tmp_path / "valid-agent.md"
        agent_file.write_text("""---
name: valid-agent
stack: [python]
phase: implementation
capabilities: [cap1, cap2, cap3]
keywords: [key1, key2, key3]
---

# Valid Agent
""")

        # Verify
        _verify_agent_metadata([agent_file])

        # Check output
        captured = capsys.readouterr()
        assert "✓ valid-agent: Valid metadata" in captured.out
        assert "All agents have valid discovery metadata" in captured.out

    def test_verify_agent_metadata_missing_fields(self, tmp_path, capsys):
        """Test verification when agent missing required fields."""
        # Create agent with missing stack field
        agent_file = tmp_path / "incomplete-agent.md"
        agent_file.write_text("""---
name: incomplete-agent
phase: implementation
---

# Incomplete Agent
""")

        # Verify
        _verify_agent_metadata([agent_file])

        # Check output
        captured = capsys.readouterr()
        assert "⚠️  Warning: incomplete-agent missing discovery metadata:" in captured.out
        assert "Missing required field: stack" in captured.out
        assert "Missing required field: capabilities" in captured.out
        assert "Missing required field: keywords" in captured.out
        assert "/agent-enhance" in captured.out

    def test_verify_agent_metadata_mixed(self, tmp_path, capsys):
        """Test verification with mix of valid and invalid agents."""
        # Create valid agent
        valid_agent = tmp_path / "valid-agent.md"
        valid_agent.write_text("""---
name: valid-agent
stack: [python]
phase: implementation
capabilities: [cap1, cap2, cap3]
keywords: [key1, key2, key3]
---

# Valid Agent
""")

        # Create invalid agent
        invalid_agent = tmp_path / "invalid-agent.md"
        invalid_agent.write_text("""---
name: invalid-agent
---

# Invalid Agent
""")

        # Verify both
        _verify_agent_metadata([valid_agent, invalid_agent])

        # Check output
        captured = capsys.readouterr()
        assert "✓ valid-agent: Valid metadata" in captured.out
        assert "⚠️  Warning: invalid-agent missing discovery metadata:" in captured.out
        assert "1 agent(s) missing discovery metadata" in captured.out

    def test_verify_agent_metadata_unreadable_file(self, tmp_path, capsys):
        """Test verification handles unreadable files gracefully."""
        # Create file that doesn't exist
        nonexistent = tmp_path / "nonexistent.md"

        # Should not crash
        _verify_agent_metadata([nonexistent])

        # Check output includes warning
        captured = capsys.readouterr()
        assert "⚠️  Warning: Could not read" in captured.out


class TestAgentDiscoveryTest:
    """Tests for agent discovery testing (TASK-ENF-P0-3: FR2)."""

    @patch('commands.lib.agentic_init.agent_installer.discover_agents')
    def test_discovery_test_success(self, mock_discover, temp_project_dir, sample_template, capsys):
        """Test discovery test with successful agent discovery."""
        # Mock discovery to return local agents
        mock_discover.return_value = [
            {
                'name': 'test-specialist',
                'source': 'local',
                'stack': ['python']
            }
        ]

        # Run test
        _test_agent_discovery(sample_template, temp_project_dir)

        # Check output
        captured = capsys.readouterr()
        assert "🧪 Testing agent discovery..." in captured.out
        assert "✅ Agent discovery successful:" in captured.out
        assert "test-specialist" in captured.out

    @patch('commands.lib.agentic_init.agent_installer.discover_agents')
    def test_discovery_test_no_local_agents(self, mock_discover, temp_project_dir, sample_template, capsys):
        """Test discovery test when no local agents found."""
        # Mock discovery to return only global agents
        mock_discover.return_value = [
            {
                'name': 'global-agent',
                'source': 'global',
                'stack': ['python']
            }
        ]

        # Run test
        _test_agent_discovery(sample_template, temp_project_dir)

        # Check output
        captured = capsys.readouterr()
        assert "⚠️  No local agents discovered" in captured.out

    @patch('commands.lib.agentic_init.agent_installer.discover_agents')
    def test_discovery_test_no_agents(self, mock_discover, temp_project_dir, sample_template, capsys):
        """Test discovery test when no agents found."""
        # Mock discovery to return empty list
        mock_discover.return_value = []

        # Run test
        _test_agent_discovery(sample_template, temp_project_dir)

        # Check output
        captured = capsys.readouterr()
        assert "⚠️  No agents discovered" in captured.out

    @patch('commands.lib.agentic_init.agent_installer.discover_agents')
    def test_discovery_test_exception(self, mock_discover, temp_project_dir, sample_template, capsys):
        """Test discovery test handles exceptions gracefully."""
        # Mock discovery to raise exception
        mock_discover.side_effect = Exception("Discovery failed")

        # Should not crash
        _test_agent_discovery(sample_template, temp_project_dir)

        # Check output includes error
        captured = capsys.readouterr()
        assert "⚠️  Agent discovery test failed:" in captured.out


class TestRegisteredAgentReport:
    """Tests for registered agent reporting (TASK-ENF-P0-3: FR3)."""

    def test_report_agents_with_metadata(self, tmp_path, capsys):
        """Test reporting agents with complete metadata."""
        # Create agent with metadata
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text("""---
name: test-agent
stack: [python, typescript]
phase: implementation
capabilities: [cap1, cap2]
keywords: [key1, key2]
---

# Test Agent
""")

        # Report
        _report_registered_agents([agent_file])

        # Check output
        captured = capsys.readouterr()
        assert "Registered Agents" in captured.out
        assert "• test-agent" in captured.out
        assert "Stack: python, typescript" in captured.out
        assert "Phase: implementation" in captured.out

    def test_report_multiple_agents(self, tmp_path, capsys):
        """Test reporting multiple agents."""
        # Create first agent
        agent1 = tmp_path / "agent1.md"
        agent1.write_text("""---
name: agent1
stack: [python]
phase: implementation
capabilities: [cap1]
keywords: [key1]
---

# Agent 1
""")

        # Create second agent
        agent2 = tmp_path / "agent2.md"
        agent2.write_text("""---
name: agent2
stack: [react]
phase: testing
capabilities: [cap1]
keywords: [key1]
---

# Agent 2
""")

        # Report
        _report_registered_agents([agent1, agent2])

        # Check output
        captured = capsys.readouterr()
        assert "• agent1" in captured.out
        assert "Stack: python, Phase: implementation" in captured.out
        assert "• agent2" in captured.out
        assert "Stack: react, Phase: testing" in captured.out

    def test_report_agents_no_metadata(self, tmp_path, capsys):
        """Test reporting when agents have no metadata."""
        # Create agent without metadata
        agent_file = tmp_path / "no-metadata.md"
        agent_file.write_text("# Agent Without Metadata")

        # Report
        _report_registered_agents([agent_file])

        # Check output - should show agent with "unknown" defaults
        captured = capsys.readouterr()
        assert "Registered Agents" in captured.out
        assert "• no-metadata" in captured.out
        assert "Stack: unknown, Phase: unknown" in captured.out


class TestInstallTemplateAgentsIntegration:
    """Integration tests for full install_template_agents flow."""

    @patch('commands.lib.agentic_init.agent_installer.HAS_AGENT_DISCOVERY', True)
    def test_install_with_verification(self, temp_project_dir, sample_template, capsys):
        """Test full installation flow with verification enabled."""
        # Install agents
        install_template_agents(sample_template, temp_project_dir)

        # Check agents were copied
        agents_dir = temp_project_dir / ".claude" / "agents"
        assert (agents_dir / "test-specialist.md").exists()
        assert (agents_dir / "incomplete-agent.md").exists()

        # Check verification ran (output should contain verification messages)
        captured = capsys.readouterr()
        assert "Installing agents..." in captured.out
        assert "Total agents:" in captured.out

    def test_install_no_agents(self, temp_project_dir, tmp_path, capsys):
        """Test installation when template has no agents."""
        # Create template without agents directory
        template_dir = tmp_path / "no-agents-template"
        template_dir.mkdir()

        manifest = {"name": "no-agents-template"}
        (template_dir / "manifest.json").write_text(json.dumps(manifest))

        template = TemplateInfo(
            name="no-agents-template",
            version="1.0.0",
            source="test",
            source_path=template_dir,
            description="Template without agents",
            language="Python",
            frameworks=[],
            architecture=""
        )

        # Install
        install_template_agents(template, temp_project_dir)

        # Check output
        captured = capsys.readouterr()
        assert "Template has no agents" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
