# The harness selector is the kwarg-consumption boundary, not each harness `__init__`

> **Source**: Seeded by TASK-FIX-002R-CONSUME (commit `812b2c4aa`, 2026-06-03).
> Pair with the Graphiti design-rule node *"cwd is a selector-layer concern, not
> a harness-init concern"* under `guardkit__project_decisions`. Sibling of
> [`namespace-hygiene.md`](namespace-hygiene.md) (its "runner without producer"
> parent class-of-defect) and its sibling consumer-wiring fix TASK-FIX-MODELPLUMB
> (model-alias auto-prefixing, same commit).

## The rule

`guardkit/orchestrator/harness/selector.py::select_harness` is the single
boundary where SDK-shaped orchestrator kwargs are translated into
harness-shaped kwargs. When a kwarg is needed by one substrate at a *different
lifecycle stage* than another (needed at construction time by one, at
`.invoke()` time by another, or not at all by a third), the selector MUST
**consume it at the selector layer** — pop it from `harness_kwargs` at the top
of `select_harness` and route it explicitly in each branch — rather than adding
it to any harness's `__init__` signature.

Callers (`agent_invoker._invoke_with_role`) pass the full SDK-shaped kwarg bag
**unconditionally**, including kwargs only one substrate uses. Every concrete
`HarnessAdapter.__init__` signature stays stable across substrates; a
substrate-specific kwarg never leaks into a constructor that has no use for it.

The canonical instance is `cwd`:

- `ClaudeSDKHarness` has **no** `cwd` `__init__` parameter — it receives `cwd`
  later, as a parameter of `ClaudeSDKHarness.invoke()`
  (`sdk_harness.py:204`, threaded to `cwd=str(cwd)` at `:273`).
- `LangGraphHarness` needs `cwd` **at construction time** to build a
  path-confined `LocalShellBackend` via
  `guardkitfactory.harness.build_autobuild_backend(cwd)`.

Both receive the same kwarg bag from `_invoke_with_role`; the selector pops
`cwd` (`selector.py:329`) so the SDK branch never sees it and the langgraph
branch threads it into `build_autobuild_backend(Path(cwd))` (`selector.py:401`).

## Why this rule exists

TASK-FIX-002R-CONSUME wired guardkitfactory's `build_autobuild_backend` +
`build_autobuild_permissions` factories (complete in guardkitfactory since
TASK-HMIG-002R, 2026-05-20) into guardkit's selector. Before the fix the
langgraph branch constructed `LangGraphHarness(model=..., backend=None,
permissions=None)` because nothing called the factories — the consumer-side
gap that surfaced in AC-001D run 3 (2026-06-03).

The wiring needed the worktree path (`cwd`) at the langgraph branch, but the
SDK branch's `ClaudeSDKHarness.__init__` has no `cwd` parameter. The naive fix
— add `cwd` to both harness constructors — would have coupled every substrate's
`__init__` to a kwarg only one of them uses at construction. Instead the
selector pops `cwd` once (`selector.py:329`), and:

- the SDK branch passes the remaining `harness_kwargs` through unchanged to
  `ClaudeSDKHarness(**harness_kwargs)` (`selector.py:361`);
- the langgraph branch uses the local `cwd` to build the backend
  (`selector.py:396-402`), raising an actionable `AgentInvocationError` naming
  `_invoke_with_role` as the caller if `cwd` is missing (`selector.py:385-394`).

The caller (`agent_invoker._invoke_with_role`, def at `agent_invoker.py:3575`)
passes `cwd=self.worktree_path` unconditionally at every `select_harness` call
site (`agent_invoker.py:3777-3802`, `:7361-7393`).

This boundary has since absorbed **every** subsequent substrate-asymmetric
kwarg the same way, which is the proof the rule generalises: `recursion_limit`
and `max_tool_result_chars` (TASK-PERF-COACHSYNTH) and `on_model_activity`
(TASK-FIX-SPECINVOKE01) are all popped at the top of `select_harness`
(`selector.py:343-354`) and routed only to the langgraph branch — the SDK
harness, which needs none of them, never sees them.

## Symptom

- A new harness substrate needs a value at construction time that another
  substrate needs later (or not at all), and the temptation is to grow every
  `HarnessAdapter.__init__` signature to carry it.
- `TypeError: __init__() got an unexpected keyword argument '<x>'` from a
  harness constructor when a caller passes a kwarg only a *different* substrate
  uses.
