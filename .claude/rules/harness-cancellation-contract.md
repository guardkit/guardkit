# Harness Cancellation Contract

> **Source**: Seeded by TASK-FIX-CTOUT01 (2026-06-05). Pair with the
> Graphiti design-rule node *"harness-cancellation-contract"* under
> `guardkit__project_decisions`. Sibling of
> `absence-of-failure-is-not-success.md` (false-green inverse) and
> `path-string-mismatch-is-not-dishonesty.md` (false-red inverse) —
> all three are instances of the broader meta-frame: *a binary
> verdict from a low-fidelity oracle that cannot distinguish "no
> signal" from "positive/negative signal"*.

## The rule

A cooperative-cancellation layer that polls a shared
`cancellation_event` MUST dispatch the cancellation through ALL
substrates the orchestrator supports, not just the substrate that
existed when the layer was first written. When a new substrate is
introduced (e.g. the LangGraph harness alongside the Claude SDK
harness), the cancellation path that worked for the original
substrate (e.g. SIGTERM to a CLI subprocess) is almost certainly
**not enough** for the new one (e.g. an in-process httpx request).
The substrate-agnostic boundary is the
`HarnessAdapter.cancel()` interface — if the new substrate doesn't
honour it, in-flight LLM calls will run to natural completion despite
the orchestrator's timer having fired.

The rule applies to **any** runtime contract layer whose
implementation was paired with a specific substrate at the time of
introduction. Two known instances are documented below; future
incidents that match the same shape (an orchestrator-layer
abstraction whose "do the thing" path is silently substrate-specific)
should be folded under this rule rather than retried as ad-hoc fixes.

## Why this rule exists

The class-of-defect emerged when LangGraph harness landed alongside
the original SDK harness:

1. **2026-04** — TASK-FIX-ASPF-004 wired
   `AgentInvoker._cancel_monitor` + `_kill_child_claude_processes`
   so the orchestrator's task-level timeout could terminate the
   in-flight Claude CLI subprocess by SIGTERM. The comment at
   `agent_invoker.py:2820-2823` was explicit: *"the kill path is
   SDK-subprocess specific but the polling logic itself is
   substrate-agnostic (D-3)"*. The substrate-agnostic claim was
   half-true: the polling was agnostic, but the action wasn't.

2. **2026-06-05 (this defect)** — TASK-HMIG-010 run 3 exposed the
   gap. TASK-FIX-GD02 (LangGraph substrate, complexity 6) had its
   3000s task-level timer fire mid-Coach-invoke. `_cancel_monitor`
   detected the event, called `_kill_child_claude_processes` — a
   no-op under LangGraph because there is no subprocess. The
   in-flight `agent.ainvoke()` ran to natural completion ~48s later
   and Coach approved. Meanwhile the outer feature_orchestrator
   recorded `final_decision=timeout` and `success=False`. Layer 4
   (`LATE_APPROVAL_GRACE_S`, 60s reconciliation window) WOULD have
   caught this — the Coach approval landed inside the 60s window —
   but the reconciliation path had its own silent-swallow bug
   (`feature_orchestrator.py:3237`) that made the failure invisible
   at INFO-level logging.

Both incidents share a mechanism: **an orchestrator-layer abstraction
that "does the cancellation" by directly invoking a substrate-
specific primitive**. The fix is the standard composite-pattern
remediation — push the substrate-specific primitive **down** into the
substrate adapter, and call it through the substrate-agnostic
interface. The orchestrator polls the event and dispatches via
`await harness.cancel()`; each harness implements `cancel()` for its
own substrate.

## The four-layer cancellation taxonomy

GuardKit's autobuild orchestrator carries cancellation through four
distinct layers, each with its own failure modes. Understanding the
taxonomy is the only way to reason about which layer SHOULD have
caught a given regression and which layer DID:

### Layer 1 — `asyncio.wait_for(asyncio.to_thread(...))`

**Location:** `feature_orchestrator.py:2335-2347`
**Mechanism:** `asyncio.wait_for` cancels its inner Task wrapper when
the timeout fires. But the inner work is `asyncio.to_thread`, which
runs on a real Python thread that **cannot be hard-cancelled**.
**Failure mode:** Thread keeps running; the asyncio cancellation
fires but the work continues.
**Acknowledged at:** `feature_orchestrator.py:260-271` (docstring on
TASK-ATR-003 explicitly calls this out).

### Layer 2 — Cooperative `timeout_event` / `cancellation_event` checkpoints

