---
id: TASK-FIX-986D
title: Add missing command workflow episodes to seed_command_workflows.py
status: completed
created: 2026-02-12T00:00:00Z
updated: 2026-02-12T00:00:00Z
completed: 2026-02-12T00:00:00Z
priority: high
tags: [graphiti, seeding, falkordb, knowledge-graph]
parent_review: TASK-REV-3ECA
complexity: 3
completed_location: tasks/completed/TASK-FIX-986D/
---

# Task: Add missing command workflow episodes

## Description

`seed_command_workflows.py` currently seeds 7 episodes but 12+ CLI commands and workflows have been added since the original seeding was written. Add the missing episodes to ensure the Graphiti knowledge graph has complete command coverage.

## Context

- Parent review: TASK-REV-3ECA (FINDING-1 + FINDING-3)
- Current branch: `graphiti-falkorDB-migration`
- FalkorDB migration is complete, this is pre-seed cleanup

## Current State (7 episodes)

1. `workflow_overview` - Core 3-command workflow
2. `command_task_create` - /task-create
3. `command_task_work` - /task-work
4. `command_task_complete` - /task-complete
5. `command_feature_plan` - /feature-plan
6. `command_feature_build` - /feature-build
7. `workflow_feature_to_build` - Feature planning to build flow

## Episodes to Add (12)

### Slash Commands (8)
- `command_task_review` - /task-review with modes (architectural, code-quality, decision, security, technical-debt) and decision checkpoint ([A]ccept/[R]evise/[I]mplement/[C]ancel)
- `command_task_refine` - /task-refine iterative code refinement
- `command_task_status` - /task-status progress dashboard with epic/feature context
- `command_feature_complete` - /feature-complete merge and archive AutoBuild results
- `command_debug` - /debug systematic bug investigation and root cause analysis
- `command_system_overview` - /system-overview architecture summary
- `command_impact_analysis` - /impact-analysis pre-task architecture validation
- `command_context_switch` - /context-switch multi-project navigation

### CLI Commands (2)
- `cli_guardkit_review` - `guardkit review` CLI with `--capture-knowledge` flag
- `cli_guardkit_graphiti` - `guardkit graphiti` subcommands overview (seed, status, verify, capture, search, show, list, clear, add-context)

### Workflows (2)
- `workflow_review_to_implement` - Review -> Decision -> [I]mplement -> task-work flow
- `workflow_design_first` - /task-work --design-only -> approve -> /task-work --implement-only flow

## Acceptance Criteria

- [x] AC-001: 19 total episodes in `seed_command_workflows.py` (7 existing + 12 new)
- [x] AC-002: Each episode follows existing pattern: (name, {entity_type, name/purpose, syntax, ...})
- [x] AC-003: Docstring updated from "Creates 7 episodes" to "Creates 19 episodes"
- [x] AC-004: Test in `test_seeding.py` updated from `call_count == 7` to `call_count == 19`
- [x] AC-005: All existing tests pass (no regressions) - 46 passed, 0 failed

## Files to Change

- `guardkit/knowledge/seed_command_workflows.py` - Add 12 new episodes, update docstring
- `tests/knowledge/test_seeding.py` - Update episode count assertion (line 182)

## Reference

- Command specs: `installer/core/commands/*.md`
- CLI source: `guardkit/cli/main.py`, `guardkit/cli/graphiti.py`, `guardkit/cli/review.py`
- Episode format: Follow existing pattern in `seed_command_workflows.py:26-127`
