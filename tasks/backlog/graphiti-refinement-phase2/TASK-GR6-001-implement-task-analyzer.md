---
id: TASK-GR6-001
title: Implement TaskAnalyzer
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: task-work
complexity: 5
estimate_hours: 3
dependencies: []
autobuild_state:
  current_turn: 3
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T15:07:59.516414'
  last_updated: '2026-02-01T15:19:38.517011'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T15:07:59.516414'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T15:15:24.540113'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: approve
    feedback: null
    timestamp: '2026-02-01T15:17:23.677029'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Implement TaskAnalyzer

## Description

Create the `TaskAnalyzer` class that analyzes task characteristics to inform context retrieval decisions, including AutoBuild-specific characteristics.

## Acceptance Criteria

- [ ] `analyze(task, phase)` returns `TaskCharacteristics`
- [ ] Classifies task type (IMPLEMENTATION, REVIEW, PLANNING, etc.)
- [ ] Determines complexity, novelty, refinement status
- [ ] Queries historical performance (avg_turns, success_rate)
- [ ] Includes AutoBuild fields: current_actor, turn_number, is_autobuild

## Technical Details

**Location**: `guardkit/knowledge/task_analyzer.py`

**TaskCharacteristics Fields**:
- Basic: task_id, description, tech_stack
- Classification: task_type, current_phase, complexity
- Novelty: is_first_of_type, similar_task_count
- Context: feature_id, is_refinement, refinement_attempt
- Performance: avg_turns_for_type, success_rate_for_type
- AutoBuild: current_actor, turn_number, is_autobuild, has_previous_turns

**Reference**: See FEAT-GR-006-job-specific-context.md TaskAnalyzer section.
