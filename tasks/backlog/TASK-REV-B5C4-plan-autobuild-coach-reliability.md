---
id: TASK-REV-B5C4
title: "Plan: AutoBuild Coach Reliability and Graphiti Connection Resilience"
status: completed
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T10:00:00Z
priority: high
task_type: review
tags: [autobuild, coach, reliability, graphiti, asyncio, circuit-breaker]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan: AutoBuild Coach Reliability and Graphiti Connection Resilience

## Description
Plan the implementation of fixes for two compounding failures that make AutoBuild unreliable:
- F2: Coach criteria verification always returns 0/10 because Player output format doesn't match what coach_validator.py expects
- F3: FalkorDB/Graphiti asyncio corruption during parallel task execution causes connection errors

These failures interact in a doom loop that prevents successful task completion.

## Context
Feature spec: docs/features/FEAT-AUTOBUILD-COACH-RELIABILITY-spec.md

## Acceptance Criteria
- [ ] Technical options analyzed for F2 (criteria verification) fixes
- [ ] Technical options analyzed for F3 (asyncio/Graphiti) fixes
- [ ] Implementation breakdown with task dependencies identified
- [ ] Risk assessment for each approach
- [ ] Parallel execution groups determined

## Review Scope
- Focus: All aspects (comprehensive)
- Trade-off priority: Quality/reliability
