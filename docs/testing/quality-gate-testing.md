# Quality Gate Testing Guide

## Overview

This guide explains how to test GuardKit's quality gates using dedicated test features. Quality gates ensure that code meets minimum standards for architecture, testing, and maintainability before being approved.

**Quality Gates**:
1. **Architectural Review**: SOLID/DRY/YAGNI principles (threshold: ≥60/100)
2. **Test Coverage**: Line and branch coverage (thresholds: ≥80% lines, ≥75% branches)
3. **Tests Passing**: All tests must pass (threshold: 100%)
4. **Plan Audit**: Implementation matches plan (variance thresholds: ±20% LOC, ±30% duration)

## Test Features Overview

GuardKit includes two complementary test features for validating quality gates:

### FEAT-1D98: FastAPI Health App (Scaffolding Focus)

**Purpose**: Validate workflow for scaffolding tasks (configuration files, project setup)

**First Task**: TASK-HLTH-61B6 - Setup project structure and pyproject.toml

**Expected Behavior**:
- Architectural review scores low (<60) for config files (expected)
- Demonstrates need for task type profiles to skip/adjust gates for scaffolding
- Useful for testing overall AutoBuild workflow

**Location**: External test repository (not in GuardKit codebase)

**Key Insight**: This test exposed that scaffolding tasks fail architectural gates, leading to implementation of task type profiles (TASK-FBSDK-019, TASK-FBSDK-021).

### FEAT-CODE-TEST: Quality Gate Validation Feature (Code Focus)

**Purpose**: Validate quality gates for actual code implementation tasks

**First Task**: TASK-QGV-001 - Implement calculator service with SOLID principles

**Expected Behavior**:
- Architectural review scores high (≥60) for well-structured code
- Demonstrates quality gates working correctly for feature code
- Useful for testing quality gate validation logic

**Location**: `tests/integration/test_features/FEAT-CODE-TEST/`

**Key Benefit**: Validates positive case where quality gates should pass, complementing FEAT-1D98's negative case.

### Comparison Matrix

| Aspect | FEAT-1D98 | FEAT-CODE-TEST |
|--------|-----------|----------------|
| **Focus** | Scaffolding tasks | Feature code tasks |
| **First Task Type** | Project setup | SOLID implementation |
| **Arch Score Expected** | <60 (config files) | ≥60 (well-structured code) |
| **Primary Use** | Workflow testing | Quality gate validation |
| **Location** | External repo | `tests/integration/test_features/` |
| **Task Type Profile** | Scaffolding (adjusted gates) | Feature (full gates) |
| **Created By** | Initial feature-build testing | TASK-FBSDK-024 |

## Running Tests

### Prerequisites

```bash
# Install GuardKit with AutoBuild support
pip install guardkit-py[autobuild]

# Or install development dependencies
pip install -e ".[dev]"

# Verify installation
guardkit-py autobuild --help
```

### Running FEAT-CODE-TEST Tests

#### Quick Validation (Structure Only)

Test that test feature files exist and are valid:

```bash
pytest tests/integration/test_quality_gate_validation.py::test_feat_code_test_structure_exists -v
pytest tests/integration/test_quality_gate_validation.py::test_feat_code_test_yaml_valid -v
```

Expected output:
```
tests/integration/test_quality_gate_validation.py::test_feat_code_test_structure_exists PASSED
tests/integration/test_quality_gate_validation.py::test_feat_code_test_yaml_valid PASSED
```

#### Lightweight Integration Test (Worktree Creation)

Test that AutoBuild creates worktree correctly (runs 1 turn only):

```bash
pytest tests/integration/test_quality_gate_validation.py::test_autobuild_creates_worktree -v -s
```

Expected duration: ~2-5 minutes

Expected output:
```
tests/integration/test_quality_gate_validation.py::test_autobuild_creates_worktree PASSED
```

#### Standard Integration Test (Quality Gates Evaluation)

Test that quality gates are evaluated (runs 2 turns):

```bash
pytest tests/integration/test_quality_gate_validation.py::test_quality_gates_evaluated -v -s
```

Expected duration: ~5-10 minutes

Expected output:
```
tests/integration/test_quality_gate_validation.py::test_quality_gates_evaluated PASSED
```

