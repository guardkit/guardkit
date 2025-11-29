"""
Scoring aggregation for agent validation.

Combines individual check scores into category scores and overall scores.
"""

from typing import Dict

try:
    from .models import CategoryScore, CheckResult
except ImportError:
    from models import CategoryScore, CheckResult


class ScoreAggregator:
    """Aggregates validation scores across categories."""

    # Category weights (must sum to 1.0)
    CATEGORY_WEIGHTS = {
        'structure': 0.15,        # 15%
        'example_density': 0.25,  # 25%
        'boundaries': 0.20,       # 20%
        'specificity': 0.20,      # 20%
        'example_quality': 0.15,  # 15%
        'maintenance': 0.05       # 5%
    }

    def aggregate_categories(
        self,
        category_results: Dict[str, Dict[str, CheckResult]]
    ) -> Dict[str, CategoryScore]:
        """
        Aggregate check results into category scores.

        Args:
            category_results: Dict mapping category name to dict of CheckResults

        Returns:
            Dict mapping category name to CategoryScore
        """
        category_scores = {}

        for category_name, check_results in category_results.items():
            # Calculate weighted average of check scores within category
            total_weighted_score = 0.0
            total_weight = 0.0

            for check_result in check_results.values():
                total_weighted_score += check_result.score * check_result.weight
                total_weight += check_result.weight

            # Category score is weighted average of its checks
            category_score = total_weighted_score / total_weight if total_weight > 0 else 0.0

            category_scores[category_name] = CategoryScore(
                name=category_name,
                score=category_score,
                weight=self.CATEGORY_WEIGHTS.get(category_name, 0.0),
                checks=check_results
            )

        return category_scores

    def calculate_overall(self, category_scores: Dict[str, CategoryScore]) -> float:
        """
        Calculate overall score from category scores.

        Args:
            category_scores: Dict mapping category name to CategoryScore

        Returns:
            Overall score (0.0-10.0)
        """
        total_weighted_score = 0.0
        total_weight = 0.0

        for category_score in category_scores.values():
            total_weighted_score += category_score.weighted_score
            total_weight += category_score.weight

        # Overall score is weighted average of category scores
        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0.0

        # Clamp to 0.0-10.0 range
        return max(0.0, min(10.0, overall_score))
