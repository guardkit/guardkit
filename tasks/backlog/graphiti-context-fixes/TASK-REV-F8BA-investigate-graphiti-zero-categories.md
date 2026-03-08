---
id: TASK-REV-F8BA
title: Investigate Graphiti context retrieval returning 0 categories despite seeded data
status: backlog
task_type: review
review_mode: decision
review_depth: comprehensive
priority: critical
tags: [graphiti, investigation, falkordb, context-loading, autobuild]
complexity: 7
parent_review: TASK-REV-982B
feature_id: FEAT-GCF
related_tasks: [TASK-GCF-001, TASK-GCF-002, TASK-GCF-003, TASK-GCF-004, TASK-GCF-005]
created: 2026-03-08T16:00:00Z
updated: 2026-03-08T16:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Investigate Graphiti Context Retrieval Returning 0 Categories Despite Seeded Data

## Description

AutoBuild context loading returns 0 categories/0 tokens for ALL tasks across Run 3 and Run 4, despite:

1. **FalkorDB connectivity confirmed** — pre-flight TCP check passes, indices exist, workarounds applied
2. **74/79 episodes successfully seeded** — `guardkit graphiti seed --force` completed on 2026-03-06 from Richards-MBP (see `docs/reviews/vllm-profiling/graphiti_seeding.md`)
3. **System groups have no namespace prefix** — `patterns` (5 episodes), `failure_patterns` (4), `quality_gate_phases` (12), `product_knowledge` (3) etc. should be queryable from any project

The investigation must determine why seeded system group data is not returned by `GraphitiClient.search()` when invoked from `JobContextRetriever._query_category()` during AutoBuild runs on promaxgb10-41b1.

## Context

### Known Root Causes (from TASK-REV-982B revised analysis)

| RC | Description | Status |
|----|-------------|--------|
| RC2 | `patterns` seeded as system group, queried as `patterns_python` (project-prefixed) | **FIXED** — TASK-GCF-001 implemented |
| RC3 | Dynamic groups (`task_outcomes`, `turn_states`, `feature_specs`) empty on fresh runs | **FIXED** — TASK-GCF-003 implemented (groups added to `_group_defs.py`) |
| RC4 | Project groups seeded under `guardkit__` prefix, queried under `vllm-profiling__` | **Confirmed** — namespace mismatch, needs operational fix |
| RC5 | `_query_category()` has bare `except Exception: return [], 0` — no logging | **FIXED** — TASK-GCF-002 implemented |

### Completed Fixes

The following tasks have been implemented:

| Task | Description | Status |
|------|-------------|--------|
| TASK-GCF-001 | Fix `patterns_{tech_stack}` → `patterns` group ID mismatch | **Implemented** |
| TASK-GCF-002 | Add `logger.warning()` to `_query_category()` exception handler | **Implemented** |
| TASK-GCF-003 | Add `task_outcomes`/`turn_states` to `_group_defs.py` | **Implemented** |
| TASK-VOPT-001 | Context reduction (~19KB → ~10-12KB) | **Implemented** |
| TASK-VOPT-002 | Per-SDK-turn timing instrumentation | **Implemented** |
| TASK-VOPT-003 | Suppress FalkorDB index log noise | **Implemented** |

### Unresolved Mystery

With RC2, RC3, and RC5 code fixes now in place, the next AutoBuild run will have diagnostic visibility via the new logging. However, the core question remains: system groups like `failure_patterns`, `quality_gate_phases`, `role_constraints`, `implementation_modes` have **no prefix** and were seeded with 4-12 episodes each. Why do these also return 0?

Possible hypotheses:
1. **Silent exceptions in search** — FalkorDB fulltext search or embedding search failing, caught by RC5's bare except
2. **FalkorDB workaround side effects** — `build_fulltext_query` patched to remove group_id filter; may break group-scoped queries
3. **Embedding model mismatch** — seeding used vLLM embeddings on promaxgb10-41b1, but search may use different embeddings or model state
4. **Cross-machine FalkorDB state** — seeding from Mac via Tailscale; queries from GB10 via Tailscale; possible graph state inconsistency
5. **Graphiti-core search API behaviour** — search may require specific query formats or return edges not matching expected dict structure
6. **Group ID not passed to search correctly** — FalkorDB workaround patches `handle_multiple_group_ids` for "single group_id support"; may not pass group filter at all

