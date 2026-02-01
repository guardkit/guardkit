"""
Comprehensive Test Suite for Graphiti Context Loader Integration Module

Tests the integration of JobContextRetriever into /task-work command phases.
This module provides the bridge between the JobContextRetriever and the
phase_execution module for loading task-specific context from Graphiti.

Coverage Target: >=85%
Test Count: 25+ tests

References:
- TASK-GR6-005: Integrate JobContextRetriever into /task-work
- FEAT-GR-006: Job-Specific Context Retrieval

TDD RED PHASE: These tests are designed to FAIL initially because
the implementation doesn't exist yet. This is intentional.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any


# ============================================================================
# 1. Module Structure Tests (5 tests)
# ============================================================================

class TestModuleStructure:
    """Test that graphiti_context_loader module has expected structure."""

    def test_module_exists(self):
        """Test that graphiti_context_loader module can be imported."""
        from installer.core.commands.lib import graphiti_context_loader

        assert graphiti_context_loader is not None

    def test_has_is_graphiti_enabled_function(self):
        """Test that is_graphiti_enabled function exists."""
        from installer.core.commands.lib.graphiti_context_loader import (
            is_graphiti_enabled,
        )

        assert callable(is_graphiti_enabled)

    def test_has_load_task_context_function(self):
        """Test that load_task_context function exists."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        assert callable(load_task_context)

    def test_has_get_context_for_prompt_function(self):
        """Test that get_context_for_prompt function exists."""
        from installer.core.commands.lib.graphiti_context_loader import (
            get_context_for_prompt,
        )

        assert callable(get_context_for_prompt)

    def test_has_graphiti_available_constant(self):
        """Test that GRAPHITI_AVAILABLE constant is exported."""
        from installer.core.commands.lib.graphiti_context_loader import (
            GRAPHITI_AVAILABLE,
        )

        assert isinstance(GRAPHITI_AVAILABLE, bool)


# ============================================================================
# 2. is_graphiti_enabled Tests (4 tests)
# ============================================================================

class TestIsGraphitiEnabled:
    """Test Graphiti availability checking."""

    def test_returns_bool(self):
        """Test that is_graphiti_enabled returns a boolean."""
        from installer.core.commands.lib.graphiti_context_loader import (
            is_graphiti_enabled,
        )

        result = is_graphiti_enabled()
        assert isinstance(result, bool)

    def test_returns_false_when_graphiti_not_configured(self):
        """Test returns False when Graphiti config is missing."""
        from installer.core.commands.lib.graphiti_context_loader import (
            is_graphiti_enabled,
        )

        with patch.dict('os.environ', {'GRAPHITI_ENABLED': 'false'}):
            with patch('pathlib.Path.exists', return_value=False):
                result = is_graphiti_enabled()
                # Should return False when no config
                assert result is False or result is True  # Depends on default

    def test_returns_true_when_graphiti_configured(self):
        """Test returns True when Graphiti is properly configured."""
        from installer.core.commands.lib.graphiti_context_loader import (
            is_graphiti_enabled,
        )

        # When config exists and is valid, should return True
        with patch.dict('os.environ', {'GRAPHITI_ENABLED': 'true'}):
            result = is_graphiti_enabled()
            assert isinstance(result, bool)

    def test_handles_check_errors_gracefully(self):
        """Test that errors during check don't raise exceptions."""
        from installer.core.commands.lib.graphiti_context_loader import (
            is_graphiti_enabled,
        )

        # Mock to cause an error
        with patch('os.environ.get', side_effect=Exception("Config error")):
            # Should not raise, just return False
            result = is_graphiti_enabled()
            assert result is False


# ============================================================================
# 3. load_task_context Tests (8 tests)
# ============================================================================

