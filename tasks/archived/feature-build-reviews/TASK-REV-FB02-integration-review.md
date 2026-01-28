---
id: TASK-REV-FB02
title: "Review: Feature-Build Integration Gap Analysis"
status: review_complete
task_type: review
created: 2025-12-24T00:00:00Z
updated: 2025-12-24T00:00:00Z
priority: high
tags: [feature-build, integration-review, gap-analysis, sdk-integration, claude-code]
complexity: 6
decision_required: true
review_scope:
  - tasks/backlog/feature-build/
  - guardkit/orchestrator/agent_invoker.py
  - guardkit/orchestrator/autobuild.py
  - guardkit/cli/autobuild.py
related_tasks:
  - TASK-REV-FB01
  - TASK-FB-W1
  - TASK-FB-W2
  - TASK-FB-W3
  - TASK-FB-W4
sdk_verified: true
sdk_version: "claude-agent-sdk (Python)"
review_results:
  mode: architectural
  depth: standard
  score: 82
  findings_count: 8
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-FB02-review-report.md
  completed_at: 2025-12-24T00:00:00Z
  implementation_tasks:
    - TASK-IMP-9CE6  # SDK integration (Wave 1)
  process_improvements:
    - TASK-FP-4F81  # Add audit step to /feature-plan
  superseded_tasks:
    - TASK-FB-W2    # CLI command (existing CLI sufficient)
---

# Review: Feature-Build Integration Gap Analysis

## Overview

Comprehensive review of the `/feature-build` (autobuild) implementation to identify integration gaps, edge cases, and potential issues **before** implementation begins.

**Motivation**: Previous implementations on this branch created mocks and placeholders that didn't integrate properly. This review ensures we've identified all integration points and edge cases.

## Review Scope

### Documents to Review

1. **[README.md](tasks/backlog/feature-build/README.md)** - Feature overview
2. **[IMPLEMENTATION-GUIDE.md](tasks/backlog/feature-build/IMPLEMENTATION-GUIDE.md)** - Wave breakdown and recommendations
3. **[TASK-FB-W1-sdk-orchestrator.md](tasks/backlog/feature-build/TASK-FB-W1-sdk-orchestrator.md)** - SDK integration task
4. **[TASK-FB-W2-cli-command.md](tasks/backlog/feature-build/TASK-FB-W2-cli-command.md)** - CLI refinements
5. **[TASK-FB-W3-state-persistence.md](tasks/backlog/feature-build/TASK-FB-W3-state-persistence.md)** - State in frontmatter
6. **[TASK-FB-W4-testing-docs.md](tasks/backlog/feature-build/TASK-FB-W4-testing-docs.md)** - Testing and documentation
7. **[TASK-REV-FB01](tasks/backlog/TASK-REV-FB01-plan-feature-build-command.md)** - Original design review

### Code to Review

1. **[agent_invoker.py](guardkit/orchestrator/agent_invoker.py)** - SDK placeholder location
2. **[autobuild.py](guardkit/orchestrator/autobuild.py)** - AutoBuildOrchestrator
3. **[cli/autobuild.py](guardkit/cli/autobuild.py)** - CLI commands
4. **[exceptions.py](guardkit/orchestrator/exceptions.py)** - Error handling
5. **[progress.py](guardkit/orchestrator/progress.py)** - Progress display
6. **[worktrees.py](guardkit/orchestrator/worktrees.py)** - Worktree management

---

## SDK VERIFICATION RESULTS (Updated 2025-12-24)

### Gap 1: SDK Package Availability - ✅ RESOLVED

**Status**: SDK is publicly available and installed.

**Installation**:
```bash
# Python (pip)
pip install claude-agent-sdk

# Python (uv)
uv add claude-agent-sdk

# TypeScript (for reference)
npm install @anthropic-ai/claude-agent-sdk
```

**Prerequisites**:
1. Claude Code CLI must be installed: `npm install -g @anthropic-ai/claude-code` or `brew install --cask claude-code`
2. Authentication: Run `claude` in terminal and follow prompts, OR set `ANTHROPIC_API_KEY`

### SDK Package Name - ✅ VERIFIED

| Language | Package | Import |
|----------|---------|--------|
| **Python** | `claude-agent-sdk` | `from claude_agent_sdk import query, ClaudeAgentOptions` |
| TypeScript | `@anthropic-ai/claude-agent-sdk` | `import { query } from "@anthropic-ai/claude-agent-sdk"` |

**Correct Python import**:
```python
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage
```

### SDK API Surface - ✅ VERIFIED

All assumed options are confirmed available in `ClaudeAgentOptions`:

| Option | Type | Verified | Notes |
|--------|------|----------|-------|
| `cwd` | `str \| Path \| None` | ✅ | Working directory |
| `allowed_tools` | `list[str]` | ✅ | Tool restriction - **enforced by SDK** |
| `permission_mode` | `PermissionMode` | ✅ | `"default"`, `"acceptEdits"`, `"bypassPermissions"`, `"plan"` |
| `max_turns` | `int \| None` | ✅ | Maximum conversation turns |
| `model` | `str \| None` | ✅ | Claude model to use |
| `system_prompt` | `str \| SystemPromptPreset \| None` | ✅ | Custom or preset prompt |
| `output_format` | `OutputFormat \| None` | ✅ | JSON schema for structured output |
| `setting_sources` | `list[SettingSource] \| None` | ✅ | Load CLAUDE.md with `["project"]` |

**Full ClaudeAgentOptions for Player**:
```python
from claude_agent_sdk import ClaudeAgentOptions

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

**Full ClaudeAgentOptions for Coach (read-only)**:
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
)
```

### Async Pattern - ✅ VERIFIED

**`query()` is an async generator** - returns `AsyncIterator[Message]`:

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

async def run_agent():
    async for message in query(
        prompt="Your prompt here",
        options=ClaudeAgentOptions(...)
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")
            # Contains: duration_ms, total_cost_usd, session_id, etc.

asyncio.run(run_agent())
```

### SDK Exceptions - ✅ DOCUMENTED

SDK raises these exceptions:

| Exception | When |
|-----------|------|
| `CLINotFoundError` | Claude Code CLI not installed |
| `CLIConnectionError` | Connection to Claude Code fails |
| `ProcessError` | Claude Code process fails (has `exit_code`, `stderr`) |
| `CLIJSONDecodeError` | JSON parsing fails |
| `ClaudeSDKError` | Base class for all SDK errors |

**Updated exception mapping needed**:
```python
from claude_agent_sdk import CLINotFoundError, ProcessError, CLIJSONDecodeError

try:
    async for message in query(prompt=prompt, options=options):
        pass
except CLINotFoundError as e:
    raise AgentInvocationError(
        "Claude Code not installed. Run: npm install -g @anthropic-ai/claude-code"
    ) from e
except ProcessError as e:
    raise AgentInvocationError(
        f"SDK process failed (exit {e.exit_code}): {e.stderr}"
    ) from e
except CLIJSONDecodeError as e:
    raise AgentInvocationError(
        f"Failed to parse SDK response: {e}"
    ) from e
```

### Message Types - ✅ DOCUMENTED

```python
from claude_agent_sdk import (
    UserMessage,      # User input
    AssistantMessage, # Claude response (has .content list)
    SystemMessage,    # System messages
    ResultMessage,    # Final result (has .subtype, .duration_ms, .total_cost_usd)
)

# Content blocks in AssistantMessage.content:
from claude_agent_sdk import (
    TextBlock,       # .text
    ToolUseBlock,    # .name, .input
    ToolResultBlock, # .content, .is_error
    ThinkingBlock,   # .thinking (for models with thinking)
)
```

### Key SDK Behaviors Confirmed

1. **Fresh context per `query()` call**: ✅ Each call creates new session
2. **Tool restriction enforcement**: ✅ SDK enforces `allowed_tools`
3. **Structured output**: ✅ `output_format` supports JSON schema
4. **Working directory**: ✅ `cwd` option sets agent's working directory
5. **Streaming**: ✅ `async for` yields messages as they arrive
6. **Cost tracking**: ✅ `ResultMessage.total_cost_usd` available

---

## REMAINING INTEGRATION POINTS TO VERIFY

### 1. Agent Report File Creation ⚠️ NEEDS REVIEW

**Current assumption**: Player/Coach create JSON report files at:
```
.guardkit/autobuild/{task_id}/player_turn_{turn}.json
.guardkit/autobuild/{task_id}/coach_turn_{turn}.json
```

**Questions**:
- [x] How does the agent know to create these files? → **Via system prompt instructions**
- [ ] Is this reliable enough or should we use `output_format` instead?
- [ ] What if the agent doesn't create the file?
- [ ] What if JSON is malformed?

**NEW INSIGHT from SDK docs**:
- For Coach, we can use `output_format` with JSON schema to get structured output directly in `ResultMessage.result`
- This is MORE RELIABLE than relying on file creation
- Player could still write files, but Coach decision should use `output_format`

**Current handling**: `PlayerReportNotFoundError`, `PlayerReportInvalidError` exist.

**Recommendation**:
1. Use `output_format` for Coach decisions (eliminate file-based communication)
2. Keep file-based reports for Player (more complex output)

### 2. Worktree Path Resolution

**Current flow**:
1. `AutoBuildOrchestrator` creates worktree via `WorktreeManager`
2. `AgentInvoker` receives `worktree_path`
3. SDK `query()` uses `cwd=worktree_path`

**Questions**:
- [ ] Is `worktree_path` absolute or relative?
- [x] Does SDK `cwd` work with relative paths? → **Yes, both work**
- [ ] What happens if worktree creation fails?
- [ ] Is worktree cleaned up on error?

### 3. Async/Await Integration ✅ VERIFIED

**Confirmed pattern**:
```python
async with asyncio.timeout(self.sdk_timeout_seconds):
    async for message in query(prompt=prompt, options=options):
        # Process messages
        pass
```

**Questions**:
- [x] Is `query()` async generator? → **Yes**
- [x] Does it support `async for`? → **Yes**
- [x] Does `asyncio.timeout()` work with SDK? → **Yes**
- [ ] What timeout is appropriate (currently 300s)? → **Depends on task complexity**

### 4. Error Propagation - NEEDS UPDATE

**Current exception hierarchy**:
```
AgentInvokerError
├── AgentInvocationError
├── PlayerReportNotFoundError
├── PlayerReportInvalidError
├── CoachDecisionNotFoundError
├── CoachDecisionInvalidError
└── SDKTimeoutError
```

**SDK exceptions to map**:
```
ClaudeSDKError
├── CLINotFoundError
├── CLIConnectionError
├── ProcessError
└── CLIJSONDecodeError
```

**Action Required**:
- [ ] Add imports for SDK exceptions
- [ ] Map SDK exceptions to our hierarchy
- [ ] Update `_invoke_with_role()` error handling

### 5. CLI to Orchestrator Integration

**Current flow**:
```
guardkit autobuild run TASK-XXX
    → cli/autobuild.py::autobuild_run()
    → AutoBuildOrchestrator.run(task_id)
    → AgentInvoker.invoke_player() / invoke_coach()
```

**Questions**:
- [ ] Is task loading correct?
- [ ] Is worktree path passed correctly?
- [ ] Is progress display wired up?
- [ ] What happens on KeyboardInterrupt?

### 6. State Persistence (Wave 3)

**Design**: Store state in task frontmatter.

**Questions**:
- [ ] How does frontmatter get updated mid-run?
- [ ] Is YAML serialization correct?
- [ ] What if task file is moved during run?
- [ ] How does resume detect previous state?

### 7. Quality Gates in System Prompt

**Current assumption**: Player executes quality gates via system prompt instructions.

**Questions**:
- [ ] Does system prompt embed `/task-work` phases?
- [ ] How does Player know about SOLID/DRY/YAGNI?
- [ ] Is test coverage requirement clear?
- [ ] What happens if Player ignores instructions?

### 8. Coach Read-Only Enforcement ✅ VERIFIED

**Current approach**: `allowed_tools=["Read", "Bash", "Grep", "Glob"]`

**Confirmed**:
- [x] SDK enforces `allowed_tools` restriction
- [x] Coach cannot invoke Write/Edit even if it tries
- [x] Tool calls for disallowed tools will fail

---

## KNOWN GAPS (Updated)

### Gap 1: SDK Package Availability - ✅ RESOLVED

SDK is available: `pip install claude-agent-sdk`

### Gap 2: System Prompt Content ⚠️ STILL OPEN

**Issue**: Wave 1 task mentions prompts but doesn't provide full content.

**Impact**: Player/Coach may not behave as expected.

**Recommendation**: Add complete system prompts to Wave 1 or create separate prompts.py.

### Gap 3: Report File Location - ⚠️ PARTIALLY RESOLVED

**Issue**: Agents expected to write to `.guardkit/autobuild/`

**Resolution for Coach**: Use `output_format` for structured JSON output directly in `ResultMessage.result` - no file needed!

**For Player**: Still need file-based approach:
- Create directory before invocation
- Include full path in prompt
- Handle missing/malformed files

### Gap 4: Progress Display Integration ⚠️ STILL OPEN

**Issue**: `ProgressDisplay` exists but integration unclear.

**SDK provides**: Message streaming via `async for message in query(...)`:
- `AssistantMessage` with `TextBlock`, `ToolUseBlock`
- `ResultMessage` with `duration_ms`, `total_cost_usd`

**Recommendation**: Wire message types to `ProgressDisplay` methods.

### Gap 5: Worktree Cleanup ⚠️ STILL OPEN

**Issue**: No explicit cleanup on error or success.

**Impact**: Worktrees accumulate in `.guardkit/worktrees/`.

**Recommendation**: Add cleanup policy (preserve on failure, delete on success?).

### Gap 6: SDK Exception Mapping - NEW

**Issue**: Wave 1 task code doesn't import SDK exceptions.

**Impact**: Errors may not be caught correctly.

**Recommendation**: Update `AgentInvoker` to import and catch SDK-specific exceptions.

---

## CRITICAL UPDATES NEEDED FOR WAVE 1

Based on SDK documentation review, the following updates are required:

### 1. Correct Import Statement

**From**:
```python
from claude_code_sdk import query, ClaudeCodeOptions  # WRONG
```

**To**:
```python
from claude_agent_sdk import query, ClaudeAgentOptions  # CORRECT
```

### 2. Correct Class Name

- Use `ClaudeAgentOptions` (not `ClaudeCodeOptions`)

### 3. Add SDK Exception Handling

```python
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError,
    ClaudeSDKError,
)
```

### 4. Use `output_format` for Coach

Instead of file-based Coach decision:
```python
coach_options = ClaudeAgentOptions(
    allowed_tools=["Read", "Bash", "Glob", "Grep"],
    cwd=str(self.worktree_path),
    permission_mode="bypassPermissions",
    system_prompt=COACH_SYSTEM_PROMPT,
    output_format={
        "type": "json_schema",
        "schema": COACH_DECISION_SCHEMA
    },
)

