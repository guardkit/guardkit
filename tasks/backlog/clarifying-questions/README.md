# Feature: Clarifying Questions in GuardKit Commands

## Overview

Add a unified clarification questions system to GuardKit that asks users targeted questions before making assumptions. This applies to three commands:

- **`/task-work`** - Ask about scope, technology choices, trade-offs before implementation planning
- **`/task-review`** - Ask about review focus, priorities before analysis
- **`/feature-plan`** - Inherits clarifications from task-review + adds implementation preferences

## Why This Matters

**Current State**: AI makes assumptions during planning, leading to ~20% rework rate when assumptions don't match user intent.

**Future State**: AI asks clarifying questions, reducing rework to ~5% and improving implementation accuracy to ~95%.

## Inspiration Sources

1. **Anthropic's feature-dev plugin** - Explicit Phase 3 "Clarifying Questions" that blocks until user responds
2. **RequireKit's gather-requirements** - 5W1H framework (What/Who/When/Where/Why/How)
3. **GuardKit's existing checkpoints** - Phase 2.7/2.8 complexity checkpoint patterns

## Three Clarification Contexts

| Context | Command(s) | When | Purpose |
|---------|------------|------|---------|
| **A: Review Scope** | `/task-review`, `/feature-plan` | Before analysis | Guide what to analyze |
| **B: Implementation Prefs** | `/feature-plan` [I]mplement | Before subtask creation | Guide approach & constraints |
| **C: Implementation Planning** | `/task-work` | Before planning (Phase 1.5) | Guide scope, tech, trade-offs |

## Architecture

```
installer/global/commands/lib/clarification/
├── __init__.py              # Module exports
├── core.py                  # Shared: ClarificationContext, Decision, Question
├── detection.py             # Shared: Ambiguity detection functions
├── display.py               # Shared: UI formatting (full/quick/skip)
├── templates/
│   ├── review_scope.py          # Context A questions
│   ├── implementation_prefs.py  # Context B questions
│   └── implementation_planning.py # Context C questions
└── generators/
    ├── review_generator.py      # For task-review
    ├── implement_generator.py   # For [I]mplement
    └── planning_generator.py    # For task-work Phase 1.5
```

## Complexity Gating

Questions are complexity-gated to avoid fatigue:

| Complexity | task-work | task-review | feature-plan |
|------------|-----------|-------------|--------------|
| 1-2 | Skip | Skip | Skip |
| 3-4 | Quick (15s timeout) | Skip | Quick |
| 5-6 | Full (blocking) | Quick | Full |
| 7+ | Full (blocking) | Full | Full |

## Command-Line Flags

All commands support:
- `--no-questions` - Skip clarification entirely
- `--with-questions` - Force clarification even for simple tasks
- `--defaults` - Use defaults without prompting
- `--answers="1:Y 2:N 3:JWT"` - Inline answers for automation

## Related Resources

- **Review Report**: [.claude/reviews/TASK-REV-B130-review-report.md](../../../.claude/reviews/TASK-REV-B130-review-report.md)
- **Original Review Task**: [TASK-REV-B130](../TASK-REV-B130-clarifying-questions-in-task-work.md)

## Subtasks

| Task ID | Title | Method | Wave |
|---------|-------|--------|------|
| TASK-CLQ-001 | Create clarification module core | /task-work | 1 |
| TASK-CLQ-002 | Create detection algorithms | /task-work | 1 |
| TASK-CLQ-003 | Create display formatting | Direct | 1 |
| TASK-CLQ-004 | Create Context C templates (task-work) | /task-work | 2 |
| TASK-CLQ-005 | Create Context A templates (task-review) | Direct | 2 |
| TASK-CLQ-006 | Create Context B templates (feature-plan) | Direct | 2 |
| TASK-CLQ-007 | Integrate into task-work.md | /task-work | 3 |
| TASK-CLQ-008 | Integrate into task-review.md | /task-work | 3 |
| TASK-CLQ-009 | Integrate into feature-plan.md | Direct | 3 |
| TASK-CLQ-010 | Implement persistence & audit trail | Direct | 4 |
| TASK-CLQ-011 | Update documentation (CLAUDE.md) | Direct | 4 |
| TASK-CLQ-012 | Testing & user acceptance | /task-work | 4 |

## Estimated Effort

| Phase | Effort | Conductor Workspaces |
|-------|--------|---------------------|
| Wave 1: Core Module | 2 days | 3 parallel |
| Wave 2: Templates | 1 day | 3 parallel |
| Wave 3: Integration | 2 days | 3 parallel |
| Wave 4: Polish | 1 day | 3 parallel |
| **Total** | **6 days** | Max 3 concurrent |

## Getting Started

See [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) for detailed execution instructions.
