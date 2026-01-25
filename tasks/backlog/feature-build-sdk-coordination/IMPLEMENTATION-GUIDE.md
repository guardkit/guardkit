# Implementation Guide: Feature-Build SDK Coordination

## Wave Execution Strategy

### Wave 1: Blocking Fixes (P0)
**Duration**: 3 days
**Dependencies**: None

Both tasks can run in parallel using Conductor workspaces.

| Task | Workspace | Effort |
|------|-----------|--------|
| TASK-FBSDK-001 | feature-build-sdk-wave1-1 | 1 day |
| TASK-FBSDK-002 | feature-build-sdk-wave1-2 | 2 days |

**Commands**:
```bash
# Terminal 1
conductor workspace feature-build-sdk-wave1-1
/task-work TASK-FBSDK-001

# Terminal 2
conductor workspace feature-build-sdk-wave1-2
/task-work TASK-FBSDK-002
```

**Verification**:
1. Task files are copied to worktree during setup
2. `task_work_results.json` is created after SDK execution
3. Feature-build reaches Coach validation without "not found" errors

---

### Wave 2: Coordination Improvements (P1-P2)
**Duration**: 1.5 days
**Dependencies**: Wave 1 complete

Both tasks can run in parallel.

| Task | Workspace | Effort |
|------|-----------|--------|
| TASK-FBSDK-003 | feature-build-sdk-wave2-1 | 1 day |
| TASK-FBSDK-004 | feature-build-sdk-wave2-2 | 0.5 days |

**Commands**:
```bash
# Terminal 1
conductor workspace feature-build-sdk-wave2-1
/task-work TASK-FBSDK-003

# Terminal 2
conductor workspace feature-build-sdk-wave2-2
/task-work TASK-FBSDK-004
```

**Verification**:
1. All path references use `TaskArtifactPaths`
2. Feature tasks have stub plans when pre-loop is disabled

---

### Wave 3: Optimization (P3)
**Duration**: 0.5 days
**Dependencies**: Wave 2 complete

| Task | Workspace | Effort |
|------|-----------|--------|
| TASK-FBSDK-005 | feature-build-sdk-wave3-1 | 0.5 days |

**Commands**:
```bash
conductor workspace feature-build-sdk-wave3-1
/task-work TASK-FBSDK-005
```

Or use direct implementation since it's low complexity:
```bash
# Manually update timeout logic and documentation
```

**Verification**:
1. Timeout is pre-loop-aware
2. Documentation updated

---

## Integration Testing

After all waves complete, verify end-to-end:

```bash
# Create simple test feature
/feature-plan "Create hello world app"

# Run feature-build
guardkit autobuild feature FEAT-XXX --max-turns 3

# Expected: At least one task should complete without "not found" errors
```

## Rollback Plan

If issues arise:
1. Wave 1 changes are additive (task copy, results write)
2. Wave 2 changes are refactoring (can revert to inline paths)
3. Wave 3 changes are configuration (can use CLI override)

No destructive changes are introduced.

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| Feature-build success rate | 0% | >80% |
| Coach "not found" errors | 100% | 0% |
| State transition failures | 100% | <5% |
