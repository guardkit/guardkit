---
id: TASK-AB-COACHRUNPARITY01
title: Coach approves on pytest while the smoke gate rejects a non-runnable deliverable — thread runtime parity + feed smoke-gate failure back to the Player
status: completed
task_type: fix
created: 2026-06-14T16:20:00Z
updated: 2026-06-14T19:45:00Z
completed: 2026-06-14T19:45:00Z
completed_location: tasks/completed/TASK-AB-COACHRUNPARITY01/
previous_state: in_review
state_transition_reason: "task-complete — both arms implemented, 32 new tests pass, code review APPROVE-WITH-FIXES (addressed)"
priority: high
complexity: 7
related: [TASK-FIX-BSEXTRAS01, TASK-FIX-COACHTESTTO, FEAT-9DDE]
implementation_mode: task-work
tags: [autobuild, coach, smoke-gate, runtime-parity, feedback-loop, phase-2.5, absence-of-failure, namespace-hygiene]
---

# Task: Coach pytest-vs-smoke runtime-parity gap (+ smoke-gate-failure feedback loop)

> **Phase 2.5 required.** This is an architecturally significant change to
> smoke-gate-failure control flow with high blast radius (runaway retry,
> `stop_on_failure` interaction, checkpoint/rollback, wave-state corruption).
> Design first; do not rush.

## Why this task exists

FEAT-9DDE **run 8** (2026-06-14): the per-task Coach **approved** TASK-TSJ-001
because its independent test passed (`pytest tests/unit/commands/test_task_status_json.py`,
2.6s). The feature's post-wave **smoke gate** then **failed** because the
producer doesn't run standalone:

```
smoke command (FEAT-9DDE.yaml):
  pytest tests/unit/commands -k task_status_json          # passes
  python3 installer/core/commands/lib/task_status_json.py --base-path . | python3 -m json.tool
                                                          # FAILED: ModuleNotFoundError: No module named 'installer'
                                                          # (and a datetime JSON-serialization crash)
```

`pytest` puts the worktree root on `sys.path`, so `from installer.core...`
resolves; the **standalone script invocation does not**. The Coach verified
via pytest only, so it never exercised the real runtime entry point — a
classic "passes tests but doesn't run" (see `namespace-hygiene.md`). Worse,
the smoke-gate failure **terminated the feature** (Wave 2 / DIRECTFG01 never
ran) with **no feedback to the Player**.

> The producer bug itself was hand-patched to unblock run 9 (dual-mode import
> + `json default=str`, commit on `feat9dde-run9-base`). THIS task is the
> orchestrator-side root cause: the Coach has no positive-evidence oracle for
> "does the deliverable actually run", and the smoke gate (which does) is a
> hard terminator instead of a feedback source.

## Root cause (grounded)

- Coach runs only pytest on task files: `coach_validator.py:3866-4117`
  (`run_independent_tests`), command from `_detect_test_command`
  (`coach_validator.py:5604-5688`). Never the deliverable entry point.
- The command-exec oracle (`verify_command_criteria` `coach_validator.py:4461`;
  `_execute_command_criteria` `autobuild.py:3903-3949`) runs only on the
  synthetic-report path (`autobuild.py:2984-2993`) — not for normal AC
  verification. TSJ-001's ACs named only pytest; the standalone run lived
  only in the smoke command (`FEAT-9DDE.yaml:46-58`), unseen by the Coach.
- **Smoke-gate failure terminates, no feedback:** `feature_orchestrator.py:2169-2221`;
  on not-passed (`:2179`) it prints a banner then `break` (`:2212`), exiting
  the wave-enumerate loop (`:2099-2101`). Classified `smoke_gate_failed`
  (`:3373-3376`), `final_status` forced `failed` (`:3383-3385`).

## Candidate fixes (from investigation)

- **(a) Feed back / re-open the wave (RECOMMENDED primary):** replace the
  `break` at `feature_orchestrator.py:2212` with a **bounded** re-invocation of
  the wave that injects the smoke-gate stderr as Player feedback, so the Player
  fixes runtime failures the Coach's pytest missed. Best adversarial-loop fit
  (failures → feedback → fix, not terminate). **High blast radius**: the wave
  loop (`:2099-2142`) has no retry state; must add a bounded retry budget and
  reconcile with `stop_on_failure` (`:2158-2162`), the classifier
  (`:3373-3422`), and checkpoint/rollback + `completed_waves`/`current_wave`.
