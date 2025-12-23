---
id: TASK-AB-A76A
title: Implement AgentInvoker class
status: completed
created: 2025-12-23T07:22:00Z
updated: 2025-12-23T15:02:21.998263Z
completed: 2025-12-23T15:02:21.998263Z
priority: high
tags: [autobuild, orchestration, implementation]
complexity: 4
parent_review: TASK-REV-47D2
wave: 1
conductor_workspace: autobuild-phase1a-wave1-3
implementation_mode: task-work
completed_location: tasks/completed/TASK-AB-A76A/
organized_files: ["TASK-AB-A76A.md"]
test_results:
  status: passed
  coverage: 84.62
  last_run: 2025-12-23T09:25:00Z
  tests_passed: 28
  tests_failed: 0
  branch_coverage: 85.29
architectural_review:
  score: 76
  status: approved_with_recommendations
  solid: 84
  dry: 72
  yagni: 64
code_review:
  score: 92
  status: approved
  quality: excellent
plan_audit:
  severity: medium
  status: approved
  justification: Quality improvements (docstrings, error handling, tests)
  loc_variance: 69.1
completion_summary:
  duration: "~45 minutes"
  files_created: 5
  total_loc: 1150
  quality_gates_passed: 7
---

# Task: Implement AgentInvoker class

## Description

Create `guardkit/orchestrator/agent_invoker.py` with AgentInvoker class that handles Claude Agents SDK invocation for Player and Coach agents.

## Parent Review

This task was generated from review task TASK-REV-47D2.

## Files to Create/Modify

- guardkit/orchestrator/agent_invoker.py
- tests/unit/test_agent_invoker.py

## Estimated Effort

4-5 hours

## Implementation Mode

**task-work** - Requires implementation, testing, and quality gates

## Acceptance Criteria

See IMPLEMENTATION-GUIDE.md for detailed Wave 1 acceptance criteria and deliverables.
