---
id: TASK-IMP-9CE6
title: "Implement Claude Agent SDK Integration in AgentInvoker"
status: completed
task_type: implementation
created: 2025-12-24T00:00:00Z
updated: 2025-12-24T00:00:00Z
completed: 2025-12-24T00:00:00Z
priority: high
tags: [feature-build, claude-agent-sdk, agent-invoker, sdk-integration]
complexity: 5
estimated_hours: 2-3
origin_review: TASK-REV-FB02
origin_wave: TASK-FB-W1
implementation_mode: direct
---

# Implement Claude Agent SDK Integration in AgentInvoker

## Overview

Replace the `NotImplementedError` placeholder in `AgentInvoker._invoke_with_role()` with actual Claude Agent SDK `query()` calls. This is the **only blocking work** remaining for the feature-build/AutoBuild system.

## Context from Review (TASK-REV-FB02)

The architectural review found:
- ✅ `AutoBuildOrchestrator` complete (1095 lines)
- ✅ `AgentInvoker` 95% complete (651 lines)
- ✅ CLI commands complete (`guardkit autobuild task`)
- ⚠️ SDK placeholder at lines 480-516 needs replacement

## Requirements

### Functional Requirements

1. **FR-1**: Replace `NotImplementedError` with SDK `query()` call
   - Import from `claude_agent_sdk` (correct package name)
   - Use `ClaudeAgentOptions` (correct class name)
   - Stream messages via `async for`

2. **FR-2**: Configure SDK options correctly
   - Player: `permission_mode="acceptEdits"`, full tools
   - Coach: `permission_mode="bypassPermissions"`, read-only tools
   - Both: `setting_sources=["project"]` to load CLAUDE.md

3. **FR-3**: Handle SDK-specific exceptions
   - Map `CLINotFoundError` → `AgentInvocationError`
   - Map `ProcessError` → `AgentInvocationError`
   - Map `CLIJSONDecodeError` → `AgentInvocationError`
   - Map `asyncio.TimeoutError` → `SDKTimeoutError`

4. **FR-4**: Add `claude-agent-sdk` to `pyproject.toml`

## Files to Modify

### 1. `guardkit/orchestrator/agent_invoker.py`

**Location**: Lines 480-516 (`_invoke_with_role` method)

**Current code** (placeholder):
```python
async def _invoke_with_role(
    self,
    prompt: str,
    agent_type: Literal["player", "coach"],
    allowed_tools: list[str],
    permission_mode: Literal["acceptEdits", "default"],
    model: str,
) -> None:
    """Low-level SDK invocation with role-based permissions."""
    try:
        # For now, raise NotImplementedError to indicate SDK integration needed
        raise NotImplementedError(
            "Claude Agents SDK integration pending. "
            "This will be completed when SDK is available."
        )
    except asyncio.TimeoutError:
        raise SDKTimeoutError(...)
```

**Updated code** (SDK integration):
```python
async def _invoke_with_role(
    self,
    prompt: str,
    agent_type: Literal["player", "coach"],
    allowed_tools: list[str],
    permission_mode: Literal["acceptEdits", "default", "bypassPermissions"],
    model: str,
) -> None:
    """Low-level SDK invocation with role-based permissions."""
    from claude_agent_sdk import (
        query,
        ClaudeAgentOptions,
        CLINotFoundError,
        ProcessError,
        CLIJSONDecodeError,
    )

    try:
        options = ClaudeAgentOptions(
            cwd=str(self.worktree_path),
            allowed_tools=allowed_tools,
            permission_mode=permission_mode,
            max_turns=self.max_turns_per_agent,
            model=model,
            setting_sources=["project"],  # Load CLAUDE.md from worktree
        )

        async with asyncio.timeout(self.sdk_timeout_seconds):
            async for message in query(prompt=prompt, options=options):
                # Progress tracking handled by ProgressDisplay
                # Agent writes report to JSON file, loaded after query completes
                pass

    except asyncio.TimeoutError:
        raise SDKTimeoutError(
            f"Agent invocation exceeded {self.sdk_timeout_seconds}s timeout"
        )
    except CLINotFoundError as e:
        raise AgentInvocationError(
            "Claude Code CLI not installed. "
            "Run: npm install -g @anthropic-ai/claude-code"
        ) from e
    except ProcessError as e:
        raise AgentInvocationError(
            f"SDK process failed (exit {e.exit_code}): {e.stderr}"
        ) from e
    except CLIJSONDecodeError as e:
        raise AgentInvocationError(
            f"Failed to parse SDK response: {e}"
        ) from e
    except ImportError as e:
        raise AgentInvocationError(
            "Claude Agent SDK not installed. Run: pip install claude-agent-sdk"
        ) from e
    except Exception as e:
        raise AgentInvocationError(
            f"SDK invocation failed for {agent_type}: {str(e)}"
        ) from e
```

