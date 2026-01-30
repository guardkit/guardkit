# Feature Specification: Graphiti Refinement Phase 2

> **For**: `/feature-plan` command
> **Status**: Ready for Implementation
> **Reviewed**: TASK-REV-1505 (2026-01-30)
> **Architecture Score**: 78/100
> **Prerequisites**: Phase 1 (MVP) must be complete

---

## Feature Overview

Extend the Graphiti integration with workflow automation, interactive knowledge capture, query commands, and job-specific context retrieval - the ultimate goal of giving each task precisely the knowledge it needs.

**Building on MVP**:
Phase 1 (MVP) established: project namespacing, episode metadata, upsert logic, project seeding, and the add-context command. Phase 2 builds on this foundation to deliver the full vision.

**Problem Solved**:
- Manual context management during feature planning
- Knowledge gaps that require guessing
- No visibility into stored knowledge
- Generic context that wastes tokens or misses relevance
- No cross-turn learning in AutoBuild workflows

**Expected Outcomes**:
- Automatic feature spec context during `/feature-plan`
- Interactive sessions to capture implicit knowledge
- CLI commands to inspect and verify stored knowledge
- Dynamic, job-specific context retrieval
- Cross-turn learning via turn state tracking

---

## Phase 2 Scope

**Total Estimate**: 79 hours (~10 days)

### Feature Spec Integration (15h)

| Task | Description | Estimate |
|------|-------------|----------|
| GR-003-A | Implement FeatureDetector class | 2h |
| GR-003-B | Implement FeaturePlanContext dataclass and formatting | 2h |
| GR-003-C | Implement FeaturePlanContextBuilder | 3h |
| GR-003-D | Integrate with /feature-plan command | 2h |
| GR-003-E | Add --context CLI option to feature-plan | 1h |
| GR-003-F | Add AutoBuild context queries (role_constraints, quality_gate_configs, implementation_modes) | 2h |
| GR-003-G | Add tests for context building (including AutoBuild context) | 2h |
| GR-003-H | Update documentation | 1h |

### Interactive Knowledge Capture (19h)

| Task | Description | Estimate |
|------|-------------|----------|
| GR-004-A | Implement KnowledgeGapAnalyzer | 3h |
| GR-004-B | Implement InteractiveCaptureSession | 3h |
| GR-004-C | Create CLI capture command | 2h |
| GR-004-D | Add fact extraction logic | 2h |
| GR-004-E | Implement Graphiti persistence | 2h |
| GR-004-F | Add /task-review --capture-knowledge integration | 2h |
| GR-004-G | Add AutoBuild workflow customization questions | 2h |
| GR-004-H | Add tests (including AutoBuild categories) | 2h |
| GR-004-I | Update documentation | 1h |

### Knowledge Query Command (13h)

| Task | Description | Estimate |
|------|-------------|----------|
| GR-005-A | Implement `show` command | 2h |
| GR-005-B | Implement `search` command | 2h |
| GR-005-C | Implement `list` command | 1h |
| GR-005-D | Implement `status` command | 1h |
| GR-005-E | Add output formatting utilities | 1h |
| GR-005-F | Create TurnStateEpisode schema | 1h |
| GR-005-G | Add turn state capture to feature-build | 2h |
| GR-005-H | Add turn context loading for next turn | 1h |
| GR-005-I | Add tests (including turn states) | 2h |
| GR-005-J | Update documentation | 1h |

### Job-Specific Context Retrieval (32h)

| Task | Description | Estimate |
|------|-------------|----------|
| GR-006-A | Implement TaskAnalyzer (including AutoBuild characteristics) | 3h |
| GR-006-B | Implement DynamicBudgetCalculator (including AutoBuild allocation) | 4h |
| GR-006-C | Implement JobContextRetriever (including AutoBuild context) | 4h |
| GR-006-D | Implement RetrievedContext formatting (including AutoBuild sections) | 3h |
| GR-006-E | Integrate with /task-work | 2h |
| GR-006-F | Integrate with /feature-build | 2h |
| GR-006-G | Add role_constraints retrieval and formatting | 2h |
| GR-006-H | Add quality_gate_configs retrieval and formatting | 2h |
| GR-006-I | Add turn_states retrieval for cross-turn learning | 3h |
| GR-006-J | Add implementation_modes retrieval | 1h |
| GR-006-K | Add relevance tuning and testing | 3h |
| GR-006-L | Performance optimization | 2h |
| GR-006-M | Add tests (including AutoBuild context) | 3h |
| GR-006-N | Update documentation | 1h |

---

## Key Technical Decisions

