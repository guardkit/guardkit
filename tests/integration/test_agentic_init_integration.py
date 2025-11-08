"""Integration tests for agentic-init command.

Tests the complete workflow including:
- Template discovery from multiple sources
- Template selection
- Agent installation with conflict handling
- Project initialization
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from commands.lib.agentic_init.command import (
    agentic_init,
    _copy_template_structure
)
from commands.lib.agentic_init.agent_installer import (
    install_template_agents,
    list_template_agents,
    verify_agent_integrity
)
from commands.lib.agentic_init.template_discovery import TemplateInfo


@pytest.fixture
def integration_setup(tmp_path):
    """Setup complete integration test environment."""
    # Create personal and repository template directories
    personal_dir = tmp_path / "personal_templates"
    repo_dir = tmp_path / "repo_templates"
    project_dir = tmp_path / "test_project"

    personal_dir.mkdir()
    repo_dir.mkdir()
    project_dir.mkdir()

    # Create a personal template
    personal_template = personal_dir / "my-react-template"
    personal_template.mkdir()

    manifest = {
        "name": "my-react-template",
        "version": "2.0.0",
        "description": "Personal React template",
        "language": "TypeScript",
        "frameworks": ["React", "Vite", "Tailwind"],
        "architecture": "Component-based"
    }
    (personal_template / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (personal_template / "settings.json").write_text(json.dumps({"test_coverage": 80}, indent=2))
    (personal_template / "CLAUDE.md").write_text("# Personal React Template\n\nInstructions...")

    # Create agents for personal template
    agents_dir = personal_template / "agents"
    agents_dir.mkdir()
    (agents_dir / "react-specialist.md").write_text("# React Specialist\n\nPersonal version")
    (agents_dir / "test-verifier.md").write_text("# Test Verifier")

    # Create a repository template
    repo_template = repo_dir / "builtin-python"
    repo_template.mkdir()

    manifest = {
        "name": "builtin-python",
        "version": "1.0.0",
        "description": "Built-in Python template",
        "language": "Python",
        "frameworks": ["FastAPI", "pytest"],
        "architecture": "Clean Architecture"
    }
    (repo_template / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # Create agents for repo template
    agents_dir = repo_dir / "builtin-python" / "agents"
    agents_dir.mkdir()
    (agents_dir / "python-specialist.md").write_text("# Python Specialist")

    return {
        "personal_dir": personal_dir,
        "repo_dir": repo_dir,
        "project_dir": project_dir,
        "personal_template": personal_template,
        "repo_template": repo_template
    }


class TestAgentInstallation:
    """Tests for agent installation."""

    def test_install_agents_no_conflicts(self, integration_setup):
        """Test installing agents when no conflicts exist."""
        template = TemplateInfo(
            name="my-react-template",
            version="2.0.0",
            source="personal",
            source_path=integration_setup["personal_template"],
            description="Personal React template",
            language="TypeScript",
            frameworks=["React"],
            architecture="Component-based"
        )

        project_path = integration_setup["project_dir"]

        # Install agents
        install_template_agents(template, project_path)

        # Verify agents were installed
        agents_dir = project_path / ".claude/agents"
        assert agents_dir.exists()
        assert (agents_dir / "react-specialist.md").exists()
        assert (agents_dir / "test-verifier.md").exists()

    def test_install_agents_with_conflict_keep_existing(self, integration_setup):
        """Test installing agents with conflict, keeping existing version."""
        template = TemplateInfo(
            name="my-react-template",
            version="2.0.0",
            source="personal",
            source_path=integration_setup["personal_template"],
            description="Personal React template",
            language="TypeScript",
            frameworks=["React"],
            architecture="Component-based"
        )

        project_path = integration_setup["project_dir"]

        # Create existing agent
        agents_dir = project_path / ".claude/agents"
        agents_dir.mkdir(parents=True)
        existing_agent = agents_dir / "react-specialist.md"
        existing_agent.write_text("# Existing React Specialist\n\nMy custom version")

        # Mock user input to keep existing
        with patch('builtins.input', return_value='a'):
            install_template_agents(template, project_path)

        # Verify existing agent was kept
        content = existing_agent.read_text()
        assert "My custom version" in content
        assert "Personal version" not in content

    def test_list_template_agents(self, integration_setup):
        """Test listing agents from a template."""
        template = TemplateInfo(
            name="my-react-template",
            version="2.0.0",
            source="personal",
            source_path=integration_setup["personal_template"],
            description="Personal React template",
            language="TypeScript",
            frameworks=["React"],
            architecture="Component-based"
        )

        agents = list_template_agents(template)

        assert agents is not None
        assert len(agents) == 2
        assert "react-specialist.md" in agents
        assert "test-verifier.md" in agents

    def test_list_agents_no_agents_directory(self, integration_setup):
        """Test listing agents when template has no agents."""
        # Create template without agents
        template_dir = integration_setup["repo_dir"] / "no-agents-template"
        template_dir.mkdir()

        template = TemplateInfo(
            name="no-agents-template",
            version="1.0.0",
            source="repository",
            source_path=template_dir,
            description="Template without agents",
            language="Python",
            frameworks=[],
            architecture=""
        )

        agents = list_template_agents(template)
        assert agents is None

    def test_verify_agent_integrity_valid(self, integration_setup):
        """Test verifying valid agent file."""
        agent_file = integration_setup["personal_template"] / "agents/react-specialist.md"
        assert verify_agent_integrity(agent_file) is True

    def test_verify_agent_integrity_invalid(self, tmp_path):
        """Test verifying invalid agent files."""
        # Non-existent file
        assert verify_agent_integrity(tmp_path / "nonexistent.md") is False

        # Wrong extension
        wrong_ext = tmp_path / "agent.txt"
        wrong_ext.write_text("content")
        assert verify_agent_integrity(wrong_ext) is False

        # Empty file
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("")
        assert verify_agent_integrity(empty_file) is False


class TestProjectInitialization:
    """Tests for complete project initialization."""

    def test_copy_template_structure(self, integration_setup):
        """Test copying template structure to project."""
        template = TemplateInfo(
            name="my-react-template",
            version="2.0.0",
            source="personal",
            source_path=integration_setup["personal_template"],
            description="Personal React template",
            language="TypeScript",
            frameworks=["React"],
            architecture="Component-based"
        )

        project_path = integration_setup["project_dir"]

        # Copy structure
        success = _copy_template_structure(template, project_path)

        assert success is True

        # Verify files were copied
        assert (project_path / ".claude/manifest.json").exists()
        assert (project_path / ".claude/settings.json").exists()
        assert (project_path / "CLAUDE.md").exists()

        # Verify content
        manifest = json.loads((project_path / ".claude/manifest.json").read_text())
        assert manifest["name"] == "my-react-template"
        assert manifest["version"] == "2.0.0"

    def test_full_initialization_with_template_name(self, integration_setup):
        """Test full initialization specifying template name."""
        # Mock discover_templates to return our test templates
        with patch('commands.lib.agentic_init.command.discover_templates') as mock_discover:
            template = TemplateInfo(
                name="my-react-template",
                version="2.0.0",
                source="personal",
                source_path=integration_setup["personal_template"],
                description="Personal React template",
                language="TypeScript",
                frameworks=["React"],
                architecture="Component-based"
            )
            mock_discover.return_value = [template]

            project_path = integration_setup["project_dir"]

            # Run agentic-init with template name
            success = agentic_init(
                template_name="my-react-template",
                project_path=project_path
            )

            assert success is True

            # Verify project was initialized
            assert (project_path / ".claude").exists()
            assert (project_path / ".claude/manifest.json").exists()
            assert (project_path / "CLAUDE.md").exists()
            assert (project_path / ".claude/agents").exists()

    def test_initialization_no_templates_found(self, integration_setup):
        """Test initialization when no templates are found."""
        with patch('commands.lib.agentic_init.command.discover_templates') as mock_discover:
            mock_discover.return_value = []

            project_path = integration_setup["project_dir"]

            # Run agentic-init
            success = agentic_init(
                template_name="nonexistent",
                project_path=project_path
            )

            assert success is False

    def test_initialization_template_not_found(self, integration_setup):
        """Test initialization when specified template doesn't exist."""
        with patch('commands.lib.agentic_init.command.discover_templates') as mock_discover:
            template = TemplateInfo(
                name="my-react-template",
                version="2.0.0",
                source="personal",
                source_path=integration_setup["personal_template"],
                description="Personal React template",
                language="TypeScript",
                frameworks=["React"],
                architecture="Component-based"
            )
            mock_discover.return_value = [template]

            project_path = integration_setup["project_dir"]

            # Try to initialize with wrong template name
            success = agentic_init(
                template_name="nonexistent-template",
                project_path=project_path
            )

            assert success is False


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_complete_workflow_personal_template(self, integration_setup):
        """Test complete workflow from discovery to initialization."""
        with patch('commands.lib.agentic_init.command.discover_templates') as mock_discover:
            # Setup mock templates
            personal_template = TemplateInfo(
                name="my-react-template",
                version="2.0.0",
                source="personal",
                source_path=integration_setup["personal_template"],
                description="Personal React template",
                language="TypeScript",
                frameworks=["React", "Vite"],
                architecture="Component-based"
            )

            repo_template = TemplateInfo(
                name="builtin-python",
                version="1.0.0",
                source="repository",
                source_path=integration_setup["repo_template"],
                description="Built-in Python template",
                language="Python",
                frameworks=["FastAPI"],
                architecture="Clean Architecture"
            )

            mock_discover.return_value = [personal_template, repo_template]

            project_path = integration_setup["project_dir"]

            # Initialize with personal template
            success = agentic_init(
                template_name="my-react-template",
                project_path=project_path
            )

            assert success is True

            # Verify complete setup
            assert (project_path / ".claude/manifest.json").exists()
            assert (project_path / ".claude/settings.json").exists()
            assert (project_path / "CLAUDE.md").exists()
            assert (project_path / ".claude/agents/react-specialist.md").exists()
            assert (project_path / ".claude/agents/test-verifier.md").exists()

            # Verify manifest content
            manifest = json.loads((project_path / ".claude/manifest.json").read_text())
            assert manifest["name"] == "my-react-template"
            assert manifest["language"] == "TypeScript"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
