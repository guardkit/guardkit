---
complexity: 4
dependencies: []
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR3-001
implementation_mode: task-work
parallel_group: wave1-gr003
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-003
task_type: feature
title: Implement FeatureDetector class
wave: 1
completed_at: "2026-02-01T12:30:00Z"
test_coverage: 96
test_count: 22
---

# Implement FeatureDetector class

## Description

Create the `FeatureDetector` class that detects feature specs from IDs and descriptions. This is the foundation for auto-detecting feature context during `/feature-plan`.

## Acceptance Criteria

- [x] `detect_feature_id(description: str) -> Optional[str]` extracts FEAT-XXX pattern from text
- [x] `find_feature_spec(feature_id: str) -> Optional[Path]` searches default paths for matching spec
- [x] `find_related_features(feature_id: str) -> List[Path]` finds features with same prefix
- [x] Searches `docs/features/`, `.guardkit/features/`, `features/` directories
- [x] Unit tests cover pattern matching and file discovery

## Technical Details

**Location**: `guardkit/knowledge/feature_detector.py`

**Pattern**: `FEAT-[A-Z0-9]+-\d+` (e.g., FEAT-SKEL-001, FEAT-GR-003)

**Reference**: See `docs/research/graphiti-refinement/FEAT-GR-003-feature-spec-integration.md` for full specification.

## Implementation Summary

### Files Created
1. `guardkit/knowledge/feature_detector.py` (145 lines)
   - FeatureDetector class with 3 public methods
   - Compiled regex pattern for performance
   - Graceful handling of missing directories

2. `tests/unit/knowledge/test_feature_detector.py` (289 lines)
   - 22 test cases across 5 test classes
   - 96% code coverage

### TDD Workflow
- **RED**: Tests written first (22 tests, all failing)
- **GREEN**: Implementation to make tests pass
- **REFACTOR**: Code review (APPROVED)

## Code Review Summary

**Status**: APPROVED

**Positive Findings**:
- Excellent documentation with examples
- Clean error handling (TypeError for None, graceful degradation)
- Python best practices (type hints, Pathlib, compiled regex)
- Consistent with GuardKit patterns

**Minor Notes**:
- One edge case (single-part feature ID) could have additional test
- All critical functionality fully tested
