"""
Comprehensive Test Suite for ImplementationModeEpisode Schema

Tests the implementation mode episode schema for Graphiti including:
- ImplementationModeEpisode dataclass creation and validation
- Default field values and entity_type
- Mode-specific fields (mode, invocation_method, result_location_pattern, state_recovery_strategy)
- List fields (when_to_use, pitfalls) with proper default_factory
- to_episode_content() method for natural language conversion
- get_entity_id() method for stable entity identification
- IMPLEMENTATION_MODE_DEFAULTS dictionary with all 3 modes
- Default mode validation (direct, task-work, manual)

Coverage Target: >=85%
Test Count: 40+ tests

TDD RED Phase: All tests should fail until implementation is complete.

Acceptance Criteria (TASK-GR-001-F):
- AC-001: ImplementationModeEpisode dataclass with required fields
- AC-002: Default modes (direct, task-work, manual) seeded with guidance
- AC-003: When-to-use and pitfalls documented for each mode
- AC-004: Stable entity ID generation
- AC-005: Natural language conversion for Graphiti
"""

import pytest

# These imports will fail initially - that's expected for TDD RED phase
from guardkit.integrations.graphiti.episodes.implementation_mode import (
    ImplementationModeEpisode,
    IMPLEMENTATION_MODE_DEFAULTS,
)


# ============================================================================
# 1. ImplementationModeEpisode Creation Tests (8 tests)
# ============================================================================

class TestImplementationModeEpisodeCreation:
    """Test ImplementationModeEpisode dataclass creation."""

    def test_create_with_all_fields(self):
        """Test creating ImplementationModeEpisode with all fields populated."""
        episode = ImplementationModeEpisode(
            mode="direct",
            invocation_method="inline",
            result_location_pattern="In current context",
            state_recovery_strategy="None needed - atomic execution",
            when_to_use=["Simple tasks", "Quick fixes"],
            pitfalls=["No testing", "No review"]
        )

        assert episode.entity_type == "implementation_mode"
        assert episode.mode == "direct"
        assert episode.invocation_method == "inline"
        assert episode.result_location_pattern == "In current context"
        assert episode.state_recovery_strategy == "None needed - atomic execution"
        assert episode.when_to_use == ["Simple tasks", "Quick fixes"]
        assert episode.pitfalls == ["No testing", "No review"]

    def test_default_entity_type(self):
        """Test that entity_type defaults to 'implementation_mode'."""
        episode = ImplementationModeEpisode()

        assert episode.entity_type == "implementation_mode"

    def test_default_mode_is_empty_string(self):
        """Test that mode defaults to empty string."""
        episode = ImplementationModeEpisode()

        assert episode.mode == ""

    def test_default_invocation_method_is_empty_string(self):
        """Test that invocation_method defaults to empty string."""
        episode = ImplementationModeEpisode()

        assert episode.invocation_method == ""

    def test_default_result_location_pattern_is_empty_string(self):
        """Test that result_location_pattern defaults to empty string."""
        episode = ImplementationModeEpisode()

        assert episode.result_location_pattern == ""

    def test_default_state_recovery_strategy_is_empty_string(self):
        """Test that state_recovery_strategy defaults to empty string."""
        episode = ImplementationModeEpisode()

        assert episode.state_recovery_strategy == ""

    def test_default_when_to_use_is_empty_list(self):
        """Test that when_to_use defaults to empty list."""
        episode = ImplementationModeEpisode()

        assert episode.when_to_use == []

    def test_default_pitfalls_is_empty_list(self):
        """Test that pitfalls defaults to empty list."""
        episode = ImplementationModeEpisode()

        assert episode.pitfalls == []


# ============================================================================
# 2. List Field Isolation Tests (3 tests)
# ============================================================================

class TestImplementationModeListFieldIsolation:
    """Test that list fields are not shared between instances."""

    def test_when_to_use_not_shared_between_instances(self):
        """Test that when_to_use list is not shared between instances."""
        episode1 = ImplementationModeEpisode(
            mode="direct",
            when_to_use=["Simple tasks"]
        )

        episode2 = ImplementationModeEpisode(
            mode="task-work",
            when_to_use=["Complex tasks"]
        )

        assert episode1.when_to_use != episode2.when_to_use
        assert "Simple tasks" in episode1.when_to_use
        assert "Complex tasks" in episode2.when_to_use
        assert "Complex tasks" not in episode1.when_to_use

    def test_pitfalls_not_shared_between_instances(self):
        """Test that pitfalls list is not shared between instances."""
        episode1 = ImplementationModeEpisode(
            mode="direct",
            pitfalls=["No testing"]
        )

        episode2 = ImplementationModeEpisode(
            mode="task-work",
            pitfalls=["State coordination"]
        )

        assert episode1.pitfalls != episode2.pitfalls
        assert "No testing" in episode1.pitfalls
        assert "State coordination" in episode2.pitfalls
        assert "State coordination" not in episode1.pitfalls

    def test_modifying_list_does_not_affect_other_instances(self):
        """Test that modifying one instance's list doesn't affect others."""
        episode1 = ImplementationModeEpisode(mode="direct")
        episode2 = ImplementationModeEpisode(mode="task-work")

        episode1.when_to_use.append("New item")

        assert "New item" in episode1.when_to_use
        assert "New item" not in episode2.when_to_use


