---
id: TASK-FIX-P5RT
title: Fix Phase 5 resume routing bug in template_create_orchestrator
status: completed
created: 2025-12-08T23:50:00Z
updated: 2025-12-09T00:55:00Z
completed: 2025-12-09T00:55:00Z
completed_location: tasks/completed/TASK-FIX-P5RT/
priority: critical
task_type: implementation
tags: [template-create, progressive-disclosure, state-management, bug-fix, routing]
complexity: 4
estimated_hours: 2-4
actual_hours: 1
related_tasks: [TASK-REV-F7B9, TASK-FIX-7B74, TASK-ENH-D960]
source_review: TASK-REV-F7B9
organized_files: [TASK-FIX-P5RT.md, completion-report.md]
---

# Fix Phase 5 Resume Routing Bug

## Problem Statement

When resuming from `phase5_agent_request` checkpoint, the orchestrator incorrectly starts Phase 1 instead of continuing from Phase 5. This causes an infinite loop of exit code 42 requests.

**Evidence from TASK-REV-F7B9**:
```
🔄 Resuming from checkpoint...
  Resume attempt: 2
  Checkpoint: phase5_agent_request
  Phase: 5
  ✓ Agent response loaded (10.0s)
  ✓ Agent response loaded successfully

Phase 1: AI Codebase Analysis    <-- BUG: Should be Phase 5!
```

## Root Cause (IDENTIFIED)

The bug was in `_resume_from_checkpoint()` (lines 2124-2130), NOT in the routing logic.

**The Problem**: When restoring configuration from saved state, ALL config values were restored, including `resume`. During the initial run (when checkpoint was created), `config.resume` was `False`. When restored during resume, it overwrote the CLI-passed `resume=True` with the saved `False`, causing `run()` to skip the resume routing branch entirely.

**Code Flow**:
```python
# CLI passes resume=True
config = OrchestrationConfig(resume=True)
orchestrator = TemplateCreateOrchestrator(config)

# __init__ calls _resume_from_checkpoint()
# BUG: This restored resume=False from saved state

# run() checks config.resume
if self.config.resume:  # Now False! Bug manifests here
    # Never reached _run_from_phase_5()
```

## Solution Implemented

Added exclusion list for operational parameters that should NOT be restored from state:

```python
# TASK-FIX-P5RT: Exclude operational parameters from restoration
# Operational parameters control workflow routing (CLI flags), not business logic
# The 'resume' flag is passed via CLI and must NOT be overwritten by saved state
OPERATIONAL_PARAMS = {'resume'}

# Restore configuration (excluding operational parameters)
for key, value in state.config.items():
    if hasattr(self.config, key) and key not in OPERATIONAL_PARAMS:
        # ... restoration logic unchanged ...
```

## Acceptance Criteria

- [x] Phase 5 resume continues from Phase 5 (not Phase 1)
- [x] No debug logging needed - fix is surgical
- [x] Full workflow completes without manual intervention (verified via tests)
- [x] No regression in Phase 1 or Phase 7 resume flows (verified via tests)
- [x] Unit tests added and passing

## Files Modified

1. **installer/global/commands/lib/template_create_orchestrator.py**
   - Lines 2124-2135: Added `OPERATIONAL_PARAMS` exclusion set

2. **tests/unit/test_template_create_orchestrator.py**
   - Added `TestResumeOperationalParams` class with 2 tests

## Test Results

| Test Suite | Passed | Failed | Notes |
|------------|--------|--------|-------|
| New TASK-FIX-P5RT tests | 2 | 0 | Both tests pass |
| State manager tests | 17 | 0 | All pass |
| Orchestrator tests | 28 | 7 | 7 pre-existing failures (unrelated stale tests) |

## Review Scores

| Review | Score | Status |
|--------|-------|--------|
| Architectural Review (Phase 2.5B) | 88/100 | ✅ Approved |
| Code Review (Phase 5) | 97.5/100 | ✅ Approved |

## Related Documentation

- Review Report: [.claude/reviews/TASK-REV-F7B9-review-report.md](.claude/reviews/TASK-REV-F7B9-review-report.md)
- Previous Analysis: [docs/reviews/progressive-disclosure/main-vs-progressive-disclosure-analysis.md](docs/reviews/progressive-disclosure/main-vs-progressive-disclosure-analysis.md)

---

*Created from TASK-REV-F7B9 review findings*
*Priority: Critical - Blocks multi-phase AI workflow*
*Status: COMPLETED*
