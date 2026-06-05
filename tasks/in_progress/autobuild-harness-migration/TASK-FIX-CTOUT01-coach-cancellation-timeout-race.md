---
id: TASK-FIX-CTOUT01
title: Coach cancellation race — task-level timeout fires but Coach continues to approval
status: in_progress
task_type: bug
created: 2026-06-05T09:00:00Z
updated: 2026-06-05T12:30:00Z
previous_state: backlog
state_transition_reason: "task-work invocation 2026-06-05"
priority: high
complexity: 5
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: task-work
intensity: standard
effort_hours: 3
blocks:
  - TASK-HMIG-010
falsifier: "After landing, when feature_orchestrator fires task_timeout cancellation during an in-flight Coach invocation, the Coach invocation terminates within 30s of the cancellation event. The outer orchestrator's task verdict (timeout/failed) and the inner orchestrator's task verdict (approved/feedback/etc.) agree. A regression test exercises the cancellation-during-Coach case and asserts no timeout-then-approved divergence in the resulting bookkeeping."
tags:
  - autobuild
  - bug
  - orchestrator
  - cancellation
  - bookkeeping
---

# Task: Cancellation race — task-level timeout fires but Coach continues to approval anyway

## Description

Surfaced by TASK-HMIG-010 run 3 (2026-06-05, see [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md) lines 1555–1601). When `feature_orchestrator` fires task-level timeout cancellation during an in-flight Coach invocation for TASK-FIX-GD02:

