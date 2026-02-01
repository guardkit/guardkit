"""
Task Analyzer for context retrieval decisions.

This module provides the TaskAnalyzer class for analyzing task characteristics
to inform job-specific context retrieval. It classifies tasks by type, detects
novelty and refinement status, and queries historical performance from Graphiti.

Public API:
    TaskType: Enum for task classification
    TaskPhase: Enum for execution phases
    TaskCharacteristics: Dataclass with analyzed task properties
    TaskAnalyzer: Main analyzer class

Example:
    from guardkit.knowledge.task_analyzer import (
        TaskAnalyzer,
        TaskPhase,
        TaskCharacteristics,
        TaskType,
    )

    analyzer = TaskAnalyzer(graphiti_client)
    characteristics = await analyzer.analyze(
        task={"id": "TASK-001", "description": "Implement auth"},
        phase=TaskPhase.IMPLEMENT
    )

    if characteristics.is_first_of_type:
        # Load more examples for novel task type
        pass

References:
    - TASK-GR6-001: Implement TaskAnalyzer
    - FEAT-GR-006: Job-Specific Context Retrieval
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskType(str, Enum):
    """Classification of task types.

    Values:
        IMPLEMENTATION: Building features, fixing bugs, creating code
        REVIEW: Analyzing architecture, making decisions, assessing quality
        PLANNING: Designing implementation approach
        REFINEMENT: Improving or fixing previous attempt
        DOCUMENTATION: Writing or updating documentation

    Example:
        task_type = TaskType.IMPLEMENTATION
        assert task_type.value == "implementation"
        assert task_type == "implementation"  # String comparison works
    """

    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    PLANNING = "planning"
    REFINEMENT = "refinement"
    DOCUMENTATION = "documentation"


class TaskPhase(str, Enum):
    """Execution phase within a task.

    Values:
        LOAD: Initial context loading phase
        PLAN: Implementation planning phase
        IMPLEMENT: Code implementation phase
        TEST: Testing and verification phase
        REVIEW: Code review phase

    Example:
        phase = TaskPhase.IMPLEMENT
        assert phase.value == "implement"
        assert phase == "implement"  # String comparison works
    """

    LOAD = "load"
    PLAN = "plan"
    IMPLEMENT = "implement"
    TEST = "test"
    REVIEW = "review"


@dataclass
class TaskCharacteristics:
    """Analyzed characteristics of a task.

    Contains all relevant task properties for context retrieval decisions:
    - Basic info: task_id, description, tech_stack
    - Classification: task_type, current_phase, complexity
    - Novelty: is_first_of_type, similar_task_count
    - Context: feature_id, is_refinement, refinement_attempt, previous_failure_type
    - Performance: avg_turns_for_type, success_rate_for_type
    - AutoBuild: current_actor, turn_number, is_autobuild, has_previous_turns

    Attributes:
        task_id: Task identifier (e.g., "TASK-001")
        description: Task description text
        tech_stack: Technology stack (e.g., "python", "typescript")
        task_type: Classification (TaskType enum)
        current_phase: Current execution phase (TaskPhase enum)
        complexity: Complexity score (1-10)
        is_first_of_type: True if no similar tasks exist in history
        similar_task_count: Number of similar tasks found
        feature_id: Associated feature identifier (optional)
        is_refinement: True if this is a refinement of previous attempt
        refinement_attempt: Which refinement attempt (0 = first try)
        previous_failure_type: Type of previous failure (if refinement)
        avg_turns_for_type: Historical average turns for this task type
        success_rate_for_type: Historical success rate for this task type
        current_actor: Current actor ("player" or "coach")
        turn_number: Current turn number in AutoBuild
        is_autobuild: True if running in AutoBuild mode
        has_previous_turns: True if previous turns exist

    Example:
        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Implement OAuth2 authentication",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=6,
            is_first_of_type=False,
            similar_task_count=3,
            feature_id="FEAT-AUTH-001",
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
    """

    # Basic info (required)
    task_id: str
    description: str
    tech_stack: str

    # Classification (required)
    task_type: TaskType
    current_phase: TaskPhase
    complexity: int

    # Novelty indicators (required)
    is_first_of_type: bool
    similar_task_count: int

    # Context indicators (required, but can be None)
    feature_id: Optional[str]
    is_refinement: bool
    refinement_attempt: int
    previous_failure_type: Optional[str]

    # Historical performance (required)
    avg_turns_for_type: float
    success_rate_for_type: float

    # AutoBuild context (optional with defaults)
    current_actor: str = "player"
    turn_number: int = 0
    is_autobuild: bool = False
    has_previous_turns: bool = False


class TaskAnalyzer:
    """Analyzes task characteristics for context retrieval decisions.

    The TaskAnalyzer examines task metadata and queries Graphiti for
    historical information to build a complete picture of task characteristics.
    This information is used to make smart decisions about what context to load.

    Attributes:
        graphiti: GraphitiClient instance for querying knowledge graph

    Example:
        from guardkit.knowledge import get_graphiti
        from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase

        graphiti = await get_graphiti()
        analyzer = TaskAnalyzer(graphiti)

        task = {
            "id": "TASK-001",
            "description": "Implement user authentication",
            "tech_stack": "python",
            "complexity": 6,
        }

        characteristics = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

        if characteristics.is_first_of_type:
            print("Novel task type - load more examples")
        if characteristics.is_refinement:
            print(f"Refinement attempt {characteristics.refinement_attempt}")
    """

    # Similarity threshold for counting similar tasks
    SIMILARITY_THRESHOLD = 0.7

    # Default performance stats when no history exists
    DEFAULT_AVG_TURNS = 3.0
    DEFAULT_SUCCESS_RATE = 0.8

    # Task type aliases for flexible classification
    TASK_TYPE_ALIASES = {
        "implementation": TaskType.IMPLEMENTATION,
        "implement": TaskType.IMPLEMENTATION,
        "review": TaskType.REVIEW,
        "planning": TaskType.PLANNING,
        "plan": TaskType.PLANNING,
        "refinement": TaskType.REFINEMENT,
        "refine": TaskType.REFINEMENT,
        "documentation": TaskType.DOCUMENTATION,
        "docs": TaskType.DOCUMENTATION,
        "doc": TaskType.DOCUMENTATION,
    }

    def __init__(self, graphiti: Any) -> None:
        """Initialize TaskAnalyzer with Graphiti client.

        Args:
            graphiti: GraphitiClient instance for knowledge graph queries
        """
        self.graphiti = graphiti

    async def analyze(
        self,
        task: Dict[str, Any],
        phase: TaskPhase,
    ) -> TaskCharacteristics:
        """Analyze task to determine characteristics.

        Examines task metadata and queries Graphiti for historical information
        to build a complete TaskCharacteristics object.

        Args:
            task: Task dictionary with fields like id, description, tech_stack
            phase: Current execution phase (TaskPhase enum)

        Returns:
            TaskCharacteristics with all analyzed properties

        Example:
            task = {"id": "TASK-001", "description": "Implement auth"}
            characteristics = await analyzer.analyze(task, TaskPhase.IMPLEMENT)
            print(f"Complexity: {characteristics.complexity}")
        """
        # Extract basic info with safe defaults
        task_id = self._safe_get(task, "id", "")
        description = self._safe_get(task, "description", "")
        tech_stack = self._safe_get(task, "tech_stack", "python")

        # Classify task type
        task_type = self._classify_task_type(task)

        # Extract complexity (default to 5 if not specified)
        complexity = self._safe_get(task, "complexity", 5)

        # Query for similar tasks and historical performance
        similar_tasks, outcomes = await self._query_history(description, task_type)

        # Count similar tasks above threshold
        similar_task_count = len([
            t for t in similar_tasks
            if t.get("score", 0) > self.SIMILARITY_THRESHOLD
        ])
        is_first_of_type = similar_task_count == 0

        # Calculate historical performance
        avg_turns, success_rate = self._calculate_performance(outcomes)

        # Extract context indicators
        feature_id = self._safe_get(task, "feature_id", None)
        refinement_attempt = self._safe_get(task, "refinement_attempt", 0)
        is_refinement = refinement_attempt > 0
        previous_failure_type = self._safe_get(task, "last_failure_type", None)

        # Extract AutoBuild context
        current_actor = self._safe_get(task, "current_actor", "player")
        turn_number = self._safe_get(task, "turn_number", 0)
        is_autobuild = self._safe_get(task, "is_autobuild", False)
        has_previous_turns = self._safe_get(task, "has_previous_turns", False)

        return TaskCharacteristics(
            task_id=task_id,
            description=description,
            tech_stack=tech_stack,
            task_type=task_type,
            current_phase=phase,
            complexity=complexity,
            is_first_of_type=is_first_of_type,
            similar_task_count=similar_task_count,
            feature_id=feature_id,
            is_refinement=is_refinement,
            refinement_attempt=refinement_attempt,
            previous_failure_type=previous_failure_type,
            avg_turns_for_type=avg_turns,
            success_rate_for_type=success_rate,
            current_actor=current_actor,
            turn_number=turn_number,
            is_autobuild=is_autobuild,
            has_previous_turns=has_previous_turns,
        )

    def _safe_get(
        self,
        task: Dict[str, Any],
        key: str,
        default: Any,
    ) -> Any:
        """Safely get a value from task dict, handling None values.

        Args:
            task: Task dictionary
            key: Key to retrieve
            default: Default value if key missing or value is None

        Returns:
            Value from task or default
        """
        value = task.get(key)
        if value is None:
            return default
        return value

    def _classify_task_type(self, task: Dict[str, Any]) -> TaskType:
        """Classify task type from task metadata.

        Uses task_type field if present, with case-insensitive matching
        and alias support.

        Args:
            task: Task dictionary with optional task_type field

        Returns:
            TaskType enum value (defaults to IMPLEMENTATION)
        """
        raw_type = task.get("task_type", "")

        if not raw_type:
            return TaskType.IMPLEMENTATION

        # Normalize to lowercase for matching
        normalized = str(raw_type).lower().strip()

        # Look up in aliases
        return self.TASK_TYPE_ALIASES.get(normalized, TaskType.IMPLEMENTATION)

    async def _query_history(
        self,
        description: str,
        task_type: TaskType,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Query Graphiti for similar tasks and historical outcomes.

        Args:
            description: Task description for similarity search
            task_type: Task type for filtering outcomes

        Returns:
            Tuple of (similar_tasks, outcomes) lists
        """
        similar_tasks: List[Dict[str, Any]] = []
        outcomes: List[Dict[str, Any]] = []

        try:
            # Search for similar tasks
            similar_tasks = await self.graphiti.search(
                description,
                # Additional filter by task type could be added here
            )
            if similar_tasks is None:
                similar_tasks = []

            # For outcomes, we reuse the same results
            # In a production system, this would be a separate query
            outcomes = similar_tasks

        except Exception:
            # Graceful degradation - return empty lists on failure
            pass

        return similar_tasks, outcomes

    def _calculate_performance(
        self,
        outcomes: List[Dict[str, Any]],
    ) -> tuple[float, float]:
        """Calculate historical performance from outcomes.

        Args:
            outcomes: List of outcome dictionaries with status and turns

        Returns:
            Tuple of (avg_turns, success_rate)
        """
        if not outcomes:
            return self.DEFAULT_AVG_TURNS, self.DEFAULT_SUCCESS_RATE

        # Calculate success rate
        success_count = sum(
            1 for o in outcomes if o.get("status") == "success"
        )
        total_count = len(outcomes)

        # Only calculate if we have status information
        if any("status" in o for o in outcomes):
            success_rate = success_count / total_count if total_count > 0 else self.DEFAULT_SUCCESS_RATE
        else:
            success_rate = self.DEFAULT_SUCCESS_RATE

        # Calculate average turns
        turns_data = [o.get("turns") for o in outcomes if o.get("turns") is not None]
        if turns_data:
            avg_turns = sum(turns_data) / len(turns_data)
        else:
            avg_turns = self.DEFAULT_AVG_TURNS

        return avg_turns, success_rate
