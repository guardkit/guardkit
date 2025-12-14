# Feature: Unified Clarification Subagent

## Problem Statement

The clarifying questions feature has been fully implemented (~8,740 lines of code across 17 tasks) but is **dead code** because:
1. Python orchestrators exist but are never invoked by slash commands
2. `/task-work` has no clarification integration at all
3. The original wire-up approach (TASK-WC-001 through TASK-WC-003) used orchestrators with complex handoff issues

## Solution Approach

**Use a unified subagent pattern for ALL commands** (`/task-work`, `/feature-plan`, `/task-review`).

Create a single `clarification-questioner` agent that:
1. Handles all three clarification contexts (review_scope, implementation_prefs, implementation_planning)
2. Is invoked via Task tool at appropriate workflow points
3. Imports and uses existing `lib/clarification/*` Python code
4. Returns `ClarificationContext` to Claude for use in subsequent steps

## Benefits

- **No handoff complexity** - Agent returns context, Claude continues workflow
- **Unified architecture** - One pattern across all commands
- **Lower effort** - 6-8 hours vs 12-16 hours for orchestrator approach
- **Better maintainability** - Single clarification agent to maintain
- **Reuses existing code** - All ~3,451 lines of clarification code becomes functional

## Subtasks

| Task | Description | Mode | Priority | Wave |
|------|-------------|------|----------|------|
| TASK-WC-005 | Create clarification-questioner agent | task-work | High | 1 |
| TASK-WC-006 | Update task-work.md with subagent invocation | direct | High | 2 |
| TASK-WC-007 | Update feature-plan.md with subagent invocation | direct | High | 2 |
| TASK-WC-008 | Update task-review.md with subagent invocation | direct | High | 2 |
| TASK-WC-009 | Update installer to copy new agent | direct | Medium | 3 |
| TASK-WC-010 | Update guardkit init to include agent | direct | Medium | 3 |
| TASK-WC-011 | Update CLAUDE.md documentation | direct | Medium | 3 |
| TASK-WC-012 | Add integration smoke tests | task-work | Medium | 4 |

## Execution Strategy

### Wave 1 (No Dependencies)
- TASK-WC-005: Create clarification-questioner agent

### Wave 2 (Depends on Wave 1) - Parallel Execution
- TASK-WC-006: Update task-work.md
  - Conductor workspace: `unified-clarification-wave2-1`
- TASK-WC-007: Update feature-plan.md
  - Conductor workspace: `unified-clarification-wave2-2`
- TASK-WC-008: Update task-review.md
  - Conductor workspace: `unified-clarification-wave2-3`

### Wave 3 (Depends on Wave 1) - Parallel Execution
- TASK-WC-009: Update installer
  - Conductor workspace: `unified-clarification-wave3-1`
- TASK-WC-010: Update guardkit init
  - Conductor workspace: `unified-clarification-wave3-2`
- TASK-WC-011: Update documentation
  - Conductor workspace: `unified-clarification-wave3-3`

### Wave 4 (Depends on Waves 2 & 3)
- TASK-WC-012: Integration smoke tests

## Supersedes

The following tasks from TASK-REV-CLQ2 are **superseded**:

| Original Task | Original Purpose | Status |
|---------------|------------------|--------|
| TASK-WC-001 | Update feature-plan.md for orchestrator | **SUPERSEDED** by TASK-WC-007 |
| TASK-WC-002 | Update task-review.md for orchestrator | **SUPERSEDED** by TASK-WC-008 |
| TASK-WC-003 | Add orchestrator symlinks | **DELETED** (not needed) |
| TASK-WC-004 | Smoke test | **RENAMED** to TASK-WC-012 |

## Expected Outcome

After implementation:
- Clarifying questions will be displayed for ambiguous inputs
- ~15% reduction in incorrect assumptions
- ~8,740 lines of existing code becomes functional
- Consistent architecture across all commands

## Related

- **Decision Review**: TASK-REV-CLQ3
- **Review Report**: [.claude/reviews/TASK-REV-CLQ3-review-report.md](../../../.claude/reviews/TASK-REV-CLQ3-review-report.md)
- **Technical Debt Review**: TASK-REV-CLQ2
- **Original Implementation**: TASK-CLQ-001 through TASK-CLQ-012

## Generated

- Date: 2025-12-13
- Method: `/task-review TASK-REV-CLQ3` → [R]evise → [I]mplement
- Estimated Effort: 6-8 hours total
