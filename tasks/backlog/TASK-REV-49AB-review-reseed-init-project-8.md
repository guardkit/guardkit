---
id: TASK-REV-49AB
title: Review reseed + guardkit init output (init_project_8)
status: completed
created: 2026-03-04T17:15:00Z
updated: 2026-03-04T20:00:00Z
priority: high
task_type: review
review_mode: code-quality
review_depth: standard
complexity: 5
parent_review: TASK-REV-C043
feature_id: FEAT-ISF
tags: [graphiti, init, seeding, review, falkordb]
review_results:
  mode: code-quality
  depth: standard
  score: 72
  findings_count: 5
  recommendations_count: 3
  decision: implement
  implementation_feature: FEAT-SQF
  implementation_tasks: [TASK-FIX-b06f, TASK-FIX-bbbd, TASK-FIX-ec01]
  report_path: .claude/reviews/TASK-REV-49AB-review-report.md
  completed_at: 2026-03-04T20:00:00Z
---

# Review: Reseed + guardkit init Output (init_project_8)

## Review Scope

Analyse the output of the full `guardkit graphiti clear` + `guardkit graphiti seed --force` + `guardkit init fastapi-python -n vllm-profiling --copy-graphiti-from ~/Projects/appmilla_github/guardkit` run captured in:

**Source file**: `docs/reviews/reduce-static-markdown/reseed_init_project_8.md` (3,694 lines)

## Context

This is the first init run after:
1. **Full Graphiti clear** — wiped all system + project groups (clean graph)
2. **Full reseed** (`guardkit graphiti seed --force`) — re-seeded 17 system knowledge categories
3. **guardkit init** — seeded project knowledge to Graphiti

The prior review (TASK-REV-C043) identified:
- Parallel sync + main_content causing 0/12 rule sync failure
- System content re-seeded every init (architectural issue)
- Circuit breaker cascade from parallel failures
- TASK-ISF-001 through ISF-006 created as implementation tasks

## Key Questions for This Review

### Seed Phase (`guardkit graphiti seed --force`)
1. How many of the 17 knowledge categories succeeded vs failed/timed out?
2. What were the episode completion times? Any concerning slowdowns?
3. Did the circuit breaker trip? If so, what was the cascade?
4. Note: 3 template episodes timed out at 120s (line 3502-3553), circuit breaker tripped — what was skipped?
5. Pattern files ERROR (line 3566): "Pattern files not found: dataclasses, pydantic-models, orchestrators" — these files exist in `.claude/rules/patterns/` in the guardkit repo, not in the target project. Is the seed command looking in the wrong location?

### Init Phase (`guardkit init fastapi-python`)
1. Step 1: Did `-ext.md` files copy correctly? (Line 3640-3646 shows they DID copy — TASK-ISF-003 may already be resolved)
2. Step 2: Project knowledge seeding — 3 episodes, what were the times?
3. Note: Episode 3/3 took 249.7s — is this project_architecture? Was it the same timeout issue?
4. Multiple "LLM returned invalid duplicate_facts idx values" warnings — what do these mean?
5. The init now shows "Next steps: 1. Seed system knowledge: guardkit graphiti seed-system" — this references TASK-ISF-005 which doesn't exist yet. Is this premature?

### Comparison with init_project_7
1. How does the clean-graph init compare to the bloated-graph init_7?
2. Did the graph clear resolve the progressive slowdown issue?
3. Are the TASK-ISF-001/002 reverts still needed given the clean graph?

## Review Approach

Compare against TASK-REV-C043 findings to determine:
- Which FEAT-ISF tasks are still needed vs already addressed
- Whether the clean graph baseline changes the priority ordering
- Any new issues not previously identified

## Acceptance Criteria

- [ ] Seed phase analysed: successes, failures, timings, circuit breaker behaviour
- [ ] Init phase analysed: template copy, project seeding, timings
- [ ] Comparison with init_project_7 documented
- [ ] FEAT-ISF task relevance reassessed
- [ ] New findings (if any) documented
- [ ] Recommendations updated based on clean-graph baseline
