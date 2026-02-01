"""
Comprehensive Test Suite for DynamicBudgetCalculator

Tests the dynamic context budget calculation functionality including:
- ContextBudget dataclass
- DynamicBudgetCalculator class with calculate() method
- Base budget by complexity (simple/medium/complex)
- Budget adjustments for novelty, refinement, AutoBuild
- DEFAULT_ALLOCATION and AUTOBUILD_ALLOCATION percentages
- Allocation adjustments by task type, phase, and characteristics

Coverage Target: >=85%
Test Count: 45+ tests

References:
- TASK-GR6-002: Implement DynamicBudgetCalculator
- FEAT-GR-006: Job-Specific Context Retrieval
"""

import pytest
from unittest.mock import MagicMock
from dataclasses import is_dataclass, fields


# ============================================================================
# 1. ContextBudget Dataclass Tests (10 tests)
# ============================================================================

class TestContextBudgetDataclass:
    """Test ContextBudget dataclass definition."""

    def test_is_dataclass(self):
        """Test that ContextBudget is a proper dataclass."""
        from guardkit.knowledge.budget_calculator import ContextBudget

        assert is_dataclass(ContextBudget)

    def test_has_total_tokens_field(self):
        """Test that ContextBudget has total_tokens field."""
        from guardkit.knowledge.budget_calculator import ContextBudget

        field_names = {f.name for f in fields(ContextBudget)}
        assert "total_tokens" in field_names

    def test_has_default_allocation_fields(self):
        """Test that ContextBudget has all DEFAULT_ALLOCATION fields."""
        from guardkit.knowledge.budget_calculator import ContextBudget

        field_names = {f.name for f in fields(ContextBudget)}

        assert "feature_context" in field_names
        assert "similar_outcomes" in field_names
        assert "relevant_patterns" in field_names
        assert "architecture_context" in field_names
        assert "warnings" in field_names
        assert "domain_knowledge" in field_names

    def test_has_autobuild_allocation_fields(self):
        """Test that ContextBudget has AutoBuild allocation fields."""
        from guardkit.knowledge.budget_calculator import ContextBudget

        field_names = {f.name for f in fields(ContextBudget)}

        assert "role_constraints" in field_names
        assert "quality_gate_configs" in field_names
        assert "turn_states" in field_names
        assert "implementation_modes" in field_names

    def test_autobuild_fields_have_zero_defaults(self):
        """Test that AutoBuild fields default to 0.0."""
        from guardkit.knowledge.budget_calculator import ContextBudget

        budget = ContextBudget(
            total_tokens=4000,
            feature_context=0.15,
            similar_outcomes=0.25,
            relevant_patterns=0.20,
            architecture_context=0.20,
            warnings=0.15,
            domain_knowledge=0.05,
        )

        assert budget.role_constraints == 0.0
        assert budget.quality_gate_configs == 0.0
        assert budget.turn_states == 0.0
        assert budget.implementation_modes == 0.0

    def test_can_create_with_all_fields(self):
        """Test creating ContextBudget with all fields."""
        from guardkit.knowledge.budget_calculator import ContextBudget

        budget = ContextBudget(
            total_tokens=5000,
            feature_context=0.10,
            similar_outcomes=0.15,
            relevant_patterns=0.15,
            architecture_context=0.10,
            warnings=0.10,
            domain_knowledge=0.05,
            role_constraints=0.10,
            quality_gate_configs=0.10,
            turn_states=0.10,
            implementation_modes=0.05,
        )

        assert budget.total_tokens == 5000
        assert budget.role_constraints == 0.10
        assert budget.turn_states == 0.10

    def test_get_allocation_returns_integer_tokens(self):
        """Test that get_allocation returns integer token count."""
        from guardkit.knowledge.budget_calculator import ContextBudget

        budget = ContextBudget(
            total_tokens=4000,
            feature_context=0.15,
            similar_outcomes=0.25,
            relevant_patterns=0.20,
            architecture_context=0.20,
            warnings=0.15,
            domain_knowledge=0.05,
        )

        result = budget.get_allocation("feature_context")

        assert isinstance(result, int)
        assert result == 600  # 4000 * 0.15 = 600

    def test_get_allocation_for_all_categories(self):
        """Test get_allocation works for all category types."""
        from guardkit.knowledge.budget_calculator import ContextBudget

        budget = ContextBudget(
            total_tokens=4000,
            feature_context=0.15,
            similar_outcomes=0.25,
            relevant_patterns=0.20,
            architecture_context=0.20,
            warnings=0.15,
            domain_knowledge=0.05,
            role_constraints=0.10,
            quality_gate_configs=0.10,
            turn_states=0.10,
            implementation_modes=0.05,
        )

        # Test all categories
        assert budget.get_allocation("feature_context") == 600
        assert budget.get_allocation("similar_outcomes") == 1000
        assert budget.get_allocation("relevant_patterns") == 800
        assert budget.get_allocation("architecture_context") == 800
        assert budget.get_allocation("warnings") == 600
        assert budget.get_allocation("domain_knowledge") == 200
        assert budget.get_allocation("role_constraints") == 400
        assert budget.get_allocation("quality_gate_configs") == 400
        assert budget.get_allocation("turn_states") == 400
        assert budget.get_allocation("implementation_modes") == 200

    def test_get_allocation_unknown_category_returns_zero(self):
        """Test that get_allocation returns 0 for unknown category."""
        from guardkit.knowledge.budget_calculator import ContextBudget

        budget = ContextBudget(
            total_tokens=4000,
            feature_context=0.15,
            similar_outcomes=0.25,
            relevant_patterns=0.20,
            architecture_context=0.20,
            warnings=0.15,
            domain_knowledge=0.05,
        )

        result = budget.get_allocation("unknown_category")

        assert result == 0

    def test_total_tokens_is_integer(self):
        """Test that total_tokens is an integer."""
        from guardkit.knowledge.budget_calculator import ContextBudget

        budget = ContextBudget(
            total_tokens=4000,
            feature_context=0.15,
            similar_outcomes=0.25,
            relevant_patterns=0.20,
            architecture_context=0.20,
            warnings=0.15,
            domain_knowledge=0.05,
        )

        assert isinstance(budget.total_tokens, int)


