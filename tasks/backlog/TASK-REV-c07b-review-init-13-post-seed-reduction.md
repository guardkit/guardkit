---
id: TASK-REV-c07b
title: Review init_project_13 results after seed scope reduction
status: completed
created: 2026-03-06T15:00:00Z
updated: 2026-03-06T16:30:00Z
review_results:
  mode: code-quality
  depth: comprehensive
  findings_count: 8
  recommendations_count: 5
  report_path: .claude/reviews/TASK-REV-c07b-review-report.md
priority: high
task_type: review
review_mode: code-quality
review_depth: comprehensive
complexity: 5
parent_review: TASK-REV-acbc
tags: [graphiti, init, seeding, performance, verification]
---

# Review: init_project_13 Results After Seed Scope Reduction

## Review Scope

Verify whether the implementation of TASK-REV-acbc recommendations (TASK-daab, TASK-a912) has resolved the seeding waste issues. Compare init_project_13 results against the TASK-REV-acbc review findings and the init_project_12 baseline.

### Data Sources

1. **init_project_13 output**: `docs/reviews/reduce-static-markdown/init_project_13.md`
   - Contains 2 runs: Run 1 appears to be pre-implementation (identical to init_12), Run 2 is post-implementation with new features (episode profiling)
2. **TASK-REV-acbc review report**: `.claude/reviews/TASK-REV-acbc-review-report.md`
3. **Previous baselines**: init_project_12 (TASK-REV-8A31), init_project_11 (TASK-REV-FFD3)

### Context: What Changed

TASK-REV-acbc identified a three-layer problem:
1. **Seed duration**: Seeds all 7 templates (~263 min) — recommended template filtering
2. **Static context per turn**: ~116 KB injected every AutoBuild turn — recommended selective rule loading
3. **Seeding vs static gap**: Graphiti seeding is additive, not substitutive

Implementation tasks:
- **TASK-daab** (Wave 1): Selective rule loading for AutoBuild worktrees — target ~46 KB reduction
- **TASK-a912** (Wave 2): Template filtering in `guardkit graphiti seed` — target 40-60% seed time reduction

## Quick Observations from init_project_13

### Run 2 (post-implementation)

- **Episode 1/3 (project_purpose): 425.2s** — significant regression from 254.4s (init_12). Now exceeds the 300s timeout ceiling that was previously the limit.
- **Episode 2/3 (project_tech_stack): 116.6s** — previously this was Episode 2=project_overview. Episode names may have changed. Similar timing to previous project_overview (~108s).
- **Episode 3/3 (project_architecture): 338.7s** — previously this was Episode 3=tech_stack at ~249s. Significant regression (+90s).
- **Total: 880.5s (14.7 min)** — vs 611.3s (10.2 min) in init_12. **44% slower overall.**
- **New feature**: Episode profiling output (`nodes=X, edges=Y, invalidated=Z`)
- **No "out of bounds" warnings** in Run 2 — resolved!
- **No embedding retries** — infrastructure stable
- **Increased duplicate_facts warnings** — significantly more than init_12

### Key Differences to Investigate

1. **Episode names changed**: `project_purpose` / `project_overview` / `tech_stack` → `project_purpose` / `project_tech_stack` / `project_architecture` — was the init content restructured?
2. **Episode 1 now 425s** (was 254s) — massive regression. Is this because the 300s timeout was removed/increased per TASK-FIX-cc7e?
3. **Episode 3 now 339s** (was 249s) — another significant regression
4. **No timeout at all** — all 3 episodes completed. Were timeouts removed or increased?
5. **Episode profiling is new** — nodes/edges/invalidated counts. What do these reveal about graph operations?

## Key Questions

### 1. What is the actual impact of the seed scope reduction?
- Run 2 is clearly a different codebase version — what specifically changed?
- Is the init seeding now template-filtered (only fastapi-python relevant content)?
- Did the episode content/structure change (different names, different content being seeded)?

### 2. Why are all episodes slower in Run 2?
- Episode 1: 254.4s → 425.2s (+67%)
- Episode 2: 108.1s → 116.6s (+8%)
- Episode 3: 248.8s → 338.7s (+36%)
- Is this due to content changes, graph state differences, or vLLM performance?

### 3. Were the "out of bounds" warnings actually resolved?
- Run 2 has zero "out of bounds" warnings (Run 1 had 14)
- Is this a code fix, content change, or coincidental?

### 4. What do the new episode profiling metrics reveal?
- Episode 1: 23 nodes, 60 edges — is this expected for project_purpose?
- Episode 2: 13 nodes, 14 edges — lightweight
- Episode 3: 24 nodes, 59 edges — similar to Episode 1
- What do these tell us about graph operations per episode?

### 5. Did the reseed (`guardkit graphiti seed`) also improve?
- Was a reseed run done after the implementation? If so, what were the category results?
- How many categories are now seeded? What's the template-filtered count?

### 6. TASK-REV-acbc metrics: were targets met?
- Target: 40-60% seed time reduction — achieved?
- Target: ~46 KB context reduction per AutoBuild turn — achieved?
- Target: 100% waste elimination on irrelevant episodes — achieved?

## Acceptance Criteria

- [ ] init_13 Run 2 fully analysed with timing breakdown
- [ ] Episode name/content changes documented (what restructuring occurred)
- [ ] Performance regression root cause identified (425s Ep1, 339s Ep3)
- [ ] "Out of bounds" warning resolution confirmed or investigated
- [ ] Episode profiling metrics analysed
- [ ] Comparison to init_12 baseline with delta analysis
- [ ] TASK-REV-acbc target metrics assessed (seed time reduction, context reduction)
- [ ] Cross-run trend analysis updated (init_8 → 13)
- [ ] Assessment of whether implementation objectives were met
- [ ] Recommendations for further optimisation or acceptance of results
