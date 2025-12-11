# Review Report: TASK-CRS-014 (REVISED)

## Agent-Enhance Command Rules Structure Support

**Review Mode**: Architectural
**Review Depth**: Standard (Revised after Conductor worktree feedback)
**Reviewer**: architectural-reviewer agent
**Date**: 2025-12-11
**Status**: COMPLETE - **NO CHANGES NEEDED**

---

## Executive Summary

**REVISED FINDING**: After additional analysis from the Conductor worktree, the `/agent-enhance` command **does NOT need updating** for rules structure support.

### Key Insight: Two Different Systems

The analysis revealed that `agents/` and `.claude/rules/agents/` serve **completely different purposes**:

| Directory | Purpose | Content Type | Used By |
|-----------|---------|--------------|---------|
| `agents/` | Full specialist agent definitions | Rich agent specs with frontmatter, capabilities, examples, boundaries | `/agent-enhance`, Task tool, agent discovery |
| `.claude/rules/agents/` | Path-based contextual guidance | Lightweight rules with `paths:` frontmatter for conditional loading | Claude Code's rule loading system |

**These are NOT the same thing.** The rules structure agents are static guidance documents, not dynamic agent definitions that need enhancement.

---

## Evidence: nextjs-fullstack Template

The nextjs-fullstack template demonstrates this clearly:

### `agents/` Directory (Full Agent Definitions)
```
installer/core/templates/nextjs-fullstack/agents/
├── nextjs-fullstack-specialist.md        # Full agent spec
├── nextjs-fullstack-specialist-ext.md    # Extended content
├── nextjs-server-components-specialist.md
├── nextjs-server-components-specialist-ext.md
├── nextjs-server-actions-specialist.md
├── nextjs-server-actions-specialist-ext.md
├── react-state-specialist.md
└── react-state-specialist-ext.md
```

**These are enhanced by `/agent-enhance`** with:
- Full YAML frontmatter (name, description, tools, model, stack, capabilities)
- Rich examples and boundaries
- Progressive disclosure split (-ext.md files)

### `.claude/rules/agents/` Directory (Path-Based Rules)
```
installer/core/templates/nextjs-fullstack/.claude/rules/agents/
├── fullstack.md           # paths: (none - always load)
├── server-components.md   # paths: **/app/**/*.tsx, **/app/**/page.tsx
├── server-actions.md      # paths: **/actions/**, **/*.action.ts
└── react-state.md         # paths: **/*store*, **/*context*
```

**These are STATIC guidance loaded by Claude Code** based on file path matching:
- Simple `paths:` frontmatter for conditional loading
- Lightweight ALWAYS/NEVER/ASK rules
- Links back to full agent docs in `agents/` directory

---

## Comparison: Agent File vs Rule File

### Full Agent Definition (`agents/nextjs-fullstack-specialist.md`)

```yaml
---
name: nextjs-fullstack-specialist
description: Full-stack Next.js application development
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
stack: [typescript, nextjs, react]
phase: implementation
capabilities:
  - Next.js App Router conventions
  - Server Components and Server Actions
  - Database integration with Prisma
keywords: [nextjs, react, prisma, server-components]
---

## Role
You are a Next.js full-stack specialist...

## Boundaries
### ALWAYS
- ✅ Follow Next.js App Router conventions...
[150-300 lines of rich content]
```

### Path-Based Rule (`.claude/rules/agents/server-components.md`)

```yaml
---
paths: **/app/**/*.tsx, **/app/**/page.tsx, **/app/**/layout.tsx
---

# Server Components Specialist

## Purpose
React Server Components and data fetching patterns...

## Boundaries
### ALWAYS
- Use async/await for data fetching
[~50 lines of lightweight guidance]

## Extended Documentation
For comprehensive patterns, see:
- `installer/core/templates/nextjs-fullstack/agents/nextjs-server-components-specialist.md`
```

---

## Why No Changes Are Needed

1. **Different purposes**: `/agent-enhance` enhances specialist agents in `agents/`, not static rules
2. **Backward compatible**: Old templates without rules structure still work
3. **Rules are static**: `.claude/rules/agents/*.md` files don't need enhancement - they're manually authored guidance
4. **References work both ways**: Rule files link to full agent docs when more detail is needed

### Command Behavior (Unchanged)

