---
id: TASK-GR4-007
title: Add AutoBuild workflow customization questions
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-004
wave: 1
parallel_group: wave1-gr004
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies:
- TASK-GR4-005
autobuild_state:
  current_turn: 6
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T13:33:05.826457'
  last_updated: '2026-02-01T14:01:08.362201'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T13:33:05.826457'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T13:36:03.362958'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- task-work execution exceeded 900s timeout'
    timestamp: '2026-02-01T13:41:22.982132'
    player_summary: '[RECOVERED via git_only] Original error: SDK timeout after 900s:
      task-work execution exceeded 900s timeout'
    player_success: true
    coach_success: true
  - turn: 4
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T13:56:26.466366'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 5
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T13:57:44.213343'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 6
    decision: approve
    feedback: null
    timestamp: '2026-02-01T13:59:50.714417'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Add AutoBuild workflow customization questions

## Description

Add interactive capture questions for AutoBuild workflow customization, addressing TASK-REV-7549 findings on role reversal and threshold drift.

## Acceptance Criteria

- [ ] Role customization questions (player_ask_before, coach_escalate_when)
- [ ] Quality gate questions (coverage_threshold, arch_review_threshold)
- [ ] Workflow preference questions (implementation_mode, max_auto_turns)
- [ ] Captured to appropriate group_ids
- [ ] CLI focus options: `--focus role-customization`, `--focus quality-gates`

## Question Templates

**Role Customization**:
- "What tasks should the AI Player ALWAYS ask about before implementing?"
- "What decisions should the AI Coach escalate to humans?"
- "Are there areas where AI should NEVER make changes autonomously?"

**Quality Gates**:
- "What test coverage threshold is acceptable?" (e.g., "80% for features")
- "What architectural review score should block implementation?"

**Reference**: See FEAT-GR-004 AutoBuild workflow customization section.
