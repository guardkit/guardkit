# FEAT-CODE-TEST: Quality Gate Validation Feature

## Overview

This test feature validates that GuardKit's quality gates work correctly for actual code implementation tasks (not scaffolding). It complements FEAT-1D98 which focuses on scaffolding tasks like project setup and configuration.

## Purpose

**FEAT-CODE-TEST** demonstrates quality gate validation for:
- Code with clear architectural principles (SOLID)
- Meaningful test coverage thresholds
- Proper separation of concerns
- Production-like implementation patterns

## Relationship to FEAT-1D98

| Feature | Focus | First Task Type | Quality Gate Challenge |
|---------|-------|-----------------|------------------------|
| **FEAT-1D98** | FastAPI Health App | Scaffolding (pyproject.toml) | Low arch scores expected for config |
| **FEAT-CODE-TEST** | Calculator Service | Feature Code (SOLID implementation) | High arch scores expected for code |

### Why Two Test Features?

1. **FEAT-1D98** exposed a real issue: scaffolding tasks consistently fail architectural review gates (score <60) because configuration files don't demonstrate SOLID principles. This is expected behavior.

2. **FEAT-CODE-TEST** validates the positive case: well-structured feature code should pass quality gates with high architectural scores (≥60).

Together, these tests ensure:
- ✅ Scaffolding tasks are handled appropriately (skipped gates or adjusted thresholds)
- ✅ Feature code is properly validated (full quality gates applied)

## Task Structure

### TASK-QGV-001: Calculator Service with SOLID Principles

**Complexity**: 4/10
**Wave**: 1
**Type**: Feature implementation

**Acceptance Criteria**:
- Single Responsibility: One class per operation
- Open/Closed: Extensible operation interface
- Liskov Substitution: All operations implement same interface
- Interface Segregation: Calculator depends on operation interface
- Dependency Inversion: Operations injected into calculator
- 80%+ test coverage
- All tests passing

**Expected Architectural Score**: ≥60 (should pass gates)

### Expected Implementation Structure

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

## Running the Test

### Manual Execution

```bash
# Run via pytest
pytest tests/integration/test_quality_gate_validation.py::test_quality_gates_pass_for_good_code -v

# Run via AutoBuild directly (for debugging)
guardkit autobuild feature FEAT-CODE-TEST --max-turns 5
```

### Expected Outcomes

#### Happy Path (Well-Structured Code)
- AutoBuild completes in 1-3 turns
- Architectural review score ≥60
- Test coverage ≥80%
- All tests passing
- Coach approves implementation

#### Failure Scenarios
- **Poor Structure**: Monolithic code → Arch score <60 → Coach provides feedback
- **Missing Tests**: No tests → Coverage <80% → Coach provides feedback
- **Failing Tests**: Broken tests → Test gate fails → Coach provides feedback

## Validation Points

The integration test validates:

1. **Quality Gate Execution**: All gates (arch review, coverage, tests) are evaluated
2. **Coach Decision**: Coach correctly approves or rejects based on gate results
3. **Report Generation**: Player and Coach reports are created with correct structure
4. **State Management**: Task transitions through correct states (backlog → design_approved → in_review)
5. **Worktree Preservation**: Failed attempts preserve worktree for debugging

## CI/CD Integration

```yaml
# .github/workflows/quality-gate-tests.yml
name: Quality Gate Tests

on: [push, pull_request]

jobs:
  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e ".[autobuild]"
          pip install pytest pytest-cov
      - name: Run quality gate validation tests
        run: |
          pytest tests/integration/test_quality_gate_validation.py -v --cov
```

## Troubleshooting

### Issue: Test fails with "feature not found"

**Solution**: Ensure FEAT-CODE-TEST.yaml is in the correct location:
```bash
ls -la tests/integration/test_features/FEAT-CODE-TEST/FEAT-CODE-TEST.yaml
```

### Issue: AutoBuild times out

**Solution**: Increase max_turns or check SDK timeout:
```python
result = run_autobuild_on_feature("FEAT-CODE-TEST", max_turns=10)
```

### Issue: Architectural score lower than expected

**Solution**: Review Coach reports to see specific feedback:
```bash
cat .guardkit/autobuild/TASK-QGV-001/coach_turn_1.json | jq '.quality_gates'
```

## Related Documentation

- [Quality Gate Testing Guide](../../../../docs/testing/quality-gate-testing.md)
- [FEAT-1D98 Test Execution Log](../../../../docs/reviews/feature-build/after_FBSDK-015_016_017.md)
- [Task Type Profiles](../../../../docs/guides/task-type-profiles.md)
- [CoachValidator Implementation](../../../../guardkit/orchestrator/quality_gates/coach_validator.py)

## Maintenance

### Adding New Test Scenarios

1. Create new task markdown in this directory
2. Add task to FEAT-CODE-TEST.yaml
3. Create corresponding test in test_quality_gate_validation.py
4. Update this README with new scenario description

### Updating Thresholds

If quality gate thresholds change:
1. Update TASK-QGV-001 acceptance criteria
2. Update test assertions in test_quality_gate_validation.py
3. Update documentation in quality-gate-testing.md

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-22 | Initial creation as part of TASK-FBSDK-024 |
