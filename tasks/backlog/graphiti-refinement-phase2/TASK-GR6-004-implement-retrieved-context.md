---
id: TASK-GR6-004
title: Implement RetrievedContext formatting
status: backlog
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
