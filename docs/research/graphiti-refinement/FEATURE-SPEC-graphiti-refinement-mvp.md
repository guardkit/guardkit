# Feature Specification: Graphiti Refinement MVP

> **For**: `/feature-plan` command
> **Status**: Ready for Implementation
> **Reviewed**: TASK-REV-1505 (2026-01-30)
> **Architecture Score**: 78/100

---

## Feature Overview

Enhance Graphiti integration to support project-specific knowledge seeding, job-specific context retrieval, and cross-session learning from AutoBuild lessons.

**Problem Solved**:
- Context loss across sessions (50-70% of time re-learning architecture)
- Repeated mistakes (~40% of issues)
- No "big picture" visibility during development
- Player-Coach role reversal
- Quality gate threshold drift

**Expected Outcomes**:
- 25-40% reduction in Phase 2 context size
- 55-60% reduction in time re-learning architecture
- 75% reduction in repeated mistakes
- 50-70% faster time to first success

---

## MVP Scope

**Total Estimate**: 72 hours (~9 days)

### Phase 0: Seeding Update (6h)

| Task | Description | Estimate |
|------|-------------|----------|
| PRE-000-A | Add `_metadata` block to existing seeding episodes | 3h |
| PRE-000-B | Add `guardkit graphiti clear` command | 2h |
| PRE-000-C | Add tests and documentation | 1h |

### Phase 1: Foundation (27h)

| Task | Description | Estimate |
|------|-------------|----------|
| PRE-001-A | Add project_id to GraphitiClient | 2h |
| PRE-001-B | Implement group ID prefixing | 3h |
| PRE-001-C | Add project initialization logic | 3h |
| PRE-001-D | Tests and documentation | 2h |
| PRE-002-A | Define standard metadata fields | 2h |
| PRE-002-B | Create EpisodeMetadata dataclass | 2h |
| PRE-002-C | Update add_episode to include metadata | 2h |
| PRE-002-D | Tests and documentation | 1h |
| PRE-003-A | Research graphiti-core upsert capabilities | 2h |
| PRE-003-B | Implement episode_exists method | 2h |
| PRE-003-C | Implement upsert_episode (or invalidate+create) | 4h |
| PRE-003-D | Tests and documentation | 2h |

### Phase 2: Core Functionality (39h)

| Task | Description | Estimate |
|------|-------------|----------|
| GR-001-A | Add project-specific group IDs to config | 1h |
| GR-001-B | Create ProjectOverviewEpisode schema | 2h |
| GR-001-C | Create ProjectArchitectureEpisode schema | 1h |
| GR-001-D | **NEW**: Create RoleConstraintsEpisode + seed defaults | 2h |
| GR-001-E | **NEW**: Create QualityGateConfigEpisode + seed defaults | 2h |
| GR-001-F | **NEW**: Create ImplementationModeEpisode + seed defaults | 1h |
| GR-001-G | Implement CLAUDE.md/README.md parsing | 2h |
| GR-001-H | Add project seeding to `guardkit init` | 3h |
| GR-001-I | Implement optional interactive setup | 2h |
| GR-002-A | Create parser registry infrastructure | 2h |
| GR-002-B | Implement FeatureSpecParser | 3h |
| GR-002-C | Implement ADRParser | 2h |
| GR-002-D | Implement ProjectOverviewParser | 2h |
| GR-002-E | Add `guardkit graphiti add-context` CLI command | 3h |
| GR-002-F | Add --type, --force, --dry-run flags | 2h |
| GR-002-G | Tests for parsers | 3h |
| GR-002-H | Tests for CLI command | 2h |
| GR-002-I | Documentation | 2h |

---

## Key Technical Decisions

### 1. Project Namespace Strategy
- **Decision**: Use directory name with optional override in `.guardkit/graphiti.yaml`
- **Rationale**: Simple, predictable, overridable

### 2. Metadata Storage
- **Decision**: Store in episode body (not Graphiti entity properties)
- **Rationale**: Simpler to implement, can migrate later if needed

### 3. Upsert Strategy
- **Decision**: Research graphiti-core first, implement invalidate+create if no native support
- **Rationale**: Use native capabilities when available

### 4. Role Constraints (from AutoBuild lessons)
- **Decision**: Seed default Player/Coach constraints during project init
- **Rationale**: Prevents role reversal that was top-5 AutoBuild problem

### 5. Quality Gate Configs (from AutoBuild lessons)
- **Decision**: Seed task-type specific thresholds (scaffolding, feature, testing, docs)
- **Rationale**: Prevents threshold drift that caused unpredictable approvals

---

## New Group IDs

### Project Groups (prefixed with project_id)
```
{project}__project_overview
{project}__project_architecture
{project}__feature_specs
{project}__project_decisions
{project}__project_constraints
{project}__domain_knowledge
```

### AutoBuild Support Groups (system-level)
```
role_constraints          # Player/Coach role boundaries
quality_gate_configs      # Task-type specific thresholds
implementation_modes      # Direct vs task-work patterns
```

---

## New Episode Schemas

### RoleConstraintsEpisode
```python
@dataclass
class RoleConstraintsEpisode:
    entity_type: str = "role_constraints"
    role: str = ""  # "player" | "coach"
    must_do: List[str] = field(default_factory=list)
    must_not_do: List[str] = field(default_factory=list)
    ask_before: List[str] = field(default_factory=list)
    escalate_when: List[str] = field(default_factory=list)
```

### QualityGateConfigEpisode
```python
@dataclass
class QualityGateConfigEpisode:
    entity_type: str = "quality_gate_config"
    task_type: str = ""  # "scaffolding" | "feature" | "testing" | "documentation"
    complexity_range: Tuple[int, int] = (1, 10)
    arch_review_required: bool = True
    arch_review_threshold: int = 60
    coverage_required: bool = True
    coverage_threshold: float = 0.80
    tests_required: bool = True
    effective_from: str = ""
```

### ImplementationModeEpisode
```python
@dataclass
class ImplementationModeEpisode:
    entity_type: str = "implementation_mode"
    mode: str = ""  # "direct" | "task-work"
    invocation_method: str = ""  # "sdk_query" | "subprocess" | "inline"
    result_location_pattern: str = ""
    state_recovery_strategy: str = ""
    when_to_use: List[str] = field(default_factory=list)
    pitfalls: List[str] = field(default_factory=list)
```

---

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

---

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
# After MVP implementation:
guardkit graphiti clear --confirm
guardkit graphiti seed
guardkit init --template fastmcp-python --project-name test-project
guardkit graphiti add-context --type project-overview CLAUDE.md
guardkit graphiti status
guardkit graphiti search "test-project overview"
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| graphiti-core upsert complexity | Medium | High | Research API first, implement fallback |
| Parser edge cases | High | Medium | Define strict frontmatter requirements |
| Config migration complexity | Low | Medium | Provide upgrade script |

---

## Dependencies

- graphiti-core library (existing)
- Neo4j database (existing)
- OPENAI_API_KEY (existing)

---

## References

- [README.md](./README.md) - Feature index and implementation order
- [FEAT-GR-000-gap-analysis.md](./FEAT-GR-000-gap-analysis.md) - Gap analysis
- [TASK-REV-1505 Review Report](../../.claude/reviews/TASK-REV-1505-review-report.md) - Architecture review
- [TASK-REV-7549](../../tasks/backlog/TASK-REV-7549-autobuild-lessons-learned-graphiti.md) - AutoBuild lessons
