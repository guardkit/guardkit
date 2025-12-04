---
id: TASK-IMP-GA02
title: Cleanup global agents - delete redundant, move/archive stack-specific
status: completed
created: 2025-12-04T10:00:00Z
updated: 2025-12-04T14:45:00Z
completed: 2025-12-04T14:45:00Z
priority: high
tags: [agents, architecture, cleanup, templates]
task_type: implementation
complexity: 4
related_tasks: [TASK-REV-GA01, TASK-DOC-CEC6]
review_report: .claude/reviews/TASK-REV-GA01-review-report.md
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria verified"
completed_location: tasks/completed/TASK-IMP-GA02/
---

# Task: Cleanup Global Agents

## Background

Based on the architectural review (TASK-REV-GA01), stack-specific agents should not exist in `installer/global/agents/`. Global agents should be cross-stack only, with stack-specific agents living in their respective templates.

## Implementation Plan

### Phase 1: Delete Redundant Agents

Delete agents that are redundant with existing template agents:

| Agent | Reason |
|-------|--------|
| `installer/global/agents/python-api-specialist.md` | Redundant with `fastapi-specialist` in fastapi-python template |
| `installer/global/agents/dotnet-domain-specialist.md` | No .NET template exists; recreate when template added |

### Phase 2: Archive Design Integration Agents

Archive agents for features not yet fully implemented:

1. Create directory: `tasks/backlog/design-url-integration/`
2. Move `installer/global/agents/figma-react-orchestrator.md` → `tasks/backlog/design-url-integration/`
3. Move `installer/global/agents/zeplin-maui-orchestrator.md` → `tasks/backlog/design-url-integration/`

### Phase 3: Move React Agent to Templates

Move the `react-state-specialist` to React templates (it has unique Zustand/Context coverage):

1. Move `installer/global/agents/react-state-specialist.md` → `installer/global/templates/react-typescript/agents/`
2. Copy to `installer/global/templates/nextjs-fullstack/agents/` (Next.js uses React)

### Phase 4: Create Documentation Cleanup Task

Create a follow-up task to remove references to archived commands from documentation:
- Remove `/figma-to-react` command references
- Remove `/zeplin-to-maui` command references
- Update CLAUDE.md agent inventory
- Update agent discovery guide

## Acceptance Criteria

- [x] `python-api-specialist.md` deleted from global agents
- [x] `dotnet-domain-specialist.md` deleted from global agents
- [x] `figma-react-orchestrator.md` archived to `tasks/backlog/design-url-integration/`
- [x] `zeplin-maui-orchestrator.md` archived to `tasks/backlog/design-url-integration/`
- [x] `react-state-specialist.md` moved to `react-typescript/agents/`
- [x] `react-state-specialist.md` copied to `nextjs-fullstack/agents/`
- [x] Follow-up task created for documentation cleanup (TASK-DOC-CEC6)
- [x] Global agents folder contains only cross-stack agents (14 total)

## Implementation Summary

### Actions Completed

1. **Deleted redundant agents:**
   - `installer/global/agents/python-api-specialist.md` ✅
   - `installer/global/agents/dotnet-domain-specialist.md` ✅

2. **Archived design integration agents:**
   - `figma-react-orchestrator.md` → `tasks/backlog/design-url-integration/` ✅
   - `zeplin-maui-orchestrator.md` → `tasks/backlog/design-url-integration/` ✅

3. **Moved react-state-specialist to templates:**
   - Moved to `installer/global/templates/react-typescript/agents/` ✅
   - Copied to `installer/global/templates/nextjs-fullstack/agents/` ✅

4. **Created follow-up task:**
   - TASK-DOC-CEC6: Update documentation after global agents cleanup ✅

### Final State Verification

```
installer/global/agents/              # Cross-stack only (14 agents) ✅
├── agent-content-enhancer.md
├── architectural-reviewer.md
├── build-validator.md
├── code-reviewer.md
├── complexity-evaluator.md
├── database-specialist.md
├── debugging-specialist.md
├── devops-specialist.md
├── git-workflow-manager.md
├── pattern-advisor.md
├── security-specialist.md
├── task-manager.md
├── test-orchestrator.md
└── test-verifier.md

installer/global/templates/react-typescript/agents/ (4 agents)
├── feature-architecture-specialist.md
├── form-validation-specialist.md
├── react-query-specialist.md
└── react-state-specialist.md         # MOVED from global ✅

installer/global/templates/nextjs-fullstack/agents/ (4 agents)
├── nextjs-fullstack-specialist.md
├── nextjs-server-actions-specialist.md
├── nextjs-server-components-specialist.md
└── react-state-specialist.md         # COPIED from global ✅

tasks/backlog/design-url-integration/
├── figma-react-orchestrator.md       # ARCHIVED ✅
└── zeplin-maui-orchestrator.md       # ARCHIVED ✅
```

## Notes

- No changes needed to `init-project.sh` - current logic already works correctly
- This change only affects new project initializations, not existing projects
- Archived agents can be restored when design integration features are implemented
- Follow-up task TASK-DOC-CEC6 created to update documentation
