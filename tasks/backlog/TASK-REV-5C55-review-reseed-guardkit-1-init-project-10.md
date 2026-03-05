---
id: TASK-REV-5C55
title: Review reseed (guardkit_1) + init (init_project_10)
status: review_complete
created: 2026-03-05T10:00:00Z
updated: 2026-03-05T18:30:00Z
review_results:
  mode: code-quality
  depth: comprehensive
  score: 68
  findings_count: 6
  recommendations_count: 6
  revisions: 3
  decision: implement
  implementation_tasks: [TASK-FIX-7595]
  notes: "Post-FEAT-SPR verification: all 5 fixes confirmed in run output. P1 timeout tier regression from TASK-SPR-18fc → TASK-FIX-7595 created."
  report_path: .claude/reviews/TASK-REV-5C55-review-report.md
priority: high
task_type: review
review_mode: code-quality
review_depth: standard
complexity: 5
parent_review: TASK-REV-F404
feature_id: FEAT-SPR
tags: [graphiti, init, seeding, review, falkordb, circuit-breaker]
---

# Review: Reseed (reseed_guardkit_1) + Init (init_project_10)

## Review Scope

Analyse the output of two runs:

1. **Reseed**: `docs/reviews/reduce-static-markdown/reseed_guardkit_1.md` (10,413 lines)
2. **Init**: `docs/reviews/reduce-static-markdown/init_project_10.md` (70 lines)

## Context

This is the verification run after **FEAT-SPR** (Seeding Production Readiness) — 5 targeted fixes from TASK-REV-F404 findings:

| Task | Fix | Wave | Status |
|------|-----|------|--------|
| TASK-SPR-5399 | Reset circuit breaker between categories | 1 | In backlog |
| TASK-SPR-18fc | Split rules into per-template batches | 1 | In backlog |
| TASK-SPR-2cf7 | Change status display to honest ✓/⚠/✗ | 2 | In backlog |
| TASK-SPR-9d9b | Add seed summary statistics | 2 | In backlog |
| TASK-SPR-47f8 | LLM connection retry/health check | 3 | In backlog |

### What TASK-REV-F404 found (init_project_9)

1. **52% seed success rate** — only 101 of 193 episodes created
2. **Circuit breaker cascade** — rules category (72 episodes) triggers 3x 180s timeouts, trips breaker, skips project_overview + project_architecture
3. **Misleading ✓ marks** — all categories show ✓ regardless of actual success
4. **FEAT-SQF fixes confirmed working** — template timeout (5/7 now vs ~4/7), episode count logging accurate, pattern path fixed

### What init_project_10 already shows

From the 70-line init output:
- **Episode 1/3 (project_purpose) timed out at 300s** — same issue as init_8/9
- **Episode 2/3 completed at 112.3s** — OK
- **Episode 3/3 completed at 99.1s** — OK
- **Total: 511.9s** (8.5 min) — slower than init_8 (392.5s)
- **Coroutine warning**: `resolve_extracted_edge was never awaited` (RuntimeWarning, line 54-56)
- **Numerous "LLM returned invalid duplicate_facts idx values" warnings** (lines 39-51) — many more than init_8

## Key Questions for This Review

### Reseed Phase (reseed_guardkit_1.md — 10,413 lines)
1. How many of the 17 seed categories succeeded? What's the success rate vs init_9's 52%?
2. Did any FEAT-SPR fixes get applied before this run, or is this pre-SPR baseline?
3. Is the circuit breaker still cascading through rules → project_overview → project_architecture?
4. What are the episode completion times across categories?
5. Are the honest episode count logs showing (TASK-FIX-bbbd)?
6. Are pattern examples resolving correctly (TASK-FIX-ec01)?
7. Are templates completing within 180s (TASK-FIX-b06f)?

### Init Phase (init_project_10.md — 70 lines)
1. project_purpose timed out at 300s — is this the same episode that took 249.7s in init_8?
2. Why did it regress from 249.7s (init_8) to 300s+ timeout (init_10)?
3. The coroutine "resolve_extracted_edge was never awaited" warning — is this new? What causes it?
4. The duplicate_facts idx warnings are significantly more numerous — does this indicate graph state issues?
5. Total 511.9s vs 392.5s (init_8) — 30% slower. Is this graph growth or LLM variance?

### FEAT-SPR Assessment
1. Were any FEAT-SPR tasks completed before this run?
2. If pre-SPR: does the output confirm the need for all 5 FEAT-SPR tasks?
3. If post-SPR: which fixes are validated and which still need work?
4. Is the circuit breaker reset between categories (TASK-SPR-5399) confirmed working?
5. Are rules split into per-template batches (TASK-SPR-18fc) confirmed working?

### Cross-Run Trend Analysis
1. init_project_8 → 9 → 10: is episode timing trending up (graph growth)?
2. Is the project_architecture/project_purpose timeout getting worse?
3. Review chain: TASK-REV-C043 → 49AB → F404 → **5C55** — are we converging on stability or still finding new issues?

## Acceptance Criteria

- [ ] Reseed phase analysed: all 17 categories assessed (success/fail/time)
- [ ] Init phase analysed: 3 project episodes assessed
- [ ] Circuit breaker behaviour documented
- [ ] Coroutine warning investigated
- [ ] duplicate_facts warnings assessed
- [ ] Comparison with init_project_8 and init_project_9
- [ ] FEAT-SPR task relevance confirmed or updated
- [ ] Cross-run trend analysis (init_8 → 9 → 10)
- [ ] Recommendations for next steps
