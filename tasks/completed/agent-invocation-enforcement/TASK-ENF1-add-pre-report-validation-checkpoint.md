---
id: TASK-ENF1
title: Add pre-report validation checkpoint to task-work
status: completed
created: 2025-11-27T12:50:00Z
updated: 2025-11-27T21:30:00Z
completed_at: 2025-11-27T21:30:00Z
priority: critical
tags: [enforcement, validation, quality-gates, task-work, agent-invocation]
task_type: implementation
epic: null
feature: agent-invocation-enforcement
requirements: []
dependencies: [TASK-ENF-P0-1, TASK-ENF2]
blocks: []
complexity: 5
effort_estimate: 5-7 hours
actual_effort: 4 hours
related_to: TASK-8D3F, TASK-REV-9A4E
completion_metrics:
  total_duration: 4 hours
  implementation_time: 3 hours
  testing_time: 1 hour
  files_created: 4
  files_modified: 2
  tests_written: 31
  test_pass_rate: 100%
  lines_added: 1350
final_test_results:
  status: passed
  total_tests: 31
  passed: 31
  failed: 0
  skipped: 0
  execution_time: 0.06s
---

# Task: Add Pre-Report Validation Checkpoint to task-work

## ⚠️ CRITICAL DEPENDENCY (Added 2025-11-27)

**BLOCKED BY**: TASK-ENF-P0-1 (Fix agent discovery to scan `.claude/agents/`)

**Why Blocked**: TASK-REV-9A4E architectural review identified that agent discovery does NOT scan `.claude/agents/` where template-init copies local agents. Without this fix, validation will fail to recognize template agents, generating false positives and blocking valid tasks.

**Action Required**:
1. ✅ Complete TASK-ENF-P0-1 (Fix agent discovery) - 2-3 hours
2. ✅ Validate local agent discovery works
3. ✅ Then implement this task with local agent support

**Review Report**: `.claude/reviews/TASK-REV-9A4E-review-report.md`

**Updated Scope**: This task now includes local agent validation support (effort: 4-6h → 5-7h)

---

## Context

**From TASK-8D3F Review**: The `/task-work` command currently allows completion reports to be generated even when required agents were not invoked. This results in false reporting where agents are listed as "used" when they were never called via the Task tool.

**From TASK-REV-9A4E Review**: Validation must support local agents (`.claude/agents/`) created by template initialization. Without this, template workflows will be blocked incorrectly.

**Issue**: No validation exists before final report generation to verify that all required agent invocations actually occurred, and validation doesn't account for template-generated local agents.

**Priority**: CRITICAL - This is the most immediate issue preventing false reporting, but MUST NOT be implemented until Phase 0 fixes complete.

## Objective

Add a mandatory validation checkpoint before the "Step 11: Display Completion Summary" section in `task-work.md` that:
1. Counts actual Task tool invocations from the conversation/execution log
2. Compares against expected invocations based on workflow mode
3. Blocks report generation if invocations are missing
4. Displays clear error showing which phases were skipped

## Requirements

### R1: Validation Function

**Requirement**: Create validation function that verifies all required agents were invoked

**Implementation**:
```python
def validate_agent_invocations(tracker: AgentInvocationTracker, workflow_mode: str):
    """
    Validate that all required agents were invoked before generating final report.

    Args:
        tracker: Agent invocation tracker with recorded invocations
        workflow_mode: 'standard' | 'micro' | 'design-only' | 'implement-only'

    Raises:
        ValidationError: If invocations don't match expected phases

    Returns:
        bool: True if validation passes
    """
    expected = get_expected_phases(workflow_mode)  # Standard: 5, Micro: 3, etc.
    actual = len([inv for inv in tracker.invocations if inv["status"] == "completed"])

    if actual < expected:
        missing_phases = identify_missing_phases(tracker, expected)
        raise ValidationError(
            f"❌ PROTOCOL VIOLATION: Agent invocation incomplete\n\n"
            f"Expected: {expected} agent invocations\n"
            f"Actual: {actual} completed invocations\n\n"
            f"Missing phases:\n" + "\n".join(f"  - Phase {p}" for p in missing_phases) +
            f"\n\nCannot generate completion report until all agents are invoked.\n"
            f"Review the AGENT INVOCATIONS LOG above to see which phases were skipped."
        )

    return True
```

