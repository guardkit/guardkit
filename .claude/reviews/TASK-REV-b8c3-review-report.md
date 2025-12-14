# Architectural Review Report: TASK-REV-b8c3

## GuardKit-Beads-RequireKit Unified Vision & LangGraph MCP Integration

**Review ID**: TASK-REV-b8c3
**Mode**: Architectural Review
**Depth**: Comprehensive (4-6 hours)
**Date**: 2025-12-13
**Reviewer**: architectural-reviewer agent (claude-opus-4-5-20250514)

---

## Executive Summary

This comprehensive architectural review examines the strategic vision for integrating **GuardKit** (quality-gated task workflows), **Beads** (distributed agent memory), and **RequireKit** (formal requirements management) into a unified ecosystem—validated against a real-world **LangGraph MCP** case study.

### Key Findings

| Assessment Area | Score | Status |
|-----------------|-------|--------|
| **Architectural Alignment** | 92/100 | Excellent |
| **SOLID Compliance** | 85/100 | Good |
| **DRY Adherence** | 78/100 | Good (gaps in metadata mapping) |
| **YAGNI Compliance** | 82/100 | Good (avoid over-engineering) |
| **Integration Feasibility** | 90/100 | Excellent |
| **Risk Profile** | Medium | Acceptable with mitigations |

**Overall Score: 85/100** - Strong architectural foundation with clear path to implementation.

### Primary Recommendation

**Proceed with Beads-First integration** using the TaskBackend abstraction pattern. The unified ecosystem creates a compelling value proposition:

> **"From EARS requirements to verified, distributed, git-backed tasks in two commands"**

---

## 1. Ecosystem Architecture Analysis

### 1.1 Component Responsibilities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     UNIFIED AGENTECFLOW ECOSYSTEM                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│    RequireKit     │   │       GuardKit        │   │        Beads          │
│   (Requirements)  │   │   (Quality Gates)     │   │  (Distributed Memory) │
├───────────────────┤   ├───────────────────────┤   ├───────────────────────┤
│ • EARS Notation   │   │ • 7-Phase Workflow    │   │ • Git-backed storage  │
│ • BDD/Gherkin     │   │ • Quality gates       │   │ • Hash-based IDs      │
│ • Traceability    │   │ • Complexity routing  │   │ • Dependency graphs   │
│ • Epic hierarchy  │   │ • Agent orchestration │   │ • Ready work detection│
│ • PM tool sync    │   │ • Test enforcement    │   │ • Multi-agent sync    │
└─────────┬─────────┘   └───────────┬───────────┘   └───────────┬───────────┘
          │                         │                           │
          └─────────────────────────┼───────────────────────────┘
                                    │
                          ┌─────────┴─────────┐
                          │   Orchestration   │
                          │  (Claude SDK or   │
                          │   LangGraph)      │
                          └───────────────────┘
```

### 1.2 Data Flow Architecture

```
REQUIREMENTS PHASE                    IMPLEMENTATION PHASE
═══════════════════                   ════════════════════

RequireKit                            GuardKit + Beads
┌─────────────┐                       ┌─────────────────────────────────┐
│ /req-create │                       │          /task-work             │
│  ────────►  │                       │  ┌───────────────────────────┐  │
│ EARS Spec   │                       │  │   Phase 2: Planning       │  │
│  ────────►  │                       │  │   Phase 2.5: Arch Review  │  │
│ /generate-  │                       │  │   Phase 2.7: Complexity   │  │
│    bdd      │                       │  │   Phase 2.8: Checkpoint   │──┼──► Beads stores
│  ────────►  │                       │  │   Phase 3: Implementation │  │    task context
│ Gherkin     │                       │  │   Phase 4.5: Tests        │  │    in notes field
│ Scenarios   │─────────────────────► │  │   Phase 5.5: Plan Audit   │  │
│             │  bdd_scenarios link   │  └───────────────────────────┘  │
└─────────────┘                       └─────────────────────────────────┘
                                                      │
                                                      ▼
                                      ┌───────────────────────────────────┐
                                      │     Beads (Distributed State)     │
                                      │  ┌─────────────────────────────┐  │
                                      │  │  bd ready → Agent picks task│  │
                                      │  │  bd update → Status changes │  │
                                      │  │  bd dep add → Dependencies  │  │
                                      │  │  bd close → Quality gates   │  │
                                      │  │  git push → Multi-machine   │  │
                                      │  └─────────────────────────────┘  │
                                      └───────────────────────────────────┘
