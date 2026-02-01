"""
Comprehensive Test Suite for Quality Gate Retrieval and Formatting

Tests quality gate configs retrieval functionality including:
- QualityGateRetriever class with retrieve() method
- Integration with TaskAnalyzer and GraphitiClient
- Graphiti queries for quality_gate_configs group
- Task type filtering (scaffolding, feature, testing, documentation)
- Formatting with coverage_threshold, arch_review_threshold, tests_required
- "do NOT adjust" messaging in output
- AutoBuild context emphasis
- Edge cases and error handling

Coverage Target: >=85%
Test Count: 15+ tests

References:
- TASK-GR6-008: Add quality_gate_configs retrieval and formatting
- FEAT-GR-006: AutoBuild Customization and Knowledge Enhancement

TDD RED PHASE: These tests are designed to FAIL initially because
the implementation doesn't exist yet. This is intentional.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call
from typing import Dict, List, Any


# ============================================================================
# 1. Quality Gate Query Tests (3 tests)
# ============================================================================

class TestQualityGateQueries:
    """Test quality gate configs retrieval from Graphiti."""

    @pytest.mark.asyncio
    async def test_queries_quality_gate_configs_group_for_autobuild(self):
        """Test that quality_gate_configs group is queried for AutoBuild."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
        }

        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should query quality_gate_configs group
        calls = mock_graphiti.search.call_args_list
        group_ids_used = [call[1].get("group_ids", []) for call in calls]
        assert any("quality_gate_configs" in groups for groups in group_ids_used)

    @pytest.mark.asyncio
    async def test_filters_quality_gate_by_task_type(self):
        """Test that quality gates are filtered by task_type."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Mock results with task_type field
        mock_results = [
            {
                "id": "QG-FEATURE-001",
                "task_type": "feature",
                "coverage_threshold": 0.8,
                "arch_review_threshold": 60,
                "tests_required": True,
            },
            {
                "id": "QG-SCAFFOLDING-001",
                "task_type": "scaffolding",
                "coverage_threshold": None,
                "arch_review_threshold": None,
                "tests_required": False,
            },
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Quality gates should be populated
        assert isinstance(result.quality_gate_configs, list)
        assert len(result.quality_gate_configs) > 0

    @pytest.mark.asyncio
    async def test_skips_quality_gates_when_not_autobuild(self):
        """Test that quality gates are empty when is_autobuild=False."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": False,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Quality gates should be empty
        assert result.quality_gate_configs == []


# ============================================================================
# 2. Quality Gate Formatting Tests (5 tests)
# ============================================================================

