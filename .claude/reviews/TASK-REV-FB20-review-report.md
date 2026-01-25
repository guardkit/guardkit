# Review Report: TASK-REV-FB20

## Executive Summary

The architectural score fix (TASK-FBSDK-018 through TASK-FBSDK-022) was **partially implemented but has a critical integration gap**. The test shows `task type: feature` being used instead of `scaffolding`, causing architectural review to fail repeatedly.

**Root Cause Identified**: Two integration gaps prevent `task_type` from reaching CoachValidator:

1. **Gap 1 (Primary)**: `autobuild.py:1590` passes only `{"acceptance_criteria": [...]}` to CoachValidator, not the full task metadata including `task_type`
2. **Gap 2 (Secondary)**: Task file lacks `task_type` in frontmatter - `/feature-plan` execution path may not be using `implement_orchestrator.py`

**Decision**: The fix is well-understood and localized. Implementation requires passing task frontmatter to CoachValidator.

---

## Review Details

| Field | Value |
|-------|-------|
| **Mode** | Decision Analysis |
| **Depth** | Comprehensive |
| **Duration** | ~45 minutes |
| **Files Analyzed** | 12 |
| **Root Cause** | Integration gap in data flow |

---

## Findings

### Finding 1: CoachValidator Not Receiving task_type (CRITICAL)

**Evidence**: `guardkit/orchestrator/autobuild.py:1586-1591`

```python
validator = CoachValidator(str(worktree.path))
validation_result = validator.validate(
    task_id=task_id,
    turn=turn,
    task={"acceptance_criteria": acceptance_criteria or []},  # Missing task_type!
)
```

The `task` dict passed to `validate()` only contains `acceptance_criteria`. The `task_type` field is never included.

**Impact**: CoachValidator's `_resolve_task_type()` method at line 309-314 defaults to `TaskType.FEATURE` when `task_type` is not present:

```python
task_type_str = task.get("task_type")
if task_type_str is None:
    logger.debug("No task_type specified, defaulting to FEATURE profile")
    return TaskType.FEATURE
```

### Finding 2: Task File Missing task_type Field

**Evidence**: Actual task file frontmatter from test:

```yaml
---
id: TASK-FHE-001
title: Create project structure and configuration
status: blocked
created: 2026-01-22 10:00:00+00:00
priority: high
tags: [fastapi, setup, configuration]
complexity: 2
parent_review: TASK-REV-A3F8
feature_id: FEAT-FHE-001
wave: 1
implementation_mode: task-work
dependencies: []
# NOTE: task_type field is MISSING!
---
```

The `implement_orchestrator.py` code (TASK-FBSDK-022) writes `task_type` at line 275, but the test file doesn't have it. This suggests the Claude Code execution path didn't use the updated orchestrator.

### Finding 3: TaskLoader Extracts Frontmatter But It's Not Passed Through

**Evidence**: `guardkit/tasks/task_loader.py:206-213`

```python
return {
    "task_id": task_id,
    "requirements": requirements,
    "acceptance_criteria": acceptance_criteria,
    "frontmatter": metadata,  # Contains task_type if present
    "content": post.content,
    "file_path": path,
}
```

The frontmatter is loaded but the orchestrator only extracts `acceptance_criteria` to pass to Coach.

### Finding 4: Quality Gate Profiles Working Correctly

**Evidence**: `guardkit/models/task_types.py:163-170`

The SCAFFOLDING profile is correctly defined:

```python
TaskType.SCAFFOLDING: QualityGateProfile(
    arch_review_required=False,  # Would skip arch review
    arch_review_threshold=0,
    coverage_required=False,
    coverage_threshold=0.0,
    tests_required=False,
    plan_audit_required=True,
)
```

The CoachValidator correctly applies profiles when `task_type` is provided (verified in unit tests).

### Finding 5: Confirmation from Logs

**Evidence**: Test output shows:

```
INFO:guardkit.orchestrator.quality_gates.coach_validator:Using quality gate profile for task type: feature
```

This confirms CoachValidator is defaulting to `feature` (not `scaffolding`) because it's not receiving `task_type`.

---

## Data Flow Analysis

### Expected Flow (Post-Fix)

```
/feature-plan
    └── implement_orchestrator.py
        └── detect_task_type() → TaskType.SCAFFOLDING
            └── Write frontmatter: task_type: scaffolding
                └── Task file created

guardkit autobuild feature
    └── TaskLoader.load_task()
        └── Returns {frontmatter: {task_type: "scaffolding"}}
            └── autobuild.py._invoke_coach_safely()
                └── Pass task_type to CoachValidator
                    └── get_profile(TaskType.SCAFFOLDING)
                        └── arch_review_required=False ✓
```

### Actual Flow (Current - Broken)

```
/feature-plan  [BREAK 1: May not use implement_orchestrator.py]
    └── Task file created WITHOUT task_type

guardkit autobuild feature
    └── TaskLoader.load_task()
        └── Returns {frontmatter: {}} (no task_type)
            └── autobuild.py._invoke_coach_safely()
                └── Pass ONLY acceptance_criteria [BREAK 2]
                    └── CoachValidator._resolve_task_type()
                        └── task_type = None → default FEATURE
                            └── arch_review_required=True ✗
```

---

## Recommendations

### Recommendation 1: Pass task_type to CoachValidator (CRITICAL)

**Location**: `guardkit/orchestrator/autobuild.py:1586-1591`

**Fix**: The orchestrator needs to load and pass the full task data including `task_type`:

