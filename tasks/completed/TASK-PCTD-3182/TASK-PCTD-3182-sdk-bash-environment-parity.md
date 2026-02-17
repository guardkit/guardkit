---
id: TASK-PCTD-3182
title: "SDK Bash tool environment parity for Coach test execution (Option C)"
status: completed
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T19:00:00Z
completed: 2026-02-17T19:00:00Z
completed_location: tasks/completed/TASK-PCTD-3182/
priority: critical
tags: [autobuild, coach-validator, environment-parity, sdk, root-cause-fix]
task_type: feature
complexity: 7
parent_review: TASK-REV-D7B2
feature_id: FEAT-27F2
wave: 3
implementation_mode: task-work
dependencies: [TASK-PCTD-5208]
previous_state: in_review
state_transition_reason: "Human review approved - task completed"
test_results:
  status: passed
  tests_total: 228
  tests_passed: 228
  tests_failed: 0
  new_tests: 25
  regression_tests: 203
  last_run: 2026-02-17T19:00:00Z
organized_files:
  - TASK-PCTD-3182-sdk-bash-environment-parity.md
---

# Task: SDK Bash tool environment parity for Coach test execution (Option C)

## Description

This is the **root cause fix** for the Player/Coach test divergence (Finding F1 in TASK-REV-D7B2). The Coach currently runs tests via `subprocess.run(shell=True)` which uses `/bin/sh` without sourcing user shell profiles, venv activation, or environment variables. The Player runs tests via the Claude Agent SDK's Bash tool which inherits the full user environment.

**Solution**: Use a minimal Claude Agent SDK invocation (1 turn, Haiku model, Bash-only) to run Coach tests, achieving 100% environment parity with the Player. Fall back to `subprocess.run()` only on explicit config or SDK errors.

The SDK is a **hard runtime requirement** for AutoBuild (enforced by `_require_sdk()` at both CLI entry points), so it is always available when CoachValidator executes.

## Acceptance Criteria

