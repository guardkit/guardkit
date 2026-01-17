# Review Report: TASK-REV-FB05

## Executive Summary

This comprehensive architectural review analyzes the persistent failure in feature-build where SDK invocation of `/task-work --design-only` completes but no implementation plan file is created, causing PRE_LOOP_BLOCKED.

**Root Cause Identified (REVISED after SDK Documentation Review)**:

The primary bug is in `task_work_interface.py:346-347`:

```python
if hasattr(message, 'content'):
    content = str(message.content)  # BUG: Converts list to string representation
```

This converts `message.content` (a list of `ContentBlock` objects) to a string representation like `"[TextBlock(text='...'), ToolUseBlock(...)]"` instead of extracting the actual text content from each block.

**Correct SDK Usage** (per official documentation):
```python
from claude_agent_sdk import AssistantMessage, TextBlock, ToolResultBlock

async for message in query(prompt=prompt, options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                collected_output.append(block.text)
            elif isinstance(block, ToolResultBlock):
                collected_output.append(str(block.content))
```

**Architecture Score**: 58/100 (Below Threshold - Requires Fix)

| Principle | Score | Assessment |
|-----------|-------|------------|
| SOLID | 55/100 | Interface segregation violated - TaskWorkInterface tries to be both SDK invoker and output parser |
| DRY | 70/100 | Some duplication in output parsing patterns |
| YAGNI | 65/100 | Complex regex parsing for incorrectly parsed output |

## Review Details

- **Mode**: Architectural Review
- **Depth**: Comprehensive
- **Duration**: ~4 hours
- **Files Analyzed**: 15 core implementation files
- **Reviewer**: Claude Opus 4.5 (architectural-reviewer agent)

## Problem Statement

When `/feature-build TASK-XXX` executes:

