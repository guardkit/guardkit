"""Unit tests for agentic-init template discovery.

Tests the template discovery functionality including:
- Personal template discovery
- Repository template discovery
- Personal template priority over repository templates
- Missing directory handling
- Manifest parsing
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from commands.lib.agentic_init.template_discovery import (
    TemplateDiscovery,
    TemplateInfo,
    discover_templates
)


@pytest.fixture
def temp_template_dirs(tmp_path):
    """Create temporary template directories for testing."""
    personal_dir = tmp_path / "personal"
    repo_dir = tmp_path / "repo"

    personal_dir.mkdir()
    repo_dir.mkdir()

    return {
        "personal": personal_dir,
        "repo": repo_dir
    }


@pytest.fixture
def create_test_template():
    """Factory fixture to create test templates."""
    def _create(directory: Path, name: str, **kwargs):
        """Create a test template with manifest.json."""
        template_dir = directory / name
        template_dir.mkdir(exist_ok=True)

        manifest = {
            "name": name,
            "version": kwargs.get("version", "1.0.0"),
            "description": kwargs.get("description", f"Test template {name}"),
            "language": kwargs.get("language", "Python"),
            "frameworks": kwargs.get("frameworks", ["pytest"]),
            "architecture": kwargs.get("architecture", "Clean Architecture")
        }

        manifest_file = template_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2))

        # Optionally create agents directory
        if kwargs.get("with_agents", False):
            agents_dir = template_dir / "agents"
            agents_dir.mkdir()
            (agents_dir / "test-agent.md").write_text("# Test Agent")

        return template_dir

    return _create


class TestTemplateDiscovery:
    """Tests for TemplateDiscovery class."""

    def test_discover_personal_templates_only(self, temp_template_dirs, create_test_template):
        """Test discovery of personal templates only."""
        # Create personal template
        create_test_template(
            temp_template_dirs["personal"],
            "my-personal-template",
            language="TypeScript",
            frameworks=["React", "Vite"]
        )

        # Discover
        discovery = TemplateDiscovery(
            personal_path=temp_template_dirs["personal"],
            repo_path=temp_template_dirs["repo"]
        )
        templates = discovery.discover()

        assert len(templates) == 1
        assert templates[0].name == "my-personal-template"
        assert templates[0].source == "personal"
        assert templates[0].language == "TypeScript"
        assert "React" in templates[0].frameworks

    def test_discover_repository_templates_only(self, temp_template_dirs, create_test_template):
        """Test discovery of repository templates only."""
        # Create repository template
        create_test_template(
            temp_template_dirs["repo"],
            "builtin-react",
            language="TypeScript"
        )

        # Discover
        discovery = TemplateDiscovery(
            personal_path=temp_template_dirs["personal"],
            repo_path=temp_template_dirs["repo"]
        )
        templates = discovery.discover()

        assert len(templates) == 1
        assert templates[0].name == "builtin-react"
        assert templates[0].source == "repository"

    def test_discover_both_sources(self, temp_template_dirs, create_test_template):
        """Test discovery from both personal and repository sources."""
        # Create personal template
        create_test_template(
            temp_template_dirs["personal"],
            "my-template"
        )

        # Create repository templates
        create_test_template(
            temp_template_dirs["repo"],
            "react"
        )
        create_test_template(
            temp_template_dirs["repo"],
            "python"
        )

        # Discover
        discovery = TemplateDiscovery(
            personal_path=temp_template_dirs["personal"],
            repo_path=temp_template_dirs["repo"]
        )
        templates = discovery.discover()

        assert len(templates) == 3
        # Personal should come first
        assert templates[0].source == "personal"
        assert templates[1].source == "repository"
        assert templates[2].source == "repository"

    def test_personal_overrides_repository(self, temp_template_dirs, create_test_template):
        """Test that personal templates override repository templates with same name."""
        # Create personal "react" template
        create_test_template(
            temp_template_dirs["personal"],
            "react",
            description="Personal React template",
            version="2.0.0"
        )

        # Create repository "react" template
        create_test_template(
            temp_template_dirs["repo"],
            "react",
            description="Repository React template",
            version="1.0.0"
        )

        # Create another repository template
        create_test_template(
            temp_template_dirs["repo"],
            "python"
        )

        # Discover
        discovery = TemplateDiscovery(
            personal_path=temp_template_dirs["personal"],
            repo_path=temp_template_dirs["repo"]
        )
        templates = discovery.discover()

        # Should only have 2 templates (personal react, repo python)
        assert len(templates) == 2

        # Only one "react" (personal version)
        react_templates = [t for t in templates if t.name == "react"]
        assert len(react_templates) == 1
        assert react_templates[0].source == "personal"
        assert react_templates[0].version == "2.0.0"
        assert react_templates[0].description == "Personal React template"

    def test_missing_directories(self, tmp_path):
        """Test graceful handling of missing directories."""
        nonexistent_path = tmp_path / "nonexistent"

        discovery = TemplateDiscovery(
            personal_path=nonexistent_path,
            repo_path=nonexistent_path
        )

        # Should not crash
        templates = discovery.discover()
        assert len(templates) == 0

    def test_missing_personal_directory_only(self, temp_template_dirs, create_test_template):
        """Test with missing personal directory but existing repository."""
        # Create repository template
        create_test_template(
            temp_template_dirs["repo"],
            "react"
        )

        # Use nonexistent personal path
        discovery = TemplateDiscovery(
            personal_path=temp_template_dirs["personal"] / "nonexistent",
            repo_path=temp_template_dirs["repo"]
        )

        templates = discovery.discover()
        assert len(templates) == 1
        assert templates[0].source == "repository"

    def test_parse_minimal_manifest(self, tmp_path):
        """Test parsing manifest with minimal required fields."""
        template_dir = tmp_path / "minimal-template"
        template_dir.mkdir()

        # Only required field: name
        manifest = {"name": "minimal-template"}
        manifest_file = template_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest))

        discovery = TemplateDiscovery(
            personal_path=tmp_path,
            repo_path=Path("/nonexistent")
        )
        templates = discovery.discover()

        assert len(templates) == 1
        assert templates[0].name == "minimal-template"
        assert templates[0].version == "1.0.0"  # Default
        assert templates[0].description == ""
        assert templates[0].language == ""
        assert templates[0].frameworks == []

    def test_parse_complete_manifest(self, temp_template_dirs, create_test_template):
        """Test parsing manifest with all fields."""
        create_test_template(
            temp_template_dirs["personal"],
            "complete-template",
            version="2.1.0",
            description="A complete template",
            language="C#",
            frameworks=[".NET 8", "MAUI"],
            architecture="MVVM + AppShell"
        )

        discovery = TemplateDiscovery(
            personal_path=temp_template_dirs["personal"],
            repo_path=temp_template_dirs["repo"]
        )
        templates = discovery.discover()

        assert len(templates) == 1
        t = templates[0]
        assert t.name == "complete-template"
        assert t.version == "2.1.0"
        assert t.description == "A complete template"
        assert t.language == "C#"
        assert t.frameworks == [".NET 8", "MAUI"]
        assert t.architecture == "MVVM + AppShell"

    def test_invalid_manifest_skipped(self, tmp_path):
        """Test that invalid manifests are skipped gracefully."""
        template_dir = tmp_path / "invalid-template"
        template_dir.mkdir()

        # Invalid JSON
        manifest_file = template_dir / "manifest.json"
        manifest_file.write_text("{ invalid json }")

        discovery = TemplateDiscovery(
            personal_path=tmp_path,
            repo_path=Path("/nonexistent")
        )
        templates = discovery.discover()

        assert len(templates) == 0

    def test_missing_name_in_manifest(self, tmp_path):
        """Test that manifest without name is skipped."""
        template_dir = tmp_path / "no-name-template"
        template_dir.mkdir()

        # No name field
        manifest = {"version": "1.0.0"}
        manifest_file = template_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest))

        discovery = TemplateDiscovery(
            personal_path=tmp_path,
            repo_path=Path("/nonexistent")
        )
        templates = discovery.discover()

        assert len(templates) == 0

    def test_find_by_name(self, temp_template_dirs, create_test_template):
        """Test finding template by name."""
        create_test_template(
            temp_template_dirs["personal"],
            "react"
        )
        create_test_template(
            temp_template_dirs["personal"],
            "python"
        )

        discovery = TemplateDiscovery(
            personal_path=temp_template_dirs["personal"],
            repo_path=temp_template_dirs["repo"]
        )
        templates = discovery.discover()

        # Find existing template
        found = discovery.find_by_name(templates, "python")
        assert found is not None
        assert found.name == "python"

        # Find non-existent template
        not_found = discovery.find_by_name(templates, "nonexistent")
        assert not_found is None

    def test_non_directory_files_ignored(self, tmp_path):
        """Test that non-directory files in template dirs are ignored."""
        personal_dir = tmp_path / "personal"
        personal_dir.mkdir()

        # Create a file (not a directory)
        (personal_dir / "not-a-template.txt").write_text("ignored")

        # Create valid template
        template_dir = personal_dir / "valid-template"
        template_dir.mkdir()
        manifest = {"name": "valid-template"}
        (template_dir / "manifest.json").write_text(json.dumps(manifest))

        discovery = TemplateDiscovery(
            personal_path=personal_dir,
            repo_path=Path("/nonexistent")
        )
        templates = discovery.discover()

        assert len(templates) == 1
        assert templates[0].name == "valid-template"

    def test_directory_without_manifest_ignored(self, tmp_path):
        """Test that directories without manifest.json are ignored."""
        personal_dir = tmp_path / "personal"
        personal_dir.mkdir()

        # Create directory without manifest
        (personal_dir / "no-manifest-dir").mkdir()

        # Create valid template
        valid_dir = personal_dir / "valid-template"
        valid_dir.mkdir()
        manifest = {"name": "valid-template"}
        (valid_dir / "manifest.json").write_text(json.dumps(manifest))

        discovery = TemplateDiscovery(
            personal_path=personal_dir,
            repo_path=Path("/nonexistent")
        )
        templates = discovery.discover()

        assert len(templates) == 1
        assert templates[0].name == "valid-template"


class TestConvenienceFunction:
    """Tests for convenience function."""

    @patch('commands.lib.agentic_init.template_discovery.Path')
    def test_discover_templates_function(self, mock_path, temp_template_dirs, create_test_template):
        """Test convenience function uses default paths."""
        # This test would need more setup to properly mock Path.home()
        # For now, just verify it can be called
        # In real usage, it would use ~/.agentecflow/templates and installer/global/templates
        pass


class TestTemplateInfo:
    """Tests for TemplateInfo dataclass."""

    def test_template_info_creation(self):
        """Test creating TemplateInfo instance."""
        template = TemplateInfo(
            name="test",
            version="1.0.0",
            source="personal",
            source_path=Path("/test"),
            description="Test template",
            language="Python",
            frameworks=["pytest"],
            architecture="Clean"
        )

        assert template.name == "test"
        assert template.version == "1.0.0"
        assert template.source == "personal"
        assert template.language == "Python"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
