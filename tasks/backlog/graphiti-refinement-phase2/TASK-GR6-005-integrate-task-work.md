---
id: TASK-GR6-005
title: Integrate with /task-work
status: in_review
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
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T17:23:00.922181'
  last_updated: '2026-02-01T17:35:59.021817'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T17:23:00.922181'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
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
