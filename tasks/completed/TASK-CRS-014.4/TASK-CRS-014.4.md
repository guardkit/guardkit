---
id: TASK-CRS-014.4
title: Rename fastapi-python rules/agents/ to rules/guidance/
status: completed
task_type: implementation
created: 2025-12-11T15:00:00Z
updated: 2025-12-11T17:00:00Z
completed: 2025-12-11T17:00:00Z
priority: high
tags: [rules-structure, naming, fastapi-python]
complexity: 1
parent_task: TASK-CRS-014
implementation_mode: direct
estimated_hours: 0.25
depends_on: [TASK-CRS-006]
completed_location: tasks/completed/TASK-CRS-014.4/
organized_files: [TASK-CRS-014.4.md]
---

# Task: Rename fastapi-python rules/agents/ to rules/guidance/

## Background

The fastapi-python template was refactored to rules structure in CRS-006. The `rules/agents/` directory needs renaming to `rules/guidance/` per the naming decision in TASK-CRS-014.

**Note**: If CRS-006 is still in a conductor worktree, this rename should be done there before merging. If already merged, rename in main branch.

## Changes Required

### Directory Rename

```bash
# From:
installer/core/templates/fastapi-python/.claude/rules/agents/

# To:
installer/core/templates/fastapi-python/.claude/rules/guidance/
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
ls -la installer/core/templates/fastapi-python/.claude/rules/guidance/

# Verify no orphaned references
grep -r "rules/agents" installer/core/templates/fastapi-python/
```

## Notes

- Check if CRS-006 work is in a conductor worktree or already merged
- If in worktree, do rename there before merge
- If merged, rename in main branch
