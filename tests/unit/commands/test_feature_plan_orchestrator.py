"""
Unit tests for feature_plan_orchestrator.py

Tests the feature-plan orchestrator with clarification integration,
including Context A (review scope) and Context B (implementation preferences).
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import tempfile
import shutil
import sys

# Add installer lib to path
installer_lib_path = Path(__file__).parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
if installer_lib_path.exists():
    sys.path.insert(0, str(installer_lib_path))

from feature_plan_orchestrator import (
    execute_feature_plan,
    create_review_task,
    execute_context_b_clarification,
    generate_feature_structure,
    extract_feature_slug,
    _generate_task_id,
    _estimate_complexity,
    _estimate_subtask_count,
    _extract_task_name,
    _format_clarification_decisions,
)


class TestExtractFeatureSlug:
    """Test feature slug extraction from descriptions."""

    def test_basic_slug(self):
        """Test basic slug generation."""
        assert extract_feature_slug("user authentication") == "user-authentication"

    def test_with_add_prefix(self):
        """Test removal of 'add' prefix."""
        assert extract_feature_slug("add user authentication") == "user-authentication"

    def test_with_implement_prefix(self):
        """Test removal of 'implement' prefix."""
        assert extract_feature_slug("implement dark mode") == "dark-mode"

    def test_with_create_prefix(self):
        """Test removal of 'create' prefix."""
        assert extract_feature_slug("create dashboard widget") == "dashboard-widget"

    def test_with_build_prefix(self):
        """Test removal of 'build' prefix."""
        assert extract_feature_slug("build user profile page") == "user-profile-page"

    def test_special_characters_removed(self):
        """Test that special characters are removed."""
        assert extract_feature_slug("add user's authentication!") == "users-authentication"

    def test_multiple_spaces_normalized(self):
        """Test that multiple spaces become single hyphens."""
        assert extract_feature_slug("add   user    auth") == "user-auth"

    def test_multiple_hyphens_normalized(self):
        """Test that multiple hyphens become single hyphen."""
        assert extract_feature_slug("add user--auth") == "user-auth"

    def test_case_insensitive(self):
        """Test case normalization."""
        assert extract_feature_slug("Add User Authentication") == "user-authentication"

    def test_complex_description(self):
        """Test complex feature description."""
        assert extract_feature_slug("Implement dark mode toggle with persistence") == "dark-mode-toggle-with-persistence"


class TestEstimateComplexity:
    """Test complexity estimation from descriptions."""

    def test_short_description_base_complexity(self):
        """Test short descriptions get base complexity."""
        complexity = _estimate_complexity("add button")
        assert 3 <= complexity <= 5  # base + possible keyword adjustment

    def test_long_description_higher_complexity(self):
        """Test longer descriptions get higher complexity."""
        short = _estimate_complexity("add button")
        long = _estimate_complexity("add user authentication with oauth integration and password reset")
        assert long >= short

    def test_high_complexity_keywords(self):
        """Test high complexity keywords increase score."""
        base = _estimate_complexity("add button")
        with_keyword = _estimate_complexity("integrate payment system")
        assert with_keyword > base

    def test_complexity_capped_at_10(self):
        """Test complexity never exceeds 10."""
        # Very complex description
        complexity = _estimate_complexity(
            "integrate migrate refactor architecture with many many many many words"
        )
        assert complexity <= 10


class TestEstimateSubtaskCount:
    """Test subtask count estimation."""

    def test_empty_recommendations(self):
        """Test default count for empty recommendations."""
        assert _estimate_subtask_count([]) == 3

    def test_count_from_recommendations(self):
        """Test count matches recommendation count."""
        recs = [{"title": "Task 1"}, {"title": "Task 2"}]
        assert _estimate_subtask_count(recs) == 2

    def test_minimum_count(self):
        """Test minimum count is 1."""
        recs = []
        # Even with empty, returns default 3, but if we had -1 somehow, it should be 1
        assert _estimate_subtask_count(recs) >= 1

    def test_maximum_count(self):
        """Test count capped at 12."""
        recs = [{"title": f"Task {i}"} for i in range(20)]
        assert _estimate_subtask_count(recs) == 12


class TestGenerateTaskId:
    """Test task ID generation."""

    def test_generates_hash_id(self):
        """Test that task ID is generated with hash."""
        task_id = _generate_task_id("test description")
        assert task_id.startswith("TASK-")
        assert len(task_id) == 9  # "TASK-" + 4 char hash

    def test_custom_prefix(self):
        """Test custom prefix is used."""
        task_id = _generate_task_id("test description", prefix="REV")
        assert task_id.startswith("REV-")

    def test_different_descriptions_different_ids(self):
        """Test different descriptions produce different IDs."""
        id1 = _generate_task_id("description one")
        id2 = _generate_task_id("description two")
        # Due to timestamp, these will always differ
        assert id1 != id2


class TestExtractTaskName:
    """Test task name extraction from recommendations."""

    def test_basic_extraction(self):
        """Test basic task name extraction."""
        rec = {"title": "Add User Authentication"}
        name = _extract_task_name(rec)
        assert name == "add-user-authentication"

    def test_missing_title(self):
        """Test default when title missing."""
        rec = {}
        name = _extract_task_name(rec)
        assert name == "task"

    def test_special_chars_removed(self):
        """Test special characters are removed."""
        rec = {"title": "Add User's Auth!"}
        name = _extract_task_name(rec)
        assert name == "add-users-auth"

    def test_length_limit(self):
        """Test name is limited to 50 characters."""
        rec = {"title": "A" * 100}
        name = _extract_task_name(rec)
        assert len(name) <= 50


class TestFormatClarificationDecisions:
    """Test clarification decision formatting."""

    def test_none_context(self):
        """Test formatting with None context."""
        result = _format_clarification_decisions(None)
        assert result == "No decisions recorded"

    def test_empty_decisions(self):
        """Test formatting with empty decisions."""
        # Create minimal context mock
        class MockContext:
            decisions = []

        result = _format_clarification_decisions(MockContext())
        assert result == "No decisions recorded"


class TestCreateReviewTask:
    """Test review task creation."""

    def setup_method(self):
        """Create temporary directory structure."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.tasks_dir = self.temp_dir / "tasks" / "backlog"
        self.tasks_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    @patch('feature_plan_orchestrator.get_git_root')
    def test_creates_task_file(self, mock_git_root):
        """Test that task file is created."""
        mock_git_root.return_value = self.temp_dir

        task_id, complexity = create_review_task(
            "Add user authentication",
            {"priority": "high"}
        )

        assert task_id.startswith("REV-")
        assert 3 <= complexity <= 10

        # Verify file exists
        task_files = list(self.tasks_dir.glob(f"{task_id}.md"))
        assert len(task_files) == 1

        # Verify content
        content = task_files[0].read_text()
        assert "user authentication" in content.lower()
        assert "## Description" in content
        assert "## Review Scope" in content

    @patch('feature_plan_orchestrator.get_git_root')
    def test_returns_complexity(self, mock_git_root):
        """Test that complexity is returned."""
        mock_git_root.return_value = self.temp_dir

        _, complexity = create_review_task("simple task", {})
        assert isinstance(complexity, int)
        assert 1 <= complexity <= 10


