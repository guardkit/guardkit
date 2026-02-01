---
id: TASK-GR6-004
title: Implement RetrievedContext formatting
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: task-work
complexity: 5
estimate_hours: 3
dependencies:
- TASK-GR6-003
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T16:59:40.605768'
  last_updated: '2026-02-01T17:09:00.644629'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T16:59:40.605768'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Implement RetrievedContext formatting

## Description

Create the `RetrievedContext` dataclass with comprehensive formatting for prompt injection, including AutoBuild-specific sections.

## Acceptance Criteria

- [ ] `to_prompt()` returns formatted context string
- [ ] Sections for each context category
- [ ] Budget usage displayed (used/total)
- [ ] AutoBuild sections: Role Constraints, Quality Gates, Turn States, Implementation Modes
- [ ] Emoji markers for different section types

## Technical Details

**Location**: `guardkit/knowledge/job_context_retriever.py`

**Prompt Format**:
```
## Job-Specific Context
Budget used: 4500/6000 tokens

### Feature Context
...

### What Worked for Similar Tasks
...

### Role Constraints
**Player**: Must do: ... Must NOT do: ...

### Quality Gate Thresholds
**feature**: coverage≥80%, arch≥60

### Previous Turn Context
Turn 1: FEEDBACK - Initial implementation incomplete
```

**Reference**: See FEAT-GR-006 RetrievedContext section.
