---
id: TASK-FIX-SPECHANG
title: test-orchestrator specialist consumes full SDK timeout polling backgrounded Bash on multi-turn runs
task_type: bug-fix
status: completed
created: 2026-06-03T20:25:00Z
updated: 2026-06-03T21:15:00Z
completed: 2026-06-03T21:15:00Z
completed_location: tasks/completed/2026-06/
previous_state: in_progress
state_transition_reason: "Implementation landed + unit-tested; falsifier (AC-004/AC-005) deferred to next canary batch"
priority: high
complexity: 3
effort_hours: 3
parent_review: TASK-REV-HM09
parent_task: TASK-HMIG-009A
parent_feature: autobuild-harness-migration
deadline: 2026-06-15
related_tasks:
  - TASK-HMIG-009A   # AC-003 batch surfaced this; not a blocker for AC-001D but expensive
  - TASK-HMIG-010    # Cutover
tags:
  - bug-fix
  - autobuild
  - specialist-runtime
  - sdk-harness
  - batch-finding
falsifier: "After fix: test-orchestrator specialist completes (success or self-terminated) in <600s in a canary batch rep where pytest is launched with run_in_background=true, instead of consuming the full 2340s SDK timeout. Verified by re-running TASK-HMIG-009A AC-003 with the runner's default --max-turns 5 and observing test-orchestrator wall-clock <600s on at least 4 of 6 SDK reps."
---

# Task: test-orchestrator specialist polls backgrounded Bash until SDK timeout

## Surfaced by TASK-HMIG-009A AC-003 batch rep 1 (2026-06-03 SDK)

Per [`docs/reviews/autobuild-migration/long-run-1.md`](../../../docs/reviews/autobuild-migration/long-run-1.md) and rep 1's stderr.log (159min total wall-clock, 3 turns to `unrecoverable_stall`):

- **test-orchestrator specialist hit the 2340s SDK timeout on every turn** (lines 123/179/231/467/956 of long-run-1.md — `SDKTimeoutError: Agent invocation exceeded 2340s timeout`).
- **Specialist contributed 115 min of the 159 min total** (3 turns × 38min each); only ~44 min was actual Player + Coach work.
- **Specialist was NOT genuinely hung** — heartbeats continued, tool blocks fired (`Bash run_in_background=true`, `TaskOutput`). Pattern: the specialist launches pytest in background via Claude Code's `Bash run_in_background=true` then polls via `TaskOutput` waiting for completion. The polling continues until the SDK timeout fires.

This is consistent with — but distinct from — the F6 honesty-failure pattern that caused the `unrecoverable_stall`. Even if the Player had perfect honesty, this specialist behaviour would still burn ~38 min per turn.

## Why this didn't bite in AC-001C / AC-001D run 6 (single-turn smokes)

Both smokes used `--max-turns 2` and the Coach approved on turn 1 — so the specialist was only invoked **once**, and in those runs it completed in 150s (AC-001C) and 120s (AC-001D run 6). The pathological polling-until-timeout behaviour was masked by either:

1. **Faster pytest completion** in the smokes (smaller worktree state, fewer files to test against), OR
2. **Different LLM decision-making** in the smokes (specialist chose to read results inline rather than poll-then-wait), OR
3. **Both** — single-turn shape never accumulated enough context-pollution to push the specialist into the polling loop

In the batch (`--max-turns 5`), each turn after Coach feedback gives the specialist more files to test, larger output, and apparently a stronger tendency to use the `Bash run_in_background=true` + `TaskOutput` polling pattern. The polling cap is the SDK timeout — there's no specialist-level guard.

## Acceptance Criteria

