# FEAT-GIP: Graphiti Init Performance

## Problem

After FEAT-SPR delivered +64% rules improvement and +17% overall seeding success, two performance issues remain:

1. **Episode 1 (project_purpose)**: Fragile — 254.4s with a 300s timeout ceiling (85% utilisation)
2. **Episode 3 (tech_stack)**: Structural slowdown from ~99s to ~249s (2.5x), reproducible across vLLM states
3. **Agents**: 9/18 still timeout at 150s despite improvement from 6/18

## Solution

Pragmatic timeout adjustments (Wave 1+2) plus structured investigation of the Episode 3 step change.

## Tasks

| ID | Title | Wave | Priority | Status |
|----|-------|------|----------|--------|
| TASK-FIX-cc7e | Increase project_purpose timeout to 600s | 1 | High | Backlog |
| TASK-INV-7c71 | Investigate Episode 3 structural slowdown | 1 | Medium | Backlog |
| TASK-OPS-64fe | Close FEAT-SPR as delivered | 1 | Medium | Backlog |
| TASK-FIX-303e | Raise agent timeout to 240s | 2 | Low | Backlog |

## Source

Created from [TASK-REV-8A31](../TASK-REV-8A31-review-reseed-guardkit-3-init-project-12.md) review recommendations.
