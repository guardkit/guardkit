---
id: TASK-GR6-011
title: Relevance tuning and testing
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: task-work
complexity: 5
estimate_hours: 3
dependencies:
- TASK-GR6-009
autobuild_state:
  current_turn: 4
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T17:35:59.111897'
  last_updated: '2026-02-01T17:53:14.051459'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:35:59.111897'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:44:44.858757'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:49:55.096586'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 4
    decision: approve
    feedback: null
    timestamp: '2026-02-01T17:51:34.021780'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Relevance tuning and testing

## Description

Tune and test relevance scoring for context retrieval to ensure high-quality, relevant context is returned.

## Acceptance Criteria

- [ ] Relevance threshold configurable (default 0.5-0.6)
- [ ] Lower threshold for first-of-type tasks (0.5)
- [ ] Higher threshold for refinements (0.6)
- [ ] Manual testing with variety of task types
- [ ] Context quality metrics (relevance, coverage, usefulness)

## Technical Details

**Tuning Parameters**:
- `relevance_threshold`: 0.5 (first-of-type), 0.6 (normal)
- `max_results_per_category`: 5-10
- `budget_safety_margin`: 10%

**Quality Metrics**:
- Were all retrieved items relevant?
- Was important context missed?
- Was context used in implementation?

**Reference**: See FEAT-GR-006 relevance tuning section.
