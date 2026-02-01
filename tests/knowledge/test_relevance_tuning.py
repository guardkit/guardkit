"""
Tests for relevance tuning functionality (TASK-GR6-011).

Tests cover:
- RelevanceConfig dataclass for configurable thresholds
- ContextQualityMetrics for tracking retrieval quality
- Integration with JobContextRetriever

TDD RED PHASE: These tests define the expected behavior.

Coverage Target: >=85%

References:
- TASK-GR6-011: Add relevance tuning
- FEAT-GR-006: Job-Specific Context Retrieval
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import is_dataclass, fields


# ============================================================================
# 1. RelevanceConfig Dataclass Tests
# ============================================================================


class TestRelevanceConfigDataclass:
    """Test RelevanceConfig dataclass for configurable thresholds."""

    def test_dataclass_exists(self):
        """Test that RelevanceConfig dataclass exists."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        assert RelevanceConfig is not None

    def test_dataclass_is_dataclass(self):
        """Test that RelevanceConfig is a dataclass."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        assert is_dataclass(RelevanceConfig)

    def test_dataclass_has_required_fields(self):
        """Test that RelevanceConfig has all required fields."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        field_names = {f.name for f in fields(RelevanceConfig)}
        expected_fields = {
            "first_of_type_threshold",
            "standard_threshold",
            "refinement_threshold",
            "autobuild_threshold",
        }

        assert expected_fields.issubset(field_names)

    def test_default_first_of_type_threshold(self):
        """Test default first_of_type_threshold is 0.5."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        config = RelevanceConfig()
        assert config.first_of_type_threshold == 0.5

    def test_default_standard_threshold(self):
        """Test default standard_threshold is 0.6."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        config = RelevanceConfig()
        assert config.standard_threshold == 0.6

    def test_default_refinement_threshold(self):
        """Test default refinement_threshold is 0.55."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        config = RelevanceConfig()
        assert config.refinement_threshold == 0.55

    def test_default_autobuild_threshold(self):
        """Test default autobuild_threshold is 0.5."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        config = RelevanceConfig()
        assert config.autobuild_threshold == 0.5

    def test_custom_thresholds(self):
        """Test that custom thresholds can be set."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        config = RelevanceConfig(
            first_of_type_threshold=0.4,
            standard_threshold=0.7,
            refinement_threshold=0.6,
            autobuild_threshold=0.45,
        )

        assert config.first_of_type_threshold == 0.4
        assert config.standard_threshold == 0.7
        assert config.refinement_threshold == 0.6
        assert config.autobuild_threshold == 0.45

    def test_threshold_validation_min(self):
        """Test that thresholds must be >= 0.0."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        with pytest.raises(ValueError, match="threshold must be between 0.0 and 1.0"):
            RelevanceConfig(first_of_type_threshold=-0.1)

    def test_threshold_validation_max(self):
        """Test that thresholds must be <= 1.0."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        with pytest.raises(ValueError, match="threshold must be between 0.0 and 1.0"):
            RelevanceConfig(standard_threshold=1.5)

    def test_get_threshold_for_task_first_of_type(self):
        """Test get_threshold returns first_of_type_threshold for novel tasks."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        config = RelevanceConfig()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,
            is_first_of_type=True,  # First of type
            similar_task_count=0,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        threshold = config.get_threshold(characteristics)
        assert threshold == 0.5  # first_of_type_threshold

    def test_get_threshold_for_task_standard(self):
        """Test get_threshold returns standard_threshold for standard tasks."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        config = RelevanceConfig()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,
            is_first_of_type=False,  # Not first of type
            similar_task_count=5,
            feature_id=None,
            is_refinement=False,  # Not refinement
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            is_autobuild=False,  # Not autobuild
        )

        threshold = config.get_threshold(characteristics)
        assert threshold == 0.6  # standard_threshold

    def test_get_threshold_for_task_refinement(self):
        """Test get_threshold returns refinement_threshold for refinement tasks."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        config = RelevanceConfig()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,
            is_first_of_type=False,
            similar_task_count=5,
            feature_id=None,
            is_refinement=True,  # Refinement
            refinement_attempt=2,
            previous_failure_type="test_failure",
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        threshold = config.get_threshold(characteristics)
        assert threshold == 0.55  # refinement_threshold

    def test_get_threshold_for_task_autobuild(self):
        """Test get_threshold returns autobuild_threshold for AutoBuild tasks."""
        from guardkit.knowledge.relevance_tuning import RelevanceConfig
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        config = RelevanceConfig()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,
            is_first_of_type=False,
            similar_task_count=5,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            is_autobuild=True,  # AutoBuild
            current_actor="player",
            turn_number=1,
        )

        threshold = config.get_threshold(characteristics)
        assert threshold == 0.5  # autobuild_threshold


