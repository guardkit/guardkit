# Feature: Graphiti Refinement MVP

## Overview

Enhance Graphiti integration to support project-specific knowledge seeding, job-specific context retrieval, and cross-session learning from AutoBuild lessons.

**Parent Review**: TASK-REV-1505 (Architecture Score: 78/100)
**Feature Spec**: `docs/research/graphiti-refinement/FEATURE-SPEC-graphiti-refinement-mvp.md`

## Problem Solved

- Context loss across sessions (50-70% of time re-learning architecture)
- Repeated mistakes (~40% of issues)
- No "big picture" visibility during development
- Player-Coach role reversal
- Quality gate threshold drift

## Expected Outcomes

- 25-40% reduction in Phase 2 context size
- 55-60% reduction in time re-learning architecture
- 75% reduction in repeated mistakes
- 50-70% faster time to first success

## Subtasks

### Phase 0: Seeding Update (6h)

| Task ID | Title | Mode | Wave | Complexity |
|---------|-------|------|------|------------|
| TASK-GR-PRE-000-A | Add metadata block to existing seeding episodes | task-work | 1 | 4 |
| TASK-GR-PRE-000-B | Add guardkit graphiti clear command | task-work | 1 | 3 |
| TASK-GR-PRE-000-C | Add tests and documentation for seeding update | direct | 2 | 2 |

### Phase 1: Foundation (27h)

| Task ID | Title | Mode | Wave | Complexity |
|---------|-------|------|------|------------|
| TASK-GR-PRE-001-A | Add project_id to GraphitiClient | task-work | 3 | 3 |
| TASK-GR-PRE-001-B | Implement group ID prefixing | task-work | 3 | 4 |
| TASK-GR-PRE-001-C | Add project initialization logic | task-work | 4 | 4 |
| TASK-GR-PRE-001-D | Tests and documentation for project namespace | direct | 4 | 3 |
| TASK-GR-PRE-002-A | Define standard metadata fields | task-work | 3 | 3 |
| TASK-GR-PRE-002-B | Create EpisodeMetadata dataclass | task-work | 3 | 3 |
| TASK-GR-PRE-002-C | Update add_episode to include metadata | task-work | 4 | 3 |
| TASK-GR-PRE-002-D | Tests and documentation for episode metadata | direct | 4 | 2 |
| TASK-GR-PRE-003-A | Research graphiti-core upsert capabilities | manual | 3 | 3 |
| TASK-GR-PRE-003-B | Implement episode_exists method | task-work | 4 | 3 |
| TASK-GR-PRE-003-C | Implement upsert_episode logic | task-work | 5 | 5 |
| TASK-GR-PRE-003-D | Tests and documentation for upsert | direct | 5 | 3 |

### Phase 2: Core Functionality (39h)

| Task ID | Title | Mode | Wave | Complexity |
|---------|-------|------|------|------------|
| TASK-GR-001-A | Add project-specific group IDs to config | task-work | 6 | 2 |
| TASK-GR-001-B | Create ProjectOverviewEpisode schema | task-work | 6 | 3 |
| TASK-GR-001-C | Create ProjectArchitectureEpisode schema | task-work | 6 | 2 |
| TASK-GR-001-D | Create RoleConstraintsEpisode and seed defaults | task-work | 6 | 3 |
| TASK-GR-001-E | Create QualityGateConfigEpisode and seed defaults | task-work | 6 | 3 |
| TASK-GR-001-F | Create ImplementationModeEpisode and seed defaults | task-work | 6 | 2 |
| TASK-GR-001-G | Implement CLAUDE.md/README.md parsing | task-work | 7 | 4 |
| TASK-GR-001-H | Add project seeding to guardkit init | task-work | 7 | 4 |
| TASK-GR-001-I | Implement optional interactive setup | task-work | 8 | 3 |
| TASK-GR-002-A | Create parser registry infrastructure | task-work | 6 | 4 |
| TASK-GR-002-B | Implement FeatureSpecParser | task-work | 7 | 4 |
| TASK-GR-002-C | Implement ADRParser | task-work | 7 | 3 |
| TASK-GR-002-D | Implement ProjectOverviewParser | task-work | 7 | 3 |
| TASK-GR-002-E | Add guardkit graphiti add-context CLI command | task-work | 8 | 4 |
| TASK-GR-002-F | Add --type, --force, --dry-run flags | task-work | 8 | 3 |
| TASK-GR-002-G | Tests for parsers | task-work | 9 | 4 |
| TASK-GR-002-H | Tests for CLI command | task-work | 9 | 3 |
| TASK-GR-002-I | Documentation for context addition | direct | 9 | 3 |

## Dependencies

- graphiti-core library (existing)
- Neo4j database (existing)
- OPENAI_API_KEY (existing)

## Success Criteria

### Phase 0 Complete
- [ ] All existing seeding episodes include `_metadata` block
- [ ] `guardkit graphiti clear --confirm` works
- [ ] `guardkit graphiti clear --system-only --confirm` works

### Phase 1 Complete
- [ ] Projects can be initialized with unique namespace
- [ ] Group IDs are correctly prefixed (e.g., `youtube-mcp__feature_specs`)
- [ ] Episodes include standard metadata
- [ ] Upsert logic handles duplicates correctly

### Phase 2 Complete
- [ ] `guardkit init` seeds project knowledge
- [ ] Role constraints, quality gate configs, implementation modes seeded
- [ ] `guardkit graphiti add-context` parses and seeds files
- [ ] Feature specs can be queried during `/feature-plan`

## Testing Strategy

### Unit Tests
- Episode schema serialization/deserialization
- Parser output validation
- Group ID prefixing logic
- Metadata extraction

### Integration Tests
- Full init workflow with Graphiti seeding
- add-context command with various file types
- Search and retrieval of seeded knowledge

### Manual Verification
```bash
guardkit graphiti clear --confirm
guardkit graphiti seed
guardkit init --template fastmcp-python --project-name test-project
guardkit graphiti add-context --type project-overview CLAUDE.md
guardkit graphiti status
guardkit graphiti search "test-project overview"
```

## References

- [Feature Specification](../../../docs/research/graphiti-refinement/FEATURE-SPEC-graphiti-refinement-mvp.md)
- [Architecture Review Report](../../../.claude/reviews/TASK-REV-1505-review-report.md)
- [Gap Analysis](../../../docs/research/graphiti-refinement/FEAT-GR-000-gap-analysis.md)
