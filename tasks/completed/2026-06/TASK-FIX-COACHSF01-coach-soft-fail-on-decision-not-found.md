---
id: TASK-FIX-COACHSF01
title: Wire synthetic-feedback safety net for "Coach decision not found" verdict-emission failures
status: completed
task_type: bug
created: 2026-06-05T17:30:00Z
updated: 2026-06-05T18:45:00Z
completed: 2026-06-05T18:45:00Z
completed_location: tasks/completed/2026-06/
previous_state: in_review
state_transition_reason: "Completion: AC-001/002/003/004 satisfied, 5/5 regression tests pass. AC-005 (live HMIG-010 run 5 smoke) deferred to TASK-HMIG-010 — now unblocked."
priority: critical
complexity: 3
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: task-work
intensity: standard
effort_hours: 1.5
blocks:
  - TASK-HMIG-010
falsifier: "After landing, run 5 of `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse` under GUARDKIT_HARNESS=langgraph: if Coach LLM completes its invocation but does NOT write coach_turn_N.json (qwen36-workhorse F2-at-Coach-level substrate behaviour), `_invoke_coach_primary` MUST emit a synthetic feedback decision (writes coach_turn_N.json with rationale naming the failure mode) and return success=True. The Player gets to retry on turn 2 with Coach's feedback. Regression test exercises invoke_coach returning success=False with `Coach decision not found` error → assert synthetic feedback fires."
tags:
  - autobuild
  - langgraph-migration
  - bugfix
  - coach
  - substrate-mitigation
---

# Task: Wire synthetic-feedback safety net for Coach decision-not-found failures

## Description

Surfaced by TASK-HMIG-010 run 4 (2026-06-05T16:05, see [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-4.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-4.md)). Investigation in this session's analysis identified the root cause:

**F17 — qwen36-workhorse Coach can't reliably emit the structured Bash-heredoc verdict.**

Coach's contract:
- Prompt instructs Coach to write a JSON verdict file via Bash heredoc ([`agent_invoker.py:2393-2394`](../../../guardkit/orchestrator/agent_invoker.py))
- Allowed tools: `["Read", "Bash", "Grep", "Glob"]` — no `Write` tool ([`agent_invoker.py:1959`](../../../guardkit/orchestrator/agent_invoker.py))
- Coach must construct a multi-line Bash heredoc with valid JSON to persist its verdict

Under qwen36-workhorse + LangGraph, this multi-step structured emission is unreliable. In run 4, Coach LLM ran for 140s with 12 successful HTTP responses but never emitted the Bash tool call to write `coach_turn_1.json`. This is **canary F2** (model discusses tool calls in prose without emitting actual tool_use blocks) manifesting at Coach level.

The substantive Player work was correct ([`phase_4_summary.json`](../../../.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/phase_4_summary.json) shows 14/14 doc-level exclusion tests passing). Only the verdict-emission failed.

## The orchestrator already has the fix mechanism — it isn't wired for this case

`_invoke_coach_primary` ([`autobuild.py:5508-5675`](../../../guardkit/orchestrator/autobuild.py)) has the right safety net:

```python
except Exception as sdk_error:
    logger.error("Coach invocation failed in primary path: %s. Emitting synthetic feedback decision.", sdk_error, exc_info=True)
    return self._emit_synthetic_coach_feedback(...)
```

But the safety net only fires on raised exceptions. `invoke_coach` catches `CoachDecisionNotFoundError` internally at [`agent_invoker.py:1987-1997`](../../../guardkit/orchestrator/agent_invoker.py):

```python
except (CoachDecisionNotFoundError, CoachDecisionInvalidError) as e:
    return AgentInvocationResult(
        task_id=task_id, turn=turn, agent_type="coach",
        success=False, report={}, error=str(e),
    )
```

So the file-not-found case returns `success=False` instead of propagating an exception. The synthetic-feedback safety net never fires. The orchestrator's downstream consumer sees `coach_decision="error"`, Wave 1 FAILS, AC-008 verdict computation is blocked.

## Acceptance Criteria