# ============================================================================
# 2. ContextQualityMetrics Dataclass Tests
# ============================================================================


class TestContextQualityMetricsDataclass:
    """Test ContextQualityMetrics for tracking retrieval quality."""

    def test_dataclass_exists(self):
        """Test that ContextQualityMetrics dataclass exists."""
        from guardkit.knowledge.relevance_tuning import ContextQualityMetrics

        assert ContextQualityMetrics is not None

    def test_dataclass_is_dataclass(self):
        """Test that ContextQualityMetrics is a dataclass."""
        from guardkit.knowledge.relevance_tuning import ContextQualityMetrics

        assert is_dataclass(ContextQualityMetrics)

    def test_dataclass_has_required_fields(self):
        """Test that ContextQualityMetrics has all required fields."""
        from guardkit.knowledge.relevance_tuning import ContextQualityMetrics

        field_names = {f.name for f in fields(ContextQualityMetrics)}
        expected_fields = {
            "avg_relevance_score",
            "total_items_retrieved",
            "items_above_threshold",
            "items_below_threshold",
            "category_coverage",
            "budget_utilization",
        }

        assert expected_fields.issubset(field_names)

    def test_can_be_instantiated(self):
        """Test that ContextQualityMetrics can be instantiated."""
        from guardkit.knowledge.relevance_tuning import ContextQualityMetrics

        metrics = ContextQualityMetrics(
            avg_relevance_score=0.75,
            total_items_retrieved=10,
            items_above_threshold=8,
            items_below_threshold=2,
            category_coverage={"feature_context": 0.8, "similar_outcomes": 0.6},
            budget_utilization=0.85,
        )

        assert metrics.avg_relevance_score == 0.75
        assert metrics.total_items_retrieved == 10
        assert metrics.items_above_threshold == 8
        assert metrics.items_below_threshold == 2
        assert metrics.category_coverage["feature_context"] == 0.8
        assert metrics.budget_utilization == 0.85

    def test_relevance_rate_property(self):
        """Test relevance_rate calculated property."""
        from guardkit.knowledge.relevance_tuning import ContextQualityMetrics

        metrics = ContextQualityMetrics(
            avg_relevance_score=0.75,
            total_items_retrieved=10,
            items_above_threshold=8,
            items_below_threshold=2,
            category_coverage={},
            budget_utilization=0.85,
        )

        # 8 / 10 = 0.8
        assert metrics.relevance_rate == 0.8

    def test_relevance_rate_zero_items(self):
        """Test relevance_rate when no items retrieved."""
        from guardkit.knowledge.relevance_tuning import ContextQualityMetrics

        metrics = ContextQualityMetrics(
            avg_relevance_score=0.0,
            total_items_retrieved=0,
            items_above_threshold=0,
            items_below_threshold=0,
            category_coverage={},
            budget_utilization=0.0,
        )

        # Should return 0.0, not divide by zero
        assert metrics.relevance_rate == 0.0

    def test_is_quality_acceptable_true(self):
        """Test is_quality_acceptable returns True for good metrics."""
        from guardkit.knowledge.relevance_tuning import ContextQualityMetrics

        metrics = ContextQualityMetrics(
            avg_relevance_score=0.75,
            total_items_retrieved=10,
            items_above_threshold=8,
            items_below_threshold=2,
            category_coverage={"feature_context": 0.8},
            budget_utilization=0.85,
        )

        # Default threshold is 0.7 for relevance_rate
        assert metrics.is_quality_acceptable() is True

    def test_is_quality_acceptable_false(self):
        """Test is_quality_acceptable returns False for poor metrics."""
        from guardkit.knowledge.relevance_tuning import ContextQualityMetrics

        metrics = ContextQualityMetrics(
            avg_relevance_score=0.5,
            total_items_retrieved=10,
            items_above_threshold=4,
            items_below_threshold=6,
            category_coverage={"feature_context": 0.3},
            budget_utilization=0.4,
        )

        # Only 40% relevance rate
        assert metrics.is_quality_acceptable() is False

    def test_is_quality_acceptable_custom_threshold(self):
        """Test is_quality_acceptable with custom minimum rate."""
        from guardkit.knowledge.relevance_tuning import ContextQualityMetrics

        metrics = ContextQualityMetrics(
            avg_relevance_score=0.6,
            total_items_retrieved=10,
            items_above_threshold=6,
            items_below_threshold=4,
            category_coverage={},
            budget_utilization=0.7,
        )

        # 60% relevance rate
        assert metrics.is_quality_acceptable(min_relevance_rate=0.5) is True
        assert metrics.is_quality_acceptable(min_relevance_rate=0.7) is False

    def test_to_dict_method(self):
        """Test to_dict returns dictionary representation."""
        from guardkit.knowledge.relevance_tuning import ContextQualityMetrics

        metrics = ContextQualityMetrics(
            avg_relevance_score=0.75,
            total_items_retrieved=10,
            items_above_threshold=8,
            items_below_threshold=2,
            category_coverage={"feature_context": 0.8},
            budget_utilization=0.85,
        )

        result = metrics.to_dict()

        assert isinstance(result, dict)
        assert result["avg_relevance_score"] == 0.75
        assert result["total_items_retrieved"] == 10
        assert result["relevance_rate"] == 0.8


