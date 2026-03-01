# Feature: System Architecture & Design Commands

## Problem Statement

GuardKit's `/system-plan` and `/feature-spec` commands currently operate without explicit upstream architecture context. When developers run `/system-plan` on a new project, the command asks foundational architecture questions (bounded contexts, technology stack, structural pattern) that should have been captured once and persisted — not re-asked every session. Similarly, `/feature-spec` generates Gherkin scenarios that reference assumed domain entities and API endpoints rather than real ones from an explicit design.

This gap leads to:
- Repeated architecture explanations across sessions
- Assumed domain models that drift from actual implementation
- Feature specs with low-confidence assumptions about API contracts
- No structured mechanism to refine architectural decisions with impact analysis

## Solution

Four new commands that sit upstream of `/system-plan` in the pipeline:

| Command | Purpose | Depends On |
|---------|---------|------------|
| `/system-arch` | Establish system-level architecture decisions, generate C4 L1+L2 diagrams | None (entry point) |
| `/system-design` | Design API contracts, data models, and multi-protocol surfaces per bounded context | `/system-arch` |
| `/arch-refine` | Iteratively refine architecture decisions with temporal superseding and impact analysis | `/system-arch` |
| `/design-refine` | Iteratively refine design decisions with feature spec staleness detection | `/system-design` |

**Pipeline**: `/system-arch` -> `/system-design` -> `/system-plan` -> `/feature-spec` -> `/feature-plan`

## Subtask Summary

| Task | Title | Wave | Complexity | Mode |
|------|-------|------|------------|------|
| TASK-SAD-001 | Temporal superseding spike | 1 | 4 | task-work |
| TASK-SAD-002 | Update ArchitectureDecision dataclass | 1 | 3 | task-work |
| TASK-SAD-003 | Create design entity dataclasses | 1 | 5 | task-work |
| TASK-SAD-004 | Update ADR template + create new templates | 2 | 5 | task-work |
| TASK-SAD-005 | Create SystemDesignGraphiti + DesignWriter | 2 | 6 | task-work |
| TASK-SAD-006 | /system-arch command spec | 3 | 8 | task-work |
| TASK-SAD-007 | /system-design command spec | 3 | 8 | task-work |
| TASK-SAD-008 | /arch-refine command spec | 3 | 7 | task-work |
| TASK-SAD-009 | /design-refine command spec | 3 | 6 | task-work |
| TASK-SAD-010 | Integration testing | 4 | 5 | task-work |

## Key Decisions

1. **ADR location**: `docs/architecture/decisions/` (match existing code convention)
2. **DDR location**: `docs/design/decisions/` (parallel convention)
3. **ADR prefix**: Parametrised (`"ARCH"` for /system-arch, `"SP"` default)
4. **Temporal superseding**: Data-level Option A (spike determines mechanism)
5. **C4 Mermaid syntax**: Native C4 keywords for new templates
6. **OpenAPI validation**: Quality gate in /system-design

## Review

Original review: [TASK-REV-AEE1](../TASK-REV-AEE1-plan-system-architecture-design-commands.md)
Full report: [.claude/reviews/TASK-REV-AEE1-review-report.md](../../../.claude/reviews/TASK-REV-AEE1-review-report.md)
BDD spec: [features/system-arch-design-commands/](../../../features/system-arch-design-commands/)
