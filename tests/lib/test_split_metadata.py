"""
Unit tests for TemplateSplitMetadata (TASK-PD-007)

Tests the split metadata model and its integration with TemplateSplitOutput,
including metadata generation, validation status tracking, and serialization.
"""

import pytest
from lib.template_generator.models import (
    TemplateSplitMetadata,
    TemplateSplitOutput
)


class TestTemplateSplitMetadata:
    """Test TemplateSplitMetadata dataclass"""

    def test_metadata_creation_valid(self):
        """Test creating metadata with valid data"""
        metadata = TemplateSplitMetadata(
            core_size_bytes=8192,
            patterns_size_bytes=12288,
            reference_size_bytes=10240,
            total_size_bytes=30720,
            reduction_percent=73.33,
            generated_at="2025-12-05T10:30:00Z",
            validation_passed=True,
            validation_errors=[]
        )

        assert metadata.core_size_bytes == 8192
        assert metadata.patterns_size_bytes == 12288
        assert metadata.reference_size_bytes == 10240
        assert metadata.total_size_bytes == 30720
        assert metadata.reduction_percent == 73.33
        assert metadata.generated_at == "2025-12-05T10:30:00Z"
        assert metadata.validation_passed is True
        assert metadata.validation_errors == []

    def test_metadata_creation_with_errors(self):
        """Test creating metadata with validation errors"""
        metadata = TemplateSplitMetadata(
            core_size_bytes=11264,  # Exceeds 10KB
            patterns_size_bytes=12288,
            reference_size_bytes=10240,
            total_size_bytes=33792,
            reduction_percent=66.67,
            generated_at="2025-12-05T10:30:00Z",
            validation_passed=False,
            validation_errors=["Core content exceeds 10KB limit: 11.00KB"]
        )

        assert metadata.validation_passed is False
        assert len(metadata.validation_errors) == 1
        assert "exceeds 10KB limit" in metadata.validation_errors[0]

    def test_metadata_to_dict(self):
        """Test metadata serialization to dictionary"""
        metadata = TemplateSplitMetadata(
            core_size_bytes=8192,
            patterns_size_bytes=12288,
            reference_size_bytes=10240,
            total_size_bytes=30720,
            reduction_percent=73.33,
            generated_at="2025-12-05T10:30:00Z",
            validation_passed=True,
            validation_errors=[]
        )

        result = metadata.to_dict()

        assert result['core_size_bytes'] == 8192
        assert result['patterns_size_bytes'] == 12288
        assert result['reference_size_bytes'] == 10240
        assert result['total_size_bytes'] == 30720
        assert result['reduction_percent'] == 73.33
        assert result['generated_at'] == "2025-12-05T10:30:00Z"
        assert result['validation_passed'] is True
        assert result['validation_errors'] == []

    def test_metadata_reduction_percent_bounds(self):
        """Test reduction_percent field bounds (0-100)"""
        # Valid: 0%
        metadata = TemplateSplitMetadata(
            core_size_bytes=100,
            patterns_size_bytes=0,
            reference_size_bytes=0,
            total_size_bytes=100,
            reduction_percent=0.0,
            generated_at="2025-12-05T10:30:00Z",
            validation_passed=True,
            validation_errors=[]
        )
        assert metadata.reduction_percent == 0.0

        # Valid: 100%
        metadata = TemplateSplitMetadata(
            core_size_bytes=0,
            patterns_size_bytes=100,
            reference_size_bytes=0,
            total_size_bytes=100,
            reduction_percent=100.0,
            generated_at="2025-12-05T10:30:00Z",
            validation_passed=True,
            validation_errors=[]
        )
        assert metadata.reduction_percent == 100.0


class TestTemplateSplitOutputMetadataIntegration:
    """Test TemplateSplitOutput integration with metadata"""

    def test_split_output_optional_metadata_field(self):
        """Test that metadata field is optional"""
        split_output = TemplateSplitOutput(
            core_content="# Core content",
            patterns_content="# Patterns",
            reference_content="# Reference",
            generated_at="2025-12-05T10:30:00Z"
        )

        assert split_output.metadata is None

    def test_split_output_with_metadata(self):
        """Test split output with metadata attached"""
        metadata = TemplateSplitMetadata(
            core_size_bytes=8192,
            patterns_size_bytes=12288,
            reference_size_bytes=10240,
            total_size_bytes=30720,
            reduction_percent=73.33,
            generated_at="2025-12-05T10:30:00Z",
            validation_passed=True,
            validation_errors=[]
        )

        split_output = TemplateSplitOutput(
            core_content="# Core content",
            patterns_content="# Patterns",
            reference_content="# Reference",
            generated_at="2025-12-05T10:30:00Z",
            metadata=metadata
        )

        assert split_output.metadata is not None
        assert split_output.metadata.core_size_bytes == 8192
        assert split_output.metadata.validation_passed is True

    def test_generate_metadata_valid_content(self):
        """Test generate_metadata() with valid content (≤10KB core)"""
        core = "# Core\n" * 100  # ~800 bytes
        patterns = "# Patterns\n" * 200  # ~2400 bytes
        reference = "# Reference\n" * 150  # ~1800 bytes

        split_output = TemplateSplitOutput(
            core_content=core,
            patterns_content=patterns,
            reference_content=reference,
            generated_at="2025-12-05T10:30:00Z"
        )

        metadata = split_output.generate_metadata()

        assert metadata.core_size_bytes == len(core.encode('utf-8'))
        assert metadata.patterns_size_bytes == len(patterns.encode('utf-8'))
        assert metadata.reference_size_bytes == len(reference.encode('utf-8'))
        assert metadata.total_size_bytes == len((core + patterns + reference).encode('utf-8'))
        assert metadata.validation_passed is True
        assert metadata.validation_errors == []
        assert 0 <= metadata.reduction_percent <= 100

    def test_generate_metadata_invalid_content(self):
        """Test generate_metadata() with invalid content (>10KB core)"""
        core = "# Core\n" * 2000  # ~16KB (exceeds 10KB limit)
        patterns = "# Patterns\n" * 200
        reference = "# Reference\n" * 150

        split_output = TemplateSplitOutput(
            core_content=core,
            patterns_content=patterns,
            reference_content=reference,
            generated_at="2025-12-05T10:30:00Z"
        )

        metadata = split_output.generate_metadata()

        assert metadata.validation_passed is False
        assert len(metadata.validation_errors) == 1
        assert "exceeds 10KB limit" in metadata.validation_errors[0]

    def test_generate_metadata_preserves_timestamp(self):
        """Test that generate_metadata() preserves generated_at timestamp"""
        timestamp = "2025-12-05T10:30:00Z"
        split_output = TemplateSplitOutput(
            core_content="# Core",
            patterns_content="# Patterns",
            reference_content="# Reference",
            generated_at=timestamp
        )

        metadata = split_output.generate_metadata()

        assert metadata.generated_at == timestamp

    def test_backward_compatibility_without_metadata(self):
        """Test that existing code works without metadata field"""
        split_output = TemplateSplitOutput(
            core_content="# Core",
            patterns_content="# Patterns",
            reference_content="# Reference",
            generated_at="2025-12-05T10:30:00Z"
        )

        # All existing methods should still work
        assert split_output.get_core_size() > 0
        assert split_output.get_patterns_size() > 0
        assert split_output.get_reference_size() > 0
        assert split_output.get_total_size() > 0
        assert split_output.get_reduction_percent() >= 0
        is_valid, error = split_output.validate_size_constraints()
        assert is_valid is True
        assert error is None
