---
task_id: TASK-FIX-4B2E
title: Fix task creation workflow integration for --create-agent-tasks flag
status: BACKLOG
priority: HIGH
complexity: 6
created: 2025-11-20T21:20:00Z
updated: 2025-11-20T21:20:00Z
assignee: null
tags: [bug, phase-8, production-blocker, task-creation]
related_tasks: [TASK-PHASE-8-INCREMENTAL, TASK-AI-2B37, TASK-TEST-87F4]
estimated_duration: 1 day
technologies: [python, task-management]
review_source: docs/reviews/phase-8-implementation-review.md
---

# Fix Task Creation Workflow Integration

## Problem Statement

The `--create-agent-tasks` flag in `/template-create` is documented but NOT implemented. When users run template creation with this flag, no task files are created in `tasks/backlog/`, breaking the documented incremental enhancement workflow.

**Review Finding** (Section 1, Critical Finding):
> **What Should Have Happened**: 3 task files created in `tasks/backlog/`
> **What Actually Happened**: No task files were created
> **Root Cause**: Flag is documented but not implemented in orchestrator

## Current State

**Location**: `installer/global/commands/lib/template_create_orchestrator.py`

The orchestrator has task creation logic (lines 963-1013) but it's NOT integrated with the main workflow:

```python
def _create_agent_enhancement_task(self, agent_name: str, ...):
    """Creates individual task for agent enhancement."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    task_id = f"TASK-AGENT-{agent_name[:8].upper()}-{timestamp}"
    # ... task creation logic exists but never called
```

**Integration Point Missing**: No code calls this method when `--create-agent-tasks` is passed.

## Acceptance Criteria

### 1. Flag Integration
- [ ] `--create-agent-tasks` flag actually creates tasks in workflow
- [ ] Tasks created in `tasks/backlog/` directory
- [ ] One task per agent file in template
- [ ] Task creation happens after Phase 7 (validation complete)

### 2. Task File Format
- [ ] Task ID format: `TASK-{agent-name[:12]}-{uuid[:8]}`
- [ ] Includes agent_file path in metadata
- [ ] Includes template_dir path in metadata
- [ ] Includes template_name in metadata
- [ ] Priority set to MEDIUM by default
- [ ] Status set to BACKLOG

### 3. Error Handling
- [ ] File write errors handled gracefully (don't crash workflow)
- [ ] Permission errors logged and reported
- [ ] Directory creation errors handled
- [ ] Duplicate task IDs prevented (see TASK-FIX-9E1A)

### 4. User Experience
- [ ] Print summary: "Created N enhancement tasks in tasks/backlog/"
- [ ] List task IDs created
- [ ] Provide next steps: "/task-work TASK-XXX to enhance agent"
- [ ] Works with --dry-run (shows what would be created)

### 5. Documentation
- [ ] Command spec matches implementation
- [ ] Example usage in template-create.md
- [ ] Integration with /agent-enhance documented

## Technical Details

### Files to Modify

**1. `installer/global/commands/lib/template_create_orchestrator.py`**
- Add call to `_create_agent_enhancement_task` in Phase 8 logic
- Ensure Phase 8 only runs when `--create-agent-tasks` is True
- Handle errors without blocking template creation

**2. `installer/global/commands/template-create.md`**
- Verify documentation matches implementation
- Add examples of task creation output

### Implementation Steps

1. **Integrate Task Creation Phase**
   ```python
   def run(self):
       # ... existing phases ...

       if self.create_agent_tasks:
           self._phase8_create_agent_tasks()

   def _phase8_create_agent_tasks(self):
       """Phase 8: Create enhancement tasks for agents."""
       logger.info("Phase 8: Creating agent enhancement tasks...")

       agent_files = self._discover_agent_files()
       task_ids = []

       for agent_file in agent_files:
           try:
               task_id = self._create_agent_enhancement_task(
                   agent_name=agent_file.stem,
                   agent_file=agent_file,
                   template_dir=self.template_dir,
                   template_name=self.template_name
               )
               task_ids.append(task_id)
           except (PermissionError, OSError) as e:
               logger.error(f"Failed to create task for {agent_file.name}: {e}")
               continue  # Non-fatal, continue with other agents

       self._print_task_summary(task_ids)
   ```

2. **Add Error Handling** (see TASK-FIX-7C3D)
   - Try/except around file writes
   - Log errors with context
   - Continue with other tasks on failure

3. **Fix Task ID Generation** (see TASK-FIX-9E1A)
   - Use UUID instead of timestamp
   - Ensure uniqueness

4. **Test Integration**
   - Unit test: Phase 8 creates correct task files
   - Integration test: End-to-end with real template
   - Error test: Permission denied, disk full, etc.

## Success Metrics

### Functional Tests
- [ ] Running with `--create-agent-tasks` creates task files
- [ ] Task files have correct format and metadata
- [ ] Works with 1 agent (simple case)
- [ ] Works with 10+ agents (batch case)
- [ ] --dry-run shows what would be created without creating

### Error Scenarios
- [ ] Permission denied on tasks/backlog/ (logged, continues)
- [ ] Disk full (graceful failure)
- [ ] Invalid agent file (skipped with warning)

### Performance
- [ ] Task creation adds <500ms to workflow
- [ ] No memory leaks with 50+ agents

## Dependencies

**Blocked By**:
- TASK-FIX-9E1A (task ID uniqueness) - should fix before integration
- TASK-FIX-7C3D (file I/O error handling) - needed for robust implementation

**Blocks**:
- User adoption of incremental enhancement workflow
- Documentation accuracy (TASK-DOC-F3A3)

## Related Review Findings

**From**: `docs/reviews/phase-8-implementation-review.md`

- **Section 1**: Critical Finding: Task Creation Failure
- **Section 3.1**: Integration with template_create_utils.py (missing)
- **Section 4.1**: Automatic Task Creation (not implemented)
- **Section 6.1**: Priority 1 production blocker

## Estimated Effort

**Duration**: 1 day (6-8 hours)

**Breakdown**:
- Integration (2-3 hours): Connect Phase 8 to orchestrator
- Error handling (2 hours): Robust file I/O
- Testing (2 hours): Unit + integration tests
- Documentation (1 hour): Update command spec

## Notes

- This is a **production blocker** per review section "Critical Finding"
- Must be completed before Phase 8 can be considered production-ready
- Consider creating subtasks if this becomes complex
- May need to coordinate with TASK-FIX-9E1A and TASK-FIX-7C3D for optimal solution

## Alternative Approaches

### Option A: Full Implementation (Recommended)
Complete the integration as designed.

### Option B: Remove Flag from Docs
Mark as "COMING SOON" until implemented.
- **Pros**: Honest about current state
- **Cons**: Workflow unavailable to users

### Decision
Implement Option A - the design is sound, just needs integration.
