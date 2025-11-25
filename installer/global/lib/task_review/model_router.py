"""
Model Router for Task Review Command

Determines optimal Claude model based on review mode and depth.
Balances cost efficiency with quality requirements.

Decision Matrix:
- Quick reviews: Sonnet (speed matters)
- Standard reviews: Mixed (Opus for critical scenarios)
- Comprehensive reviews: Opus for high-value analysis
- Security: Always Opus (security breaches cost more than models)
"""

from typing import Dict, Literal, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

ReviewMode = Literal["architectural", "code-quality", "decision", "technical-debt", "security"]
ReviewDepth = Literal["quick", "standard", "comprehensive"]
ModelId = Literal["claude-opus-4-20250514", "claude-sonnet-4-20250620"]


@dataclass
class ModelCostInfo:
    """Cost information for model selection transparency."""
    model_id: str
    input_cost_per_mtok: float  # Per million tokens
    output_cost_per_mtok: float
    estimated_tokens: int
    estimated_cost_usd: float
    rationale: str


class ModelRouter:
    """
    Routes review tasks to appropriate Claude model.

    Philosophy:
    - Quick: Speed > thoroughness (except security)
    - Standard: Balance cost/quality (Opus for critical scenarios)
    - Comprehensive: Quality justifies cost (high-value analysis)
    - Security: Always Opus (breaches cost more than models)
    """

    # Model routing matrix (80% Sonnet, 20% Opus)
    ROUTING_MATRIX: Dict[ReviewDepth, Dict[ReviewMode, ModelId]] = {
        "quick": {
            "architectural": "claude-sonnet-4-20250620",
            "code-quality": "claude-sonnet-4-20250620",
            "decision": "claude-sonnet-4-20250620",
            "technical-debt": "claude-sonnet-4-20250620",
            "security": "claude-opus-4-20250514",  # Exception: Always critical
        },
        "standard": {
            "architectural": "claude-sonnet-4-20250620",
            "code-quality": "claude-sonnet-4-20250620",
            "decision": "claude-opus-4-20250514",  # Decisions need deep reasoning
            "technical-debt": "claude-sonnet-4-20250620",
            "security": "claude-opus-4-20250514",  # Always critical
        },
        "comprehensive": {
            "architectural": "claude-opus-4-20250514",  # Deep SOLID/DRY/YAGNI analysis
            "code-quality": "claude-sonnet-4-20250620",  # Metrics are objective
            "decision": "claude-opus-4-20250514",  # Critical decisions
            "technical-debt": "claude-opus-4-20250514",  # Complex prioritization
            "security": "claude-opus-4-20250514",  # Always critical
        }
    }

    # Pricing per million tokens
    PRICING = {
        "claude-opus-4-20250514": {"input": 5.00, "output": 25.00},
        "claude-sonnet-4-20250620": {"input": 3.00, "output": 15.00},
    }

    # Estimated token usage by depth
    TOKEN_ESTIMATES = {
        "quick": 20_000,      # 15-30 min
        "standard": 60_000,   # 1-2 hours
        "comprehensive": 150_000,  # 4-6 hours
    }

    def get_model_for_review(
        self,
        mode: ReviewMode,
        depth: ReviewDepth = "standard"
    ) -> ModelId:
        """
        Select optimal model for review task.

        Args:
            mode: Type of review (architectural, security, etc.)
            depth: Review thoroughness (quick, standard, comprehensive)

        Returns:
            Claude model ID to use
        """
        model_id = self.ROUTING_MATRIX[depth][mode]

        logger.info(
            f"Model routing: mode={mode}, depth={depth} → {model_id}",
            extra={
                "review_mode": mode,
                "review_depth": depth,
                "selected_model": model_id,
            }
        )

        return model_id

    def get_cost_estimate(
        self,
        mode: ReviewMode,
        depth: ReviewDepth = "standard"
    ) -> ModelCostInfo:
        """
        Estimate cost for review task with transparency.

        Args:
            mode: Type of review
            depth: Review thoroughness

        Returns:
            Cost information including model, pricing, and rationale
        """
        model_id = self.get_model_for_review(mode, depth)
        pricing = self.PRICING[model_id]
        estimated_tokens = self.TOKEN_ESTIMATES[depth]

        # Assume 70/30 input/output split
        input_tokens = int(estimated_tokens * 0.7)
        output_tokens = int(estimated_tokens * 0.3)

        estimated_cost = (
            (input_tokens / 1_000_000) * pricing["input"] +
            (output_tokens / 1_000_000) * pricing["output"]
        )

        rationale = self._get_routing_rationale(mode, depth, model_id)

        return ModelCostInfo(
            model_id=model_id,
            input_cost_per_mtok=pricing["input"],
            output_cost_per_mtok=pricing["output"],
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=round(estimated_cost, 2),
            rationale=rationale,
        )

    def _get_routing_rationale(
        self,
        mode: ReviewMode,
        depth: ReviewDepth,
        model_id: ModelId
    ) -> str:
        """Generate human-readable rationale for model selection."""

        if mode == "security":
            return "Security reviews always use Opus 4.5 (security breaches cost exponentially more than model costs)"

        if model_id.startswith("claude-opus"):
            reasons = []
            if depth == "comprehensive":
                reasons.append(f"{depth} depth requires deep analysis")
            if mode == "decision":
                reasons.append("complex decisions require strong reasoning capabilities")
            if mode == "architectural":
                reasons.append("thorough SOLID/DRY/YAGNI evaluation needs deep pattern recognition")
            if mode == "technical-debt":
                reasons.append("debt prioritization requires nuanced effort vs impact analysis")

            return f"Using Opus 4.5: {', '.join(reasons)}"
        else:
            reasons = []
            if depth == "quick":
                reasons.append("quick reviews prioritize speed over thoroughness")
            if mode == "code-quality":
                reasons.append("quality metrics are objective and well-suited for Sonnet")

            return f"Using Sonnet 4.5: {', '.join(reasons) or 'cost-effective for this review type'}"

    def log_model_usage(
        self,
        task_id: str,
        mode: ReviewMode,
        depth: ReviewDepth,
        model_id: ModelId,
        actual_tokens: int = None
    ) -> None:
        """
        Log model usage for cost tracking and analysis.

        Args:
            task_id: Task being reviewed
            mode: Review mode
            depth: Review depth
            model_id: Model used
            actual_tokens: Actual token count (if available)
        """
        logger.info(
            f"Review completed: {task_id} using {model_id}",
            extra={
                "task_id": task_id,
                "review_mode": mode,
                "review_depth": depth,
                "model_id": model_id,
                "actual_tokens": actual_tokens,
            }
        )