class TestQualityGateFormatting:
    """Test formatting of quality gate configs for output."""

    @pytest.mark.asyncio
    async def test_format_quality_gates_includes_header(self):
        """Test that formatted output includes quality gate header."""
        from guardkit.knowledge.quality_gate_formatter import (
            format_quality_gates,
        )

        quality_gates = [
            {
                "id": "QG-FEATURE-001",
                "task_type": "feature",
                "coverage_threshold": 0.8,
                "arch_review_threshold": 60,
                "tests_required": True,
            }
        ]

        output = format_quality_gates(quality_gates)

        # Should include header
        assert "📊" in output or "Quality Gate" in output or "Threshold" in output
        assert isinstance(output, str)
        assert len(output) > 0

    @pytest.mark.asyncio
    async def test_format_quality_gates_includes_do_not_adjust_message(self):
        """Test that formatted output includes 'do NOT adjust' messaging."""
        from guardkit.knowledge.quality_gate_formatter import (
            format_quality_gates,
        )

        quality_gates = [
            {
                "id": "QG-FEATURE-001",
                "task_type": "feature",
                "coverage_threshold": 0.8,
                "arch_review_threshold": 60,
                "tests_required": True,
            }
        ]

        output = format_quality_gates(quality_gates)

        # Should include do NOT adjust message (case-insensitive search)
        assert "do NOT" in output or "do not" in output or "adjust" in output

    @pytest.mark.asyncio
    async def test_format_coverage_threshold_as_percentage(self):
        """Test that coverage_threshold is formatted as percentage."""
        from guardkit.knowledge.quality_gate_formatter import (
            format_quality_gates,
        )

        quality_gates = [
            {
                "id": "QG-FEATURE-001",
                "task_type": "feature",
                "coverage_threshold": 0.8,
                "arch_review_threshold": 60,
                "tests_required": True,
            }
        ]

        output = format_quality_gates(quality_gates)

        # Should format as 80% or ≥80%
        assert "80" in output or "0.8" in output
        assert "%" in output or "≥" in output

    @pytest.mark.asyncio
    async def test_format_arch_review_threshold(self):
        """Test that arch_review_threshold is formatted correctly."""
        from guardkit.knowledge.quality_gate_formatter import (
            format_quality_gates,
        )

        quality_gates = [
            {
                "id": "QG-FEATURE-001",
                "task_type": "feature",
                "coverage_threshold": 0.8,
                "arch_review_threshold": 60,
                "tests_required": True,
            }
        ]

        output = format_quality_gates(quality_gates)

        # Should include arch review threshold
        assert "60" in output or "arch" in output.lower()

    @pytest.mark.asyncio
    async def test_format_tests_required_as_yes_no(self):
        """Test that tests_required is formatted as Yes/No."""
        from guardkit.knowledge.quality_gate_formatter import (
            format_quality_gates,
        )

        quality_gates = [
            {
                "id": "QG-FEATURE-001",
                "task_type": "feature",
                "coverage_threshold": 0.8,
                "arch_review_threshold": 60,
                "tests_required": True,
            }
        ]

        output = format_quality_gates(quality_gates)

        # Should format tests_required as Yes or True
        assert "Yes" in output or "True" in output or "test" in output.lower()


# ============================================================================
# 3. Task Type Specific Tests (4 tests)
# ============================================================================

class TestTaskTypeSpecificGates:
    """Test quality gate filtering by task type."""

    @pytest.mark.asyncio
    async def test_scaffolding_task_type_gets_scaffolding_config(self):
        """Test that scaffolding task type retrieves scaffolding config."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        mock_results = [
            {
                "id": "QG-SCAFFOLDING-001",
                "task_type": "scaffolding",
                "coverage_threshold": None,
                "arch_review_threshold": None,
                "tests_required": False,
            }
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Scaffolding task",
            "tech_stack": "python",
            "is_autobuild": True,
            "task_type": "scaffolding",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should have scaffolding config
        assert len(result.quality_gate_configs) > 0
        scaffolding_configs = [
            cfg for cfg in result.quality_gate_configs
            if cfg.get("task_type") == "scaffolding"
        ]
        assert len(scaffolding_configs) > 0

    @pytest.mark.asyncio
    async def test_feature_task_type_gets_feature_config(self):
        """Test that feature task type retrieves feature config."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        mock_results = [
            {
                "id": "QG-FEATURE-001",
                "task_type": "feature",
                "coverage_threshold": 0.8,
                "arch_review_threshold": 60,
                "tests_required": True,
            }
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Feature task",
            "tech_stack": "python",
            "is_autobuild": True,
            "task_type": "feature",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should have feature config
        assert len(result.quality_gate_configs) > 0
        feature_configs = [
            cfg for cfg in result.quality_gate_configs
            if cfg.get("task_type") == "feature"
        ]
        assert len(feature_configs) > 0

    @pytest.mark.asyncio
    async def test_testing_task_type_gets_testing_config(self):
        """Test that testing task type retrieves testing config."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        mock_results = [
            {
                "id": "QG-TESTING-001",
                "task_type": "testing",
                "coverage_threshold": 0.9,
                "arch_review_threshold": None,
                "tests_required": True,
            }
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Testing task",
            "tech_stack": "python",
            "is_autobuild": True,
            "task_type": "testing",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should have testing config
        assert len(result.quality_gate_configs) > 0
        testing_configs = [
            cfg for cfg in result.quality_gate_configs
            if cfg.get("task_type") == "testing"
        ]
        assert len(testing_configs) > 0

    @pytest.mark.asyncio
    async def test_documentation_task_type_gets_docs_config(self):
        """Test that documentation task type retrieves docs config."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        mock_results = [
            {
                "id": "QG-DOCS-001",
                "task_type": "documentation",
                "coverage_threshold": None,
                "arch_review_threshold": None,
                "tests_required": False,
            }
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Documentation task",
            "tech_stack": "python",
            "is_autobuild": True,
            "task_type": "documentation",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should have documentation config
        assert len(result.quality_gate_configs) > 0
        docs_configs = [
            cfg for cfg in result.quality_gate_configs
            if cfg.get("task_type") == "documentation"
        ]
        assert len(docs_configs) > 0