class TestGenerateFeatureStructure:
    """Test feature structure generation."""

    def setup_method(self):
        """Create temporary directory structure."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.tasks_dir = self.temp_dir / "tasks" / "backlog"
        self.tasks_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    @patch('feature_plan_orchestrator.get_git_root')
    def test_creates_feature_directory(self, mock_git_root):
        """Test that feature directory is created."""
        mock_git_root.return_value = self.temp_dir

        recommendations = [
            {"title": "Add authentication", "description": "Add auth flow"}
        ]
        feature_path, count = generate_feature_structure(
            "user-auth",
            recommendations,
            None,
            {}
        )

        assert feature_path.exists()
        assert feature_path.name == "user-auth"
        assert count == 1

    @patch('feature_plan_orchestrator.get_git_root')
    def test_creates_readme(self, mock_git_root):
        """Test that README.md is created."""
        mock_git_root.return_value = self.temp_dir

        recommendations = [{"title": "Task 1"}]
        feature_path, _ = generate_feature_structure(
            "test-feature",
            recommendations,
            None,
            {}
        )

        readme_path = feature_path / "README.md"
        assert readme_path.exists()
        assert "Feature: Test Feature" in readme_path.read_text()

    @patch('feature_plan_orchestrator.get_git_root')
    def test_creates_implementation_guide(self, mock_git_root):
        """Test that IMPLEMENTATION-GUIDE.md is created."""
        mock_git_root.return_value = self.temp_dir

        recommendations = [{"title": "Task 1"}, {"title": "Task 2"}]
        feature_path, _ = generate_feature_structure(
            "test-feature",
            recommendations,
            None,
            {}
        )

        guide_path = feature_path / "IMPLEMENTATION-GUIDE.md"
        assert guide_path.exists()
        assert "Implementation Guide" in guide_path.read_text()
        assert "Wave 1" in guide_path.read_text()

    @patch('feature_plan_orchestrator.get_git_root')
    def test_creates_subtask_files(self, mock_git_root):
        """Test that subtask files are created."""
        mock_git_root.return_value = self.temp_dir

        recommendations = [
            {"title": "Add login", "description": "Add login flow"},
            {"title": "Add logout", "description": "Add logout flow"},
        ]
        feature_path, count = generate_feature_structure(
            "auth",
            recommendations,
            None,
            {}
        )

        assert count == 2

        # Check subtask files exist
        subtasks = list(feature_path.glob("TASK-AUTH-*.md"))
        assert len(subtasks) == 2


class TestExecuteContextBClarification:
    """Test Context B clarification execution."""

    def test_skips_when_no_questions_flag(self):
        """Test clarification is skipped with no_questions flag."""
        flags = {"no_questions": True}
        review_findings = {"task_context": {"metadata": {"complexity": 5}}}

        result = execute_context_b_clarification(review_findings, 3, flags)

        # Should return skip context
        assert result is not None
        assert result.mode == "skip"

    def test_skips_for_low_complexity(self):
        """Test clarification is skipped for low complexity tasks."""
        flags = {}
        review_findings = {"task_context": {"metadata": {"complexity": 2}}}

        result = execute_context_b_clarification(review_findings, 3, flags)

        # Should return skip context for complexity 2
        assert result is not None
        # Low complexity returns skip context
        assert result.mode == "skip" or result.user_override == "skip"


class TestExecuteFeaturePlan:
    """Test main execute_feature_plan function."""

    def test_empty_description_raises_error(self):
        """Test that empty description raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            execute_feature_plan("", {})

    def test_whitespace_description_raises_error(self):
        """Test that whitespace-only description raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            execute_feature_plan("   ", {})

    def test_returns_dict_structure(self):
        """Test that function returns expected dict structure."""
        # This will fail at task creation since we're not in a git repo,
        # but we can verify error handling returns proper structure
        result = execute_feature_plan("test feature", {})

        assert isinstance(result, dict)
        assert "status" in result
        # Should be error since we're not in a proper environment
        assert result["status"] == "error"


class TestIntegration:
    """Integration tests for feature plan workflow."""

    def setup_method(self):
        """Create complete test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.tasks_dir = self.temp_dir / "tasks"

        # Create all required directories
        for subdir in ["backlog", "in_progress", "in_review", "review_complete"]:
            (self.tasks_dir / subdir).mkdir(parents=True)

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    @patch('feature_plan_orchestrator.get_git_root')
    def test_create_and_generate_workflow(self, mock_git_root):
        """Test creating review task and generating feature structure."""
        mock_git_root.return_value = self.temp_dir

        # Create review task
        task_id, complexity = create_review_task(
            "Add user authentication",
            {"priority": "medium"}
        )

        assert task_id.startswith("REV-")

        # Verify task file was created
        task_file = list(self.tasks_dir.glob(f"backlog/{task_id}.md"))
        assert len(task_file) == 1

        # Generate feature structure (simulating after review)
        recommendations = [
            {"title": "Add login form", "description": "Create login UI"},
            {"title": "Add auth service", "description": "Create auth backend"},
        ]

        feature_path, count = generate_feature_structure(
            "user-auth",
            recommendations,
            None,
            {}
        )

        assert feature_path.exists()
        assert count == 2

        # Verify all expected files
        assert (feature_path / "README.md").exists()
        assert (feature_path / "IMPLEMENTATION-GUIDE.md").exists()
        assert len(list(feature_path.glob("TASK-*.md"))) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
