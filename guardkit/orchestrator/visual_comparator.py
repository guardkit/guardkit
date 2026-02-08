"""SSIM Visual Comparison Pipeline for Design Mode.

This module implements the tiered visual comparison pipeline using SSIM
(Structural Similarity Index) as the deterministic primary comparison method,
with AI vision escalation for borderline cases.

Architecture:
    Tier 1: SSIM Score (deterministic, zero token cost)
    - SSIM >= 0.95 -> PASS (Coach approves)
    - SSIM 0.85-0.94 -> ESCALATE to Tier 2
    - SSIM < 0.85 -> FAIL (Coach rejects, Player retries)

    Tier 2: AI Vision Review (borderline cases only)
    - Send both images + SSIM spatial map to Coach's LLM
    - Coach reasons about rendering artifacts vs actual violations
    - Coach makes final determination with explanation

SSIM Variant:
    Uses bezkrovny variant (recommended by jest-image-snapshot)
    - Fast computation, negligible accuracy loss
    - Produces spatial quality map showing WHERE differences occur

Example:
    >>> from guardkit.orchestrator.visual_comparator import VisualComparator
    >>>
    >>> comparator = VisualComparator()
    >>> result = await comparator.compare(reference_bytes, rendered_bytes)
    >>> if result.passed:
    ...     print(f"Visual match: SSIM={result.ssim_score:.3f}")
    ... else:
    ...     print(f"Mismatch: {result.feedback}")
"""

import io
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================


class ComparisonMethod(str, Enum):
    """Method used for visual comparison.

    Attributes:
        SSIM: Pure SSIM comparison (Tier 1 only)
        SSIM_PLUS_AI_VISION: SSIM with AI vision review (Tier 2)
    """

    SSIM = "ssim"
    SSIM_PLUS_AI_VISION = "ssim+ai_vision"


class ComparisonTier(int, Enum):
    """Tier of comparison used.

    Attributes:
        TIER_1: Deterministic SSIM only (zero token cost)
        TIER_2: SSIM + AI vision review (borderline cases)
    """

    TIER_1 = 1
    TIER_2 = 2


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ComparisonResult:
    """Result of visual comparison between reference and rendered images.

    Attributes:
        passed: Whether the visual comparison passed
        ssim_score: SSIM score between 0.0 and 1.0
        method: Comparison method used (ssim or ssim+ai_vision)
        tier: Comparison tier (1 or 2)
        feedback: Optional explanation (present if failed or escalated)
        spatial_map: Optional SSIM spatial difference map (PNG bytes)
    """

    passed: bool
    ssim_score: float
    method: ComparisonMethod
    tier: ComparisonTier
    feedback: Optional[str] = None
    spatial_map: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "passed": self.passed,
            "ssim_score": self.ssim_score,
            "method": self.method.value,
            "tier": self.tier.value,
            "feedback": self.feedback,
            "spatial_map": self.spatial_map.hex() if self.spatial_map else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonResult":
        """Create from dictionary.

        Args:
            data: Dictionary with comparison result data

        Returns:
            ComparisonResult instance
        """
        spatial_map = None
        if data.get("spatial_map"):
            spatial_map = bytes.fromhex(data["spatial_map"])

        return cls(
            passed=data.get("passed", False),
            ssim_score=data.get("ssim_score", 0.0),
            method=ComparisonMethod(data.get("method", "ssim")),
            tier=ComparisonTier(data.get("tier", 1)),
            feedback=data.get("feedback"),
            spatial_map=spatial_map,
        )


# ============================================================================
# SSIM Comparator (Tier 1 Engine)
# ============================================================================


