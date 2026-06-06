---
task_id: TASK-HMIG-006.3
title: Migrate CoachValidator._run_tests_via_sdk to HarnessAdapter substrate seam
status: DESIGN_APPROVED
effort_hours: 4
complexity: 5
---

# TASK-HMIG-006.3 Implementation Plan

## 1. Files to modify

### `guardkit/orchestrator/quality_gates/coach_validator.py`

**Lines 2344–2618** — the entire `_run_tests_via_sdk` async method.

The current method body:
- Lines 2364–2378: lazy-imports `claude_agent_sdk` symbols directly.
- Lines 2390–2394: lazy-imports `MessageParseError` sentinel.
- Lines 2410–2419: constructs `ClaudeAgentOptions` with `env=`, `allowed_tools`, `permission_mode`, `max_turns`.
- Lines 2424–2435: sdk_debug preservation of prompt + options.
- Lines 2437–2508: message-loop iterating `query(prompt, options)`, walking `AssistantMessage` and `UserMessage/ToolResultBlock`.
- Lines 2515–2568: tri-state `bash_is_error` → `IndependentTestResult` assembly.
- Lines 2570–2618: exception cascade (`TimeoutError`, `CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError`, generic `Exception`).

The method signature does not change:
```python
async def _run_tests_via_sdk(self, test_cmd: str) -> IndependentTestResult:
```

The caller at line 2867 (`loop.run_until_complete(self._run_tests_via_sdk(test_cmd))`) does not change.

**Specific changes inside `_run_tests_via_sdk`:**

1. **Remove lines 2364–2394** (the direct `from claude_agent_sdk import ...` and `MessageParseError` sentinel blocks). These imports move inside `ClaudeSDKHarness.invoke` where they already live; they are not needed at the Coach call site after the migration.

2. **Remove lines 2410–2419** (`options_kwargs` dict and `options = ClaudeAgentOptions(...)` construction). Replaced by `select_harness(...)` call — see Step D for env-plumbing consequence.

3. **Remove lines 2424–2435** (sdk_debug `preserve_prompt` call against `options`). After migration, the harness owns no external `options` object the Coach holds. The debug-preservation responsibility moves into `ClaudeSDKHarness.invoke` (already partially present for the Player path; Coach-specific sdk_debug is a separate follow-up if needed). The `_sdk_debug_dir` local and its subsequent `_sdk_preserve_event` calls at line 2474 are also removed.

4. **Replace lines 2437–2508** (the `gen = query(...)` message loop) with a harness-driven event loop — see Step B.

5. **Keep lines 2515–2568** (the tri-state `bash_is_error` → `IndependentTestResult` assembly) unchanged. The output-assembly logic is substrate-agnostic and correct; only the source of `bash_is_error` / `bash_output` / `collected_text` changes.

6. **Replace lines 2570–2618** (exception cascade) with a single catch for `AgentInvocationError` (re-raised from inside the harness per Design Decision D-4). `CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError` are no longer visible to Coach after migration. Keep `asyncio.TimeoutError` handling unchanged (line 2570–2579).