# ============================================================================
# 2. DynamicBudgetCalculator Initialization Tests (3 tests)
# ============================================================================

class TestDynamicBudgetCalculatorInit:
    """Test DynamicBudgetCalculator initialization."""

    def test_calculator_can_be_instantiated(self):
        """Test creating a DynamicBudgetCalculator instance."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        calculator = DynamicBudgetCalculator()

        assert calculator is not None

    def test_calculator_has_base_budgets(self):
        """Test that calculator has BASE_BUDGETS constant."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        assert hasattr(DynamicBudgetCalculator, "BASE_BUDGETS")
        assert isinstance(DynamicBudgetCalculator.BASE_BUDGETS, dict)

    def test_calculator_has_allocation_constants(self):
        """Test that calculator has allocation constants."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        assert hasattr(DynamicBudgetCalculator, "DEFAULT_ALLOCATION")
        assert hasattr(DynamicBudgetCalculator, "AUTOBUILD_ALLOCATION")


# ============================================================================
# 3. BASE_BUDGETS Configuration Tests (5 tests)
# ============================================================================

class TestBaseBudgets:
    """Test BASE_BUDGETS configuration."""

    def test_simple_tasks_get_2000_tokens(self):
        """Test that complexity 1-3 gets 2000 tokens."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        budgets = DynamicBudgetCalculator.BASE_BUDGETS

        # Find the budget for complexity 1-3
        for (low, high), budget in budgets.items():
            if low <= 1 <= high and low <= 3 <= high:
                assert budget == 2000
                return

        pytest.fail("No budget range found for complexity 1-3")

    def test_medium_tasks_get_4000_tokens(self):
        """Test that complexity 4-6 gets 4000 tokens."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        budgets = DynamicBudgetCalculator.BASE_BUDGETS

        for (low, high), budget in budgets.items():
            if low <= 4 <= high and low <= 6 <= high:
                assert budget == 4000
                return

        pytest.fail("No budget range found for complexity 4-6")

    def test_complex_tasks_get_6000_tokens(self):
        """Test that complexity 7-10 gets 6000 tokens."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        budgets = DynamicBudgetCalculator.BASE_BUDGETS

        for (low, high), budget in budgets.items():
            if low <= 7 <= high and low <= 10 <= high:
                assert budget == 6000
                return

        pytest.fail("No budget range found for complexity 7-10")

    def test_base_budgets_covers_all_complexity_levels(self):
        """Test that BASE_BUDGETS covers complexity 1-10."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        budgets = DynamicBudgetCalculator.BASE_BUDGETS

        for complexity in range(1, 11):
            found = False
            for (low, high), budget in budgets.items():
                if low <= complexity <= high:
                    found = True
                    break
            assert found, f"No budget range for complexity {complexity}"

    def test_base_budgets_has_three_ranges(self):
        """Test that BASE_BUDGETS has exactly 3 ranges."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        budgets = DynamicBudgetCalculator.BASE_BUDGETS

        assert len(budgets) == 3


