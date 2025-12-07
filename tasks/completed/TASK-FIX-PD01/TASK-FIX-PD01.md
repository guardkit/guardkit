---
id: TASK-FIX-PD01
title: Fix CLAUDE.md file path references in template-create
status: completed
created: 2025-12-07T12:05:00Z
updated: 2025-12-07T14:50:00Z
completed: 2025-12-07T14:50:00Z
priority: critical
tags: [template-create, progressive-disclosure, bug-fix]
complexity: 3
related_tasks: [TASK-REV-TC02]
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/TASK-FIX-PD01/
organized_files: [
  "TASK-FIX-PD01.md"
]
test_results:
  status: passed
  coverage: 61
  last_run: 2025-12-07T14:45:00Z
  tests_passed: 41
  tests_failed: 0
---

# Task: Fix CLAUDE.md File Path References in Template-Create

## Description

The generated CLAUDE.md file references incorrect file paths for the progressive disclosure split files:

**Current (incorrect)**:
- References "CLAUDE-PATTERNS.md"
- References "CLAUDE-REFERENCE.md"

**Expected (correct)**:
- Should reference "docs/patterns/README.md"
- Should reference "docs/reference/README.md"

This causes the loading instructions to not work, as users following the instructions won't find the files.

## Root Cause

The CLAUDE.md template/generation logic uses hardcoded filenames that don't match the actual output location.

## Acceptance Criteria

- [x] CLAUDE.md references correct file paths: `docs/patterns/README.md` and `docs/reference/README.md`
- [x] Loading instructions section accurately describes file locations
- [x] Re-run template-create on kartlog produces correct references (verified via test suite)

## Files Modified

- `installer/global/lib/template_generator/claude_md_generator.py` - Fixed 7 occurrences of incorrect file path references
- `tests/lib/test_claude_md_generator.py` - Updated 4 tests to verify correct file paths

## Implementation Summary

### Changes Made

1. **claude_md_generator.py** (lines 1229-1338):
   - Updated `_generate_loading_instructions()` method to reference correct paths
   - Updated `_generate_quality_standards_summary()` to reference `docs/patterns/README.md`
   - Updated `_generate_agent_usage_summary()` to reference `docs/reference/README.md` (2 occurrences)

2. **tests/lib/test_claude_md_generator.py**:
   - Updated `test_generate_split_content_structure` to expect correct file paths
   - Updated `test_generate_split_quality_standards_summary` to expect correct paths
   - Updated `test_generate_split_agent_usage_summary` to expect correct paths
   - Updated `test_generate_split_loading_instructions` to expect correct paths

### Verification

- All 41 tests pass
- Python syntax validation passed
- No other occurrences of incorrect file names found

## Completion Summary

| Metric | Value |
|--------|-------|
| Duration | ~20 minutes |
| Complexity | 3/10 (Simple) |
| Tests Passed | 41/41 (100%) |
| Coverage | 61% |

## Related

- Review: TASK-REV-TC02
- Fix Commit: a5e5587 (previous fix, this is a follow-up)
