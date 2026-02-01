# Feature: Feature-Build UX Improvements

**Feature ID**: FEAT-FB-UX
**Parent Review**: [TASK-REV-FBA1](.claude/reviews/TASK-REV-FBA1-review-report.md)
**Created**: 2025-01-31

## Problem Statement

When running `/feature-build` via Claude Code, users experience poor UX:

1. **No progress feedback** - Bash tool buffers output, user sees nothing for 5-15 minutes
2. **TTY-dependent display** - Rich library spinners/progress bars fail silently in non-TTY context
3. **Timeout confusion** - Bash tool 120s default kills long-running builds

## Strategic Vision

This feature implements a **phased approach** toward event-driven agent orchestration, informed by the Reachy PA architecture:

```
Phase 1 (Now)     Phase 2 (Q1)           Phase 3 (Q2)
─────────────     ─────────────          ─────────────
File polling  →   NATS events      →     Multi-interface
TTY fallback  →   guardkit watch   →     Web dashboard
                  MCP bridge       →     A2A semantics
                                         Reachy voice
```

## Target Architecture (Phase 3)

```
┌─────────────────────────────────────────────────────────────────┐
│                     NATS Message Bus (A2A Semantics)             │
└──────────────────────────┬───────────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │          │           │           │          │
    ▼          ▼           ▼           ▼          ▼
 CLI       Web UI      Claude      Reachy     Mobile
(watch)   (React)    (MCP Bridge) (Voice)    (Future)
```

## Phase 1 Tasks (Current)

| ID | Title | Mode | Wave | Status |
|----|-------|------|------|--------|
| TASK-FB-001 | TTY detection in ProgressDisplay | direct | 1 | backlog |
| TASK-FB-002 | Simple text output fallback | task-work | 1 | backlog |
| TASK-FB-003 | Progress file writer | task-work | 1 | backlog |
| TASK-FB-004 | /feature-build polling integration | task-work | 2 | backlog |
| TASK-FB-005 | Timeout documentation update | direct | 2 | backlog |
| TASK-FB-006 | --timeout flag passthrough | direct | 2 | backlog |

### Wave Execution Order

**Wave 1** (can run in parallel):
- TASK-FB-001: TTY detection (foundation)
- TASK-FB-002: Text fallback (depends on FB-001)
- TASK-FB-003: Progress file (depends on FB-001)

**Wave 2** (depends on Wave 1):
- TASK-FB-004: Polling integration (depends on FB-002, FB-003)
- TASK-FB-005: Timeout docs (independent)
- TASK-FB-006: Timeout flag (depends on FB-005)

## Phase 2 Tasks (Q1 - Future)

| ID | Title | Mode | Effort |
|----|-------|------|--------|
| TASK-FB-010 | Add NATS JetStream integration | task-work | Medium |
| TASK-FB-011 | Publish turn status events | task-work | Medium |
| TASK-FB-012 | `guardkit watch FEAT-XXX` CLI subscriber | task-work | Medium |
| TASK-FB-013 | Approval request/response via NATS | task-work | Medium |
| TASK-FB-014 | MCP bridge for Claude Code integration | task-work | High |

## Phase 3 Tasks (Q2 - Future)

| ID | Title | Mode | Effort |
|----|-------|------|--------|
| TASK-FB-020 | Web dashboard (React + WebSocket) | task-work | High |
| TASK-FB-021 | Voice notifications (Reachy integration) | task-work | Medium |
| TASK-FB-022 | Adopt A2A message semantics | task-work | Medium |
| TASK-FB-023 | Multi-project build orchestration | task-work | High |
| TASK-FB-024 | Priority-based interruption | task-work | Medium |

## Success Metrics

### Phase 1 (Immediate)

| Metric | Current | Target |
|--------|---------|--------|
| User sees progress during build | No | Yes (polled) |
| Time to first feedback | >5 min | <60s |
| Non-TTY output quality | Poor | Acceptable |

### Phase 2 (Q1)

| Metric | Current | Target |
|--------|---------|--------|
| Real-time progress updates | No | Yes (<100ms) |
| Multiple interface support | 1 | 3 (terminal, Claude, watch) |
| Human checkpoint handling | Manual | Event-driven |

### Phase 3 (Q2)

| Metric | Current | Target |
|--------|---------|--------|
| Web dashboard | No | Yes |
| Multi-project orchestration | No | Yes |
| A2A compatibility | No | Yes |

## Architecture References

- **Reachy PA**: Event-driven orchestration patterns
- **NATS JetStream**: Message bus with persistence
- **A2A Protocol**: Linux Foundation agent interoperability standard
- **FastStream**: Python framework for broker-agnostic messaging

## Related Documents

- [Review Report](.claude/reviews/TASK-REV-FBA1-review-report.md)
- [Previous Review (BAF6)](.claude/reviews/TASK-REV-BAF6-review-report.md)
- [AutoBuild Documentation](.claude/rules/autobuild.md)
- [Feature-Build Command](installer/core/commands/feature-build.md)