# ============================================================================
# 4. DEFAULT_ALLOCATION Tests (6 tests)
# ============================================================================

class TestDefaultAllocation:
    """Test DEFAULT_ALLOCATION configuration."""

    def test_default_allocation_has_all_keys(self):
        """Test that DEFAULT_ALLOCATION has all required keys."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        allocation = DynamicBudgetCalculator.DEFAULT_ALLOCATION

        expected_keys = {
            "feature_context",
            "similar_outcomes",
            "relevant_patterns",
            "architecture_context",
            "warnings",
            "domain_knowledge",
            "role_constraints",
            "quality_gate_configs",
            "turn_states",
            "implementation_modes",
        }

        assert set(allocation.keys()) == expected_keys

    def test_default_feature_context_allocation(self):
        """Test that feature_context is 0.15 (15%)."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        allocation = DynamicBudgetCalculator.DEFAULT_ALLOCATION

        assert allocation["feature_context"] == 0.15

    def test_default_similar_outcomes_allocation(self):
        """Test that similar_outcomes is 0.25 (25%)."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        allocation = DynamicBudgetCalculator.DEFAULT_ALLOCATION

        assert allocation["similar_outcomes"] == 0.25

    def test_default_relevant_patterns_allocation(self):
        """Test that relevant_patterns is 0.20 (20%)."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        allocation = DynamicBudgetCalculator.DEFAULT_ALLOCATION

        assert allocation["relevant_patterns"] == 0.20

    def test_default_autobuild_allocations_are_zero(self):
        """Test that AutoBuild allocations are 0 in DEFAULT."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        allocation = DynamicBudgetCalculator.DEFAULT_ALLOCATION

        assert allocation["role_constraints"] == 0.0
        assert allocation["quality_gate_configs"] == 0.0
        assert allocation["turn_states"] == 0.0
        assert allocation["implementation_modes"] == 0.0

    def test_default_allocation_sums_to_one(self):
        """Test that DEFAULT_ALLOCATION values sum to 1.0."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        allocation = DynamicBudgetCalculator.DEFAULT_ALLOCATION
        total = sum(allocation.values())

        assert abs(total - 1.0) < 0.001, f"DEFAULT_ALLOCATION sums to {total}, not 1.0"


# ============================================================================
# 5. AUTOBUILD_ALLOCATION Tests (6 tests)
# ============================================================================