```bash
# This works correctly - enhances agents/fastapi-specialist.md
/agent-enhance fastapi-python/fastapi-specialist

# Does NOT touch .claude/rules/agents/ (that's a different system)
```

---

## Revised Recommendations

### Primary: Close TASK-CRS-014 as "Not Needed"

The task was based on a misunderstanding. The `/agent-enhance` command:
- ✅ Already works correctly with `agents/` directory
- ✅ Is NOT intended to modify `.claude/rules/agents/` files
- ✅ Needs no changes for rules structure

### Secondary: Document the Distinction

Add documentation clarifying:
1. `agents/` = Full specialist definitions (enhanced by `/agent-enhance`)
2. `.claude/rules/agents/` = Static path-based guidance (manually authored)
3. Rule files can link to full agent docs for extended reference

### Tertiary: Update Task Status

- Mark TASK-CRS-014 as **COMPLETE** with "No implementation needed"
- Update README.md to change status from "⏳ Backlog" to "✅ Complete (No changes needed)"

---

## Architecture Scoring (Revised)

| Aspect | Score | Notes |
|--------|-------|-------|
| **Current Design** | 9/10 | Clean separation between agent definitions and rule files |
| **Backward Compatibility** | 10/10 | No changes needed, everything works |
| **Clarity** | 7/10 | Could benefit from better documentation |

**Overall**: The existing architecture is correct. No implementation work required.

---

## Original Questions (Answered)

### Q1: Should agent-enhance auto-detect rules structure or require explicit flag?
**Answer**: Neither - `/agent-enhance` operates on `agents/`, not `rules/agents/`. No changes needed.

### Q2: How should path patterns be inferred from agent metadata?
**Answer**: Not applicable - rule files are manually authored with `paths:` frontmatter, not generated by `/agent-enhance`.

### Q3: Should existing `agents/` output be migrated to `rules/agents/`?
**Answer**: No - they serve different purposes. Both directories can coexist.

### Q4: What happens to extended files (`-ext.md`) in rules structure?
**Answer**: Extended files stay in `agents/`. Rule files in `.claude/rules/agents/` link to them when detailed guidance is needed.

### Q5: How does this interact with template validation?
**Answer**: Template validation should check both directories independently - they're separate systems.

---

## Decision Checkpoint (Revised)

```
=========================================================================
📋 REVIEW COMPLETE (REVISED): TASK-CRS-014
=========================================================================

REVISED FINDING: NO CHANGES NEEDED

Key Insight:
  agents/ and .claude/rules/agents/ are DIFFERENT systems:

  - agents/           → Full specialist definitions (for /agent-enhance)
  - rules/agents/     → Static path-based guidance (manually authored)

Evidence:
  nextjs-fullstack template has BOTH directories coexisting

Recommendations:
  1. Close TASK-CRS-014 as "Complete - No changes needed"
  2. Document the distinction between agent types
  3. Update task status in README.md

Report: .claude/reviews/TASK-CRS-014-review-report.md

Decision Options:
  [A]ccept - Close task as "No changes needed"
  [R]evise - Request additional analysis
  [I]mplement - (Not recommended - no implementation needed)
  [C]ancel - Discard review

Your choice:
=========================================================================
```

---

## Appendix: Template Structure Reference

### Template with Rules Structure (nextjs-fullstack)

```
nextjs-fullstack/
├── agents/                              # Full agent definitions
│   ├── nextjs-fullstack-specialist.md   # Enhanced by /agent-enhance
│   ├── nextjs-fullstack-specialist-ext.md
│   └── ...
├── .claude/
│   ├── CLAUDE.md                        # Core documentation
│   └── rules/
│       ├── code-style.md                # paths: **/*.{ts,tsx}
│       ├── testing.md                   # paths: **/*.test.*
│       └── agents/                      # Static path-based guidance
│           ├── fullstack.md             # paths: (none)
│           ├── server-components.md     # paths: **/app/**/*.tsx
│           └── server-actions.md        # paths: **/actions/**
└── templates/                           # Code templates
```

### Template without Rules Structure (fastapi-python - before Wave 4)

```
fastapi-python/
├── agents/                              # Full agent definitions
│   ├── fastapi-specialist.md            # Enhanced by /agent-enhance
│   ├── fastapi-specialist-ext.md
│   └── ...
├── CLAUDE.md                            # All-in-one documentation
└── templates/                           # Code templates
```

Both structures work with `/agent-enhance` - it only operates on the `agents/` directory.