- [x] AC-001: Locate the call site in `_invoke_coach_primary` where `asyncio.run(self._agent_invoker.invoke_coach(...))` returns ([`autobuild.py:5625`](../../../guardkit/orchestrator/autobuild.py)). **Done**: changed `return asyncio.run(...)` → `result = asyncio.run(...)` (and matching change to the `RuntimeError`-fallback `loop.run_until_complete` path).
- [x] AC-002: After the return, check `result.success`. If `False` AND `"Coach decision not found"` (or `"Coach decision invalid"`) appears in `result.error`: emit `self._emit_synthetic_coach_feedback(rationale=f"Coach verdict-emission failed: {result.error}. Likely substrate limitation (qwen36-workhorse F2 at Coach level). Player should retry on turn 2 with this feedback.")` and return that result. **Done**: lines `autobuild.py:5672-5698`. Rationale uses dynamic `turn + 1` rather than hardcoded `2`.
- [x] AC-003: Other `success=False` outcomes (`SDKTimeoutError`, generic `Unexpected error`) continue to return as-is — only the verdict-emission failure converts to synthetic feedback. **Done**: predicate gates on the substring match; `return result` at line 5700 falls through for all other failures. Verified by `test_sdk_timeout_propagates_unchanged` and `test_unexpected_error_propagates_unchanged`.
- [x] AC-004: Regression test exercises invoke_coach returning `success=False` with `"Coach decision not found"` error → assert `_invoke_coach_primary` emits synthetic feedback (writes coach_turn_N.json, returns `success=True`). **Done**: `tests/orchestrator/test_llm_coach_primary.py::TestPrimaryFlowVerdictEmissionSoftFail` with 5 tests (not-found, invalid, SDK timeout passthrough, unexpected passthrough, success-true passthrough sanity guard). All pass.
- [ ] AC-005: Live smoke (HMIG-010 run 5): when Coach fails to write coach_turn_1.json, the orchestrator emits a synthetic feedback verdict instead of hard-failing the turn. Player gets a turn 2 to retry. (Bonus: run 5 may produce an actual approval on turn 2, since qwen36-workhorse sometimes succeeds at simpler verdicts.) **Pending**: out of scope for the unit-fix task; falsifier evaluation step is filed against TASK-HMIG-010 (this task now unblocks it).

## Implementation Notes

- This is fix-shape (a) from the run-4 investigation. The simpler "let invoke_coach raise" (fix b) was rejected because it would change the invoke_coach contract for other callers (`GUARDKIT_COACH_LEGACY=1`, tests, etc.) — narrower fix is safer.
- The synthetic feedback rationale should specifically name "Coach verdict-emission failed" so future runs can distinguish this failure class from other Coach-side errors. Future telemetry / Graphiti capture can then track F17 recurrence rate as a substrate-quality metric.
- After landing, F17 effectively becomes a soft-fail with a tracked rationale. The substrate-quality finding remains — qwen36-workhorse Coach is unreliable at structured verdict emission — but the orchestrator no longer hard-blocks on it.

## Out of scope (filed separately)

- **F2-at-Coach-level fundamental fix**: would require either Coach prompt simplification (smaller verdict format), Coach output mode change (orchestrator parses text response into JSON), or upgrading the Coach model. Each is a bigger architectural decision. This task only wires the soft-fail safety net; the substrate-quality finding is recorded for AC-008 evidence.
- **Pip-cache ghost-path filter** (F18): the orchestrator's ghost-path filter at [`agent_invoker.py:180`](../../../guardkit/orchestrator/agent_invoker.py) caught 4 known paths in run 4 but didn't filter the 40+ `Library/Caches/pip/http-v2/...` entries that the env bootstrap leaves in git detection. Cosmetic; recorded as I-008 in feature-run-incidents.md.

## References

- Run-4 failure log: [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-4.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-4.md)
- Canary F2: [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md) §3.F2
- Coach prompt: [`agent_invoker.py:2384-2415`](../../../guardkit/orchestrator/agent_invoker.py)
- Coach allowed-tools: [`agent_invoker.py:1959`](../../../guardkit/orchestrator/agent_invoker.py)
- Coach safety-net (synthetic feedback): [`autobuild.py:5677-5732`](../../../guardkit/orchestrator/autobuild.py) (`_emit_synthetic_coach_feedback`)
- Blocked task: [TASK-HMIG-010](../../in_progress/TASK-HMIG-010-full-feature-autobuild-validation.md)

## Notes

After this lands, the AC-008 falsifier evaluation can proceed:
- Player produces real work (F2 mostly closed for Player per run 3/4 evidence)
- Coach soft-fails on verdict-emission, Player retries with feedback
- Eventually Coach either succeeds (substrate variance) or the orchestrator exhausts retries and produces a clean "feedback after N turns" verdict

Either outcome is a usable AC-008 data point.

## Implementation Summary

Fix-shape (a) from the run-4 investigation: at
[`autobuild.py:5625`](../../../guardkit/orchestrator/autobuild.py), the
result of `asyncio.run(self._agent_invoker.invoke_coach(...))` is now
captured into a local rather than returned directly. After capture, a
narrow predicate checks `result.success is False` AND `result.error`
contains either `"Coach decision not found"` or `"Coach decision
invalid"`. When matched, the orchestrator emits a synthetic feedback
decision via the existing `_emit_synthetic_coach_feedback` with a
rationale that names the failure class verbatim
(`"Coach verdict-emission failed: <error>. Likely substrate limitation
(qwen36-workhorse F2 at Coach level). Player should retry on turn
{turn+1} with this feedback."`). All other `success=False` outcomes
(`SDKTimeoutError` "SDK timeout after Xs", generic "Unexpected error: X")
pass through to `return result` unchanged, preserving AC-003's narrow
scope. The `invoke_coach` contract is not modified — fix-shape (b)
("let invoke_coach raise") was rejected because it would change the
contract for other callers (`GUARDKIT_COACH_LEGACY=1` legacy path,
existing tests).