class TestAutoBuildAllocation:
    """Test AUTOBUILD_ALLOCATION configuration."""

    def test_autobuild_allocation_has_all_keys(self):
        """Test that AUTOBUILD_ALLOCATION has all required keys."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        allocation = DynamicBudgetCalculator.AUTOBUILD_ALLOCATION

        expected_keys = {
            "feature_context",
            "similar_outcomes",
            "relevant_patterns",
            "architecture_context",
            "warnings",
            "domain_knowledge",
            "role_constraints",
            "quality_gate_configs",
            "turn_states",
            "implementation_modes",
        }

        assert set(allocation.keys()) == expected_keys

    def test_autobuild_role_constraints_allocation(self):
        """Test that role_constraints is 0.10 (10%) in AutoBuild."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        allocation = DynamicBudgetCalculator.AUTOBUILD_ALLOCATION

        assert allocation["role_constraints"] == 0.10

    def test_autobuild_quality_gate_configs_allocation(self):
        """Test that quality_gate_configs is 0.10 (10%) in AutoBuild."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        allocation = DynamicBudgetCalculator.AUTOBUILD_ALLOCATION

        assert allocation["quality_gate_configs"] == 0.10

    def test_autobuild_turn_states_allocation(self):
        """Test that turn_states is 0.10 (10%) in AutoBuild."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        allocation = DynamicBudgetCalculator.AUTOBUILD_ALLOCATION

        assert allocation["turn_states"] == 0.10

    def test_autobuild_implementation_modes_allocation(self):
        """Test that implementation_modes is 0.05 (5%) in AutoBuild."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        allocation = DynamicBudgetCalculator.AUTOBUILD_ALLOCATION

        assert allocation["implementation_modes"] == 0.05

    def test_autobuild_allocation_sums_to_one(self):
        """Test that AUTOBUILD_ALLOCATION values sum to 1.0."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        allocation = DynamicBudgetCalculator.AUTOBUILD_ALLOCATION
        total = sum(allocation.values())

        assert abs(total - 1.0) < 0.001, f"AUTOBUILD_ALLOCATION sums to {total}, not 1.0"


# ============================================================================
# 6. calculate() Method Tests (8 tests)
# ============================================================================