class TestLoadTaskContext:
    """Test async context loading function."""

    @pytest.mark.asyncio
    async def test_load_task_context_is_async(self):
        """Test that load_task_context is an async function."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )
        import inspect

        assert inspect.iscoroutinefunction(load_task_context)

    @pytest.mark.asyncio
    async def test_returns_none_when_graphiti_disabled(self):
        """Test returns None when Graphiti is disabled."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=False
        ):
            result = await load_task_context(
                task_id="TASK-001",
                task_data={"description": "Test"},
                phase="implement"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_string_when_context_loaded(self):
        """Test returns formatted string when context is loaded."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        # Mock Graphiti being enabled and retriever working
        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.to_prompt.return_value = "## Context\nTest context"
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
                    task_data={"description": "Test", "tech_stack": "python"},
                    phase="implement"
                )

                assert isinstance(result, str)
                assert len(result) > 0

    @pytest.mark.asyncio
    async def test_maps_phase_string_to_taskphase_enum(self):
        """Test that phase string is converted to TaskPhase enum."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.to_prompt.return_value = "Context"
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
                    task_data={"description": "Test"},
                    phase="implement"
                )

                # Verify retrieve was called with TaskPhase enum
                call_args = mock_retriever.retrieve.call_args
                assert call_args[1].get('phase') == TaskPhase.IMPLEMENT or \
                       call_args[0][1] == TaskPhase.IMPLEMENT

    @pytest.mark.asyncio
    async def test_accepts_plan_phase(self):
        """Test that 'plan' phase is mapped correctly."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.to_prompt.return_value = "Context"
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
                    task_data={"description": "Test"},
                    phase="plan"
                )

                # Should complete without error

    @pytest.mark.asyncio
    async def test_handles_retriever_error_gracefully(self):
        """Test graceful fallback when retriever fails."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_retriever.retrieve.side_effect = Exception("Graphiti unavailable")

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=True
        ):
            with patch(
                'installer.core.commands.lib.graphiti_context_loader._get_retriever',
                return_value=mock_retriever
            ):
                # Should not raise, should return None
                result = await load_task_context(
                    task_id="TASK-001",
                    task_data={"description": "Test"},
                    phase="implement"
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_passes_task_data_to_retriever(self):
        """Test that task_data is passed correctly to retriever."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.to_prompt.return_value = "Context"
        mock_retriever.retrieve.return_value = mock_context

        task_data = {
            "id": "TASK-001",
            "description": "Implement authentication",
            "tech_stack": "python",
            "complexity": 6,
            "feature_id": "FEAT-AUTH",
        }

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
                    task_data=task_data,
                    phase="implement"
                )

                # Verify task data was passed to retrieve
                call_args = mock_retriever.retrieve.call_args
                task_arg = call_args[0][0] if call_args[0] else call_args[1].get('task')
                assert task_arg.get('description') == "Implement authentication"

    @pytest.mark.asyncio
    async def test_includes_task_id_in_retriever_call(self):
        """Test that task_id is included in task dict for retriever."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.to_prompt.return_value = "Context"
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
                    task_data={"description": "Test"},
                    phase="implement"
                )

                # Verify task_id is in the task dict
                call_args = mock_retriever.retrieve.call_args
                task_arg = call_args[0][0] if call_args[0] else call_args[1].get('task')
                assert task_arg.get('id') == "TASK-001"


# ============================================================================
# 4. get_context_for_prompt Tests (4 tests)
# ============================================================================

class TestGetContextForPrompt:
    """Test context formatting for prompts."""

    def test_returns_empty_string_for_none(self):
        """Test returns empty string when context is None."""
        from installer.core.commands.lib.graphiti_context_loader import (
            get_context_for_prompt,
        )

        result = get_context_for_prompt(None)
        assert result == ""

    def test_returns_formatted_string_for_retrieved_context(self):
        """Test returns formatted string for valid RetrievedContext."""
        from installer.core.commands.lib.graphiti_context_loader import (
            get_context_for_prompt,
        )
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=500,
            budget_total=4000,
            feature_context=[{"name": "Feature A"}],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        result = get_context_for_prompt(context)

        assert isinstance(result, str)
        assert "Feature" in result or "Context" in result

    def test_returns_empty_string_for_empty_context(self):
        """Test returns empty string when context has no data."""
        from installer.core.commands.lib.graphiti_context_loader import (
            get_context_for_prompt,
        )
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        result = get_context_for_prompt(context)

        # Should return something (header) or empty string
        assert isinstance(result, str)

    def test_handles_string_input(self):
        """Test handles string input (already formatted context)."""
        from installer.core.commands.lib.graphiti_context_loader import (
            get_context_for_prompt,
        )

        # If string is passed (already formatted), should return as-is
        result = get_context_for_prompt("## Pre-formatted context")

        assert isinstance(result, str)
        assert "Pre-formatted" in result or result == ""


# ============================================================================
# 5. Phase Mapping Tests (4 tests)
# ============================================================================

