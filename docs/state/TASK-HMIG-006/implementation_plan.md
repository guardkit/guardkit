# Implementation Plan — TASK-HMIG-006

**Task:** Refactor `agent_invoker._invoke_with_role` to dispatch through `HarnessAdapter` (cross-repo import from guardkitfactory)

| Field | Value |
|---|---|
| Task ID | TASK-HMIG-006 |
| Feature | FEAT-HMIG (autobuild-harness-migration) |
| Parent review | TASK-REV-HMIG |
| Wave | 2 / parallel group 2A |
| Complexity | 7/10 |
| Intensity | strict |
| Effort estimate | ~10h (multi-session) |
| Plan version | v3 (2026-05-20) — folds Phase 2.5B reviewer recommendations AND Phase 2.8 OQ-1 resolution (use `[tool.uv.sources]` sibling-repo editable path, not PyPI / git+https) |
| Author | Claude (planning agent), interactive `/task-work --design-only` |
| Arch review score | 78/100 (strict threshold ≥70) — see `architectural_review.md` |
| Approved | 2026-05-20 by rich@appmilla.com via `/task-work --design-only` Phase 2.8 checkpoint |
| OQ-1 resolution | `[tool.uv.sources]` sibling-repo editable pattern (fleet convention from jarvis/specialist-agent — see D-5 below) |
| OQ-2 resolution | File 006.1 / 006.2 / 006.3 follow-ups during Phase 3 as backlog tasks |

---

## 1. Scope at a glance

### In scope (this task)

- One SDK boundary only: `AgentInvoker._invoke_with_role` at `guardkit/orchestrator/agent_invoker.py:2359-2740`.
- New module `guardkit/orchestrator/harness/sdk_harness.py` (`ClaudeSDKHarness` — wraps the existing SDK call behind the ABC from HMIG-001A).
- Lazy import of `guardkitfactory.harness.LangGraphHarness` for the `GUARDKIT_HARNESS=langgraph` path.
- Env-var dispatch in `_invoke_with_role` (`os.environ.get("GUARDKIT_HARNESS", "sdk")`).
- `pyproject.toml` adds `guardkitfactory>=0.1,<1` to the `autobuild` optional dep group.
- `guardkit doctor` extension to report active harness + guardkitfactory version.
- New tests `tests/orchestrator/test_agent_invoker_langgraph.py` covering the LangGraph path with a stub model wired through guardkitfactory's `LangGraphHarness`.
- New README `guardkit/orchestrator/harness/README.md` documenting the substrate switch, cross-repo dependency, and cutover-day flip.

### Explicitly out of scope (deferred to other tasks)

