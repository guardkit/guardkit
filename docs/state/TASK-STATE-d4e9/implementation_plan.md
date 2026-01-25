# Implementation Plan: TASK-STATE-d4e9

**Task**: Implement multi-layered partial work detection
**Status**: Pending Approval
**Created**: 2026-01-08
**Complexity**: 8/10 (HIGH)
**Architectural Review**: 82/100 (APPROVED WITH RECOMMENDATIONS)

---

## Executive Summary

This plan implements a phased solution to fix the single point of failure in AutoBuild state tracking. The current system loses all work when Player times out without writing `player_turn_N.json`, despite files created and tests passing.

### Problem Evidence (TASK-INFRA-001)
- 224-line config.py created
- ~400-line test file created
- 32/40 tests passing (80%)
- Player timed out at 300s
- **No JSON report = 100% work loss**

### Architectural Issues Fixed
- **DIP Violation**: State tracking tightly coupled to JSON format
- **OCP Violation**: Cannot extend detection mechanisms
- **SRP Violation**: Mixed state persistence and detection concerns

---

## Architecture Overview

The solution uses a **cascade detection pattern** with three layers:

1. **Layer 1: Player JSON** (highest fidelity) - Primary source of truth
2. **Layer 2: Test Results** (verifies implementation quality) - Reuses CoachVerifier
3. **Layer 3: Git Changes** (detects file-level work) - Filesystem verification

```
Current (Single Point of Failure):
┌─────────────┐
│   Player    │───[JSON report]───┐
└─────────────┘                   │
                                  ▼
                          ┌──────────────┐
                          │ AutoBuild    │
                          │ Orchestrator │
                          └──────────────┘
                                  │
                          [No report = 100% loss]

Proposed (Multi-Layered Detection):
┌─────────────┐
│   Player    │───[JSON report]───┐ (Layer 1: Highest fidelity)
└─────────────┘                   │
                                  ▼
┌─────────────┐          ┌──────────────────┐
│CoachVerifier│───────▶  │ StateTracker/    │
│ (tests)     │          │ Detection        │
└─────────────┘          │ Cascade          │
                         └──────────────────┘
┌─────────────┐                   │
│ Git Changes │───────────────────┘ (Layer 3: File-level)
└─────────────┘
```

---

## Files to Create

### 1. `guardkit/orchestrator/state_detection.py` (~200 LOC)

**Purpose**: Lightweight detection functions for git changes and test results

**Contents**:
- `GitChangesSummary` dataclass - Summary of git changes
- `TestResultsSummary` dataclass - Summary of test results
- `detect_git_changes(worktree_path)` - Detect uncommitted changes via git
- `detect_test_results(worktree_path)` - Detect test results via CoachVerifier
- `_parse_diff_stats(diff_output)` - Parse insertions/deletions

### 2. `guardkit/orchestrator/state_tracker.py` (~400 LOC)

**Purpose**: State tracker abstraction and multi-layered implementation

**Contents**:
- `WorkState` dataclass - Unified state representation
- `StateTracker` ABC - Abstract interface (fixes DIP violation)
- `MultiLayeredStateTracker` - Cascade detection implementation

**Note**: Per architectural review, Phase 3 ABC may be deferred if Phase 1-2 are sufficient.

### 3. `tests/unit/test_state_detection.py` (~300 LOC)

**Purpose**: Unit tests for detection functions

**Test Cases**:
- `test_detect_no_changes` - No changes in worktree
- `test_detect_modified_files` - Modified files detected
- `test_detect_new_files` - New files detected
- `test_parse_diff_stats` - Diff statistics parsing
- `test_detect_passing_tests` - Passing tests detected
- `test_detect_failing_tests` - Failing tests detected
- `test_no_tests_present` - Handle no tests gracefully

### 4. `tests/unit/test_state_tracker.py` (~300 LOC)

**Purpose**: Unit tests for state tracker

**Test Cases**:
- `test_capture_with_player_report` - Player JSON available
- `test_capture_without_player_report` - Fallback detection
- `test_cascade_priority` - Verify cascade order
- `test_synthesize_from_git_only` - Git-only detection
- `test_backward_compatibility` - Player reports still work

---

## Files to Modify

### `guardkit/orchestrator/autobuild.py` (+40 LOC)

**Location**: `_execute_turn` method, after Player invocation

**Changes**:
1. Import detection functions
2. On Player failure, attempt git detection
3. On git changes found, attempt test detection
4. Enhanced error reporting with detected work
5. Create partial TurnRecord from detected state

---

## External Dependencies

**None** - Uses only stdlib and existing GuardKit modules

**Internal Dependencies**:
- `guardkit.orchestrator.coach_verification.CoachVerifier` (for test execution)
- `guardkit.worktrees.manager.WorktreeManager` (for worktree paths)

---

## Phased Implementation

### Phase 1: Git-Based Detection (IMMEDIATE)
- **Complexity**: 4/10
- **Effort**: 2-3 hours
- **Priority**: IMMEDIATE
- **Files**: `state_detection.py` (partial), `autobuild.py` (integration)

### Phase 2: Test-Based Verification (HIGH)
- **Complexity**: 5/10
- **Effort**: 3-4 hours
- **Priority**: HIGH
- **Files**: `state_detection.py` (complete), tests

### Phase 3: Comprehensive State Tracker (MEDIUM - Optional)
- **Complexity**: 8/10
- **Effort**: 1-2 days (or 4-6 hours per review recommendation)
- **Priority**: MEDIUM
- **Files**: `state_tracker.py`, integration tests
- **Note**: Consider deferring ABC to Phase 4 per architectural review

---

## Estimated Effort

| Phase | Complexity | Duration | LOC |
|-------|------------|----------|-----|
| Phase 1 | 4/10 | 2-3 hours | ~150 |
| Phase 2 | 5/10 | 3-4 hours | ~200 |
| Phase 3 | 8/10 | 4-6 hours* | ~400 |
| **Total** | **8/10** | **1-1.5 days** | **~1200** |

*Reduced from 1-2 days per architectural review recommendations

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Git detection fails | Low | Low | Catch exceptions, log warnings |
| False positives | Medium | Low | Only report, don't auto-recover |
| Performance overhead | Low | Low | Only runs on Player failure |
| Test execution timeout | Medium | Medium | Use existing timeout (120s) |
| Breaking backward compat | Low | High | Comprehensive integration tests |

---

## Architectural Review Recommendations

### Priority 1: Immediate (Apply during implementation)
1. Add timeout handling to git commands (5 seconds)
2. Make WorkState fields explicitly Optional
3. Add error recovery cascade in integration

### Priority 2: Design Adjustments
4. Accept CoachVerifier as DI parameter for testability
5. Consider CommandExecutor protocol for git commands

### Priority 3: Scope Reduction (Optional)
6. Defer StateTracker ABC to Phase 4
7. Remove restore_state() method until needed

---

## Success Criteria

- [ ] Phase 1: Git detection catches 100% of file changes when Player times out
- [ ] Phase 2: Test detection provides quality signal (passing/failing)
- [ ] Phase 3: State tracker provides unified interface (if implemented)
- [ ] All phases: Zero breaking changes to existing workflows
- [ ] All phases: Backward compatible with Player JSON reports

---

## Design Patterns Used

1. **Strategy Pattern**: StateTracker ABC enables interchangeable strategies
2. **Chain of Responsibility**: Cascade detection (Player → Tests → Git)
3. **Dataclass Pattern**: Lightweight state containers (GuardKit standard)

---

## Plan Version

- **Version**: v1
- **Created**: 2026-01-08
- **Architectural Score**: 82/100
- **Status**: Pending Human Approval