# ============================================================================
# 3. MetricsCollector Class Tests
# ============================================================================


class TestMetricsCollector:
    """Test MetricsCollector for aggregating quality metrics."""

    def test_class_exists(self):
        """Test that MetricsCollector class exists."""
        from guardkit.knowledge.relevance_tuning import MetricsCollector

        assert MetricsCollector is not None

    def test_can_be_instantiated(self):
        """Test MetricsCollector can be instantiated with threshold."""
        from guardkit.knowledge.relevance_tuning import MetricsCollector

        collector = MetricsCollector(threshold=0.6)
        assert collector is not None
        assert collector.threshold == 0.6

    def test_add_result_above_threshold(self):
        """Test adding a result above threshold."""
        from guardkit.knowledge.relevance_tuning import MetricsCollector

        collector = MetricsCollector(threshold=0.6)

        collector.add_result({"score": 0.8, "content": "test"}, category="feature_context")

        metrics = collector.get_metrics()
        assert metrics.items_above_threshold >= 1

    def test_add_result_below_threshold(self):
        """Test adding a result below threshold."""
        from guardkit.knowledge.relevance_tuning import MetricsCollector

        collector = MetricsCollector(threshold=0.6)

        collector.add_result({"score": 0.4, "content": "test"}, category="feature_context")

        metrics = collector.get_metrics()
        assert metrics.items_below_threshold >= 1

    def test_add_multiple_results(self):
        """Test adding multiple results and calculating metrics."""
        from guardkit.knowledge.relevance_tuning import MetricsCollector

        collector = MetricsCollector(threshold=0.5)

        # Add results for different categories
        collector.add_result({"score": 0.8}, category="feature_context")
        collector.add_result({"score": 0.6}, category="feature_context")
        collector.add_result({"score": 0.4}, category="similar_outcomes")
        collector.add_result({"score": 0.9}, category="warnings")

        metrics = collector.get_metrics()

        assert metrics.total_items_retrieved == 4
        assert metrics.items_above_threshold == 3  # 0.8, 0.6, 0.9
        assert metrics.items_below_threshold == 1  # 0.4

    def test_category_coverage_tracking(self):
        """Test that category coverage is tracked."""
        from guardkit.knowledge.relevance_tuning import MetricsCollector

        collector = MetricsCollector(threshold=0.5, budget_per_category={
            "feature_context": 5,
            "similar_outcomes": 3,
        })

        # Add 2 items to feature_context (40% of budget 5)
        collector.add_result({"score": 0.8}, category="feature_context")
        collector.add_result({"score": 0.7}, category="feature_context")

        metrics = collector.get_metrics()

        assert "feature_context" in metrics.category_coverage
        assert metrics.category_coverage["feature_context"] == pytest.approx(0.4, rel=0.01)

    def test_budget_utilization_calculation(self):
        """Test budget utilization is calculated correctly."""
        from guardkit.knowledge.relevance_tuning import MetricsCollector

        collector = MetricsCollector(threshold=0.5, total_budget=100)

        # Simulate using 85 tokens
        collector.add_budget_usage(85)

        metrics = collector.get_metrics()

        assert metrics.budget_utilization == 0.85

    def test_avg_relevance_score_calculation(self):
        """Test average relevance score is calculated correctly."""
        from guardkit.knowledge.relevance_tuning import MetricsCollector

        collector = MetricsCollector(threshold=0.5)

        collector.add_result({"score": 0.8}, category="test")
        collector.add_result({"score": 0.6}, category="test")
        collector.add_result({"score": 0.4}, category="test")

        metrics = collector.get_metrics()

        # (0.8 + 0.6 + 0.4) / 3 = 0.6
        assert metrics.avg_relevance_score == pytest.approx(0.6, rel=0.01)

    def test_reset_clears_all_metrics(self):
        """Test reset() clears all collected metrics."""
        from guardkit.knowledge.relevance_tuning import MetricsCollector

        collector = MetricsCollector(threshold=0.5)

        collector.add_result({"score": 0.8}, category="test")
        collector.add_result({"score": 0.6}, category="test")

        collector.reset()

        metrics = collector.get_metrics()
        assert metrics.total_items_retrieved == 0
        assert metrics.items_above_threshold == 0


