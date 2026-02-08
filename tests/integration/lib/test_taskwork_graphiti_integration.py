"""
Test Suite for Task-Work Graphiti Context Integration (Phase 1.7).

Tests the integration pattern specified in task-work.md Phase 1.7:
- load_task_context_sync() called with phase="plan"
- Task data dictionary matches expected shape
- Context injected into planning prompt
- Graceful degradation display patterns
- "Standard" budget allocation exercised via plan phase

References:
- TASK-FIX-GCI1: Wire Graphiti context into /task-work
- FEAT-GR-006: Job-Specific Context Retrieval

Coverage Target: >=85%
Test Count: 15+ tests
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================================
# 1. Phase 1.7 Calling Convention Tests (5 tests)
# ============================================================================

class TestPhase17CallingConvention:
    """Test the exact calling pattern used by Phase 1.7 in task-work.md."""

    def test_sync_wrapper_with_plan_phase(self):
        """Test load_task_context_sync called with phase='plan' as spec requires."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context_sync,
        )

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=False
        ):
            result = load_task_context_sync(
                task_id="TASK-FIX-GCI1",
                task_data={
                    "description": "Wire Graphiti context into task-work",
                    "tech_stack": "python",
                    "complexity": 5,
                    "feature_id": "FEAT-GR-006",
                },
                phase="plan"
            )

            assert result is None  # Disabled => None

    def test_task_data_shape_matches_spec(self):
        """Test task_data dict matches Phase 1.7 spec shape."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context_sync,
        )

        # The spec says task_data must include: description, tech_stack, complexity, feature_id
        task_data = {
            "description": "Implement user authentication API",
            "tech_stack": "python",
            "complexity": 7,
            "feature_id": "FEAT-AUTH-001",
        }

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=False
        ):
            # Should accept the dict shape without error
            result = load_task_context_sync(
                task_id="TASK-001",
                task_data=task_data,
                phase="plan"
            )
            assert result is None

    def test_task_data_with_none_feature_id(self):
        """Test task_data with feature_id=None (task not part of feature)."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context_sync,
        )

        task_data = {
            "description": "Fix typo in error message",
            "tech_stack": "python",
            "complexity": 2,
            "feature_id": None,
        }

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=False
        ):
            result = load_task_context_sync(
                task_id="TASK-002",
                task_data=task_data,
                phase="plan"
            )
            assert result is None

    def test_task_data_with_unknown_stack(self):
        """Test task_data with tech_stack='unknown' (default in spec)."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context_sync,
        )

        task_data = {
            "description": "Generic task",
            "tech_stack": "unknown",
            "complexity": 5,
            "feature_id": None,
        }

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=False
        ):
            result = load_task_context_sync(
                task_id="TASK-003",
                task_data=task_data,
                phase="plan"
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_plan_phase_triggers_standard_allocation(self):
        """Test that phase='plan' triggers standard (not AutoBuild) budget allocation."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.to_prompt.return_value = "## Feature Context\n- Auth module"
        mock_retriever.retrieve.return_value = mock_context

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=True
        ):
            with patch(
                'installer.core.commands.lib.graphiti_context_loader._get_retriever',
                return_value=mock_retriever
            ):
                await load_task_context(
                    task_id="TASK-001",
                    task_data={"description": "Test", "tech_stack": "python"},
                    phase="plan"
                )

                # Verify retrieve called with PLAN phase (triggers standard allocation)
                call_args = mock_retriever.retrieve.call_args
                phase_arg = call_args[0][1]
                assert phase_arg == TaskPhase.PLAN


# ============================================================================
# 2. Context Prompt Injection Tests (4 tests)
# ============================================================================

