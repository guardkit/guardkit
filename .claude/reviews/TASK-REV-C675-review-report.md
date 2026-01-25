# Architectural Review Report: TASK-REV-C675

## Executive Summary

This review analyzes the current AutoBuild CLI task discovery mechanism and provides recommendations for adding nested directory support. The core issue is straightforward: the `TaskLoader` class only searches for exact filename matches at the top level of each state directory, but `/feature-plan` and `/task-review [I]mplement` create tasks in feature-specific subfolders.

**Architecture Score: 72/100**
- SOLID Compliance: 7/10
- DRY Adherence: 6/10 (duplicate task resolution logic across modules)
- YAGNI Compliance: 8/10

**Risk Level: Low**
- Changes are isolated to task discovery logic
- Existing tests provide good coverage for current behavior
- Fallback behavior maintains backward compatibility

---

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard
- **Duration**: ~45 minutes
- **Reviewer**: Claude Code (architectural-reviewer mode)

---

## Findings

### Finding 1: TaskLoader Uses Non-Recursive Search (HIGH PRIORITY)

**Location**: [guardkit/tasks/task_loader.py:144-150](guardkit/tasks/task_loader.py#L144-L150)

**Evidence**:
```python
def _find_task_file(task_id: str, repo_root: Path) -> Path:
    for dir_name in TaskLoader.SEARCH_PATHS:
        task_path = repo_root / "tasks" / dir_name / f"{task_id}.md"
        if task_path.exists():
            return task_path
    return None
```

**Issue**: The search only looks for exact filename matches (`{task_id}.md`) directly in each state directory. It does not search subdirectories where feature tasks are created.

**Impact**:
- `/feature-build TASK-XX-001` fails when task is in `tasks/backlog/feature-slug/TASK-XX-001.md`
- All tasks created via `/feature-plan` or `/task-review [I]mplement` are unreachable

---

### Finding 2: Inconsistent Task Resolution Across Modules (MEDIUM PRIORITY)

**Evidence**: Three different modules implement task file discovery with varying approaches:

| Module | Method | Recursive? |
|--------|--------|------------|
| `TaskLoader._find_task_file()` | Exact path match | No |
| `task_completion_helper.find_task_file()` | `iterdir()` + glob | Partial (1 level) |
| `task_utils.move_task_to_blocked()` | `rglob()` | Yes |

**Locations**:
- [guardkit/tasks/task_loader.py:144-150](guardkit/tasks/task_loader.py#L144-L150)
- [installer/core/commands/lib/task_completion_helper.py:97-114](installer/core/commands/lib/task_completion_helper.py#L97-L114)
- [installer/core/commands/lib/task_utils.py:332-346](installer/core/commands/lib/task_utils.py#L332-L346)

**Impact**: DRY violation - same problem solved differently in different places, leading to inconsistent behavior and maintenance burden.

---

### Finding 3: Feature Subfolder Pattern Is Established (POSITIVE)

**Evidence**: The `implement_orchestrator.py` creates the expected nested structure:

```python
def create_subfolder(self) -> None:
    self.subfolder_path = f"tasks/backlog/{self.feature_slug}"
    os.makedirs(self.subfolder_path, exist_ok=True)
```

**Location**: [installer/core/lib/implement_orchestrator.py:222-229](installer/core/lib/implement_orchestrator.py#L222-L229)

**Impact**: The architecture already assumes nested directories exist. Only the discovery logic needs updating.

---

### Finding 4: Test Coverage Gap for Nested Directories

**Location**: [tests/unit/test_task_loader.py](tests/unit/test_task_loader.py)

**Evidence**: Current tests only verify:
- Loading from flat `tasks/backlog/` directory
- Loading from flat `tasks/in_progress/` directory
- Search order between directories

No tests exist for:
- Loading from `tasks/backlog/feature-slug/TASK-XXX.md`
- Loading with extended filename (`TASK-XXX-descriptive-name.md`)
- Loading from multiple nested levels

---

### Finding 5: Error Messages Don't Mention Subdirectories

**Location**: [guardkit/tasks/task_loader.py:115-123](guardkit/tasks/task_loader.py#L115-L123)

**Evidence**:
```python
raise TaskNotFoundError(
    f"Task {task_id} not found.\n\n"
    f"Searched locations:\n"
    + "\n".join(f"  - {path}" for path in searched)
)
```

The error message lists only top-level directories, not subdirectories, making debugging harder when tasks exist in feature folders.

---

## Recommendations

### Recommendation 1: Update TaskLoader._find_task_file() to Use rglob (HIGH PRIORITY)

**What**: Replace exact path matching with recursive glob pattern.

**Why**:
- Single point of change
- `rglob` is already used successfully in `task_utils.move_task_to_blocked()`
- Maintains backward compatibility (still finds flat files)

**Proposed Change**:
```python
@staticmethod
def _find_task_file(task_id: str, repo_root: Path) -> Path:
    """Find task file using recursive glob."""
    for dir_name in TaskLoader.SEARCH_PATHS:
        search_dir = repo_root / "tasks" / dir_name
        if not search_dir.exists():
            continue

        # Use rglob for recursive search
        # Pattern matches: TASK-XXX.md or TASK-XXX-descriptive-name.md
        for task_path in search_dir.rglob(f"{task_id}*.md"):
            logger.debug(f"Found task {task_id} at {task_path}")
            return task_path

    return None
```

**Effort**: ~30 minutes implementation + testing

---

### Recommendation 2: Add Comprehensive Tests for Nested Directories (MEDIUM PRIORITY)

**What**: Add unit tests for nested task discovery.

**Tests to Add**:
1. `test_load_task_from_nested_backlog` - Task in `tasks/backlog/feature-slug/`
2. `test_load_task_with_extended_filename` - Task named `TASK-XXX-name.md`
3. `test_load_task_deep_nesting` - Task in multiple nesting levels
4. `test_error_message_includes_subdirectories` - Error message improvement

**Effort**: ~45 minutes

---

### Recommendation 3: Unify Task Resolution Logic (LOW PRIORITY - FUTURE)

**What**: Extract shared task resolution to a single utility, deprecating duplicates.

**Current Duplicates**:
- `TaskLoader._find_task_file()`
- `task_completion_helper.find_task_file()`
- `task_utils.move_task_to_blocked()` (search portion)

**Proposed**: Create `guardkit.tasks.resolver.find_task()` as single source of truth.

**Why Defer**: Current fix is localized. Unification can be done as separate refactoring task.

**Effort**: ~2 hours (separate task)

---

### Recommendation 4: Improve Error Messages (LOW PRIORITY)

**What**: Update error messages to indicate subdirectories were searched.

**Proposed**:
```python
raise TaskNotFoundError(
    f"Task {task_id} not found.\n\n"
    f"Searched locations (including subdirectories):\n"
    + "\n".join(f"  - {path}/**/" for path in searched)
)
```

**Effort**: ~10 minutes

---

## Implementation Priority Matrix

| Recommendation | Priority | Effort | Risk | Order |
|----------------|----------|--------|------|-------|
| R1: Update TaskLoader | HIGH | 30min | Low | 1 |
| R2: Add nested tests | MEDIUM | 45min | None | 2 |
| R4: Improve errors | LOW | 10min | None | 3 |
| R3: Unify resolution | LOW | 2h | Medium | Future |

---

## Decision Options

Based on this review, the recommended path is:

**Option A: Minimal Fix (Recommended)**
- Implement R1 (recursive search in TaskLoader)
- Implement R2 (tests)
- Implement R4 (error messages)
- Total effort: ~1.5 hours
- Risk: Low

**Option B: Comprehensive Refactor**
- Implement R1-R4 including R3 (unified resolution)
- Total effort: ~4 hours
- Risk: Medium (touching multiple modules)

**Option C: Quick Workaround**
- Document that `/feature-build` requires full path
- Users must specify `tasks/backlog/feature-slug/TASK-XXX.md`
- No code changes
- Poor UX, not recommended

---

## Appendix

### Files Analyzed

1. [guardkit/tasks/task_loader.py](guardkit/tasks/task_loader.py) - Core task loading (323 lines)
2. [guardkit/cli/autobuild.py](guardkit/cli/autobuild.py) - AutoBuild CLI
3. [guardkit/orchestrator/autobuild.py](guardkit/orchestrator/autobuild.py) - AutoBuild orchestrator
4. [installer/core/commands/lib/task_completion_helper.py](installer/core/commands/lib/task_completion_helper.py) - Task completion utilities
5. [installer/core/commands/lib/task_utils.py](installer/core/commands/lib/task_utils.py) - Task utilities (uses rglob)
6. [installer/core/lib/implement_orchestrator.py](installer/core/lib/implement_orchestrator.py) - Creates nested structure
7. [installer/core/commands/feature-build.md](installer/core/commands/feature-build.md) - Command spec
8. [tests/unit/test_task_loader.py](tests/unit/test_task_loader.py) - Existing tests

### Related Tasks

- **Origin**: Tasks created by `/feature-plan` or `/task-review [I]mplement` are placed in nested directories
- **Consumer**: `/feature-build` and AutoBuild CLI need to find these tasks

### Architectural Patterns Observed

- **Single Responsibility**: TaskLoader handles only loading, orchestrator handles workflow
- **Open/Closed**: Current design requires modification (not extension) to support nesting
- **DRY Violation**: Multiple task resolution implementations exist

---

*Review completed: 2025-12-31*