class TestCalculateMethod:
    """Test calculate() method."""

    def test_calculate_returns_context_budget(self):
        """Test that calculate() returns ContextBudget."""
        from guardkit.knowledge.budget_calculator import (
            DynamicBudgetCalculator,
            ContextBudget,
        )
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

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

        result = calculator.calculate(characteristics)

        assert isinstance(result, ContextBudget)

    def test_calculate_simple_task_base_budget(self):
        """Test that simple task (complexity 1-3) gets 2000 base tokens."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=2,  # Simple
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        # Base budget should be 2000 (no adjustments applied)
        assert result.total_tokens == 2000

    def test_calculate_medium_task_base_budget(self):
        """Test that medium task (complexity 4-6) gets 4000 base tokens."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Medium
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        # Base budget should be 4000 (no adjustments applied)
        assert result.total_tokens == 4000

    def test_calculate_complex_task_base_budget(self):
        """Test that complex task (complexity 7-10) gets 6000 base tokens."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=8,  # Complex
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        # Base budget should be 6000 (no adjustments applied)
        assert result.total_tokens == 6000

    def test_calculate_returns_allocations(self):
        """Test that calculate() returns proper allocations."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

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

        result = calculator.calculate(characteristics)

        # Check allocations are floats between 0 and 1
        assert 0 <= result.feature_context <= 1
        assert 0 <= result.similar_outcomes <= 1
        assert 0 <= result.relevant_patterns <= 1
        assert 0 <= result.architecture_context <= 1
        assert 0 <= result.warnings <= 1
        assert 0 <= result.domain_knowledge <= 1

    def test_calculate_allocation_sums_to_one(self):
        """Test that calculated allocation sums to 1.0."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

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

        result = calculator.calculate(characteristics)

        total = (
            result.feature_context
            + result.similar_outcomes
            + result.relevant_patterns
            + result.architecture_context
            + result.warnings
            + result.domain_knowledge
            + result.role_constraints
            + result.quality_gate_configs
            + result.turn_states
            + result.implementation_modes
        )

        assert abs(total - 1.0) < 0.001, f"Allocation sums to {total}, not 1.0"

    def test_calculate_has_calculate_method(self):
        """Test that DynamicBudgetCalculator has calculate method."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator

        calculator = DynamicBudgetCalculator()

        assert hasattr(calculator, "calculate")
        assert callable(calculator.calculate)

    def test_calculate_accepts_task_characteristics(self):
        """Test that calculate() accepts TaskCharacteristics parameter."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

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

        # Should not raise
        result = calculator.calculate(characteristics)
        assert result is not None


# ============================================================================
# 7. Novelty Adjustment Tests (4 tests)
# ============================================================================

class TestNoveltyAdjustment:
    """Test budget adjustment for task novelty."""

    def test_first_of_type_gets_30_percent_bonus(self):
        """Test that first-of-type task gets +30% budget."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Base 4000
            is_first_of_type=True,  # +30%
            similar_task_count=0,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        # 4000 * 1.3 = 5200
        assert result.total_tokens == 5200

    def test_few_similar_tasks_gets_15_percent_bonus(self):
        """Test that task with few similar tasks gets +15% budget."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Base 4000
            is_first_of_type=False,
            similar_task_count=2,  # < 3, +15%
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        # 4000 * 1.15 = 4600
        assert result.total_tokens == 4600

    def test_many_similar_tasks_no_bonus(self):
        """Test that task with many similar tasks gets no novelty bonus."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Base 4000
            is_first_of_type=False,
            similar_task_count=10,  # >= 3, no bonus
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        # No adjustment
        assert result.total_tokens == 4000

    def test_boundary_similar_task_count_three(self):
        """Test that similar_task_count=3 gets no bonus (boundary)."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Base 4000
            is_first_of_type=False,
            similar_task_count=3,  # Exactly 3, no bonus
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        # No adjustment at count=3
        assert result.total_tokens == 4000


# ============================================================================
# 8. Refinement Adjustment Tests (3 tests)
# ============================================================================

class TestRefinementAdjustment:
    """Test budget adjustment for refinement tasks."""

    def test_refinement_gets_20_percent_bonus(self):
        """Test that refinement task gets +20% budget."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Base 4000
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=True,  # +20%
            refinement_attempt=2,
            previous_failure_type="test_failure",
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        # 4000 * 1.2 = 4800
        assert result.total_tokens == 4800

    def test_non_refinement_no_bonus(self):
        """Test that non-refinement task gets no refinement bonus."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Base 4000
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,  # No bonus
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        # No adjustment
        assert result.total_tokens == 4000

    def test_refinement_combined_with_novelty(self):
        """Test that refinement and novelty bonuses stack."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Base 4000
            is_first_of_type=True,  # +30%: 4000 -> 5200
            similar_task_count=0,
            feature_id=None,
            is_refinement=True,  # +20%: 5200 -> 6240
            refinement_attempt=2,
            previous_failure_type="test_failure",
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        # 4000 * 1.3 * 1.2 = 6240
        assert result.total_tokens == 6240


# ============================================================================
# 9. AutoBuild Adjustment Tests (5 tests)
# ============================================================================

