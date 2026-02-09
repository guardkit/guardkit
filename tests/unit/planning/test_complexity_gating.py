"""
Unit tests for complexity gating functionality.

Tests the architecture context token budget allocation based on task complexity.
These tests verify that:
- Low complexity tasks (1-3) receive no architecture context
- Medium complexity tasks (4-6) receive limited context
- High complexity tasks (7-8) receive more context
- Critical complexity tasks (9-10) receive maximum context
"""

import pytest
from guardkit.planning.complexity_gating import (
    ARCHITECTURE_CONTEXT_THRESHOLD,
    ARCH_TOKEN_BUDGETS,
    get_arch_token_budget,
)


class TestComplexityGatingConstants:
    """Test that required constants are defined with correct values."""

    def test_architecture_context_threshold_exists(self):
        """Verify ARCHITECTURE_CONTEXT_THRESHOLD constant is defined."""
        assert ARCHITECTURE_CONTEXT_THRESHOLD is not None

    def test_architecture_context_threshold_value(self):
        """Verify ARCHITECTURE_CONTEXT_THRESHOLD is set to 4."""
        assert ARCHITECTURE_CONTEXT_THRESHOLD == 4

    def test_arch_token_budgets_exists(self):
        """Verify ARCH_TOKEN_BUDGETS dictionary is defined."""
        assert ARCH_TOKEN_BUDGETS is not None
        assert isinstance(ARCH_TOKEN_BUDGETS, dict)

    def test_arch_token_budgets_has_all_tiers(self):
        """Verify ARCH_TOKEN_BUDGETS contains all required tiers."""
        required_tiers = ['low', 'medium', 'high', 'critical']
        for tier in required_tiers:
            assert tier in ARCH_TOKEN_BUDGETS, f"Missing tier: {tier}"

    def test_arch_token_budgets_tier_values(self):
        """Verify ARCH_TOKEN_BUDGETS has correct token values for each tier."""
        assert ARCH_TOKEN_BUDGETS['low'] == 0
        assert ARCH_TOKEN_BUDGETS['medium'] == 1000
        assert ARCH_TOKEN_BUDGETS['high'] == 2000
        assert ARCH_TOKEN_BUDGETS['critical'] == 3000


class TestGetArchTokenBudget:
    """Test the get_arch_token_budget function."""

    def test_function_exists(self):
        """Verify get_arch_token_budget function is callable."""
        assert callable(get_arch_token_budget)

    # Low complexity tests (1-3) - should return 0 tokens
    def test_complexity_1_returns_zero_tokens(self):
        """Complexity 1 should return 0 tokens (no architecture context)."""
        result = get_arch_token_budget(1)
        assert result == 0
        assert isinstance(result, int)

    def test_complexity_2_returns_zero_tokens(self):
        """Complexity 2 should return 0 tokens (no architecture context)."""
        result = get_arch_token_budget(2)
        assert result == 0
        assert isinstance(result, int)

    def test_complexity_3_returns_zero_tokens(self):
        """Complexity 3 should return 0 tokens (no architecture context)."""
        result = get_arch_token_budget(3)
        assert result == 0
        assert isinstance(result, int)

    # Medium complexity tests (4-6) - should return 1000 tokens
    def test_complexity_4_returns_1000_tokens(self):
        """Complexity 4 (threshold) should return 1000 tokens."""
        result = get_arch_token_budget(4)
        assert result == 1000
        assert isinstance(result, int)

    def test_complexity_5_returns_1000_tokens(self):
        """Complexity 5 should return 1000 tokens."""
        result = get_arch_token_budget(5)
        assert result == 1000
        assert isinstance(result, int)

    def test_complexity_6_returns_1000_tokens(self):
        """Complexity 6 should return 1000 tokens."""
        result = get_arch_token_budget(6)
        assert result == 1000
        assert isinstance(result, int)

    # High complexity tests (7-8) - should return 2000 tokens
    def test_complexity_7_returns_2000_tokens(self):
        """Complexity 7 should return 2000 tokens."""
        result = get_arch_token_budget(7)
        assert result == 2000
        assert isinstance(result, int)

    def test_complexity_8_returns_2000_tokens(self):
        """Complexity 8 should return 2000 tokens."""
        result = get_arch_token_budget(8)
        assert result == 2000
        assert isinstance(result, int)

    # Critical complexity tests (9-10) - should return 3000 tokens
    def test_complexity_9_returns_3000_tokens(self):
        """Complexity 9 should return 3000 tokens."""
        result = get_arch_token_budget(9)
        assert result == 3000
        assert isinstance(result, int)

    def test_complexity_10_returns_3000_tokens(self):
        """Complexity 10 should return 3000 tokens."""
        result = get_arch_token_budget(10)
        assert result == 3000
        assert isinstance(result, int)

    # Edge cases
    def test_complexity_zero_handles_gracefully(self):
        """Complexity 0 should handle gracefully (return 0 or clamp to 1)."""
        result = get_arch_token_budget(0)
        assert isinstance(result, int)
        assert result >= 0, "Token budget should not be negative"
        # Should either return 0 (treat as invalid/minimal) or same as complexity 1
        assert result in [0], "Complexity 0 should return 0 tokens"

    def test_complexity_11_handles_gracefully(self):
        """Complexity 11 (above max) should handle gracefully (clamp to 10)."""
        result = get_arch_token_budget(11)
        assert isinstance(result, int)
        # Should clamp to maximum complexity (10) behavior
        assert result == 3000, "Complexity above 10 should clamp to critical tier (3000 tokens)"

    def test_complexity_negative_handles_gracefully(self):
        """Negative complexity should handle gracefully."""
        result = get_arch_token_budget(-1)
        assert isinstance(result, int)
        assert result >= 0, "Token budget should not be negative"
        # Should treat as invalid and return minimum (0)
        assert result == 0, "Negative complexity should return 0 tokens"

    def test_complexity_very_high_clamps_to_maximum(self):
        """Very high complexity (>10) should clamp to maximum tier."""
        result = get_arch_token_budget(100)
        assert isinstance(result, int)
        assert result == 3000, "Complexity far above 10 should clamp to critical tier (3000 tokens)"

    # Type validation tests
    def test_return_type_is_integer(self):
        """Verify function always returns an integer."""
        for complexity in [1, 4, 7, 10]:
            result = get_arch_token_budget(complexity)
            assert isinstance(result, int), f"Expected int, got {type(result)} for complexity {complexity}"

    def test_accepts_integer_input(self):
        """Verify function accepts integer input."""
        # Should not raise any exception
        try:
            get_arch_token_budget(5)
        except TypeError:
            pytest.fail("Function should accept integer input")


