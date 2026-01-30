# FEAT-GR-000: Graphiti Implementation Gap Analysis

> **Purpose**: Identify gaps between the current Graphiti implementation and the new project-knowledge features (FEAT-GR-001 through FEAT-GR-006).
>
> **Date**: January 2026
> **Status**: Analysis Complete + Reviewed (TASK-REV-1505)
> **Architecture Score**: 78/100
> **Recommendation**: Create 4 prerequisite features (PRE-000 through PRE-003) + add critical entities from AutoBuild lessons

---

## Current Implementation Summary

### What Exists

| Component | Location | Status | Notes |
|-----------|----------|--------|-------|
| **GraphitiClient** | `guardkit/knowledge/graphiti_client.py` | ✅ Complete | graphiti-core wrapper with graceful degradation |
| **GraphitiConfig** | `guardkit/knowledge/graphiti_client.py` | ✅ Complete | Basic config (enabled, neo4j_uri, user, password, timeout) |
| **GraphitiSettings** | `guardkit/knowledge/config.py` | ✅ Complete | YAML loading with env overrides |
| **CLI: seed** | `guardkit/cli/graphiti.py` | ✅ Complete | Seeds 13+ knowledge categories |
| **CLI: status** | `guardkit/cli/graphiti.py` | ✅ Complete | Shows connection and seeding status |
| **CLI: verify** | `guardkit/cli/graphiti.py` | ✅ Complete | Test queries |
| **CLI: seed-adrs** | `guardkit/cli/graphiti.py` | ✅ Complete | Seeds feature-build ADRs |
| **Context Loader** | `guardkit/knowledge/context_loader.py` | ✅ Complete | Loads critical context at session start |
| **Seeding** | `guardkit/knowledge/seeding.py` | ✅ Complete | 13+ categories of system knowledge |

### Current Seeding Categories

From `seeding.py`:
1. `product_knowledge` - What GuardKit is
2. `command_workflows` - How commands work  
3. `quality_gate_phases` - 5-phase structure
4. `technology_stack` - Python CLI, SDK, worktrees
5. `feature_build_architecture` - Player-Coach pattern
6. `architecture_decisions` - Key design decisions
7. `failure_patterns` - Known failures
8. `component_status` - What's incomplete
9. `integration_points` - How components connect
10. `templates` - Template metadata
11. `agents` - Agent capabilities
12. `patterns` - Design patterns
13. `rules` - Code rules

---

## Gaps Identified

### Gap 1: No Project-Specific Group IDs

**Current**: All group IDs are for GuardKit system knowledge.

**Missing Group IDs for Project Knowledge**:
- `project_overview` - Project purpose, goals, constraints
- `project_architecture` - Project-specific architecture
- `feature_specs` - Feature specifications
- `project_decisions` - Project-specific ADRs
- `project_constraints` - Technical/business constraints
- `domain_knowledge` - Domain terminology and concepts

**Impact**: FEAT-GR-001 and FEAT-GR-002 need these group IDs.

**Fix**: Add project-specific group IDs to config and seeding infrastructure.

---

### Gap 2: No Episode Metadata Support

**Current**: Episodes are added with minimal metadata:
```python
await client.add_episode(
    name=name,
    episode_body=json.dumps(body),
    group_id=group_id
)
```

**Missing Metadata Fields** (from research docs):
- `source_type` - Where episode came from (e.g., "seeding", "feature_spec_parse", "interactive_capture")
- `source_file` - Original file path if from file
- `entity_type` - What kind of entity (e.g., "feature_spec", "project_overview", "adr")
- `version` - For temporal versioning
- `confidence` - For discovered vs explicit knowledge
- `project_id` - For project namespace isolation

**Impact**: FEAT-GR-002 parsers need to store metadata. FEAT-GR-006 job-specific retrieval needs to filter by entity_type.

**Fix**: Extend episode body schema to include standard metadata fields.

---

### Gap 3: No File Parsing Infrastructure

**Current**: No utilities for parsing markdown files into structured episodes.

