---
complexity: 4
dependencies:
- TASK-GR4-005
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR4-007
implementation_mode: task-work
parallel_group: wave1-gr004
parent_review: TASK-REV-0CD7
status: design_approved
sub_feature: GR-004
task_type: feature
title: Add AutoBuild workflow customization questions
wave: 1
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