### 1. Feature Detection Strategy
- **Decision**: Regex pattern matching for FEAT-XXX IDs in descriptions
- **Rationale**: Simple, reliable, no LLM calls needed

### 2. Knowledge Gap Analysis
- **Decision**: Question templates with field checking against existing knowledge
- **Rationale**: Deterministic gap detection, can enhance with LLM later

### 3. Turn State Storage
- **Decision**: Store turn states as episodes in `turn_states` group
- **Rationale**: Consistent with existing episode model, queryable

### 4. Context Budget Calculation
- **Decision**: Dynamic allocation based on task characteristics
- **Rationale**: Different tasks need different context mixes

### 5. AutoBuild Context Priority
- **Decision**: Dedicated allocations for role_constraints, quality_gate_configs, turn_states, implementation_modes
- **Rationale**: Addresses top AutoBuild issues from TASK-REV-7549

---

## New Group IDs (Phase 2 Only)

### Turn State Tracking
```
turn_states              # Feature-build turn-by-turn history
```

### Captured Knowledge Categories
```
{project}__captured_knowledge  # Interactively captured facts
```

---

## New Episode Schemas (Phase 2)

### TurnStateEpisode (FEAT-GR-005)
```python
@dataclass
class TurnStateEpisode:
    """Captures state at the end of each feature-build turn."""

    entity_type: str = "turn_state"
    feature_id: str = ""  # FEAT-XXX
    task_id: str = ""     # TASK-XXX being worked on
    turn_number: int = 0

    # What happened this turn
    player_decision: str = ""
    coach_decision: str = ""  # "APPROVED" | "REJECTED" | "FEEDBACK"
    feedback_summary: str = ""

    # Progress tracking
    blockers_found: List[str] = field(default_factory=list)
    progress_summary: str = ""
    files_modified: List[str] = field(default_factory=list)

    # Acceptance criteria status
    acceptance_criteria_status: Dict[str, str] = field(default_factory=dict)

    # Mode tracking
    mode: str = "FRESH_START"  # "FRESH_START" | "RECOVERING_STATE" | "CONTINUING_WORK"
```

### FeaturePlanContext (FEAT-GR-003)
```python
@dataclass
class FeaturePlanContext:
    """Rich context for feature planning."""

    feature_spec: Dict[str, Any]
    related_features: List[Dict[str, Any]]
    relevant_patterns: List[Dict[str, Any]]
    similar_implementations: List[Dict[str, Any]]
    project_architecture: Dict[str, Any]
    warnings: List[Dict[str, Any]]

    # AutoBuild support context
    role_constraints: List[Dict[str, Any]] = field(default_factory=list)
    quality_gate_configs: List[Dict[str, Any]] = field(default_factory=list)
    implementation_modes: List[Dict[str, Any]] = field(default_factory=list)
```

### RetrievedContext (FEAT-GR-006)
```python
@dataclass
class RetrievedContext:
    """Context retrieved for a specific job."""

    task_id: str
    budget_used: int
    budget_total: int

    # Standard context
    feature_context: List[Dict]
    similar_outcomes: List[Dict]
    relevant_patterns: List[Dict]
    architecture_context: List[Dict]
    warnings: List[Dict]
    domain_knowledge: List[Dict]

    # AutoBuild context
    role_constraints: List[Dict] = field(default_factory=list)
    quality_gate_configs: List[Dict] = field(default_factory=list)
    turn_states: List[Dict] = field(default_factory=list)
    implementation_modes: List[Dict] = field(default_factory=list)
```

---

## New CLI Commands (Phase 2)

```bash
# Feature Spec Integration (GR-003)
/feature-plan "implement FEAT-XXX" --context docs/features/FEAT-XXX.md

# Interactive Knowledge Capture (GR-004)
guardkit graphiti capture --interactive
guardkit graphiti capture --interactive --focus architecture
guardkit graphiti capture --interactive --focus role-customization
guardkit graphiti capture --interactive --focus quality-gates

# Knowledge Query Commands (GR-005)
guardkit graphiti show feature FEAT-XXX
guardkit graphiti show adr ADR-001
guardkit graphiti search "authentication patterns"
guardkit graphiti list features
guardkit graphiti status --verbose

# Turn state commands
guardkit graphiti show turns FEAT-XXX
guardkit graphiti list turns --limit 10
```

---

## Success Criteria

### FEAT-GR-003 Complete
- [ ] Feature ID auto-detected from description
- [ ] Feature spec found and seeded automatically
- [ ] Context includes role_constraints, quality_gate_configs
- [ ] Planning prompt enriched with relevant context

