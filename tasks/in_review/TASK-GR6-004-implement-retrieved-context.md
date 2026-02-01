---
complexity: 5
dependencies:
- TASK-GR6-003
estimate_hours: 3
feature_id: FEAT-0F4A
id: TASK-GR6-004
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-006
task_type: feature
title: Implement RetrievedContext formatting
wave: 3
---

# Implement RetrievedContext formatting

## Description

Create the `RetrievedContext` dataclass with comprehensive formatting for prompt injection, including AutoBuild-specific sections.

## Acceptance Criteria

- [x] `to_prompt()` returns formatted context string
- [x] Sections for each context category
- [x] Budget usage displayed (used/total)
- [x] AutoBuild sections: Role Constraints, Quality Gates, Turn States, Implementation Modes
- [x] Emoji markers for different section types

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