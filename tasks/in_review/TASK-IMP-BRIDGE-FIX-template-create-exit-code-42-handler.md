---
id: TASK-IMP-BRIDGE-FIX
title: "Fix: Add Exit Code 42 Bridge Handler to /template-create Command"
status: in_review
created: 2025-12-03T08:30:00Z
updated: 2025-12-03T08:30:00Z
priority: critical
task_type: implementation
tags: [template-create, bridge-protocol, exit-code-42, pre-release-blocker, minimal-fix]
related_tasks: [TASK-REV-AGENT-GEN, TASK-IMP-TMPL-FIX, TASK-REV-TMPL-CMD]
parent_review: TASK-REV-AGENT-GEN
---

# Implementation Task: Add Exit Code 42 Bridge Handler to /template-create

## CRITICAL: MINIMAL SCOPE FIX

**This is a pre-release blocker requiring a MINIMAL, TARGETED fix.**

- **ONLY MODIFY ONE FILE**: `installer/global/commands/template-create.md`
- **NO PYTHON CHANGES**: The Python checkpoint-resume infrastructure is working correctly
- **NO NEW FEATURES**: Only add the missing bridge handler instructions
- **NO REFACTORING**: Keep existing structure intact

### Related Tasks
- **TASK-REV-AGENT-GEN**: Root cause analysis (this task implements the recommended fix)
- **TASK-IMP-TMPL-FIX**: Previous fix that removed orchestrator bypass (commit 773f534)
- **TASK-REV-TMPL-CMD**: Original review that identified pseudocode issue

---

## Problem Statement

The `/template-create` command generates only 3 agents at ~68% confidence instead of 7-8 agents at 90%+ confidence because the **exit code 42 bridge pattern is not handled**.

### Root Cause

The Python orchestrator correctly implements checkpoint-resume:
1. Writes `.agent-request.json` with agent invocation details
2. Exits with code 42 to signal "NEED_AGENT"
3. Expects Claude to invoke the agent and write `.agent-response.json`
4. Expects Claude to re-run with `--resume` flag

**BUT** the command file (`template-create.md`) only says:
```bash
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```

Without any instructions to:
- Detect exit code 42
- Read `.agent-request.json`
- Invoke the architectural-reviewer agent
- Write `.agent-response.json`
- Re-run with `--resume`

When Python exits with code 42, Claude sees it exit and falls back to manual behavior (heuristic-based generation).

---

## Fix Specification

### File to Modify

**Path**: `installer/global/commands/template-create.md`

**Location**: Replace lines 1117-1127 (the `## Command Execution` section)

### Current Content (Lines 1117-1127)

```markdown
---

## Command Execution

```bash
# Execute via symlinked Python script
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```

**Note**: This command uses the orchestrator pattern with the entry point in `lib/template_create_orchestrator.py`. The symlink is created as `template-create-orchestrator` (underscores converted to hyphens for consistency).
```

### Replacement Content

Replace lines 1117-1127 with the following **exact content**:

```markdown
---

## Command Execution

Execute this command using a checkpoint-resume loop that handles Python-Claude agent bridge communication.

### Execution Loop

When the user invokes `/template-create`, execute this loop:

```
LOOP (max 5 iterations to prevent infinite loops):
  1. Run Python orchestrator
  2. Capture exit code
  3. IF exit code == 0: SUCCESS - display results and exit loop
  4. IF exit code == 42: AGENT NEEDED - handle bridge protocol (see below)
  5. IF exit code == other: ERROR - display error and exit loop
  6. After handling exit code 42, add --resume flag and continue loop
```

### Step 1: Run Python Orchestrator

```bash
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```

Capture the exit code from this command.

### Step 2: Handle Exit Code 42 (NEED_AGENT)

When exit code is 42, Python has written a request file and needs Claude to invoke an agent.

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
  "agent_name": "architectural-reviewer",
  "prompt": "Full prompt text for the agent...",
  "timeout_seconds": 120,
  "created_at": "ISO-8601-timestamp",
  "context": {},
  "model": null
}
```

