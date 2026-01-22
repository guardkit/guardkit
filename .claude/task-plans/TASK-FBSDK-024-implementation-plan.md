# Implementation Plan: TASK-FBSDK-024

## Task Information
- **ID**: TASK-FBSDK-024
- **Title**: Create feature-code test case for quality gates
- **Complexity**: 3/10
- **Status**: in_progress
- **Created**: 2025-01-22T12:30:00Z

## Objective

Create a comprehensive test case for feature-build that validates quality gates work correctly for actual code implementation (not scaffolding). This complements FEAT-1D98 which exposed issues with scaffolding tasks having low architectural scores.

## Problem Context

FEAT-1D98 starts with Wave 1 scaffolding tasks (pyproject.toml, project structure) which consistently failed architectural review gates (score <60) across 5 turns. This is expected behavior for scaffolding, but it prevents us from validating that quality gates work correctly for feature code. We need a second test case that:

1. Starts with a code-focused task (not scaffolding)
2. Has sufficient architectural complexity to score well
3. Can be used to validate both success and failure scenarios
4. Serves as a reference for quality gate testing

## Implementation Strategy

### 1. Test Feature Structure

Create `tests/integration/test_features/FEAT-CODE-TEST/` directory with:
- Feature definition YAML (FEAT-CODE-TEST.yaml)
- Task markdown file (TASK-QGV-001-calculator-service.md)
- README explaining the test feature
- Expected outputs for validation

### 2. Test Integration Script

Create `tests/integration/test_quality_gate_validation.py` with:
- Setup fixtures for test feature
- Happy path test (well-structured code passes gates)
- Failure scenario tests (poor structure, missing tests)
- Cleanup utilities
- Integration with pytest

### 3. Documentation

Create `docs/testing/quality-gate-testing.md` with:
- Test execution procedures
- Expected outcomes
- Troubleshooting guide
- CI/CD integration instructions

## Detailed File-by-File Plan

### File 1: `tests/integration/test_features/FEAT-CODE-TEST/README.md`

**Purpose**: Explain the test feature structure and usage

**Content**:
- Overview of quality gate validation
- Relationship to FEAT-1D98
- How to run the test
- Expected outcomes

**Lines of Code**: ~50 lines

### File 2: `tests/integration/test_features/FEAT-CODE-TEST/FEAT-CODE-TEST.yaml`

**Purpose**: Feature definition for quality gate testing

**Content**:
```yaml
feature_id: FEAT-CODE-TEST
name: Quality Gate Validation Feature
description: Test feature for validating quality gates with actual code implementation
status: testing
tasks:
  - id: TASK-QGV-001
    title: Implement calculator service with SOLID principles
    wave: 1
    task_type: feature
    complexity: 4
    file: TASK-QGV-001-calculator-service.md
```

**Lines of Code**: ~10 lines

### File 3: `tests/integration/test_features/FEAT-CODE-TEST/TASK-QGV-001-calculator-service.md`

**Purpose**: Task definition with clear acceptance criteria for SOLID code

**Content**:
```markdown
---
id: TASK-QGV-001
title: Implement calculator service with SOLID principles
status: backlog
created: 2025-01-22T00:00:00Z
priority: medium
tags: [testing, quality-gates, solid-principles]
complexity: 4
---

# Task: Implement calculator service with SOLID principles

## Description

Implement a calculator service that demonstrates SOLID principles. This task is designed to have sufficient architectural complexity to pass quality gates while remaining simple enough to implement in 1-2 AutoBuild turns.

## Acceptance Criteria

- [ ] Single Responsibility Principle: One class per operation (Add, Subtract, Multiply, Divide)
- [ ] Open/Closed Principle: Extensible operation interface allowing new operations
- [ ] Liskov Substitution: All operations implement same interface
- [ ] Interface Segregation: Calculator depends on operation interface, not concrete classes
- [ ] Dependency Inversion: Operations injected into calculator via constructor
- [ ] 80%+ test coverage with passing tests
- [ ] Type hints for all functions and methods
- [ ] Docstrings for all public interfaces

## Implementation Notes

### Expected Structure

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

### Example Code Pattern

```python
from abc import ABC, abstractmethod

class Operation(ABC):
    @abstractmethod
    def execute(self, a: float, b: float) -> float:
        pass

class Add(Operation):
    def execute(self, a: float, b: float) -> float:
        return a + b

class Calculator:
    def __init__(self, operations: dict[str, Operation]):
        self.operations = operations

    def calculate(self, operation: str, a: float, b: float) -> float:
        if operation not in self.operations:
            raise ValueError(f"Unknown operation: {operation}")
        return self.operations[operation].execute(a, b)
```

## Quality Gate Expectations

- **Architectural Review**: Should score ≥60 (good SOLID adherence)
- **Test Coverage**: Should meet ≥80% threshold
- **Tests Passing**: All tests should pass
- **Plan Audit**: Should match implementation plan
```

**Lines of Code**: ~100 lines

### File 4: `tests/integration/test_features/FEAT-CODE-TEST/expected_structure.txt`

**Purpose**: Document expected directory structure after successful AutoBuild

**Content**:
```
src/calculator/
  __init__.py
  calculator.py
  operations.py

tests/calculator/
  __init__.py
  test_calculator.py
  test_operations.py
```

**Lines of Code**: ~10 lines

### File 5: `tests/integration/test_quality_gate_validation.py`

**Purpose**: Pytest integration test for quality gate validation

