# Implementation Guide: Feature Plan Schema Fix

## Overview

This feature fixes the schema mismatch between `/feature-plan` output and `FeatureLoader` expectations, which currently causes `/feature-build` to fail with multiple errors.

## Problem Statement

When running `/feature-build FEAT-XXX`, the CLI fails because:
1. `file_path` field is missing from task entries (stored in separate `task_files` section)
2. `execution_groups` format doesn't match expected `parallel_groups` format
3. Fresh repositories fail with "invalid reference: main"

## Solution Approach

Update the **generator** (feature-plan) to match the **consumer** (FeatureLoader), rather than modifying the consumer. This is the lower-risk approach with minimal code changes.

---

## Execution Waves

### Wave 1: Core Schema Fix (Parallel - 2 tasks)

These tasks can run in parallel as they modify different files.

| Task | Title | Mode | Workspace |
|------|-------|------|-----------|
| TASK-FP-001 | Update feature-plan.md schema documentation | task-work | fp-schema-wave1-docs |
| TASK-FP-002 | Update generate-feature-yaml script output | task-work | fp-schema-wave1-generator |

**Estimated Duration**: 3-4 hours (parallel)

**Conductor Command**:
```bash
conductor spawn --workspace fp-schema-wave1-docs
conductor spawn --workspace fp-schema-wave1-generator
```

---

### Wave 2: Edge Cases & UX (Parallel - 2 tasks)

These tasks handle edge cases and improve user experience.

| Task | Title | Mode | Workspace |
|------|-------|------|-----------|
| TASK-FP-003 | Add repository state check to worktree manager | task-work | fp-schema-wave2-worktree |
| TASK-FP-004 | Improve FeatureLoader error messages | direct | fp-schema-wave2-errors |

**Dependencies**: TASK-FP-004 depends on TASK-FP-001 (needs schema docs for error messages)

**Estimated Duration**: 2-3 hours (parallel)

---

### Wave 3: Testing (Sequential - 1 task)

Comprehensive testing after all changes are complete.

| Task | Title | Mode | Workspace |
|------|-------|------|-----------|
| TASK-FP-005 | Add unit tests for schema parsing edge cases | task-work | fp-schema-wave3-tests |

**Dependencies**: Depends on TASK-FP-002 and TASK-FP-004

**Estimated Duration**: 2 hours

---

## Dependency Graph

```
Wave 1 (parallel):
  TASK-FP-001 ──────────────────────┐
  TASK-FP-002 ──────────────────────┤
                                    │
Wave 2 (parallel):                  │
  TASK-FP-003 (independent)         │
  TASK-FP-004 ←── depends on ───────┘
                    │
Wave 3 (sequential): │
  TASK-FP-005 ←─────┴── depends on TASK-FP-002, TASK-FP-004
```

---

## Schema Changes Summary

### Before (Incorrect)

```yaml
tasks:
  - id: TASK-XXX
    name: "Task Name"
    wave: 1
    dependencies: []

task_files:
  - path: "tasks/backlog/.../TASK-XXX.md"

execution_groups:
  - wave: 1
    name: "Foundation"
    strategy: sequential
    tasks: [TASK-XXX]
```

### After (Correct)

```yaml
tasks:
  - id: TASK-XXX
    name: "Task Name"
    file_path: "tasks/backlog/.../TASK-XXX.md"
    status: pending
    complexity: 5
    dependencies: []
    implementation_mode: task-work
    estimated_minutes: 30

orchestration:
  parallel_groups:
    - - TASK-XXX
  estimated_duration_minutes: 30
  recommended_parallel: 1
```

---

## Verification Steps

After all tasks complete:

1. **Run schema validation**:
   ```bash
   python -m pytest tests/unit/test_feature_loader.py -v
   ```

2. **Test end-to-end**:
   ```bash
   # Create new feature
   /feature-plan "test feature"

   # Verify YAML generated correctly
   cat .guardkit/features/FEAT-XXX.yaml

   # Run feature build
   /feature-build FEAT-XXX
   ```

3. **Test fresh repository edge case**:
   ```bash
   mkdir test-repo && cd test-repo
   git init
   # Should get helpful error, not crash
   /feature-build FEAT-XXX
   ```

---

## Rollback Plan

If issues arise after deployment:

1. Schema documentation is backward compatible (just docs)
2. Generator script can be reverted to previous version
3. No database migrations or breaking API changes
4. All changes are additive to error handling

---

## Related Resources

- Review Report: [.claude/reviews/TASK-REV-66B4-review-report.md](../../.claude/reviews/TASK-REV-66B4-review-report.md)
- Error Log: [docs/reviews/feature-build/feature-build-output.md](../../../docs/reviews/feature-build/feature-build-output.md)
- FeatureLoader: [guardkit/orchestrator/feature_loader.py](../../../guardkit/orchestrator/feature_loader.py)
