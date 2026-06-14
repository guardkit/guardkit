# Implementation Plan — TASK-AB-COACHRUNPARITY01

**Coach pytest-vs-smoke runtime-parity gap (+ smoke-gate-failure feedback loop)**

Complexity: 7/10 · task_type: fix · Phase 2.5 required (high blast radius)
Grounded against `main` @ `188f8497` on 2026-06-14.

## Problem (run-8, FEAT-9DDE)

Per-task Coach **approved** TASK-TSJ-001 on pytest (`from installer.core...`
resolves because pytest puts the worktree root on `sys.path`). The post-wave
**smoke gate** then ran the deliverable's real entry point
(`python3 installer/core/commands/lib/task_status_json.py`) which raised
`ModuleNotFoundError: No module named 'installer'` — a "passes tests but does
not run" defect. The smoke failure then **terminated the feature** (Wave 2
never ran) **with no feedback to the Player**.

Two orchestrator-side root causes:
1. The Coach has **no positive-evidence oracle** for "does the deliverable run".
2. The smoke gate is a **hard terminator**, not a feedback source
   ([feature_orchestrator.py:2212](../../../guardkit/orchestrator/feature_orchestrator.py#L2212) `break`).

## Scope decision (two arms)

| Arm | What | AC coverage | Blast | Recommendation |
|-----|------|-------------|-------|----------------|
| **(a) Bounded smoke-feedback-retry** | Feed smoke stderr back to the Player as turn-1 seed feedback; re-enter the wave for a bounded number of turns instead of terminating. | AC1, AC2, AC3, AC5 | High (wave-loop control flow) | **Implement now (primary).** Fully closes the run-8 reproducer. |
| **(b) Per-task Coach runtime-parity check** | Coach runs the deliverable's declared runtime entry point before approving, catching the defect one turn earlier (pre-approval). | AC4 | Medium (couples per-task Coach to feature smoke config; dependency-ordering caveat) | **Defer to fast-follow** (recommended) OR include now — operator's call at checkpoint. |

**Rationale for the split:** Arm (a) alone fixes the actual run-8 failure mode
(termination-without-feedback) and gives the Player the runtime error to fix.
Arm (b) is defence-in-depth that catches the same defect pre-approval, but it
couples the per-task Coach to feature-level smoke config and has a real caveat:
a single task's deliverable may not be runnable until peer tasks in the wave
finish, so a naive per-task smoke run can false-fail multi-task waves. That
caveat warrants its own design pass. Both arms honour
`feature-build-invariants.md` (never auto-merge; preserve worktrees) and
`absence-of-failure-is-not-success.md` (a non-runnable deliverable surfaces as
failed/absent runtime signal, never a silent pass).

---

## Arm (a) — detailed design (ready to implement)

### A1. `seed_feedback` thread (additive, default `None`, low coupling)

The Player's turn-1 `previous_feedback` becomes the carrier for the smoke error.

1. **Injection** — [autobuild.py:2369](../../../guardkit/orchestrator/autobuild.py#L2369):
   ```python
   # before
   previous_feedback = self._get_last_feedback() if self.resume else None
   # after
   previous_feedback = self._get_last_feedback() if self.resume else self._seed_feedback
   ```
   Verified safe: `_should_reset_perspective` fires only at turns [3, 5], so a
   turn-1 seed survives to the Player invocation at
   [autobuild.py:2438](../../../guardkit/orchestrator/autobuild.py#L2438).

2. **Store** — `AutoBuildOrchestrator.__init__`
   ([autobuild.py:1076-1114](../../../guardkit/orchestrator/autobuild.py#L1076)):
   add `seed_feedback: Optional[str] = None` after `evidence_repos`; assign
   `self._seed_feedback = seed_feedback` in the body. `_loop_phase` reads
   `self`; no signature change there.

3. **Thread up** (`feature_orchestrator.py`):
   - `_execute_task` ([2914](../../../guardkit/orchestrator/feature_orchestrator.py#L2914)):
     add `seed_feedback: Optional[str] = None`; pass `seed_feedback=seed_feedback`
     into `AutoBuildOrchestrator(...)` ([2989](../../../guardkit/orchestrator/feature_orchestrator.py#L2989)).
   - `_execute_wave_parallel` ([2225](../../../guardkit/orchestrator/feature_orchestrator.py#L2225)):
     add `seed_feedback: Optional[str] = None`; pass it in the
     `asyncio.to_thread(self._execute_task, ...)` dispatch
     ([2377-2386](../../../guardkit/orchestrator/feature_orchestrator.py#L2377)).
   - `_execute_wave` ([2659](../../../guardkit/orchestrator/feature_orchestrator.py#L2659)):
     add `seed_feedback: Optional[str] = None`; forward to `_execute_wave_parallel`.
   - Single-task dispatch ([3133](../../../guardkit/orchestrator/feature_orchestrator.py#L3133))
     unchanged — default `None`.

   Note: seed feedback is wave-scoped — on a re-run every task in the wave
   receives the same smoke feedback as turn-1 context. Acceptable for v1
   (the run-8 case is a single-task wave); documented as a known limitation.

### A2. Bounded retry in the wave loop

Replace the inline smoke block
([feature_orchestrator.py:2169-2221](../../../guardkit/orchestrator/feature_orchestrator.py#L2169))
with a call to a new helper that owns the bounded retry loop:

```python
if feature.smoke_gates is not None and should_fire_for_wave(feature.smoke_gates, wave_number):
    outcome = self._run_post_wave_smoke_gate(
        wave_number, task_ids, feature, worktree, wave_result
    )
    wave_results[-1] = outcome.final_wave_result   # REPLACE, never append
    if outcome.terminate:
        break
```

Helper (new method, returns a small `SmokeGatePhaseOutcome(terminate, final_wave_result)`):

```python
retries_remaining = self._smoke_gate_max_retries   # env GUARDKIT_SMOKE_GATE_MAX_RETRIES, default 1
while True:
    smoke_result = run_smoke_gate(feature.smoke_gates, cwd=Path(worktree.path),
                                  wave_number=wave_number, venv_python=self._bootstrap_venv_python)
    wave_result.smoke_gate_result = smoke_result

    if smoke_result.passed:
        if smoke_result.gate_not_wired:
            console.print(<existing soft-warn banner>)
        return SmokeGatePhaseOutcome(terminate=False, final_wave_result=wave_result)

    if smoke_result.gate_not_wired:                 # exit-5 hard fail: NO retry (config gap)
        console.print(<existing banner-A>)
        return SmokeGatePhaseOutcome(terminate=True, final_wave_result=wave_result)

    if retries_remaining <= 0:                       # retries exhausted: terminate (unchanged)
        console.print(<existing banner-B + stderr tail>)
        return SmokeGatePhaseOutcome(terminate=True, final_wave_result=wave_result)

    retries_remaining -= 1                            # RETRY: feed back + re-enter the wave
    smoke_feedback = self._build_smoke_feedback(smoke_result, feature)
    console.print(<retry banner: "Re-entering wave N with smoke feedback (retry X/Y)">)
    wave_result = self._execute_wave(wave_number, task_ids, feature, worktree,
                                     seed_feedback=smoke_feedback)
    # update wave-completion display for the re-run
    if not wave_result.all_succeeded and self.stop_on_failure:
        console.print(<stop_on_failure banner>)
        return SmokeGatePhaseOutcome(terminate=True, final_wave_result=wave_result)
    # loop: re-run the smoke gate against the re-executed wave
```

### A2b. Phase 2.5 review fixes (folded into the design)

Independent architectural review (66/100, approve-with-recommendations) found
three issues the first-pass design missed. All are now part of the design:

- **C1 (critical, state corruption — RESOLVED in design).** `_execute_wave`
  calls `_mark_wave_completed` at
  [2703-2704](../../../guardkit/orchestrator/feature_orchestrator.py#L2703),
  which **persists `completed_waves` to disk** the instant tasks pass — *before*
  the smoke gate runs. A smoke failure + retry (or a crash in that window)
  leaves the wave marked completed on disk though smoke never passed; a resume
  would skip it. (This is a latent bug in current code too; the retry makes it
  live.) **Fix:** move `_mark_wave_completed` OUT of `_execute_wave` and into
  the wave-loop call-site, gated on **task success AND smoke success** (or no
  smoke gate configured for the wave). `_execute_wave` has exactly one caller,
  so this is contained.
- **S2 (should-fix, duplicate telemetry — RESOLVED in design).** The
  `wave.completed` event ([2706-2727](../../../guardkit/orchestrator/feature_orchestrator.py#L2706))
  fires unconditionally inside `_execute_wave` with a stable
  `wave_id=f"wave-{wave_number}"`. A retry re-emits the same `wave_id` (TASK-INST-004
  consumers would dedupe or double-count). **Fix:** thread an `attempt: int = 0`
  into `_execute_wave`; suffix retries `wave-{n}-retry-{attempt}` so each
  execution is a distinct, observable event.
- **S1 (should-fix, retry UX — RESOLVED in design).** `_wave_display.start_wave`
  is emitted once per wave before `_execute_wave`; a re-run wouldn't re-emit it.
  **Fix:** the retry path prints a clearly-labelled re-run header banner (and,
  where a `_wave_display` exists, re-emits `start_wave`/`complete_wave` for the
  re-run so the live panel stays consistent).
- **N1 (nice-to-have).** Add an explicit test for `GUARDKIT_SMOKE_GATE_MAX_RETRIES=0`
  (degrades to today's immediate-terminate, no feedback).
- **N2 (traceability).** AC4 (arm b) is deferred → must be filed as a follow-up
  task and AC4 marked explicitly deferred (not left silently unchecked).

### A3. State reconciliation (AC3) — why this is correct (post-C1-fix)

- **No double-count.** We **replace** `wave_results[-1]`, never append. The
  classifier ([3373](../../../guardkit/orchestrator/feature_orchestrator.py#L3373))
  and the `tasks_completed`/`tasks_failed`/`total_turns` sums iterate
  `wave_results`; each wave appears once, holding its FINAL result.
- **`smoke_gate_failed` reflects the final attempt.** The classifier reads
  `wr.smoke_gate_result.passed` off the final `wave_result`; a retry that
  passes ⇒ `smoke_gate_failed=False` ⇒ `final_status=completed`; exhaustion ⇒
  `smoke_gate_failed=True` ⇒ `final_status=failed`.
- **`completed_waves` now smoke-gated (C1 fix).** `_mark_wave_completed`
  ([3711-3712](../../../guardkit/orchestrator/feature_orchestrator.py#L3711))
  is no longer called inside `_execute_wave`; the wave loop calls it once,
  after the smoke phase, gated on task-success AND smoke-success. The
  `if wave_number not in ...` guard keeps it idempotent. A wave whose tasks
  pass but whose smoke fails is **never** persisted as completed.
- **`current_wave`** is set to `wave_number` at the top of `_execute_wave`
  ([2690](../../../guardkit/orchestrator/feature_orchestrator.py#L2690)); a
  re-run keeps the same value.
- **`gate_not_wired` (exit-5) path unchanged** — no retry; terminates as today.
- **Known metrics nuance:** replacing the wave result drops the first
  (failed) attempt's `total_turns` from the feature total. Accepted — the
  re-run subsumes the first attempt and avoids double-counting; documented.

### A4. `_build_smoke_feedback` (Player-facing feedback)

Compose actionable feedback from `SmokeGateResult`
(`command`, `exit_code`, `timed_out`, `timeout`, `stderr`) framing it as a
runtime-parity failure ("passes tests but does not run") and including the
command + a stderr tail (last ~40 lines). This is the positive runtime signal
the Player needs to fix the real entry point.

### A5. Config

`FeatureOrchestrator.__init__`: `self._smoke_gate_max_retries =
int(os.environ.get("GUARDKIT_SMOKE_GATE_MAX_RETRIES", "1"))`. Default 1 keeps
the blast radius minimal (one feedback round); operators can raise it.

---

## Arm (b) — per-task Coach runtime-parity check (APPROVED for this task)

**Decision (Phase 2.8): implement both arms now.** Design grounded against the
LLM-Coach evidence pipeline (TASK-HMIG-008R). The per-task Coach exercises the
deliverable's declared runtime entry point before approving; a non-runnable
deliverable becomes a **ran-and-failed runtime signal** that deterministically
blocks approval — never a silent pass (`absence-of-failure-is-not-success.md`).

### Multi-task-wave caveat → `wave_size == 1` guard

A task's deliverable may not run standalone until peers in the same wave finish,
so a per-task smoke run would false-fail multi-task waves. **Guard:** the per-task
runtime-parity check runs ONLY when `wave_size == 1` (single-task wave — the
run-8 shape). Multi-task waves rely on the feature-level smoke gate + arm (a).
`CoachValidator` already carries `wave_size`
([coach_validator.py:1307](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L1307))
and `is_parallel`
([1345](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L1345)).

### B1. New evidence slice (follows the wiring-analysis precedent, §5 of `gather_evidence`)

- `coach_evidence.py`: new `@dataclass RuntimeParityResult`
  (`ran: bool`, `passed: bool`, `command: str`, `exit_code: Optional[int]`,
  `expected_exit: int`, `timed_out: bool`, `stderr_tail: str`,
  `skipped_reason: Optional[str]`) + a `runtime_parity: Optional[RuntimeParityResult]`
  field on `CoachEvidenceBundle`. Rendered into the Coach prompt alongside the
  other slices (so the LLM Coach sees it too).
- `coach_validator.py`: `smoke_command: Optional[str] = None` ctor param; new
  `gather_evidence` section (after §5 wiring,
  [~2851](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L2851)):
  when `self.smoke_command` and `wave_size == 1`, run the command in
  `self.worktree_path` (subprocess, `venv_python`-pinned, bounded timeout,
  expected exit 0), wrapped in try/except so a runner error never breaks
  gathering (→ `ran=False, skipped_reason="runner_error: ..."`). When skipped
  (no command / parallel wave) → `runtime_parity=None` (absent, not a pass).

### B2. Deterministic blocking guard (follows `_apply_spec_gap_absent_guard`)

`agent_invoker.py`: new `_apply_runtime_parity_guard(decision, evidence_bundle,
task_id, turn, coach_output_path)` called right after `_apply_spec_gap_absent_guard`
([2289](../../../guardkit/orchestrator/agent_invoker.py#L2289)). No-ops unless
`decision == "approve"` and `evidence_bundle.runtime_parity` is non-None with
`ran is True and passed is False`. On fire: override `approve`→`feedback`, prepend
a `must_fix` `runtime_parity` issue (command + exit + stderr tail framed as
"passes tests but does not run"), re-persist `coach_turn_N.json`, WARNING log.
Absent / skipped / ran-and-passed → no-op (absence-of-failure safety; an absent
runtime signal never blocks, a ran-and-failed one always does).

### B3. Threading `smoke_command` down

`feature.smoke_gates.command` → `_execute_task(..., smoke_command=...)` →
`AutoBuildOrchestrator(..., smoke_command=...)` (`self._smoke_command`) → the
`CoachValidator(...)` constructions on the gather-evidence path
([autobuild.py:5686](../../../guardkit/orchestrator/autobuild.py#L5686),
[5862](../../../guardkit/orchestrator/autobuild.py#L5862)). Only thread the
command when a smoke gate is configured; default `None` everywhere keeps every
existing caller unchanged. Pass `feature.smoke_gates.command` from `_execute_task`
unconditionally (the `wave_size==1` guard inside the Coach decides whether to run).

### Arm (b) tests
- (unit) `RuntimeParityResult` + bundle field; `gather_evidence` runs the smoke
  command for `wave_size==1`, skips (`runtime_parity=None`) for `wave_size>1`.
- (unit) `_apply_runtime_parity_guard`: ran+failed over an `approve` → `feedback`
  + must_fix issue + re-persist; ran+passed → no-op; absent/None → no-op;
  `feedback` verdict left untouched.
- (integration) the run-8 shape as a per-task case: Coach pytest passes but the
  smoke command raises `ModuleNotFoundError` → per-task Coach blocks pre-approval.

---

## Files touched (arm a)

| File | Arm | Change |
|------|-----|--------|
| `guardkit/orchestrator/autobuild.py` | a+b | `seed_feedback` + `smoke_command` params + `self._*`; injection at L2369; thread `smoke_command` into both `CoachValidator(...)` constructions (5686, 5862) |
| `guardkit/orchestrator/feature_orchestrator.py` | a+b | `seed_feedback`/`smoke_command` thread through `_execute_wave`/`_execute_wave_parallel`/`_execute_task`; new `_run_post_wave_smoke_gate` + `_build_smoke_feedback` + `SmokeGatePhaseOutcome`; `_smoke_gate_max_retries`; wave-loop swap; **C1** move `_mark_wave_completed` to smoke-gated call-site; **S2** `attempt`→unique retry `wave_id` |
| `guardkit/orchestrator/quality_gates/coach_evidence.py` | b | new `RuntimeParityResult` dataclass + `CoachEvidenceBundle.runtime_parity` field + prompt rendering |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | b | `smoke_command` ctor param; `gather_evidence` runtime-parity section (guarded `wave_size==1`) |
| `guardkit/orchestrator/agent_invoker.py` | b | `_apply_runtime_parity_guard` + call site after L2289 |

~2 source files. No new modules. Additive params (all default-safe).

## Test plan (Phase 4)

Extend `tests/integration/autobuild/test_smoke_gate_blocks_wave.py` and
`tests/unit/orchestrator/test_autobuild_smoke_placement.py`:

- (unit) `seed_feedback` reaches turn-1 `previous_feedback` (construct
  `AutoBuildOrchestrator(seed_feedback=...)`, mock `_execute_turn`, assert).
- (unit) `_build_smoke_feedback` includes command + stderr tail + parity framing.
- (integration) smoke fails once then passes on the re-run → wave re-enters →
  Wave 2 starts; `final_status=completed`.
- (integration) retries exhausted → `final_status=failed` + worktree preserved;
  never-auto-merge invariant holds.
- (integration) `stop_on_failure` on a re-run the Coach rejects → terminate.
- (integration) **run-8 regression pin**: Coach pytest passes but standalone
  `python3 <module>` raises `ModuleNotFoundError` → failure reaches the Player
  as feedback; feature does NOT terminate on the first smoke failure.
- (unit) `gate_not_wired` exit-5 still terminates without retry.
- (unit/state) `wave_results[-1]` replaced not appended → classifier counts the
  wave once; `completed_waves`/`current_wave` not corrupted.
- (unit/state, **C1**) wave tasks pass but smoke fails → `completed_waves` does
  NOT contain the wave on disk (not marked completed until smoke passes);
  after a passing retry it IS marked once.
- (unit, **S2**) a retry emits `wave.completed` with a distinct `wave_id`
  (`wave-{n}-retry-1`), never a duplicate of `wave-{n}`.
- (unit, **N1**) `GUARDKIT_SMOKE_GATE_MAX_RETRIES=0` → immediate terminate on
  smoke fail, no feedback injection (degrades to current behaviour).

## Risk & invariants

High blast radius (wave-loop control flow). Mitigations: bounded retry
(default 1); replace-not-append; idempotent `_mark_wave_completed`; `gate_not_wired`
path untouched; `stop_on_failure` honoured on re-runs. Invariants preserved:
never auto-merge, preserve worktree (`feature-build-invariants.md`); non-runnable
deliverable → failed/absent signal, not silent pass
(`absence-of-failure-is-not-success.md`); "passes tests but doesn't run" is the
exact `namespace-hygiene.md` shape this closes.

---

## Final status (2026-06-14) — IN_REVIEW

Both arms implemented. **Phase 5 code review: APPROVE-WITH-FIXES.** Core
invariants verified correct (bounded retry, absence-of-failure, complete
threading chain, C1 `_mark_wave_completed` move, FB-004 Coach read-only intact,
no stubs). Findings addressed:

- **Finding 2 (correctness):** `_gather_runtime_parity` hardcoded
  `expected_exit=0` → false-red for a feature declaring non-zero `expected_exit`.
  Fixed by threading `smoke_expected_exit` (feature.smoke_gates.expected_exit)
  through the same chain as `smoke_command`. Test:
  `test_respects_non_default_expected_exit`.
- **Finding 3 (coverage):** added `test_timeout_is_ran_and_failed`.
- **Finding 4 (coverage):** `test_smoke_gate_noop` now asserts
  `_mark_wave_completed` fires 3× (pins the C1 no-smoke-gate path).
- **Finding 5 (display, minor):** left as-is — the `↻` retry banner +
  `start_wave` disambiguate the two `complete_wave` calls into a coherent
  per-attempt narrative.

All 5 ACs met. 32 new/updated tests pass; broader regression sweep clean (657
passed; the only failures in the tree are the pre-existing
`test_coach_sdk_stream_resilience.py` cases that require the Claude Code CLI
binary, unrelated to this change). Task moved to `tasks/in_review/`.
