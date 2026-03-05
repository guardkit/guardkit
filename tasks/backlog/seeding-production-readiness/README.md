# Feature: Seeding Production Readiness (FEAT-SPR)

## Problem

The `guardkit graphiti seed` pipeline has a **52% success rate** — only 101 of 193 episodes are created. The primary cause is a circuit breaker cascade: when the rules category (72 episodes) triggers 3 consecutive 180s timeouts, the circuit breaker trips and silently skips all subsequent categories (project_overview, project_architecture). Additionally, the seed output shows misleading ✓ marks for all categories regardless of actual results.

## Solution

Five targeted fixes across three waves:

1. **Wave 1 (P0)**: Reset circuit breaker between categories + split rules into per-template batches
2. **Wave 2 (P1)**: Honest ✓/⚠/✗ status display + aggregate summary statistics
3. **Wave 3 (P2)**: LLM connection health check with retry

## Parent Review

- **TASK-REV-F404** — Review of reseed + init (init_project_9)
- **Report**: `.claude/reviews/TASK-REV-F404-review-report.md`

## Predecessor Features

- **FEAT-ISF** — Init Seeding Fixes (6/6 completed)
- **FEAT-SQF** — Seed Quality Fixes (3/3 completed, verified by TASK-REV-F404)

## Subtasks

| ID | Task | Wave | Mode | Priority | Complexity |
|----|------|------|------|----------|------------|
| TASK-SPR-5399 | Reset circuit breaker between categories | 1 | task-work | High | 4 |
| TASK-SPR-18fc | Split rules into per-template batches | 1 | task-work | High | 5 |
| TASK-SPR-2cf7 | Change status display to ✓/⚠/✗ | 2 | task-work | Medium | 3 |
| TASK-SPR-9d9b | Add seed summary statistics | 2 | direct | Medium | 2 |
| TASK-SPR-47f8 | LLM connection retry/health check | 3 | task-work | Low | 3 |

## Execution

```bash
# Wave 1 (parallel — no file conflicts)
/task-work TASK-SPR-5399
/task-work TASK-SPR-18fc

# Wave 2 (sequential — SPR-9d9b depends on SPR-2cf7)
/task-work TASK-SPR-2cf7
/task-work TASK-SPR-9d9b

# Wave 3 (independent)
/task-work TASK-SPR-47f8
```