**Location:** `autobuild.py:2164, 2240, 2339` (the three checkpoints
in `_loop_phase`).
**Mechanism:** The autobuild thread polls
`timeout_event.is_set()` at three checkpoints. When set, the loop
exits cleanly.
**Failure mode:** Mid-Coach-invoke, the thread is not at a
checkpoint. The check happens after the in-flight invoke returns.
**When this layer alone is enough:** When the invoke completes within
seconds of the cancel and the wasted compute is acceptable.

### Layer 3 — `_cancel_monitor` + `HarnessAdapter.cancel()`

**Location:**
* `agent_invoker.py:_cancel_monitor` (the polling closure)
* `HarnessAdapter.cancel()` ABC (the substrate-agnostic interface)
* `ClaudeSDKHarness.cancel()` (closes the active `query()` generator
  + relies on `_kill_child_claude_processes` for OS-level SIGTERM)
* `LangGraphHarness.cancel()` (cancels the asyncio Task wrapping
  `agent.ainvoke`)

**Mechanism:** When the polled `cancellation_event` fires, the
monitor dispatches `await harness.cancel()` (substrate-agnostic) THEN
falls through to `_kill_child_claude_processes` (substrate-aware:
no-op under LangGraph, SIGTERM under SDK).

**Deadline:** `GUARDKIT_HARNESS_CANCEL_DEADLINE` (default 30s,
env-tunable). LangGraph `cancel()` waits up to this deadline for the
in-flight `agent.ainvoke` to honour the cancellation via LangChain's
httpx client. If LangChain ignores cancellation past the deadline,
LangGraph `cancel()` logs a WARNING and leaks the task to GC.

**Failure mode (the bug that motivated this rule):** Before
TASK-FIX-CTOUT01, the monitor only called
`_kill_child_claude_processes`. Under LangGraph that's a no-op, so
the in-flight `agent.ainvoke` ran to natural completion (~48s) and
Layer 3 effectively had no cancellation path at all.

### Layer 4 — `LATE_APPROVAL_GRACE_S` reconciliation

**Location:** `feature_orchestrator.py:_check_late_approval` +
`feature_orchestrator.py:2403-2473` (the timeout-handling block).
**Mechanism:** When `asyncio.gather` returns `TimeoutError` for a
task, the wave-loop reads the latest `coach_turn_*.json` for that
task. If its mtime is within `LATE_APPROVAL_GRACE_S` (default 60s,
env-tunable via `GUARDKIT_LATE_APPROVAL_GRACE`) of the timer fire and
its `decision` is `"approve"`, the verdict is reclassified from
`timeout` to `approved_late` with `success=True`.
**Failure mode (the bug that motivated this rule):** A bare
`except Exception` swallow at `feature_orchestrator.py:3237` demoted
every transient error of `_latest_coach_turn_path` (transient
`OSError`, `JSONDecodeError`, etc.) to DEBUG-level logging. Under
INFO-level log capture (the production default), this was invisible:
the reconciliation silently didn't fire, and the operator saw a
divergent wave summary with no hint of why.

## Conflict resolution between Layer 3 and Layer 4

Layer 3 says "the outer cancellation wins; abort the in-flight
invoke." Layer 4 says "if Coach happened to approve within the grace
window, the inner verdict wins." These appear contradictory but are
NOT — they are SEQUENTIAL:

