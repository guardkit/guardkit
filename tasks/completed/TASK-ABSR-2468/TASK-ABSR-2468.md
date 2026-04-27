---
id: TASK-ABSR-2468
title: Coach conditional-approval branch for environment-class infrastructure failures
status: completed
task_type: feature
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
completed: 2026-04-27T00:00:00Z
completed_location: tasks/completed/TASK-ABSR-2468/
previous_state: in_review
state_transition_reason: "All acceptance criteria satisfied; 13/13 new tests pass; 326 existing coach_validator tests still pass; documentation updated"
priority: medium
tags: [autobuild, coach, conditional-approval, environment]
parent_review: TASK-REV-FA04
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
wave: 2
conductor_workspace: autobuild-stall-resilience-wave2-env-conditional-approval
complexity: 6
depends_on:
  - TASK-ABSR-A1B2
  - TASK-ABSR-7890
---

# TASK-ABSR-2468 — Coach conditional-approval branch for environment-class infrastructure failures

## Description

Add a fifth conditional-approval clause to [`CoachValidator.validate`](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L831-L854) for the case where:
- `failure_class == "infrastructure"`
- `failure_confidence == "ambiguous"` (`ImportError` / `ModuleNotFoundError` / "No module named" — see [`_INFRA_AMBIGUOUS`](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L399-L404))
- `gates_status.all_gates_passed == True`
- `not requires_infra` (don't conflict with the existing Docker-unavailable branch)
- The bootstrap is known-broken at the time of validation (read from worktree state)

This is the **belt-and-braces** layer for users who explicitly choose `bootstrap_failure_mode: warn` and accept that some tasks will run on a broken environment. It prevents the feedback-stall trapdoor from firing when Player did everything right and the failure is purely environmental.

This task is gated on:
- **TASK-ABSR-A1B2** — needs the bootstrap state to be reliably persisted (the smart-default work touches the same paths).
- **TASK-ABSR-7890** — the investigation must confirm that "Player gates passed" is a trustworthy signal (not systematically more permissive than Coach independent tests).

## Acceptance Criteria

- [ ] New helper `_bootstrap_likely_broken(self, task: Dict) -> bool` on `CoachValidator` that:
  - Reads `<worktree>/.guardkit/bootstrap_state.json` (path: `self.worktree_path / ".guardkit" / "bootstrap_state.json"`).
  - Returns True if the file exists and `success: false`.
  - Returns False if the file is missing, parse-fails, or reports `success: true` (conservative default — don't approve when state is unknown).
  - Has unit tests covering all three branches.
- [ ] New conditional-approval clause added at [`coach_validator.py:831-854`](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L831-L854):
  ```python
  or (
      failure_class == "infrastructure"
      and failure_confidence == "ambiguous"
      and gates_status.all_gates_passed
      and not requires_infra
      and self._bootstrap_likely_broken(task)
  )
  ```
- [ ] When this clause fires, the result must be tagged with a new flag (e.g. `environment_conditional_approval: True`) so the post-loop summary can label it differently from a clean approval.
- [ ] Logging at `WARNING` level when this clause fires:
  ```
  Conditional approval for {task_id}: environment-class infrastructure failure
  ({failure_classification}/{failure_confidence}) on a known-broken bootstrap;
  all Player gates passed. Marking approved with environment flag.
  ```
- [ ] **New tests**:
  - `test_env_conditional_approve_only_when_bootstrap_failed`
  - `test_env_conditional_approve_does_not_apply_when_bootstrap_succeeded`
  - `test_env_conditional_approve_does_not_apply_when_bootstrap_state_missing`
  - `test_env_conditional_approve_does_not_apply_when_failure_class_is_code`
  - `test_env_conditional_approve_does_not_apply_when_gates_failed`
  - `test_env_conditional_approve_does_not_apply_when_requires_infra_set`
  - `test_env_conditional_approve_marks_result_with_environment_flag`
- [ ] Replay the FEAT-J004-702C / TASK-J004-004 scenario (with mocked broken bootstrap) and assert that this clause fires and the task is approved instead of stalled.
- [ ] Documentation: update `docs/guides/autobuild-instrumentation-guide.md` to describe the new branch and when it fires.

## Implementation Notes

- The clause is **deliberately narrow**: requires the bootstrap to be observably broken. A real `ImportError` on a healthy bootstrap (e.g. Player imported a non-existent module) does NOT match — the bootstrap state is `success: true`, so the clause doesn't fire, and the existing feedback path runs as before.
- The helper should not raise — best-effort reading. Any exception path returns False (conservative).
- Coordinate with TASK-ABSR-C3D4 (environment_stall sub-type): when this branch fires, the stall never happens. When this branch doesn't fire (e.g. `bootstrap_failure_mode: block` was respected and the run aborted at preflight), neither does the stall. The two are complementary safety nets.

## Out of Scope

- Generalising to other failure classes (e.g. `code` failures on a broken bootstrap) — too aggressive.
- Removing the existing four conditional-approval clauses — this task is purely additive.
- Telemetry/metrics — file separately if needed.

## References

- Review: [TASK-REV-FA04 report](../../../.claude/reviews/TASK-REV-FA04-report.md) §F3, §R3, "Regression Analysis — R3"
- Existing branches: [coach_validator.py:831-854](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L831-L854)
- Bootstrap state path: `<worktree>/.guardkit/bootstrap_state.json` (written by [environment_bootstrap.py:1022-1048](../../../guardkit/orchestrator/environment_bootstrap.py#L1022-L1048))

## Implementation Summary

Added a fifth conditional-approval clause to `CoachValidator.validate` for environment-class ambiguous infrastructure failures (`ImportError` / `ModuleNotFoundError`) when the worktree's `.guardkit/bootstrap_state.json` reports `success: false`, all Player gates passed, and the task did not declare `requires_infrastructure`. The clause is gated by a new `_bootstrap_likely_broken(self, task)` helper whose conservative default (False on missing/unparseable/healthy state) prevents the branch from firing when bootstrap state is unknown. When the clause fires, the result is tagged with `environment_conditional_approval=True` (surfaced in `to_dict()`) and emits a `WARNING`-level log naming the failure classification and confidence. The post-loop summary in `autobuild.py` now branches on the new flag and prints "APPROVED with environment flag (known-broken bootstrap, independent tests skipped)" so reviewers can distinguish this from the existing Docker-unavailable conditional approval.

Approach: belt-and-braces layer paired with TASK-ABSR-A1B2's `bootstrap_failure_mode: block` smart default. When a user explicitly chooses `warn` mode and ships on a half-installed venv, this clause prevents the feedback-stall trapdoor (replayed by `test_replay_feat_j004_702c_environment_stall`) from firing on a purely environmental fault.

Tests: 13 new (5 helper, 7 named in the AC, 1 FEAT-J004-702C replay). Passed alongside 326 existing coach_validator tests with no regressions (339 total in 189s).

## Notes

Lessons learned:

- **Conservative defaults at predicate boundaries pay off.** `_bootstrap_likely_broken` returns False on every "unknown" path (missing file, parse error, non-dict payload, `success: True`). That single-branch test matrix made the AC's "does not apply when bootstrap state missing" requirement trivial to satisfy and naturally prevents the new clause from firing in any scenario the task author didn't explicitly authorize.
- **The `or X` factoring matters for testability.** Computing `environment_conditional_approval` as a separate boolean before OR-ing it into the existing `conditional_approval` chain (rather than inlining the new clause into the existing chain) lets the `to_dict()` payload surface the flag distinctly without re-deriving it. The post-loop summary in `autobuild.py` then needed only a `coach_report.get("environment_conditional_approval")` check — no extra plumbing.
- **Existing test data `_make_infra_result` from `TestInfrastructureFeedbackDetail` is the canonical pattern** for ambiguous-infra mocking: write a passing `task_work_results.json`, mock `run_independent_tests`, mock `_classify_test_failure` to return `("infrastructure", "ambiguous")`. Reusing this pattern across the 7 named tests + 1 replay made the new test file ~95% deterministic and 0% reliant on the real classifier's heuristics.

Architectural decisions:

- **Predicate helper signature accepts `task: Optional[Dict]` even though the task is unused** — for forward compatibility and parallelism with sibling helper `_is_psycopg2_asyncpg_mismatch`. Future task-frontmatter signals (e.g. an explicit `tolerate_broken_bootstrap: true` flag) can be wired in without breaking the call site.
- **The clause requires `not requires_infra`** to keep it disjoint from the existing high-confidence Docker-unavailable branch, even though the existing branch additionally requires `failure_confidence == "high"`. The redundant gate is intentional defence-in-depth: future evolution of `_classify_test_failure` shouldn't accidentally trigger both branches for the same failure.
- **Did NOT generalise to `failure_class == "code"` on a broken bootstrap**, even though that scenario can also be environment-driven (e.g. broken venv → wrong `sys.path` → spurious `AssertionError`s). The AC explicitly lists this as out of scope; over-broadening here would weaken the gate's guarantee that "Player did everything right" before approving.
