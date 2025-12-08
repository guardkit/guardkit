---
id: TASK-FIX-1CCE
title: Remove UX Design section from guardkit init instructions
status: completed
created: 2025-12-08T10:30:00Z
updated: 2025-12-08T12:20:00Z
completed: 2025-12-08T12:20:00Z
priority: normal
tags: [cleanup, init, ux]
complexity: 2
previous_state: in_review
state_transition_reason: "All acceptance criteria met, tests passed, ready for merge"
completed_location: tasks/completed/TASK-FIX-1CCE/
test_results:
  status: passed
  coverage: null
  last_run: 2025-12-08T12:15:00Z
---

# Task: Remove UX Design section from guardkit init instructions

## Description

Remove the "UX Design Integration" section from the output displayed when running `guardkit init`. This section references commands (`/figma-to-react` and `/zeplin-to-maui`) that are not yet implemented and are still under active development.

The CLAUDE.md already notes these are "Coming Soon" and should not be advertised as available commands.

## Current Output (removed)

```
  UX Design Integration:
    /figma-to-react   - Figma → React components
    /zeplin-to-maui   - Zeplin → MAUI components
```

## Affected File

- `installer/scripts/init-project.sh` (lines 507-509)

## Acceptance Criteria

- [x] UX Design Integration section removed from init-project.sh
- [x] No blank lines left where section was removed
- [x] guardkit init runs successfully after change

## Implementation Notes

Simple removal of 4 lines (including the blank line after) from the `show_final_summary` function in `installer/scripts/init-project.sh`.

## Test Requirements

- [x] Manual verification: run `guardkit init --dry-run` or similar to confirm output

## Test Execution Log

### Run 1 - 2025-12-08T12:15:00Z

**Verification Steps:**
1. Shell syntax check: `bash -n init-project.sh` - PASSED
2. Script execution: `./installer/scripts/init-project.sh --help` - PASSED
3. Grep verification: No matches for "UX Design|figma-to-react|zeplin-to-maui" - PASSED

**Changes Made:**
- Removed lines 507-510 from `installer/scripts/init-project.sh`:
  - `echo "  UX Design Integration:"`
  - `echo "    /figma-to-react   - Figma → React components"`
  - `echo "    /zeplin-to-maui   - Zeplin → MAUI components"`
  - `echo ""`

**Result:** All acceptance criteria met. Script syntax valid and executes correctly.

## Completion Summary

**Duration:** ~5 minutes (estimated: 15 minutes)
**Files Modified:** 1
**Lines Changed:** -4 lines removed
