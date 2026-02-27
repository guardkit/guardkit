# vLLM AutoBuild Run 2 Fixes (FEAT-FF93)

Targeted fixes for Wave 3 failures identified in the vLLM/Qwen3 autobuild run 2 on Dell GB10.

**Parent Review**: [TASK-REV-5610](../TASK-REV-5610-analyse-vllm-qwen3-db-autobuild-run2.md)
**Review Report**: [.claude/reviews/TASK-REV-5610-review-report.md](../../../.claude/reviews/TASK-REV-5610-review-report.md)

## Context

Run 2 improved from 2/8 to 5/8 tasks (Waves 1-2 fully passing) after applying timeout multiplier and text-matching fixes from run 1. Wave 3 failed with 3 new issues requiring surgical fixes.

## Tasks

| # | Task | Priority | Status |
|---|------|----------|--------|
| 1 | [TASK-FIX-6141](TASK-FIX-6141-fix-ac-search-path.md) — Fix AC search path | P0 | Backlog |
| 2 | [TASK-FIX-7718](TASK-FIX-7718-sdk-turn-budget-local.md) — SDK turn budget | P0 | Backlog |
| 3 | [TASK-FIX-CDF8](TASK-FIX-CDF8-fix-cancelled-error-display.md) — Fix error display | P1 | Backlog |
| 4 | [TASK-FIX-46F2](TASK-FIX-46F2-vllm-streaming-retry.md) — Streaming retry | P1 | Backlog |
| 5 | [TASK-FIX-DF01](TASK-FIX-DF01-wave-parallelism-config.md) — Wave parallelism | P2 | Backlog |

## Execution

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for wave breakdown and architecture constraints.

**Minimum viable fix**: Wave 1 only (TASK-FIX-6141 + TASK-FIX-7718) — predicted to enable 7-8/8 task completion on run 3.
