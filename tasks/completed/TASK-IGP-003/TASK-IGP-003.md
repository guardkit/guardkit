---
id: TASK-IGP-003
title: Encourage --copy-graphiti for multi-project FalkorDB setups
status: completed
created: 2026-03-15T12:30:00Z
updated: 2026-03-15T15:00:00Z
priority: low
tags: [init, graphiti, documentation, falkordb, config]
task_type: implementation
parent_review: TASK-REV-A73F
feature_id: FEAT-IGP
implementation_mode: direct
wave: 1
complexity: 1
depends_on: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Encourage --copy-graphiti for multi-project FalkorDB setups

## Description

The `--copy-graphiti` flag (and its auto-offer behavior) is the primary mechanism for avoiding FalkorDB embedding dimension mismatches in multi-project setups. When a child project copies config from a parent, it inherits ALL infrastructure settings including `embedding_provider`, `embedding_model`, `graph_store`, and connection details.

This task ensures documentation prominently recommends `--copy-graphiti` as the default workflow for multi-project environments.

## Context

From TASK-REV-A73F review (Finding 5 - PyYAML optional dependency):
- Without `--copy-graphiti`, projects fall back to defaults (neo4j, openai embedding)
- If actual infra is FalkorDB with different embedding model → dimension mismatch
- `--copy-graphiti` solves this completely by propagating parent config
- The auto-offer at init.py:674-695 already handles this well for adjacent projects

## Acceptance Criteria

- [x] `.claude/rules/graphiti-knowledge.md` has a "Multi-Project Setup" section recommending `--copy-graphiti`
- [x] The `guardkit init --help` output mentions `--copy-graphiti` as recommended for shared FalkorDB
- [x] No code logic changes (documentation only)

## Key Files

- `.claude/rules/graphiti-knowledge.md` - Add multi-project guidance
- `guardkit/cli/init.py` - Update help text for `--copy-graphiti` option (line ~833)

## Implementation Notes

Minimal documentation update. Add to graphiti-knowledge.md:

```markdown
## Multi-Project Setup (Shared FalkorDB)

When multiple projects share a FalkorDB instance, use `--copy-graphiti` during init
to inherit infrastructure settings from an existing project:

    guardkit init --copy-graphiti

This auto-discovers a parent project's `.guardkit/graphiti.yaml` and copies all
connection and embedding settings, replacing only the `project_id`. This prevents
embedding dimension mismatches when the shared FalkorDB was seeded with a specific
embedding model.
```
