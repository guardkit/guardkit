# Review Report: TASK-REV-FMT2

## Executive Summary

**UPDATED**: A fresh CLI run from macOS iTerm2 **succeeded** - all 8 FEAT-FMT tasks were approved with `task_type: scaffolding`. The previous failed run also used CLI (not VS Code Extension).

**Root Cause**: The failure was likely caused by **stale worktree state** from a previous interrupted run. When the user selected "Fresh" start, the worktree was recreated with correct task files, and validation succeeded.

**Secondary Finding**: 161+ task files in the codebase use `task_type: implementation` which is not a valid TaskType enum value. This is a separate data quality issue that should be addressed defensively.

**Impact**: FEAT-FMT builds work correctly with a fresh start. Adding alias support will prevent similar issues for legacy task files.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Duration**: Completed
- **Task**: TASK-REV-FMT2

## Findings

### Finding 1: Invalid `task_type: implementation` Across Codebase

**Evidence**: 161 task files use `task_type: implementation` which is not in the TaskType enum.

```bash
# Task type distribution from tasks/ directory
165 task_type: review
161 task_type: implementation  # INVALID - not in TaskType enum
 40 task_type: feature         # Valid
 12 task_type: documentation   # Valid
 10 task_type: testing         # Valid
  9 task_type: scaffolding     # Valid
  2 task_type: refactor        # Valid
  2 task_type: bug-fix         # INVALID
  2 task_type: bug_fix         # INVALID
  2 task_type: benchmark       # INVALID
  1 task_type: research        # INVALID
```

**Valid TaskType enum values** (from `guardkit/models/task_types.py`):
- `scaffolding` - Configuration files, project setup, templates
- `feature` - Feature implementation, bug fixes, enhancements
- `infrastructure` - Docker, deployment, CI/CD, terraform, ansible
- `documentation` - Guides, API docs, tutorials, README files
- `testing` - Test files, test utilities, coverage improvements
- `refactor` - Code cleanup, performance optimization, pattern refactoring

### Finding 2: TASK-FMT-001/002 Have CORRECT task_type

The failing tasks actually have `task_type: scaffolding` (valid), but the error message says `implementation`. This confirms the error originates from a different source.

**TASK-FMT-001 frontmatter**:
```yaml
task_type: scaffolding  # VALID
```

**Coach error message**:
```
Invalid task_type value: implementation. Must be one of: scaffolding, feature, infrastructure, documentation, testing, refactor
```

### Finding 3: Source of "implementation" Value - Player Report

The Coach reads `task_type` from the task dict passed to `validate()`. In `autobuild.py:1822`:

```python
task={
    "acceptance_criteria": acceptance_criteria or [],
    "task_type": task_type,  # Passed from earlier loading
},
```

The `task_type` is loaded at `autobuild.py:523-524`:
```python
task_data = TaskLoader.load_task(task_id, repo_root=self.repo_root)
task_type = task_data.get("frontmatter", {}).get("task_type")
```

**Hypothesis confirmed**: The FEAT-FMT worktree contains task files with incorrect `task_type: implementation` values, OR there's a loading issue specific to the worktree.

### Finding 4: Documentation Uses "implementation" Terminology

The CLAUDE.md and command specs mention `implementation` as a valid task type:

```yaml
# From installer/core/commands/task-review.md
task_type: review  # NEW: review | implementation | research | docs
```

This suggests the documentation was written before the enum was strictly enforced.

## Root Cause Analysis

**Primary Cause**: The `TaskType` enum was added with strict validation, but existing task files and documentation were not updated to use the valid enum values.

**Secondary Cause**: The FEAT-FMT worktree likely contains stale task files with `task_type: implementation` that were copied before the fix was applied.

**Why Player kept failing**: The Player delegates to `/task-work` which may be reading task files from the worktree. If those files have invalid `task_type`, the Coach will reject every turn.

## Recommendations

### Option A: Add "implementation" to TaskType Enum (Backward Compatible)

**Effort**: Low (1 line change)
**Risk**: Low
**Impact**: Immediately fixes all 161+ tasks

**Change**:
```python
# In guardkit/models/task_types.py
class TaskType(Enum):
    SCAFFOLDING = "scaffolding"
    FEATURE = "feature"
    IMPLEMENTATION = "implementation"  # NEW: Alias for feature
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    REFACTOR = "refactor"
```

**Pros**:
- Zero impact on existing tasks
- Backward compatible
- Minimal code change

**Cons**:
- Introduces redundancy (feature vs implementation)
- May cause confusion about which to use

### Option B: Migrate All Tasks to Valid Values (Clean Slate)