- [ ] `_run_tests_via_sdk()` async method added to `CoachValidator`
- [ ] Uses `ClaudeAgentOptions(model="claude-haiku-4-5-20251001", max_turns=1, allowed_tools=["Bash"], permission_mode="bypassPermissions")` — note: `ClaudeAgentOptions` not `ClaudeCodeOptions`
- [ ] All imports from `claude_agent_sdk` (not `claude_code_sdk`) — see SDK Migration Corrections below
- [ ] Handles `UserMessage` with `ToolResultBlock` to capture Bash output (GAP-FIX #4)
- [ ] Handles `ToolResultBlock.content` as `str | list[dict] | None` (GAP-FIX #5)
- [ ] **Three-way `is_error` handling**: `True` → fail, `False` → pass, `None` → parse output text for failure indicators (GAP-FIX #6/#7 + bug #247 defense)
- [ ] Checks `AssistantMessage.error` field for API errors returned as messages (bug #472 defense)
- [ ] **Bug #472 defense extended to all SDK stream loops** — `AssistantMessage.error` check added to `agent_invoker._invoke_with_role()`, `agent_invoker._invoke_task_work_implement()`, and `task_work_interface._execute_via_sdk()` (see Player Agent Audit below)
- [ ] Provides `duration_seconds` in all `IndependentTestResult` return paths (GAP-FIX #8)
- [ ] Uses `asyncio.get_event_loop()` with try/except safety pattern (GAP-FIX #9)
- [ ] `run_independent_tests()` modified to try SDK first, subprocess fallback on error
- [ ] `CoachValidator.__init__()` accepts `coach_test_execution: str = "sdk"` parameter
- [ ] `AutoBuildOrchestrator._load_coach_config()` reads from `.guardkit/config.yaml` under `autobuild.coach.test_execution`
- [ ] Config option: `"sdk"` (default) or `"subprocess"` (explicit opt-out)
- [x] `pyproject.toml` `[autobuild]` extra already references `claude-agent-sdk>=0.1.0` ✅ (verified 2026-02-17)
- [ ] All 4 `IndependentTestResult` fields populated in every return path (data contract validation)
- [ ] 16 tests (15 from review test plan + 1 for `is_error=None` fallback)
- [ ] 3 additional tests for `AssistantMessage.error` handling in existing SDK paths (see Player Agent Audit)

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `__init__()`, `run_independent_tests()`, `_run_tests_via_sdk()` (new)
- `guardkit/orchestrator/autobuild.py` — `_invoke_coach_safely()` (CoachValidator instantiation), `_load_coach_config()` (new)
- `guardkit/orchestrator/agent_invoker.py` — `_invoke_with_role()`, `_invoke_task_work_implement()` (bug #472 defense)
- `guardkit/orchestrator/quality_gates/task_work_interface.py` — `_execute_via_sdk()` (bug #472 defense)

## Implementation Notes

**CRITICAL**: The review report (`.claude/reviews/TASK-REV-D7B2-review-report.md` R5 section) contains a fully validated implementation with 9 GAP-FIX annotations. However, the review was written against **SDK v0.1.18 which does not exist as a public release**. The corrections below align the implementation with the **actual current SDK (`claude-agent-sdk` v0.1.36)**.

The review report remains the primary implementation reference for:
- Complete `_run_tests_via_sdk()` code with all 9 GAP-FIX annotations
- Complete `run_independent_tests()` code with SDK-first + subprocess fallback
- `CoachValidator.__init__()` changes
- `AutoBuildOrchestrator._load_coach_config()` code
- C4 Level 3 component interaction diagram with gap-fix annotations
- C4 Level 2 event loop lifecycle diagram proving no nested `run_until_complete`
- Data contract validation tracing all 4 `IndependentTestResult` fields
- 15-item test plan

### SDK Migration Corrections (Review → Actual SDK)

The SDK underwent a **breaking rename at v0.1.0**. All review report code must be adjusted:

| Review Report (WRONG) | Correct (v0.1.36) |
|---|---|
| `pip install claude-code-sdk` | `pip install claude-agent-sdk==0.1.36` |
| `from claude_code_sdk import query, ClaudeCodeOptions` | `from claude_agent_sdk import query, ClaudeAgentOptions` |
| `ClaudeCodeOptions(...)` | `ClaudeAgentOptions(...)` |
| `from claude_code_sdk import UserMessage, ToolResultBlock, ResultMessage` | `from claude_agent_sdk import UserMessage, ToolResultBlock, ResultMessage` |
| SDK version: v0.1.18 | Actual latest: v0.1.36 (PyPI) / v0.1.13 (GitHub latest release tag) |

**pyproject.toml** already correctly references `claude-agent-sdk>=0.1.0` in both `[autobuild]` and `[all]` extras — no change needed.

### GAP-FIX Validation Against v0.1.36 API Surface

All 9 GAP-FIX annotations were re-validated against the current SDK types on 2026-02-17:

| GAP-FIX | Review Claim | v0.1.36 Status | Notes |
|---|---|---|---|
| #1 | SDK import available | ✅ Valid | `_require_sdk()` enforces at CLI entry |
| #2 | Full model ID `"claude-haiku-4-5-20251001"` | ✅ Valid | `ClaudeAgentOptions.model: str \| None` accepts full IDs |
| #3 | `system_prompt` accepts `str` | ✅ Valid | `str \| SystemPromptPreset \| None` |
| #4 | Bash output in `UserMessage` with `ToolResultBlock` | ✅ Valid | `UserMessage.content: str \| list[ContentBlock]` |
| #5 | `ToolResultBlock.content: str \| list[dict] \| None` | ✅ Valid | Confirmed in types.py |
| #6/#7 | `is_error` reflects Bash exit code | ⚠️ **RISK** | See below |
| #8 | Duration from Python timing | ✅ Valid | Standard pattern |
| #9 | `asyncio.get_event_loop()` bridge | ✅ Valid | Standard pattern |

### ⚠️ GAP-FIX #6/#7: `is_error` May Be `None` — Defensive Handling Required

GitHub Issue [#247](https://github.com/anthropics/claude-agent-sdk-python/issues/247) reports `ToolResultBlock.is_error` is **always `None`** for SDK MCP server tools. The native Bash tool (used by Coach) *may* work correctly since it's a built-in tool, not an MCP tool. However, the implementation **must not rely on `is_error` alone**.

**Required defensive pattern**:
```python
# Primary: use is_error if available (native Bash tool should set it)
if tool_result.is_error is True:
    tests_passed = False
elif tool_result.is_error is False:
    tests_passed = True
else:
    # Fallback: is_error is None (bug #247 or unexpected SDK behavior)
    # Parse for pytest failure indicators in the output text
    output_text = _extract_content_text(tool_result.content)
    tests_passed = not any(indicator in output_text.lower() for indicator in [
        "failed", "error", "exit code 1", "no tests ran"
    ])
```

Add a dedicated test case for `is_error=None` fallback (extends test plan item #2).

### Additional v0.1.36 API Notes

- `ClaudeAgentOptions` now includes `tools: list[str] | ToolsPreset | None` (new field). Use `allowed_tools` as in the review — it still works.
- `ResultMessage` now includes `structured_output: Any = None` (new field). Ignored by our implementation.
- `UserMessage` now includes `uuid: str | None = None` (new field). Ignored.
- `AssistantMessage` now includes `error: AssistantMessageError | None = None` (new field). Should be checked — if the SDK returns an API error, it appears as `AssistantMessage` with this field set, NOT as an exception (see GitHub Issue [#472](https://github.com/anthropics/claude-agent-sdk-python/issues/472)).
- The SDK now **bundles the Claude Code CLI** — no separate `npm install` required.
- New features available but not needed: hooks, plugins, sandbox, structured outputs.

### Key Technology Seam Risks (Updated)

| # | Seam | Risk | Mitigation |
|---|------|------|------------|
| 2 | SDK `--model` flag | CLI doesn't recognize shorthand | Full ID: `"claude-haiku-4-5-20251001"` |
| 4 | SDK message parser | Bash output in `UserMessage`, not `AssistantMessage` | Handle `UserMessage` with `ToolResultBlock` |
| 5 | `ToolResultBlock.content` type union | `str \| list[dict] \| None` | Type-check and extract properly |
| 6/7 | Pass/fail determination | `is_error` may be `None` (bug #247) | **Three-way check**: `True` → fail, `False` → pass, `None` → parse output text |
| 9 | async/sync bridge | `RuntimeError: no current event loop` | Use exact `autobuild.py:3459-3463` pattern |
| NEW | API errors as messages | `AssistantMessage.error` set instead of exception raised (bug #472) | Check `AssistantMessage.error` field; treat as SDK failure → subprocess fallback |

### Player Agent SDK Audit (2026-02-17)

A full audit of the Player agent and design phase SDK integration was conducted against v0.1.36. All imports, option classes, exception types, content block processing, and message flow patterns are **correct and working**.

One gap was identified and folded into this task:

**Finding: `AssistantMessage.error` field not checked in any existing SDK stream loop**

All three SDK invocation paths (`_invoke_with_role`, `_invoke_task_work_implement`, `_execute_via_sdk`) process `AssistantMessage.content` blocks but do not check the `.error` field (added in SDK v0.1.9). Per GitHub Issue #472, the SDK may return API errors as `AssistantMessage` with `.error` set rather than raising an exception. If this occurs, the invocation silently "succeeds" with incomplete output.

**Required change** (applied to all 3 existing stream loops, same pattern as the new Coach `_run_tests_via_sdk`):
```python
if isinstance(message, AssistantMessage):
    # Bug #472 defense: check for API errors returned as messages
    if hasattr(message, 'error') and message.error is not None:
        error_msg = f"SDK returned API error as message: {message.error}"
        logger.error(f"[{task_id}] {error_msg}")
        # For _invoke_with_role: raise AgentInvocationError(error_msg)
        # For _invoke_task_work_implement: break loop, return TaskWorkResult(success=False)
        # For _execute_via_sdk: raise DesignPhaseError(phase="design", error=error_msg)
    for block in message.content:
        ...
```

This is a low-risk, additive change — the `.error` field is `None` in normal operation, so the check short-circuits immediately. Only fires on the #472 edge case.

Four additional lower-priority findings from this audit were documented separately in `docs/research/player-agent-sdk-audit-v0.1.36.md` and deferred as non-blocking.

## Test Execution Log
[Automatically populated by /task-work]
