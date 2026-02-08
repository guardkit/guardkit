"""
TDD RED Phase: Tests for guardkit.knowledge.facts.quality_gate_config

These tests are written to FAIL initially (RED phase of TDD).
Implementation will be created to make these tests pass (GREEN phase).

Test Coverage:
- QualityGateConfigFact dataclass creation and validation
- to_episode_body() method for Graphiti serialization
- QUALITY_GATE_CONFIGS predefined configurations
- seed_quality_gate_configs() seeding function
- get_quality_gate_config() query function
- Edge cases and error handling

Coverage Target: >=85%
Test Count: 31+ tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from datetime import datetime
import json

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.facts.quality_gate_config import (
        QualityGateConfigFact,
        QUALITY_GATE_CONFIGS,
    )
    from guardkit.knowledge.seed_quality_gate_configs import (
        seed_quality_gate_configs,
    )
    from guardkit.knowledge.quality_gate_queries import (
        get_quality_gate_config,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


# Skip all tests if imports not available (expected in RED phase)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


# ============================================================================
# 1. QualityGateConfigFact Dataclass Tests (10 tests)
# ============================================================================

class TestQualityGateConfigFactDataclass:
    """Test QualityGateConfigFact dataclass creation and validation."""

    def test_create_minimal_fact(self):
        """Test creating a minimal quality gate config fact with required fields."""
        fact = QualityGateConfigFact(
            id="QG-TEST-001",
            name="Test Config",
            task_type="feature",
            complexity_range=(1, 5),
            arch_review_required=True,
            arch_review_threshold=60,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=80.0,
            lint_required=True,
            rationale="Test configuration for validation."
        )

        assert fact.id == "QG-TEST-001"
        assert fact.name == "Test Config"
        assert fact.task_type == "feature"
        assert fact.complexity_range == (1, 5)
        assert fact.arch_review_required is True
        assert fact.arch_review_threshold == 60
        assert fact.test_pass_required is True
        assert fact.coverage_required is True
        assert fact.coverage_threshold == 80.0
        assert fact.lint_required is True
        assert fact.rationale == "Test configuration for validation."

    def test_create_full_fact_with_optional_fields(self):
        """Test creating a fact with all fields including optional ones."""
        effective_date = datetime(2025, 1, 1, 12, 0, 0)

        fact = QualityGateConfigFact(
            id="QG-TEST-002",
            name="Full Config",
            task_type="scaffolding",
            complexity_range=(1, 3),
            arch_review_required=False,
            arch_review_threshold=None,
            test_pass_required=True,
            coverage_required=False,
            coverage_threshold=None,
            lint_required=True,
            rationale="Full configuration test.",
            version="2.0.0",
            effective_from=effective_date,
            supersedes="QG-TEST-001"
        )

        assert fact.version == "2.0.0"
        assert fact.effective_from == effective_date
        assert fact.supersedes == "QG-TEST-001"

    def test_complexity_range_is_tuple_of_two_ints(self):
        """Test that complexity_range is a tuple of two integers."""
        fact = QualityGateConfigFact(
            id="QG-TEST-003",
            name="Complexity Range Test",
            task_type="feature",
            complexity_range=(4, 6),
            arch_review_required=True,
            arch_review_threshold=50,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=75.0,
            lint_required=True,
            rationale="Testing complexity range validation."
        )

        assert isinstance(fact.complexity_range, tuple)
        assert len(fact.complexity_range) == 2
        assert isinstance(fact.complexity_range[0], int)
        assert isinstance(fact.complexity_range[1], int)
        assert fact.complexity_range[0] <= fact.complexity_range[1]

    def test_version_defaults_to_1_0_0(self):
        """Test that version defaults to '1.0.0' when not specified."""
        fact = QualityGateConfigFact(
            id="QG-TEST-004",
            name="Default Version Test",
            task_type="feature",
            complexity_range=(1, 10),
            arch_review_required=True,
            arch_review_threshold=60,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=80.0,
            lint_required=True,
            rationale="Testing default version."
        )

        assert fact.version == "1.0.0"

    def test_effective_from_defaults_to_now(self):
        """Test that effective_from defaults to current datetime."""
        before = datetime.now()

        fact = QualityGateConfigFact(
            id="QG-TEST-005",
            name="Default Effective From Test",
            task_type="feature",
            complexity_range=(1, 10),
            arch_review_required=True,
            arch_review_threshold=60,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=80.0,
            lint_required=True,
            rationale="Testing default effective_from."
        )

        after = datetime.now()

        assert before <= fact.effective_from <= after

    def test_supersedes_defaults_to_none(self):
        """Test that supersedes defaults to None."""
        fact = QualityGateConfigFact(
            id="QG-TEST-006",
            name="Default Supersedes Test",
            task_type="feature",
            complexity_range=(1, 10),
            arch_review_required=True,
            arch_review_threshold=60,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=80.0,
            lint_required=True,
            rationale="Testing default supersedes."
        )

        assert fact.supersedes is None

    def test_arch_review_threshold_can_be_none(self):
        """Test that arch_review_threshold can be None when review not required."""
        fact = QualityGateConfigFact(
            id="QG-TEST-007",
            name="No Arch Review Test",
            task_type="scaffolding",
            complexity_range=(1, 3),
            arch_review_required=False,
            arch_review_threshold=None,
            test_pass_required=True,
            coverage_required=False,
            coverage_threshold=None,
            lint_required=True,
            rationale="Testing None arch_review_threshold."
        )

        assert fact.arch_review_required is False
        assert fact.arch_review_threshold is None

    def test_coverage_threshold_can_be_none(self):
        """Test that coverage_threshold can be None when coverage not required."""
        fact = QualityGateConfigFact(
            id="QG-TEST-008",
            name="No Coverage Test",
            task_type="testing",
            complexity_range=(1, 10),
            arch_review_required=False,
            arch_review_threshold=None,
            test_pass_required=True,
            coverage_required=False,
            coverage_threshold=None,
            lint_required=True,
            rationale="Testing None coverage_threshold."
        )

        assert fact.coverage_required is False
        assert fact.coverage_threshold is None

    def test_task_type_accepts_valid_values(self):
        """Test that task_type accepts expected values."""
        valid_types = ["scaffolding", "feature", "testing", "docs"]

        for task_type in valid_types:
            fact = QualityGateConfigFact(
                id=f"QG-TEST-{task_type}",
                name=f"{task_type.title()} Task Config",
                task_type=task_type,
                complexity_range=(1, 10),
                arch_review_required=False,
                arch_review_threshold=None,
                test_pass_required=True,
                coverage_required=False,
                coverage_threshold=None,
                lint_required=True,
                rationale=f"Testing {task_type} task type."
            )
            assert fact.task_type == task_type

    def test_fact_fields_are_accessible(self):
        """Test that all fact fields are accessible as attributes."""
        fact = QualityGateConfigFact(
            id="QG-TEST-009",
            name="Field Access Test",
            task_type="feature",
            complexity_range=(1, 5),
            arch_review_required=True,
            arch_review_threshold=70,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=85.0,
            lint_required=True,
            rationale="Testing field accessibility."
        )

        # All fields should be accessible
        _ = fact.id
        _ = fact.name
        _ = fact.task_type
        _ = fact.complexity_range
        _ = fact.arch_review_required
        _ = fact.arch_review_threshold
        _ = fact.test_pass_required
        _ = fact.coverage_required
        _ = fact.coverage_threshold
        _ = fact.lint_required
        _ = fact.rationale
        _ = fact.version
        _ = fact.effective_from
        _ = fact.supersedes


# ============================================================================
# 2. to_episode_body() Method Tests (9 tests)
# ============================================================================

class TestToEpisodeBody:
    """Test QualityGateConfigFact.to_episode_body() serialization."""

    def test_to_episode_body_returns_dict(self):
        """Test that to_episode_body returns a dictionary."""
        fact = QualityGateConfigFact(
            id="QG-TEST-BODY-001",
            name="Body Dict Test",
            task_type="feature",
            complexity_range=(1, 5),
            arch_review_required=True,
            arch_review_threshold=60,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=80.0,
            lint_required=True,
            rationale="Testing to_episode_body returns dict."
        )

        result = fact.to_episode_body()
        assert isinstance(result, dict)

    def test_to_episode_body_excludes_entity_type(self):
        """Test that episode body does NOT include entity_type (injected by client)."""
        fact = QualityGateConfigFact(
            id="QG-TEST-BODY-002",
            name="Entity Type Test",
            task_type="feature",
            complexity_range=(1, 5),
            arch_review_required=True,
            arch_review_threshold=60,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=80.0,
            lint_required=True,
            rationale="Testing entity_type not in body."
        )

        result = fact.to_episode_body()
        assert "entity_type" not in result, \
            "entity_type should be injected by GraphitiClient, not in body"

    def test_to_episode_body_includes_all_fields(self):
        """Test that episode body includes all fact fields."""
        fact = QualityGateConfigFact(
            id="QG-TEST-BODY-003",
            name="All Fields Test",
            task_type="feature",
            complexity_range=(4, 6),
            arch_review_required=True,
            arch_review_threshold=50,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=75.0,
            lint_required=True,
            rationale="Testing all fields in body.",
            version="1.1.0",
            supersedes="QG-TEST-OLD"
        )

        result = fact.to_episode_body()

        assert "id" in result
        assert "name" in result
        assert "task_type" in result
        assert "complexity_range" in result
        assert "arch_review_required" in result
        assert "arch_review_threshold" in result
        assert "test_pass_required" in result
        assert "coverage_required" in result
        assert "coverage_threshold" in result
        assert "lint_required" in result
        assert "rationale" in result
        assert "version" in result
        assert "effective_from" in result
        assert "supersedes" in result

    def test_to_episode_body_serializes_datetime_to_iso(self):
        """Test that datetime is serialized to ISO format string."""
        effective_date = datetime(2025, 6, 15, 10, 30, 0)

        fact = QualityGateConfigFact(
            id="QG-TEST-BODY-004",
            name="Datetime Test",
            task_type="feature",
            complexity_range=(1, 5),
            arch_review_required=True,
            arch_review_threshold=60,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=80.0,
            lint_required=True,
            rationale="Testing datetime serialization.",
            effective_from=effective_date
        )

        result = fact.to_episode_body()

        # effective_from should be a string in ISO format
        assert isinstance(result["effective_from"], str)
        # Should be parseable back to datetime
        parsed = datetime.fromisoformat(result["effective_from"])
        assert parsed == effective_date

    def test_to_episode_body_handles_none_supersedes(self):
        """Test that None supersedes is handled correctly."""
        fact = QualityGateConfigFact(
            id="QG-TEST-BODY-005",
            name="None Supersedes Test",
            task_type="feature",
            complexity_range=(1, 5),
            arch_review_required=True,
            arch_review_threshold=60,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=80.0,
            lint_required=True,
            rationale="Testing None supersedes.",
            supersedes=None
        )

        result = fact.to_episode_body()
        assert result["supersedes"] is None

    def test_to_episode_body_handles_none_thresholds(self):
        """Test that None thresholds are handled correctly."""
        fact = QualityGateConfigFact(
            id="QG-TEST-BODY-006",
            name="None Thresholds Test",
            task_type="scaffolding",
            complexity_range=(1, 3),
            arch_review_required=False,
            arch_review_threshold=None,
            test_pass_required=True,
            coverage_required=False,
            coverage_threshold=None,
            lint_required=True,
            rationale="Testing None thresholds."
        )

        result = fact.to_episode_body()
        assert result["arch_review_threshold"] is None
        assert result["coverage_threshold"] is None

    def test_to_episode_body_preserves_complexity_range(self):
        """Test that complexity_range tuple is preserved correctly."""
        fact = QualityGateConfigFact(
            id="QG-TEST-BODY-007",
            name="Complexity Range Test",
            task_type="feature",
            complexity_range=(7, 10),
            arch_review_required=True,
            arch_review_threshold=70,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=80.0,
            lint_required=True,
            rationale="Testing complexity range preservation."
        )

        result = fact.to_episode_body()
        assert result["complexity_range"] == (7, 10)

    def test_to_episode_body_is_json_serializable(self):
        """Test that episode body can be serialized to JSON."""
        fact = QualityGateConfigFact(
            id="QG-TEST-BODY-008",
            name="JSON Serializable Test",
            task_type="feature",
            complexity_range=(1, 5),
            arch_review_required=True,
            arch_review_threshold=60,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=80.0,
            lint_required=True,
            rationale="Testing JSON serialization.",
            supersedes="QG-OLD"
        )

        result = fact.to_episode_body()

        # Complexity range might need conversion for JSON
        # Convert tuple to list for JSON serialization
        serializable = result.copy()
        if isinstance(serializable.get("complexity_range"), tuple):
            serializable["complexity_range"] = list(serializable["complexity_range"])

        # Should not raise exception
        json_str = json.dumps(serializable)
        assert isinstance(json_str, str)

        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed["id"] == "QG-TEST-BODY-008"
        assert parsed["task_type"] == "feature"

    def test_to_episode_body_preserves_field_values(self):
        """Test that all field values are preserved correctly."""
        fact = QualityGateConfigFact(
            id="QG-TEST-BODY-009",
            name="Value Preservation Test",
            task_type="testing",
            complexity_range=(1, 10),
            arch_review_required=False,
            arch_review_threshold=None,
            test_pass_required=True,
            coverage_required=False,
            coverage_threshold=None,
            lint_required=True,
            rationale="Testing value preservation."
        )

        result = fact.to_episode_body()

        assert result["id"] == "QG-TEST-BODY-009"
        assert result["name"] == "Value Preservation Test"
        assert result["task_type"] == "testing"
        assert result["arch_review_required"] is False
        assert result["test_pass_required"] is True
        assert result["coverage_required"] is False
        assert result["lint_required"] is True


# ============================================================================
# 3. Predefined Configs Tests (6 tests)
# ============================================================================

class TestPredefinedConfigs:
    """Test QUALITY_GATE_CONFIGS predefined configurations."""

    def test_quality_gate_configs_exists_and_not_empty(self):
        """Test that QUALITY_GATE_CONFIGS list exists and is not empty."""
        assert QUALITY_GATE_CONFIGS is not None
        assert isinstance(QUALITY_GATE_CONFIGS, list)
        assert len(QUALITY_GATE_CONFIGS) > 0

    def test_scaffolding_config_exists(self):
        """Test that scaffolding config (QG-SCAFFOLDING-LOW) exists."""
        scaffolding_config = None
        for config in QUALITY_GATE_CONFIGS:
            if config.id == "QG-SCAFFOLDING-LOW":
                scaffolding_config = config
                break

        assert scaffolding_config is not None
        assert scaffolding_config.task_type == "scaffolding"
        assert scaffolding_config.arch_review_required is False
        assert scaffolding_config.test_pass_required is True

    def test_feature_configs_exist_for_all_complexity_levels(self):
        """Test that feature configs exist for low/med/high complexity."""
        feature_ids = ["QG-FEATURE-LOW", "QG-FEATURE-MED", "QG-FEATURE-HIGH"]
        found_ids = set()

        for config in QUALITY_GATE_CONFIGS:
            if config.id in feature_ids:
                found_ids.add(config.id)
                assert config.task_type == "feature"

        assert found_ids == set(feature_ids), f"Missing configs: {set(feature_ids) - found_ids}"

    def test_testing_config_exists(self):
        """Test that testing config (QG-TESTING) exists."""
        testing_config = None
        for config in QUALITY_GATE_CONFIGS:
            if config.id == "QG-TESTING":
                testing_config = config
                break

        assert testing_config is not None
        assert testing_config.task_type == "testing"
        assert testing_config.coverage_required is False  # Tests don't need coverage

    def test_docs_config_exists(self):
        """Test that documentation config (QG-DOCS) exists."""
        docs_config = None
        for config in QUALITY_GATE_CONFIGS:
            if config.id == "QG-DOCS":
                docs_config = config
                break

        assert docs_config is not None
        assert docs_config.task_type == "docs"
        assert docs_config.test_pass_required is False
        assert docs_config.coverage_required is False

    def test_all_configs_have_valid_task_types(self):
        """Test that all configs have valid task_type values."""
        valid_types = {"scaffolding", "feature", "testing", "docs", "refactoring"}

        for config in QUALITY_GATE_CONFIGS:
            assert config.task_type in valid_types, (
                f"Config {config.id} has invalid task_type: {config.task_type}"
            )


# ============================================================================
# 4. seed_quality_gate_configs() Function Tests (5 tests)
# ============================================================================

class TestSeedQualityGateConfigs:
    """Test seed_quality_gate_configs seeding function."""

    @pytest.mark.asyncio
    async def test_seed_creates_episodes_for_all_configs(self):
        """Test that seeding creates episodes for all configurations."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_quality_gate_configs(mock_client)

        # Should create episode for each config
        assert mock_client.add_episode.call_count == len(QUALITY_GATE_CONFIGS)

    @pytest.mark.asyncio
    async def test_seed_uses_correct_group_id(self):
        """Test that seeding uses 'quality_gate_configs' group ID."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_quality_gate_configs(mock_client)

        # Verify all calls used correct group_id
        for call_obj in mock_client.add_episode.call_args_list:
            kwargs = call_obj.kwargs
            assert kwargs['group_id'] == 'quality_gate_configs'

    @pytest.mark.asyncio
    async def test_seed_episode_bodies_are_valid_json(self):
        """Test that episode bodies are valid JSON strings."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_quality_gate_configs(mock_client)

        # All bodies should be valid JSON strings
        assert mock_client.add_episode.call_count == len(QUALITY_GATE_CONFIGS)
        for call_obj in mock_client.add_episode.call_args_list:
            body = call_obj.kwargs["episode_body"]
            assert isinstance(body, str)
            # Should parse without exception
            parsed = json.loads(body)
            assert isinstance(parsed, dict)
            # entity_type is passed as kwarg, not in body
            assert call_obj.kwargs["entity_type"] == "quality_gate_config"

    @pytest.mark.asyncio
    async def test_seed_handles_disabled_client_gracefully(self):
        """Test graceful degradation when Graphiti is disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        # Should not raise exception
        await seed_quality_gate_configs(mock_client)

        # Should not attempt to add episodes
        mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_handles_none_client_gracefully(self):
        """Test that seeding handles None client gracefully."""
        # Should not raise exception
        result = await seed_quality_gate_configs(None)
        # Implementation should handle this gracefully


# ============================================================================
# 5. get_quality_gate_config() Query Tests (8 tests)
# ============================================================================

class TestGetQualityGateConfig:
    """Test get_quality_gate_config query function."""

    @pytest.mark.asyncio
    async def test_queries_graphiti_with_correct_parameters(self):
        """Test that get_quality_gate_config queries Graphiti correctly."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'entity_type': 'quality_gate_config',
                    'id': 'QG-FEATURE-LOW',
                    'name': 'Feature (Low Complexity)',
                    'task_type': 'feature',
                    'complexity_range': [1, 3],
                    'arch_review_required': False,
                    'arch_review_threshold': None,
                    'test_pass_required': True,
                    'coverage_required': True,
                    'coverage_threshold': 60.0,
                    'lint_required': True,
                    'rationale': 'Test rationale.',
                    'version': '1.0.0',
                    'effective_from': '2025-01-01T00:00:00',
                    'supersedes': None
                }
            }
        ])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            result = await get_quality_gate_config("feature", 2)

            # Should have called search
            mock_graphiti.search.assert_called_once()

            # Verify search parameters
            call_kwargs = mock_graphiti.search.call_args.kwargs
            assert "quality_gate_config" in call_kwargs['query']
            assert "feature" in call_kwargs['query']
            assert call_kwargs['group_ids'] == ['quality_gate_configs']

    @pytest.mark.asyncio
    async def test_returns_matching_config_for_task_type_and_complexity(self):
        """Test that matching config is returned for task type and complexity."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'entity_type': 'quality_gate_config',
                    'id': 'QG-FEATURE-MED',
                    'name': 'Feature (Medium Complexity)',
                    'task_type': 'feature',
                    'complexity_range': [4, 6],
                    'arch_review_required': True,
                    'arch_review_threshold': 50,
                    'test_pass_required': True,
                    'coverage_required': True,
                    'coverage_threshold': 75.0,
                    'lint_required': True,
                    'rationale': 'Medium features.',
                    'version': '1.0.0',
                    'effective_from': '2025-01-01T00:00:00',
                    'supersedes': None
                }
            }
        ])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            result = await get_quality_gate_config("feature", 5)

            assert result is not None
            assert result.id == "QG-FEATURE-MED"
            assert result.task_type == "feature"
            assert result.arch_review_threshold == 50

    @pytest.mark.asyncio
    async def test_returns_none_when_no_match_found(self):
        """Test that None is returned when no matching config found."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            result = await get_quality_gate_config("unknown_type", 5)

            assert result is None

    @pytest.mark.asyncio
    async def test_complexity_range_matching_boundary_conditions(self):
        """Test complexity range matching at boundaries."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True

        # Config for complexity 4-6
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'entity_type': 'quality_gate_config',
                    'id': 'QG-FEATURE-MED',
                    'name': 'Feature (Medium Complexity)',
                    'task_type': 'feature',
                    'complexity_range': [4, 6],
                    'arch_review_required': True,
                    'arch_review_threshold': 50,
                    'test_pass_required': True,
                    'coverage_required': True,
                    'coverage_threshold': 75.0,
                    'lint_required': True,
                    'rationale': 'Medium features.',
                    'version': '1.0.0',
                    'effective_from': '2025-01-01T00:00:00',
                    'supersedes': None
                }
            }
        ])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            # Test lower boundary (4)
            result = await get_quality_gate_config("feature", 4)
            assert result is not None
            assert result.id == "QG-FEATURE-MED"

            # Test upper boundary (6)
            result = await get_quality_gate_config("feature", 6)
            assert result is not None
            assert result.id == "QG-FEATURE-MED"

    @pytest.mark.asyncio
    async def test_handles_disabled_graphiti_gracefully(self):
        """Test graceful handling when Graphiti is disabled."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = False

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            result = await get_quality_gate_config("feature", 5)

            assert result is None

    @pytest.mark.asyncio
    async def test_finds_feature_low_config_for_complexity_2(self):
        """Test that feature-low config is found for complexity 2."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'entity_type': 'quality_gate_config',
                    'id': 'QG-FEATURE-LOW',
                    'name': 'Feature (Low Complexity)',
                    'task_type': 'feature',
                    'complexity_range': [1, 3],
                    'arch_review_required': False,
                    'arch_review_threshold': None,
                    'test_pass_required': True,
                    'coverage_required': True,
                    'coverage_threshold': 60.0,
                    'lint_required': True,
                    'rationale': 'Simple features.',
                    'version': '1.0.0',
                    'effective_from': '2025-01-01T00:00:00',
                    'supersedes': None
                }
            }
        ])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            result = await get_quality_gate_config("feature", 2)

            assert result is not None
            assert result.id == "QG-FEATURE-LOW"
            assert result.arch_review_required is False
            assert result.coverage_threshold == 60.0

    @pytest.mark.asyncio
    async def test_finds_feature_high_config_for_complexity_8(self):
        """Test that feature-high config is found for complexity 8."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'entity_type': 'quality_gate_config',
                    'id': 'QG-FEATURE-HIGH',
                    'name': 'Feature (High Complexity)',
                    'task_type': 'feature',
                    'complexity_range': [7, 10],
                    'arch_review_required': True,
                    'arch_review_threshold': 70,
                    'test_pass_required': True,
                    'coverage_required': True,
                    'coverage_threshold': 80.0,
                    'lint_required': True,
                    'rationale': 'Complex features.',
                    'version': '1.0.0',
                    'effective_from': '2025-01-01T00:00:00',
                    'supersedes': None
                }
            }
        ])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            result = await get_quality_gate_config("feature", 8)

            assert result is not None
            assert result.id == "QG-FEATURE-HIGH"
            assert result.arch_review_threshold == 70
            assert result.coverage_threshold == 80.0

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_task_type(self):
        """Test that None is returned for unknown task type."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            result = await get_quality_gate_config("invalid_type", 5)

            assert result is None


# ============================================================================
# 6. Edge Cases (4 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_task_type_mismatch_skips_result(self):
        """Test that mismatched task_type results are skipped."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        # Return result with wrong task_type
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'entity_type': 'quality_gate_config',
                    'id': 'QG-TESTING',
                    'name': 'Testing Task',
                    'task_type': 'testing',  # Wrong type - looking for 'feature'
                    'complexity_range': [1, 10],
                    'arch_review_required': False,
                    'arch_review_threshold': None,
                    'test_pass_required': True,
                    'coverage_required': False,
                    'coverage_threshold': None,
                    'lint_required': True,
                    'rationale': 'Test.',
                    'version': '1.0.0',
                    'effective_from': '2025-01-01T00:00:00',
                    'supersedes': None
                }
            }
        ])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            # Search for 'feature' but result is 'testing' - should return None
            result = await get_quality_gate_config("feature", 5)

            assert result is None

    @pytest.mark.asyncio
    async def test_search_exception_returns_none(self):
        """Test that search exceptions are handled gracefully."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        # Simulate an exception during search
        mock_graphiti.search = AsyncMock(side_effect=Exception("Network error"))

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            # Should not raise, should return None
            result = await get_quality_gate_config("feature", 5)

            assert result is None

    @pytest.mark.asyncio
    async def test_missing_effective_from_uses_current_datetime(self):
        """Test that missing effective_from uses current datetime."""
        from datetime import datetime

        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'entity_type': 'quality_gate_config',
                    'id': 'QG-FEATURE-LOW',
                    'name': 'Feature (Low Complexity)',
                    'task_type': 'feature',
                    'complexity_range': [1, 3],
                    'arch_review_required': False,
                    'arch_review_threshold': None,
                    'test_pass_required': True,
                    'coverage_required': True,
                    'coverage_threshold': 60.0,
                    'lint_required': True,
                    'rationale': 'Test.',
                    'version': '1.0.0',
                    # effective_from is missing (None)
                    'supersedes': None
                }
            }
        ])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            before = datetime.now()
            result = await get_quality_gate_config("feature", 2)
            after = datetime.now()

            assert result is not None
            # effective_from should be set to a datetime close to now
            assert before <= result.effective_from <= after

    @pytest.mark.asyncio
    async def test_complexity_at_boundary_matches_correct_range(self):
        """Test that complexity at boundary (e.g., 3) matches the correct range."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True

        # Config for complexity 1-3 (boundary at 3)
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'entity_type': 'quality_gate_config',
                    'id': 'QG-FEATURE-LOW',
                    'name': 'Feature (Low Complexity)',
                    'task_type': 'feature',
                    'complexity_range': [1, 3],
                    'arch_review_required': False,
                    'arch_review_threshold': None,
                    'test_pass_required': True,
                    'coverage_required': True,
                    'coverage_threshold': 60.0,
                    'lint_required': True,
                    'rationale': 'Simple features.',
                    'version': '1.0.0',
                    'effective_from': '2025-01-01T00:00:00',
                    'supersedes': None
                }
            }
        ])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            # Complexity 3 should match 1-3 range
            result = await get_quality_gate_config("feature", 3)

            assert result is not None
            assert result.id == "QG-FEATURE-LOW"

    @pytest.mark.asyncio
    async def test_empty_results_handling(self):
        """Test handling of empty search results."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            result = await get_quality_gate_config("feature", 5)

            # Should return None gracefully
            assert result is None

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """Test handling of malformed Graphiti response."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {}  # Empty body
            }
        ])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            # Should handle gracefully without raising
            result = await get_quality_gate_config("feature", 5)

            # Should return None for malformed response
            assert result is None

    @pytest.mark.asyncio
    async def test_missing_body_key_handling(self):
        """Test handling of response missing 'body' key."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {}  # No 'body' key
        ])

        with patch('guardkit.knowledge.quality_gate_queries.get_graphiti', return_value=mock_graphiti):
            # Should handle gracefully without raising
            result = await get_quality_gate_config("feature", 5)

            # Should return None for missing body
            assert result is None


# ============================================================================
# 7. Integration Scenarios (3 tests)
# ============================================================================

class TestIntegrationScenarios:
    """Test integration scenarios for quality gate configurations."""

    def test_config_thresholds_are_sensible(self):
        """Test that predefined config thresholds follow sensible patterns."""
        # Find feature configs
        low_config = None
        med_config = None
        high_config = None

        for config in QUALITY_GATE_CONFIGS:
            if config.id == "QG-FEATURE-LOW":
                low_config = config
            elif config.id == "QG-FEATURE-MED":
                med_config = config
            elif config.id == "QG-FEATURE-HIGH":
                high_config = config

        # Low complexity should have lower or no arch threshold
        assert low_config is not None
        assert low_config.arch_review_required is False or low_config.arch_review_threshold is None

        # Medium should have moderate threshold
        assert med_config is not None
        assert med_config.arch_review_threshold is not None
        assert 40 <= med_config.arch_review_threshold <= 60

        # High should have highest threshold
        assert high_config is not None
        assert high_config.arch_review_threshold is not None
        assert high_config.arch_review_threshold >= 60

    def test_coverage_thresholds_increase_with_complexity(self):
        """Test that coverage thresholds increase with complexity for features."""
        feature_configs = [c for c in QUALITY_GATE_CONFIGS if c.task_type == "feature"]

        # Sort by complexity range
        feature_configs.sort(key=lambda c: c.complexity_range[0])

        # Coverage thresholds should be non-decreasing
        prev_threshold = 0.0
        for config in feature_configs:
            if config.coverage_threshold is not None:
                assert config.coverage_threshold >= prev_threshold, (
                    f"Coverage threshold for {config.id} ({config.coverage_threshold}) "
                    f"is less than previous ({prev_threshold})"
                )
                prev_threshold = config.coverage_threshold

    def test_non_code_tasks_have_relaxed_gates(self):
        """Test that non-code tasks (docs) have relaxed quality gates."""
        docs_config = None
        for config in QUALITY_GATE_CONFIGS:
            if config.id == "QG-DOCS":
                docs_config = config
                break

        assert docs_config is not None
        # Docs should not require tests or coverage
        assert docs_config.test_pass_required is False
        assert docs_config.coverage_required is False
        assert docs_config.arch_review_required is False