**Missing Components**:
- `FeatureSpecParser` - Parse FEAT-*.md files
- `ADRParser` - Parse ADR-*.md files
- `ProjectOverviewParser` - Parse CLAUDE.md
- `GuideParser` - Parse implementation guides
- `DomainParser` - Parse glossaries

**Impact**: FEAT-GR-002 (`add-context` command) needs these parsers.

**Fix**: Create `guardkit/knowledge/parsers/` module with parser classes.

---

### Gap 4: No Context Budget/Allocation System

**Current**: Context loading uses fixed queries with `num_results=5` or `num_results=10`.

**Missing**:
- Token budget calculation
- Dynamic allocation based on task characteristics
- Budget enforcement (trim results to fit)
- Allocation configuration

**Impact**: FEAT-GR-006 (Job-Specific Context) needs dynamic budget allocation.

**Fix**: Create budget allocation system in `context_builder.py` or new module.

---

### Gap 5: No Query Commands for Users

**Current**: Only `verify` command runs test queries. No way for users to:
- Search knowledge by query
- List all items in a category
- View specific episode details

**Missing Commands**:
- `guardkit graphiti search <query>` - Search across categories
- `guardkit graphiti list <category>` - List items in category
- `guardkit graphiti show <type> <id>` - Show episode details

**Impact**: FEAT-GR-005 (Knowledge Query Command) needs these.

**Fix**: Add query commands to CLI.

---

### Gap 6: No Project Namespace Isolation

**Current**: All knowledge goes to same Graphiti instance/namespace.

**Research Decision**: Per-project isolation using group_id prefixing.

**Missing**:
- Project ID detection/generation
- Group ID prefixing with project ID
- Project initialization in Graphiti

**Impact**: FEAT-GR-001 needs project namespace isolation.

**Fix**: Add project namespace to GraphitiClient and config.

---

### Gap 7: No Episode Update/Replacement Logic

**Current**: `add_episode` always creates new episodes. No way to:
- Check if episode exists
- Update existing episode
- Handle `--force` flag for replacement

**Missing**:
- Duplicate detection
- Episode update/replacement
- Version tracking

**Impact**: FEAT-GR-002 `--force` flag needs this.

**Fix**: Add `update_episode` or `upsert_episode` method to GraphitiClient.

---

## Recommended Prerequisite Features

Before implementing FEAT-GR-001 through FEAT-GR-006, we should create these foundation features:

### FEAT-GR-PRE-001: Project Namespace Foundation

**Purpose**: Establish project-specific namespacing in Graphiti.

**Tasks**:
1. Add project-specific group IDs to config schema
2. Add `project_id` to GraphitiClient
3. Implement group ID prefixing for project isolation
4. Add project initialization logic

**Estimate**: 6 hours

---

### FEAT-GR-PRE-002: Episode Metadata Schema

**Purpose**: Standardize episode metadata for all episode types.

**Tasks**:
1. Define standard metadata fields (source_type, entity_type, source_file, etc.)
2. Create base episode schema dataclass
3. Update `add_episode` to include metadata
4. Add metadata extraction in search results

**Estimate**: 4 hours

---

### FEAT-GR-PRE-003: Episode Upsert Logic

**Purpose**: Enable episode updates and duplicate handling.

**Tasks**:
1. Add `episode_exists` query method
2. Add `update_episode` or `upsert_episode` method
3. Implement duplicate detection by name/group
4. Add `--force` handling logic

**Estimate**: 4 hours

---

## Revised Feature Dependency Graph

```
FEAT-GR-PRE-001: Project Namespace Foundation (6h)
FEAT-GR-PRE-002: Episode Metadata Schema (4h)
FEAT-GR-PRE-003: Episode Upsert Logic (4h)
    ↓
FEAT-GR-001: Project Knowledge Seeding (13h)
    ↓
FEAT-GR-002: Context Addition Command (19h)
    ↓
FEAT-GR-003: Feature Spec Integration (13h)
    ↓
FEAT-GR-004: Interactive Knowledge Capture (17h)
    ↓
FEAT-GR-005: Knowledge Query Command (10h)
    ↓
FEAT-GR-006: Job-Specific Context Retrieval (25h)
```

