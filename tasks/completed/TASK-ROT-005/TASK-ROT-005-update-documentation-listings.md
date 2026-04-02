---
id: TASK-ROT-005
title: Update CLAUDE.md and docs/templates.md template listings
status: completed
created: 2026-04-02T00:00:00Z
completed: 2026-04-02T00:00:00Z
priority: medium
tags: [documentation, templates]
parent_review: TASK-REV-TI25
feature_id: FEAT-ROT
implementation_mode: direct
wave: 3
complexity: 1
depends_on:
  - TASK-ROT-003
---

# Task: Update CLAUDE.md and docs/templates.md template listings

## Description

Update all documentation that enumerates available templates to include `langchain-deepagents-orchestrator`.

## Files to Update

### 1. Root CLAUDE.md (line ~223)

Current:
```
Templates: react-typescript | fastapi-python | nextjs-fullstack | react-fastapi-monorepo | langchain-deepagents | langchain-deepagents-weighted-evaluation | default
```

Updated:
```
Templates: react-typescript | fastapi-python | nextjs-fullstack | react-fastapi-monorepo | langchain-deepagents | langchain-deepagents-weighted-evaluation | langchain-deepagents-orchestrator | default
```

### 2. docs/templates.md

Add entry for `langchain-deepagents-orchestrator` with:
- Description: Pipeline orchestrator using DeepAgents two-model architecture
- Confidence score: 68.33%
- When to use: Autonomous development pipeline agents, two-model orchestration (reasoning + implementation)

### 3. docs/research/dark_factory/README.md

Update status from "pending review task to add as built-in" to registered (after implementation complete).

## Acceptance Criteria

- [x] Root CLAUDE.md lists 8 templates (was 7)
- [x] docs/templates.md includes orchestrator template entry
- [x] Template description clearly differentiates from base and weighted-evaluation variants
