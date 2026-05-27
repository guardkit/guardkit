# `guardkit.orchestrator.harness` — Substrate Adapter Layer

This package isolates the autobuild Player/Coach invocation behind a
single abstract interface so the orchestrator can dispatch to either the
legacy `claude-agent-sdk` path or the new LangGraph/DeepAgents path
based on a single environment variable.

The harness boundary was introduced by TASK-HMIG-006 (cross-repo
dispatch refactor) as the seam separating GuardKit's orchestrator from
its execution substrate. See the parent feature
[FEAT-HMIG (autobuild-harness-migration)](../../../tasks/) for the
migration's full motivation, decisions, and Wave plan.

## Public surface

```python
from guardkit.orchestrator.harness import (
    HarnessAdapter,           # ABC — concrete impls live here + in guardkitfactory
    HarnessEvent,             # Tagged-union of stream events
    AssistantMessageEvent,
    ToolUseEvent,
    ToolResultEvent,
    ResultMessageEvent,
    ClaudeSDKHarness,         # claude-agent-sdk path (default)
    select_harness,           # env-var dispatch helper
)
```

| Module | Owner | Purpose |
|---|---|---|
| `adapter.py` | TASK-HMIG-001A | The `HarnessAdapter` ABC + `HarnessEvent` taxonomy. Substrate-free. |
| `sdk_harness.py` | TASK-HMIG-006 Phase 3a | `ClaudeSDKHarness` — wraps `claude_agent_sdk.query`. |
| `selector.py` | TASK-HMIG-006 Phase 3a/3c | `select_harness()` + `_translate_kwargs_for_langgraph()`. |
| `__init__.py` | — | Pure re-exports. Does not import `os` per OQ-3. |

The LangGraph adapter lives in the **sibling repository
`guardkitfactory`** at
[`guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py`](../../../../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py).
GuardKit only imports it lazily on the langgraph branch of
`select_harness()`, so callers running on the default SDK path do not
need `guardkitfactory` installed.

## Environment-variable contract

```bash
# Default — claude-agent-sdk path
unset GUARDKIT_HARNESS
# or explicitly:
GUARDKIT_HARNESS=sdk

# LangGraph path — requires guardkitfactory importable
GUARDKIT_HARNESS=langgraph
```

The value is read by `select_harness()` and is case-insensitive. Any
value other than `sdk` or `langgraph` raises an `AgentInvocationError`
naming the bad value — there is no silent fallback to the default.

Both `_invoke_with_role` (player/coach turn invocations) and `guardkit
doctor` consult the env var. `doctor` reports the active substrate plus
the `guardkitfactory` version when langgraph is selected (TASK-HMIG-006
AC-006).

## Cross-repo dependency

GuardKit's `pyproject.toml` adds `guardkitfactory>=0.1,<1` to the
`[project.optional-dependencies].autobuild` group. The cross-repo
resolution path is the `[tool.uv.sources]` sibling-repo editable
pattern (TASK-HMIG-006 D-5, matching the jarvis / specialist-agent fleet
convention for `nats-core`):

```toml
[tool.uv.sources]
guardkitfactory = { path = "../guardkitfactory", editable = true }
```

Operator-side development runs `uv sync --extra autobuild` (or `pip
install -e ../guardkitfactory && pip install -e .[autobuild]`) to pick
up the editable sibling. End-user installs from PyPI will resolve the
versioned release once `guardkitfactory` ships there; until then, the
`[tool.uv.sources]` block is the resolution path. See
[`docs/guides/portfolio-python-pinning.md`](../../../docs/guides/portfolio-python-pinning.md)
for the wider portfolio pattern.

The dependency is one-way: `guardkitfactory` imports the
`HarnessAdapter` ABC from `guardkit.orchestrator.harness`, and `guardkit`
lazily imports `LangGraphHarness` from `guardkitfactory.harness` only on
the langgraph branch. No cycle.

## Cutover-day flip

Through 2026-06-08 (D-7 in the parent review) the default remains
`GUARDKIT_HARNESS=sdk`. On the cutover day a single one-line PR flips
the default to `langgraph` (the env-var read in `selector.py` line 68);
the SDK path is retained as the opt-in fallback through 2026-06-15.

This README must be updated in the same PR to flip the
"default through D-7" wording above to "default after D-7".

## Wave-2 LangGraph divergences (documented, not bugs)

The LangGraph path consciously degrades the following signals through
Design Decision D-1 (the `event.raw` channel keeps SDK-shape downstream
consumers happy at the cost of LangGraph-side fidelity):

| Downstream signal | SDK path | LangGraph path (Wave-2) | Fixed in |
|---|---|---|---|
| `_emit_llm_call_event` input/output tokens | Populated from `ResultMessage.usage` | `None` (LangChain dict has different shape) | **TASK-HMIG-006.2** |
| `_track_tool_use` progress counters | Populated from `ToolUseBlock` blocks | No-op (LangChain dict has no `.content` list) | **TASK-HMIG-006.2** |
| `_extract_partial_from_messages` on cancel | Full text/tool-call extraction | Lossy (returns empty lists) | **TASK-HMIG-006.2** |
| `player_turn_N.json` `tool_calls` field | Populated when tools used | `[]` on LangGraph until 006.2 | **TASK-HMIG-006.2** |
| Resume support (`supports_resume`) | `True` (SDK `session_id`) | `False` (per AC-007, D-07) | **Out of scope** — JSON-on-disk checkpointing is the migration's chosen resume path. |
| Direct-mode SDK call at `agent_invoker.py:5269+` | Direct SDK `query()` | Still SDK | **TASK-HMIG-006.1** |
| Coach independent test pass (`coach_validator.py:1869+`) | Direct SDK `query()` | Still SDK | **TASK-HMIG-006.3** |
| Pre-loop design phase (`task_work_interface.py:_execute_via_sdk`) | Routes through `select_harness()` | Routes through `select_harness()` | **Fixed in TASK-HMIG-006.4 (this task)** |

