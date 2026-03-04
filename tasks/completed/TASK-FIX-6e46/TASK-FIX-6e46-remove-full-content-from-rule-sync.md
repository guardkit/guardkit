---
id: TASK-FIX-6e46
title: Remove full_content from rule episode sync
status: completed
task_type: implementation
created: 2026-03-04T00:00:00Z
completed: 2026-03-04T00:00:00Z
priority: critical
tags: [graphiti, template-sync, reduce-static-markdown, performance]
complexity: 2
parent_review: TASK-REV-1F78
feature_id: FEAT-falkordb-timeout-fixes
wave: 1
implementation_mode: direct
dependencies: []
---

# Task: Remove full_content from rule episode sync

## Description

Remove the `full_content` field from the rule episode body in `sync_rule_to_graphiti()`. This reduces entity extraction work by ~90% per rule, dramatically cutting the number of FalkorDB queries generated.

## Why This Is Safe

The `rules` group in Graphiti is **NEVER queried by the Player/Coach autobuild agents**. Confirmed by code trace through `job_context_retriever.py` — the autobuild retriever queries: `feature_specs`, `task_outcomes`, `patterns_{tech_stack}`, `project_architecture`, `failure_patterns`, `domain_knowledge`, `role_constraints`, `quality_gate_configs`, `turn_states`, `implementation_modes`.

The `rules` group is only available via `guardkit graphiti search` for human ad-hoc queries. The 500-char `content_preview` is sufficient for search result display.

Actual rule content is served to Claude Code via `.claude/rules/*.md` files copied during Step 1 of init.

## Files Modified

- `guardkit/knowledge/template_sync.py` — removed `full_content` field from rule_body dict
- `tests/knowledge/test_template_sync.py` — updated 2 tests to assert `full_content` is absent

## Acceptance Criteria

- [x] `full_content` field removed from rule_body dict
- [x] `content_preview` (500 chars) retained for search display
- [x] Tests updated and passing (51/51 passed)
- [x] `guardkit init fastapi-python` Step 2.5 generates fewer entities per rule
