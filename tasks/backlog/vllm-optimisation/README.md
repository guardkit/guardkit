# vLLM Optimisation (FEAT-VOPT)

**Parent Review**: TASK-REV-CB30 — Analyse vLLM Performance Regression and Viability

## Problem Statement

vLLM/Qwen3 on GB10 runs 3-7.5x slower than Anthropic API after Run 3 fixes. The remaining gap is primarily hardware-bound (3-4x per-turn latency) compounded by turn inefficiency on complex tasks. Run 3 proved Graphiti context loading helps significantly (FBP-007 went from FAILED to SUCCESS), but the gap remains above the 2.5-3x target for medium-to-complex tasks.

## Run 3 Results (Baseline)

| Metric | Run 2 | Run 3 | Change |
|--------|-------|-------|--------|
| Tasks completed | 6/7 | 7/7 | +1 |
| FBP-007 | FAILED (4 turns) | SUCCESS (1 turn) | Fixed |
| FBP-007 duration | 138m | 64m | -54% |
| Graphiti | Broken | Working | Fixed |
| SDK ceiling hits | 33% | 0% (FBP-007 only) | TBD (full run needed) |

## Subtasks

| Task | Description | Priority | Complexity | Mode | Wave |
|------|-------------|----------|------------|------|------|
| TASK-VOPT-001 | Context reduction: slim task-work protocol for local backends | High | 4 | task-work | 1 |
| TASK-VOPT-002 | Add per-SDK-turn timing instrumentation | Medium | 2 | task-work | 1 |
| TASK-VOPT-003 | Suppress FalkorDB index noise in logs | Low | 1 | direct | 1 |
| TASK-VOPT-004 | Full Run 4 with all tasks fresh (not resumed) | High | 1 | manual | 2 |

## Execution Strategy

**Wave 1** (parallel — no file conflicts):
- TASK-VOPT-001: Modifies `agent_invoker.py` (protocol generation)
- TASK-VOPT-002: Modifies `agent_invoker.py` (timing instrumentation) — separate functions
- TASK-VOPT-003: Modifies `graphiti_client.py` (log level)

**Wave 2** (depends on Wave 1):
- TASK-VOPT-004: Manual — run full fresh autobuild and record results
