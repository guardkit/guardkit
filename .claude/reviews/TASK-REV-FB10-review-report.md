# TASK-REV-FB10: Implementation Phase Failure - Root Cause Analysis

**Review ID**: TASK-REV-FB10
**Date**: 2026-01-12
**Mode**: Architectural Review
**Depth**: Comprehensive

## Executive Summary

**Root Cause Identified**: The implementation phase fails because `_invoke_task_work_implement()` in `agent_invoker.py` uses incorrect SDK message content extraction. Unlike `task_work_interface.py` (design phase) which was fixed in TASK-FB-FIX-005 to properly iterate ContentBlocks, the implementation phase code at line 1667-1668 still uses `str(message.content)` which converts a list of ContentBlocks to a string representation like `[TextBlock(...), ToolUseBlock(...)]` instead of extracting actual text content.

**Impact**: Zero files created, zero tests written across all implementation turns because:
1. SDK stream output is incorrectly collected as string representation of list
2. `TaskWorkStreamParser` receives malformed text that matches no patterns
3. `task_work_results.json` is written with empty/default values
4. Coach validates against empty results, always failing

## Technical Analysis

### Evidence Chain

#### 1. Comparing Design vs Implementation SDK Handling

**Design Phase (FIXED - `task_work_interface.py:351-368`):**
```python
async for message in query(prompt=prompt, options=options):
    # TASK-FB-FIX-005: Properly iterate ContentBlocks instead of str()
    # message.content is a list[ContentBlock], not a string
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                collected_output.append(block.text)  # ✓ Correct
            elif isinstance(block, ToolUseBlock):
                logger.debug(f"Tool invoked: {block.name}")
            elif isinstance(block, ToolResultBlock):
                if block.content:
                    collected_output.append(str(block.content))
```

**Implementation Phase (BROKEN - `agent_invoker.py:1664-1668`):**
```python
async for message in query(prompt=prompt, options=options):
    # Collect message content for parsing
    # Stream processing will be enhanced by TASK-SDK-002
    if hasattr(message, 'content'):
        collected_output.append(str(message.content))  # ✗ BUG!
```

#### 2. Message Content Structure

The SDK returns `AssistantMessage` with `content: list[ContentBlock]`:
```python
# What str(message.content) produces:
"[TextBlock(type='text', text='Phase 3: Implementation...'), ToolUseBlock(...)]"

# What we need (extracting block.text):
"Phase 3: Implementation..."
```

#### 3. Stream Parser Pattern Matching Failure

`TaskWorkStreamParser` patterns at `agent_invoker.py:103-113`:
```python
PHASE_MARKER_PATTERN = re.compile(r"Phase\s+(\d+(?:\.\d+)?)[:\s]+(.+)")
TESTS_PASSED_PATTERN = re.compile(r"(\d+)\s+tests?\s+passed", re.IGNORECASE)
FILES_CREATED_PATTERN = re.compile(r"(?:Created|Added):\s*([^\s,]+)")
```

These patterns **cannot match** the string representation `"[TextBlock(...)]"`.

#### 4. Result Data Flow

```
SDK Output: AssistantMessage(content=[TextBlock(text="Created: src/foo.py"), ...])
     |
     v (str(message.content) - BUG)
collected_output = ["[TextBlock(...), ToolUseBlock(...)]", ...]
     |
     v (parser.parse_message())
parsed_result = {}  # Nothing matches!
     |
     v (_write_task_work_results())
task_work_results.json = {
    "files_created": [],
    "files_modified": [],
    "tests_passed": null,
    "quality_gates_passed": null
}
     |
     v (_create_player_report_from_task_work())
Player report = {
    "files_created": [],
    "files_modified": [],
    "tests_written": [],
    "tests_passed": false  # Defaults to false
}
```

### Hypothesis Validation

