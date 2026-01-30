---
id: TASK-GR4-008
title: Add GR-004 tests
status: backlog
task_type: testing
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-004
wave: 1
parallel_group: wave1-gr004
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies:
  - TASK-GR4-007
---

# Add GR-004 tests

## Description

Add comprehensive tests for interactive knowledge capture, including AutoBuild customization categories.

## Acceptance Criteria

- [ ] Unit tests for KnowledgeGapAnalyzer
- [ ] Unit tests for InteractiveCaptureSession
- [ ] Unit tests for fact extraction
- [ ] Integration tests for Graphiti persistence
- [ ] Tests for AutoBuild category capture
- [ ] Coverage >= 80%

## Test Cases

```python
def test_gap_analyzer_finds_missing_knowledge():
    """Should identify gaps based on question templates."""

def test_capture_session_skip_and_quit():
    """Should handle skip and quit commands."""

def test_fact_extraction_prefixes_correctly():
    """Should prefix facts with category context."""

def test_persistence_maps_categories_correctly():
    """Should map categories to correct group_ids."""

def test_autobuild_categories_included():
    """Should include role_customization, quality_gates, workflow_preferences."""
```