- **Second SDK call site at `agent_invoker.py:5270+`** (direct-mode TaskWork dispatch). It re-imports `claude_agent_sdk` and runs its own query loop. Per parent review's §3 trace, that boundary is a separate refactor — file a follow-up task `TASK-HMIG-006.1` to migrate the direct-mode path once this task lands.
- **Third SDK call site at `coach_validator.py:1869+`** (Coach's independent test execution). AC-004 explicitly says CoachValidator is not modified by this task.
- **Migration of `_extract_partial_from_messages` (line 299) and `_track_tool_use` (line 1220) to dispatch on HarnessEvent.** These already use duck-typing (`type(block).__name__ == "ToolUseBlock"`) so they keep working if the SDK harness propagates raw SDK objects via `HarnessEvent.raw`. See §4 Design Decision D-1 below.
- **Coverage of `coach_validator.py:1992` (`isinstance(message, AssistantMessage)`).** That's the Coach's own SDK invocation, not consuming the Player's events.

### Notes on frozen-path policy

`guardkit/orchestrator/agent_invoker.py` was a frozen path through the TASK-REV-ABST window. The freeze closed 2026-05-17 (3 days before this work starts), so no override is required. However, the change is a NEW_GATE-adjacent refactor of a load-bearing module; the commit message must reference review §10 and explicitly name this as a structural refactor that preserves the existing test surface (AC-008).

---

## 2. Files to create / modify

### Create (4 new files)

| Path | Purpose | Est. LOC |
|---|---|---|
| `guardkit/orchestrator/harness/sdk_harness.py` | `ClaudeSDKHarness` — wraps the existing `query()` + `ClaudeAgentOptions` + async-message-stream loop. Yields `HarnessEvent` variants with `.raw` populated. | ~220 |
| `guardkit/orchestrator/harness/README.md` | Substrate switch documentation (AC-010). Covers env-var contract, cross-repo dep, cutover-day flip. | ~120 |
| `tests/orchestrator/test_agent_invoker_langgraph.py` | New tests covering `GUARDKIT_HARNESS=langgraph` dispatch path with a stub model. | ~180 |
| `tests/orchestrator/harness/test_sdk_harness.py` | New tests for the `ClaudeSDKHarness` adapter itself — translation of SDK message types → `HarnessEvent`, session_id capture, exception mapping. | ~200 |

### Modify (5 existing files)

| Path | Change | Est. delta |
|---|---|---|
| `guardkit/orchestrator/agent_invoker.py` | Refactor `_invoke_with_role` to dispatch through `HarnessAdapter` via env-var selector. Preserve heartbeat, cancellation monitor, latency measurement, sdk_debug instrumentation, and `_emit_llm_call_event` as orchestrator-side concerns. | -180 / +90 net |
| `guardkit/orchestrator/harness/__init__.py` | Re-export `ClaudeSDKHarness` and the env-var selector helper. | +15 |
| `pyproject.toml` | Add `guardkitfactory>=0.1,<1` to `[project.optional-dependencies].autobuild` AND add `guardkitfactory = { path = "../guardkitfactory", editable = true }` to `[tool.uv.sources]` (fleet convention from jarvis/specialist-agent nats-core pattern — see D-5). | +4 |
| `guardkit/cli/doctor.py` *(or equivalent)* | Report active `GUARDKIT_HARNESS` value + `guardkitfactory.__version__` if importable. | +30 |
| `tests/orchestrator/test_agent_invoker_sdk_errors.py` | Re-baseline imports if needed — should pass unchanged under default `GUARDKIT_HARNESS=sdk` (AC-008). | minimal |

**Net delta**: ~+685 LOC across 9 files. Original task estimate is 250 LOC of refactor; the difference is the test surface (the byte-compat parity gate from AC-004 is non-trivial).

---

## 3. Architecture

### Current shape (lines 2359-2740)

```
AgentInvoker._invoke_with_role(prompt, agent_type, allowed_tools, ...)
  ├── SDK import + ClaudeAgentOptions construction
  ├── _cancel_monitor task (orchestrator concern)
  ├── _install_sdk_cleanup_handler (orchestrator concern)
  ├── measure_latency context (orchestrator concern)
  ├── asyncio.timeout(self.sdk_timeout_seconds) (orchestrator concern)
  ├── async_heartbeat context (orchestrator concern)
  ├── gen = query(prompt, options)              ← SDK boundary START
  ├── while True: gen_iter.__anext__()
  │     ├── MessageParseError / ValueError → skip + warn
  │     ├── check_assistant_message_error(message)
  │     ├── _track_tool_use(message)
  │     ├── sdk_debug.preserve_event
  │     ├── ToolUseBlock logging (specialist-path only)
  │     └── isinstance(message, ResultMessage) → capture session_id, drain, break
  ├── Post-stream unparseable bookkeeping        ← SDK boundary END
  ├── CancelledError handler → _extract_partial_from_messages
  ├── _emit_llm_call_event (orchestrator concern)
  └── Exception cascade: CLINotFoundError, ProcessError, CLIJSONDecodeError, ValueError, generic
```

### Target shape

```
AgentInvoker._invoke_with_role(prompt, agent_type, allowed_tools, ...)
  ├── harness = _select_harness(agent_type, allowed_tools, model)  ← NEW
  ├── _cancel_monitor task (orchestrator concern, unchanged)
  ├── measure_latency context (orchestrator concern, unchanged)
  ├── async_heartbeat context (orchestrator concern, unchanged)
  ├── async with asyncio.timeout(self.sdk_timeout_seconds):
  │     async for event in harness.invoke(prompt, role, tools, cwd, timeout_seconds):
  │           ├── response_events.append(event)
  │           ├── if event.raw is not None: _track_tool_use(event.raw)   ← duck-typed today
  │           ├── if event.raw is not None: sdk_debug.preserve_event(event.raw)
  │           ├── if event.raw is not None: check_assistant_message_error(event.raw)
  │           └── isinstance(event, ResultMessageEvent) → capture session_id, break
  ├── CancelledError handler → _extract_partial_from_messages (uses event.raw)
  ├── _emit_llm_call_event (uses event.raw for token extraction)
  └── Exception cascade: substrate-specific exceptions wrapped by harness;
                         orchestrator catches AgentInvocationError + asyncio.TimeoutError
```

### New module: `guardkit/orchestrator/harness/sdk_harness.py`

```python
class ClaudeSDKHarness(HarnessAdapter):
    """HarnessAdapter wrapping claude-agent-sdk's query() + ClaudeAgentOptions.

    Preserves the existing TASK-FIX-7A03 message-parse resilience and
    TASK-RFX-B20B session_id capture by translating SDK-native types
    to HarnessEvent variants while populating event.raw with the
    original SDK message. Downstream consumers in agent_invoker.py
    (_extract_partial_from_messages, _track_tool_use,
    _emit_llm_call_event) keep working unchanged because they
    inspect event.raw with duck-typing (type(...).__name__ == ...).
    """

    def __init__(self, *, sdk_timeout_seconds: int, allowed_tools: list[str],
                 permission_mode: str, model: Optional[str] = None,
                 resume_session_id: Optional[str] = None,
                 max_turns: int, sdk_debug_dir: Optional[Path] = None) -> None:
        ...

    async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
        # Lazy import claude_agent_sdk inside invoke (matches existing
        # ImportError diagnosis at lines 2399-2420). Re-raise as
        # AgentInvocationError with the same diagnostic message.
        try:
            from claude_agent_sdk import (
                query, ClaudeAgentOptions, CLINotFoundError,
                ProcessError, CLIJSONDecodeError,
                AssistantMessage, ResultMessage,
            )
        except ImportError as e:
            raise AgentInvocationError(...)  # preserve current diagnosis

        try:
            from claude_agent_sdk._errors import MessageParseError
        except ImportError:
            class MessageParseError(Exception): ...  # sentinel

        options = ClaudeAgentOptions(...)
        gen = query(prompt=prompt, options=options)
        try:
            gen_iter = gen.__aiter__()
            unparseable = 0
            while True:
                try:
                    message = await gen_iter.__anext__()
                except StopAsyncIteration:
                    break
                except (MessageParseError, ValueError) as parse_err:
                    unparseable += 1
                    logger.warning(...)
                    continue

                # Translate SDK message → HarnessEvent
                if isinstance(message, AssistantMessage):
                    text = _extract_text(message)
                    yield AssistantMessageEvent(text=text, raw=message)
                elif isinstance(message, ResultMessage):
                    self._session_id = getattr(message, "session_id", None)
                    yield ResultMessageEvent(
                        session_id=self._session_id,
                        stop_reason=getattr(message, "stop_reason", None),
                        usage=getattr(message, "usage", None),
                        raw=message,
                    )
                    break  # ResultMessage is terminal
                # NB: ToolUseBlock blocks live INSIDE AssistantMessage.content
                # in the SDK shape. They are NOT separate stream events on the
                # SDK side. Per D-1 below, we do NOT explode them into separate
                # ToolUseEvent yields — downstream consumers iterate the raw
                # AssistantMessage.content list themselves.

            if unparseable > 0:
                ...  # mirror existing TASK-FIX-7A03 post-stream bookkeeping
        finally:
            if gen is not None:
                with suppress(Exception):
                    async with asyncio.timeout(5):
                        await gen.aclose()

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @property
    def supports_resume(self) -> bool:
        return True
```

### Env-var dispatch helper

```python
# guardkit/orchestrator/harness/__init__.py

def select_harness(env_var: str = "GUARDKIT_HARNESS", **harness_kwargs) -> HarnessAdapter:
    """Construct the harness implementation named by GUARDKIT_HARNESS.

    Default: "sdk" (ClaudeSDKHarness). Set GUARDKIT_HARNESS=langgraph
    to dispatch through guardkitfactory.harness.LangGraphHarness.

    Lazy imports the LangGraph path so guardkitfactory is not required
    for "sdk" callers (matches AC-003).
    """
    name = os.environ.get(env_var, "sdk").lower()
    if name == "sdk":
        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness
        return ClaudeSDKHarness(**harness_kwargs)
    if name == "langgraph":
        try:
            from guardkitfactory.harness import LangGraphHarness  # lazy
        except ImportError as e:
            raise AgentInvocationError(
                f"GUARDKIT_HARNESS=langgraph but guardkitfactory is not "
                f"importable: {e}. Install with `pip install guardkitfactory` "
                f"or `pip install -e ../guardkitfactory` for operator-side dev."
            ) from e
        return LangGraphHarness(**_translate_kwargs_for_langgraph(harness_kwargs))
    raise AgentInvocationError(f"Unknown GUARDKIT_HARNESS value: {name!r}. "
                               f"Expected 'sdk' or 'langgraph'.")
```

---

## 4. Design decisions

### D-1: Keep `event.raw` populated; do not migrate `_track_tool_use` / `_extract_partial_from_messages` to HarnessEvent

**Decision**: `ClaudeSDKHarness` populates `HarnessEvent.raw` with the original SDK message. Functions in `agent_invoker.py` that inspect message internals (`_track_tool_use`, `_extract_partial_from_messages`, `_emit_llm_call_event`) continue to operate on `event.raw` with their existing duck-typing.

**Why**:
- AC-008 (existing tests pass under `GUARDKIT_HARNESS=sdk`) is the hardest gate. Existing tests patch `claude_agent_sdk.query` and feed `AssistantMessage(content=[TextBlock, ToolUseBlock])` shapes. If we migrate the downstream functions to HarnessEvent dispatch in this task, every test fixture changes.
- The existing duck-typing (`type(block).__name__ == "ToolUseBlock"`) means the functions are already lenient about the *exact* type they receive — they only need the shape.
- The HarnessEvent taxonomy in `adapter.py` is *flatter* than the SDK shape (separate `AssistantMessageEvent` + `ToolUseEvent` events, not blocks-inside-message). Translating in both directions at this boundary risks the byte-compat surface (AC-004).

**Trade-off**: `LangGraphHarness` skeleton yields `AssistantMessageEvent` with `raw=` set to the LangChain `dict` result, which means `_track_tool_use(event.raw)` will look for `.content` on a dict and find nothing — `_track_tool_use` will no-op (graceful). `_extract_partial_from_messages` likewise becomes lossy on the LangGraph path. That is acceptable for cutover Day 0 because:
- The LangGraph path is opt-in (`GUARDKIT_HARNESS=langgraph`) through D-7 (2026-06-08); only canary tasks (HMIG-009) exercise it.
- Migration of these helper functions to HarnessEvent dispatch is a separate task (`TASK-HMIG-006.2`) before the cutover-day flip.

**Alternative considered**: Migrate `_extract_partial_from_messages` + `_track_tool_use` to dispatch on `HarnessEvent` variants now. Rejected because of the AC-008 test churn and because the cutover-day flip is the right moment for that breaking change, not Wave 2.

### D-2: SDK harness exposes `supports_resume = True`; LangGraph harness `supports_resume = False`

**Decision**: Per AC-007. The orchestrator's resume path at `agent_invoker.py:1751` already passes `resume_session_id` into `_invoke_with_role`. The SDK harness accepts and uses it. The LangGraph harness ignores it and orchestrator gracefully degrades: if `harness.supports_resume is False`, the orchestrator logs a warning when a resume_session_id is offered and proceeds with a fresh session.

**Why**: Matches the parent review's D-07 decision (JSON-on-disk checkpointing stays as AutoBuild's resume mechanism for the migration; the LangGraph checkpointer integration is deferred).

