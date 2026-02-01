---
complexity: 4
dependencies:
- TASK-GR3-006
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR3-007
implementation_mode: task-work
parallel_group: wave1-gr003
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-003
task_type: testing
title: Add tests for context building
wave: 1
---

# Add tests for context building

## Description

Add comprehensive unit and integration tests for the feature spec integration components, including AutoBuild context queries.

## Acceptance Criteria

- [x] Unit tests for FeatureDetector pattern matching
- [x] Unit tests for FeaturePlanContext formatting
- [x] Integration tests for FeaturePlanContextBuilder
- [x] Tests for AutoBuild context (role_constraints, quality_gates)
- [x] Tests for graceful degradation when Graphiti unavailable
- [x] Coverage >= 80%

## Test Cases

```python
def test_detect_feature_id_from_description():
    """Should extract FEAT-XXX from description."""

def test_find_feature_spec_searches_default_paths():
    """Should search docs/features/, .guardkit/features/."""

def test_context_formatting_respects_budget():
    """Should not exceed token budget."""

def test_autobuild_context_included():
    """Should include role_constraints, quality_gate_configs."""

def test_graceful_degradation_without_graphiti():
    """Should return empty context, not fail."""
```