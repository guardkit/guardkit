# Watchdog activity signal must be substrate-aware, not event-arrival-keyed

> **Source**: Seeded by TASK-FIX-SPECINVOKE01 (2026-06-13, commit `d916cf434`).
> Pair with the Graphiti design-rule node *"watchdog activity-signal must be
> substrate-aware not event-arrival-keyed"* under `guardkit__project_decisions`.
> Sibling of [`harness-cancellation-contract.md`](harness-cancellation-contract.md)
> (the same guardkit ↔ guardkitfactory substrate-asymmetry seam, dispatch locus)
> and [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)
> (the low-fidelity-oracle meta-frame: *a binary verdict from an oracle that
> cannot distinguish "no signal" from "positive signal"*).

## The rule

A no-activity watchdog — or any orchestrator oracle that infers "the model is
idle / hung" from the **absence of yielded harness events** — is
**substrate-blind**. It produces false positives on any harness substrate that
buffers events until completion instead of streaming them incrementally. The
activity signal MUST reflect **real model/tool progress** (an LLM boundary, a
tool boundary), not **event-arrival cadence** (which is an artefact of how a
given substrate chooses to yield).

When a new harness substrate is introduced whose `invoke()` awaits the whole
run before yielding any event, the event-arrival clock the watchdog polls
freezes for the entire run, the no-activity gap grows unconditionally, and the
watchdog kills a live, model-active specialist. The substrate-agnostic fix is
to thread an explicit `on_model_activity` callback from the orchestrator into
the harness, fired on every real LLM/tool boundary, so the clock is refreshed
by progress the substrate cannot buffer away. A genuine hang (the substrate
stops calling the model entirely) still starves the callback and is still
caught — that is the point of pairing the binary "no signal" verdict with a
real positive-evidence source.

## Why this rule exists

The class-of-defect emerged the same way its dispatch sibling did — a watchdog
paired with one substrate's streaming semantics silently broke on a new
buffered substrate:

1. **2026-06-13** — FEAT-9DDE run 3. The deterministic test-orchestrator
   specialist was killed at 150s every run with `hang detected (no model
   activity for 150s)`, on turns that had ~18 successful `POST :9000/v1/responses
   "200 OK"` calls *during* the "hang" — the model was working. The watchdog
   (`_run_specialist_with_watchdog` in
   [`guardkit/orchestrator/specialist_invocations.py`](../../guardkit/orchestrator/specialist_invocations.py))
   keys on `AgentInvoker._last_activity_monotonic`, which was bumped **only per
   yielded `HarnessEvent`** inside the consumer loop in
   [`agent_invoker.py`](../../guardkit/orchestrator/agent_invoker.py)
   `_invoke_with_role`. But `LangGraphHarness.invoke()` awaits the entire
   multi-turn `agent.ainvoke()` before yielding any event, so during the whole
   run zero events reached the consumer, the clock froze at its seed value, and
   the watchdog false-killed the specialist at 150s. The SDK harness streams
   per-message, so its clock stayed fresh — which is exactly why this never
   reproduced on SDK.

Both this and the harness-cancellation defect share a mechanism: **an
orchestrator-layer abstraction paired with one substrate's behaviour (event
streaming) silently breaks on a new substrate (buffered `ainvoke`) it wasn't
written for.** The activity-signal defect surfaced the moment a buffered
substrate was routed through a watchdog written against a streaming one.