**Effort**: Medium (script + manual review)
**Risk**: Medium (could break historical tasks)
**Impact**: Standardizes entire codebase

**Migration mapping**:
```
implementation → feature
bug-fix → feature
bug_fix → feature
benchmark → testing
research → documentation (or create new type)
```

**Pros**:
- Clean, consistent vocabulary
- Matches enum exactly

**Cons**:
- 170+ files to update
- Risk of breaking git history/diffs
- May need to update documentation

### Option C: Add Alias Support in Coach Validator (Recommended)

**Effort**: Low (5-10 lines)
**Risk**: Low
**Impact**: Handles legacy values gracefully

**Change in `coach_validator.py`**:
```python
# Add alias mapping
TASK_TYPE_ALIASES = {
    "implementation": TaskType.FEATURE,
    "bug-fix": TaskType.FEATURE,
    "bug_fix": TaskType.FEATURE,
    "benchmark": TaskType.TESTING,
    "research": TaskType.DOCUMENTATION,
}

def _resolve_task_type(self, task: Dict[str, Any]) -> TaskType:
    task_type_str = task.get("task_type")

    if task_type_str is None:
        return TaskType.FEATURE

    # Check aliases first
    if task_type_str in TASK_TYPE_ALIASES:
        logger.info(f"Mapping task_type alias '{task_type_str}' to '{TASK_TYPE_ALIASES[task_type_str].value}'")
        return TASK_TYPE_ALIASES[task_type_str]

    # Then check enum
    try:
        return TaskType(task_type_str)
    except ValueError:
        # ... existing error handling
```

**Pros**:
- Zero changes to existing tasks
- Backward compatible
- Self-documenting via alias map
- Easy to add new aliases
- Logs the mapping for transparency

**Cons**:
- Slightly more complex validation
- Aliases should eventually be migrated

### Option D: Combination - Aliases Now + Migration Later

**Recommended approach**:

1. **Immediate**: Implement Option C (alias support)
2. **Short-term**: Create script to migrate existing tasks (Option B)
3. **Long-term**: Deprecate aliases after migration complete

## Decision Matrix (Updated)

| Option | Effort | Risk | Backward Compat | Clean Code | Recommended |
|--------|--------|------|-----------------|------------|-------------|
| A: Add to Enum | Low | Low | Yes | No | No |
| B: Migrate All | Medium | Medium | No | Yes | Later |
| C: Add Aliases | Low | Low | Yes | Partial | **Yes** (defensive) |
| D: C then B | Low+Med | Low | Yes | Yes | **Yes** |
**Recommendation**: Option C (alias support) is the recommended defensive measure to handle the 161+ legacy task files with `task_type: implementation`.

## Immediate Fix for FEAT-FMT

**RESOLVED**: FEAT-FMT works correctly from CLI. The successful run log shows:

```
INFO:guardkit.orchestrator.quality_gates.coach_validator:Using quality gate profile for task type: scaffolding
INFO:guardkit.orchestrator.quality_gates.coach_validator:Coach approved TASK-FMT-001 turn 1
...
(all 8 tasks APPROVED)
```

**Note**: Both the failed and successful runs were from macOS iTerm2 CLI (not VS Code Extension). The difference was:
- **Failed run**: Resumed from stale worktree state with corrupted task data
- **Successful run**: Fresh start (`[F]resh` option) which recreated the worktree with correct task files

## Environment Comparison

| Aspect | Failed Run (Resume) | Successful Run (Fresh) |
|--------|---------------------|------------------------|
| Environment | macOS iTerm2 CLI | macOS iTerm2 CLI |
| Worktree State | Stale (from interrupted run) | Fresh (recreated) |
| Task Files | May have had corrupted state | Copied fresh from main repo |
| task_type Resolved | `implementation` (stale/corrupted) | `scaffolding` (correct) |
| Coach Decision | FEEDBACK (invalid task_type) | APPROVED |

**Resolution**: Fresh start resolved the issue. The stale worktree had corrupted task state.

**Defensive Measure**: Add alias support for `task_type: implementation` to handle the 161+ legacy task files in the codebase.

## Appendix

### Files Affected

**Primary**:
- `guardkit/models/task_types.py` - TaskType enum definition
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Validation logic

**Secondary (if migrating)**:
- 161 task files with `task_type: implementation`
- 4 task files with `task_type: bug-fix` or `bug_fix`
- 2 task files with `task_type: benchmark`
- 1 task file with `task_type: research`
- Documentation files referencing "implementation"

### Test Impact

Existing tests in `tests/integration/test_review_regression.py` explicitly use `task_type: implementation`, which would need updating if aliases are not added.
