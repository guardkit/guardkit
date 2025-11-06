"""
Tests for Template Update/Merge Functionality

Tests conflict detection, merge strategies, customization preservation, and version updates.

TASK-012: Template Packaging & Distribution (Sub-task 3: TASK-063)
"""

import json
from pathlib import Path
import pytest
import tempfile
import shutil

from template_merger import (
    TemplateMerger,
    MergeStrategy,
    MergeResult,
    detect_existing_template
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def existing_template(temp_dir):
    """Create existing template directory."""
    template_path = temp_dir / "existing" / "test-template"
    template_path.mkdir(parents=True)

    # Create manifest
    manifest = {
        "template": {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Existing template"
        }
    }

    with open(template_path / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # Create some files
    (template_path / "templates").mkdir()
    (template_path / "templates" / "old.template").write_text("Old template")

    # Create agents
    (template_path / "agents").mkdir()
    (template_path / "agents" / "standard-agent.md").write_text("# Standard Agent")
    (template_path / "agents" / "custom-agent.md").write_text("# Custom Agent")

    return template_path


@pytest.fixture
def new_template(temp_dir):
    """Create new template directory."""
    template_path = temp_dir / "new" / "test-template"
    template_path.mkdir(parents=True)

    # Create manifest with same name but newer version
    manifest = {
        "template": {
            "name": "test-template",
            "version": "2.0.0",
            "description": "Updated template"
        }
    }

    with open(template_path / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # Create some files (some overlap, some new)
    (template_path / "templates").mkdir()
    (template_path / "templates" / "old.template").write_text("Updated template")
    (template_path / "templates" / "new.template").write_text("New template")

    # Create agents (only standard agent, no custom)
    (template_path / "agents").mkdir()
    (template_path / "agents" / "standard-agent.md").write_text("# Updated Standard Agent")

    return template_path


class TestTemplateMerger:
    """Tests for TemplateMerger class."""

    def test_init_with_valid_paths(self, existing_template, new_template):
        """Test initialization with valid paths."""
        merger = TemplateMerger(existing_template, new_template)
        assert merger.existing_path == existing_template
        assert merger.new_path == new_template

    def test_init_with_nonexistent_existing(self, temp_dir, new_template):
        """Test initialization with nonexistent existing path raises error."""
        with pytest.raises(FileNotFoundError):
            TemplateMerger(temp_dir / "nonexistent", new_template)

    def test_init_with_nonexistent_new(self, existing_template, temp_dir):
        """Test initialization with nonexistent new path raises error."""
        with pytest.raises(FileNotFoundError):
            TemplateMerger(existing_template, temp_dir / "nonexistent")

    def test_detect_conflict_same_name(self, existing_template, new_template):
        """Test detecting conflict when templates have same name."""
        merger = TemplateMerger(existing_template, new_template)
        has_conflict = merger.detect_conflict()
        assert has_conflict is True

    def test_detect_conflict_different_names(self, existing_template, temp_dir):
        """Test no conflict when templates have different names."""
        # Create template with different name
        other_template = temp_dir / "other-template"
        other_template.mkdir()

        manifest = {
            "template": {
                "name": "other-template",
                "version": "1.0.0"
            }
        }

        with open(other_template / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        merger = TemplateMerger(existing_template, other_template)
        has_conflict = merger.detect_conflict()
        assert has_conflict is False

    def test_compare_templates(self, existing_template, new_template):
        """Test comparing templates."""
        merger = TemplateMerger(existing_template, new_template)
        comparison = merger.compare_templates()

        assert "files_to_add" in comparison
        assert "files_to_update" in comparison
        assert "custom_agents" in comparison

        # Should detect new.template as new file
        assert any("new.template" in f for f in comparison["files_to_add"])

        # Should detect custom-agent.md as custom (in existing but not in new)
        assert "custom-agent.md" in comparison["custom_agents"]

    def test_merge_cancel(self, existing_template, new_template):
        """Test merge with CANCEL strategy."""
        merger = TemplateMerger(existing_template, new_template)
        result = merger.merge(MergeStrategy.CANCEL)

        assert result.success is False
        assert result.strategy == MergeStrategy.CANCEL

    def test_merge_overwrite(self, existing_template, new_template):
        """Test merge with OVERWRITE strategy."""
        merger = TemplateMerger(existing_template, new_template)
        result = merger.merge(MergeStrategy.OVERWRITE)

        assert result.success is True
        assert result.strategy == MergeStrategy.OVERWRITE

        # Verify files were overwritten
        assert (existing_template / "templates" / "new.template").exists()

        # Custom agent should be lost
        assert not (existing_template / "agents" / "custom-agent.md").exists()

    def test_merge_smart_preserves_custom_agents(self, existing_template, new_template):
        """Test smart merge preserves custom agents."""
        merger = TemplateMerger(existing_template, new_template)
        result = merger.merge(MergeStrategy.MERGE)

        assert result.success is True
        assert result.strategy == MergeStrategy.MERGE

        # Custom agent should be preserved
        assert (existing_template / "agents" / "custom-agent.md").exists()
        assert "custom-agent.md" in result.custom_agents_preserved

    def test_merge_smart_updates_files(self, existing_template, new_template):
        """Test smart merge updates existing files."""
        merger = TemplateMerger(existing_template, new_template)
        result = merger.merge(MergeStrategy.MERGE)

        # Old template should be updated
        content = (existing_template / "templates" / "old.template").read_text()
        assert content == "Updated template"

    def test_merge_smart_adds_new_files(self, existing_template, new_template):
        """Test smart merge adds new files."""
        merger = TemplateMerger(existing_template, new_template)
        result = merger.merge(MergeStrategy.MERGE)

        # New template should be added
        assert (existing_template / "templates" / "new.template").exists()
        assert any("new.template" in f for f in result.files_added)

    def test_merge_smart_bumps_version(self, existing_template, new_template):
        """Test smart merge bumps version number."""
        # Initialize versioning on existing template
        from template_versioning import TemplateVersionManager

        version_manager = TemplateVersionManager(existing_template)
        version_manager.initialize_version("1.0.0", "Initial release")

        # Perform merge
        merger = TemplateMerger(existing_template, new_template)
        result = merger.merge(MergeStrategy.MERGE)

        # Version should be bumped
        assert result.new_version is not None
        assert result.new_version == "1.1.0"  # Minor bump

    def test_merge_smart_updates_changelog(self, existing_template, new_template):
        """Test smart merge updates changelog."""
        from template_versioning import TemplateVersionManager

        version_manager = TemplateVersionManager(existing_template)
        version_manager.initialize_version("1.0.0", "Initial release")

        merger = TemplateMerger(existing_template, new_template)
        result = merger.merge(MergeStrategy.MERGE)

        # Verify changelog was updated
        version_manager = TemplateVersionManager(existing_template)
        changelog = version_manager.get_changelog()

        assert len(changelog) == 2  # Initial + merge entry
        assert "Merged" in changelog[0].changes[0]

    def test_merge_creates_backup(self, existing_template, new_template, temp_dir):
        """Test merge creates backup of existing template."""
        merger = TemplateMerger(existing_template, new_template, backup_dir=temp_dir / "backups")
        result = merger.merge(MergeStrategy.MERGE)

        # Backup directory should exist
        assert (temp_dir / "backups").exists()

        # Should have backup subdirectory
        backups = list((temp_dir / "backups").iterdir())
        assert len(backups) > 0

    def test_merge_result_to_dict(self):
        """Test MergeResult.to_dict()."""
        result = MergeResult(
            success=True,
            strategy=MergeStrategy.MERGE,
            new_version="1.1.0",
            files_added=["new.txt"],
            files_updated=["old.txt"]
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["strategy"] == "merge"
        assert data["new_version"] == "1.1.0"

    def test_identify_custom_agents(self, existing_template, new_template):
        """Test identifying custom agents."""
        merger = TemplateMerger(existing_template, new_template)
        custom_agents = merger._identify_custom_agents()

        assert "custom-agent.md" in custom_agents
        assert "standard-agent.md" not in custom_agents

    def test_get_file_list(self, existing_template):
        """Test getting file list from template."""
        merger = TemplateMerger(existing_template, existing_template)
        files = merger._get_file_list(existing_template)

        assert "manifest.json" in files
        assert "templates/old.template" in files
        assert "agents/custom-agent.md" in files


class TestDetectExistingTemplate:
    """Tests for detect_existing_template function."""

    def test_detect_in_custom_paths(self, temp_dir):
        """Test detecting template in custom search paths."""
        # Create template in custom location
        template_path = temp_dir / "templates" / "test-template"
        template_path.mkdir(parents=True)

        manifest = {
            "template": {
                "name": "test-template"
            }
        }

        with open(template_path / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Search for template
        found_path = detect_existing_template(
            "test-template",
            search_paths=[temp_dir / "templates"]
        )

        assert found_path == template_path

    def test_detect_nonexistent_template(self, temp_dir):
        """Test detecting nonexistent template returns None."""
        found_path = detect_existing_template(
            "nonexistent-template",
            search_paths=[temp_dir]
        )

        assert found_path is None

    def test_detect_without_manifest(self, temp_dir):
        """Test directory without manifest.json is not detected."""
        # Create directory without manifest
        template_path = temp_dir / "templates" / "invalid-template"
        template_path.mkdir(parents=True)
        (template_path / "some_file.txt").write_text("test")

        found_path = detect_existing_template(
            "invalid-template",
            search_paths=[temp_dir / "templates"]
        )

        assert found_path is None

    def test_detect_with_default_paths(self, temp_dir):
        """Test detecting with default search paths."""
        # This test just verifies the function doesn't crash with default paths
        found_path = detect_existing_template("nonexistent-template")
        assert found_path is None


class TestMergeEdgeCases:
    """Tests for edge cases in merge operations."""

    def test_merge_with_no_agents_directory(self, temp_dir):
        """Test merge when existing template has no agents directory."""
        # Create existing template without agents
        existing = temp_dir / "existing"
        existing.mkdir()

        manifest = {
            "template": {
                "name": "test",
                "version": "1.0.0"
            }
        }

        with open(existing / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Create new template with agents
        new = temp_dir / "new"
        new.mkdir()

        with open(new / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        (new / "agents").mkdir()
        (new / "agents" / "test-agent.md").write_text("# Test")

        # Should not crash
        merger = TemplateMerger(existing, new)
        result = merger.merge(MergeStrategy.MERGE)

        assert result.success is True

    def test_merge_empty_templates(self, temp_dir):
        """Test merge with minimal empty templates."""
        # Create minimal templates
        existing = temp_dir / "existing"
        existing.mkdir()
        (existing / "manifest.json").write_text('{"template": {"name": "test"}}')

        new = temp_dir / "new"
        new.mkdir()
        (new / "manifest.json").write_text('{"template": {"name": "test"}}')

        merger = TemplateMerger(existing, new)
        result = merger.merge(MergeStrategy.OVERWRITE)

        assert result.success is True
