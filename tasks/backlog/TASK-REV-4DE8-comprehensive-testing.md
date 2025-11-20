---
id: TASK-REV-4DE8
title: Implement comprehensive testing for /task-review command (Phase 5)
status: backlog
created: 2025-01-20T15:00:00Z
updated: 2025-01-20T15:00:00Z
priority: medium
tags: [task-review, testing, phase-5, quality-assurance]
complexity: 5
estimated_effort: 4-6 hours
related_proposal: docs/proposals/task-review-command-proposal.md
parent_initiative: task-review-command-implementation
phase: 5
dependencies: [TASK-REV-A4AB, TASK-REV-3248, TASK-REV-2367, TASK-REV-5DC2]
---

# Task: Implement Comprehensive Testing for /task-review (Phase 5)

## Context

This is **Phase 5 of 5** (final phase) for implementing the `/task-review` command.

**Prerequisites**: All previous phases (1-4) must be complete.

**Goal**: Achieve comprehensive test coverage for the entire `/task-review` command with unit tests, integration tests, and end-to-end tests.

## Description

Create a comprehensive test suite that validates all aspects of the `/task-review` command, from basic functionality to complex multi-agent review scenarios.

### Test Coverage Goals

- **Unit tests**: ≥80% line coverage, ≥75% branch coverage
- **Integration tests**: All 5 review modes tested end-to-end
- **Edge cases**: Error handling, missing files, invalid inputs
- **Performance**: Review completion within expected time limits

## Acceptance Criteria

### Unit Test Coverage
- [ ] Orchestrator functions tested (≥90% coverage)
- [ ] All 5 review modes tested independently (≥85% coverage each)
- [ ] Report generator tested (all 3 formats)
- [ ] Decision checkpoint tested (all 4 options)
- [ ] State management tested (all transitions)
- [ ] Flag validation tested (all combinations)

### Integration Test Coverage
- [ ] Architectural review end-to-end
- [ ] Code quality review end-to-end
- [ ] Decision analysis end-to-end
- [ ] Technical debt assessment end-to-end
- [ ] Security audit end-to-end
- [ ] Review → Implement workflow
- [ ] Review → Revise workflow

### Edge Case Coverage
- [ ] Missing task file
- [ ] Invalid task_type
- [ ] Invalid review_mode
- [ ] Invalid review_depth
- [ ] Invalid output_format
- [ ] Empty review_scope
- [ ] Agent invocation failure
- [ ] Report generation failure
- [ ] State transition failure

### Performance Tests
- [ ] Quick depth completes in ≤30 minutes
- [ ] Standard depth completes in ≤2 hours
- [ ] Comprehensive depth completes in ≤6 hours
- [ ] Report generation completes in ≤5 seconds

### Regression Tests
- [ ] Existing tasks without task_type field work
- [ ] `/task-work` unaffected by task-review changes
- [ ] State manager handles review_complete state
- [ ] Task metadata backward compatible

## Implementation Notes

### Test Suite Structure

```
tests/
├── unit/
│   └── commands/
│       ├── test_task_review_orchestrator.py      # 15+ tests
│       ├── review_modes/
│       │   ├── test_architectural_review.py      # 5+ tests
│       │   ├── test_code_quality_review.py       # 5+ tests
│       │   ├── test_decision_analysis.py         # 5+ tests
│       │   ├── test_technical_debt.py            # 5+ tests
│       │   └── test_security_audit.py            # 5+ tests
│       ├── test_review_report_generator.py       # 10+ tests
│       └── test_review_state_manager.py          # 8+ tests
├── integration/
│   ├── test_task_review_workflow.py              # 10+ tests
│   ├── test_review_modes_integration.py          # 5+ tests
│   └── test_task_review_integration.py           # 5+ tests (from Phase 4)
└── performance/
    └── test_review_performance.py                # 5+ tests
```

### Example: Comprehensive Orchestrator Tests

