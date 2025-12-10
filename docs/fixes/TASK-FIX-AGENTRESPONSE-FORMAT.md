# TASK-FIX-AGENTRESPONSE-FORMAT: Agent Response Format Mismatch

**Status**: IMPLEMENTED
**Created**: 2025-12-09
**Priority**: HIGH
**Fixed**: 2025-12-09

## Problem Summary

The `/agent-enhance` command fails with:
```
TypeError: AgentResponse.__init__() got an unexpected keyword argument 'sections'
```

This error occurs during AI enhancement (both AI and hybrid strategies), causing fallback to static enhancement.

## Root Cause Analysis

### The Error Chain

1. **Python script** (`agent-enhance.py`) calls `SingleAgentEnhancer.enhance()`
2. **Enhancer** (`enhancer.py`) uses `AgentBridgeInvoker` to request agent invocation
3. **Invoker** exits with code 42, signaling Claude Code to invoke the agent
4. **Claude Code** invokes `agent-content-enhancer` agent via Task tool
5. **Agent returns** JSON with `sections`, `related_templates`, etc.
6. **Claude Code** writes `.agent-response-phase8.json` - BUT with wrong format
7. **Python resumes**, calls `invoker.load_response()`
8. **Invoker** tries to create `AgentResponse(**response_data)` - **FAILS**

### The Format Mismatch

**What Claude is writing** (WRONG - based on error):
```json
{
  "sections": ["related_templates", "examples", "boundaries"],
  "related_templates": "...",
  "examples": "...",
  ...
}
```

**What `AgentResponse` expects** (CORRECT - per `invoker.py` line 65-88):
```json
{
  "request_id": "uuid",
  "version": "1.0",
  "status": "success",
  "response": "{\"sections\": [...], ...}",  // JSON-encoded string!
  "error_message": null,
  "error_type": null,
  "created_at": "ISO 8601 timestamp",
  "duration_seconds": 1.0,
  "metadata": {}
}
```

### Why It Works for `/template-create` but Not `/agent-enhance`

The `/template-create.md` command specification includes **explicit instructions** for Claude Code on how to write the response file (lines 1274-1284):

```markdown
**2c. Write the agent response file:**

Create the **phase-specific** response file matching the request phase:
- If request was `.agent-request-phase1.json` → write `.agent-response-phase1.json`

Use this exact structure:
{
  "request_id": "<copy from request>",
  "version": "1.0",
  "status": "success",
  "response": "<agent's complete response text as a string>",
  ...
}
```

The `/agent-enhance.md` command **does NOT include these instructions**. It only references the spec document (line 656):
```markdown
- [Agent Response Format Specification](../../docs/reference/agent-response-format.md)
```

But this reference is in a "See Also" section that Claude Code doesn't read during execution.

## Evidence

### 1. Error Location

From `invoker.py` lines 248-254:
```python
try:
    response = AgentResponse(**response_data)
except TypeError as e:
    raise ValueError(f"Invalid response format: {e}")
```

The error `got an unexpected keyword argument 'sections'` means `response_data` contains `sections` as a top-level key.

### 2. AgentResponse Definition

From `invoker.py` lines 64-88:
```python
@dataclass
class AgentResponse:
    request_id: str
    version: str
    status: str
    response: Optional[str]  # Must be string, not dict!
    error_message: Optional[str]
    error_type: Optional[str]
    created_at: str
    duration_seconds: float
    metadata: dict
```

`sections` is NOT a field in `AgentResponse`. It should be inside the `response` field as a JSON-encoded string.

### 3. Agent Content Enhancer Output

From `agent-content-enhancer.md` lines 43-52:
```json
{
  "sections": ["frontmatter", "quick_start", "boundaries", "detailed_examples"],
  "frontmatter": "---\nname: agent-name\n...",
  ...
}
```

This is the enhancement content - it needs to be wrapped in the `AgentResponse` envelope with the enhancement JSON as a string in the `response` field.

## Solution Options

### Option A: Add Bridge Protocol Instructions to agent-enhance.md (Recommended)

Add explicit instructions similar to `/template-create.md` in the `/agent-enhance.md` command specification.

**Pros**:
- Fixes the issue at the source
- Consistent with how `/template-create` works
- Claude Code will see instructions during command execution

**Cons**:
- Requires documentation update
- Need to ensure instructions are clear

### Option B: Make load_response() More Tolerant

Modify `invoker.py` to detect and handle the case where the response file contains enhancement content directly (without envelope).

**Pros**:
- Backward compatible
- Handles malformed responses gracefully

**Cons**:
- Adds complexity to invoker
- Doesn't fix the root cause
- May mask other issues

### Option C: Use Different File Format for Enhancement

Have the agent write enhancement directly and skip the bridge protocol for `/agent-enhance`.

**Pros**:
- Simpler for agent enhancement
- No envelope wrapping needed

**Cons**:
- Diverges from established pattern
- More code changes
- Loses checkpoint-resume benefits

## Recommended Fix

**Implement Option A + partial Option B**:

1. **Add bridge protocol instructions to `/agent-enhance.md`** - Primary fix
2. **Add fallback handling in `load_response()`** - Defensive programming

