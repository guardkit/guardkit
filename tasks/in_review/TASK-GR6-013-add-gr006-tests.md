---
complexity: 5
dependencies:
- TASK-GR6-012
estimate_hours: 3
feature_id: FEAT-0F4A
id: TASK-GR6-013
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-006
task_type: testing
title: Add GR-006 tests
wave: 3
---

# Add GR-006 tests

## Description

Add comprehensive tests for job-specific context retrieval, including AutoBuild context.

## Acceptance Criteria

- [x] Unit tests for TaskAnalyzer (65 tests, 100% coverage)
- [x] Unit tests for DynamicBudgetCalculator (57 tests, 99% coverage)
- [x] Unit tests for JobContextRetriever (90 tests, 93% coverage)
- [x] Unit tests for RetrievedContext formatting (TestEmojiMarkers, TestTurnStatesFormatting, TestFormatItem)
- [x] Integration tests for /task-work integration (TestIntegration class)
- [x] Integration tests for /feature-build integration (TestAutoBuildContext, TestParallelRetrieval)
- [x] Tests for AutoBuild context (role, gates, turns, modes)
- [x] Performance tests (< 2 second retrieval) - tests complete in ~1.45s
- [x] Coverage >= 80% (task_analyzer: 100%, budget_calculator: 99%, job_context_retriever: 93%)

## Test Cases

```python
def test_task_analyzer_classifies_types():
    """Should classify task types correctly."""

def test_budget_calculator_adjusts_for_novelty():
    """Should increase budget for first-of-type tasks."""

def test_retriever_respects_budget():
    """Should not exceed allocated budget."""

def test_autobuild_context_included():
    """Should include role_constraints, quality_gates, turn_states."""

def test_retrieval_performance():
    """Should complete in < 2 seconds."""
```