### D-3: Orchestrator-side concerns stay in `agent_invoker.py`

The following are **not** moved into the harness:

| Concern | Stays in agent_invoker.py because... |
|---|---|
| `async_heartbeat` context | Substrate-agnostic, paired with the orchestrator's progress-display lifecycle. |
| `asyncio.timeout(sdk_timeout_seconds)` | The harness has its own `timeout_seconds` parameter — orchestrator wraps for defense-in-depth. |
| `_cancel_monitor` task + `_kill_child_claude_processes` | The kill path is SDK-subprocess specific, but `_cancel_monitor` itself just polls `_cancellation_event`. We keep the polling in orchestrator and let each harness handle its own subprocess kill. The SDK harness exposes a `cancel()` coroutine that orchestrator calls when the event fires; LangGraph harness's `cancel()` is a no-op (in-process). |
| `measure_latency` | Wall-clock measurement around the substrate call. |
| `sdk_debug.preserve_prompt` / `preserve_event` | Already substrate-agnostic (writes JSONL of whatever shape passed). |
| `_emit_llm_call_event` | Uses `extract_token_usage(response_messages)` which is itself duck-typed on SDK shape. Per D-1, keep on `event.raw`. |

**Why**: The harness boundary should be a *thin substrate seam*, not a transplant of all orchestrator concerns. The ABC in `adapter.py` already commits to this — `invoke()` only takes prompt/role/tools/cwd/timeout, not heartbeat or cancellation primitives.

