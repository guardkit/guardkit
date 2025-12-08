---
id: TASK-FIX-P7B9
title: "Update template-create.md to document phase-specific bridge protocol files"
status: in_review
created: 2025-12-08T17:30:00Z
updated: 2025-12-08T21:45:00Z
priority: high
tags: [documentation, bridge-protocol, template-create, phase-specific]
task_type: implementation
complexity: 4
related_tasks: [TASK-FIX-7B74, TASK-FIX-D8F2, TASK-REV-B7K3]
test_results:
  status: passed
  coverage: null
  last_run: 2025-12-08T21:45:00Z
  verification:
    phase_specific_patterns: 16
    generic_patterns_remaining: 0
    task_tool_references: 9
---

# Task: Update template-create.md to document phase-specific bridge protocol files

## Problem Statement

The `/template-create` command specification (`installer/global/commands/template-create.md`) is **outdated** and does not match the current Python implementation. This mismatch causes Claude to potentially mishandle the bridge protocol for Phase 5 agent invocations.

### Root Cause

TASK-FIX-7B74 introduced **separate phase-specific invokers** to fix a cache collision issue:

```python
# Phase 1 invoker for codebase analysis
self.phase1_invoker = AgentBridgeInvoker(
    phase=WorkflowPhase.PHASE_1,
    phase_name="ai_analysis"
)

# Phase 5 invoker for agent generation
self.phase5_invoker = AgentBridgeInvoker(
    phase=WorkflowPhase.PHASE_5,
    phase_name="agent_generation"
)
```

Each invoker writes to **phase-specific files** (from `invoker.py` lines 129-138):

```python
# Default to phase-specific files if not explicitly provided
if request_file is None:
    self.request_file = Path(f".agent-request-phase{phase}.json")
if response_file is None:
    self.response_file = Path(f".agent-response-phase{phase}.json")
```

### Current State

| Component | File Pattern | Status |
|-----------|--------------|--------|
| Python orchestrator | `.agent-request-phase1.json`, `.agent-request-phase5.json` | ✅ Correct |
| Python invoker | `.agent-response-phase1.json`, `.agent-response-phase5.json` | ✅ Correct |
| Command spec | `.agent-request.json` (generic) | ❌ **Outdated** |

### Evidence

From the `/template-create` command output (TASK-REV-B7K3):
- Line 36: `📝 Request written to: .agent-request-phase1.json`
- Line 893: `📝 Request written to: .agent-request-phase5.json`

The Python code IS using phase-specific files, but the command specification still references generic file names.

## Acceptance Criteria

1. **Update file references** in template-create.md to use phase-specific patterns
2. **Document both Phase 1 and Phase 5** agent invocation flows
3. **Update cleanup commands** to remove phase-specific files
4. **Add explicit Task tool requirement** for agent invocations
5. **Add test verification** that documentation matches implementation

## Implementation Details

### File to Modify

`installer/global/commands/template-create.md`

### Section 1: Update "Step 2: Handle Exit Code 42" (Lines ~1184-1248)

**Current (Incorrect)**:
```markdown
**2a. Read the agent request file:**

```bash
cat .agent-request.json
```

The file has this structure:
```json
{
  "request_id": "uuid-string",
  "version": "1.0",
  "phase": 6,
  "phase_name": "agent_generation",
  ...
}
```
```

**Updated (Correct)**:
```markdown
**2a. Read the agent request file:**

The request file is **phase-specific**. Check which phase file exists:

```bash
# Phase 1 (AI Codebase Analysis)
cat .agent-request-phase1.json

# Phase 5 (Agent Recommendation)
cat .agent-request-phase5.json
```

The file has this structure:
```json
{
  "request_id": "uuid-string",
  "version": "1.0",
  "phase": 1,  // or 5
  "phase_name": "ai_analysis",  // or "agent_generation"
  "agent_name": "architectural-reviewer",
  "prompt": "Full prompt text for the agent...",
  "timeout_seconds": 120,
  "created_at": "ISO-8601-timestamp",
  "context": {},
  "model": null
}
```

**NOTE**: The `phase` field indicates which phase requested the agent:
- `phase: 1` = AI Codebase Analysis (Phase 1)
- `phase: 5` = Agent Recommendation (Phase 5)
```

### Section 2: Update "2b. Invoke the agent using Task tool" (Lines ~1210-1219)

**Current**:
```markdown
**2b. Invoke the agent using Task tool:**

Use the Task tool to invoke the agent specified in `agent_name` with the `prompt` from the request file.

Example:
```
Task: Invoke the "architectural-reviewer" agent with the prompt from .agent-request.json
```
```

**Updated**:
```markdown
**2b. Invoke the agent using Task tool:**

**CRITICAL**: You MUST use the Task tool to invoke the agent. Do NOT write the response directly.

Use the Task tool to invoke the agent specified in `agent_name` with the `prompt` from the request file:

```
Task tool invocation:
  subagent_type: The agent_name from the request (e.g., "architectural-reviewer")
  prompt: The full prompt text from the request file
  description: "Analyze codebase architecture" (or similar based on phase)
