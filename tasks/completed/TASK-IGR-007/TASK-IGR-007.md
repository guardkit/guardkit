---
id: TASK-IGR-007
title: Document system vs project group IDs and query helper
status: completed
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T17:55:00Z
completed: 2026-03-03T17:55:00Z
priority: low
complexity: 2
tags: [documentation, graphiti, developer-experience]
parent_review: TASK-REV-21D3
feature_id: FEAT-IGR
wave: 2
implementation_mode: direct
dependencies: []
---

# Task: Document system vs project group IDs and query helper

## Description

Update documentation to clarify that system-scoped groups (e.g., `role_constraints`, `implementation_modes`) use unprefixed group IDs, while project-scoped groups use `{project_id}__` prefix. Also remove the `OPENAI_API_KEY=dummy` suggestion for vLLM configurations (verified unnecessary).

Optionally, add a CLI command or helper to list available groups by scope.

## Context

The query that returned 0 results for role_constraints was searching in `vllm-profiling__product_knowledge` instead of the unprefixed `role_constraints`. This is by design but not documented clearly.

## Acceptance Criteria

- [x] Documentation clearly explains system vs project group scoping
- [x] Examples show correct query group IDs for each scope
- [x] `OPENAI_API_KEY=dummy` suggestion removed for vLLM configs
- [ ] Optional: `guardkit graphiti list-groups` or similar helper (deferred - optional)

## Files to Modify

- Graphiti setup/usage documentation
- Optional: `guardkit/cli/graphiti.py` (list-groups helper)

## Effort Estimate

~1 hour
