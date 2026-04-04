# Feature: Improve Low-Confidence Templates and Installer Display

## Feature ID: FEAT-ILCT
## Parent Review: TASK-REV-81AA

## Problem Statement

Two builtin templates score below the 75/100 confidence threshold:
- **nats-asyncio-service**: 70.0/100 — missing quality_scores, boilerplate pattern files, null framework versions
- **langchain-deepagents-orchestrator**: 68.33/100 — missing quality_scores, generic architecture label, incomplete layer mappings

The installer template listing also has inconsistencies: missing descriptions, missing scores, no label explaining what scores mean, and the `common` internal template appearing in user-facing output.

## Solution Approach

1. **Enrich manifest metadata** for both templates (quality_scores, production flags, framework versions)
2. **Populate pattern rule files** in nats-asyncio-service with real examples from exemplar
3. **Fix orchestrator structural metadata** (architecture label, layers, patterns)
4. **Standardise installer display** (filter common, add scores, add label)
5. **Extend settings.json** for both templates (code_style, layer responsibilities)

## Subtask Summary

| Task | Title | Wave | Complexity | Method |
|------|-------|------|-----------|--------|
| TASK-ILCT-001 | Enrich nats-asyncio-service manifest and settings | 1 | 3 | task-work |
| TASK-ILCT-002 | Enrich langchain-deepagents-orchestrator manifest and settings | 1 | 3 | task-work |
| TASK-ILCT-003 | Populate nats-asyncio-service pattern rule files | 1 | 4 | task-work |
| TASK-ILCT-004 | Add mcp-typescript confidence_score to manifest | 1 | 1 | direct |
| TASK-ILCT-005 | Standardise installer template display | 2 | 3 | task-work |
| TASK-ILCT-006 | Extend settings.json code_style for both templates | 2 | 2 | direct |
| TASK-ILCT-007 | Verify confidence scores improved | 3 | 2 | direct |

## Target Outcome

- Both templates at 80+ confidence score
- All installer template lines have descriptions and confidence ratings
- Score label explains meaning to users
- `common` template filtered from user-facing display
