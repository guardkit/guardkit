# Graphiti Refinement Features

> **Purpose**: Feature specifications for enhancing Graphiti integration to support project-specific knowledge seeding, knowledge updates, and job-specific context retrieval.
>
> **Date**: January 2026
> **Status**: Ready for Implementation (reviewed via TASK-REV-1505)
> **Architecture Score**: 78/100
> **Related**: `../knowledge-graph-mcp/` research documents, `.claude/reviews/TASK-REV-1505-review-report.md`

---

## Overview

These features extend the existing Graphiti integration (which seeds GuardKit system knowledge) to support:

1. **Project-specific knowledge** - Goals, architecture, constraints for individual projects
2. **Feature spec seeding** - Structured ingestion of feature specifications
3. **Knowledge evolution** - Handling updates, supersession, and temporal versioning
4. **Interactive capture** - Q&A sessions to build project knowledge
5. **Job-specific context** - Precise context retrieval per task (ultimate goal)
6. **Cross-session learning** - Role constraints, quality gate configs, and turn states from AutoBuild lessons

---

## Review Status

**Reviewed**: TASK-REV-1505 (2026-01-30)
**Decision**: Proceed with revisions

### Critical Additions from Review

Based on TASK-REV-7549 (AutoBuild Lessons Learned), the following entities were added:

| Entity | Feature | Purpose |
|--------|---------|---------|
| `role_constraints` | FEAT-GR-001 | Prevent Player-Coach role reversal |
| `quality_gate_configs` | FEAT-GR-001 | Prevent quality gate threshold drift |
| `implementation_modes` | FEAT-GR-001 | Clarify direct vs task-work patterns |
| `turn_states` | FEAT-GR-005 | Enable cross-turn learning in feature-build |

See `.claude/reviews/TASK-REV-1505-review-report.md` for full findings.

---

## Feature Index

### Analysis Documents

| ID | Document | Description |
|----|----------|-------------|
| [FEAT-GR-000](./FEAT-GR-000-gap-analysis.md) | Gap Analysis | Analysis of current implementation vs new requirements |

### Prerequisite Features (Foundation)

These features establish the foundation required by the main features:

| ID | Feature | Description | Estimate | Status |
|----|---------|-------------|----------|--------|
| [FEAT-GR-PRE-000](./FEAT-GR-PRE-000-seeding-metadata-update.md) | Seeding Metadata Update | Update seeding to use metadata schema, add clear command | 6h | Planning |
| [FEAT-GR-PRE-001](./FEAT-GR-PRE-001-project-namespace-foundation.md) | Project Namespace Foundation | Project-specific namespacing in Graphiti | 10h | Planning |
| [FEAT-GR-PRE-002](./FEAT-GR-PRE-002-episode-metadata-schema.md) | Episode Metadata Schema | Standardized metadata for all episodes | 7h | Planning |
| [FEAT-GR-PRE-003](./FEAT-GR-PRE-003-episode-upsert-logic.md) | Episode Upsert Logic | Update/replace support with --force handling | 10h | Planning |

**Prerequisites Total**: 33 hours (~4 days) - revised from 28h based on TASK-REV-1505

### Main Features

| ID | Feature | Description | Priority | Complexity | Estimate | Status |
|----|---------|-------------|----------|------------|----------|--------|
| [FEAT-GR-001](./FEAT-GR-001-project-knowledge-seeding.md) | Project Knowledge Seeding | Seed project-specific knowledge during `guardkit init` + role constraints, quality gate configs, implementation modes | High | 6 | **16h** | Planning |
| [FEAT-GR-002](./FEAT-GR-002-context-addition-command.md) | Context Addition Command | `guardkit graphiti add-context` for explicit knowledge addition | High | 5 | **23h** | Planning |
| [FEAT-GR-003](./FEAT-GR-003-feature-spec-integration.md) | Feature Spec Integration | Auto-seed feature specs during `/feature-plan` + AutoBuild context | Medium | 4 | **15h** | Planning |
| [FEAT-GR-004](./FEAT-GR-004-interactive-knowledge-capture.md) | Interactive Knowledge Capture | Q&A sessions via `guardkit graphiti capture --interactive` + AutoBuild customization | Medium | 5 | **19h** | Planning |
| [FEAT-GR-005](./FEAT-GR-005-knowledge-query-command.md) | Knowledge Query Command | `guardkit graphiti show/search/list/status` + turn states | Low | 4 | **13h** | Planning |
| [FEAT-GR-006](./FEAT-GR-006-job-specific-context.md) | Job-Specific Context Retrieval | Dynamic context injection per task + AutoBuild context (role, quality, turns, modes) | Low | 7 | **32h** | Planning |

**Main Features Total**: 118 hours (~15 days) - revised from 114h

