# Review Report: TASK-REV-ED10 (Revised)

**Task**: Analyse vLLM Coach SDK failures in GB10 autobuild feature run
**Mode**: Decision / Root Cause Analysis
**Depth**: Standard (revised for higher confidence)
**Run Log**: `docs/reviews/gb10_local_autobuild/api_feature_2.md`
**Feature**: FEAT-EC3C — FastAPI app with health endpoint
**Completed**: 2026-02-23

---

## Executive Summary

The GB10 autobuild run (`api_feature_2.md`) failed at Wave 2 (TASK-C086) with `UNRECOVERABLE_STALL` after 3 turns. This is the **second** feature run — the first (`api_feature_1.md`) had already failed with the Player itself crashing due to a model name mismatch (TASK-REV-AB3D). Between the two runs, `scripts/vllm-serve.sh` was updated to fix that Player model name. The second run confirms Wave 1 is now stable but reveals a new, previously hidden failure: the Coach's SDK test invocation uses a hardcoded Haiku model ID that vLLM doesn't know.

Three failure categories were confirmed with high confidence:

1. **Environment Bootstrap (PEP 668)**: All 6 pip installs failed. `sys.executable` is the system Python (`/usr/bin/python3`) on Debian, which enforces PEP 668. No virtualenv fallback exists. The packages targeted (`fastapi`, `uvicorn`, `pydantic`, etc.) were not installed. However, this is **not the proximate cause** of the stall — the Player's own pytest invocations run via the user-installed pytest and still pass.

2. **Coach SDK `invalid_request` (root cause of stall)**: The Coach Validator's `_run_tests_via_sdk()` creates a `ClaudeAgentOptions` with `model="claude-haiku-4-5-20251001"` (hardcoded at line 1051 of `coach_validator.py`). vLLM serves only `claude-sonnet-4-6`. The model name mismatch causes vLLM to return an error (~0.8s) which the SDK surfaces as `AssistantMessage.error = "invalid_request"`. This is the **exact same class of bug** as TASK-REV-AB3D (model name mismatch with vLLM), but in a different component (Coach SDK vs Player SDK). The Player SDK path intentionally omits `model=` from `ClaudeAgentOptions` and lets the bundled `claude` CLI default to `claude-sonnet-4-6` — which now matches vLLM. The Coach path does NOT use this pattern.

3. **asyncio cancel scope RuntimeError**: Non-fatal deferred cleanup from a known AnyIO upstream bug. The previous turn's SDK generator cleanup runs as background asyncio tasks at the start of the next turn. Does not affect Player execution and does not contribute to the `invalid_request` error.

The stall detector behaved **correctly**. The Player's implementation is correct; the failure is entirely in the orchestrator's Coach infrastructure.

---

## Context: Two Runs, Two Failures

| Run | Log | Player Status | Cause |
|-----|-----|---------------|-------|
| Run 1 | `api_feature_1.md` | FAILED (480s, `unknown`) | vLLM served `claude-sonnet-4-5-20250929`; CLI sent `claude-sonnet-4-6` → 404 |
| Run 2 | `api_feature_2.md` | SUCCESS (Wave 1+2 Player works) | `vllm-serve.sh` fixed to `claude-sonnet-4-6`; CLI default now matches |

After the TASK-REV-AB3D fix (`SERVED_MODEL_NAME="claude-sonnet-4-6"` in `vllm-serve.sh`), the Player works. But this fix **only addressed the Player** — the Coach SDK still fails because it explicitly requests a different model.

---

## Finding 1 — Environment Bootstrap fails on PEP 668 systems

**Severity**: High (infrastructure)
**Source**: [guardkit/orchestrator/environment_bootstrap.py](guardkit/orchestrator/environment_bootstrap.py)

### Root Cause (confirmed)

`EnvironmentBootstrapper._python_dep_commands()` generates:

```python
return [[sys.executable, "-m", "pip", "install", dep] for dep in deps]
```

`sys.executable` = `/usr/bin/python3` on the GB10 host. This is the system Python protected by Debian's PEP 668 guard. All 6 installs fail with exit code 1 and stderr `externally-managed-environment`. No virtualenv fallback is present in the bootstrapper.

