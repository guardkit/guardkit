# Implementation Plan: TASK-NDS-001

## Summary
Update TaskLoader to use rglob for recursive search

## Files to Modify

| File | Action | Lines |
|------|--------|-------|
| `guardkit/tasks/task_loader.py` | Modify | 127-150 |

## Implementation Phases

### Phase 1: Update `_find_task_file()` Method
- Replace `Path.exists()` check with `rglob()` iterator
- Pattern: `f"{task_id}*.md"` to match both exact and extended filenames
- Return first match found

### Phase 2: Update Error Message
- Update error message in `load_task()` to reflect recursive search

## Estimates

| Metric | Value |
|--------|-------|
| Files Modified | 1 |
| Lines Changed | ~10 |
| Duration | 15-20 minutes |
| Complexity | 3/10 |

## Architectural Review

| Principle | Score |
|-----------|-------|
| SOLID | 85/100 |
| DRY | 90/100 |
| YAGNI | 95/100 |
| **Overall** | **90/100** |

Decision: AUTO-APPROVED

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Performance | LOW | rglob optimized |
| Multiple matches | LOW | First match wins |
| Backward compat | VERY LOW | Pattern includes exact match |