**Grand Total**: 151 hours (~19 days) - revised from 147h (+18% buffer as recommended)

---

## Implementation Order

```
FEAT-GR-PRE-000: Seeding Metadata Update (6h)
    ↓ (adds metadata to seeding, clear command)
FEAT-GR-PRE-001: Project Namespace Foundation (10h)
FEAT-GR-PRE-002: Episode Metadata Schema (7h)
FEAT-GR-PRE-003: Episode Upsert Logic (10h)
    ↓ (prerequisites complete - 33h total)
FEAT-GR-001: Project Knowledge Seeding (16h)
    ↓ (foundation - defines group IDs, schemas, role constraints, quality gate configs)
FEAT-GR-002: Context Addition Command (23h)
    ↓ (enables manual seeding - IMMEDIATE VALUE)
FEAT-GR-003: Feature Spec Integration (13h)
    ↓ (auto-seeding during /feature-plan workflow)
FEAT-GR-004: Interactive Knowledge Capture (17h)
    ↓ (builds richer knowledge interactively)
FEAT-GR-005: Knowledge Query Command (13h)
    ↓ (enables verification, debugging, turn state tracking)
FEAT-GR-006: Job-Specific Context Retrieval (32h)
    (ultimate goal - precise context per task)
```

### Recommended MVP Scope

For immediate value, implement the prerequisites and first two main features:

**Phase 0: Seeding Update (6 hours)**
- FEAT-GR-PRE-000: Update seeding with metadata, add clear command

**Phase 1: Foundation (27 hours)**
- FEAT-GR-PRE-001: Project namespace isolation
- FEAT-GR-PRE-002: Episode metadata schema
- FEAT-GR-PRE-003: Episode upsert logic

**Phase 2: Core Functionality (39 hours)**
- FEAT-GR-001: Project knowledge seeding + role constraints, quality gate configs
- FEAT-GR-002: Context addition command

**MVP Total**: 72 hours (~9 days) - revised from 60h

This enables testing Graphiti integration with the youtube-mcp project:

```bash
# Step 0: Clear and re-seed with metadata
guardkit graphiti clear --confirm
guardkit graphiti seed

# Step 1: Initialize project with knowledge namespace
guardkit init --template fastmcp-python --project-name youtube-mcp

# Step 2: Add project overview
guardkit graphiti add-context --type project-overview CLAUDE.md

# Step 3: Add feature specs
guardkit graphiti add-context --type feature docs/features/FEAT-*.md

# Step 4: Verify
guardkit graphiti status
guardkit graphiti search "walking skeleton"

# Step 5: Use in feature-plan (with enriched context)
/feature-plan "implement FEAT-SKEL-001"
```

---

## New CLI Commands (After All Prerequisites)

```bash
# Maintenance
guardkit graphiti clear --confirm  # Clear all data
guardkit graphiti clear --system-only --confirm  # Clear only system knowledge

# Existing commands (updated)
guardkit graphiti seed            # Seed system knowledge (now with metadata)
guardkit graphiti seed --force    # Force re-seed
guardkit graphiti status          # Show connection status
guardkit graphiti verify          # Run test queries

# New commands (FEAT-GR-002, FEAT-GR-005)
guardkit graphiti add-context --type feature docs/features/FEAT-001.md
guardkit graphiti add-context --type project-overview CLAUDE.md
guardkit graphiti search "authentication patterns"
guardkit graphiti list features
guardkit graphiti show feature FEAT-SKEL-001

# NEW: Turn state commands (FEAT-GR-005)
guardkit graphiti show turns FEAT-XXX
guardkit graphiti list turns --limit 10
```

---

## Design Principles

### 1. Separate Namespace Per Project

Each project gets its own Graphiti namespace via group ID prefixing:
- System knowledge: `patterns`, `agents`, etc. (shared)
- Project knowledge: `youtube-mcp__feature_specs`, `youtube-mcp__project_overview`, etc. (isolated)

### 2. Standardized Metadata

All episodes include `_metadata` block:
```json
{
  "_metadata": {
    "entity_type": "feature_spec",
    "source_type": "file_parse",
    "source_file": "docs/features/FEAT-SKEL-001.md",
    "project_id": "youtube-mcp",
    "version": 1,
    "confidence": 1.0,
    "created_at": "2026-01-30T12:00:00Z",
    "updated_at": "2026-01-30T12:00:00Z"
  }
}
```

### 3. Markdown Remains Source of Truth

Markdown files remain authoritative. Graphiti provides queryable layer on top.

### 4. Progressive Enhancement

Early features provide immediate value. Later features optimize for job-specific context.

### 5. Simple Approach

Clear and re-seed rather than complex migrations. System seeding data is fully regenerable.

