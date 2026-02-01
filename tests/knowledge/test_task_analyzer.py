"""
Comprehensive Test Suite for TaskAnalyzer

Tests the task analysis functionality including:
- TaskType and TaskPhase enums
- TaskCharacteristics dataclass
- TaskAnalyzer class with analyze() method
- Task type classification
- Historical performance querying
- AutoBuild-specific characteristics

Coverage Target: >=85%
Test Count: 45+ tests

References:
- TASK-GR6-001: Implement TaskAnalyzer
- FEAT-GR-006: Job-Specific Context Retrieval
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict
from enum import Enum
from dataclasses import is_dataclass, fields


# ============================================================================
# 1. TaskType Enum Tests (5 tests)
# ============================================================================

class TestTaskTypeEnum:
    """Test TaskType enum definition."""

    def test_enum_has_all_task_types(self):
        """Test that TaskType enum has all required task types."""
        from guardkit.knowledge.task_analyzer import TaskType

        expected_types = {
            "IMPLEMENTATION",
            "REVIEW",
            "PLANNING",
            "REFINEMENT",
            "DOCUMENTATION",
        }

        actual_types = {member.name for member in TaskType}
        assert actual_types == expected_types

    def test_enum_values_are_strings(self):
        """Test that enum values are lowercase strings."""
        from guardkit.knowledge.task_analyzer import TaskType

        assert TaskType.IMPLEMENTATION.value == "implementation"
        assert TaskType.REVIEW.value == "review"
        assert TaskType.PLANNING.value == "planning"
        assert TaskType.REFINEMENT.value == "refinement"
        assert TaskType.DOCUMENTATION.value == "documentation"

    def test_enum_is_string_enum(self):
        """Test that TaskType is a string enum."""
        from guardkit.knowledge.task_analyzer import TaskType

        assert issubclass(TaskType, str)
        assert issubclass(TaskType, Enum)

    def test_enum_can_be_compared_to_strings(self):
        """Test that enum members can be compared to strings."""
        from guardkit.knowledge.task_analyzer import TaskType

        assert TaskType.IMPLEMENTATION == "implementation"
        assert TaskType.REVIEW == "review"

    def test_enum_from_string_value(self):
        """Test creating enum from string value."""
        from guardkit.knowledge.task_analyzer import TaskType

        task_type = TaskType("implementation")
        assert task_type == TaskType.IMPLEMENTATION


# ============================================================================
# 2. TaskPhase Enum Tests (5 tests)
# ============================================================================

class TestTaskPhaseEnum:
    """Test TaskPhase enum definition."""

    def test_enum_has_all_phases(self):
        """Test that TaskPhase enum has all required phases."""
        from guardkit.knowledge.task_analyzer import TaskPhase

        expected_phases = {
            "LOAD",
            "PLAN",
            "IMPLEMENT",
            "TEST",
            "REVIEW",
        }

        actual_phases = {member.name for member in TaskPhase}
        assert actual_phases == expected_phases

    def test_enum_values_are_strings(self):
        """Test that enum values are lowercase strings."""
        from guardkit.knowledge.task_analyzer import TaskPhase

        assert TaskPhase.LOAD.value == "load"
        assert TaskPhase.PLAN.value == "plan"
        assert TaskPhase.IMPLEMENT.value == "implement"
        assert TaskPhase.TEST.value == "test"
        assert TaskPhase.REVIEW.value == "review"

    def test_enum_is_string_enum(self):
        """Test that TaskPhase is a string enum."""
        from guardkit.knowledge.task_analyzer import TaskPhase

        assert issubclass(TaskPhase, str)
        assert issubclass(TaskPhase, Enum)

    def test_enum_can_be_compared_to_strings(self):
        """Test that enum members can be compared to strings."""
        from guardkit.knowledge.task_analyzer import TaskPhase

        assert TaskPhase.IMPLEMENT == "implement"
        assert TaskPhase.TEST == "test"

    def test_enum_from_string_value(self):
        """Test creating enum from string value."""
        from guardkit.knowledge.task_analyzer import TaskPhase

        phase = TaskPhase("implement")
        assert phase == TaskPhase.IMPLEMENT


# ============================================================================
# 3. TaskCharacteristics Dataclass Tests (12 tests)
# ============================================================================

class TestTaskCharacteristicsDataclass:
    """Test TaskCharacteristics dataclass definition."""

    def test_is_dataclass(self):
        """Test that TaskCharacteristics is a proper dataclass."""
        from guardkit.knowledge.task_analyzer import TaskCharacteristics

        assert is_dataclass(TaskCharacteristics)

    def test_has_basic_info_fields(self):
        """Test that TaskCharacteristics has basic info fields."""
        from guardkit.knowledge.task_analyzer import TaskCharacteristics

        field_names = {f.name for f in fields(TaskCharacteristics)}

        assert "task_id" in field_names
        assert "description" in field_names
        assert "tech_stack" in field_names

    def test_has_classification_fields(self):
        """Test that TaskCharacteristics has classification fields."""
        from guardkit.knowledge.task_analyzer import TaskCharacteristics

        field_names = {f.name for f in fields(TaskCharacteristics)}

        assert "task_type" in field_names
        assert "current_phase" in field_names
        assert "complexity" in field_names

    def test_has_novelty_fields(self):
        """Test that TaskCharacteristics has novelty indicator fields."""
        from guardkit.knowledge.task_analyzer import TaskCharacteristics

        field_names = {f.name for f in fields(TaskCharacteristics)}

        assert "is_first_of_type" in field_names
        assert "similar_task_count" in field_names

    def test_has_context_fields(self):
        """Test that TaskCharacteristics has context indicator fields."""
        from guardkit.knowledge.task_analyzer import TaskCharacteristics

        field_names = {f.name for f in fields(TaskCharacteristics)}

        assert "feature_id" in field_names
        assert "is_refinement" in field_names
        assert "refinement_attempt" in field_names
        assert "previous_failure_type" in field_names

    def test_has_performance_fields(self):
        """Test that TaskCharacteristics has historical performance fields."""
        from guardkit.knowledge.task_analyzer import TaskCharacteristics

        field_names = {f.name for f in fields(TaskCharacteristics)}

        assert "avg_turns_for_type" in field_names
        assert "success_rate_for_type" in field_names

    def test_has_autobuild_fields(self):
        """Test that TaskCharacteristics has AutoBuild-specific fields."""
        from guardkit.knowledge.task_analyzer import TaskCharacteristics

        field_names = {f.name for f in fields(TaskCharacteristics)}

        assert "current_actor" in field_names
        assert "turn_number" in field_names
        assert "is_autobuild" in field_names
        assert "has_previous_turns" in field_names

    def test_can_create_instance_with_all_fields(self):
        """Test creating TaskCharacteristics with all fields."""
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,
            is_first_of_type=False,
            similar_task_count=10,
            feature_id="FEAT-001",
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.5,
            success_rate_for_type=0.85,
            current_actor="player",
            turn_number=1,
            is_autobuild=True,
            has_previous_turns=False,
        )

        assert characteristics.task_id == "TASK-001"
        assert characteristics.tech_stack == "python"
        assert characteristics.is_autobuild is True

    def test_autobuild_fields_have_defaults(self):
        """Test that AutoBuild fields have sensible defaults."""
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        # Create with minimal required fields
        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        # Check defaults
        assert characteristics.current_actor == "player"
        assert characteristics.turn_number == 0
        assert characteristics.is_autobuild is False
        assert characteristics.has_previous_turns is False

    def test_complexity_is_integer(self):
        """Test that complexity is an integer field."""
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=7,
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        assert isinstance(characteristics.complexity, int)
        assert characteristics.complexity == 7

    def test_turn_number_is_integer(self):
        """Test that turn_number is an integer field."""
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            turn_number=3,
        )

        assert isinstance(characteristics.turn_number, int)
        assert characteristics.turn_number == 3

    def test_feature_id_is_optional(self):
        """Test that feature_id can be None."""
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        assert characteristics.feature_id is None


# ============================================================================
# 4. TaskAnalyzer Initialization Tests (3 tests)
# ============================================================================

class TestTaskAnalyzerInit:
    """Test TaskAnalyzer initialization."""

    def test_analyzer_can_be_instantiated_with_graphiti(self):
        """Test creating a TaskAnalyzer instance with graphiti client."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer

        mock_graphiti = MagicMock()
        analyzer = TaskAnalyzer(mock_graphiti)

        assert analyzer is not None
        assert analyzer.graphiti == mock_graphiti

    def test_analyzer_stores_graphiti_reference(self):
        """Test that analyzer stores graphiti reference."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer

        mock_graphiti = MagicMock()
        analyzer = TaskAnalyzer(mock_graphiti)

        assert analyzer.graphiti is mock_graphiti

    def test_analyzer_has_analyze_method(self):
        """Test that analyzer has analyze method."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer

        mock_graphiti = MagicMock()
        analyzer = TaskAnalyzer(mock_graphiti)

        assert hasattr(analyzer, "analyze")
        assert callable(analyzer.analyze)


