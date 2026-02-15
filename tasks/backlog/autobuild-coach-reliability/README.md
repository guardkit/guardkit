# AutoBuild Coach Reliability and Graphiti Connection Resilience

## Problem

AutoBuild is unreliable due to two compounding failures:

1. **F2 — Criteria Verification Always 0/10**: The Coach's `validate_requirements()` can never verify criteria because `completion_promises` aren't propagated through the standard task-work path, and exact text matching fails on any rephrasing.

2. **F3 — Asyncio Corruption**: The autobuild orchestrator's per-thread event loops cause `Lock is bound to a different event loop` errors during cleanup, `no running event loop` errors in turn state capture, and 43+ connection retry failures without circuit breaking.

These create a doom loop: F3 degrades Graphiti -> timeouts -> synthetic reports with no promises -> F2 returns 0/10 -> identical feedback -> repeat until UNRECOVERABLE_STALL.

## Solution

8 targeted fixes across 4 execution waves:

- **Wave 1** (Foundation): Propagate completion_promises, add diagnostics, store event loop references
- **Wave 2** (Core Fixes): Fuzzy text matching, fix thread cleanup, fix turn state capture
- **Wave 3** (Advanced): Git-based synthetic promises, Graphiti circuit breaker
- **Wave 4** (Validation): Integration test with TASK-SFT-001

## Tasks

| ID | Title | Wave | Complexity |
|----|-------|------|-----------|
| TASK-ACR-001 | Propagate completion_promises | 1 | 3 |
| TASK-ACR-003 | Diagnostic logging | 1 | 2 |
| TASK-ACR-005 | Store event loop with loaders | 1 | 3 |
| TASK-ACR-002 | Fuzzy text matching | 2 | 5 |
| TASK-ACR-006 | Fix thread cleanup | 2 | 5 |
| TASK-ACR-007 | Fix turn state capture | 2 | 4 |
| TASK-ACR-004 | Synthetic report git analysis | 3 | 6 |
| TASK-ACR-008 | Graphiti circuit breaker | 3 | 5 |

## Getting Started

```bash
# Review the implementation guide
cat tasks/backlog/autobuild-coach-reliability/IMPLEMENTATION-GUIDE.md

# Start with Wave 1 tasks (parallel)
/task-work TASK-ACR-001
/task-work TASK-ACR-003
/task-work TASK-ACR-005

# Or use feature-build for autonomous execution
/feature-build FEAT-ACR
```