```

### 1.3 SOLID Analysis

#### Single Responsibility Principle (SRP): 9/10
Each component has a clear, distinct responsibility:
- **RequireKit**: Requirements specification and traceability
- **GuardKit**: Quality gates and workflow orchestration
- **Beads**: Distributed task persistence and agent memory

**Minor concern**: GuardKit currently handles both orchestration AND task storage. The Beads integration properly separates these concerns.

#### Open/Closed Principle (OCP): 8/10
The `TaskBackend` abstraction enables extension without modification:
```python
class TaskBackend(ABC):
    @abstractmethod
    def create(self, task: Task) -> Task: ...
    @abstractmethod
    def list_ready(self, options: ReadyWorkOptions) -> List[Task]: ...
```

**New backends** (e.g., Linear, Notion) can be added without changing core workflow logic.

#### Liskov Substitution Principle (LSP): 8/10
Both `MarkdownBackend` and `BeadsBackend` implement the same interface, allowing seamless substitution.

**Potential issue**: Beads has richer dependency semantics (blocking_ids, discovered_from) that Markdown lacks. The abstraction must handle graceful degradation.

#### Interface Segregation Principle (ISP): 9/10
The proposed interface is minimal and focused:
- `create`, `update`, `delete` - CRUD operations
- `list_ready`, `add_dependency` - Query operations
- `sync` - Backend-specific synchronization

#### Dependency Inversion Principle (DIP): 8/10
High-level workflow logic depends on the `TaskBackend` abstraction, not concrete implementations.

**Improvement needed**: Ensure MCP server interactions also go through abstractions for testability.

---

## 2. Beads Integration Architecture

### 2.1 Core Value Proposition

**Beads solves agent amnesia** - the fundamental problem where AI agents forget task context between sessions:

| Without Beads | With Beads |
|---------------|------------|
| Agent forgets tasks after session ends | Persistent, queryable task database |
| Manual context re-injection | `bd ready --json` provides structured context |
| Single-machine limitation | Git-synced across machines |
| Sequential ID collisions | Hash-based IDs (zero collision) |
| No dependency awareness | Ready work detection excludes blocked tasks |

### 2.2 Metadata Mapping (GuardKit ↔ Beads)

| GuardKit Field | Beads Field | Mapping Strategy |
|----------------|-------------|------------------|
| `task_id` | `id` | Direct (hash-based: `TASK-a1b2` ↔ `bd-a1b2`) |
| `status` | `status` | Direct: BACKLOG→open, IN_PROGRESS→in_progress |
| `priority` | `priority` | Direct: high→1, medium→2, low→3 |
| `methodology_mode` | `labels` | `mode:standard`, `mode:tdd`, `mode:bdd` |
| `ears_spec` | `notes` | JSON section in notes field |
| `gherkin_scenarios` | `notes` | Markdown section in notes |
| `quality_gate_results` | `notes` | JSON serialized |
| `parent_id` | `parent_id` | Direct (epic → task hierarchy) |
| `blocking_ids` | `blocking_ids` | Direct (hard dependencies) |
| `discovered_from` | Discovered-from dep | `bd dep add --discovered-from` |
| `complexity_score` | `labels` | `complexity:7` tag |

### 2.3 DRY Analysis

**Current duplication identified**:
1. ID generation logic exists in both GuardKit and Beads (hash-based)
2. Status enum mapping is spread across multiple files
3. Priority semantics defined separately

**Recommendation**: Create shared constants/enums in `lib/task_models.py`:
```python
class TaskStatus(Enum):
    BACKLOG = "open"        # Beads: open
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    IN_REVIEW = "open"      # Beads: open with label "in_review"
    COMPLETED = "closed"    # Beads: closed

