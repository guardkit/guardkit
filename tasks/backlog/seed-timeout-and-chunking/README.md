# Feature: Seed Timeout & Chunking Optimisation

**Parent Review**: TASK-REV-95B1
**Feature ID**: FEAT-seed-timeout-chunking
**Created**: 2026-03-06

## Problem

After template filter success (62.5% time reduction), the remaining seed run (98m 40s, 70/78 episodes) still has 8 timeout failures and one episode (`guardkit_purpose`) taking 151.6s. The timeout budget was previously raised (TASK-FIX-b94e) but episodes are still hitting the new ceilings.

## Solution

Two P1 tasks:
1. Raise timeout ceilings again for chronic failures (recover 5+ of 8 skips)
2. Chunk the `guardkit_purpose` episode into smaller focused episodes

## Subtasks

| Task | Description | Wave | Method |
|------|-------------|------|--------|
| TASK-FIX-7A01 | Raise episode timeouts (round 2) | 1 | task-work |
| TASK-OPT-3B02 | Chunk guardkit_purpose episode | 1 | task-work |

## Execution Strategy

Both tasks are independent and can be executed in parallel (Wave 1).
Verify with a seed run after both are complete.
