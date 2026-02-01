"""
Comprehensive Test Suite for EpisodeMetadata Schema

Tests the standard metadata schema for Graphiti episodes including:
- EpisodeMetadata dataclass creation and validation
- Required field validation
- Optional field handling
- Serialization (to_dict) and deserialization (from_dict)
- EntityType enum validation
- Schema version format validation
- ISO 8601 timestamp format validation

Coverage Target: >=85%
Test Count: 30+ tests

TDD RED Phase: All tests should fail until implementation is complete.

Acceptance Criteria:
- AC-002: EpisodeMetadata dataclass with required and optional fields
- AC-003: EntityType enum with standard entity types
- AC-004: Serialization methods (to_dict, from_dict)
"""

import pytest
from datetime import datetime, timezone

# These imports will fail initially - that's expected for TDD RED phase
from guardkit.integrations.graphiti.metadata import (
    EpisodeMetadata,
    EntityType,
)
from guardkit.integrations.graphiti.constants import SourceType


# ============================================================================
# 1. EpisodeMetadata Creation Tests (6 tests)
# ============================================================================

class TestEpisodeMetadataCreation:
    """Test EpisodeMetadata dataclass creation."""

    def test_create_with_required_fields_only(self):
        """Test creating EpisodeMetadata with only required fields."""
        metadata = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview"
        )

        assert metadata.source == "guardkit_seeding"
        assert metadata.version == "1.0.0"
        assert metadata.created_at == "2025-01-30T10:00:00Z"
        assert metadata.entity_type == "project_overview"

        # Verify optional fields default correctly
        assert metadata.updated_at is None
        assert metadata.source_hash is None
        assert metadata.source_path is None
        assert metadata.project_id is None
        assert metadata.entity_id is None
        assert metadata.expires_at is None
        assert metadata.tags is None or metadata.tags == []

    def test_create_with_all_fields(self):
        """Test creating EpisodeMetadata with all fields populated."""
        metadata = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview",
            updated_at="2025-01-30T11:00:00Z",
            source_hash="abc123def456",
            source_path="/path/to/source.md",
            project_id="PROJ-001",
            entity_id="overview_001",
            expires_at="2026-01-30T10:00:00Z",
            tags=["production", "critical"]
        )

        assert metadata.source == "guardkit_seeding"
        assert metadata.version == "1.0.0"
        assert metadata.created_at == "2025-01-30T10:00:00Z"
        assert metadata.entity_type == "project_overview"
        assert metadata.updated_at == "2025-01-30T11:00:00Z"
        assert metadata.source_hash == "abc123def456"
        assert metadata.source_path == "/path/to/source.md"
        assert metadata.project_id == "PROJ-001"
        assert metadata.entity_id == "overview_001"
        assert metadata.expires_at == "2026-01-30T10:00:00Z"
        assert metadata.tags == ["production", "critical"]

    def test_create_with_source_type_enum(self):
        """Test creating EpisodeMetadata using SourceType enum."""
        metadata = EpisodeMetadata(
            source=SourceType.GUARDKIT_SEEDING,
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview"
        )

        # Enum should resolve to string value
        assert metadata.source == "guardkit_seeding"

    def test_create_with_entity_type_enum(self):
        """Test creating EpisodeMetadata using EntityType enum."""
        metadata = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type=EntityType.PROJECT_OVERVIEW
        )

        # Enum should resolve to string value
        assert metadata.entity_type == "project_overview"

    def test_required_fields_validation(self):
        """Test that required fields cannot be empty strings."""
        with pytest.raises(ValueError, match="source"):
            EpisodeMetadata(
                source="",
                version="1.0.0",
                created_at="2025-01-30T10:00:00Z",
                entity_type="project_overview"
            )

        with pytest.raises(ValueError, match="version"):
            EpisodeMetadata(
                source="guardkit_seeding",
                version="",
                created_at="2025-01-30T10:00:00Z",
                entity_type="project_overview"
            )

    def test_tags_not_shared_between_instances(self):
        """Test that tags list is not shared between instances (mutable default check)."""
        metadata1 = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview",
            tags=["tag1"]
        )

        metadata2 = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview",
            tags=["tag2"]
        )

        assert metadata1.tags != metadata2.tags
        assert "tag1" in metadata1.tags
        assert "tag2" in metadata2.tags
        assert "tag2" not in metadata1.tags


