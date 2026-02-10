"""Tests for coach_context_builder.py module.

TDD RED phase tests for TASK-SC-004. These tests verify the budget-gated
coach prompt assembly function that bridges system overview and impact
analysis into a single context string for the AutoBuild coach prompt.

Coverage Target: >=80%
Test Count: 9+ tests

Key behaviors verified:
- Returns "" for complexity 1-3 (budget = 0)
- Returns condensed overview for complexity 4-6
- Returns overview + impact for complexity 7+
- Total output respects token budget
- Gracefully returns "" when Graphiti unavailable
- Gracefully returns "" when no architecture context
- Returns overview-only when impact analysis fails
- Handles default complexity when key missing
- Uses correct token budget from get_arch_token_budget()
"""

import pytest
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# These imports will work once implementation exists
from guardkit.planning.coach_context_builder import (
    build_coach_context,
    _estimate_tokens,
    _get_impact_section,
)


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock GraphitiClient instance."""
    client = MagicMock()
    client.enabled = True
    return client


@pytest.fixture
def mock_client_disabled() -> MagicMock:
    """Create a mock GraphitiClient with enabled=False."""
    client = MagicMock()
    client.enabled = False
    return client


@pytest.fixture
def sample_overview_ok() -> Dict[str, Any]:
    """Create sample overview with ok status."""
    return {
        "status": "ok",
        "system": {"name": "E-Commerce Platform", "methodology": "DDD"},
        "components": [
            {"name": "Order Management", "description": "Handles order lifecycle"},
            {"name": "Inventory Service", "description": "Manages stock levels"},
        ],
        "decisions": [
            {"adr_id": "ADR-SP-001", "title": "Use Event Sourcing", "status": "accepted"}
        ],
        "concerns": [{"name": "Observability", "description": "Unified logging"}],
    }


@pytest.fixture
def sample_overview_no_context() -> Dict[str, Any]:
    """Create sample overview with no_context status."""
    return {"status": "no_context"}


# =========================================================================
# 1. SIMPLE TASK TESTS (Complexity 1-3)
# =========================================================================


class TestBuildCoachContextSimpleTasks:
    """Tests for build_coach_context with simple tasks (complexity 1-3)."""

    @pytest.mark.asyncio
    async def test_build_coach_context_simple_task_returns_empty(
        self, mock_client: MagicMock
    ):
        """Test build_coach_context returns empty string for complexity 2."""
        task = {"complexity": 2, "title": "Fix typo in README"}

        result = await build_coach_context(task, mock_client, "test-project")

        assert result == ""

    @pytest.mark.asyncio
    async def test_build_coach_context_complexity_1_returns_empty(
        self, mock_client: MagicMock
    ):
        """Test build_coach_context returns empty string for complexity 1."""
        task = {"complexity": 1, "title": "Update comment"}

        result = await build_coach_context(task, mock_client, "test-project")

        assert result == ""

    @pytest.mark.asyncio
    async def test_build_coach_context_complexity_3_returns_empty(
        self, mock_client: MagicMock
    ):
        """Test build_coach_context returns empty string for complexity 3."""
        task = {"complexity": 3, "title": "Simple refactor"}

        result = await build_coach_context(task, mock_client, "test-project")

        assert result == ""


# =========================================================================
# 2. MEDIUM COMPLEXITY TESTS (Complexity 4-6)
# =========================================================================


class TestBuildCoachContextMediumComplexity:
    """Tests for build_coach_context with medium complexity tasks (4-6)."""

    @pytest.mark.asyncio
    async def test_build_coach_context_medium_complexity_returns_overview(
        self, mock_client: MagicMock, sample_overview_ok: Dict
    ):
        """Test build_coach_context returns overview only for complexity 5."""
        task = {"complexity": 5, "title": "Add new endpoint"}

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            mock_sp = MagicMock()
            MockSP.return_value = mock_sp
            mock_sp._available = True

            with patch(
                "guardkit.planning.coach_context_builder.get_system_overview",
                new_callable=AsyncMock
            ) as mock_get_overview:
                mock_get_overview.return_value = sample_overview_ok

                result = await build_coach_context(task, mock_client, "test-project")

        # Should contain architecture context header
        assert "## Architecture Context" in result
        # Should contain methodology from overview
        assert "DDD" in result or "Methodology" in result

    @pytest.mark.asyncio
    async def test_build_coach_context_complexity_4_returns_overview(
        self, mock_client: MagicMock, sample_overview_ok: Dict
    ):
        """Test build_coach_context returns overview for complexity 4."""
        task = {"complexity": 4, "title": "Add validation"}

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            mock_sp = MagicMock()
            MockSP.return_value = mock_sp
            mock_sp._available = True

            with patch(
                "guardkit.planning.coach_context_builder.get_system_overview",
                new_callable=AsyncMock
            ) as mock_get_overview:
                mock_get_overview.return_value = sample_overview_ok

                result = await build_coach_context(task, mock_client, "test-project")

        assert "## Architecture Context" in result
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_build_coach_context_complexity_6_returns_overview(
        self, mock_client: MagicMock, sample_overview_ok: Dict
    ):
        """Test build_coach_context returns overview for complexity 6."""
        task = {"complexity": 6, "title": "Implement service"}

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            mock_sp = MagicMock()
            MockSP.return_value = mock_sp
            mock_sp._available = True

            with patch(
                "guardkit.planning.coach_context_builder.get_system_overview",
                new_callable=AsyncMock
            ) as mock_get_overview:
                mock_get_overview.return_value = sample_overview_ok

                result = await build_coach_context(task, mock_client, "test-project")

        assert "## Architecture Context" in result


# =========================================================================
# 3. HIGH COMPLEXITY TESTS (Complexity 7+)
# =========================================================================


class TestBuildCoachContextHighComplexity:
    """Tests for build_coach_context with high complexity tasks (7+)."""

    @pytest.mark.asyncio
    async def test_build_coach_context_high_complexity_includes_impact(
        self, mock_client: MagicMock, sample_overview_ok: Dict
    ):
        """Test build_coach_context returns overview + impact for complexity 7."""
        task = {"complexity": 7, "title": "Major refactoring"}

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            mock_sp = MagicMock()
            MockSP.return_value = mock_sp
            mock_sp._available = True

            with patch(
                "guardkit.planning.coach_context_builder.get_system_overview",
                new_callable=AsyncMock
            ) as mock_get_overview:
                mock_get_overview.return_value = sample_overview_ok

                # Patch _get_impact_section helper instead of the dynamic import
                with patch(
                    "guardkit.planning.coach_context_builder._get_impact_section",
                    new_callable=AsyncMock
                ) as mock_get_impact:
                    mock_get_impact.return_value = "Affected: Order Management, Inventory"

                    result = await build_coach_context(task, mock_client, "test-project")

        # Should contain both architecture context and impact
        assert "## Architecture Context" in result
        # Should contain impact section for high complexity
        assert "## Task Impact" in result

    @pytest.mark.asyncio
    async def test_build_coach_context_critical_complexity_larger_budget(
        self, mock_client: MagicMock, sample_overview_ok: Dict
    ):
        """Test build_coach_context uses larger budget for complexity 9."""
        task = {"complexity": 9, "title": "System redesign"}

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            mock_sp = MagicMock()
            MockSP.return_value = mock_sp
            mock_sp._available = True

            with patch(
                "guardkit.planning.coach_context_builder.get_system_overview",
                new_callable=AsyncMock
            ) as mock_get_overview:
                mock_get_overview.return_value = sample_overview_ok

                # Patch _get_impact_section helper instead of the dynamic import
                with patch(
                    "guardkit.planning.coach_context_builder._get_impact_section",
                    new_callable=AsyncMock
                ) as mock_get_impact:
                    mock_get_impact.return_value = "Full impact analysis content"

                    result = await build_coach_context(task, mock_client, "test-project")

        # Critical complexity should include impact
        assert "## Architecture Context" in result
        assert len(result) > 50  # Should have substantial content


# =========================================================================
# 4. GRACEFUL DEGRADATION TESTS
# =========================================================================


class TestBuildCoachContextGracefulDegradation:
    """Tests for graceful degradation when Graphiti or context unavailable."""

    @pytest.mark.asyncio
    async def test_build_coach_context_graphiti_unavailable_returns_empty(
        self, mock_client_disabled: MagicMock
    ):
        """Test build_coach_context returns empty string when Graphiti disabled."""
        task = {"complexity": 7, "title": "Major task"}

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            mock_sp = MagicMock()
            MockSP.return_value = mock_sp
            mock_sp._available = False

            result = await build_coach_context(task, mock_client_disabled, "test-project")

        assert result == ""

    @pytest.mark.asyncio
    async def test_build_coach_context_no_arch_returns_empty(
        self, mock_client: MagicMock, sample_overview_no_context: Dict
    ):
        """Test build_coach_context returns empty string when no architecture context."""
        task = {"complexity": 7, "title": "Major task"}

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            mock_sp = MagicMock()
            MockSP.return_value = mock_sp
            mock_sp._available = True

            with patch(
                "guardkit.planning.coach_context_builder.get_system_overview",
                new_callable=AsyncMock
            ) as mock_get_overview:
                mock_get_overview.return_value = sample_overview_no_context

                result = await build_coach_context(task, mock_client, "test-project")

        assert result == ""

    @pytest.mark.asyncio
    async def test_build_coach_context_impact_fails_returns_overview_only(
        self, mock_client: MagicMock, sample_overview_ok: Dict
    ):
        """Test build_coach_context returns overview only when impact analysis fails."""
        task = {"complexity": 8, "title": "Complex refactor"}

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            mock_sp = MagicMock()
            MockSP.return_value = mock_sp
            mock_sp._available = True

            with patch(
                "guardkit.planning.coach_context_builder.get_system_overview",
                new_callable=AsyncMock
            ) as mock_get_overview:
                mock_get_overview.return_value = sample_overview_ok

                # Patch _get_impact_section to return empty (simulates failure)
                with patch(
                    "guardkit.planning.coach_context_builder._get_impact_section",
                    new_callable=AsyncMock
                ) as mock_get_impact:
                    # Return empty string to simulate failure
                    mock_get_impact.return_value = ""

                    result = await build_coach_context(task, mock_client, "test-project")

        # Should still contain architecture context
        assert "## Architecture Context" in result
        # Should NOT contain impact section since it failed
        assert "## Task Impact" not in result

    @pytest.mark.asyncio
    async def test_build_coach_context_exception_returns_empty(
        self, mock_client: MagicMock
    ):
        """Test build_coach_context returns empty string on unexpected exception."""
        task = {"complexity": 7, "title": "Major task"}

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            MockSP.side_effect = Exception("Unexpected error")

            result = await build_coach_context(task, mock_client, "test-project")

        assert result == ""


# =========================================================================
# 5. TOKEN BUDGET TESTS
# =========================================================================


class TestBuildCoachContextTokenBudget:
    """Tests for token budget enforcement."""

    @pytest.mark.asyncio
    async def test_build_coach_context_respects_token_budget(
        self, mock_client: MagicMock
    ):
        """Test build_coach_context output respects token budget from get_arch_token_budget."""
        task = {"complexity": 5, "title": "Medium task"}

        # Create large overview that would exceed budget if not truncated
        large_overview = {
            "status": "ok",
            "system": {"methodology": "Very long methodology name " * 50},
            "components": [
                {"name": f"Component {i}", "description": "Long description " * 100}
                for i in range(20)
            ],
            "decisions": [],
            "concerns": [],
        }

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            mock_sp = MagicMock()
            MockSP.return_value = mock_sp
            mock_sp._available = True

            with patch(
                "guardkit.planning.coach_context_builder.get_system_overview",
                new_callable=AsyncMock
            ) as mock_get_overview:
                mock_get_overview.return_value = large_overview

                result = await build_coach_context(task, mock_client, "test-project")

        # Verify output is within budget (complexity 5 → 1000 tokens)
        estimated_tokens = _estimate_tokens(result)
        assert estimated_tokens <= 1000 + 50  # Small buffer for headers


# =========================================================================
# 6. DEFAULT COMPLEXITY TESTS
# =========================================================================


class TestBuildCoachContextDefaultComplexity:
    """Tests for default complexity handling."""

    @pytest.mark.asyncio
    async def test_build_coach_context_default_complexity(
        self, mock_client: MagicMock, sample_overview_ok: Dict
    ):
        """Test build_coach_context uses default complexity 5 when key missing."""
        task = {"title": "Task without complexity key"}  # No complexity key

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            mock_sp = MagicMock()
            MockSP.return_value = mock_sp
            mock_sp._available = True

            with patch(
                "guardkit.planning.coach_context_builder.get_system_overview",
                new_callable=AsyncMock
            ) as mock_get_overview:
                mock_get_overview.return_value = sample_overview_ok

                result = await build_coach_context(task, mock_client, "test-project")

        # Default complexity 5 should return overview (not empty)
        assert "## Architecture Context" in result


# =========================================================================
# 7. ESTIMATE_TOKENS TESTS
# =========================================================================


class TestEstimateTokens:
    """Tests for _estimate_tokens helper function."""

    def test_estimate_tokens_simple_text(self):
        """Test _estimate_tokens with simple text."""
        text = "This is a simple test with ten words total here now."

        tokens = _estimate_tokens(text)

        # 10 words * 1.3 ≈ 13 tokens
        assert tokens >= 10
        assert tokens <= 15

    def test_estimate_tokens_empty_string(self):
        """Test _estimate_tokens returns 0 for empty string."""
        tokens = _estimate_tokens("")

        assert tokens == 0

    def test_estimate_tokens_long_text(self):
        """Test _estimate_tokens scales with text length."""
        short_text = "Short text"
        long_text = "This is a much longer piece of text with many more words " * 10

        short_tokens = _estimate_tokens(short_text)
        long_tokens = _estimate_tokens(long_text)

        assert long_tokens > short_tokens * 5


# =========================================================================
# 8. INTEGRATION TESTS
# =========================================================================


# =========================================================================
# 9. _GET_IMPACT_SECTION TESTS
# =========================================================================


class TestGetImpactSection:
    """Tests for _get_impact_section helper function."""

    @pytest.mark.asyncio
    async def test_get_impact_section_import_error_returns_empty(self):
        """Test _get_impact_section returns empty string when impact_analysis module missing."""
        mock_sp = MagicMock()
        mock_sp._available = True
        task = {"complexity": 7, "title": "Test task", "description": "Test description"}

        # Since impact_analysis module doesn't exist, it will hit ImportError path
        result = await _get_impact_section(mock_sp, task, max_tokens=500)

        # Should return empty string due to ImportError
        assert result == ""

    @pytest.mark.asyncio
    async def test_get_impact_section_handles_exception(self):
        """Test _get_impact_section returns empty on exception."""
        mock_sp = MagicMock()
        task = {"complexity": 7, "title": "Test task"}

        # Patch the import to simulate an exception
        with patch.dict("sys.modules", {"guardkit.planning.impact_analysis": None}):
            result = await _get_impact_section(mock_sp, task, max_tokens=500)

        assert result == ""


# =========================================================================
# 10. INTEGRATION TESTS
# =========================================================================


class TestIntegration:
    """Integration tests for the full workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow_medium_complexity(
        self, mock_client: MagicMock, sample_overview_ok: Dict
    ):
        """Test full workflow for medium complexity task."""
        task = {"complexity": 5, "title": "Add new feature"}

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            mock_sp = MagicMock()
            MockSP.return_value = mock_sp
            mock_sp._available = True

            with patch(
                "guardkit.planning.coach_context_builder.get_system_overview",
                new_callable=AsyncMock
            ) as mock_get_overview:
                mock_get_overview.return_value = sample_overview_ok

                result = await build_coach_context(task, mock_client, "test-project")

        # Verify structure
        assert "## Architecture Context" in result
        assert len(result) > 0

        # Verify token budget
        tokens = _estimate_tokens(result)
        assert tokens <= 1000 + 50  # Medium budget + buffer

    @pytest.mark.asyncio
    async def test_full_workflow_high_complexity_with_impact(
        self, mock_client: MagicMock, sample_overview_ok: Dict
    ):
        """Test full workflow for high complexity task with impact analysis."""
        task = {"complexity": 8, "title": "Complex refactoring"}

        with patch(
            "guardkit.planning.coach_context_builder.SystemPlanGraphiti"
        ) as MockSP:
            mock_sp = MagicMock()
            MockSP.return_value = mock_sp
            mock_sp._available = True

            with patch(
                "guardkit.planning.coach_context_builder.get_system_overview",
                new_callable=AsyncMock
            ) as mock_get_overview:
                mock_get_overview.return_value = sample_overview_ok

                # Patch _get_impact_section helper
                with patch(
                    "guardkit.planning.coach_context_builder._get_impact_section",
                    new_callable=AsyncMock
                ) as mock_get_impact:
                    mock_get_impact.return_value = "Affected: Order Management, Inventory"

                    result = await build_coach_context(task, mock_client, "test-project")

        # Should have both sections
        assert "## Architecture Context" in result
        assert "## Task Impact" in result

        # Verify token budget (complexity 8 → 2000 tokens)
        tokens = _estimate_tokens(result)
        assert tokens <= 2000 + 50
