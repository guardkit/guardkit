---
id: TASK-GR5-003
title: Implement `list` command
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

# Implement `list` command

## Description

Implement the `guardkit graphiti list` command to list all knowledge in a category.

## Acceptance Criteria

- [ ] `list features` lists all feature specs
- [ ] `list adrs` lists all ADRs
- [ ] `list patterns` lists all patterns
- [ ] `list constraints` lists all constraints
- [ ] `list all` lists all categories
- [ ] Shows count per category

## Usage Examples

```bash
guardkit graphiti list features
guardkit graphiti list all
```

**Reference**: See FEAT-GR-005 list output format.
