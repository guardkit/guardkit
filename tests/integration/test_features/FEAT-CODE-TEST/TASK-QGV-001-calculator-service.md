---
id: TASK-QGV-001
title: Implement calculator service with SOLID principles
status: backlog
created: 2025-01-22T00:00:00Z
priority: medium
tags: [testing, quality-gates, solid-principles, calculator]
complexity: 4
---

# Task: Implement calculator service with SOLID principles

## Description

Implement a calculator service that demonstrates SOLID principles. This task is designed to have sufficient architectural complexity to pass quality gates while remaining simple enough to implement in 1-2 AutoBuild turns.

This task serves as a test case for validating that GuardKit's quality gates work correctly for well-structured feature code (as opposed to scaffolding tasks which may have low architectural scores).

## Acceptance Criteria

- [ ] **Single Responsibility Principle**: One class per operation (Add, Subtract, Multiply, Divide)
- [ ] **Open/Closed Principle**: Extensible operation interface allowing new operations without modifying existing code
- [ ] **Liskov Substitution**: All operations implement the same interface and can be substituted for each other
- [ ] **Interface Segregation**: Calculator depends on operation interface, not concrete operation classes
- [ ] **Dependency Inversion**: Operations injected into calculator via constructor (dependency injection)
- [ ] **Test Coverage**: 80%+ coverage with all tests passing
- [ ] **Type Hints**: All functions and methods have type hints
- [ ] **Documentation**: Docstrings for all public interfaces

## Implementation Notes

### Expected Directory Structure

```
src/calculator/
  __init__.py
  calculator.py          # Main calculator class
  operations.py          # Operation interface and implementations

tests/calculator/
  __init__.py
  test_calculator.py     # Integration tests
  test_operations.py     # Unit tests for operations
```

### Design Pattern: Strategy Pattern

This task implements the Strategy pattern to demonstrate SOLID principles:

**Operation Interface** (Strategy):
```python
from abc import ABC, abstractmethod

class Operation(ABC):
    """Abstract base class for calculator operations."""

    @abstractmethod
    def execute(self, a: float, b: float) -> float:
        """Execute the operation on two numbers.

        Args:
            a: First operand
            b: Second operand

        Returns:
            Result of the operation
        """
        pass
```

**Concrete Strategies** (Operations):
```python
class Add(Operation):
    """Addition operation."""

    def execute(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b


class Subtract(Operation):
    """Subtraction operation."""

    def execute(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b


class Multiply(Operation):
    """Multiplication operation."""

    def execute(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b


class Divide(Operation):
    """Division operation."""

    def execute(self, a: float, b: float) -> float:
        """Divide a by b.

        Raises:
            ValueError: If b is zero
        """
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
```

**Context** (Calculator):
```python
class Calculator:
    """Calculator that supports multiple operations via dependency injection."""

    def __init__(self, operations: dict[str, Operation]):
        """Initialize calculator with supported operations.

        Args:
            operations: Dictionary mapping operation names to Operation instances
        """
        self.operations = operations

    def calculate(self, operation: str, a: float, b: float) -> float:
        """Execute a calculation.

        Args:
            operation: Name of the operation (e.g., "add", "subtract")
            a: First operand
            b: Second operand

        Returns:
            Result of the calculation

        Raises:
            ValueError: If operation is not supported
        """
        if operation not in self.operations:
            raise ValueError(f"Unknown operation: {operation}")
        return self.operations[operation].execute(a, b)

    def add_operation(self, name: str, operation: Operation) -> None:
        """Add a new operation to the calculator.

        Args:
            name: Name of the operation
            operation: Operation instance

        Demonstrates Open/Closed Principle: extends functionality without
        modifying existing code.
        """
        self.operations[name] = operation
```

### Test Examples