1. Layer 3 fires first. It cancels the in-flight invoke. The Coach
   invocation terminates within the 30s deadline (with WARNING if it
   doesn't).
2. The outer wave-loop's `asyncio.gather` returns `TimeoutError`.
3. Layer 4 inspects disk state. If `coach_turn_*.json` shows a
   completed approval within the 60s window, reclassify to
   `approved_late`. Otherwise the verdict stays `timeout`.

The contract: **Outer cancellation wins UNLESS inner Coach completes
within `LATE_APPROVAL_GRACE_S` of timer fire, in which case the
inner approval is honoured as `approved_late` with `success=True`.**
TASK-FIX-CTOUT01 revised the originally-filed AC-003 wording to
match.

## Symptom

The class-of-defect surfaces as a "verdict divergence" between the
outer wave-loop summary and the inner autobuild summary for a single
task:

- Outer wave summary: `Wave N ✗ FAILED: M passed, K failed` where one
  of the K failures is a `final_decision=timeout` for the affected
  task.
- Inner autobuild summary for the same task: `Status: APPROVED ...
  Coach approved implementation after N turn(s)`.
- The Coach approval's log timestamp is within
  `LATE_APPROVAL_GRACE_S` of the task-level timer fire.
- No `APPROVED_LATE` reclassification log line appears for the task
  in the feature_orchestrator log.
- No `_check_late_approval failed` line appears either (because the
  silent swallow was at DEBUG level; promoted to WARNING by
  TASK-FIX-CTOUT01).

## Detection recipe

```bash
# 1. Grep _cancel_monitor for substrate-specific calls.
rg "_cancel_monitor|_kill_child_claude_processes" \
   guardkit/orchestrator/agent_invoker.py
# Expected: monitor calls BOTH harness.cancel() (substrate-agnostic)
# AND _kill_child_claude_processes() (SDK-specific). If only the
# latter, this rule's defect-class is present.

# 2. Verify HarnessAdapter has a cancel() method that concrete
# substrates override.
rg "async def cancel" guardkit/orchestrator/harness/adapter.py \
   guardkit/orchestrator/harness/sdk_harness.py \
   ../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py
# Expected: 3 hits (one each in adapter, SDK, LangGraph).

# 3. Inspect _check_late_approval for silent swallows.
rg -A 3 "except Exception" \
   guardkit/orchestrator/feature_orchestrator.py
# Expected: WARNING with exc_info, NOT DEBUG.

# 4. Check that the LangGraph harness wraps ainvoke in an asyncio
# Task (so cancel() can cancel it) rather than awaiting it directly.
rg "asyncio.create_task\(.*ainvoke" \
   ../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py
# Expected: at least 1 hit, with self._ainvoke_task assignment.
```

## Remediation recipe

1. **Add `async def cancel(self) -> None` to the substrate-agnostic
   adapter ABC** with a no-op default (so existing test fakes don't
   break). Document the contract: must honour cancellation within
   `GUARDKIT_HARNESS_CANCEL_DEADLINE` seconds.
2. **Implement `cancel()` on every concrete substrate.** SDK closes
   the active `query()` generator; LangGraph cancels the asyncio
   Task wrapping `agent.ainvoke`. Both must clear their instance
   handles so a concurrent `cancel()` racing the natural finalisation
   is safe.
3. **Move the cancellation-monitor closure to AFTER substrate
   construction** so it can capture the live `harness` handle. Call
   `await harness.cancel()` BEFORE the legacy
   `_kill_child_claude_processes()`. Wrap the
   `harness.cancel()` call in try/except so a misbehaving
   substrate doesn't prevent the SIGTERM fallback.
4. **Promote silent-swallow log lines in reconciliation paths from
   DEBUG to WARNING with `exc_info`.** Operators need to see the
   reconciliation failure mode, not have it hidden under INFO-level
   logging.
5. **Test the deadline-expiry branch explicitly.** A stubborn-task
   test (one that catches CancelledError and continues) must drive
   the WARNING log path. Use `asyncio.wait_for(task,
   timeout=deadline_s)` not `asyncio.timeout(deadline_s) +
   suppress(CancelledError)` — the latter swallows the cancel before
   the deadline-expiry detection fires.

## Grep-able signature (for next agent)

```bash
# Verify the four-layer taxonomy is intact.

# Layer 1 acknowledgement (TASK-ATR-003 docstring):
rg "to_thread.*cannot be hard-cancelled" \
   guardkit/orchestrator/feature_orchestrator.py

# Layer 2 checkpoints (autobuild cooperative cancel):
rg "timeout_event.is_set\(\)" guardkit/orchestrator/autobuild.py

# Layer 3 monitor dispatch (the new rule's load-bearing line):
rg "await harness.cancel" guardkit/orchestrator/agent_invoker.py

# Layer 4 reconciliation + the no-longer-silent swallow:
rg "_check_late_approval failed.*exc_info" \
   guardkit/orchestrator/feature_orchestrator.py

# Substrate cancel() implementations:
rg "async def cancel" \
   guardkit/orchestrator/harness/adapter.py \
   guardkit/orchestrator/harness/sdk_harness.py \
   ../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py
```

## When this rule triggers

- Before introducing a new `HarnessAdapter` subclass for any new
  substrate (Anthropic Files API, OpenAI Responses API, etc.) —
  the new subclass MUST implement `cancel()`.
- Before adding any orchestrator-layer abstraction whose "do the
  thing" path was paired with a specific substrate at the time of
  introduction (e.g. `_kill_child_claude_processes` was paired with
  the SDK substrate; the LangGraph addition broke its substrate-
  agnosticism claim).
- During Phase 2.5 architectural review for any task that touches
  `agent_invoker.py:_invoke_with_role`, `feature_orchestrator.py`
  late-approval reconciliation, or any harness `cancel()` /
  `invoke()` implementation.
- During any diagnostic session investigating a verdict-divergence
  symptom between outer wave summary and inner autobuild summary.

## What the rule does NOT cover

- Hard-cancellation of the `asyncio.to_thread` thread itself (Layer
  1) — Python's threading model fundamentally doesn't support this
  and rewriting `_execute_task` as a native asyncio coroutine is a
  scope much broader than CTOUT01.
- The `_kill_child_claude_processes` path itself (TASK-FIX-ASPF-004)
  — that path remains the OS-level escalation for the SDK substrate
  and continues to fire after `harness.cancel()` in
  `_cancel_monitor`. Removing it would lose defence-in-depth.
- Cross-process cancellation of LangGraph-driven *subprocess* tool
  invocations (e.g. `Bash` tool calls running their own child
  processes inside the LangGraph harness). Those have their own
  lifecycle owned by the DeepAgents tool runtime.
- Cancellation-propagation timing across the orchestrator's outer
  `asyncio.timeout(self.sdk_timeout_seconds)` and the inner harness
  `GUARDKIT_HARNESS_CANCEL_DEADLINE`. The two deadlines compose
  naturally — the outer fires first if it's shorter, and the inner
  bounds how long the orchestrator waits for the substrate to honour
  the cancel — but tuning them in concert is operator policy, not a
  rule.

## Prior art

- **Sibling rule (false-green inverse direction)**:
  [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)
  — same meta-frame (binary verdict from a low-fidelity oracle),
  opposite failure mode (zero-count gates approving when zero
  attempts ran).
- **Sibling rule (false-red inverse direction)**:
  [`path-string-mismatch-is-not-dishonesty.md`](path-string-mismatch-is-not-dishonesty.md)
  — same meta-frame, opposite direction
  (orchestrator-injected ghost path triggering a false-fail).
- **Sibling rule (same guardkit ↔ guardkitfactory cross-repo seam)**:
  [`evidence-boundary-narrower-than-write-surface.md`](evidence-boundary-narrower-than-write-surface.md)
  — the other rule born of the guardkit ↔ guardkitfactory boundary. This rule
  guards a *migrated contract* (the harness `cancel()` interface) at the seam;
  that one guards the *evidence boundary* at the same seam (sibling-repo writes
  the orchestrator must collect). Both are enforced by a fast `inspect`-based
  cross-repo seam test (`test_xrepo_contract_seam.py` here;
  `test_evidence_repos_seam.py` there). Seeded by TASK-AB-XREPOEV01 (2026-06-13).
- **Sibling rule (disposition-locus instance)**:
  [`smoke-gate-is-feedback-not-terminator.md`](smoke-gate-is-feedback-not-terminator.md)
  — same meta-family (binary verdicts in the autobuild loop), new locus:
  *disposition*. This rule guards the *dispatch* of a cancellation across
  substrates; that one guards the *disposition* of a believed high-fidelity
  failure (feed it back via `seed_feedback`, bounded by
  `GUARDKIT_SMOKE_GATE_MAX_RETRIES`, rather than terminating the loop with a
  bare `break`). Seeded by TASK-AB-COACHRUNPARITY01 (commit `a11708d0`,
  2026-06-14).
- **Pair fact in Graphiti** (`guardkit__project_decisions`): node
  *"harness-cancellation-contract"* with citations to the
  TASK-FIX-CTOUT01 reproducer test
  (`tests/unit/test_feature_orchestrator.py::TestLateApprovalReconciliation::test_layer4_silent_swallow_invisible_on_current_main`)
  and the four-layer remediation commits.
- **Originating defect**: TASK-HMIG-010 run 3 GD02 verdict
  divergence, recorded at
  `docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md`
  lines 1555–1601.
- **Originating fix**: TASK-FIX-CTOUT01 (this task), implemented
  2026-06-05 on branch `fix/ctout01-coach-cancellation-race`.
- **CI enforcement (TASK-INFRA-XREPOCONTRACT)**: the
  `rg "async def cancel"` grep signature above is codified as an
  executable cross-repo seam test at
  `tests/orchestrator/harness/test_xrepo_contract_seam.py`
  (`TestSubstrateContract::test_cancel_is_overridden_not_abc_noop` +
  `test_model_is_threaded_into_constructor`). It asserts every concrete
  `HarnessAdapter` substrate overrides `cancel` (rather than inheriting
  the no-op `HarnessAdapter.cancel` default) and threads `model=`,
  against the **real installed guardkitfactory** — so a new substrate
  re-introducing the cancel-asymmetry, or the F1/F9/F10/F12/F19
  model-threading defect, fails CI in seconds instead of after a full
  autobuild run. `@pytest.mark.seam` + `importorskip` make it a clean
  no-op without the langchain stack; the merge-gating job is
  `.github/workflows/seam-tests.yml`.
