---
id: TASK-GCF-004
title: Run seed-system and seed-project for guardkit knowledge graph
status: backlog
task_type: implementation
priority: high
tags: [graphiti, seeding, operational]
complexity: 1
parent_review: TASK-REV-982B
feature_id: FEAT-GCF
wave: 2
implementation_mode: manual
dependencies: [TASK-GCF-001, TASK-GCF-003]
created: 2026-03-08T15:00:00Z
---

# Task: Run seed-system and seed-project for guardkit knowledge graph

## Problem

The `.guardkit/seeding/` directory has no `.system_seeded.json` or `.graphiti_seeded.json` markers, indicating that `seed-system` and `seed-project` were never run successfully. This means all system-scoped groups (failure_patterns, role_constraints, quality_gate_configs, implementation_modes, patterns) and project-scoped groups (project_architecture, domain_knowledge) are empty in FalkorDB.

## Prerequisites

- FalkorDB running on whitestocks:6379 (Synology NAS)
- vLLM server available at promaxgb10-41b1:8000 (for entity extraction)
- TASK-GCF-001 merged (so patterns query uses correct group ID)

## Steps

### From guardkit repo (`~/Projects/appmilla_github/guardkit/`)

System seeding uses guardkit's own templates, agents, rules, and patterns. The `.guardkit/graphiti.yaml` config (FalkorDB on whitestocks:6379, project_id: guardkit) lives here.

1. Verify FalkorDB connectivity:
   ```bash
   guardkit graphiti verify --verbose
   ```

2. Seed system content:
   ```bash
   guardkit graphiti seed-system --force
   ```

3. Verify seeding markers created:
   ```bash
   ls -la .guardkit/seeding/
   # Should see .system_seeded.json
   ```

### From vllm-profiling repo (`~/Projects/appmilla_github/vllm-profiling/`)

Project seeding reads CLAUDE.md/README.md from the target project directory. Since AutoBuild runs build the vllm-profiling project, this is where project-specific context should be seeded from.

4. Seed project knowledge (vllm-profiling already has `.guardkit/graphiti.yaml` with `project_id: vllm-profiling`):
   ```bash
   guardkit graphiti seed-project
   ```
   This will read vllm-profiling's CLAUDE.md/README.md and seed into `vllm-profiling__project_overview`, `vllm-profiling__project_architecture` etc.

5. Test context retrieval:
   ```bash
   guardkit graphiti search "structured logging middleware"
   ```

### Important: project_id Namespace Difference

- **guardkit** repo: `project_id: guardkit` → project groups prefixed `guardkit__`
- **vllm-profiling** repo: `project_id: vllm-profiling` → project groups prefixed `vllm-profiling__`

System groups (patterns, role_constraints, quality_gate_configs, etc.) have **no prefix** and are shared across both projects. Project groups are isolated per project_id — this is correct behaviour.

## Acceptance Criteria

- [ ] `.guardkit/seeding/.system_seeded.json` exists
- [ ] `guardkit graphiti search` returns results for system groups
- [ ] Project architecture context is queryable
