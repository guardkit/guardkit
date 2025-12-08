---
id: TASK-STD-8666
title: Standardize extended file token counts across agents
status: backlog
created: 2025-12-07T11:45:00Z
updated: 2025-12-07T11:45:00Z
priority: low
tags: [progressive-disclosure, consistency, documentation]
complexity: 2
related_tasks: [TASK-REV-7C49]
---

# Task: Standardize Extended File Token Counts

## Description

Extended agent files currently vary in size from 13KB to 20KB. While acceptable, standardizing to ~15KB ± 2KB would improve consistency and predictability.

**Source**: Review finding from TASK-REV-7C49

## Current State

| Agent Extended File | Size | Lines |
|---------------------|------|-------|
| svelte5-component-specialist-ext.md | ~13KB | ~422 |
| external-api-integration-specialist-ext.md | ~14KB | ~542 |
| alasql-in-memory-db-specialist-ext.md | ~17KB | ~643 |
| firebase-firestore-specialist-ext.md | ~20KB | ~814 |
| smui-material-ui-specialist-ext.md | ~13KB | ~561 |

## Target State

All extended files should be 15KB ± 2KB (13-17KB range).

## Acceptance Criteria

- [ ] Review `firebase-firestore-specialist-ext.md` for content that could be trimmed
- [ ] Ensure all extended files have consistent section structure
- [ ] Document target size in agent-enhance command
- [ ] No quality degradation from trimming

## Implementation Notes

This is a low priority task. The current variance is acceptable for production use.

Options:
1. Trim larger files (firebase) by consolidating similar examples
2. Expand smaller files (svelte, smui) with additional scenarios
3. Accept variance as-is (different agents need different depth)

## Estimated Effort

Simple (1-3 complexity) - Content review and minor adjustments.
