---
id: TASK-GR6-013
title: Add GR-006 tests
status: backlog
task_type: testing
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: task-work
complexity: 5
estimate_hours: 3
dependencies:
  - TASK-GR6-012
---

# Add GR-006 tests

## Description

Add comprehensive tests for job-specific context retrieval, including AutoBuild context.

## Acceptance Criteria

- [ ] Unit tests for TaskAnalyzer
- [ ] Unit tests for DynamicBudgetCalculator
- [ ] Unit tests for JobContextRetriever
- [ ] Unit tests for RetrievedContext formatting
- [ ] Integration tests for /task-work integration
- [ ] Integration tests for /feature-build integration
- [ ] Tests for AutoBuild context (role, gates, turns, modes)
- [ ] Performance tests (< 2 second retrieval)
- [ ] Coverage >= 80%

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