- [x] **AC-001** — Identify the test-orchestrator specialist's prompt + tool-surface in [`installer/core/agents/`](../../../installer/core/agents/) (and/or wherever the specialist's instructions live). Confirm whether the prompt advises the specialist to use `run_in_background=true` + `TaskOutput` polling, or whether it's an LLM-chosen pattern.
  - Agent definition `installer/core/agents/test-orchestrator.md` shows synchronous pytest examples; nothing instructs the specialist to use `run_in_background=true` or `TaskOutput`.
  - Focused prompt builder `_build_test_orchestrator_prompt` in `guardkit/orchestrator/specialist_invocations.py:356` says "run the test suite" but doesn't constrain how.
  - Runner `invoke_test_orchestrator` (same file, line 617) passes `allowed_tools=["Read", "Write", "Bash", "Search"]`. The SDK exposes `Bash.run_in_background` as a parameter of the `Bash` tool (not a separate tool the allow-list could deny), and `TaskOutput` shows up as callable even though it isn't in the allow-list — observed in `docs/reviews/autobuild-migration/long-run-1.md` line 78: `ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']`.
  - Conclusion: the polling-until-timeout behaviour is **LLM-chosen**, not prompted. Neither the agent file nor the focused prompt is causing it.
- [x] **AC-002** — Decide between three fix shapes (pick whichever is smallest):
  - **(a)** Specialist-prompt change: instruct test-orchestrator to use synchronous `Bash` (no `run_in_background`) for pytest invocations, OR cap polling iterations.
  - **(b)** Orchestrator-side specialist-timeout cap: introduce a per-specialist timeout (e.g. 600s for test-orchestrator) separate from the SDK harness timeout (2340s). When specialist exceeds the cap, terminate gracefully and surface the partial result via `validation=violation` (same as today's hard timeout, just faster). ← **CHOSEN**
  - **(c)** Specialist-level stall detection: count consecutive `TaskOutput` polls returning the same state; after N (e.g. 10) consecutive identical polls, force the specialist to either read inline or give up.
  - Chose **(b)** because it gives a deterministic guarantee (the falsifier `<600s` always holds) without depending on LLM compliance. (a) is cheaper to write but has a known reliability gap (LLM may ignore "do not use X" instructions). (c) is out of proportion for a complexity-3 fix.
- [x] **AC-003** — Implement the chosen fix.
  - `guardkit/orchestrator/specialist_invocations.py`:
    - Added module constant `_TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS = 600` with the TASK-HMIG-009A AC-003 rep 1 incident reference.
    - `invoke_test_orchestrator` now computes `capped_sdk_timeout = min(sdk_timeout, _TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS)` and forwards that to `run_specialist`. Logs an INFO line when the cap fires so operators can correlate fast-failed test-orchestrator turns with the cap.
    - When the cap forces the SDK timeout, the existing `run_specialist` exception path already converts it into `status="failed"` with the timeout error message, and `invoke_test_orchestrator` already writes a failed `phase_4` block (covered by `test_invoke_test_orchestrator_timeout_writes_failed_block_with_timeout_error`). No additional plumbing needed.
  - `tests/unit/orchestrator/test_specialist_invocations.py`:
    - `test_invoke_test_orchestrator_caps_sdk_timeout_above_ceiling` — caller `sdk_timeout=2340` produces `_invoke_with_role`-observed timeout of `600`.
    - `test_invoke_test_orchestrator_passes_smaller_sdk_timeout_through` — caller `sdk_timeout=300` is preserved (cap is a no-op below the ceiling).
  - All 17 tests in the file pass (15 pre-existing + 2 new). Pre-existing 7 failures in `tests/orchestrator/test_specialist_observability.py` and `tests/integration/test_autobuild_phase_4_5_orchestration.py` are unrelated environmental issues (`asyncio.timeout` requires Python 3.11+; confirmed present on `main` without this change via `git stash` baseline).
- [ ] **AC-004** — Regression test: rerun TASK-HMIG-009A AC-003 batch with `--max-turns 5` (the default). Observe test-orchestrator wall-clock on each SDK rep. Falsifier passes if 4-of-6 SDK reps show test-orchestrator <600s.
  - **Verification deferred to a batch rerun.** This implementation cannot complete a multi-hour canary batch inline; requires operator to run `python scripts/canary_validation_runner.py --variant 009a` and inspect `.guardkit/autobuild/TASK-HMIG-009A-canary/sdk/*/run_*/stderr.log` for the new "test-orchestrator sdk_timeout capped from … to 600s" log line and the resulting `<600s` test-orchestrator wall-clock per turn.
- [ ] **AC-005** — Verify LangGraph reps still complete fast (AC-001D run 6 had test-orchestrator at ~120s); no regression.
  - **Verification deferred to a batch rerun.** Cap of 600s is well above the observed ~120s LangGraph wall-clock, so no regression is expected; needs the same batch run as AC-004 to confirm empirically.

## Out of scope

- **F6 honesty-failure mitigation** — separate concern; not addressed by this task. Even with this fix, multi-turn iteration may still trigger honesty collapse and unrecoverable_stall.
- **AC-001D regression** — single-turn shape already works (run 6 PASSED). This fix is for batch reps with `--max-turns > 1`.
- **Adding `--no-checkpoints` passthrough to canary_validation_runner.py** — separate small task if needed.

## Why this matters for the cutover

If the canary batch uses `--max-turns 5`, each SDK rep that doesn't approve on turn 1 will consume ~3h instead of ~30min. 12 reps × ~2h average = ~24h vs planned ~10h. The fix is needed before the next batch attempt, OR the batch must be run with `--max-turns 2` (which avoids the multi-turn invocation pattern entirely).

## References

- **Batch log**: [`docs/reviews/autobuild-migration/long-run-1.md`](../../../docs/reviews/autobuild-migration/long-run-1.md)
- **Rep 1 preserved stderr**: [`.guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_1/stderr.log`](../../../.guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_1/stderr.log) (263KB)
- **Successful single-turn smokes** (proof the specialist works fast when not polling):
  - AC-001C SDK 2026-06-02: test-orchestrator ~150s
  - AC-001D run 6 LangGraph 2026-06-03: test-orchestrator ~120s
- **Original F7 finding** (stall-detection guard works): `docs/state/TASK-REV-HMIG/canary-analysis.md` §3.F7
- **Specialist invocation code path**: [`guardkit/orchestrator/specialist_invocations.py`](../../../guardkit/orchestrator/specialist_invocations.py)

## Implementation Summary

Chose AC-002 option **(b)**: per-specialist sdk_timeout ceiling for the Phase 4 test-orchestrator. The cap is a hard orchestrator-side ceiling that converts the SDK timeout into a graceful specialist failure at the 10-minute mark instead of letting the LLM's `Bash run_in_background=true` + `TaskOutput` polling pattern consume the full Player/Coach budget (2340s on the canary batch).

**Code changes**:
- `guardkit/orchestrator/specialist_invocations.py`: added module constant `_TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS = 600` and a `min(sdk_timeout, cap)` call inside `invoke_test_orchestrator`, plus an INFO log when the cap fires so operators can correlate fast-failed Phase 4 turns with the cap.
- `tests/unit/orchestrator/test_specialist_invocations.py`: two regression tests (caps at 2340 → 600; passes 300 through unchanged). All 17 tests in the file pass.

**Approach rationale**: the polling-until-timeout behaviour was confirmed in AC-001 to be LLM-chosen (not prompted), so a prompt-only fix (option a) had a known reliability gap. Stall detection (option c) was disproportionate for a complexity-3 fix. Option (b) gives a deterministic falsifier guarantee without depending on LLM compliance.

**Behaviour when cap fires**: `run_specialist`'s existing exception path converts the SDK timeout into `status="failed"`, `invoke_test_orchestrator` writes the failed `phase_4` block (already covered by `test_invoke_test_orchestrator_timeout_writes_failed_block_with_timeout_error`), and the autobuild turn loop sees a fast-failed Phase 4 instead of a 2340s burn. Coach will reject the turn with a failed test-orchestrator signal — the correct shape because the Player needs to know pytest didn't complete cleanly. Suites that legitimately need >600s should be decomposed at the task level, not papered over here.

## Completion Notes

**Status: COMPLETED with deferred verification.** Operator (`rich@appmilla.com`, 2026-06-03) chose to complete despite AC-004/AC-005 being unverified.

- AC-001 / AC-002 / AC-003: ✅ done inline (see AC checkboxes above).
- AC-004 (canary batch falsifier, `<600s` on ≥4-of-6 SDK reps) — **not run inline.** Cap is deterministic so the falsifier is structurally guaranteed (any caller-supplied `sdk_timeout > 600` is forced to 600 before `run_specialist`), but empirical confirmation requires `python scripts/canary_validation_runner.py --variant 009a` and inspection of the per-rep stderr.log for the new `test-orchestrator sdk_timeout capped from … to 600s` log line.
- AC-005 (LangGraph no-regression at ~120s) — **not run inline.** Cap of 600s is well above the observed ~120s LangGraph wall-clock, so no regression is structurally possible; needs the same batch as AC-004 to confirm empirically.

If the next canary batch surfaces issues that this cap-based fix doesn't address (e.g. the specialist still wastes most of its 600s budget), the natural escalation is to combine with option (a) — a prompt instruction telling the specialist NOT to use `run_in_background=true`. That's a follow-up task, not a reopening of this one.

**Pre-existing test failures**: 7 failures in `tests/orchestrator/test_specialist_observability.py` and `tests/integration/test_autobuild_phase_4_5_orchestration.py` exist on `main` without this change (`asyncio.timeout` requires Python 3.11+); confirmed via `git stash` baseline. Out of scope.
