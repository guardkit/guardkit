# Implementation Guide: Task Type Expansion

## Wave Breakdown

### Wave 1: Core Implementation (3 tasks, parallel)

These tasks can be executed in parallel as they modify different parts of the codebase.

| Task | Title | Workspace | Method |
|------|-------|-----------|--------|
| TASK-TT-001 | Add TESTING and REFACTOR to TaskType enum | task-type-wave1-enum | task-work |
| TASK-TT-002 | Add quality gate profiles for new types | task-type-wave1-profiles | task-work |
| TASK-TT-003 | Add testing keywords to task_type_detector | task-type-wave1-detector | task-work |

**Note**: TASK-TT-002 depends on TASK-TT-001 completing first (needs enum values). Run TASK-TT-001 and TASK-TT-003 in parallel, then TASK-TT-002.

### Wave 2: Verification (2 tasks, parallel)

After Wave 1 completes, verify the implementation.

| Task | Title | Workspace | Method |
|------|-------|-----------|--------|
| TASK-TT-004 | Add unit tests for new task types | task-type-wave2-tests | task-work |
| TASK-TT-005 | Verify existing tasks pass | task-type-wave2-verify | direct |

## Execution Strategy

```bash
# Wave 1a: Parallel (no dependencies)
/task-work TASK-TT-001  # Add enum values
/task-work TASK-TT-003  # Add detector keywords

# Wave 1b: Sequential (depends on TASK-TT-001)
/task-work TASK-TT-002  # Add profiles (after TASK-TT-001)

# Wave 2: Parallel (after Wave 1)
/task-work TASK-TT-004  # Add tests
# TASK-TT-005 is direct verification
```

## Key Implementation Details

### TASK-TT-001: Enum Values

Add to `guardkit/models/task_types.py`:

```python
class TaskType(Enum):
    SCAFFOLDING = "scaffolding"
    FEATURE = "feature"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
    TESTING = "testing"          # NEW
    REFACTOR = "refactor"        # NEW
```

### TASK-TT-002: Quality Gate Profiles

Add to `DEFAULT_PROFILES` in `guardkit/models/task_types.py`:

```python
TaskType.TESTING: QualityGateProfile(
    arch_review_required=False,
    arch_review_threshold=0,
    coverage_required=False,
    coverage_threshold=0.0,
    tests_required=True,
    plan_audit_required=True,
),
TaskType.REFACTOR: QualityGateProfile(
    arch_review_required=True,
    arch_review_threshold=60,
    coverage_required=True,
    coverage_threshold=80.0,
    tests_required=True,
    plan_audit_required=True,
),
```

### TASK-TT-003: Detector Keywords

Add to `KEYWORD_MAPPINGS` in `guardkit/lib/task_type_detector.py`:

```python
TaskType.TESTING: [
    "test",
    "testing",
    "pytest",
    "unittest",
    "jest",
    "vitest",
    "spec",
    "e2e",
    "integration test",
    "unit test",
],
TaskType.REFACTOR: [
    "refactor",
    "refactoring",
    "migrate",
    "migration",
    "upgrade",
    "modernize",
    "cleanup",
    "clean up",
],
```

**Important**: Update the priority order to check TESTING before SCAFFOLDING (since "setup testing" could match both).

## Verification Checklist

After all tasks complete:

- [ ] `TaskType("testing")` returns `TaskType.TESTING`
- [ ] `TaskType("refactor")` returns `TaskType.REFACTOR`
- [ ] `get_profile(TaskType.TESTING)` returns appropriate profile
- [ ] `get_profile(TaskType.REFACTOR)` returns appropriate profile
- [ ] `detect_task_type("Add unit tests")` returns `TaskType.TESTING`
- [ ] `detect_task_type("Refactor auth module")` returns `TaskType.REFACTOR`
- [ ] Coach validation passes for tasks with `task_type: testing`
- [ ] Existing tests still pass

## Risk Mitigation

1. **Backward Compatibility**: Existing valid task types must continue working
2. **Priority Order**: TESTING keywords must be checked before SCAFFOLDING to avoid "setup" matching first
3. **Profile Defaults**: TESTING and REFACTOR profiles should have sensible defaults
