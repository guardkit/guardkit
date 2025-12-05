# Feature: Workflow Streamlining

## Overview

This feature introduces the `/feature-plan` command and enhances the `/task-review` [I]mplement option to provide a streamlined, single-command feature planning experience.

**Parent Review**: [TASK-REV-FW01](../TASK-REV-FW01-feature-workflow-streamlining.md)
**Review Report**: [.claude/reviews/TASK-REV-FW01-review-report.md](../../../.claude/reviews/TASK-REV-FW01-review-report.md)

## Problem Statement

The current feature planning workflow requires 5-6 manual steps:
1. `/task-create "Review task..."` with correct flags
2. `/task-review TASK-XXX` with correct mode
3. Choose [R]evise or [I]mplement
4. Request subfolder organization
5. Request IMPLEMENTATION-GUIDE.md creation
6. Request README.md creation

**Pain points**:
- Remembering flags for each command
- Multiple manual steps and requests
- Inconsistent structure across features
- No automation pathway

## Solution

### Phase 1: Single-Command Planning (This Feature)

**New Command**: `/feature-plan`
```bash
/feature-plan "implement dark mode"
```

Automatically:
1. Creates review task with correct flags
2. Executes `/task-review` with decision mode
3. On [I]mplement: Auto-creates subfolder + subtasks + guide + readme

**Key Discovery**: No SDK required! Slash commands are markdown instruction files.

### Phase 2: Automated Execution (Future)

**New Command**: `/feature-work`
```bash
/feature-work dark-mode
```

Executes all subtasks in parallel using Conductor worktrees via Claude Agent SDK.

## Scope

### In Scope (Phase 1)
- `/feature-plan` command (markdown orchestration)
- Auto-detect feature slug from title
- Auto-detect subtasks from recommendations
- Implementation mode auto-tagging
- Parallel group detection (file conflicts)
- IMPLEMENTATION-GUIDE.md generator
- README.md generator
- Enhanced [I]mplement orchestration

### Out of Scope (Phase 2)
- `/feature-work` command
- SDK-based parallel execution
- Git worktree automation
- Wave-based execution with checkpoints

## Success Criteria

1. User can type ONE command to start feature planning
2. [I]mplement creates complete subfolder structure automatically
3. IMPLEMENTATION-GUIDE.md follows established template pattern
4. Wave analysis correctly identifies parallel-safe tasks
5. Implementation mode correctly assigned based on complexity

## Competitive Advantage

This workflow is a significant differentiator against:
- BMAD
- SpecKit
- AgentOS
- Other spec-driven development tools

**Key differentiators**:
- Single command to start
- Quality gates built-in
- Clear human decision points
- Parallel execution support
- Progressive automation path

## Related Documents

- [Claude_Agent_SDK_Two_Command_Feature_Workflow.md](../../../docs/research/Claude_Agent_SDK_Two_Command_Feature_Workflow.md)
- [Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md](../../../docs/research/Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md)
- [progressive-disclosure/IMPLEMENTATION-GUIDE.md](../progressive-disclosure/IMPLEMENTATION-GUIDE.md) - Template reference