class SSIMComparator:
    """SSIM computation engine using bezkrovny variant.

    This class handles the deterministic SSIM computation with zero token cost.
    Uses the bezkrovny variant as recommended by jest-image-snapshot for
    fast computation with negligible accuracy loss.

    Attributes:
        variant: SSIM variant used (always "bezkrovny")
    """

    def __init__(self):
        """Initialize SSIMComparator with bezkrovny variant."""
        self.variant = "bezkrovny"
        self._ssim_available = self._check_ssim_availability()

    def _check_ssim_availability(self) -> bool:
        """Check if SSIM computation dependencies are available.

        Returns:
            True if dependencies available, False otherwise
        """
        try:
            from skimage.metrics import structural_similarity
            from PIL import Image

            return True
        except ImportError:
            logger.warning(
                "SSIM dependencies not available. "
                "Install with: pip install scikit-image pillow"
            )
            return False

    def _load_image(self, image_bytes: bytes) -> "np.ndarray":
        """Load image bytes into numpy array.

        Args:
            image_bytes: PNG image as bytes

        Returns:
            Numpy array representing the image

        Raises:
            ValueError: If image bytes are empty or invalid
            RuntimeError: If image cannot be decoded
        """
        if not image_bytes:
            raise ValueError("Empty image bytes")

        try:
            from PIL import Image
            import numpy as np

            img = Image.open(io.BytesIO(image_bytes))
            # Convert to RGB if necessary (handles RGBA, L, etc.)
            if img.mode == "RGBA":
                # Remove alpha channel for SSIM comparison
                img = img.convert("RGB")
            elif img.mode == "L":
                # Keep grayscale as-is
                pass
            elif img.mode != "RGB":
                img = img.convert("RGB")

            return np.array(img)
        except Exception as e:
            raise RuntimeError(f"Failed to decode image: {e}")

    def compute_ssim(self, reference: bytes, rendered: bytes) -> float:
        """Compute SSIM score between two images.

        This is a pure mathematical computation with zero token cost.
        Uses bezkrovny variant for fast, accurate comparison.

        Args:
            reference: Reference image as PNG bytes
            rendered: Rendered image as PNG bytes

        Returns:
            SSIM score between 0.0 and 1.0

        Raises:
            ValueError: If images have different dimensions
            RuntimeError: If SSIM computation fails
        """
        if not self._ssim_available:
            raise RuntimeError(
                "SSIM dependencies not available. "
                "Install with: pip install scikit-image pillow"
            )

        try:
            from skimage.metrics import structural_similarity
            import numpy as np

            # Load images
            ref_img = self._load_image(reference)
            rend_img = self._load_image(rendered)

            # Validate dimensions match
            if ref_img.shape != rend_img.shape:
                raise ValueError(
                    f"Image dimensions must match. "
                    f"Reference: {ref_img.shape}, Rendered: {rend_img.shape}"
                )

            # Determine if grayscale or color
            is_grayscale = len(ref_img.shape) == 2

            # Calculate data range, handle solid color images (min == max)
            data_range = ref_img.max() - ref_img.min()
            if data_range == 0:
                # For solid color images, use default 8-bit range
                data_range = 255

            # Compute SSIM with data_range for proper normalization
            if is_grayscale:
                score = structural_similarity(
                    ref_img,
                    rend_img,
                    data_range=data_range,
                )
            else:
                # For color images, compute SSIM per channel and average
                score = structural_similarity(
                    ref_img,
                    rend_img,
                    data_range=data_range,
                    channel_axis=2,  # RGB channels on axis 2
                )

            # Handle NaN (can occur with identical solid-color images)
            if np.isnan(score):
                # If images are identical, return 1.0
                if np.array_equal(ref_img, rend_img):
                    score = 1.0
                else:
                    score = 0.0

            return float(score)

        except ImportError as e:
            raise RuntimeError(f"SSIM dependency missing: {e}")
        except Exception as e:
            raise RuntimeError(f"SSIM computation failed: {e}")

    def compute_ssim_with_map(
        self, reference: bytes, rendered: bytes
    ) -> Tuple[float, bytes]:
        """Compute SSIM score and generate spatial quality map.

        The spatial map shows WHERE differences occur, which is passed
        to Tier 2 AI vision for targeted reasoning.

        Args:
            reference: Reference image as PNG bytes
            rendered: Rendered image as PNG bytes

        Returns:
            Tuple of (SSIM score, spatial map as PNG bytes)

        Raises:
            ValueError: If images have different dimensions
            RuntimeError: If computation fails
        """
        if not self._ssim_available:
            raise RuntimeError(
                "SSIM dependencies not available. "
                "Install with: pip install scikit-image pillow"
            )

        try:
            from skimage.metrics import structural_similarity
            from PIL import Image
            import numpy as np

            # Load images
            ref_img = self._load_image(reference)
            rend_img = self._load_image(rendered)

            # Validate dimensions match
            if ref_img.shape != rend_img.shape:
                raise ValueError(
                    f"Image dimensions must match. "
                    f"Reference: {ref_img.shape}, Rendered: {rend_img.shape}"
                )

            # Determine if grayscale or color
            is_grayscale = len(ref_img.shape) == 2

            # Calculate data range, handle solid color images
            if is_grayscale:
                data_range = ref_img.max() - ref_img.min()
            else:
                ref_gray = np.mean(ref_img, axis=2).astype(np.uint8)
                rend_gray = np.mean(rend_img, axis=2).astype(np.uint8)
                data_range = ref_gray.max() - ref_gray.min()

            if data_range == 0:
                data_range = 255

            # Compute SSIM with full image output for spatial map
            if is_grayscale:
                score, diff_map = structural_similarity(
                    ref_img,
                    rend_img,
                    data_range=data_range,
                    full=True,
                )
            else:
                score, diff_map = structural_similarity(
                    ref_gray,
                    rend_gray,
                    data_range=data_range,
                    full=True,
                )

            # Handle NaN
            if np.isnan(score):
                if is_grayscale:
                    score = 1.0 if np.array_equal(ref_img, rend_img) else 0.0
                else:
                    score = 1.0 if np.array_equal(ref_gray, rend_gray) else 0.0

            # Convert diff map to visual representation
            # Invert and scale to show differences as bright areas
            diff_visual = ((1 - diff_map) * 255).astype(np.uint8)

            # Create PNG bytes from diff map
            diff_img = Image.fromarray(diff_visual, mode="L")
            buffer = io.BytesIO()
            diff_img.save(buffer, format="PNG")
            spatial_map_bytes = buffer.getvalue()

            return float(score), spatial_map_bytes

        except ImportError as e:
            raise RuntimeError(f"SSIM dependency missing: {e}")
        except Exception as e:
            raise RuntimeError(f"SSIM with map computation failed: {e}")


