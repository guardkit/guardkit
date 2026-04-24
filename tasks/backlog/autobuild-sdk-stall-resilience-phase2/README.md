# Feature: AutoBuild SDK Stall Resilience — Phase 2

**Feature ID**: FEAT-F3D7
**Parent review**: [TASK-REV-F3D7](../TASK-REV-F3D7-analyse-forge-run-3-autobuild-failure.md)
**Review report**: [docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md](../../../docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md)

## Problem Statement

The original `autobuild-sdk-stall-resilience` feature (FEAT-7A00) shipped seven
subtasks — TASK-FIX-7A01 through TASK-FIX-7A07 plus TASK-DOC-7A06 — and all
landed correctly. However, re-running `FEAT-FORGE-002 (NATS Fleet Integration)`
on GB10 still fails with the same root behaviour the feature was supposed to
address: the Player completes `task-work` mode tasks inline without invoking
the required specialists (`test-orchestrator`, `code-reviewer`, stack-specific
Phase-3) via the Task tool.

The review of forge-run-3 (TASK-REV-F3D7) identified that:

1. The `coach_agent_invocations_stall` classifier (TASK-FIX-7A07) fires correctly
   and names `TASK-FIX-7A08` as the remediation — but **TASK-FIX-7A08 was never
   filed** as a subtask in the original IMPLEMENTATION-GUIDE. It exists only as a
   hardcoded string literal at `autobuild.py:5078` and `feature_orchestrator.py:1616`.
2. TASK-FIX-7A03's defensive SDK stream handling covers `_invoke_with_role` but
   **does not cover the Coach independent-test SDK path** at `coach_validator.py:1375`,
   so transport-level `ProcessError` (`exit code 1`) is logged opaquely rather
   than classified.
3. The dead `TASK-FIX-7A08` reference in the summary/advice text needs
   resolution.

## Solution Approach

Three tasks, two waves:

- **Wave 1 (parallel)**: file and implement the two load-bearing fixes on
  disjoint files — `TASK-FIX-7A08` (prompts + `agent_invoker.py`) and
  `TASK-FIX-7A09` (`coach_validator.py`).
- **Wave 2 (sequential)**: `TASK-FIX-7A0A` adds a CI lint check asserting every
  hardcoded `TASK-FIX-XXXX` / `TASK-REV-XXXX` literal in orchestrator code
  resolves to a real task file — preventing the class of defect that originated
  this review.

## Subtasks

| ID | Title | Wave | Mode | Complexity | Hypothesis |
|----|-------|------|------|------------|------------|
| TASK-FIX-7A08 | Player prompt mandates Task-tool invocation for Phase 3/4/5 | 1 | task-work | 4 | H1 (load-bearing) |
| TASK-FIX-7A09 | Extend 7A03 defensive handling to Coach independent-test SDK path | 1 | task-work | 3 | H3 (scope gap) |
| TASK-FIX-7A0A | CI lint: every hardcoded TASK-ID literal resolves to a real task file | 2 | direct | 1 | H1 (cleanup) |

## Expected Outcome

A clean re-run of `guardkit autobuild feature FEAT-FORGE-002` on GB10 with:

- Wave 2 tasks (NFI-003, NFI-007) pass the agent-invocations gate on turn 1
  (Player invokes `test-orchestrator`, `code-reviewer`, and the Phase-3
  specialist via the Task tool).
- Any future Coach independent-test SDK transport failure surfaces as a
  classified log with `stderr` attached, not an opaque "exit code 1".
- CI fails if a future change introduces a dead task-ID reference in
  orchestrator code.

## Completion

When all three subtasks are in `completed/`:

```bash
/task-complete TASK-REV-F3D7
```

…then capture the feature-level outcome to Graphiti under
`guardkit__task_outcomes` (FEAT-F3D7).
