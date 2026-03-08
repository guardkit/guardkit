# Implementation Guide: Graphiti Context Fixes (FEAT-GCF)

## Parent Review

TASK-REV-982B — vLLM Run 3 and Run 4 Performance Analysis (Revised)

## Problem Statement

Graphiti knowledge graph returns 0 context categories for ALL AutoBuild tasks across Run 3 and Run 4, despite FalkorDB connectivity working. Five independent root causes identified.

## Execution Strategy

### Wave 1: Code Fixes (3 tasks, parallel)

All three tasks are independent — no file conflicts.

| Task | Description | Mode | Workspace |
|------|-------------|------|-----------|
| TASK-GCF-001 | Fix `patterns_{tech_stack}` → `patterns` group ID | task-work | graphiti-context-fixes-wave1-1 |
| TASK-GCF-002 | Add logging to `_query_category()` exception handler | direct | graphiti-context-fixes-wave1-2 |
| TASK-GCF-003 | Add `task_outcomes`/`turn_states` to `_group_defs.py` | direct | graphiti-context-fixes-wave1-3 |

### Wave 2: Operational Seeding (1 task, sequential)

Depends on Wave 1 completion (needs correct group IDs before seeding).

| Task | Description | Mode |
|------|-------------|------|
| TASK-GCF-004 | Run `seed-system --force` and `seed-project` | manual |

### Wave 3: Validation (1 task, sequential)

Depends on Wave 2 completion (needs seeded data).

| Task | Description | Mode |
|------|-------------|------|
| TASK-GCF-005 | Run seeded AutoBuild (Run 5) and validate context loads | manual |

## Key Files

| File | Changes |
|------|---------|
| `guardkit/knowledge/job_context_retriever.py` | Fix group ID (line ~583), add logging (line ~996) |
| `guardkit/_group_defs.py` | Add `task_outcomes`, `turn_states` to PROJECT_GROUPS |

## Expected Outcome

- **Before**: 0/10 categories, 0 tokens context
- **After**: 6-7/10 categories, ~2000-4000 tokens context
- **Performance impact**: 1.1-1.3x improvement (8.1x → 6.2-7.4x ratio to Anthropic)

## Related Tasks

- TASK-VOPT-001: Context reduction (~19KB → ~10-12KB) — separate feature, complementary
- TASK-VOPT-003: Suppress FalkorDB log noise — separate task, low priority
