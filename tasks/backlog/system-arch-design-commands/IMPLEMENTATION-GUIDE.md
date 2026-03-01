# Implementation Guide: System Architecture & Design Commands

## Data Flow: Read/Write Paths

This is the most important diagram — it shows every write path and every read path for the four new commands.

```mermaid
flowchart LR
    subgraph Writes["Write Paths"]
        W1["/system-arch\nwrite_adr()\nwrite_context_diagram()\nwrite_container_diagram()"]
        W2["/system-design\nwrite_ddr()\nwrite_api_contract()\nwrite_data_model()\nwrite_component_diagram()"]
        W3["/arch-refine\nsupersede_adr()\nflag_stale()"]
        W4["/design-refine\nsupersede_ddr()\nupdate_api_contract()"]
    end

    subgraph Storage["Storage"]
        S1[("Graphiti\nproject_architecture\nproject_decisions")]
        S2[("Graphiti\nproject_design\napi_contracts")]
        S3[("docs/architecture/\ndecisions/\ndiagrams/")]
        S4[("docs/design/\ndecisions/\ncontracts/\nmodels/")]
    end

    subgraph Reads["Read Paths"]
        R1["/system-design\nhas_architecture_context()\nread bounded contexts"]
        R2["/system-plan\nget_relevant_context()\nread ADRs"]
        R3["/feature-spec\nread domain entities\nread API contracts"]
        R4["/feature-plan\nread architecture summary"]
        R5["/arch-refine\nsemantic_search()\nimpact_analysis()"]
        R6["/design-refine\nsearch_design_context()\nfeature_staleness()"]
    end

    W1 -->|"upsert_episode()"| S1
    W1 -->|"ArchitectureWriter"| S3
    W2 -->|"upsert_episode()"| S2
    W2 -->|"DesignWriter"| S4
    W3 -->|"upsert superseded + new"| S1
    W3 -->|"stale flag"| S2
    W4 -->|"upsert superseded + new"| S2

    S1 -->|"has_architecture_context()"| R1
    S1 -->|"get_relevant_context()"| R2
    S2 -->|"search_design_context()"| R3
    S1 -->|"context_loader"| R4
    S1 -->|"semantic_search()"| R5
    S2 -->|"search_design_context()"| R6
    S2 -->|"feature_staleness()"| R6

    style W1 fill:#cfc,stroke:#090
    style W2 fill:#cfc,stroke:#090
    style W3 fill:#ffc,stroke:#990
    style W4 fill:#ffc,stroke:#990
```

_Green = new write paths. Yellow = refinement/update paths. All read paths have corresponding write paths — no disconnections detected._

## Integration Contracts

```mermaid
sequenceDiagram
    participant SA as /system-arch
    participant G1 as Graphiti<br/>project_architecture
    participant SD as /system-design
    participant G2 as Graphiti<br/>project_design
    participant SP as /system-plan
    participant FS as /feature-spec

    SA->>G1: upsert_episode(ADR-ARCH-001)
    SA->>G1: upsert_episode(SystemContext)
    SA->>G1: upsert_episode(Containers)

    SD->>G1: has_architecture_context()
    G1-->>SD: true (bounded contexts, ADRs)

    SD->>G2: upsert_episode(DDR-001)
    SD->>G2: upsert_episode(ApiContract)
    SD->>G2: upsert_episode(DataModel)

    SP->>G1: get_relevant_context("feature X")
    G1-->>SP: ADRs, bounded contexts, constraints
    Note over SP: Planning session grounded in architecture

    FS->>G2: search_design_context("user entity")
    G2-->>FS: Real domain entities, API contracts
    Note over FS: Gherkin references real endpoints
```

_This diagram shows the sequential data flow through the pipeline. Each downstream command reads context seeded by upstream commands._

## Task Dependencies

```mermaid
graph TD
    T1[TASK-SAD-001<br/>Temporal Spike<br/>C:4] --> T8[TASK-SAD-008<br/>/arch-refine spec<br/>C:7]
    T1 --> T9[TASK-SAD-009<br/>/design-refine spec<br/>C:6]

    T2[TASK-SAD-002<br/>Update ArchDecision<br/>C:3] --> T4[TASK-SAD-004<br/>Templates<br/>C:5]
    T2 --> T6[TASK-SAD-006<br/>/system-arch spec<br/>C:8]
    T2 --> T8

    T3[TASK-SAD-003<br/>Design Entities<br/>C:5] --> T4
    T3 --> T5[TASK-SAD-005<br/>Graphiti + Writer<br/>C:6]

    T4 --> T6
    T5 --> T7[TASK-SAD-007<br/>/system-design spec<br/>C:8]
    T5 --> T9

    T3 --> T7
    T6 --> T10[TASK-SAD-010<br/>Integration Testing<br/>C:5]
    T7 --> T10
    T8 --> T10
    T9 --> T10

    style T1 fill:#cfc,stroke:#090
    style T2 fill:#cfc,stroke:#090
    style T3 fill:#cfc,stroke:#090
    style T4 fill:#cfc,stroke:#090
    style T5 fill:#cfc,stroke:#090
    style T6 fill:#ffc,stroke:#990
    style T7 fill:#ffc,stroke:#990
```

