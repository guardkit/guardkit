# Implementation Guide: Honesty / State-Bridge Resilience Fix

**Feature ID**: FEAT-1B452
**Total estimated effort**: 8.5 hours across 4 tasks, 3 waves

## Wave 1 — parallel (load-bearing fixes)

Both tasks must land before next autobuild attempt. They touch disjoint files and can run concurrently in Conductor workspaces.

### Wave 1 / Task 1 — TASK-FIX-1B4A (Layer 1)

- **Workspace**: `honesty-fix-wave1-1`
- **Files touched**: `guardkit/tasks/state_bridge.py` (+~5 lines), `guardkit/orchestrator/coach_verification.py` (+~20 lines), `guardkit/orchestrator/quality_gates/coach_validator.py` (~5 lines)
- **Estimated**: 3 hours
- **Acceptance**: 5 ACs (AC-A1..AC-A5)
- **Tests**: new `tests/unit/test_coach_verification_state_bridge.py`

### Wave 1 / Task 2 — TASK-FIX-1B4C (Layer 3')

- **Workspace**: `honesty-fix-wave1-2`
- **Files touched**: `guardkit/tasks/state_bridge.py` (+~25 lines), `guardkit/orchestrator/agent_invoker.py` (+~15 lines)
- **Estimated**: 3 hours
- **Acceptance**: 5 ACs (AC-C1..AC-C5)
- **Tests**: new `tests/unit/test_orchestrator_induced_path_filter.py`

**Note on parallel-safety**: both Wave 1 tasks edit `state_bridge.py`. They touch different methods (1B4A adds `canonical_path_for`; 1B4C adds `transition tracking` + `orchestrator_induced_paths_for`). Merge order: whichever lands first; the second resolves a small textual conflict at the bottom of the file's public-method block. No semantic conflict.

## Wave 2 — single (depends on Wave 1)

### TASK-FIX-1B4B (Layer 2)

- **Workspace**: `honesty-fix-wave2-1`
- **Files touched**: `guardkit/orchestrator/quality_gates/coach_validator.py` (~25 lines)
- **Depends on**: TASK-FIX-1B4A (test fixtures align with Layer 1's resolution semantics)
- **Estimated**: 2 hours
- **Acceptance**: 5 ACs (AC-B1..AC-B5)
- **Tests**: extend `tests/unit/test_coach_validator.py`

## Wave 3 — single (documentation)

### TASK-DOC-1B4D

- **Workspace**: `honesty-fix-wave3-1`
- **Files touched**: `.claude/rules/path-string-mismatch-is-not-dishonesty.md` (new), `.claude/rules/absence-of-failure-is-not-success.md` (cross-link in prior-art)
- **Depends on**: TASK-FIX-1B4A and TASK-FIX-1B4C (rule must cite landed fixes, not proposals)
- **Estimated**: 30 minutes
- **Acceptance**: 3 ACs (AC-DOC1..AC-DOC3)

## Validation criteria (feature-level)

Feature is complete when:

1. All 4 subtasks pass their individual quality gates.
2. **End-to-end regression**: an integration test reproduces the FFC3 scenario (record baseline → state_bridge.transition_to_design_approved → simulate Player → orchestrator collects report → CoachValidator.validate) and asserts:
   - `result.acceptance_criteria_verification.criteria_results` is non-empty (16 ACs evaluated).
   - `"Adversarial verification overrode"` is **not** in `result.rationale`.
   - Either: `report["files_modified"]` does not contain the pre-move path (Layer 3' filtered it), OR `result.honesty_verification.resolved_paths` records the resolution (Layer 1 caught it).
3. Manual smoke test: run a fresh autobuild against a small task, observe state_bridge move, verify Coach evaluates ACs successfully.

## Risk-mitigation invariants

These must hold across all four tasks:

- **AC-A3 / AC-C5 (fail-open)**: when state_bridge data is missing or malformed, behaviour falls back to current — no new failure mode introduced.
- **AC-A2 / AC-A4 (identity-bounded resolution)**: Layer 1 resolution only consults canonical path for the task being validated. A claim referencing a different task's path is not resolved.
- **AC-B3 / AC-B4 (adversarial property preserved)**: Layer 2 demotion does NOT apply to `promise_file_existence` (FEAT-6CC5 case), `test_result`, or `test_count` — those remain `must_fix`.
- **No silencing**: every honesty signal still reaches the Player as feedback (either as `should_fix` or recorded on `resolved_paths`); nothing is silently dropped.
