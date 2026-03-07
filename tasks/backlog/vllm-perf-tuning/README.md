# vLLM Performance Tuning (FEAT-VPT1)

Performance tuning for vLLM autobuild runs on Dell ProMax GB10, based on profiling data from FEAT-1637.

**Parent Review**: [TASK-REV-5E93](../TASK-REV-5E93-review-vllm-performance-context-retrieval.md)
**Review Report**: [.claude/reviews/TASK-REV-5E93-review-report.md](../../../.claude/reviews/TASK-REV-5E93-review-report.md)

## Context

Profiling of the FEAT-1637 autobuild run revealed that parallel execution (max_parallel=2) causes a 4.3x throughput penalty on single-GPU hardware, and that several default values are suboptimal for local backends.

**Previously completed** (from this review):
- TASK-FIX-GCW6: Graphiti factory singleton init — **COMPLETED**
- TASK-FIX-7718: SDK turn budget for local models — **COMPLETED**
- CancelledError fix — **COMPLETED**

## Tasks

| # | Task | Priority | Status | Complexity |
|---|------|----------|--------|------------|
| 1 | [TASK-VPT-001](TASK-VPT-001-tune-local-backend-defaults.md) — Tune local backend defaults | High | Backlog | 1 |
| 2 | [TASK-VPT-002](TASK-VPT-002-reduce-embedding-gpu-reservation.md) — Reduce embedding GPU | Low | Backlog | 1 |

## Execution

Both tasks are independent and can run in parallel. Both are "direct" mode (trivial value changes).

**Expected outcome**: ~40 minutes saved per autobuild run (eliminating parallel throughput penalty), plus improved SDK turn headroom and more appropriate timeout scaling.
