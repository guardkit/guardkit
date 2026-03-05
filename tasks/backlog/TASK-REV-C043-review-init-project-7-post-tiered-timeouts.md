---
id: TASK-REV-C043
title: Review init project 7 output after tiered timeout and concurrency fixes
status: review_complete
task_type: review
created: 2026-03-04T00:00:00Z
updated: 2026-03-04T00:00:00Z
priority: high
tags: [graphiti, falkordb, timeout, init, tiered-timeouts, concurrency, performance, verification]
complexity: 5
parent_review: TASK-REV-BAC1
feature_id: FEAT-init-graphiti-remaining-fixes
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review init project 7 output after tiered timeout and concurrency fixes

## Description

Analyse the `guardkit init fastapi-python` output captured in `docs/reviews/reduce-static-markdown/init_project_7.md` to assess the effectiveness of the fixes implemented from review TASK-REV-BAC1 and its implementation tasks.

| Task | Fix | Status |
|------|-----|--------|
| TASK-FIX-b7a7 | Expand tiered episode timeouts: project_overview=300s, rules=180s, role_constraints=150s, agents=150s, default=120s | Completed — verify effectiveness |
| TASK-FIX-b7a7 | Add `max_concurrent_episodes` config (default 3) to GraphitiConfig | Completed — verify effectiveness |
| TASK-FIX-b7a7 | Rate-limit-aware retry with exponential backoff (4s, 8s for 429s) | Completed — verify effectiveness |
| TASK-FIX-8f75 | Split large episodes into smaller chunks | BACKLOG — not yet implemented |
| TASK-FIX-3921 | Skip re-seeding unchanged episodes (--copy-graphiti-from) | BACKLOG — not yet implemented |
| TASK-FIX-77b2 | Parallelise episode seeding within groups | BACKLOG — not yet implemented |

## Source File

`docs/reviews/reduce-static-markdown/init_project_7.md` (currently empty — populate before review)

## Context — What Was Fixed (TASK-FIX-b7a7)

### Tiered Episode Timeouts (5-tier system)

Changed `_create_episode()` in `graphiti_client.py` to use 5-tier timeouts:

```python
if group_id.endswith("project_overview"):
    episode_timeout = 300.0   # Was 240s; project_architecture hit ceiling at 240s
elif group_id == "rules":
    episode_timeout = 180.0   # Working for 10/12 rules at this level
elif group_id == "role_constraints":
    episode_timeout = 150.0   # Coach at 120s needs ~130s with growth
elif group_id == "agents":
    episode_timeout = 150.0   # testing-specialist at 120s needs ~130s
else:
    episode_timeout = 120.0   # templates, implementation_modes: safe
```

### Concurrency Control

Added `max_concurrent_episodes: int = 3` to `GraphitiConfig` to limit parallel episode creation calls, reducing OpenAI API pressure and potential rate limiting.

### Rate-Limit-Aware Retry

Enhanced retry logic with longer backoff for HTTP 429 / rate-limit errors:
- Rate limit errors: 4s, 8s backoff (vs 2s, 4s for other transient errors)
- Covers `429`, `Rate limit`, `rate_limit` in error strings

**Expected impact**:
- project_overview: 2/2 SUCCESS (project_architecture had 240.0s timeout in init_project_6, now has 300s — 25% headroom)
- role_constraints: coach episode should succeed (was 120.0s timeout, now 150s — 25% headroom)
- agents: fastapi-testing-specialist should succeed (was 120.0s timeout, now 150s — 25% headroom)
- rules: 10-12/12 (crud and schemas were at 180s ceiling; may still timeout depending on graph size)
- Rate limiting: fewer OpenAI retry warnings with concurrency cap
- Total init time: ~35-40 min (similar to init_project_6, slight improvement from fewer retries)

## Prior Baseline (init_project_6.md — TASK-REV-BAC1)

| Metric | init_project_5 | init_project_6 | Delta |
|--------|----------------|----------------|-------|
| Total output | 157 lines | 185 lines | +28 |
| Step 2 duration | 715.0s | 840.9s | +17.6% |
| Step 2.5 duration | 1,468.2s | 1,523.3s | +3.7% |
| Total init time | ~2,183s (~36.4 min) | ~2,364s (~39.4 min) | +8.3% |
| Episode-level timeouts | 6 (all at 120s) | 5 | -1 |
| Rule sync failures | 6 | 2 (crud, schemas) | -4 |
| Agent sync failures | 0 | 1 (testing-specialist) | +1 regression |
| Role constraint failures | 0 | 1 (coach) | +1 regression |
| Project overview | 2/2 (171.7s, 176.7s) | 1/2 (189.6s OK, 240.0s TIMEOUT) | -1 regression |
| Unawaited coroutine warnings | 1 | 1 | same |
| LLM duplicate_facts warnings | 24+ | present | similar |
| OpenAI retries | 0 | 1 | +1 |
| Index out of bounds warnings | 0 | present (new) | new warning type |

