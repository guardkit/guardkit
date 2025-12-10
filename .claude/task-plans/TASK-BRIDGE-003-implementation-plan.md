# Implementation Plan: TASK-BRIDGE-003

**Task**: Integrate Bridge with /template-create Command
**Status**: in_progress
**Priority**: high
**Estimated Duration**: 1-2 hours

---

## Overview

Modify the `/template-create` markdown command to implement a checkpoint-resume loop that handles exit code 42, invokes agents via the Task tool, and re-runs the orchestrator with the `--resume` flag.

---

## Architecture Analysis

### Current State
- `/template-create` command runs Python orchestrator once
- Exit codes 0-6 and 130 are handled
- No support for agent invocation loop
- No checkpoint-resume mechanism

### Target State
- Checkpoint-resume loop supporting up to 5 iterations
- Exit code 42 handling for agent invocations
- Agent request/response file I/O
- Task tool integration for agent invocation
- Automatic cleanup of temporary files

### Design Principles
- **Fail-Safe**: Maximum iteration limit prevents infinite loops
- **Clean State**: Temporary files cleaned up on completion/error
- **Clear Feedback**: User-friendly progress messages
- **Graceful Degradation**: Proper error handling for all scenarios

---

## Implementation Steps

### Step 1: Add Execution Section to template-create.md

**File**: `installer/core/commands/template-create.md`
**Location**: End of file (after line 898)
**Estimated Duration**: 60 minutes

**Changes**:
1. Add new "## Execution" section with complete checkpoint-resume loop
2. Implement argument parsing logic
3. Add iteration loop (max 5 iterations)
4. Handle exit code 42 (NEED_AGENT)
5. Read agent request from `.agent-request.json`
6. Invoke agent via Task tool
7. Write response to `.agent-response.json`
8. Add cleanup function for temporary files
9. Add helper function for agent invocation

**Key Components**:
- Checkpoint-resume loop with iteration counter
- Exit code handling (0, 1, 2, 3, 4, 5, 6, 42, 130)
- Agent request/response file I/O
- Task tool integration
- Cleanup on completion/error
- Timeout handling (600s for orchestrator, configurable for agents)

**Exit Codes**:
- 0: Success
- 1: User cancelled
- 2: Codebase not found
- 3: AI analysis failed
- 4: Component generation failed
- 5: Validation failed
- 6: Save failed
- 42: Need agent invocation
- 130: Interrupted (Ctrl+C)

---

## Files to Modify

### 1. `installer/core/commands/template-create.md`

**Type**: Markdown command specification
**Changes**: Add "Execution" section at end of file
**Lines**: ~400 new lines
**Risk**: Low (additive change, no existing content modified)

---

## Testing Strategy

### Test Scenarios

Since this is a markdown command specification, testing will be manual:

1. **Normal Execution** (no agent needed)
   - Command: `/template-create --path test_simple_codebase --dry-run`
   - Expected: Exit code 0, no agent files created

2. **Single Agent Invocation**
   - Command: `/template-create --path test_complex_codebase`
   - Expected: Exit code 42 → agent invoked → exit code 0

3. **Multiple Agent Invocations**
   - Simulate orchestrator needing 2-3 agents
   - Expected: Loop continues until exit code 0

4. **Error Handling**
   - Test missing codebase
   - Test cancelled Q&A
   - Test invalid agent request file
   - Test agent timeout
   - Test agent invocation error

5. **Cleanup Verification**
   - Verify `.agent-request.json` deleted on success
   - Verify `.agent-response.json` deleted on success
   - Verify `.template-create-state.json` deleted on success
   - Verify temp files deleted on error

6. **Maximum Iterations**
   - Simulate infinite loop scenario
   - Expected: Stop at 5 iterations with error message

---

## Dependencies

### Prerequisites (Completed)
- ✅ TASK-BRIDGE-001: Agent Bridge Infrastructure
- ✅ TASK-BRIDGE-002: Orchestrator Integration

### Required Files
- `installer/core/commands/lib/template_create_orchestrator.py` (must support --resume)
- `.agent-request.json` (created by orchestrator on exit 42)
- `.agent-response.json` (created by command on agent completion)

---

## Risk Assessment

### Low Risk
- Additive change (no existing content modified)
- Clear separation from existing exit code handling
- Well-defined iteration limit prevents runaway loops

### Potential Issues
1. **Infinite Loop**: Mitigated by 5-iteration limit
2. **Orphaned Temp Files**: Mitigated by cleanup function
3. **Agent Timeout**: Handled with try-catch and timeout response
4. **Malformed Request**: Handled with JSON parsing error catch

---

## Validation Criteria

### Functional Requirements
- ✅ Exit code 42 detected and handled
- ✅ Agent request file read and parsed
- ✅ Agent invoked via Task tool
- ✅ Response written to response file
- ✅ Orchestrator re-run with --resume
- ✅ Multiple invocations supported (up to 5)
- ✅ Error handling for all scenarios
- ✅ Cleanup of temporary files

### Quality Requirements
- ✅ Clear user feedback at each step
- ✅ Proper error messages
- ✅ Timeout handling
- ✅ Graceful degradation

---

## Implementation Details

### Agent Invocation Flow

```
1. Orchestrator runs → Exit 42
2. Command reads .agent-request.json
3. Command invokes agent via Task tool
4. Agent returns response
5. Command writes .agent-response.json
6. Command deletes .agent-request.json
7. Command re-runs orchestrator with --resume
8. Orchestrator reads .agent-response.json
9. Orchestrator continues or exits with 0/error
```

### Agent Mapping

Map agent names to subagent types for Task tool:
- `architectural-reviewer` → `architectural-reviewer`
- `software-architect` → `software-architect`
- Add more mappings as needed (extensible)

### Timeout Strategy

- **Orchestrator**: 600 seconds (10 minutes)
- **Agents**: Configurable in request (default: 120 seconds)
- **Timeout Response**: Status "timeout", error_type "TimeoutError"

---

## Success Criteria

### Definition of Done
1. Execution section added to template-create.md
2. Checkpoint-resume loop implemented
3. All exit codes handled correctly
4. Agent invocation via Task tool works
5. Manual test scenarios documented
6. Error handling complete and tested
7. Cleanup function works correctly

### Quality Gates
- No syntax errors in markdown/code blocks
- Clear documentation of all parameters
- Comprehensive error handling
- User-friendly progress messages

---

## Timeline

- **Phase 2 (Planning)**: 15 minutes ✅
- **Phase 2.5 (Review)**: 10 minutes (next)
- **Phase 3 (Implementation)**: 45 minutes
- **Phase 4 (Testing)**: 30 minutes (manual)
- **Phase 5 (Review)**: 10 minutes
- **Phase 5.5 (Audit)**: 5 minutes

**Total**: ~2 hours

---

## Notes

- This is a markdown command specification, not executable code
- The code blocks in the markdown represent pseudocode/logic for Claude to execute
- Actual testing requires running the command via Claude Code
- The Task tool integration is the key integration point for agent invocation
