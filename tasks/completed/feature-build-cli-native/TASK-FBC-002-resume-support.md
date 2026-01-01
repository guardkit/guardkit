---
id: TASK-FBC-002
title: Add resume support for feature orchestration
status: completed
created: 2025-12-31T17:00:00Z
completed: 2025-12-31T19:00:00Z
priority: medium
complexity: 5
tags: [cli, autobuild, resume, state-persistence]
parent_feature: feature-build-cli-native
source_review: TASK-REV-FB01
implementation_mode: task-work
estimated_hours: 4-6
dependencies: [TASK-FBC-001]
---

# Add Resume Support for Feature Orchestration

## Description

Enable `--resume` flag for feature-mode orchestration. Large features can be long-running and may be interrupted. Users should be able to resume from where they left off.

**User Impact**: Reduces frustration when long-running feature builds are interrupted.

## Requirements

1. **State Persistence**
   - Update feature YAML with task statuses after each completion
   - Track current wave and task progress
   - Store last successful turn for each task

2. **Resume Detection**
   - Detect incomplete feature execution
   - Prompt user to resume or start fresh
   - `--resume` flag to skip prompt

3. **Resume Execution**
   - Skip completed tasks
   - Resume current task from last turn
   - Continue with remaining waves

4. **Clean Start Option**
   - `--fresh` flag to ignore saved state
   - Clean up incomplete worktree

## Acceptance Criteria

- [x] Feature YAML updated after each task completion
- [x] `--resume` flag skips completed tasks
- [x] Interrupted tasks resume from last turn
- [x] `--fresh` flag starts from scratch
- [x] Prompt shown when incomplete state detected
- [x] State correctly persisted across process restarts

## Implementation Summary

### Files Modified

| File | Action | Description |
|------|--------|-------------|
| `guardkit/orchestrator/feature_loader.py` | Modified | Enhanced `FeatureTask` and `FeatureExecution` dataclasses with state tracking fields. Added `is_incomplete()`, `get_resume_point()`, and `reset_state()` static methods. |
| `guardkit/orchestrator/feature_orchestrator.py` | Modified | Added `fresh` parameter, rewrote `_setup_phase()` with resume/fresh logic, added helper methods for state tracking. |
| `guardkit/cli/autobuild.py` | Modified | Added `--fresh` flag, validation for mutually exclusive flags. |
| `tests/unit/test_feature_loader.py` | Modified | Added 11 new tests for resume functionality. |
| `tests/unit/test_feature_orchestrator.py` | Modified | Added 6 new tests for resume/fresh flag handling. |

### Key Implementation Details

1. **Enhanced Data Models**:
   - `FeatureTask`: Added `turns_completed`, `current_turn`, `started_at`, `completed_at` fields
   - `FeatureExecution`: Added `current_wave`, `completed_waves`, `last_updated` fields

2. **State Detection**:
   - `is_incomplete()`: Detects if a feature has incomplete execution state
   - `get_resume_point()`: Returns wave/task/turn to resume from
   - `reset_state()`: Clears all state for fresh start

3. **Resume Behavior**:
   - If incomplete state detected and no flags: prompts user to resume or start fresh
   - `--resume`: skip prompt, resume from last saved state
   - `--fresh`: skip prompt, start from scratch (clears previous state)
   - Cannot use both `--resume` and `--fresh` together

4. **Wave Tracking**:
   - Tracks current wave being executed
   - Records completed waves for resume
   - Updates `last_updated` timestamp after each state change

### Test Results

- 63 tests passing (36 feature_loader + 27 feature_orchestrator)
- All new resume functionality tests passing
- Type checking passes (only pre-existing YAML stub warning)

## Testing

```bash
# Run feature orchestration tests
pytest tests/unit/test_feature_loader.py tests/unit/test_feature_orchestrator.py -v

# Test resume behavior (manual)
guardkit autobuild feature FEAT-XXX
# Interrupt with Ctrl+C mid-execution

# Resume
guardkit autobuild feature FEAT-XXX --resume
# Verify skips completed tasks

# Fresh start
guardkit autobuild feature FEAT-XXX --fresh
# Should show: "Starting fresh, clearing previous state"
```

## Dependencies

- TASK-FBC-001 (CLI feature command) - Completed

## Notes

Resume support is critical for large features with many tasks. Without it, any interruption requires starting over.