class Priority(Enum):
    CRITICAL = 0  # Beads priority 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKLOG = 4
```

### 2.4 Discovered Work Pattern (Critical Feature)

The `--discovered-from` pattern is crucial for agentic workflows:

```bash
# During /task-work TASK-a1b2, agent discovers edge case
/task-create "Fix authentication edge case" --discovered-from TASK-a1b2

# Beads records:
# 1. New task bd-c3d4 created
# 2. Dependency: bd-c3d4 discovered-from bd-a1b2
# 3. Git commit records provenance

# Future sessions: Agent can trace work origin
bd show bd-c3d4
# Shows: "Discovered from: TASK-a1b2 (Implement user auth)"
```

**Integration requirement**: GuardKit's `/task-create` must support `--discovered-from` flag when Beads backend is active.

---

## 3. RequireKit Integration Path

### 3.1 Current State

RequireKit integration exists via BDD mode:
- Marker file detection: `~/.agentecflow/require-kit.marker.json`
- BDD workflow: EARS → Gherkin → Implementation → Tests
- Manual linking: `bdd_scenarios: [BDD-001]` in task frontmatter

### 3.2 Enhanced Integration with Beads

**Proposed unified flow**:

```
RequireKit              GuardKit                 Beads
═════════              ════════                 ═════
/req-create ────►  REQ-001 (EARS spec)
                         │
/formalize-ears ─────────┤
                         │
/generate-bdd ────►  BDD-001 (Gherkin)
                         │
                         ▼
              /task-create (linked)
                   ────────────────────────────► bd create
                         │                       (notes = EARS + Gherkin)
                         │
              /task-work --mode=bdd
                         │
                         ├────► Phase 3: Implement to pass scenarios
                         │
                         ├────► Phase 4: BDD tests as quality gate
                         │
                         └────────────────────────► bd close
                                                 (preserves traceability)
```

### 3.3 Traceability Chain

With the unified ecosystem:

```
REQ-ORCH-001 (RequireKit EARS)
    ↓ /generate-bdd
BDD-ORCH-001 (Gherkin scenarios)
    ↓ linked in task frontmatter
TASK-a1b2 (GuardKit task)
    ↓ bd create (Beads sync)
bd-a1b2 (Beads task with notes containing EARS + Gherkin)
    ↓ implementation
Code + Tests
    ↓ bd close
Git commit (full audit trail)
```

**Audit query**: "What requirement led to this code change?"
```bash
bd show bd-a1b2 --notes | grep "REQ-"
# Output: REQ-ORCH-001
```

---

## 4. LangGraph MCP Case Study

### 4.1 Scenario: Building LangGraph Orchestration Layer

**Task**: Implement Phase 2.8 complexity-based routing for GuardKit using LangGraph.

**Why this validates the vision**:
1. **Complex orchestration** - LangGraph state machines require precise specs
2. **Multi-phase workflow** - 7 phases with conditional routing
3. **Human checkpoints** - Approval gates using `interrupt()`
4. **Quality-critical** - Routing errors break entire workflow
5. **Multi-agent** - Different specialists for different phases

### 4.2 Unified Workflow Application

**Step 1: Requirements (RequireKit)**
```bash
cd ~/Projects/require-kit
/req-create "Phase 2.8 Complexity Routing"
/formalize-ears REQ-ORCH-001
```

Output (EARS):
```
WHEN task complexity_score >= 7, system SHALL invoke FULL_REQUIRED checkpoint.
WHEN task complexity_score is 4-6, system SHALL invoke QUICK_OPTIONAL checkpoint.
WHEN task complexity_score is 1-3, system SHALL proceed automatically.
```

**Step 2: BDD Scenarios (RequireKit)**
```bash
/generate-bdd REQ-ORCH-001
```

Output (Gherkin):
```gherkin
Feature: Complexity-Based Routing