- **(b) Smoke-command / runtime parity (interim, narrower):** thread the smoke
  command (`SmokeGates`, `feature_loader.py:321-393`) into the per-task
  `CoachValidator` and run the deliverable's real entry point **before**
  approval, reusing `verify_command_criteria` / `_execute_command_criteria`.
  Medium blast; couples per-task Coach to feature-level smoke config. Catches
  the defect pre-approval but doesn't fix the terminate-without-feedback flow.
- (c) Surface the smoke command into the Coach evidence bundle only — weakest.

**Recommendation:** primary = (a) bounded feedback-and-retry; pair with a
narrow (b) so the Coach catches non-runnable deliverables pre-approval. Both
honour `feature-build-invariants.md` (never auto-merge; preserve worktrees).

## Acceptance Criteria

- [x] A smoke-gate failure after a wave feeds the failure (stderr) back to the
      Player as feedback and re-enters the wave for a **bounded** number of
      additional turns, instead of terminating the feature outright.
      *(arm a: `_run_post_wave_smoke_gate` + `seed_feedback` thread;
      `test_smoke_failure_retries_then_passes`)*
- [x] The retry budget is bounded; exhaustion leaves `final_status=failed`
      with the worktree preserved (never auto-merge).
      *(`GUARDKIT_SMOKE_GATE_MAX_RETRIES`, default 1;
      `test_smoke_retries_exhausted_terminates`)*
- [x] Interaction with `stop_on_failure`, the smoke-gate classifier
      (`:3373-3422`), and `completed_waves`/`current_wave` is correct (no
      state corruption, no runaway retry). *(replace-not-append +
      C1 fix: `_mark_wave_completed` moved to smoke-gated call-site;
      `test_smoke_{pass,fail}_*mark_wave_completed`)*
- [x] (Parity arm) The Coach exercises the deliverable's declared runtime
      entry point (smoke command) before approving, so a "passes pytest but
      fails to run" deliverable is caught pre-approval, surfaced as
      absent/failed runtime signal (not a silent pass — `absence-of-failure-is-not-success.md`).
      *(arm b: `CoachValidator._gather_runtime_parity` +
      `AgentInvoker._apply_runtime_parity_guard`, single-task-wave guard;
      `test_runtime_parity.py`)*
- [x] Regression: a deliverable whose Coach pytest passes but whose standalone
      `python3 <module>` raises `ModuleNotFoundError` reaches the Player as
      feedback (reproduces run-8) and the feature does not terminate on the
      first smoke failure. *(`test_smoke_failure_retries_then_passes`
      asserts RUNTIME-PARITY feedback reaches the retry; arm b
      `test_runtime_entry_point_fails` + guard override)*

## Implementation outcome (2026-06-14)

**Both arms implemented** (Phase 2.8 human checkpoint decision). Phase 2.5
architectural review (66/100, approve-with-recommendations) caught a critical
state-corruption hazard (C1: `_mark_wave_completed` persisted `completed_waves`
before the smoke gate ran → resume could skip an unverified wave) + two
should-fixes (S2 duplicate telemetry `wave_id`; S1 retry display), all folded
in. Phase 5 code review (APPROVE-WITH-FIXES) found the per-task parity check
hardcoded `expected_exit=0`; fixed by threading `smoke_expected_exit` so it
agrees with the feature's configured gate.

**Files:** `feature_orchestrator.py` (bounded retry + C1/S2 + threading),
`autobuild.py` (`seed_feedback`/`smoke_command`/`smoke_expected_exit` thread +
injection), `coach_evidence.py` (`RuntimeParityResult` + bundle field),
`coach_validator.py` (`_gather_runtime_parity`), `agent_invoker.py`
(`_apply_runtime_parity_guard`). **Tests:** 32 new/updated across
`test_smoke_feedback_retry.py`, `test_runtime_parity.py`,
`test_smoke_gate_blocks_wave.py`, `test_autobuild_smoke_placement.py`,
`test_smoke_gate_noop.py`. Full plan + review trail:
`docs/state/TASK-AB-COACHRUNPARITY01/implementation_plan.md`.

