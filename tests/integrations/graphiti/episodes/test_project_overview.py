"""Tests for ProjectOverviewEpisode schema.

This test file follows TDD RED phase - comprehensive tests written FIRST.
All tests should FAIL initially until implementation is complete.
"""

import pytest
from dataclasses import asdict
from guardkit.integrations.graphiti.episodes.project_overview import ProjectOverviewEpisode


class TestProjectOverviewEpisodeInstantiation:
    """Test basic instantiation with default and custom values."""

    def test_instantiate_with_defaults(self):
        """Should create instance with all default values."""
        episode = ProjectOverviewEpisode()

        assert episode.entity_type == "project_overview"
        assert episode.project_name == ""
        assert episode.purpose == ""
        assert episode.target_users == ""
        assert episode.primary_language == ""
        assert episode.frameworks == []
        assert episode.key_dependencies == []
        assert episode.key_goals == []
        assert episode.constraints == []
        assert episode.testing_strategy == ""
        assert episode.deployment_target == ""

    def test_instantiate_with_all_fields(self):
        """Should create instance with all fields populated."""
        episode = ProjectOverviewEpisode(
            project_name="guardkit",
            purpose="Lightweight AI-assisted development framework",
            target_users="Solo developers and small teams",
            primary_language="Python",
            frameworks=["Click", "Rich", "Pydantic"],
            key_dependencies=["graphiti-core", "pyyaml", "httpx"],
            key_goals=[
                "Quality gates for all tasks",
                "Zero ceremony workflow",
                "AI-human collaboration"
            ],
            constraints=[
                "Must support Python 3.10+",
                "Must work without RequireKit"
            ],
            testing_strategy="pytest with 80% coverage minimum",
            deployment_target="PyPI package"
        )

        assert episode.project_name == "guardkit"
        assert episode.purpose == "Lightweight AI-assisted development framework"
        assert episode.target_users == "Solo developers and small teams"
        assert episode.primary_language == "Python"
        assert len(episode.frameworks) == 3
        assert "Pydantic" in episode.frameworks
        assert len(episode.key_dependencies) == 3
        assert "graphiti-core" in episode.key_dependencies
        assert len(episode.key_goals) == 3
        assert len(episode.constraints) == 2
        assert episode.testing_strategy == "pytest with 80% coverage minimum"
        assert episode.deployment_target == "PyPI package"

    def test_instantiate_with_partial_fields(self):
        """Should handle partial field population."""
        episode = ProjectOverviewEpisode(
            project_name="test-project",
            purpose="Test purpose",
            primary_language="TypeScript"
        )

        assert episode.project_name == "test-project"
        assert episode.purpose == "Test purpose"
        assert episode.primary_language == "TypeScript"
        # Defaults for unprovided fields
        assert episode.frameworks == []
        assert episode.key_goals == []


class TestProjectOverviewEpisodeEntityId:
    """Test entity ID generation for Graphiti upsert."""

    def test_get_entity_id_basic(self):
        """Should generate stable entity ID from project name."""
        episode = ProjectOverviewEpisode(project_name="guardkit")
        entity_id = episode.get_entity_id()

        assert entity_id == "project_overview_guardkit"

    def test_get_entity_id_with_spaces(self):
        """Should handle project names with spaces."""
        episode = ProjectOverviewEpisode(project_name="My Cool Project")
        entity_id = episode.get_entity_id()

        # Should normalize spaces to underscores or similar
        assert "My_Cool_Project" in entity_id or "my-cool-project" in entity_id
        assert entity_id.startswith("project_overview_")

    def test_get_entity_id_stability(self):
        """Same project name should always generate same entity ID."""
        episode1 = ProjectOverviewEpisode(project_name="guardkit")
        episode2 = ProjectOverviewEpisode(
            project_name="guardkit",
            purpose="Different purpose"
        )

        assert episode1.get_entity_id() == episode2.get_entity_id()

    def test_get_entity_id_empty_project_name(self):
        """Should handle empty project name gracefully."""
        episode = ProjectOverviewEpisode(project_name="")
        entity_id = episode.get_entity_id()

        # Should still be valid, perhaps with default
        assert entity_id.startswith("project_overview_")


