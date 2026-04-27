---
id: TASK-ABSR-C3D4
title: Add environment_stall sub-type with environment-aware diagnostic message
status: completed
task_type: feature
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
completed: 2026-04-27T00:00:00Z
completed_location: tasks/completed/TASK-ABSR-C3D4/
previous_state: in_review
state_transition_reason: "All AC met, 19 new tests pass, 34 existing classifier tests still pass"
priority: high
tags: [autobuild, stall-detection, diagnostics]
parent_review: TASK-REV-FA04
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
wave: 1
conductor_workspace: autobuild-stall-resilience-wave1-env-stall
complexity: 5
depends_on: []
---

# TASK-ABSR-C3D4 — Add environment_stall sub-type with environment-aware diagnostic message

## Description

Replace the misleading "Suggested action: Review task_type classification" hint with environment-aware diagnostic guidance when an `unrecoverable_stall` is driven by repeated `infrastructure`-class failures. Add a new sub-type value `environment_stall` to [`_classify_unrecoverable_stall`](../../../guardkit/orchestrator/autobuild.py#L371-L414) and route the post-loop summary renderer to a dedicated message naming the bootstrap state, the active interpreter, and the manifest's `requires-python` constraint.

This task is purely additive — no existing sub-type semantics change.

## Acceptance Criteria

- [x] New `EnvironmentStallSubtype` enum value (or string literal) added at [`autobuild.py:283-414`](../../../guardkit/orchestrator/autobuild.py#L283-L414) alongside `agent_invocations_violation`, `context_pollution`, `coach_feedback_stall`.
- [x] `_classify_unrecoverable_stall` returns `environment_stall` when **all** of the following hold across the trailing 3 turns of the failing task:
  - `final_decision == "unrecoverable_stall"`
  - For each of the trailing 3 turn records: `validation_results.quality_gates.all_gates_passed == True`
  - For each of the trailing 3 turn records: `validation_results.independent_tests.tests_passed == False`
  - `issues[].failure_classification == "infrastructure"` for the test_verification issue in each turn
  - `failure_confidence` is identical across the three turns (any value)
- [x] Existing sub-types remain unchanged for non-matching cases (`agent_invocations_violation` and `context_pollution` continue to take precedence where applicable).
- [x] Post-loop summary renderer at [`autobuild.py:5046-5329`](../../../guardkit/orchestrator/autobuild.py#L5046-L5329) (or wherever the `final_decision == "unrecoverable_stall"` summary path lives) emits an `environment_stall`-specific message containing:
  - "Stall driven by repeated infrastructure-class failures while all Player gates passed."
  - The bootstrap state (read from `<worktree>/.guardkit/bootstrap_state.json` if present): success/failure flag and `installs_attempted` / `installs_failed`.
  - The active Python interpreter version (`platform.python_version()`).
  - The manifest's `requires-python` constraint (read from the worktree's `pyproject.toml`).
  - Concrete remediation: "Set `bootstrap_failure_mode: block` in `.guardkit/config.yaml` (or pass `--bootstrap-failure-mode block`). Install a compatible interpreter with `uv python install <X>`, `pyenv install <X>`, or `conda create -n <name> python=<X>`."
- [x] The misleading "Suggested action: Review task_type classification..." hint must NOT appear when sub-type is `environment_stall`. (It may remain for `coach_feedback_stall` where task-type classification could still be the issue.)
- [x] **New tests**:
  - `test_environment_stall_classification_when_infrastructure_repeated`
  - `test_environment_stall_diagnostic_includes_bootstrap_state`
  - `test_environment_stall_diagnostic_names_interpreter_and_constraint`
  - `test_environment_stall_does_not_fire_when_only_one_turn_matches`
  - `test_existing_subtypes_unchanged_for_non_env_stalls`
  - `test_environment_stall_takes_precedence_over_generic_coach_feedback_stall_when_pattern_matches`
- [x] Documentation: update `docs/guides/autobuild-instrumentation-guide.md#if-autobuild-stalls-immediately` (or the runbook section it references) to include `environment_stall` and its remediation.

## Implementation Notes

- The renderer should treat the bootstrap state file as best-effort: if missing or unparseable, omit those fields from the message rather than crashing. The diagnostic is helpful even partial.
- Reading the `pyproject.toml` for `requires-python` should reuse [`DetectedManifest.get_requires_python()`](../../../guardkit/orchestrator/environment_bootstrap.py#L260-L293) rather than re-parsing.
- If the worktree was not created from a Python project (no manifest), the renderer should fall through to the generic stall message. This task only enriches the Python-project case.
- Cross-stack note (per [.claude/rules/namespace-hygiene.md](../../../.claude/rules/namespace-hygiene.md) sibling rule): the env-stall diagnostic should also fire when the failure is `ImportError` for a known service-client lib not in `_KNOWN_SERVICE_CLIENT_LIBS`. This is currently covered by `failure_class=="infrastructure"` so no extra logic is needed — verify in tests.

## Out of Scope

- Interpreter discovery (R5).
- Changes to the stall-detection threshold itself (still 3 identical turns).
- Cross-stack diagnostic for non-Python stalls — defer until evidence emerges.

## References

- Review: [TASK-REV-FA04 report](../../../.claude/reviews/TASK-REV-FA04-report.md) §F4, §R2, "Regression Analysis — R2"
- Sub-type infrastructure: [autobuild.py:283-414](../../../guardkit/orchestrator/autobuild.py#L283-L414), [autobuild.py:5046-5329](../../../guardkit/orchestrator/autobuild.py#L5046-L5329)

## Implementation Summary

Added the `environment_stall` sub-type to GuardKit's stall classifier so that a Player-clean / Coach-infra-fail signal pattern routes to an environment-aware diagnostic instead of the misleading "Review task_type classification" hint.

**Changes**:
- `guardkit/orchestrator/autobuild.py`:
  - Added `import platform` and the `STALL_ENVIRONMENT = "environment_stall"` constant alongside the existing stall sub-type labels.
  - New helper `_extract_environment_stall_signal(turn_record)` walks `coach_result.report` defensively and returns the matching `test_verification` issue when `all_gates_passed=True`, `independent_tests.tests_passed=False`, and `failure_classification == "infrastructure"`.
  - Updated `classify_stall()` to fire `STALL_ENVIRONMENT` when the trailing 3 turns all match the pattern with identical `failure_confidence`. `coach_agent_invocations_stall` and `context_pollution_stall_no_checkpoint` continue to take precedence.
  - Added `AutoBuildOrchestrator._build_environment_stall_diagnostic()` which builds a multi-line message naming the bootstrap state (success / installs_attempted / installs_failed from `<worktree>/.guardkit/bootstrap_state.json`), the active interpreter (`platform.python_version()`), the manifest's `requires-python` (via `DetectedManifest.get_requires_python()`), and concrete `uv` / `pyenv` / `conda` remediation. Returns `None` for non-Python worktrees so the renderer falls through to the generic message.
  - Wired the env-stall branch into `_build_summary_details()` between the existing `coach_agent_invocations_stall` block and the SDK-API-error fallback, so the misleading task-type hint is suppressed when `environment_stall` fires.
- `tests/unit/test_environment_stall_classification.py`: 19 tests covering predicate, classification (positive + negative + precedence + confidence-mismatch + threshold), diagnostic renderer (bootstrap state present/absent/corrupt, non-Python fall-through, interpreter + constraint), and `_build_summary_details` routing. All 6 AC-named tests included.
- `docs/guides/autobuild-instrumentation-guide.md`: Added an `environment_stall` row to the "If AutoBuild stalls immediately" triage table and a paragraph describing where the signal lives, how the renderer enriches it, and how `TASK-ABSR-A1B2` interacts.

**Test results**: 19 new tests pass; 34 pre-existing classifier tests still pass; 0 regressions. Pre-existing failures elsewhere in the suite (e.g. `TestCoachValidatorPathConstruction`) confirmed unrelated via `git stash` baseline.

## Notes

**Lessons**:
- The renderer treats every external input as best-effort: `bootstrap_state.json` may be missing, partial, or unparseable, and the diagnostic still renders the parts it can read. This avoids a class of "diagnostic crashed in the diagnostic" failures.
- The `_extract_environment_stall_signal` predicate reuses the schema-stable walk pattern from `_extract_agent_invocations_violation` (TASK-FIX-7A07). Keeping the two predicates parallel makes it easier to add future stall sub-types — same shape, same defensiveness.
- Precedence between sub-types matters: making `coach_agent_invocations_stall` and `context_pollution` take precedence over `environment_stall` (rather than co-firing) keeps the most actionable diagnostic on top. The agent-invocations message names the missing phases; co-firing it with env-stall would dilute the signal.
- `AutoBuildOrchestrator` constructor requires a real git repo at `repo_root`. Test harnesses must inject a fake `worktree_manager=` to bypass `WorktreeManager(repo_root=...)` git validation.

**Cross-stack confirmation**: The `failure_class == "infrastructure"` check already covers the `ImportError` for service-client libs case (per the task brief's cross-stack note) — no extra logic needed; verified by the predicate test suite.

**Sibling task interaction**: `TASK-ABSR-A1B2` (smart-default `bootstrap_failure_mode: block`) runs in parallel; its work touches `bootstrap_state.json` semantics (may add `installs_attempted` / `installs_failed` fields explicitly). The renderer here only reads fields if present, so the two tasks compose without ordering constraints.
