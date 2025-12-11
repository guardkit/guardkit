---
id: TASK-CRS-014.5
title: Rename react-fastapi-monorepo rules/agents/ to rules/guidance/
status: backlog
task_type: implementation
created: 2025-12-11T15:00:00Z
updated: 2025-12-11T15:00:00Z
priority: high
tags: [rules-structure, naming, react-fastapi-monorepo]
complexity: 1
parent_task: TASK-CRS-014
implementation_mode: direct
estimated_hours: 0.25
depends_on: [TASK-CRS-009]
---

# Task: Rename react-fastapi-monorepo rules/agents/ to rules/guidance/

## Background

The react-fastapi-monorepo template was refactored to rules structure in CRS-009. The `rules/agents/` directory needs renaming to `rules/guidance/` per the naming decision in TASK-CRS-014.

**Note**: If CRS-009 is still in a conductor worktree, this rename should be done there before merging. If already merged, rename in main branch.

## Changes Required

### Directory Rename

```bash
# From:
installer/core/templates/react-fastapi-monorepo/.claude/rules/agents/

# To:
installer/core/templates/react-fastapi-monorepo/.claude/rules/guidance/
```

### Update References

Check and update any references in:
1. `.claude/CLAUDE.md` (if it mentions `rules/agents/`)
2. Any files within the rules directory that cross-reference

## Acceptance Criteria

- [ ] Directory renamed from `rules/agents/` to `rules/guidance/`
- [ ] All internal references updated
- [ ] Template still works correctly with rules loading

## Verification

```bash
# Verify rename
ls -la installer/core/templates/react-fastapi-monorepo/.claude/rules/guidance/

# Verify no orphaned references
grep -r "rules/agents" installer/core/templates/react-fastapi-monorepo/
```

## Notes

- Check if CRS-009 work is in a conductor worktree or already merged
- If in worktree, do rename there before merge
- If merged, rename in main branch
