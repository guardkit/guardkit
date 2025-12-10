---
id: TASK-FIX-PD05
title: Fix "When to Use" guidance accuracy in reference docs
status: completed
created: 2025-12-07T12:05:00Z
updated: 2025-12-07T14:30:00Z
completed: 2025-12-07T15:00:00Z
priority: high
tags: [template-create, documentation, bug-fix]
complexity: 4
related_tasks: [TASK-REV-TC02]
test_results:
  status: passed
  coverage: 62
  last_run: 2025-12-07T14:30:00Z
  tests_passed: 48
  tests_total: 48
---

# Task: Fix "When to Use" Guidance Accuracy in Reference Docs

## Description

The docs/reference/README.md contains misaligned "When to Use" guidance that doesn't match the agent's purpose:

**Current (incorrect)**:
```markdown
### firebase-firestore-specialist
**Purpose**: Firebase Firestore CRUD operations with authentication guards...
**When to Use**: Use this agent when creating UI components, implementing views, or working with user interfaces
```

**Expected**:
```markdown
### firebase-firestore-specialist
**Purpose**: Firebase Firestore CRUD operations with authentication guards...
**When to Use**: Use this agent when implementing database operations, Firestore queries, or data persistence logic
```

## Root Cause

The "When to Use" generation logic appears to use a generic template that doesn't match the agent's actual purpose/technologies.

## Acceptance Criteria

- [x] "When to Use" guidance matches agent purpose
- [x] Database agents → database-related guidance
- [x] UI agents → UI-related guidance
- [x] API agents → API-related guidance
- [x] Re-run template-create produces accurate guidance

## Implementation Notes

Consider deriving "When to Use" from:
- Agent technologies list
- Agent description keywords
- Category (ui, data, api, etc.)

## Files to Modify

- `installer/core/commands/lib/template_create_orchestrator.py` - Reference doc generation
- Or the agent categorization logic

## Test Plan

1. Run `/template-create` on a project with diverse agents
2. Verify each agent's "When to Use" matches its purpose
3. Verify no misalignment between purpose and guidance

## Related

- Review: TASK-REV-TC02

## Implementation Summary

### Files Modified
1. `installer/core/lib/template_generator/claude_md_generator.py`
   - Added `_categorize_agent_by_keywords()` method (lines 946-1016)
   - Refactored fallback logic in `_enhance_agent_info_with_ai()` (lines 1078-1099)

2. `tests/lib/test_claude_md_generator.py`
   - Added 5 new test functions (lines 1092-1372)

### Solution
- **Technology-first matching**: Checks agent technologies list before falling back to description keywords
- **Priority ordering**: database > testing > api > domain > ui > general (prevents false positives)
- **Expanded keywords**: Added 'firestore', 'firebase', 'crud', 'persistence', 'query', 'repository' to database detection
- **Removed 'view'**: Removed generic 'view' keyword from UI detection to prevent false matches

### Test Results
- 48/48 tests passing
- 0 regressions
- 62% file coverage (modified code 100% tested)
