"""
Relevance Tuning for Job-Specific Context Retrieval.

This module provides configurable relevance thresholds and quality metrics
for context retrieval. It enables tuning of how strictly results are filtered
based on task characteristics.

Public API:
    RelevanceConfig: Configurable relevance thresholds
    ContextQualityMetrics: Tracking metrics for retrieval quality
    MetricsCollector: Collector for aggregating quality metrics
    default_config: Factory for default configuration
    strict_config: Factory for stricter thresholds
    relaxed_config: Factory for more inclusive results

Example:
    from guardkit.knowledge.relevance_tuning import (
        RelevanceConfig,
        ContextQualityMetrics,
        default_config,
    )

    # Use default thresholds
    config = default_config()

    # Or customize thresholds
    config = RelevanceConfig(
        standard_threshold=0.7,
        first_of_type_threshold=0.55,
    )

    # Track quality during retrieval
    metrics = ContextQualityMetrics(...)
    if metrics.is_quality_acceptable():
        print("Good quality context retrieved")

References:
    - TASK-GR6-011: Add relevance tuning
    - FEAT-GR-006: Job-Specific Context Retrieval
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .task_analyzer import TaskCharacteristics


def _validate_threshold(value: float, name: str) -> None:
    """Validate that a threshold is between 0.0 and 1.0.

    Args:
        value: Threshold value to validate
        name: Name of the threshold for error message

    Raises:
        ValueError: If threshold is outside valid range
    """
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{name} threshold must be between 0.0 and 1.0, got {value}")


@dataclass
class RelevanceConfig:
    """Configuration for relevance thresholds.

    Provides configurable thresholds for filtering context retrieval results
    based on task characteristics. Different thresholds can be applied to
    different task types.

    Attributes:
        first_of_type_threshold: Threshold for novel task types (default: 0.5)
        standard_threshold: Threshold for standard tasks (default: 0.6)
        refinement_threshold: Threshold for refinement tasks (default: 0.55)
        autobuild_threshold: Threshold for AutoBuild tasks (default: 0.5)

    Example:
        config = RelevanceConfig(
            standard_threshold=0.7,  # Stricter filtering
        )

        threshold = config.get_threshold(characteristics)
    """

    first_of_type_threshold: float = 0.5
    standard_threshold: float = 0.6
    refinement_threshold: float = 0.55
    autobuild_threshold: float = 0.5

    def __post_init__(self) -> None:
        """Validate all threshold values after initialization."""
        _validate_threshold(self.first_of_type_threshold, "first_of_type")
        _validate_threshold(self.standard_threshold, "standard")
        _validate_threshold(self.refinement_threshold, "refinement")
        _validate_threshold(self.autobuild_threshold, "autobuild")

    def get_threshold(self, characteristics: TaskCharacteristics) -> float:
        """Get the appropriate threshold for a task's characteristics.

        Determines which threshold to use based on task properties,
        with the following priority:
        1. AutoBuild tasks use autobuild_threshold
        2. First-of-type tasks use first_of_type_threshold
        3. Refinement tasks use refinement_threshold
        4. All other tasks use standard_threshold

        Args:
            characteristics: TaskCharacteristics with task properties

        Returns:
            Appropriate threshold value for the task

        Example:
            threshold = config.get_threshold(characteristics)
            if result.score >= threshold:
                include_result(result)
        """
        # Priority 1: AutoBuild tasks get lowest threshold for more context
        if getattr(characteristics, "is_autobuild", False):
            return self.autobuild_threshold

        # Priority 2: First-of-type tasks need more context (lower threshold)
        if characteristics.is_first_of_type:
            return self.first_of_type_threshold

        # Priority 3: Refinement tasks benefit from broader context
        if characteristics.is_refinement:
            return self.refinement_threshold

        # Default: Standard threshold
        return self.standard_threshold


@dataclass
class ContextQualityMetrics:
    """Metrics for tracking context retrieval quality.

    Provides insights into the quality and effectiveness of retrieved context,
    including relevance scores, coverage, and budget utilization.

    Attributes:
        avg_relevance_score: Average relevance score of retrieved items
        total_items_retrieved: Total number of items retrieved
        items_above_threshold: Items with score above threshold
        items_below_threshold: Items with score below threshold
        category_coverage: Dict mapping category to fill percentage
        budget_utilization: Percentage of budget used (0.0-1.0)

    Example:
        metrics = ContextQualityMetrics(
            avg_relevance_score=0.75,
            total_items_retrieved=10,
            items_above_threshold=8,
            items_below_threshold=2,
            category_coverage={"feature_context": 0.8},
            budget_utilization=0.85,
        )

        if metrics.is_quality_acceptable():
            print("Good quality")
    """

    avg_relevance_score: float
    total_items_retrieved: int
    items_above_threshold: int
    items_below_threshold: int
    category_coverage: Dict[str, float]
    budget_utilization: float

    @property
    def relevance_rate(self) -> float:
        """Calculate the rate of items above threshold.

        Returns:
            Percentage of items above threshold (0.0-1.0),
            or 0.0 if no items retrieved
        """
        if self.total_items_retrieved == 0:
            return 0.0
        return self.items_above_threshold / self.total_items_retrieved

    def is_quality_acceptable(self, min_relevance_rate: float = 0.7) -> bool:
        """Check if retrieval quality meets minimum standards.

        Args:
            min_relevance_rate: Minimum acceptable relevance rate (default: 0.7)

        Returns:
            True if quality is acceptable, False otherwise
        """
        return self.relevance_rate >= min_relevance_rate

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary representation.

        Returns:
            Dictionary with all metrics including calculated properties
        """
        return {
            "avg_relevance_score": self.avg_relevance_score,
            "total_items_retrieved": self.total_items_retrieved,
            "items_above_threshold": self.items_above_threshold,
            "items_below_threshold": self.items_below_threshold,
            "category_coverage": self.category_coverage,
            "budget_utilization": self.budget_utilization,
            "relevance_rate": self.relevance_rate,
            "is_quality_acceptable": self.is_quality_acceptable(),
        }