**Content**:
- Test fixtures for temporary feature directory
- Helper functions to setup/teardown test features
- Test case: Happy path (well-structured code passes gates)
- Test case: Poor structure scenario (monolithic code fails gates)
- Test case: Missing tests scenario (no tests fails coverage gate)
- Validation helpers to check Coach reports

**Key Functions**:
```python
@pytest.fixture
def test_feature_dir(tmp_path):
    """Create temporary directory for test feature."""
    feature_dir = tmp_path / "test_features" / "FEAT-CODE-TEST"
    feature_dir.mkdir(parents=True)
    return feature_dir

def setup_test_feature(feature_dir: Path) -> None:
    """Copy test feature files to temporary directory."""
    pass

def run_autobuild_on_feature(feature_id: str, max_turns: int = 5) -> dict:
    """Run AutoBuild and return results."""
    pass

def test_quality_gates_pass_for_good_code(test_feature_dir):
    """Verify quality gates pass for well-structured SOLID code."""
    # Setup
    setup_test_feature(test_feature_dir)

    # Execute
    result = run_autobuild_on_feature("FEAT-CODE-TEST", max_turns=3)

    # Verify
    assert result["status"] == "approved"
    assert result["tasks"][0]["quality_gates"]["arch_review_passed"] == True
    assert result["tasks"][0]["quality_gates"]["coverage_met"] == True
    assert result["tasks"][0]["quality_gates"]["tests_passed"] == True
    assert result["tasks"][0]["quality_gates"]["all_gates_passed"] == True

def test_quality_gates_fail_for_poor_structure(test_feature_dir):
    """Verify quality gates fail for monolithic code."""
    # This test would require modifying the task to request poor structure
    pass

def test_quality_gates_fail_for_missing_tests(test_feature_dir):
    """Verify quality gates fail when tests are missing."""
    # This test would require modifying acceptance criteria to skip tests
    pass
```

**Lines of Code**: ~200 lines

### File 6: `docs/testing/quality-gate-testing.md`

**Purpose**: Documentation for quality gate testing procedures

**Content**:
- Overview of quality gate system
- Test feature descriptions (FEAT-1D98 vs FEAT-CODE-TEST)
- Running tests manually
- Running tests in CI/CD
- Interpreting test results
- Troubleshooting guide
- Adding new test scenarios

**Sections**:
1. Introduction
2. Test Features Overview
3. Running Tests
4. Expected Outcomes
5. CI/CD Integration
6. Troubleshooting
7. Extending Tests

**Lines of Code**: ~250 lines

## Implementation Order

1. **Create test feature directory structure** (`tests/integration/test_features/FEAT-CODE-TEST/`)
2. **Create README.md** - Document test feature purpose
3. **Create FEAT-CODE-TEST.yaml** - Feature definition
4. **Create TASK-QGV-001-calculator-service.md** - Task with acceptance criteria
5. **Create expected_structure.txt** - Expected output structure
6. **Create test_quality_gate_validation.py** - Integration tests
7. **Create quality-gate-testing.md** - Documentation
8. **Run tests** - Verify everything works
9. **Update existing tests** - Ensure integration with existing test suite

## Estimated Metrics

- **Files Created**: 7 files
- **Lines of Code**: ~620 lines total
  - Test feature files: ~170 lines
  - Integration test: ~200 lines
  - Documentation: ~250 lines
- **Directories Created**: 1 (`tests/integration/test_features/FEAT-CODE-TEST/`)
- **Duration**: 2-3 hours
  - Planning: 30 minutes (done)
  - Implementation: 1.5 hours
  - Testing: 1 hour

## Quality Gates

### Architectural Review (Phase 2.5B)

Expected score: **75/100** (Good)

**SOLID Principles** (45/50):
- Single Responsibility: 9/10 - Clean separation of concerns
- Open/Closed: 9/10 - Test feature is extensible
- Liskov Substitution: 9/10 - Test structure follows interfaces
- Interface Segregation: 9/10 - Clear test contracts
- Dependency Inversion: 9/10 - Test fixtures well-structured

**DRY Principle** (20/25):
- Minimal code duplication in test utilities
- Reusable fixtures and helpers
- Minor duplication in task examples

**YAGNI Principle** (10/25):
- Creates comprehensive test infrastructure
- Some features may not be immediately needed
- Justified for long-term test maintainability

### Test Coverage (Phase 4.5)

- Target: 80%+ line coverage
- Integration tests will cover:
  - Feature setup/teardown
  - AutoBuild invocation
  - Quality gate validation
  - Report parsing

### Plan Audit (Phase 5.5)

- File count: 7 files (100% match)
- LOC variance: ±10% acceptable
- Duration variance: ±30% acceptable
- Scope creep: 0 violations expected

## Success Criteria

1. All 7 files created successfully
2. Integration test runs without errors
3. Documentation is clear and complete
4. Test can be executed manually via pytest
5. Test can be integrated into CI/CD pipeline
6. Quality gates validation works for both success and failure scenarios

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| AutoBuild API changes | Medium | Use stable public APIs, add version checks |
| Test fixture complexity | Low | Keep fixtures simple, document thoroughly |
| File path issues | Low | Use Path objects, test on multiple platforms |
| Coach report format changes | Medium | Use JSON schema validation, version guards |

## Related Tasks

- **TASK-FBSDK-019**: Write code review score calculation (dependency)
- **FEAT-1D98**: Existing test feature (comparison point)
- **TASK-REV-FB19**: Parent review task (architectural analysis)

## Notes

- This test complements FEAT-1D98 by focusing on feature code vs scaffolding
- Calculator service was chosen for its clear SOLID principles demonstration
- Test should be runnable both manually and in CI/CD
- Documentation should help future developers extend test coverage