# ============================================================================
# 4. JobContextRetriever Integration Tests
# ============================================================================


class TestJobContextRetrieverRelevanceIntegration:
    """Test relevance tuning integration with JobContextRetriever."""

    @pytest.mark.asyncio
    async def test_retriever_accepts_relevance_config(self):
        """Test JobContextRetriever accepts RelevanceConfig."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        mock_graphiti = AsyncMock()
        config = RelevanceConfig(standard_threshold=0.7)

        retriever = JobContextRetriever(mock_graphiti, relevance_config=config)

        assert retriever.relevance_config is not None
        assert retriever.relevance_config.standard_threshold == 0.7

    @pytest.mark.asyncio
    async def test_retriever_uses_custom_threshold(self):
        """Test retriever uses custom threshold from config."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        mock_graphiti = AsyncMock()

        # Results with varying scores
        mock_results = [
            {"score": 0.9, "content": "high"},
            {"score": 0.75, "content": "medium-high"},
            {"score": 0.65, "content": "medium"},  # Would pass 0.6, fail 0.7
            {"score": 0.5, "content": "low"},
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        # Custom config with higher threshold
        config = RelevanceConfig(standard_threshold=0.7)
        retriever = JobContextRetriever(mock_graphiti, relevance_config=config)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should filter out items with score < 0.7
        all_items = (
            result.feature_context
            + result.similar_outcomes
            + result.relevant_patterns
            + result.architecture_context
            + result.warnings
            + result.domain_knowledge
        )

        for item in all_items:
            if "score" in item:
                assert item["score"] >= 0.7

    @pytest.mark.asyncio
    async def test_retriever_returns_quality_metrics(self):
        """Test retriever returns quality metrics when requested."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase
        from guardkit.knowledge.relevance_tuning import ContextQualityMetrics

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[
            {"score": 0.8, "content": "test"},
        ])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await retriever.retrieve(
            task,
            TaskPhase.IMPLEMENT,
            collect_metrics=True,
        )

        # Result should have metrics attribute
        assert hasattr(result, "quality_metrics")
        assert isinstance(result.quality_metrics, ContextQualityMetrics)

    @pytest.mark.asyncio
    async def test_retriever_metrics_track_relevance(self):
        """Test quality metrics track relevance correctly."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[
            {"score": 0.8, "content": "high"},
            {"score": 0.7, "content": "medium"},
            {"score": 0.4, "content": "low"},  # Below threshold
        ])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await retriever.retrieve(
            task,
            TaskPhase.IMPLEMENT,
            collect_metrics=True,
        )

        # Check metrics reflect filtering
        metrics = result.quality_metrics
        assert metrics.total_items_retrieved > 0
        assert metrics.avg_relevance_score > 0


# ============================================================================
# 5. RelevanceConfig Factory Function Tests
# ============================================================================


class TestRelevanceConfigFactory:
    """Test factory functions for creating RelevanceConfig."""

    def test_default_config_factory(self):
        """Test default_config() factory function."""
        from guardkit.knowledge.relevance_tuning import default_config

        config = default_config()

        assert config.first_of_type_threshold == 0.5
        assert config.standard_threshold == 0.6
        assert config.refinement_threshold == 0.55
        assert config.autobuild_threshold == 0.5

    def test_strict_config_factory(self):
        """Test strict_config() factory function for stricter filtering."""
        from guardkit.knowledge.relevance_tuning import strict_config

        config = strict_config()

        # Stricter thresholds
        assert config.first_of_type_threshold >= 0.6
        assert config.standard_threshold >= 0.7
        assert config.refinement_threshold >= 0.6

    def test_relaxed_config_factory(self):
        """Test relaxed_config() factory function for more inclusive results."""
        from guardkit.knowledge.relevance_tuning import relaxed_config

        config = relaxed_config()

        # More relaxed thresholds
        assert config.first_of_type_threshold <= 0.4
        assert config.standard_threshold <= 0.5
        assert config.refinement_threshold <= 0.4
