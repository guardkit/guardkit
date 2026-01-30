# Implementation Guide: Graphiti Refinement MVP

## Execution Strategy

This feature uses a **9-wave execution strategy** organized into 3 phases:
- **Phase 0** (Waves 1-2): Seeding Update - 6 hours
- **Phase 1** (Waves 3-5): Foundation - 27 hours
- **Phase 2** (Waves 6-9): Core Functionality - 39 hours

**Total Estimate**: 72 hours (~9 working days)

## Wave Breakdown

### Wave 1: Seeding Metadata Foundation (6h)

**Parallel Execution Possible**: Yes (2 tasks)
**Conductor Workspaces**: `gr-mvp-wave1-metadata`, `gr-mvp-wave1-clear`

| Task ID | Title | Mode | Est. |
|---------|-------|------|------|
| TASK-GR-PRE-000-A | Add metadata block to existing seeding episodes | task-work | 3h |
| TASK-GR-PRE-000-B | Add guardkit graphiti clear command | task-work | 2h |

**Dependencies**: None (first wave)
**Outputs**: All seeding episodes have `_metadata` block, clear command exists

---

### Wave 2: Seeding Tests (1h)

**Parallel Execution Possible**: No (single task)

| Task ID | Title | Mode | Est. |
|---------|-------|------|------|
| TASK-GR-PRE-000-C | Add tests and documentation for seeding update | direct | 1h |

**Dependencies**: Wave 1 complete
**Outputs**: Test coverage for metadata, documentation updated

---

### Wave 3: Foundation Parallel (12h)

**Parallel Execution Possible**: Yes (6 tasks, 3 parallel groups)
**Conductor Workspaces**: `gr-mvp-wave3-namespace`, `gr-mvp-wave3-metadata`, `gr-mvp-wave3-research`

| Task ID | Title | Mode | Est. |
|---------|-------|------|------|
| TASK-GR-PRE-001-A | Add project_id to GraphitiClient | task-work | 2h |
| TASK-GR-PRE-001-B | Implement group ID prefixing | task-work | 3h |
| TASK-GR-PRE-002-A | Define standard metadata fields | task-work | 2h |
| TASK-GR-PRE-002-B | Create EpisodeMetadata dataclass | task-work | 2h |
| TASK-GR-PRE-003-A | Research graphiti-core upsert capabilities | manual | 2h |

**Parallel Groups**:
- Group A: PRE-001-A + PRE-001-B (namespace)
- Group B: PRE-002-A + PRE-002-B (metadata)
- Group C: PRE-003-A (research - can run in parallel)

**Dependencies**: Wave 2 complete
**Outputs**: project_id support, prefixing, metadata schema, upsert research

---

### Wave 4: Foundation Integration (8h)

**Parallel Execution Possible**: Yes (4 tasks)
**Conductor Workspaces**: `gr-mvp-wave4-init`, `gr-mvp-wave4-episode`

| Task ID | Title | Mode | Est. |
|---------|-------|------|------|
| TASK-GR-PRE-001-C | Add project initialization logic | task-work | 3h |
| TASK-GR-PRE-001-D | Tests and documentation for project namespace | direct | 2h |
| TASK-GR-PRE-002-C | Update add_episode to include metadata | task-work | 2h |
| TASK-GR-PRE-002-D | Tests and documentation for episode metadata | direct | 1h |
| TASK-GR-PRE-003-B | Implement episode_exists method | task-work | 2h |

**Dependencies**: Wave 3 complete
**Outputs**: Project init works, metadata in episodes, exists check

---

### Wave 5: Upsert Implementation (6h)

**Parallel Execution Possible**: No (dependent tasks)

| Task ID | Title | Mode | Est. |
|---------|-------|------|------|
| TASK-GR-PRE-003-C | Implement upsert_episode logic | task-work | 4h |
| TASK-GR-PRE-003-D | Tests and documentation for upsert | direct | 2h |

**Dependencies**: Wave 4 complete (especially PRE-003-B)
**Outputs**: Complete upsert capability

---

### Wave 6: Episode Schemas (15h)

**Parallel Execution Possible**: Yes (7 tasks)
**Conductor Workspaces**: `gr-mvp-wave6-schemas`, `gr-mvp-wave6-parsers`

| Task ID | Title | Mode | Est. |
|---------|-------|------|------|
| TASK-GR-001-A | Add project-specific group IDs to config | task-work | 1h |
| TASK-GR-001-B | Create ProjectOverviewEpisode schema | task-work | 2h |
| TASK-GR-001-C | Create ProjectArchitectureEpisode schema | task-work | 1h |
| TASK-GR-001-D | Create RoleConstraintsEpisode and seed defaults | task-work | 2h |
| TASK-GR-001-E | Create QualityGateConfigEpisode and seed defaults | task-work | 2h |
| TASK-GR-001-F | Create ImplementationModeEpisode and seed defaults | task-work | 1h |
| TASK-GR-002-A | Create parser registry infrastructure | task-work | 2h |

