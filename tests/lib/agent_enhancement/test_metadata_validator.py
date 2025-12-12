"""
Test metadata validator functionality.

TASK-META-FIX: Test stack normalization and library detection.
"""

import pytest
from pathlib import Path
import sys

# Import the module to test
lib_path = Path(__file__).parent.parent.parent.parent / 'installer' / 'core' / 'lib' / 'agent_enhancement'
sys.path.insert(0, str(lib_path))

from metadata_validator import (
    validate_stack,
    is_library,
    normalize_stack_value,
    extract_libraries_from_stack,
    post_process_metadata,
    VALID_STACKS,
    STACK_NORMALIZATIONS,
    LIBRARY_NOT_STACK,
)


class TestValidateStack:
    """Test stack validation and normalization."""

    def test_valid_stack_unchanged(self):
        """Test that valid stack values pass through unchanged."""
        stack = ['python', 'typescript', 'react']
        normalized, warnings = validate_stack(stack)

        assert normalized == ['python', 'typescript', 'react']
        assert len(warnings) == 0

    def test_normalize_dotnet_maui(self):
        """Test that dotnet-maui is normalized to maui."""
        stack = ['dotnet-maui', 'csharp']
        normalized, warnings = validate_stack(stack)

        assert 'maui' in normalized
        assert 'csharp' in normalized
        assert 'dotnet-maui' not in normalized
        assert any("Normalized 'dotnet-maui' to 'maui'" in w for w in warnings)

    def test_normalize_dotnet_core(self):
        """Test that dotnet-core is normalized to dotnet."""
        stack = ['dotnet-core']
        normalized, warnings = validate_stack(stack)

        assert normalized == ['dotnet']
        assert any("Normalized 'dotnet-core' to 'dotnet'" in w for w in warnings)

    def test_normalize_case_insensitive(self):
        """Test that stack values are normalized to lowercase."""
        stack = ['Python', 'REACT', 'TypeScript']
        normalized, warnings = validate_stack(stack)

        assert normalized == ['python', 'react', 'typescript']

    def test_normalize_csharp_alias(self):
        """Test that c# is normalized to csharp."""
        stack = ['c#']
        normalized, warnings = validate_stack(stack)

        assert normalized == ['csharp']
        assert any("Normalized 'c#' to 'csharp'" in w for w in warnings)

    def test_library_moved_to_keywords(self):
        """Test that library names are excluded from stack."""
        stack = ['python', 'erroror', 'fastapi']
        normalized, warnings = validate_stack(stack)

        assert 'python' in normalized
        assert 'erroror' not in normalized
        assert 'fastapi' not in normalized
        assert any("'erroror' is a library" in w for w in warnings)
        assert any("'fastapi' is a library" in w for w in warnings)

    def test_unknown_stack_kept_with_warning(self):
        """Test that unknown stack values are kept but with warning."""
        stack = ['unknown-stack', 'python']
        normalized, warnings = validate_stack(stack)

        assert 'python' in normalized
        assert 'unknown-stack' in normalized
        assert any("Unknown stack value 'unknown-stack'" in w for w in warnings)

    def test_empty_stack(self):
        """Test that empty stack returns empty."""
        normalized, warnings = validate_stack([])

        assert normalized == []
        assert warnings == []

    def test_none_stack(self):
        """Test that None stack returns empty."""
        normalized, warnings = validate_stack(None)

        assert normalized == []
        assert warnings == []

    def test_mixed_valid_invalid_library(self):
        """Test complex case with valid, invalid, and library values."""
        stack = ['dotnet-maui', 'csharp', 'erroror', 'unknown', 'Python']
        normalized, warnings = validate_stack(stack)

        assert 'maui' in normalized
        assert 'csharp' in normalized
        assert 'python' in normalized
        assert 'unknown' in normalized  # Unknown kept with warning
        assert 'erroror' not in normalized  # Library excluded
        assert len(warnings) >= 3  # At least 3 warnings (normalize, library, unknown)


class TestIsLibrary:
    """Test library detection."""

    def test_erroror_is_library(self):
        """Test that erroror is detected as library."""
        assert is_library('erroror') is True
        assert is_library('ErrorOr') is True

    def test_testing_libraries(self):
        """Test that testing libraries are detected."""
        assert is_library('xunit') is True
        assert is_library('nsubstitute') is True
        assert is_library('pytest') is True
        assert is_library('vitest') is True
        assert is_library('jest') is True

    def test_api_libraries(self):
        """Test that API libraries are detected."""
        assert is_library('fastapi') is True
        assert is_library('flask') is True
        assert is_library('express') is True
        assert is_library('nestjs') is True

    def test_state_management_libraries(self):
        """Test that state management libraries are detected."""
        assert is_library('redux') is True
        assert is_library('react-query') is True

    def test_valid_stacks_not_libraries(self):
        """Test that valid stack values are not detected as libraries."""
        assert is_library('python') is False
        assert is_library('react') is False
        assert is_library('dotnet') is False
        assert is_library('maui') is False

    def test_non_string_returns_false(self):
        """Test that non-string values return False."""
        assert is_library(None) is False
        assert is_library(123) is False
        assert is_library(['erroror']) is False


class TestNormalizeStackValue:
    """Test single stack value normalization."""

    def test_dotnet_maui_normalized(self):
        """Test dotnet-maui normalization."""
        value, was_normalized = normalize_stack_value('dotnet-maui')
        assert value == 'maui'
        assert was_normalized is True

    def test_valid_value_unchanged(self):
        """Test valid value returns lowercase."""
        value, was_normalized = normalize_stack_value('Python')
        assert value == 'python'
        assert was_normalized is True  # Changed case

        value, was_normalized = normalize_stack_value('python')
        assert value == 'python'
        assert was_normalized is False  # No change

    def test_csharp_aliases(self):
        """Test c# aliases."""
        value, was_normalized = normalize_stack_value('c#')
        assert value == 'csharp'
        assert was_normalized is True

        value, was_normalized = normalize_stack_value('.net')
        assert value == 'dotnet'
        assert was_normalized is True


