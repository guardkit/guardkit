"""
Tests for Template Packaging System

Tests .tar.gz creation, checksum generation, metadata creation, and distribution README.

TASK-012: Template Packaging & Distribution (Sub-task 1: TASK-061)
"""

import json
import tarfile
from pathlib import Path
import pytest
import tempfile
import shutil

from template_packager import (
    TemplatePackager,
    PackageMetadata,
    verify_package
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_template(temp_dir):
    """Create sample template directory with manifest."""
    template_dir = temp_dir / "test-template"
    template_dir.mkdir()

    # Create manifest.json
    manifest = {
        "template": {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template for packaging",
            "author": "Test Author"
        },
        "stack": {
            "framework": "TestFramework",
            "language": "Python"
        },
        "agents": ["test-agent.md"]
    }

    with open(template_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # Create some template files
    (template_dir / "templates").mkdir()
    (template_dir / "templates" / "test.template").write_text("Test template content")

    # Create agents directory
    (template_dir / "agents").mkdir()
    (template_dir / "agents" / "test-agent.md").write_text("# Test Agent")

    # Create CLAUDE.md
    (template_dir / "CLAUDE.md").write_text("# Test Template Guide")

    return template_dir


class TestTemplatePackager:
    """Tests for TemplatePackager class."""

    def test_init_with_valid_path(self, sample_template):
        """Test initialization with valid template path."""
        packager = TemplatePackager(sample_template)
        assert packager.template_path == sample_template

    def test_init_with_nonexistent_path(self, temp_dir):
        """Test initialization with nonexistent path raises error."""
        with pytest.raises(FileNotFoundError):
            TemplatePackager(temp_dir / "nonexistent")

    def test_init_with_file_not_directory(self, temp_dir):
        """Test initialization with file path raises error."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test")

        with pytest.raises(ValueError):
            TemplatePackager(file_path)

    def test_package_creates_tarball(self, sample_template, temp_dir):
        """Test package creates .tar.gz file."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output"

        result = packager.package(output_dir)

        package_path = output_dir / result.package_file
        assert package_path.exists()
        assert package_path.suffix == ".gz"

    def test_package_creates_metadata(self, sample_template, temp_dir):
        """Test package creates metadata JSON file."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output"

        result = packager.package(output_dir)

        metadata_path = output_dir / "test-template-1.0.0.metadata.json"
        assert metadata_path.exists()

        # Verify metadata content
        with open(metadata_path) as f:
            metadata = json.load(f)

        assert metadata["template_name"] == "test-template"
        assert metadata["version"] == "1.0.0"
        assert "checksum_sha256" in metadata
        assert metadata["size_bytes"] > 0

    def test_package_creates_checksum_file(self, sample_template, temp_dir):
        """Test package creates checksum file."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output"

        result = packager.package(output_dir)

        checksum_path = output_dir / f"{result.package_file}.sha256"
        assert checksum_path.exists()

        # Verify checksum format
        content = checksum_path.read_text()
        parts = content.strip().split()
        assert len(parts) == 2
        assert parts[0] == result.checksum_sha256
        assert parts[1] == result.package_file

    def test_package_creates_readme(self, sample_template, temp_dir):
        """Test package creates distribution README."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output"

        result = packager.package(output_dir, include_readme=True)

        readme_path = output_dir / "test-template-1.0.0.README.md"
        assert readme_path.exists()

        content = readme_path.read_text()
        assert "test-template" in content
        assert "1.0.0" in content
        assert "Installation" in content

    def test_package_without_readme(self, sample_template, temp_dir):
        """Test package without README creation."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output"

        result = packager.package(output_dir, include_readme=False)

        readme_path = output_dir / "test-template-1.0.0.README.md"
        assert not readme_path.exists()

    def test_package_with_custom_version(self, sample_template, temp_dir):
        """Test package with custom version string."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output"

        result = packager.package(output_dir, version="2.0.0")

        assert result.version == "2.0.0"
        assert "2.0.0" in result.package_file

    def test_tarball_contains_all_files(self, sample_template, temp_dir):
        """Test tarball contains all template files."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output"

        result = packager.package(output_dir)

        package_path = output_dir / result.package_file

        # Extract and verify contents
        with tarfile.open(package_path, "r:gz") as tar:
            members = tar.getnames()

        assert "test-template/manifest.json" in members
        assert "test-template/CLAUDE.md" in members
        assert "test-template/templates/test.template" in members
        assert "test-template/agents/test-agent.md" in members

    def test_checksum_is_valid(self, sample_template, temp_dir):
        """Test generated checksum is valid SHA256."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output"

        result = packager.package(output_dir)

        assert len(result.checksum_sha256) == 64  # SHA256 hex length
        assert result.checksum_sha256.isalnum()

    def test_metadata_includes_file_list(self, sample_template, temp_dir):
        """Test metadata includes list of files."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output"

        result = packager.package(output_dir)

        assert len(result.files_included) > 0
        assert any("manifest.json" in f for f in result.files_included)

    def test_metadata_to_dict(self):
        """Test PackageMetadata.to_dict()."""
        metadata = PackageMetadata(
            template_name="test",
            version="1.0.0",
            package_file="test-1.0.0.tar.gz",
            checksum_sha256="abc123",
            size_bytes=1024,
            created_at="2025-01-01T00:00:00Z"
        )

        data = metadata.to_dict()

        assert data["template_name"] == "test"
        assert data["version"] == "1.0.0"
        assert data["checksum_sha256"] == "abc123"

    def test_metadata_from_dict(self):
        """Test PackageMetadata.from_dict()."""
        data = {
            "template_name": "test",
            "version": "1.0.0",
            "package_file": "test-1.0.0.tar.gz",
            "checksum_sha256": "abc123",
            "size_bytes": 1024,
            "created_at": "2025-01-01T00:00:00Z"
        }

        metadata = PackageMetadata.from_dict(data)

        assert metadata.template_name == "test"
        assert metadata.version == "1.0.0"

    def test_verify_package_success(self, sample_template, temp_dir):
        """Test verify_package with valid checksum."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output"

        result = packager.package(output_dir)

        package_path = output_dir / result.package_file
        checksum_path = output_dir / f"{result.package_file}.sha256"

        # Verification should succeed
        is_valid = verify_package(package_path, checksum_path)
        assert is_valid is True

    def test_verify_package_failure(self, sample_template, temp_dir):
        """Test verify_package with invalid checksum."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output"

        result = packager.package(output_dir)

        package_path = output_dir / result.package_file
        checksum_path = output_dir / f"{result.package_file}.sha256"

        # Corrupt checksum file
        checksum_path.write_text("invalid_checksum  " + result.package_file)

        # Verification should fail
        is_valid = verify_package(package_path, checksum_path)
        assert is_valid is False

    def test_package_creates_output_directory(self, sample_template, temp_dir):
        """Test package creates output directory if it doesn't exist."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output" / "nested" / "path"

        result = packager.package(output_dir)

        assert output_dir.exists()
        assert (output_dir / result.package_file).exists()

    def test_readme_includes_installation_instructions(self, sample_template, temp_dir):
        """Test README includes installation instructions."""
        packager = TemplatePackager(sample_template)
        output_dir = temp_dir / "output"

        result = packager.package(output_dir)

        readme_path = output_dir / "test-template-1.0.0.README.md"
        content = readme_path.read_text()

        assert "tar -xzf" in content
        assert "guardkit init" in content
        assert result.checksum_sha256 in content

    def test_package_with_missing_manifest(self, temp_dir):
        """Test package with template missing manifest.json."""
        template_dir = temp_dir / "no-manifest"
        template_dir.mkdir()
        (template_dir / "test.txt").write_text("test")

        packager = TemplatePackager(template_dir)
        output_dir = temp_dir / "output"

        # Should still work, just with default values
        result = packager.package(output_dir)

        assert result.version == "1.0.0"  # Default version
