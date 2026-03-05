---
id: TASK-FIX-ec01
title: Fix relative path in seed_pattern_examples.py using __file__ walk-up
status: completed
task_type: implementation
created: 2026-03-04T00:00:00Z
updated: 2026-03-04T00:00:00Z
completed: 2026-03-04T00:00:00Z
completed_location: tasks/completed/TASK-FIX-ec01/
priority: medium
tags: [graphiti, seeding, path-resolution, bug-fix]
complexity: 2
parent_review: TASK-REV-49AB
feature_id: FEAT-SQF
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Fix relative path in seed_pattern_examples.py using __file__ walk-up

## Description

`seed_pattern_examples.py:56` uses `Path(".claude/rules/patterns")` which resolves against the current working directory (the target project). This fails when running from any project other than the guardkit repo itself. The pattern files exist in the guardkit installation, not the target project.

## Root Cause (from TASK-REV-49AB)

- `seed_pattern_examples.py:56`: `patterns_dir = Path(".claude/rules/patterns")` — relative path
- Resolves as `CWD/.claude/rules/patterns/` → e.g., `/Users/.../vllm-profiling/.claude/rules/patterns/`
- Pattern files exist at `guardkit/.claude/rules/patterns/{dataclasses,pydantic-models,orchestrators}.md`
- Target project may not have these files at all (or has different ones)

## Correct Pattern (from seed_templates.py)

`seed_templates.py:20-37` uses the correct approach:

```python
def _get_templates_dir() -> Path:
    current = Path(__file__).resolve().parent
    while current != current.parent:
        candidate = current / "installer" / "core" / "templates"
        if candidate.is_dir():
            return candidate
        current = current.parent
    return Path.cwd() / "installer" / "core" / "templates"
```

## Change

**File**: `guardkit/knowledge/seed_pattern_examples.py`

```python
# BEFORE (line 56):
patterns_dir = Path(".claude/rules/patterns")

# AFTER:
def _get_patterns_dir() -> Path:
    """Locate the .claude/rules/patterns/ directory.

    Walks up from this file to find the guardkit project root, then resolves
    the patterns directory. Falls back to CWD-relative path.
    """
    current = Path(__file__).resolve().parent
    while current != current.parent:
        candidate = current / ".claude" / "rules" / "patterns"
        if candidate.is_dir():
            return candidate
        current = current.parent
    return Path.cwd() / ".claude" / "rules" / "patterns"

# In seed_pattern_examples():
patterns_dir = _get_patterns_dir()
```

## Evidence

From `reseed_init_project_8.md`:
```
ERROR: Pattern files not found: dataclasses, pydantic-models, orchestrators
```

This function has **never worked correctly** when running from a target project directory.

## Regression Risk

**None** — fixes a function that currently always fails when CWD is not the guardkit repo. The walk-up pattern is proven by `seed_templates.py` which works correctly.

## Acceptance Criteria

- [ ] New `_get_patterns_dir()` function using `Path(__file__).resolve().parent` walk-up
- [ ] `patterns_dir` assignment updated to call `_get_patterns_dir()`
- [ ] Pattern matches `seed_templates.py:_get_templates_dir()` approach
- [ ] Existing tests pass
- [ ] New test: verify `_get_patterns_dir()` resolves to guardkit's `.claude/rules/patterns/`
- [ ] New test: verify `_get_patterns_dir()` works when CWD is a different directory