This test verifies:
- Player and Coach reports are generated
- All quality gates are evaluated (tests, coverage, arch review, plan audit)
- Gate results are recorded in Coach reports

#### Full AutoBuild Test (Happy Path)

Test complete AutoBuild workflow with quality gate approval:

```bash
pytest tests/integration/test_quality_gate_validation.py::test_quality_gates_pass_for_good_code -v -s -m "not skip"
```

Expected duration: ~10-20 minutes

Expected output:
```
tests/integration/test_quality_gate_validation.py::test_quality_gates_pass_for_good_code PASSED
```

This test validates:
- Calculator service implements SOLID principles
- Architectural review score ≥60
- Test coverage ≥80%
- All tests passing
- Coach approves implementation

**Note**: This test is skipped by default due to long execution time. Use `-m "not skip"` to run it.

### Running All Quality Gate Tests

```bash
# Run all quality gate validation tests (excluding skipped tests)
pytest tests/integration/test_quality_gate_validation.py -v

# Run all tests including long-running ones
pytest tests/integration/test_quality_gate_validation.py -v -m "not skip"

# Run with coverage
pytest tests/integration/test_quality_gate_validation.py -v --cov=guardkit.orchestrator.quality_gates
```

### Manual AutoBuild Execution (Debugging)

For debugging or manual validation:

```bash
# Create temporary test repository
mkdir -p /tmp/feat-code-test-manual
cd /tmp/feat-code-test-manual

# Initialize git repository
git init
git config user.name "Test User"
git config user.email "test@example.com"

# Copy FEAT-CODE-TEST files
mkdir -p .guardkit/features tasks/backlog
cp tests/integration/test_features/FEAT-CODE-TEST/FEAT-CODE-TEST.yaml .guardkit/features/
cp tests/integration/test_features/FEAT-CODE-TEST/TASK-QGV-001-calculator-service.md tasks/backlog/

# Commit
git add .
git commit -m "Add FEAT-CODE-TEST"

# Run AutoBuild
guardkit-py autobuild feature FEAT-CODE-TEST --max-turns 5

# Check results
cat .guardkit/autobuild/TASK-QGV-001/coach_turn_*.json | jq '.quality_gates'
```

## Expected Outcomes

### Successful Quality Gate Validation

When FEAT-CODE-TEST executes successfully:

**Turn 1-3**: Player implements calculator service
- Creates `src/calculator/` with operations and calculator classes
- Creates `tests/calculator/` with comprehensive tests
- Demonstrates SOLID principles clearly

**Coach Validation**:
```json
{
  "decision": "approved",
  "quality_gates": {
    "tests_passed": true,
    "coverage_met": true,
    "arch_review_passed": true,
    "plan_audit_passed": true,
    "all_gates_passed": true
  },
  "architectural_review": {
    "overall_score": 75,
    "solid": 45,
    "dry": 20,
    "yagni": 10
  },
  "test_metrics": {
    "total": 15,
    "passed": 15,
    "failed": 0,
    "coverage_lines": 92.5,
    "coverage_branches": 85.0
  }
}
```

**Final Status**: Task transitions to IN_REVIEW, AutoBuild completes successfully

### Failed Quality Gates (Expected for Testing)

When intentionally testing failure scenarios:

**Poor Structure Test**:
```json
{
  "decision": "feedback",
  "quality_gates": {
    "tests_passed": true,
    "coverage_met": true,
    "arch_review_passed": false,
    "plan_audit_passed": true,
    "all_gates_passed": false
  },
  "feedback": "Architectural review score below 60: monolithic implementation violates SRP and OCP"
}
```

**Missing Tests Test**:
```json
{
  "decision": "feedback",
  "quality_gates": {
    "tests_passed": null,
    "coverage_met": false,
    "arch_review_passed": true,
    "plan_audit_passed": true,
    "all_gates_passed": false
  },
  "feedback": "Coverage threshold not met: 0% (required ≥80%)"
}
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/quality-gate-tests.yml
name: Quality Gate Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  quality-gate-validation:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[autobuild,dev]"

      - name: Run structure validation tests
        run: |
          pytest tests/integration/test_quality_gate_validation.py \
            -k "structure or yaml" \
            -v

      - name: Run lightweight integration tests
        run: |
          pytest tests/integration/test_quality_gate_validation.py \
            -k "worktree or gates_evaluated" \
            -v \
            --timeout=600

      - name: Upload test reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: quality-gate-test-reports
          path: .guardkit/autobuild/TASK-QGV-001/
```

