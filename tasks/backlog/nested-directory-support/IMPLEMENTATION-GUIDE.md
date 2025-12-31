# Implementation Guide: Nested Directory Support

## Feature Overview

This feature adds recursive directory search to the AutoBuild CLI's task discovery mechanism, enabling tasks created by `/feature-plan` and `/task-review [I]mplement` to be found in feature subfolders.

**Parent Review**: TASK-REV-C675
**Architecture Score**: 72/100
**Total Tasks**: 3
**Estimated Effort**: ~1.5 hours

---

## Wave Execution Strategy

### Wave 1: Core Implementation (1 task)

| Task | Title | Mode | Effort |
|------|-------|------|--------|
| TASK-NDS-001 | Update TaskLoader to use rglob | task-work | 30 min |

**Dependencies**: None
**Parallel Execution**: N/A (single task)

```bash
# Execute Wave 1
/task-work TASK-NDS-001
```

### Wave 2: Tests & Polish (2 tasks)

| Task | Title | Mode | Effort |
|------|-------|------|--------|
| TASK-NDS-002 | Add nested directory tests | task-work | 45 min |
| TASK-NDS-003 | Improve error messages | direct | 10 min |

**Dependencies**: Both depend on TASK-NDS-001
**Parallel Execution**: Can run simultaneously

```bash
# Execute Wave 2 (parallel with Conductor)
# Workspace 1: nested-dir-wave2-1
/task-work TASK-NDS-002

# Workspace 2: nested-dir-wave2-2
# Direct implementation (no task-work needed)
```

---

## Task Details

### TASK-NDS-001: Update TaskLoader to use rglob

**File**: `guardkit/tasks/task_loader.py`
**Method**: `_find_task_file()` (lines 127-150)

**Change Summary**:
- Replace exact path matching with `rglob` pattern
- Pattern: `{task_id}*.md` for extended filename support
- Maintain search order priority

**Key Code Change**:
```python
# Before (exact match)
task_path = repo_root / "tasks" / dir_name / f"{task_id}.md"
if task_path.exists():
    return task_path

# After (recursive glob)
for task_path in search_dir.rglob(f"{task_id}*.md"):
    logger.debug(f"Found task {task_id} at {task_path}")
    return task_path
```

---

### TASK-NDS-002: Add nested directory tests

**File**: `tests/unit/test_task_loader.py`

**Test Cases**:
1. `test_load_task_from_nested_backlog` - Feature subfolder
2. `test_load_task_with_extended_filename` - `TASK-XXX-name.md`
3. `test_load_task_deep_nesting` - Multiple levels
4. `test_load_task_nested_search_order` - Priority validation

---

### TASK-NDS-003: Improve error messages

**File**: `guardkit/tasks/task_loader.py`
**Method**: `load_task()` (lines 115-123)

**Change Summary**:
- Add `/**/` to indicate recursive search in error message
- Add hints section for common issues

---

## Verification Checklist

After implementation, verify:

- [ ] `guardkit autobuild task TASK-NDS-001` finds task in this subfolder
- [ ] `/feature-build TASK-XXX` works for tasks in `tasks/backlog/feature-slug/`
- [ ] All existing tests pass (backward compatibility)
- [ ] New tests pass with 100% coverage for `_find_task_file()`

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| rglob performance | Low | Low | Task directories are small |
| Pattern collision | Low | Medium | Use specific `{task_id}*.md` pattern |
| Backward compatibility | Very Low | High | Existing flat structure still works |

---

## Rollback Plan

If issues arise:

1. Revert `_find_task_file()` to exact path matching
2. Remove new tests (they would fail without recursive search)
3. Keep error message improvements (safe change)

```bash
git revert HEAD~2  # Revert last 2 commits (NDS-001, NDS-002)
```
