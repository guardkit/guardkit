# Review Report: TASK-REV-FB02

## Executive Summary

This architectural review assesses the feature-build (AutoBuild) integration readiness, identifying gaps between planned SDK integration and existing implementation. The codebase is **95% complete** with a well-designed architecture. Only **Wave 1 (SDK integration)** requires actual implementation - approximately 20-30 lines of code replacement.

**Architecture Score: 82/100**

| Category | Score | Notes |
|----------|-------|-------|
| SOLID Compliance | 8/10 | Strong SRP and DIP; minor OCP opportunity |
| DRY Adherence | 9/10 | Excellent code reuse; helper methods centralized |
| YAGNI Compliance | 9/10 | Auto-merge removed per prior review; minimal over-engineering |
| Integration Readiness | 7/10 | SDK placeholder exists; some gaps documented |
| Documentation | 9/10 | Comprehensive task files; SDK verification complete |

**Recommendation: PROCEED with Wave 1 implementation**

---

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard
- **Duration**: ~45 minutes
- **Reviewer**: Opus 4.5 via /task-review

---

## Findings

### Finding 1: SDK Package and Import Inconsistencies ⚠️ CRITICAL

**Evidence**: Wave task files contain outdated package references.

| Location | Current (Incorrect) | Required (Correct) |
|----------|--------------------|--------------------|
| [README.md:65](tasks/backlog/feature-build/README.md#L65) | `pip install claude-code-sdk` | `pip install claude-agent-sdk` |
| [IMPLEMENTATION-GUIDE.md:179](tasks/backlog/feature-build/IMPLEMENTATION-GUIDE.md#L179) | `pip install claude-code-sdk` | `pip install claude-agent-sdk` |
| [agent_invoker.py:485](guardkit/orchestrator/agent_invoker.py#L485) | `claude_code_sdk` | `claude_agent_sdk` |
| [agent_invoker.py:487](guardkit/orchestrator/agent_invoker.py#L487) | `ClaudeCodeOptions` | `ClaudeAgentOptions` |

**Impact**: Implementation will fail on import if incorrect package name used.

**RESOLVED in TASK-REV-FB02**: The gap analysis document correctly identifies this issue and provides the correct import:
```python
from claude_agent_sdk import query, ClaudeAgentOptions
```

---

### Finding 2: Coach Permission Mode Mismatch ⚠️ IMPORTANT

**Evidence**: [agent_invoker.py:250-252](guardkit/orchestrator/agent_invoker.py#L250-L252)

**Current**:
```python
await self._invoke_with_role(
    ...
    permission_mode="default",  # Coach currently uses "default"
)
```

**Required** (per SDK verification):
```python
permission_mode="bypassPermissions"  # Coach is read-only, no prompts needed
```

**Rationale**: Coach has read-only tools only (`Read`, `Bash`, `Grep`, `Glob`). Using `"default"` mode would prompt for permission on each Bash command, slowing execution. Since Coach cannot modify files anyway, `"bypassPermissions"` is appropriate.

**Impact**: Medium - affects execution speed but not correctness.

---

### Finding 3: Coach Output Method - File vs output_format 💡 ENHANCEMENT

**Evidence**: [TASK-REV-FB02:240-266](tasks/backlog/TASK-REV-FB02-integration-review.md#L240-L266)

**Current design**: Coach writes decision to `.guardkit/autobuild/{task_id}/coach_turn_{turn}.json`

**Better approach**: Use SDK `output_format` for structured JSON output directly in `ResultMessage.result`:

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

**Benefits**:
1. Eliminates file I/O dependency
2. More reliable (no "file not found" edge cases)
3. SDK guarantees JSON schema compliance
4. Simpler error handling

**Recommendation**: Implement Coach with `output_format` for Wave 1. Keep file-based Player reports (more complex output).

---

### Finding 4: SDK Exception Handling Not Implemented ⚠️ IMPORTANT

**Evidence**: [agent_invoker.py:480-516](guardkit/orchestrator/agent_invoker.py#L480-L516)

**Current**: Placeholder raises `NotImplementedError`

**Missing**: SDK-specific exception imports and mapping:

```python
from claude_agent_sdk import (
    CLINotFoundError,
    CLIConnectionError,
    ProcessError,
    CLIJSONDecodeError,
    ClaudeSDKError,
)
```

**Required exception mapping**:
| SDK Exception | Maps To | When |
|---------------|---------|------|
| `CLINotFoundError` | `AgentInvocationError` | Claude Code CLI not installed |
| `ProcessError` | `AgentInvocationError` | CLI process fails (has `exit_code`, `stderr`) |
| `CLIJSONDecodeError` | `AgentInvocationError` | JSON parsing fails |
| `asyncio.TimeoutError` | `SDKTimeoutError` | Timeout exceeded |

**Impact**: High - unhandled exceptions will cause unclear error messages.

---

### Finding 5: Missing `setting_sources` for CLAUDE.md Loading ⚠️ IMPORTANT

**Evidence**: [agent_invoker.py:487-493](guardkit/orchestrator/agent_invoker.py#L487-L493) (placeholder)

**Current placeholder** omits `setting_sources`:
```python
# options = ClaudeCodeOptions(
#     cwd=str(self.worktree_path),
#     allowed_tools=allowed_tools,
#     permission_mode=permission_mode,
#     max_turns=self.max_turns_per_agent,
#     model=model,
# )
```

**Required** (per SDK verification):
```python
options = ClaudeAgentOptions(
    ...
    setting_sources=["project"],  # Load CLAUDE.md from worktree
)
```

**Impact**: High - Player agent won't inherit quality gate instructions from CLAUDE.md without this option.

---

### Finding 6: Progress Display Integration Unclear 💡 ENHANCEMENT

**Evidence**: [TASK-REV-FB02:376-389](tasks/backlog/TASK-REV-FB02-integration-review.md#L376-L389)

**Current**: `ProgressDisplay` exists but SDK message streaming integration not defined.

**SDK provides**:
- `AssistantMessage` with `TextBlock`, `ToolUseBlock`
- `ResultMessage` with `duration_ms`, `total_cost_usd`

**Recommendation**: Wire SDK message types to `ProgressDisplay` methods in Wave 1:
```python
async for message in query(prompt=prompt, options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, ToolUseBlock):
                self._progress_display.log_tool_use(block.name)
```

**Impact**: Low - affects UX polish, not core functionality.

---

### Finding 7: Worktree Cleanup Policy Undefined ⚠️ DESIGN GAP

**Evidence**: [TASK-REV-FB02:386-395](tasks/backlog/TASK-REV-FB02-integration-review.md#L386-L395)

**Current**: Worktrees preserved on all exits (correct for human review).

**Missing**: No cleanup mechanism for old worktrees.

**Current behavior**:
- Success: Worktree preserved for review
- Failure: Worktree preserved for debugging
- After merge: Worktree persists indefinitely

**Recommendation**: Document manual cleanup process for now (YAGNI - defer automated cleanup):
```bash
# After successful merge
guardkit worktree cleanup TASK-XXX
```

**Impact**: Low - disk space concern only, not functional.

---

### Finding 8: Wave 2-4 Reference Outdated Components ℹ️ INFORMATIONAL

**Evidence**: Wave 2-4 task files reference `DialecticalOrchestrator` and `sdk_orchestrator.py`, but the actual implementation uses `AutoBuildOrchestrator` and `agent_invoker.py`.

**Example**: [TASK-FB-W2:62-65](tasks/backlog/feature-build/TASK-FB-W2-cli-command.md#L62-L65)
```python
from guardkit.orchestrator.sdk_orchestrator import (
    DialecticalOrchestrator,  # WRONG - doesn't exist
```

**Actual**:
```python
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,  # CORRECT
```

**Impact**: Low - Wave 2-4 are deferred; documentation can be corrected later.

**Recommendation**: Update Wave 2-4 task files OR mark them as superseded by existing `cli/autobuild.py`.

---

## SOLID/DRY/YAGNI Analysis

### SOLID Compliance: 8/10

| Principle | Score | Assessment |
|-----------|-------|------------|
| **S**ingle Responsibility | 9/10 | `AgentInvoker` handles SDK invocation only; `AutoBuildOrchestrator` handles loop logic |
| **O**pen/Closed | 7/10 | Could use strategy pattern for Player/Coach invocation (minor improvement) |
| **L**iskov Substitution | 9/10 | `Worktree` dataclass is immutable, substitutable |
| **I**nterface Segregation | 8/10 | Clean separation between CLI, orchestrator, invoker |
| **D**ependency Inversion | 9/10 | `AutoBuildOrchestrator` accepts `AgentInvoker` via DI for testability |

**Strengths**:
- Excellent dependency injection pattern in `AutoBuildOrchestrator.__init__`
- Clean helper method extraction (`_invoke_player_safely`, `_invoke_coach_safely`)
- Immutable `TurnRecord` dataclass for audit trail

**Improvement opportunity**: Extract SDK options construction to separate factory (minor).

### DRY Adherence: 9/10

**Strengths**:
- `_invoke_with_role()` centralizes SDK call logic
- `_build_player_prompt()` / `_build_coach_prompt()` avoid duplication
- Exception hierarchy defined once in `exceptions.py`

**Minor duplication**:
- Report validation logic (`_validate_player_report`, `_validate_coach_decision`) could use shared schema validator

### YAGNI Compliance: 9/10

**Strengths**:
- Auto-merge removed per prior architectural review
- State persistence deferred to Wave 3 (not in MVP)
- Resume capability deferred (not needed for initial release)
- Human checkpoint mid-loop removed (YAGNI)

**No premature optimization detected**.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SDK package name wrong | Low (documented) | High | TASK-FB-W1 has correct imports |
| Coach file-based output fails | Medium | Medium | Use `output_format` instead |
| Progress display missing | Low | Low | Core functionality works without it |
| Worktree cleanup forgotten | Medium | Low | Document manual cleanup |
| Wave 2-4 outdated | Low | Low | Already superseded by existing CLI |

---

## Recommendations

### R1: Update Wave 1 with SDK Corrections [HIGH PRIORITY]

Update [TASK-FB-W1-sdk-orchestrator.md](tasks/backlog/feature-build/TASK-FB-W1-sdk-orchestrator.md) to include:

1. ✅ Correct import: `from claude_agent_sdk import ...` (already done)
2. ✅ Correct class: `ClaudeAgentOptions` (already done)
3. ⚠️ Add SDK exception handling
4. ⚠️ Add `setting_sources=["project"]`
5. ⚠️ Change Coach `permission_mode` to `"bypassPermissions"`
6. 💡 Use `output_format` for Coach decisions

### R2: Use output_format for Coach [RECOMMENDED]

Replace file-based Coach decision with SDK structured output:

```python
coach_options = ClaudeAgentOptions(
    allowed_tools=["Read", "Bash", "Glob", "Grep"],
    cwd=str(self.worktree_path),
    permission_mode="bypassPermissions",
    output_format={
        "type": "json_schema",
        "schema": COACH_DECISION_SCHEMA
    },
    setting_sources=["project"],
)
```

**Benefits**: More reliable, no file I/O issues, SDK enforces schema.

### R3: Defer Wave 2-4 [RECOMMENDED]

The existing `cli/autobuild.py` already provides:
- ✅ `guardkit autobuild task TASK-XXX` command
- ✅ `--max-turns`, `--model`, `--verbose` options
- ✅ Rich progress display
- ✅ Status command

Wave 2-4 are redundant with existing implementation. Recommend:
1. Complete Wave 1 (SDK integration)
2. Test with real tasks
3. Only implement Wave 2-4 if real-world testing reveals needs

### R4: Document Worktree Cleanup [LOW PRIORITY]

Add to CLAUDE.md AutoBuild section:
```markdown
### Worktree Management

After successful merge:
```bash
# List worktrees
guardkit worktree list

# Cleanup specific worktree
guardkit worktree cleanup TASK-XXX
```

### R5: Update Documentation with SDK Verification [LOW PRIORITY]

Update [README.md](tasks/backlog/feature-build/README.md) and [IMPLEMENTATION-GUIDE.md](tasks/backlog/feature-build/IMPLEMENTATION-GUIDE.md) with:
- Correct package name: `claude-agent-sdk`
- Prerequisites section with Claude Code CLI installation
- SDK verification results from TASK-REV-FB02

---

## Implementation Readiness Summary

| Component | Status | Blocking? |
|-----------|--------|-----------|
| `AutoBuildOrchestrator` | ✅ Complete | No |
| `AgentInvoker` | ⚠️ SDK placeholder | **Yes - Wave 1** |
| `ProgressDisplay` | ✅ Complete | No |
| `WorktreeManager` | ✅ Complete | No |
| CLI Commands | ✅ Complete | No |
| Exception Classes | ✅ Complete | No |
| SDK Package | ✅ Verified available | No |
| SDK API | ✅ Verified compatible | No |
| System Prompts | ⚠️ Need enhancement | No (can defer) |

**Blocking work**: Replace `NotImplementedError` in `AgentInvoker._invoke_with_role()` with actual SDK calls.

**Estimated effort**: 2-3 hours for Wave 1.

---

## Decision Matrix

| Option | Effort | Risk | Recommendation |
|--------|--------|------|----------------|
| Complete Wave 1 only | 2-3h | Low | ✅ **RECOMMENDED** |
| Complete all waves | 8-12h | Medium | Defer waves 2-4 |
| Add state persistence (W3) | +2-3h | Low | Defer to MVP+1 |
| Add resume capability | +1-2h | Low | Defer to MVP+1 |

---

## Appendix

### SDK Verification Reference

From TASK-REV-FB02 SDK verification (2025-12-24):

**Installation**:
```bash
pip install claude-agent-sdk
```

**Correct imports**:
```python
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError,
)
```

**ClaudeAgentOptions** (verified):
| Option | Type | Player | Coach |
|--------|------|--------|-------|
| `cwd` | `str \| Path` | ✅ worktree | ✅ worktree |
| `allowed_tools` | `list[str]` | Full | Read-only |
| `permission_mode` | `str` | `"acceptEdits"` | `"bypassPermissions"` |
| `max_turns` | `int` | 30 | 30 |
| `model` | `str` | Configurable | Configurable |
| `setting_sources` | `list[str]` | `["project"]` | `["project"]` |
| `output_format` | `dict` | - | JSON schema |

### Files Reviewed

1. [TASK-REV-FB02-integration-review.md](tasks/backlog/TASK-REV-FB02-integration-review.md)
2. [README.md](tasks/backlog/feature-build/README.md)
3. [IMPLEMENTATION-GUIDE.md](tasks/backlog/feature-build/IMPLEMENTATION-GUIDE.md)
4. [TASK-FB-W1-sdk-orchestrator.md](tasks/backlog/feature-build/TASK-FB-W1-sdk-orchestrator.md)
5. [TASK-FB-W2-cli-command.md](tasks/backlog/feature-build/TASK-FB-W2-cli-command.md)
6. [TASK-FB-W3-state-persistence.md](tasks/backlog/feature-build/TASK-FB-W3-state-persistence.md)
7. [TASK-FB-W4-testing-docs.md](tasks/backlog/feature-build/TASK-FB-W4-testing-docs.md)
8. [TASK-REV-FB01-plan-feature-build-command.md](tasks/backlog/TASK-REV-FB01-plan-feature-build-command.md)
9. [agent_invoker.py](guardkit/orchestrator/agent_invoker.py)
10. [autobuild.py](guardkit/orchestrator/autobuild.py)
11. [cli/autobuild.py](guardkit/cli/autobuild.py)
12. [exceptions.py](guardkit/orchestrator/exceptions.py)

---

*Report generated: 2025-12-24*
*Review mode: architectural*
*Review depth: standard*