| Hypothesis | Status | Evidence |
|------------|--------|----------|
| H1: SDK returns "success" but agent didn't execute | **REJECTED** | SDK does execute - design phase works (19-24 turns) |
| H2: task_work_results.json contains wrong data | **CONFIRMED** | Written with empty defaults due to parsing failure |
| H3: Skill command not executing | **REJECTED** | Logs show "task-work completed successfully" |
| H4: State mismatch between phases | **REJECTED** | State transitions are correct |
| H5: SDK working directory issue | **REJECTED** | Same cwd works for design phase |
| H6: task-work has --implement-only bug | **REJECTED** | Bug is in SDK message extraction, not skill |

**Actual Root Cause**: Message content extraction bug in `_invoke_task_work_implement()`

### Configuration Difference

The design phase SDK configuration includes `setting_sources=["user", "project"]` (TASK-FB-FIX-006), while implementation phase only has `setting_sources=["project"]`:

**Design Phase (`task_work_interface.py:344-346`):**
```python
# TASK-FB-FIX-006: Include "user" to load skills from ~/.claude/commands/
setting_sources=["user", "project"],
```

**Implementation Phase (`agent_invoker.py:1659`):**
```python
setting_sources=["project"],  # Missing "user"!
```

This may prevent `/task-work` skill from loading in implementation phase.

## Recommended Fix

### TASK-FB-FIX-013: Fix SDK Message Content Extraction in Implementation Phase

**File**: `guardkit/orchestrator/agent_invoker.py`
**Method**: `_invoke_task_work_implement()` (lines 1662-1668)

**Current Code:**
```python
collected_output = []
async with asyncio.timeout(self.sdk_timeout_seconds):
    async for message in query(prompt=prompt, options=options):
        # Collect message content for parsing
        # Stream processing will be enhanced by TASK-SDK-002
        if hasattr(message, 'content'):
            collected_output.append(str(message.content))  # BUG
```

**Fixed Code:**
```python
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

# ... in _invoke_task_work_implement():

collected_output: List[str] = []
async with asyncio.timeout(self.sdk_timeout_seconds):
    async for message in query(prompt=prompt, options=options):
        # TASK-FB-FIX-013: Properly iterate ContentBlocks instead of str()
        # Mirrors TASK-FB-FIX-005 pattern from task_work_interface.py
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    collected_output.append(block.text)
                    # Log progress for debugging
                    if "Phase" in block.text or "test" in block.text.lower():
                        logger.debug(f"SDK progress: {block.text[:100]}...")
                elif isinstance(block, ToolUseBlock):
                    logger.debug(f"Tool invoked: {block.name}")
                elif isinstance(block, ToolResultBlock):
                    if block.content:
                        collected_output.append(str(block.content))
        elif isinstance(message, ResultMessage):
            logger.info(f"SDK completed: turns={message.num_turns}")
```

### TASK-FB-FIX-014: Add "user" to Implementation Phase setting_sources

**File**: `guardkit/orchestrator/agent_invoker.py`
**Method**: `_invoke_task_work_implement()` (line 1659)

**Current Code:**
```python
setting_sources=["project"],  # Load CLAUDE.md from worktree
```

**Fixed Code:**
```python
# TASK-FB-FIX-014: Include "user" to load skills from ~/.claude/commands/
# Without "user", the SDK can't find /task-work skill
setting_sources=["user", "project"],
```

## Test Strategy

### Unit Tests

1. **Test ContentBlock extraction**:
```python
def test_content_block_extraction():
    """Verify TextBlock.text is extracted, not str(list)."""
    from claude_agent_sdk import TextBlock, AssistantMessage

    message = AssistantMessage(content=[
        TextBlock(type="text", text="12 tests passed, 0 failed")
    ])

    # Correct extraction
    extracted = []
    for block in message.content:
        if isinstance(block, TextBlock):
            extracted.append(block.text)

    assert extracted == ["12 tests passed, 0 failed"]
    assert str(message.content) != "12 tests passed, 0 failed"  # Wrong approach
```

2. **Test parser receives correct input**:
```python
def test_stream_parser_with_proper_input():
    """Verify parser matches patterns with correct input format."""
    parser = TaskWorkStreamParser()

    # Correct format
    parser.parse_message("12 tests passed, 0 failed")
    parser.parse_message("Created: src/auth.py")

    result = parser.to_result()
    assert result["tests_passed"] == 12
    assert result["tests_failed"] == 0
    assert "src/auth.py" in result["files_created"]
```

