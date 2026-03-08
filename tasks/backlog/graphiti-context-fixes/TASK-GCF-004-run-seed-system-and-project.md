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

System seeding WAS run successfully from Richards-MBP (74/79 episodes, see `docs/reviews/vllm-profiling/graphiti_seeding.md`). However:

1. **Seeding marker is machine-local**: `.graphiti_seeded.json` was written to the Mac's filesystem, not present on promaxgb10-41b1 where AutoBuild runs. The `verify` command exits early without querying FalkorDB when the marker is absent.
2. **Project groups seeded under wrong namespace**: Seeding ran from guardkit repo (`project_id: guardkit`), creating `guardkit__project_overview`. AutoBuild runs from vllm-profiling (`project_id: vllm-profiling`), querying `vllm-profiling__project_overview` — namespace mismatch.
3. **System groups should be queryable** (no prefix) but queries still return 0 — needs investigation (may be RC5 silent exceptions or FalkorDB search issues).

## Prerequisites

- FalkorDB running on whitestocks:6379 (Synology NAS)
- vLLM server available at promaxgb10-41b1:8000 (for entity extraction)
- TASK-GCF-001 merged (so patterns query uses correct group ID)
- TASK-GCF-002 merged (so query failures are logged, not silently swallowed)

## Steps

### Step 0: Investigate why system group queries return 0 (from promaxgb10-41b1)

System groups have no prefix and should be queryable regardless of project_id. The 74 seeded episodes include `patterns` (5), `failure_patterns` (4), `quality_gate_phases` (12), etc. We need to determine why these return empty.

1. Create the seeding marker on GB10 so `verify` doesn't exit early:
   ```bash
   cd ~/Projects/appmilla_github/guardkit
   mkdir -p .guardkit/seeding
   echo '{"seeded": true, "version": "1.2.0", "source": "copied-from-mac"}' > .guardkit/seeding/.graphiti_seeded.json
   ```

2. Run verify with verbose output:
   ```bash
   guardkit graphiti verify --verbose
   ```

3. If verify still returns 0 results, run a manual search to isolate:
   ```bash
   guardkit graphiti search "quality gate phases" --group quality_gate_phases --verbose
   guardkit graphiti search "Player Coach pattern" --group feature_build_architecture --verbose
   ```

4. If manual searches also return 0, the issue is in FalkorDB's search layer (fulltext index, embedding search, or the FalkorDB workarounds). If they return results, the issue is in the JobContextRetriever query construction.

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