_Green = can run in parallel within their wave. Yellow = high-complexity tasks requiring focused attention. C:N = complexity score._

## Execution Strategy

### Wave 1: Entity Foundation (Days 1-3)

3 tasks, all can run in parallel:

| Task | Title | Complexity | Parallel Group |
|------|-------|------------|---------------|
| TASK-SAD-001 | Temporal superseding spike | 4 | wave1 |
| TASK-SAD-002 | Update ArchitectureDecision dataclass | 3 | wave1 |
| TASK-SAD-003 | Create design entity dataclasses | 5 | wave1 |

**No file conflicts**: spike touches `tests/`, dataclass update touches `architecture_context.py`, new entities are new files.

### Wave 2: Templates + Services (Days 4-6)

2 tasks, can run in parallel:

| Task | Title | Complexity | Parallel Group |
|------|-------|------------|---------------|
| TASK-SAD-004 | Update ADR + create templates | 5 | wave2 |
| TASK-SAD-005 | SystemDesignGraphiti + DesignWriter | 6 | wave2 |

**No file conflicts**: templates are in `guardkit/templates/`, services are in `guardkit/planning/`.

### Wave 3: Command Specs (Days 7-14)

4 tasks with partial parallelisation:

| Task | Title | Complexity | Parallel Group |
|------|-------|------------|---------------|
| TASK-SAD-006 | /system-arch command spec | 8 | wave3a |
| TASK-SAD-007 | /system-design command spec | 8 | wave3a |
| TASK-SAD-008 | /arch-refine command spec | 7 | wave3b |
| TASK-SAD-009 | /design-refine command spec | 6 | wave3b |

**Parallel groups**: SAD-006 + SAD-007 can run in parallel (different files). SAD-008 + SAD-009 can run in parallel after SAD-001 spike completes.

### Wave 4: Integration Testing (Days 15-18)

1 task, sequential (depends on all Wave 3 tasks):

| Task | Title | Complexity |
|------|-------|------------|
| TASK-SAD-010 | Integration testing | 5 |

## Architecture Notes

### Existing Infrastructure Reuse

| Component | Existing | Reuse Plan |
|-----------|----------|------------|
| `SystemPlanGraphiti` | `guardkit/planning/graphiti_arch.py` | Extend or wrap for `/system-arch` |
| `ArchitectureWriter` | `guardkit/planning/architecture_writer.py` | Direct reuse for ADR/diagram writing |
| `ArchitectureDecision` | `guardkit/knowledge/entities/architecture_context.py` | Extend with 3 new fields |
| Entity pattern | `guardkit/knowledge/entities/*.py` | Follow for new entities |
| Template pattern | `guardkit/templates/*.md.j2` | Follow for new templates |

### New Components

| Component | File | Purpose |
|-----------|------|---------|
| `DesignDecision` | `guardkit/knowledge/entities/design_decision.py` | DDR entity |
| `ApiContract` | `guardkit/knowledge/entities/api_contract.py` | Per-bounded-context contract |
| `DataModel` | `guardkit/knowledge/entities/data_model.py` | Domain entities and relationships |
| `SystemDesignGraphiti` | `guardkit/planning/graphiti_design.py` | Graphiti ops for design layer |
| `DesignWriter` | `guardkit/planning/design_writer.py` | File output for design artefacts |
| `container.md.j2` | `guardkit/templates/container.md.j2` | C4 L2 Container diagram |
| `component-l3.md.j2` | `guardkit/templates/component-l3.md.j2` | C4 L3 Component diagram |
| `api-contract.md.j2` | `guardkit/templates/api-contract.md.j2` | API contract markdown |
| `ddr.md.j2` | `guardkit/templates/ddr.md.j2` | Design Decision Record |

### Key Technical Decisions

1. **ADR convention**: `docs/architecture/decisions/ADR-{PREFIX}-{NNN}.md` — matches existing code
2. **DDR convention**: `docs/design/decisions/DDR-{NNN}.md` — parallel structure
3. **Temporal superseding**: Data-level encoding via `superseded_by`/`supersedes` fields
4. **C4 syntax**: Native Mermaid C4 keywords (`C4Container`, `C4Component`)
5. **OpenAPI validation**: `openapi-spec-validator` as quality gate
6. **Protocol extensibility**: User-selectable protocol support in `/system-design`

## Risk Mitigations

| Risk | Mitigation | Owner |
|------|-----------|-------|
| Temporal superseding unproven | TASK-SAD-001 spike before Wave 3 | Wave 1 |
| OpenAPI generation quality | Validation gate in /system-design spec | TASK-SAD-007 |
| Diagram splitting (>30 nodes) | Warning at review gate (MVP) | TASK-SAD-006 |
| ADR location conflict | Follow existing code convention | All tasks |

## Next Steps

1. Review this implementation guide
2. Start with Wave 1 tasks (all 3 can run in parallel)
3. Wave 1 completion unblocks Wave 2
4. Wave 2 completion unblocks Wave 3
5. Wave 3 completion unblocks Wave 4 (integration testing)

Start implementation:
```bash
/task-work TASK-SAD-001  # Temporal superseding spike
/task-work TASK-SAD-002  # Update ArchitectureDecision
/task-work TASK-SAD-003  # Create design entities
```
