---
id: TASK-TI-003
title: Orchestrator-gated writes scaffold pattern
status: completed
created: 2026-03-27T22:00:00Z
updated: 2026-03-29T00:00:00Z
completed: 2026-03-29T00:00:00Z
completed_location: tasks/completed/TASK-TI-003/
priority: p0
tags: [template, orchestration, adversarial, base-template]
complexity: 5
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 1
implementation_mode: task-work
depends_on: []
previous_state: in_review
state_transition_reason: "All quality gates passed, all acceptance criteria met"
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-29T00:00:00Z
  tests_total: 30
  tests_passed: 30
  tests_failed: 0
organized_files:
  - TASK-TI-003-orchestrator-gated-writes.md
---

# Task: Orchestrator-Gated Writes Scaffold

## Description

Create a scaffold pattern for the `langchain-deepagents` base template that enforces the orchestrator-gated writes pattern. This prevents the Player from writing output before Coach evaluation, the single most architecturally significant bug pattern (TRF-005, TRF-006).

## What to Build

### 1. Tool Separation Contract
- Player tool list: domain-specific tools ONLY (e.g., rag_retrieval). NO write, NO filesystem.
- Coach/Evaluator tool list: EMPTY. Evaluation only, no side effects.
- Orchestrator: owns `write_output` call, invoked programmatically after acceptance.

### 2. Write Gate
- Orchestrator calls `write_output` ONLY after Coach returns acceptance verdict
- Retry cap: configurable, default 3 per target (TRF-006 lesson)
- On retry exhaustion: reject target with structured error, do NOT loop indefinitely

### 3. Scaffold Code
- `OrchestratorWriteGate` class with:
  - `attempt_write(example, max_retries=3)` — calls write with retry logic
  - `on_acceptance(coach_verdict, player_output)` — triggered by Coach acceptance
  - `on_rejection(coach_verdict, player_output)` — triggered by Coach rejection
  - `on_exhaustion(target, attempts)` — triggered when retries exceeded

### 4. Player Prompt Enforcement
- System prompt includes: "You MUST NOT call write_output. Return the example as response content."
- Assertion at factory: `"write_output" not in [t.name for t in player.tools]`

## Fixes Prevented

TRF-003, TRF-005, TRF-006, TRF-016

## Target Location

`scaffold/orchestrator_pattern.py` (in the template output)

## Acceptance Criteria

- [x] Tool separation contract documented and enforced
- [x] Write gate with configurable retry cap
- [x] Player cannot call write_output (assertion at factory)
- [x] Orchestrator-only write invocation after Coach acceptance
- [x] Retry exhaustion handled gracefully (no infinite loops)
- [x] Unit tests for all gate states (accept, reject, exhaust)
- [x] Integration test showing full Player -> Coach -> Write flow

## Implementation Summary

### Files Created
- `installer/core/templates/langchain-deepagents/templates/other/scaffold/orchestrator_pattern.py.template` — OrchestratorWriteGate class, CoachVerdict dataclass, WriteResult, validate_player_tools()
- `tests/templates/langchain-deepagents/test_orchestrator_pattern.py` — 30 tests across 7 test classes

### Files Modified
- `installer/core/templates/langchain-deepagents/templates/other/agents/player.py.template` — Removed write_output from tool list, added factory assertion
- `installer/core/templates/langchain-deepagents/templates/other/prompts/player_prompts.py.template` — Added "MUST NOT call write_output" enforcement
- `installer/core/templates/langchain-deepagents/templates/other/other/agent.py.template` — Wired OrchestratorWriteGate into entrypoint

## Effort Estimate

1-2 days (actual: <1 day)
