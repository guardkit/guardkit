---
id: TASK-CMD1-003
title: Consolidate .claude/CLAUDE.md redundant sections
status: completed
created: 2026-01-13T11:35:00Z
priority: high
tags: [documentation, deduplication]
complexity: 2
parent: TASK-REV-CMD1
implementation_mode: direct
parallel_group: wave-1
conductor_workspace: claude-md-reduction-wave1-3
---

# Task: Consolidate .claude/CLAUDE.md redundant sections

## Problem Statement

The `.claude/CLAUDE.md` file (8,417 chars) contains content that duplicates the root CLAUDE.md and existing rules files:
- "Clarifying Questions" section duplicates `.claude/rules/clarifying-questions.md`
- "Progressive Disclosure" section duplicates root CLAUDE.md

## Acceptance Criteria

- [x] Remove "Clarifying Questions" section (lines 148-198), keep pointer to rules file
- [x] Remove "Progressive Disclosure" section (lines 200-259), keep brief summary
- [x] Ensure file focuses on project-specific context only
- [x] Final size < 5,000 characters (achieved: 4,091 chars)

## Implementation Notes

### Content to KEEP (Project-Specific)

1. Project Context (lines 1-8)
2. Core Principles (lines 9-25) - Different focus than root
3. System Philosophy (lines 17-24)
4. Workflow Overview (lines 26-52)
5. Technology Stack Detection (lines 44-52)
6. Getting Started (lines 53-77)
7. Development Mode Selection (lines 79-146)

### Content to REMOVE/CONDENSE

1. **Clarifying Questions** (lines 148-198): Replace with:
   ```markdown
   ## Clarifying Questions

   See: `.claude/rules/clarifying-questions.md` for details.
   ```

2. **Progressive Disclosure** (lines 200-259): Replace with:
   ```markdown
   ## Progressive Disclosure

   Core files (`{name}.md`) always load; extended files (`{name}-ext.md`) load on-demand.
   See root CLAUDE.md for detailed structure.
   ```

## Estimated Savings

~3,500 characters (current: 8,417, target: ~4,900)

## Related Files

- Target: `/.claude/CLAUDE.md`
- Reference: `.claude/rules/clarifying-questions.md`