class TestAutoBuildAdjustment:
    """Test budget adjustment for AutoBuild tasks."""

    def test_autobuild_uses_autobuild_allocation(self):
        """Test that AutoBuild task uses AUTOBUILD_ALLOCATION."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

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
            is_autobuild=True,  # AutoBuild mode
            current_actor="player",
            turn_number=1,
            has_previous_turns=False,
        )

        result = calculator.calculate(characteristics)

        # AutoBuild should have non-zero AutoBuild allocations
        assert result.role_constraints > 0
        assert result.quality_gate_configs > 0
        assert result.turn_states >= 0  # May be 0 if no previous turns
        assert result.implementation_modes > 0

    def test_autobuild_later_turn_gets_15_percent_bonus(self):
        """Test that AutoBuild turn > 1 gets +15% budget."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Base 4000
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            is_autobuild=True,
            current_actor="player",
            turn_number=3,  # > 1, +15%
            has_previous_turns=False,
        )

        result = calculator.calculate(characteristics)

        # 4000 * 1.15 = 4600
        assert result.total_tokens == 4600

    def test_autobuild_has_previous_turns_gets_10_percent_bonus(self):
        """Test that AutoBuild with previous turns gets +10% budget."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Base 4000
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            is_autobuild=True,
            current_actor="player",
            turn_number=1,  # Not > 1
            has_previous_turns=True,  # +10%
        )

        result = calculator.calculate(characteristics)

        # 4000 * 1.10 = 4400
        assert result.total_tokens == 4400

    def test_autobuild_later_turn_with_history_stacks(self):
        """Test that later turn and history bonuses stack."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Base 4000
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            is_autobuild=True,
            current_actor="player",
            turn_number=3,  # +15%: 4000 -> 4600
            has_previous_turns=True,  # +10%: 4600 -> 5060
        )

        result = calculator.calculate(characteristics)

        # 4000 * 1.15 * 1.10 = 5060
        assert result.total_tokens == 5060

    def test_non_autobuild_no_autobuild_adjustment(self):
        """Test that non-AutoBuild task gets no AutoBuild adjustment."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Base 4000
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            is_autobuild=False,  # Not AutoBuild
            turn_number=3,  # Should be ignored
            has_previous_turns=True,  # Should be ignored
        )

        result = calculator.calculate(characteristics)

        # No adjustment (is_autobuild is False)
        assert result.total_tokens == 4000
        # Should use DEFAULT_ALLOCATION (AutoBuild fields = 0)
        assert result.role_constraints == 0.0
        assert result.quality_gate_configs == 0.0
        assert result.turn_states == 0.0
        assert result.implementation_modes == 0.0


# ============================================================================
# 10. Allocation by Task Type Tests (4 tests)
# ============================================================================

class TestAllocationByTaskType:
    """Test allocation adjustments by task type."""

    def test_review_task_type_adjusts_allocation(self):
        """Test that REVIEW task type increases pattern/architecture allocation."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.REVIEW,  # Review type
            current_phase=TaskPhase.REVIEW,
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

        result = calculator.calculate(characteristics)

        # Review should have higher patterns and architecture
        assert result.relevant_patterns >= 0.25
        assert result.architecture_context >= 0.20

    def test_planning_task_type_adjusts_allocation(self):
        """Test that PLANNING task type increases feature/architecture allocation."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.PLANNING,  # Planning type
            current_phase=TaskPhase.PLAN,
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

        result = calculator.calculate(characteristics)

        # Planning should have higher feature and architecture
        assert result.feature_context >= 0.20
        assert result.architecture_context >= 0.25

    def test_implementation_task_type_default_allocation(self):
        """Test that IMPLEMENTATION task type uses base allocation."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

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

        result = calculator.calculate(characteristics)

        # Should have reasonable allocation
        assert result.similar_outcomes > 0
        assert result.relevant_patterns > 0

    def test_refinement_task_type_adjusts_allocation(self):
        """Test that refinement adjusts allocation to emphasize warnings."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

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
            is_refinement=True,  # Refinement
            refinement_attempt=2,
            previous_failure_type="test_failure",
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        # Refinement should emphasize warnings and similar_outcomes
        assert result.warnings >= 0.25
        assert result.similar_outcomes >= 0.20


# ============================================================================
# 11. Allocation by Phase Tests (3 tests)
# ============================================================================

class TestAllocationByPhase:
    """Test allocation adjustments by current phase."""

    def test_implement_phase_adjusts_allocation(self):
        """Test that IMPLEMENT phase increases patterns/warnings allocation."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,  # Implement phase
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

        result = calculator.calculate(characteristics)

        # Implement phase should have higher patterns and warnings
        assert result.relevant_patterns >= 0.20
        assert result.warnings >= 0.15

    def test_test_phase_adjusts_allocation(self):
        """Test that TEST phase increases similar_outcomes allocation."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.TEST,  # Test phase
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

        result = calculator.calculate(characteristics)

        # Test phase should have higher similar_outcomes for test patterns
        assert result.similar_outcomes >= 0.30

    def test_load_phase_uses_default_allocation(self):
        """Test that LOAD phase uses default allocation."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.LOAD,  # Load phase
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

        result = calculator.calculate(characteristics)

        # Load phase should use reasonable defaults
        assert result.total_tokens == 4000


