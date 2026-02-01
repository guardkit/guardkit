---
id: TASK-GR5-001
title: Implement `show` command
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-005
wave: 2
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies: []
---

# Implement `show` command

## Description

Implement the `guardkit graphiti show` command to display details of specific knowledge by type and ID.

## Acceptance Criteria

- [ ] `show feature FEAT-XXX` displays feature spec details
- [ ] `show adr ADR-001` displays ADR details
- [ ] `show project-overview` displays project overview
- [ ] Supports types: feature, adr, project-overview, pattern, constraint, guide
- [ ] Formatted output with colored sections
- [ ] Handles "not found" gracefully

## Usage Examples

```bash
guardkit graphiti show feature FEAT-SKEL-001
guardkit graphiti show adr ADR-001
guardkit graphiti show project-overview
```

**Reference**: See FEAT-GR-005-knowledge-query-command.md for output format.