The pre-loop design-phase row above is now closed: the design phase
(Phases 1.5–2.8) dispatches through `select_harness()` rather than
importing `claude_agent_sdk` directly, so `GUARDKIT_HARNESS=langgraph`
routes the design phase through the LangGraph harness instead of
silently using the SDK. The four SDK-only pre-loop kwargs
(`setting_sources`, `max_turns`, `allowed_tools`, `permission_mode`) are
forwarded to `select_harness()`; `_translate_kwargs_for_langgraph` drops
them on the langgraph branch — `setting_sources` is a documented no-op
(DeepAgents loads its default context; project-sources injection is
deferred to a follow-up if needed).

Each divergence is asserted explicitly by the AC-004 byte-compat test
suite — see [`tests/orchestrator/harness/`](../../../tests/orchestrator/harness/).
The schema-subset check fixtures include both parity-asserting and
divergence-asserting cases per
[`.claude/rules/absence-of-failure-is-not-success.md`](../../../.claude/rules/absence-of-failure-is-not-success.md)
("pair every `count_failed == 0` rule with `count_attempted > 0`"):
the divergences make the AC-004 contract a positive-evidence test, not a
silently-passing zero-cardinality check.

When TASK-HMIG-006.2 lands, the divergence assertions invert (from
"divergence expected" to "parity expected"). That inversion is the
verifiable signal that the helper-function migration is complete.

## Adapter ownership boundary

The substrate seam is intentionally thin. The harness handles ONLY:

- SDK / LangGraph lazy imports
- Constructing the underlying client (`ClaudeAgentOptions` or
  `create_deep_agent`)
- The per-turn message-stream loop
- Translating native messages → `HarnessEvent` (with `event.raw`
  populated for SDK-shape downstream consumers)
- Generator hygiene (`aclose`, drain on terminal event)
- Translating substrate-specific exceptions to `AgentInvocationError`
  (D-4 normalisation)
- `_install_sdk_cleanup_handler` invocation (D-6 — bound to the
  per-invocation subprocess lifetime)

These stay in `agent_invoker.py` per Design Decision D-3 — they are
substrate-agnostic concerns of the orchestrator, not the substrate:

- `_cancel_monitor` task + `_kill_child_claude_processes`
- `measure_latency` context
- `asyncio.timeout(self.sdk_timeout_seconds)`
- `async_heartbeat` (and `heartbeat_label_override` for specialists)
- `sdk_debug.preserve_prompt` / `preserve_event` JSONL writers
- `_emit_llm_call_event` event emission
- `check_assistant_message_error` validation
- `_track_tool_use` progress counters
- TASK-CRV-1540 partial-extract on `CancelledError`
- TASK-RFX-B20B `session_id` rescan loop

## Testing

The substrate-specific test surfaces are kept separate:

```bash
# Adapter ABC contract
pytest tests/orchestrator/harness/test_adapter_interface.py

# ClaudeSDKHarness in isolation
pytest tests/orchestrator/harness/test_sdk_harness.py

# Selector env-var dispatch + kwarg translator
pytest tests/orchestrator/harness/test_selector.py

# LangGraph dispatch via _invoke_with_role (stub model)
pytest tests/orchestrator/test_agent_invoker_langgraph.py

# AC-008 surface — existing _invoke_with_role consumers
# (must remain green with no env-var override)
pytest tests/orchestrator/test_agent_invoker_sdk_errors.py \
       tests/orchestrator/test_coach_sdk_stream_resilience.py \
       tests/orchestrator/test_specialist_observability.py \
       tests/orchestrator/instrumentation/test_llm_call_events.py
```

The AC-004 byte-compat parity test (added in Phase 4) parametrises over
both substrates and runs the same fixture turn through each, asserting
either parity or one of the documented Wave-2 divergences above.

## References

- Parent task: [TASK-HMIG-006](../../../tasks/design_approved/autobuild-harness-migration/TASK-HMIG-006-refactor-agent-invoker-cross-repo-dispatch.md)
- Parent feature: FEAT-HMIG (autobuild-harness-migration)
- Parent review: TASK-REV-HMIG (review §10 — frozen-path-touch justification)
- ABC definition task: [TASK-HMIG-001A](../../../tasks/completed/2026-05/TASK-HMIG-001A-define-harness-adapter-interface.md)
- LangGraph skeleton task: TASK-HMIG-001B (in `guardkitfactory` repo)
- Backend/permissions wiring task: TASK-HMIG-002R (in `guardkitfactory` repo)
- Implementation plan: [`docs/state/TASK-HMIG-006/implementation_plan.md`](../../../docs/state/TASK-HMIG-006/implementation_plan.md)
- Architectural review: [`docs/state/TASK-HMIG-006/architectural_review.md`](../../../docs/state/TASK-HMIG-006/architectural_review.md)
- Portfolio Python pinning: [`docs/guides/portfolio-python-pinning.md`](../../../docs/guides/portfolio-python-pinning.md)
