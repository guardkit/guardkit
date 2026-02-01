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
completed_at: 2026-02-01T14:30:00Z
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

## Implementation Summary

### TDD Workflow Completed

**RED Phase**: Created 16 failing tests in `tests/cli/test_graphiti_show.py`:
- Command registration and argument validation
- Feature spec display (FEAT-XXX routing)
- ADR display (ADR-XXX routing)
- Project overview display
- Pattern, constraint, and guide display
- "Not found" error handling
- Disabled Graphiti handling
- Connection error handling
- Group ID routing verification
- Formatted output verification

**GREEN Phase**: Implemented show command in `guardkit/cli/graphiti.py`:
- `@graphiti.command("show")` with `knowledge_id` argument
- `_detect_group_ids()` for smart routing based on ID prefix
- `_format_show_output()` for Rich console colored output
- Async implementation with proper error handling

### Test Results

- **16/16** show command tests pass
- **73/73** total graphiti CLI tests pass (no regressions)

### Files Modified

1. `guardkit/cli/graphiti.py` - Added show command implementation
2. `tests/cli/test_graphiti_show.py` - Created comprehensive test suite