---
id: TASK-REV-BAC1
title: Review init project 6 output after rule and project_overview timeout fixes
status: review_complete
task_type: review
created: 2026-03-04T00:00:00Z
updated: 2026-03-04T00:00:00Z
priority: high
tags: [graphiti, falkordb, timeout, init, template-sync, performance, verification]
complexity: 5
parent_review: TASK-REV-EE12
feature_id: FEAT-init-graphiti-remaining-fixes
review_results:
  mode: technical-assessment
  depth: comprehensive
  score: 70
  findings_count: 10
  recommendations_count: 3
  decision: implement
  report_path: .claude/reviews/TASK-REV-BAC1-review-report.md
  completed_at: 2026-03-04T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review init project 6 output after rule and project_overview timeout fixes

## Description

Analyse the `guardkit init fastapi-python` output captured in `docs/reviews/reduce-static-markdown/init_project_6.md` (185 lines) to assess the effectiveness of the timeout fix implemented from review TASK-REV-EE12:

| Task | Fix | Status |
|------|-----|--------|
| TASK-FIX-b94e | Raise `project_overview` timeout to 240s, `rules` timeout to 180s, others remain 120s | Completed — verify effectiveness |

## Source File

`docs/reviews/reduce-static-markdown/init_project_6.md` (185 lines)

## Context — What Was Fixed

### TASK-FIX-b94e: Raise episode timeouts (rules 180s, project_overview 240s)

- Changed `_create_episode()` in `graphiti_client.py` to use tiered timeouts:
  - `project_overview` group: 180s → 240s (for better headroom on episodes 1 & 3)
  - `rules` group: 120s → 180s (to accommodate graph-size scaling effect)
  - All other groups: unchanged at 120s
- **Expected impact**: Rule sync success from 50% (6/12) → 83-100% (10-12/12); project_overview episodes complete reliably with ~35% headroom

## Prior Baseline (init_project_5.md — TASK-REV-EE12)

| Metric | init_project_5 (before this fix) |
|--------|----------------------------------|
| Total output | 157 lines |
| Step 2 duration | 715.0s (11.9 min) |
| Step 2.5 duration | 1,468.2s (24.5 min) |
| Total init time | ~2,183s (~36.4 min) |
| Episode-level timeouts | 6 (all at 120s) |
| Failed episode syncs | 6 (all rules) |
| Agent sync failures | 0 |
| Rule sync failures | 6 (code-style, migrations, crud, pydantic-constraints, testing, schemas) |
| Project overview episodes | 2/2 SUCCESS (171.7s, 176.7s — thin headroom at 180s) |
| Unawaited coroutine warnings | 1 |
| LLM duplicate_facts warnings | 24+ |

### Projected Metrics (from TASK-REV-EE12 review report)

| Metric | Projected (after fix) |
|--------|----------------------|
| Step 2 time | ~720-780s |
| Step 2.5 time | ~1,400-1,600s |
| Total init time | ~2,100-2,380s (~35-40 min) |
| Rule sync failures | 0-2 |
| Agent sync failures | 0 |
| Project overview failures | 0 |

## Initial Observations from init_project_6 Output

Quick scan reveals:
- Episode 1 (project_purpose): 189.6s SUCCESS — within 240s ceiling
- Episode 3 (project_architecture): 240.0s TIMEOUT — hit the new 240s ceiling
- Episode 5 (role constraints coach): 120.0s TIMEOUT — hit 120s ceiling (not in rules group)
- Agent `fastapi-testing-specialist`: 120.0s TIMEOUT/FAILED — regression from init_project_5
- Rule `crud`: 180.0s TIMEOUT/FAILED — hit new 180s ceiling
- Rule `schemas`: 180.0s TIMEOUT/FAILED — hit new 180s ceiling
- Step 2 total: 840.9s
- Step 2.5 total: 1,523.3s
- Rules synced: 10/12 (was 6/12)
- New warning type: "Source index N out of bounds for chunk of size N in edge X"
- OpenAI retry: "Retrying request to /chat/completions in 0.396672 seconds"

## Review Questions

1. **TASK-FIX-b94e effectiveness**: Did raising rule timeout to 180s improve rule sync success rate? Quantify improvement.
2. **Project overview headroom**: Episode 1 completed at 189.6s (within 240s) but episode 3 timed out at 240s. Is 240s still insufficient? What timeout would provide adequate headroom?
3. **Agent regression**: `fastapi-testing-specialist` was successfully syncing at 64.0s in init_project_5 but timed out at 120s in init_project_6. Why did this regress? Is it graph-size related?
4. **Role constraint timeout**: Episode 5 (coach role constraint) timed out at 120s — is this a new category of failure? Should role_constraints get a higher timeout too?
5. **Rule sync details**: Which rules now succeed that previously failed? Which still fail and why?
6. **Projection accuracy**: How close are actual results to the projections from TASK-REV-EE12?
7. **New warning types**: What are the "Source/Target index out of bounds for chunk" warnings? Are they harmful?
8. **OpenAI retry**: What caused the OpenAI API retry? Is this a new transient issue?
9. **Total init time**: What is the new total? Is it within the projected ~35-40 min range?
10. **Remaining optimisations**: Given this is the 4th iteration, should we pursue further fixes or accept the current state as production-ready? What is the cost/benefit of each remaining failure?

## Acceptance Criteria

- [ ] Quantitative comparison of init_project_5 vs init_project_6 metrics
- [ ] Assessment of TASK-FIX-b94e effectiveness (rule sync improvement, project_overview headroom)
- [ ] Comparison of actual results vs TASK-REV-EE12 projections
- [ ] Analysis of agent regression (fastapi-testing-specialist)
- [ ] Analysis of role_constraint timeout (new failure category)
- [ ] Analysis of remaining rule failures (crud, schemas) and whether 180s is sufficient
- [ ] Analysis of new warning types and OpenAI retry
- [ ] Updated cumulative metrics table (init_project_3 → 4 → 5 → 6 progression)
- [ ] Definitive recommendation: accept as production-ready or specify final fixes needed

## Implementation Tasks (from [I]mplement decision)

| Priority | Task | Title | Complexity | Status |
|----------|------|-------|------------|--------|
| 1 (HIGH) | TASK-FIX-b7a7 | Expand tiered episode timeouts for role_constraints and agents | 2/10 | BACKLOG |
| 2 (MED) | TASK-FIX-8f75 | Split large episodes into smaller chunks | 4/10 | BACKLOG |
| 3 (MED) | TASK-FIX-3921 | Skip re-seeding unchanged episodes (--copy-graphiti-from) | 5/10 | BACKLOG |
| 4 (LOW) | TASK-FIX-77b2 | Parallelise episode seeding within groups | 5/10 | BACKLOG |

**Wave 1** (immediate): TASK-FIX-b7a7 — single conditional expansion, +2-3 items synced
**Wave 2** (architectural): TASK-FIX-3921, TASK-FIX-8f75 — parallel, address root cause
**Wave 3** (optimisation): TASK-FIX-77b2 — after wave 2 for maximum benefit

## Implementation Notes

This is a review/analysis task. Use `/task-review TASK-REV-BAC1` to execute the review.
