---
complexity: 4
dependencies: []
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR5-001
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-005
task_type: feature
title: Implement `show` command
wave: 2
---

# Implement `show` command

## Description

Implement the `guardkit graphiti show` command to display details of specific knowledge by type and ID.

## Acceptance Criteria

- [x] `show feature FEAT-XXX` displays feature spec details
- [x] `show adr ADR-001` displays ADR details
- [x] `show project-overview` displays project overview
- [x] Supports types: feature, adr, project-overview, pattern, constraint, guide
- [x] Formatted output with colored sections
- [x] Handles "not found" gracefully

## Usage Examples

```bash
guardkit graphiti show feature FEAT-SKEL-001
guardkit graphiti show adr ADR-001
guardkit graphiti show project-overview
```

**Reference**: See FEAT-GR-005-knowledge-query-command.md for output format.