**Net shape of the new `_run_tests_via_sdk` body** (pseudocode):
```python
async def _run_tests_via_sdk(self, test_cmd: str) -> IndependentTestResult:
    import asyncio, time
    from guardkit.orchestrator.harness import (
        select_harness, AssistantMessageEvent, ToolResultEvent, ResultMessageEvent,
    )
    from guardkit.orchestrator.exceptions import AgentInvocationError

    start_time = time.time()
    prompt = f"Run the following test command..."

    try:
        model = self._get_coach_test_model()
        # env plumbing: see Step D
        current_pythonpath = os.environ.get("PYTHONPATH", "")
        worktree_str = str(self.worktree_path)
        new_pythonpath = f"{worktree_str}:{current_pythonpath}" if current_pythonpath else worktree_str
        os.environ["PYTHONPATH"] = new_pythonpath  # context-managed mutation — see Step D

        harness = select_harness(
            sdk_timeout_seconds=self.test_timeout,
            allowed_tools=["Bash"],
            permission_mode="bypassPermissions",
            max_turns=1,
            model=model,
            cwd=self.worktree_path,
        )

        collected_text: List[str] = []
        bash_output: Optional[str] = None
        bash_is_error: Optional[bool] = None

        async with asyncio.timeout(self.test_timeout):
            async for event in harness.invoke(
                prompt=prompt,
                role="coach_test",
                tools=["Bash"],
                cwd=self.worktree_path,
                timeout_seconds=self.test_timeout,
            ):
                if isinstance(event, AssistantMessageEvent):
                    collected_text.append(event.text)
                elif isinstance(event, ToolResultEvent):
                    # see Step B for is_error tri-state handling
                    bash_output = event.content if isinstance(event.content, str) \
                        else self._extract_content_text(event.content)
                    bash_is_error = event.is_error if event.is_error else None  # see Step B
                elif isinstance(event, ResultMessageEvent):
                    break

        # lines 2515–2568 unchanged (tri-state branch → IndependentTestResult)

    except asyncio.TimeoutError:
        # unchanged (lines 2570–2579)
    except AgentInvocationError as e:
        duration = time.time() - start_time
        logger.error(f"SDK coach test execution failed (AgentInvocationError): {e}")
        raise
    except Exception as e:
        # catch-all retained for non-harness exceptions (os.environ restore failure etc.)
        duration = time.time() - start_time
        logger.error(f"SDK coach test execution failed (error_class={type(e).__name__}): {e}")
        raise
```

### `tests/unit/test_coach_validator.py`

**Class `TestSdkEnvMerge` (lines 5323–5363)** — existing AC-003 surface.

These tests patch `sys.modules["claude_agent_sdk"]` with `_make_mock_sdk(captured_env)` and then call `asyncio.run(validator._run_tests_via_sdk(...))`. After migration the direct `ClaudeAgentOptions` construction moves inside `ClaudeSDKHarness`, so `CapturingOptions.__init__` will no longer be called at the Coach method level.

Two options exist:
- **Option A (preferred)**: Redirect the mock to patch at the harness boundary. Patch `sys.modules["claude_agent_sdk"]` with the existing `_make_mock_sdk` mock — since `ClaudeSDKHarness.invoke` still does `from claude_agent_sdk import ClaudeAgentOptions` inside its body, the mock is still resolved. The existing `CapturingOptions` class captures `kwargs.get("env", {})` from the harness-side construction. This option requires **zero changes** to `_make_mock_sdk` or the test bodies if the `env=` kwarg flows through `select_harness` → `ClaudeSDKHarness.__init__` → `ClaudeAgentOptions`. See Step D for how `env` plumbing is resolved.
- **Option B (fallback)**: If `ClaudeSDKHarness` does not accept an `env` kwarg, update `_make_mock_sdk` to capture `ClaudeAgentOptions` kwargs from wherever they're constructed.

The tests themselves (`test_sdk_env_inherits_os_environ_keys`, `test_sdk_env_pythonpath_prepends_worktree`) assert the same invariants either way and do not need body changes under Option A.

**New AC-004 test class** `TestCoachHarnessMigration` — added to the same file after the `TestSdkEnvMerge` block (after line 5363). See Section 5 for the three tests.

## 2. Files to create

No new files. The AC-004 tests are added to the existing `tests/unit/test_coach_validator.py` rather than a standalone file to keep the SDK-env mock fixture (`_make_mock_sdk`) in the same module scope and avoid a separate import chain.

If the `env` plumbing decision (Step D) requires a `ClaudeSDKHarness` constructor change, that change lives in `guardkit/orchestrator/harness/sdk_harness.py` (no new file needed).

## 3. External dependencies

None. The migration reuses:
- `guardkit.orchestrator.harness.select_harness` (already imported by `agent_invoker.py`)
- `guardkit.orchestrator.harness.AssistantMessageEvent`, `ToolResultEvent`, `ResultMessageEvent` (already in `__all__`)
- `guardkit.orchestrator.exceptions.AgentInvocationError` (already used in `coach_validator.py` elsewhere)

