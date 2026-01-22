---
id: TASK-FBSDK-024
title: Create feature-code test case for quality gates
status: in_review
created: 2025-01-21T16:30:00Z
updated: 2025-01-22T12:55:00Z
priority: medium
tags: [testing, quality-gates, feature-build, integration]
parent_review: TASK-REV-FB19
feature_id: FEAT-ARCH-SCORE-FIX
implementation_mode: task-work
wave: 3
conductor_workspace: arch-score-fix-wave3-2
complexity: 3
depends_on: [TASK-FBSDK-019]
previous_state: in_progress
state_transition_reason: "All quality gates passed"
quality_gates:
  architectural_review:
    score: 75
    threshold: 60
    passed: true
  test_coverage:
    critical_path: 100
    test_file: 40
    passed: true
  tests_passing:
    total: 3
    passed: 3
    failed: 0
    pass_rate: 100
    passed: true
  code_review:
    score: 88
    passed: true
  plan_audit:
    file_count_variance: 0
    loc_variance: 118
    duration_variance: 0
    scope_creep: 0
    passed: true
    notes: "LOC variance justified - higher quality implementation"
---

# Task: Create feature-code test case for quality gates

## Description

Create a second feature-build test case that starts with a feature task (not scaffolding) to validate quality gates work correctly for actual code implementation. This complements the existing FEAT-1D98 test which exposed the scaffolding issue.

## Problem

The current test case (FEAT-1D98 FastAPI Health App) starts with Wave 1 scaffolding tasks. While valid for testing the overall workflow, it's not ideal for testing quality gates because scaffolding produces configuration files, not code.

## Acceptance Criteria

- [x] New test feature defined with code-focused first task
- [x] Feature includes at least one task requiring architectural review
- [x] Test validates quality gates pass for well-structured code
- [~] Test validates quality gates fail for poorly-structured code (stubbed, implementation pattern provided)
- [x] Documented test execution procedure
- [x] Can be run as part of CI/CD pipeline

## Implementation Notes

### Test Feature Definition

Create `tests/integration/test_features/FEAT-CODE-TEST/`:

```yaml
# .guardkit/features/FEAT-CODE-TEST.yaml
feature_id: FEAT-CODE-TEST
name: Quality Gate Validation Feature
description: Test feature for validating quality gates with code
status: testing
tasks:
  - id: TASK-QGV-001
    title: Implement calculator service with SOLID principles
    wave: 1
    task_type: feature
    complexity: 4
```

### Task Content

`TASK-QGV-001-calculator-service.md`:
```markdown
## Description
Implement a calculator service demonstrating SOLID principles.

## Acceptance Criteria
- [ ] Single Responsibility: One class per operation
- [ ] Open/Closed: Extensible operation interface
- [ ] Dependency Inversion: Operations injected into calculator
- [ ] 80%+ test coverage
- [ ] All tests passing
```

### Test Cases

1. **Happy Path**: Well-structured implementation
   - Expected: Architectural score ≥60, all gates pass

2. **Poor Structure**: Monolithic implementation
   - Expected: Architectural score <60, Coach provides feedback

3. **Missing Tests**: Implementation without tests
   - Expected: Test gate fails, Coach provides feedback

### Test Script

`tests/integration/test_quality_gate_validation.py`:

```python
def test_feature_build_with_code_quality_gates():
    """Verify quality gates work correctly for code tasks."""
    # Setup test feature
    setup_test_feature("FEAT-CODE-TEST")

    # Run AutoBuild
    result = run_autobuild("FEAT-CODE-TEST", max_turns=5)

    # Verify quality gates were evaluated
    assert result.tasks[0].quality_gates.arch_review_passed
    assert result.tasks[0].quality_gates.coverage_met
    assert result.tasks[0].quality_gates.tests_passed
```

### Files to Create

1. `tests/integration/test_features/FEAT-CODE-TEST/` directory
2. Feature definition YAML
3. Task markdown files
4. Test script `tests/integration/test_quality_gate_validation.py`
5. Documentation in `docs/testing/quality-gate-testing.md`

## Related Files

- `docs/reviews/feature-build/after_FBSDK-015_016_017.md` (existing test log)
- `tests/integration/` (existing integration tests)

## Notes

This test case should be used alongside FEAT-1D98 to validate both scaffolding (with skipped gates) and feature code (with full gates) scenarios.
