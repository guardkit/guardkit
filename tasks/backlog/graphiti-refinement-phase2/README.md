# Feature: Graphiti Refinement Phase 2

**Feature ID**: FEAT-0F4A
**Parent Review**: TASK-REV-0CD7
**Architecture Score**: 78/100
**Total Estimate**: 79 hours (~64h wall-clock with parallelism)
**Prerequisites**: Phase 1 (MVP) must be complete

## Problem Statement

Phase 1 (MVP) established project namespacing, episode metadata, upsert logic, project seeding, and the add-context command. Phase 2 builds on this foundation to address remaining context loss issues:

- Manual context management during feature planning
- Knowledge gaps that require guessing
- No visibility into stored knowledge
- Generic context that wastes tokens or misses relevance
- No cross-turn learning in AutoBuild workflows

## Solution Approach

Implement 4 sub-features using **Parallel Tracks** approach:

### Wave 1: Foundation Features (Parallel)
- **FEAT-GR-003**: Feature Spec Integration (15h)
- **FEAT-GR-004**: Interactive Knowledge Capture (19h)

### Wave 2: Query Commands (Sequential)
- **FEAT-GR-005**: Knowledge Query Command (13h)

### Wave 3: Job-Specific Context (Sequential)
- **FEAT-GR-006**: Job-Specific Context Retrieval (32h)

## Expected Outcomes

1. Automatic feature spec context during `/feature-plan`
2. Interactive sessions to capture implicit knowledge
3. CLI commands to inspect and verify stored knowledge
4. Dynamic, job-specific context retrieval
5. Cross-turn learning via turn state tracking

## Sub-Features

| ID | Name | Estimate | Dependencies |
|----|------|----------|--------------|
| GR-003 | Feature Spec Integration | 15h | Phase 1 MVP |
| GR-004 | Interactive Knowledge Capture | 19h | Phase 1 MVP |
| GR-005 | Knowledge Query Command | 13h | GR-003, GR-004 |
| GR-006 | Job-Specific Context Retrieval | 32h | GR-005 |

## Task Summary

| Wave | Tasks | Total Hours | Mode |
|------|-------|-------------|------|
| Wave 1 | 17 | 34h | Parallel (GR-003 \|\| GR-004) |
| Wave 2 | 10 | 13h | Sequential |
| Wave 3 | 14 | 32h | Sequential |
| **Total** | **41** | **79h** | |

## Key Technical Decisions

1. **Feature Detection Strategy**: Regex pattern matching for FEAT-XXX IDs
2. **Knowledge Gap Analysis**: Question templates with field checking
3. **Turn State Storage**: Episodes in `turn_states` group
4. **Context Budget Calculation**: Dynamic allocation based on task characteristics
5. **AutoBuild Context Priority**: Dedicated allocations for role_constraints, quality_gate_configs, turn_states

## Success Criteria

- Feature ID auto-detected from descriptions
- Interactive Q&A captures missing knowledge
- Query commands show/search/list/status work
- Context varies by task characteristics
- Performance under 2 seconds per retrieval

## References

- [Feature Specification](../../../../docs/research/graphiti-refinement/FEATURE-SPEC-graphiti-refinement-phase2.md)
- [FEAT-GR-003 Detail](../../../../docs/research/graphiti-refinement/FEAT-GR-003-feature-spec-integration.md)
- [FEAT-GR-004 Detail](../../../../docs/research/graphiti-refinement/FEAT-GR-004-interactive-knowledge-capture.md)
- [FEAT-GR-005 Detail](../../../../docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md)
- [FEAT-GR-006 Detail](../../../../docs/research/graphiti-refinement/FEAT-GR-006-job-specific-context.md)
- [Architecture Review](../../../../.claude/reviews/TASK-REV-1505-review-report.md)
