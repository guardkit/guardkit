"""
Tests for Template Versioning System

Tests semantic versioning, changelog management, version comparison, and lineage tracking.

TASK-012: Template Packaging & Distribution (Sub-task 2: TASK-062)
"""

import json
from pathlib import Path
import pytest
import tempfile
import shutil

from template_versioning import (
    TemplateVersionManager,
    SemanticVersion,
    ChangelogEntry,
    TemplateLineage
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def template_dir(temp_dir):
    """Create template directory with basic manifest."""
    template_path = temp_dir / "test-template"
    template_path.mkdir()

    manifest = {
        "template": {
            "name": "test-template",
            "description": "Test template"
        }
    }

    with open(template_path / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return template_path


class TestSemanticVersion:
    """Tests for SemanticVersion class."""

    def test_parse_valid_version(self):
        """Test parsing valid semantic version."""
        version = SemanticVersion.parse("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_parse_invalid_version(self):
        """Test parsing invalid version raises error."""
        with pytest.raises(ValueError):
            SemanticVersion.parse("1.2")

        with pytest.raises(ValueError):
            SemanticVersion.parse("v1.2.3")

        with pytest.raises(ValueError):
            SemanticVersion.parse("1.2.3-beta")

    def test_version_to_string(self):
        """Test version string formatting."""
        version = SemanticVersion(1, 2, 3)
        assert str(version) == "1.2.3"

    def test_version_equality(self):
        """Test version equality comparison."""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 2, 3)
        v3 = SemanticVersion(1, 2, 4)

        assert v1 == v2
        assert v1 != v3

    def test_version_less_than(self):
        """Test version less than comparison."""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 2, 4)
        v3 = SemanticVersion(2, 0, 0)

        assert v1 < v2
        assert v1 < v3
        assert not v2 < v1

    def test_version_greater_than(self):
        """Test version greater than comparison."""
        v1 = SemanticVersion(2, 0, 0)
        v2 = SemanticVersion(1, 9, 9)

        assert v1 > v2
        assert not v2 > v1

    def test_bump_major(self):
        """Test bumping major version."""
        version = SemanticVersion(1, 2, 3)
        new_version = version.bump_major()

        assert new_version.major == 2
        assert new_version.minor == 0
        assert new_version.patch == 0

    def test_bump_minor(self):
        """Test bumping minor version."""
        version = SemanticVersion(1, 2, 3)
        new_version = version.bump_minor()

        assert new_version.major == 1
        assert new_version.minor == 3
        assert new_version.patch == 0

    def test_bump_patch(self):
        """Test bumping patch version."""
        version = SemanticVersion(1, 2, 3)
        new_version = version.bump_patch()

        assert new_version.major == 1
        assert new_version.minor == 2
        assert new_version.patch == 4


class TestChangelogEntry:
    """Tests for ChangelogEntry class."""

    def test_to_dict(self):
        """Test converting changelog entry to dictionary."""
        entry = ChangelogEntry(
            version="1.0.0",
            date="2025-01-01T00:00:00Z",
            changes=["Initial release"],
            author="Test Author"
        )

        data = entry.to_dict()

        assert data["version"] == "1.0.0"
        assert data["changes"] == ["Initial release"]
        assert data["author"] == "Test Author"

    def test_from_dict(self):
        """Test creating changelog entry from dictionary."""
        data = {
            "version": "1.0.0",
            "date": "2025-01-01T00:00:00Z",
            "changes": ["Initial release"],
            "author": "Test Author"
        }

        entry = ChangelogEntry.from_dict(data)

        assert entry.version == "1.0.0"
        assert entry.changes == ["Initial release"]
        assert entry.author == "Test Author"


class TestTemplateLineage:
    """Tests for TemplateLineage class."""

    def test_to_dict(self):
        """Test converting lineage to dictionary."""
        lineage = TemplateLineage(
            based_on="parent-template",
            based_on_version="1.0.0",
            customizations=["Added custom agent", "Modified settings"]
        )

        data = lineage.to_dict()

        assert data["based_on"] == "parent-template"
        assert data["based_on_version"] == "1.0.0"
        assert len(data["customizations"]) == 2

    def test_from_dict(self):
        """Test creating lineage from dictionary."""
        data = {
            "based_on": "parent-template",
            "based_on_version": "1.0.0",
            "customizations": ["Added custom agent"]
        }

        lineage = TemplateLineage.from_dict(data)

        assert lineage.based_on == "parent-template"
        assert lineage.based_on_version == "1.0.0"
        assert len(lineage.customizations) == 1


class TestTemplateVersionManager:
    """Tests for TemplateVersionManager class."""

    def test_init_with_valid_path(self, template_dir):
        """Test initialization with valid template path."""
        manager = TemplateVersionManager(template_dir)
        assert manager.template_path == template_dir

    def test_init_with_nonexistent_path(self, temp_dir):
        """Test initialization with nonexistent path raises error."""
        with pytest.raises(FileNotFoundError):
            TemplateVersionManager(temp_dir / "nonexistent")

    def test_initialize_version(self, template_dir):
        """Test initializing template version."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version("1.0.0", "Initial release", author="Test Author")

        # Verify manifest was updated
        with open(template_dir / "manifest.json") as f:
            manifest = json.load(f)

        assert manifest["template"]["version"] == "1.0.0"
        assert len(manifest["changelog"]) == 1
        assert manifest["changelog"][0]["version"] == "1.0.0"
        assert manifest["changelog"][0]["author"] == "Test Author"

    def test_initialize_version_with_lineage(self, template_dir):
        """Test initializing version with lineage information."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version(
            "1.0.0",
            "Initial release",
            based_on="parent-template",
            based_on_version="2.0.0"
        )

        with open(template_dir / "manifest.json") as f:
            manifest = json.load(f)

        assert "lineage" in manifest
        assert manifest["lineage"]["based_on"] == "parent-template"
        assert manifest["lineage"]["based_on_version"] == "2.0.0"

    def test_initialize_version_invalid_format(self, template_dir):
        """Test initializing with invalid version format raises error."""
        manager = TemplateVersionManager(template_dir)

        with pytest.raises(ValueError):
            manager.initialize_version("1.2", "Invalid version")

    def test_bump_version_patch(self, template_dir):
        """Test bumping patch version."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version("1.0.0", "Initial release")

        new_version = manager.bump_version("patch", ["Bug fix"], author="Dev")

        assert new_version == "1.0.1"

        with open(template_dir / "manifest.json") as f:
            manifest = json.load(f)

        assert manifest["template"]["version"] == "1.0.1"
        assert len(manifest["changelog"]) == 2
        assert manifest["changelog"][0]["version"] == "1.0.1"

    def test_bump_version_minor(self, template_dir):
        """Test bumping minor version."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version("1.0.0", "Initial release")

        new_version = manager.bump_version("minor", ["New feature"])

        assert new_version == "1.1.0"

    def test_bump_version_major(self, template_dir):
        """Test bumping major version."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version("1.0.0", "Initial release")

        new_version = manager.bump_version("major", ["Breaking change"])

        assert new_version == "2.0.0"

    def test_bump_version_invalid_type(self, template_dir):
        """Test bumping with invalid bump type raises error."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version("1.0.0", "Initial release")

        with pytest.raises(ValueError):
            manager.bump_version("invalid", ["Change"])

    def test_bump_version_not_initialized(self, template_dir):
        """Test bumping version when not initialized raises error."""
        manager = TemplateVersionManager(template_dir)

        with pytest.raises(ValueError):
            manager.bump_version("patch", ["Change"])

    def test_get_current_version(self, template_dir):
        """Test getting current version."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version("1.0.0", "Initial release")

        version = manager.get_current_version()
        assert version == "1.0.0"

    def test_get_current_version_not_initialized(self, template_dir):
        """Test getting version when not initialized returns None."""
        manager = TemplateVersionManager(template_dir)
        version = manager.get_current_version()
        assert version is None

    def test_get_changelog(self, template_dir):
        """Test getting changelog history."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version("1.0.0", "Initial release")
        manager.bump_version("patch", ["Bug fix"])

        changelog = manager.get_changelog()

        assert len(changelog) == 2
        assert changelog[0].version == "1.0.1"  # Newest first
        assert changelog[1].version == "1.0.0"

    def test_get_lineage(self, template_dir):
        """Test getting lineage information."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version(
            "1.0.0",
            "Initial release",
            based_on="parent-template",
            based_on_version="1.0.0"
        )

        lineage = manager.get_lineage()

        assert lineage is not None
        assert lineage.based_on == "parent-template"
        assert lineage.based_on_version == "1.0.0"

    def test_get_lineage_none(self, template_dir):
        """Test getting lineage when not set returns None."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version("1.0.0", "Initial release")

        lineage = manager.get_lineage()
        assert lineage is None

    def test_update_lineage(self, template_dir):
        """Test updating lineage customizations."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version(
            "1.0.0",
            "Initial release",
            based_on="parent-template"
        )

        manager.update_lineage(customizations=["Added custom agent"])

        lineage = manager.get_lineage()
        assert len(lineage.customizations) == 1

    def test_update_lineage_append(self, template_dir):
        """Test appending to lineage customizations."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version(
            "1.0.0",
            "Initial release",
            based_on="parent-template"
        )

        manager.update_lineage(customizations=["Custom 1"], append=True)
        manager.update_lineage(customizations=["Custom 2"], append=True)

        lineage = manager.get_lineage()
        assert len(lineage.customizations) == 2

    def test_compare_versions(self, template_dir):
        """Test comparing two versions."""
        manager = TemplateVersionManager(template_dir)

        comparison = manager.compare_versions("1.0.0", "1.0.1")

        assert comparison["equal"] is False
        assert comparison["b_newer"] is True
        assert comparison["patch_change"] is True

    def test_compare_versions_equal(self, template_dir):
        """Test comparing equal versions."""
        manager = TemplateVersionManager(template_dir)

        comparison = manager.compare_versions("1.0.0", "1.0.0")

        assert comparison["equal"] is True

    def test_validate_version_string_valid(self, template_dir):
        """Test validating valid version string."""
        manager = TemplateVersionManager(template_dir)

        is_valid, error = manager.validate_version_string("1.2.3")

        assert is_valid is True
        assert error is None

    def test_validate_version_string_invalid(self, template_dir):
        """Test validating invalid version string."""
        manager = TemplateVersionManager(template_dir)

        is_valid, error = manager.validate_version_string("1.2")

        assert is_valid is False
        assert error is not None

    def test_changelog_ordering(self, template_dir):
        """Test changelog maintains reverse chronological order."""
        manager = TemplateVersionManager(template_dir)
        manager.initialize_version("1.0.0", "Initial")
        manager.bump_version("patch", ["Fix 1"])
        manager.bump_version("patch", ["Fix 2"])

        changelog = manager.get_changelog()

        assert changelog[0].version == "1.0.2"
        assert changelog[1].version == "1.0.1"
        assert changelog[2].version == "1.0.0"
