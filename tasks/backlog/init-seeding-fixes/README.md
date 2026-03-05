# Feature: Init Seeding Fixes (FEAT-ISF)

## Problem

`guardkit init` Graphiti seeding regressed in init_project_7: 0/12 rules synced (was 10/12 in init_6). Two code changes in TASK-FIX-b7a7 compound to cascade-fail the circuit breaker:

1. **Parallel sync** (`_sync_items_parallel`) — concurrent failures accumulate faster than successes can reset the circuit breaker counter
2. **Full rule content** (`main_content: chunk.content`) — 4x more text per episode, slower graphiti-core Phase 4 resolution, pushes episodes past timeout

Additionally, init re-seeds ~18 system-scoped episodes every run (role constraints, impl modes, template, agents, rules) — content that doesn't change between projects. This causes graph bloat and wastes ~25 min per init.

## Solution

**Wave 1 (Short-term reverts):** Restore sequential sync and content_preview to unblock init reliability.

**Wave 2 (Ext file fix + Graphiti knowledge):** Fix `-ext.md` file copying during init and seed critical Graphiti fidelity knowledge.

**Wave 3 (Architectural fix):** Create `guardkit graphiti seed-system` command, slim init to project-only seeding.

## Parent Review

- **TASK-REV-C043** — Review of init_project_7 post tiered timeouts
- **Report**: `.claude/reviews/TASK-REV-C043-review-report.md`

## Related Features

- **FEAT-CR01** — Context Reduction via Path-Gating and Trimming (static trimming, Graphiti-independent)
- **FEAT-GE** — Graphiti Enhancements for AutoBuild (turn states, North Star, failed approaches)
- **FEAT-init-graphiti-remaining-fixes** — Prior init/Graphiti fix iterations

## Subtasks

| ID | Task | Wave | Mode | Status |
|----|------|------|------|--------|
| TASK-ISF-001 | Revert parallel sync to sequential | 1 | task-work | Pending |
| TASK-ISF-002 | Revert rule main_content to content_preview | 1 | task-work | **Completed** |
| TASK-ISF-003 | Fix -ext.md file copying in init | 2 | task-work | Pending |
| TASK-ISF-004 | Seed Graphiti fidelity knowledge | 2 | direct | Pending |
| TASK-ISF-005 | Create guardkit graphiti seed-system command | 3 | task-work | Pending |
| TASK-ISF-006 | Slim init to project-only seeding | 3 | task-work | Pending |

## Token Reduction Summary

| Metric | Before (init_7) | After Wave 1 | After Wave 3 |
|--------|-----------------|--------------|--------------|
| Rules synced | 0/12 | ~10/12 | N/A (seed-system) |
| Init duration | ~22 min | ~35 min (slower but reliable) | ~5-8 min |
| System episodes per init | ~18 | ~18 | 2 (project only) |

## Execution

```bash
# Wave 1 (parallel - short-term reverts)
/task-work TASK-ISF-001
/task-work TASK-ISF-002

# Wave 2 (parallel - ext files + knowledge)
/task-work TASK-ISF-003
# TASK-ISF-004 is direct edit

# Wave 3 (sequential - architectural fix)
/task-work TASK-ISF-005  # must complete before ISF-006
/task-work TASK-ISF-006
```