The fix (TASK-FIX-SPECINVOKE01) threads an `on_model_activity` callback from
`AgentInvoker._bump_activity`
([`agent_invoker.py:3559`](../../guardkit/orchestrator/agent_invoker.py#L3559),
passed at the `_invoke_with_role` `select_harness` call,
[`agent_invoker.py:3810`](../../guardkit/orchestrator/agent_invoker.py#L3810))
through `select_harness`
([`selector.py:354`, `:416-428`](../../guardkit/orchestrator/harness/selector.py#L354))
into the guardkitfactory `LangGraphHarness` (a paired commit added a LangChain
`BaseCallbackHandler` on the `on_chat_model_start` / `on_llm_start` /
`on_llm_new_token` / `on_llm_end` / `on_tool_start` / `on_tool_end` boundaries).
The SDK branch never sees the callback — the selector pops it (it already
streams). A stale factory that lacks the param is dropped-with-WARNING rather
than crashing, and the cross-repo seam test
[`test_xrepo_contract_seam.py::test_langgraph_harness_init_accepts_on_model_activity`](../../tests/orchestrator/harness/test_xrepo_contract_seam.py#L414)
fails loud in CI if a real installed guardkitfactory ever drops it.

## Symptom

- A specialist (or any harness-driven sub-invocation) is killed with the
  literal reason `hang detected (no model activity for <N>s)` on a run where
  the model was demonstrably active — the run log shows successful
  `POST .../v1/responses "200 OK"` calls *during* the "hang", and the
  orchestrator logs `Extracted partial data from 0 events`.
- The kill is **deterministic, substrate-specific, and model-independent**:
  it reproduces on every run under the LangGraph harness and never under SDK.
- The watchdog's clock (`_last_activity_monotonic`) is stuck at its seed value
  because no `HarnessEvent` was yielded for the whole run.

## Detection recipe

```bash
# 1. Watchdog reads the event-arrival clock. Confirm the clock is fed by a
#    real-activity callback, not ONLY the per-yielded-event bump.
rg -n "_last_activity_monotonic|_run_specialist_with_watchdog" \
   guardkit/orchestrator/specialist_invocations.py guardkit/orchestrator/agent_invoker.py

# 2. The substrate-aware signal MUST be wired: a callback bumps the clock.
#    Absence = the watchdog has reverted to the substrate-blind event clock.
rg -n "on_model_activity|_bump_activity" \
   guardkit/orchestrator/agent_invoker.py guardkit/orchestrator/harness/selector.py

# 3. The selector must pop on_model_activity for SDK and forward it (guarded by
#    inspect.signature) to LangGraph only.
rg -n "on_model_activity" guardkit/orchestrator/harness/selector.py

# 4. The cross-repo seam guard must exist (fails loud on a stale factory).
rg -n "test_langgraph_harness_init_accepts_on_model_activity|on_model_activity" \
   tests/orchestrator/harness/test_xrepo_contract_seam.py

# 5. Cross-check the substrate-asymmetry family.
rg "watchdog-activity-signal|harness-cancellation|absence-of-failure" .claude/rules/
```

## Remediation

1. **Make the activity signal reflect real progress, not event arrival.**
   Thread an explicit callback (`on_model_activity`) from the orchestrator into
   the harness, fired on every LLM/tool boundary, and refresh the watchdog
   clock from it — not only from yielded harness events.
2. **Route the callback through the substrate boundary, not the harness
   constructor blindly.** The selector (`select_harness`) is the boundary where
   SDK-shaped kwargs become harness-shaped kwargs: pop `on_model_activity` for
   the streaming SDK substrate (which needs no callback), forward it only to the
   buffered substrate that does.
3. **Degrade gracefully on a stale factory.** Forward the param only when the
   installed harness's `__init__` signature accepts it
   (`inspect.signature(...).parameters`); drop-with-WARNING otherwise rather
   than crashing. The fallback reverts to the substrate-blind clock — so pair it
   with a loud CI seam test.
4. **Keep the genuine-hang case caught.** A real hang (the substrate stops
   calling the model entirely → no callbacks fire → clock freezes → watchdog
   trips) must still be killed. The callback restores the *positive-evidence*
   precondition; it does not disarm the watchdog.
5. **CI-guard the cross-repo contract.** Add a seam test asserting the real
   installed harness `__init__` accepts the callback param, so a version skew
   across the repo split is a red CI build, not a silent regression to the
   false-kill.

## Grep-able signature (for next agent)

```bash
# Substrate-aware-signal fingerprint (MUST MATCH; absence = regression):
rg -n "on_model_activity=self._bump_activity" guardkit/orchestrator/agent_invoker.py   # -> 3810
rg -n "def _bump_activity" guardkit/orchestrator/agent_invoker.py                        # -> 3559

# Selector forward/pop fingerprint (MUST MATCH):
rg -n "on_model_activity = harness_kwargs.pop" guardkit/orchestrator/harness/selector.py # -> 354

# Cross-repo seam guard (MUST MATCH):
rg -n "test_langgraph_harness_init_accepts_on_model_activity" \
   tests/orchestrator/harness/test_xrepo_contract_seam.py                                 # -> 414

# Watchdog reason string (the false-kill fingerprint):
rg -n "no model activity for" guardkit/orchestrator/specialist_invocations.py            # -> 141

# Sibling-rule lookup:
rg "watchdog-activity-signal|harness-cancellation|absence-of-failure" .claude/rules/
```

## When this rule triggers

- Before introducing a new no-activity / idle / hang watchdog, or any oracle
  that infers idleness from the absence of orchestrator-observable events.
- Before adding a new `HarnessAdapter` substrate whose `invoke()` buffers work
  before yielding events — confirm its progress is surfaced to any watchdog via
  a real-activity callback, not left to event cadence.
- During Phase 2.5 architectural review for any task touching
  `specialist_invocations.py` watchdog logic, `agent_invoker.py`
  `_invoke_with_role` / `_bump_activity`, or `selector.py` kwarg forwarding.
- During any diagnostic session investigating a "specialist killed as hung but
  the model was making HTTP calls the whole time" report.

## What this rule does NOT cover

- **Genuine hangs.** A substrate that truly stops calling the model starves the
  callback and is correctly killed; the rule requires the watchdog measure real
  progress, not that it never fire.
- **The watchdog timeout value itself** (`GUARDKIT_SPECIALIST_WATCHDOG_SECONDS`,
  default 150s in `specialist_invocations.py`) — that is operator policy. The
  rule governs *what feeds the clock*, not the deadline.
- **Duration caps** (the SDK-timeout hard cap on total specialist wall-clock,
  TASK-FIX-SPECHANG) — those are a separate bound and continue to fire
  independently of the no-activity signal.
- **The SDK streaming substrate**, which needs no callback (it already refreshes
  the clock per yielded message); the selector correctly pops the param for it.
