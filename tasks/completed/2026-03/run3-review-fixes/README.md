# FEAT-RFX: Run 3 Review Fixes

**Feature ID**: FEAT-RFX
**Parent Review**: [TASK-REV-A8C6](../../backlog/TASK-REV-A8C6-analyse-run3-success-youtube-transcript-mcp.md)
**Review Report**: [.claude/reviews/TASK-REV-A8C6-review-report.md](../../../.claude/reviews/TASK-REV-A8C6-review-report.md)
**Status**: 5/9 tasks complete

## Summary

Fixes and improvements identified from the TASK-REV-A8C6 architectural review of AutoBuild Run 3 (youtube-transcript-mcp FEAT-2AAA). Run 3 succeeded (5/5 tasks, 27m 51s) but exposed four systemic issues requiring attention: CancelledError in direct-mode invocations, non-functional cross-turn Graphiti learning, invisible command execution failures in Coach feedback, and stale task tracking.

## Tasks

| Wave | Task ID | Title | Priority | Complexity | Mode | Status |
|------|---------|-------|----------|-----------|------|--------|
| 1 | TASK-RFX-5E37 | Clean up stale CRV task files | high | 1 | direct | **complete** |
| 1 | TASK-RFX-BAD9 | Normalize pip to sys.executable -m pip | high | 2 | direct | **complete** |
| 1 | TASK-RFX-C9D9 | Deprioritise CRV-B275 and CRV-7DBC | low | 1 | direct | **complete** |
| 2 | TASK-RFX-8332 | Fix CancelledError via explicit gen.aclose() | high | 5 | task-work | **complete** |
| 2 | TASK-RFX-5FED | Local file-based turn state capture | high | 5 | task-work | **complete** |
| 3 | TASK-RFX-528E | Coach criteria soft gate Phase 1 | medium | 3 | task-work | backlog |
| 3 | TASK-RFX-F7F5 | Coach criteria soft gate Phase 2 | medium | 6 | task-work | backlog |
| 4 | TASK-RFX-7C63 | Extended CoachValidator (CRV-9914) | medium | 6 | task-work | backlog |
| 4 | TASK-RFX-B20B | SDK session resume (CRV-3B1A) | medium | 7 | task-work | backlog |

## Key Decisions

- **Turn state capture**: Option E (local file-based) selected over Graphiti-dependent approaches
- **Coach criteria policy**: Option B (Soft Gate) -- failure classifier + advisory injection, no threshold changes
- **CancelledError strategy**: Short-term fix (explicit gen.aclose()) in Wave 2, long-term fix (SDK session resume) in Wave 4

## Getting Started

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for wave breakdown, dependency graph, and execution strategy.