### GitLab CI

```yaml
# .gitlab-ci.yml
quality-gate-tests:
  stage: test
  image: python:3.11
  timeout: 30m

  script:
    - pip install -e ".[autobuild,dev]"
    - pytest tests/integration/test_quality_gate_validation.py -k "structure or yaml" -v
    - pytest tests/integration/test_quality_gate_validation.py -k "worktree or gates_evaluated" -v --timeout=600

  artifacts:
    when: always
    paths:
      - .guardkit/autobuild/TASK-QGV-001/
    expire_in: 1 week
```

## Troubleshooting

### Issue: Test fails with "feature not found"

**Symptoms**:
```
FileNotFoundError: .guardkit/features/FEAT-CODE-TEST.yaml not found
```

**Solution**:
Ensure test fixture copies feature file correctly:
```bash
ls -la tests/integration/test_features/FEAT-CODE-TEST/FEAT-CODE-TEST.yaml
```

If file exists, check `temp_test_repo` fixture is copying files to `.guardkit/features/`.

### Issue: AutoBuild times out

**Symptoms**:
```
TimeoutError: Command exceeded 600 seconds
```

**Solutions**:
1. Increase timeout in test:
```python
result = run_autobuild_feature(
    temp_test_repo,
    "FEAT-CODE-TEST",
    max_turns=5,
    timeout=1200  # 20 minutes
)
```

2. Reduce max_turns for faster execution:
```python
result = run_autobuild_feature(
    temp_test_repo,
    "FEAT-CODE-TEST",
    max_turns=2,  # Faster but may not complete
    timeout=600
)
```

3. Check if SDK is hanging:
```bash
export ANTHROPIC_LOG=debug
pytest tests/integration/test_quality_gate_validation.py::test_quality_gates_evaluated -v -s
```

### Issue: Architectural score lower than expected

**Symptoms**:
```
AssertionError: Architectural review failed
arch_review_passed: false
score: 45
```

**Diagnosis**:
Check Coach report for specific feedback:
```bash
cat .guardkit/autobuild/TASK-QGV-001/coach_turn_1.json | jq '.architectural_review'
```

**Common Causes**:
1. **Incomplete SOLID implementation**: Missing interfaces or dependency injection
2. **Duplicated code**: DRY violations reduce score
3. **Over-engineering**: YAGNI violations reduce score

**Solutions**:
1. Review task acceptance criteria - ensure they're clear
2. Check Player implementation - verify SOLID patterns
3. Adjust thresholds if needed (for testing purposes):
```python
# In test: lower threshold temporarily
assert coach_report["architectural_review"]["overall_score"] >= 50  # Was 60
```

### Issue: Tests not passing

**Symptoms**:
```
AssertionError: Tests did not pass
tests_passed: false
```

**Diagnosis**:
Check test results in Coach report:
```bash
cat .guardkit/autobuild/TASK-QGV-001/coach_turn_1.json | jq '.test_metrics'
```

**Common Causes**:
1. **Test import errors**: Missing dependencies
2. **Test assertion failures**: Logic errors
3. **Test setup issues**: Fixtures not working

**Solutions**:
1. Check Player report for test execution errors
2. Run tests manually in worktree:
```bash
cd .guardkit/worktrees/FEAT-CODE-TEST
pytest tests/calculator/ -v
```

### Issue: Coverage below threshold

**Symptoms**:
```
AssertionError: Coverage threshold not met
coverage_met: false
coverage_lines: 65.0  # Below 80%
```

**Diagnosis**:
Check coverage report:
```bash
cat .guardkit/autobuild/TASK-QGV-001/coach_turn_1.json | jq '.test_metrics.coverage'
```

**Common Causes**:
1. **Missing test cases**: Not all code paths tested
2. **Untested error handling**: Exception paths not covered
3. **Incomplete test suite**: Some modules untested

**Solutions**:
1. Review coverage gaps in worktree:
```bash
cd .guardkit/worktrees/FEAT-CODE-TEST
pytest tests/calculator/ --cov=src/calculator --cov-report=term-missing
```

