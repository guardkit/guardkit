# Player Agent SDK Audit — claude-agent-sdk v0.1.36

**Date**: 2026-02-17
**Auditor**: Claude (via Rich's SDK version validation session)
**Scope**: All SDK integration points in `agent_invoker.py` and `task_work_interface.py`
**SDK Version**: `claude-agent-sdk` v0.1.36 (PyPI latest, 2026-02-13)
**Trigger**: Pre-implementation validation for TASK-PCTD-3182 (Wave 3)

## Summary

The Player agent and design phase SDK integration are **correct and working well**. All imports, option classes, exception types, content block processing, and async patterns are valid against v0.1.36. No regressions or breaking changes were found.

One medium-priority gap (AssistantMessage.error not checked) was folded into TASK-PCTD-3182. Four lower-priority findings are documented below for future reference. None require immediate action.

## Files Audited

| File | SDK Invocation Methods | Status |
|------|----------------------|--------|
| `guardkit/orchestrator/agent_invoker.py` | `_invoke_with_role()`, `_invoke_task_work_implement()` | ✅ Correct |
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | `_execute_via_sdk()` | ✅ Correct |

## Verified Correct (No Action)

These aspects were explicitly validated and confirmed working:

- **Package name**: All imports use `claude_agent_sdk` (not legacy `claude_code_sdk`)
- **Options class**: All use `ClaudeAgentOptions` (not legacy `ClaudeCodeOptions`)
- **pyproject.toml**: `claude-agent-sdk>=0.1.0` in `[autobuild]` and `[all]` extras
- **Exception types**: `CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError` imported correctly from `claude_agent_sdk`
- **Lazy imports**: SDK imported inside methods to avoid import-time failures when SDK not installed — correct pattern
- **Heartbeat/timeout**: `asyncio.timeout()` + `async_heartbeat()` context manager — robust
- **TaskWorkStreamParser**: Regex parsing and ToolUseBlock file tracking both work correctly
- **ClaudeAgentOptions fields**: `cwd`, `allowed_tools`, `permission_mode`, `max_turns`, `model`, `setting_sources` — all valid v0.1.36 fields
- **Content block processing**: `TextBlock`, `ToolUseBlock`, `ToolResultBlock`, `ResultMessage` — all correct types, correctly imported

## Folded into TASK-PCTD-3182

**Finding 1 (Medium): `AssistantMessage.error` field not checked**

All three SDK stream loops process `AssistantMessage.content` but none check the `.error` field (added SDK v0.1.9, GitHub Issue #472). API errors can silently arrive as messages rather than exceptions. This was folded into TASK-PCTD-3182 as an additional acceptance criterion since the same pattern is already being implemented for the new Coach `_run_tests_via_sdk()` method.

## Deferred Findings

### Finding 2 (Low): Missing `model` parameter in delegation paths

**Location**: `agent_invoker._invoke_task_work_implement()` line ~920, `task_work_interface._execute_via_sdk()` line ~280

`_invoke_with_role()` correctly passes `model=self.player_model` to `ClaudeAgentOptions`, but the task-work delegation path and design phase path both omit `model`, relying on the SDK's default (typically the user's subscription default model).

**Assessment**: This is likely **intentional** — the delegation paths benefit from the most capable model available, and the model is not a correctness concern for design/implementation work. The direct invocation path explicitly sets the model because Coach uses Haiku for cost efficiency.

**Risk**: None in current usage. Would only matter if the SDK default changed to an unexpected model, or if API billing needed per-invocation model tracking.

**Recommendation**: No action required. If model pinning becomes necessary, add `model=self.player_model` to both `ClaudeAgentOptions` constructors.

### Finding 3 (Low): Dead code branch — `ToolResultBlock` inside `AssistantMessage`

**Location**: `agent_invoker._invoke_task_work_implement()` approximately line ~960

```python
if isinstance(message, AssistantMessage):
    for block in message.content:
        ...
        elif isinstance(block, ToolResultBlock):  # ← never matches
            collected_output.append(str(block.content))
```

Per the SDK message flow, `ToolResultBlock` lives in `UserMessage.content` (tool execution results from the environment), not `AssistantMessage.content` (Claude's response containing `TextBlock` and `ToolUseBlock`). This branch never executes.

The same pattern appears in `task_work_interface._execute_via_sdk()`.

**Assessment**: Completely harmless — the `isinstance` check simply never matches and falls through. The code works correctly because file tracking happens via `ToolUseBlock` (Claude's tool call request) and quality gate parsing happens via `TextBlock` (Claude describing results in natural language). The actual tool results in `UserMessage` are not needed since the information is redundant.

**Risk**: None. Dead code only.

**Recommendation**: Could be removed for clarity in a future cleanup pass. Not worth a dedicated task. If removed, add a comment explaining why `UserMessage` tool results are intentionally skipped (they're redundant with TextBlock output).

### Finding 4 (Low): Rate limit detection missing from `_invoke_with_role()`

**Location**: `agent_invoker._invoke_with_role()` exception handler (~line 650)

`_invoke_task_work_implement()` has proper rate limit detection in its exception handler — it calls `detect_rate_limit()` and raises `RateLimitExceededError` with the reset time. However, `_invoke_with_role()` catches generic `Exception` and wraps it as `AgentInvocationError`, losing any rate limit information.

**Assessment**: `_invoke_with_role()` is used for legacy direct Player invocation and for Coach agent invocation. Rate limit hits through this path would be reported as generic `AgentInvocationError` without the reset time, making the orchestrator's rate limit backoff logic less effective.

**Risk**: Low — rate limit hits are infrequent, and the orchestrator already has retry logic. The error message text would still contain "rate limit" or "429" which could be parsed upstream. The main loss is the structured `reset_time` field.

**Recommendation**: Add `detect_rate_limit()` call to `_invoke_with_role()`'s generic exception handler, matching the pattern in `_invoke_task_work_implement()`. Could be done as a minor improvement during any future work on `_invoke_with_role()`.

### Finding 5 (Cosmetic): `str(block.content)` for ToolResultBlock multi-part content

**Location**: Same dead code branch as Finding 3

When `ToolResultBlock.content` is `list[dict[str, Any]]` (the multi-part response format), `str()` produces Python repr: `[{'type': 'text', 'text': '...'}]` rather than extracting the text content.

**Assessment**: Since the branch is dead code (Finding 3), this is purely cosmetic. If the branch were ever reached, it would produce garbled output in `collected_output` but wouldn't cause errors.

**Risk**: None.

**Recommendation**: No action. If Finding 3's dead code is ever activated (e.g., SDK changes message routing), the content extraction should use the same `_extract_content_text()` helper that TASK-PCTD-3182 introduces for Coach's `_run_tests_via_sdk()`.

## Version Compatibility Notes

For reference, these v0.1.36 fields are **new since v0.1.0** but unused by our implementation:

| Field | Added In | Our Usage |
|-------|----------|-----------|
| `ClaudeAgentOptions.tools` | v0.1.5 | Unused — we use `allowed_tools` |
| `ClaudeAgentOptions.effort` | v0.1.12 | Unused |
| `ClaudeAgentOptions.thinking` | v0.1.8 | Unused |
| `ClaudeAgentOptions.structured_output` | v0.1.7 | Unused |
| `ResultMessage.structured_output` | v0.1.7 | Unused |
| `ResultMessage.total_cost_usd` | v0.1.3 | Unused — could be useful for cost tracking |
| `UserMessage.uuid` | v0.1.4 | Unused |
| `AssistantMessage.error` | v0.1.9 | **Should be used** — addressed in TASK-PCTD-3182 |

None of these new fields break existing code — they all have `None` defaults.