# ============================================================================
# 2. Serialization Tests (5 tests)
# ============================================================================

class TestEpisodeMetadataSerialization:
    """Test EpisodeMetadata serialization methods."""

    def test_to_dict_with_required_fields_only(self):
        """Test to_dict() with only required fields."""
        metadata = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview"
        )

        result = metadata.to_dict()

        assert result["source"] == "guardkit_seeding"
        assert result["version"] == "1.0.0"
        assert result["created_at"] == "2025-01-30T10:00:00Z"
        assert result["entity_type"] == "project_overview"

        # None values should be excluded from dict
        assert "updated_at" not in result or result.get("updated_at") is None
        assert "source_hash" not in result or result.get("source_hash") is None

    def test_to_dict_with_all_fields(self):
        """Test to_dict() with all fields populated."""
        metadata = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview",
            updated_at="2025-01-30T11:00:00Z",
            source_hash="abc123",
            source_path="/path/to/source.md",
            project_id="PROJ-001",
            entity_id="overview_001",
            expires_at="2026-01-30T10:00:00Z",
            tags=["production"]
        )

        result = metadata.to_dict()

        assert result["source"] == "guardkit_seeding"
        assert result["version"] == "1.0.0"
        assert result["created_at"] == "2025-01-30T10:00:00Z"
        assert result["entity_type"] == "project_overview"
        assert result["updated_at"] == "2025-01-30T11:00:00Z"
        assert result["source_hash"] == "abc123"
        assert result["source_path"] == "/path/to/source.md"
        assert result["project_id"] == "PROJ-001"
        assert result["entity_id"] == "overview_001"
        assert result["expires_at"] == "2026-01-30T10:00:00Z"
        assert result["tags"] == ["production"]

    def test_from_dict_creates_metadata(self):
        """Test from_dict() creates EpisodeMetadata from dictionary."""
        data = {
            "source": "guardkit_seeding",
            "version": "1.0.0",
            "created_at": "2025-01-30T10:00:00Z",
            "entity_type": "project_overview",
            "updated_at": "2025-01-30T11:00:00Z",
            "source_hash": "abc123",
            "project_id": "PROJ-001"
        }

        metadata = EpisodeMetadata.from_dict(data)

        assert metadata.source == "guardkit_seeding"
        assert metadata.version == "1.0.0"
        assert metadata.created_at == "2025-01-30T10:00:00Z"
        assert metadata.entity_type == "project_overview"
        assert metadata.updated_at == "2025-01-30T11:00:00Z"
        assert metadata.source_hash == "abc123"
        assert metadata.project_id == "PROJ-001"

    def test_round_trip_serialization(self):
        """Test that to_dict() → from_dict() preserves data."""
        original = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview",
            updated_at="2025-01-30T11:00:00Z",
            source_hash="abc123",
            tags=["production", "critical"]
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = EpisodeMetadata.from_dict(data)

        # Verify all fields match
        assert restored.source == original.source
        assert restored.version == original.version
        assert restored.created_at == original.created_at
        assert restored.entity_type == original.entity_type
        assert restored.updated_at == original.updated_at
        assert restored.source_hash == original.source_hash
        assert restored.tags == original.tags

    def test_to_dict_excludes_none_values(self):
        """Test that to_dict() excludes None values."""
        metadata = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview",
            source_hash="abc123",  # Only one optional field set
        )

        result = metadata.to_dict()

        # Should have the one optional field
        assert result.get("source_hash") == "abc123"

        # None values should be excluded
        assert "updated_at" not in result or result.get("updated_at") is None
        assert "source_path" not in result or result.get("source_path") is None


# ============================================================================
# 3. EntityType Enum Tests (5 tests)
# ============================================================================

