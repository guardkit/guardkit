---
id: TASK-GR5-004
title: Implement `status` command
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-005
wave: 2
implementation_mode: direct
complexity: 3
estimate_hours: 1
dependencies:
  - TASK-GR5-001
---

# Implement `status` command

## Description

Implement the `guardkit graphiti status` command to show knowledge graph health and statistics.

## Acceptance Criteria

- [ ] Shows enabled/disabled status
- [ ] Counts episodes per category (System, Project, Decisions, Learning)
- [ ] `--verbose` shows all groups even if empty
- [ ] Total episode count
- [ ] Colored status indicators (green/yellow/red)

## Usage Examples

```bash
guardkit graphiti status
guardkit graphiti status --verbose
```

**Reference**: See FEAT-GR-005 status output format.
