---
id: TASK-GR5-002
title: Implement `search` command
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

# Implement `search` command

## Description

Implement the `guardkit graphiti search` command to search for knowledge across all categories.

## Acceptance Criteria

- [ ] `search "query"` searches all groups
- [ ] `--group` option limits to specific group
- [ ] `--limit` option controls max results
- [ ] Results show relevance score with color coding
- [ ] Truncates long facts with "..."

## Usage Examples

```bash
guardkit graphiti search "authentication"
guardkit graphiti search "error handling" --group patterns
guardkit graphiti search "walking skeleton" --limit 5
```

**Reference**: See FEAT-GR-005 search output format.
