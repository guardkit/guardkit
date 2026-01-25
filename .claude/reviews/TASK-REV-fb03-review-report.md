# Review Report: TASK-REV-fb03

## Executive Summary

**Critical Finding**: The task-work delegation feature is attempting to call a CLI command (`guardkit task-work`) that does not exist. The delegation flag `use_task_work_delegation=True` is correctly set (TASK-FB-DEL1 is deployed), but the underlying command fails silently because `guardkit task-work` is not implemented in the CLI.

**Root Cause**: Architecture mismatch between the intended delegation target (a Claude Code slash command `/task-work`) and the actual implementation (subprocess call to a non-existent CLI command `guardkit task-work`).

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Comprehensive
- **Duration**: ~30 minutes
- **Reviewer**: Decision analysis with code examination

## Findings

### Finding 1: Missing CLI Command (CRITICAL)

**Evidence**: `guardkit/cli/main.py:70` shows only `autobuild` command is registered:

```python
# Add AutoBuild command group
cli.add_command(autobuild)
```

Available CLI commands:
- `guardkit autobuild task|feature|status`
- `guardkit version`
- `guardkit doctor`

**Missing**: `guardkit task-work`

**Impact**: The subprocess call in `_invoke_task_work_implement()` at `guardkit/orchestrator/agent_invoker.py:1428-1431` fails:

```python
proc = await asyncio.create_subprocess_exec(
    "guardkit",
    "task-work",
    *args,
    ...
)
```

This explains why `task_work_results.json` is never created - the command that would create it doesn't exist.

### Finding 2: Delegation Flag Is Correctly Set (VERIFIED)

**Evidence**: `guardkit/orchestrator/autobuild.py` at lines 640, 659, and 1884 all have:

```python
use_task_work_delegation=True
```

**Verification**: The logs in `complete_failure.md` show:
```
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via task-work delegation for TASK-INFRA-001 (turn 1)
```

TASK-FB-DEL1 fix is deployed and working - the issue is downstream.

### Finding 3: Architecture Design Intent vs Implementation

**Design Intent** (from documentation):
- `/task-work` is a Claude Code slash command that leverages the full subagent infrastructure
- Player should delegate to task-work to achieve 100% code reuse of quality gates
- task-work creates `task_work_results.json` for Coach validation

**Actual Implementation**:
- `_invoke_task_work_implement()` calls `guardkit task-work` as subprocess
- This requires a CLI command, not a slash command
- No CLI command exists for task-work

### Finding 4: Pre-Existing vs Regression

**Not a Regression**: This is a pre-existing implementation gap, not a regression from a working state.

The delegation architecture was designed in TASK-REV-0414 (Option D) and partially implemented, but the CLI command component was never created. The feature worked temporarily via the legacy path (direct SDK invocation), and TASK-FB-DEL1 enabled the new path which exposed the missing implementation.

### Finding 5: Test Coverage Gap

**Evidence**: Tests in `tests/unit/test_agent_invoker.py` mock `_invoke_task_work_implement` rather than testing the actual subprocess call:

```python
with patch.object(
    delegation_invoker,
    "_invoke_task_work_implement",
    new_callable=AsyncMock,
    return_value=mock_result,
) as mock_invoke:
```

This pattern means the missing CLI command was never caught during testing.

## Options Analysis

### Option A: Implement CLI Command (RECOMMENDED)

**Description**: Add `guardkit task-work` CLI command that wraps the task-work slash command logic.

**Pros**:
- Matches existing architecture design
- Enables true subprocess-based delegation
- Works from any context (not just Claude Code)
- Clean separation of concerns

**Cons**:
- Larger implementation effort
- Requires porting slash command logic to Python
- May duplicate logic

**Effort**: Medium-High (3-5 days)
**Risk**: Low

### Option B: Use Claude Agents SDK for Delegation

**Description**: Instead of subprocess, use the Claude Agents SDK to invoke task-work as an agent.

**Pros**:
- Leverages existing slash command infrastructure
- No new CLI command needed
- Consistent with Coach invocation pattern

**Cons**:
- Different architecture than designed
- May have timeout/context issues
- Nested agent invocation complexity

**Effort**: Medium (2-3 days)
**Risk**: Medium

### Option C: Revert to Direct SDK Path (TEMPORARY)

**Description**: Set `use_task_work_delegation=False` to restore direct SDK invocation while proper fix is developed.

**Pros**:
- Immediate fix
- Restores working state
- Buys time for proper solution

**Cons**:
- Loses quality gate code reuse
- Direct SDK doesn't have Phase 4.5 fix loop
- Technical debt

**Effort**: Low (30 minutes)
**Risk**: Low (known working path)