# ============================================================================
# 3. Entity ID Generation Tests (5 tests)
# ============================================================================

class TestImplementationModeEntityId:
    """Test get_entity_id() method for stable entity identification."""

    def test_get_entity_id_format(self):
        """Test that get_entity_id() returns correct format."""
        episode = ImplementationModeEpisode(mode="direct")

        entity_id = episode.get_entity_id()

        assert entity_id == "implementation_mode_direct"

    def test_get_entity_id_for_task_work_mode(self):
        """Test entity ID generation for task-work mode."""
        episode = ImplementationModeEpisode(mode="task-work")

        entity_id = episode.get_entity_id()

        assert entity_id == "implementation_mode_task-work"

    def test_get_entity_id_for_manual_mode(self):
        """Test entity ID generation for manual mode."""
        episode = ImplementationModeEpisode(mode="manual")

        entity_id = episode.get_entity_id()

        assert entity_id == "implementation_mode_manual"

    def test_get_entity_id_is_stable(self):
        """Test that get_entity_id() returns same value for same mode."""
        episode1 = ImplementationModeEpisode(mode="direct")
        episode2 = ImplementationModeEpisode(mode="direct")

        assert episode1.get_entity_id() == episode2.get_entity_id()

    def test_get_entity_id_different_for_different_modes(self):
        """Test that different modes generate different entity IDs."""
        direct = ImplementationModeEpisode(mode="direct")
        task_work = ImplementationModeEpisode(mode="task-work")
        manual = ImplementationModeEpisode(mode="manual")

        assert direct.get_entity_id() != task_work.get_entity_id()
        assert direct.get_entity_id() != manual.get_entity_id()
        assert task_work.get_entity_id() != manual.get_entity_id()


# ============================================================================
# 4. Episode Content Conversion Tests (6 tests)
# ============================================================================

class TestImplementationModeEpisodeContent:
    """Test to_episode_content() method for natural language conversion."""

    def test_to_episode_content_returns_string(self):
        """Test that to_episode_content() returns a string."""
        episode = ImplementationModeEpisode(
            mode="direct",
            invocation_method="inline",
            when_to_use=["Simple tasks"]
        )

        content = episode.to_episode_content()

        assert isinstance(content, str)
        assert len(content) > 0

    def test_to_episode_content_includes_mode(self):
        """Test that episode content includes the mode name."""
        episode = ImplementationModeEpisode(mode="task-work")

        content = episode.to_episode_content()

        assert "task-work" in content.lower()

    def test_to_episode_content_includes_invocation_method(self):
        """Test that episode content includes invocation method."""
        episode = ImplementationModeEpisode(
            mode="direct",
            invocation_method="subprocess"
        )

        content = episode.to_episode_content()

        assert "subprocess" in content.lower()

    def test_to_episode_content_includes_when_to_use(self):
        """Test that episode content includes when-to-use guidance."""
        episode = ImplementationModeEpisode(
            mode="direct",
            when_to_use=["Simple tasks", "Quick fixes"]
        )

        content = episode.to_episode_content()

        assert "simple tasks" in content.lower() or "Simple tasks" in content
        assert "quick fixes" in content.lower() or "Quick fixes" in content

    def test_to_episode_content_includes_pitfalls(self):
        """Test that episode content includes pitfalls."""
        episode = ImplementationModeEpisode(
            mode="direct",
            pitfalls=["No testing", "No review"]
        )

        content = episode.to_episode_content()

        assert "no testing" in content.lower() or "No testing" in content
        assert "no review" in content.lower() or "No review" in content

    def test_to_episode_content_readable_format(self):
        """Test that episode content is in human-readable format."""
        episode = ImplementationModeEpisode(
            mode="direct",
            invocation_method="inline",
            result_location_pattern="In current context",
            state_recovery_strategy="None needed",
            when_to_use=["Simple tasks"],
            pitfalls=["No testing"]
        )

        content = episode.to_episode_content()

        # Should contain descriptive phrases, not just field names
        assert "mode" in content.lower() or "direct" in content.lower()
        assert len(content.split()) > 10  # Should be a sentence, not just values


