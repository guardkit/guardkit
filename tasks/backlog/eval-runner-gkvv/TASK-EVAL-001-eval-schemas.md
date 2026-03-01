---
id: TASK-EVAL-001
title: "Create eval schemas (EvalBrief, EvalResult, InputSource)"
task_type: scaffolding
parent_review: TASK-REV-EAE8
feature_id: FEAT-GKVV
status: pending
created: 2026-03-01T00:00:00Z
priority: high
tags: [eval-runner, schemas, pydantic]
complexity: 3
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Create Eval Schemas (EvalBrief, EvalResult, InputSource)

## Description

Define the core Pydantic models and dataclasses for the eval runner system. These schemas are the foundation that all other eval runner components depend on.

## Acceptance Criteria

- [ ] `EvalBrief` Pydantic model parses YAML brief files with validation
- [ ] `GuardKitVsVanillaBrief` extends `EvalBrief` with `input`, `guardkit_arm`, `vanilla_arm` fields
- [ ] `InputSource` enum: `text`, `file`, `linear_ticket`
- [ ] `EvalBrief.from_yaml(path)` loads and validates YAML, dispatches to correct subclass based on `type` field
- [ ] `EvalResult` dataclass with `eval_id`, `status` (PASSED/FAILED/ESCALATED/ERROR), `weighted_score`, `criterion_scores`, `run_date`
- [ ] `ArmMetrics` dataclass with `turns_total`, `test_coverage_pct`, `lint_violations`, `assumptions_explicit`, `runnable`
- [ ] `ComparisonMetrics` dataclass with `guardkit: ArmMetrics`, `vanilla: ArmMetrics`, plus `coverage_delta()`, `lint_delta()`, `assumption_surfacing_delta()` methods
- [ ] `EvalResult.to_graphiti_episode()` serializes to the Graphiti JSON schema (including `guardkit_arm`, `vanilla_arm`, `deltas` fields for comparison results)
- [ ] All models follow GuardKit Pydantic v2 patterns (see `.claude/rules/patterns/pydantic-models.md`)
- [ ] Unit tests for YAML parsing, validation, serialization, delta calculations

## Technical Context

- Location: `guardkit/eval/schemas.py` (new module)
- Reference schemas: `docs/research/eval-runner/eval-runner-architecture.md` (Section 4)
- Reference schemas: `docs/research/eval-runner/eval-runner-guardkit-vs-vanilla.md` (Sections 3, 7, 9)
- Example brief: `docs/research/eval-runner/EVAL-007-guardkit-vs-vanilla-youtube.yaml`
- Pattern reference: `.claude/rules/patterns/pydantic-models.md` for Pydantic models, `.claude/rules/patterns/dataclasses.md` for ArmMetrics/ComparisonMetrics

## BDD Scenario Coverage

- Boundary: pass_threshold 0.65 exactly → PASSED
- Boundary: weighted score 0.64 → FAILED
- Boundary: escalate_threshold 0.40 exactly → FAILED (not escalated)
- Boundary: weighted score 0.39 → ESCALATED
- Boundary: perfect tie → weighted score 0.5
- Negative: unknown input source "database" → InputResolutionError

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
