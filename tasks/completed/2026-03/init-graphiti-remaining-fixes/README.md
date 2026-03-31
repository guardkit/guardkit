# FEAT-init-graphiti-remaining-fixes

## Problem

After the FEAT-falkordb-timeout-fixes round of fixes (TASK-REV-1F78 → 6 TASK-FIX tasks), `guardkit init` improved from ~119 min to ~33 min with 95% output reduction. However, 6 episodes still timeout at 120s (2 project_overview, 1 template, 2 agents, 2 rules) and 4 syncs fail.

## Solution

Two targeted fixes eliminate the remaining failures:

1. **TASK-FIX-9d45**: Remove `body_content` from agent sync, replace with `content_preview` — eliminates 2 agent sync failures
2. **TASK-FIX-f672**: Raise `project_overview` episode timeout to 180s — lets project purpose/architecture episodes complete

## Parent Review

TASK-REV-FE10 — Review init project 4 output after falkordb timeout fixes

## Projected Impact

| Metric | Current | After fixes |
|--------|---------|-------------|
| Total init time | ~33 min | ~27-29 min |
| Failed syncs | 4 | 0-1 |
| Episode timeouts | 6 | 1-2 |

## Execution

Both tasks are Wave 1 (independent, can run in parallel). Both are complexity 1, direct implementation mode.
