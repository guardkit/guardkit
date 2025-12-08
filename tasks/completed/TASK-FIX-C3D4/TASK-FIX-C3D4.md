---
id: TASK-FIX-C3D4
title: Fix Phase 5 resume routing to use correct invoker
status: completed
created: 2025-12-08T21:35:00Z
updated: 2025-12-09T00:20:00Z
completed: 2025-12-09T00:20:00Z
priority: critical
task_type: implementation
tags: [template-create, checkpoint-resume, progressive-disclosure, orchestrator]
complexity: 5
estimated_hours: 4-6
actual_hours: 1.5
related_tasks: [TASK-REV-D4A8, TASK-FIX-7B74, TASK-ENH-D960]
parent_review: TASK-REV-D4A8
completed_location: tasks/completed/TASK-FIX-C3D4/
---

# Fix Phase 5 Resume Routing to Use Correct Invoker

## Overview

The multi-phase AI orchestrator incorrectly routes to `phase1_invoker` when resuming from a Phase 5 agent request. This prevents Phase 5 agent generation from ever succeeding.

## Root Cause Analysis

From TASK-REV-D4A8 review:

**Issue 3 (CRITICAL)**: Phase resume routing selects wrong invoker

The checkpoint/resume pattern has a timing issue:
1. Phase 4 saves checkpoint `templates_generated` with `phase=4`
2. Phase 5 starts and requests agent invocation (exit 42)
3. User writes `.agent-response-phase5.json`
4. On resume, `state.phase == 4` → Falls into `else` branch → Uses `phase1_invoker`
5. `phase1_invoker` looks for `.agent-response-phase1.json` (WRONG!)

## Acceptance Criteria

1. [x] Phase 5 agent request saves its own checkpoint before invoking
2. [x] Resume routing correctly identifies Phase 5 pending state
3. [x] `phase5_invoker` is selected when Phase 5 response is expected
4. [x] Add integration test for multi-phase resume scenario

## Implementation Completed

### Changes Made

**File: `installer/global/commands/lib/template_create_orchestrator.py`**

1. **Line 905-908**: Added checkpoint save at Phase 5 entry
   ```python
   # TASK-FIX-C3D4: Save checkpoint BEFORE agent invocation
   # This ensures resume routing knows we're waiting for Phase 5 response
   # When resuming, state.phase == 5 triggers the correct phase5_invoker
   self._save_checkpoint("phase5_agent_request", phase=WorkflowPhase.PHASE_5)
   ```

2. **Lines 270-272**: Added explicit Phase 5 routing in `run()` method
   ```python
   elif phase == WorkflowPhase.PHASE_5:
       # TASK-FIX-C3D4: Explicit Phase 5 routing for agent generation resume
       return self._run_from_phase_5()
   ```

**File: `tests/unit/lib/template_creation/test_resume_routing.py`**

3. **Lines 355-437**: Added 3 new test cases:
   - `test_phase5_checkpoint_routes_to_phase5_invoker`
   - `test_phase5_explicit_routing_in_run_method`
   - `test_phase4_checkpoint_falls_through_to_phase5`

## Test Results

```
tests/unit/lib/template_creation/test_resume_routing.py - 20 tests PASSED
tests/unit/lib/agent_bridge/test_multi_phase_cache.py - 17 tests PASSED
tests/unit/test_template_create_orchestrator.py::test_phase5_* - 2 tests PASSED
```

## Why This Fix Works

**Before Fix:**
1. Phase 4 saves checkpoint: `phase=4`, checkpoint="templates_generated"
2. Phase 5 starts → agent request → exit 42
3. Resume: `state.phase == 4` → routing doesn't match Phase 5 → falls to `else` using Phase 1 invoker ❌

**After Fix:**
1. Phase 4 saves checkpoint: `phase=4`, checkpoint="templates_generated"
2. Phase 5 starts → **saves checkpoint: `phase=5`** → agent request → exit 42
3. Resume: `state.phase == 5` → explicit elif matches → uses Phase 5 invoker ✅

## Sequence Diagram

```
Initial Run:
  Phase 1 → Exit 42 (agent-request-phase1.json)

Resume 1:
  Load agent-response-phase1.json ✓
  Phase 1 completes
  Phase 2-4 run
  Phase 5 → Save checkpoint: phase5_agent_request, phase=5 [NEW]
  Phase 5 → Exit 42 (agent-request-phase5.json)

Resume 2:
  Detect phase=5 → Use phase5_invoker [FIXED]
  Load agent-response-phase5.json ✓
  Phase 5 completes
  Phase 6-9 run
  SUCCESS
```

---

*Created from TASK-REV-D4A8 review findings*
*Priority: CRITICAL (blocks agent generation)*
*Effort: Estimated 4-6 hours, Actual 1.5 hours*
*Completed: 2025-12-09*