### 6. AutoBuild Lessons Integration (NEW)

All features incorporate lessons from TASK-REV-7549:
- Role constraints prevent Player-Coach confusion
- Quality gate configs prevent threshold drift
- Turn states enable cross-turn learning
- Implementation modes clarify execution patterns

---

## Group ID Schema

### System Groups (Existing)

```
product_knowledge         # What GuardKit is
command_workflows         # How commands work
quality_gate_phases       # 5-phase structure
technology_stack          # Python CLI, SDK, worktrees
feature_build_architecture # Player-Coach pattern
architecture_decisions    # Key design decisions
failure_patterns          # Known failures
component_status          # What's incomplete
integration_points        # How components connect
templates                 # Template metadata
agents                    # Agent capabilities
patterns                  # Design patterns
rules                     # Code rules
```

### Project Groups (New)

Per-project, prefixed with project ID (e.g., `youtube-mcp__`):
```
project_overview          # What the project is, goals, constraints
project_architecture      # System architecture for this project
feature_specs             # Feature specifications
project_decisions         # Project-specific ADRs
project_constraints       # Technical/business constraints
domain_knowledge          # Domain terminology and concepts
```

### AutoBuild Support Groups (NEW - from TASK-REV-1505)

```
role_constraints          # Player/Coach role boundaries
quality_gate_configs      # Task-type specific thresholds
implementation_modes      # Direct vs task-work patterns
turn_states               # Feature-build turn-by-turn history
```

---

## Success Criteria

| Phase | Milestone | Success Criteria |
|-------|-----------|------------------|
| **Phase 0** | Seeding Update | Seeding includes metadata, clear command works |
| **Prerequisites** | Foundation | Project namespacing works, metadata schema defined, upsert logic functional |
| **Phase 1** | MVP | Can seed youtube-mcp project knowledge and query it during `/feature-plan` |
| **Phase 2** | Workflow Integration | Feature specs automatically available as context during planning |
| **Phase 3** | Rich Knowledge | Interactive sessions build comprehensive project knowledge |
| **Phase 4** | Job-Specific | Each task gets precisely relevant context |
| **NEW** | AutoBuild Support | Role constraints, quality gates, and turn states prevent context loss |

---

## Context Reduction Impact

Based on TASK-REV-1505 analysis:

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Phase 2 context size | 25-40KB | 15-30KB | **25-40%** |
| Time re-learning architecture | 50-70% | 10-15% | **55-60%** |
| Repeated mistakes | ~40% | <10% | **75%** |
| Time to first success | 10+ turns | 3-5 turns | **50-70%** |

---

## Quick Start (After Implementation)

```bash
# 1. Ensure Graphiti is running
docker compose -f docker/docker-compose.graphiti.yml up -d

# 2. Clear and re-seed (one-time after PRE-000)
guardkit graphiti clear --confirm
guardkit graphiti seed

# 3. Initialize project
cd /Users/richardwoollcott/Projects/appmilla_github/youtube-mcp
guardkit init --template fastmcp-python --project-name youtube-mcp

# 4. Add project knowledge
guardkit graphiti add-context --type project-overview CLAUDE.md
guardkit graphiti add-context --type feature docs/features/FEAT-*.md

# 5. Verify
guardkit graphiti status
guardkit graphiti search "walking skeleton"

# 6. Use enhanced context in planning
/feature-plan "implement FEAT-SKEL-001 walking skeleton"
```

---

## Feature Specifications for `/feature-plan`

| Phase | Specification | Description | Estimate |
|-------|--------------|-------------|----------|
| **MVP** | [FEATURE-SPEC-graphiti-refinement-mvp.md](./FEATURE-SPEC-graphiti-refinement-mvp.md) | Phase 0-2: Foundation + Core Functionality | 72h (~9 days) |
| **Phase 2** | [FEATURE-SPEC-graphiti-refinement-phase2.md](./FEATURE-SPEC-graphiti-refinement-phase2.md) | Phase 3+: Automation + Ultimate Goal | 79h (~10 days) |

Use these specifications with `/feature-plan` to generate implementation tasks.

---

## References

- [Gap Analysis](./FEAT-GR-000-gap-analysis.md)
- [Architecture Review Report](../../.claude/reviews/TASK-REV-1505-review-report.md)
- [AutoBuild Lessons Learned](../../tasks/backlog/TASK-REV-7549-autobuild-lessons-learned-graphiti.md)
- [Graphiti System Context Seeding](../knowledge-graph-mcp/graphiti-system-context-seeding.md)
- [Graphiti Prototype Integration Plan](../knowledge-graph-mcp/graphiti-prototype-integration-plan.md)
- [Unified Data Architecture Decision](../knowledge-graph-mcp/unified-data-architecture-decision.md)
