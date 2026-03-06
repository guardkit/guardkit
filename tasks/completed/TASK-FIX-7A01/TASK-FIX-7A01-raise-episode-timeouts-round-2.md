---
id: TASK-FIX-7A01
title: Raise episode timeouts round 2 — recover chronic timeout failures
status: completed
created: 2026-03-06T17:30:00Z
updated: 2026-03-06T18:05:00Z
completed: 2026-03-06T18:05:00Z
completed_location: tasks/completed/TASK-FIX-7A01/
priority: high
task_type: implementation
complexity: 2
tags: [graphiti, seeding, timeout, performance]
parent_review: TASK-REV-95B1
feature_id: FEAT-seed-timeout-chunking
wave: 1
implementation_mode: task-work
previous_state: in_review
state_transition_reason: "All acceptance criteria met, quality gates passed"
organized_files:
  - TASK-FIX-7A01-raise-episode-timeouts-round-2.md
---

# Task: Raise Episode Timeouts Round 2

## Description

The first timeout raise (TASK-FIX-b94e) set rules to 180s and project_overview to 240s. However, reseed_guardkit_5 still shows 8 timeout failures:

### Episodes Still Timing Out

| Episode | Current timeout | Category |
|---------|----------------|----------|
| command_task_work | 120s | command_workflows |
| command_feature_spec | 120s | command_workflows |
| workflow_feature_to_build | 120s | command_workflows |
| phases_overview | 120s | quality_gate_phases |
| component_taskwork_interface | 120s | component_status |
| rule_default_quality_gates | 180s | rules |
| rule_default_workflow | 180s | rules |
| guardkit_project_structure | 120s | project_architecture |

### Proposed Changes

**File**: `guardkit/knowledge/graphiti_client.py`

Raise timeouts based on observed patterns:
- **rules**: 180s → 240s (both default rules consistently time out at 180s)
- **command_workflows**: 120s → 180s (3 episodes timing out)
- **quality_gate_phases**: 120s → 150s (phases_overview times out)
- **component_status**: 120s → 150s (component_taskwork_interface times out)
- **project_architecture**: 120s → 150s (guardkit_project_structure times out)

Alternatively, implement a more granular per-episode timeout map rather than per-group.

## Acceptance Criteria

- [x] Timeout values raised for affected groups
- [x] No existing passing episodes broken
- [x] Code compiles and existing tests pass
- [x] Estimated recovery: at least 5 of 8 currently-failing episodes

## Evidence

- reseed_guardkit_5 log: `docs/reviews/reduce-static-markdown/reseed_guardkit_5.md`
- Review report: `.claude/reviews/TASK-REV-95B1-review-report.md`

## Implementation Summary

### Changes Made

**`guardkit/knowledge/graphiti_client.py`** (lines 975-988):
- `rules` timeout: 180s → 240s (recovers rule_default_quality_gates, rule_default_workflow)
- Added `command_workflows` → 180s (recovers command_task_work, command_feature_spec, workflow_feature_to_build)
- Added `quality_gate_phases`, `component_status`, `project_architecture` → 150s (recovers phases_overview, component_taskwork_interface, guardkit_project_structure)

**`tests/knowledge/test_graphiti_client.py`**:
- Updated 3 existing tests to expect 240s for rules (was 180s)
- Added 4 new timeout tier assertions for command_workflows, quality_gate_phases, component_status, project_architecture

### Expected Recovery

All 8 failing episodes should now have sufficient timeout headroom:
- 2 rules episodes: 180s → 240s (+33%)
- 3 command_workflows episodes: 120s → 180s (+50%)
- 1 quality_gate_phases episode: 120s → 150s (+25%)
- 1 component_status episode: 120s → 150s (+25%)
- 1 project_architecture episode: 120s → 150s (+25%)
