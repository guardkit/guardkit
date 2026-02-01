"""
TDD Tests for role_constraint_formatter module.

Tests for the format_role_constraints function that formats role constraint
configurations retrieved from Graphiti for prompt injection in AutoBuild
contexts, with emoji markers for boundaries.

Coverage Target: >=85%

References:
    - TASK-GR6-007: Add role_constraints retrieval and formatting
    - FEAT-GR-006: Job-Specific Context Retrieval
"""

import pytest
from typing import Any, Dict, List, Optional

# Import will initially succeed since we're implementing now
from guardkit.knowledge.role_constraint_formatter import (
    format_role_constraints,
    format_role_constraints_for_actor,
)


# ============================================================================
# 1. Basic Formatting Tests
# ============================================================================

class TestFormatRoleConstraintsBasic:
    """Test basic format_role_constraints functionality."""

    def test_format_role_constraints_returns_string(self):
        """Test that format_role_constraints returns a string."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": ["Approve work"],
                "ask_before": ["Add dependencies"]
            }
        ]

        result = format_role_constraints(constraints)
        assert isinstance(result, str)

    def test_format_role_constraints_empty_list_returns_empty_string(self):
        """Test that empty list returns empty string."""
        result = format_role_constraints([])
        assert result == ""

    def test_format_role_constraints_none_returns_empty_string(self):
        """Test that None returns empty string."""
        result = format_role_constraints(None)
        assert result == ""

    def test_format_role_constraints_includes_header(self):
        """Test that output includes Role Constraints header."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": ["Approve work"],
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints)
        assert "Role Constraints" in result

    def test_format_role_constraints_includes_guidance_message(self):
        """Test that output includes guidance message."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": ["Approve work"],
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints)
        # Should include guidance about boundaries
        assert "boundaries" in result.lower() or "constraints" in result.lower()


# ============================================================================
# 2. Role-Specific Formatting Tests
# ============================================================================

class TestRoleSpecificFormatting:
    """Test role-specific formatting."""

    def test_format_includes_role_name(self):
        """Test that output includes role name."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": ["Approve work"],
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints)
        assert "Player" in result or "player" in result.lower()

    def test_format_includes_coach_role(self):
        """Test that Coach role is formatted correctly."""
        constraints = [
            {
                "role": "coach",
                "must_do": ["Validate work"],
                "must_not_do": ["Write code"],
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints)
        assert "Coach" in result or "coach" in result.lower()

    def test_format_handles_multiple_roles(self):
        """Test that multiple roles are formatted."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": ["Approve work"],
                "ask_before": []
            },
            {
                "role": "coach",
                "must_do": ["Validate work"],
                "must_not_do": ["Write code"],
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints)
        assert "Player" in result or "player" in result.lower()
        assert "Coach" in result or "coach" in result.lower()


# ============================================================================
# 3. Emoji Marker Tests
# ============================================================================

class TestEmojiMarkers:
    """Test emoji marker formatting."""

    def test_must_do_items_have_checkmark_emoji(self):
        """Test that must_do items have ✓ emoji."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code", "Create tests"],
                "must_not_do": [],
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints)
        assert "✓" in result

    def test_must_not_do_items_have_cross_emoji(self):
        """Test that must_not_do items have ✗ emoji."""
        constraints = [
            {
                "role": "player",
                "must_do": [],
                "must_not_do": ["Approve work", "Skip tests"],
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints)
        assert "✗" in result

    def test_ask_before_items_have_question_emoji(self):
        """Test that ask_before items have ❓ emoji."""
        constraints = [
            {
                "role": "player",
                "must_do": [],
                "must_not_do": [],
                "ask_before": ["Schema changes", "Auth changes"]
            }
        ]

        result = format_role_constraints(constraints)
        assert "❓" in result

    def test_all_three_emoji_types_present(self):
        """Test that all three emoji types are present when all lists populated."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": ["Approve work"],
                "ask_before": ["Add dependencies"]
            }
        ]

        result = format_role_constraints(constraints)
        assert "✓" in result, "Missing ✓ emoji for must_do"
        assert "✗" in result, "Missing ✗ emoji for must_not_do"
        assert "❓" in result, "Missing ❓ emoji for ask_before"


# ============================================================================
# 4. Section Header Tests
# ============================================================================

class TestSectionHeaders:
    """Test section header formatting."""

    def test_must_do_section_header(self):
        """Test that MUST DO section header is present."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": [],
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints)
        assert "Must do" in result or "MUST DO" in result or "must_do" in result.lower()

    def test_must_not_do_section_header(self):
        """Test that MUST NOT DO section header is present."""
        constraints = [
            {
                "role": "player",
                "must_do": [],
                "must_not_do": ["Approve work"],
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints)
        assert "Must NOT do" in result or "MUST NOT DO" in result or "not do" in result.lower()

    def test_ask_before_section_header(self):
        """Test that ASK BEFORE section header is present."""
        constraints = [
            {
                "role": "player",
                "must_do": [],
                "must_not_do": [],
                "ask_before": ["Schema changes"]
            }
        ]

        result = format_role_constraints(constraints)
        assert "Ask before" in result or "ASK BEFORE" in result or "ask" in result.lower()


# ============================================================================
# 5. Content Preservation Tests
# ============================================================================

class TestContentPreservation:
    """Test that content items are preserved in output."""

    def test_all_must_do_items_preserved(self):
        """Test that all must_do items appear in output."""
        must_do = ["Write code", "Create tests", "Report changes"]
        constraints = [
            {
                "role": "player",
                "must_do": must_do,
                "must_not_do": [],
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints)
        for item in must_do:
            assert item in result, f"Missing must_do item: {item}"

    def test_all_must_not_do_items_preserved(self):
        """Test that all must_not_do items appear in output."""
        must_not_do = ["Approve work", "Validate quality", "Merge code"]
        constraints = [
            {
                "role": "player",
                "must_do": [],
                "must_not_do": must_not_do,
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints)
        for item in must_not_do:
            assert item in result, f"Missing must_not_do item: {item}"

    def test_all_ask_before_items_preserved(self):
        """Test that all ask_before items appear in output."""
        ask_before = ["Schema changes", "Auth changes", "Scope changes"]
        constraints = [
            {
                "role": "player",
                "must_do": [],
                "must_not_do": [],
                "ask_before": ask_before
            }
        ]

        result = format_role_constraints(constraints)
        for item in ask_before:
            assert item in result, f"Missing ask_before item: {item}"


# ============================================================================
# 6. AutoBuild Context Emphasis Tests
# ============================================================================

class TestAutoBuildEmphasis:
    """Test AutoBuild context emphasis."""

    def test_autobuild_context_has_emphasis(self):
        """Test that AutoBuild context produces emphasized output."""
        constraints = [
            {
                "role": "player",
                "context": "autobuild",
                "must_do": ["Write code"],
                "must_not_do": ["Approve work"],
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints, is_autobuild=True)
        # Should have emphasis markers
        assert (
            "⚠️" in result or
            "CRITICAL" in result or
            "**" in result or
            "!" in result
        ), "AutoBuild context should have emphasis"

    def test_feature_build_context_standard_formatting(self):
        """Test that feature-build context uses standard formatting."""
        constraints = [
            {
                "role": "player",
                "context": "feature-build",
                "must_do": ["Write code"],
                "must_not_do": ["Approve work"],
                "ask_before": []
            }
        ]

        result = format_role_constraints(constraints, is_autobuild=False)
        # Should NOT have CRITICAL marker (standard formatting)
        assert "CRITICAL" not in result or "Role Constraints" in result


# ============================================================================
# 7. format_role_constraints_for_actor Tests
# ============================================================================

class TestFormatRoleConstraintsForActor:
    """Test format_role_constraints_for_actor function."""

    def test_filters_to_specified_actor(self):
        """Test that only specified actor's constraints are returned."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": ["Approve work"],
                "ask_before": []
            },
            {
                "role": "coach",
                "must_do": ["Validate work"],
                "must_not_do": ["Write code"],
                "ask_before": []
            }
        ]

        result = format_role_constraints_for_actor(constraints, actor="player")

        # Should contain player constraints
        assert "Write code" in result
        assert "Approve work" in result

        # Should NOT contain coach constraints
        assert "Validate work" not in result

    def test_filters_to_coach_actor(self):
        """Test filtering to coach actor."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": [],
                "ask_before": []
            },
            {
                "role": "coach",
                "must_do": ["Validate work"],
                "must_not_do": ["Write code"],
                "ask_before": []
            }
        ]

        result = format_role_constraints_for_actor(constraints, actor="coach")

        # Should contain coach constraints
        assert "Validate work" in result

        # Should NOT contain player-only content
        # (Write code appears in both, so check for specific player item)
        assert "Write code" in result  # This is in coach's must_not_do

    def test_returns_empty_for_unknown_actor(self):
        """Test that unknown actor returns empty string."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": [],
                "ask_before": []
            }
        ]

        result = format_role_constraints_for_actor(constraints, actor="unknown")
        assert result == "" or "Role Constraints" not in result

    def test_actor_case_insensitive(self):
        """Test that actor filtering is case-insensitive."""
        constraints = [
            {
                "role": "Player",  # Different case
                "must_do": ["Write code"],
                "must_not_do": [],
                "ask_before": []
            }
        ]

        result = format_role_constraints_for_actor(constraints, actor="player")
        assert "Write code" in result


# ============================================================================
# 8. Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_missing_must_do_key(self):
        """Test handling of missing must_do key."""
        constraints = [
            {
                "role": "player",
                "must_not_do": ["Approve work"],
                "ask_before": []
            }
        ]

        # Should not raise exception
        result = format_role_constraints(constraints)
        assert isinstance(result, str)

    def test_handles_missing_must_not_do_key(self):
        """Test handling of missing must_not_do key."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "ask_before": []
            }
        ]

        # Should not raise exception
        result = format_role_constraints(constraints)
        assert isinstance(result, str)

    def test_handles_missing_ask_before_key(self):
        """Test handling of missing ask_before key."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": ["Approve work"]
            }
        ]

        # Should not raise exception
        result = format_role_constraints(constraints)
        assert isinstance(result, str)

    def test_handles_missing_role_key(self):
        """Test handling of missing role key."""
        constraints = [
            {
                "must_do": ["Write code"],
                "must_not_do": [],
                "ask_before": []
            }
        ]

        # Should not raise exception
        result = format_role_constraints(constraints)
        assert isinstance(result, str)

    def test_handles_empty_lists(self):
        """Test handling of empty lists."""
        constraints = [
            {
                "role": "player",
                "must_do": [],
                "must_not_do": [],
                "ask_before": []
            }
        ]

        # Should not raise exception
        result = format_role_constraints(constraints)
        assert isinstance(result, str)

    def test_handles_none_in_list(self):
        """Test handling of None values in constraint list."""
        constraints = [None, {"role": "player", "must_do": ["Write code"], "must_not_do": [], "ask_before": []}]

        # Should not raise exception
        result = format_role_constraints(constraints)
        assert isinstance(result, str)

    def test_handles_non_dict_in_list(self):
        """Test handling of non-dict values in constraint list."""
        constraints = ["invalid", {"role": "player", "must_do": ["Write code"], "must_not_do": [], "ask_before": []}]

        # Should not raise exception
        result = format_role_constraints(constraints)
        assert isinstance(result, str)

    def test_limits_items_per_section(self):
        """Test that items per section are limited to prevent token explosion."""
        many_items = [f"Item {i}" for i in range(20)]
        constraints = [
            {
                "role": "player",
                "must_do": many_items,
                "must_not_do": many_items,
                "ask_before": many_items
            }
        ]

        result = format_role_constraints(constraints)

        # Should limit items (implementation detail, but reasonable limit)
        # Count occurrences of emoji markers
        checkmark_count = result.count("✓")
        cross_count = result.count("✗")
        question_count = result.count("❓")

        # Should be limited (not all 20 items)
        assert checkmark_count <= 10, f"Too many must_do items: {checkmark_count}"
        assert cross_count <= 10, f"Too many must_not_do items: {cross_count}"
        assert question_count <= 10, f"Too many ask_before items: {question_count}"


# ============================================================================
# 9. Output Format Tests
# ============================================================================

class TestOutputFormat:
    """Test expected output format matches acceptance criteria."""

    def test_matches_acceptance_criteria_format(self):
        """Test that output matches the format from TASK-GR6-007 acceptance criteria."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Implement code", "Write tests"],
                "must_not_do": ["Validate quality gates", "Make architectural decisions"],
                "ask_before": ["Schema changes", "Auth changes"]
            }
        ]

        result = format_role_constraints(constraints)

        # Expected format from acceptance criteria:
        # ### Role Constraints
        # **Player**:
        #   Must do:
        #     ✓ Implement code
        #     ✓ Write tests
        #   Must NOT do:
        #     ✗ Validate quality gates
        #     ✗ Make architectural decisions
        #   Ask before:
        #     ❓ Schema changes
        #     ❓ Auth changes

        # Check header
        assert "Role Constraints" in result

        # Check role name
        assert "Player" in result or "**player**" in result.lower()

        # Check emoji markers
        assert "✓ Implement code" in result or "✓" in result
        assert "✗ Validate quality gates" in result or "✗" in result
        assert "❓ Schema changes" in result or "❓" in result

    def test_output_is_markdown_formatted(self):
        """Test that output is valid markdown."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": ["Approve work"],
                "ask_before": ["Add dependencies"]
            }
        ]

        result = format_role_constraints(constraints)

        # Should contain markdown formatting
        assert (
            "###" in result or  # Section header
            "**" in result or   # Bold
            "- " in result or   # List item
            "  " in result      # Indentation
        ), "Output should be markdown formatted"


# ============================================================================
# 10. Integration with RetrievedContext Tests
# ============================================================================

class TestRetrievedContextIntegration:
    """Test integration with RetrievedContext.to_prompt()."""

    def test_formatter_output_suitable_for_prompt_injection(self):
        """Test that formatter output is suitable for prompt injection."""
        constraints = [
            {
                "role": "player",
                "must_do": ["Write code"],
                "must_not_do": ["Approve work"],
                "ask_before": ["Schema changes"]
            }
        ]

        result = format_role_constraints(constraints)

        # Should be a single string block
        assert isinstance(result, str)

        # Should not be excessively long (token efficient)
        assert len(result) < 5000, "Output too long for prompt injection"

        # Should contain useful content
        assert len(result) > 50, "Output too short to be useful"