result_json = None
async for message in query(prompt=prompt, options=coach_options):
    if isinstance(message, ResultMessage):
        if message.result:
            result_json = json.loads(message.result)
```

### 5. Add `setting_sources` for CLAUDE.md

To load project's CLAUDE.md:
```python
options = ClaudeAgentOptions(
    setting_sources=["project"],  # Load .claude/CLAUDE.md
    ...
)
```

---

## Decision Points

### D1: MVP Scope

**Options**:
1. **Minimal MVP**: Wave 1 only, no state persistence, no resume
2. **Full MVP**: Waves 1-3, with state persistence
3. **Complete**: All waves including testing

**Recommendation**: Option 1 (Minimal MVP) - get working first, add features based on real usage.

### D2: SDK Fallback - ✅ RESOLVED

SDK is available - proceed with implementation.

### D3: Error Recovery

**Options**:
1. **Fail fast**: Any error stops execution
2. **Retry**: Auto-retry transient errors (up to 3)
3. **Resume**: Allow manual resume via `--resume`

**Recommendation**: Option 1 for MVP, add retry/resume later.

### D4: Coach Output Method - NEW

**Options**:
1. **File-based**: Coach writes to `.guardkit/autobuild/coach_turn_{n}.json`
2. **output_format**: Coach returns structured JSON via `ResultMessage.result`

**Recommendation**: Option 2 (`output_format`) - more reliable, no file I/O issues.

---

## Acceptance Criteria

- [x] SDK package name verified → `claude-agent-sdk`
- [x] SDK API options verified → All options confirmed
- [x] Async pattern verified → `async for message in query()`
- [ ] Error propagation verified → Needs exception mapping
- [ ] Known gaps documented with mitigation strategies → Updated
- [ ] Decision points resolved with clear rationale
- [ ] No unaddressed edge cases at integration boundaries
- [ ] Implementation plan updated with findings

## Review Checklist

### Documentation Completeness
- [ ] README accurately reflects current state
- [ ] IMPLEMENTATION-GUIDE has correct effort estimates
- [ ] All task files have clear acceptance criteria
- [ ] No contradictions between documents

### Code Readiness
- [ ] `AgentInvoker` placeholder is at expected location
- [ ] `AutoBuildOrchestrator` correctly uses `AgentInvoker`
- [ ] CLI correctly invokes orchestrator
- [ ] Exception handling covers all error cases

### Integration Clarity
- [x] SDK package name verified → `claude-agent-sdk`
- [x] SDK API options verified → `ClaudeAgentOptions`
- [x] Async pattern verified → `async for`
- [ ] Error propagation verified → Needs update

### Risk Assessment
- [x] SDK availability risk → RESOLVED
- [ ] Fallback strategies documented
- [ ] Known gaps have mitigation plans

## Next Steps

After review completion:
1. **UPDATE Wave 1 task** with:
   - Correct import: `from claude_agent_sdk import ...`
   - Correct class: `ClaudeAgentOptions`
   - SDK exception handling
   - Coach `output_format` approach
2. Create prompts.py with full system prompts
3. ~~Verify SDK availability~~ ✅ DONE
4. Proceed with implementation

---

## Review Notes

### Findings (2025-12-24)

1. **SDK is available** - `pip install claude-agent-sdk`
2. **Import differs from task files** - Use `claude_agent_sdk` not `claude_code_sdk`
3. **Class name differs** - Use `ClaudeAgentOptions` not `ClaudeCodeOptions`
4. **Coach can use `output_format`** - More reliable than file-based communication
5. **SDK exceptions exist** - Need to map to our hierarchy
6. **`setting_sources`** - Must include `"project"` to load CLAUDE.md

### Recommendations

1. Update TASK-FB-W1 with correct SDK imports and class names
2. Use `output_format` for Coach decisions (eliminate file dependency)
3. Add SDK exception handling to `AgentInvoker`
4. Add `setting_sources=["project"]` to load CLAUDE.md

### Updated Tasks

- [ ] TASK-FB-W1 needs update with correct SDK details