class TestComplexityTierBoundaries:
    """Test tier boundary behavior to ensure no off-by-one errors."""

    def test_boundary_below_threshold(self):
        """Complexity just below threshold (3) should return 0 tokens."""
        assert get_arch_token_budget(3) == 0

    def test_boundary_at_threshold(self):
        """Complexity at threshold (4) should return 1000 tokens."""
        assert get_arch_token_budget(4) == 1000

    def test_boundary_medium_to_high(self):
        """Boundary between medium (6) and high (7) tiers."""
        assert get_arch_token_budget(6) == 1000
        assert get_arch_token_budget(7) == 2000

    def test_boundary_high_to_critical(self):
        """Boundary between high (8) and critical (9) tiers."""
        assert get_arch_token_budget(8) == 2000
        assert get_arch_token_budget(9) == 3000

    def test_tier_progression_is_monotonic(self):
        """Verify that token budgets increase monotonically with complexity."""
        budgets = [get_arch_token_budget(i) for i in range(1, 11)]
        for i in range(len(budgets) - 1):
            assert budgets[i] <= budgets[i + 1], \
                f"Token budget should not decrease: {budgets[i]} > {budgets[i + 1]}"


class TestComplexityGatingIntegration:
    """Integration tests for complexity gating behavior."""

    def test_low_complexity_gets_no_architecture_context(self):
        """Verify low complexity tasks (1-3) explicitly get 0 tokens."""
        for complexity in [1, 2, 3]:
            budget = get_arch_token_budget(complexity)
            assert budget == 0, \
                f"Low complexity task (complexity={complexity}) should get no architecture context"

    def test_medium_complexity_gets_limited_context(self):
        """Verify medium complexity tasks (4-6) get 1000 tokens."""
        for complexity in [4, 5, 6]:
            budget = get_arch_token_budget(complexity)
            assert budget == 1000, \
                f"Medium complexity task (complexity={complexity}) should get 1000 tokens"

    def test_high_complexity_gets_more_context(self):
        """Verify high complexity tasks (7-8) get 2000 tokens."""
        for complexity in [7, 8]:
            budget = get_arch_token_budget(complexity)
            assert budget == 2000, \
                f"High complexity task (complexity={complexity}) should get 2000 tokens"

    def test_critical_complexity_gets_maximum_context(self):
        """Verify critical complexity tasks (9-10) get 3000 tokens."""
        for complexity in [9, 10]:
            budget = get_arch_token_budget(complexity)
            assert budget == 3000, \
                f"Critical complexity task (complexity={complexity}) should get 3000 tokens"

    def test_threshold_semantic_meaning(self):
        """Verify the threshold value has semantic meaning."""
        # Below threshold: no architecture context
        assert get_arch_token_budget(ARCHITECTURE_CONTEXT_THRESHOLD - 1) == 0
        # At threshold: gets architecture context
        assert get_arch_token_budget(ARCHITECTURE_CONTEXT_THRESHOLD) > 0