### Option D: Hybrid Approach (PRAGMATIC)

**Description**:
1. Short-term: Revert to direct SDK (Option C)
2. Medium-term: Implement CLI command (Option A)

**Pros**:
- Unblocks current users immediately
- Provides time for proper implementation
- Reduces pressure on implementation quality

**Cons**:
- Temporary technical debt
- Two-phase implementation

**Effort**: Low (immediate) + Medium-High (follow-up)
**Risk**: Low

## Recommendation

**Recommended Decision**: **Option D (Hybrid Approach)**

### Rationale

1. **User Impact**: The current state completely breaks feature-build for all users. An immediate fix is critical.

2. **Root Cause Clarity**: The root cause is now definitively identified - no further investigation needed.

3. **Architecture Integrity**: The task-work delegation design is sound. The missing CLI command should be implemented properly, not worked around permanently.

4. **Risk Management**: The direct SDK path is known to work (used before TASK-FB-DEL1). Reverting is low-risk.

### Implementation Plan

**Phase 1: Immediate Fix (30 min)**
- Create task TASK-FB-REVERT1: Set `USE_TASK_WORK_DELEGATION` default to `false`
- Or: Remove `use_task_work_delegation=True` from autobuild.py (3 locations)
- Test: Verify feature-build works with direct SDK

**Phase 2: Proper Implementation (3-5 days)**
- Create task TASK-CLI-001: Implement `guardkit task-work` CLI command
- Subtasks:
  1. Port task-work phases 3-5.5 to Python
  2. Add results file generation (task_work_results.json)
  3. Add CLI tests
  4. Re-enable delegation flag
  5. End-to-end test

## Decision Matrix (Original)

| Option | User Impact | Effort | Risk | Long-term | Score |
|--------|-------------|--------|------|-----------|-------|
| A: CLI Command | Delayed fix | High | Low | Best | 7/10 |
| B: SDK Delegation | Medium | Medium | Medium | Good | 6/10 |
| C: Revert Only | Immediate | Low | Low | Poor | 5/10 |
| **D: Hybrid** | Immediate | Low+High | Low | Best | **9/10** |

---

## Deep Dive: Option B (SDK-Based Delegation)

**Requested by user** - User context indicates:
- Direct SDK path (Option C/D) didn't produce quality results ("chock full of errors and fallbacks")
- CLI command (Option A) not appealing due to planned LangChain/DeepAgents migration
- Option B is the pragmatic choice before committing resources

### How Option B Would Work

Instead of subprocess call to non-existent CLI:
```python
# Current (BROKEN) - subprocess to non-existent CLI
proc = await asyncio.create_subprocess_exec("guardkit", "task-work", ...)
```

Use SDK query directly:
```python
# Option B - Direct SDK invocation of task-work slash command
from claude_agent_sdk import query, ClaudeAgentOptions

async def _invoke_task_work_implement(self, task_id: str, mode: str) -> TaskWorkResult:
    options = ClaudeAgentOptions(
        cwd=str(self.worktree_path),
        allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        permission_mode="acceptEdits",
        max_turns=50,
        setting_sources=["project"],
    )

    result_data = {}
    async for message in query(
        prompt=f"/task-work {task_id} --implement-only --mode={mode}",
        options=options
    ):
        if message.type == "assistant":
            # Parse quality gate status from output
            text = extract_text(message)
            result_data = self._parse_task_work_stream(text, result_data)
        elif message.type == "result":
            result_data["completed"] = True

    # Create task_work_results.json from parsed data
    self._write_task_work_results(task_id, result_data)

    return TaskWorkResult(success=result_data.get("completed", False), output=result_data)
```

### Technical Validation

**Confirmed Working:**
1. ✅ SDK `query()` can invoke slash commands directly (confirmed in research docs)
2. ✅ SDK supports `cwd` parameter for worktree context
3. ✅ SDK streams messages allowing progress monitoring
4. ✅ SDK has timeout support via `asyncio.timeout()`
5. ✅ Research doc `Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md` confirms this design

**Evidence from research docs:**
```python
# From docs/research/guardkit-agent/Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md:61-71
async for message in query(
    prompt=f"/task-work {task_id}",
    options=options
):
    if message.type == "assistant":
        print(extract_text(message))
    elif message.type == "result":
        print(f"Task completed: {message.result}")
```

### Gap Identified: task_work_results.json

**Issue**: The task-work slash command doesn't create `task_work_results.json`. This file is expected by Coach validator but doesn't exist.

**Solution Options:**

1. **Parse SDK stream** (Lower effort): Parse messages from SDK stream to extract quality gate results, then create `task_work_results.json` from parsed data

2. **Modify task-work command** (Higher effort): Add Phase 5.6 to task-work that writes results to JSON

