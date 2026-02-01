"""
Dynamic Budget Calculator for context retrieval.

This module provides the DynamicBudgetCalculator class for calculating
context budget and allocation based on task characteristics. It supports
both standard tasks and AutoBuild-specific allocations.

Public API:
    ContextBudget: Dataclass for budget allocation
    DynamicBudgetCalculator: Main calculator class

Example:
    from guardkit.knowledge.budget_calculator import (
        DynamicBudgetCalculator,
        ContextBudget,
    )
    from guardkit.knowledge.task_analyzer import TaskCharacteristics

    calculator = DynamicBudgetCalculator()
    budget = calculator.calculate(characteristics)

    # Get token allocation for a category
    pattern_tokens = budget.get_allocation("relevant_patterns")

References:
    - TASK-GR6-002: Implement DynamicBudgetCalculator
    - FEAT-GR-006: Job-Specific Context Retrieval
"""

from dataclasses import dataclass
from typing import Dict

from .task_analyzer import TaskCharacteristics, TaskType, TaskPhase


@dataclass
class ContextBudget:
    """Budget allocation for context retrieval.

    Contains total token budget and percentage allocations for each
    context category. AutoBuild categories default to 0.0 for standard
    tasks and are populated for AutoBuild workflows.

    Attributes:
        total_tokens: Total token budget for context retrieval
        feature_context: Allocation for feature context (0.0-1.0)
        similar_outcomes: Allocation for similar task outcomes (0.0-1.0)
        relevant_patterns: Allocation for relevant patterns (0.0-1.0)
        architecture_context: Allocation for architecture context (0.0-1.0)
        warnings: Allocation for warnings/failures (0.0-1.0)
        domain_knowledge: Allocation for domain knowledge (0.0-1.0)
        role_constraints: Allocation for role constraints (AutoBuild)
        quality_gate_configs: Allocation for quality gate configs (AutoBuild)
        turn_states: Allocation for turn states (AutoBuild)
        implementation_modes: Allocation for implementation modes (AutoBuild)

    Example:
        budget = ContextBudget(
            total_tokens=4000,
            feature_context=0.15,
            similar_outcomes=0.25,
            relevant_patterns=0.20,
            architecture_context=0.20,
            warnings=0.15,
            domain_knowledge=0.05,
        )

        # Get token allocation for patterns
        pattern_tokens = budget.get_allocation("relevant_patterns")
        assert pattern_tokens == 800  # 4000 * 0.20
    """

    total_tokens: int

    # Standard allocation percentages (must sum to 1.0)
    feature_context: float
    similar_outcomes: float
    relevant_patterns: float
    architecture_context: float
    warnings: float
    domain_knowledge: float

    # AutoBuild allocations (default to 0.0 for standard tasks)
    role_constraints: float = 0.0
    quality_gate_configs: float = 0.0
    turn_states: float = 0.0
    implementation_modes: float = 0.0

    def get_allocation(self, category: str) -> int:
        """Get token allocation for a category.

        Args:
            category: Category name (e.g., "feature_context", "warnings")

        Returns:
            Integer token count for the category (0 if unknown category)

        Example:
            tokens = budget.get_allocation("similar_outcomes")
        """
        allocation_map = {
            "feature_context": self.feature_context,
            "similar_outcomes": self.similar_outcomes,
            "relevant_patterns": self.relevant_patterns,
            "architecture_context": self.architecture_context,
            "warnings": self.warnings,
            "domain_knowledge": self.domain_knowledge,
            # AutoBuild categories
            "role_constraints": self.role_constraints,
            "quality_gate_configs": self.quality_gate_configs,
            "turn_states": self.turn_states,
            "implementation_modes": self.implementation_modes,
        }

        return int(self.total_tokens * allocation_map.get(category, 0))