- A substrate-specific kwarg (`cwd`, a backend factory input, a LangGraph-only
  cap) appears in `ClaudeSDKHarness.__init__` (or vice versa) with a comment
  like "ignored on this path" — that's the leak this rule prevents.

## Detection recipe

```bash
# 1. Confirm select_harness pops substrate-asymmetric kwargs at the top,
#    rather than forwarding them into a harness __init__.
rg -n "harness_kwargs.pop\(" guardkit/orchestrator/harness/selector.py

# 2. Confirm cwd is NOT an __init__ parameter of the SDK harness (it is an
#    .invoke() parameter instead).
rg -n "def __init__|def invoke|cwd" guardkit/orchestrator/harness/sdk_harness.py

# 3. Confirm callers pass cwd unconditionally to select_harness.
rg -n "cwd=self.worktree_path" guardkit/orchestrator/agent_invoker.py

# 4. Confirm the langgraph branch threads cwd into the backend factory.
rg -n "build_autobuild_backend|build_autobuild_permissions" \
   guardkit/orchestrator/harness/selector.py
```

## Remediation

1. **Pop substrate-asymmetric kwargs at the top of `select_harness`** (next to
   the existing `cwd` / `recursion_limit` / `max_tool_result_chars` /
   `on_model_activity` pops, `selector.py:329-354`). Do not add them to any
   harness `__init__`.
2. **Route the popped value explicitly in each branch.** The SDK branch forwards
   only the remaining `harness_kwargs`; the langgraph branch uses the local
   variable — e.g. `cwd` is passed as `Path(cwd)` into the backend factory at
   `selector.py:401` (via the defensive `_build_backend_with_optional_cap`
   helper).
3. **Fail loud on a required-but-missing substrate kwarg** with a message naming
   the caller — see the `cwd is None` guard at `selector.py:385-394`.
4. **Keep callers unconditional.** `_invoke_with_role` passes the SDK-shaped bag
   as-is; the selector, not the caller, decides which substrate consumes what.
5. **Forward optional cross-repo kwargs defensively.** When the value goes to a
   separately-versioned guardkitfactory factory, forward it only when the
   installed signature accepts it and drop-with-WARNING on a stale factory
   (`_build_backend_with_optional_cap`, the `on_model_activity` `inspect`-guard
   at `selector.py:416-424`) rather than crashing on version skew.

## Grep-able signature (for next agent)

```bash
# Selector-consumes-cwd fingerprint (MUST MATCH; absence = the kwarg leaked
# back into a harness __init__).
rg -n 'cwd = harness_kwargs.pop\("cwd"' guardkit/orchestrator/harness/selector.py   # -> 329

# SDK harness takes cwd at invoke() time, NOT __init__.
rg -n "cwd: Path" guardkit/orchestrator/harness/sdk_harness.py                        # -> 204

# Callers pass cwd unconditionally.
rg -n "cwd=self.worktree_path" guardkit/orchestrator/agent_invoker.py                 # -> 3802, 7393 (+ nested)

# Regression tests for the three cwd branches.
rg -n "test_langgraph_wires_backend_and_permissions|test_sdk_path_ignores_cwd_kwarg|test_langgraph_missing_cwd_raises_with_actionable_message" \
   tests/orchestrator/harness/test_selector.py                                        # -> 462, 542, 518
```

## When this rule triggers

- Before adding a new `HarnessAdapter` subclass, or a new kwarg that only some
  substrates consume (or consume at different lifecycle stages).
- Before growing any `HarnessAdapter.__init__` signature to carry a value the
  selector could route instead.
- During Phase 2.5 architectural review for anything touching
  `harness/selector.py`, `_translate_kwargs_for_langgraph`, or
  `agent_invoker._invoke_with_role`.

## What it does NOT cover

- Kwargs consumed identically by every substrate at construction time — those
  can legitimately be plain `__init__` parameters; the selector only special-
  cases *asymmetric* ones.
- The *content* of the backend/permissions factories (owned by guardkitfactory,
  TASK-HMIG-002R). This rule governs the guardkit-side *wiring*, not the
  factory internals.
- Cross-repo version-skew handling beyond the defensive-forward pattern (see
  [`harness-cancellation-contract.md`](harness-cancellation-contract.md) and its
  cross-repo seam test for the CI-guard side of the guardkit ↔ guardkitfactory
  boundary).
