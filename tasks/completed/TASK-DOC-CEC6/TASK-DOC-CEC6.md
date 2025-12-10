---
id: TASK-DOC-CEC6
title: Update documentation after global agents cleanup
status: completed
created: 2025-12-04T14:35:00Z
updated: 2025-12-05T10:00:00Z
completed: 2025-12-05T10:00:00Z
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria satisfied"
priority: medium
tags: [documentation, cleanup, agents]
task_type: implementation
complexity: 2
related_tasks: [TASK-IMP-GA02, TASK-REV-GA01]
completed_location: tasks/completed/TASK-DOC-CEC6/
---

# Task: Update Documentation After Global Agents Cleanup

## Background

Following TASK-IMP-GA02 (global agents cleanup), documentation needs updating to reflect the architectural changes:
- Design integration agents archived (figma-react-orchestrator, zeplin-maui-orchestrator)
- Stack-specific agents moved to templates
- Global agents now cross-stack only

## Scope

### 1. Remove Archived Command References

Remove references to commands that are now archived:
- `/figma-to-react` command references
- `/zeplin-to-maui` command references

Files to update:
- `CLAUDE.md` (root and .claude/)
- `docs/workflows/ux-design-integration-workflow.md` (archive or delete)

### 2. Update Agent Inventory

Update CLAUDE.md "Core AI Agents" section to reflect:
- 14 cross-stack agents in global (not stack-specific)
- Stack-specific agents are in templates

### 3. Update Agent Discovery Guide

Update `docs/guides/agent-discovery-guide.md`:
- Clarify that global agents are cross-stack only
- Document template agent locations
- Update examples to match new architecture

### 4. Update Template Documentation

Ensure template READMEs document their agents:
- `installer/core/templates/react-typescript/README.md`
- `installer/core/templates/nextjs-fullstack/README.md`

## Acceptance Criteria

- [x] No references to `/figma-to-react` or `/zeplin-to-maui` in active documentation (now "Coming Soon")
- [x] CLAUDE.md agent inventory accurately reflects 14 cross-stack global agents
- [x] Agent discovery guide updated with template agent architecture
- [x] Template READMEs list their stack-specific agents

## Notes

- This is a documentation-only task (no code changes)
- Low risk, can be done incrementally
- Consider keeping a "Coming Soon" note for design integration features

## Implementation Summary

### Files Modified (7 files)

1. **CLAUDE.md** (root)
   - Updated UX Design Integration section to "Coming Soon"
   - Updated Stack-Specific Implementation Agents to template-based
   - Updated MCP Integration section - Design MCPs now "Coming Soon"
   - Updated agent inventory reference

2. **docs/workflows/ux-design-integration-workflow.md**
   - Added "Coming Soon" header at top of file

3. **docs/guides/agent-discovery-guide.md**
   - Updated examples to use correct agent names (fastapi-specialist vs python-api-specialist)
   - Updated precedence examples to show template agents
   - Clarified global agents are cross-stack only
   - Updated Available Specialists section with template-based agents

4. **docs/guides/guardkit-workflow.md**
   - Updated MCP section - Design MCPs now "Coming Soon"
   - Updated Design System Detection section to "Coming Soon"

5. **installer/core/templates/react-typescript/README.md**
   - Updated agent list from 3 to 4 agents (added react-state-specialist)

6. **installer/core/templates/nextjs-fullstack/README.md**
   - Updated agent list from 3 to 4 agents (added react-state-specialist)

7. **installer/core/templates/react-fastapi-monorepo/README.md**
   - Added new Specialized AI Agents section with 3 agents

### Validation Results

- Global agent count: 14 (confirmed)
- Design integration commands: All references now in "Coming Soon" context
- Stack-specific agents: Correctly documented as template-based
