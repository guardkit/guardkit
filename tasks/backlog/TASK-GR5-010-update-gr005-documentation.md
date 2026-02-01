---
id: TASK-GR5-010
title: Update GR-005 documentation
status: backlog
task_type: documentation
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-005
wave: 2
implementation_mode: direct
complexity: 2
estimate_hours: 1
dependencies:
  - TASK-GR5-009
---

# Update GR-005 documentation

## Description

Update documentation for knowledge query commands and turn state tracking.

## Acceptance Criteria

- [ ] Add CLI usage to CLAUDE.md
- [ ] Document all query commands with examples
- [ ] Document turn state capture behavior
- [ ] Add troubleshooting for query issues
- [ ] Mark FEAT-GR-005 as implemented

## Documentation Updates

1. **CLAUDE.md**: Add `guardkit graphiti show/search/list/status`
2. **CLI help**: Ensure all commands have `--help`
3. **Turn states**: Document capture and loading behavior
4. **FEAT-GR-005**: Mark as implemented, add final notes