1. The timeout fires correctly (`task_timeout=3000s expired`)
2. A cancellation event is detected (`Cancellation event detected during coach invocation`, line 1559 — references `TASK-FIX-ASPF-004`'s existing cancellation handling)
3. **But the Coach invocation continues running** — 5+ additional `POST /v1/responses` calls succeed after the cancellation event (lines 1560–1564)
4. Coach reaches APPROVED state ~48 seconds after the cancellation fired (line 1565: `Coach approved - ready for human review`)
5. Outer feature_orchestrator records `TASK-FIX-GD02 timed out / FAILED`
6. Inner autobuild orchestrator records `decision=approved`
7. Final bookkeeping shows the divergence:
   - Wave 2 summary: `Wave 2 ✗ FAILED: 1 passed, 1 failed`
   - Inner summary table: `Status: APPROVED ... Coach approved implementation after 2 turn(s)`

## Why this matters for AC-008

TASK-HMIG-010 AC-008 requires computing first-pass-success rate + non-recoverable failure count to decide the cutover verdict. With GD02 in ambiguous state:

- If counted as failure: 2/3 = 67% first-pass success, 1 non-recoverable → **HALT cutover**
- If counted as success (Coach DID approve): 3/3 = 100% (eventually), 0 non-recoverable → **PROCEED with cutover**

The right answer here depends on what GD02's *true* verdict is. Right now we can't compute it because the orchestrator is contradicting itself. **This blocks accurate AC-008 evaluation**, hence TASK-HMIG-010 is re-blocked on this fix specifically.

## Symptom

Run-3 log lines 1555–1601 (relevant excerpt):

```
07:45:26  WARNING: TIMEOUT (feature-level): task_timeout=3000s expired for TASK-FIX-GD02
07:45:26  WARNING: Task TASK-FIX-GD02 timed out after 3000s (50 min)
07:45:26  ⏱ TASK-FIX-GD02: Task TASK-FIX-GD02 timed out after 3000s (50 min)
07:45:26  TASK-FIX-ASPF-004: Cancellation event detected during coach invocation, terminating SDK subprocess
07:45:30+ INFO:httpx:HTTP Request: POST .../v1/responses "HTTP/1.1 200 OK"  (×5)
07:46:14  ✓ Coach approved - ready for human review
07:46:14  Completed turn 2: success - Coach approved - ready for human review
          [... AutoBuild Summary (APPROVED) ...]
          Wave 2 ✗ FAILED: 1 passed, 1 failed         ← outer says failed
          Status: APPROVED ... Coach approved          ← inner says approved
```

## Root cause hypothesis

The `TASK-FIX-ASPF-004: Cancellation event detected ... terminating SDK subprocess` log line suggests the **cancellation flag is set but the in-flight subprocess isn't actually terminated** — or the LangGraph harness path doesn't honour the same cancellation contract that the SDK harness path was wired for. Specifically:

- ASPF-004 likely terminated the SDK transport's subprocess
- Under LangGraph, there's no subprocess to terminate — the in-flight call is an `async agent.ainvoke(...)` running on the orchestrator's event loop
- The cancellation handler may not propagate to LangGraph's pregel loop or the in-flight `langchain_anthropic._async_client.messages.create(...)` HTTP request

If true, this is a **harness-asymmetry bug**: the cancellation contract was honoured by the SDK harness (process-level termination) but not by the LangGraph harness (which needs `asyncio.CancelledError` propagation instead).

Suggested investigation steps:

1. Locate ASPF-004's cancellation handling — confirm it's SDK-subprocess-specific
2. Check whether `LangGraphHarness.invoke()` accepts and respects an `asyncio.CancelledError` from its caller
3. Inspect `feature_orchestrator`'s timeout-fires code path — what does it actually do beyond logging? Does it cancel the in-flight asyncio Task?

## Acceptance Criteria

- [ ] AC-001: Reproduce the bug deterministically (mock LangGraph harness with a slow-to-complete invoke, fire task_timeout while in flight). Assert that current behaviour shows timeout-then-approve divergence.
- [ ] AC-002: Implement cancellation propagation under the LangGraph harness path. Specifically: when `feature_orchestrator`'s task_timeout fires, the in-flight `harness.invoke(...)` async iteration must terminate within a bounded window (≤30s).
- [ ] AC-003: Outer cancellation wins UNLESS inner Coach completes within `LATE_APPROVAL_GRACE_S` of timer fire, in which case the inner approval is honoured as `approved_late` with `success=True`. This preserves the existing `LATE_APPROVAL_GRACE_S` design (TASK-ATR-003) while ensuring under-grace approvals are no longer silently lost. Revision rationale: the original "outer always wins" wording (filed 2026-06-05 AM) was naïvely contradicting the load-bearing `LATE_APPROVAL_GRACE_S` reconciliation path that was designed for precisely the GD02 scenario. Investigation under TASK-FIX-CTOUT01 confirmed the actual bookkeeping divergence was caused by a silent-exception-swallow in `_check_late_approval` (`feature_orchestrator.py:3237`), not by the cancellation contract being mis-designed.
- [ ] AC-004: Regression test exercises the cancellation-during-Coach case under both SDK and LangGraph harnesses; both must produce consistent bookkeeping.
- [ ] AC-005: Re-run TASK-HMIG-010 (run 4) — GD02's verdict is unambiguous (either it completes within 3000s, OR it cleanly times out without a phantom-approval).
- [ ] AC-006: Document the cancellation contract in `guardkitfactory.harness.langgraph_harness` docstring or a `.claude/rules/` rule — the contract is: "an in-flight `invoke(...)` MUST honour asyncio cancellation within 30s, even if a mid-call LLM response is pending."

## Implementation Notes

- The TASK-FIX-ASPF-004 reference in the log suggests there's prior cancellation work to consult. Investigate that task's commits as the starting point.
- A non-invasive workaround that might be useful for run 4 evidence-gathering: bump `--task-timeout 3000s → 4500s` so GD02 has more slack. But this doesn't fix the underlying race; it just makes it less likely to surface.
- Consider whether the `--task-timeout` semantics need to change (e.g., split into a "soft" timeout that sends a hint and a "hard" timeout that force-terminates).

## References

- Run-3 log: [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md) lines 1555–1601
- ASPF-004 precedent: search `TASK-FIX-ASPF-004` for prior cancellation handling
- Blocked task: [TASK-HMIG-010](../../in_progress/TASK-HMIG-010-full-feature-autobuild-validation.md) — AC-008 verdict cannot be computed until GD02's outcome is unambiguous
- Sibling tasks: [TASK-FIX-LGFM3](TASK-FIX-LGFM3-coach-test-role-model-threading.md) (F12), [TASK-FIX-FALK01](TASK-FIX-FALK01-graphiti-falkordb-teardown-race.md) (F16)

## Notes

This is the most consequential of the run-3 findings because it directly affects the AC-008 cutover-verdict computation. Without a clean cancellation contract, every run that has a complexity-6 task at the edge of the substrate's iteration speed will produce ambiguous bookkeeping — and the cutover decision becomes politicised between "did the substrate work?" (Coach approved) and "did the orchestrator's budget hold?" (timeout fired).

Recommended sequencing: fix this BEFORE landing the LGFM3 (F12) fix — LGFM3 is a soft-fail anyway. CTOUT01's resolution is what gates the AC-008 verdict.

## AC-001 evidence (2026-06-05 PM)

Investigation under TASK-FIX-CTOUT01 found that the four-layer cancellation contract had a silent-bookkeeping failure mode that hadn't been seen because every exception in `_check_late_approval` was demoted to DEBUG. The reproducer test
`tests/unit/test_feature_orchestrator.py::TestLateApprovalReconciliation::test_layer4_silent_swallow_invisible_on_current_main`
runs RED on current `main` (no WARNING in caplog when `_latest_coach_turn_path` raises) and GREEN after the line-3237 promotion to WARNING + `exc_info`. The companion non-spam regression
`test_check_late_approval_does_not_warn_when_decision_key_missing`
asserts the upgrade does NOT spam logs on the legitimate "decision key absent" code path (no exception → no WARNING).

**Hypothesis ranking (AC-001 outcome):**
- **Hypothesis (b) "silent exception swallow"** — empirically confirmed by the reproducer test running RED on `main`. The fix at `feature_orchestrator.py:3237` lands in the same commit as the reproducer.
- **Hypothesis (a) "wrong directory under worktree-backed layout"** — empirically NOT reached by the reproducer. The planning agent's analysis (saved at `docs/state/TASK-FIX-CTOUT01/implementation_plan.md` §0) confirmed the candidate-dirs walk is structurally correct for the run-3 FEAT-AOF worktree layout. Conditional Step 3 of the plan (path-canonicalisation fix) is therefore SKIPPED.
- **Open follow-up:** the canary-worktree nested layout (`docs/state/TASK-FIX-CTOUT01/implementation_plan.md` §0 point 3) is acknowledged out-of-scope for CTOUT01 — file a separate task if it ever surfaces in production.

**Implication for AC-005 (re-run TASK-HMIG-010):** without the line-3237 promotion, run-3's silent swallow would have invisibly hidden any future late-approval failures. Run-4 should now produce loud WARNING-level diagnostics if Layer 4 ever fails to reclassify, making AC-008's cutover-verdict computation observable.

## Split decision

The original plan (`docs/state/TASK-FIX-CTOUT01/implementation_plan.md` §4) considered splitting into CTOUT01-a (Layer 4 fix only) and CTOUT01-b (`harness.cancel()` abstraction, deferrable). With hypothesis (a) empirically ruled out, CTOUT01-a's distinguishing fix (path canonicalisation) does not need to land — the Layer 4 fix collapses to a single-line log-level promotion, too small to be its own task. **Verdict: CTOUT01 lands as one task,** bundling the silent-swallow upgrade with the harness `cancel()` abstraction work.
