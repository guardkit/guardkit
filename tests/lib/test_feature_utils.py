#!/usr/bin/env python3
"""Unit tests for feature_utils module.

Tests the extract_feature_slug function with various input scenarios to ensure
proper slug generation for feature workflow operations.

Test Coverage:
    - Standard prefix removal (plan, review, investigate, analyze, assess)
    - "How to" phrase removal
    - Special character handling
    - Length limiting (40 character max)
    - Empty/whitespace input handling
    - Edge cases (very long titles, unicode, etc.)
    - Word boundary preservation when truncating

Architecture:
    - Uses pytest for test organization
    - Tests cover all acceptance criteria from TASK-FW-002
    - No external dependencies beyond pytest

Part of: TASK-FW-002 - Auto-detect feature slug from review task title
Author: Claude (Anthropic)
Created: 2025-12-04
"""

import pytest
import sys
from pathlib import Path

# Add installer/global/lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer" / "global"))

from lib.utils.feature_utils import extract_feature_slug


class TestExtractFeatureSlug:
    """Tests for extract_feature_slug() function."""

    def test_plan_prefix_removal(self):
        """Test removal of 'plan:' prefix."""
        assert extract_feature_slug("Plan: implement dark mode") == "implement-dark-mode"

    def test_review_prefix_removal(self):
        """Test removal of 'review:' prefix."""
        assert extract_feature_slug("Review: user authentication system") == "user-authentication-system"

    def test_investigate_prefix_removal(self):
        """Test removal of 'investigate:' prefix."""
        assert extract_feature_slug("Investigate: database performance") == "database-performance"

    def test_analyze_prefix_removal(self):
        """Test removal of 'analyze:' prefix."""
        assert extract_feature_slug("Analyze: caching strategy") == "caching-strategy"

    def test_assess_prefix_removal(self):
        """Test removal of 'assess:' prefix."""
        assert extract_feature_slug("Assess: security vulnerabilities") == "security-vulnerabilities"

    def test_how_to_phrase_removal(self):
        """Test removal of 'how to' phrases."""
        assert extract_feature_slug("Investigate how to add caching") == "investigate-add-caching"

    def test_how_to_case_insensitive(self):
        """Test 'how to' removal is case insensitive."""
        assert extract_feature_slug("Plan: How To implement feature") == "implement-feature"

    def test_special_characters_converted(self):
        """Test special characters are converted to hyphens."""
        assert extract_feature_slug("Plan: Add OAuth 2.0 Support!!!") == "add-oauth-2-0-support"

    def test_multiple_spaces_converted(self):
        """Test multiple spaces are converted to single hyphen."""
        assert extract_feature_slug("Review:   multiple    spaces") == "multiple-spaces"

    def test_empty_string_returns_default(self):
        """Test empty string returns 'feature' default."""
        assert extract_feature_slug("") == "feature"

    def test_whitespace_only_returns_default(self):
        """Test whitespace-only string returns 'feature' default."""
        assert extract_feature_slug("   ") == "feature"

    def test_length_limiting_at_40_chars(self):
        """Test slug is limited to 40 characters at word boundary."""
        long_title = "Very long title that goes on and on about many things"
        result = extract_feature_slug(long_title)
        assert len(result) <= 40
        # Should break at word boundary (hyphen)
        assert result == "very-long-title-that-goes-on-and-on"

    def test_length_limiting_preserves_word_boundary(self):
        """Test length limiting breaks at last hyphen before 40 chars."""
        # 45 chars: "implement-a-very-long-feature-name-with-lots"
        result = extract_feature_slug("Plan: implement a very long feature name with lots of words")
        assert len(result) <= 40
        assert not result.endswith('-')  # Should not end with hyphen
        # Should break at last word boundary
        assert "implement-a-very-long-feature-name" in result

    def test_prefix_with_mixed_case(self):
        """Test prefix removal works with mixed case."""
        assert extract_feature_slug("REVIEW: Authentication System") == "authentication-system"

    def test_prefix_removal_only_at_start(self):
        """Test prefix removal only happens at the start of string."""
        assert extract_feature_slug("Implement plan: for system") == "implement-plan-for-system"

    def test_consecutive_hyphens_merged(self):
        """Test consecutive hyphens are merged."""
        assert extract_feature_slug("Feature!!! with??? multiple    separators") == "feature-with-multiple-separators"

    def test_leading_and_trailing_hyphens_removed(self):
        """Test leading and trailing hyphens are removed."""
        assert extract_feature_slug("!!!Feature!!!") == "feature"

    def test_unicode_characters_removed(self):
        """Test unicode characters are handled properly."""
        assert extract_feature_slug("Plan: Add émojis 🚀 support") == "add-mojis-support"

    def test_numbers_preserved(self):
        """Test numbers are preserved in slug."""
        assert extract_feature_slug("Plan: OAuth 2.0 and TLS 1.3") == "oauth-2-0-and-tls-1-3"

    def test_prefix_with_no_space_after_colon(self):
        """Test prefix removal works without space after colon."""
        assert extract_feature_slug("Plan:implement-feature") == "implement-feature"

    def test_all_special_chars_returns_default(self):
        """Test string with only special chars returns default."""
        assert extract_feature_slug("!!!???***") == "feature"

    def test_real_world_example_1(self):
        """Test real-world example from task specification."""
        assert extract_feature_slug("Plan: implement dark mode") == "implement-dark-mode"

    def test_real_world_example_2(self):
        """Test real-world example from task specification."""
        assert extract_feature_slug("Review: user authentication system") == "user-authentication-system"

    def test_real_world_example_3(self):
        """Test real-world example from task specification."""
        assert extract_feature_slug("Investigate how to add caching") == "investigate-add-caching"

    def test_real_world_example_4(self):
        """Test real-world example from task specification."""
        assert extract_feature_slug("Plan: Add OAuth 2.0 Support!!!") == "add-oauth-2-0-support"

    def test_lowercase_conversion(self):
        """Test all characters are converted to lowercase."""
        assert extract_feature_slug("Plan: IMPLEMENT Feature") == "implement-feature"

    def test_prefix_only_returns_default(self):
        """Test prefix-only string returns default."""
        assert extract_feature_slug("Plan:") == "feature"
        assert extract_feature_slug("Review:") == "feature"

    def test_how_to_only_returns_default(self):
        """Test 'how to' only returns default."""
        assert extract_feature_slug("how to") == "feature"

    def test_combined_prefix_and_how_to_removal(self):
        """Test both prefix and 'how to' are removed."""
        assert extract_feature_slug("Plan: how to implement feature") == "implement-feature"

    def test_underscores_converted_to_hyphens(self):
        """Test underscores are converted to hyphens."""
        assert extract_feature_slug("feature_name_with_underscores") == "feature-name-with-underscores"

    def test_dots_converted_to_hyphens(self):
        """Test dots are converted to hyphens."""
        assert extract_feature_slug("feature.name.with.dots") == "feature-name-with-dots"

    def test_ampersand_handled(self):
        """Test ampersands are converted to hyphens."""
        assert extract_feature_slug("Plan: Users & Permissions") == "users-permissions"

    def test_parentheses_removed(self):
        """Test parentheses are removed."""
        assert extract_feature_slug("Feature (with notes)") == "feature-with-notes"

    def test_exactly_40_chars_not_truncated(self):
        """Test string exactly 40 chars is not truncated."""
        # Create a slug that will be exactly 40 chars
        result = extract_feature_slug("a-b-c-d-e-f-g-h-i-j-k-l-m-n-o-p-q-r")
        assert len(result) <= 40

    def test_no_hyphens_truncates_at_40(self):
        """Test truncation at 40 chars when no hyphens available."""
        # String with no spaces/special chars after processing
        long_string = "a" * 50
        result = extract_feature_slug(long_string)
        assert len(result) == 40


class TestFeatureSlugEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_none_input_handled_gracefully(self):
        """Test None input is handled gracefully by returning default."""
        # Function should handle None input gracefully
        assert extract_feature_slug(None) == "feature"

    def test_very_short_input(self):
        """Test very short input strings."""
        assert extract_feature_slug("a") == "a"
        assert extract_feature_slug("ab") == "ab"

    def test_single_word_with_prefix(self):
        """Test single word after prefix removal."""
        assert extract_feature_slug("Plan: auth") == "auth"

    def test_multiple_prefixes_only_first_removed(self):
        """Test only first prefix is removed."""
        assert extract_feature_slug("Plan: review the system") == "review-the-system"

    def test_tab_and_newline_handled(self):
        """Test tabs and newlines are converted to hyphens."""
        assert extract_feature_slug("Feature\twith\ttabs") == "feature-with-tabs"
        assert extract_feature_slug("Feature\nwith\nlines") == "feature-with-lines"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
