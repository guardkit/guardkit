# Feature: Feature-Build Design Phase Fix

## Overview

Fix the critical gap in feature-build where the pre-loop phase returns mock data instead of actually invoking `/task-work --design-only` via SDK, causing the Player agent to fail with "Implementation plan not found".

**Source Review**: [TASK-REV-FB04](.claude/reviews/TASK-REV-FB04-review-report.md)
**Architecture Score**: 58/100
**Priority**: HIGH (blocks all feature-build functionality)

## Problem Statement

The feature-build orchestration fails because:
1. Pre-loop claims success (complexity=5, arch_score=80) but returns **mock data**
2. No implementation plan file is created
3. Player agent expects plan at `.claude/task-plans/{task_id}-implementation-plan.md`
4. Every Player turn fails with "Implementation plan not found"

## Solution Approach

**Option A (Selected)**: Fix TaskWorkInterface to actually invoke SDK with `/task-work --design-only`

This approach:
- Achieves 100% code reuse of task-work quality gates
- Maintains architectural consistency with documented design
- Unblocks all feature-build functionality

## Subtasks

| Task ID | Title | Mode | Wave | Effort |
|---------|-------|------|------|--------|
| TASK-FB-FIX-001 | Fix TaskWorkInterface to invoke SDK | task-work | 1 | 2-4h |
| TASK-FB-FIX-002 | Add plan existence validation in pre-loop | task-work | 1 | 1h |
| TASK-FB-FIX-003 | Centralize path logic in TaskArtifactPaths | task-work | 2 | 2h |
| TASK-FB-FIX-004 | Add integration test for pre-loop + Player | task-work | 2 | 2h |

## Dependencies

- Wave 1 tasks can run in parallel
- Wave 2 tasks depend on Wave 1 completion
- TASK-FB-FIX-003 and TASK-FB-FIX-004 can run in parallel

## Acceptance Criteria

- [ ] Pre-loop actually invokes `/task-work --design-only` via SDK
- [ ] Implementation plan file exists after pre-loop completes
- [ ] Player agent can read the plan and proceed with implementation
- [ ] Feature-build completes at least one task successfully
- [ ] Integration test verifies end-to-end flow

## Related Tasks

- TASK-REV-FB04 (source review)
- TASK-REV-FB01 (timeout analysis)
- TASK-REV-FB02 (task-work results analysis)