### D-4: SDK-specific exception types translate to `AgentInvocationError` *inside* the harness

`CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError` are SDK-specific and currently caught in `_invoke_with_role` to translate to `AgentInvocationError`. The harness now owns those translations — orchestrator only sees `AgentInvocationError` and `asyncio.TimeoutError`. This keeps the orchestrator's exception cascade substrate-agnostic.

**Architectural review tightening (Phase 2.5B)**: `ClaudeSDKHarness.invoke()` ALSO catches `ValueError` raised inside the SDK message-stream translation loop and re-raises it as `AgentInvocationError(error_class="ValueError")` before it escapes the harness. The orchestrator's existing `except ValueError` clause at `agent_invoker.py:2715` is preserved as a catch-all net for non-harness `ValueError` (e.g. from `select_harness()`, from `_emit_llm_call_event`, from event-dispatch glue), but it can no longer fire from harness-internal paths. This makes the harness the **single point** of SDK-exception normalisation and removes the structural ambiguity that would otherwise result from the refactor.

### D-6: Harness instances are single-use per invocation

**Architectural review clarification (Phase 2.5B)**: `select_harness()` returns a freshly constructed `HarnessAdapter` for each `_invoke_with_role` call. Concrete consequence: `_install_sdk_cleanup_handler` is called **inside `ClaudeSDKHarness.invoke()`**, not in `__init__`. The cleanup handler installation is bound to the lifetime of the SDK subprocess, which is per-invocation.

