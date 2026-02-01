---
id: TASK-GR3-007
title: Add tests for context building
status: in_review
task_type: testing
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-003
wave: 1
parallel_group: wave1-gr003
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies:
- TASK-GR3-006
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T13:22:18.052866'
  last_updated: '2026-02-01T13:24:27.228200'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T13:22:18.052866'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Add tests for context building

## Description

Add comprehensive unit and integration tests for the feature spec integration components, including AutoBuild context queries.

## Acceptance Criteria

- [ ] Unit tests for FeatureDetector pattern matching
- [ ] Unit tests for FeaturePlanContext formatting
- [ ] Integration tests for FeaturePlanContextBuilder
- [ ] Tests for AutoBuild context (role_constraints, quality_gates)
- [ ] Tests for graceful degradation when Graphiti unavailable
- [ ] Coverage >= 80%

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