**Confirmed by log**: Lines 167-304 of `api_feature_2.md` show all 6 consecutive pip failures. The state JSON records `success=False` and the next run would trigger a retry (after the 60-second cooldown).

### Does this cause the stall?

**No.** The stall is caused by the Coach SDK failure (Finding 2). The bootstrap failure means the project packages aren't available via `/usr/bin/python3 -m pytest`. However:
- The Player's pytest invocations use `~/.local/bin/pytest` (user-installed, confirmed: `which pytest=/home/richardwoollcott/.local/bin/pytest` in log line 392)
- User-installed packages in `~/.local/lib/python3.12/site-packages/` are accessible to that pytest
- Player turn 1 reported `1 tests (passing)` despite the bootstrap failure

**Secondary risk**: If the Coach's subprocess fallback path were reached (it isn't due to Finding 2), it would use `sys.executable -m pytest` which is the system Python. Whether this passes depends on whether the test imports are available in user packages accessible from system Python.

### Scope

Affects any Debian/Ubuntu host where the autobuild orchestrator runs as the system Python. Not an issue when guardkit runs inside a venv, on macOS, or on Ubuntu 22.04 LTS (Python 3.10, PEP 668 not enforced).

---

## Finding 2 — Coach SDK `invalid_request`: exact model name mismatch with vLLM