# ============================================================================
# 5. IMPLEMENTATION_MODE_DEFAULTS Dictionary Tests (9 tests)
# ============================================================================

class TestImplementationModeDefaults:
    """Test IMPLEMENTATION_MODE_DEFAULTS dictionary structure and content."""

    def test_defaults_dictionary_exists(self):
        """Test that IMPLEMENTATION_MODE_DEFAULTS dictionary exists."""
        assert IMPLEMENTATION_MODE_DEFAULTS is not None
        assert isinstance(IMPLEMENTATION_MODE_DEFAULTS, dict)

    def test_defaults_has_three_modes(self):
        """Test that defaults dictionary contains exactly 3 modes."""
        assert len(IMPLEMENTATION_MODE_DEFAULTS) == 3

    def test_defaults_contains_direct_mode(self):
        """Test that defaults dictionary contains 'direct' mode."""
        assert "direct" in IMPLEMENTATION_MODE_DEFAULTS

    def test_defaults_contains_task_work_mode(self):
        """Test that defaults dictionary contains 'task-work' mode."""
        assert "task-work" in IMPLEMENTATION_MODE_DEFAULTS

    def test_defaults_contains_manual_mode(self):
        """Test that defaults dictionary contains 'manual' mode."""
        assert "manual" in IMPLEMENTATION_MODE_DEFAULTS

    def test_all_defaults_are_implementation_mode_episodes(self):
        """Test that all default values are ImplementationModeEpisode instances."""
        for mode_name, episode in IMPLEMENTATION_MODE_DEFAULTS.items():
            assert isinstance(episode, ImplementationModeEpisode)

    def test_all_defaults_have_matching_mode_names(self):
        """Test that each default episode's mode matches its dictionary key."""
        for mode_name, episode in IMPLEMENTATION_MODE_DEFAULTS.items():
            assert episode.mode == mode_name

    def test_all_defaults_have_entity_type(self):
        """Test that all defaults have entity_type set correctly."""
        for episode in IMPLEMENTATION_MODE_DEFAULTS.values():
            assert episode.entity_type == "implementation_mode"

    def test_all_defaults_have_when_to_use_guidance(self):
        """Test that all defaults have when_to_use guidance populated."""
        for mode_name, episode in IMPLEMENTATION_MODE_DEFAULTS.items():
            assert len(episode.when_to_use) > 0, f"{mode_name} missing when_to_use"


# ============================================================================
# 6. Direct Mode Default Tests (5 tests)
# ============================================================================

class TestDirectModeDefault:
    """Test 'direct' mode default configuration."""

    def test_direct_mode_invocation_method(self):
        """Test that direct mode uses inline invocation."""
        direct = IMPLEMENTATION_MODE_DEFAULTS["direct"]

        assert direct.invocation_method == "inline"

    def test_direct_mode_result_location(self):
        """Test that direct mode result location is current context."""
        direct = IMPLEMENTATION_MODE_DEFAULTS["direct"]

        assert "current context" in direct.result_location_pattern.lower()

    def test_direct_mode_state_recovery(self):
        """Test that direct mode requires no state recovery."""
        direct = IMPLEMENTATION_MODE_DEFAULTS["direct"]

        assert "none needed" in direct.state_recovery_strategy.lower() or \
               "atomic" in direct.state_recovery_strategy.lower()

    def test_direct_mode_when_to_use(self):
        """Test that direct mode when_to_use includes simple tasks."""
        direct = IMPLEMENTATION_MODE_DEFAULTS["direct"]

        when_to_use_text = " ".join(direct.when_to_use).lower()
        assert "simple" in when_to_use_text or "low" in when_to_use_text

    def test_direct_mode_pitfalls(self):
        """Test that direct mode pitfalls include testing gaps."""
        direct = IMPLEMENTATION_MODE_DEFAULTS["direct"]

        pitfalls_text = " ".join(direct.pitfalls).lower()
        assert "test" in pitfalls_text or "quality" in pitfalls_text


# ============================================================================
# 7. Task-Work Mode Default Tests (5 tests)
# ============================================================================

