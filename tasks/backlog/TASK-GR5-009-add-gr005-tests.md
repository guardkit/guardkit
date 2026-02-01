---
id: TASK-GR5-009
title: Add GR-005 tests
status: backlog
task_type: testing
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-005
wave: 2
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies:
  - TASK-GR5-008
---

# Add GR-005 tests

## Description

Add comprehensive tests for knowledge query commands and turn state functionality.

## Acceptance Criteria

- [ ] Unit tests for show, search, list, status commands
- [ ] Unit tests for TurnStateEpisode serialization
- [ ] Integration tests for turn state capture
- [ ] Integration tests for turn context loading
- [ ] Tests for "not found" and empty cases
- [ ] Coverage >= 80%

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
