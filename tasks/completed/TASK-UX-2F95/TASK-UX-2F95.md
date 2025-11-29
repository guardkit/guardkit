# TASK-UX-2F95: Update template-create output to recommend agent-enhance command

**Task ID**: TASK-UX-2F95
**Priority**: MEDIUM
**Status**: COMPLETED
**Created**: 2025-11-21T12:00:00Z
**Completed**: 2025-11-21T14:10:00Z
**Duration**: 45 minutes (estimated: 1 hour)
**Location**: tasks/completed/TASK-UX-2F95/
**Tags**: ux, template-create, agent-enhancement, documentation

---

## Description

Update the output instructions displayed at the end of the `/template-create` command to recommend using `/agent-enhance` instead of `/task-work` for enhancing agents.

**Current Behavior**:
When `/template-create --create-agent-tasks` completes, it displays instructions suggesting users run `/task-work TASK-AGENT-XXX` to enhance agents.

**Desired Behavior**:
Display instructions recommending `/agent-enhance template-name/agent-name` as the primary method for agent enhancement, with `/task-work TASK-AGENT-XXX` as an optional alternative for full workflow.

## Context

- `/agent-enhance` is the direct, fast method for enhancing agents (2-5 minutes)
- `/task-work` executes full task workflow with all phases (30-60 minutes)
- Most users want quick agent enhancement, not full task workflow
- The 7 created TASK-AGENT-* files are for optional batch processing
- This aligns with TASK-AI-2B37's successful AI integration

## Acceptance Criteria

### AC1: Update Output Instructions

- [x] **AC1.1**: Modify Phase 8 output in `template_create_orchestrator.py` to recommend `/agent-enhance`
- [x] **AC1.2**: Show `/agent-enhance` command syntax with template-name/agent-name format
- [x] **AC1.3**: Include `--strategy=hybrid` flag recommendation
- [x] **AC1.4**: Mention `/task-work` as optional alternative for full workflow
- [x] **AC1.5**: Update any other locations that reference agent enhancement workflow

**Primary Recommendation Format**:
```bash
# Fast Enhancement (Recommended)
/agent-enhance maui-mydrive/engine-orchestration-specialist --strategy=hybrid
/agent-enhance maui-mydrive/realm-repository-specialist --strategy=hybrid
# ... (for each agent)
```

**Alternative Workflow Format**:
```bash
# Full Task Workflow (Optional)
/task-work TASK-AGENT-ENGINE-O-20251121-081004
/task-work TASK-AGENT-REALM-RE-20251121-081004
# ... (for each task)
```

### AC2: Clear Explanation

- [x] **AC2.1**: Explain difference between `/agent-enhance` (fast) and `/task-work` (full workflow)
- [x] **AC2.2**: Show estimated duration for each approach
- [x] **AC2.3**: Clarify that both approaches produce same result
- [x] **AC2.4**: Mention that tasks are available for batch processing if desired

**Example Explanation**:
```
Agent Enhancement Options:

Option A - Fast Enhancement (Recommended): 2-5 minutes per agent
  Use /agent-enhance for direct AI-powered enhancement
  Best for: Quick iteration, testing TASK-AI-2B37, single agent work

Option B - Full Task Workflow: 30-60 minutes per agent
  Use /task-work for complete quality gates (planning, review, testing)
  Best for: Batch processing, full traceability, comprehensive documentation

Both approaches use the same AI enhancement logic (TASK-AI-2B37).
```

### AC3: Update Command Help

- [x] **AC3.1**: Update `/template-create --help` to reflect `/agent-enhance` recommendation (auto-generated from template-create.md)
- [x] **AC3.2**: Update template creation documentation
- [x] **AC3.3**: Ensure consistency across all user-facing messages

## Implementation Notes

**Files to Modify**:
1. `installer/global/commands/lib/template_create_orchestrator.py` (Phase 8 output)
2. `installer/global/commands/template-create.md` (command documentation)
3. `docs/guides/template-creation-guide.md` (if exists)

**Key Output Locations**:
- Phase 8 completion message (after task creation)
- Final summary output
- Validation report (if `--validate` flag used)