```python
# tests/unit/commands/test_task_review_orchestrator.py

import pytest
from installer.global.commands.lib.task_review_orchestrator import (
    execute_task_review,
    validate_review_mode,
    validate_review_depth,
    validate_output_format
)

class TestTaskReviewOrchestrator:
    """Test suite for task-review orchestrator."""

    def test_execute_review_default_params(self):
        """Test review execution with default parameters."""
        result = execute_task_review("TASK-001")

        assert result["status"] == "success"
        assert result["review_mode"] == "architectural"
        assert result["review_depth"] == "standard"
        assert result["task_id"] == "TASK-001"

    def test_execute_review_all_modes(self):
        """Test that all 5 review modes execute successfully."""
        modes = ["architectural", "code-quality", "decision", "technical-debt", "security"]

        for mode in modes:
            result = execute_task_review("TASK-001", mode=mode)
            assert result["status"] == "success"
            assert result["review_mode"] == mode

    def test_execute_review_all_depths(self):
        """Test that all 3 depth levels work."""
        depths = ["quick", "standard", "comprehensive"]

        for depth in depths:
            result = execute_task_review("TASK-001", depth=depth)
            assert result["status"] == "success"

    def test_execute_review_all_outputs(self):
        """Test that all 3 output formats work."""
        outputs = ["summary", "detailed", "presentation"]

        for output in outputs:
            result = execute_task_review("TASK-001", output=output)
            assert result["status"] == "success"

    def test_invalid_review_mode(self):
        """Test validation of invalid review mode."""
        with pytest.raises(ValueError, match="Invalid review mode"):
            execute_task_review("TASK-001", mode="invalid")

    def test_invalid_review_depth(self):
        """Test validation of invalid review depth."""
        with pytest.raises(ValueError, match="Invalid review depth"):
            execute_task_review("TASK-001", depth="invalid")

    def test_invalid_output_format(self):
        """Test validation of invalid output format."""
        with pytest.raises(ValueError, match="Invalid output format"):
            execute_task_review("TASK-001", output="invalid")

    def test_missing_task_file(self):
        """Test handling of non-existent task."""
        with pytest.raises(FileNotFoundError, match="Task not found"):
            execute_task_review("TASK-NONEXISTENT")

    def test_review_state_transitions(self):
        """Test that state transitions work correctly."""
        task_id = "TASK-001"

        # Initial state: backlog
        task = load_task(task_id)
        assert task["status"] == "backlog"

        # After review: review_complete
        execute_task_review(task_id)
        task = load_task(task_id)
        assert task["status"] == "review_complete"

    def test_review_metadata_saved(self):
        """Test that review metadata is saved to task."""
        task_id = "TASK-001"
        execute_task_review(task_id, mode="security", depth="comprehensive")

        task = load_task(task_id)
        assert task["review_results"]["mode"] == "security"
        assert task["review_results"]["depth"] == "comprehensive"
        assert "completion_date" in task["review_results"]

    # ... (5 more tests for edge cases)
```

### Example: Performance Tests

```python
# tests/performance/test_review_performance.py

import pytest
import time

class TestReviewPerformance:
    """Performance tests for task-review command."""

    @pytest.mark.slow
    def test_quick_review_completes_in_time(self):
        """Test that quick review completes within 30 minutes."""
        start = time.time()
        execute_task_review("TASK-001", depth="quick")
        duration = time.time() - start

        assert duration < 1800  # 30 minutes in seconds

    @pytest.mark.slow
    def test_standard_review_completes_in_time(self):
        """Test that standard review completes within 2 hours."""
        start = time.time()
        execute_task_review("TASK-001", depth="standard")
        duration = time.time() - start

        assert duration < 7200  # 2 hours in seconds

    def test_report_generation_is_fast(self):
        """Test that report generation completes quickly."""
        results = {"mode": "architectural", "findings": [...]}
        recommendations = {"recommendations": [...]}

        start = time.time()
        report = generate_review_report(results, recommendations, "detailed")
        duration = time.time() - start

        assert duration < 5  # 5 seconds max
```

### Example: Integration Tests

```python
# tests/integration/test_task_review_workflow.py

class TestTaskReviewWorkflow:
    """End-to-end workflow tests."""

    def test_architectural_review_workflow(self):
        """Test complete architectural review workflow."""
        # Create review task
        task_id = create_task(
            title="Review authentication architecture",
            task_type="review",
            review_mode="architectural"
        )

        # Execute review
        result = execute_task_review(task_id, mode="architectural")

        # Verify review completed
        assert result["status"] == "success"

        # Verify report generated
        report_path = f"docs/state/{task_id}/review-report.md"
        assert Path(report_path).exists()

        # Verify state transition
        task = load_task(task_id)
        assert task["status"] == "review_complete"

    def test_review_implement_workflow(self):
        """Test review → implement workflow."""
        # Create and execute review
        task_id = create_task("Review auth", task_type="review")
        execute_task_review(task_id, mode="decision")

        # Choose [I]mplement decision
        impl_task_id = handle_implement_decision(task_id)

        # Verify implementation task created
        assert impl_task_id is not None
        impl_task = load_task(impl_task_id)
        assert impl_task["title"].startswith("Implement")
        assert "review_source" in impl_task
        assert impl_task["review_source"] == task_id

    # ... (8 more integration tests)
```

## Test Requirements

### Coverage Thresholds
- Overall coverage: ≥80% lines, ≥75% branches
- Critical modules: ≥90% lines, ≥85% branches
- Review modes: ≥85% lines each

### Test Execution
- All tests must pass with 0 failures
- No test should take >10 minutes (except performance tests marked @pytest.mark.slow)
- Tests should be independent (can run in any order)

### CI/CD Integration
- Tests run automatically on commit
- Coverage reports generated
- Performance tests run nightly only

## Related Tasks

- **TASK-REV-A4AB**: Core command (prerequisite)
- **TASK-REV-3248**: Review modes (prerequisite)
- **TASK-REV-2367**: Report generation (prerequisite)
- **TASK-REV-5DC2**: Integration (prerequisite)

## Success Criteria

- [ ] ≥60 total tests written
- [ ] All tests pass with 0 failures
- [ ] Coverage ≥80% lines, ≥75% branches
- [ ] All 5 review modes tested end-to-end
- [ ] All edge cases covered
- [ ] Performance tests validate time limits
- [ ] Regression tests pass (no breaking changes)
- [ ] CI/CD pipeline configured

---

**Note**: This is the final phase. Upon completion, the `/task-review` command is production-ready and fully tested.
