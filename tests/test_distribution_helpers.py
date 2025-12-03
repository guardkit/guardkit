"""
Tests for Distribution Helper Utilities

Tests git helpers, documentation generation, and verification scripts.

TASK-012: Template Packaging & Distribution (Sub-task 4: TASK-064)
"""

import json
from pathlib import Path
import pytest
import tempfile
import shutil

from distribution_helpers import (
    DistributionHelper,
    GitOperationResult
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def template_dir(temp_dir):
    """Create template directory with manifest."""
    template_path = temp_dir / "test-template"
    template_path.mkdir()

    manifest = {
        "template": {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template for distribution",
            "author": "Test Author"
        },
        "stack": {
            "framework": "TestFramework",
            "language": "Python"
        },
        "agents": [
            "test-agent-1.md",
            "test-agent-2.md"
        ]
    }

    with open(template_path / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # Create some template structure
    (template_path / "templates").mkdir()
    (template_path / "templates" / "test.template").write_text("Test")

    (template_path / "agents").mkdir()
    (template_path / "agents" / "test-agent-1.md").write_text("# Agent 1")

    (template_path / "CLAUDE.md").write_text("# Template Guide")

    return template_path


class TestDistributionHelper:
    """Tests for DistributionHelper class."""

    def test_init_with_valid_path(self, template_dir):
        """Test initialization with valid template path."""
        helper = DistributionHelper(template_dir)
        assert helper.template_path == template_dir

    def test_init_with_nonexistent_path(self, temp_dir):
        """Test initialization with nonexistent path raises error."""
        with pytest.raises(FileNotFoundError):
            DistributionHelper(temp_dir / "nonexistent")

    def test_generate_usage_instructions(self, template_dir):
        """Test generating usage instructions."""
        helper = DistributionHelper(template_dir)
        instructions = helper.generate_usage_instructions()

        assert "test-template" in instructions
        assert "1.0.0" in instructions
        assert "Installation" in instructions
        assert "guardkit init" in instructions

    def test_generate_usage_instructions_saves_file(self, template_dir):
        """Test usage instructions are saved to file."""
        helper = DistributionHelper(template_dir)
        output_path = template_dir / "USAGE.md"

        instructions = helper.generate_usage_instructions(output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert content == instructions

    def test_generate_usage_instructions_default_path(self, template_dir):
        """Test usage instructions default path."""
        helper = DistributionHelper(template_dir)
        helper.generate_usage_instructions()

        # Should create USAGE.md in template directory
        assert (template_dir / "USAGE.md").exists()

    def test_generate_sharing_guide(self, template_dir):
        """Test generating sharing guide."""
        helper = DistributionHelper(template_dir)
        guide = helper.generate_sharing_guide()

        assert "test-template" in guide
        assert "Git Repository" in guide
        assert "Package Distribution" in guide
        assert "git add" in guide
        assert "tar -xzf" in guide

    def test_generate_sharing_guide_with_registry(self, template_dir):
        """Test sharing guide with registry instructions."""
        helper = DistributionHelper(template_dir)
        guide = helper.generate_sharing_guide(include_registry=True)

        assert "Template Registry" in guide
        assert "guardkit registry" in guide

    def test_generate_sharing_guide_without_registry(self, template_dir):
        """Test sharing guide without registry instructions."""
        helper = DistributionHelper(template_dir)
        guide = helper.generate_sharing_guide(include_registry=False)

        assert "Template Registry" not in guide

    def test_generate_sharing_guide_saves_file(self, template_dir):
        """Test sharing guide is saved to file."""
        helper = DistributionHelper(template_dir)
        output_path = template_dir / "SHARING.md"

        guide = helper.generate_sharing_guide(output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert content == guide

    def test_generate_verification_script(self, template_dir):
        """Test generating verification script."""
        helper = DistributionHelper(template_dir)
        script = helper.generate_verification_script()

        assert "#!/bin/bash" in script
        assert "test-template" in script
        assert "manifest.json" in script
        assert "Verification" in script

    def test_generate_verification_script_saves_file(self, template_dir):
        """Test verification script is saved to file."""
        helper = DistributionHelper(template_dir)
        output_path = template_dir / "verify.sh"

        script = helper.generate_verification_script(output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert content == script

    def test_generate_verification_script_is_executable(self, template_dir):
        """Test verification script is made executable."""
        helper = DistributionHelper(template_dir)
        output_path = template_dir / "verify.sh"

        helper.generate_verification_script(output_path)

        # Check file is executable
        import stat
        mode = output_path.stat().st_mode
        assert mode & stat.S_IXUSR  # User executable
        assert mode & stat.S_IXGRP  # Group executable
        assert mode & stat.S_IXOTH  # Others executable

    def test_git_operation_result_success(self):
        """Test GitOperationResult for successful operation."""
        result = GitOperationResult(
            success=True,
            command="git status",
            output="On branch main"
        )

        assert result.success is True
        assert result.command == "git status"
        assert result.output == "On branch main"

    def test_git_operation_result_failure(self):
        """Test GitOperationResult for failed operation."""
        result = GitOperationResult(
            success=False,
            command="git commit",
            error="nothing to commit"
        )

        assert result.success is False
        assert result.error == "nothing to commit"

    def test_usage_instructions_includes_all_methods(self, template_dir):
        """Test usage instructions include all installation methods."""
        helper = DistributionHelper(template_dir)
        instructions = helper.generate_usage_instructions()

        assert "Method 1: From Local Directory" in instructions
        assert "Method 2: From Package" in instructions
        assert "Method 3: From Git Repository" in instructions

    def test_sharing_guide_includes_versioning(self, template_dir):
        """Test sharing guide includes version management section."""
        helper = DistributionHelper(template_dir)
        guide = helper.generate_sharing_guide()

        assert "Version Management" in guide
        assert "Semantic Versioning" in guide
        assert "Changelog" in guide

    def test_sharing_guide_includes_troubleshooting(self, template_dir):
        """Test sharing guide includes troubleshooting section."""
        helper = DistributionHelper(template_dir)
        guide = helper.generate_sharing_guide()

        assert "Troubleshooting" in guide
        assert "Template Not Found" in guide

    def test_verification_script_checks_manifest(self, template_dir):
        """Test verification script checks for manifest.json."""
        helper = DistributionHelper(template_dir)
        script = helper.generate_verification_script()

        assert "manifest.json" in script
        assert "jq" in script

    def test_verification_script_checks_structure(self, template_dir):
        """Test verification script checks template structure."""
        helper = DistributionHelper(template_dir)
        script = helper.generate_verification_script()

        assert "agents" in script
        assert "templates" in script

    def test_format_template_contents_with_stack(self, template_dir):
        """Test formatting template contents includes stack info."""
        helper = DistributionHelper(template_dir)
        manifest = helper._load_manifest()
        contents = helper._format_template_contents(manifest)

        assert "Technology Stack" in contents
        assert "TestFramework" in contents

    def test_format_template_contents_with_agents(self, template_dir):
        """Test formatting template contents includes agents."""
        helper = DistributionHelper(template_dir)
        manifest = helper._load_manifest()
        contents = helper._format_template_contents(manifest)

        assert "AI Agents" in contents
        assert "test-agent-1.md" in contents

    def test_load_manifest(self, template_dir):
        """Test loading manifest from template."""
        helper = DistributionHelper(template_dir)
        manifest = helper._load_manifest()

        assert manifest["template"]["name"] == "test-template"
        assert manifest["template"]["version"] == "1.0.0"

    def test_load_manifest_missing_file(self, temp_dir):
        """Test loading manifest when file doesn't exist."""
        template_path = temp_dir / "no-manifest"
        template_path.mkdir()

        helper = DistributionHelper(template_path)
        manifest = helper._load_manifest()

        assert manifest == {}

    def test_usage_instructions_includes_template_description(self, template_dir):
        """Test usage instructions include template description."""
        helper = DistributionHelper(template_dir)
        instructions = helper.generate_usage_instructions()

        assert "Test template for distribution" in instructions

    def test_sharing_guide_includes_best_practices(self, template_dir):
        """Test sharing guide includes best practices section."""
        helper = DistributionHelper(template_dir)
        guide = helper.generate_sharing_guide()

        assert "Best Practices" in guide
        assert "Version Everything" in guide
        assert "Document Changes" in guide


class TestGitOperations:
    """Tests for git operations (mocked)."""

    def test_create_git_commit_without_git(self, template_dir):
        """Test git commit when git is not available."""
        helper = DistributionHelper(template_dir)

        # This will fail if git is not installed, which is expected
        result = helper.create_git_commit("Test commit", add_files=False)

        # Result should indicate either success or failure gracefully
        assert isinstance(result, GitOperationResult)

    def test_create_git_tag(self, template_dir):
        """Test creating git tag."""
        helper = DistributionHelper(template_dir)

        # Will fail if not in git repo, which is expected
        result = helper.create_git_tag("1.0.0", message="Release v1.0.0")

        assert isinstance(result, GitOperationResult)
        assert "git tag" in result.command

    def test_create_git_tag_generates_correct_name(self, template_dir):
        """Test git tag name format."""
        helper = DistributionHelper(template_dir)

        result = helper.create_git_tag("1.0.0")

        # Tag name should be template-name-v1.0.0
        assert "test-template-v1.0.0" in result.command

    def test_create_git_tag_annotated(self, template_dir):
        """Test creating annotated git tag."""
        helper = DistributionHelper(template_dir)

        result = helper.create_git_tag("1.0.0", annotated=True)

        assert "-a" in result.command

    def test_create_git_tag_lightweight(self, template_dir):
        """Test creating lightweight git tag."""
        helper = DistributionHelper(template_dir)

        result = helper.create_git_tag("1.0.0", annotated=False)

        assert "-a" not in result.command

    def test_push_to_remote(self, template_dir):
        """Test pushing to remote repository."""
        helper = DistributionHelper(template_dir)

        result = helper.push_to_remote("origin", push_tags=True)

        assert isinstance(result, GitOperationResult)

    def test_run_git_command_captures_error(self, template_dir):
        """Test git command error is captured."""
        helper = DistributionHelper(template_dir)

        # Run invalid git command
        result = helper._run_git_command(["git", "invalid-command"])

        assert result.success is False
        assert result.error != ""


class TestDocumentationQuality:
    """Tests for documentation quality."""

    def test_usage_instructions_well_formatted(self, template_dir):
        """Test usage instructions are well-formatted markdown."""
        helper = DistributionHelper(template_dir)
        instructions = helper.generate_usage_instructions()

        # Should have proper markdown structure
        assert instructions.startswith("#")
        assert "```bash" in instructions
        assert "```" in instructions

    def test_sharing_guide_well_formatted(self, template_dir):
        """Test sharing guide is well-formatted markdown."""
        helper = DistributionHelper(template_dir)
        guide = helper.generate_sharing_guide()

        assert guide.startswith("#")
        assert "```bash" in guide

    def test_verification_script_has_shebang(self, template_dir):
        """Test verification script has proper shebang."""
        helper = DistributionHelper(template_dir)
        script = helper.generate_verification_script()

        assert script.startswith("#!/bin/bash")

    def test_verification_script_uses_set_e(self, template_dir):
        """Test verification script uses set -e for error handling."""
        helper = DistributionHelper(template_dir)
        script = helper.generate_verification_script()

        assert "set -e" in script