3. **Test parser fails with string representation**:
```python
def test_stream_parser_fails_with_str_content():
    """Verify parser fails with str(list) format - demonstrates the bug."""
    parser = TaskWorkStreamParser()

    # Bug format: str(message.content)
    parser.parse_message("[TextBlock(type='text', text='12 tests passed')]")

    result = parser.to_result()
    assert result.get("tests_passed") is None  # Fails to parse
```

### Integration Tests

1. **End-to-end implementation phase test**:
```python
async def test_implementation_phase_creates_files():
    """Verify implementation phase creates files in worktree."""
    invoker = AgentInvoker(worktree_path=test_worktree)
    result = await invoker._invoke_task_work_implement(
        task_id="TASK-TEST-001",
        mode="standard"
    )

    assert result.success
    assert len(result.output.get("files_created", [])) > 0
    # Verify files actually exist
    for f in result.output["files_created"]:
        assert (test_worktree / f).exists()
```

## Architecture Observations

### Duplication Between Design and Implementation

The SDK invocation pattern is duplicated between:
- `task_work_interface.py:_execute_via_sdk()` (design phase)
- `agent_invoker.py:_invoke_task_work_implement()` (implementation phase)

**Recommendation**: Extract common SDK invocation pattern to a shared utility:
```python
# guardkit/orchestrator/sdk_utils.py
async def collect_sdk_stream(
    prompt: str,
    worktree_path: Path,
    allowed_tools: List[str],
    permission_mode: str,
    max_turns: int,
    timeout_seconds: int,
) -> Tuple[List[str], int]:
    """Execute SDK query and collect text content from stream."""
    # Proper ContentBlock iteration (TASK-FB-FIX-005 pattern)
    ...
```

### Missing Code Review for Implementation Phase

The implementation phase code (`_invoke_task_work_implement`) was added but never received the TASK-FB-FIX-005 fix that was applied to the design phase. This suggests:
1. Code review didn't catch the duplication
2. Tests don't cover both paths
3. No shared abstraction enforces consistency

## Risk Assessment

| Factor | Rating | Rationale |
|--------|--------|-----------|
| Severity | **CRITICAL** | Complete implementation failure |
| Scope | **Isolated** | Only affects `_invoke_task_work_implement()` |
| Fix Complexity | **LOW** | Copy pattern from working design phase |
| Regression Risk | **LOW** | Adding proper typing, no behavior change |
| Test Coverage | **MEDIUM** | Need new tests for ContentBlock extraction |

## Action Items

1. **TASK-FB-FIX-013** (P0): Fix ContentBlock extraction in `_invoke_task_work_implement()`
2. **TASK-FB-FIX-014** (P0): Add "user" to setting_sources in implementation phase
3. **Future**: Extract shared SDK invocation utility to prevent duplication
4. **Future**: Add integration tests for implementation phase file creation

## Files Analyzed

| File | Lines | Analysis |
|------|-------|----------|
| `guardkit/orchestrator/agent_invoker.py` | 2145 | Primary bug location (lines 1664-1668) |
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | 748 | Reference for correct pattern |
| `guardkit/orchestrator/autobuild.py` | 2262 | Orchestration context |
| `installer/core/commands/task-work.md` | ~1500 | Skill specification (not the issue) |
| `tasks/backlog/TASK-REV-FB10-implementation-phase-failure.md` | 206 | Task definition |

## Conclusion

The implementation phase failure is caused by a **message content extraction bug** in `agent_invoker.py:1667-1668`. The code uses `str(message.content)` which converts a list of ContentBlocks to a string representation, rather than properly iterating and extracting `TextBlock.text` values as done in the design phase after TASK-FB-FIX-005.

The fix is straightforward: apply the same ContentBlock iteration pattern from `task_work_interface.py` to `agent_invoker.py._invoke_task_work_implement()`, and ensure `setting_sources` includes `"user"` to enable skill loading.

---

**Review Status**: COMPLETE
**Recommended Next Action**: Create TASK-FB-FIX-013 and TASK-FB-FIX-014 with the specified changes
