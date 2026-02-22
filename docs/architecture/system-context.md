# System Context

> **System**: GuardKit
> **Purpose**: AI-assisted software development with quality gates that prevents broken code from reaching production
> **Methodology**: Modular
> **Deployment**: CLI tool via pip, optional Docker services (FalkorDB, Graphiti)
> **Tech Stack**: Python 3.13+ (Click CLI, asyncio, Pydantic v2), Claude Agent SDK, LangGraph

## Actors

| Actor | Role | Interaction Mode |
|-------|------|-----------------|
| **Developer** | Primary user. Plans features, reviews checkpoints, merges work | CLI commands in Claude Code |
| **Product Owner** | Defines requirements via RequireKit, approves feature scope | Markdown artifacts (REQ, BDD, FEAT specs) |
| **Player Agent** | Implementation role in AutoBuild. Writes code, runs tests | Claude Code subagent (spawned by Agent Invoker) |
| **Coach Agent** | Validation role in AutoBuild. Reviews against requirements contract | Claude Code subagent (spawned by Agent Invoker) |
| **AI Agent (General)** | Executes /task-work in standard mode. Plans, implements, tests | Claude Code via interactive commands |

## External Systems

| System | Integration | Purpose |
|--------|-------------|---------|
| **FalkorDB** | Direct (graphiti-core library) | Knowledge graph storage (temporal facts, architecture context) |
| **OpenAI API** | Via Graphiti | text-embedding-3-small for semantic search embeddings |
| **Conductor.build** | Compatible (hash-based task IDs) | Parallel development with Git worktree isolation |
| **PM Tools** | Metadata export (JIRA, Azure DevOps, Linear, GitHub) | Task/feature ID mapping |
| **MCP Servers** | Optional (context7, design-patterns) | Library documentation, pattern recommendations |
| **RequireKit** | One-way artifact flow (RequireKit -> GuardKit) | Requirements, BDD scenarios, feature specs |

## System Boundary

```mermaid
graph TB
    Dev[Developer] -->|CLI commands| GK[GuardKit CLI]
    Dev -->|Loose description| FS[/feature-spec]
    PO[Product Owner] -->|Requirements artifacts| RK[RequireKit]
    RK -->|REQ, BDD, FEAT specs| GK
    FS -->|.feature + summary + assumptions| GK
    GK -->|Subagent spawning| CC[Claude Code]
    GK -->|Knowledge read/write| FDB[(FalkorDB)]
    GK -->|Embeddings| OAI[OpenAI API]
    GK -.->|Optional| MCP[MCP Servers]
    GK -.->|Compatible| COND[Conductor.build]
    GK -.->|Metadata export| PM[PM Tools]

    style FS fill:#ff9,stroke:#333
```

## Integrations

### /feature-spec (Specification Pipeline)

- **Direction**: Developer -> `/feature-spec` -> `/feature-plan` -> AutoBuild
- **Artifacts**: `{name}.feature` (Gherkin), `{name}_assumptions.yaml` (assumptions manifest), `{name}_summary.md` (for `/feature-plan`)
- **Methodology**: Propose-Review (Specification by Example) — AI proposes Gherkin scenarios, human curates (see [ADR-FS-003](decisions/ADR-FS-003-propose-review-methodology.md))
- **Graphiti Seeding**: Individual scenarios seeded as distinct episodes to `feature_specs` group; assumptions seeded to `domain_knowledge` group
- **Key Principle**: Purely additive — existing workflows work unchanged when no Gherkin spec exists

### RequireKit

- **Direction**: One-way (RequireKit -> GuardKit)
- **Artifacts**: REQ-*.md (EARS notation), BDD-*.feature (Gherkin), FEAT-*.md (feature specs), EPIC-*.md
- **Key Principle**: GuardKit never calls RequireKit commands. Data flows through markdown artifacts only.
- **Traceability**: REQ -> BDD -> FEAT -> TASK -> Code -> Quality Gates -> Verified Implementation

### Conductor.build

- **Mode**: Passive compatibility (not active integration)
- **Features**: Hash-based task IDs prevent duplicates, Git worktree isolation for parallel execution, PM tool mapping for sequential IDs
- **Usage**: `/feature-build` creates worktrees in `.guardkit/worktrees/FEAT-XXX/`

### MCP Servers

- **context7**: Library documentation retrieval (resolves library ID -> fetches docs -> context injection)
- **design-patterns**: Pattern recommendations (optional, tied to complexity/task type)
- **Principle**: All MCPs optional. Falls back gracefully to training data. MCP failures logged as warnings, never block execution.
