---
id: TASK-EVAL-009
title: "Implement Graphiti storage for comparison eval results"
task_type: feature
parent_review: TASK-REV-EAE8
feature_id: FEAT-GKVV
status: pending
created: 2026-03-01T00:00:00Z
priority: high
tags: [eval-runner, graphiti, storage, episodes]
complexity: 4
wave: 4
implementation_mode: task-work
dependencies:
  - TASK-EVAL-001
  - TASK-EVAL-007
---

# Task: Implement Graphiti Storage for Comparison Eval Results

## Description

Implement Graphiti episode storage for guardkit_vs_vanilla eval results, including per-arm metrics, deltas, and local JSON cache fallback.

## Acceptance Criteria

- [ ] `EvalResultStore.store(eval_result) -> bool` stores result as Graphiti episode
- [ ] Episode includes `eval_id`, `type: "guardkit_vs_vanilla"`, `status`, `weighted_score`
- [ ] Episode includes `guardkit_arm` field with per-arm metrics (turns, coverage, lint, assumptions, runnable)
- [ ] Episode includes `vanilla_arm` field with per-arm metrics
- [ ] Episode includes `deltas` field with coverage, lint, and assumption deltas
- [ ] Episode includes `eval_type` as `"guardkit_vs_vanilla"` for filtering
- [ ] Uses existing `graphiti_client.get_graphiti()` singleton — no new client creation
- [ ] Graphiti unavailability does NOT prevent local JSON cache write
- [ ] Results cached locally at `results/{eval_id}.json` (ASSUM-007)
- [ ] Warning logged on Graphiti storage failure (not error, not exception)
- [ ] Local JSON cache can be synced to Graphiti later (manual or batch)
- [ ] Unit tests for episode serialization, Graphiti failure handling, local cache write

## Technical Context

- Location: `guardkit/eval/storage.py` (new module)
- Graphiti client: `guardkit/knowledge/graphiti_client.py` (reuse `get_graphiti()`)
- Graphiti patterns: `guardkit/integrations/graphiti/` (episode patterns)
- Design reference: `docs/research/eval-runner/eval-runner-architecture.md` (Section 6)
- Design reference: `docs/research/eval-runner/eval-runner-guardkit-vs-vanilla.md` (Section 9)
- JSON schema: `docs/research/eval-runner/eval-runner-guardkit-vs-vanilla.md` (Section 9)

## BDD Scenario Coverage

- Edge case: Comparison results stored in Graphiti include arm-level detail and deltas
- Edge case: Graphiti storage failure does not prevent NATS result publication (for CLI: does not prevent local cache)

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
