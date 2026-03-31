# Implementation Guide: Feature-Spec Review Fixes

**Feature:** FEAT-FSRF
**Source Review:** TASK-REV-FCA5

## Wave 1 (Parallel — no dependencies)

### TASK-FSRF-001: Commit FalkorDB workaround fix
- **Method**: direct (git operations)
- **Effort**: ~5 minutes
- **Action**: Stage and commit existing working-tree changes to `falkordb_workaround.py` and its test file

### TASK-FSRF-002: Fix write_outputs stack passthrough
- **Method**: task-work
- **Effort**: ~30 minutes
- **Action**: Add `stack` parameter to `write_outputs()`, update `execute()` caller, add tests

### TASK-FSRF-003: Update CLAUDE.md
- **Method**: direct
- **Effort**: ~10 minutes
- **Action**: Add `/feature-spec` to Essential Commands section

### TASK-FSRF-006: Update README statuses
- **Method**: direct
- **Effort**: ~5 minutes
- **Action**: Update task table in `tasks/backlog/feature-spec-command/README.md`

## Wave 2 (After TASK-FSRF-002)

### TASK-FSRF-004: Add scan result to FeatureSpecResult
- **Method**: task-work
- **Effort**: ~30 minutes
- **Action**: Add fields to dataclass, populate in execute(), add tests

### TASK-FSRF-005: Extend input file extensions
- **Method**: task-work
- **Effort**: ~30 minutes
- **Action**: Extend `SUPPORTED_EXTENSIONS`, add tests for each type

## Total Estimated Effort

- Wave 1: ~50 minutes (parallel)
- Wave 2: ~60 minutes (parallel)
- **Total**: ~2 hours (wall-clock ~1 hour with parallelisation)