class TestProjectOverviewEpisodeToEpisodeContent:
    """Test conversion to natural language for Graphiti."""

    def test_to_episode_content_minimal(self):
        """Should generate content with minimal fields."""
        episode = ProjectOverviewEpisode(
            project_name="guardkit",
            purpose="Task workflow system",
            target_users="Developers"
        )

        content = episode.to_episode_content()

        assert isinstance(content, str)
        assert len(content) > 0
        assert "guardkit" in content
        assert "Task workflow system" in content
        assert "Developers" in content

    def test_to_episode_content_full(self):
        """Should generate comprehensive content with all fields."""
        episode = ProjectOverviewEpisode(
            project_name="guardkit",
            purpose="Lightweight AI-assisted development framework",
            target_users="Solo developers and small teams",
            primary_language="Python",
            frameworks=["Click", "Rich", "Pydantic"],
            key_dependencies=["graphiti-core", "pyyaml"],
            key_goals=[
                "Quality gates for all tasks",
                "Zero ceremony workflow"
            ],
            constraints=[
                "Must support Python 3.10+"
            ],
            testing_strategy="pytest with 80% coverage",
            deployment_target="PyPI package"
        )

        content = episode.to_episode_content()

        # Should contain all major components
        assert "guardkit" in content
        assert "Lightweight AI-assisted development framework" in content
        assert "Solo developers and small teams" in content
        assert "Python" in content
        assert "Click" in content or "Rich" in content or "Pydantic" in content
        assert "graphiti-core" in content or "pyyaml" in content
        assert "Quality gates" in content or "Zero ceremony" in content
        assert "pytest" in content
        assert "PyPI" in content

    def test_to_episode_content_format(self):
        """Content should be well-formatted natural language."""
        episode = ProjectOverviewEpisode(
            project_name="test-project",
            purpose="Test purpose",
            primary_language="Python"
        )

        content = episode.to_episode_content()

        # Should be readable sentences, not just data dump
        assert content[0].isupper()  # Starts with capital letter
        assert "." in content or ";" in content  # Contains punctuation
        # Should not look like JSON or dict representation
        assert not content.startswith("{")
        assert not content.startswith("[")


class TestProjectOverviewEpisodeValidation:
    """Test validation of required fields."""

    def test_validation_requires_project_name(self):
        """Should enforce project_name is not empty when validating."""
        # This test assumes there will be a validate() method
        # or validation happens in to_episode_content() or get_entity_id()
        episode = ProjectOverviewEpisode(project_name="")

        # Validation could happen in different ways:
        # 1. Explicit validate() method
        # 2. Validation in to_episode_content()
        # 3. Validation in get_entity_id()

        # For now, test that empty project_name is problematic
        with pytest.raises((ValueError, RuntimeError)):
            # Assuming validation happens when creating episode content
            if hasattr(episode, 'validate'):
                episode.validate()
            else:
                # Or validation might happen during serialization
                episode.to_episode_content()


class TestProjectOverviewEpisodeSerialization:
    """Test serialization to dict format for Graphiti."""

    def test_serialization_to_dict(self):
        """Should serialize to dict compatible with Graphiti."""
        episode = ProjectOverviewEpisode(
            project_name="guardkit",
            purpose="Task workflow system",
            primary_language="Python",
            frameworks=["Click", "Rich"]
        )

        # Use dataclass asdict for serialization
        data = asdict(episode)

        assert isinstance(data, dict)
        assert data["entity_type"] == "project_overview"
        assert data["project_name"] == "guardkit"
        assert data["purpose"] == "Task workflow system"
        assert data["primary_language"] == "Python"
        assert isinstance(data["frameworks"], list)
        assert len(data["frameworks"]) == 2

    def test_serialization_preserves_lists(self):
        """Should preserve list fields in serialization."""
        episode = ProjectOverviewEpisode(
            project_name="test",
            frameworks=["A", "B", "C"],
            key_goals=["Goal 1", "Goal 2"]
        )

        data = asdict(episode)

        assert isinstance(data["frameworks"], list)
        assert data["frameworks"] == ["A", "B", "C"]
        assert isinstance(data["key_goals"], list)
        assert data["key_goals"] == ["Goal 1", "Goal 2"]

    def test_serialization_empty_lists(self):
        """Should handle empty lists in serialization."""
        episode = ProjectOverviewEpisode(project_name="test")

        data = asdict(episode)

        assert data["frameworks"] == []
        assert data["key_dependencies"] == []
        assert data["key_goals"] == []
        assert data["constraints"] == []


class TestProjectOverviewEpisodeEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_fields(self):
        """Should handle very long text fields."""
        long_purpose = "A" * 1000
        episode = ProjectOverviewEpisode(
            project_name="test",
            purpose=long_purpose
        )

        assert episode.purpose == long_purpose
        content = episode.to_episode_content()
        assert len(content) > 0

    def test_special_characters_in_project_name(self):
        """Should handle special characters in project name."""
        episode = ProjectOverviewEpisode(project_name="my-project@2024")
        entity_id = episode.get_entity_id()

        # Should sanitize or handle special characters
        assert entity_id.startswith("project_overview_")

    def test_unicode_in_fields(self):
        """Should handle unicode characters."""
        episode = ProjectOverviewEpisode(
            project_name="プロジェクト",
            purpose="测试目的"
        )

        content = episode.to_episode_content()
        assert isinstance(content, str)
        assert len(content) > 0

    def test_empty_list_items(self):
        """Should handle lists with empty strings."""
        episode = ProjectOverviewEpisode(
            project_name="test",
            frameworks=["", "Valid", ""]
        )

        # Should filter out empty strings or handle gracefully
        content = episode.to_episode_content()
        assert "Valid" in content
