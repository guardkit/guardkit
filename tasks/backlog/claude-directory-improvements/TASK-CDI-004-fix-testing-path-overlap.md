---
id: TASK-CDI-004
title: Fix testing.md path overlap
status: backlog
created: 2025-12-13T17:00:00Z
updated: 2025-12-13T17:00:00Z
priority: medium
tags: [rules-structure, testing, path-optimization]
parent_task: TASK-REV-79E0
implementation_mode: direct
wave: 2
conductor_workspace: claude-improvements-wave2-testing
complexity: 1
depends_on:
  - TASK-CDI-001
  - TASK-CDI-002
  - TASK-CDI-003
---

# Task: Fix testing.md path overlap

## Description

Consolidate the overlapping path patterns in `.claude/rules/testing.md` to prevent potential duplicate rule loading.

## Source

TASK-REV-79E0 code quality review identified this as a medium-priority issue:
> "testing.md overlapping path patterns - Has both `tests/**/*.py` and `**/test_*.py, **/*_test.py`"

## Current State

```yaml
---
paths: tests/**/*.py, **/test_*.py, **/*_test.py, **/conftest.py
---
```

The patterns overlap:
- `tests/**/*.py` - Matches all Python files in tests/ directory
- `**/test_*.py` - Matches test files anywhere (overlaps with tests/)
- `**/*_test.py` - Matches test files anywhere (overlaps with tests/)

## Target State

Option A: Consolidate to single comprehensive pattern
```yaml
---
paths: tests/**/*.py, **/conftest.py
---
```

Option B: Keep both but ensure no functional overlap
```yaml
---
paths: "tests/**/*.py", "**/conftest.py"
---
```

## Implementation

### File to Edit
`.claude/rules/testing.md`

### Analysis Required

1. Check if test files exist outside `tests/` directory in GuardKit
2. Determine if `**/test_*.py` and `**/*_test.py` are needed

```bash
# Check for test files outside tests/ directory
find . -name "test_*.py" -not -path "./tests/*" -not -path "./.*"
find . -name "*_test.py" -not -path "./tests/*" -not -path "./.*"
```

### Recommended Change

If no test files exist outside `tests/`:
```yaml
---
paths: tests/**/*.py, **/conftest.py
---
```

## Acceptance Criteria

- [ ] Path patterns analyzed for overlap
- [ ] Consolidated to minimal necessary patterns
- [ ] No functional coverage lost
- [ ] No syntax errors in frontmatter

## Notes

- This is a low-risk change
- The functional behavior should remain identical
- Simplifies path matching logic
