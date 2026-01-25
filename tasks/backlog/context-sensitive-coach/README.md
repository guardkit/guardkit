# Feature: Context-Sensitive Coach

## Overview

Implements an AI-powered context-sensitive CoachValidator that adapts quality gate thresholds based on what was actually implemented, rather than applying fixed thresholds based solely on task_type.

**Problem**: The current quality gate system is binary - a 20-line Pydantic model faces the same 60-point arch review threshold and 80% coverage requirement as a 500-line authentication system. This causes simple, legitimate implementations to fail.

**Solution**: Use AI-based context analysis (no plugins required) to understand what code was implemented and select appropriate validation profiles dynamically.

## Key Design Decisions

1. **AI-First Approach**: Uses AI to analyze implementation context instead of language-specific plugins
2. **Zero Plugin Overhead**: No need to create/maintain plugins for each language/framework
3. **Fast Classification Gate**: Trivial and obvious cases bypass AI analysis entirely
4. **Caching**: AI analysis cached between turns for performance

## Architecture

```
Universal Context (Tier 1) → Fast Classification Gate
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                Trivial         Uncertain        Complex
               (<30 LOC)       (30-300 LOC)     (>300 LOC)
                    │               │               │
                    ▼               ▼               ▼
               MINIMAL          AI Analysis       STRICT
               profile              │             profile
                                    ▼
                            Dynamic Profile
                              Selection
```

## Subtasks

| Task ID | Title | Wave | Mode | Complexity |
|---------|-------|------|------|------------|
| TASK-CSC-001 | Create data models and universal context gatherer | 1 | task-work | 4 |
| TASK-CSC-002 | Implement fast classification gate | 1 | task-work | 3 |
| TASK-CSC-003 | Implement AI context analysis | 2 | task-work | 5 |
| TASK-CSC-004 | Implement context caching | 2 | task-work | 4 |
| TASK-CSC-005 | Integrate with existing CoachValidator | 3 | task-work | 5 |
| TASK-CSC-006 | Add unit and integration tests | 4 | task-work | 4 |
| TASK-CSC-007 | Update documentation and proposal | 4 | direct | 2 |

## Dependencies

- Internal: `guardkit/orchestrator/quality_gates/coach_validator.py`
- Internal: `guardkit/models/task_types.py`
- External: None (uses existing AI infrastructure)

## References

- **Original Proposal**: `docs/research/context-sensitive-coach-proposal.md`
- **Review Task**: TASK-REV-CSC1
- **Parent Review**: TASK-REV-FB22 (identified the root cause)
