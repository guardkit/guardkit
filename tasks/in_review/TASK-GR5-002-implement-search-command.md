---
complexity: 4
dependencies: []
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR5-002
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-005
task_type: feature
title: Implement `search` command
wave: 2
completed_at: 2026-02-01
---

# Implement `search` command

## Description

Implement the `guardkit graphiti search` command to search for knowledge across all categories.

## Acceptance Criteria

- [x] `search "query"` searches all groups
- [x] `--group` option limits to specific group
- [x] `--limit` option controls max results
- [x] Results show relevance score with color coding
- [x] Truncates long facts with "..."

## Usage Examples

```bash
guardkit graphiti search "authentication"
guardkit graphiti search "error handling" --group patterns
guardkit graphiti search "walking skeleton" --limit 5
```

**Reference**: See FEAT-GR-005 search output format.