**New Total Estimate**: 97h (original) + 14h (prerequisites) = **111 hours (~14 days)**

---

## Existing Code to Leverage

### Episode Schema Patterns (from seeding.py)

The current seeding already uses a consistent pattern for episode bodies:

```python
("episode_name", {
    "entity_type": "product",
    "name": "...",
    "description": "...",
    # ... other fields
})
```

This pattern can be formalized into a base schema.

### Search Result Handling (from context_loader.py)

The `_filter_valid_results` function already handles search result validation:

```python
def _filter_valid_results(results: List[Any]) -> List[Dict[str, Any]]:
    """Filter search results to only include valid dict entries."""
    valid = []
    for r in results:
        if r is None:
            continue
        if not isinstance(r, dict):
            continue
        valid.append(r)
    return valid
```

### Configuration Loading (from config.py)

The YAML loading with env overrides pattern is well-established and can be extended for new settings.

---

## Recommended Actions

1. **Create prerequisite feature specs** (FEAT-GR-PRE-001, PRE-002, PRE-003)
2. **Update README.md** with prerequisite features in the dependency chain
3. **Implement prerequisites first** - they're small (14 hours total) and unblock everything else
4. **Then proceed with FEAT-GR-001** which now has the foundation it needs

---

## Questions for Refinement

1. **Project ID Strategy**: 
   - Use project name from CLAUDE.md?
   - Use directory name?
   - Generate hash-based ID?
   
   **Recommendation**: Use directory name with optional override in `.guardkit/graphiti.yaml`

2. **Metadata Storage**:
   - Store metadata in episode body (current approach)?
   - Use Graphiti entity properties?
   
   **Recommendation**: Store in episode body for now (simpler), migrate to entity properties later if needed

3. **Version Strategy**:
   - Use Graphiti's `valid_at`/`invalid_at`?
   - Custom version field?
   
   **Recommendation**: Use Graphiti's temporal model (already supports this)

---

## Gap 8: No Role Constraints Entity (NEW - from TASK-REV-1505)

**Source**: TASK-REV-7549 AutoBuild Lessons Learned

**Current**: No seeding of Player/Coach role boundaries. Sessions experience role confusion.

**Missing**:
- `role_constraints` group ID
- RoleConstraintsEpisode schema
- Default seeding of Player/Coach constraints

**Impact**: Feature-build sessions will continue to experience role reversal (top-5 AutoBuild problem).

**Fix**: Add `role_constraints` to FEAT-GR-001 seeding.

---

## Gap 9: No Quality Gate Configuration Entity (NEW - from TASK-REV-1505)

**Source**: TASK-REV-7549 AutoBuild Lessons Learned

**Current**: Quality gate thresholds are hardcoded. Sessions experience threshold drift.

**Missing**:
- `quality_gate_configs` group ID
- QualityGateConfigEpisode schema with task_type and complexity_range
- Default seeding of scaffolding/feature/testing/documentation profiles

**Impact**: Quality gate threshold drift - acceptable scores change mid-session.

**Fix**: Add `quality_gate_configs` to FEAT-GR-001 seeding.

---

## Gap 10: No Implementation Mode Entity (NEW - from TASK-REV-1505)

**Source**: TASK-REV-7549 AutoBuild Lessons Learned

**Current**: No documentation of direct vs task-work mode differences in knowledge graph.

**Missing**:
- `implementation_modes` group ID
- ImplementationModeEpisode schema
- Default seeding with invocation methods, result locations, pitfalls

**Impact**: Direct mode vs task-work mode confusion causes file location errors.

**Fix**: Add `implementation_modes` to FEAT-GR-001 seeding.

---

## Gap 11: No Turn State Tracking (NEW - from TASK-REV-1505)

**Source**: TASK-REV-7549 AutoBuild Lessons Learned