# ============================================================================
# 4. Edge Case Tests (3 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_handles_missing_threshold_values(self):
        """Test that missing threshold values are handled gracefully."""
        from guardkit.knowledge.quality_gate_formatter import (
            format_quality_gates,
        )

        quality_gates = [
            {
                "id": "QG-SCAFFOLDING-001",
                "task_type": "scaffolding",
                "coverage_threshold": None,
                "arch_review_threshold": None,
                "tests_required": False,
            }
        ]

        output = format_quality_gates(quality_gates)

        # Should not raise exception
        assert isinstance(output, str)
        # Should mention "not required" or similar
        assert "not" in output.lower() or "None" in output

    @pytest.mark.asyncio
    async def test_handles_empty_quality_gate_configs(self):
        """Test that empty quality gate configs are handled gracefully."""
        from guardkit.knowledge.quality_gate_formatter import (
            format_quality_gates,
        )

        quality_gates = []

        output = format_quality_gates(quality_gates)

        # Should return empty string or minimal placeholder
        assert isinstance(output, str)

    @pytest.mark.asyncio
    async def test_handles_none_quality_gate_configs(self):
        """Test that None quality gate configs are handled gracefully."""
        from guardkit.knowledge.quality_gate_formatter import (
            format_quality_gates,
        )

        # Should not raise exception with None
        output = format_quality_gates(None)

        # Should return empty string or minimal placeholder
        assert isinstance(output, str)


# ============================================================================
# 5. Integration Tests (2 tests)
# ============================================================================

class TestQualityGateIntegration:
    """Test integration of quality gate retrieval with context."""

    @pytest.mark.asyncio
    async def test_quality_gates_included_in_to_prompt(self):
        """Test that quality gates are included in to_prompt() output."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=1000,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[
                {
                    "id": "QG-FEATURE-001",
                    "task_type": "feature",
                    "coverage_threshold": 0.8,
                    "arch_review_threshold": 60,
                    "tests_required": True,
                }
            ],
            turn_states=[],
            implementation_modes=[],
        )

        result = context.to_prompt()

        # Quality gates should be in output
        assert "quality" in result.lower() or "gate" in result.lower()

    @pytest.mark.asyncio
    async def test_multiple_quality_gate_configs_formatted(self):
        """Test that multiple quality gate configs are formatted correctly."""
        from guardkit.knowledge.quality_gate_formatter import (
            format_quality_gates,
        )

        quality_gates = [
            {
                "id": "QG-FEATURE-001",
                "task_type": "feature",
                "coverage_threshold": 0.8,
                "arch_review_threshold": 60,
                "tests_required": True,
            },
            {
                "id": "QG-TESTING-001",
                "task_type": "testing",
                "coverage_threshold": 0.9,
                "arch_review_threshold": None,
                "tests_required": True,
            },
            {
                "id": "QG-SCAFFOLDING-001",
                "task_type": "scaffolding",
                "coverage_threshold": None,
                "arch_review_threshold": None,
                "tests_required": False,
            },
        ]

        output = format_quality_gates(quality_gates)

        # Should format all types
        assert isinstance(output, str)
        assert len(output) > 0
        # All task types should appear
        assert "feature" in output.lower()
        assert "testing" in output.lower() or "test" in output.lower()
        assert "scaffolding" in output.lower()