**2b. Invoke the agent using Task tool:**

Use the Task tool to invoke the agent specified in `agent_name` with the `prompt` from the request file.

Example:
```
Task: Invoke the "architectural-reviewer" agent with the prompt from .agent-request.json
```

Capture the agent's complete response text.

**2c. Write the agent response file:**

Create `.agent-response.json` with this exact structure:

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

**2d. Delete the request file:**

```bash
rm .agent-request.json
```

**2e. Re-run orchestrator with --resume flag:**

Add `--resume` to the original arguments and continue the loop:

```bash
python3 ~/.agentecflow/bin/template-create-orchestrator "$@" --resume
```

### Step 3: Handle Success (Exit Code 0)

When exit code is 0:
1. Display the success message from Python's output
2. Clean up any remaining bridge files:
   ```bash
   rm -f .agent-request.json .agent-response.json .template-create-state.json
   ```
3. Exit the loop

### Step 4: Handle Errors (Other Exit Codes)

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| 0 | SUCCESS | Display results, cleanup, exit |
| 1 | USER_CANCELLED | Display cancellation message |
| 2 | CODEBASE_NOT_FOUND | Display error with path |
| 3 | ANALYSIS_FAILED | Display error, suggest --verbose |
| 4 | GENERATION_FAILED | Display error |
| 5 | VALIDATION_FAILED | Display validation errors |
| 6 | SAVE_FAILED | Display file I/O error |
| 42 | NEED_AGENT | Handle bridge protocol (loop) |
| 130 | INTERRUPTED | Display interruption message |

### Error Handling for Bridge Protocol

**If `.agent-request.json` does not exist when exit code is 42:**
```
ERROR: Exit code 42 received but no .agent-request.json found.
This indicates a bug in the orchestrator. Please report this issue.
```

**If agent invocation fails:**
Write an error response to `.agent-response.json`:
```json
{
  "request_id": "<from request>",
  "version": "1.0",
  "status": "error",
  "response": null,
  "error_message": "<error description>",
  "error_type": "AgentInvocationError",
  "created_at": "<timestamp>",
  "duration_seconds": 0,
  "metadata": {}
}
```
Then continue with `--resume` to let Python handle the fallback.

**If JSON parsing fails:**
Display error and suggest re-running without --resume:
```
ERROR: Failed to parse bridge protocol files.
Try: rm -f .agent-request.json .agent-response.json .template-create-state.json
Then re-run: /template-create [original args]
```

### Example Execution Flow

```
User: /template-create --path /my/project

[Iteration 1]
  Run: python3 ~/.agentecflow/bin/template-create-orchestrator --path /my/project
  Exit code: 42

  Read: .agent-request.json
  Agent: architectural-reviewer
  Invoke agent with prompt...
  Write: .agent-response.json
  Delete: .agent-request.json

[Iteration 2]
  Run: python3 ~/.agentecflow/bin/template-create-orchestrator --path /my/project --resume
  Exit code: 0

  SUCCESS: Template created at ~/.agentecflow/templates/my-project/
  Cleanup bridge files
  Exit loop
```

**Note**: This command uses the orchestrator pattern with checkpoint-resume. The Python orchestrator handles state persistence in `.template-create-state.json`, and the bridge protocol enables AI-powered agent generation that produces 7-8 agents at 90%+ confidence (vs 3 agents at 68% with heuristic fallback).
```

---

## JSON Schemas (Reference - DO NOT MODIFY)

### AgentRequest Schema

From `installer/global/lib/agent_bridge/invoker.py` lines 37-62:

```python
@dataclass
class AgentRequest:
    request_id: str       # UUID v4 string
    version: str          # "1.0"
    phase: int            # Current phase number (1-8)
    phase_name: str       # Human-readable phase name
    agent_name: str       # Agent to invoke (e.g., "architectural-reviewer")
    prompt: str           # Complete prompt text
    timeout_seconds: int  # Maximum wait time (default: 120)
    created_at: str       # ISO 8601 timestamp
    context: dict         # Additional debugging context
    model: Optional[str]  # Optional model ID
