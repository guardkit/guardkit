---
complexity: 5
dependencies:
- TASK-SFT-001
feature_id: FEAT-AC1A
id: TASK-SFT-003
implementation_mode: task-work
parent_review: TASK-REV-AC1A
priority: high
status: design_approved
task_type: testing
title: Seam tests S3 — Orchestrator-to-module wiring
wave: 2
---

# Seam Tests S3: Orchestrator → Module Wiring

## Objective

Write seam tests that verify orchestrator functions actually call their module dependencies — catching stub implementations where `run_system_plan()` is `pass` or `run_feature_plan()` silently skips steps.

## Seam Definition

**Layer A**: Orchestrator entry points (`run_system_plan()`, `run_feature_plan()`, `run_impact_analysis()`)
**Layer B**: Module calls (spec parser, Graphiti client, architecture writer, feature planner)

## Acceptance Criteria

- [ ] `tests/seam/test_orchestrator_wiring.py` created
- [ ] Test: `run_system_plan()` with context file calls `parse_architecture_spec()` (not a stub)
- [ ] Test: `run_system_plan()` with context file calls `_persist_entities()` when Graphiti is available
- [ ] Test: `run_system_plan()` with context file calls `_write_artefacts()`
- [ ] Test: `run_system_plan()` without Graphiti still calls `_write_artefacts()` (graceful degradation)
- [ ] Test: `run_feature_plan()` calls feature decomposition modules
- [ ] Test: `run_impact_analysis()` calls Graphiti context retrieval
- [ ] Tests use real implementations on the orchestrator side, protocol-level mocks on the external boundary (Graphiti client AsyncMock, tmp filesystem for file I/O)
- [ ] All tests pass with `pytest tests/seam/test_orchestrator_wiring.py -v`
- [ ] No function-level mocks on the orchestrator methods themselves (the whole point is to verify they're not stubs)

## Anti-Patterns to Avoid

- Do NOT mock `run_system_plan()` — call it directly
- Do NOT mock `parse_architecture_spec()` — let it run against a real fixture
- DO mock the Graphiti client at the protocol level (AsyncMock with `.enabled = True`)
- DO use tmp directories for file I/O assertions