class TestTaskWorkModeDefault:
    """Test 'task-work' mode default configuration."""

    def test_task_work_mode_invocation_method(self):
        """Test that task-work mode uses subprocess invocation."""
        task_work = IMPLEMENTATION_MODE_DEFAULTS["task-work"]

        assert task_work.invocation_method == "subprocess"

    def test_task_work_mode_result_location(self):
        """Test that task-work mode uses task-plans directory."""
        task_work = IMPLEMENTATION_MODE_DEFAULTS["task-work"]

        assert ".claude/task-plans" in task_work.result_location_pattern or \
               "task-plans" in task_work.result_location_pattern

    def test_task_work_mode_state_recovery(self):
        """Test that task-work mode uses task file state recovery."""
        task_work = IMPLEMENTATION_MODE_DEFAULTS["task-work"]

        assert "task" in task_work.state_recovery_strategy.lower() and \
               ("state" in task_work.state_recovery_strategy.lower() or \
                "resume" in task_work.state_recovery_strategy.lower())

    def test_task_work_mode_when_to_use(self):
        """Test that task-work mode when_to_use includes quality gates."""
        task_work = IMPLEMENTATION_MODE_DEFAULTS["task-work"]

        when_to_use_text = " ".join(task_work.when_to_use).lower()
        assert "quality" in when_to_use_text or "complex" in when_to_use_text or \
               "medium" in when_to_use_text

    def test_task_work_mode_pitfalls(self):
        """Test that task-work mode pitfalls include state coordination."""
        task_work = IMPLEMENTATION_MODE_DEFAULTS["task-work"]

        pitfalls_text = " ".join(task_work.pitfalls).lower()
        assert "task file" in pitfalls_text or "state" in pitfalls_text or \
               "subprocess" in pitfalls_text


# ============================================================================
# 8. Manual Mode Default Tests (5 tests)
# ============================================================================

class TestManualModeDefault:
    """Test 'manual' mode default configuration."""

    def test_manual_mode_invocation_method(self):
        """Test that manual mode uses human invocation."""
        manual = IMPLEMENTATION_MODE_DEFAULTS["manual"]

        assert manual.invocation_method == "human"

    def test_manual_mode_result_location(self):
        """Test that manual mode result location varies."""
        manual = IMPLEMENTATION_MODE_DEFAULTS["manual"]

        assert "varies" in manual.result_location_pattern.lower() or \
               "manual" in manual.result_location_pattern.lower()

    def test_manual_mode_state_recovery(self):
        """Test that manual mode uses human-driven recovery."""
        manual = IMPLEMENTATION_MODE_DEFAULTS["manual"]

        assert "human" in manual.state_recovery_strategy.lower()

    def test_manual_mode_when_to_use(self):
        """Test that manual mode when_to_use includes research/decisions."""
        manual = IMPLEMENTATION_MODE_DEFAULTS["manual"]

        when_to_use_text = " ".join(manual.when_to_use).lower()
        assert "research" in when_to_use_text or "decision" in when_to_use_text or \
               "human" in when_to_use_text

    def test_manual_mode_pitfalls(self):
        """Test that manual mode pitfalls include lack of automation."""
        manual = IMPLEMENTATION_MODE_DEFAULTS["manual"]

        pitfalls_text = " ".join(manual.pitfalls).lower()
        assert "automation" in pitfalls_text or "manual" in pitfalls_text


# ============================================================================
# 9. Entity ID Uniqueness Tests (2 tests)
# ============================================================================

class TestDefaultEntityIdUniqueness:
    """Test that all default modes have unique entity IDs."""

    def test_all_defaults_have_unique_entity_ids(self):
        """Test that each default mode generates a unique entity ID."""
        entity_ids = [episode.get_entity_id() for episode in IMPLEMENTATION_MODE_DEFAULTS.values()]

        assert len(entity_ids) == len(set(entity_ids)), "Duplicate entity IDs found"

    def test_entity_ids_follow_naming_convention(self):
        """Test that all entity IDs follow implementation_mode_{mode} convention."""
        for mode_name, episode in IMPLEMENTATION_MODE_DEFAULTS.items():
            entity_id = episode.get_entity_id()
            assert entity_id == f"implementation_mode_{mode_name}"


# ============================================================================
# 10. Edge Cases and Validation Tests (2 tests)
# ============================================================================

class TestImplementationModeEdgeCases:
    """Test edge cases and validation."""

    def test_empty_lists_allowed(self):
        """Test that empty when_to_use and pitfalls lists are allowed."""
        episode = ImplementationModeEpisode(
            mode="custom",
            when_to_use=[],
            pitfalls=[]
        )

        assert episode.when_to_use == []
        assert episode.pitfalls == []

    def test_episode_with_minimal_fields(self):
        """Test creating episode with only mode field."""
        episode = ImplementationModeEpisode(mode="test")

        assert episode.mode == "test"
        assert episode.entity_type == "implementation_mode"
        assert episode.invocation_method == ""
        assert episode.when_to_use == []
        assert episode.pitfalls == []