**Recommended**: Option 1 (parse SDK stream) - No changes to task-work command required

### Implementation Steps for Option B

1. **Modify `_invoke_task_work_implement`** (agent_invoker.py):
   - Replace subprocess with `query()` call
   - Add message stream parsing
   - Create `task_work_results.json` from parsed output

2. **Add stream parser** (new method):
   - Extract test results from output
   - Extract coverage metrics
   - Extract quality gate pass/fail status
   - Handle Phase 4.5 fix loop output

3. **Write results file** (new method):
   - Create structured JSON from parsed data
   - Write to `.guardkit/autobuild/{task_id}/task_work_results.json`

4. **Ensure worktree has commands**:
   - Worktree inherits from main branch
   - `.claude/commands/task-work.md` should be present
   - Verify during worktree creation

### Effort Estimate

| Component | Effort |
|-----------|--------|
| Replace subprocess with SDK query | 2 hours |
| Implement stream parser | 4 hours |
| Create task_work_results.json writer | 2 hours |
| Testing and debugging | 4 hours |
| **Total** | ~1.5 days |

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Stream parsing fails | Low | Fallback to git-based detection |
| Timeout handling | Low | SDK has native timeout support |
| Command not found in worktree | Low | Verify at worktree creation |
| Nested context issues | Medium | Single SDK session, not nested |

**Overall Risk: Low-Medium** - The SDK approach is well-documented and has been validated in research phase.

### Comparison: Option B vs Original Options

| Factor | Direct SDK (C) | CLI Command (A) | SDK Delegation (B) |
|--------|----------------|-----------------|-------------------|
| Quality gates | ❌ None | ✅ Full | ✅ Full |
| Implementation effort | Low | High | Medium |
| Future-proof | ❌ Dead end | ❌ Replaced soon | ✅ SDK patterns transfer |
| Error handling | ❌ Fallbacks | ✅ Proper | ✅ Proper |
| Time to working | Immediate | 3-5 days | 1-2 days |

### Recommendation Update

**Option B is viable and recommended** given user context:

1. Provides full quality gates (unlike direct SDK)
2. Lower investment than CLI command
3. SDK patterns will transfer to LangChain/DeepAgents migration
4. Can be implemented in 1-2 days

## Appendix

### Evidence Files Analyzed

1. `docs/reviews/feature-build/complete_failure.md` - Latest failure output showing delegation being triggered but task-work results not found
2. `docs/reviews/feature-build/feature_build_output_following_fixes.md` - Pre-TASK-FB-DEL1 output showing direct SDK path
3. `guardkit/orchestrator/agent_invoker.py` - Delegation implementation (subprocess call to non-existent command)
4. `guardkit/cli/main.py` - CLI command registration (task-work missing)
5. `tasks/completed/TASK-FB-DEL1/TASK-FB-DEL1.md` - Delegation enablement task
6. `tasks/completed/TASK-REV-fb02-task-work-results-not-found.md` - Previous analysis

### Key Log Analysis

**complete_failure.md Line 114**:
```
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via task-work delegation for TASK-INFRA-001 (turn 1)
```
Shows delegation IS being triggered.

**feature_build_output_following_fixes.md Lines 99, 142**:
```
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via direct SDK for TASK-INFRA-001
```
Shows pre-TASK-FB-DEL1 used direct SDK path.

### Architecture Gap Visualization

```
DESIGNED ARCHITECTURE:
┌─────────────────────┐       ┌──────────────────────┐
│  AutoBuild          │       │  guardkit task-work  │
│  Orchestrator       │ ───►  │  CLI Command         │ ◄── NOT IMPLEMENTED
│                     │       │  (Python subprocess) │
└─────────────────────┘       └──────────────────────┘
                                       │
                                       ▼
                              ┌──────────────────────┐
                              │  task_work_results   │
                              │  .json               │
                              └──────────────────────┘

ACTUAL STATE:
┌─────────────────────┐       ┌──────────────────────┐
│  AutoBuild          │       │  guardkit task-work  │
│  Orchestrator       │ ───►  │  (COMMAND NOT FOUND) │
│                     │       │                      │
└─────────────────────┘       └──────────────────────┘
                                       │
                                       ▼
                              ┌──────────────────────┐
                              │  FileNotFoundError   │
                              │  or Exit Code ≠ 0    │
                              └──────────────────────┘
```

### Success Criteria Verification

- [x] Root cause identified with evidence
- [x] Determine if issue is code bug vs deployment gap → **Implementation gap**
- [x] Clear action plan (fix code OR redeploy and retest) → **Option D: Hybrid**
- [x] Verification strategy to confirm fix works → **Revert to direct SDK, verify feature-build succeeds**
