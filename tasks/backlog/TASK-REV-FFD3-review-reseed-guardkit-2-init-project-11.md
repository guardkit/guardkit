---
id: TASK-REV-FFD3
title: Review reseed (guardkit_2) + init (init_project_11)
status: completed
created: 2026-03-05T22:00:00Z
updated: 2026-03-05T23:30:00Z
review_results:
  mode: code-quality
  depth: comprehensive
  score: 55
  findings_count: 12
  recommendations_count: 7
  report_path: docs/reviews/TASK-REV-FFD3-review-report.md
  completed_at: 2026-03-05T23:30:00Z
priority: high
task_type: review
review_mode: code-quality
review_depth: comprehensive
complexity: 5
parent_review: TASK-REV-5C55
feature_id: FEAT-SPR
tags: [graphiti, init, seeding, review, falkordb, circuit-breaker, timeout]
---

# Review: Reseed (reseed_guardkit_2) + Init (init_project_11)

## Review Scope

Analyse the output of two runs performed **after** changes from TASK-REV-5C55 review and TASK-FIX-7595 (rules timeout regression fix):

1. **Reseed**: `docs/reviews/reduce-static-markdown/reseed_guardkit_2.md` (23,205 lines — contains 2 full reseed runs)
2. **Init**: `docs/reviews/reduce-static-markdown/init_project_11.md` (172 lines — contains 2 init runs)

## Context

### What TASK-REV-5C55 found (reseed_guardkit_1 + init_project_10)

**Reseed Run 1 (guardkit_1):**
- 12/17 fully seeded, 5 partial — 106/171 episodes (62.0%) — 209m 29s
- Circuit breaker not cascading (confirmed TASK-SPR-5399 working)
- Honest status display working (✓/⚠ correctly shown)
- Rules: 25/72 episodes (massive timeout failures)
- Agents: 6/18 episodes
- Templates: 3/7 episodes

**Init Run (init_project_10):**
- Episode 1/3 (project_purpose) timed out at 300s
- Episode 2/3 completed at 112.3s
- Episode 3/3 completed at 99.1s
- Total: 511.9s — 30% slower than init_8 (392.5s)
- Coroutine "resolve_extracted_edge was never awaited" warning
- Numerous duplicate_facts idx warnings

**Key outcome:** TASK-FIX-7595 created for rules timeout tier regression (120s too aggressive for rules)

### What changed since TASK-REV-5C55

- **TASK-FIX-7595** completed: Fixed rules timeout regression (commit 333f5d39)
- Previous FEAT-SPR fixes confirmed working:
  - TASK-SPR-5399: Circuit breaker reset between categories
  - TASK-SPR-2cf7: Honest ✓/⚠/✗ status display
  - TASK-SPR-9d9b: Seed summary statistics

### Quick observations from new runs

**Reseed Run 1 (first half of reseed_guardkit_2.md):**
- 12/17 fully seeded, 5 partial — 106/171 episodes (62.0%) — 209m 29s

**Reseed Run 2 (second half of reseed_guardkit_2.md):**
- 10/17 fully seeded, 7 partial — 120/171 episodes (70.2%) — 261m 22s
- Rules improved: 41/72 (57%) vs 25/72 (35%) from run 1

**Init Run 1 (first half of init_project_11.md):**
- Episode 1/3 timed out at 300s (project_purpose — same pattern)
- Episode 2/3: 112.3s, Episode 3/3: 99.1s
- Total: 511.9s

**Init Run 2 (second half of init_project_11.md):**
- Episode 1/3 timed out at 300s (project_purpose — persistent)
- Embedding retries (new: "Retrying request to /embeddings")
- Episode 2/3: 110.2s, Episode 3/3: 249.2s (massive regression!)
- New warning type: "Target/Source index out of bounds for chunk of size 15"
- Total: 659.9s (28% slower than init run 1, 68% slower than init_8)

## Key Questions for This Review

### Reseed Phase — TASK-FIX-7595 Impact Assessment
1. Did the rules timeout fix (TASK-FIX-7595) improve rules seeding? Run 1 had 25/72, Run 2 has 41/72 — was TASK-FIX-7595 applied between the two runs?
2. Overall episode success rate: 62.0% → 70.2% — is this improvement attributable to the timeout fix?
3. Categories that regressed: Run 1 had 12/17 fully seeded, Run 2 has 10/17 — which categories regressed and why?
4. Agents still at 6/18 in both runs — no improvement. Is the 150s timeout still too aggressive?
5. Templates improved from 3/7 to 4/7 — which template now succeeds?
6. Duration increased: 209m → 261m — is this due to more episodes completing (longer total) or slowdowns?

### Init Phase — Episode 3 Regression Analysis
1. **Critical:** Episode 3/3 regressed from 99.1s → 249.2s. Why?
2. New "index out of bounds for chunk of size 15" warnings on episode 3 — is this graph growth causing O(n^2) edge resolution?
3. The out-of-bounds warnings reference IS_PART_OF and CONTAINS_PURPOSE edges — are these accumulating from successive runs?
4. Embedding retry warnings ("Retrying request to /embeddings") — infrastructure instability or load-related?
5. project_purpose timeout persists at 300s across init_8→10→11. Is 300s too low, or is this episode genuinely too complex?
6. Total time trending: 392.5s → 511.9s → 659.9s — this is a clear upward trajectory. Graph growth?

### Cross-Run Trend Analysis
1. Review chain: TASK-REV-C043 → 49AB → F404 → 5C55 → **FFD3** — are we converging?
2. Reseed success rate trend: 52% (init_9 era) → 62.0% → 70.2% — positive trajectory
3. Init total time trend: 392.5s → 511.9s → 511.9s → 659.9s — negative trajectory
4. Are the "duplicate_facts idx" warnings getting worse with graph growth?
5. New warning types in init_11 run 2 (out-of-bounds) — regression or known graphiti-core issue?

### FEAT-SPR Remaining Tasks Assessment
1. TASK-SPR-18fc (split rules into per-template batches): Is this reflected in the run 2 rules improvement (41/72)?
2. TASK-SPR-47f8 (LLM connection retry/health check): The embedding retries suggest this may still be needed
3. Are there any new issues not covered by existing FEAT-SPR tasks?

## Acceptance Criteria

- [ ] Both reseed runs fully analysed: all 17 categories assessed per run with success/fail/time
- [ ] Both init runs fully analysed: 3 project episodes assessed per run
- [ ] TASK-FIX-7595 impact quantified (rules improvement attribution)
- [ ] Episode 3 regression in init run 2 root-caused
- [ ] New "index out of bounds" warnings investigated
- [ ] Embedding retry warnings assessed
- [ ] Cross-run trend analysis (init_8 → 10 → 11, reseed_1 → 2)
- [ ] FEAT-SPR remaining task relevance confirmed or updated
- [ ] Comparison with TASK-REV-5C55 findings (regression/improvement)
- [ ] Recommendations for next steps
