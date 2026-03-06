---
id: TASK-REV-95B1
title: Review reseed_guardkit_5 and init_project_14 — post template filter
status: review_complete
created: 2026-03-06T17:00:00Z
updated: 2026-03-06T17:30:00Z
review_results:
  mode: decision
  depth: comprehensive
  findings_count: 8
  recommendations_count: 5
  report_path: .claude/reviews/TASK-REV-95B1-review-report.md
priority: high
task_type: review
review_mode: decision
review_depth: comprehensive
complexity: 5
tags: [graphiti, seeding, templates, performance, template-filter, init]
related_to: [TASK-REV-acbc, TASK-a912]
---

# Review: Reseed GuardKit 5 & Init Project 14 — Post Template Filter

## Review Scope

Analyse the results of `guardkit graphiti seed --force` and `guardkit init fastapi-python` after applying the template filter changes from TASK-a912. Compare against previous runs (reseed_guardkit_3: 263m, 124/171 episodes) to quantify the improvement and identify remaining issues.

### Core Questions

1. **Did the template filter work?** How many episodes were seeded vs previous runs?
2. **How much time was saved?** Compare 98m 40s vs previous 263m
3. **What failed?** 8 episodes skipped — which ones and why?
4. **Init project performance?** How long did init take and what was the episode quality?
5. **Are there new issues?** LLM invalid duplicate_facts warnings — are these a problem?
6. **What's the next optimisation target?** Where is time still being spent unnecessarily?

### Evidence Available

| File | Description |
|------|-------------|
| `docs/reviews/reduce-static-markdown/reseed_guardkit_5.md` | Seed run with template filter (98m 40s, 70/78 episodes) |
| `docs/reviews/reduce-static-markdown/init_project_14.md` | Init of vllm-profiling project with fastapi-python template (830.9s) |

### Headline Results (to be verified)

**Seed (reseed_guardkit_5)**:
- Duration: **98m 40s** (down from 263m — **62% reduction**)
- Episodes: **70/78 created** (89.7%) — down from 171 total episodes
- Template filter: `{'default'}` — auto-detected
- Templates seeded: 1 (down from 7)
- Agents seeded: 0 (default has no agents, down from 18)
- Rules seeded: 1/3 (default rules, down from 72)
- 5 categories partial, 12 fully seeded

**Init (init_project_14)**:
- Template: fastapi-python
- Project: vllm-profiling
- Init seeding: 3 episodes in 830.9s (~13.8 min)
- Multiple `invalid duplicate_facts idx values` warnings from Qwen

### Key Questions

#### 1. Seed performance improvement
- Exact time comparison: 98m 40s vs 263m (reseed_3) — is this the expected improvement?
- Episode count: 78 total vs 171 — does this match the expected reduction?
- Are the 8 skipped episodes the same ones that always skip, or new failures?

#### 2. Category-by-category comparison
- Compare each category's success rate between reseed_3 and reseed_5
- Which categories improved, degraded, or stayed the same?
- Are the universal categories (product_knowledge, etc.) performing consistently?

#### 3. Template filter effectiveness
- Confirm templates seeded: 1 (default only)
- Confirm agents seeded: 0 (default has none)
- Confirm rules: only default template rules attempted (3 episodes, 1 succeeded)
- Why did 2/3 default rules skip?

#### 4. Init project quality
- 830.9s for 3 episodes — is this acceptable?
- Numerous `invalid duplicate_facts idx values` warnings — what causes these?
- Episode profiles: nodes=26/edges=44, nodes=13/edges=12, nodes=23/edges=63 — reasonable?
- Is the Qwen model producing quality graph extractions?

#### 5. Remaining optimisation opportunities
- Where is the remaining 98 minutes being spent?
- Which categories take the longest?
- Can any universal categories be skipped or cached?
- What's the next target for time reduction?

## Acceptance Criteria

- [ ] Duration comparison: reseed_5 vs reseed_3 with percentage improvement
- [ ] Episode-by-episode comparison where possible
- [ ] Category success rate comparison table
- [ ] Template filter verification (correct episodes excluded)
- [ ] Init project analysis (duration, quality, warnings)
- [ ] Root cause of skipped episodes identified
- [ ] Root cause of invalid duplicate_facts warnings assessed
- [ ] Remaining optimisation opportunities identified
- [ ] Recommendation for next steps
