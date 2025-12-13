---
id: TASK-CDI-004
title: Fix testing.md path overlap
status: completed
created: 2025-12-13T17:00:00Z
updated: 2025-12-13T19:30:00Z
completed: 2025-12-13T19:30:00Z
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

- [x] Path patterns analyzed for overlap
- [x] Consolidated to minimal necessary patterns
- [x] No functional coverage lost
- [x] No syntax errors in frontmatter

## Completion Summary

**Completed: 2025-12-13T19:30:00Z**

### Analysis Results

Found test files in two locations:
1. `tests/` directory - standard test location
2. `installer/core/commands/lib/test_*.py` - 13 test files outside tests/

No `*_test.py` files exist anywhere in the codebase.

### Change Made

**Before:**
```yaml
paths: tests/**/*.py, **/test_*.py, **/*_test.py, **/conftest.py
```

**After:**
```yaml
paths: tests/**/*.py, **/test_*.py, **/conftest.py
```

### Rationale

- Removed `**/*_test.py` - no files match this pattern
- Kept `**/test_*.py` - needed for `installer/core/commands/lib/test_*.py` files (13 files)
- Kept `tests/**/*.py` - standard test directory
- Kept `**/conftest.py` - pytest fixtures in multiple locations

### Verification

The remaining patterns cover all 13 test files outside `tests/`:
- test_quick_review.py
- test_full_review.py
- test_complexity_comprehensive.py
- test_micro_basic.py
- test_agent_invocation_tracker.py
- test_agent_invocation_validator.py
- test_plan_integration.py
- test_micro_workflow.py
- test_refinement_handler.py
- test_complexity.py
- test_plan_markdown.py
- test_phase_gate_validator.py
- test_micro_task_detector.py

## Notes

- This is a low-risk change
- The functional behavior should remain identical
- Simplifies path matching logic
