---
id: TASK-CR-010
title: Regression test /task-work, /feature-build, /feature-plan workflows
status: backlog
created: 2026-02-05T14:00:00Z
updated: 2026-02-05T14:00:00Z
priority: high
tags: [testing, regression, context-optimization]
parent_review: TASK-REV-5F19
feature_id: FEAT-CR01
implementation_mode: task-work
wave: 3
complexity: 4
task_type: testing
depends_on:
  - TASK-CR-001
  - TASK-CR-002
  - TASK-CR-004
---

# Task: Regression Test Core Workflows After Context Reduction

## Description

Verify that trimming static files has not broken any core GuardKit workflows. Test each primary command flow to confirm Claude still has the context it needs.

## Acceptance Criteria

- [ ] /task-create: Successfully creates a task with correct frontmatter
- [ ] /task-work: Executes phases 2-5.5 without missing context (test with a simple task)
- [ ] /feature-plan: Auto-detection pipeline works, generates subtasks
- [ ] /feature-build: Player-Coach loop initiates correctly
- [ ] /task-review: Review modes function, decision checkpoint appears
- [ ] /task-complete: Archives task correctly
- [ ] Quality gates (Phase 2.5, Phase 4.5) still reference correct thresholds
- [ ] Pattern guidance still available when editing Python files (path-gated rules load)

## Implementation Notes

This is a manual verification task. Run each command in a test scenario and confirm:
1. No "missing context" or confused responses from Claude
2. Phase transitions work correctly
3. Quality gate thresholds are correct (80% coverage, 75% branch)
4. Path-gated rules load when expected

Run after Wave 1 completes (TASK-CR-001, CR-002, CR-004) and again after Wave 3.