**Dependencies**: Wave 5 complete (all prerequisites done)
**Outputs**: All episode schemas, parser registry ready

---

### Wave 7: Parsers & Seeding (13h)

**Parallel Execution Possible**: Yes (4 tasks)
**Conductor Workspaces**: `gr-mvp-wave7-parsers`, `gr-mvp-wave7-seeding`

| Task ID | Title | Mode | Est. |
|---------|-------|------|------|
| TASK-GR-001-G | Implement CLAUDE.md/README.md parsing | task-work | 2h |
| TASK-GR-001-H | Add project seeding to guardkit init | task-work | 3h |
| TASK-GR-002-B | Implement FeatureSpecParser | task-work | 3h |
| TASK-GR-002-C | Implement ADRParser | task-work | 2h |
| TASK-GR-002-D | Implement ProjectOverviewParser | task-work | 2h |

**Parallel Groups**:
- Group A: GR-001-G + GR-001-H (project seeding)
- Group B: GR-002-B + GR-002-C + GR-002-D (parsers)

**Dependencies**: Wave 6 complete
**Outputs**: All parsers implemented, init seeding works

---

### Wave 8: CLI Commands (8h)

**Parallel Execution Possible**: Partial

| Task ID | Title | Mode | Est. |
|---------|-------|------|------|
| TASK-GR-001-I | Implement optional interactive setup | task-work | 2h |
| TASK-GR-002-E | Add guardkit graphiti add-context CLI command | task-work | 3h |
| TASK-GR-002-F | Add --type, --force, --dry-run flags | task-work | 2h |

**Dependencies**: Wave 7 complete
**Outputs**: Interactive setup, add-context command with flags

---

### Wave 9: Final Testing & Docs (9h)

**Parallel Execution Possible**: Yes (3 tasks)
**Conductor Workspaces**: `gr-mvp-wave9-tests`, `gr-mvp-wave9-docs`

| Task ID | Title | Mode | Est. |
|---------|-------|------|------|
| TASK-GR-002-G | Tests for parsers | task-work | 3h |
| TASK-GR-002-H | Tests for CLI command | task-work | 2h |
| TASK-GR-002-I | Documentation for context addition | direct | 2h |

**Dependencies**: Wave 8 complete
**Outputs**: Complete test coverage, documentation

---

## Critical Path

```
Wave 1 (6h) → Wave 2 (1h) → Wave 3 (12h) → Wave 4 (8h) → Wave 5 (6h) → Wave 6 (15h) → Wave 7 (13h) → Wave 8 (8h) → Wave 9 (9h)
```

**Total Sequential Time**: 78 hours
**With Parallel Execution**: ~50-55 hours (estimated 30% reduction)

## Recommended Execution Order

### Solo Developer Path
Execute waves sequentially with parallel tasks where beneficial:
1. Complete Wave 1 tasks in parallel
2. Complete Wave 2
3. Complete Wave 3 with 3 parallel tracks
4. Complete Wave 4 tasks in parallel
5. Complete Wave 5 sequentially
6. Complete Wave 6 tasks in parallel
7. Complete Wave 7 with 2 parallel tracks
8. Complete Wave 8 sequentially
9. Complete Wave 9 tasks in parallel

### Team Execution (2-3 developers)
- **Dev 1**: PRE-000, PRE-001, GR-001 (init flow)
- **Dev 2**: PRE-002, PRE-003 (metadata/upsert)
- **Dev 3**: GR-002 (parsers and CLI)

## Key Technical Decisions

### 1. Project Namespace Strategy
- Use directory name with optional override in `.guardkit/graphiti.yaml`
- Simple, predictable, overridable

### 2. Metadata Storage
- Store in episode body (not Graphiti entity properties)
- Simpler to implement, can migrate later if needed

### 3. Upsert Strategy
- Research graphiti-core first (TASK-GR-PRE-003-A)
- Implement invalidate+create if no native support

### 4. Role Constraints
- Seed default Player/Coach constraints during project init
- Prevents role reversal identified in AutoBuild lessons

### 5. Quality Gate Configs
- Seed task-type specific thresholds (scaffolding, feature, testing, docs)
- Prevents threshold drift

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| graphiti-core upsert complexity | Medium | High | Research API first, implement fallback |
| Parser edge cases | High | Medium | Define strict frontmatter requirements |
| Config migration complexity | Low | Medium | Provide upgrade script |

## Success Verification

After all waves complete, verify with:

```bash
# Clean slate
guardkit graphiti clear --confirm

# Seed system knowledge
guardkit graphiti seed

# Initialize with project
guardkit init --template fastmcp-python --project-name test-project

# Add context manually
guardkit graphiti add-context --type project-overview CLAUDE.md

# Verify seeding
guardkit graphiti status
guardkit graphiti search "test-project overview"
```
