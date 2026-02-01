---
id: TASK-GR4-001
title: Implement KnowledgeGapAnalyzer
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-004
wave: 1
parallel_group: wave1-gr004
implementation_mode: task-work
complexity: 5
estimate_hours: 3
dependencies: []
autobuild_state:
  current_turn: 3
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T11:46:55.201474'
  last_updated: '2026-02-01T12:53:44.804383'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T11:46:55.201474'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- task-work execution exceeded 900s timeout'
    timestamp: '2026-02-01T11:47:41.531734'
    player_summary: '[RECOVERED via git_only] Original error: SDK timeout after 900s:
      task-work execution exceeded 900s timeout'
    player_success: true
    coach_success: true
  - turn: 3
    decision: approve
    feedback: null
    timestamp: '2026-02-01T12:51:27.334678'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Implement KnowledgeGapAnalyzer

## Description

Create the `KnowledgeGapAnalyzer` class that analyzes existing knowledge in Graphiti to identify gaps and generates targeted questions to fill them.

## Acceptance Criteria

- [ ] `analyze_gaps(focus, max_questions)` returns `List[KnowledgeGap]`
- [ ] Queries Graphiti for existing knowledge
- [ ] Compares against question templates to find gaps
- [ ] Supports focus filtering by category
- [ ] Sorts by importance (high/medium/low)
- [ ] Includes AutoBuild categories (role_customization, quality_gates, workflow_preferences)

## Technical Details

**Location**: `guardkit/knowledge/gap_analyzer.py`

**Knowledge Categories**:
- `project_overview`, `architecture`, `domain`, `constraints`, `decisions`, `goals`
- `role_customization` (NEW - from TASK-REV-1505)
- `quality_gates` (NEW - from TASK-REV-1505)
- `workflow_preferences` (NEW - from TASK-REV-1505)

**Reference**: See FEAT-GR-004-interactive-knowledge-capture.md for question templates.
