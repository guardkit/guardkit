# FEAT-CF57 Closeout Tasks

Implementation tasks created from TASK-REV-7535 (success verification review) recommendations.

## Source

- **Review**: TASK-REV-7535 — Analyse FEAT-CF57 success run and verify ABFIX fix effectiveness
- **Report**: `.claude/reviews/TASK-REV-7535-review-report.md`

## Tasks

| Task | Title | Complexity | Wave | Mode |
|------|-------|-----------|------|------|
| TASK-FIX-7536 | Normalise legacy task_type values | 2 | 1 | direct |
| TASK-FIX-7537 | Add pre-flight feature validation | 4 | 1 | task-work |
| TASK-FIX-7538 | Archive FEAT-CF57 | 1 | 2 | manual |
| TASK-FIX-7539 | Suppress irrelevant bootstrap noise | 3 | 1 | task-work |

## Execution Strategy

**Wave 1** (3 tasks, parallel):
- TASK-FIX-7536: Bulk find-and-replace, low risk
- TASK-FIX-7537: New validation module, TDD
- TASK-FIX-7539: Bootstrap improvement, TDD

**Wave 2** (1 task, sequential):
- TASK-FIX-7538: Manual `/feature-complete` execution (depends on 7536)
