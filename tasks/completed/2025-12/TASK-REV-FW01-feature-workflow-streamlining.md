---
id: TASK-REV-FW01
title: Review feature workflow streamlining - /feature-task-create command and /task-review enhancements
status: completed
created: 2025-12-04T10:00:00Z
updated: 2025-12-04T11:00:00Z
implementation_tasks_created: true
implementation_folder: tasks/backlog/feature-workflow-streamlining/
priority: high
task_type: review
decision_required: true
tags: [feature-workflow, ux-improvement, developer-experience, competitive-differentiator]
complexity: 7
review_results:
  mode: decision
  depth: standard
  findings_count: 5
  recommendations_count: 3
  decision: implement_phased
  report_path: .claude/reviews/TASK-REV-FW01-review-report.md
  completed_at: 2025-12-04T10:30:00Z
---

# Review: Feature Workflow Streamlining

## Context

This review task analyzes how to formalize and streamline the evolved feature development workflow that has emerged from practical use.

### Current Evolved Workflow (Manual Steps)

The user has evolved a highly effective pattern:

1. **Create Review Task**: `/task-create "Review task to plan [feature]"` - Creates a review task
2. **Execute Review**: `/task-review TASK-XXX` - Investigates and plans the feature
3. **Revise or Accept**: Choose [R]evise for refinement or [I]mplement to create subtasks
4. **Organize Subtasks**: Request subtasks be placed in `tasks/backlog/{feature-name}/` subfolder
5. **Create Implementation Guide**: Request `IMPLEMENTATION-GUIDE.md` identifying:
   - Which tasks use `/task-work`
   - Which use direct Claude Code implementation
   - Wave/phase breakdown for parallel execution (Conductor)
6. **Create README.md**: Optional feature documentation

### Pain Points

1. **Remembering flags**: Tricky to remember which flags to pass to `/task-create` and `/task-review`
2. **Multiple manual steps**: Each step requires user intervention
3. **Inconsistent structure**: Manual requests for subfolder organization
4. **No automation pathway**: Gap between planning and automated implementation

### Competitive Advantage Opportunity

This workflow, if streamlined, would be a **massive differentiator** against:
- BMAD
- SpecKit
- AgentOS
- Other spec-driven development tools

**Key differentiators**:
- Ease of use (single command to start)
- Quality gates built-in
- Clear human decision points
- Parallel execution support via Conductor
- Progressive automation path via Claude Agent SDK

## Related Research Documents

1. [Claude_Agent_SDK_Two_Command_Feature_Workflow.md](../../docs/research/Claude_Agent_SDK_Two_Command_Feature_Workflow.md)
   - Two-command workflow: `/feature-task-create` + `/feature-task-work`
   - Human control points at investigation and merge
   - Manual override capability for risky tasks
   - Risk indicators on tasks

2. [Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md](../../docs/research/Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md)
   - SDK can invoke existing slash commands directly
   - ~1 week to working orchestrator
   - Message parsing for checkpoints

3. [Claude_Agent_SDK_True_End_to_End_Orchestrator.md](../../docs/research/Claude_Agent_SDK_True_End_to_End_Orchestrator.md)
   - Full automation specification (superseded but useful reference)
   - Parallel execution via git worktrees
   - AI Reviewer subagent for auto-approval

## Proposed Enhancements

### 1. New Command: `/feature-task-create`

**Purpose**: Single command to initiate feature planning workflow

**Behavior**:
```bash
/feature-task-create "implement dark mode"
```

Would automatically:
1. Create review task with `task_type:review` flag
2. Invoke `/task-review TASK-XXX` automatically
3. Present investigation findings
4. On [I]mplement: Create subtasks in `tasks/backlog/{feature-slug}/`
5. Generate `IMPLEMENTATION-GUIDE.md` with wave analysis
6. Generate `README.md` for the feature

**Key insight**: Combines what currently takes 5-6 manual steps into one command with clear checkpoints.

### 2. Enhanced `/task-review` [I]mplement Option

**Current**: Creates implementation task, user must organize manually

**Proposed**: When [I]mplement is chosen:
1. **Subtask creation**: Auto-create subtasks in subfolder
2. **Parallel analysis**: Identify which tasks can run in parallel (no file conflicts)
3. **Implementation guide**: Auto-generate with:
   - Wave/phase breakdown
   - `/task-work` vs direct implementation recommendations
   - Conductor workspace suggestions
4. **README.md**: Feature documentation with scope, decisions, structure

### 3. Implementation Modes for Subtasks

Each subtask should be tagged with recommended implementation approach:

| Mode | When to Use | Tool |
|------|-------------|------|
| `task-work` | Complex logic, needs quality gates | `/task-work TASK-XXX` |
| `direct` | Simple changes, configuration | Claude Code direct |
| `parallel-safe` | No file conflicts, can run with others | Conductor worktree |

## Review Questions

### Technical Decisions

1. **Command naming**: `/feature-task-create` vs `/feature-plan` vs `/feature-create`?
2. **Subfolder structure**: `tasks/backlog/{feature-slug}/` or `tasks/features/{feature-slug}/`?
3. **Implementation guide format**: Markdown with YAML frontmatter or pure markdown?
4. **Wave identification**: Automatic file conflict detection or manual specification?

### Scope Decisions

1. **Phase 1 scope**: What's the minimum viable enhancement for public release?
2. **Phase 2 scope**: What requires Claude Agent SDK integration?
3. **Integration with existing commands**: How to avoid breaking changes?

### Quality Considerations

1. **Backward compatibility**: Must work without SDK for initial release
2. **Progressive disclosure**: Simple use → advanced features
3. **Error handling**: What if investigation fails? What if decomposition is rejected?

## Acceptance Criteria for Review

- [ ] Clear recommendation on command structure and naming
- [ ] Defined scope for Phase 1 (pre-SDK) and Phase 2 (with SDK)
- [ ] Implementation plan with subtasks
- [ ] Risk assessment
- [ ] Competitive differentiation analysis

## Decision Options

At review completion, the following options will be available:

- **[A]ccept**: Findings are comprehensive, proceed to archive
- **[I]mplement**: Create implementation subtasks in `tasks/backlog/feature-workflow-streamlining/`
- **[R]evise**: Request deeper analysis on specific aspects
- **[C]ancel**: Discard review

## Notes

This is a high-priority enhancement that could significantly improve developer experience and competitive positioning before public release. The research documents provide excellent technical foundations - this review should focus on:

1. Synthesizing the research into actionable plan
2. Identifying minimum viable scope
3. Creating clear implementation path
