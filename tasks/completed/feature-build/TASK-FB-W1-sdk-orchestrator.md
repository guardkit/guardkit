---
id: TASK-FB-W1
title: "Wave 1: Integrate Claude Agent SDK into AgentInvoker"
status: completed
task_type: implementation
created: 2025-12-24T00:00:00Z
updated: 2025-12-25T00:00:00Z
completed: 2025-12-25T00:00:00Z
priority: high
tags: [feature-build, claude-agent-sdk, agent-invoker, wave-1]
complexity: 5
parent_feature: feature-build
wave: 1
estimated_hours: 3-4
dependencies: []
implementation_mode: direct  # Use Claude Code directly (NOT /task-work)
sdk_verified: true
sdk_package: claude-agent-sdk
---

# Wave 1: Integrate Claude Agent SDK into AgentInvoker

## Overview

Replace the `NotImplementedError` placeholder in `AgentInvoker._invoke_with_role()` with actual Claude Agent SDK `query()` calls. The existing orchestrator (`AutoBuildOrchestrator`) and supporting components (`ProgressDisplay`, `WorktreeManager`) are already complete and should be reused.

## What Already Exists (DO NOT RECREATE)

The following components are already implemented and working:

| Component | Location | Status |
|-----------|----------|--------|
| `AutoBuildOrchestrator` | `guardkit/orchestrator/autobuild.py` | ✅ Complete (1095 lines) |
| `AgentInvoker` | `guardkit/orchestrator/agent_invoker.py` | ⚠️ Placeholder at L500-504 |
| `ProgressDisplay` | `guardkit/orchestrator/progress.py` | ✅ Complete |
| `WorktreeManager` | `guardkit/orchestrator/worktrees.py` | ✅ Complete |
| CLI Commands | `guardkit/cli/autobuild.py` | ✅ Complete |
| Exception Classes | `guardkit/orchestrator/exceptions.py` | ✅ Complete |

## SDK Details (VERIFIED 2025-12-24)

### Installation

```bash
# Prerequisites: Claude Code CLI must be installed first
npm install -g @anthropic-ai/claude-code
# OR
brew install --cask claude-code

# Then install Python SDK
pip install claude-agent-sdk
```

### Correct Import (VERIFIED)

```python
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    # Exceptions
    CLINotFoundError,
    CLIConnectionError,
    ProcessError,
    CLIJSONDecodeError,
    ClaudeSDKError,
)
```

### Key SDK Features Confirmed

| Feature | Status | Notes |
|---------|--------|-------|
| Fresh context per `query()` | ✅ | Each call creates new session |
| `allowed_tools` enforcement | ✅ | SDK enforces tool restrictions |
| `output_format` for JSON | ✅ | Use for Coach structured output |
| `cwd` option | ✅ | Sets working directory |
| `permission_mode` | ✅ | `acceptEdits`, `bypassPermissions` |
| `setting_sources` | ✅ | `["project"]` loads CLAUDE.md |
| Async streaming | ✅ | `async for message in query()` |

## Requirements

### Functional Requirements

1. **FR-1**: Replace `NotImplementedError` in `AgentInvoker._invoke_with_role()` with SDK `query()` call
   - Import from `claude_agent_sdk` (NOT `claude_code_sdk`)
   - Use `ClaudeAgentOptions` (NOT `ClaudeCodeOptions`)
   - Stream messages via `async for`

2. **FR-2**: Ensure fresh context per turn
   - Each `query()` call creates a fresh session (SDK guarantees this)
   - No context pollution between Player and Coach turns
   - No context pollution between dialectical turns

3. **FR-3**: Add `claude-agent-sdk` to `pyproject.toml` dependencies

4. **FR-4**: Handle SDK-specific exceptions
   - Map `CLINotFoundError`, `ProcessError`, etc. to our exception hierarchy

## Files to Modify

### 1. `guardkit/orchestrator/agent_invoker.py`

**Location of change**: Lines 480-516 (`_invoke_with_role` method)

**Current code (placeholder)**:
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

