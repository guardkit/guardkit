---
id: TASK-GLI-005
title: Re-seed ALL Graphiti content via local vLLM inference
task_type: implementation
status: completed
created: 2026-02-22T23:45:00Z
updated: 2026-03-01T12:00:00Z
completed: 2026-03-01T12:00:00Z
completed_location: tasks/completed/TASK-GLI-005/
priority: high
tags: [graphiti, vllm, testing, seeding]
complexity: 3
parent_review: TASK-REV-8B3A
feature_id: FEAT-GLI
wave: 3
implementation_mode: direct
dependencies: [TASK-GLI-001, TASK-GLI-003, TASK-GLI-004]
---

# Task: Re-seed ALL Graphiti Content via Local vLLM Inference

## Description

FalkorDB has been fully cleared. ALL knowledge content must be re-seeded from scratch using local vLLM inference on the GB10. This covers system context (17 categories), feature-build ADRs, and project documents — not just the feature-spec v2 document.

This is the end-to-end verification that the complete Graphiti knowledge pipeline works with local vLLM, fully bypassing OpenAI API.

## Context

- FalkorDB has been cleared — zero data remains (incompatible OpenAI embedding vectors purged)
- The feature-spec v2 document (70KB, 8,841 words) previously failed to seed due to OpenAI rate limiting
- After TASK-GLI-001 through TASK-GLI-004, Graphiti should be configured to use vLLM on the GB10
- `guardkit graphiti seed --force` seeds 17 system knowledge categories
- `guardkit graphiti seed-adrs` seeds feature-build ADRs (ADR-FB-001 through ADR-FB-003)
- `guardkit graphiti add-context` seeds project documents (feature-spec, architecture docs, etc.)

## Acceptance Criteria

### 1. Verify vLLM infrastructure is ready

- [x] Verify `.guardkit/graphiti.yaml` is configured with vLLM provider settings
- [x] Verify vLLM embedding instance is running on GB10 port 8001: `curl http://promaxgb10-41b1:8001/health`
- [x] Verify vLLM LLM instance is running on GB10 port 8000: `curl http://promaxgb10-41b1:8000/health`
- [x] Verify FalkorDB is accessible: `guardkit graphiti status`

### 2. Re-seed system context (17 categories)

- [x] Clear seeding marker if stale: the marker at `.guardkit/seeding/.graphiti_seeded.json` may reference old OpenAI-based seeding
- [x] Run: `guardkit graphiti seed --force`
- [x] Verify all 17 categories seed successfully:
  - product_knowledge (27 nodes, 72 edges)
  - command_workflows (113 nodes, 346 edges)
  - quality_gate_phases (56 nodes, 191 edges)
  - technology_stack (44 nodes, 129 edges)
  - feature_build_architecture (51 nodes, 118 edges)
  - architecture_decisions (45 nodes, 151 edges)
  - failure_patterns (26 nodes, 49 edges)
  - component_status (42 nodes, 96 edges)
  - integration_points (26 nodes, 70 edges)
  - templates (38 nodes, 121 edges)
  - agents (35 nodes, 46 edges)
  - patterns (88 nodes, 229 edges)
  - rules (47 nodes, 132 edges)
  - project_overview (46 nodes, 133 edges)
  - project_architecture (38 nodes, 71 edges)
  - failed_approaches (33 nodes, 101 edges)
  - pattern_examples (merged into patterns graph)
- [x] Verify: no rate limit errors (confirms vLLM is being used, not OpenAI)
- [x] Verify: `guardkit graphiti verify` passes all test queries

### 3. Re-seed feature-build ADRs

- [x] Run: `guardkit graphiti seed-adrs --force`
- [x] Verify ADRs seeded:
  - ADR-FB-001: Use SDK query() for task-work invocation
  - ADR-FB-002: Use FEAT-XXX paths in feature mode
  - ADR-FB-003: Pre-loop must invoke real task-work

### 4. Re-seed project documents

- [x] Run: `guardkit graphiti add-context docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md --type feature-spec`
- [x] Verify: episode creation succeeds (no rate limit errors) — 62 nodes, 308 edges, ~27 min
- [x] Verify: no "Episode creation returned None" errors
- [x] Verify: no unawaited coroutine warnings (`extract_edges_for_chunk`)

### 5. Verify complete knowledge graph

- [x] Run: `guardkit graphiti status` — 19 graphs, 817 nodes, 2363 edges
- [x] Verify search quality across all content types:
  - `guardkit graphiti search "What is GuardKit?"` — 5 results (product_knowledge)
  - `guardkit graphiti search "task-work command"` — 5 results (command_workflows)
  - `guardkit graphiti search "feature-spec command"` — 5 results (feature-spec-bdd-specification-generator)
  - `guardkit graphiti search "BDD Gherkin"` — 5 results (feature-spec-bdd-specification-generator)
  - `guardkit graphiti search "Player-Coach pattern"` — 5 results (feature_build_architecture)
- [x] Document: capture seed logs to `docs/reviews/feature-spec/graphiti_seed_3.md`
- [x] Document: note any content parsing warnings or partial failures

## Success Metric

All three seeding commands complete without errors and knowledge is searchable across all categories. `guardkit graphiti status` shows non-zero episode counts in System Knowledge, Project Knowledge, Decisions, and Learning sections. This confirms the full local vLLM inference pipeline works end-to-end, resolving the original OpenAI rate limiting failure documented in TASK-REV-8B3A.

## Key Files

- `.guardkit/graphiti.yaml` — config (vLLM provider settings)
- `guardkit/knowledge/seeding.py` — system context seeding orchestrator (17 categories)
- `guardkit/cli/graphiti.py` — CLI commands (seed, seed-adrs, add-context, status, verify)
- `docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md` — feature-spec document to seed
- `docs/reviews/feature-spec/graphiti_seed_2.md` — previous failed seed log

## Reference

- Parent review: TASK-REV-8B3A
- Previous failure log: `docs/reviews/feature-spec/graphiti_seed_2.md`