class TestContextPromptInjection:
    """Test that context is formatted correctly for Phase 2 prompt injection."""

    @pytest.mark.asyncio
    async def test_context_returns_markdown_for_prompt(self):
        """Test that loaded context is markdown suitable for prompt injection."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.to_prompt.return_value = (
            "## Feature Context\n"
            "- Auth module handles JWT validation\n\n"
            "## Similar Outcomes\n"
            "- TASK-042: Used bcrypt for password hashing (success)\n\n"
            "## Relevant Patterns\n"
            "- Repository Pattern for data access\n\n"
            "## Warnings\n"
            "- TASK-037: Avoid raw SQL queries (caused injection)\n"
        )
        mock_retriever.retrieve.return_value = mock_context

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=True
        ):
            with patch(
                'installer.core.commands.lib.graphiti_context_loader._get_retriever',
                return_value=mock_retriever
            ):
                result = await load_task_context(
                    task_id="TASK-001",
                    task_data={
                        "description": "Implement auth",
                        "tech_stack": "python",
                        "complexity": 6,
                        "feature_id": "FEAT-AUTH",
                    },
                    phase="plan"
                )

                assert isinstance(result, str)
                assert "Feature Context" in result
                assert "Similar Outcomes" in result
                assert "Relevant Patterns" in result
                assert "Warnings" in result

    @pytest.mark.asyncio
    async def test_context_can_be_concatenated_with_prompt(self):
        """Test that context string can be cleanly joined with a base prompt."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.to_prompt.return_value = "## Context\nSome knowledge graph data"
        mock_retriever.retrieve.return_value = mock_context

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=True
        ):
            with patch(
                'installer.core.commands.lib.graphiti_context_loader._get_retriever',
                return_value=mock_retriever
            ):
                context = await load_task_context(
                    task_id="TASK-001",
                    task_data={"description": "Test"},
                    phase="plan"
                )

                # Simulate Phase 2 prompt assembly
                base_prompt = "Design python implementation approach for TASK-001."
                full_prompt = f"{base_prompt}\n\n{context}"

                assert base_prompt in full_prompt
                assert "Context" in full_prompt
                assert isinstance(full_prompt, str)

    def test_get_context_for_prompt_with_none_returns_empty(self):
        """Test that None context produces empty string (no injection)."""
        from installer.core.commands.lib.graphiti_context_loader import (
            get_context_for_prompt,
        )

        result = get_context_for_prompt(None)
        assert result == ""

        # When context is empty, prompt should not have extraneous newlines
        base_prompt = "Design implementation."
        graphiti_section = result
        if graphiti_section:
            full = f"{base_prompt}\n\n{graphiti_section}"
        else:
            full = base_prompt

        assert full == "Design implementation."

    def test_get_context_for_prompt_preserves_string(self):
        """Test that pre-formatted string passes through unchanged."""
        from installer.core.commands.lib.graphiti_context_loader import (
            get_context_for_prompt,
        )

        formatted = "## Knowledge Graph Context\n- Pattern: Repository\n- Warning: Avoid raw SQL"
        result = get_context_for_prompt(formatted)
        assert result == formatted


# ============================================================================
# 3. Graceful Degradation Tests (4 tests)
# ============================================================================

