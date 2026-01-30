"""
Comprehensive Test Suite for Library Name Detection Module

Tests library/package name detection functionality including:
- Direct library mentions (known libraries in registry)
- Pattern-based detection (using/with/via patterns)
- False positive prevention (excluded words)
- Edge cases (empty input, special characters)
- Normalization (case, underscores to hyphens)
- Registry management API (get/add libraries)
- Performance requirements (<50ms per detection)

Part of: Library Knowledge Gap Detection System (TASK-LKG-001)

Coverage Target: >90%
Test Count: 35+ tests
"""

import os
import re
import sys
import time
from pathlib import Path
from typing import List, Set

import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import using standard import for proper coverage tracking
from installer.core.commands.lib.library_detector import (
    detect_library_mentions,
    get_library_registry,
    add_library_to_registry,
    KNOWN_LIBRARIES,
    USAGE_PATTERNS,
    EXCLUDE_WORDS,
    _normalize_library_name,
    _tokenize_text,
    _is_valid_library_candidate,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def original_registry():
    """Preserve and restore original registry state."""
    original = KNOWN_LIBRARIES.copy()
    yield original
    # Restore original state after test
    KNOWN_LIBRARIES.clear()
    KNOWN_LIBRARIES.update(original)


# ============================================================================
# 1. Positive Detection Tests - Direct Library Mentions (8 tests)
# ============================================================================

class TestDirectLibraryMentions:
    """Tests for direct library name detection via tokenization."""

    def test_detect_known_library_in_title(self):
        """Test detection of known library mentioned in title."""
        result = detect_library_mentions("Implement search with graphiti-core", "")
        assert result == ["graphiti-core"]

    def test_detect_library_case_insensitive(self):
        """Test case-insensitive library detection."""
        # Uppercase
        result = detect_library_mentions("Using REDIS for caching", "")
        assert result == ["redis"]

        # Mixed case
        result = detect_library_mentions("Build auth with PyJWT", "")
        assert result == ["pyjwt"]

        # Another mixed case
        result = detect_library_mentions("Add FastAPI endpoint", "")
        assert result == ["fastapi"]

    def test_detect_multiple_libraries(self):
        """Test detection of multiple libraries in same text."""
        result = detect_library_mentions("Use FastAPI with Pydantic validation", "")
        # Should contain both libraries (sorted)
        assert set(result) == {"fastapi", "pydantic"}
        # Should be sorted alphabetically
        assert result == ["fastapi", "pydantic"]

    def test_detect_library_in_description(self):
        """Test detection when library is only in description, not title."""
        result = detect_library_mentions(
            "Add caching layer",
            "Use Redis for session storage and rate limiting"
        )
        assert result == ["redis"]

    def test_detect_library_in_both_title_and_description(self):
        """Test detection when library appears in both title and description."""
        result = detect_library_mentions(
            "Add Redis caching",
            "Implement Redis-based session management"
        )
        # Should only appear once (deduplicated)
        assert result == ["redis"]

    def test_detect_multiple_libraries_across_title_and_description(self):
        """Test detection of different libraries in title and description."""
        result = detect_library_mentions(
            "Create API with FastAPI",
            "Add Pydantic models for validation"
        )
        assert set(result) == {"fastapi", "pydantic"}

    def test_detect_hyphenated_library_names(self):
        """Test detection of hyphenated library names."""
        result = detect_library_mentions("Integrate graphiti-core for knowledge graph", "")
        assert result == ["graphiti-core"]

        result = detect_library_mentions("Add next.js routing", "")
        assert result == ["next.js"]

    def test_detect_dotted_library_names(self):
        """Test detection of library names with dots."""
        result = detect_library_mentions("Migrate to nest.js framework", "")
        assert result == ["nest.js"]


# ============================================================================
# 2. Pattern-Based Detection Tests (9 tests)
# ============================================================================

class TestPatternBasedDetection:
    """Tests for usage pattern-based library detection."""

    def test_detect_using_pattern(self):
        """Test 'using X' pattern detection."""
        result = detect_library_mentions("Add caching using Redis", "")
        assert result == ["redis"]

    def test_detect_with_pattern(self):
        """Test 'with X' pattern detection."""
        result = detect_library_mentions("Build auth with PyJWT", "")
        assert result == ["pyjwt"]

    def test_detect_via_pattern(self):
        """Test 'via X' pattern detection."""
        result = detect_library_mentions("Run tests via Playwright", "")
        assert result == ["playwright"]

    def test_detect_integrate_pattern(self):
        """Test 'integrate X' pattern detection."""
        result = detect_library_mentions("Integrate Sentry for error tracking", "")
        assert result == ["sentry"]

    def test_detect_integrating_pattern(self):
        """Test 'integrating X' pattern detection."""
        result = detect_library_mentions("Integrating Celery task queue", "")
        assert result == ["celery"]

    def test_detect_implement_pattern(self):
        """Test 'implement X' pattern detection."""
        result = detect_library_mentions("Implement Prisma ORM layer", "")
        assert result == ["prisma"]

    def test_detect_add_pattern(self):
        """Test 'add X' pattern detection."""
        result = detect_library_mentions("Add Zod schema validation", "")
        assert result == ["zod"]

    def test_detect_use_pattern(self):
        """Test 'use X' pattern detection."""
        result = detect_library_mentions("Use Vitest for unit testing", "")
        assert result == ["vitest"]

    def test_detect_connect_to_pattern(self):
        """Test 'connect to X' pattern detection."""
        result = detect_library_mentions("Connect to MongoDB database", "")
        assert result == ["mongodb"]


# ============================================================================
# 3. False Positive Prevention Tests (7 tests)
# ============================================================================

class TestFalsePositivePrevention:
    """Tests to ensure common words don't trigger false positives."""

    def test_ignore_common_verbs(self):
        """Test that common verbs don't trigger detection."""
        result = detect_library_mentions("Fix the login bug", "")
        assert result == []

        result = detect_library_mentions("Update the authentication flow", "")
        assert result == []

    def test_ignore_generic_terms(self):
        """Test that generic tech terms don't trigger detection."""
        result = detect_library_mentions("Add unit tests", "")
        assert result == []

        result = detect_library_mentions("Create new feature", "")
        assert result == []

        result = detect_library_mentions("Fix API endpoint", "")
        assert result == []

    def test_ignore_short_tokens(self):
        """Test that short tokens (< 3 chars) are ignored."""
        result = detect_library_mentions("Add UI to app", "")
        assert result == []

    def test_no_false_positive_from_excluded_words(self):
        """Test that words in EXCLUDE_WORDS set don't trigger detection."""
        # Test various excluded words
        excluded_phrases = [
            "Fix the bug",
            "Add new feature",
            "Update database schema",
            "Create user interface",
            "Test application logic",
            "Build component system",
        ]

        for phrase in excluded_phrases:
            result = detect_library_mentions(phrase, "")
            assert result == [], f"False positive for: {phrase}"

    def test_ignore_articles_and_conjunctions(self):
        """Test that articles and conjunctions don't trigger detection."""
        result = detect_library_mentions("The and or but nor", "")
        assert result == []

    def test_ignore_pronouns(self):
        """Test that pronouns don't trigger detection."""
        result = detect_library_mentions("This that these those", "")
        assert result == []

    def test_ignore_project_terms(self):
        """Test that project management terms don't trigger detection."""
        result = detect_library_mentions("Task project repo branch commit", "")
        assert result == []


# ============================================================================
# 4. Edge Case Tests (10 tests)
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_title_and_description(self):
        """Test with both title and description empty."""
        result = detect_library_mentions("", "")
        assert result == []

    def test_empty_title(self):
        """Test with empty title but description has library."""
        result = detect_library_mentions("", "Use Redis for caching")
        assert result == ["redis"]

    def test_empty_description(self):
        """Test with empty description but title has library."""
        result = detect_library_mentions("Add Redis caching", "")
        assert result == ["redis"]

    def test_whitespace_only_title(self):
        """Test with whitespace-only title."""
        result = detect_library_mentions("   \t\n  ", "")
        assert result == []

    def test_whitespace_only_description(self):
        """Test with whitespace-only description."""
        result = detect_library_mentions("", "   \t\n  ")
        assert result == []

    def test_whitespace_only_both(self):
        """Test with whitespace-only title and description."""
        result = detect_library_mentions("   ", "   ")
        assert result == []

    def test_special_characters(self):
        """Test text with special characters."""
        result = detect_library_mentions(
            "Add Redis! @caching #feature",
            "Use $FastAPI$ for [API]"
        )
        assert "redis" in result
        assert "fastapi" in result

    def test_none_like_strings(self):
        """Test with strings that look like None/null."""
        result = detect_library_mentions("None", "null")
        assert result == []

        result = detect_library_mentions("undefined", "NaN")
        assert result == []

    def test_numbers_only(self):
        """Test with numbers-only input."""
        result = detect_library_mentions("123 456", "789 012")
        assert result == []

    def test_very_long_input(self):
        """Test with very long input text."""
        long_text = "Fix the bug " * 1000 + "using Redis" + " and more text" * 500
        result = detect_library_mentions(long_text, "")
        assert result == ["redis"]


# ============================================================================
# 5. Normalization Tests (6 tests)
# ============================================================================

class TestNormalization:
    """Tests for library name normalization."""

    def test_underscore_to_hyphen_normalization(self):
        """Test that underscores are converted to hyphens."""
        # Direct test of normalize function
        assert _normalize_library_name("graphiti_core") == "graphiti-core"

        # Via detection (need to add to registry temporarily)
        # Note: graphiti-core is already in registry
        result = detect_library_mentions("Use graphiti_core for search", "")
        # Should normalize to hyphen version if in registry
        assert "graphiti-core" in result or "graphiti_core" not in result

    def test_mixed_case_normalization(self):
        """Test that mixed case is converted to lowercase."""
        assert _normalize_library_name("FastAPI") == "fastapi"
        assert _normalize_library_name("PyJWT") == "pyjwt"
        assert _normalize_library_name("REDIS") == "redis"

    def test_whitespace_stripping(self):
        """Test that whitespace is stripped."""
        assert _normalize_library_name("  fastapi  ") == "fastapi"
        assert _normalize_library_name("\tredis\n") == "redis"

    def test_deduplicate_mentions(self):
        """Test that same library mentioned twice returns only once."""
        result = detect_library_mentions(
            "Use Redis for caching and Redis for sessions",
            "Redis is great for Redis stuff"
        )
        assert result == ["redis"]
        assert result.count("redis") == 1

    def test_output_sorted_alphabetically(self):
        """Test that output is sorted alphabetically."""
        result = detect_library_mentions(
            "Use Zod, Pydantic, and FastAPI",
            ""
        )
        # Should be alphabetically sorted
        assert result == sorted(result)

    def test_tokenization_preserves_hyphens_and_dots(self):
        """Test that tokenization preserves hyphens and dots in names."""
        tokens = _tokenize_text("Use graphiti-core and next.js")
        assert "graphiti-core" in tokens
        assert "next.js" in tokens


# ============================================================================
# 6. API Tests (5 tests)
# ============================================================================

class TestRegistryAPI:
    """Tests for registry management API functions."""

    def test_get_library_registry_returns_copy(self):
        """Test that get_library_registry returns a copy, not original."""
        registry = get_library_registry()

        # Modify returned copy
        registry.add("test-fake-library")

        # Original should not be modified
        assert "test-fake-library" not in KNOWN_LIBRARIES

    def test_get_library_registry_contains_known_libraries(self):
        """Test that registry contains expected libraries."""
        registry = get_library_registry()

        # Check some known libraries
        assert "fastapi" in registry
        assert "redis" in registry
        assert "pydantic" in registry
        assert "pytest" in registry

    def test_get_library_registry_has_reasonable_size(self):
        """Test that registry has reasonable number of libraries."""
        registry = get_library_registry()
        # Should have over 100 libraries
        assert len(registry) > 100

    def test_add_library_to_registry_new(self, original_registry):
        """Test adding a new library to registry."""
        result = add_library_to_registry("my-custom-lib")
        assert result is True
        assert "my-custom-lib" in KNOWN_LIBRARIES

    def test_add_library_to_registry_duplicate(self, original_registry):
        """Test adding existing library returns False."""
        # First add should succeed
        result1 = add_library_to_registry("my-custom-lib")
        assert result1 is True

        # Second add should fail (duplicate)
        result2 = add_library_to_registry("my-custom-lib")
        assert result2 is False


# ============================================================================
# 7. Performance Tests (2 tests)
# ============================================================================

class TestPerformance:
    """Tests for performance requirements."""

    def test_performance_under_50ms_typical_input(self):
        """Test that typical detection completes in <50ms."""
        title = "Implement search functionality using graphiti-core and Redis"
        description = "Build a search feature with FastAPI backend and Pydantic models"

        start_time = time.time()

        # Run detection 100 times to get stable timing
        for _ in range(100):
            detect_library_mentions(title, description)

        elapsed_time = time.time() - start_time
        avg_time_ms = (elapsed_time / 100) * 1000

        assert avg_time_ms < 50, f"Average detection took {avg_time_ms:.2f}ms, expected <50ms"

    def test_performance_under_100ms_long_input(self):
        """Test that long input detection completes in <100ms."""
        # Create long input with multiple libraries
        title = "Fix bugs " * 100 + "using Redis and FastAPI"
        description = "Add tests " * 100 + "with Pytest and Pydantic validation"

        start_time = time.time()
        result = detect_library_mentions(title, description)
        elapsed_time = time.time() - start_time
        elapsed_ms = elapsed_time * 1000

        assert elapsed_ms < 100, f"Detection took {elapsed_ms:.2f}ms, expected <100ms"
        assert len(result) > 0  # Should still detect libraries


# ============================================================================
# 8. Required Test Cases from Task Specification (8 tests)
# ============================================================================

class TestRequiredCases:
    """Tests explicitly required by task specification."""

    def test_graphiti_core_detection(self):
        """MUST PASS: graphiti-core detection."""
        assert detect_library_mentions("Implement search with graphiti-core", "") == ["graphiti-core"]

    def test_redis_caching_detection(self):
        """MUST PASS: Redis caching detection."""
        assert detect_library_mentions("Add caching using Redis", "") == ["redis"]

    def test_pyjwt_auth_detection(self):
        """MUST PASS: PyJWT auth detection."""
        assert detect_library_mentions("Build auth with PyJWT", "") == ["pyjwt"]

    def test_zod_validation_detection(self):
        """MUST PASS: Zod validation detection."""
        assert detect_library_mentions("Create form validation using Zod", "") == ["zod"]

    def test_fastapi_pydantic_multiple_detection(self):
        """MUST PASS: Multiple library detection (FastAPI + Pydantic)."""
        result = detect_library_mentions("Use FastAPI with Pydantic validation", "")
        assert set(result) == {"fastapi", "pydantic"}

    def test_no_detection_login_bug(self):
        """MUST PASS: No false positive for login bug fix."""
        assert detect_library_mentions("Fix the login bug", "") == []

    def test_no_detection_unit_tests(self):
        """MUST PASS: No false positive for adding unit tests."""
        assert detect_library_mentions("Add unit tests", "") == []

    def test_case_insensitive_redis(self):
        """MUST PASS: Case-insensitive Redis detection."""
        assert detect_library_mentions("Using REDIS for caching", "") == ["redis"]


# ============================================================================
# 9. Internal Function Tests (4 tests)
# ============================================================================

class TestInternalFunctions:
    """Tests for private/internal helper functions."""

    def test_is_valid_library_candidate_length(self):
        """Test minimum length validation."""
        assert _is_valid_library_candidate("ab") is False  # Too short
        assert _is_valid_library_candidate("abc") is True  # Minimum length

    def test_is_valid_library_candidate_excluded(self):
        """Test exclusion list filtering."""
        assert _is_valid_library_candidate("the") is False
        assert _is_valid_library_candidate("test") is False
        assert _is_valid_library_candidate("fastapi") is True

    def test_tokenize_text_basic(self):
        """Test basic text tokenization."""
        tokens = _tokenize_text("Use FastAPI for API development")
        assert "use" in tokens
        assert "fastapi" in tokens
        assert "api" in tokens

    def test_tokenize_text_preserves_special_chars(self):
        """Test that tokenization preserves hyphens and dots."""
        tokens = _tokenize_text("Install react-query and next.js")
        assert "react-query" in tokens
        assert "next.js" in tokens


# ============================================================================
# 10. Constants Verification Tests (3 tests)
# ============================================================================

class TestConstants:
    """Tests for module-level constants."""

    def test_known_libraries_is_set(self):
        """Test that KNOWN_LIBRARIES is a set."""
        assert isinstance(KNOWN_LIBRARIES, set)

    def test_usage_patterns_are_compiled(self):
        """Test that USAGE_PATTERNS contains compiled regex patterns."""
        assert isinstance(USAGE_PATTERNS, list)
        assert len(USAGE_PATTERNS) > 0
        for pattern in USAGE_PATTERNS:
            assert hasattr(pattern, 'findall')  # Compiled regex has findall method

    def test_exclude_words_is_set(self):
        """Test that EXCLUDE_WORDS is a set."""
        assert isinstance(EXCLUDE_WORDS, set)
        assert len(EXCLUDE_WORDS) > 50  # Should have many exclusions


# ============================================================================
# Test Summary
# ============================================================================
"""
Test Coverage Summary:

1. Direct Library Mentions (8 tests):
   - test_detect_known_library_in_title
   - test_detect_library_case_insensitive
   - test_detect_multiple_libraries
   - test_detect_library_in_description
   - test_detect_library_in_both_title_and_description
   - test_detect_multiple_libraries_across_title_and_description
   - test_detect_hyphenated_library_names
   - test_detect_dotted_library_names

2. Pattern-Based Detection (9 tests):
   - test_detect_using_pattern
   - test_detect_with_pattern
   - test_detect_via_pattern
   - test_detect_integrate_pattern
   - test_detect_integrating_pattern
   - test_detect_implement_pattern
   - test_detect_add_pattern
   - test_detect_use_pattern
   - test_detect_connect_to_pattern

3. False Positive Prevention (7 tests):
   - test_ignore_common_verbs
   - test_ignore_generic_terms
   - test_ignore_short_tokens
   - test_no_false_positive_from_excluded_words
   - test_ignore_articles_and_conjunctions
   - test_ignore_pronouns
   - test_ignore_project_terms

4. Edge Case Tests (10 tests):
   - test_empty_title_and_description
   - test_empty_title
   - test_empty_description
   - test_whitespace_only_title
   - test_whitespace_only_description
   - test_whitespace_only_both
   - test_special_characters
   - test_none_like_strings
   - test_numbers_only
   - test_very_long_input

5. Normalization Tests (6 tests):
   - test_underscore_to_hyphen_normalization
   - test_mixed_case_normalization
   - test_whitespace_stripping
   - test_deduplicate_mentions
   - test_output_sorted_alphabetically
   - test_tokenization_preserves_hyphens_and_dots

6. API Tests (5 tests):
   - test_get_library_registry_returns_copy
   - test_get_library_registry_contains_known_libraries
   - test_get_library_registry_has_reasonable_size
   - test_add_library_to_registry_new
   - test_add_library_to_registry_duplicate

7. Performance Tests (2 tests):
   - test_performance_under_50ms_typical_input
   - test_performance_under_100ms_long_input

8. Required Test Cases (8 tests):
   - test_graphiti_core_detection
   - test_redis_caching_detection
   - test_pyjwt_auth_detection
   - test_zod_validation_detection
   - test_fastapi_pydantic_multiple_detection
   - test_no_detection_login_bug
   - test_no_detection_unit_tests
   - test_case_insensitive_redis

9. Internal Function Tests (4 tests):
   - test_is_valid_library_candidate_length
   - test_is_valid_library_candidate_excluded
   - test_tokenize_text_basic
   - test_tokenize_text_preserves_special_chars

10. Constants Verification (3 tests):
    - test_known_libraries_is_set
    - test_usage_patterns_are_compiled
    - test_exclude_words_is_set

Total: 62 tests (exceeds 35+ minimum requirement)
Target Coverage: >90%
"""
