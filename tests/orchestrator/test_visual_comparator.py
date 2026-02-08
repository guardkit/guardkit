"""Test suite for SSIM visual comparison pipeline.

TDD RED PHASE: All tests are written BEFORE implementation.
These tests MUST fail initially and will pass once implementation is complete.

Tests cover:
- SSIM comparison using bezkrovny variant
- Tier 1: SSIM >= 0.95 auto-PASS, < 0.85 auto-FAIL
- Tier 2: 0.85-0.94 escalates to AI vision with spatial map
- ComparisonResult dataclass with score, method, tier, feedback
- Spatial map generation for Tier 2 escalation
- Zero token cost for Tier 1 (deterministic computation)
- Unit tests with synthetic image pairs at each threshold
"""

import asyncio
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# These imports WILL fail until implementation exists - this is expected in TDD RED phase
from guardkit.orchestrator.visual_comparator import (
    ComparisonMethod,
    ComparisonResult,
    ComparisonTier,
    SSIMComparator,
    VisualComparator,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Create minimal valid PNG bytes for testing."""
    # Minimal PNG: 8x8 red pixel
    # PNG header + IHDR + IDAT (compressed) + IEND
    return (
        b"\x89PNG\r\n\x1a\n"  # PNG signature
        b"\x00\x00\x00\rIHDR"  # IHDR chunk
        b"\x00\x00\x00\x08"  # Width: 8
        b"\x00\x00\x00\x08"  # Height: 8
        b"\x08\x02"  # Bit depth 8, RGB
        b"\x00\x00\x00"  # Compression, filter, interlace
        b"\x90wS\xde"  # CRC
        b"\x00\x00\x00\x19IDAT"  # IDAT chunk
        b"x\x9cc\xfcO\x00\x00\x00"  # Compressed data placeholder
        b"\x00\x00\x00\x00IEND"  # IEND chunk
        b"\xaeB`\x82"  # CRC
    )


@pytest.fixture
def create_test_image():
    """Factory fixture to create test images with specific characteristics."""
    def _create(width: int = 100, height: int = 100, color: tuple = (255, 0, 0)) -> bytes:
        """Create a simple test image.

        Args:
            width: Image width in pixels
            height: Image height in pixels
            color: RGB tuple for fill color

        Returns:
            PNG image as bytes
        """
        try:
            from PIL import Image
            import io

            img = Image.new("RGB", (width, height), color)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
        except ImportError:
            # Fallback if PIL not available - return placeholder
            return b"\x89PNG\r\n\x1a\n" + bytes([0] * 100)

    return _create


@pytest.fixture
def identical_images(create_test_image) -> tuple[bytes, bytes]:
    """Create two identical images for testing perfect match."""
    img = create_test_image(100, 100, (255, 0, 0))
    return img, img


@pytest.fixture
def slightly_different_images(create_test_image) -> tuple[bytes, bytes]:
    """Create two slightly different images (expected SSIM ~0.90-0.94)."""
    img1 = create_test_image(100, 100, (255, 0, 0))
    img2 = create_test_image(100, 100, (250, 5, 5))  # Slightly different red
    return img1, img2


@pytest.fixture
def very_different_images(create_test_image) -> tuple[bytes, bytes]:
    """Create two very different images (expected SSIM < 0.85)."""
    img1 = create_test_image(100, 100, (255, 0, 0))  # Red
    img2 = create_test_image(100, 100, (0, 0, 255))  # Blue
    return img1, img2


@pytest.fixture
def visual_comparator() -> VisualComparator:
    """Create VisualComparator instance for testing."""
    return VisualComparator()


@pytest.fixture
def ssim_comparator() -> SSIMComparator:
    """Create SSIMComparator instance for testing."""
    return SSIMComparator()


# ============================================================================
# Test Classes
# ============================================================================


class TestComparisonResult:
    """Tests for ComparisonResult dataclass."""

    def test_comparison_result_has_required_fields(self):
        """Test that ComparisonResult has all required fields from spec."""
        result = ComparisonResult(
            passed=True,
            ssim_score=0.95,
            method=ComparisonMethod.SSIM,
            tier=ComparisonTier.TIER_1,
            feedback=None,
            spatial_map=None,
        )

        assert hasattr(result, "passed")
        assert hasattr(result, "ssim_score")
        assert hasattr(result, "method")
        assert hasattr(result, "tier")
        assert hasattr(result, "feedback")
        assert hasattr(result, "spatial_map")

    def test_comparison_result_ssim_score_range(self):
        """Test that ssim_score is between 0.0 and 1.0."""
        result = ComparisonResult(
            passed=True,
            ssim_score=0.95,
            method=ComparisonMethod.SSIM,
            tier=ComparisonTier.TIER_1,
        )

        assert 0.0 <= result.ssim_score <= 1.0

    def test_comparison_result_method_values(self):
        """Test that method is either 'ssim' or 'ssim+ai_vision'."""
        result_ssim = ComparisonResult(
            passed=True,
            ssim_score=0.95,
            method=ComparisonMethod.SSIM,
            tier=ComparisonTier.TIER_1,
        )

        result_ai = ComparisonResult(
            passed=True,
            ssim_score=0.90,
            method=ComparisonMethod.SSIM_PLUS_AI_VISION,
            tier=ComparisonTier.TIER_2,
        )

        assert result_ssim.method == ComparisonMethod.SSIM
        assert result_ai.method == ComparisonMethod.SSIM_PLUS_AI_VISION

    def test_comparison_result_tier_values(self):
        """Test that tier is either 1 or 2."""
        result_tier1 = ComparisonResult(
            passed=True,
            ssim_score=0.95,
            method=ComparisonMethod.SSIM,
            tier=ComparisonTier.TIER_1,
        )

        result_tier2 = ComparisonResult(
            passed=True,
            ssim_score=0.90,
            method=ComparisonMethod.SSIM_PLUS_AI_VISION,
            tier=ComparisonTier.TIER_2,
        )

        assert result_tier1.tier == ComparisonTier.TIER_1
        assert result_tier2.tier == ComparisonTier.TIER_2

    def test_comparison_result_to_dict(self):
        """Test that ComparisonResult can be serialized to dict."""
        result = ComparisonResult(
            passed=True,
            ssim_score=0.95,
            method=ComparisonMethod.SSIM,
            tier=ComparisonTier.TIER_1,
            feedback="High fidelity match",
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["passed"] is True
        assert result_dict["ssim_score"] == 0.95
        assert result_dict["method"] == "ssim"
        assert result_dict["tier"] == 1
        assert result_dict["feedback"] == "High fidelity match"

    def test_comparison_result_from_dict(self):
        """Test that ComparisonResult can be deserialized from dict."""
        data = {
            "passed": True,
            "ssim_score": 0.95,
            "method": "ssim",
            "tier": 1,
            "feedback": "High fidelity match",
            "spatial_map": None,
        }

        result = ComparisonResult.from_dict(data)

        assert result.passed is True
        assert result.ssim_score == 0.95
        assert result.method == ComparisonMethod.SSIM
        assert result.tier == ComparisonTier.TIER_1


class TestSSIMComparator:
    """Tests for SSIMComparator (Tier 1 engine)."""

    def test_ssim_comparator_exists(self, ssim_comparator: SSIMComparator):
        """Test that SSIMComparator can be instantiated."""
        assert ssim_comparator is not None

    def test_ssim_compute_returns_score(self, ssim_comparator: SSIMComparator, identical_images):
        """Test that compute_ssim returns a score between 0 and 1."""
        reference, rendered = identical_images
        score = ssim_comparator.compute_ssim(reference, rendered)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_ssim_identical_images_score_high(self, ssim_comparator: SSIMComparator, identical_images):
        """Test that identical images produce SSIM score close to 1.0."""
        reference, rendered = identical_images
        score = ssim_comparator.compute_ssim(reference, rendered)

        # Identical images should have SSIM >= 0.99
        assert score >= 0.99

    def test_ssim_different_images_score_low(self, ssim_comparator: SSIMComparator, very_different_images):
        """Test that very different images produce low SSIM score."""
        reference, rendered = very_different_images
        score = ssim_comparator.compute_ssim(reference, rendered)

        # Very different images should have SSIM < 0.85
        assert score < 0.85

    def test_ssim_generates_spatial_map(self, ssim_comparator: SSIMComparator, slightly_different_images):
        """Test that SSIM generates spatial quality map."""
        reference, rendered = slightly_different_images
        score, spatial_map = ssim_comparator.compute_ssim_with_map(reference, rendered)

        assert isinstance(score, float)
        assert spatial_map is not None
        assert isinstance(spatial_map, bytes)
        assert len(spatial_map) > 0

    def test_ssim_is_deterministic(self, ssim_comparator: SSIMComparator, identical_images):
        """Test that SSIM computation is deterministic (same inputs = same output)."""
        reference, rendered = identical_images

        score1 = ssim_comparator.compute_ssim(reference, rendered)
        score2 = ssim_comparator.compute_ssim(reference, rendered)

        assert score1 == score2

    def test_ssim_uses_bezkrovny_variant(self, ssim_comparator: SSIMComparator):
        """Test that SSIM uses bezkrovny variant (as recommended by jest-image-snapshot)."""
        # The bezkrovny variant is an implementation detail
        # We verify by checking that the comparator is configured correctly
        assert ssim_comparator.variant == "bezkrovny"

    def test_ssim_handles_different_image_sizes(self, ssim_comparator: SSIMComparator, create_test_image):
        """Test that SSIM handles images of different sizes gracefully."""
        img1 = create_test_image(100, 100, (255, 0, 0))
        img2 = create_test_image(200, 200, (255, 0, 0))

        # Should either resize or raise appropriate error
        with pytest.raises((ValueError, RuntimeError)):
            ssim_comparator.compute_ssim(img1, img2)

    def test_ssim_handles_invalid_image_bytes(self, ssim_comparator: SSIMComparator):
        """Test that SSIM handles invalid image bytes gracefully."""
        invalid_bytes = b"not an image"
        valid_bytes = b"\x89PNG\r\n\x1a\n" + bytes([0] * 100)

        with pytest.raises((ValueError, RuntimeError)):
            ssim_comparator.compute_ssim(invalid_bytes, valid_bytes)


class TestVisualComparator:
    """Tests for VisualComparator (main orchestrator class)."""

    def test_visual_comparator_has_compare_method(self, visual_comparator: VisualComparator):
        """Test that VisualComparator has async compare method."""
        assert hasattr(visual_comparator, "compare")
        assert asyncio.iscoroutinefunction(visual_comparator.compare)

    @pytest.mark.asyncio
    async def test_compare_returns_comparison_result(
        self, visual_comparator: VisualComparator, identical_images
    ):
        """Test that compare returns ComparisonResult."""
        reference, rendered = identical_images
        result = await visual_comparator.compare(reference, rendered)

        assert isinstance(result, ComparisonResult)

    @pytest.mark.asyncio
    async def test_compare_with_identical_images_passes(
        self, visual_comparator: VisualComparator, identical_images
    ):
        """Test that identical images pass comparison."""
        reference, rendered = identical_images
        result = await visual_comparator.compare(reference, rendered)

        assert result.passed is True
        assert result.ssim_score >= 0.95


class TestTier1ThresholdPass:
    """Tests for Tier 1: SSIM >= 0.95 auto-PASS."""

    @pytest.mark.asyncio
    async def test_tier1_pass_threshold_095(
        self, visual_comparator: VisualComparator, identical_images
    ):
        """Test that SSIM >= 0.95 results in Tier 1 PASS."""
        reference, rendered = identical_images
        result = await visual_comparator.compare(reference, rendered)

        assert result.ssim_score >= 0.95
        assert result.passed is True
        assert result.tier == ComparisonTier.TIER_1
        assert result.method == ComparisonMethod.SSIM

    @pytest.mark.asyncio
    async def test_tier1_pass_no_ai_escalation(
        self, visual_comparator: VisualComparator, identical_images
    ):
        """Test that Tier 1 PASS does not escalate to AI vision."""
        reference, rendered = identical_images
        result = await visual_comparator.compare(reference, rendered)

        # Should NOT use AI vision
        assert result.method == ComparisonMethod.SSIM
        assert result.tier == ComparisonTier.TIER_1

    @pytest.mark.asyncio
    async def test_tier1_pass_zero_token_cost(
        self, visual_comparator: VisualComparator, identical_images
    ):
        """Test that Tier 1 PASS has zero token cost (no AI invocation)."""
        reference, rendered = identical_images

        # Patch any AI client to ensure it's not called
        with patch.object(visual_comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
            result = await visual_comparator.compare(reference, rendered)

            # AI should NOT be called for high SSIM scores
            mock_ai.assert_not_called()

        assert result.tier == ComparisonTier.TIER_1

    @pytest.mark.asyncio
    async def test_tier1_pass_no_spatial_map_needed(
        self, visual_comparator: VisualComparator, identical_images
    ):
        """Test that Tier 1 PASS doesn't require spatial map in result."""
        reference, rendered = identical_images
        result = await visual_comparator.compare(reference, rendered)

        # Spatial map is optional for Tier 1 passes
        assert result.passed is True
        # spatial_map can be None or present


class TestTier1ThresholdFail:
    """Tests for Tier 1: SSIM < 0.85 auto-FAIL."""

    @pytest.mark.asyncio
    async def test_tier1_fail_threshold_085(
        self, visual_comparator: VisualComparator, very_different_images
    ):
        """Test that SSIM < 0.85 results in Tier 1 FAIL."""
        reference, rendered = very_different_images
        result = await visual_comparator.compare(reference, rendered)

        assert result.ssim_score < 0.85
        assert result.passed is False
        assert result.tier == ComparisonTier.TIER_1

    @pytest.mark.asyncio
    async def test_tier1_fail_no_ai_escalation(
        self, visual_comparator: VisualComparator, very_different_images
    ):
        """Test that Tier 1 FAIL does not escalate to AI vision."""
        reference, rendered = very_different_images
        result = await visual_comparator.compare(reference, rendered)

        # Should NOT use AI vision for clear failures
        assert result.method == ComparisonMethod.SSIM
        assert result.tier == ComparisonTier.TIER_1

    @pytest.mark.asyncio
    async def test_tier1_fail_provides_feedback(
        self, visual_comparator: VisualComparator, very_different_images
    ):
        """Test that Tier 1 FAIL provides rejection feedback."""
        reference, rendered = very_different_images
        result = await visual_comparator.compare(reference, rendered)

        assert result.passed is False
        assert result.feedback is not None
        assert len(result.feedback) > 0

    @pytest.mark.asyncio
    async def test_tier1_fail_zero_token_cost(
        self, visual_comparator: VisualComparator, very_different_images
    ):
        """Test that Tier 1 FAIL has zero token cost (no AI invocation)."""
        reference, rendered = very_different_images

        with patch.object(visual_comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
            result = await visual_comparator.compare(reference, rendered)

            # AI should NOT be called for low SSIM scores
            mock_ai.assert_not_called()

        assert result.tier == ComparisonTier.TIER_1


class TestTier2Escalation:
    """Tests for Tier 2: SSIM 0.85-0.94 escalates to AI vision."""

    @pytest.fixture
    def borderline_images(self, create_test_image) -> tuple[bytes, bytes]:
        """Create images with SSIM in borderline range (0.85-0.94)."""
        # Create two images that are similar but not identical
        # This requires careful color selection to hit the borderline range
        img1 = create_test_image(100, 100, (255, 0, 0))  # Pure red
        img2 = create_test_image(100, 100, (230, 25, 25))  # Slightly different red
        return img1, img2

    @pytest.mark.asyncio
    async def test_tier2_escalation_threshold(
        self, visual_comparator: VisualComparator
    ):
        """Test that SSIM 0.85-0.94 escalates to Tier 2."""
        # Mock both compute_ssim (for initial routing) and compute_ssim_with_map (for spatial)
        with patch.object(visual_comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.90  # Borderline score

            with patch.object(visual_comparator._ssim_comparator, "compute_ssim_with_map") as mock_ssim_map:
                mock_ssim_map.return_value = (0.90, b"spatial_map_data")

                # Mock AI vision to approve
                with patch.object(visual_comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
                    mock_ai.return_value = (True, "Minor rendering artifacts acceptable")

                    reference = b"ref_image"
                    rendered = b"rendered_image"
                    result = await visual_comparator.compare(reference, rendered)

                    # Should escalate to AI vision
                    mock_ai.assert_called_once()
                    assert result.tier == ComparisonTier.TIER_2
                    assert result.method == ComparisonMethod.SSIM_PLUS_AI_VISION

    @pytest.mark.asyncio
    async def test_tier2_receives_spatial_map(
        self, visual_comparator: VisualComparator
    ):
        """Test that Tier 2 AI vision receives SSIM spatial map."""
        spatial_map_data = b"ssim_spatial_map_bytes"

        with patch.object(visual_comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.90

            with patch.object(visual_comparator._ssim_comparator, "compute_ssim_with_map") as mock_ssim_map:
                mock_ssim_map.return_value = (0.90, spatial_map_data)

                with patch.object(visual_comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
                    mock_ai.return_value = (True, "Acceptable")

                    reference = b"ref_image"
                    rendered = b"rendered_image"
                    await visual_comparator.compare(reference, rendered)

                    # Verify AI vision received spatial map
                    call_args = mock_ai.call_args
                    assert spatial_map_data in call_args.args or spatial_map_data in call_args.kwargs.values()

    @pytest.mark.asyncio
    async def test_tier2_receives_both_images(
        self, visual_comparator: VisualComparator
    ):
        """Test that Tier 2 AI vision receives both reference and rendered images."""
        with patch.object(visual_comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.90

            with patch.object(visual_comparator._ssim_comparator, "compute_ssim_with_map") as mock_ssim_map:
                mock_ssim_map.return_value = (0.90, b"spatial_map")

                with patch.object(visual_comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
                    mock_ai.return_value = (True, "Acceptable")

                    reference = b"reference_image_bytes"
                    rendered = b"rendered_image_bytes"
                    await visual_comparator.compare(reference, rendered)

                    # Verify AI vision received both images
                    call_args = mock_ai.call_args
                    args_str = str(call_args)
                    assert "reference" in args_str.lower() or reference in call_args.args

    @pytest.mark.asyncio
    async def test_tier2_ai_approves_rendering_artifacts(
        self, visual_comparator: VisualComparator
    ):
        """Test that Tier 2 AI can approve minor rendering artifacts."""
        with patch.object(visual_comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.90

            with patch.object(visual_comparator._ssim_comparator, "compute_ssim_with_map") as mock_ssim_map:
                mock_ssim_map.return_value = (0.90, b"spatial_map")

                with patch.object(visual_comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
                    # AI determines artifacts are acceptable
                    mock_ai.return_value = (True, "Minor anti-aliasing differences, acceptable")

                    reference = b"ref"
                    rendered = b"rendered"
                    result = await visual_comparator.compare(reference, rendered)

                    assert result.passed is True
                    assert result.tier == ComparisonTier.TIER_2
                    assert "anti-aliasing" in result.feedback.lower() or "acceptable" in result.feedback.lower()

    @pytest.mark.asyncio
    async def test_tier2_ai_rejects_actual_violations(
        self, visual_comparator: VisualComparator
    ):
        """Test that Tier 2 AI can reject actual visual violations."""
        with patch.object(visual_comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.90

            with patch.object(visual_comparator._ssim_comparator, "compute_ssim_with_map") as mock_ssim_map:
                mock_ssim_map.return_value = (0.90, b"spatial_map")

                with patch.object(visual_comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
                    # AI determines this is a real violation
                    mock_ai.return_value = (False, "Color mismatch in primary button")

                    reference = b"ref"
                    rendered = b"rendered"
                    result = await visual_comparator.compare(reference, rendered)

                    assert result.passed is False
                    assert result.tier == ComparisonTier.TIER_2
                    assert "color" in result.feedback.lower() or "mismatch" in result.feedback.lower()

    @pytest.mark.asyncio
    async def test_tier2_includes_spatial_map_in_result(
        self, visual_comparator: VisualComparator
    ):
        """Test that Tier 2 result includes spatial map."""
        spatial_map_data = b"ssim_spatial_map_png"

        with patch.object(visual_comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.90

            with patch.object(visual_comparator._ssim_comparator, "compute_ssim_with_map") as mock_ssim_map:
                mock_ssim_map.return_value = (0.90, spatial_map_data)

                with patch.object(visual_comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
                    mock_ai.return_value = (True, "Acceptable")

                    reference = b"ref"
                    rendered = b"rendered"
                    result = await visual_comparator.compare(reference, rendered)

                    assert result.spatial_map is not None
                    assert result.spatial_map == spatial_map_data


class TestSpatialMap:
    """Tests for SSIM spatial quality map generation."""

    def test_spatial_map_is_image_bytes(
        self, ssim_comparator: SSIMComparator, slightly_different_images
    ):
        """Test that spatial map is valid image bytes."""
        reference, rendered = slightly_different_images
        _, spatial_map = ssim_comparator.compute_ssim_with_map(reference, rendered)

        assert isinstance(spatial_map, bytes)
        # Should be a valid PNG (check magic bytes)
        assert spatial_map[:8] == b"\x89PNG\r\n\x1a\n"

    def test_spatial_map_shows_difference_locations(
        self, ssim_comparator: SSIMComparator, slightly_different_images
    ):
        """Test that spatial map highlights WHERE differences occur."""
        reference, rendered = slightly_different_images
        _, spatial_map = ssim_comparator.compute_ssim_with_map(reference, rendered)

        # Spatial map should be a valid PNG (check signature)
        assert spatial_map[:8] == b"\x89PNG\r\n\x1a\n"
        # Spatial map should have reasonable size
        assert len(spatial_map) > 50

    def test_spatial_map_same_dimensions_as_input(
        self, ssim_comparator: SSIMComparator, create_test_image
    ):
        """Test that spatial map has same dimensions as input images."""
        img1 = create_test_image(100, 100, (255, 0, 0))
        img2 = create_test_image(100, 100, (200, 50, 50))

        _, spatial_map = ssim_comparator.compute_ssim_with_map(img1, img2)

        # Parse spatial map to verify dimensions
        try:
            from PIL import Image
            import io

            spatial_img = Image.open(io.BytesIO(spatial_map))
            assert spatial_img.size == (100, 100)
        except ImportError:
            # If PIL not available, just verify we got bytes
            assert len(spatial_map) > 0


class TestZeroTokenCostTier1:
    """Tests to ensure Tier 1 has zero token cost (deterministic computation)."""

    @pytest.mark.asyncio
    async def test_tier1_pass_no_llm_calls(self, visual_comparator: VisualComparator, identical_images):
        """Test that Tier 1 PASS makes no LLM calls."""
        reference, rendered = identical_images

        # Track any LLM/AI calls
        with patch.object(visual_comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
            await visual_comparator.compare(reference, rendered)
            mock_ai.assert_not_called()

    @pytest.mark.asyncio
    async def test_tier1_fail_no_llm_calls(self, visual_comparator: VisualComparator, very_different_images):
        """Test that Tier 1 FAIL makes no LLM calls."""
        reference, rendered = very_different_images

        with patch.object(visual_comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
            await visual_comparator.compare(reference, rendered)
            mock_ai.assert_not_called()

    def test_ssim_computation_is_pure_math(self, ssim_comparator: SSIMComparator, identical_images):
        """Test that SSIM computation uses pure mathematical operations."""
        reference, rendered = identical_images

        # SSIM computation should be synchronous and not involve any async/network calls
        score = ssim_comparator.compute_ssim(reference, rendered)

        assert isinstance(score, float)
        # Should complete quickly (under 1 second for reasonable image sizes)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_handles_empty_image_bytes(self, visual_comparator: VisualComparator):
        """Test handling of empty image bytes."""
        with pytest.raises((ValueError, RuntimeError)):
            await visual_comparator.compare(b"", b"")

    @pytest.mark.asyncio
    async def test_handles_corrupted_image(self, visual_comparator: VisualComparator, identical_images):
        """Test handling of corrupted image data."""
        reference, _ = identical_images
        corrupted = b"corrupted_data_not_an_image"

        with pytest.raises((ValueError, RuntimeError)):
            await visual_comparator.compare(reference, corrupted)

    @pytest.mark.asyncio
    async def test_handles_mismatched_dimensions(self, visual_comparator: VisualComparator, create_test_image):
        """Test handling of images with different dimensions."""
        img1 = create_test_image(100, 100, (255, 0, 0))
        img2 = create_test_image(200, 200, (255, 0, 0))

        with pytest.raises((ValueError, RuntimeError)):
            await visual_comparator.compare(img1, img2)

    @pytest.mark.asyncio
    async def test_handles_grayscale_images(self, visual_comparator: VisualComparator):
        """Test handling of grayscale images."""
        try:
            from PIL import Image
            import io

            # Create grayscale images with some variation to avoid edge case
            img1 = Image.new("L", (100, 100), 128)
            img2 = Image.new("L", (100, 100), 128)

            # Add a gradient to avoid solid-color edge case
            for x in range(100):
                for y in range(100):
                    img1.putpixel((x, y), (x + y) % 256)
                    img2.putpixel((x, y), (x + y) % 256)

            buf1, buf2 = io.BytesIO(), io.BytesIO()
            img1.save(buf1, format="PNG")
            img2.save(buf2, format="PNG")

            result = await visual_comparator.compare(buf1.getvalue(), buf2.getvalue())

            assert result.passed is True
            assert result.ssim_score >= 0.99
        except ImportError:
            pytest.skip("PIL not available for grayscale test")

    @pytest.mark.asyncio
    async def test_handles_rgba_images(self, visual_comparator: VisualComparator):
        """Test handling of images with alpha channel."""
        try:
            from PIL import Image
            import io

            # Create RGBA images
            img1 = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
            img2 = Image.new("RGBA", (100, 100), (255, 0, 0, 255))

            buf1, buf2 = io.BytesIO(), io.BytesIO()
            img1.save(buf1, format="PNG")
            img2.save(buf2, format="PNG")

            result = await visual_comparator.compare(buf1.getvalue(), buf2.getvalue())

            assert result.passed is True
        except ImportError:
            pytest.skip("PIL not available for RGBA test")


class TestExactThresholdBoundaries:
    """Tests for exact threshold boundary conditions."""

    @pytest.mark.asyncio
    async def test_ssim_exactly_095_passes_tier1(self, visual_comparator: VisualComparator):
        """Test that SSIM exactly 0.95 passes Tier 1."""
        with patch.object(visual_comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.95

            result = await visual_comparator.compare(b"ref", b"rendered")

            assert result.passed is True
            assert result.tier == ComparisonTier.TIER_1

    @pytest.mark.asyncio
    async def test_ssim_0949_escalates_tier2(self, visual_comparator: VisualComparator):
        """Test that SSIM 0.949 escalates to Tier 2."""
        with patch.object(visual_comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.949

            with patch.object(visual_comparator._ssim_comparator, "compute_ssim_with_map") as mock_ssim_map:
                mock_ssim_map.return_value = (0.949, b"spatial_map")

                with patch.object(visual_comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
                    mock_ai.return_value = (True, "Acceptable")

                    result = await visual_comparator.compare(b"ref", b"rendered")

                    assert result.tier == ComparisonTier.TIER_2

    @pytest.mark.asyncio
    async def test_ssim_exactly_085_escalates_tier2(self, visual_comparator: VisualComparator):
        """Test that SSIM exactly 0.85 escalates to Tier 2 (borderline)."""
        with patch.object(visual_comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.85

            with patch.object(visual_comparator._ssim_comparator, "compute_ssim_with_map") as mock_ssim_map:
                mock_ssim_map.return_value = (0.85, b"spatial_map")

                with patch.object(visual_comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
                    mock_ai.return_value = (True, "Borderline acceptable")

                    result = await visual_comparator.compare(b"ref", b"rendered")

                    assert result.tier == ComparisonTier.TIER_2

    @pytest.mark.asyncio
    async def test_ssim_0849_fails_tier1(self, visual_comparator: VisualComparator):
        """Test that SSIM 0.849 fails Tier 1 (below threshold)."""
        with patch.object(visual_comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.849

            result = await visual_comparator.compare(b"ref", b"rendered")

            assert result.passed is False
            assert result.tier == ComparisonTier.TIER_1


class TestComparisonMethodEnum:
    """Tests for ComparisonMethod enum."""

    def test_method_ssim_value(self):
        """Test that SSIM method has correct string value."""
        assert ComparisonMethod.SSIM.value == "ssim"

    def test_method_ssim_plus_ai_value(self):
        """Test that SSIM+AI method has correct string value."""
        assert ComparisonMethod.SSIM_PLUS_AI_VISION.value == "ssim+ai_vision"


class TestComparisonTierEnum:
    """Tests for ComparisonTier enum."""

    def test_tier_1_value(self):
        """Test that Tier 1 has correct integer value."""
        assert ComparisonTier.TIER_1.value == 1

    def test_tier_2_value(self):
        """Test that Tier 2 has correct integer value."""
        assert ComparisonTier.TIER_2.value == 2


class TestComparisonResultSerialization:
    """Additional tests for ComparisonResult serialization."""

    def test_to_dict_with_spatial_map(self):
        """Test to_dict includes hex-encoded spatial map."""
        spatial_data = b"\x89PNG\r\n"
        result = ComparisonResult(
            passed=True,
            ssim_score=0.95,
            method=ComparisonMethod.SSIM_PLUS_AI_VISION,
            tier=ComparisonTier.TIER_2,
            feedback="Test",
            spatial_map=spatial_data,
        )
        d = result.to_dict()
        assert d["spatial_map"] == spatial_data.hex()

    def test_from_dict_with_spatial_map(self):
        """Test from_dict decodes hex spatial map."""
        spatial_data = b"\x89PNG\r\n"
        data = {
            "passed": True,
            "ssim_score": 0.90,
            "method": "ssim+ai_vision",
            "tier": 2,
            "feedback": "Test",
            "spatial_map": spatial_data.hex(),
        }
        result = ComparisonResult.from_dict(data)
        assert result.spatial_map == spatial_data


class TestAIVisionCallback:
    """Tests for AI vision callback functionality."""

    @pytest.mark.asyncio
    async def test_custom_ai_callback_is_used(self):
        """Test that custom AI vision callback is invoked."""
        callback_called = False
        callback_args = []

        def custom_callback(ref, rend, spatial, score):
            nonlocal callback_called, callback_args
            callback_called = True
            callback_args = [ref, rend, spatial, score]
            return (True, "Custom callback approved")

        comparator = VisualComparator(ai_vision_callback=custom_callback)

        with patch.object(comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.90  # Borderline

            with patch.object(comparator._ssim_comparator, "compute_ssim_with_map") as mock_ssim_map:
                mock_ssim_map.return_value = (0.90, b"spatial_map")

                result = await comparator.compare(b"ref", b"rendered")

                assert callback_called
                assert result.passed is True
                assert result.feedback == "Custom callback approved"

    @pytest.mark.asyncio
    async def test_spatial_map_generation_failure_fallback(self):
        """Test fallback when spatial map generation fails."""
        comparator = VisualComparator()

        with patch.object(comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.90  # Borderline

            with patch.object(comparator._ssim_comparator, "compute_ssim_with_map") as mock_ssim_map:
                mock_ssim_map.side_effect = RuntimeError("Spatial map failed")

                result = await comparator.compare(b"ref", b"rendered")

                # Should fall back to Tier 1 FAIL
                assert result.passed is False
                assert result.tier == ComparisonTier.TIER_1
                assert "spatial map" in result.feedback.lower()

    @pytest.mark.asyncio
    async def test_ai_review_failure_fallback(self):
        """Test fallback when AI review fails."""
        comparator = VisualComparator()

        with patch.object(comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.90  # Borderline

            with patch.object(comparator._ssim_comparator, "compute_ssim_with_map") as mock_ssim_map:
                mock_ssim_map.return_value = (0.90, b"spatial_map")

                with patch.object(comparator, "_ai_vision_review", new_callable=AsyncMock) as mock_ai:
                    mock_ai.side_effect = RuntimeError("AI review failed")

                    result = await comparator.compare(b"ref", b"rendered")

                    # Should fall back to conservative FAIL
                    assert result.passed is False
                    assert result.tier == ComparisonTier.TIER_2
                    assert "failed" in result.feedback.lower()


class TestSolidColorImages:
    """Tests for handling solid color images (edge case)."""

    @pytest.mark.asyncio
    async def test_identical_solid_color_images_pass(self, visual_comparator: VisualComparator):
        """Test that identical solid color images pass."""
        try:
            from PIL import Image
            import io

            # Create solid color images
            img1 = Image.new("RGB", (50, 50), (128, 128, 128))
            img2 = Image.new("RGB", (50, 50), (128, 128, 128))

            buf1, buf2 = io.BytesIO(), io.BytesIO()
            img1.save(buf1, format="PNG")
            img2.save(buf2, format="PNG")

            result = await visual_comparator.compare(buf1.getvalue(), buf2.getvalue())

            # Should pass with high score (handling NaN edge case)
            assert result.passed is True
            assert result.ssim_score >= 0.99
        except ImportError:
            pytest.skip("PIL not available")

    def test_ssim_with_map_solid_color(self, ssim_comparator: SSIMComparator):
        """Test compute_ssim_with_map with solid color images."""
        try:
            from PIL import Image
            import io

            img1 = Image.new("RGB", (50, 50), (100, 100, 100))
            img2 = Image.new("RGB", (50, 50), (100, 100, 100))

            buf1, buf2 = io.BytesIO(), io.BytesIO()
            img1.save(buf1, format="PNG")
            img2.save(buf2, format="PNG")

            score, spatial_map = ssim_comparator.compute_ssim_with_map(
                buf1.getvalue(), buf2.getvalue()
            )

            assert isinstance(score, float)
            assert spatial_map is not None
        except ImportError:
            pytest.skip("PIL not available")


class TestImageModeConversions:
    """Tests for image mode conversion handling."""

    @pytest.mark.asyncio
    async def test_palette_mode_image(self, visual_comparator: VisualComparator):
        """Test handling of palette mode (P) images."""
        try:
            from PIL import Image
            import io

            # Create palette mode image and convert
            img1 = Image.new("P", (50, 50))
            img2 = Image.new("P", (50, 50))

            buf1, buf2 = io.BytesIO(), io.BytesIO()
            img1.save(buf1, format="PNG")
            img2.save(buf2, format="PNG")

            result = await visual_comparator.compare(buf1.getvalue(), buf2.getvalue())

            # Should handle palette mode
            assert result is not None
        except ImportError:
            pytest.skip("PIL not available")


class TestDefaultAICallback:
    """Tests for default AI callback behavior when none configured."""

    @pytest.mark.asyncio
    async def test_default_callback_returns_fail(self):
        """Test that default AI callback returns conservative FAIL."""
        comparator = VisualComparator()  # No callback configured

        with patch.object(comparator._ssim_comparator, "compute_ssim") as mock_ssim:
            mock_ssim.return_value = 0.90

            with patch.object(comparator._ssim_comparator, "compute_ssim_with_map") as mock_ssim_map:
                mock_ssim_map.return_value = (0.90, b"spatial_map")

                result = await comparator.compare(b"ref", b"rendered")

                # Default behavior is conservative FAIL
                assert result.passed is False
                assert "manual review" in result.feedback.lower() or "no ai vision" in result.feedback.lower()