### FEAT-GR-004 Complete
- [ ] Gap analysis identifies missing knowledge
- [ ] Interactive Q&A session works smoothly
- [ ] Facts extracted and persisted to Graphiti
- [ ] AutoBuild customization questions available
- [ ] Role constraints, quality gates can be customized

### FEAT-GR-005 Complete
- [ ] `show`, `search`, `list`, `status` commands work
- [ ] Output is formatted and readable
- [ ] Turn states captured during feature-build
- [ ] Turn context loaded for subsequent turns

### FEAT-GR-006 Complete
- [ ] Context varies by task characteristics
- [ ] Budget allocation respects complexity and type
- [ ] AutoBuild context (role, quality, turns, modes) retrieved
- [ ] Performance under 2 seconds per retrieval

---

## Implementation Order

```
FEAT-GR-003: Feature Spec Integration (15h)
    ↓ (enables automatic context during planning)
FEAT-GR-004: Interactive Knowledge Capture (19h)
    ↓ (enables gap filling and customization)
FEAT-GR-005: Knowledge Query Command (13h)
    ↓ (enables verification, debugging, turn states)
FEAT-GR-006: Job-Specific Context Retrieval (32h)
    (ultimate goal - precise context per task)
```

### Parallel Implementation Opportunities

GR-003 and GR-004 can be implemented in parallel after MVP completion.
GR-005 turn state features are required before GR-006 turn state retrieval.

---

## Testing Strategy

### Unit Tests
- Feature detector pattern matching
- Knowledge gap analyzer question selection
- Budget calculator allocation logic
- Context retriever query construction

### Integration Tests
- Full feature-plan workflow with context injection
- Interactive capture session with Graphiti persistence
- Query commands returning accurate results
- Job-specific retrieval for various task types

### Manual Verification
```bash
# After Phase 2 implementation:

# Test feature spec integration
/feature-plan "implement FEAT-SKEL-001 walking skeleton"
# Verify: Context includes feature spec + role constraints + quality gates

# Test interactive capture
guardkit graphiti capture --interactive --focus role-customization
# Verify: Role constraints captured and queryable

# Test query commands
guardkit graphiti search "authentication"
guardkit graphiti show turns FEAT-XXX
# Verify: Results accurate and formatted

# Test job-specific context
/task-work TASK-XXX
# Verify: Context varies by task type and includes AutoBuild context
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Feature detection false positives | Medium | Low | Require FEAT-XXX format, validate file exists |
| Interactive session abandonment | Medium | Low | Support quit at any time, save partial progress |
| Turn state storage growth | Medium | Medium | Add turn compression for older entries |
| Budget calculation complexity | Low | Medium | Start with simple heuristics, tune over time |
| Performance with large knowledge base | Medium | High | Implement caching, limit search results |

---

## Dependencies

- Phase 1 (MVP) complete: PRE-000 through GR-002
- graphiti-core library (existing)
- Neo4j database (existing)
- OPENAI_API_KEY (existing)

---

## Context Reduction Impact (Phase 2)

Building on Phase 1 metrics:

| Metric | After Phase 1 | After Phase 2 | Additional Reduction |
|--------|---------------|---------------|---------------------|
| Generic context loaded | 15-30KB | 5-15KB | **50-67%** |
| Time finding relevant context | 10-15% | 2-5% | **67-80%** |
| Cross-turn knowledge loss | 40% | <5% | **87%** |
| Manual knowledge entry | 30% | 10% | **67%** |

---

## References

- [FEATURE-SPEC-graphiti-refinement-mvp.md](./FEATURE-SPEC-graphiti-refinement-mvp.md) - Phase 1 (MVP) specification
- [FEAT-GR-003-feature-spec-integration.md](./FEAT-GR-003-feature-spec-integration.md) - Detailed spec
- [FEAT-GR-004-interactive-knowledge-capture.md](./FEAT-GR-004-interactive-knowledge-capture.md) - Detailed spec
- [FEAT-GR-005-knowledge-query-command.md](./FEAT-GR-005-knowledge-query-command.md) - Detailed spec
- [FEAT-GR-006-job-specific-context.md](./FEAT-GR-006-job-specific-context.md) - Detailed spec
- [README.md](./README.md) - Feature index and implementation order
- [TASK-REV-1505 Review Report](../../.claude/reviews/TASK-REV-1505-review-report.md) - Architecture review
- [TASK-REV-7549](../../tasks/backlog/TASK-REV-7549-autobuild-lessons-learned-graphiti.md) - AutoBuild lessons