**Why**: A reusable harness instance would require explicit state-reset between invocations (last_session_id, last_partial_report, debug_dir, etc.), and the existing per-call construction cost is negligible (~1ms). Single-use harnesses also make test fixtures cleaner — each test constructs its own harness with stub model + stub options, no shared-state contamination across tests.

### D-7: LangGraph-path degradations are documented, not fixed

**Architectural review tightening (Phase 2.5B)**: The LangGraph path consciously degrades these signals through D-1 (`event.raw` channel keeps SDK-shape downstream consumers happy at the cost of LangGraph-side fidelity):

| Downstream signal | SDK path | LangGraph path (Wave 2) | Fixed in |
|---|---|---|---|
| `_emit_llm_call_event` input/output tokens | Populated from `ResultMessage.usage` | `None` (LangChain dict has different shape) | TASK-HMIG-006.2 |
| `_track_tool_use` progress counters | Populated from `ToolUseBlock` blocks | No-op (LangChain dict has no `.content` list) | TASK-HMIG-006.2 |
| `_extract_partial_from_messages` | Full text/tool-call extraction | Lossy (returns empty lists) | TASK-HMIG-006.2 |
| `player_turn_N.json` `tool_calls` field | Populated when tools used | `[]` on LangGraph until 006.2 | TASK-HMIG-006.2 |

**These are documented divergences, not bugs.** `guardkit/orchestrator/harness/README.md` (AC-010) must list every Wave-2 divergence explicitly with the corresponding follow-up task ID. Per `.claude/rules/absence-of-failure-is-not-success.md`, the AC-004 byte-compat test must NOT silently accept empty fixtures — see §6 below for the tightened test plan.

### D-5: pyproject pinning — sibling-repo editable pattern (fleet convention)

**Phase 2.8 OQ-1 resolution**: Use the `[tool.uv.sources]` sibling-repo editable path pattern that jarvis and specialist-agent already use for `nats-core`. This is the established fleet convention for unpublished internal packages — no PyPI publication required, no git+https URL pinning, no deferral.

Per AC-005, `docs/guides/portfolio-python-pinning.md`, AND the jarvis/specialist-agent `nats-core` precedent:

```toml
[project.optional-dependencies]
autobuild = [
    "claude-agent-sdk>=0.1.49,<0.2",
    "guardkitfactory>=0.1,<1",  # AC-005 — version-pinned, sibling-repo resolved
]

[tool.uv.sources]
guardkitfactory = { path = "../guardkitfactory", editable = true }
```

**How this works**:
- The `>=0.1,<1` pin in `[project.optional-dependencies].autobuild` is the version contract end users see.
- `[tool.uv.sources]` tells `uv` (and editable installs via pip) to resolve `guardkitfactory` from the sibling worktree at `../guardkitfactory` in editable mode, not from PyPI.
- Operator-side dev: `pip install -e ".[autobuild]"` or `uv sync --extra autobuild` pulls in the editable sibling. Matches jarvis's existing setup for nats-core.
- Future PyPI publication: if/when guardkitfactory ships to PyPI, the `[tool.uv.sources]` block can be removed and end users resolve normally. The version pin stays.

