# Implementation Guide: Seed Quality Fixes (FEAT-SQF)

## Parent Review

- **TASK-REV-49AB** — Review of reseed + init (init_project_8) on clean graph
- **Report**: `.claude/reviews/TASK-REV-49AB-review-report.md`

## Predecessor Feature

- **FEAT-ISF** — Init Seeding Fixes (all 6 tasks completed, validated by TASK-REV-49AB)

## Execution Strategy

### Wave 1: All 3 fixes (Parallel — no file conflicts)

All 3 tasks touch different files with no overlap. They can all run in parallel.

| Task | Description | Effort | File(s) | Method |
|------|-------------|--------|---------|--------|
| TASK-FIX-b06f | Add `"templates"` to 180s timeout tier | 1/10 | `graphiti_client.py:897` | /task-work |
| TASK-FIX-bbbd | Return episode counts from `_add_episodes` | 2/10 | `seed_helpers.py`, `seeding.py`, all `seed_*.py` | /task-work |
| TASK-FIX-ec01 | Fix pattern examples path resolution | 2/10 | `seed_pattern_examples.py` | /task-work |

```bash
# All 3 can run in parallel (different files)
/task-work TASK-FIX-b06f
/task-work TASK-FIX-bbbd
/task-work TASK-FIX-ec01
```

## File Impact Map

| File | TASK-FIX-b06f | TASK-FIX-bbbd | TASK-FIX-ec01 |
|------|:---:|:---:|:---:|
| `guardkit/knowledge/graphiti_client.py` | **MODIFY** (line 897) | — | — |
| `guardkit/knowledge/seed_helpers.py` | — | **MODIFY** (return type) | — |
| `guardkit/knowledge/seeding.py` | — | **MODIFY** (log loop) | — |
| `guardkit/knowledge/seed_*.py` (all) | — | **MODIFY** (propagate return) | — |
| `guardkit/knowledge/seed_pattern_examples.py` | — | — | **MODIFY** (path resolution) |
| `tests/knowledge/test_graphiti_client.py` | **ADD** test | — | — |
| `tests/knowledge/test_seed_helpers.py` | — | **ADD** test | — |
| `tests/knowledge/test_seed_pattern_examples.py` | — | — | **ADD** test |

No file conflicts between tasks — safe for parallel execution.

## Verification

After all 3 fixes, run a full reseed + init:

```bash
guardkit graphiti clear
guardkit graphiti seed --force
guardkit init fastapi-python --project-id test-verify
```

**Expected outcomes:**
- Template episodes complete within 180s (no circuit breaker trip)
- Seed summary accurately reports episode counts per category
- Pattern examples seeded successfully (no path error)
- All 17 seed categories show accurate created/skipped counts

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Template still times out at 180s | Low | Medium | Can raise to 240s; evidence shows 120-150s range |
| `_add_episodes` caller missed | Low | Low | Grep for all callers; old callers still work (ignore return) |
| Pattern walk-up finds wrong directory | Very Low | Low | Same pattern proven by `seed_templates.py` |
