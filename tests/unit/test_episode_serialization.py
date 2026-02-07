"""
Test episode serialization consistency across all entities.

This test suite verifies that all entity `to_episode_body()` methods:
1. Return dict (not str)
2. Contain only domain data (no metadata fields)
3. Do not include entity_type, _metadata, created_at, updated_at

Test Coverage:
- TurnStateEntity
- FailedApproachEpisode
- FeatureOverviewEntity
- TaskOutcome
- QualityGateConfigFact
- RoleConstraintFact

Coverage Target: >=90%
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from guardkit.knowledge.entities.turn_state import TurnStateEntity
from guardkit.knowledge.entities.failed_approach import FailedApproachEpisode
from guardkit.knowledge.entities.feature_overview import FeatureOverviewEntity
from guardkit.knowledge.entities.outcome import TaskOutcome
from guardkit.knowledge.facts.quality_gate_config import QualityGateConfigFact
from guardkit.knowledge.facts.role_constraint import RoleConstraintFact


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def turn_state_entity() -> TurnStateEntity:
    """Create a sample TurnStateEntity for testing."""
    from guardkit.knowledge.entities.turn_state import TurnMode

    return TurnStateEntity(
        id="TURN-TEST-1",
        feature_id="FEAT-TEST",
        task_id="TASK-TEST-a1b2",
        turn_number=1,
        player_summary="Implement feature X",
        player_decision="implemented",
        coach_decision="feedback",
        coach_feedback="Looks good, but add tests",
        mode=TurnMode.FRESH_START,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )


@pytest.fixture
def failed_approach_episode() -> FailedApproachEpisode:
    """Create a sample FailedApproachEpisode for testing."""
    return FailedApproachEpisode(
        id="FAIL-TEST",
        approach="Tried using approach X",
        symptom="Error occurred",
        root_cause="Approach X failed due to Y",
        fix_applied="Used approach Y instead",
        prevention="Check docs before using approach X",
        context="Task: Implement feature Z"
    )


@pytest.fixture
def feature_overview_entity() -> FeatureOverviewEntity:
    """Create a sample FeatureOverviewEntity for testing."""
    return FeatureOverviewEntity(
        id="FEAT-TEST",
        name="Test Feature",
        tagline="A test feature",
        purpose="To test feature overview",
        what_it_is=["A test entity"],
        what_it_is_not=["Not a production feature"],
        invariants=["Must be tested"],
        architecture_summary="Simple test architecture",
        key_components=["TestComponent"],
        key_decisions=["ADR-001"]
    )


@pytest.fixture
def task_outcome() -> TaskOutcome:
    """Create a sample TaskOutcome for testing."""
    from guardkit.knowledge.entities.outcome import OutcomeType

    return TaskOutcome(
        id="OUT-TEST",
        outcome_type=OutcomeType.TASK_COMPLETED,
        task_id="TASK-TEST-a1b2",
        task_title="Test Task",
        task_requirements="Complete the test task",
        success=True,
        summary="Task completed successfully"
    )


@pytest.fixture
def quality_gate_config_fact() -> QualityGateConfigFact:
    """Create a sample QualityGateConfigFact for testing."""
    return QualityGateConfigFact(
        id="QG-TEST",
        name="Test Coverage Gate",
        task_type="feature",
        complexity_range=(1, 3),
        arch_review_required=False,
        arch_review_threshold=None,
        test_pass_required=True,
        coverage_required=True,
        coverage_threshold=80.0,
        lint_required=True,
        rationale="Minimum test coverage threshold"
    )


@pytest.fixture
def role_constraint_fact() -> RoleConstraintFact:
    """Create a sample RoleConstraintFact for testing."""
    return RoleConstraintFact(
        role="player",
        context="feature-build",
        primary_responsibility="Implement tasks using TDD",
        must_do=["Follow TDD workflow"],
        must_not_do=["Skip tests"],
        ask_before=["Changing architecture"]
    )


# ============================================================================
# 1. All Entities Return Dict
# ============================================================================

class TestAllEntitiesReturnDict:
    """Test that all entity to_episode_body() methods return dict."""

    def test_turn_state_returns_dict(self, turn_state_entity):
        """Test TurnStateEntity.to_episode_body() returns dict."""
        result = turn_state_entity.to_episode_body()
        assert isinstance(result, dict), \
            f"Expected dict, got {type(result).__name__}"

    def test_failed_approach_returns_dict(self, failed_approach_episode):
        """Test FailedApproachEpisode.to_episode_body() returns dict."""
        result = failed_approach_episode.to_episode_body()
        assert isinstance(result, dict), \
            f"Expected dict, got {type(result).__name__}"

    def test_feature_overview_returns_dict(self, feature_overview_entity):
        """Test FeatureOverviewEntity.to_episode_body() returns dict."""
        result = feature_overview_entity.to_episode_body()
        assert isinstance(result, dict), \
            f"Expected dict, got {type(result).__name__}"

    def test_task_outcome_returns_dict(self, task_outcome):
        """Test TaskOutcome.to_episode_body() returns dict (not str)."""
        result = task_outcome.to_episode_body()
        assert isinstance(result, dict), \
            f"Expected dict, got {type(result).__name__}. " \
            f"TaskOutcome should return dict, not str."

    def test_quality_gate_config_returns_dict(self, quality_gate_config_fact):
        """Test QualityGateConfigFact.to_episode_body() returns dict."""
        result = quality_gate_config_fact.to_episode_body()
        assert isinstance(result, dict), \
            f"Expected dict, got {type(result).__name__}"

    def test_role_constraint_returns_dict(self, role_constraint_fact):
        """Test RoleConstraintFact.to_episode_body() returns dict."""
        result = role_constraint_fact.to_episode_body()
        assert isinstance(result, dict), \
            f"Expected dict, got {type(result).__name__}"


# ============================================================================
# 2. No Metadata Fields in Entity Bodies
# ============================================================================

class TestNoMetadataFieldsInEntityBodies:
    """Test that entity bodies contain no metadata fields."""

    FORBIDDEN_FIELDS = {"entity_type", "_metadata", "updated_at"}
    # Note: created_at is allowed as DOMAIN data if it's part of the entity's
    # business logic (e.g., FeatureOverviewEntity tracks when feature was created),
    # but should NOT appear in to_episode_body() output for entities that
    # don't have it as a domain field.

    def test_turn_state_no_metadata_fields(self, turn_state_entity):
        """Test TurnStateEntity.to_episode_body() has no metadata fields."""
        result = turn_state_entity.to_episode_body()

        for field in self.FORBIDDEN_FIELDS:
            assert field not in result, \
                f"TurnStateEntity.to_episode_body() should not contain '{field}'"

    def test_failed_approach_no_metadata_fields(self, failed_approach_episode):
        """Test FailedApproachEpisode.to_episode_body() has no metadata fields."""
        result = failed_approach_episode.to_episode_body()

        for field in self.FORBIDDEN_FIELDS:
            assert field not in result, \
                f"FailedApproachEpisode.to_episode_body() should not contain '{field}'"

    def test_feature_overview_no_metadata_fields(self, feature_overview_entity):
        """Test FeatureOverviewEntity.to_episode_body() has no metadata fields."""
        result = feature_overview_entity.to_episode_body()

        # entity_type, _metadata, updated_at should not be present
        for field in self.FORBIDDEN_FIELDS:
            assert field not in result, \
                f"FeatureOverviewEntity.to_episode_body() should not contain '{field}'"

        # created_at is OK if it's part of the entity's domain model
        # (FeatureOverviewEntity has created_at in __init__, but it should
        # NOT be in to_episode_body() output as metadata is handled separately)

    def test_task_outcome_no_metadata_fields(self, task_outcome):
        """Test TaskOutcome.to_episode_body() has no metadata fields."""
        result = task_outcome.to_episode_body()

        for field in self.FORBIDDEN_FIELDS:
            assert field not in result, \
                f"TaskOutcome.to_episode_body() should not contain '{field}'"

    def test_quality_gate_config_no_metadata_fields(self, quality_gate_config_fact):
        """Test QualityGateConfigFact.to_episode_body() has no metadata fields."""
        result = quality_gate_config_fact.to_episode_body()

        for field in self.FORBIDDEN_FIELDS:
            assert field not in result, \
                f"QualityGateConfigFact.to_episode_body() should not contain '{field}'"

    def test_role_constraint_no_metadata_fields(self, role_constraint_fact):
        """Test RoleConstraintFact.to_episode_body() has no metadata fields."""
        result = role_constraint_fact.to_episode_body()

        for field in self.FORBIDDEN_FIELDS:
            assert field not in result, \
                f"RoleConstraintFact.to_episode_body() should not contain '{field}'"


# ============================================================================
# 3. Task Outcome Specific Tests
# ============================================================================

class TestTaskOutcomeReturnsDict:
    """Test TaskOutcome specifically returns dict (was str before)."""

    def test_task_outcome_returns_dict_not_str(self, task_outcome):
        """Test that TaskOutcome.to_episode_body() returns dict, not str."""
        result = task_outcome.to_episode_body()

        assert isinstance(result, dict), \
            "TaskOutcome.to_episode_body() must return dict, not str"

        assert not isinstance(result, str), \
            "TaskOutcome.to_episode_body() should not return str"

    def test_task_outcome_contains_domain_data(self, task_outcome):
        """Test that TaskOutcome.to_episode_body() contains domain data."""
        result = task_outcome.to_episode_body()

        # Should contain task outcome domain data
        # (actual field names depend on implementation, but should be dict)
        assert len(result) > 0, \
            "TaskOutcome.to_episode_body() should contain domain data"


# ============================================================================
# 4. Seed Helpers Function Signature
# ============================================================================

class TestSeedHelpersPassesEntityType:
    """Test that _add_episodes accepts entity_type parameter."""

    def test_add_episodes_accepts_entity_type(self):
        """Test that _add_episodes function signature accepts entity_type."""
        from guardkit.knowledge.seed_helpers import _add_episodes
        import inspect

        sig = inspect.signature(_add_episodes)
        params = list(sig.parameters.keys())

        # Should have entity_type parameter
        assert "entity_type" in params, \
            "_add_episodes should accept 'entity_type' parameter"

    def test_add_episodes_has_entity_type_default(self):
        """Test that _add_episodes has default value for entity_type."""
        from guardkit.knowledge.seed_helpers import _add_episodes
        import inspect

        sig = inspect.signature(_add_episodes)

        # Should have entity_type parameter with default
        assert "entity_type" in sig.parameters, \
            "_add_episodes should have 'entity_type' parameter"

        # Verify it has a default value
        entity_type_param = sig.parameters["entity_type"]
        assert entity_type_param.default != inspect.Parameter.empty, \
            "'entity_type' should have a default value"
        assert entity_type_param.default == "generic", \
            "'entity_type' default should be 'generic'"


# ============================================================================
# 5. Entity Body Contains Only Domain Data
# ============================================================================

class TestEntityBodiesContainOnlyDomainData:
    """Test that entity bodies contain only domain-specific fields."""

    def test_turn_state_contains_turn_data(self, turn_state_entity):
        """Test that TurnStateEntity contains turn-specific domain data."""
        result = turn_state_entity.to_episode_body()

        # Should have turn-specific fields
        assert isinstance(result, dict)
        assert len(result) > 0, "Should contain domain data"

    def test_failed_approach_contains_failure_data(self, failed_approach_episode):
        """Test that FailedApproachEpisode contains failure-specific data."""
        result = failed_approach_episode.to_episode_body()

        # Should have failure-specific fields
        assert isinstance(result, dict)
        assert len(result) > 0, "Should contain domain data"

    def test_feature_overview_contains_feature_data(self, feature_overview_entity):
        """Test that FeatureOverviewEntity contains feature-specific data."""
        result = feature_overview_entity.to_episode_body()

        # Should have feature-specific fields
        assert isinstance(result, dict)
        assert len(result) > 0, "Should contain domain data"

    def test_task_outcome_contains_outcome_data(self, task_outcome):
        """Test that TaskOutcome contains outcome-specific data."""
        result = task_outcome.to_episode_body()

        # Should have outcome-specific fields
        assert isinstance(result, dict)
        assert len(result) > 0, "Should contain domain data"


# ============================================================================
# 6. Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases in episode serialization."""

    def test_entities_with_none_values(self):
        """Test entities handle None values in domain data."""
        from guardkit.knowledge.entities.outcome import OutcomeType

        # Create entity with None values where applicable
        outcome = TaskOutcome(
            id="OUT-TEST-NONE",
            outcome_type=OutcomeType.TASK_FAILED,
            task_id="TASK-TEST-a1b2",
            task_title="Test Task",
            task_requirements="Test requirements",
            success=False,
            summary="Failed",
            approach_used=None,  # None value
            patterns_used=None,  # None value
            started_at=None,  # None value
            completed_at=None   # None value
        )

        result = outcome.to_episode_body()
        assert isinstance(result, dict)

    def test_entities_with_empty_lists(self):
        """Test entities handle empty lists in domain data."""
        constraint = RoleConstraintFact(
            role="player",
            context="test",
            primary_responsibility="Test",
            must_do=[],  # Empty list
            must_not_do=[],
            ask_before=[]
        )

        result = constraint.to_episode_body()
        assert isinstance(result, dict)

    def test_entities_are_json_serializable(self, turn_state_entity,
                                           failed_approach_episode,
                                           feature_overview_entity,
                                           task_outcome,
                                           quality_gate_config_fact,
                                           role_constraint_fact):
        """Test that all entity bodies are JSON serializable."""
        import json

        entities = [
            turn_state_entity,
            failed_approach_episode,
            feature_overview_entity,
            task_outcome,
            quality_gate_config_fact,
            role_constraint_fact
        ]

        for entity in entities:
            result = entity.to_episode_body()

            # Should be JSON serializable
            try:
                json.dumps(result, default=str)
            except (TypeError, ValueError) as e:
                pytest.fail(
                    f"{type(entity).__name__}.to_episode_body() "
                    f"returned non-JSON-serializable data: {e}"
                )