class TestEntityTypeEnum:
    """Test EntityType enum validation."""

    def test_entity_type_enum_values_exist(self):
        """Test that all expected EntityType values exist."""
        expected_types = [
            "PROJECT_OVERVIEW",
            "PROJECT_ARCHITECTURE",
            "FEATURE_SPEC",
            "DECISION_RECORD",
            "ROLE_CONSTRAINTS",
            "QUALITY_GATE_CONFIG",
            "IMPLEMENTATION_MODE",
            "DOMAIN_TERM",
            "CONSTRAINT"
        ]

        for type_name in expected_types:
            assert hasattr(EntityType, type_name), f"EntityType.{type_name} not found"

    def test_entity_type_enum_string_values(self):
        """Test that EntityType enum values map to correct strings."""
        assert EntityType.PROJECT_OVERVIEW.value == "project_overview"
        assert EntityType.PROJECT_ARCHITECTURE.value == "project_architecture"
        assert EntityType.FEATURE_SPEC.value == "feature_spec"
        assert EntityType.DECISION_RECORD.value == "decision_record"
        assert EntityType.ROLE_CONSTRAINTS.value == "role_constraints"
        assert EntityType.QUALITY_GATE_CONFIG.value == "quality_gate_config"
        assert EntityType.IMPLEMENTATION_MODE.value == "implementation_mode"
        assert EntityType.DOMAIN_TERM.value == "domain_term"
        assert EntityType.CONSTRAINT.value == "constraint"

    def test_entity_type_can_be_used_in_metadata(self):
        """Test that EntityType enum can be used in EpisodeMetadata."""
        metadata = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type=EntityType.FEATURE_SPEC
        )

        assert metadata.entity_type == "feature_spec"

    def test_entity_type_is_str_enum(self):
        """Test that EntityType is a string enum."""
        assert isinstance(EntityType.PROJECT_OVERVIEW, str)
        assert EntityType.PROJECT_OVERVIEW == "project_overview"

    def test_all_entity_types_unique(self):
        """Test that all EntityType enum values are unique."""
        values = [member.value for member in EntityType]
        assert len(values) == len(set(values)), "Duplicate EntityType values found"


# ============================================================================
# 4. SourceType Enum Tests (4 tests)
# ============================================================================

class TestSourceTypeEnum:
    """Test SourceType enum validation."""

    def test_source_type_enum_values_exist(self):
        """Test that all expected SourceType values exist."""
        expected_types = [
            "GUARDKIT_SEEDING",
            "USER_ADDED",
            "AUTO_CAPTURED"
        ]

        for type_name in expected_types:
            assert hasattr(SourceType, type_name), f"SourceType.{type_name} not found"

    def test_source_type_enum_string_values(self):
        """Test that SourceType enum values map to correct strings."""
        assert SourceType.GUARDKIT_SEEDING.value == "guardkit_seeding"
        assert SourceType.USER_ADDED.value == "user_added"
        assert SourceType.AUTO_CAPTURED.value == "auto_captured"

    def test_source_type_can_be_used_in_metadata(self):
        """Test that SourceType enum can be used in EpisodeMetadata."""
        metadata = EpisodeMetadata(
            source=SourceType.USER_ADDED,
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview"
        )

        assert metadata.source == "user_added"

    def test_source_type_is_str_enum(self):
        """Test that SourceType is a string enum."""
        assert isinstance(SourceType.GUARDKIT_SEEDING, str)
        assert SourceType.GUARDKIT_SEEDING == "guardkit_seeding"


# ============================================================================
# 5. Validation Tests (5 tests)
# ============================================================================

class TestMetadataValidation:
    """Test EpisodeMetadata validation logic."""

    def test_validate_schema_version_format(self):
        """Test that schema version follows semantic versioning."""
        metadata = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview"
        )

        # Version should be in X.Y.Z format
        parts = metadata.version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_validate_iso_8601_timestamp_format(self):
        """Test that timestamps are valid ISO 8601 format."""
        metadata = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview",
            updated_at="2025-01-30T11:00:00Z"
        )

        # Should be parseable as ISO format
        created = datetime.fromisoformat(metadata.created_at.replace("Z", "+00:00"))
        updated = datetime.fromisoformat(metadata.updated_at.replace("Z", "+00:00"))

        assert created.tzinfo is not None
        assert updated.tzinfo is not None

    def test_validate_source_is_valid_type(self):
        """Test that source is one of the valid SourceType values."""
        valid_sources = ["guardkit_seeding", "user_added", "auto_captured"]

        for source in valid_sources:
            metadata = EpisodeMetadata(
                source=source,
                version="1.0.0",
                created_at="2025-01-30T10:00:00Z",
                entity_type="project_overview"
            )
            assert metadata.source in valid_sources

    def test_validate_entity_type_is_valid(self):
        """Test that entity_type is one of the valid EntityType values."""
        valid_types = [
            "project_overview",
            "project_architecture",
            "feature_spec",
            "decision_record",
            "role_constraints",
            "quality_gate_config",
            "implementation_mode",
            "domain_term",
            "constraint"
        ]

        for entity_type in valid_types:
            metadata = EpisodeMetadata(
                source="guardkit_seeding",
                version="1.0.0",
                created_at="2025-01-30T10:00:00Z",
                entity_type=entity_type
            )
            assert metadata.entity_type in valid_types

    def test_tags_is_list_of_strings(self):
        """Test that tags field is a list of strings when provided."""
        metadata = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview",
            tags=["production", "critical", "v1.0"]
        )

        assert isinstance(metadata.tags, list)
        assert all(isinstance(tag, str) for tag in metadata.tags)