**Why this pattern, not git+https**: The `graphiti-core @ git+https://...` precedent exists in pyproject.toml today, but the jarvis/specialist-agent `nats-core` pattern is the *newer* fleet convention for sibling-repo internal packages — preserving editability for portfolio-style multi-repo dev. We follow the new pattern.

`guardkitfactory` stays in the `autobuild` optional dep group, not core, so users who don't run autobuild don't need the cross-repo dep at all.

---

## 5. Phased rollout

| Phase | Deliverable | Verifiable outcome |
|---|---|---|
| **3a** | `ClaudeSDKHarness` skeleton + `select_harness()` helper + `harness/__init__.py` re-exports + new `harness/test_sdk_harness.py` (unit tests for the adapter in isolation, no orchestrator integration yet) | `pytest tests/orchestrator/harness/test_sdk_harness.py` green |
| **3b** | Refactor `_invoke_with_role` to dispatch through `select_harness()`. Default env-var `sdk` → ClaudeSDKHarness. No behavioural change. | `pytest tests/orchestrator/test_agent_invoker_*.py` green (AC-008) |
| **3c** | Add `GUARDKIT_HARNESS=langgraph` dispatch + lazy `guardkitfactory` import + `test_agent_invoker_langgraph.py` with stub model | New tests pass; existing SDK tests still pass (AC-008, AC-009) |
| **3d** | `pyproject.toml` dep add + `guardkit doctor` extension | `pip install -e ".[autobuild]"` resolves guardkitfactory; `guardkit doctor` prints `Active harness: sdk` and `guardkitfactory: x.y.z` |
| **3e** | `guardkit/orchestrator/harness/README.md` | AC-010 satisfied |
| **4** | Run full suite. Compilation + tests via Coach's independent pytest pass. | Zero failures with `GUARDKIT_HARNESS=sdk`. New langgraph-tagged tests pass with `GUARDKIT_HARNESS=langgraph`. |
| **5** | Code review (strict mode: SOLID/DRY/YAGNI + security scan). | code-reviewer agent approves. |
| **5.5** | Plan audit. | Zero unjustified scope creep. |

---

## 6. Test strategy

### AC-008: Existing tests pass with `GUARDKIT_HARNESS=sdk`

- Existing fixtures (`stub_sdk.py`, `test_agent_invoker_sdk_errors.py`) patch `claude_agent_sdk.query`. They continue to work because `ClaudeSDKHarness` calls `query()` exactly as today.
- Add a `pytest.fixture(autouse=False)` `with_sdk_harness` that explicitly sets `os.environ["GUARDKIT_HARNESS"] = "sdk"` to insulate against test-suite ordering effects.
- No changes to the existing tests themselves (regression risk minimization).

### AC-009: New LangGraph-path tests

- Stub model: a `FakeChatModel` that returns deterministic AI messages, wired through `guardkitfactory.harness.LangGraphHarness(model=stub_model)`.
- Fixture worktree: temp dir under `tmp_path`.
- Cases:
  - Single-turn invocation yields exactly one `AssistantMessageEvent` + one `ResultMessageEvent` with `session_id=None`.
  - `harness.supports_resume == False` honoured.
  - `LangGraphHarnessError` raised when stub model raises.
  - Token-extraction graceful degradation: `_emit_llm_call_event` doesn't crash when `event.raw` is a LangChain dict.

### AC-004: Byte-compat on-disk artefacts

- This is the hardest gate. Add a parametrized test that runs the same fixture turn through both `GUARDKIT_HARNESS=sdk` and `GUARDKIT_HARNESS=langgraph` and asserts:
  - `player_turn_N.json` schema (top-level keys, value types) is identical
  - `coach_turn_N.json` schema is identical
- This test can be marked `skipif` when guardkitfactory is not installed, so the SDK-only test surface still runs.
- A schema-diff helper in `tests/orchestrator/harness/byte_compat_helpers.py` documents the AC-004 contract — every key/type difference between the two substrates is a contract violation.

**Architectural review tightening (Phase 2.5B)**: The schema-subset check **MUST be paired with a non-empty fixture** per `.claude/rules/absence-of-failure-is-not-success.md` ("pair every `count_failed == 0` rule with `count_attempted > 0`"). Without this, the schema-subset check passes trivially when both paths produce `tool_calls: []` — a false-green that hides the D-7 divergence.

**Required fixture surface for AC-004**:

| Fixture | SDK assertion | LangGraph assertion |
|---|---|---|
| `turn_with_text_only` | `tool_calls: []`, `text_blocks: ["..."]` | Identical (parity holds) |
| `turn_with_one_tool_use` | `tool_calls: [{"name": "Edit", "input_keys": ["file_path", "old_string", "new_string"]}]` | `tool_calls: []` (DOCUMENTED Wave-2 divergence per D-7) — test asserts the divergence explicitly, NOT parity |
| `turn_with_result_message` | `session_id: "<some-uuid>"` | `session_id: null` (per AC-007 — `supports_resume = False`) — test asserts the divergence explicitly |

The "divergence-asserting" test cases are not failures — they are the explicit known-divergence list that converts a potential false-green into a documented contract. When TASK-HMIG-006.2 lands, those assertions invert (from divergence-expected to parity-expected); that inversion is the verifiable signal that the helper-migration is complete.

### Coverage targets (strict intensity)

- Line coverage on `sdk_harness.py`: ≥ 85% (strict elevated bar)
- Branch coverage on `sdk_harness.py`: ≥ 80%
- Line coverage on the refactored portion of `agent_invoker.py:2359-2740`: ≥ 85%

---

## 7. Risks

| Severity | Risk | Mitigation |
|---|---|---|
| 🔴 HIGH | **AC-004 byte-compat parity is hard.** SDK and LangGraph produce different intermediate shapes. The `event.raw` channel (D-1) means token extraction, tool-use tracking, and partial-extract all return *less* information on the LangGraph path. The on-disk JSON may diverge in subtle ways (e.g. `tool_calls: []` vs `tool_calls: [{...}]`). | Schema-diff test (§6) is mandatory. If divergence surfaces, **fail the build** — do not silently diverge. The task description explicitly says "schema drift here breaks every downstream consumer." Pre-cutover, file follow-up `TASK-HMIG-006.2` to migrate the helpers to HarnessEvent dispatch and re-establish parity. |
| 🔴 HIGH | **Frozen-path NEW_GATE-adjacency.** This is a refactor of a load-bearing module that just came off freeze. Subtle regressions in cancellation, heartbeat, or session_id capture surface as autobuild stalls or duplicate turns. | Phase 4.5 fix loop (strict: 5 attempts) catches behavioural regressions via existing tests. Phase 2.5B arch review must explicitly score the cancellation + heartbeat + session_id preservation against the existing surface. |
| 🟡 MEDIUM | **Cross-repo dependency direction.** `guardkit` now depends on `guardkitfactory` at install time (not just at import time). End-user `pip install guardkit-py[autobuild]` must resolve guardkitfactory from PyPI. | Confirm guardkitfactory is published to the same index. If not, this task is blocked on guardkitfactory's release process. **Open question — see §9 OQ-1.** |
| 🟡 MEDIUM | **Lazy-import ordering.** `select_harness()` defers `from guardkitfactory.harness import LangGraphHarness` until the env-var is set to `langgraph`. If a test sets the env var but guardkitfactory isn't installed in that environment, the helpful diagnostic must be the *only* error the user sees — not a stack trace from deep inside LangChain. | Wrap the lazy import in `try/except ImportError` and raise `AgentInvocationError` with a portable diagnostic (matches the existing SDK ImportError pattern at line 2408-2420). |
| 🟡 MEDIUM | **Coach's independent SDK invocation (`coach_validator.py:1869+`) is out of scope but uses `AssistantMessage`/`UserMessage`/`ToolResultBlock` directly.** When Coach runs the LangGraph substrate later in the migration, *that* boundary will need its own harness dispatch. | Note in `harness/README.md` that Coach has its own SDK invocation (`TASK-HMIG-006.3` follow-up). This task does not touch it. |
| 🟢 LOW | **Heartbeat label preservation.** `heartbeat_label_override` is used for specialist-path differentiation (`"specialist:{name} invocation"`). Refactor must preserve. | Test covers it explicitly. |
| 🟢 LOW | **`_install_sdk_cleanup_handler` is SDK-specific.** Currently called inside `_invoke_with_role`. Move into `ClaudeSDKHarness.__init__` or the `invoke()` method, not into the orchestrator. | Mechanical move. |

---

## 8. Acceptance criteria mapping

