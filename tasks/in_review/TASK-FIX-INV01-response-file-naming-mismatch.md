---
id: TASK-FIX-INV01
title: Fix agent bridge invoker response file naming mismatch
status: in_review
task_type: implementation
created: 2025-12-09
updated: 2025-12-09
priority: high
tags: [bug, agent-bridge, invoker, progressive-disclosure]
related_tasks: [TASK-REV-A36C, TASK-FIX-PD08]
estimated_complexity: 3
source_review: TASK-REV-A36C
previous_state: in_progress
state_transition_reason: "All quality gates passed"
architectural_review_score: 95
test_pass_rate: 100
---

# TASK-FIX-INV01: Fix Response File Naming Mismatch

## Summary

The agent bridge invoker has a file naming mismatch between request and response files during phase 8 (agent enhancement) operations:

- **Request file created**: `.agent-request-phase8.json`
- **Response file expected by orchestrator**: `.agent-response.json`
- **Response file written by agent**: `.agent-response-phase8.json`

This forces users to manually rename files to continue enhancement, breaking the automated workflow.

## Root Cause

Evidence from session logs:
```
⏺ Error: Exit code 42
   📝 Request written to: .agent-request-phase8.json
   🔄 Checkpoint: Orchestrator will resume after agent responds

⏺ Bash(python3 ~/.agentecflow/bin/agent-enhance --resume)
   ✗ Unexpected error: Cannot resume - no agent response file found
   Expected: .agent-response.json
```

The orchestrator creates phase-specific request files but the `has_response()` check looks for non-phase-specific response files.

## Acceptance Criteria

### AC1: Consistent File Naming
- [x] Request and response files use matching naming convention
- [x] Either both use phase suffix or neither uses phase suffix

### AC2: Resume Functionality
- [x] `--resume` flag works without manual file renaming
- [x] Orchestrator correctly locates response file after agent completion

### AC3: Cleanup
- [x] No orphaned request/response files after successful enhancement
- [x] Error handling cleans up files on failure

## Implementation

### Changes Made (orchestrator.py)

**Change 1: Error message (line 233)**
- Before: Hardcoded `"Expected: .agent-response.json"`
- After: Dynamic `f"Expected: {self.bridge_invoker.response_file}"`

**Change 2: Cleanup method (lines 314-326)**
- Before: Hardcoded paths without null check
- After: Uses `self.bridge_invoker.request_file` and `self.bridge_invoker.response_file` with null check

## Testing

- **17/17 tests passing** (100%)
- **3 new tests** added for TASK-FIX-INV01:
  - `test_cleanup_state_uses_phase_specific_response_file`
  - `test_cleanup_state_handles_none_bridge_invoker`
  - `test_run_with_resume_error_message_uses_phase_specific_file`

## Definition of Done

- [x] Enhancement workflow completes without manual file renaming
- [x] `--resume` flag works correctly
- [x] Unit tests added for file naming consistency
- [x] Integration test for full enhancement cycle