# ============================================================================
# 12. AutoBuild Allocation Adjustment Tests (4 tests)
# ============================================================================

class TestAutoBuildAllocationAdjustment:
    """Test allocation adjustments for AutoBuild characteristics."""

    def test_player_actor_emphasizes_role_constraints(self):
        """Test that player actor emphasizes role_constraints."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

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
            is_autobuild=True,
            current_actor="player",  # Player
            turn_number=1,
            has_previous_turns=False,
        )

        result = calculator.calculate(characteristics)

        # Player should have emphasized role_constraints and implementation_modes
        assert result.role_constraints >= 0.10
        assert result.implementation_modes >= 0.05

    def test_coach_actor_emphasizes_quality_gates(self):
        """Test that coach actor emphasizes quality_gate_configs."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.REVIEW,
            complexity=5,
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            is_autobuild=True,
            current_actor="coach",  # Coach
            turn_number=1,
            has_previous_turns=False,
        )

        result = calculator.calculate(characteristics)

        # Coach should have emphasized quality_gate_configs
        assert result.quality_gate_configs >= 0.10

    def test_later_turn_emphasizes_turn_states(self):
        """Test that later turn (> 1) emphasizes turn_states."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

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
            is_autobuild=True,
            current_actor="player",
            turn_number=3,  # Later turn
            has_previous_turns=True,
        )

        result = calculator.calculate(characteristics)

        # Later turns should have emphasized turn_states
        assert result.turn_states >= 0.10

    def test_autobuild_refinement_emphasizes_turn_states_and_warnings(self):
        """Test that AutoBuild refinement emphasizes turn_states and warnings."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

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
            is_refinement=True,  # Refinement
            refinement_attempt=2,
            previous_failure_type="test_failure",
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            is_autobuild=True,
            current_actor="player",
            turn_number=3,
            has_previous_turns=True,
        )

        result = calculator.calculate(characteristics)

        # AutoBuild refinement should emphasize turn_states and warnings
        assert result.turn_states >= 0.15
        assert result.warnings >= 0.10


# ============================================================================
# 13. Edge Cases and Boundary Tests (4 tests)
# ============================================================================

class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""

    def test_complexity_boundary_1(self):
        """Test complexity=1 (minimum) gets simple budget."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=1,  # Minimum
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        assert result.total_tokens == 2000

    def test_complexity_boundary_10(self):
        """Test complexity=10 (maximum) gets complex budget."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=10,  # Maximum
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        assert result.total_tokens == 6000

    def test_out_of_range_complexity_uses_default(self):
        """Test that out-of-range complexity uses default budget."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=15,  # Out of range
            is_first_of_type=False,
            similar_task_count=10,
            feature_id=None,
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
        )

        result = calculator.calculate(characteristics)

        # Should use default (4000)
        assert result.total_tokens == 4000

    def test_all_adjustments_combined(self):
        """Test combining all budget adjustments."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,  # Base 4000
            is_first_of_type=True,  # +30%: 4000 -> 5200
            similar_task_count=0,
            feature_id=None,
            is_refinement=True,  # +20%: 5200 -> 6240
            refinement_attempt=2,
            previous_failure_type="test_failure",
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            is_autobuild=True,  # +15% (turn > 1): 6240 -> 7176
            current_actor="player",
            turn_number=3,
            has_previous_turns=True,  # +10%: 7176 -> 7893
        )

        result = calculator.calculate(characteristics)

        # Sequential integer truncation (not single multiplication):
        # 4000 -> int(4000 * 1.3) = 5200
        # 5200 -> int(5200 * 1.2) = 6240
        # 6240 -> int(6240 * 1.15) = 7175 (floating point: 7175.999...)
        # 7175 -> int(7175 * 1.10) = 7892
        assert result.total_tokens == 7892