| AC | Phase | Verified by |
|---|---|---|
| AC-001 (`_invoke_with_role` substrate-agnostic) | 3b | `pytest tests/orchestrator/test_agent_invoker_sdk_errors.py` (unchanged passing) + new env-var dispatch test |
| AC-002 (`sdk_harness.py` wraps SDK invocation) | 3a | `pytest tests/orchestrator/harness/test_sdk_harness.py` |
| AC-003 (lazy `guardkitfactory` import) | 3c | `pytest tests/orchestrator/test_agent_invoker_langgraph.py::test_lazy_import_when_sdk_default` |
| AC-004 (byte-compat artefacts) | 4 | Parametrized schema-diff test, §6 |
| AC-005 (pyproject dep) | 3d | `pip install -e ".[autobuild]"` resolves guardkitfactory |
| AC-006 (doctor reports harness) | 3d | `guardkit doctor` CLI output |
| AC-007 (resume support) | 3a, 3c | Tests for `supports_resume` property on each harness |
| AC-008 (existing tests pass under sdk default) | 3b | Full pre-existing test suite green |
| AC-009 (langgraph tests) | 3c | `tests/orchestrator/test_agent_invoker_langgraph.py` green |
| AC-010 (README) | 3e | `guardkit/orchestrator/harness/README.md` present and reviewed |

---

## 9. Open questions for Phase 2.8 checkpoint

| ID | Question | Recommendation |
|---|---|---|
| OQ-1 | ~~Is `guardkitfactory>=0.1` published to PyPI yet~~ | **RESOLVED (Phase 2.8)**: Use the `[tool.uv.sources]` sibling-repo editable pattern — the fleet convention from jarvis/specialist-agent for `nats-core`. Both options (a) PyPI defer and (b) git+https pin from the v1 plan were wrong. See updated D-5 for the actual mechanism. |
| OQ-2 | The 4 new test files add ~580 LOC of test code. Strict intensity demands ≥ 85% coverage. The byte-compat parity test (AC-004) is genuinely the hardest part — should the parity test be (a) a strict equality check on the JSON shape, (b) a schema-subset check (LangGraph path can produce *less* info, never different shape), or (c) a side-by-side documented divergence list with a regression-only check? | Recommend (b) for Wave-2; (a) is the long-term target for cutover-day. Document the divergences in `harness/README.md` and file `TASK-HMIG-006.2` for the helper-function migration that achieves (a). |
| OQ-3 | Should `select_harness()` live in `guardkit.orchestrator.harness.__init__` or in a separate `harness/selector.py`? The ABC + Event types in `adapter.py` are intentionally substrate-free. Adding `select_harness()` to `__init__.py` would make the package import `os` (currently doesn't). | Recommend separate `harness/selector.py` to keep `adapter.py` as a pure abstract surface and `__init__.py` as a thin re-exports module. |
| OQ-4 | ~~Filing timing for follow-up tasks~~ | **RESOLVED (Phase 2.8)**: File 006.1 / 006.2 / 006.3 during Phase 3 as `backlog` tasks under `tasks/backlog/autobuild-harness-migration/`. Matches jarvis convention of filing follow-ups immediately when scope is carved out. Tasks become Wave 3 candidates. |

---

## 10. Estimated effort breakdown

| Phase | Activity | Estimate |
|---|---|---|
| 3a | `ClaudeSDKHarness` + selector + unit tests | 2h |
| 3b | `_invoke_with_role` refactor (preserve all 10+ inline cross-cutting concerns) | 3h |
| 3c | LangGraph dispatch + lazy import + new tests with stub model | 1.5h |
| 3d | pyproject + doctor extension | 0.5h |
| 3e | README | 0.5h |
| 4 | Test execution + byte-compat parity validation | 1.5h |
| 4.5 | Fix loop (strict: 5 attempts allowed) | 0.5h budgeted |
| 5 | Code review (strict: full SOLID/DRY/YAGNI + security scan) | 0.25h |
| 5.5 | Plan audit | 0.25h |
| **Total** | | **~10h** (matches frontmatter estimate) |

---

## 11. Definition of done

- [ ] All 10 ACs pass per §8 mapping
- [ ] Existing `tests/orchestrator/test_agent_invoker_*.py` green under `GUARDKIT_HARNESS=sdk` (AC-008)
- [ ] New `tests/orchestrator/test_agent_invoker_langgraph.py` green under `GUARDKIT_HARNESS=langgraph` (AC-009)
- [ ] `tests/orchestrator/harness/test_sdk_harness.py` green (new adapter unit tests)
- [ ] Byte-compat parity test passes (AC-004, per OQ-2 chosen variant)
- [ ] Coverage: ≥ 85% line / ≥ 80% branch on changed code (strict intensity)
- [ ] No new compile errors in `guardkit/orchestrator/`
- [ ] Phase 5.5 plan audit: 0 unjustified scope creep
- [ ] Commit message references review §10 (frozen-path-touch justification)
- [ ] Follow-up tasks filed per OQ-4
