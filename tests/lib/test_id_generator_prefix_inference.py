"""
Unit tests for prefix inference functionality in id_generator module.

Tests cover:
1. Prefix validation and normalization
2. Epic-based prefix inference
3. Tag-based prefix inference
4. Title-based prefix inference
5. Priority order handling
6. Prefix registry management
"""

import pytest
import sys
from pathlib import Path

# Add installer/core/lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer" / "core" / "lib"))

from id_generator import (
    validate_prefix,
    infer_prefix,
    register_prefix,
    STANDARD_PREFIXES,
    TAG_PREFIX_MAP,
    TITLE_KEYWORDS
)


class TestPrefixValidation:
    """Test suite for validate_prefix() function."""

    def test_validate_prefix_uppercase(self):
        """Test that prefixes are converted to uppercase."""
        assert validate_prefix("doc") == "DOC"
        assert validate_prefix("DOC") == "DOC"
        assert validate_prefix("Fix") == "FIX"
        assert validate_prefix("api") == "API"

    def test_validate_prefix_truncate(self):
        """Test that long prefixes are truncated to 4 characters."""
        assert validate_prefix("REFAC") == "REFA"
        assert validate_prefix("EXTRA-LONG") == "EXTR"
        assert validate_prefix("documentation") == "DOCU"
        assert validate_prefix("INFRASTRUCTURE") == "INFR"

    def test_validate_prefix_invalid_chars(self):
        """Test that invalid characters are removed."""
        assert validate_prefix("D-O-C") == "DOC"
        assert validate_prefix("API_V2") == "APIV"
        assert validate_prefix("E-01") == "E01"
        assert validate_prefix("FIX!") == "FIX"

    def test_validate_prefix_too_short(self):
        """Test that single-character prefixes raise ValueError."""
        with pytest.raises(ValueError, match="too short"):
            validate_prefix("X")

        with pytest.raises(ValueError, match="too short"):
            validate_prefix("a")

        # Edge case: two chars after invalid removal becomes one char
        with pytest.raises(ValueError, match="too short"):
            validate_prefix("X-")

    def test_validate_prefix_empty(self):
        """Test that empty prefixes raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_prefix("")

        with pytest.raises(ValueError, match="cannot be empty"):
            validate_prefix(None)

    def test_validate_prefix_valid_range(self):
        """Test valid prefix lengths (2-4 characters)."""
        assert validate_prefix("AB") == "AB"
        assert validate_prefix("ABC") == "ABC"
        assert validate_prefix("ABCD") == "ABCD"
        assert validate_prefix("E01") == "E01"


class TestEpicInference:
    """Test suite for epic-based prefix inference."""

    def test_infer_prefix_from_epic_basic(self):
        """Test basic epic number extraction."""
        assert infer_prefix(epic="EPIC-001") == "E001"
        assert infer_prefix(epic="EPIC-042") == "E042"
        assert infer_prefix(epic="EPIC-123") == "E123"

    def test_infer_prefix_epic_case_insensitive(self):
        """Test that epic matching is case-insensitive."""
        assert infer_prefix(epic="epic-001") == "E001"
        assert infer_prefix(epic="Epic-001") == "E001"
        assert infer_prefix(epic="EPIC-001") == "E001"

    def test_infer_prefix_epic_invalid_format(self):
        """Test that invalid epic formats return None."""
        # No number
        assert infer_prefix(epic="EPIC-") is None
        assert infer_prefix(epic="EPIC-ABC") is None

        # Wrong format
        assert infer_prefix(epic="INVALID") is None
        assert infer_prefix(epic="E-001") is None

    def test_infer_prefix_epic_with_text(self):
        """Test epic extraction with additional text."""
        assert infer_prefix(epic="EPIC-001 Authentication") == "E001"
        assert infer_prefix(epic="EPIC-042: Payment System") == "E042"


class TestTagInference:
    """Test suite for tag-based prefix inference."""

    def test_infer_prefix_from_tags_basic(self):
        """Test basic tag-to-prefix mapping."""
        assert infer_prefix(tags=["docs"]) == "DOC"
        assert infer_prefix(tags=["bug"]) == "FIX"
        assert infer_prefix(tags=["feature"]) == "FEAT"
        assert infer_prefix(tags=["api"]) == "API"

    def test_infer_prefix_multiple_tags(self):
        """Test that first matching tag is used."""
        # First tag matches
        assert infer_prefix(tags=["docs", "api"]) == "DOC"

        # Second tag matches (first doesn't)
        assert infer_prefix(tags=["general", "bug"]) == "FIX"

        # Multiple matches - first wins
        assert infer_prefix(tags=["docs", "api", "bug"]) == "DOC"

    def test_infer_prefix_tags_case_insensitive(self):
        """Test that tag matching is case-insensitive."""
        assert infer_prefix(tags=["DOCS"]) == "DOC"
        assert infer_prefix(tags=["Docs"]) == "DOC"
        assert infer_prefix(tags=["docs"]) == "DOC"
        assert infer_prefix(tags=["BUG"]) == "FIX"

    def test_infer_prefix_tags_no_match(self):
        """Test that unrecognized tags return None."""
        assert infer_prefix(tags=["unknown"]) is None
        assert infer_prefix(tags=["general"]) is None
        assert infer_prefix(tags=["random", "stuff"]) is None

    def test_infer_prefix_tags_synonyms(self):
        """Test that tag synonyms work correctly."""
        # Documentation synonyms
        assert infer_prefix(tags=["docs"]) == "DOC"
        assert infer_prefix(tags=["documentation"]) == "DOC"

        # Bug fix synonyms
        assert infer_prefix(tags=["bug"]) == "FIX"
        assert infer_prefix(tags=["bugfix"]) == "FIX"
        assert infer_prefix(tags=["fix"]) == "FIX"

        # Stack synonyms
        assert infer_prefix(tags=["api"]) == "API"
        assert infer_prefix(tags=["backend"]) == "API"


class TestTitleInference:
    """Test suite for title-based prefix inference."""

    def test_infer_prefix_from_title_fix(self):
        """Test Fix/Bug keyword detection."""
        assert infer_prefix(title="Fix login validation bug") == "FIX"
        assert infer_prefix(title="Bug in authentication") == "FIX"
        assert infer_prefix(title="fix: user session timeout") == "FIX"

    def test_infer_prefix_from_title_api(self):
        """Test API keyword detection."""
        assert infer_prefix(title="Add API endpoint for users") == "API"
        assert infer_prefix(title="Update user API") == "API"

    def test_infer_prefix_from_title_database(self):
        """Test database keyword detection."""
        assert infer_prefix(title="Update database schema") == "DB"
        assert infer_prefix(title="Add database migration") == "DB"

    def test_infer_prefix_from_title_document(self):
        """Test documentation keyword detection."""
        assert infer_prefix(title="Document API endpoints") == "DOC"
        assert infer_prefix(title="Add documentation for auth") == "DOC"

    def test_infer_prefix_from_title_test(self):
        """Test test keyword detection."""
        assert infer_prefix(title="Add test coverage for auth") == "TEST"
        assert infer_prefix(title="Testing authentication flow") == "TEST"

    def test_infer_prefix_title_no_match(self):
        """Test that titles without keywords return None."""
        assert infer_prefix(title="Refactor authentication module") is None
        assert infer_prefix(title="Update user profile logic") is None
        assert infer_prefix(title="General improvements") is None

    def test_infer_prefix_title_case_insensitive(self):
        """Test that title matching is case-insensitive."""
        assert infer_prefix(title="FIX login bug") == "FIX"
        assert infer_prefix(title="Fix LOGIN BUG") == "FIX"
        assert infer_prefix(title="fix login bug") == "FIX"


class TestPriorityOrder:
    """Test suite for prefix inference priority order."""

    def test_manual_override_wins(self):
        """Test that manual prefix overrides all other sources."""
        result = infer_prefix(
            manual_prefix="CUST",
            epic="EPIC-001",
            tags=["docs"],
            title="Fix bug"
        )
        assert result == "CUST"

    def test_epic_over_tags(self):
        """Test that epic has priority over tags."""
        result = infer_prefix(
            epic="EPIC-001",
            tags=["docs"],
            title="Fix bug"
        )
        assert result == "E001"

    def test_tags_over_title(self):
        """Test that tags have priority over title."""
        result = infer_prefix(
            tags=["api"],
            title="Fix bug"
        )
        assert result == "API"

    def test_title_as_fallback(self):
        """Test that title is used when no other sources available."""
        result = infer_prefix(title="Fix login bug")
        assert result == "FIX"

    def test_none_when_no_matches(self):
        """Test that None is returned when nothing matches."""
        result = infer_prefix(title="Refactor code")
        assert result is None

        result = infer_prefix(tags=["unknown"])
        assert result is None

    def test_priority_partial_sources(self):
        """Test priority with partial source availability."""
        # Only epic and title (epic wins)
        result = infer_prefix(epic="EPIC-042", title="Fix bug")
        assert result == "E042"

        # Only tags and title (tags win)
        result = infer_prefix(tags=["docs"], title="Fix bug")
        assert result == "DOC"


class TestRegistryManagement:
    """Test suite for prefix registry management."""

    def test_register_prefix(self):
        """Test registering a new custom prefix."""
        register_prefix("CUST", "Custom feature")
        assert "CUST" in STANDARD_PREFIXES
        assert STANDARD_PREFIXES["CUST"] == "Custom feature"

    def test_register_prefix_validates(self):
        """Test that register_prefix validates the prefix."""
        # Too short
        with pytest.raises(ValueError, match="too short"):
            register_prefix("X", "Invalid")

        # Empty
        with pytest.raises(ValueError):
            register_prefix("", "Empty prefix")

    def test_register_prefix_normalizes(self):
        """Test that register_prefix normalizes the prefix."""
        register_prefix("custom", "Custom Prefix")
        assert "CUST" in STANDARD_PREFIXES
        assert STANDARD_PREFIXES["CUST"] == "Custom Prefix"

    def test_register_prefix_updates_existing(self):
        """Test that registering an existing prefix updates it."""
        register_prefix("TEST", "New description")
        assert STANDARD_PREFIXES["TEST"] == "New description"


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_infer_prefix_empty_lists(self):
        """Test that empty lists are handled gracefully."""
        assert infer_prefix(tags=[]) is None
        assert infer_prefix(tags=[], title="") is None

    def test_infer_prefix_none_values(self):
        """Test that None values are handled gracefully."""
        assert infer_prefix(epic=None, tags=None, title=None) is None

    def test_infer_prefix_whitespace_only(self):
        """Test that whitespace-only strings are handled."""
        assert infer_prefix(title="   ") is None
        assert infer_prefix(epic="   ") is None

    def test_validate_prefix_special_cases(self):
        """Test special validation cases."""
        # Only numbers
        assert validate_prefix("123") == "123"

        # Mix of letters and numbers
        assert validate_prefix("E01") == "E01"
        assert validate_prefix("V2") == "V2"

    def test_infer_prefix_epic_edge_cases(self):
        """Test epic parsing edge cases."""
        # Very large epic numbers
        assert infer_prefix(epic="EPIC-999") == "E999"

        # Leading zeros
        assert infer_prefix(epic="EPIC-001") == "E001"
        assert infer_prefix(epic="EPIC-042") == "E042"


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_inference_workflow(self):
        """Test complete inference workflow."""
        # Register custom prefix
        register_prefix("AUTH", "Authentication tasks")

        # Infer with priority
        result1 = infer_prefix(
            manual_prefix="AUTH",
            epic="EPIC-001",
            tags=["api"],
            title="Fix bug"
        )
        assert result1 == "AUTH"

        # Infer from epic
        result2 = infer_prefix(
            epic="EPIC-001",
            tags=["docs"],
            title="Fix bug"
        )
        assert result2 == "E001"

    def test_validate_then_register(self):
        """Test validation followed by registration."""
        # Validate first
        normalized = validate_prefix("payment-system")
        assert normalized == "PAYM"

        # Then register
        register_prefix(normalized, "Payment System")
        assert STANDARD_PREFIXES["PAYM"] == "Payment System"


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
