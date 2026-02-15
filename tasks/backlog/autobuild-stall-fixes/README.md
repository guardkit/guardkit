# FEAT-ASF: AutoBuild Stall Fixes

## Source

- Review: [TASK-REV-SFT1-review-report.md](../../../.claude/reviews/TASK-REV-SFT1-review-report.md)
- Diagnostic Diagrams: [autobuild-diagnostic-diagrams.md](../../../docs/reviews/feature-build/autobuild-diagnostic-diagrams.md)
- Stall Log: [stall_1.md](../../../docs/reviews/seam_first_testing/stall_1.md)

## Problem Statement

The FEAT-AC1A autobuild failed due to 6 compounding root causes that turned a complexity-2 scaffolding task (TASK-SFT-001) into an unrecoverable 45-minute stall. Diagrammatic analysis surfaced 5 additional issues including ghost thread interference across features, false approval risk from fix interactions, and cancellation checkpoint gaps.

## Solution Approach

8 tasks across 4 phases, ordered by risk and dependency:

| Phase | Risk | Tasks | Focus |
|-------|------|-------|-------|
| 1 | Zero | ASF-001, ASF-002 | Unblock re-run (config + pre-flight) |
| 2 | Low | ASF-003, ASF-004 | Fix feedback loop + add observability |
| 3 | Medium | ASF-005, ASF-006 | Fix detection (ordered: R5 before R4-full) |
| 4 | Medium-High | ASF-007, ASF-008 | Fix lifecycle (thread cancellation + timeout) |

## Phased Execution Plan

### Phase 1: Unblock Re-Run (0 risk, ~10 minutes)

| Task | Type | Complexity | Description |
|------|------|------------|-------------|
| TASK-ASF-001 | configuration | 1 | Switch SFT-001 to direct mode |
| TASK-ASF-002 | feature | 2 | Add FalkorDB pre-flight check |

### Phase 2: Fix Feedback Loop (low risk)

| Task | Type | Complexity | Description |
|------|------|------------|-------------|
| TASK-ASF-003 | bugfix | 3 | Include missing_criteria in feedback text |
| TASK-ASF-004 | feature | 2 | Add synthetic report observability (R4-lite) |

### Phase 3: Fix Detection (medium risk, order matters)

| Task | Type | Complexity | Depends On | Description |
|------|------|------------|------------|-------------|
| TASK-ASF-005 | bugfix | 4 | ASF-003, ASF-004 | Scope test detection to task paths |
| TASK-ASF-006 | feature | 5 | **ASF-005** | Enrich synthetic reports (R4-full) |

**CRITICAL**: ASF-005 must be complete before ASF-006. See interaction risk in IMPLEMENTATION-GUIDE.md.

### Phase 4: Fix Lifecycle (medium-high risk)

| Task | Type | Complexity | Description |
|------|------|------------|-------------|
| TASK-ASF-007 | feature | 6 | Cooperative thread cancellation |
| TASK-ASF-008 | feature | 3 | Dynamic SDK timeout |

## Root Cause → Fix Mapping

| Finding | Severity | Fix Task(s) |
|---------|----------|-------------|
| F1: Zero-message SDK timeouts | Critical | ASF-001 (immediate), ASF-008 (systemic) |
| F2: Synthetic reports unapprovable | Critical | ASF-004 (observability), ASF-006 (enrichment) |
| F3: Test detection unscoped | High | ASF-005 |
| F4: Feedback loses specificity | High | ASF-003 |
| F5: Thread cannot be cancelled | High | ASF-007 |
| F6: Graphiti connection errors | Medium | ASF-002 |
| Q8: Ghost thread interference | High | ASF-002 + ASF-007 |

## Newly Identified Issues (from Diagnostic Diagrams)

1. **Ghost thread interference (Q8)** — Ghost threads from failed features hit Graphiti and consume API credits when subsequent features launch
2. **R4+R5 false approval risk** — File-existence promises + worktree-wide tests = false approvals. Fix: R5 before R4-full
3. **R4 phasing** — Synthetic report structure change is medium-risk; split into R4-lite (logging) and R4-full (enrichment)
4. **Cancellation checkpoint gap** — Cancellation must check in both Player and Coach phases, not just loop top
5. **No fast-fail for synthetic reports** — Synthetic reports always fail promise matching; add fast-fail to skip it