**Severity**: Critical (root cause of UNRECOVERABLE_STALL)
**Source**: [guardkit/orchestrator/quality_gates/coach_validator.py:1051](guardkit/orchestrator/quality_gates/coach_validator.py#L1051)

### Root Cause (confirmed with high confidence)

The Coach Validator's `_run_tests_via_sdk()` method (line 1005) creates SDK options with an explicitly hardcoded model:

```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Bash"],
    permission_mode="bypassPermissions",
    max_turns=1,
    model="claude-haiku-4-5-20251001",   # ← hardcoded Anthropic Haiku model ID
)
```

vLLM is configured to serve only one model alias: `claude-sonnet-4-6` (set in `scripts/vllm-serve.sh` line 24, after the TASK-REV-AB3D fix). When the Coach SDK sends a request for `claude-haiku-4-5-20251001`, vLLM's `/v1/messages` handler rejects it with an error that the SDK surfaces as `AssistantMessage.error = "invalid_request"`.

**Timing** confirms API-level rejection: the error returns in 0.7–0.8s — consistent with a local HTTP request + immediate validation failure, not a model inference timeout.

### The Player/Coach asymmetry — the precise mechanism

This is the exact same class of bug as TASK-REV-AB3D but in a different code path. Comparing the two:

**Player SDK path** (`agent_invoker.py`, task-work delegation, line 3416):
```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task"],
    permission_mode="acceptEdits",
    max_turns=TASK_WORK_SDK_MAX_TURNS,
    setting_sources=["project"],
    # NOTE: NO model= parameter
)
```
No `model=` is passed. The bundled `claude` CLI uses its own default: `claude-sonnet-4-6`. This matches vLLM → **Player works**.

**Coach SDK path** (`coach_validator.py`, line 1046):
```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Bash"],
    permission_mode="bypassPermissions",
    max_turns=1,
    model="claude-haiku-4-5-20251001",   # explicit — does NOT match vLLM
)
```
Explicit `model="claude-haiku-4-5-20251001"`. vLLM doesn't know this model → **Coach fails**.

The fix for TASK-REV-AB3D (updating `SERVED_MODEL_NAME` in `vllm-serve.sh`) fixed the Player because the CLI default changed, but it could not fix the Coach because the Coach has its own hardcoded model ID that was never aligned with the vLLM alias.

There is also a second issue: `AgentInvoker` stores `player_model="claude-sonnet-4-5-20250929"` and `coach_model="claude-sonnet-4-5-20250929"` as instance fields (line 606-607) but the task-work delegation path (`_run_task_work_via_sdk`) does not pass these to `ClaudeAgentOptions`. These fields appear unused in the current task-work path. The model for the Player is implicitly the CLI default; the model for the Coach SDK test execution is the hardcoded haiku value — neither is governed by these fields.

### Why conditional approval did not trigger

The `conditional_approval` logic (line 644) requires ALL of:

| Condition | Value | Met? |
|-----------|-------|------|
| `failure_class == "infrastructure"` | `code` | ✗ |
| `failure_confidence == "high"` | `n/a` | ✗ |
| `bool(requires_infra)` | `[]` (task has no infrastructure requirements) | ✗ |
| `not docker_available` | `False` (Docker IS available on GB10) | ✗ |
| `gates_status.all_gates_passed` | `True` | ✓ |

The failure classifier (`_classify_test_failure`) inspects `raw_output = "SDK API error: invalid_request"`. This string matches none of `_INFRA_HIGH_CONFIDENCE` (connection errors, database errors), `_INFRA_AMBIGUOUS` (import errors), or `_KNOWN_SERVICE_CLIENT_LIBS`. It falls through to default: `failure_class=code, confidence=n/a`. This is technically a misclassification — the failure is an SDK infrastructure problem, not a code defect — but since `requires_infra=[]` is also empty, conditional approval would not trigger even with the correct classification.

### Why the subprocess fallback was never reached

`run_independent_tests()` selects the execution path:

```python
use_sdk = (
    self._coach_test_execution == "sdk"    # True by default
    and not requires_infra                  # True (no infra declared)
)
```

When `use_sdk=True`, `_run_tests_via_sdk()` is called. The SDK error is caught **inside** `_run_tests_via_sdk()` at line 1063 and returned as a `IndependentTestResult(tests_passed=False, ...)` — NOT as an exception. The outer `run_independent_tests()` receives this result and returns it. No exception propagates, so the subprocess fallback (line 1276) is never reached.

If the SDK had raised an exception instead, the fallback at line 1270-1274 would catch it and try subprocess. This is a gap in the error handling design: API-level errors in `_run_tests_via_sdk` should either fall back to subprocess or be classified distinctly.

### Stall detection was correct

Coach feedback for all 3 turns: `"Independent test verification failed: SDK API error: invalid_request"` (hash `sig=9632f335`). With `criteria_passed=0` across 3 turns, the stall threshold was correctly reached. Further Player turns would not resolve the issue, since the Coach SDK failure is independent of the Player's code quality. The Player's implementation is correct; the stall is due to orchestrator infrastructure, not a code defect.

However, the stall termination message ("Review task_type classification and acceptance criteria") is misleading in this case — the player code is not the problem.

---

## Finding 3 — asyncio cancel scope RuntimeError: precise mechanism confirmed

**Severity**: Low (cosmetic noise)
**Source**: `anyio._backends._asyncio` — known upstream bug

### Mechanism (confirmed)

The error appears at the **start** of turns 2 and 3, as two background task exceptions each time:

**Exception 1**: `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in`
- Traceback path: `GeneratorExit` → `client.py:process_query` → `await query.close()` → `_tg.__aexit__()` → `cancel_scope.__exit__()`
- The previous turn's `query()` async generator is closed (Python sends `GeneratorExit` when the `async for` loop ends)
- AnyIO's task group tries to exit its cancel scope, but the cleanup runs in a new asyncio task (`Task-24`, `Task-37`) scheduled by Python's background async generator finalizer
- This is a known AnyIO issue: cancel scopes must be exited in the same task they were entered in

**Exception 2**: `ProcessError: Command failed with exit code 1`
- The bundled `claude` CLI subprocess is forcefully closed during generator cleanup
- The subprocess exits with code 1 (non-zero) when terminated by signal
- Reported as `ProcessError` by the transport layer

Both are background asyncio task exceptions reported by Python's event loop. They do NOT affect the current turn's SDK invocation, which starts fresh. **Confirmed non-fatal**: turns 2 and 3 complete normally (27 and 24 SDK turns, player files created and modified successfully).

### Why turns 1, 2, 3 vs only 2 and 3?

Turn 1 has no previous SDK invocation — nothing to clean up. The cleanup from turn 1's generator runs at the start of turn 2, and turn 2's cleanup runs at the start of turn 3. This is consistent with Python's async generator finalizer scheduling cleanup on the next event loop iteration.

### Is this vLLM-specific?

No — this error can appear on any host with this SDK version. It may be more visible with longer SDK invocations (vLLM responses take longer per token than Anthropic's API, meaning the generators run longer and cleanup timing is different). Not caused by vLLM.

---

## Finding 4 — Stall detection: correct decision, misleading message

**Verdict**: Stall detection behaved correctly. Termination message is misleading.

The stall detector correctly identifies that 3 identical Coach feedback strings with 0 criteria progress constitutes an unrecoverable stall. The Player cannot fix an SDK infrastructure failure no matter how many turns it gets.

The misleading part: the final status box says "Suggested action: Review task_type classification and acceptance criteria." This is appropriate for Player code failures, but wrong for orchestrator infrastructure failures. When the stall feedback is exclusively an SDK API error (e.g. contains "SDK API error"), the suggested action should be "Check ANTHROPIC_BASE_URL configuration and SDK model name compatibility."

---

## Key Question Answers (updated with higher confidence)

| # | Question | Answer |
|---|----------|--------|
| 1 | What does `invalid_request` mean from vLLM? | vLLM's `/v1/messages` endpoint returns an error response (consistent with Anthropic error format) when the requested model ID is not in its served model aliases. The SDK surfaces this as `AssistantMessage.error = "invalid_request"`. Confirmed: vLLM serves only `claude-sonnet-4-6`; Coach requests `claude-haiku-4-5-20251001`. |
| 2 | Does `environment_bootstrap.py` have a virtualenv fallback? | No. Confirmed by full code review. |
| 3 | Why did conditional approval not trigger? | `failure_class=code` (misclassified), `requires_infra=[]` (empty), `docker_available=True` — zero of four conditions met. |
| 4 | Can Coach skip SDK-based tests when running against vLLM? | Yes: (a) set `coach_test_execution="subprocess"`, (b) detect non-Anthropic `ANTHROPIC_BASE_URL` and override to subprocess, OR (c) don't pass an explicit `model=` to `ClaudeAgentOptions` and let the CLI default to whatever vLLM serves (same pattern as the Player). |
| 5 | Does the asyncio cancel scope error contribute to `invalid_request`? | No. Confirmed. Cancel scope error = previous turn's generator cleanup. `invalid_request` = Coach's SDK calling the wrong model ID on vLLM. Different processes, different timing, no causal link. |

---

## Recommendations

### R1 (Critical, Low effort) — Remove hardcoded `model=` from Coach `_run_tests_via_sdk`

The simplest fix: remove the explicit `model=` from `ClaudeAgentOptions` in `_run_tests_via_sdk` and let the bundled CLI default (same pattern as the Player). This ensures the Coach always uses the same model as the Player, which is already known to work against the configured vLLM alias:

```python
# coach_validator.py line 1046
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Bash"],
    permission_mode="bypassPermissions",
    max_turns=1,
    # No model= — use CLI default (claude-sonnet-4-6), same as Player
)
```

**Risk**: None for vLLM mode. For real Anthropic API, the CLI default (Sonnet) may be more expensive than Haiku for this one-turn test execution. If cost is a concern, the model should be configurable rather than hardcoded.

**Scope**: `guardkit/orchestrator/quality_gates/coach_validator.py` line 1051

---

### R2 (Critical, Low effort) — Detect non-Anthropic base URL; use subprocess fallback

A more robust fix: detect when `ANTHROPIC_BASE_URL` points to a non-Anthropic server and bypass the SDK path entirely for test execution:

```python
# In run_independent_tests() — replace existing use_sdk logic:
def _is_custom_api_base() -> bool:
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    return bool(base_url) and "api.anthropic.com" not in base_url

use_sdk = (
    self._coach_test_execution == "sdk"
    and not requires_infra
    and not _is_custom_api_base()  # NEW: bypass SDK for vLLM / custom endpoints
)
```

This ensures the Coach's test execution works correctly against vLLM (using subprocess with `~/.local/bin/pytest`) while preserving the SDK path for real Anthropic API. R1 may still be needed alongside this if the model name causes issues in other scenarios.

**Scope**: `guardkit/orchestrator/quality_gates/coach_validator.py` — `run_independent_tests()`

---

### R3 (High, Medium effort) — Fix environment_bootstrap.py: virtualenv fallback for PEP 668

When any pip install fails with `externally-managed-environment` in stderr, detect and create a project-local venv:

1. Create `.guardkit/venv/` using `python3 -m venv`
2. Retry all failed installs using the venv Python
3. Update `_state_file` with venv path so subsequent runs know to use it

The venv approach is cleaner than `--break-system-packages` and does not require modifying the system Python.

**Scope**: `guardkit/orchestrator/environment_bootstrap.py` — `_run_single_command()`, `_run_install()`, `BootstrapResult`

---

### R4 (Medium, Low effort) — Improve `invalid_request` failure classification

Add "SDK API error" pattern to the failure classification to distinguish "API-level infrastructure failure" from "code defect". This produces better Coach feedback and could enable a targeted fallback:

```python
# _INFRA_HIGH_CONFIDENCE (or a new _SDK_ERROR category):
"SDK API error",
"invalid_request",
"invalid_request_error",
```

Also improve the stall termination message: when all stall turns share an SDK API error pattern, display "Check ANTHROPIC_BASE_URL and SDK model configuration" rather than "Review task_type classification".

**Scope**: `guardkit/orchestrator/quality_gates/coach_validator.py` — `_classify_test_failure()`
**Scope**: `guardkit/orchestrator/autobuild.py` — stall exit message

---

### R5 (Medium, Low effort) — Align AgentInvoker model fields with actual usage

`AgentInvoker.__init__` stores `player_model` and `coach_model` fields (both defaulting to `claude-sonnet-4-5-20250929`), but neither is passed to `ClaudeAgentOptions` in the current task-work delegation path. These fields are vestigial and create false confidence that model selection is centrally controlled.

Options:
- Remove the fields and document that model selection is delegated to the CLI default
- Wire the fields through to `ClaudeAgentOptions` AND align `player_model` with the vLLM `SERVED_MODEL_NAME`

Also: the Coach's `_run_tests_via_sdk` model selection should be sourced from a central configuration (e.g. `GUARDKIT_COACH_TEST_MODEL` env var) rather than hardcoded.

**Scope**: `guardkit/orchestrator/agent_invoker.py`, `guardkit/orchestrator/quality_gates/coach_validator.py`

---

### R6 (Low, Minimal effort) — Update vllm-serve.sh comment and documentation

Document clearly that:
- `SERVED_MODEL_NAME` must match the model ID used by the bundled `claude` CLI default (currently `claude-sonnet-4-6`)
- If this alias drifts with a Claude SDK upgrade, ALL SDK-based paths break (Player AND Coach, if Coach is fixed per R1)
- The `SERVED_MODEL_NAME` should be updated whenever the Claude CLI bundled default changes

Consider adding a health-check step to autobuild startup that verifies `ANTHROPIC_BASE_URL`'s `/v1/models` includes the expected model alias before starting waves.

**Scope**: `scripts/vllm-serve.sh`, `docs/guides/` (simple-local-autobuild)

---

### R7 (Low, Minimal effort) — asyncio cancel scope: update AnyIO / check SDK version

The cancel scope error is an upstream AnyIO/SDK issue. Check if a newer version of `claude-agent-sdk` resolves it. If not, suppress the specific `RuntimeError("Attempted to exit cancel scope")` log in `agent_invoker.py`'s exception handler to reduce noise.

**Scope**: `guardkit/orchestrator/agent_invoker.py`, `pyproject.toml` (dependency version)

---

## Scope Assessment

| Issue | GB10/vLLM-specific? | Notes |
|-------|---------------------|-------|
| PEP 668 bootstrap failure | Partially | Any Debian/Ubuntu host running as system Python. Not an issue inside a venv. |
| Coach SDK `invalid_request` | Yes — vLLM only | Anthropic API accepts any valid Anthropic model ID. Issue is unique to vLLM with a single registered alias. |
| asyncio cancel scope error | No — universal | Any host with this SDK version and workload. Non-fatal. |
| Misleading stall message | No — universal | Would appear whenever the stall is caused by Coach SDK failures rather than Player code failures. |

---

## Fix Priority Order

For unblocking GB10 local autobuild:
1. **R1** (remove `model=` from Coach `ClaudeAgentOptions`) — 1 line change, immediate fix
2. **R2** (detect non-Anthropic base URL) — 5–10 lines, defensive belt-and-suspenders
3. **R3** (venv fallback in bootstrap) — prevents a secondary risk once R1/R2 are in place

For production robustness:
4. **R4** (better failure classification)
5. **R5** (align model fields)
6. **R6** (documentation)
7. **R7** (asyncio noise)

---

*Revised report — TASK-REV-ED10 | Confidence: High for all root causes*