Regression coverage added as
`tests/orchestrator/test_llm_coach_primary.py::TestPrimaryFlowVerdictEmissionSoftFail`
with 5 tests:
- `test_decision_not_found_emits_synthetic_feedback` (AC-002 primary)
- `test_decision_invalid_emits_synthetic_feedback` (AC-002 sibling)
- `test_sdk_timeout_propagates_unchanged` (AC-003 guard)
- `test_unexpected_error_propagates_unchanged` (AC-003 guard)
- `test_success_true_propagates_unchanged` (sanity guard so the
  predicate cannot regress to overwrite real Coach approvals)

All 5 pass. The full `test_llm_coach_primary.py` file passes 17/17 (no
regression to the pre-existing 12 tests).

### Approach

- Narrow soft-fail at orchestrator boundary, not at agent-invoker
  boundary, so the `invoke_coach` contract stays intact for
  `GUARDKIT_COACH_LEGACY=1` and existing tests.
- Error-string matching at orchestrator layer rather than re-raising
  the typed exception, because `invoke_coach` already catches it
  internally and the typed exception never crosses the orchestrator
  boundary. A subsequent fix could move the predicate onto a typed
  field on `AgentInvocationResult` if the error-string match proves
  fragile across substrates — for now the substring is stable across
  SDK and LangGraph because the exception text is set by GuardKit's
  own `_load_agent_report` / `_validate_coach_decision` in
  `agent_invoker.py`, not by the substrate.

### Lessons

- **Soft-fail predicate must be substrate-agnostic by inspection, not
  by assumption.** The matched strings here ("Coach decision not
  found", "Coach decision invalid") are emitted by GuardKit's own
  loaders, not by the SDK / LangGraph harness — so the predicate
  trivially works under both substrates. Confirming this by reading
  the producer was cheaper than writing a substrate-parametrised test
  fixture, but the next maintainer should re-confirm if a new
  substrate adapter changes the error-text emission path.
- **Narrow-shape fixes (fix (a)) over broader contract changes (fix
  (b)) when the broader change has many downstream callers.**
  Modifying `invoke_coach` to raise instead of return
  `success=False` would have rippled into the legacy Coach path,
  multiple test fixtures, and any future direct callers — for a
  payoff (slightly cleaner orchestrator code) that didn't justify the
  risk. The orchestrator-layer check is more code but lower blast
  radius.
- **Sanity-guard tests for boolean predicates are cheap insurance.**
  The `test_success_true_propagates_unchanged` test exists only to
  catch a future refactor that drops the `not result.success` guard
  from the predicate. Without it, a maintainer could "simplify" the
  check to just the error-string match and silently overwrite real
  Coach approvals on turns where `result.error` happens to contain
  the matched string (unlikely but not impossible). Five extra lines
  of test, zero LOC of production code, infinite blast-radius
  reduction.
- **Comment density at the orchestrator layer matters more than
  elsewhere.** This block is one of dozens of branches in
  `_invoke_coach_primary`; the next maintainer reading the file
  needs to know *why* this predicate exists (substrate F2 at Coach
  level), *what failure class it catches* (verdict-emission, not
  cancellation, timeout, or arbitrary exception), and *what it
  doesn't catch* (anything else with `success=False`). The 26-line
  comment is load-bearing for future correctness.

### Related design rules

- [`harness-cancellation-contract.md`](../../../.claude/rules/harness-cancellation-contract.md)
  — sibling rule with the same shape: an orchestrator-layer
  abstraction whose primitive was paired with a specific substrate at
  introduction time. Both rules are instances of the broader
  meta-frame "verdict from a low-fidelity oracle" — that rule's
  Layer-4 reconciliation (`_check_late_approval`) and this fix's
  soft-fail are both *positive-evidence preconditions* added to
  binary-verdict gates to disambiguate "no signal" from "negative
  signal".
- The failure class itself (F17 from
  [`autobuild-FEAT-AOF-run-4.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-4.md)
  + canary F2 from
  [`canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md))
  is a substrate-quality finding about qwen36-workhorse's reliability
  at structured Bash-heredoc verdict emission. The fundamental fix
  (Coach prompt simplification, Coach output mode change, or Coach
  model upgrade) is filed separately and out of scope here.