### 2. `guardkit/orchestrator/agent_invoker.py` - Coach permission_mode fix

**Location**: Line 250-252 (in `invoke_coach` method)

**Current**:
```python
permission_mode="default",
```

**Updated**:
```python
permission_mode="bypassPermissions",
```

### 3. `pyproject.toml`

**Add dependency**:
```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "claude-agent-sdk>=0.1.0",
]
```

## Acceptance Criteria

- [x] `_invoke_with_role()` uses SDK `query()` instead of `NotImplementedError`
- [x] Import from `claude_agent_sdk` (correct package name)
- [x] Use `ClaudeAgentOptions` (correct class name)
- [x] Handle SDK-specific exceptions with clear error messages
- [x] Player uses `permission_mode="acceptEdits"`
- [x] Coach uses `permission_mode="bypassPermissions"`
- [x] Include `setting_sources=["project"]` to load CLAUDE.md
- [x] Timeout handling works correctly
- [x] `claude-agent-sdk` added to `requirements.txt` (project uses requirements.txt, not pyproject.toml)
- [x] Existing tests still pass (32/32 tests passing)
- [ ] Manual smoke test with simple task succeeds (pending - requires Claude Code CLI)

## Testing

### Unit Test (Mock SDK)

Add to `tests/unit/orchestrator/test_agent_invoker_sdk.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.exceptions import AgentInvocationError

@pytest.mark.asyncio
async def test_invoke_with_role_calls_sdk():
    """Test that _invoke_with_role calls SDK query()."""
    async def mock_query_gen(*args, **kwargs):
        yield MagicMock(type="assistant")
        yield MagicMock(type="result", subtype="success")

    with patch("claude_agent_sdk.query", side_effect=mock_query_gen):
        invoker = AgentInvoker(worktree_path=Path("/tmp/test"))
        await invoker._invoke_with_role(
            prompt="Test",
            agent_type="player",
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits",
            model="claude-sonnet-4-5-20250514",
        )

@pytest.mark.asyncio
async def test_invoke_handles_cli_not_found():
    """Test that CLINotFoundError is mapped correctly."""
    from claude_agent_sdk import CLINotFoundError

    async def mock_query_error(*args, **kwargs):
        raise CLINotFoundError("Claude Code not found")
        yield  # Make it a generator

    with patch("claude_agent_sdk.query", side_effect=mock_query_error):
        invoker = AgentInvoker(worktree_path=Path("/tmp/test"))
        with pytest.raises(AgentInvocationError) as exc_info:
            await invoker._invoke_with_role(
                prompt="Test",
                agent_type="player",
                allowed_tools=["Read"],
                permission_mode="acceptEdits",
                model="claude-sonnet-4-5-20250514",
            )

        assert "Claude Code CLI not installed" in str(exc_info.value)
```

### Smoke Test (Manual)

```bash
# 1. Install Claude Code CLI (if not installed)
npm install -g @anthropic-ai/claude-code

# 2. Authenticate
claude  # Follow prompts

# 3. Install Python SDK
pip install claude-agent-sdk

# 4. Run simple task
guardkit autobuild task TASK-TEST-001

# 5. Verify Player and Coach execute
# 6. Check reports created in .guardkit/autobuild/
```

## Prerequisites

Before implementation:

1. **Install Claude Agent SDK**:
   ```bash
   pip install claude-agent-sdk
   ```

2. **Verify Claude Code CLI installed** (SDK runtime dependency):
   ```bash
   which claude
   # If not found:
   npm install -g @anthropic-ai/claude-code
   ```

3. **Authenticate**:
   ```bash
   claude  # Follow prompts
   ```

## Implementation Notes

### Why Direct Implementation (Not /task-work)

This task modifies a single method with clear requirements:
1. **Scope is narrow**: Replace ~20 lines in one method
2. **Pattern is documented**: SDK documentation provides exact pattern
3. **Existing tests cover orchestration**: No new test framework needed
4. **Risk is low**: Isolated change with clear rollback

Use Claude Code directly for faster iteration.

### Coach Decision via output_format (Enhancement)

Consider using SDK `output_format` for structured Coach output instead of file-based decisions:

```python
coach_options = ClaudeAgentOptions(
    ...
    output_format={
        "type": "json_schema",
        "schema": COACH_DECISION_SCHEMA
    },
)

async for message in query(prompt=prompt, options=coach_options):
    if isinstance(message, ResultMessage):
        if message.result:
            coach_decision = json.loads(message.result)
```

This is optional for Wave 1 but recommended for reliability.

## Related

- **TASK-REV-FB02**: Architectural review that identified this work
- **TASK-FB-W1**: Original wave task (detailed SDK documentation)
- **TASK-FB-W2**: CLI task (SUPERSEDED - existing CLI sufficient)
- **guardkit/cli/autobuild.py**: Existing CLI to use with this integration