## Test plan
Extend `tests/integration/autobuild/test_smoke_gate_blocks_wave.py` (~85, ~155)
and `tests/unit/orchestrator/test_autobuild_smoke_placement.py`. Cases: smoke
fails once then passes after a fix turn → wave re-enters → Wave 2 starts; retry
budget exhausted → `failed` + worktree preserved; never-auto-merge invariant;
the run-8 regression-pin (Coach pytest passes, standalone module raises
ModuleNotFoundError → failure reaches Player). Reuse `make_wave_result` /
`SmokeGateResult` fixtures.

## Risk
High. Re-entry risks runaway retry; interactions with `stop_on_failure`
(`:2158-2162`), checkpoint/rollback, classifier mis-fire (`:3373-3422`), and
wave-state corruption. Rules: `absence-of-failure-is-not-success.md`,
`evidence-boundary-narrower-than-write-surface.md`, `namespace-hygiene.md`
(tests-pass/production-fails), `feature-build-invariants.md`.

## Implementation design (derived 2026-06-14, ready to implement)

The seed-feedback injection point is clean — this is a low-coupling, additive
(default-`None`) thread plus one bounded-retry control-flow change:

1. **Injection point** — `autobuild.py::_loop_phase` line 2369:
   `previous_feedback = self._get_last_feedback() if self.resume else None`.
   Change the `else` branch to `else self._seed_feedback`. That makes the
   Player's **turn-1** `previous_feedback` carry the smoke error.
2. **Store it** — `AutoBuildOrchestrator.__init__` (params end ~line 1113,
   after `evidence_repos`): add `seed_feedback: Optional[str] = None`; assign
   `self._seed_feedback = seed_feedback` in the body. `_loop_phase` is called
   once (line 1590); no signature change needed there since it reads `self`.
3. **Thread up**:
   - `feature_orchestrator.py::_execute_task` (def ~2914): add
     `seed_feedback: Optional[str] = None`; pass `seed_feedback=seed_feedback`
     into `AutoBuildOrchestrator(...)` (construction ~2989).
   - `_execute_wave` (def ~2659) + its dispatch
     (`_execute_wave_parallel` / sequential → `_execute_task`): thread the
     same optional param through to `_execute_task`.
4. **Bounded retry** — wave loop (`feature_orchestrator.py:2169-2212`): wrap
   `run_smoke_gate` in a loop bounded by `self._smoke_gate_max_retries`
   (new, env `GUARDKIT_SMOKE_GATE_MAX_RETRIES`, default 1). On a real
   (non-`gate_not_wired`) failure with retries remaining:
   `smoke_feedback = _build_smoke_feedback(smoke_result)` (the banner reason +
   stderr tail); `wave_result = self._execute_wave(wave_number, task_ids,
   feature, worktree, seed_feedback=smoke_feedback)`; **replace** the appended
   result (`wave_results[-1] = wave_result`, do NOT append a duplicate);
   re-check `wave_result.all_succeeded` + `stop_on_failure` before re-running
   the gate; `continue`. On retries exhausted: the existing banner + `break`
   (terminate, worktree preserved — unchanged).
5. **State reconciliation**: ensure `completed_waves`/`current_wave` (classifier
   `:3373-3422`) reflect the FINAL wave_result; re-running a wave must not
   double-count. The `gate_not_wired` (exit-5) path is unchanged (no retry).
6. **Invariants**: never-auto-merge, preserve-worktree (`feature-build-invariants.md`)
   hold unchanged; exhaustion still ends `failed`.

**Test matrix** (unit + integration): (a) seed_feedback reaches turn-1
`previous_feedback` (unit, construct orchestrator with seed_feedback, mock
`_execute_turn`, assert); (b) smoke fails once then passes after the re-run →
wave re-enters → Wave 2 starts (`test_smoke_gate_blocks_wave.py`); (c) retries
exhausted → `final_status=failed` + worktree preserved; (d) `stop_on_failure`
interaction on a re-run that the Coach rejects; (e) the run-8 regression pin
(Coach pytest passes, standalone module raises ModuleNotFoundError → failure
reaches the Player as feedback, feature does not terminate on first smoke
failure); (f) `gate_not_wired` exit-5 still terminates without retry.

## Evidence / references
- Run-8 log + evidence: `docs/retro/run8-evidence/` (approved turn 2; smoke
  ModuleNotFoundError; Wave 2 never started).
- Investigation (this session): structured root-cause + fix design,
  high-confidence, `implement_or_file = file-task-architecturally-significant`.
- Producer hand-patch that unblocked run 9: `feat9dde-run9-base` (dual-mode
  import + `json default=str`).