## Review Objectives

### Objective 1: Reproduce on GB10

- Create seeding marker on GB10 (so `verify` doesn't exit early)
- Run `guardkit graphiti verify --verbose` to test system group queries
- Run manual `guardkit graphiti search` commands against known-seeded groups
- Document which groups return results and which don't

### Objective 2: Trace the search code path

- Trace `GraphitiClient.search()` → `_execute_search()` → `graphiti_core.search()`
- Examine the FalkorDB workaround patches (especially `build_fulltext_query` and `handle_multiple_group_ids`)
- Determine if group_id filtering is actually applied to FalkorDB queries
- Check if the `_apply_group_prefix()` logic handles system groups correctly when called from `search()`

### Objective 3: Isolate the failure layer

- Is the issue in: (a) GraphitiClient prefix resolution, (b) graphiti-core search API, (c) FalkorDB query layer, or (d) data not actually present?
- Run direct FalkorDB queries (via redis-cli or FalkorDB browser) to verify data exists
- Compare seeding log group IDs with runtime query group IDs

### Objective 4: Test with implemented fixes

- TASK-GCF-001 (patterns fix), TASK-GCF-002 (logging), TASK-GCF-003 (group defs) are now implemented
- TASK-VOPT-001 (context reduction), TASK-VOPT-002 (timing), TASK-VOPT-003 (log noise suppression) are now implemented
- Run an AutoBuild task and check logs for:
  - Category-level warning messages from the new `_query_category()` logging (reveals exceptions vs empty results)
  - Whether `patterns` (now queried correctly without `_{tech_stack}` suffix) returns results
  - Per-SDK-turn timing data from TASK-VOPT-002
  - Reduced context size from TASK-VOPT-001

### Objective 5: Resolution plan

- Determine the root cause(s) for system group queries returning 0
- Propose specific code/config fixes
- Estimate impact on AutoBuild performance if context loads successfully

## Reference Files

| File | Description |
|------|-------------|
| `docs/reviews/vllm-profiling/graphiti_seeding.md` | Full seeding log (74/79 episodes, 106m) |
| `docs/reviews/vllm-profiling/vllm_run_4.md` | Run 4 log showing 0 categories |
| `.claude/reviews/TASK-REV-982B-review-report.md` | Parent review with RC analysis |
| `guardkit/knowledge/graphiti_client.py` | Client with search(), _apply_group_prefix() |
| `guardkit/knowledge/job_context_retriever.py` | _query_category() with silent exception |
| `guardkit/knowledge/falkordb_workaround.py` | FalkorDB patches (build_fulltext_query, handle_multiple_group_ids) |
| `guardkit/knowledge/autobuild_context_loader.py` | Context loader reporting 0 categories |
| `guardkit/_group_defs.py` | Group definitions (PROJECT vs SYSTEM) |
| `.guardkit/graphiti.yaml` | guardkit config (project_id: guardkit) |
| `~/Projects/appmilla_github/vllm-profiling/.guardkit/graphiti.yaml` | vllm-profiling config (project_id: vllm-profiling) |

## Acceptance Criteria

- [ ] Reproduced 0-category issue on GB10 with controlled test
- [ ] Determined whether system group data is queryable via direct FalkorDB access
- [ ] Identified which layer fails: prefix resolution, graphiti-core, FalkorDB, or data absence
- [ ] FalkorDB workaround patches reviewed for group_id filtering impact
- [ ] RC5 logging fix applied and AutoBuild run with visible query diagnostics
- [ ] Root cause documented with evidence
- [ ] Resolution plan with specific code/config changes

## Implementation Notes

This is a review/investigation task. Use `/task-review TASK-REV-F8BA` to execute.

Priority is critical because Graphiti context loading is a fundamental design component of AutoBuild — if it never delivers context, the 8x performance gap to Anthropic cannot be reduced through knowledge-based optimisation.
