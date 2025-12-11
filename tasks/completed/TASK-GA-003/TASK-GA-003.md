---
id: TASK-GA-003
title: Document guidance architecture in rules-structure-guide
status: completed
task_type: implementation
created: 2025-12-11T20:00:00Z
updated: 2025-12-11T21:30:00Z
priority: medium
tags: [documentation, rules-structure, guidance, architecture]
complexity: 2
parent: TASK-REV-ARCH
related_to: [TASK-GA-001, TASK-GA-004]
implementation_mode: direct
conductor_workspace: guidance-architecture-wave2-1
wave: 2
completed: 2025-12-11T21:30:00Z
completed_location: tasks/completed/TASK-GA-003/
organized_files: ["TASK-GA-003.md"]
---

# Task: Document Guidance Architecture in Rules-Structure-Guide

## Background

The relationship between `agents/` files and `rules/guidance/` files needs formal documentation. Currently this architecture is implied but not explicitly documented.

## Acceptance Criteria

- [x] New section added to `docs/guides/rules-structure-guide.md`
- [x] Clear comparison table between agent and guidance files
- [x] Source of truth policy documented
- [x] Size guidelines documented

## Implementation Details

### File to Modify

`docs/guides/rules-structure-guide.md`

### Content to Add

Add a new section after "Path-Specific Loading" section:

```markdown
## Guidance vs Agent Files

GuardKit templates use two complementary file types for specialist guidance:

### Purpose Comparison

| Aspect | agents/{name}.md | rules/guidance/{slug}.md |
|--------|------------------|--------------------------|
| **Purpose** | Task tool subprocess context | Path-triggered hints |
| **Loading** | Explicit (Task tool, @mention) | Automatic (file path match) |
| **Size Target** | Full content (6-12KB) | Slim summary (<3KB) |
| **Content** | Role, capabilities, examples, testing | Boundaries, brief summary, references |
| **Frontmatter** | name, tools, model, stack, phase | paths, applies_when, agent |

### When Each Is Used

**Agent files** (`agents/`) are loaded when:
- The Task tool invokes a specialist agent
- User explicitly mentions an agent with `@agent-name`
- An orchestrator selects a specialist for implementation

**Guidance files** (`rules/guidance/`) are loaded when:
- Claude Code detects you're editing a file matching the `paths:` pattern
- Provides passive context hints without invoking a full agent subprocess

### Source of Truth

**`agents/{name}.md` is the source of truth** for all specialist content.

`rules/guidance/{slug}.md` files are derived summaries that:
1. Extract boundaries (ALWAYS/NEVER/ASK) from the agent
2. Provide a brief capability summary
3. Reference the full agent for detailed guidance

**Never edit guidance files directly** - regenerate them from agent files.

### Size Guidelines

| File Type | Target Size | Maximum |
|-----------|-------------|---------|
| Agent core | 6-10KB | 15KB |
| Agent extended (-ext) | 15-25KB | 30KB |
| Guidance | 2-3KB | 5KB |

Guidance files exceeding 5KB trigger a validation warning during template creation.

### Example Structure

```
template/
├── agents/
│   ├── api-specialist.md           # Full context (8KB)
│   └── api-specialist-ext.md       # Detailed examples (20KB)
└── .claude/rules/guidance/
    └── api.md                      # Slim summary (2.5KB)
```

### Why Two Files?

This architecture optimizes for different contexts:

1. **Context Window Efficiency**: Guidance files load automatically on path match. Keeping them slim (<3KB) prevents context bloat when you're just editing code.

2. **Full Context When Needed**: When the Task tool invokes an agent for implementation, it needs the full role definition, all capabilities, and testing patterns.

3. **Different Frontmatter**: Agents need `tools`, `model`, `phase` for subprocess execution. Guidance needs `paths` for conditional loading.

4. **Progressive Disclosure**: Developers get hints automatically (guidance), detailed help on demand (agent), and exhaustive reference when needed (agent-ext).
```

## Notes

- This is a documentation-only task (no code changes)
- Use `direct` implementation mode (simple markdown edits)
- Coordinate with TASK-GA-004 to avoid duplicate content