2. Adjust threshold for testing (temporary):
```python
# In CoachValidator or test: lower threshold
COVERAGE_THRESHOLD = 70  # Was 80
```

## Extending Tests

### Adding New Test Scenarios

To add a new quality gate test scenario:

1. **Create new task** in FEAT-CODE-TEST:
```bash
cd tests/integration/test_features/FEAT-CODE-TEST/
vi TASK-QGV-002-monolithic-calculator.md  # Poor structure scenario
```

2. **Update feature YAML**:
```yaml
tasks:
  - id: TASK-QGV-001
    title: Implement calculator service with SOLID principles
    wave: 1
    task_type: feature
  - id: TASK-QGV-002
    title: Implement monolithic calculator (anti-pattern)
    wave: 2
    task_type: feature
```

3. **Add test function**:
```python
def test_quality_gates_fail_for_poor_structure(temp_test_repo: Path):
    """Verify quality gates fail for monolithic code."""
    # Modify task to request monolithic implementation
    task_path = temp_test_repo / "tasks" / "backlog" / "TASK-QGV-002-monolithic-calculator.md"
    # ... copy task file ...

    result = run_autobuild_feature(temp_test_repo, "FEAT-CODE-TEST", max_turns=3)

    player, coach = get_latest_turn_reports(temp_test_repo, "TASK-QGV-002")
    gates = check_quality_gates(coach)

    assert not gates["arch_review_passed"], "Should fail arch review"
    assert coach["architectural_review"]["overall_score"] < 60
```

### Creating New Test Features

To create an entirely new test feature (e.g., for different tech stack):

1. **Create feature directory**:
```bash
mkdir -p tests/integration/test_features/FEAT-MY-TEST
```

2. **Create feature YAML**:
```yaml
feature_id: FEAT-MY-TEST
name: My Test Feature
description: Test feature for X
status: testing
tasks:
  - id: TASK-MT-001
    title: My test task
    wave: 1
    task_type: feature
```

3. **Create task markdown** with clear acceptance criteria

4. **Add to test suite**:
```python
@pytest.fixture
def feat_my_test_dir(test_features_dir: Path) -> Path:
    return test_features_dir / "FEAT-MY-TEST"

def test_my_feature_quality_gates(temp_test_repo: Path):
    # ... test implementation ...
```

## Best Practices

### Test Execution Strategy

1. **Run structure tests first** (fast, catches basic errors):
```bash
pytest tests/integration/test_quality_gate_validation.py -k structure -v
```

2. **Run lightweight integration tests** (medium speed, validates workflow):
```bash
pytest tests/integration/test_quality_gate_validation.py -k "worktree or gates_evaluated" -v
```

3. **Run full tests only when needed** (slow, comprehensive validation):
```bash
pytest tests/integration/test_quality_gate_validation.py -m "not skip" -v
```

### CI/CD Strategy

- **On every commit**: Run structure and lightweight tests (5-10 min)
- **On PR**: Run all tests except long-running ones (10-15 min)
- **Nightly**: Run full test suite including long-running tests (30-60 min)

### Debugging Strategy

1. **Enable verbose logging**:
```bash
export ANTHROPIC_LOG=debug
export GUARDKIT_LOG_LEVEL=DEBUG
```

2. **Run single test with output**:
```bash
pytest tests/integration/test_quality_gate_validation.py::test_name -v -s
```

3. **Inspect worktree manually**:
```bash
cd .guardkit/worktrees/FEAT-CODE-TEST
ls -la
git log --oneline
git diff main
```

4. **Use debug helper**:
```python
from tests.integration.test_quality_gate_validation import debug_autobuild_failure
debug_autobuild_failure(temp_test_repo, "TASK-QGV-001")
```

## Related Documentation

- [AutoBuild User Guide](../guides/autobuild-user-guide.md)
- [Quality Gates Overview](../architecture/quality-gates.md)
- [Task Type Profiles](../guides/task-type-profiles.md)
- [CoachValidator Implementation](../../guardkit/orchestrator/quality_gates/coach_validator.py)
- [FEAT-CODE-TEST README](../../tests/integration/test_features/FEAT-CODE-TEST/README.md)

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-22 | Initial documentation as part of TASK-FBSDK-024 |
