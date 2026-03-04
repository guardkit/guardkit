---
id: TASK-REV-AE10
title: Review init project output (second run, post-IGR-001 fix)
status: completed
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T00:00:00Z
priority: high
complexity: 5
tags: [graphiti, init, review, falkordb, vllm, graphiti-core]
task_type: review
review_mode: architectural
review_depth: standard
parent_review: TASK-REV-21D3
feature_id: FEAT-IGR
dependencies: []
---

# Task: Review init project output (second run, post-IGR-001 fix)

## Description

Analyse the second `guardkit init` run output captured in `docs/reviews/reduce-static-markdown/init_project_2.md` (lines 689-806). This run was performed after applying TASK-IGR-001 (suppress noisy loggers) and the template sync fix. The run shows significant improvements but also surfaces **new issues** from graphiti-core's edge_operations module and template sync YAML parsing.

## Context

- **Parent review**: TASK-REV-21D3 (original init output analysis)
- **Feature**: FEAT-IGR (Init + Graphiti Resilience)
- **Input file**: `docs/reviews/reduce-static-markdown/init_project_2.md` (lines 689-806, second run)
- **Environment**: vLLM on promaxgb10-41b1 (LLM port 8000, embeddings port 8001), FalkorDB on whitestocks:6379
- **Previous fixes applied**: TASK-IGR-001 (log suppression), TASK-IGR-003 (template sync client reuse)

## Known Issues to Analyse

### Issue 1: LLM returns invalid duplicate_facts indices (NEW)
- **Source**: `graphiti_core.utils.maintenance.edge_operations`
- **Message**: `LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)`
- **Occurrences**: 4 (3 in episode 3, 1 in Step 2.5 template sync)
- **Impact**: Unknown — may cause silent data loss or duplicate edges in knowledge graph
- **Root cause hypothesis**: vLLM/Claude response format mismatch with graphiti-core's expected JSON structure for duplicate fact detection

### Issue 2: Double timezone suffix in valid_at date parsing (NEW)
- **Source**: `graphiti_core.utils.maintenance.edge_operations`
- **Message**: `Error parsing valid_at date: Invalid isoformat string: '2026-03-03T20:09:08.043388+00:00+00:00'. Input: 2026-03-03T20:09:08.043388+00:00Z`
- **Occurrences**: 13 (all in episode 4)
- **Impact**: Edge temporal metadata may be incorrect or missing
- **Root cause hypothesis**: LLM generates `+00:00Z` suffix (double timezone: offset + Z), graphiti-core strips trailing Z but appends +00:00 again, resulting in `+00:00+00:00`

### Issue 3: Target index out of bounds for edge chunks (NEW)
- **Source**: `graphiti_core.utils.maintenance.edge_operations`
- **Message**: `Target index 15/16 out of bounds for chunk of size 15 in edge HAS_PHASE`
- **Occurrences**: 3 (Step 2.5, fastapi-testing-specialist sync)
- **Impact**: Edge relationships may be incorrectly linked or missing
- **Root cause hypothesis**: Zero-indexed vs 1-indexed mismatch between LLM output and graphiti-core chunk array

### Issue 4: YAML frontmatter parsing fails for glob paths (NEW)
- **Source**: `guardkit.knowledge.template_sync`
- **Message**: `Failed to parse agent frontmatter: while scanning an alias ... paths: **/*.py`
- **Occurrences**: 3 (code-style.md, testing.md, database/migrations.md rules)
- **Impact**: Rule metadata (paths, globs) not captured in knowledge graph — rules are still synced but without structured metadata
- **Root cause hypothesis**: template_sync uses `yaml.safe_load()` on frontmatter containing unquoted glob patterns; YAML treats `*` as alias indicator

### Issue 5: Episode 1 performance regression
- **Observation**: Episode 1 took 187.1s (vs 46.9s in first run — 4x slower)
- **Total seeding time**: 525.6s for 8 episodes
- **Episode timing**: 187.1s, 61.6s, 73.3s, 40.7s, 14.1s, 55.3s, 51.9s, 41.5s
- **Impact**: Init takes ~9 minutes for seeding alone
- **Root cause hypothesis**: Cold start on vLLM after Graphiti data clear, or episode 1 content is significantly larger

### Issue 6: Step 2.5 template sync — no completion message / truncated output
- **Observation**: Output ends at line 806 after syncing rule 'testing' — no completion summary for Step 2.5, no "Done" message
- **Template sync episode timings**: 125.9s, 115.5s, 127.3s, 154.9s, 406.4s, 120.5s
- **Impact**: Unknown whether remaining rules were synced; last visible episodes took 120-406s each
- **Root cause hypothesis**: Output may have been truncated during capture, or init process was still running

## Improvements Confirmed (from FEAT-IGR fixes)

These should be verified and documented in the review:

1. **TASK-IGR-001 (log suppression)**: httpx/httpcore/falkordb noise eliminated — output is readable
2. **TASK-IGR-003 (template sync)**: Step 2.5 now works — synced template + 3 agents + rules (was "incomplete results" before)
3. **No "Max pending queries" errors**: All 8 episodes completed (episode 3 was dropped before)
4. **Progress indicator working**: "Seeding episode N/8..." with timing visible

## Acceptance Criteria

- [ ] Each of the 6 known issues analysed with severity rating (CRITICAL/HIGH/MEDIUM/LOW)
- [ ] Root cause confirmed or hypothesised for each issue (graphiti-core vs GuardKit vs vLLM)
- [ ] Determine which issues are upstream (graphiti-core) vs fixable in GuardKit
- [ ] Verify improvements from TASK-IGR-001 and TASK-IGR-003 are working as expected
- [ ] Recommendations for new FEAT-IGR tasks if warranted
- [ ] Episode timing analysis — is 525.6s acceptable or should it be optimised?

## Files to Review

- `docs/reviews/reduce-static-markdown/init_project_2.md` (lines 689-806)
- `guardkit/knowledge/template_sync.py` (YAML frontmatter parsing)
- `guardkit/knowledge/graphiti_client.py` (episode creation, timing)
- graphiti-core source: `graphiti_core/utils/maintenance/edge_operations.py` (upstream issues 1-3)

## Review Report Location

`.claude/reviews/TASK-REV-AE10-review-report.md`

## Review Decision

**Decision**: [I]mplement (Approach A)
**Implementation tasks created**: `tasks/backlog/init-graphiti-yaml-fix/`
- TASK-IGR-YQ01: Quote glob patterns in 38 rule frontmatter files
- TASK-IGR-TS01: Add template sync completion summary

## Effort Estimate

~2 hours