class TestExtractLibrariesFromStack:
    """Test library extraction from stack list."""

    def test_extract_single_library(self):
        """Test extracting single library."""
        clean, libs = extract_libraries_from_stack(['python', 'erroror'])

        assert clean == ['python']
        assert libs == ['erroror']

    def test_extract_multiple_libraries(self):
        """Test extracting multiple libraries."""
        clean, libs = extract_libraries_from_stack(['python', 'erroror', 'fastapi', 'pytest'])

        assert clean == ['python']
        assert sorted(libs) == sorted(['erroror', 'fastapi', 'pytest'])

    def test_no_libraries(self):
        """Test with no libraries."""
        clean, libs = extract_libraries_from_stack(['python', 'react', 'typescript'])

        assert clean == ['python', 'react', 'typescript']
        assert libs == []

    def test_all_libraries(self):
        """Test with all libraries (edge case)."""
        clean, libs = extract_libraries_from_stack(['erroror', 'pytest', 'fastapi'])

        assert clean == []
        assert sorted(libs) == sorted(['erroror', 'pytest', 'fastapi'])


class TestPostProcessMetadata:
    """Test full metadata post-processing."""

    def test_normalize_stack_in_metadata(self):
        """Test stack normalization in metadata dict."""
        metadata = {
            'stack': ['dotnet-maui', 'csharp'],
            'phase': 'implementation'
        }

        fixed, warnings = post_process_metadata(metadata)

        assert 'maui' in fixed['stack']
        assert 'csharp' in fixed['stack']
        assert 'dotnet-maui' not in fixed['stack']
        assert len(warnings) > 0

    def test_move_library_to_keywords(self):
        """Test that libraries are moved to keywords."""
        metadata = {
            'stack': ['csharp', 'maui', 'erroror'],
            'phase': 'implementation',
            'keywords': ['existing']
        }

        fixed, warnings = post_process_metadata(metadata)

        assert 'erroror' not in fixed['stack']
        assert 'erroror' in fixed['keywords']
        assert 'existing' in fixed['keywords']

    def test_create_keywords_if_missing(self):
        """Test that keywords list is created if missing."""
        metadata = {
            'stack': ['python', 'erroror'],
            'phase': 'implementation'
        }

        fixed, warnings = post_process_metadata(metadata)

        assert 'keywords' in fixed
        assert 'erroror' in fixed['keywords']

    def test_preserve_other_fields(self):
        """Test that other metadata fields are preserved."""
        metadata = {
            'stack': ['python'],
            'phase': 'implementation',
            'capabilities': ['api', 'async'],
            'custom_field': 'preserved'
        }

        fixed, warnings = post_process_metadata(metadata)

        assert fixed['phase'] == 'implementation'
        assert fixed['capabilities'] == ['api', 'async']
        assert fixed['custom_field'] == 'preserved'

    def test_empty_metadata(self):
        """Test with empty metadata."""
        fixed, warnings = post_process_metadata({})

        assert fixed == {}
        assert warnings == []

    def test_none_metadata(self):
        """Test with None metadata."""
        fixed, warnings = post_process_metadata(None)

        assert fixed is None
        assert warnings == []

    def test_no_stack_field(self):
        """Test with metadata missing stack field."""
        metadata = {
            'phase': 'implementation',
            'keywords': ['test']
        }

        fixed, warnings = post_process_metadata(metadata)

        assert fixed == metadata
        assert warnings == []

    def test_combined_normalization_and_library_extraction(self):
        """Test comprehensive case from task description."""
        # This is the exact scenario from TASK-REV-CB0F
        metadata = {
            'stack': ['dotnet-maui', 'csharp', 'erroror'],
            'phase': 'implementation',
            'keywords': ['railway-oriented']
        }

        fixed, warnings = post_process_metadata(metadata)

        # Stack should have maui and csharp
        assert 'maui' in fixed['stack']
        assert 'csharp' in fixed['stack']
        assert 'dotnet-maui' not in fixed['stack']
        assert 'erroror' not in fixed['stack']

        # Keywords should have erroror
        assert 'erroror' in fixed['keywords']
        assert 'railway-oriented' in fixed['keywords']

        # Should have warnings for both normalization and library
        assert any('dotnet-maui' in w and 'maui' in w for w in warnings)
        assert any('erroror' in w and 'library' in w for w in warnings)


class TestConstants:
    """Test that constants are properly defined."""

    def test_valid_stacks_contains_expected(self):
        """Test VALID_STACKS contains expected values."""
        expected = ['python', 'typescript', 'csharp', 'react', 'dotnet', 'maui', 'cross-stack']
        for stack in expected:
            assert stack in VALID_STACKS

    def test_normalizations_map_correctly(self):
        """Test STACK_NORMALIZATIONS map correctly."""
        assert STACK_NORMALIZATIONS['dotnet-maui'] == 'maui'
        assert STACK_NORMALIZATIONS['c#'] == 'csharp'
        assert STACK_NORMALIZATIONS['.net'] == 'dotnet'

    def test_libraries_contain_expected(self):
        """Test LIBRARY_NOT_STACK contains expected values."""
        expected = ['erroror', 'pytest', 'fastapi', 'redux', 'xunit']
        for lib in expected:
            assert lib in LIBRARY_NOT_STACK
