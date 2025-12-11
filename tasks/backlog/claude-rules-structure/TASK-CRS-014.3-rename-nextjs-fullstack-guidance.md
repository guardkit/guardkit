---
id: TASK-CRS-014.3
title: Rename nextjs-fullstack rules/agents/ to rules/guidance/
status: backlog
task_type: implementation
created: 2025-12-11T15:00:00Z
updated: 2025-12-11T15:00:00Z
priority: high
tags: [rules-structure, naming, nextjs-fullstack]
complexity: 1
parent_task: TASK-CRS-014
implementation_mode: direct
estimated_hours: 0.25
---

# Task: Rename nextjs-fullstack rules/agents/ to rules/guidance/

## Background

The nextjs-fullstack template was refactored to rules structure in CRS-008. The `rules/agents/` directory needs renaming to `rules/guidance/` per the naming decision in TASK-CRS-014.

## Changes Required

### Directory Rename

```bash
# From:
installer/core/templates/nextjs-fullstack/.claude/rules/agents/

# To:
installer/core/templates/nextjs-fullstack/.claude/rules/guidance/
```

### Update References

Check and update any references in:
1. `.claude/CLAUDE.md` (if it mentions `rules/agents/`)
2. Any files within the rules directory that cross-reference
3. Guidance files that link to full agent docs in `agents/` directory (these references should remain unchanged - they point to the real agents)

## Acceptance Criteria

- [ ] Directory renamed from `rules/agents/` to `rules/guidance/`
- [ ] All internal references updated
- [ ] Links to `agents/` directory (full specialist docs) preserved
- [ ] Template still works correctly with rules loading

## Verification

```bash
# Verify rename
ls -la installer/core/templates/nextjs-fullstack/.claude/rules/guidance/

# Verify no orphaned references to rules/agents
grep -r "rules/agents" installer/core/templates/nextjs-fullstack/

# Verify agents/ references preserved (should still exist)
grep -r "agents/" installer/core/templates/nextjs-fullstack/.claude/rules/guidance/
```

## Notes

- Simple directory rename task
- May be done in parallel with other template renames
- References to `agents/` (full specialist definitions) should NOT be changed
