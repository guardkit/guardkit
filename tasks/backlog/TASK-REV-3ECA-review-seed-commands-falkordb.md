---
id: TASK-REV-3ECA
title: Review and update seed function for FalkorDB migration
status: backlog
created: 2026-02-12T00:00:00Z
updated: 2026-02-12T00:00:00Z
priority: high
tags: [graphiti, falkordb, seeding, knowledge-graph, migration]
task_type: review
complexity: 4
---

# Task: Review and update seed function for FalkorDB migration

## Description

Review the Graphiti knowledge graph seed function (`seed_command_workflows.py` and `seeding.py`) to ensure all recently added CLI commands are included, then run the seed command against the new FalkorDB backend (migrated from Neo4J).

## Context

- FalkorDB migration is complete and connection is verified working
- Current branch: `graphiti-falkorDB-migration`
- The seed function was written when only 7 command episodes existed
- Multiple CLI commands have been added since the original seeding was written
- The CLI `_cmd_seed()` display lists only 13 categories but `seed_all_system_context()` seeds 18

## Scope of Review

### 1. Command Workflows Seed (`seed_command_workflows.py`)

**Currently seeded (7 episodes):**
- `workflow_overview` - Core 3-command workflow
- `command_task_create` - /task-create
- `command_task_work` - /task-work
- `command_task_complete` - /task-complete
- `command_feature_plan` - /feature-plan
- `command_feature_build` - /feature-build
- `workflow_feature_to_build` - Feature planning to build flow

**Commands potentially missing:**
- `/task-review` - Structured analysis and decision-making
- `/task-refine` - Iterative code refinement
- `/task-status` - Task progress dashboard
- `/feature-complete` - Merge and archive AutoBuild results
- `guardkit review` - CLI review with knowledge capture
- `guardkit system-plan` - Architecture planning
- `guardkit system-overview` - Architecture summary
- `guardkit impact-analysis` - Pre-task validation
- `guardkit context-switch` - Multi-project navigation
- `guardkit graphiti capture` - Interactive knowledge capture
- `guardkit graphiti search/list/show` - Knowledge query commands
- `guardkit graphiti clear` - Clear knowledge data

### 2. CLI Display Sync (`graphiti.py:_cmd_seed()`)

The `_cmd_seed()` success display (lines 127-141) only lists 13 categories but `seed_all_system_context()` seeds 18. Missing from display:
- `project_overview`
- `project_architecture`
- `failed_approaches`
- `quality_gate_configs`
- `pattern_examples`

### 3. Run Seed Against FalkorDB

After updates, run `guardkit graphiti seed --force` against the FalkorDB backend to populate the knowledge graph.

## Acceptance Criteria

- [ ] AC-001: All current CLI commands are represented in `seed_command_workflows.py`
- [ ] AC-002: CLI `_cmd_seed()` display lists all 18 (or current) seeded categories
- [ ] AC-003: `guardkit graphiti seed --force` completes successfully against FalkorDB
- [ ] AC-004: `guardkit graphiti verify` passes after seeding
- [ ] AC-005: No regression in existing seed tests

## Files to Review/Update

- `guardkit/knowledge/seed_command_workflows.py` - Add missing command episodes
- `guardkit/cli/graphiti.py` - Update `_cmd_seed()` category display list
- `guardkit/knowledge/seeding.py` - Verify all categories in orchestrator

## Implementation Notes

- FalkorDB connection is confirmed working (TASK-FKDB-001 validated)
- Use `--force` flag to re-seed since marker may exist from Neo4J era
- Seeding is idempotent via `upsert_episode()`
