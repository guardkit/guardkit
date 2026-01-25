---
id: TASK-FC-001
title: Create feature-complete orchestrator skeleton
status: completed
created: 2026-01-24T12:00:00Z
updated: 2026-01-24T14:30:00Z
completed: 2026-01-24T14:45:00Z
priority: high
tags: [feature-complete, orchestrator, architecture]
complexity: 3
parent_review: TASK-REV-FC01
feature_id: FEAT-FC-001
implementation_mode: task-work
wave: 1
dependencies: []
estimated_minutes: 45
actual_minutes: 25
workflow_mode: minimal
intensity: minimal
auto_detected: true
completed_location: tasks/completed/TASK-FC-001/
organized_files: [TASK-FC-001.md]
test_results:
  compilation: passed
  tests_total: 16
  tests_passed: 16
  tests_failed: 0
  coverage_line: 100
  coverage_branch: 100
---

# Task: Create feature-complete orchestrator skeleton

## Description

Create the core `FeatureCompleteOrchestrator` class that coordinates the feature completion workflow. This orchestrator handles the three-phase execution pattern: Validation → Completion → Handoff.

## Requirements

1. Create `guardkit/orchestrator/feature_complete.py` with:
   - `FeatureCompleteOrchestrator` class
   - Three-phase execution: validate, complete tasks, display handoff instructions
   - Integration with `FeatureLoader` for feature YAML operations
   - Integration with `WorktreeManager` for worktree status

2. Add CLI command in `guardkit/cli/autobuild.py`:
   - `guardkit autobuild complete FEAT-XXX` command
   - Basic flags: `--dry-run`, `--force`

3. Follow existing patterns from:
   - `feature_orchestrator.py` (phase pattern)
   - `autobuild.py` (CLI integration)

## Acceptance Criteria

- [x] `FeatureCompleteOrchestrator` class created with `complete()` method
- [x] Phase 1 (Validation): Checks feature exists and status is valid
- [x] Phase 2 (Completion): Placeholder for task completion (implemented in TASK-FC-002)
- [x] Phase 3 (Handoff): Placeholder for instructions (implemented in TASK-FC-004)
- [x] CLI command `guardkit autobuild complete FEAT-XXX` works
- [x] `--dry-run` flag shows what would happen without executing
- [x] Unit tests for orchestrator skeleton

## Implementation Summary

### Files Created
1. **guardkit/orchestrator/feature_complete.py** - 245 lines
   - FeatureCompleteOrchestrator class with 4-phase workflow
   - FeatureCompleteResult dataclass
   - FeatureCompleteError exception
   - Integration with FeatureLoader and WorktreeManager

2. **tests/orchestrator/test_feature_complete.py** - 16 tests
   - Initialization tests
   - Validation phase tests (success, errors, force mode, worktree detection)
   - Placeholder phase tests (completion, archival, handoff)
   - Complete method tests (success, errors, dry-run)
   - Data model tests

### Files Modified
1. **guardkit/cli/autobuild.py**
   - Added imports for FeatureCompleteOrchestrator
   - Added `guardkit autobuild complete FEAT-XXX` command
   - Flags: --dry-run, --force
   - Helper function _display_complete_result()

### Test Results
- ✅ All 16 tests passing
- ✅ CLI command verified (--help works)
- ✅ 100% coverage of new code

### Quality Gates
- ✅ Code compiles
- ✅ All tests passing (100%)
- ✅ CLI command functional
- ✅ Integration verified

## Completion Report

**Duration**: 25 minutes (estimated: 45 minutes, 44% under estimate)
**Workflow**: MINIMAL (auto-detected from parent_review + complexity)
**All Acceptance Criteria**: Met ✅

**Next Tasks in Feature**:
- TASK-FC-002: Task Completion Phase
- TASK-FC-003: Archival Phase
- TASK-FC-004: Handoff Instructions Phase

## Technical Notes

```python
# Skeleton structure
class FeatureCompleteOrchestrator:
    def __init__(self, repo_root: Path, ...):
        self.repo_root = repo_root
        self._feature_loader = FeatureLoader
        self._worktree_manager = WorktreeManager(repo_root)

    def complete(self, feature_id: str, dry_run: bool = False) -> FeatureCompleteResult:
        """Execute feature completion workflow."""
        # Phase 1: Validation
        feature = self._validate_phase(feature_id)
        
        if dry_run:
            return self._dry_run_result(feature)
        
        # Phase 2: Task Completion (TASK-FC-002)
        task_results = self._complete_tasks_phase(feature)
        
        # Phase 3: Archival (TASK-FC-003)
        self._archive_phase(feature)
        
        # Phase 4: Handoff Instructions (TASK-FC-004)
        self._display_handoff(feature)
        
        return FeatureCompleteResult(...)
```
