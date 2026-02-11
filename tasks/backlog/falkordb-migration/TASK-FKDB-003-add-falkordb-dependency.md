---
id: TASK-FKDB-003
title: Add falkordb optional dependency to pyproject.toml
status: backlog
created: 2026-02-11T17:00:00Z
priority: high
tags: [falkordb, dependencies, migration]
parent_review: TASK-REV-38BC
feature_id: FEAT-FKDB-001
implementation_mode: direct
wave: 1
complexity: 1
depends_on:
  - TASK-FKDB-001
---

# Task: Add falkordb optional dependency to pyproject.toml

## Description

Add `falkordb` as an optional dependency so users can install FalkorDB support with `pip install guardkit-py[falkordb]`.

## Acceptance Criteria

- [ ] AC-001: `pyproject.toml` has `falkordb` optional dependency group
- [ ] AC-002: `pip install guardkit-py[falkordb]` installs the `falkordb` Python package
- [ ] AC-003: Base install (`pip install guardkit-py`) does NOT install `falkordb`

## Files to Modify

- `pyproject.toml` — Add optional dependency group

## Implementation Notes

```toml
[project.optional-dependencies]
falkordb = ["graphiti-core[falkordb]"]
```

The `graphiti-core[falkordb]` extra pulls in the `falkordb` package which provides `falkordb.asyncio.FalkorDB`.
