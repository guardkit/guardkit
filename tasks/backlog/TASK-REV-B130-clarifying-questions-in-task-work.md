---
id: TASK-REV-B130
title: Evaluate Adding Clarifying Questions to task-work Workflow
status: completed
created: 2025-12-08T12:00:00Z
updated: 2025-12-08T14:30:00Z
priority: high
task_type: review
tags: [workflow, ux, ai-collaboration, questions, assumptions]
complexity: 0
review_mode: decision
review_depth: standard
review_results:
  score: 85
  findings_count: 4
  recommendations_count: 3
  decision: implement
  report_path: .claude/reviews/TASK-REV-B130-review-report.md
  completed_at: 2025-12-08T14:30:00Z
implementation:
  option_selected: "Option 2: Unified cross-command (6 days)"
  subtasks_created: 12
  feature_folder: tasks/backlog/clarifying-questions/
  waves: 4
---

# Review: Evaluate Adding Clarifying Questions to task-work Workflow

## Description

Investigate the feasibility and value of introducing a "clarifying questions" phase to GuardKit's `/task-work` command. Rather than the AI making assumptions during implementation planning, the system would ask targeted questions to reduce ambiguity and improve implementation accuracy.

## Background & Inspiration

1. **Existing GuardKit Patterns**:
   - `/task-review` already uses interactive checkpoints (Accept/Revise/Implement/Cancel)
   - Requirements gathering in other tools asks clarifying questions
   - Phase 2.8 has human checkpoints for complexity ≥7
   - Complexity evaluation (Phase 2.7) exists but doesn't ask clarifying questions

2. **External Reference**:
   - Anthropic's `feature-dev` plugin has a clarifying questions concept
   - URL: https://github.com/anthropics/claude-code/tree/main/plugins/feature-dev

3. **GuardKit Concepts Reference**:
   - URL: https://guardkit.ai/concepts/

## Research Scope

### 1. Current Workflow Analysis
- Map existing checkpoints in task-work phases (2.5, 2.7, 2.8, 4.5, 5.5)
- Identify where assumptions are currently made
- Document what types of assumptions lead to rework

### 2. External Reference Analysis
- Analyze Anthropic's `feature-dev` plugin implementation
- Document how clarifying questions are structured
- Note UX patterns for question presentation
- Identify what triggers questions vs auto-proceed

### 3. Integration Points
- Phase 2 (Implementation Planning) - before planning starts?
- Phase 2.7 (Complexity Evaluation) - tie questions to complexity?
- Phase 2.8 (Human Checkpoint) - extend existing checkpoint?
- New Phase 2.1 (Clarification) - dedicated phase?

### 4. Question Categories to Consider
- Scope clarification ("Should X include Y?")
- Technology choices ("Prefer library A or B?")
- Architecture decisions ("Centralized vs distributed?")
- Priority trade-offs ("Performance vs simplicity?")
- Boundary definitions ("Where does this stop?")

## Acceptance Criteria

- [ ] Document current assumption points in task-work workflow
- [ ] Analyze Anthropic feature-dev plugin implementation
- [ ] Evaluate integration options with existing phases
- [ ] Assess implementation effort (quick win vs major change)
- [ ] Provide recommendation with pros/cons
- [ ] Draft high-level implementation plan if recommended

## Expected Deliverables

1. **Analysis Report** covering:
   - Current workflow gap analysis
   - External implementation review
   - Integration options comparison
   - Effort estimation

2. **Recommendation** with:
   - Go/No-Go decision
   - Justification
   - If Go: Implementation approach and rough plan

## Questions for Review

1. Should questions be mandatory or optional (like complexity checkpoint)?
2. Should question depth scale with complexity score?
3. How to avoid question fatigue for simple tasks?
4. Should answers be persisted for future reference?

## Related Files

- `installer/global/commands/task-work.md` - Main task-work command
- `.claude/commands/task-work-specification.md` - Internal spec
- `docs/workflows/complexity-management-workflow.md` - Existing checkpoint patterns
- `installer/global/commands/task-review.md` - Interactive checkpoint patterns

## External References

- https://github.com/anthropics/claude-code/tree/main/plugins/feature-dev
- https://guardkit.ai/concepts/

## Implementation Notes

**Decision**: Implement Option 2 - Unified cross-command clarification system (6 days)

**Architecture**: Single clarification module shared across `/task-work`, `/task-review`, and `/feature-plan` with three contexts:
- **Context A**: Review Scope (task-review, feature-plan)
- **Context B**: Implementation Preferences (feature-plan [I]mplement)
- **Context C**: Implementation Planning (task-work Phase 1.5)

**Implementation Structure**: Created feature subfolder with 12 subtasks organized into 4 waves:
- Wave 1 (Core Module): 3 parallel tasks - core.py, detection.py, display.py
- Wave 2 (Templates): 3 parallel tasks - Context A, B, C question templates
- Wave 3 (Integration): 3 parallel tasks - task-work, task-review, feature-plan integration
- Wave 4 (Polish): 3 parallel tasks - persistence, documentation, testing

## Review Decision

**Selected**: [I]mplement - Option 2: Unified cross-command (6 days)

**Rationale**: The unified approach maximizes code reuse across all three commands while providing context-specific question templates. The 4-wave implementation with Conductor parallel execution minimizes calendar time while maintaining quality gates.

## Generated Subtasks

See [tasks/backlog/clarifying-questions/](./clarifying-questions/) for:
- [README.md](./clarifying-questions/README.md) - Feature overview
- [IMPLEMENTATION-GUIDE.md](./clarifying-questions/IMPLEMENTATION-GUIDE.md) - Wave breakdown with parallel execution commands
- 12 subtask files (TASK-CLQ-001 through TASK-CLQ-012)

## Review Report

Full review report: [.claude/reviews/TASK-REV-B130-review-report.md](../../.claude/reviews/TASK-REV-B130-review-report.md)
