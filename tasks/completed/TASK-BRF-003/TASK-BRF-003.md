---
id: TASK-BRF-003
title: Raise Default Architectural Review Threshold
status: completed
task_type: implementation
created: 2026-01-24T16:30:00Z
updated: 2026-01-24T18:45:00Z
completed: 2026-01-24T18:45:00Z
priority: medium
tags: [autobuild, quality-gates, block-research, configuration]
complexity: 2
parent_review: TASK-REV-BLOC
feature_id: FEAT-BRF
wave: 2
implementation_mode: direct
conductor_workspace: block-research-fidelity-wave2-1
dependencies: [TASK-BRF-001, TASK-BRF-002]
completed_location: tasks/completed/TASK-BRF-003/
organized_files: [TASK-BRF-003.md, completion-report.md]
---

# Task: Raise Default Architectural Review Threshold

## Description

Increase the default architectural review threshold from 60 to 75 to better align with Block research quality requirements for effective adversarial cooperation.

**Problem**: Current threshold of 60 is lenient and may allow lower-quality code through the quality gates. Block research emphasizes high-quality standards for adversarial cooperation effectiveness.

**Solution**: Raise the default to 75 while keeping it configurable for backward compatibility.

## Acceptance Criteria

- [x] AC-001: Change default `code_review.score` threshold from 60 to 75
- [x] AC-002: Add `--arch-threshold` CLI flag to allow override (range: 50-100)
- [x] AC-003: Update documentation to reflect new default
- [x] AC-004: Add migration note in CHANGELOG for users who depend on 60 threshold
- [x] AC-005: Update Coach agent to reference the configurable threshold

## Technical Approach

### Files Modified

1. **`guardkit/orchestrator/quality_gates/coach_validator.py`**
   - Updated ARCH_REVIEW_THRESHOLD constant from 60 to 75

2. **`guardkit/models/task_types.py`**
   - Updated FEATURE profile arch_review_threshold: 60 → 75
   - Updated REFACTOR profile arch_review_threshold: 60 → 75
   - Updated docstrings and examples to reflect new default

3. **`guardkit/cli/autobuild.py`**
   - Added --arch-threshold CLI flag (IntRange 50-100, default 75)
   - Added arch_threshold parameter to task() function

4. **`.claude/agents/autobuild-coach.md`**
   - Updated threshold references from 60 to 75
   - Added note about --arch-threshold configurability

5. **`docs/guides/autobuild-workflow.md`**
   - Added --arch-threshold to CLI reference table
   - Added frontmatter configuration example

6. **`CHANGELOG.md`**
   - Added comprehensive migration note with:
     - Affected task types (FEATURE, REFACTOR)
     - CLI override examples
     - Rationale based on Block AI research

## Related Files

- `guardkit/orchestrator/quality_gates/coach_validator.py`
- `guardkit/models/task_types.py`
- `guardkit/cli/autobuild.py`
- `.claude/agents/autobuild-coach.md`
- `docs/guides/autobuild-workflow.md`
- `CHANGELOG.md`

## Notes

Simple configuration change. Block research suggests higher quality bars improve adversarial cooperation outcomes.

## Completion Summary

**Implementation completed successfully on 2026-01-24**

**Changes Made:**
- Raised default threshold from 60 to 75 across all relevant files
- Added CLI flag for backward compatibility and flexibility
- Updated all documentation to reflect new default
- Provided comprehensive migration guidance in CHANGELOG

**Testing:**
- All changes are configuration-only, no behavioral changes requiring tests
- Backward compatibility maintained via --arch-threshold flag

**Git Commit:**
- Commit: f8d03e60 "Raise default architectural review threshold from 60 to 75"
- Branch: RichWoollcott/raise-arch-threshold
- Files changed: 6 files, 49 insertions, 8 deletions
