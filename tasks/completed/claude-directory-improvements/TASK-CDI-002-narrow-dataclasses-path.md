---
id: TASK-CDI-002
title: Narrow dataclasses.md path pattern
status: completed
created: 2025-12-13T17:00:00Z
updated: 2025-12-13T19:30:00Z
completed: 2025-12-13T19:30:00Z
priority: high
tags: [rules-structure, patterns, dataclasses, path-optimization]
parent_task: TASK-REV-79E0
implementation_mode: direct
wave: 1
conductor_workspace: claude-improvements-wave1-dataclasses
complexity: 1
depends_on:
  - TASK-REV-79E0
---

# Task: Narrow dataclasses.md path pattern

## Description

Update the path pattern in `.claude/rules/patterns/dataclasses.md` to be more specific, avoiding unnecessary loading for all Python files.

## Source

TASK-REV-79E0 code quality review identified this as a high-priority issue:
> "dataclasses.md path too broad - `**/*.py` matches all Python files"

## Current State

```yaml
---
paths: "**/*.py"
---
```

This causes the dataclasses rules to load for **every Python file**, even when dataclasses are not relevant.

## Target State

```yaml
---
paths: "**/state*.py", "**/*_state.py", "**/*result*.py", "**/*context*.py"
---
```

This targets files that typically contain dataclass definitions in GuardKit:
- `**/state*.py` - State containers
- `**/*_state.py` - State modules
- `**/*result*.py` - Result types
- `**/*context*.py` - Context objects

## Implementation

### File to Edit
`.claude/rules/patterns/dataclasses.md`

### Change Required
Edit line 2 (the paths frontmatter) from:
```yaml
paths: "**/*.py"
```
to:
```yaml
paths: "**/state*.py", "**/*_state.py", "**/*result*.py", "**/*context*.py"
```

## Acceptance Criteria

- [x] Path pattern updated in dataclasses.md
- [x] Pattern validated against actual GuardKit dataclass usage
- [x] No syntax errors in frontmatter

## Verification

Check that the pattern matches relevant GuardKit files:
```bash
find installer/core/lib -name "*state*.py" -o -name "*result*.py" -o -name "*context*.py"
```

## Notes

- This is a simple frontmatter edit
- No content changes required
- Test that rules load correctly after change
