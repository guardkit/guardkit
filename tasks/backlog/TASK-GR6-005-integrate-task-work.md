---
id: TASK-GR6-005
title: Integrate with /task-work
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies:
  - TASK-GR6-004
---

# Integrate with /task-work

## Description

Integrate the `JobContextRetriever` into the `/task-work` command so that job-specific context is retrieved and injected into the task execution prompt.

## Acceptance Criteria

- [ ] Context retrieved at start of task execution
- [ ] Context injected into task prompt
- [ ] Phase-appropriate context (planning vs implementation vs review)
- [ ] `--verbose` flag shows context retrieval details
- [ ] Graceful degradation if Graphiti unavailable

## Technical Details

**Integration Point**: Phase 2 (Planning) and Phase 3 (Implementation)

**Workflow**:
1. Load task
2. Retrieve job-specific context via `JobContextRetriever`
3. Format context with `to_prompt()`
4. Inject into task execution prompt

**Reference**: See FEAT-GR-006 Integration with /task-work section.
