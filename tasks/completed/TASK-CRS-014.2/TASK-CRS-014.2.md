---
id: TASK-CRS-014.2
title: Rename react-typescript rules/agents/ to rules/guidance/
status: completed
task_type: implementation
created: 2025-12-11T15:00:00Z
updated: 2025-12-11T16:55:00Z
completed: 2025-12-11T16:55:00Z
priority: high
tags: [rules-structure, naming, react-typescript]
complexity: 1
parent_task: TASK-CRS-014
implementation_mode: direct
estimated_hours: 0.25
completed_location: tasks/completed/TASK-CRS-014.2/
organized_files: [TASK-CRS-014.2.md]
---

# Task: Rename react-typescript rules/agents/ to rules/guidance/

## Background

The react-typescript template was refactored to rules structure in CRS-007. The `rules/agents/` directory needs renaming to `rules/guidance/` per the naming decision in TASK-CRS-014.

## Changes Required

### Directory Rename

```bash
# From:
installer/core/templates/react-typescript/.claude/rules/agents/

# To:
installer/core/templates/react-typescript/.claude/rules/guidance/
```

### Update References

Check and update any references in:
1. `.claude/CLAUDE.md` (if it mentions `rules/agents/`)
2. Any files within the rules directory that cross-reference

## Acceptance Criteria

- [x] Directory renamed from `rules/agents/` to `rules/guidance/`
- [x] All internal references updated
- [x] Template still works correctly with rules loading

## Verification

```bash
# Verify rename
ls -la installer/core/templates/react-typescript/.claude/rules/guidance/

# Verify no orphaned references
grep -r "rules/agents" installer/core/templates/react-typescript/
```

## Notes

- Simple directory rename task
- May be done in parallel with other template renames
