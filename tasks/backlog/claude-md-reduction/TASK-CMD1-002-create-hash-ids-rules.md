---
id: TASK-CMD1-002
title: Create rules/hash-based-ids.md from root CLAUDE.md section
status: completed
created: 2026-01-13T11:35:00Z
priority: high
tags: [documentation, rules-structure, progressive-disclosure]
complexity: 2
parent: TASK-REV-CMD1
implementation_mode: direct
parallel_group: wave-1
conductor_workspace: claude-md-reduction-wave1-2
---

# Task: Create rules/hash-based-ids.md from root CLAUDE.md section

## Problem Statement

The "Hash-Based Task IDs" section in root CLAUDE.md is 3,692 characters. This reference documentation should be moved to the rules/ structure.

## Acceptance Criteria

- [x] Create `.claude/rules/hash-based-ids.md` with full documentation
- [x] Add appropriate `paths:` frontmatter for conditional loading
- [x] Replace root CLAUDE.md section with 3-line summary and pointer
- [x] Remove FAQ subsection (move most common 3 questions only to summary)

## Implementation Notes

### Source Content
Lines 539-644 of `/CLAUDE.md` (from "## Hash-Based Task IDs" to end of section)

### Target File Structure

```markdown
---
paths: tasks/**/*.md, guardkit/cli/**/*.py
---

# Hash-Based Task IDs

[Full content from root CLAUDE.md]
```

### Root CLAUDE.md Replacement

```markdown
## Hash-Based Task IDs

Format: `TASK-{hash}` or `TASK-{prefix}-{hash}` (e.g., `TASK-FIX-a3f8`)
Benefits: Zero duplicates, concurrent-safe, Conductor compatible.
See: `.claude/rules/hash-based-ids.md` for full documentation.
```

## Estimated Savings

~3,200 characters (current: 3,692, replacement: ~200)

## Related Files

- Source: `/CLAUDE.md` lines 539-644
- Target: `.claude/rules/hash-based-ids.md`
