---
id: TASK-CMD1-001
title: Create rules/autobuild.md from root CLAUDE.md section
status: completed
created: 2026-01-13T11:35:00Z
completed: 2026-01-13T13:10:00Z
priority: high
tags: [documentation, rules-structure, progressive-disclosure]
complexity: 2
parent: TASK-REV-CMD1
implementation_mode: direct
parallel_group: wave-1
conductor_workspace: claude-md-reduction-wave1-1
---

# Task: Create rules/autobuild.md from root CLAUDE.md section

## Problem Statement

The "AutoBuild - Autonomous Task Implementation" section in root CLAUDE.md is 12,377 characters (22% of the file). This detailed documentation should be moved to the rules/ structure per GuardKit's progressive disclosure principles.

## Acceptance Criteria

- [x] Create `.claude/rules/autobuild.md` with full AutoBuild documentation
- [x] Add appropriate `paths:` frontmatter for conditional loading
- [x] Replace root CLAUDE.md section with 3-line summary and pointer
- [x] Verify no loss of functionality

## Implementation Notes

### Source Content
Lines 146-538 of `/CLAUDE.md` (from "## AutoBuild - Autonomous Task Implementation" to end of section)

### Target File Structure

```markdown
---
paths: guardkit/**/*.py, .guardkit/**/*
---

# AutoBuild - Autonomous Task Implementation

[Full content from root CLAUDE.md]
```

### Root CLAUDE.md Replacement

```markdown
## AutoBuild

Autonomous task implementation using Player-Coach adversarial workflow.
Run: `guardkit autobuild task TASK-XXX [--mode=tdd]`
See: `.claude/rules/autobuild.md` for full documentation.
```

## Estimated Savings

~10,500 characters (current: 12,377, replacement: ~200)

## Related Files

- Source: `/CLAUDE.md` lines 146-538
- Target: `.claude/rules/autobuild.md`
- Review: `.claude/reviews/TASK-REV-CMD1-review-report.md`
