---
id: TASK-GR4-006
title: Add /task-review --capture-knowledge integration
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-004
wave: 1
parallel_group: wave1-gr004
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies:
  - TASK-GR4-005
---

# Add /task-review --capture-knowledge integration

## Description

Integrate knowledge capture into the `/task-review` command so insights from reviews can be captured and persisted.

## Acceptance Criteria

- [ ] `--capture-knowledge` flag triggers post-review capture
- [ ] Context-specific questions based on review findings
- [ ] Abbreviated session (3-5 questions max)
- [ ] Captured decisions/warnings linked to task context
- [ ] Works with all review modes

## Technical Details

**Integration Point**: After review completion, before decision checkpoint

**Context-Specific Questions**:
- "What did you learn about {task_type} from this review?"
- "Were there any decisions made that should be remembered?"
- "Are there any warnings for similar future tasks?"

**Reference**: See FEAT-GR-004 task-review integration section.
