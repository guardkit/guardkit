"""
Unit tests for Model Router

Tests the model routing logic for /task-review command to ensure optimal
Claude model selection based on review mode and depth.
"""

import pytest
import sys
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent.parent.parent.parent / "installer" / "global" / "lib"
sys.path.insert(0, str(lib_path))

from task_review.model_router import ModelRouter

OPUS_ID = "claude-opus-4-20250514"
SONNET_ID = "claude-sonnet-4-20250620"


class TestModelRouter:
    """Unit tests for model routing logic."""

    def test_quick_architectural_uses_sonnet(self):
        """Quick architectural reviews use Sonnet for speed."""
        router = ModelRouter()
        assert router.get_model_for_review("architectural", "quick") == SONNET_ID

    def test_quick_security_uses_opus(self):
        """Security is always Opus, even for quick reviews."""
        router = ModelRouter()
        assert router.get_model_for_review("security", "quick") == OPUS_ID

    def test_standard_decision_uses_opus(self):
        """Decisions need deep reasoning at standard depth."""
        router = ModelRouter()
        assert router.get_model_for_review("decision", "standard") == OPUS_ID

    def test_standard_security_uses_opus(self):
        """Security is always Opus."""
        router = ModelRouter()
        assert router.get_model_for_review("security", "standard") == OPUS_ID

    def test_comprehensive_architectural_uses_opus(self):
        """Comprehensive architectural analysis needs Opus."""
        router = ModelRouter()
        assert router.get_model_for_review("architectural", "comprehensive") == OPUS_ID

    def test_comprehensive_code_quality_uses_sonnet(self):
        """Code quality metrics are objective, Sonnet sufficient."""
        router = ModelRouter()
        assert router.get_model_for_review("code-quality", "comprehensive") == SONNET_ID

    def test_all_security_uses_opus(self):
        """Security always uses Opus regardless of depth."""
        router = ModelRouter()
        for depth in ["quick", "standard", "comprehensive"]:
            assert router.get_model_for_review("security", depth) == OPUS_ID

    def test_cost_estimate_accuracy_sonnet(self):
        """Cost estimates are accurate for Sonnet."""
        router = ModelRouter()
        cost_info = router.get_cost_estimate("code-quality", "standard")

        assert cost_info.model_id == SONNET_ID
        assert cost_info.input_cost_per_mtok == 3.00
        assert cost_info.output_cost_per_mtok == 15.00
        assert cost_info.estimated_tokens == 60_000
        # 70/30 split: (42K * $3 + 18K * $15) / 1M = $0.126 + $0.270 = $0.396
        assert 0.39 <= cost_info.estimated_cost_usd <= 0.41

    def test_cost_estimate_accuracy_opus(self):
        """Cost estimates are accurate for Opus."""
        router = ModelRouter()
        cost_info = router.get_cost_estimate("security", "comprehensive")

        assert cost_info.model_id == OPUS_ID
        assert cost_info.input_cost_per_mtok == 5.00
        assert cost_info.output_cost_per_mtok == 25.00
        assert cost_info.estimated_tokens == 150_000
        # 70/30 split: (105K * $5 + 45K * $25) / 1M = $0.525 + $1.125 = $1.65
        assert 1.60 <= cost_info.estimated_cost_usd <= 1.70

    def test_rationale_generation_security(self):
        """Security reviews have clear rationale."""
        router = ModelRouter()
        cost_info = router.get_cost_estimate("security", "quick")

        assert "security breaches cost" in cost_info.rationale.lower()
        assert "opus" in cost_info.rationale.lower()

    def test_rationale_generation_comprehensive(self):
        """Comprehensive reviews explain why Opus is needed."""
        router = ModelRouter()
        cost_info = router.get_cost_estimate("architectural", "comprehensive")

        assert "opus" in cost_info.rationale.lower()
        assert "comprehensive" in cost_info.rationale.lower() or "deep" in cost_info.rationale.lower()

    def test_routing_matrix_coverage(self):
        """All mode/depth combinations are defined."""
        router = ModelRouter()

        modes = ["architectural", "code-quality", "decision", "technical-debt", "security"]
        depths = ["quick", "standard", "comprehensive"]

        for mode in modes:
            for depth in depths:
                model = router.get_model_for_review(mode, depth)
                assert model in [OPUS_ID, SONNET_ID]

    def test_standard_architectural_uses_sonnet(self):
        """Standard architectural reviews use Sonnet."""
        router = ModelRouter()
        assert router.get_model_for_review("architectural", "standard") == SONNET_ID

    def test_quick_code_quality_uses_sonnet(self):
        """Quick code quality reviews use Sonnet."""
        router = ModelRouter()
        assert router.get_model_for_review("code-quality", "quick") == SONNET_ID

    def test_comprehensive_decision_uses_opus(self):
        """Comprehensive decision reviews use Opus."""
        router = ModelRouter()
        assert router.get_model_for_review("decision", "comprehensive") == OPUS_ID

    def test_comprehensive_technical_debt_uses_opus(self):
        """Comprehensive technical debt reviews use Opus."""
        router = ModelRouter()
        assert router.get_model_for_review("technical-debt", "comprehensive") == OPUS_ID

    def test_quick_technical_debt_uses_sonnet(self):
        """Quick technical debt reviews use Sonnet."""
        router = ModelRouter()
        assert router.get_model_for_review("technical-debt", "quick") == SONNET_ID

    def test_standard_technical_debt_uses_sonnet(self):
        """Standard technical debt reviews use Sonnet."""
        router = ModelRouter()
        assert router.get_model_for_review("technical-debt", "standard") == SONNET_ID


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