```

**Why Task tool is required**:
1. Ensures consistent agent behavior across invocations
2. Provides proper model selection for the agent
3. Maintains separation between orchestration and analysis
4. Enables proper timeout handling and error recovery

**DO NOT** write the response file directly based on your own analysis. The bridge protocol requires actual agent subprocess invocation.
```

### Section 3: Update "2c. Write the agent response file" (Lines ~1221-1240)

**Current**:
```markdown
**2c. Write the agent response file:**

Create `.agent-response.json` with this exact structure:
```

**Updated**:
```markdown
**2c. Write the agent response file:**

Create the **phase-specific** response file matching the request phase:

- If request was `.agent-request-phase1.json` → write `.agent-response-phase1.json`
- If request was `.agent-request-phase5.json` → write `.agent-response-phase5.json`

Use this exact structure:
```json
{
  "request_id": "<copy from request>",
  "version": "1.0",
  "status": "success",
  "response": "<agent's complete response text as a string>",
  "error_message": null,
  "error_type": null,
  "created_at": "<current ISO-8601 timestamp>",
  "duration_seconds": <time taken in seconds>,
  "metadata": {
    "agent_name": "<copy from request>",
    "model": "claude-sonnet-4"
  }
}
```

**CRITICAL**: The `response` field MUST be a string, not an object. If the agent returns JSON, serialize it to a string.
```

### Section 4: Update "2d. Delete the request file" (Lines ~1244-1248)

**Current**:
```markdown
**2d. Delete the request file:**

```bash
rm .agent-request.json
```
```

**Updated**:
```markdown
**2d. Delete the request file:**

Delete the phase-specific request file that was processed:

```bash
# If processing Phase 1 request:
rm .agent-request-phase1.json

# If processing Phase 5 request:
rm .agent-request-phase5.json
```
```

### Section 5: Update "Step 3: Handle Success" cleanup (Lines ~1258-1266)

**Current**:
```markdown
2. Clean up any remaining bridge files:
   ```bash
   rm -f .agent-request.json .agent-response.json .template-create-state.json
   ```
```

**Updated**:
```markdown
2. Clean up any remaining bridge files:
   ```bash
   rm -f .agent-request-phase*.json .agent-response-phase*.json .template-create-state.json
   ```
```

### Section 6: Add Phase-Specific Workflow Summary (New section after line ~1170)

Add new section:

```markdown
### Phase-Specific Agent Invocations

The `/template-create` command may require **two separate agent invocations**:

| Phase | Request File | Response File | Purpose |
|-------|--------------|---------------|---------|
| Phase 1 | `.agent-request-phase1.json` | `.agent-response-phase1.json` | AI Codebase Analysis |
| Phase 5 | `.agent-request-phase5.json` | `.agent-response-phase5.json` | Agent Recommendation |

**Workflow**:
```
Run 1: Orchestrator → Exit 42 (Phase 1 request)
       Claude → Invoke agent via Task tool
       Claude → Write phase1 response
       Claude → Resume orchestrator

Run 2: Orchestrator → Exit 42 (Phase 5 request)
       Claude → Invoke agent via Task tool
       Claude → Write phase5 response
       Claude → Resume orchestrator

Run 3: Orchestrator → Exit 0 (Success)
       Claude → Display results, cleanup
```

**IMPORTANT**: Each phase has its own request/response file pair. Do NOT confuse Phase 1 responses with Phase 5 requests.
```

## Verification

After implementation, verify:

1. **File pattern match**: Grep for `.agent-request-phase` in template-create.md
2. **No generic references**: Ensure no `.agent-request.json` (without phase) remains
3. **Task tool emphasis**: Verify "Task tool" is explicitly required for agent invocation
4. **Cleanup commands**: Verify wildcard pattern `.agent-request-phase*.json` is used

### Test Command

```bash
# Verify phase-specific patterns documented
grep -c "agent-request-phase" installer/global/commands/template-create.md
# Expected: >= 6 occurrences

# Verify no generic patterns remain
grep -c '\.agent-request\.json' installer/global/commands/template-create.md
# Expected: 0 occurrences (or only in "before" examples)
```

## Context

### Why This Matters

When Claude sees exit code 42, it needs to know:
1. Which file to read (phase-specific)
2. That it MUST use Task tool (not write directly)
3. Which file to write (matching phase)

Without this documentation, Claude may:
- Look for the wrong file
- Write responses directly without agent invocation
- Confuse Phase 1 and Phase 5 responses

### Related Documentation

- `installer/global/lib/agent_bridge/invoker.py` - Source of truth for file patterns
- `installer/global/commands/lib/template_create_orchestrator.py` - Uses two separate invokers
- `docs/reviews/progressive-disclosure/main-vs-progressive-disclosure-analysis.md` - Analysis document (now outdated)

## Notes

This task was identified during TASK-REV-B7K3 review. The Phase 5 agent invocation in the reviewed command output showed Claude writing the response directly instead of using the Task tool, likely due to the outdated command specification.