**Output Format**:
```python
# After Phase 8 task creation
print(f"\n{'='*70}")
print("AGENT ENHANCEMENT INSTRUCTIONS")
print(f"{'='*70}\n")

print(f"Created {len(agent_tasks)} agent enhancement tasks")
print(f"\nOption A - Fast Enhancement (Recommended):\n")

for agent_name in agent_names:
    print(f"  /agent-enhance {template_name}/{agent_name} --strategy=hybrid")

print(f"\nOption B - Full Task Workflow (Optional):\n")
for task_id in task_ids:
    print(f"  /task-work {task_id}")

print(f"\n{'='*70}\n")
```

## Test Plan

### Manual Testing
1. Run `/template-create --name test-template --create-agent-tasks`
2. Verify output shows `/agent-enhance` as primary recommendation
3. Verify output shows `/task-work` as optional alternative
4. Verify clear explanation of differences
5. Verify command syntax is correct (template-name/agent-name format)

### Expected Output
```
=========================================================================
AGENT ENHANCEMENT COMPLETED - 7 TASKS CREATED
=========================================================================

Agent Enhancement Options:

Option A - Fast Enhancement (Recommended): 2-5 minutes per agent
Use /agent-enhance for direct AI-powered enhancement

  /agent-enhance maui-mydrive/engine-orchestration-specialist --strategy=hybrid
  /agent-enhance maui-mydrive/entity-mapper-specialist --strategy=hybrid
  /agent-enhance maui-mydrive/erroror-pattern-specialist --strategy=hybrid
  /agent-enhance maui-mydrive/maui-mvvm-specialist --strategy=hybrid
  /agent-enhance maui-mydrive/maui-navigation-specialist --strategy=hybrid
  /agent-enhance maui-mydrive/realm-repository-specialist --strategy=hybrid
  /agent-enhance maui-mydrive/xunit-nsubstitute-specialist --strategy=hybrid

Option B - Full Task Workflow (Optional): 30-60 minutes per agent
Use /task-work for complete quality gates (planning, review, testing)

  /task-work TASK-AGENT-ENGINE-O-20251121-081004
  /task-work TASK-AGENT-ENTITY-M-20251121-081004
  /task-work TASK-AGENT-ERROROR--20251121-081004
  /task-work TASK-AGENT-MAUI-MVV-20251121-081004
  /task-work TASK-AGENT-MAUI-NAV-20251121-081004
  /task-work TASK-AGENT-REALM-RE-20251121-081004
  /task-work TASK-AGENT-XUNIT-NS-20251121-081004

Both approaches use the same AI enhancement logic (TASK-AI-2B37).

=========================================================================
```

## Related Tasks

- TASK-AI-2B37: AI integration for agent enhancement (completed)
- Phase 8: Incremental agent enhancement workflow (completed)

## Dependencies

- None (documentation/UX improvement only)

## Estimated Effort

- **Implementation**: 30 minutes
- **Testing**: 15 minutes
- **Documentation**: 15 minutes
- **Total**: ~1 hour

## Benefits

1. **Reduced Confusion**: Users immediately understand which command to use
2. **Faster Adoption**: Direct path to agent enhancement
3. **Better UX**: Clear distinction between fast and full workflows
4. **Alignment**: Matches actual usage patterns discovered during testing

---

## Implementation Complete ✅

**Files Modified**:
1. `installer/global/commands/lib/template_create_orchestrator.py` (+47 lines)
   - Added `_print_agent_enhancement_instructions()` method
   - Updated Phase 8 to call new instruction method

2. `installer/global/commands/template-create.md` (+18 lines, -9 lines)
   - Updated Phase 8 workflow description
   - Enhanced `--create-agent-tasks` flag documentation

**Acceptance Criteria**: 11/11 (100%) ✅

**Testing**: Manual testing passed - output matches expected format ✅

**See**: `completion-summary.md` for detailed implementation report

---

**Created**: 2025-11-21T12:00:00Z
**Completed**: 2025-11-21T14:10:00Z
**Status**: COMPLETED
**Location**: tasks/completed/TASK-UX-2F95/