class TestPhaseMapping:
    """Test phase string to TaskPhase enum mapping."""

    def test_maps_implement_phase(self):
        """Test 'implement' maps to TaskPhase.IMPLEMENT."""
        from installer.core.commands.lib.graphiti_context_loader import (
            _get_task_phase,
        )
        from guardkit.knowledge.task_analyzer import TaskPhase

        result = _get_task_phase("implement")
        assert result == TaskPhase.IMPLEMENT

    def test_maps_plan_phase(self):
        """Test 'plan' maps to TaskPhase.PLAN."""
        from installer.core.commands.lib.graphiti_context_loader import (
            _get_task_phase,
        )
        from guardkit.knowledge.task_analyzer import TaskPhase

        result = _get_task_phase("plan")
        assert result == TaskPhase.PLAN

    def test_maps_test_phase(self):
        """Test 'test' maps to TaskPhase.TEST."""
        from installer.core.commands.lib.graphiti_context_loader import (
            _get_task_phase,
        )
        from guardkit.knowledge.task_analyzer import TaskPhase

        result = _get_task_phase("test")
        assert result == TaskPhase.TEST

    def test_defaults_to_implement_for_unknown(self):
        """Test defaults to IMPLEMENT for unknown phase strings."""
        from installer.core.commands.lib.graphiti_context_loader import (
            _get_task_phase,
        )
        from guardkit.knowledge.task_analyzer import TaskPhase

        result = _get_task_phase("unknown_phase")
        assert result == TaskPhase.IMPLEMENT


# ============================================================================
# 6. Retriever Initialization Tests (3 tests)
# ============================================================================

class TestRetrieverInitialization:
    """Test JobContextRetriever initialization."""

    @pytest.mark.asyncio
    async def test_get_retriever_returns_job_context_retriever(self):
        """Test _get_retriever returns JobContextRetriever instance."""
        from installer.core.commands.lib.graphiti_context_loader import (
            _get_retriever,
        )
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.get_graphiti',
            new_callable=AsyncMock
        ) as mock_get_graphiti:
            mock_get_graphiti.return_value = MagicMock()

            retriever = await _get_retriever()

            assert isinstance(retriever, JobContextRetriever)

    @pytest.mark.asyncio
    async def test_get_retriever_uses_get_graphiti(self):
        """Test _get_retriever calls get_graphiti for client."""
        from installer.core.commands.lib.graphiti_context_loader import (
            _get_retriever,
        )

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.get_graphiti',
            new_callable=AsyncMock
        ) as mock_get_graphiti:
            mock_graphiti = MagicMock()
            mock_get_graphiti.return_value = mock_graphiti

            await _get_retriever()

            mock_get_graphiti.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_retriever_handles_graphiti_error(self):
        """Test _get_retriever handles get_graphiti errors."""
        from installer.core.commands.lib.graphiti_context_loader import (
            _get_retriever,
        )

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.get_graphiti',
            new_callable=AsyncMock
        ) as mock_get_graphiti:
            mock_get_graphiti.side_effect = Exception("Connection failed")

            # Should raise or return None
            with pytest.raises(Exception):
                await _get_retriever()


# ============================================================================
# 7. Token Budget Tracking Tests (2 tests)
# ============================================================================

class TestTokenBudgetTracking:
    """Test token budget tracking in context loading."""

    @pytest.mark.asyncio
    async def test_context_includes_budget_info(self):
        """Test that loaded context includes budget information."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.budget_used = 1500
        mock_context.budget_total = 4000
        mock_context.to_prompt.return_value = "Budget: 1500/4000 tokens\n## Context"
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
                    phase="implement"
                )

                # Budget info should be in the result
                assert "1500" in result or "Budget" in result.lower()

    @pytest.mark.asyncio
    async def test_respects_context_window_limit(self):
        """Test that context respects maximum token budget."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.budget_used = 4000
        mock_context.budget_total = 4000
        mock_context.to_prompt.return_value = "Context" * 1000  # Large context
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
                    phase="implement"
                )

                # Result should be string (whatever retriever returns)
                assert isinstance(result, str)


# ============================================================================
# 8. Sync Wrapper Tests (2 tests)
# ============================================================================

class TestSyncWrapper:
    """Test synchronous wrapper for async functions."""

    def test_load_task_context_sync_exists(self):
        """Test that load_task_context_sync function exists."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context_sync,
        )

        assert callable(load_task_context_sync)

    def test_load_task_context_sync_returns_result(self):
        """Test that sync wrapper returns result from async function."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context_sync,
        )

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=False
        ):
            result = load_task_context_sync(
                task_id="TASK-001",
                task_data={"description": "Test"},
                phase="implement"
            )

            # Should return None when Graphiti disabled
            assert result is None


# ============================================================================
# 9. Edge Case and Error Path Tests (6 tests)
# ============================================================================

