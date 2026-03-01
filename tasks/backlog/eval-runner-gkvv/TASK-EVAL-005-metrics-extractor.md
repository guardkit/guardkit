---
id: TASK-EVAL-005
title: "Implement MetricsExtractor for evidence file parsing"
task_type: feature
parent_review: TASK-REV-EAE8
feature_id: FEAT-GKVV
status: pending
created: 2026-03-01T00:00:00Z
priority: high
tags: [eval-runner, metrics, evidence]
complexity: 3
wave: 2
implementation_mode: task-work
dependencies:
  - TASK-EVAL-001
---

# Task: Implement MetricsExtractor for Evidence File Parsing

## Description

Implement the metrics extraction system that reads `.eval/evidence/` files from both arm workspaces and produces `ComparisonMetrics` with deltas.

## Acceptance Criteria

- [ ] `MetricsExtractor.extract(guardkit_ws, vanilla_ws) -> ComparisonMetrics`
- [ ] Reads `.eval/evidence/c1.txt` for assumptions count (`assumptions_surfaced=N`)
- [ ] Reads `.eval/evidence/c2.txt` for test coverage (`coverage=N%`)
- [ ] Reads `.eval/evidence/c3.txt` for lint violations (`violations=N`)
- [ ] Reads `.eval/evidence/c5.txt` for runnable status (`runnable=yes|no`)
- [ ] Evidence file format: `key=value` plain text (ASSUM-003 confirmed)
- [ ] Missing evidence files produce `-1` / "not measurable" — NOT errors
- [ ] `ComparisonMetrics.coverage_delta()` returns positive when GuardKit better
- [ ] `ComparisonMetrics.lint_delta()` returns negative when GuardKit better (fewer violations)
- [ ] `ComparisonMetrics.assumption_surfacing_delta()` returns positive when GuardKit surfaced more
- [ ] Both arms with identical metrics → all deltas are 0
- [ ] `ComparisonMetrics.to_graphiti_fields()` serializes deltas for Graphiti storage
- [ ] Unit tests for parsing, missing files, delta calculations, edge cases

## Technical Context

- Location: `guardkit/eval/metrics.py` (new module)
- Prototype reference: `docs/research/eval-runner/guardkit_vs_vanilla_runner.py` (MetricsExtractor, ArmMetrics, ComparisonMetrics)
- Design reference: `docs/research/eval-runner/eval-runner-guardkit-vs-vanilla.md` (Section 7)
- Evidence convention: `docs/research/eval-runner/eval-runner-architecture.md` (Section 5.2)

## BDD Scenario Coverage

- Key example: Quantitative metrics extracted from both workspaces
- Boundary: Missing evidence files produce not-measurable metrics, not errors
- Boundary: Perfect tie produces weighted score of 0.5
- Key example: Comparison includes coverage delta, lint delta, assumption delta

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
