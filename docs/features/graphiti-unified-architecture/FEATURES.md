# Graphiti Unified Architecture: Feature List

> **Purpose**: Define the features needed to implement the unified Graphiti architecture where tasks, features, templates, agents, patterns, and rules all live in the same knowledge graph.
>
> **Date**: January 2025
> **Status**: Feature Identification
> **Related**: 
> - `docs/research/knowledge-graph-mcp/unified-data-architecture-decision.md`
> - `docs/research/knowledge-graph-mcp/graphiti-system-context-seeding.md`
> - `docs/research/knowledge-graph-mcp/graphiti-prototype-integration-plan.md`

---

## Strategic Context

### The Problem We're Solving

Claude Code sessions lack persistent memory. Each session:
1. Doesn't know what GuardKit IS (system context)
2. Doesn't know what decisions were made (architecture)
3. Doesn't know what failed before (failure patterns)
4. Doesn't know what templates/agents/patterns exist (development knowledge)

This leads to "locally-optimal decisions" that conflict with overall system design.

### The Solution

Graphiti as a unified knowledge graph containing:
- **System context** (product knowledge, workflows, phases, tech stack)
- **Tasks and features** (replacing markdown files)
- **Development knowledge** (templates, agents, patterns, rules)
- **Outcomes** (what worked, what didn't, lessons learned)

---

## Feature List

### FEAT-001: Graphiti Infrastructure Setup

**Goal**: Get Graphiti running and accessible from GuardKit CLI.

**Scope**:
- Docker Compose configuration for FalkorDB + Graphiti
- Python client wrapper with connection management
- Configuration (environment variables, settings)
- Health check and connection verification
- Graceful degradation when Graphiti unavailable

**Dependencies**: None (foundation feature)

**Estimated Complexity**: Medium

---

### FEAT-002: System Context Seeding

**Goal**: Seed Graphiti with foundational GuardKit knowledge that every session needs.

**Scope**:
- Product knowledge episodes (what GuardKit is, philosophy, value prop)
- Command workflow episodes (how commands flow together)
- Quality gate phase episodes (the 5-phase structure)
- Technology stack episodes (Python CLI, SDK, worktrees)
- Feature-build architecture episodes (Player-Coach pattern)
- Seeding CLI command (`guardkit graphiti seed`)
- Verification queries to confirm seeding worked

**Dependencies**: FEAT-001

**Estimated Complexity**: Medium

---

### FEAT-003: Development Knowledge Seeding

**Goal**: Seed Graphiti with template, agent, pattern, and rule knowledge for semantic search.

**Scope**:
- Template entities from existing manifests (fastapi-python, react-typescript, etc.)
- Agent entities from existing agent markdown files
- Pattern entities (Dependency Injection, Repository, Player-Coach, etc.)
- Rule entities from existing .claude/rules/ files
- Sync command to update after template/agent changes
- Query examples for "which template for X", "which agent handles Y"

**Dependencies**: FEAT-001, FEAT-002

**Estimated Complexity**: Medium-High

---

### FEAT-004: Session Context Loading

**Goal**: Load critical context at the start of every command execution.

**Scope**:
- `load_critical_context()` function
- Integration into CLI entry points
- Architecture decisions query
- Failure patterns query
- Component status query
- Integration points query
- Context injection into command prompts
- Performance optimization (caching, parallel queries)

**Dependencies**: FEAT-002

**Estimated Complexity**: Medium

---

### FEAT-005: Task Entity Storage

**Goal**: Store tasks as Graphiti entities instead of markdown files.

**Scope**:
- TaskEntity dataclass definition
- Create task as Graphiti episode
- Task dependency edges (BLOCKS, DEPENDS_ON, PARENT_OF)
- Read task by ID
- Update task status/properties
- List tasks with filters (status, priority, etc.)
- Ready work detection (tasks with no blockers)
- Migration from existing markdown tasks

**Dependencies**: FEAT-001

**Estimated Complexity**: High

---

### FEAT-006: Feature Entity Storage

**Goal**: Store features as Graphiti entities instead of YAML files.

**Scope**:
- FeatureEntity dataclass definition
- Create feature as Graphiti episode
- Feature-to-task edges (CONTAINS_TASK)
- Feature dependency edges (DEPENDS_ON_FEATURE)
- Read feature by ID
- Update feature status
- List features with filters
- Parallel group representation
- Migration from existing YAML features

**Dependencies**: FEAT-005

**Estimated Complexity**: Medium-High

---

### FEAT-007: Task CLI Commands

**Goal**: Provide CLI commands for task management backed by Graphiti.

**Scope**:
- `guardkit task create "description"` - Create new task
- `guardkit task show TASK-XXX` - Show task details with context
- `guardkit task ready` - List tasks ready to work (no blockers)
- `guardkit task update TASK-XXX --status done` - Update task
- `guardkit task list --status pending` - List with filters
- `guardkit task context TASK-XXX` - Show related knowledge
- Output formatting (table, JSON, markdown)

**Dependencies**: FEAT-005

**Estimated Complexity**: Medium

---

### FEAT-008: Outcome Episode Capture

**Goal**: Automatically capture outcomes when tasks complete to build learning over time.

**Scope**:
- Task completion outcome episodes
- Success/failure classification
- Pattern extraction from implementation
- Linking outcomes to tasks
- Review decision capture
- Quality gate result capture
- Query interface for "what worked for similar tasks"

**Dependencies**: FEAT-005

**Estimated Complexity**: Medium-High

---

### FEAT-009: Template/Agent Sync Hooks

**Goal**: Keep Graphiti in sync when templates or agents are created/modified.

**Scope**:
- Post-hook for `/template-create` command
- Post-hook for `/agent-enhance` command
- Sync template manifest to Graphiti
- Sync agent metadata to Graphiti
- Sync rules to Graphiti
- Extract and sync patterns
- Incremental update (not full re-seed)

**Dependencies**: FEAT-003

**Estimated Complexity**: Medium

---

### FEAT-010: Backward Compatibility Layer

**Goal**: Support gradual migration from markdown to Graphiti with fallback.

**Scope**:
- TaskStore abstraction with backend detection
- MarkdownTaskStore for legacy reading
- GraphitiTaskStore for new storage
- Auto-detection of which backend to use
- Configuration for backend preference
- Migration command (`guardkit migrate --to graphiti`)
- Validation that migration was successful

**Dependencies**: FEAT-005, FEAT-006

**Estimated Complexity**: Medium

---

## Feature Dependency Graph

```
FEAT-001 (Infrastructure)
    │
    ├──▶ FEAT-002 (System Context Seeding)
    │        │
    │        ├──▶ FEAT-003 (Development Knowledge Seeding)
    │        │        │
    │        │        └──▶ FEAT-009 (Template/Agent Sync Hooks)
    │        │
    │        └──▶ FEAT-004 (Session Context Loading)
    │
    ├──▶ FEAT-005 (Task Entity Storage)
    │        │
    │        ├──▶ FEAT-006 (Feature Entity Storage)
    │        │        │
    │        │        └──▶ FEAT-010 (Backward Compatibility)
    │        │
    │        ├──▶ FEAT-007 (Task CLI Commands)
    │        │
    │        └──▶ FEAT-008 (Outcome Episode Capture)
    │
    └──▶ FEAT-010 (Backward Compatibility)
```

---

## Implementation Priority

### Phase 1: Foundation + Immediate Value (Week 1)
1. **FEAT-001**: Infrastructure Setup
2. **FEAT-002**: System Context Seeding
3. **FEAT-004**: Session Context Loading

*Validates*: Does having system context in sessions prevent bad decisions?

### Phase 2: Development Knowledge (Week 2)
4. **FEAT-003**: Development Knowledge Seeding
5. **FEAT-009**: Template/Agent Sync Hooks

*Validates*: Does semantic search across templates/agents/patterns help?

### Phase 3: Task Migration (Week 3-4)
6. **FEAT-005**: Task Entity Storage
7. **FEAT-007**: Task CLI Commands
8. **FEAT-010**: Backward Compatibility Layer

*Validates*: Can we replace markdown tasks with Graphiti entities?

### Phase 4: Full Integration (Week 4-5)
9. **FEAT-006**: Feature Entity Storage
10. **FEAT-008**: Outcome Episode Capture

*Validates*: Does outcome capture improve future task execution?

---

## Superseded Work

The following Beads integration tasks are superseded by this feature set:

| Old Task | Reason | Replaced By |
|----------|--------|-------------|
| TASK-BI-001: TaskBackend interface | Graphiti provides this | FEAT-005 |
| TASK-BI-002: MarkdownBackend | Keep as migration source | FEAT-010 |
| TASK-BI-003: BeadsBackend | Not needed | FEAT-005 |
| TASK-BI-004: Backend registry | Single Graphiti backend | FEAT-001 |
| TASK-BI-005: Configuration | Graphiti config instead | FEAT-001 |
| TASK-BI-006-011 | Various Beads features | Various FEAT-* |

---

## Next Steps

1. Create detailed feature documents for each FEAT-XXX
2. Run `/feature-plan` on each to generate tasks with clarifying questions
3. Review and refine based on clarifying question responses
4. Begin implementation with Phase 1 features

---

## Open Questions for Feature Planning

These questions will likely surface during `/feature-plan` clarifying questions:

### Infrastructure (FEAT-001)
- Where should Docker Compose live? (repo root vs .guardkit/)
- Should Graphiti be optional or required?
- What's the graceful degradation strategy?

### Task Storage (FEAT-005)
- Should task IDs change format? (TASK-XXX vs Graphiti UUIDs)
- How to handle task history/versioning?
- What's the query performance requirement?

### Migration (FEAT-010)
- Automatic migration or explicit command?
- Keep markdown as backup?
- What happens to existing task history?

### CLI (FEAT-007)
- Match Beads CLI style (`bd ready`) or GuardKit style (`guardkit task ready`)?
- Interactive mode vs pure CLI?
- Output formats (JSON for scripting, table for humans)?