`guardkit.orchestrator.harness` is already importable from `coach_validator.py`'s package context.

## 4. Implementation phases

### Step A — Wire `select_harness` into `_run_tests_via_sdk`

Replace the `ClaudeAgentOptions` construction block (lines 2410–2419) with:

```python
from guardkit.orchestrator.harness import (
    select_harness,
    AssistantMessageEvent,
    ToolResultEvent,
    ResultMessageEvent,
)
harness = select_harness(
    sdk_timeout_seconds=self.test_timeout,
    allowed_tools=["Bash"],
    permission_mode="bypassPermissions",
    max_turns=1,
    model=model,         # None is handled by select_harness / ClaudeSDKHarness
    cwd=self.worktree_path,
)
```

Key differences from the Player dispatch in `agent_invoker.py:2855–2874`:
- `sdk_timeout_seconds=self.test_timeout` (not `self.sdk_timeout_seconds` — Coach has its own independent timeout, typically 300s, stored in `self.test_timeout`)
- No `resume_session_id` (Coach never resumes)
- No `sdk_debug_dir`, no `cleanup_handler_installer` (simplification; the Coach test path has no heartbeat infra)
- No `setting_sources` (default `["project"]` inside `ClaudeSDKHarness` is fine)

The `select_harness` call pops `cwd` before delegating to `ClaudeSDKHarness.__init__`, which has no `cwd` parameter (it receives `cwd` later in `invoke()`). This is the same TASK-FIX-002R-CONSUME pattern already handling the Player path.

### Step B — Event-loop translation

Replace the `gen = query(...)` while-loop (lines 2455–2508) with:

```python
async with asyncio.timeout(self.test_timeout):
    async for event in harness.invoke(
        prompt=prompt,
        role="coach_test",
        tools=["Bash"],
        cwd=self.worktree_path,
        timeout_seconds=self.test_timeout,
    ):
        if isinstance(event, AssistantMessageEvent):
            collected_text.append(event.text)
        elif isinstance(event, ToolResultEvent):
            content = event.content
            if isinstance(content, str):
                bash_output = content
            else:
                bash_output = self._extract_content_text(content)
            # Tri-state preservation: ToolResultEvent.is_error defaults to False
            # (not None) per the dataclass definition at adapter.py:75.
            # The SDK harness currently does NOT yield ToolResultEvent at all
            # (it only yields AssistantMessageEvent, ToolUseEvent, ResultMessageEvent).
            # This means Coach's pre-migration bash_is_error=None (heuristic) path
            # becomes the dominant case on the SDK harness post-migration too —
            # but via the absence of a ToolResultEvent, not via is_error=None.
            # The heuristic branch (lines 2544–2568) remains live and correct.
            # If ToolResultEvent is never yielded, bash_is_error stays None
            # and the heuristic runs. Document this as a design note, not a bug.
            # If a future harness does yield ToolResultEvent with is_error=False,
            # the False→True→False ternary below maps it correctly:
            bash_is_error = True if event.is_error else None
            # Rationale: is_error=False from the harness means "tool ran, no error"
            # but not "tests passed" — that's determined by output text (heuristic).
            # is_error=True means the tool invocation itself errored; map to True.
            # is_error=False maps to None to preserve the heuristic path.
        elif isinstance(event, ResultMessageEvent):
            break
```