```

### AgentResponse Schema

From `installer/global/lib/agent_bridge/invoker.py` lines 65-88:

```python
@dataclass
class AgentResponse:
    request_id: str          # Must match request
    version: str             # "1.0"
    status: str              # "success" | "error" | "timeout"
    response: Optional[str]  # Agent response text (MUST be string)
    error_message: Optional[str]  # Error description if status != "success"
    error_type: Optional[str]     # Error type identifier
    created_at: str          # ISO 8601 timestamp
    duration_seconds: float  # Time taken for agent invocation
    metadata: dict           # Additional metadata
```

**CRITICAL**: The `response` field MUST be a string, not an object. The Python code at lines 219-239 in `invoker.py` handles type conversion if needed.

---

## Acceptance Criteria

### Must Pass

1. [ ] **Single File Change**: Only `installer/global/commands/template-create.md` is modified
2. [ ] **Lines 1117-1127 Replaced**: The `## Command Execution` section contains bridge handler instructions
3. [ ] **Exit Code 42 Documented**: Instructions for handling NEED_AGENT signal present
4. [ ] **Request/Response Formats**: JSON schemas documented correctly
5. [ ] **Loop Structure**: Max 5 iterations documented to prevent infinite loops
6. [ ] **Error Handling**: All error cases documented

### Functional Tests

7. [ ] **Agent Invocation**: When exit code 42 fires, Claude reads `.agent-request.json` and invokes agent
8. [ ] **Response Written**: Claude writes `.agent-response.json` with correct schema
9. [ ] **Resume Works**: Python `--resume` flag processes the response correctly
10. [ ] **Agent Count**: 7-8 agents generated (not 3)
11. [ ] **Confidence Score**: 90%+ confidence (not 68%)
12. [ ] **Clean Exit**: Exit code 0 with successful template creation

### Non-Regression Tests

13. [ ] **Dry Run Works**: `/template-create --dry-run` completes without error
14. [ ] **No Agents Works**: `/template-create --no-agents` skips exit code 42 flow
15. [ ] **Validate Works**: `/template-create --validate` produces quality report
16. [ ] **Interrupt Works**: Ctrl+C during execution cleans up state files

---

## Files (Read-Only Reference)

These files should be READ for understanding but NOT MODIFIED:

| File | Purpose | Key Lines |
|------|---------|-----------|
| `installer/global/lib/agent_bridge/invoker.py` | Bridge invoker | 37-88 (schemas), 135-196 (invoke), 197-270 (load_response) |
| `installer/global/lib/agent_bridge/state_manager.py` | State persistence | 16-37 (state schema), 72-122 (save/load) |
| `installer/global/commands/lib/template_create_orchestrator.py` | Main orchestrator | 174-177 (invoker init), 779-828 (phase 5), 1743-1836 (checkpoint) |
| `installer/global/lib/codebase_analyzer/ai_analyzer.py` | AI analysis | 87 (bridge passed), 173-214 (fallback) |
| `installer/global/lib/codebase_analyzer/agent_invoker.py` | Agent invocation | 95-131 (invoke) |

---

## Implementation Steps

### Step 1: Read Current File

```bash
# Verify current state
head -n 1130 installer/global/commands/template-create.md | tail -n 15
```

Expected output (lines 1117-1127):
```markdown
---

## Command Execution

```bash
# Execute via symlinked Python script
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```

**Note**: This command uses the orchestrator pattern...
```

### Step 2: Apply the Fix

Replace lines 1117-1127 with the replacement content specified above.