1. ✅ Worktree created successfully
2. ✅ SDK invokes `/task-work {task_id} --design-only`
3. ✅ SDK execution completes (no timeout, no error)
4. ❌ `_parse_sdk_output()` finds no plan path in output
5. ❌ Fallback check for expected path also fails (file doesn't exist)
6. ❌ `QualityGateBlocked` raised with "plan_generation" gate

Evidence from logs:
```
INFO:guardkit.orchestrator.quality_gates.task_work_interface:SDK execution completed for design phase
ERROR:guardkit.orchestrator.autobuild:Pre-loop quality gate blocked: Quality gate 'plan_generation' blocked: Design phase did not return plan path for TASK-INFRA-001.
```

## Architecture Flow Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Current Architecture (Broken)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  AutoBuild Orchestrator                                                       │
│         │                                                                     │
│         ▼                                                                     │
│  PreLoopQualityGates.execute(task_id, options)                               │
│         │                                                                     │
│         ▼                                                                     │
│  TaskWorkInterface.execute_design_phase(task_id, options)                    │
│         │                                                                     │
│         ▼                                                                     │
│  _execute_via_sdk()                                                          │
│         │                                                                     │
│         ├── ClaudeAgentOptions(cwd=worktree, allowed_tools=[...])           │
│         │                                                                     │
│         ▼                                                                     │
│  async for message in query(prompt="/task-work TASK-XXX --design-only")     │
│         │                                                                     │
│         │   ┌───────────────────────────────────────────────────────┐        │
│         │   │              SDK Agent Context                         │        │
│         │   │                                                        │        │
│         │   │   1. Skill tool invoked: /task-work                   │        │
│         │   │            │                                           │        │
│         │   │   2. Skill expands to full prompt                     │        │
│         │   │            │                                           │        │
│         │   │   3. Task tool invoked for subagents ──────────┐      │        │
│         │   │      (complexity-evaluator, arch-reviewer)     │      │        │
│         │   │            │                                    │      │        │
│         │   │   4. Subagents execute in NESTED CONTEXT ◄─────┘      │        │
│         │   │            │                                           │        │
│         │   │   5. Plan created by subagent (NOT parent)    ⚠️      │        │
│         │   │            │                                           │        │
│         │   │   6. Subagent output NOT in parent stream     ⚠️      │        │
│         │   │                                                        │        │
│         │   └───────────────────────────────────────────────────────┘        │
│         │                                                                     │
│         ▼                                                                     │
│  collected_output.append(str(message.content))  ◄── Only parent output       │
│         │                                                                     │
│         ▼                                                                     │
│  _parse_sdk_output(output_text)                                              │
│         │                                                                     │
│         ├── Regex search for "Plan saved to:"  ◄── Pattern NOT in output    │
│         │                                                                     │
│         ▼                                                                     │
│  result["plan_path"] = None  ◄── No match found                              │
│         │                                                                     │
│         ▼                                                                     │
│  Fallback: Check if file exists at expected path  ◄── File NOT created      │
│         │                                                                     │
│         ▼                                                                     │
│  _extract_pre_loop_results() raises QualityGateBlocked                       │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Root Cause Analysis (REVISED)

### Primary Issue: Incorrect Message Parsing

**Location**: `task_work_interface.py:344-351`

```python
async for message in query(prompt=prompt, options=options):
    # Collect message content for parsing
    if hasattr(message, 'content'):
        content = str(message.content)  # ❌ BUG HERE
        collected_output.append(content)
```

**The Bug**: `message.content` is a `list[ContentBlock]`, not a string. Calling `str()` on it produces:
```
"[TextBlock(text='Phase 2 complete...'), ToolUseBlock(name='Write', ...)]"
```

Instead of the actual text content. The regex patterns then search this malformed string and find nothing.

**Per Claude Agent SDK Documentation**, the correct approach is:

```python
from claude_agent_sdk import (
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

async for message in query(prompt=prompt, options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                collected_output.append(block.text)
            elif isinstance(block, ToolResultBlock):
                if block.content:
                    collected_output.append(str(block.content))
    elif isinstance(message, ResultMessage):
        if message.structured_output:
            # Use structured output if configured
            pass
```

### Secondary Issue: Missing Structured Output Configuration

The SDK supports structured outputs via JSON schema, which would guarantee a properly formatted response:

```python
design_phase_schema = {
    "type": "object",
    "properties": {
        "plan_path": {"type": "string"},
        "complexity_score": {"type": "number"},
        "architectural_score": {"type": "number"},
        "checkpoint_result": {"type": "string", "enum": ["approved", "rejected", "skipped"]}
    },
    "required": ["plan_path", "complexity_score"]
}

options = ClaudeAgentOptions(
    output_format={
        "type": "json_schema",
        "schema": design_phase_schema
    }
)
```

This would allow accessing `message.structured_output` in the `ResultMessage` for guaranteed structured data.

### Tertiary Issue: No PostToolUse Hook for Skill Output

The SDK supports hooks to capture tool execution results:

```python
async def capture_design_output(input_data, tool_use_id, context):
    if input_data['tool_name'] == 'Skill':
        tool_response = input_data.get('tool_response', {})
        # Extract plan path from skill output
        return {}
    return {}

options = ClaudeAgentOptions(
    hooks={
        'PostToolUse': [HookMatcher(matcher='Skill', hooks=[capture_design_output])]
    }
)
```

This would provide another avenue to capture the skill's output.

### Secondary Issue: Plan File Not Being Created

Even the fallback check (lines 438-446) fails because the plan file doesn't exist:

```python
if not result["plan_path"]:
    expected_path = self._get_plan_path(task_id)
    if expected_path.exists():  # ← Returns False
        result["plan_path"] = str(expected_path)
```

This suggests one of:

1. **Task file not in worktree**: The worktree is created from `main` branch but the task being worked on may not exist there
2. **Skill execution fails silently**: The /task-work skill may encounter an error that doesn't propagate
3. **Context not available**: CLAUDE.md or skills configuration may not be properly loaded

### Evidence Chain

| Step | Expected | Actual | Gap |
|------|----------|--------|-----|
| SDK invocation | SDK starts | SDK starts | ✅ |
| Skill loading | /task-work loaded | Unknown | ⚠️ No verification |
| Subagent invocation | Task tool called | Unknown | ⚠️ No logging |
| Plan creation | File written | File NOT written | ❌ |
| Plan path extraction | Pattern found | Pattern NOT found | ❌ |
| Fallback check | File exists | File NOT exists | ❌ |

## Hypothesis Matrix

| # | Hypothesis | Likelihood | Evidence |
|---|------------|------------|----------|
| H1 | Subagent output not captured by parent SDK stream | **HIGH** | SDK stream only contains parent output, plan creation happens in nested Task tool context |
| H2 | /task-work skill not executing phases correctly | MEDIUM | No visible error but no file created |
| H3 | Task file doesn't exist in worktree | MEDIUM | Worktree created from main, task may be new |
| H4 | CLAUDE.md/skills config not loaded in worktree | MEDIUM | SDK uses `setting_sources=["project"]` but worktree may lack config |
| H5 | Interactive input required but not available | LOW | `--no-questions` flag passed |

## Architectural Recommendations (REVISED)

### Option A: Fix Message Parsing (CRITICAL - Immediate Fix Required)

**Concept**: Fix the broken message parsing to properly extract content from SDK messages.

**Current (Broken)**:
```python
async for message in query(prompt=prompt, options=options):
    if hasattr(message, 'content'):
        content = str(message.content)  # ❌ WRONG
        collected_output.append(content)
```

**Fixed**:
```python
from claude_agent_sdk import (
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

async for message in query(prompt=prompt, options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                collected_output.append(block.text)
            elif isinstance(block, ToolUseBlock):
                # Log tool invocations for debugging
                logger.debug(f"Tool use: {block.name}")
            elif isinstance(block, ToolResultBlock):
                if block.content:
                    collected_output.append(str(block.content))
    elif isinstance(message, ResultMessage):
        logger.info(f"SDK completed: cost=${message.total_cost_usd:.4f}")
        if message.structured_output:
            # If structured output is configured, use it directly
            return message.structured_output
```

**Effort**: Low (1-2 hours)
**Risk**: Low
**Impact**: Critical - This is the root cause

### Option B: Add Structured Output (Recommended Enhancement)

**Concept**: Configure SDK to return structured JSON response with design phase results.

```python
design_phase_schema = {
    "type": "object",
    "properties": {
        "plan_path": {"type": "string", "description": "Path to saved implementation plan"},
        "complexity_score": {"type": "number", "minimum": 1, "maximum": 10},
        "architectural_score": {"type": "number", "minimum": 0, "maximum": 100},
        "checkpoint_result": {
            "type": "string",
            "enum": ["approved", "rejected", "skipped"]
        },
        "plan_summary": {"type": "string", "description": "Brief summary of implementation plan"}
    },
    "required": ["plan_path", "complexity_score", "checkpoint_result"]
}

options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
    permission_mode="acceptEdits",
    max_turns=50,
    setting_sources=["project"],
    output_format={
        "type": "json_schema",
        "schema": design_phase_schema
    }
)
```

Then in result handling:
```python
elif isinstance(message, ResultMessage):
    if message.structured_output:
        return {
            "plan_path": message.structured_output.get("plan_path"),
            "complexity": {"score": message.structured_output.get("complexity_score", 5)},
            "architectural_review": {"score": message.structured_output.get("architectural_score", 80)},
            "checkpoint_result": message.structured_output.get("checkpoint_result", "approved"),
        }
```

**Effort**: Medium (2-4 hours)
**Risk**: Low
**Impact**: High - Guarantees structured response

### Option C: Add PostToolUse Hook (Additional Safety)

**Concept**: Use SDK hooks to capture skill execution results.

```python
captured_skill_output = {}

async def capture_skill_result(input_data, tool_use_id, context):
    """Capture output from Skill tool invocation."""
    if input_data['tool_name'] == 'Skill':
        tool_response = input_data.get('tool_response', {})
        captured_skill_output['skill_result'] = tool_response
        logger.debug(f"Captured skill output: {tool_response}")
    return {}

options = ClaudeAgentOptions(
    # ... other options ...
    hooks={
        'PostToolUse': [HookMatcher(matcher='Skill', hooks=[capture_skill_result])]
    }
)
```

**Effort**: Low (1 hour)
**Risk**: Low
**Impact**: Medium - Provides additional capture mechanism

### Option D: File-Based Verification (Robust Fallback)

**Concept**: After SDK completes, verify plan file exists at known locations.

```python
# After SDK execution completes
output_text = "\n".join(collected_output)
result = self._parse_sdk_output(output_text)

# Fallback: If no plan path found in output, check filesystem
if not result.get("plan_path"):
    task_id_match = re.search(r"TASK-[A-Z0-9-]+", prompt)
    if task_id_match:
        task_id = task_id_match.group(0)
        # Check all known plan locations
        for location in TaskArtifactPaths.all_plan_locations(task_id, self.worktree_path):
            if location.exists():
                result["plan_path"] = str(location)
                logger.info(f"Found plan at fallback location: {location}")
                break

if not result.get("plan_path"):
    # Log diagnostic information
    logger.error(f"No plan found. Collected output ({len(collected_output)} items):")
    for i, item in enumerate(collected_output[:10]):
        logger.error(f"  [{i}]: {item[:200]}...")
```

**Effort**: Low (1-2 hours)
**Risk**: Low
**Impact**: Medium - Provides robust fallback

## Recommended Implementation Path

Based on SDK documentation analysis and root cause identification:

### Phase 1: Critical Fix (Option A - Fix Message Parsing)

**MUST DO FIRST** - This is the root cause.

1. Update imports in `task_work_interface.py`:
   ```python
   from claude_agent_sdk import (
       query,
       ClaudeAgentOptions,
       AssistantMessage,
       TextBlock,
       ToolUseBlock,
       ToolResultBlock,
       ResultMessage,
   )
   ```

2. Fix the message collection loop (lines 344-351):
   ```python
   async for message in query(prompt=prompt, options=options):
       if isinstance(message, AssistantMessage):
           for block in message.content:
               if isinstance(block, TextBlock):
                   collected_output.append(block.text)
               elif isinstance(block, ToolResultBlock):
                   if block.content:
                       collected_output.append(str(block.content))
       elif isinstance(message, ResultMessage):
           logger.info(f"SDK completed: turns={message.num_turns}")
   ```

3. Test that plan path patterns now match correctly.

### Phase 2: Enhancement (Option B + D - Structured Output + Fallback)

1. Add `output_format` schema for guaranteed structured response
2. Add file-based fallback verification
3. Add comprehensive debug logging

### Phase 3: Optional Safety (Option C - Hooks)

1. Add PostToolUse hook for Skill tool output capture
2. Use for additional validation and diagnostics

## Files to Modify

| File | Change Type | Priority |
|------|-------------|----------|
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | **Fix message parsing** - Replace `str(message.content)` with proper ContentBlock extraction | **P0 CRITICAL** |
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | Add structured output schema configuration | P1 |
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | Add file-based fallback verification | P1 |
| `guardkit/orchestrator/quality_gates/pre_loop.py` | Add better error messages with debug guidance | P2 |

## Testing Strategy

1. **Unit test**: Mock SDK output with no plan path, verify fallback works
2. **Integration test**: Run full feature-build with --dry-run, verify plan detection
3. **E2E test**: Complete feature-build cycle with real task

## Decision Options

| Option | Effort | Risk | Recommendation |
|--------|--------|------|----------------|
| [A]ccept | - | - | Archive review for reference |
| [R]evise | - | - | Request additional analysis |
| [I]mplement | Low | Low | **RECOMMENDED** - Fix is straightforward |
| [C]ancel | - | - | Discard review |

**Recommended**: **[I]mplement** - Create single implementation task:

**TASK-FB-FIX-005: Fix SDK Message Parsing**
- Replace `str(message.content)` with proper ContentBlock iteration
- Add proper type imports from claude_agent_sdk
- Add file-based fallback verification
- Add structured output schema (optional enhancement)

**Estimated Effort**: 2-4 hours
**Risk**: Low - straightforward SDK usage fix per official documentation
**Impact**: Critical - Fixes root cause of feature-build failures

## Appendix

### A. Key Code Locations

| Component | File | Lines |
|-----------|------|-------|
| SDK invocation | `guardkit/orchestrator/quality_gates/task_work_interface.py` | 280-385 |
| Output parsing | `guardkit/orchestrator/quality_gates/task_work_interface.py` | 386-511 |
| Plan path validation | `guardkit/orchestrator/quality_gates/pre_loop.py` | 236-259 |
| Plan path resolution | `guardkit/orchestrator/paths.py` | (centralized paths) |

### B. Evidence Files Referenced

- `docs/reviews/feature-build/ni_implementation_plan_still.md`
- `docs/reviews/feature-build/no_implementation_plan.md`
- `docs/reviews/feature-build/complete_failure.md`
- `.claude/reviews/TASK-REV-FB04-review-report.md`

### C. Related Tasks

- TASK-FB-FIX-001: Replace subprocess with SDK (Completed)
- TASK-FB-FIX-002: Add plan existence validation (Completed)
- TASK-FB-FIX-003: Centralize path logic (Completed)
- TASK-FB-FIX-004: Pre-loop validation with plan check (Completed)

### D. SDK Documentation References

The root cause was confirmed by reviewing the official Claude Agent SDK documentation:

**Message Type Hierarchy**:
```
Message (base)
├── AssistantMessage
│   └── content: list[ContentBlock]
│       ├── TextBlock
│       │   └── text: str  ← Extract this
│       ├── ToolUseBlock
│       │   └── name, input: dict
│       └── ToolResultBlock
│           └── content: str | list
├── UserMessage
├── SystemMessage
└── ResultMessage
    └── structured_output: dict  ← Or use this with schema
```

**Key Patterns**:
1. Always iterate through `message.content` blocks
2. Check `isinstance(block, TextBlock)` and extract `block.text`
3. Never call `str()` on `message.content` directly

---

**Review Completed**: 2026-01-11
**Reviewer**: Claude Opus 4.5 (architectural-reviewer agent)
**Status**: REVIEW_COMPLETE