**Updated code (SDK integration)**:
```python
async def _invoke_with_role(
    self,
    prompt: str,
    agent_type: Literal["player", "coach"],
    allowed_tools: list[str],
    permission_mode: Literal["acceptEdits", "default", "bypassPermissions"],
    model: str,
) -> None:
    """Low-level SDK invocation with role-based permissions.

    This method handles the actual Claude Agent SDK invocation with
    appropriate permissions and timeout handling.

    Args:
        prompt: Formatted prompt for agent
        agent_type: "player" or "coach"
        allowed_tools: List of allowed SDK tools
        permission_mode: "acceptEdits" (Player) or "bypassPermissions" (Coach)
        model: Model identifier

    Raises:
        AgentInvocationError: If SDK invocation fails
        SDKTimeoutError: If invocation exceeds timeout
    """
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
                # Log progress for debugging
                # SDK messages can be: AssistantMessage, ResultMessage, etc.
                pass  # Progress tracking handled by ProgressDisplay
                # The agent writes its report to a JSON file,
                # which we load after the query completes

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

### 2. `pyproject.toml`

Add dependency:
```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "claude-agent-sdk>=0.1.0",
]
```

## SDK Options Reference

### Player Options (Full Access)

```python
player_options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    cwd=str(worktree_path),
    permission_mode="acceptEdits",  # Auto-approve file edits
    system_prompt=PLAYER_SYSTEM_PROMPT,
    model="claude-sonnet-4-5-20250514",  # Or None for default
    max_turns=30,
    setting_sources=["project"],  # Load CLAUDE.md
)
```

### Coach Options (Read-Only + Structured Output)

```python
coach_options = ClaudeAgentOptions(
    allowed_tools=["Read", "Bash", "Glob", "Grep"],  # NO Write/Edit
    cwd=str(worktree_path),
    permission_mode="bypassPermissions",  # No prompts (read-only anyway)
    system_prompt=COACH_SYSTEM_PROMPT,
    output_format={
        "type": "json_schema",
        "schema": COACH_DECISION_SCHEMA
    },
    model="claude-sonnet-4-5-20250514",
    setting_sources=["project"],
)
```

### Coach Decision via output_format (RECOMMENDED)

Instead of relying on file-based Coach decisions, use `output_format` for structured output:

```python
from claude_agent_sdk import ResultMessage

result_json = None
async for message in query(prompt=prompt, options=coach_options):
    if isinstance(message, ResultMessage):
        if message.result:
            result_json = json.loads(message.result)

# result_json now contains the structured Coach decision
# No need to read from .guardkit/autobuild/coach_turn_{n}.json
```

## SDK Exceptions

| SDK Exception | Maps To | When |
|---------------|---------|------|
| `CLINotFoundError` | `AgentInvocationError` | Claude Code CLI not installed |
| `CLIConnectionError` | `AgentInvocationError` | Connection to CLI fails |
| `ProcessError` | `AgentInvocationError` | CLI process fails (has `exit_code`, `stderr`) |
| `CLIJSONDecodeError` | `AgentInvocationError` | JSON parsing fails |
| `asyncio.TimeoutError` | `SDKTimeoutError` | Timeout exceeded |

## Acceptance Criteria

- [ ] `_invoke_with_role()` uses SDK `query()` instead of `NotImplementedError`
- [ ] Import from `claude_agent_sdk` (correct package name)
- [ ] Use `ClaudeAgentOptions` (correct class name)
- [ ] Handle SDK-specific exceptions (`CLINotFoundError`, `ProcessError`, etc.)
- [ ] Player invocation uses full tool access (`Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`)
- [ ] Coach invocation uses read-only tools (`Read`, `Bash`, `Grep`, `Glob`)
- [ ] Coach uses `permission_mode="bypassPermissions"` (not `"default"`)
- [ ] Include `setting_sources=["project"]` to load CLAUDE.md
- [ ] Timeout handling works correctly
- [ ] `claude-agent-sdk` added to `pyproject.toml`
- [ ] Existing tests still pass
- [ ] Manual smoke test with simple task succeeds

## Testing

### Unit Test (Mock SDK)
```python
# tests/unit/test_agent_invoker_sdk.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from guardkit.orchestrator.agent_invoker import AgentInvoker

@pytest.mark.asyncio
async def test_invoke_with_role_calls_sdk():
    """Test that _invoke_with_role calls SDK query()."""
    # Create async generator mock
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
            await invoker._invoke_with_role(...)

        assert "Claude Code CLI not installed" in str(exc_info.value)
```

### Smoke Test (Manual)
```bash
# 1. Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# 2. Authenticate
claude  # Follow prompts

# 3. Install Python SDK
pip install claude-agent-sdk

# 4. Run simple task
guardkit autobuild run TASK-TEST-001

# 5. Verify Player and Coach execute
# 6. Check reports are created in .guardkit/autobuild/
```

## Dependencies

- **Claude Code CLI**: `npm install -g @anthropic-ai/claude-code` (runtime dependency)
- **Claude Agent SDK**: `pip install claude-agent-sdk` (Python package)
- Existing `AutoBuildOrchestrator` (already complete)
- Existing `ProgressDisplay` (already complete)
- Existing exception classes (already complete)

## Why Direct Implementation (Not /task-work)

This task modifies a single method with clear requirements:
1. **Scope is narrow**: Replace ~20 lines in one method
2. **Pattern is documented**: SDK documentation provides exact pattern
3. **Existing tests cover orchestration**: No new test framework needed
4. **Risk is low**: Isolated change with clear rollback

Use Claude Code directly for faster iteration.

## Common Issues

### "Claude Code not found"
```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code
# OR
brew install --cask claude-code

# Restart terminal, then authenticate
claude
```

### "API key not found"
```bash
# Option 1: Authenticate via CLI
claude  # Follow prompts

# Option 2: Set environment variable
export ANTHROPIC_API_KEY=your-api-key
```

### Import Error
```bash
# Make sure you're using the correct package
pip install claude-agent-sdk  # NOT claude-code-sdk
```