# ============================================================================
# 5. analyze() Return Type Tests (4 tests)
# ============================================================================

class TestAnalyzeReturnType:
    """Test analyze() return type and structure."""

    @pytest.mark.asyncio
    async def test_analyze_returns_task_characteristics(self):
        """Test that analyze() returns TaskCharacteristics."""
        from guardkit.knowledge.task_analyzer import (
            TaskAnalyzer,
            TaskPhase,
            TaskCharacteristics,
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert isinstance(result, TaskCharacteristics)

    @pytest.mark.asyncio
    async def test_analyze_returns_correct_task_id(self):
        """Test that analyze() returns correct task_id."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-TEST-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.task_id == "TASK-TEST-001"

    @pytest.mark.asyncio
    async def test_analyze_returns_correct_phase(self):
        """Test that analyze() returns correct phase."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.TEST)

        assert result.current_phase == TaskPhase.TEST

    @pytest.mark.asyncio
    async def test_analyze_returns_description(self):
        """Test that analyze() returns correct description."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Implement user authentication",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.description == "Implement user authentication"


# ============================================================================
# 6. Task Type Classification Tests (8 tests)
# ============================================================================

class TestTaskTypeClassification:
    """Test task type classification logic."""

    @pytest.mark.asyncio
    async def test_classifies_implementation_task(self):
        """Test classification of implementation task."""
        from guardkit.knowledge.task_analyzer import (
            TaskAnalyzer,
            TaskPhase,
            TaskType,
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "task_type": "implementation",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.task_type == TaskType.IMPLEMENTATION

    @pytest.mark.asyncio
    async def test_classifies_review_task(self):
        """Test classification of review task."""
        from guardkit.knowledge.task_analyzer import (
            TaskAnalyzer,
            TaskPhase,
            TaskType,
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "task_type": "review",
        }

        result = await analyzer.analyze(task, TaskPhase.REVIEW)

        assert result.task_type == TaskType.REVIEW

    @pytest.mark.asyncio
    async def test_classifies_planning_task(self):
        """Test classification of planning task."""
        from guardkit.knowledge.task_analyzer import (
            TaskAnalyzer,
            TaskPhase,
            TaskType,
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "task_type": "planning",
        }

        result = await analyzer.analyze(task, TaskPhase.PLAN)

        assert result.task_type == TaskType.PLANNING

    @pytest.mark.asyncio
    async def test_classifies_refinement_task(self):
        """Test classification of refinement task."""
        from guardkit.knowledge.task_analyzer import (
            TaskAnalyzer,
            TaskPhase,
            TaskType,
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "task_type": "refinement",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.task_type == TaskType.REFINEMENT

    @pytest.mark.asyncio
    async def test_classifies_refine_as_refinement(self):
        """Test that 'refine' maps to REFINEMENT."""
        from guardkit.knowledge.task_analyzer import (
            TaskAnalyzer,
            TaskPhase,
            TaskType,
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "task_type": "refine",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.task_type == TaskType.REFINEMENT

    @pytest.mark.asyncio
    async def test_classifies_documentation_task(self):
        """Test classification of documentation task."""
        from guardkit.knowledge.task_analyzer import (
            TaskAnalyzer,
            TaskPhase,
            TaskType,
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "task_type": "documentation",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.task_type == TaskType.DOCUMENTATION

    @pytest.mark.asyncio
    async def test_classifies_docs_as_documentation(self):
        """Test that 'docs' maps to DOCUMENTATION."""
        from guardkit.knowledge.task_analyzer import (
            TaskAnalyzer,
            TaskPhase,
            TaskType,
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "task_type": "docs",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.task_type == TaskType.DOCUMENTATION

    @pytest.mark.asyncio
    async def test_defaults_to_implementation(self):
        """Test that unknown task type defaults to IMPLEMENTATION."""
        from guardkit.knowledge.task_analyzer import (
            TaskAnalyzer,
            TaskPhase,
            TaskType,
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            # No task_type specified - should default to implementation
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.task_type == TaskType.IMPLEMENTATION


# ============================================================================
# 7. Complexity and Novelty Tests (6 tests)
# ============================================================================

class TestComplexityAndNovelty:
    """Test complexity and novelty detection."""

    @pytest.mark.asyncio
    async def test_extracts_complexity_from_task(self):
        """Test that complexity is extracted from task data."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "complexity": 8,
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.complexity == 8

    @pytest.mark.asyncio
    async def test_defaults_complexity_to_5(self):
        """Test that complexity defaults to 5 if not provided."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            # No complexity specified
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.complexity == 5

    @pytest.mark.asyncio
    async def test_detects_first_of_type_when_no_similar_tasks(self):
        """Test that is_first_of_type is True when no similar tasks exist."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Implement new feature X",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.is_first_of_type is True
        assert result.similar_task_count == 0

    @pytest.mark.asyncio
    async def test_detects_not_first_of_type_when_similar_tasks_exist(self):
        """Test that is_first_of_type is False when similar tasks exist."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        # Mock similar tasks found
        similar_tasks = [
            {"uuid": "1", "fact": "Similar task 1", "score": 0.8},
            {"uuid": "2", "fact": "Similar task 2", "score": 0.75},
        ]

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=similar_tasks)

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Implement user authentication",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.is_first_of_type is False
        assert result.similar_task_count > 0

    @pytest.mark.asyncio
    async def test_counts_similar_tasks_above_threshold(self):
        """Test that only similar tasks above score threshold are counted."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        # Mix of high and low score results
        search_results = [
            {"uuid": "1", "fact": "Very similar", "score": 0.9},
            {"uuid": "2", "fact": "Similar", "score": 0.75},
            {"uuid": "3", "fact": "Low similarity", "score": 0.3},  # Below threshold
        ]

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=search_results)

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        # Only 2 tasks have score > 0.7
        assert result.similar_task_count == 2

    @pytest.mark.asyncio
    async def test_extracts_tech_stack(self):
        """Test that tech_stack is extracted from task data."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "typescript",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.tech_stack == "typescript"


# ============================================================================
# 8. Refinement Detection Tests (4 tests)
# ============================================================================

class TestRefinementDetection:
    """Test refinement status detection."""

    @pytest.mark.asyncio
    async def test_detects_refinement_from_attempt_count(self):
        """Test that refinement is detected from refinement_attempt > 0."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "refinement_attempt": 2,
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.is_refinement is True
        assert result.refinement_attempt == 2

    @pytest.mark.asyncio
    async def test_not_refinement_when_attempt_is_zero(self):
        """Test that is_refinement is False when refinement_attempt is 0."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "refinement_attempt": 0,
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.is_refinement is False
        assert result.refinement_attempt == 0

    @pytest.mark.asyncio
    async def test_extracts_previous_failure_type(self):
        """Test that previous_failure_type is extracted."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "last_failure_type": "test_failure",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.previous_failure_type == "test_failure"

    @pytest.mark.asyncio
    async def test_extracts_feature_id(self):
        """Test that feature_id is extracted."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "feature_id": "FEAT-AUTH-001",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.feature_id == "FEAT-AUTH-001"


# ============================================================================
# 9. Historical Performance Tests (4 tests)
# ============================================================================

class TestHistoricalPerformance:
    """Test historical performance querying."""

    @pytest.mark.asyncio
    async def test_queries_historical_stats(self):
        """Test that historical stats are queried from Graphiti."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        # Mock historical outcomes
        outcomes = [
            {"uuid": "1", "fact": "Task completed", "status": "success", "turns": 2},
            {"uuid": "2", "fact": "Task completed", "status": "success", "turns": 4},
        ]

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=outcomes)

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        # Verify graphiti.search was called
        assert mock_graphiti.search.called

    @pytest.mark.asyncio
    async def test_returns_default_stats_when_no_history(self):
        """Test that default stats are returned when no history exists."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        # Default values
        assert result.avg_turns_for_type == 3.0
        assert result.success_rate_for_type == 0.8

    @pytest.mark.asyncio
    async def test_calculates_success_rate_from_outcomes(self):
        """Test that success rate is calculated from outcomes."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        # 3 successes, 1 failure = 75% success rate
        outcomes = [
            {"uuid": "1", "fact": "Task 1", "status": "success"},
            {"uuid": "2", "fact": "Task 2", "status": "success"},
            {"uuid": "3", "fact": "Task 3", "status": "failure"},
            {"uuid": "4", "fact": "Task 4", "status": "success"},
        ]

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=outcomes)

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.success_rate_for_type == 0.75

    @pytest.mark.asyncio
    async def test_calculates_avg_turns_from_outcomes(self):
        """Test that average turns is calculated from outcomes."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        # Average of 2, 4, 3 = 3.0
        outcomes = [
            {"uuid": "1", "fact": "Task 1", "turns": 2},
            {"uuid": "2", "fact": "Task 2", "turns": 4},
            {"uuid": "3", "fact": "Task 3", "turns": 3},
        ]

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=outcomes)

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.avg_turns_for_type == 3.0


# ============================================================================
# 10. AutoBuild Context Tests (8 tests)
# ============================================================================

class TestAutoBuildContext:
    """Test AutoBuild-specific characteristics."""

    @pytest.mark.asyncio
    async def test_extracts_current_actor(self):
        """Test that current_actor is extracted from task data."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "current_actor": "coach",
        }

        result = await analyzer.analyze(task, TaskPhase.REVIEW)

        assert result.current_actor == "coach"

    @pytest.mark.asyncio
    async def test_defaults_current_actor_to_player(self):
        """Test that current_actor defaults to 'player'."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.current_actor == "player"

    @pytest.mark.asyncio
    async def test_extracts_turn_number(self):
        """Test that turn_number is extracted from task data."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "turn_number": 3,
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.turn_number == 3

    @pytest.mark.asyncio
    async def test_defaults_turn_number_to_zero(self):
        """Test that turn_number defaults to 0."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.turn_number == 0

    @pytest.mark.asyncio
    async def test_extracts_is_autobuild(self):
        """Test that is_autobuild is extracted from task data."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.is_autobuild is True

    @pytest.mark.asyncio
    async def test_defaults_is_autobuild_to_false(self):
        """Test that is_autobuild defaults to False."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.is_autobuild is False

    @pytest.mark.asyncio
    async def test_extracts_has_previous_turns(self):
        """Test that has_previous_turns is extracted from task data."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "has_previous_turns": True,
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.has_previous_turns is True

    @pytest.mark.asyncio
    async def test_defaults_has_previous_turns_to_false(self):
        """Test that has_previous_turns defaults to False."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.has_previous_turns is False


# ============================================================================
# 11. Edge Cases and Error Handling Tests (5 tests)
# ============================================================================

class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_handles_graphiti_search_failure(self):
        """Test that analyze() handles Graphiti search failures gracefully."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(side_effect=Exception("Connection failed"))

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        # Should not raise, should return with defaults
        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.task_id == "TASK-001"
        # Should use defaults on failure
        assert result.is_first_of_type is True  # No similar tasks found
        assert result.avg_turns_for_type == 3.0
        assert result.success_rate_for_type == 0.8

    @pytest.mark.asyncio
    async def test_handles_empty_task_dict(self):
        """Test that analyze() handles empty task dict."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {}

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        # Should use defaults
        assert result.task_id == ""
        assert result.description == ""
        assert result.tech_stack == "python"  # Default
        assert result.complexity == 5  # Default

    @pytest.mark.asyncio
    async def test_handles_none_values_in_task(self):
        """Test that analyze() handles None values in task dict."""
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": None,
            "description": None,
            "tech_stack": None,
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        # Should handle None gracefully
        assert result.task_id == ""
        assert result.description == ""
        assert result.tech_stack == "python"  # Default

    @pytest.mark.asyncio
    async def test_case_insensitive_task_type(self):
        """Test that task type classification is case insensitive."""
        from guardkit.knowledge.task_analyzer import (
            TaskAnalyzer,
            TaskPhase,
            TaskType,
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "task_type": "IMPLEMENTATION",  # Uppercase
        }

        result = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        assert result.task_type == TaskType.IMPLEMENTATION

    @pytest.mark.asyncio
    async def test_handles_mixed_case_task_type(self):
        """Test that task type classification handles mixed case."""
        from guardkit.knowledge.task_analyzer import (
            TaskAnalyzer,
            TaskPhase,
            TaskType,
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        analyzer = TaskAnalyzer(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "task_type": "Review",  # Mixed case
        }

        result = await analyzer.analyze(task, TaskPhase.REVIEW)

        assert result.task_type == TaskType.REVIEW
