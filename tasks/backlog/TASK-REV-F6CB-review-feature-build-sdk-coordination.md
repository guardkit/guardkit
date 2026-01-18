---
id: TASK-REV-F6CB
title: Review feature-build SDK coordination gaps after task-work refactor
status: review_complete
created: 2026-01-18T10:30:00Z
updated: 2026-01-18T12:00:00Z
priority: high
task_type: review
decision_required: true
tags: [feature-build, claude-agent-sdk, task-work, coordination, review]
complexity: 6
parent_reviews: [TASK-REV-FB15, TASK-REV-FB16]
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  findings_count: 5
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-F6CB-review-report.md
  completed_at: 2026-01-18T12:00:00Z
implementation_tasks:
  feature_id: FEAT-FBSDK
  feature_path: tasks/backlog/feature-build-sdk-coordination/
  tasks_created: 5
  task_ids:
    - TASK-FBSDK-001
    - TASK-FBSDK-002
    - TASK-FBSDK-003
    - TASK-FBSDK-004
    - TASK-FBSDK-005
---

# Task: Review feature-build SDK coordination gaps after task-work refactor

## Description

Following the successful implementation of recommendations from TASK-REV-FB15 (root cause analysis) and TASK-REV-FB16 (provenance-aware intensity system), the `/feature-build` command still exhibits coordination issues with the Claude Agent SDK during task execution.

The test trace in `docs/reviews/feature-build/test_after_task_work_refactor.md` shows that while the task-work performance improvements were implemented, the integration between the AutoBuild orchestrator and the SDK has gaps that need to be addressed.

## Context from Prior Reviews

### TASK-REV-FB15 Key Findings
- Phase 2 agent invocation consuming 58 minutes (81% of total time) - excessive documentation generation
- Documentation level enforcement needed (2 files max constraint not enforced)
- Recommended raising micro-mode threshold from complexity ≤1 to complexity ≤3

### TASK-REV-FB16 Key Findings
- Task provenance should inform intensity level (tasks from `/task-review` or `/feature-plan` shouldn't redo ceremony)
- Proposed 4-level intensity gradient: minimal, light, standard, strict
- Implemented provenance-aware auto-detection

## Current Issue Summary (from test trace)

The test trace shows repeated failures with pattern:

```
Turn 1/5: Player Implementation - error - Player failed - attempting state recovery
Turn 1: Coach Validation - feedback - Task-work results not found at ...
```

Key observations:
1. **Task file not found in worktree** - Tasks weren't copied to worktree initially
2. **SDK timeout at 2400s** (40 minutes) but made progress - 15 files created
3. **State recovery mechanism working** but coordination with SDK results incomplete
4. **task_work_results.json not being written** despite work being done

## Review Objectives

1. **Identify SDK integration gaps** - Where is the coordination failing between AutoBuild orchestrator and Claude Agent SDK?

2. **Analyze state handoff** - How is state being passed between:
   - GuardKit orchestrator → SDK invocation
   - SDK execution → task_work_results.json
   - task_work_results.json → Coach validator

3. **Assess worktree setup** - Why weren't task files available in worktree?

4. **Evaluate timeout handling** - Is 2400s timeout appropriate? How should partial progress be handled?

5. **Recommend coordination improvements** - What changes needed to ensure clean handoff between components?

## Files to Review

- `docs/reviews/feature-build/test_after_task_work_refactor.md` - Full test trace
- `src/guardkit/orchestrator/agent_invoker.py` - SDK invocation logic
- `src/guardkit/orchestrator/autobuild.py` - AutoBuild orchestration
- `src/guardkit/orchestrator/feature_orchestrator.py` - Feature-level orchestration
- `src/guardkit/tasks/state_bridge.py` - Task state management
- `src/guardkit/orchestrator/quality_gates/coach_validator.py` - Coach validation

## Acceptance Criteria

- [ ] Root cause of task file not found in worktree identified
- [ ] SDK result handoff mechanism documented
- [ ] Gaps in task_work_results.json generation identified
- [ ] Recommendations for coordination improvements provided
- [ ] Risk assessment for proposed changes included
- [ ] Implementation priority recommendations provided

## Related Work

- Prior reviews: TASK-REV-FB15, TASK-REV-FB16
- Related backlog: `tasks/backlog/feature-build/`
- Implementation guide: `tasks/backlog/task-work-performance/IMPLEMENTATION-GUIDE.md`

## Review Mode Suggestion

**Mode**: decision (technical decision analysis)
**Depth**: standard (1-2 hours)

```bash
/task-review TASK-REV-F6CB --mode=decision --depth=standard
```

## Implementation Notes

This review should produce:
1. Decision analysis report identifying coordination gaps
2. Prioritized list of fixes needed
3. Implementation tasks if [I]mplement is selected at checkpoint

## Test Execution Log

[Automatically populated by /task-review]