class DynamicBudgetCalculator:
    """Calculates context budget based on task characteristics.

    The DynamicBudgetCalculator determines the appropriate context budget
    and allocation percentages based on task complexity, novelty, refinement
    status, and AutoBuild characteristics.

    Class Attributes:
        BASE_BUDGETS: Mapping of complexity ranges to base token budgets
        DEFAULT_ALLOCATION: Standard allocation percentages
        AUTOBUILD_ALLOCATION: AutoBuild-specific allocation percentages

    Example:
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Implement user auth",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=6,
            is_first_of_type=True,
            similar_task_count=0,
            feature_id="FEAT-AUTH",
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        budget = calculator.calculate(characteristics)
        print(f"Total budget: {budget.total_tokens}")  # 5200 (4000 * 1.3)
    """

    # Base budgets by complexity range
    # Simple (1-3): 2000 tokens
    # Medium (4-6): 4000 tokens
    # Complex (7-10): 6000 tokens
    BASE_BUDGETS: Dict[tuple, int] = {
        (1, 3): 2000,   # Simple tasks
        (4, 6): 4000,   # Medium tasks
        (7, 10): 6000,  # Complex tasks
    }

    # Default allocation for standard tasks (sums to 1.0)
    DEFAULT_ALLOCATION: Dict[str, float] = {
        "feature_context": 0.15,
        "similar_outcomes": 0.25,
        "relevant_patterns": 0.20,
        "architecture_context": 0.20,
        "warnings": 0.15,
        "domain_knowledge": 0.05,
        # AutoBuild allocations are 0 for standard tasks
        "role_constraints": 0.0,
        "quality_gate_configs": 0.0,
        "turn_states": 0.0,
        "implementation_modes": 0.0,
    }

    # AutoBuild-specific allocation (sums to 1.0)
    AUTOBUILD_ALLOCATION: Dict[str, float] = {
        "feature_context": 0.10,
        "similar_outcomes": 0.15,
        "relevant_patterns": 0.15,
        "architecture_context": 0.10,
        "warnings": 0.10,
        "domain_knowledge": 0.05,
        "role_constraints": 0.10,      # Player/Coach boundaries
        "quality_gate_configs": 0.10,  # Task-type thresholds
        "turn_states": 0.10,           # Previous turn context
        "implementation_modes": 0.05,  # Direct vs task-work
    }

    def calculate(self, characteristics: TaskCharacteristics) -> ContextBudget:
        """Calculate context budget based on task characteristics.

        Applies the following adjustments to base budget:
        - Novelty: +30% for first-of-type, +15% for few similar tasks
        - Refinement: +20% for refinement attempts
        - AutoBuild: +15% for later turns, +10% for previous turn history

        Args:
            characteristics: TaskCharacteristics with task properties

        Returns:
            ContextBudget with total tokens and allocation percentages

        Example:
            budget = calculator.calculate(characteristics)
            print(f"Budget: {budget.total_tokens} tokens")
        """
        # Start with base budget from complexity
        total = self._get_base_budget(characteristics.complexity)

        # Adjust for novelty (first-of-type or few similar tasks)
        total = self._adjust_for_novelty(total, characteristics)

        # Adjust for refinement attempts
        total = self._adjust_for_refinement(total, characteristics)

        # Adjust for AutoBuild workflows
        if characteristics.is_autobuild:
            total = self._adjust_for_autobuild(total, characteristics)

        # Calculate allocation percentages
        allocation = self._calculate_allocation(characteristics)

        return ContextBudget(
            total_tokens=total,
            **allocation,
        )

    def _get_base_budget(self, complexity: int) -> int:
        """Get base budget from complexity level.

        Args:
            complexity: Task complexity (1-10)

        Returns:
            Base token budget (2000, 4000, or 6000)
        """
        for (low, high), budget in self.BASE_BUDGETS.items():
            if low <= complexity <= high:
                return budget
        # Default for out-of-range complexity
        return 4000

    def _adjust_for_novelty(
        self,
        budget: int,
        char: TaskCharacteristics,
    ) -> int:
        """Adjust budget for task novelty.

        First-of-type tasks get +30% budget.
        Tasks with < 3 similar tasks get +15% budget.

        Args:
            budget: Current budget
            char: Task characteristics

        Returns:
            Adjusted budget
        """
        if char.is_first_of_type:
            # First of type needs more context
            budget = int(budget * 1.3)
        elif char.similar_task_count < 3:
            # Few similar tasks
            budget = int(budget * 1.15)

        return budget

    def _adjust_for_refinement(
        self,
        budget: int,
        char: TaskCharacteristics,
    ) -> int:
        """Adjust budget for refinement attempts.

        Refinement tasks get +20% budget for failure context.

        Args:
            budget: Current budget
            char: Task characteristics

        Returns:
            Adjusted budget
        """
        if char.is_refinement:
            # Refinement needs more context about what failed
            budget = int(budget * 1.2)

        return budget

    def _adjust_for_autobuild(
        self,
        budget: int,
        char: TaskCharacteristics,
    ) -> int:
        """Adjust budget for AutoBuild workflows.

        Later turns (> 1) get +15% for turn context.
        Previous turn history gets +10% for learning.

        Args:
            budget: Current budget
            char: Task characteristics

        Returns:
            Adjusted budget
        """
        if char.turn_number > 1:
            # Later turns need more context about previous turns
            budget = int(budget * 1.15)

        if char.has_previous_turns:
            # Has turn history to load
            budget = int(budget * 1.10)

        return budget

    def _calculate_allocation(
        self,
        char: TaskCharacteristics,
    ) -> Dict[str, float]:
        """Calculate allocation percentages based on characteristics.

        Uses AutoBuild allocation for feature-build mode, otherwise
        adjusts default allocation based on task type, phase, and
        refinement status.

        Args:
            char: Task characteristics

        Returns:
            Dictionary of allocation percentages (sums to 1.0)
        """
        # Use AutoBuild allocation if in feature-build mode
        if char.is_autobuild:
            allocation = self.AUTOBUILD_ALLOCATION.copy()
            return self._adjust_autobuild_allocation(allocation, char)

        # Start with default allocation
        allocation = self.DEFAULT_ALLOCATION.copy()

        # Adjust for task type
        if char.task_type == TaskType.REVIEW:
            # Reviews need more patterns and architecture
            allocation["relevant_patterns"] = 0.30
            allocation["architecture_context"] = 0.25
            allocation["similar_outcomes"] = 0.15

        elif char.task_type == TaskType.PLANNING:
            # Planning needs architecture and feature context
            allocation["feature_context"] = 0.25
            allocation["architecture_context"] = 0.30
            allocation["similar_outcomes"] = 0.15

        # Adjust for phase
        if char.current_phase == TaskPhase.IMPLEMENT:
            # Implementation needs patterns and warnings
            allocation["relevant_patterns"] = 0.30
            allocation["warnings"] = 0.20

        elif char.current_phase == TaskPhase.TEST:
            # Testing needs similar outcomes for test patterns
            allocation["similar_outcomes"] = 0.35

        # Adjust for refinement (highest priority - overrides other adjustments)
        if char.is_refinement:
            # Emphasize warnings and similar fixes
            allocation["warnings"] = 0.35
            allocation["similar_outcomes"] = 0.30
            allocation["relevant_patterns"] = 0.15
            allocation["architecture_context"] = 0.10
            allocation["feature_context"] = 0.05
            allocation["domain_knowledge"] = 0.05

        # Adjust for novelty (only if not refinement)
        elif char.is_first_of_type:
            # More architecture and patterns for new task types
            allocation["architecture_context"] = 0.30
            allocation["relevant_patterns"] = 0.25

        # Normalize to sum to 1.0
        total = sum(allocation.values())
        return {k: v / total for k, v in allocation.items()}

    def _adjust_autobuild_allocation(
        self,
        allocation: Dict[str, float],
        char: TaskCharacteristics,
    ) -> Dict[str, float]:
        """Adjust allocation for AutoBuild-specific context.

        Emphasizes different context based on current actor and turn number.
        For later turns (turn_number > 1), allocates 15-20% to turn_states
        for cross-turn learning.

        Args:
            allocation: Base AutoBuild allocation
            char: Task characteristics

        Returns:
            Adjusted allocation (normalized to 1.0)
        """
        # Emphasize role constraints based on current actor
        if char.current_actor == "player":
            allocation["role_constraints"] = 0.15  # Player needs clear boundaries
            allocation["implementation_modes"] = 0.10  # Player needs mode guidance
        elif char.current_actor == "coach":
            allocation["role_constraints"] = 0.12
            allocation["quality_gate_configs"] = 0.15  # Coach needs gate thresholds

        # Emphasize turn states for later turns (TASK-GR6-009: 15-20% allocation)
        if char.turn_number > 1:
            # Set turn_states to 17.5% pre-normalization (middle of 15-20% range)
            # Reduce other categories proportionally to maintain sum near 1.0
            allocation["turn_states"] = 0.175  # Target 15-20% after normalization
            allocation["similar_outcomes"] = 0.08  # Reduce from default
            allocation["feature_context"] = 0.08  # Reduce from default

        # After rejection (refinement), emphasize what went wrong even more
        if char.is_refinement:
            allocation["turn_states"] = 0.20  # Load rejection feedback (top of 15-20%)
            allocation["warnings"] = 0.15
            allocation["similar_outcomes"] = 0.08  # Further reduced

        # Normalize to sum to 1.0
        total = sum(allocation.values())
        return {k: v / total for k, v in allocation.items()}