class MetricsCollector:
    """Collector for aggregating context quality metrics.

    Collects metrics during context retrieval and produces a
    ContextQualityMetrics summary.

    Attributes:
        threshold: Relevance threshold for classification
        total_budget: Total token budget (optional)
        budget_per_category: Dict of category budgets (optional)

    Example:
        collector = MetricsCollector(threshold=0.6, total_budget=4000)

        # During retrieval
        for result in search_results:
            collector.add_result(result, category="feature_context")

        collector.add_budget_usage(2500)

        # Get aggregated metrics
        metrics = collector.get_metrics()
    """

    def __init__(
        self,
        threshold: float,
        total_budget: int = 0,
        budget_per_category: Optional[Dict[str, int]] = None,
    ) -> None:
        """Initialize MetricsCollector.

        Args:
            threshold: Relevance threshold for above/below classification
            total_budget: Total token budget for utilization calculation
            budget_per_category: Dict mapping category to budget allocation
        """
        self.threshold = threshold
        self.total_budget = total_budget
        self.budget_per_category = budget_per_category or {}

        # Internal tracking
        self._results: List[Dict[str, Any]] = []
        self._category_counts: Dict[str, int] = {}
        self._budget_used: int = 0

    def add_result(
        self,
        result: Dict[str, Any],
        category: str,
    ) -> None:
        """Add a retrieval result to metrics collection.

        Args:
            result: Result dictionary with optional "score" field
            category: Category name for coverage tracking
        """
        self._results.append({
            "result": result,
            "category": category,
            "score": result.get("score", 1.0),  # Default to 1.0 if no score
        })

        # Track category counts
        self._category_counts[category] = self._category_counts.get(category, 0) + 1

    def add_budget_usage(self, tokens: int) -> None:
        """Add to the budget usage counter.

        Args:
            tokens: Number of tokens used
        """
        self._budget_used += tokens

    def reset(self) -> None:
        """Reset all collected metrics."""
        self._results = []
        self._category_counts = {}
        self._budget_used = 0

    def get_metrics(self) -> ContextQualityMetrics:
        """Calculate and return aggregated metrics.

        Returns:
            ContextQualityMetrics with all calculated values
        """
        total_items = len(self._results)

        if total_items == 0:
            return ContextQualityMetrics(
                avg_relevance_score=0.0,
                total_items_retrieved=0,
                items_above_threshold=0,
                items_below_threshold=0,
                category_coverage={},
                budget_utilization=0.0,
            )

        # Calculate scores
        scores = [r["score"] for r in self._results]
        avg_score = sum(scores) / len(scores)

        # Count above/below threshold
        above = sum(1 for s in scores if s >= self.threshold)
        below = total_items - above

        # Calculate category coverage
        category_coverage: Dict[str, float] = {}
        for category, count in self._category_counts.items():
            if category in self.budget_per_category and self.budget_per_category[category] > 0:
                category_coverage[category] = count / self.budget_per_category[category]

        # Calculate budget utilization
        budget_utilization = 0.0
        if self.total_budget > 0:
            budget_utilization = self._budget_used / self.total_budget

        return ContextQualityMetrics(
            avg_relevance_score=avg_score,
            total_items_retrieved=total_items,
            items_above_threshold=above,
            items_below_threshold=below,
            category_coverage=category_coverage,
            budget_utilization=budget_utilization,
        )


# ============================================================================
# Factory Functions
# ============================================================================


def default_config() -> RelevanceConfig:
    """Create a RelevanceConfig with default thresholds.

    Returns:
        RelevanceConfig with default values:
        - first_of_type_threshold: 0.5
        - standard_threshold: 0.6
        - refinement_threshold: 0.55
        - autobuild_threshold: 0.5
    """
    return RelevanceConfig()


def strict_config() -> RelevanceConfig:
    """Create a RelevanceConfig with stricter thresholds.

    Use this when you want more precise, higher-quality context
    at the cost of potentially retrieving fewer items.

    Returns:
        RelevanceConfig with stricter thresholds:
        - first_of_type_threshold: 0.6
        - standard_threshold: 0.7
        - refinement_threshold: 0.65
        - autobuild_threshold: 0.6
    """
    return RelevanceConfig(
        first_of_type_threshold=0.6,
        standard_threshold=0.7,
        refinement_threshold=0.65,
        autobuild_threshold=0.6,
    )


def relaxed_config() -> RelevanceConfig:
    """Create a RelevanceConfig with more relaxed thresholds.

    Use this when you want more inclusive results, accepting
    items with lower relevance scores.

    Returns:
        RelevanceConfig with relaxed thresholds:
        - first_of_type_threshold: 0.35
        - standard_threshold: 0.45
        - refinement_threshold: 0.4
        - autobuild_threshold: 0.35
    """
    return RelevanceConfig(
        first_of_type_threshold=0.35,
        standard_threshold=0.45,
        refinement_threshold=0.4,
        autobuild_threshold=0.35,
    )
