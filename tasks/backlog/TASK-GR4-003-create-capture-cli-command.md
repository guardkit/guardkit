---
id: TASK-GR4-003
title: Create CLI capture command
status: backlog
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