### Key Regressions in init_project_6 (addressed by TASK-FIX-b7a7)

1. **project_architecture** (240.0s TIMEOUT): Hit 240s ceiling → now 300s
2. **role_constraints coach** (120.0s TIMEOUT): Was using default 120s → now 150s
3. **fastapi-testing-specialist** (120.0s TIMEOUT): Was using default 120s → now 150s

### Projected Metrics (from TASK-REV-BAC1 review report)

| Metric | Projected (after TASK-FIX-b7a7) |
|--------|--------------------------------|
| Step 2 time | ~800-900s (similar, fewer retries) |
| Step 2.5 time | ~1,400-1,600s |
| Total init time | ~2,200-2,500s (~37-42 min) |
| Rule sync failures | 0-2 (crud/schemas may still timeout at 180s) |
| Agent sync failures | 0 (150s should cover testing-specialist) |
| Role constraint failures | 0 (150s should cover coach) |
| Project overview failures | 0 (300s should cover project_architecture) |
| OpenAI retries | fewer (concurrency cap + backoff) |

## Review Questions

1. **TASK-FIX-b7a7 effectiveness — project_overview**: Did raising to 300s resolve the project_architecture timeout? What was the actual duration? How much headroom remains?
2. **TASK-FIX-b7a7 effectiveness — role_constraints**: Did raising to 150s resolve the coach episode timeout? What was the actual duration?
3. **TASK-FIX-b7a7 effectiveness — agents**: Did raising to 150s resolve the fastapi-testing-specialist timeout? What was the actual duration?
4. **Rules plateau**: Did crud and schemas still timeout at 180s? If so, has graph growth from additional successes pushed other rules towards the ceiling?
5. **Concurrency control impact**: Did `max_concurrent_episodes=3` reduce OpenAI retry warnings? Any evidence of rate limiting?
6. **Rate-limit retry impact**: Were there fewer OpenAI retry log entries compared to init_project_6?
7. **Graph growth effect**: With more items succeeding (project_architecture, coach, testing-specialist), did the cumulative graph size push previously-successful items closer to their ceilings?
8. **New regressions**: Did any previously-successful episodes regress due to graph size growth? (The "plateau problem" identified in TASK-REV-BAC1)
9. **Warning types**: Are the "Source/Target index out of bounds" warnings still present? Any new warning types?
10. **Projection accuracy**: How close are actual results to the projections from TASK-REV-BAC1?
11. **Production readiness**: Given this is iteration 7, should we accept the current state or pursue TASK-FIX-8f75 (episode splitting) and TASK-FIX-3921 (skip re-seeding)?
12. **Cost/benefit of remaining fixes**: For each remaining backlog task, what is the expected improvement vs implementation effort?

## Acceptance Criteria

- [ ] Quantitative comparison of init_project_6 vs init_project_7 metrics
- [ ] Assessment of TASK-FIX-b7a7 effectiveness across all 5 tiers
- [ ] Comparison of actual results vs TASK-REV-BAC1 projections
- [ ] Analysis of graph growth / plateau effect
- [ ] Analysis of concurrency control and rate-limit retry impact
- [ ] Analysis of any new regressions or warning types
- [ ] Updated cumulative metrics table (init_project_3 → 4 → 5 → 6 → 7 progression)
- [ ] Definitive recommendation: accept as production-ready OR specify remaining fixes needed
- [ ] If not production-ready: updated priority ordering for TASK-FIX-8f75, TASK-FIX-3921, TASK-FIX-77b2

## Remaining Backlog (from TASK-REV-BAC1)

| Priority | Task | Title | Complexity | Status |
|----------|------|-------|------------|--------|
| 1 (HIGH) | TASK-FIX-b7a7 | Expand tiered episode timeouts + concurrency + retry | 2/10 | COMPLETED |
| 2 (MED) | TASK-FIX-8f75 | Split large episodes into smaller chunks | 4/10 | BACKLOG |
| 3 (MED) | TASK-FIX-3921 | Skip re-seeding unchanged episodes (--copy-graphiti-from) | 5/10 | BACKLOG |
| 4 (LOW) | TASK-FIX-77b2 | Parallelise episode seeding within groups | 5/10 | BACKLOG |

## Implementation Notes

This is a review/analysis task. Use `/task-review TASK-REV-C043` to execute the review.

**Prerequisites**: Populate `docs/reviews/reduce-static-markdown/init_project_7.md` with the output of `guardkit init fastapi-python` before running the review.