**Design call on tri-state**: `ToolResultEvent.is_error` is `bool` with default `False` (not `Optional[bool]`), confirmed at `adapter.py:75`. The pre-migration `ToolResultBlock.is_error` was tri-state (`None` if the SDK didn't set it). Post-migration, `False` means "tool ran without error" which maps semantically to "let the heuristic decide" (not "tests passed"). `True` means the Bash tool invocation errored and maps directly to `bash_is_error = True`. The `is_error=False → None` mapping intentionally keeps the heuristic branch alive for the SDK harness.

The `MessageParseError`/`ValueError` per-message skip and the `unparseable_count` tracking (lines 2463–2513) are **not needed** in the new loop because `ClaudeSDKHarness.invoke` already handles per-message resilience internally (TASK-FIX-7A03), raising `AgentInvocationError` only if all messages fail. The Coach loop is now a clean typed-event consumer.

### Step C — Preserve `asyncio.timeout(self.test_timeout)` wrapper

The `async with asyncio.timeout(self.test_timeout):` at line 2455 wraps the `query(...)` call. After migration it wraps the `async for event in harness.invoke(...)` loop in the same position. The timeout semantics are unchanged: `asyncio.TimeoutError` propagates out of the `async with` block and is caught by the existing handler at lines 2570–2579.

The Player path in `agent_invoker.py` also wraps `harness.invoke` in `asyncio.timeout`, so the pattern is consistent.

### Step D — env plumbing decision

The current code passes `env={**os.environ, "PYTHONPATH": new_pythonpath}` as a kwarg to `ClaudeAgentOptions` (line 2415). `ClaudeSDKHarness.__init__` (sdk_harness.py:130–158) does not accept an `env` kwarg — it constructs `ClaudeAgentOptions` without `env=` in `invoke()` (lines 252–266).

**Chosen approach: context-managed `os.environ` mutation** (option b from the discovery prompt, accepted as the lower-risk choice because it preserves the existing PYTHONPATH semantics without touching the harness constructor).

Implementation:
```python
import os
from contextlib import contextmanager

@contextmanager
def _patched_pythonpath(worktree_str: str):
    original = os.environ.get("PYTHONPATH")
    current = os.environ.get("PYTHONPATH", "")
    new = f"{worktree_str}:{current}" if current else worktree_str
    os.environ["PYTHONPATH"] = new
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = original
```

The `harness.invoke(...)` call is wrapped in this context manager. `ClaudeSDKHarness.invoke` then sees the already-mutated `os.environ` when it calls `query()`, which is how the SDK inherits env. Since the async generator is exhausted (or broken on `ResultMessageEvent`) before the context manager exits, the mutation is scoped tightly.

This preserves the AC-003 invariant: `_make_mock_sdk(captured_env)` patches `sys.modules["claude_agent_sdk"]` and `CapturingOptions` captures kwargs from inside `ClaudeSDKHarness.invoke` — but currently `ClaudeSDKHarness` does not pass `env=` to `ClaudeAgentOptions`. This means the `test_sdk_env_inherits_os_environ_keys` and `test_sdk_env_pythonpath_prepends_worktree` tests may break under the current harness.

**AC-003 compatibility assessment**: The existing tests assert that specific keys appear in `captured_env`, which captures whatever `env=` kwarg is passed to `ClaudeAgentOptions`. Since `ClaudeSDKHarness` currently does not pass `env=`, `CapturingOptions.__init__` receives `kwargs.get("env", {})` as `{}` and the tests would fail. This is a pre-existing gap between the Coach's direct SDK call and the harness: the harness never supported `env=`.

**Resolution**: The `os.environ` context-manager approach means tests that rely on `PYTHONPATH` being set in the running process will pass — but the `captured_env` assertion mechanism in `_make_mock_sdk` tests that `ClaudeAgentOptions` received `env=` explicitly, which it will not receive via the context-manager route.

The test bodies must be updated to assert process-environment values via `monkeypatch` directly and drop the `captured_env` assertion against `ClaudeAgentOptions`. The invariant being tested (that `PYTHONPATH` is prepended) is preserved end-to-end; the assertion mechanism changes from "captured ClaudeAgentOptions.env" to "process environment at the time harness.invoke runs". See Section 5 for the updated test strategy.

### Step E — Add AC-004 tests

See Section 5.

## 5. Test strategy

### AC-003 (existing SDK env tests) — updated for migration

The two tests in `TestSdkEnvMerge` currently call `asyncio.run(validator._run_tests_via_sdk(...))` with `sys.modules["claude_agent_sdk"]` patched. After migration:

- `_make_mock_sdk` still patches the right import target (`ClaudeSDKHarness.invoke` does `from claude_agent_sdk import ...` lazily).
- `CapturingOptions` no longer captures `env=` because `ClaudeSDKHarness` does not pass `env=` to `ClaudeAgentOptions`; the PYTHONPATH prepend is now a process-environment mutation.

**Updated test strategy for `test_sdk_env_inherits_os_environ_keys`**:
- Patch `sys.modules["claude_agent_sdk"]` with `_make_mock_sdk({})` (still needed to prevent real SDK import).
- Instead of asserting `captured_env`, assert that when the harness calls its generator, the process `os.environ["PYTHONPATH"]` contains `str(tmp_worktree)`. This can be done by inspecting `os.environ` inside a custom `fake_query` that captures the environment at call time.

**Simpler alternative**: Replace `TestSdkEnvMerge` tests with tests that patch at the `select_harness` boundary (mock `select_harness` to return a `FakeHarness` that records the `os.environ` snapshot at `invoke()` time). This is the preferred AC-004 approach and extends naturally to AC-003.

These tests continue to live in `test_coach_validator.py` with the existing `_make_mock_sdk` fixture updated or replaced. The intent (PYTHONPATH is prepended with worktree root, inherited keys are present) is preserved.

### AC-004 (new tests) — `TestCoachHarnessMigration`

Three new tests added after line 5363 in `tests/unit/test_coach_validator.py`:

**`test_run_tests_via_sdk_dispatches_through_select_harness`**
```
Purpose: Assert that _run_tests_via_sdk calls select_harness with Coach-specific
         parameters (allowed_tools=["Bash"], max_turns=1, permission_mode="bypassPermissions").

Mechanism:
  - patch("guardkit.orchestrator.quality_gates.coach_validator.select_harness") to
    return a FakeHarness that yields one ResultMessageEvent and records its kwargs.
  - asyncio.run(validator._run_tests_via_sdk("pytest tests/"))
  - Assert recorded kwargs include allowed_tools=["Bash"], max_turns=1,
    permission_mode="bypassPermissions", and cwd=tmp_worktree.
  - Assert select_harness was called once.
```

**`test_run_tests_via_sdk_consumes_tool_result_event`**
```
Purpose: Assert that a ToolResultEvent(content="...", is_error=False) causes
         the heuristic-fallback branch to run (bash_is_error set to None)
         and a ToolResultEvent(is_error=True) causes tests_passed=False.

Mechanism:
  - FakeHarness that yields ToolResultEvent(tool_use_id="x", content="1 passed",
    is_error=False) then ResultMessageEvent(session_id=None).
  - asyncio.run(validator._run_tests_via_sdk("pytest tests/"))
  - Assert result.tests_passed is True (heuristic: output contains "passed").
  - Second subtest: FakeHarness yields ToolResultEvent(is_error=True,
    content="error: command not found").
  - Assert result.tests_passed is False.
```

**`test_run_tests_via_sdk_honours_langgraph_env_var`**
```
Purpose: Assert that GUARDKIT_HARNESS=langgraph causes select_harness to be
         called (dispatch is env-var-driven, not hardcoded to SDK).

Mechanism:
  - Do NOT attempt to import guardkitfactory (would fail in CI).
  - patch("guardkit.orchestrator.quality_gates.coach_validator.select_harness")
    to return FakeHarness unconditionally, regardless of GUARDKIT_HARNESS value.
  - monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")
  - asyncio.run(validator._run_tests_via_sdk("pytest tests/"))
  - Assert select_harness was called once (verifies dispatch goes through the
    factory, not a hardcoded SDK import in the Coach method).

This test is intentionally shallow: it verifies the dispatch boundary, not
LangGraph behavioural parity (which is out of scope per Section 8).
```

**`FakeHarness` fixture** (module-level in the test section, not a pytest fixture):
```python
class FakeHarness:
    """Minimal HarnessAdapter stub for AC-004 tests."""
    def __init__(self, events):
        self._events = events
        self.supports_resume = False

    async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
        for event in self._events:
            yield event
```

### AC-005 (regression surface)

No changes to existing test classes beyond `TestSdkEnvMerge` (updated assertions as described above). All other test classes (`TestCoachValidator`, `TestIndependentTestVerification`, `TestCustomApiBase`, `TestZeroTestAnomalyIndependentTestOverride`, `TestHonestyShortCircuitDemotion`, etc.) patch at `subprocess.run` or `run_independent_tests`, not at the SDK level, and are unaffected.

## 6. Risks and mitigations

**Risk: `ToolResultEvent` is never yielded by `ClaudeSDKHarness`**

`ClaudeSDKHarness.invoke` (sdk_harness.py:309–382) currently handles `AssistantMessage`, `ResultMessage`, and (TASK-HMIG-006.2) `ToolUseEvent`. It does not walk `UserMessage`/`ToolResultBlock` from the SDK stream to produce `ToolResultEvent`. The Coach's pre-migration path reads `UserMessage.content` for `ToolResultBlock` — this is the source of `bash_output` and `bash_is_error`. After migration, if `ClaudeSDKHarness` does not yield `ToolResultEvent`, `bash_output` and `bash_is_error` stay `None` and the heuristic branch always runs.

Mitigation: The heuristic branch (lines 2544–2568, checking for "failed"/"error" vs "passed"/"ok" in `collected_text`) is the correct fallback for `AssistantMessage`-only streams, which is exactly what the Coach test prompt produces — the SDK agent responds with a text summary of the test output, not raw tool results. In practice, the `ClaudeSDKHarness` not yielding `ToolResultEvent` is the correct current behavior; `bash_is_error=None` + heuristic is the intended codepath. Document this explicitly with a comment in the new loop (see Step B).

If a future extension of `ClaudeSDKHarness` adds `ToolResultEvent` emission (by walking `UserMessage.content`), the new Coach loop handles it correctly because `is_error=True` → `bash_is_error=True` and `is_error=False` → `bash_is_error=None` (heuristic).

**Risk: env plumbing via `os.environ` mutation is not thread-safe**

The context-managed `os.environ["PYTHONPATH"]` mutation is visible to other threads in the same process. In production, CoachValidator runs in a subprocess-isolated worktree with one active Coach turn at a time, so thread contention is not a real concern. In tests, `monkeypatch.setenv` already touches `os.environ` and `asyncio.run()` is single-threaded per call.

Mitigation: Accept the known limitation; document it with a comment on the context manager. If a future use case needs concurrent Coach invocations in the same process, the `env=` kwarg should be added to `ClaudeSDKHarness.__init__` as a separate task.

**Risk: AC-003 test `captured_env` mechanism breaks**

As documented in Step D, `ClaudeSDKHarness` does not pass `env=` to `ClaudeAgentOptions`, so the `CapturingOptions` mock captures an empty dict. The AC-003 tests assert `"ANTHROPIC_API_KEY" in captured_env`.

Mitigation: Update `TestSdkEnvMerge` to capture the process environment at `invoke()` time inside `FakeHarness.invoke` (or a `fake_query` that snapshots `os.environ`). The invariant tested (PYTHONPATH is prepended, API keys are inherited) is preserved; only the capture mechanism changes. This is a test-only change with no production consequence.

**Risk: `AgentInvocationError` exception cascade differs from pre-migration**

Pre-migration, Coach handles `CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError` as distinct typed exceptions with structured `error_class` logging. Post-migration, all three are normalised inside `ClaudeSDKHarness.invoke` to `AgentInvocationError` with `error_class` in the message string. The `run_independent_tests` fallback at line 2873 catches the exception generically (`except Exception as e`) and reads `error_class = type(e).__name__` and `exit_code = getattr(e, "exit_code", None)`. After migration, `type(e).__name__` is `"AgentInvocationError"` and `exit_code` is absent (no attribute). The structured diagnostic info is preserved inside the exception message string from `ClaudeSDKHarness`.

Mitigation: The `run_independent_tests` caller only uses `error_class` and `exit_code` for log formatting (lines 2882–2898); it doesn't branch on them. The fallback to subprocess still occurs. The only difference is the logged `error_class` changes from `ProcessError` to `AgentInvocationError`. This is acceptable; document with a comment.

**Risk: `LangGraphHarness` does not support `["Bash"]`-only tool sets**

`select_harness` with `GUARDKIT_HARNESS=langgraph` drops `allowed_tools` via `_translate_kwargs_for_langgraph` and constructs `LangGraphHarness` with DeepAgents' built-in tool set. The Coach test prompt asks the agent to run a Bash command; DeepAgents' `execute` tool serves this purpose. However, behavioural parity is not tested (Section 8).

Mitigation: AC-004 only asserts dispatch, not behaviour. This risk is deferred to the LangGraph integration test suite in `guardkitfactory`.

## 7. Estimated effort

- `coach_validator.py` changes: ~120 lines changed/removed, ~40 lines added (net ~80 line reduction).
- `tests/unit/test_coach_validator.py` changes: ~30 lines updated in `TestSdkEnvMerge`, ~90 lines added for `TestCoachHarnessMigration` (3 tests + `FakeHarness`).
- Total LOC delta: −80 production, +90 test = +10 net.
- Duration: 4h (complexity 5, medium).

## 8. Out of scope / non-goals

- Adding `ToolResultEvent` emission to `ClaudeSDKHarness` (the harness currently does not walk `UserMessage.content`; this is a separate TASK-HMIG concern if needed).
- Adding `env=` kwarg to `ClaudeSDKHarness.__init__` (the context-manager approach is chosen for this migration; a future task may promote this to a first-class harness parameter).
- `LangGraphHarness` behavioural parity for `["Bash"]`-only invocations (only dispatch is tested per AC-004).
- Touching the second call site at `coach_validator.py:1987–1992` (`run_independent_tests` → `gather_evidence`). That is a call to `run_independent_tests()`, not a direct SDK call. It is not the second SDK call site; the only direct SDK call site in `coach_validator.py` is `_run_tests_via_sdk`.
- Modifying `sdk_debug` preservation for Coach test runs (pre-migration, `_sdk_preserve_prompt` at line 2428 records the prompt + options; post-migration this is deferred to a follow-up if needed).
- Modifying `agent_invoker.py` (already migrated by TASK-HMIG-006.2).

---

## Context Used

| Discovery fact | Decision it shaped |
|---|---|
| `_run_tests_via_sdk` uses `allowed_tools=["Bash"]`, `max_turns=1`, no `resume_session_id` | Step A kwarg differences from Player dispatch documented explicitly |
| `ToolResultEvent.is_error` is `bool = False` (not `Optional[bool]`) at `adapter.py:75` | Step B tri-state mapping: `False→None` (heuristic), `True→True`; heuristic branch remains live |
| `ClaudeSDKHarness.invoke` does not yield `ToolResultEvent` (it only handles `AssistantMessage`/`ResultMessage`/`ToolUseEvent`) | Risk 1: `bash_is_error=None` is the normal production path; heuristic branch is correct default |
| `ClaudeSDKHarness.__init__` has no `env=` parameter (sdk_harness.py:130–158) | Step D: context-managed `os.environ` mutation chosen over harness constructor change |
| `select_harness` pops `cwd` before delegating to `ClaudeSDKHarness` (selector.py:202) | Step A: `cwd=self.worktree_path` must be passed unconditionally |
| `_make_mock_sdk` patches `sys.modules["claude_agent_sdk"]` and `CapturingOptions` captures `env=` kwarg | AC-003 risk identified; `TestSdkEnvMerge` test bodies require assertion-mechanism update |
| `run_independent_tests` at line 2867 uses `loop.run_until_complete(self._run_tests_via_sdk(...))` | Step A/C: method signature unchanged, caller unchanged |
| `AgentInvocationError` is the normalised exception from `ClaudeSDKHarness` (D-4) | Exception cascade simplified to single `AgentInvocationError` catch |
| `self.test_timeout` (Coach) is independent of `sdk_timeout_seconds` | `select_harness(sdk_timeout_seconds=self.test_timeout)` — not `self.sdk_timeout_seconds` |
| TASK-DIAG-F4A2 `preserve_prompt` / `preserve_event` calls at lines 2424–2435 and 2474 | Removed as sdk_debug integration for Coach test path is a separate follow-up |