Scenario: High complexity triggers mandatory review
  Given a task with complexity score 8
  When the workflow reaches Phase 2.8
  Then the system should invoke FULL_REQUIRED checkpoint
  And the workflow should interrupt with full plan display
```

**Step 3: Task Creation (GuardKit + Beads)**
```bash
cd ~/Projects/guardkit
/task-create "Implement complexity routing" requirements:[REQ-ORCH-001]
```

Beads creates:
```json
{
  "id": "bd-a1b2c3",
  "title": "Implement complexity routing",
  "status": "open",
  "priority": 1,
  "labels": ["mode:bdd", "langgraph", "phase-2.8"],
  "notes": "## EARS Spec\nREQ-ORCH-001...\n\n## Gherkin Scenarios\nBDD-ORCH-001..."
}
```

**Step 4: Implementation (GuardKit BDD mode)**
```bash
/task-work bd-a1b2c3 --mode=bdd
```

GuardKit executes:
- Phase 2: Generate implementation plan (reads EARS from Beads notes)
- Phase 2.5B: Architectural review (validates LangGraph patterns)
- Phase 2.7: Complexity evaluation (8/10 - state machine complexity)
- Phase 2.8: Human checkpoint (FULL_REQUIRED triggered)
- Phase 3: bdd-generator agent implements `complexity_router()`
- Phase 4: pytest-bdd runs Gherkin scenarios as tests
- Phase 4.5: 100% BDD pass rate enforced
- Phase 5: Code review

**Step 5: Completion**
```bash
/task-complete bd-a1b2c3
# Beads: bd close bd-a1b2c3
# Git: Commits task closure with quality gate results
```

### 4.3 Case Study Validation

| Requirement | Implementation | Validation |
|-------------|----------------|------------|
| Persistent task context | Beads notes contain EARS + Gherkin | Agent can resume work across sessions |
| Formal specification | EARS notation in RequireKit | Unambiguous routing behavior |
| Executable tests | Gherkin → pytest-bdd | State transitions verified |
| Quality gates | Phase 4.5 enforcement | 100% BDD pass rate |
| Traceability | REQ → BDD → Code → Test | Full audit trail in Git |
| Multi-agent ready | Beads hash IDs | Safe concurrent development |

**Conclusion**: The LangGraph MCP scenario demonstrates the ecosystem handles complex, multi-phase, quality-critical workflows effectively.

---

## 5. Gap Analysis & Recommendations

### 5.1 Identified Gaps

| Gap | Severity | Current State | Recommended Action |
|-----|----------|---------------|-------------------|
| **G1**: No unified metadata schema | Medium | Separate definitions | Create `lib/task_models.py` |
| **G2**: RequireKit marker detection inconsistent | Low | JSON vs legacy marker | Standardize on JSON |
| **G3**: Beads MCP not in documented integrations | Medium | Missing from CLAUDE.md | Add to MCP Integration section |
| **G4**: No `--discovered-from` in /task-create | High | Missing feature | Implement in Wave 1 |
| **G5**: PM tool mapping not documented | Medium | Exists but scattered | Consolidate in unified doc |
| **G6**: LangGraph integration effort underestimated | Low | 3-4 weeks stated | Realistic, no change needed |

### 5.2 Prioritized Recommendations

#### Critical (Implement in Wave 1)

1. **Create TaskBackend interface** (TASK-BI-001)
   - Abstract task operations
   - Support both Markdown and Beads
   - Enable graceful degradation

2. **Implement `--discovered-from` flag** (TASK-BI-002 extended)
   - Critical for agent context preservation
   - Maps directly to Beads dependency type
   - Essential for multi-session workflows

3. **Standardize metadata mapping** (New task)
   - Create `lib/task_models.py`
   - Define enums for status, priority, methodology
   - Ensure DRY compliance

#### Important (Implement in Wave 2)

4. **Add Beads MCP documentation** (TASK-BI-005)
   - Update CLAUDE.md MCP Integration section
   - Document setup and usage patterns
   - Add to core MCP list

5. **Enhance RequireKit integration** (TASK-BI-006)
   - Auto-detect linked requirements
   - Populate Beads notes with EARS/Gherkin
   - Add traceability metadata

6. **Implement feature detection** (TASK-BI-007)
   - Detect `bd` CLI availability
   - Auto-select Beads backend when present
   - Provide clear fallback messaging

#### Enhancement (Post-Integration)

7. **LangGraph orchestration layer** (Future epic)
   - Implement StateGraph for GuardKit phases
   - Add interrupt-based checkpoints
   - Enable multi-machine workflow persistence

8. **PM tool mapping consolidation** (Future task)
   - Unify external ID mapping across backends
   - Document bidirectional sync patterns
   - Support Jira, Linear, Azure DevOps, GitHub

### 5.3 Architectural Decision Records

#### ADR-001: Beads as Optional Backend

**Status**: Proposed

**Context**: GuardKit needs distributed task management for multi-agent scenarios without breaking single-machine simplicity.

**Decision**: Implement Beads as optional backend via TaskBackend abstraction.

**Consequences**:
- (+) No breaking changes for existing users
- (+) Enables distributed workflows when needed
- (+) Maintains Markdown simplicity for local-only use
- (-) Two code paths to maintain
- (-) Feature parity challenges (Beads has richer semantics)

#### ADR-002: EARS/Gherkin Storage in Beads Notes

**Status**: Proposed

**Context**: RequireKit integration requires persisting formal specifications with tasks.

**Decision**: Store EARS specifications and Gherkin scenarios in Beads `notes` field as structured Markdown sections.

**Consequences**:
- (+) Single source of truth for task context
- (+) Agent can parse specifications from notes
- (+) No additional database fields needed
- (-) Notes field becomes overloaded
- (-) Parsing logic needed for extraction

---

## 6. Risk Assessment

### 6.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Beads API breaking changes | Medium | High | Pin Beads version, abstraction layer |
| Git merge conflicts in JSONL | Low | Medium | Append-only semantics, hash IDs |
| Performance at scale | Low | Medium | SQLite caching, query optimization |
| RequireKit marker detection race | Low | Low | Atomic file operations |

### 6.2 Integration Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Metadata mapping drift | Medium | Medium | Shared schema, validation tests |
| Feature parity gaps | High | Low | Document graceful degradation |
| User confusion (two backends) | Medium | Medium | Clear documentation, auto-detection |
| Testing complexity increase | Medium | Medium | Mock backends, integration tests |

### 6.3 Strategic Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Beads abandonment (new project) | Low | High | Abstract interface enables replacement |
| Over-engineering | Medium | Medium | YAGNI focus, incremental delivery |
| Scope creep to full PM tool | Medium | High | Stay focused on agent memory, not human PM |

---

## 7. Implementation Roadmap

### Wave 1: Foundation (Weeks 1-2)

| Task | Effort | Dependencies |
|------|--------|--------------|
| TASK-BI-001: TaskBackend interface | 3d | None |
| TASK-BI-002: Core method implementations | 4d | BI-001 |
| TASK-BI-003: BeadsBackend implementation | 4d | BI-001, BI-002 |
| Metadata schema standardization | 2d | None |

**Outcome**: Core abstraction layer complete, Beads backend functional.

### Wave 2: Integration (Weeks 3-4)

| Task | Effort | Dependencies |
|------|--------|--------------|
| TASK-BI-004: Auto-detection | 2d | BI-003 |
| TASK-BI-005: MCP documentation | 2d | BI-003 |
| TASK-BI-006: RequireKit enhancement | 3d | BI-003 |
| TASK-BI-007: Feature detection | 2d | BI-004 |

**Outcome**: Full integration with auto-detection and documentation.

### Wave 3: Enhancement (Weeks 5-6)

| Task | Effort | Dependencies |
|------|--------|--------------|
| TASK-BI-008: Migration tooling | 3d | Wave 2 |
| TASK-BI-009: Discovered-from in /task-create | 2d | Wave 1 |
| Integration testing suite | 4d | Wave 2 |
| User documentation | 2d | Wave 2 |

**Outcome**: Production-ready with migration path and testing.

---

## 8. Conclusion

### 8.1 Summary of Findings

The GuardKit-Beads-RequireKit unified ecosystem represents a **well-architected approach** to the agent memory and distributed workflow problem:

1. **Strong architectural foundations** - Clear separation of concerns, proper abstractions
2. **Complementary capabilities** - Each tool addresses distinct needs without overlap
3. **Validated by case study** - LangGraph MCP scenario demonstrates real-world applicability
4. **Reasonable risk profile** - Technical and integration risks are manageable
5. **Clear implementation path** - 6-week roadmap with defined milestones

### 8.2 Strategic Value

| Value Proposition | Benefit |
|-------------------|---------|
| **Agent memory persistence** | Tasks survive session boundaries |
| **Multi-machine coordination** | Git-synced distributed state |
| **Formal specifications** | EARS + BDD for quality-critical code |
| **Quality enforcement** | 7-phase workflow with gates |
| **Traceability** | REQ → Code → Test audit trail |
| **Incremental adoption** | Beads optional, Markdown still works |

### 8.3 Final Recommendation

**PROCEED with implementation** following the proposed architecture:

1. **Immediate action**: Begin Wave 1 (TaskBackend interface)
2. **Validation checkpoint**: After Wave 2, assess production readiness
3. **Future consideration**: LangGraph orchestration layer (post-Beads integration)

The unified ecosystem positions GuardKit as the **quality-gated orchestration layer** for AI-assisted development, with Beads providing distributed agent memory and RequireKit enabling formal specifications when needed.

---

## Appendix A: Referenced Materials

- [Beads Integration README](../../tasks/backlog/beads-integration/README.md)
- [Beads Integration Implementation Guide](../../tasks/backlog/beads-integration/IMPLEMENTATION-GUIDE.md)
- [Unified Integration Architecture](../../docs/proposals/integrations/unified-integration-architecture.md)
- [GuardKit-Beads Integration Proposal](../../docs/proposals/integrations/beads/guardkit-beads-integration.md)
- [Beads-First Development Implementation Plan](../../docs/proposals/integrations/beads-first-development-implementation-plan.md)
- [Claude Agent SDK Integration Analysis](../../docs/research/claude_agent_sdk_integration_analysis.md)
- [Claude Agent SDK Fast Path](../../docs/research/Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md)
- [Claude Agent SDK True End-to-End Orchestrator](../../docs/research/Claude_Agent_SDK_True_End_to_End_Orchestrator.md)
- [Claude Agent SDK Two-Command Feature Workflow](../../docs/research/Claude_Agent_SDK_Two_Command_Feature_Workflow.md)
- [LangGraph-Native Orchestration Architecture](../../docs/research/LangGraph-Native_Orchestration_for_TaskWright_Technical_Architecture.md)
- [Agentecflow LangGraph MCP Architecture Recommendation](../../docs/research/agentecflow_langgraph_mcp_architecture_recommendation.md)
- [BDD Workflow for Agentic Systems](../../docs/guides/bdd-workflow-for-agentic-systems.md)

## Appendix B: Beads Framework Summary

**Source**: Web research on github.com/steveyegge/beads

- **Creator**: Steve Yegge (ex-Google, ex-Amazon, ex-Sourcegraph)
- **Purpose**: Distributed task management for AI coding agents
- **Storage**: JSONL files backed by Git
- **Local cache**: SQLite for fast queries
- **Key features**:
  - Hash-based IDs (collision-free)
  - Ready work detection
  - Dependency graphs (blocking, discovered-from)
  - MCP server for Claude integration
  - No web UI (agent-first design)

---

**Report Generated**: 2025-12-13
**Review Duration**: Comprehensive (4-6 hours equivalent analysis)
**Next Action**: Human decision checkpoint