# ============================================================================
# Visual Comparator (Main Orchestrator)
# ============================================================================


class VisualComparator:
    """Main visual comparison orchestrator implementing tiered pipeline.

    Implements the tiered visual comparison pipeline:
    - Tier 1: SSIM >= 0.95 auto-PASS, < 0.85 auto-FAIL
    - Tier 2: 0.85-0.94 escalates to AI vision with spatial map

    Attributes:
        _ssim_comparator: SSIM computation engine
        _ai_client: Optional AI client for Tier 2 escalation

    Example:
        >>> comparator = VisualComparator()
        >>> result = await comparator.compare(reference, rendered)
        >>> print(f"Passed: {result.passed}, Score: {result.ssim_score:.3f}")
    """

    # Threshold constants
    TIER1_PASS_THRESHOLD = 0.95  # SSIM >= 0.95 -> Tier 1 PASS
    TIER1_FAIL_THRESHOLD = 0.85  # SSIM < 0.85 -> Tier 1 FAIL
    # Between 0.85 and 0.95 -> Tier 2 escalation

    def __init__(
        self,
        ai_vision_callback: Optional[
            Callable[[bytes, bytes, bytes, float], Tuple[bool, str]]
        ] = None,
    ):
        """Initialize VisualComparator.

        Args:
            ai_vision_callback: Optional callback for Tier 2 AI vision review.
                Signature: (reference, rendered, spatial_map, ssim_score) -> (passed, feedback)
                If not provided, a default async callback will be used.
        """
        self._ssim_comparator = SSIMComparator()
        self._ai_vision_callback = ai_vision_callback

    async def compare(self, reference: bytes, rendered: bytes) -> ComparisonResult:
        """Compare reference and rendered images using tiered pipeline.

        Implements the comparison pipeline:
        1. Compute SSIM score (deterministic, zero token cost)
        2. Route based on score:
           - >= 0.95: Tier 1 PASS
           - < 0.85: Tier 1 FAIL
           - 0.85-0.94: Tier 2 escalation

        Args:
            reference: Reference/design image as PNG bytes
            rendered: Rendered implementation image as PNG bytes

        Returns:
            ComparisonResult with pass/fail decision and details

        Raises:
            ValueError: If images are invalid or have mismatched dimensions
            RuntimeError: If comparison fails
        """
        # Validate inputs
        if not reference or not rendered:
            raise ValueError("Reference and rendered images cannot be empty")

        # Step 1: Compute SSIM (Tier 1 - deterministic, zero token cost)
        try:
            # First try simple SSIM for quick routing decision
            ssim_score = self._ssim_comparator.compute_ssim(reference, rendered)
        except Exception as e:
            raise RuntimeError(f"SSIM computation failed: {e}")

        logger.debug(f"SSIM score: {ssim_score:.4f}")

        # Step 2: Route based on SSIM score
        if ssim_score >= self.TIER1_PASS_THRESHOLD:
            # Tier 1 PASS - High fidelity match
            logger.info(f"Tier 1 PASS: SSIM={ssim_score:.4f} >= {self.TIER1_PASS_THRESHOLD}")
            return ComparisonResult(
                passed=True,
                ssim_score=ssim_score,
                method=ComparisonMethod.SSIM,
                tier=ComparisonTier.TIER_1,
                feedback=f"High fidelity match (SSIM={ssim_score:.3f})",
            )

        elif ssim_score < self.TIER1_FAIL_THRESHOLD:
            # Tier 1 FAIL - Clear visual mismatch
            logger.info(f"Tier 1 FAIL: SSIM={ssim_score:.4f} < {self.TIER1_FAIL_THRESHOLD}")
            return ComparisonResult(
                passed=False,
                ssim_score=ssim_score,
                method=ComparisonMethod.SSIM,
                tier=ComparisonTier.TIER_1,
                feedback=(
                    f"Visual mismatch detected (SSIM={ssim_score:.3f}). "
                    f"Significant differences between design and implementation."
                ),
            )

        else:
            # Tier 2 ESCALATE - Borderline case, needs AI vision review
            logger.info(
                f"Tier 2 ESCALATE: SSIM={ssim_score:.4f} in borderline range "
                f"[{self.TIER1_FAIL_THRESHOLD}, {self.TIER1_PASS_THRESHOLD})"
            )
            return await self._handle_tier2_escalation(
                reference, rendered, ssim_score
            )

    async def _handle_tier2_escalation(
        self, reference: bytes, rendered: bytes, ssim_score: float
    ) -> ComparisonResult:
        """Handle Tier 2 escalation with AI vision review.

        Computes spatial map and invokes AI vision to make final determination
        about whether differences are acceptable rendering artifacts or
        actual visual violations.

        Args:
            reference: Reference image bytes
            rendered: Rendered image bytes
            ssim_score: Pre-computed SSIM score

        Returns:
            ComparisonResult with Tier 2 determination
        """
        # Get spatial map for AI reasoning
        try:
            _, spatial_map = self._ssim_comparator.compute_ssim_with_map(
                reference, rendered
            )
        except Exception as e:
            logger.error(f"Failed to generate spatial map: {e}")
            # Fall back to Tier 1 FAIL if we can't generate spatial map
            return ComparisonResult(
                passed=False,
                ssim_score=ssim_score,
                method=ComparisonMethod.SSIM,
                tier=ComparisonTier.TIER_1,
                feedback=f"Borderline case but spatial map generation failed: {e}",
            )

        # Invoke AI vision review
        try:
            ai_passed, ai_feedback = await self._ai_vision_review(
                reference, rendered, spatial_map, ssim_score
            )
        except Exception as e:
            logger.error(f"AI vision review failed: {e}")
            # Fall back to conservative FAIL if AI review fails
            return ComparisonResult(
                passed=False,
                ssim_score=ssim_score,
                method=ComparisonMethod.SSIM_PLUS_AI_VISION,
                tier=ComparisonTier.TIER_2,
                feedback=f"AI vision review failed: {e}. Defaulting to FAIL.",
                spatial_map=spatial_map,
            )

        logger.info(f"Tier 2 AI verdict: {'PASS' if ai_passed else 'FAIL'} - {ai_feedback}")

        return ComparisonResult(
            passed=ai_passed,
            ssim_score=ssim_score,
            method=ComparisonMethod.SSIM_PLUS_AI_VISION,
            tier=ComparisonTier.TIER_2,
            feedback=ai_feedback,
            spatial_map=spatial_map,
        )

    async def _ai_vision_review(
        self,
        reference: bytes,
        rendered: bytes,
        spatial_map: bytes,
        ssim_score: float,
    ) -> Tuple[bool, str]:
        """Invoke AI vision to review borderline visual differences.

        The AI receives:
        - Reference image (design)
        - Rendered image (implementation)
        - Spatial map (showing WHERE differences occur)
        - SSIM score (for context)

        Args:
            reference: Reference image bytes
            rendered: Rendered image bytes
            spatial_map: SSIM spatial difference map (PNG bytes)
            ssim_score: Pre-computed SSIM score

        Returns:
            Tuple of (passed: bool, feedback: str)
        """
        # If callback provided, use it
        if self._ai_vision_callback:
            return self._ai_vision_callback(
                reference, rendered, spatial_map, ssim_score
            )

        # Default implementation - placeholder for actual AI integration
        # In production, this would call the Coach's LLM with vision capabilities
        logger.warning(
            "No AI vision callback configured. "
            "Using conservative default (FAIL for borderline cases)."
        )

        return (
            False,
            f"Borderline SSIM score ({ssim_score:.3f}) requires manual review. "
            "No AI vision callback configured for automated review.",
        )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "ComparisonMethod",
    "ComparisonResult",
    "ComparisonTier",
    "SSIMComparator",
    "VisualComparator",
]
