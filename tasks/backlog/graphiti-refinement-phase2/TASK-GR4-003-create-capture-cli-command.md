---
id: TASK-GR4-003
title: Create CLI capture command
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-004
wave: 1
parallel_group: wave1-gr004
implementation_mode: direct
complexity: 3
estimate_hours: 2
dependencies:
- TASK-GR4-002
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T13:09:05.709858'
  last_updated: '2026-02-01T13:14:58.838020'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T13:09:05.709858'
    player_summary: 'Implemented the `guardkit graphiti capture` CLI command with
      full support for interactive knowledge capture sessions. The command integrates
      with the existing InteractiveCaptureSession from TASK-GR4-002 and provides rich
      colored console output using the Rich library. Key features: (1) --interactive
      flag to start session, (2) --focus option to filter by 9 knowledge categories
      including AutoBuild workflow categories (role-customization, quality-gates,
      workflow-preferences), (3) --max-questions to '
    player_success: true
    coach_success: true
---

# Create CLI capture command

## Description

Create the `guardkit graphiti capture` CLI command that launches interactive knowledge capture sessions.

## Acceptance Criteria

- [ ] `guardkit graphiti capture --interactive` starts session
- [ ] `--focus` option filters by category
- [ ] `--max-questions` limits question count
- [ ] Supports all focus areas including AutoBuild categories
- [ ] Colored output for questions, captured facts, summary

## Usage Examples

```bash
guardkit graphiti capture --interactive
guardkit graphiti capture --interactive --focus architecture
guardkit graphiti capture --interactive --focus role-customization
guardkit graphiti capture --interactive --focus quality-gates
guardkit graphiti capture --interactive --max-questions 5
```

**Reference**: See FEAT-GR-004 CLI integration section.