# ============================================================================
# 6. Helper Methods Tests (4 tests)
# ============================================================================

class TestMetadataHelperMethods:
    """Test helper methods for creating metadata."""

    def test_create_now_with_minimal_args(self):
        """Test create_now() creates instance with current timestamp."""
        before = datetime.now(timezone.utc)

        metadata = EpisodeMetadata.create_now(
            source="guardkit_seeding",
            entity_type="project_overview"
        )

        after = datetime.now(timezone.utc)

        assert metadata.source == "guardkit_seeding"
        assert metadata.entity_type == "project_overview"
        assert metadata.version == "1.0.0"

        # Parse created_at and verify it's between before and after
        created_at_dt = datetime.fromisoformat(metadata.created_at.replace('Z', '+00:00'))
        assert before <= created_at_dt <= after

    def test_create_now_with_optional_args(self):
        """Test create_now() with optional fields."""
        metadata = EpisodeMetadata.create_now(
            source="guardkit_seeding",
            entity_type="project_overview",
            project_id="PROJ-001",
            tags=["tag1", "tag2"]
        )

        assert metadata.source == "guardkit_seeding"
        assert metadata.entity_type == "project_overview"
        assert metadata.project_id == "PROJ-001"
        assert metadata.tags == ["tag1", "tag2"]
        assert metadata.created_at is not None

    def test_create_now_timestamp_format(self):
        """Test create_now() creates ISO 8601 formatted timestamp."""
        metadata = EpisodeMetadata.create_now(
            source="guardkit_seeding",
            entity_type="project_overview"
        )

        # Should be parseable as ISO format
        created_at_dt = datetime.fromisoformat(metadata.created_at.replace('Z', '+00:00'))
        assert isinstance(created_at_dt, datetime)

    def test_create_now_uses_utc(self):
        """Test create_now() uses UTC timezone."""
        metadata = EpisodeMetadata.create_now(
            source="guardkit_seeding",
            entity_type="project_overview"
        )

        # Should end with Z or be parseable as UTC
        assert 'T' in metadata.created_at
        created_at_dt = datetime.fromisoformat(metadata.created_at.replace('Z', '+00:00'))

        # Should be close to current UTC time
        now = datetime.now(timezone.utc)
        time_diff = abs((now - created_at_dt).total_seconds())
        assert time_diff < 5  # Within 5 seconds


# ============================================================================
# 7. Edge Cases and Error Handling (2 tests)
# ============================================================================

class TestMetadataEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_tags_list(self):
        """Test that empty tags list is allowed."""
        metadata = EpisodeMetadata(
            source="guardkit_seeding",
            version="1.0.0",
            created_at="2025-01-30T10:00:00Z",
            entity_type="project_overview",
            tags=[]
        )

        assert metadata.tags == []

    def test_from_dict_with_missing_optional_fields(self):
        """Test from_dict() handles missing optional fields."""
        data = {
            "source": "guardkit_seeding",
            "version": "1.0.0",
            "created_at": "2025-01-30T10:00:00Z",
            "entity_type": "project_overview"
            # All optional fields missing
        }

        metadata = EpisodeMetadata.from_dict(data)

        assert metadata.source == "guardkit_seeding"
        assert metadata.updated_at is None
        assert metadata.source_hash is None
        assert metadata.tags is None or metadata.tags == []