**Unit Tests for Operations** (`tests/calculator/test_operations.py`):
```python
import pytest
from src.calculator.operations import Add, Subtract, Multiply, Divide


def test_add_operation():
    add = Add()
    assert add.execute(2, 3) == 5
    assert add.execute(-1, 1) == 0
    assert add.execute(0.1, 0.2) == pytest.approx(0.3)


def test_subtract_operation():
    subtract = Subtract()
    assert subtract.execute(5, 3) == 2
    assert subtract.execute(0, 5) == -5


def test_multiply_operation():
    multiply = Multiply()
    assert multiply.execute(2, 3) == 6
    assert multiply.execute(-2, 3) == -6
    assert multiply.execute(0, 100) == 0


def test_divide_operation():
    divide = Divide()
    assert divide.execute(6, 2) == 3
    assert divide.execute(5, 2) == 2.5


def test_divide_by_zero():
    divide = Divide()
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide.execute(5, 0)
```

**Integration Tests for Calculator** (`tests/calculator/test_calculator.py`):
```python
import pytest
from src.calculator.calculator import Calculator
from src.calculator.operations import Add, Subtract, Multiply, Divide, Operation


@pytest.fixture
def calculator():
    """Create a calculator with standard operations."""
    return Calculator({
        "add": Add(),
        "subtract": Subtract(),
        "multiply": Multiply(),
        "divide": Divide()
    })


def test_calculator_addition(calculator):
    assert calculator.calculate("add", 2, 3) == 5


def test_calculator_subtraction(calculator):
    assert calculator.calculate("subtract", 5, 3) == 2


def test_calculator_multiplication(calculator):
    assert calculator.calculate("multiply", 4, 5) == 20


def test_calculator_division(calculator):
    assert calculator.calculate("divide", 10, 2) == 5


def test_calculator_unknown_operation(calculator):
    with pytest.raises(ValueError, match="Unknown operation: power"):
        calculator.calculate("power", 2, 3)


def test_calculator_extensibility():
    """Test Open/Closed Principle: adding new operations."""
    class Power(Operation):
        def execute(self, a: float, b: float) -> float:
            return a ** b

    calc = Calculator({"add": Add()})
    calc.add_operation("power", Power())
    assert calc.calculate("power", 2, 3) == 8
```

## Quality Gate Expectations

This task is designed to pass all quality gates when properly implemented:

### Architectural Review
- **Expected Score**: ≥60 (Good to Excellent)
- **SOLID Principles**: 40-45/50
  - Clear separation of concerns (SRP)
  - Extensible design (OCP)
  - Proper abstraction (DIP)
- **DRY**: 18-20/25
  - Minimal duplication
  - Reusable operation interface
- **YAGNI**: 15-20/25
  - Focused implementation
  - No unnecessary complexity

### Test Coverage
- **Threshold**: ≥80% line coverage
- **Expected**: ~90% coverage
  - All operations tested
  - Calculator integration tested
  - Edge cases covered (division by zero, etc.)

### Tests Passing
- **Requirement**: 100% tests passing
- **Expected**: All tests pass
  - Unit tests for each operation
  - Integration tests for calculator
  - Edge case tests

### Plan Audit
- **File Count**: 6 files expected
- **LOC Variance**: ±20% acceptable
- **Scope**: No scope creep expected

## Design Rationale

### Why Calculator Service?

1. **Clear SOLID Demonstration**: Calculator operations naturally demonstrate all five SOLID principles
2. **Simple Domain**: Everyone understands basic arithmetic operations
3. **Testable**: Easy to write comprehensive tests with clear assertions
4. **Extensible**: Easy to add new operations (power, modulo, etc.)
5. **Appropriate Complexity**: Not too simple (like "hello world") but not too complex

### Why Strategy Pattern?

1. **SOLID Alignment**: Strategy pattern naturally follows SOLID principles
2. **Dependency Injection**: Demonstrates DIP through constructor injection
3. **Open/Closed**: New operations can be added without modifying calculator
4. **Testability**: Each operation and the calculator can be tested independently

## Related Files

- Feature definition: `FEAT-CODE-TEST.yaml`
- Test feature README: `README.md`
- Integration test: `tests/integration/test_quality_gate_validation.py`
- Documentation: `docs/testing/quality-gate-testing.md`

## Notes

- This task is a test fixture, not a production implementation
- Focus is on demonstrating SOLID principles clearly
- Code should be simple and readable, not production-optimized
- Tests should be comprehensive to ensure quality gates work correctly
