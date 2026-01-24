---
id: TASK-FC-003
title: Implement feature folder archival
status: completed
created: 2026-01-24T12:00:00Z
updated: 2026-01-24T08:16:09Z
completed: 2026-01-24T08:20:00Z
priority: medium
tags: [feature-complete, archival, file-management]
complexity: 2
parent_review: TASK-REV-FC01
feature_id: FEAT-FC-001
implementation_mode: direct
wave: 1
dependencies: []
estimated_minutes: 30
actual_duration_minutes: 90
completed_location: tasks/completed/TASK-FC-003/
organized_files:
  - TASK-FC-003-feature-folder-archival.md
quality_gates:
  compilation: passed
  tests_passing: passed (11/11)
  code_review: approved
previous_state: in_review
---

# Task: Implement feature folder archival

## Description

Implement the Phase 3 logic in `FeatureCompleteOrchestrator` that moves the feature folder from `tasks/backlog/{slug}/` to `tasks/completed/{date}/{slug}/` and updates the feature YAML status.

## Requirements

1. Add `_archive_phase()` method to `FeatureCompleteOrchestrator`:
   - Move feature folder: `tasks/backlog/{slug}/` → `tasks/completed/{date}/{slug}/`
   - Date format: `YYYY-MM-DD`
   - Update feature YAML: set `status: awaiting_merge`
   - Update `completion.archived_at` timestamp

2. Feature YAML updates in `.guardkit/features/FEAT-XXX.yaml`:
   ```yaml
   status: awaiting_merge
   completion:
     archived_at: "2026-01-24T12:00:00Z"
     archived_to: "tasks/completed/2026-01-24/fastapi-health/"
     tasks_completed: 5
     tasks_failed: 0
   ```

3. Handle edge cases:
   - Feature folder doesn't exist (already archived or manual move)
   - Target directory already exists (append suffix or error)
   - Permission errors

## Acceptance Criteria

- [x] `_archive_phase()` method implemented
- [x] Feature folder moved to `tasks/completed/{date}/{slug}/`
- [x] Feature YAML status updated to `awaiting_merge`
- [x] Completion metadata added to feature YAML
- [x] Works on both macOS and Linux
- [x] Handles missing folder gracefully
- [x] Unit tests for archival logic

## Implementation Summary

**Files Modified:**
1. `guardkit/orchestrator/feature_orchestrator.py`
   - Added `_archive_phase()` method (lines 1661-1733)
   - Added `_detect_feature_slug()` helper method (lines 1735-1811)

2. `guardkit/orchestrator/feature_loader.py`
   - Extended `FeatureExecution` dataclass with archival fields
   - Updated YAML parsing and serialization

**Files Created:**
1. `tests/integration/test_feature_archival.py`
   - 11 comprehensive tests covering all scenarios

**Test Results:**
- Total: 11 tests
- Passed: 11 (100%)
- Failed: 0
- Execution time: 1.54s

**Code Quality:**
- Lint: Clean (no issues)
- Error handling: Robust
- Cross-platform: Yes (pathlib)
- Documentation: Complete docstrings
