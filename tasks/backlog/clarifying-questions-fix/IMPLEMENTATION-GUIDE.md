# Implementation Guide: Clarifying Questions Fix

## Execution Strategy

### Wave 1: Core Fix (Sequential)

**TASK-CLQ-FIX-001**: Integrate clarification into task-review orchestrator

This is the foundation - must complete before other tasks.

```bash
/task-work TASK-CLQ-FIX-001
```

**Estimated Time**: 2-3 hours
**Parallel Execution**: No (foundation task)

---

### Wave 2: Extensions (Parallel)

After Wave 1 completes, these can run in parallel:

| Task | Method | Conductor Workspace |
|------|--------|---------------------|
| TASK-CLQ-FIX-002 | /task-work | clq-fix-wave2-1 |
| TASK-CLQ-FIX-003 | /task-work | clq-fix-wave2-2 |
| TASK-CLQ-FIX-004 | direct | clq-fix-wave2-3 |

```bash
# In parallel workspaces:
# Workspace 1:
/task-work TASK-CLQ-FIX-002

# Workspace 2:
/task-work TASK-CLQ-FIX-003

# Workspace 3 (direct - simple enough to implement directly):
# Create the smoke test file as specified
```

**Estimated Time**: 2-3 hours (parallel)
**Total Wave 2**: ~3 hours with 3 parallel workspaces

---

## Total Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Wave 1 | 2-3 hours | 2-3 hours |
| Wave 2 | 2-3 hours (parallel) | 4-6 hours |
| Verification | 0.5 hours | 4.5-6.5 hours |

**Total**: ~1 day with efficient parallel execution

---

## Verification Checklist

After all tasks complete:

```bash
# 1. Run smoke test
python -m pytest tests/smoke/test_clarification_smoke.py -v

# 2. Manual verification
/task-create "Test clarification" complexity:6 task_type:review
/task-review TASK-XXX --mode=decision
# Expected: Clarification questions appear

# 3. Feature-plan verification
/feature-plan "add a new feature"
# Expected: Context A questions before analysis

# 4. Skip flag verification
/task-review TASK-XXX --mode=decision --no-questions
# Expected: No questions, direct to Phase 2
```

---

## Rollback Strategy

If issues emerge:

1. **Immediate**: Use `--no-questions` flag as workaround
2. **Revert**: The clarification integration is isolated to:
   - `task_review_orchestrator.py` (can revert changes)
   - `feature_plan_orchestrator.py` (new file, can delete)
3. **Fallback**: Markdown-based workflow still exists

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Clarification triggers correctly | 100% |
| Existing tests pass | 100% |
| Smoke test passes | 100% |
| No regression in task-work | 100% |
| User can skip with flag | 100% |
