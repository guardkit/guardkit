---
complexity: 4
dependencies:
- TASK-GR5-008
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR5-009
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-005
task_type: testing
title: Add GR-005 tests
wave: 2
---

# Add GR-005 tests

## Description

Add comprehensive tests for knowledge query commands and turn state functionality.

## Acceptance Criteria

- [x] Unit tests for show, search, list, status commands
- [x] Unit tests for TurnStateEpisode serialization
- [x] Integration tests for turn state capture
- [x] Integration tests for turn context loading
- [x] Tests for "not found" and empty cases
- [x] Coverage >= 80%

## Test Cases

```python
def test_show_feature_displays_spec():
    """Should display feature spec details."""

def test_search_returns_sorted_results():
    """Should return results sorted by relevance."""

def test_turn_state_capture():
    """Should capture and persist turn state."""

def test_turn_context_loading():
    """Should load previous turns and format context."""

def test_context_emphasizes_rejection_feedback():
    """Should highlight feedback from rejected turns."""
```