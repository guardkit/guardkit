---
id: TASK-REV-8A31
title: Review reseed (guardkit_3) + init (init_project_12)
status: review_complete
created: 2026-03-06T10:00:00Z
updated: 2026-03-06T10:00:00Z
priority: high
task_type: review
review_mode: code-quality
review_depth: comprehensive
complexity: 5
parent_review: TASK-REV-FFD3
feature_id: FEAT-SPR
tags: [graphiti, init, seeding, review, falkordb, vllm, timeout]
---

# Review: Reseed (reseed_guardkit_3) + Init (init_project_12)

## Review Scope

Analyse the output of runs performed **after restarting both vllm-serve and vllm-embed Docker containers** and re-running the clear/seed/init flow. This is a confirmation run following TASK-REV-FFD3.

1. **Reseed**: `docs/reviews/reduce-static-markdown/reseed_guardkit_3.md` (12,224 lines — 1 reseed run)
2. **Init**: `docs/reviews/reduce-static-markdown/init_project_12.md` (80 lines — 1 init run)

## Context

### What TASK-REV-FFD3 concluded

- TASK-FIX-7595 validated: rules seeding improved 25/72 → 41/72 (+64%)
- Init Episode 3 regressed from 99.1s → 249.2s in init_11 run 2
- TASK-REV-FFD3 attributed the Episode 3 regression to **transient vLLM inference degradation** (not graph growth)
- Recommended restarting vLLM and re-running to confirm the ~99s Episode 3 baseline

### What changed since TASK-REV-FFD3

- Both `vllm-serve.sh` and `vllm-embed.sh` Docker containers restarted (fresh state)
- `guardkit graphiti clear --confirm` performed
- Single reseed run (`guardkit graphiti seed --force`)
- Single init run (`guardkit init fastapi-python -n vllm-profiling`)

### Quick observations from init_project_12

- **Episode 1/3 (project_purpose): 254.4s** — completed! Did NOT timeout (300s limit). First successful completion since init_8.
- **Episode 2/3 (project_overview): 108.1s** — consistent with baseline (~110s)
- **Episode 3/3 (tech_stack): 248.8s** — still elevated, comparable to init_11 run 2 (249.2s)
- **Total: 611.3s** — faster than init_11 run 2 (659.9s) due to Episode 1 completing, but Episode 3 remains slow
- **New warning pattern**: "Target index -1 out of bounds" on Episode 1 (negative indices — different from init_11's positive overflow)
- **No embedding retries** — vLLM infrastructure stable after restart
- 3 "out of bounds" warnings on Episode 3 (indices 15-17, CONTAINS_FILE edge)

## Key Questions for This Review

### Primary: Was the Episode 3 regression transient?

1. **Critical**: Episode 3 at 248.8s after fresh vLLM restart **refutes the transient vLLM degradation hypothesis**. The ~249s timing is now reproducible across 2 runs with different vLLM states. What is the actual root cause?
2. Episode 1 completing at 254.4s (vs 300s timeout) — does this suggest the vLLM restart helped Episode 1 but not Episode 3?
3. Is the ~248s Episode 3 timing now the **new baseline** rather than the ~99s seen in init_10/11 run 1?

### Episode 1 Breakthrough

4. Episode 1 completed at 254.4s — first time since init_8 it hasn't timed out at 300s. Is this due to the fresh vLLM state?
5. The 254.4s is still very close to the 300s timeout. Is this fragile?
6. New "Target index -1" warnings (negative!) on Episode 1 — different LLM hallucination pattern. Is the edge type IS_PART_OF_PROJECT different from init_11's IS_PART_OF?

### Reseed Comparison

7. How does reseed_guardkit_3 compare to reseed_guardkit_2 run 2 (the post-TASK-FIX-7595 run)?
8. Were rules maintained at the ~41/72 level? Any improvement or regression?
9. Did the fresh vLLM state affect reseed episode success rates?

### Warning Pattern Analysis

10. init_12 Episode 1: "Target index -1" — negative indices are a new failure mode. What does this mean?
11. init_12 Episode 3: indices 15-17 on CONTAINS_FILE edge — same chunk overflow pattern as init_11 but on a different edge type
12. Are the edge types shifting (IS_PART_OF → IS_PART_OF_PROJECT, CONTAINS_PURPOSE → CONTAINS_FILE)?

### Revised Hypothesis

13. If not transient vLLM degradation, what explains the jump from ~99s to ~249s between init_11 run 1 and subsequent runs?
14. Could the CLAUDE.md content have changed between init_10/init_11-run-1 and init_11-run-2/init_12?
15. Could the graphiti-core or guardkit code have changed between those runs?
16. Is it possible that init_11 run 1's 99.1s was the outlier, and ~249s is the true baseline for the current CLAUDE.md content?

### FEAT-SPR Assessment

17. Does the confirmation run change any FEAT-SPR task priorities?
18. Should TASK-SPR-47f8 (LLM health check) scope be narrowed since vLLM restart didn't fix Episode 3?
19. Is a new task needed for the Episode 3 investigation (structural, not infra)?

## Acceptance Criteria

- [x] Reseed run fully analysed: all 17 categories assessed with success/fail comparison to guardkit_2 run 2
- [x] Init run fully analysed: 3 episodes assessed with timing comparison
- [x] TASK-REV-FFD3 "transient vLLM degradation" hypothesis evaluated (confirmed or refuted)
- [x] Episode 1 breakthrough (254.4s, no timeout) analysed
- [x] New "Target index -1" warning pattern investigated
- [x] Episode 3 root cause revised if vLLM hypothesis refuted
- [x] Cross-run trend analysis updated (init_8 → 10 → 11 → 12)
- [x] FEAT-SPR remaining task relevance confirmed or updated
- [x] TASK-REV-FFD3 report corrections identified (if hypothesis was wrong)
- [x] Recommendations for next steps

## Review Results

- **Report**: [TASK-REV-8A31-review-report.md](../../docs/reviews/TASK-REV-8A31-review-report.md)
- **Completed**: 2026-03-06