**Acceptance Criteria**:
- [ ] Function counts completed agent invocations from tracker
- [ ] Function compares against expected count based on workflow mode
- [ ] Function raises ValidationError with detailed message if count < expected
- [ ] Function identifies which specific phases are missing
- [ ] Function returns True if all validations pass

### R2: Workflow Mode Phase Counts

**Requirement**: Define expected phase counts for each workflow mode

**Implementation**:
```python
def get_expected_phases(workflow_mode: str) -> int:
    """
    Get expected number of agent invocations based on workflow mode.

    Standard: 5 phases (Planning, Arch Review, Implementation, Testing, Code Review)
    Micro: 3 phases (Planning, Implementation, Quick Review)
    Design-only: 3 phases (Planning, Arch Review, Complexity)
    Implement-only: 3 phases (Implementation, Testing, Code Review)
    """
    phase_counts = {
        "standard": 5,
        "micro": 3,
        "design-only": 3,
        "implement-only": 3
    }
    return phase_counts.get(workflow_mode, 5)
```

**Acceptance Criteria**:
- [ ] Function returns correct count for 'standard' workflow (5)
- [ ] Function returns correct count for 'micro' workflow (3)
- [ ] Function returns correct count for 'design-only' workflow (3)
- [ ] Function returns correct count for 'implement-only' workflow (3)
- [ ] Function defaults to 5 if workflow_mode not recognized

### R3: Integration with task-work.md

**Requirement**: Add validation call before final report generation

**Location**: `installer/global/commands/task-work.md` before "Step 11: Display Completion Summary"

**Implementation**:
```markdown
### Step 10.5: Validate Agent Invocations (NEW - Prevent False Reporting)

**CRITICAL**: Verify all required agents were invoked before generating completion report.

**VALIDATE**:
```python
try:
    validate_agent_invocations(tracker, workflow_mode)
    print("✅ Validation Passed: All required agents invoked\n")
except ValidationError as e:
    print(str(e))
    print("\nTASK MOVED TO BLOCKED STATE")
    print("Reason: Protocol violation - required agents not invoked")
    move_task_to_blocked(task_id, reason="Agent invocation protocol violation")
    exit(1)
```

**IF validation passes**: Proceed to Step 11 (Completion Summary)
**IF validation fails**:
- Display error with missing phases
- Move task to BLOCKED state
- Exit without generating completion report
```

**Acceptance Criteria**:
- [ ] Validation runs before Step 11 (completion summary)
- [ ] Success case displays "✅ Validation Passed" and proceeds
- [ ] Failure case displays detailed error with missing phases
- [ ] Failure case moves task to BLOCKED state
- [ ] Failure case exits without generating completion report

### R4: Error Message Display

**Requirement**: Provide clear, actionable error message when validation fails

**Expected Output** (Failure Case):
```
═══════════════════════════════════════════════════════
❌ PROTOCOL VIOLATION: Agent invocation incomplete
═══════════════════════════════════════════════════════

Expected: 5 agent invocations
Actual: 3 completed invocations

Missing phases:
  - Phase 3 (Implementation)
  - Phase 4 (Testing)

Cannot generate completion report until all agents are invoked.
Review the AGENT INVOCATIONS LOG above to see which phases were skipped.

AGENT INVOCATIONS LOG:
✅ Phase 2: python-api-specialist (Planning)
✅ Phase 2.5B: architectural-reviewer (Review - 95/100)
❌ Phase 3: SKIPPED (no invocation detected)
❌ Phase 4: SKIPPED (no invocation detected)
✅ Phase 5: code-reviewer (Review - 95/100)

TASK MOVED TO BLOCKED STATE
Reason: Protocol violation - required agents not invoked
═══════════════════════════════════════════════════════
```

