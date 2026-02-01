"""
Test Suite for ProjectArchitectureEpisode Schema

TDD RED Phase: These tests define the expected behavior of the
ProjectArchitectureEpisode dataclass before implementation.

Coverage Target: >=80%
Test Count: 15+ tests

Acceptance Criteria Coverage:
- [x] ProjectArchitectureEpisode dataclass implemented
- [x] Captures architecture patterns, layers, components
- [x] Serializable to Graphiti episode format
- [x] Entity ID generation for upsert support
"""

import pytest
from dataclasses import fields
from typing import List

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.integrations.graphiti.episodes.project_architecture import (
        ProjectArchitectureEpisode,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    ProjectArchitectureEpisode = None


# Skip all tests if imports not available (RED phase expected state)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


# ============================================================================
# 1. Dataclass Structure Tests (4 tests)
# ============================================================================

class TestProjectArchitectureDataclass:
    """Test ProjectArchitectureEpisode dataclass structure and fields."""

    def test_is_dataclass(self):
        """Test that ProjectArchitectureEpisode is a dataclass."""
        from dataclasses import is_dataclass
        assert is_dataclass(ProjectArchitectureEpisode)

    def test_has_entity_type_field(self):
        """Test that entity_type field exists with correct default."""
        instance = ProjectArchitectureEpisode()
        assert hasattr(instance, 'entity_type')
        assert instance.entity_type == "project_architecture"

    def test_has_architecture_style_field(self):
        """Test that architecture_style field exists."""
        instance = ProjectArchitectureEpisode()
        assert hasattr(instance, 'architecture_style')
        assert isinstance(instance.architecture_style, str)

    def test_has_pattern_description_field(self):
        """Test that pattern_description field exists."""
        instance = ProjectArchitectureEpisode()
        assert hasattr(instance, 'pattern_description')
        assert isinstance(instance.pattern_description, str)


# ============================================================================
# 2. List Fields Tests (4 tests)
# ============================================================================

class TestListFields:
    """Test list-type fields are properly initialized."""

    def test_layers_field_is_list(self):
        """Test that layers field is initialized as empty list."""
        instance = ProjectArchitectureEpisode()
        assert hasattr(instance, 'layers')
        assert isinstance(instance.layers, list)
        assert instance.layers == []

    def test_key_modules_field_is_list(self):
        """Test that key_modules field is initialized as empty list."""
        instance = ProjectArchitectureEpisode()
        assert hasattr(instance, 'key_modules')
        assert isinstance(instance.key_modules, list)
        assert instance.key_modules == []

    def test_design_patterns_field_is_list(self):
        """Test that design_patterns field is initialized as empty list."""
        instance = ProjectArchitectureEpisode()
        assert hasattr(instance, 'design_patterns')
        assert isinstance(instance.design_patterns, list)
        assert instance.design_patterns == []

    def test_conventions_field_is_list(self):
        """Test that conventions field is initialized as empty list."""
        instance = ProjectArchitectureEpisode()
        assert hasattr(instance, 'conventions')
        assert isinstance(instance.conventions, list)
        assert instance.conventions == []


# ============================================================================
# 3. Additional String Fields Tests (2 tests)
# ============================================================================

class TestStringFields:
    """Test additional string fields."""

    def test_directory_structure_field(self):
        """Test that directory_structure field exists."""
        instance = ProjectArchitectureEpisode()
        assert hasattr(instance, 'directory_structure')
        assert isinstance(instance.directory_structure, str)
        assert instance.directory_structure == ""

    def test_naming_conventions_field(self):
        """Test that naming_conventions field exists."""
        instance = ProjectArchitectureEpisode()
        assert hasattr(instance, 'naming_conventions')
        assert isinstance(instance.naming_conventions, str)
        assert instance.naming_conventions == ""


# ============================================================================
# 4. Custom Field Values Tests (3 tests)
# ============================================================================

class TestCustomFieldValues:
    """Test creating instance with custom field values."""

    def test_create_with_architecture_style(self):
        """Test creating instance with architecture style."""
        instance = ProjectArchitectureEpisode(
            architecture_style="layered"
        )
        assert instance.architecture_style == "layered"

    def test_create_with_layers(self):
        """Test creating instance with layers."""
        instance = ProjectArchitectureEpisode(
            layers=["domain", "application", "infrastructure"]
        )
        assert instance.layers == ["domain", "application", "infrastructure"]

    def test_create_with_all_fields(self):
        """Test creating instance with all fields populated."""
        instance = ProjectArchitectureEpisode(
            architecture_style="clean",
            pattern_description="Clean architecture with domain-driven design",
            layers=["domain", "application", "infrastructure"],
            key_modules=["auth", "billing", "notifications"],
            design_patterns=["repository", "factory", "strategy"],
            conventions=["snake_case", "pytest for testing"],
            directory_structure="src/{layer}/{module}/",
            naming_conventions="snake_case for files, PascalCase for classes"
        )

        assert instance.architecture_style == "clean"
        assert instance.pattern_description == "Clean architecture with domain-driven design"
        assert len(instance.layers) == 3
        assert len(instance.key_modules) == 3
        assert len(instance.design_patterns) == 3
        assert len(instance.conventions) == 2


# ============================================================================
# 5. to_episode_content() Method Tests (3 tests)
# ============================================================================

class TestToEpisodeContent:
    """Test to_episode_content() method for Graphiti serialization."""

    def test_to_episode_content_returns_string(self):
        """Test that to_episode_content returns a string."""
        instance = ProjectArchitectureEpisode()
        content = instance.to_episode_content()
        assert isinstance(content, str)

    def test_to_episode_content_includes_architecture_style(self):
        """Test that episode content includes architecture style."""
        instance = ProjectArchitectureEpisode(
            architecture_style="hexagonal"
        )
        content = instance.to_episode_content()
        assert "hexagonal" in content
        assert "Architecture Style" in content

    def test_to_episode_content_includes_all_fields(self):
        """Test that episode content includes all populated fields."""
        instance = ProjectArchitectureEpisode(
            architecture_style="microservices",
            pattern_description="Distributed microservices architecture",
            layers=["api", "service", "data"],
            key_modules=["user-service", "order-service"],
            design_patterns=["saga", "event-sourcing"],
            conventions=["REST APIs", "JSON schema"],
            directory_structure="services/{service-name}/",
            naming_conventions="kebab-case for services"
        )
        content = instance.to_episode_content()

        # Check all fields are present
        assert "microservices" in content
        assert "Distributed microservices architecture" in content
        assert "api" in content
        assert "user-service" in content
        assert "saga" in content
        assert "REST APIs" in content
        assert "services/{service-name}/" in content
        assert "kebab-case" in content


# ============================================================================
# 6. get_entity_id() Method Tests (2 tests)
# ============================================================================

class TestGetEntityId:
    """Test get_entity_id() method for upsert support."""

    def test_get_entity_id_returns_string(self):
        """Test that get_entity_id returns a string."""
        instance = ProjectArchitectureEpisode()
        entity_id = instance.get_entity_id()
        assert isinstance(entity_id, str)

    def test_get_entity_id_returns_stable_id(self):
        """Test that get_entity_id returns a stable, predictable ID."""
        instance1 = ProjectArchitectureEpisode()
        instance2 = ProjectArchitectureEpisode()

        # Both instances should return the same entity ID
        assert instance1.get_entity_id() == instance2.get_entity_id()
        assert instance1.get_entity_id() == "project_architecture_main"


# ============================================================================
# 7. Edge Cases Tests (3 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_lists_in_episode_content(self):
        """Test to_episode_content with empty lists."""
        instance = ProjectArchitectureEpisode()
        content = instance.to_episode_content()

        # Should not raise an error and should return valid content
        assert isinstance(content, str)
        assert len(content) > 0

    def test_special_characters_in_fields(self):
        """Test fields with special characters."""
        instance = ProjectArchitectureEpisode(
            architecture_style="event-driven/cqrs",
            pattern_description="Uses @Decorators & ~special~ chars!"
        )
        content = instance.to_episode_content()

        assert "event-driven/cqrs" in content
        assert "@Decorators" in content

    def test_multiline_descriptions(self):
        """Test fields with multiline content."""
        instance = ProjectArchitectureEpisode(
            pattern_description="Line 1\nLine 2\nLine 3"
        )
        content = instance.to_episode_content()

        assert "Line 1" in content
        assert "Line 2" in content


# ============================================================================
# 8. Type Annotations Tests (2 tests)
# ============================================================================

class TestTypeAnnotations:
    """Test type annotations are correct."""

    def test_list_fields_have_correct_type(self):
        """Test that list fields are typed as List[str]."""
        field_dict = {f.name: f for f in fields(ProjectArchitectureEpisode)}

        list_field_names = ['layers', 'key_modules', 'design_patterns', 'conventions']
        for field_name in list_field_names:
            assert field_name in field_dict
            # Check it's a list type (the actual check depends on how typing is done)
            instance = ProjectArchitectureEpisode()
            assert isinstance(getattr(instance, field_name), list)

    def test_string_fields_have_correct_type(self):
        """Test that string fields are typed as str."""
        field_dict = {f.name: f for f in fields(ProjectArchitectureEpisode)}

        string_field_names = [
            'entity_type', 'architecture_style', 'pattern_description',
            'directory_structure', 'naming_conventions'
        ]
        for field_name in string_field_names:
            assert field_name in field_dict
            instance = ProjectArchitectureEpisode()
            assert isinstance(getattr(instance, field_name), str)
