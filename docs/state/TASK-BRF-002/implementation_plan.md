# Implementation Plan: TASK-BRF-002

**Task**: Add Worktree State Checkpoint and Rollback Mechanism
**Created**: 2026-01-24T20:50:00Z
**Complexity**: 7/10
**Estimated Duration**: ~7 hours

## Overview

Implement checkpoint/rollback mechanism for worktree state to mitigate context pollution from accumulated failed code across turns.

## Files to Create/Modify

### New Files (1)
1. `guardkit/orchestrator/worktree_checkpoints.py` (250 lines)
   - `Checkpoint` dataclass
   - `CheckpointError` exceptions
   - `WorktreeCheckpointManager` class

### Modified Files (2)
2. `guardkit/orchestrator/autobuild.py` (+50 lines)
   - Integration in `_loop_phase()`
   - Add checkpoint manager instantiation
3. `guardkit/cli/autobuild.py` (+15 lines)
   - Add `--enable-checkpoints` flag
   - Add `--rollback-on-pollution` flag

### Test Files (1)
4. `tests/unit/test_worktree_checkpoints.py` (new)
   - Unit tests for checkpoint manager
   - Integration tests with orchestrator

**Total Files**: 2 new + 2 modified = 4 files

## External Dependencies

No new external dependencies required. Uses existing:
- `subprocess` (stdlib)
- `pathlib` (stdlib)
- `dataclasses` (stdlib)
- `json` (stdlib)

## Architecture Patterns

- **Checkpoint Pattern**: Git commit-based state snapshots
- **Orchestrator Pattern**: Integration into AutoBuildOrchestrator
- **Strategy Pattern**: Pluggable checkpoint manager
- **DI Pattern**: CommandExecutor protocol (recommendation)

## Implementation Phases

### Phase 1: Core Checkpoint Manager (2.5 hours, 40%)
- Create `Checkpoint` dataclass
- Implement `WorktreeCheckpointManager`:
  - `create_checkpoint(turn, test_results)`
  - `rollback_to(turn)`
  - `detect_pollution()`
  - `_save_checkpoints()` / `_load_checkpoints()`

### Phase 2: AutoBuild Integration (2 hours, 30%)
- Add checkpoint manager to orchestrator
- Create checkpoint after each turn
- Add pollution detection before turn execution
- Handle rollback logging

### Phase 3: CLI Flags (45 min, 10%)
- Add `--enable-checkpoints/--no-checkpoints`
- Add `--rollback-on-pollution/--no-rollback-on-pollution`
- Update CLI help text

### Phase 4: Testing (1.5 hours, 20%)
- Unit tests for checkpoint manager
- Integration tests with orchestrator
- Target: ≥80% coverage

## Risk Mitigations

1. **Git Operation Failures**
   - Risk: Checkpoint creation may fail
   - Mitigation: Try/except with detailed error logging

2. **State Loss on Rollback**
   - Risk: Rollback discards all subsequent work
   - Mitigation: Preserve checkpoint history, log rollback actions

3. **Pollution Detection False Positives**
   - Risk: Auto-rollback may trigger incorrectly
   - Mitigation: `--rollback-on-pollution` flag for control

## Test Strategy

### Unit Tests
- `test_create_checkpoint_creates_commit`
- `test_rollback_resets_to_checkpoint_state`
- `test_detect_pollution_on_repeated_failures`
- `test_no_pollution_on_different_failures`
- `test_checkpoint_persistence`

### Integration Tests
- `test_checkpoint_created_after_each_turn`
- `test_rollback_triggered_on_pollution`

**Coverage Target**: ≥80% line, ≥75% branch

## Architectural Review Notes

**Score**: 72/100 (Approved with Recommendations)

**Recommendations**:
1. Simplify persistence - use git log instead of JSON file (YAGNI)
2. Extract git operations to CommandExecutor protocol (DRY + ISP)
3. Consider manual rollback only for MVP (YAGNI)
4. Extract persistence to repository if keeping JSON (SRP)

## Acceptance Criteria Mapping

- AC-001: `create_checkpoint()` method ✓
- AC-002: `rollback_to()` method ✓
- AC-003: `--enable-checkpoints` CLI flag ✓
- AC-004: Auto-rollback via `detect_pollution()` ✓
- AC-005: Commit message format `[guardkit-checkpoint] Turn {N}` ✓
- AC-006: Checkpoint history in checkpoints.json ✓
- AC-007: `--rollback-on-pollution` CLI flag ✓
- AC-008: Unit/integration tests ≥80% coverage ✓

## Next Steps

1. Implement Phase 1 (Core Checkpoint Manager)
2. Implement Phase 2 (AutoBuild Integration)
3. Implement Phase 3 (CLI Flags)
4. Implement Phase 4 (Testing)
5. Run quality gates (compilation, tests, coverage)
6. Code review