**Current**: No capture of feature-build turn-by-turn state. Turn N doesn't know what Turn N-1 learned.

**Missing**:
- `turn_states` group ID
- TurnStateEpisode schema with player_decision, coach_decision, progress
- Turn state capture integration with feature-build
- Turn context loading for next turn

**Impact**: Cross-turn learning failure - each turn starts from zero.

**Fix**: Add `turn_states` to FEAT-GR-005 query commands and feature-build integration.

---

## Revised Prerequisite Features

Based on original analysis + TASK-REV-1505 review:

### FEAT-GR-PRE-000: Seeding Metadata Update (NEW)

**Purpose**: Add metadata to existing seeding, add clear command.

**Tasks**:
1. Add `_metadata` block to all existing seeding episodes
2. Add `guardkit graphiti clear --confirm` command
3. Add `guardkit graphiti clear --system-only --confirm` option

**Estimate**: 6 hours

---

### FEAT-GR-PRE-001: Project Namespace Foundation

**Purpose**: Establish project-specific namespacing in Graphiti.

**Tasks**:
1. Add project-specific group IDs to config schema
2. Add `project_id` to GraphitiClient
3. Implement group ID prefixing for project isolation
4. Add project initialization logic

**Estimate**: 10 hours (revised from 6h based on review)

---

### FEAT-GR-PRE-002: Episode Metadata Schema

**Purpose**: Standardize episode metadata for all episode types.

**Tasks**:
1. Define standard metadata fields (source_type, entity_type, source_file, etc.)
2. Create base episode schema dataclass
3. Update `add_episode` to include metadata
4. Add metadata extraction in search results

**Estimate**: 7 hours (revised from 4h)

---

### FEAT-GR-PRE-003: Episode Upsert Logic

**Purpose**: Enable episode updates and duplicate handling.

**Tasks**:
1. Research graphiti-core native capabilities
2. Add `episode_exists` query method
3. Add `update_episode` or `upsert_episode` method (or invalidate+create pattern)
4. Implement duplicate detection by name/group
5. Add `--force` handling logic

**Estimate**: 10 hours (revised from 4h based on potential complexity)

---

## Revised Feature Dependency Graph

```
FEAT-GR-PRE-000: Seeding Metadata Update (6h)
    ↓ (adds metadata to seeding, clear command)
FEAT-GR-PRE-001: Project Namespace Foundation (10h)
FEAT-GR-PRE-002: Episode Metadata Schema (7h)
FEAT-GR-PRE-003: Episode Upsert Logic (10h)
    ↓ (prerequisites complete - 33h total)
FEAT-GR-001: Project Knowledge Seeding (16h)
    + role_constraints
    + quality_gate_configs
    + implementation_modes
    ↓
FEAT-GR-002: Context Addition Command (23h)
    ↓
FEAT-GR-003: Feature Spec Integration (13h)
    ↓
FEAT-GR-004: Interactive Knowledge Capture (17h)
    ↓
FEAT-GR-005: Knowledge Query Command (13h)
    + turn_states tracking
    ↓
FEAT-GR-006: Job-Specific Context Retrieval (32h)
```

**New Total Estimate**: 147 hours (~18 days) - includes 18% buffer

---

## Next Steps

1. ✅ Created feature spec for FEAT-GR-PRE-000 (Seeding Metadata Update)
2. ✅ Created feature spec for FEAT-GR-PRE-001 (Project Namespace Foundation)
3. ✅ Created feature spec for FEAT-GR-PRE-002 (Episode Metadata Schema)
4. ✅ Created feature spec for FEAT-GR-PRE-003 (Episode Upsert Logic)
5. ✅ Updated FEAT-GR-001 with role_constraints, quality_gate_configs, implementation_modes
6. ✅ Updated FEAT-GR-005 with turn_states tracking
7. ✅ Updated README.md with complete feature list and revised estimates
8. **NEXT**: Run `/feature-plan "graphiti refinement MVP"` to generate implementation tasks
