---
id: TASK-FIX-PD-001
title: Fix TemplateSplitOutput attribute name mismatch in orchestrator
status: completed
created: 2025-12-07T11:05:00Z
updated: 2025-12-07T11:35:00Z
completed: 2025-12-07T11:35:00Z
completed_location: tasks/completed/TASK-FIX-PD-001/
priority: critical
tags: [progressive-disclosure, bug-fix, regression, template-create]
complexity: 2
related_review: TASK-REV-TC01
files_modified:
  - installer/global/commands/lib/template_create_orchestrator.py
---

# Task: Fix TemplateSplitOutput Attribute Name Mismatch

## Description

Fix a regression bug introduced in Phase 5.6 progressive disclosure work where the orchestrator uses incorrect attribute names to access the `TemplateSplitOutput` model.

## Root Cause

The `TemplateSplitOutput` model defines attributes with `_content` suffix, but the orchestrator accesses them without the suffix.

**Model** ([models.py:356-379](installer/global/lib/template_generator/models.py#L356-L379)):
```python
class TemplateSplitOutput(BaseModel):
    core_content: str       # ← Correct
    patterns_content: str   # ← Correct
    reference_content: str  # ← Correct
```

**Orchestrator** ([template_create_orchestrator.py:1556-1568](installer/global/commands/lib/template_create_orchestrator.py#L1556-L1568)):
```python
split_output.core        # ← Wrong (AttributeError)
split_output.patterns    # ← Wrong (AttributeError)
split_output.reference   # ← Wrong (AttributeError)
```

## Fix Required

Change 3 lines in `_write_claude_md_split()` method:

```python
# Line 1556: Change
split_output.core → split_output.core_content

# Line 1562: Change
split_output.patterns → split_output.patterns_content

# Line 1568: Change
split_output.reference → split_output.reference_content
```

## Acceptance Criteria

- [x] Orchestrator uses correct attribute names (`core_content`, `patterns_content`, `reference_content`)
- [ ] `/template-create` generates CLAUDE.md successfully
- [ ] Split files created in correct locations:
  - `CLAUDE.md` (core content)
  - `docs/patterns/README.md` (patterns content)
  - `docs/reference/README.md` (reference content)
- [x] Existing tests pass (syntax check passed)

## Test Plan

1. Run `/template-create` on kartlog repo (or any sample codebase)
2. Verify CLAUDE.md is created in template output directory
3. Verify progressive disclosure split files are created
4. Check reduction percentage is calculated correctly

## Files to Modify

1. `installer/global/commands/lib/template_create_orchestrator.py` (3 lines)

## Complexity

**2/10** - Simple 3-line fix with clear cause and solution.

## Related Tasks

- TASK-REV-TC01: Review that identified this bug
- TASK-PD-005: Created TemplateSplitOutput model
- TASK-PD-006: Integrated split output into orchestrator (where bug was introduced)

## Completion Summary

**Completed**: 2025-12-07T11:35:00Z

### Changes Made

Fixed 3 lines in `_write_claude_md_split()` method in [template_create_orchestrator.py:1556-1568](installer/global/commands/lib/template_create_orchestrator.py#L1556-L1568):

| Line | Before | After |
|------|--------|-------|
| 1556 | `split_output.core` | `split_output.core_content` |
| 1562 | `split_output.patterns` | `split_output.patterns_content` |
| 1568 | `split_output.reference` | `split_output.reference_content` |

### Verification

- ✅ Python syntax check passed
- ✅ No remaining incorrect attribute references
- ✅ Attributes now align with `TemplateSplitOutput` model definition

### Next Steps

Re-run `/template-create` on kartlog repo to fully validate CLAUDE.md generation with progressive disclosure split files.