class TestGracefulDegradation:
    """Test that task-work continues without Graphiti."""

    def test_disabled_via_env_var(self):
        """Test Graphiti disabled via GRAPHITI_ENABLED=false."""
        from installer.core.commands.lib.graphiti_context_loader import (
            is_graphiti_enabled,
            load_task_context_sync,
        )

        with patch.dict(os.environ, {'GRAPHITI_ENABLED': 'false'}):
            assert is_graphiti_enabled() is False

            result = load_task_context_sync(
                task_id="TASK-001",
                task_data={"description": "Test"},
                phase="plan"
            )
            assert result is None

    def test_disabled_when_modules_not_importable(self):
        """Test graceful fallback when guardkit.knowledge not importable."""
        from installer.core.commands.lib import graphiti_context_loader

        original = graphiti_context_loader.GRAPHITI_AVAILABLE

        try:
            graphiti_context_loader.GRAPHITI_AVAILABLE = False

            assert graphiti_context_loader.is_graphiti_enabled() is False

            result = graphiti_context_loader.load_task_context_sync(
                task_id="TASK-001",
                task_data={"description": "Test"},
                phase="plan"
            )
            assert result is None
        finally:
            graphiti_context_loader.GRAPHITI_AVAILABLE = original

    @pytest.mark.asyncio
    async def test_retriever_exception_returns_none(self):
        """Test that retriever exceptions don't propagate to task-work."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_retriever.retrieve.side_effect = ConnectionError("Neo4j unavailable")

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=True
        ):
            with patch(
                'installer.core.commands.lib.graphiti_context_loader._get_retriever',
                return_value=mock_retriever
            ):
                result = await load_task_context(
                    task_id="TASK-001",
                    task_data={"description": "Test"},
                    phase="plan"
                )

                # Must return None, not raise
                assert result is None

    @pytest.mark.asyncio
    async def test_retriever_timeout_returns_none(self):
        """Test that retriever timeouts don't block task-work."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_retriever.retrieve.side_effect = TimeoutError("Request timed out")

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=True
        ):
            with patch(
                'installer.core.commands.lib.graphiti_context_loader._get_retriever',
                return_value=mock_retriever
            ):
                result = await load_task_context(
                    task_id="TASK-001",
                    task_data={"description": "Test"},
                    phase="plan"
                )

                assert result is None


# ============================================================================
# 4. Standard Budget Allocation Tests (3 tests)
# ============================================================================

class TestStandardBudgetAllocation:
    """Test that standard allocation (6 categories) is exercised."""

    @pytest.mark.asyncio
    async def test_plan_phase_uses_standard_categories(self):
        """Test that plan phase retrieval covers standard 6 categories."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        # Realistic standard allocation response with all 6 categories
        mock_context.to_prompt.return_value = (
            "## Feature Context\n- Auth module\n\n"
            "## Similar Outcomes\n- TASK-042 succeeded\n\n"
            "## Relevant Patterns\n- Repository pattern\n\n"
            "## Architecture Context\n- Clean architecture\n\n"
            "## Warnings\n- Avoid raw SQL\n\n"
            "## Domain Knowledge\n- JWT tokens expire\n"
        )
        mock_context.budget_used = 2800
        mock_context.budget_total = 4000
        mock_retriever.retrieve.return_value = mock_context

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=True
        ):
            with patch(
                'installer.core.commands.lib.graphiti_context_loader._get_retriever',
                return_value=mock_retriever
            ):
                result = await load_task_context(
                    task_id="TASK-001",
                    task_data={
                        "description": "Implement user auth",
                        "tech_stack": "python",
                        "complexity": 6,
                        "feature_id": "FEAT-AUTH",
                    },
                    phase="plan"
                )

                assert "Feature Context" in result
                assert "Similar Outcomes" in result
                assert "Relevant Patterns" in result
                assert "Architecture Context" in result
                assert "Warnings" in result
                assert "Domain Knowledge" in result

    @pytest.mark.asyncio
    async def test_context_is_non_empty_when_data_exists(self):
        """Test that context has content when knowledge graph has data."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.to_prompt.return_value = "## Context\nReal data here"
        mock_retriever.retrieve.return_value = mock_context

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=True
        ):
            with patch(
                'installer.core.commands.lib.graphiti_context_loader._get_retriever',
                return_value=mock_retriever
            ):
                result = await load_task_context(
                    task_id="TASK-001",
                    task_data={"description": "Test"},
                    phase="plan"
                )

                assert result is not None
                assert len(result) > 0

    @pytest.mark.asyncio
    async def test_context_empty_when_graph_empty(self):
        """Test that empty knowledge graph still returns valid string."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.to_prompt.return_value = ""  # Empty graph
        mock_retriever.retrieve.return_value = mock_context

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=True
        ):
            with patch(
                'installer.core.commands.lib.graphiti_context_loader._get_retriever',
                return_value=mock_retriever
            ):
                result = await load_task_context(
                    task_id="TASK-001",
                    task_data={"description": "Test"},
                    phase="plan"
                )

                # Empty string is valid - indicates no relevant context
                assert isinstance(result, str)
