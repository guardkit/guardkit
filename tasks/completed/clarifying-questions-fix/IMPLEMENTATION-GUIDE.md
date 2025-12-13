# Implementation Guide: Clarifying Questions Fix

## Execution Strategy

### Wave 1: Core Fixes (Parallel - Both Commands)

These two tasks fix the core commands and can run in parallel since they modify different files:

| Task | Method | Conductor Workspace | Command Fixed |
|------|--------|---------------------|---------------|
| TASK-CLQ-FIX-001 | /task-work | clq-fix-wave1-1 | /task-review |
| TASK-CLQ-FIX-005 | /task-work | clq-fix-wave1-2 | /task-work |

```bash
# Workspace 1:
/task-work TASK-CLQ-FIX-001

# Workspace 2 (parallel):
/task-work TASK-CLQ-FIX-005
```

**Estimated Time**: 2-3 hours (parallel)

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

---

## Total Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Wave 1 (001 + 005) | 2-3 hours (parallel) | 2-3 hours |
| Wave 2 (002, 003, 004) | 2-3 hours (parallel) | 4-6 hours |
| Verification | 0.5 hours | 4.5-6.5 hours |

**Total**: ~1 day with efficient parallel execution

---

## Clarification Contexts by Command

| Command | Context | Generator Module | When Triggered |
|---------|---------|------------------|----------------|
| /task-review | Context A (Review Scope) | `review_generator.py` | Before analysis |
| /task-work | Context C (Implementation Planning) | `planning_generator.py` | Phase 1.6, before Phase 2 |
| /feature-plan | Context A + B | Both | Before analysis + after [I]mplement |

---

## Verification Checklist

After all tasks complete:

```bash
# 1. Run smoke tests
python -m pytest tests/smoke/test_clarification_smoke.py -v

# 2. Verify /task-review clarification (Context A)
/task-create "Test review clarification" complexity:6 task_type:review
/task-review TASK-XXX --mode=decision
# Expected: Clarification questions appear before analysis

# 3. Verify /task-work clarification (Context C)
/task-create "Test implementation clarification" complexity:5
/task-work TASK-XXX
# Expected: Phase 1.6 clarification questions appear before Phase 2

# 4. Verify /feature-plan clarification (Context A + B)
/feature-plan "add a new feature"
# Expected: Context A questions before analysis, Context B after [I]mplement

# 5. Skip flag verification (all commands)
/task-review TASK-XXX --mode=decision --no-questions
/task-work TASK-XXX --no-questions
/feature-plan "feature" --no-questions
# Expected: No questions, proceed directly
```

---

## Rollback Strategy

If issues emerge:

1. **Immediate**: Use `--no-questions` flag as workaround
2. **Revert**: The clarification integration is isolated to:
   - `task_review_orchestrator.py` (can revert changes)
   - `phase_execution.py` or `task_work_orchestrator.py` (can revert)
   - `feature_plan_orchestrator.py` (new file, can delete)
3. **Fallback**: Markdown-based workflow still exists

---

## Success Metrics

| Metric | Target |
|--------|--------|
| /task-review clarification works | 100% |
| /task-work clarification works | 100% |
| /feature-plan clarification works | 100% |
| Existing tests pass | 100% |
| Smoke tests pass | 100% |
| User can skip with flag | 100% |
| Complexity gating correct | 100% |
