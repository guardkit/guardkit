---
id: TASK-GA-004
title: Add source-of-truth documentation to CLAUDE.md
status: completed
task_type: implementation
created: 2025-12-11T20:00:00Z
updated: 2025-12-11T20:30:00Z
completed: 2025-12-11T20:30:00Z
priority: medium
tags: [documentation, claude-md, guidance, source-of-truth]
complexity: 2
parent: TASK-REV-ARCH
related_to: [TASK-GA-001, TASK-GA-003]
implementation_mode: direct
conductor_workspace: guidance-architecture-wave2-2
wave: 2
---

# Task: Add Source-of-Truth Documentation to CLAUDE.md

## Background

The CLAUDE.md files need a brief note clarifying that `agents/` is the source of truth for specialist content, with guidance files being derived summaries.

## Acceptance Criteria

- [x] Add brief note to root `CLAUDE.md` in Progressive Disclosure section
- [x] Add brief note to `.claude/CLAUDE.md`
- [x] Reference the detailed guide in rules-structure-guide.md

## Implementation Details

### Files to Modify

1. `CLAUDE.md` (root)
2. `.claude/CLAUDE.md`

### Content to Add to Root CLAUDE.md

In the "Progressive Disclosure" section, add after "For Template Authors":

```markdown
### Guidance vs Agent Files

Templates include two types of specialist files:
- **`agents/{name}.md`**: Full agent context for Task tool execution (source of truth)
- **`rules/guidance/{slug}.md`**: Slim summary for path-triggered loading (derived)

**Source of Truth**: Always edit `agents/` files. Guidance files are generated summaries.

See [Rules Structure Guide](docs/guides/rules-structure-guide.md#guidance-vs-agent-files) for details.
```

### Content to Add to .claude/CLAUDE.md

In the "Progressive Disclosure" section, add:

```markdown
### Guidance Architecture

When working with templates:
- **`agents/`** = Source of truth (full content, 6-12KB)
- **`rules/guidance/`** = Derived summary (slim, <3KB)

Never edit guidance files directly - they are regenerated from agents.
```

## Notes

- Keep additions brief - detailed docs are in rules-structure-guide.md
- Use `direct` implementation mode (simple markdown edits)
- This complements TASK-GA-003 (detailed guide) with brief pointers