### Implementation Details

#### Step 1: Update `/agent-enhance.md`

Add a new section after "Command Execution (MANDATORY)" with explicit bridge protocol instructions:

```markdown
## Bridge Protocol for AI Invocation

When the Python script exits with code 42, Claude Code must:

1. Read `.agent-request-phase8.json` to get agent name and prompt
2. Invoke the agent via Task tool
3. Write the response to `.agent-response-phase8.json` with this EXACT format:

{
  "request_id": "<copy from .agent-request-phase8.json>",
  "version": "1.0",
  "status": "success",
  "response": "<JSON-encode the agent's enhancement output>",
  "error_message": null,
  "error_type": null,
  "created_at": "<ISO 8601 timestamp>",
  "duration_seconds": <seconds>,
  "metadata": {}
}

CRITICAL: The `response` field must be a JSON STRING, not an object.
Use json.dumps() on the agent's output before placing in response field.

4. Re-run the Python script with --resume flag
```

#### Step 2: Add Defensive Handling in invoker.py

Add detection for malformed response at line 250:

```python
try:
    # Check if response_data looks like raw enhancement content
    if "sections" in response_data and "request_id" not in response_data:
        # Convert raw enhancement to proper envelope
        logger.warning(
            "Response file contains raw enhancement, not AgentResponse envelope. "
            "Auto-wrapping for backward compatibility. "
            "Please update Claude Code to use proper envelope format."
        )
        response_data = {
            "request_id": "unknown",
            "version": "1.0",
            "status": "success",
            "response": json.dumps(response_data),  # Wrap as string
            "error_message": None,
            "error_type": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": 0.0,
            "metadata": {"auto_wrapped": True}
        }

    response = AgentResponse(**response_data)
except TypeError as e:
    raise ValueError(f"Invalid response format: {e}")
```

## Files Modified

1. `/installer/core/commands/agent-enhance.md` - Added "Bridge Protocol for AI Invocation" section
2. `/installer/core/lib/agent_bridge/invoker.py` - Added defensive auto-wrapping for raw enhancement content

### Changes Made

#### invoker.py (lines 227-247)

Added detection for raw enhancement content without AgentResponse envelope:

```python
# TASK-FIX-AGENTRESPONSE-FORMAT: Detect raw enhancement content without envelope
if "sections" in response_data and "request_id" not in response_data:
    logger.warning(
        "Response file contains raw enhancement content, not AgentResponse envelope. "
        "Auto-wrapping for backward compatibility."
    )
    response_data = {
        "request_id": "auto-wrapped",
        "version": "1.0",
        "status": "success",
        "response": json.dumps(response_data),  # JSON-encode the raw content
        "error_message": None,
        "error_type": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": 0.0,
        "metadata": {"auto_wrapped": True}
    }
```

#### agent-enhance.md (lines 688-801)

Added complete "Bridge Protocol for AI Invocation (Exit Code 42)" section with:
- Step-by-step instructions for Claude Code
- Request file format
- Response file format (with CRITICAL emphasis on JSON-encoded string)
- Error handling
- Cleanup instructions

## Testing Plan

1. Run `/agent-enhance kartlog/repository-pattern-specialist --hybrid`
2. Verify AI enhancement completes without falling back to static
3. Verify split output files are created correctly

## Test Results (2025-12-09)

**Test Command**:
```bash
python3 ~/.agentecflow/bin/agent-enhance kartlog/repository-pattern-specialist --hybrid --verbose
```

**Results**: ✅ SUCCESS

- AI enhancement completed without falling back to static
- Exit code 42 handled correctly (checkpoint-resume pattern)
- Response file written with proper AgentResponse envelope format
- Split output files created:
  - `repository-pattern-specialist.md` (3,122 bytes) - Core documentation
  - `repository-pattern-specialist-ext.md` (4,895 bytes) - Extended documentation
- All 5 sections enhanced (related_templates, examples, boundaries, common_patterns, integration_points)
- Boundaries section properly formatted with ALWAYS/NEVER/ASK framework

**Console Output**:
```
✓ Enhanced repository-pattern-specialist.md using hybrid strategy (AI with fallback)
  Sections added: 5
  Templates referenced: 20
  Code examples: 2988
  Split output: ✓ (core + extended files)
    Core: repository-pattern-specialist.md
    Extended: repository-pattern-specialist-ext.md
```

**Defensive Fix Validation**:
- The defensive auto-wrapping code in `invoker.py` was NOT triggered during this test
- This indicates the proper envelope format was used (as expected with the documentation fix)
- The defensive code serves as a fallback for edge cases

**Note**: Agent metadata (stack, phase, capabilities, keywords) was reported as incomplete. This is expected - the current enhancement focuses on content (boundaries, examples, templates). Metadata generation requires separate enhancement pass or manual addition.

## Related Tasks

- TASK-FIX-267C: Agent response format specification (completed)
- TASK-PHASE-8-INCREMENTAL: Incremental agent enhancement workflow

## References

- `installer/core/lib/agent_bridge/invoker.py` - AgentResponse dataclass
- `installer/core/commands/template-create.md` - Working bridge protocol example
- `docs/reference/agent-response-format.md` - Format specification