### Step 3: Verify the Fix

```bash
# Verify line count increased
wc -l installer/global/commands/template-create.md
# Expected: ~1213 lines (was 1127)

# Verify bridge instructions present
grep -c "exit code.*42\|NEED_AGENT\|\.agent-request\.json" installer/global/commands/template-create.md
# Expected: >= 5

# Verify loop structure documented
grep "LOOP (max 5 iterations" installer/global/commands/template-create.md
# Expected: 1 match
```

### Step 4: Test the Fix

```bash
# Test with a small codebase
/template-create --path /path/to/test/codebase --dry-run

# Watch for:
# - Exit code 42 message: "⏸️  Requesting agent invocation"
# - Bridge handler activation
# - Agent invocation via Task tool
# - Resume with --resume flag
# - 7-8 agents generated
# - 90%+ confidence score
```

---

## Risk Mitigation

### Risk 1: Claude Misinterprets Instructions

**Probability**: Medium
**Impact**: High
**Mitigation**: Instructions are explicit with exact JSON schemas and example flow

### Risk 2: Infinite Loop

**Probability**: Low
**Impact**: High
**Mitigation**: Max 5 iterations documented; Python will eventually exit with code != 42

### Risk 3: Response Format Mismatch

**Probability**: Medium
**Impact**: Medium
**Mitigation**: JSON schemas documented; Python has type conversion at lines 219-239

### Risk 4: File Cleanup Issues

**Probability**: Low
**Impact**: Low
**Mitigation**: Cleanup commands documented for all exit paths

---

## Notes

### Why This Is Safe

1. **Python code is working**: The checkpoint-resume infrastructure is fully implemented and tested
2. **Single file change**: Only documentation changes, no code changes
3. **Explicit instructions**: Claude Code follows explicit instructions well
4. **Fallback exists**: If bridge fails, Python falls back to heuristics (current behavior)

### Why This Is Necessary

1. **Quality**: AI-powered generation produces 7-8 agents at 90%+ confidence
2. **Correctness**: Heuristic fallback produces only 3 agents at 68% confidence
3. **Design Intent**: The bridge pattern was designed for this exact use case
4. **Pre-release**: This is a blocker for template creation quality

---

## Review Status

- **Parent Review**: TASK-REV-AGENT-GEN (REVIEW_COMPLETE)
- **Root Cause**: Identified and verified
- **Fix Approach**: Approved (Option A: Add bridge logic to command file)
- **Implementation Status**: IN_REVIEW (fix applied, ready for testing)

## Implementation Summary

**File Modified**: `installer/global/commands/template-create.md`

**Changes**:
- Replaced lines 1117-1127 (minimal Command Execution section)
- Added 183 lines of bridge handler instructions
- Total file size: 1300 lines (was 1127)

**Verification**:
- Line count: 1300 ✅
- Bridge references (exit code 42, NEED_AGENT, .agent-request.json): 14 occurrences ✅
- Loop structure (max 5 iterations): 1 occurrence ✅

**Acceptance Criteria Completed**:
1. [x] Single File Change: Only `template-create.md` modified
2. [x] Lines 1117-1127 Replaced: Bridge handler instructions added
3. [x] Exit Code 42 Documented: NEED_AGENT signal handling present
4. [x] Request/Response Formats: JSON schemas documented
5. [x] Loop Structure: Max 5 iterations documented
6. [x] Error Handling: All error cases documented

**Pending Functional Tests** (require manual testing):
7. [ ] Agent Invocation: When exit code 42 fires, Claude reads `.agent-request.json`
8. [ ] Response Written: Claude writes `.agent-response.json` with correct schema
9. [ ] Resume Works: Python `--resume` flag processes the response
10. [ ] Agent Count: 7-8 agents generated (not 3)
11. [ ] Confidence Score: 90%+ confidence (not 68%)
12. [ ] Clean Exit: Exit code 0 with successful template creation