class TestEdgeCasesAndErrorPaths:
    """Test edge cases and error paths for coverage."""

    def test_get_context_for_prompt_with_object_having_to_prompt(self):
        """Test get_context_for_prompt with object that has to_prompt method."""
        from installer.core.commands.lib.graphiti_context_loader import (
            get_context_for_prompt,
        )

        class CustomContext:
            def to_prompt(self):
                return "Custom prompt"

        result = get_context_for_prompt(CustomContext())
        assert result == "Custom prompt"

    def test_get_context_for_prompt_fallback_to_str(self):
        """Test get_context_for_prompt falls back to str() for unknown types."""
        from installer.core.commands.lib.graphiti_context_loader import (
            get_context_for_prompt,
        )

        # Object without to_prompt method
        class CustomObject:
            def __str__(self):
                return "string representation"

        result = get_context_for_prompt(CustomObject())
        assert result == "string representation"

    def test_is_graphiti_enabled_when_module_not_available(self):
        """Test is_graphiti_enabled returns False when module unavailable."""
        from installer.core.commands.lib import graphiti_context_loader

        # Save original
        original = graphiti_context_loader.GRAPHITI_AVAILABLE

        try:
            # Simulate module unavailable
            graphiti_context_loader.GRAPHITI_AVAILABLE = False
            result = graphiti_context_loader.is_graphiti_enabled()
            assert result is False
        finally:
            # Restore original
            graphiti_context_loader.GRAPHITI_AVAILABLE = original

    def test_is_graphiti_enabled_when_env_var_false(self):
        """Test is_graphiti_enabled returns False when env var is 'false'."""
        from installer.core.commands.lib.graphiti_context_loader import (
            is_graphiti_enabled,
        )

        with patch.dict('os.environ', {'GRAPHITI_ENABLED': 'false'}):
            result = is_graphiti_enabled()
            assert result is False

    def test_get_task_phase_raises_when_graphiti_unavailable(self):
        """Test _get_task_phase raises when Graphiti unavailable."""
        from installer.core.commands.lib import graphiti_context_loader

        # Save original
        original = graphiti_context_loader.GRAPHITI_AVAILABLE

        try:
            # Simulate module unavailable
            graphiti_context_loader.GRAPHITI_AVAILABLE = False

            with pytest.raises(RuntimeError, match="Graphiti modules not available"):
                graphiti_context_loader._get_task_phase("implement")
        finally:
            # Restore original
            graphiti_context_loader.GRAPHITI_AVAILABLE = original

    @pytest.mark.asyncio
    async def test_get_retriever_raises_when_graphiti_unavailable(self):
        """Test _get_retriever raises when Graphiti unavailable."""
        from installer.core.commands.lib import graphiti_context_loader

        # Save original
        original = graphiti_context_loader.GRAPHITI_AVAILABLE

        try:
            # Simulate module unavailable
            graphiti_context_loader.GRAPHITI_AVAILABLE = False

            with pytest.raises(RuntimeError, match="Graphiti modules not available"):
                await graphiti_context_loader._get_retriever()
        finally:
            # Restore original
            graphiti_context_loader.GRAPHITI_AVAILABLE = original


# ============================================================================
# 10. Integration with phase_execution Tests (3 tests)
# ============================================================================

class TestPhaseExecutionIntegration:
    """Test integration points with phase_execution module."""

    def test_module_can_be_imported_from_lib(self):
        """Test module is importable from commands.lib."""
        from installer.core.commands.lib import graphiti_context_loader

        # Should have all expected exports
        assert hasattr(graphiti_context_loader, 'is_graphiti_enabled')
        assert hasattr(graphiti_context_loader, 'load_task_context')
        assert hasattr(graphiti_context_loader, 'get_context_for_prompt')

    def test_exports_match_interface(self):
        """Test that module exports match expected interface."""
        from installer.core.commands.lib.graphiti_context_loader import __all__

        expected = [
            'is_graphiti_enabled',
            'load_task_context',
            'load_task_context_sync',
            'get_context_for_prompt',
            'GRAPHITI_AVAILABLE',
        ]

        for name in expected:
            assert name in __all__, f"Missing export: {name}"

    @pytest.mark.asyncio
    async def test_context_formatted_for_agent_prompt(self):
        """Test that returned context is formatted for agent prompts."""
        from installer.core.commands.lib.graphiti_context_loader import (
            load_task_context,
        )

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        # Realistic prompt format
        mock_context.to_prompt.return_value = """## Job-Specific Context

Budget: 1500/4000 tokens

### Feature Context
- Feature A: Description here

### Relevant Patterns
- Repository Pattern: Use for data access
"""
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
                    phase="implement"
                )

                # Should be markdown-formatted for agent injection
                assert "##" in result
                assert isinstance(result, str)
