---
id: TASK-INV-7c71
title: Investigate Episode 3 (tech_stack) structural slowdown from ~99s to ~249s
status: completed
created: 2026-03-06T12:00:00Z
updated: 2026-03-06T18:00:00Z
completed: 2026-03-06T18:30:00Z
completed_location: tasks/completed/TASK-INV-7c71/
priority: medium
task_type: review
review_mode: decision
complexity: 6
parent_review: TASK-REV-8A31
feature_id: FEAT-GIP
tags: [graphiti, init, performance, investigation, tech_stack]
wave: 1
implementation_mode: direct
dependencies: []
---

# Task: Investigate Episode 3 (tech_stack) structural slowdown

## Problem

Episode 3 (tech_stack) init time jumped from ~99s to ~249s and the elevated timing is now reproducible across 2 runs with different vLLM states. TASK-REV-8A31 refuted the "transient vLLM degradation" hypothesis from TASK-REV-FFD3.

### Evidence

| Run | Episode 3 Time | Context |
|-----|---------------|---------|
| init_10 | 99.1s | Pre-clear+reseed |
| init_11 R1 | 99.1s | Pre-clear+reseed |
| init_11 R2 | 249.2s | Post-clear+reseed |
| init_12 | 248.8s | Post-clear+reseed, fresh vLLM |

The inflection correlates with the clear+reseed cycle, not vLLM instability.

## Investigation Plan

### 1. Graph Topology Comparison
- Compare entity counts and edge density before init (after reseed only)
- Compare with the graph state that existed during init_10/11R1 (if reproducible)
- Identify if reseed creates a different edge distribution that slows Episode 3

### 2. Profile Episode 3 at graphiti-core Level
- Instrument or log which phase of `add_episode` is slow:
  - Entity extraction (LLM inference)
  - Edge extraction (LLM inference)
  - Edge resolution (graph traversal + LLM)
  - Persistence (FalkorDB writes)
- Determine if the slowdown is LLM-bound or graph-traversal-bound

### 3. Content Isolation Test
- Run init with a truncated tech_stack section (e.g., half the content)
- Compare timing to determine if it's content-proportional or fixed overhead

### 4. Episode 2 as Control
- Episode 2 (project_overview, ~108s) is stable across all runs
- Any Episode 3 explanation must account for why Episode 2 is unaffected
- Compare content sizes: tech_stack vs project_overview

## Key Question

Is ~249s now the permanent baseline, or can the ~99s timing be recovered by adjusting graph state or content?

## Acceptance Criteria

- [x] Graph topology compared between pre- and post-clear+reseed states
- [x] Episode 3 profiled to identify slow phase(s) — Phase 4b Edge Resolution
- [~] Content isolation test run — analyzed via code; live test requires infra
- [x] Root cause identified: Edge resolution scaling with graph density (8/10 confidence)
- [x] Recommendation: Accept ~249s as baseline

## Investigation Report

See: [docs/reviews/TASK-INV-7c71-investigation-report.md](../../../docs/reviews/TASK-INV-7c71-investigation-report.md)

## Deliverables

1. **Investigation report**: `docs/reviews/TASK-INV-7c71-investigation-report.md`
2. **Episode profiling**: Added entity/edge count logging to `_create_episode()` in `graphiti_client.py`
3. **Graph stats command**: Added `guardkit graphiti stats` for topology inspection