```python
# Current (broken)
task={"acceptance_criteria": acceptance_criteria or []}

# Fix: Include task_type from loaded task data
task={
    "acceptance_criteria": acceptance_criteria or [],
    "task_type": task_data.get("frontmatter", {}).get("task_type"),
}
```

**Complexity**: Low (single code location, ~10 lines changed)
**Risk**: Low (additive change, backward compatible)

### Recommendation 2: Add task_type to Orchestrate Method Signature

**Location**: `guardkit/orchestrator/autobuild.py` - `orchestrate()` method

**Fix**: Add optional `task_type` parameter and pass through the call chain:

```python
def orchestrate(
    self,
    task_id: str,
    requirements: str,
    acceptance_criteria: List[str],
    base_branch: str = "main",
    task_file_path: Optional[Path] = None,
    task_type: Optional[str] = None,  # NEW
) -> OrchestrationResult:
```

**Complexity**: Low-Medium (multiple method signatures to update)
**Risk**: Low (optional parameter, backward compatible)

### Recommendation 3: Verify /feature-plan Uses implement_orchestrator.py

**Investigation**: Confirm Claude Code's `/feature-plan` command actually invokes the Python script that writes `task_type`.

**Possible Issues**:
- Claude Code may generate task files directly instead of using the script
- The skill may have been executed before TASK-FBSDK-022 was merged

**Action**: Test `/feature-plan` with verbose logging to verify `implement_orchestrator.py` is called.

### Recommendation 4: Add Integration Test

**Test Case**: End-to-end test that:
1. Creates a feature via `/feature-plan`
2. Runs `guardkit autobuild feature`
3. Verifies scaffolding tasks skip architectural review

**Location**: `tests/integration/test_task_type_end_to_end.py`

---

## Decision Matrix

| Option | Effort | Risk | Coverage | Recommendation |
|--------|--------|------|----------|----------------|
| Fix Gap 1 Only (autobuild.py) | Low | Low | 80% | Implement |
| Fix Gap 1 + Gap 2 (both) | Medium | Low | 100% | **Implement** |
| Skip arch review via CLI flag | Low | Medium | Workaround | Not recommended |
| Increase max_turns | None | High | 0% | Not recommended |

---

## Implementation Tasks

### TASK-FBSDK-025: Pass task_type to CoachValidator

**Title**: Fix task_type data flow from task file to CoachValidator

**Description**: Modify `autobuild.py` to load task frontmatter and pass `task_type` to CoachValidator.validate()

**Files**:
- `guardkit/orchestrator/autobuild.py` - Pass task_type in _invoke_coach_safely()
- `guardkit/orchestrator/autobuild.py` - Update _run_loop() to pass task_data
- `tests/unit/test_coach_validator_task_type.py` - Integration test

**Acceptance Criteria**:
- [ ] CoachValidator receives task_type from task frontmatter
- [ ] Scaffolding tasks skip architectural review
- [ ] Feature tasks still require architectural review
- [ ] Unit tests pass
- [ ] Integration test verifies end-to-end flow

**Complexity**: 4/10
**Implementation Mode**: task-work

### TASK-FBSDK-026: Verify feature-plan Task Type Generation

**Title**: Verify /feature-plan creates task files with task_type in frontmatter

**Description**: Create test to verify Claude Code's /feature-plan skill uses implement_orchestrator.py and writes task_type to frontmatter.

**Files**:
- Manual test: Run `/feature-plan` and inspect generated files
- `tests/integration/test_feature_plan_generates_task_type.py`

**Acceptance Criteria**:
- [ ] Generated task files contain task_type in frontmatter
- [ ] task_type correctly matches detection rules (scaffolding/feature/etc.)
- [ ] Integration test covers the full generation flow

**Complexity**: 3/10
**Implementation Mode**: direct (verification + test)

---

## Appendix

### Log Evidence

```
INFO:guardkit.orchestrator.quality_gates.coach_validator:Using quality gate profile for task type: feature
INFO:guardkit.orchestrator.quality_gates.coach_validator:Quality gate evaluation complete:
    tests=True (required=True),
    coverage=True (required=True),
    arch=False (required=True),  ← FAILING GATE
    audit=True (required=True),
    ALL_PASSED=False
```

### Code References

| File | Line | Purpose |
|------|------|---------|
| `autobuild.py` | 1590 | CoachValidator invocation (missing task_type) |
| `coach_validator.py` | 309-314 | task_type resolution with default |
| `task_types.py` | 163-170 | SCAFFOLDING profile definition |
| `implement_orchestrator.py` | 275 | task_type frontmatter writing |
| `task_loader.py` | 206 | Frontmatter extraction |

### Test Worktree

Location: `/Users/richardwoollcott/Projects/guardkit_testing/simple_feature_test/.guardkit/worktrees/FEAT-FHE-001`

Task file analyzed: `tasks/backlog/fastapi-health-endpoint/TASK-FHE-001-create-project-structure.md`

---

## Conclusion

The architectural score fix infrastructure (task types, profiles, CoachValidator integration) is **correctly implemented**. The failure is due to a **simple integration gap**: the autobuild orchestrator doesn't pass `task_type` from task frontmatter to CoachValidator.

The fix is localized, low-risk, and can be implemented in a single task (TASK-FBSDK-025).

**Recommendation**: **[I]mplement** - Create TASK-FBSDK-025 to fix the data flow and TASK-FBSDK-026 to verify the generation path.
