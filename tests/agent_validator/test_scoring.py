"""Tests for scoring aggregation."""

import unittest
import sys
from pathlib import Path

# Add lib path
lib_path = Path(__file__).parent.parent.parent / 'installer' / 'global' / 'commands' / 'lib'
sys.path.insert(0, str(lib_path))

from agent_validator.scoring import ScoreAggregator
from agent_validator.models import CategoryScore, CheckResult


class TestScoreAggregator(unittest.TestCase):
    """Test score aggregation logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.aggregator = ScoreAggregator()

    def test_category_weights_sum_to_one(self):
        """Test that category weights sum to 1.0."""
        total_weight = sum(self.aggregator.CATEGORY_WEIGHTS.values())
        self.assertAlmostEqual(total_weight, 1.0, places=2)

    def test_aggregate_categories_simple(self):
        """Test aggregating check results into category scores."""
        category_results = {
            'structure': {
                'frontmatter': CheckResult(
                    name="Test",
                    measured_value=1,
                    threshold=1,
                    score=10.0,
                    weight=0.5,
                    status="pass",
                    message="Test"
                ),
                'length': CheckResult(
                    name="Test2",
                    measured_value=1,
                    threshold=1,
                    score=8.0,
                    weight=0.5,
                    status="pass",
                    message="Test"
                )
            }
        }

        category_scores = self.aggregator.aggregate_categories(category_results)

        self.assertIn('structure', category_scores)
        self.assertEqual(category_scores['structure'].score, 9.0)  # (10*0.5 + 8*0.5)

    def test_calculate_overall_score(self):
        """Test overall score calculation from category scores."""
        category_scores = {
            'structure': CategoryScore(
                name='structure',
                score=8.0,
                weight=0.15
            ),
            'example_density': CategoryScore(
                name='example_density',
                score=7.0,
                weight=0.25
            )
        }

        overall = self.aggregator.calculate_overall(category_scores)

        # (8.0 * 0.15 + 7.0 * 0.25) / (0.15 + 0.25) = 7.375
        expected = (8.0 * 0.15 + 7.0 * 0.25) / 0.4
        self.assertAlmostEqual(overall, expected, places=2)

    def test_overall_score_clamped(self):
        """Test that overall score is clamped to 0-10 range."""
        # Test upper bound
        category_scores = {
            'test': CategoryScore(name='test', score=15.0, weight=1.0)
        }
        overall = self.aggregator.calculate_overall(category_scores)
        self.assertLessEqual(overall, 10.0)

        # Test lower bound (should not go below 0)
        category_scores = {
            'test': CategoryScore(name='test', score=-5.0, weight=1.0)
        }
        overall = self.aggregator.calculate_overall(category_scores)
        self.assertGreaterEqual(overall, 0.0)


if __name__ == '__main__':
    unittest.main()