**Acceptance Criteria**:
- [ ] Error clearly states "Protocol violation"
- [ ] Error shows expected vs actual invocation counts
- [ ] Error lists specific missing phases with phase numbers and names
- [ ] Error references the AGENT INVOCATIONS LOG for details
- [ ] Error explains task is moved to BLOCKED state

## Implementation Plan

### Phase 1: Create Validation Functions

**Files**:
- `installer/global/commands/lib/agent_invocation_validator.py` (new file)

**Implementation**:
1. Create `validate_agent_invocations()` function
2. Create `get_expected_phases()` function
3. Create `identify_missing_phases()` helper function
4. Add unit tests for all validation logic

### Phase 2: Integrate with task-work.md

**Files**:
- `installer/global/commands/task-work.md` (modify)

**Implementation**:
1. Add Step 10.5 "Validate Agent Invocations" section
2. Add validation call with try/except error handling
3. Add clear documentation of success/failure behavior
4. Update step numbering (Step 11 becomes final step)

### Phase 3: Add Error Handling

**Files**:
- `installer/global/commands/lib/task_state_manager.py` (modify)

**Implementation**:
1. Add `move_task_to_blocked()` function if not exists
2. Update function to accept `reason` parameter
3. Write reason to task frontmatter (`blocked_reason` field)
4. Update task status to 'blocked'

### Phase 4: Testing

**Test Cases**:
1. **Standard workflow with all agents invoked** → Validation passes, report generated
2. **Standard workflow with missing Phase 3** → Validation fails, error displayed, task BLOCKED
3. **Standard workflow with missing Phase 4** → Validation fails, error displayed, task BLOCKED
4. **Micro workflow with 3 agents invoked** → Validation passes (correct for micro mode)
5. **Design-only workflow with 3 agents invoked** → Validation passes

**Acceptance Criteria**:
- [ ] All test cases pass
- [ ] Error messages are clear and actionable
- [ ] Task state transitions are correct (BLOCKED when validation fails)

## Success Criteria

### SC1: Validation Enforced

- [ ] Validation runs before every completion report
- [ ] Validation correctly counts agent invocations
- [ ] Validation uses correct expected count for workflow mode

### SC2: False Reporting Prevented

- [ ] Task cannot complete if agents were not invoked
- [ ] Completion report cannot list agents that weren't used
- [ ] Task moved to BLOCKED state when validation fails

### SC3: Clear Error Messages

- [ ] Error clearly identifies which phases were skipped
- [ ] Error provides actionable guidance (invoke missing agents)
- [ ] Error references agent invocation log for details

### SC4: No Breaking Changes

- [ ] Existing tasks with proper agent usage unaffected
- [ ] Validation integrates seamlessly with current workflow
- [ ] Error handling doesn't break task-work execution

## Estimated Effort

**Total**: 4-6 hours

**Breakdown**:
- Phase 1 (Validation Functions): 2 hours
- Phase 2 (Integration): 1 hour
- Phase 3 (Error Handling): 1 hour
- Phase 4 (Testing): 1-2 hours

## Related Tasks

- TASK-8D3F - Review task that identified this gap
- TASK-ENF2 - Add agent invocation tracking & logging (prerequisite for this task)
- TASK-5F8A - Review and improve subagent invocation enforcement

## Notes

**Dependencies**: This task requires TASK-ENF2 (Agent Invocation Tracking) to be implemented first, as it relies on the `AgentInvocationTracker` to record invocations.

**Implementation Order**: Complete TASK-ENF2 before starting this task.

**Testing**: Use MyDrive TASK-ROE-007g scenario as test case (should fail validation since Phases 3 and 4 were skipped).
