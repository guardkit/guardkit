# System Architecture & Design Command — Ideation & Intent

**Date:** 2026-02-28  
**Author:** Rich  
**Status:** Ideation — Ready for `/feature-spec`  
**Source:** Voice conversation (iPad), synthesised via Claude  
**Target Commands:** `/system-arch`, `/system-design`, `/arch-refine` (new, sit upstream of `/system-plan`)

---

## 1. The Problem This Solves

GuardKit has a strong, battle-tested flow from feature idea → implementation:

```
/feature-spec → /feature-plan → AutoBuild (Player-Coach)
```

And `/system-plan` provides big-picture context grounding via the Graphiti knowledge graph, reducing LLM stochasticity. But there is a **missing upstream layer**: before you can plan or spec features, you need to have made the foundational architectural decisions — bounded contexts, domain model, API structure, multi-tenancy strategy, agent protocol integration points, infrastructure topology.

Currently those decisions happen informally, in the developer's head, or in ad-hoc documents that don't feed systematically into Graphiti and therefore don't reliably ground downstream commands. The result: `/system-plan` and `/feature-spec` work from incomplete context, and the stochastic nature of LLMs means those gaps get silently filled by assumption rather than decision.

**The goal:** a repeatable, codified process for system-level architecture and design that sits upstream of `/system-plan`, populates the Graphiti knowledge graph with the domain model and architectural decisions as first-class artefacts, and introduces mandatory C4 diagramming as an early verification gate.

---

## 2. Key Insights from the Ideation Session

### 2.1 The Factory Principle
The repeatable process is more important than any one project. FIM Proxy / FinProxy LPA Platform is the immediate vehicle, but the real objective is proving and refining a reusable architectural template that can be applied to any backend API platform. The factory produces repeatable, high-quality architectures the same way AutoBuild produces repeatable, high-quality feature implementations.

### 2.2 Target Platform Pattern
The API backend platform will need to serve multiple consumer types simultaneously:
- **React web apps** — human-facing UI clients
- **AI agents via agent-to-agent protocols** (e.g., MCP, A2A, ACP) — agentic consumers
- **Internal agentic AI flows** — AI embedded within the platform itself (not just a consumer)

This multi-consumer reality must be a first-class concern in the architecture, not retrofitted. The design of bounded contexts, API contracts, and state management must account for agent orchestration from the outset.

### 2.3 Stack Agnosticism as a Design Principle
The `/system-arch` command must be entirely stack-agnostic. It should work equally well whether the system is built on .NET, Go, Rust, Node, Python, or any other backend stack, and whether the frontend is React, Vue, HTMX, or absent entirely. Similarly, structural pattern choices — modular monolith, microservices, serverless, event-driven — are decisions the command helps the human make, not assumptions it bakes in.

The command should open with clarifying questions that establish these fundamentals as explicit decisions, capturing the rationale and alternatives rejected. This makes them first-class ADRs in Graphiti rather than silent defaults. Two questions that must always be asked early:

- **Structural pattern** — modular monolith vs microservices vs serverless vs event-driven, with trade-offs surfaced for the specific domain and team size
- **Technology stack** — backend language/framework, frontend approach (if applicable), data storage strategy

DDD remains a recommended structural lens regardless of stack — it gives both the human and the LLM a shared vocabulary for bounded contexts, aggregates, and domain events that is language-neutral and generation-friendly. But it should be offered as an approach, not mandated.

### 2.4 Graphiti as the Architectural Memory
The knowledge graph (Graphiti + FalkorDB) is not just for feature-level context. The architectural decisions, bounded contexts, domain model, and integration topology should be seeded into Graphiti **before** `/system-plan` or `/feature-spec` are run. This is what allows those downstream commands to work from grounded architectural reality rather than regenerating structure from scratch on every invocation.

The cognitive load reduction goal: a developer (or future team member) should be able to run `/system-plan` on a new feature and get responses that already "know" the domain, the bounded contexts, the integration decisions, and the warnings — without re-explaining the architecture in every session.

### 2.5 C4 Diagramming as a Verification Gate
**Validated pattern:** In task review and debugging sessions, forcing the LLM to diagram the system (sequence diagrams, flow diagrams) before analysing root cause produces better root-cause analysis approximately 9 out of 10 times. The first analysis without diagramming is often wrong. The diagram forces explicit mapping of flows and connections, surfacing contradictions and gaps that verbal analysis glosses over.

This same pattern should be applied architecturally: **C4 diagrams are a mandatory verification step in the architecture and design command**, not an optional output. By forcing the LLM to render C4 Context, Container, and Component diagrams from the proposed architecture, you catch integration and boundary issues before any feature-level work begins. This is earlier, cheaper discovery of structural problems.

Diagramming elements have already been introduced into some existing commands (believed to be in `/feature-plan`, `/feature-spec`, and/or `/task-review`). The `/system-arch` command should build on and extend this established pattern.

---

## 3. Proposed Command: `/system-arch`

### 3.1 Position in the Pipeline

```
/system-arch    ←── NEW: structural decisions, bounded contexts, C4 L1/L2 diagrams → Graphiti
     │
     ▼
/system-design  ←── NEW: API contracts, endpoint design, data models, OpenAPI → Graphiti
     │
     ▼
/system-plan    ←── existing: per-feature/sprint coherence, reads both layers from Graphiti
     │
     ▼
/feature-spec   ←── existing: Gherkin scenarios, assumptions manifest
     │
     ▼
/feature-plan   ←── existing: task decomposition, wave structure
     │
     ▼
AutoBuild       ←── existing: Player-Coach implementation loop
```

`/arch-refine` and `/design-refine` sit alongside their respective commands and are invoked
whenever architectural or design artefacts need to evolve. They feed updated artefacts back
into Graphiti using temporal superseding rather than silent replacement (see Section 5).

### 3.2 Core Responsibilities

The `/system-arch` command is responsible for:

1. **Domain Modelling** — Elicit and codify the core domain, bounded contexts, aggregate roots, and key domain events using DDD vocabulary. Output as structured ADRs and domain model artefact.

2. **Architectural Decision Records** — Capture technology choices, structural patterns (modular monolith, layered architecture, CQRS, etc.), integration strategies, and rejected alternatives. Every decision must have rationale and alternatives considered.

3. **C4 Diagram Generation** — Produce mandatory C4 Level 1 (System Context) and Level 2 (Container) diagrams as Mermaid. Optionally Level 3 (Component) for complex areas. Diagrams must be reviewed before the command completes — this is the verification gate.

4. **Multi-Consumer API Design** — Explicitly define how the API serves each consumer type: web clients, agents via protocol (MCP/A2A/ACP), and internal agentic flows. This shapes API contract design and authentication/authorisation strategy.

5. **Graphiti Seeding** — All outputs (ADRs, domain model, bounded context map, architecture warnings) are seeded into the project's Graphiti knowledge graph as the final step, making them available to all downstream commands.

6. **Infrastructure Topology** — High-level deployment topology, multi-tenancy strategy, observability hooks, and "scale without code change" design principles.

### 3.3 Propose-Review Methodology (consistent with `/feature-spec`)

Following the established propose-review pattern from `/feature-spec`:
- The command generates concrete proposals (bounded context diagram, decision options, C4 diagrams)
- The human curates — accept, reject, modify, defer
- Nothing is assumed silently — all inferences are marked `[ASSUMPTION]` with confidence level
- The propose-review cycle continues until the human explicitly confirms completion

### 3.4 Output Artefacts

| Artefact | Format | Purpose | Fed Into |
|----------|--------|---------|----------|
| Domain model | Markdown + YAML | Core domain, bounded contexts, aggregates | Graphiti |
| Architectural Decision Records | `docs/adr/ADR-XXX.md` | Decisions with rationale | Graphiti |
| C4 Context diagram | Mermaid in `.md` | System-level relationships | Review gate, docs |
| C4 Container diagram | Mermaid in `.md` | Services, datastores, external systems | Review gate, docs |
| C4 Component diagram (optional) | Mermaid in `.md` | Internal structure of key containers | Review gate, docs |
| Assumptions manifest | YAML | Architecture-level assumptions with confidence | `/system-plan`, docs |
| Architecture summary | Markdown | Human-readable overview for `/system-plan` consumption | `/system-plan` |
| Graphiti seed script | Bash | Commands to seed all artefacts into Graphiti | Automation |

---

## 4. Proposed Command: `/system-design`

### 4.1 Purpose and Scope

Where `/system-arch` answers *"what are the boundaries and why"*, `/system-design` answers *"given those boundaries, what exactly are the contracts"*. It is the detailed design layer — the bridge between architectural intent and implementable specifications.

You cannot write good API endpoints until you know your bounded contexts. `/system-design` therefore depends on `/system-arch` having run first, reading the bounded contexts and structural decisions from Graphiti before proposing any contracts.

### 4.2 Core Responsibilities

1. **API Contract Design** — For each bounded context, define the endpoint structure: resource naming, HTTP methods, request/response shapes, error codes, pagination, versioning strategy. Stack-agnostic at this level — REST, GraphQL, gRPC, or event-driven are all valid outputs depending on what `/system-arch` decided.

2. **Multi-Protocol Surface Design** — Explicitly design for each consumer type the architecture identified:
   - REST/HTTP for web clients
   - MCP tool definitions for agent consumers
   - A2A/ACP task schemas if relevant
   - Internal event contracts if the platform uses async flows

3. **Data Model Design** — Core entities per bounded context, relationships, key invariants. Not a full ORM schema — that's implementation detail — but enough to ground feature specs in real domain concepts.

4. **OpenAPI/Swagger Generation** — Produce an OpenAPI 3.x spec as a primary output artefact. This serves as the contract document for both human developers and AI-generated code. Where agent protocols are involved, generate their equivalent discovery/schema documents alongside.

5. **C4 Level 3 Components** — Where `/system-arch` produces L1/L2 diagrams, `/system-design` produces L3 (Component) diagrams for the containers being designed, showing internal structure and how API requests flow through layers.

6. **Graphiti Seeding** — API contracts, data models, and design decisions seeded into Graphiti so that `/feature-spec` Gherkin scenarios can reference real endpoints and domain entities rather than inventing them.

### 4.3 Output Artefacts

| Artefact | Format | Purpose | Fed Into |
|----------|--------|---------|----------|
| API contracts per bounded context | Markdown | Endpoint structure, request/response shapes, error codes | Graphiti, `/feature-spec` |
| OpenAPI 3.x specification | `openapi.yaml` | Machine-readable contract, Swagger UI | Graphiti, implementation |
| Agent protocol schemas | MCP tool definitions / A2A task schemas | Agent consumer contracts | Graphiti, agent integration |
| Data model | Markdown + YAML | Core entities, relationships, invariants | Graphiti |
| C4 Component diagrams | Mermaid in `.md` | Internal container structure, request flows | Review gate, docs |
| Design Decision Records | `docs/ddr/DDR-XXX.md` | Design choices with rationale | Graphiti |
| Graphiti seed script | Bash | Commands to seed all artefacts | Automation |

### 4.4 The Value of the Gate

With API contracts in Graphiti before any `/feature-spec` runs, Gherkin scenarios can reference real endpoint behaviour rather than inferring it. This closes a significant source of assumption-drift in the current flow — scenarios that describe `"the upload should succeed"` rather than inventing an imaginary endpoint that may conflict with what gets implemented.

---

## 5. Iterative Refinement: `/arch-refine` and `/design-refine`

### 5.1 The Living Artefacts Problem

Architecture and design are not one-shot activities. As a system is built and used, understanding of the problem domain improves, integration constraints surface, and earlier decisions turn out to be wrong or incomplete. The pipeline must support this evolution without it becoming ad-hoc.

The key distinction from feature-level iteration is that architectural and design artefacts are **shared upstream context**. When a bounded context changes, it potentially invalidates downstream feature specs. When an API contract evolves, existing Gherkin scenarios may reference a contract that no longer exists. Unmanaged evolution at this level creates silent inconsistency throughout the graph.

`/task-refine` is explicitly scoped to task-level code polish and is the wrong tool here — its concepts (state machine, quality gate re-execution, scope creep constraints) are all implementation-specific. The one concept worth carrying forward is the **session log**: tracking what changed, why, and when. Everything else is new ground.

### 5.2 Core Behaviours

**Impact analysis before changes.** Before applying any architectural or design change, the command shows the human what else is affected — which ADRs are invalidated, which downstream feature specs reference the changed area, which diagrams need redrawing. The human approves the impact scope before any edits happen. This prevents silent propagation of changes that break downstream artefacts.

**Graphiti temporal superseding, not silent replacement.** Graphiti's temporal model supports this natively: a revised decision is recorded as a new node that explicitly supersedes the prior one, with a reason and timestamp. This means the knowledge graph reflects the evolution of thinking rather than accumulating contradictions or losing history. The prior decision remains queryable — you can always ask "what did we decide before and why did we change it".

**C4 re-review gate.** Any diagram that changes must be re-confirmed by the human before the refinement is considered complete — the same gate as the initial command.

**Downstream staleness flags.** If a bounded context or API contract changes significantly, the command flags which feature specs may now reference stale contracts or domain concepts. The human decides whether to re-run `/feature-spec` on those areas or accept the delta as managed technical debt.

### 5.3 What Triggers a Refinement

Typical triggers for `/arch-refine`:
- A new integration requirement doesn't fit cleanly within the current bounded context boundaries
- A scaling constraint surfaces that changes the structural pattern decision
- A third-party dependency turns out to behave differently than the ADR assumed
- Domain understanding improves enough that the original context decomposition is visibly wrong

Typical triggers for `/design-refine`:
- An API endpoint proves awkward in practice once features start being built against it
- An agent protocol requirement wasn't known when `/system-design` ran
- A new bounded context was added in `/arch-refine` that needs its API surface designed
- The OpenAPI spec is discovered to be inconsistent with what AutoBuild actually implemented

### 5.4 Relationship to `/arch-refine` vs `/design-refine`

These may be one command with a scope flag (`/arch-refine --layer arch` vs `--layer design`) or two separate commands. The distinction matters because an architecture change often cascades into a design change, but a design change doesn't necessarily require re-examining the architecture. Separating them keeps the scope of each invocation clear and avoids over-triggering impact analysis.

This is an open question for the `/feature-spec` session.

---

## 6. Disambiguation: How Refinement Commands Know What You Mean

### 6.1 The Problem

When you invoke `/arch-refine` or `/design-refine`, the command needs to know which existing artefacts in Graphiti you're referring to before it can do anything useful. This is non-trivial: a real system might have dozens of ADRs, multiple bounded contexts or structural modules, many API contracts, and numerous data model entities. The command must resolve your natural language description to specific graph nodes — confidently enough to act, but not so confidently that it acts on the wrong things without asking.

This needs to work regardless of whether the project used DDD, whether you remember ADR numbers, and without requiring a taxonomy of IDs that the developer has to maintain mentally.

### 6.2 Primary Mechanism: Semantic Search + Explicit Confirmation

The default flow is:

1. You describe what you want to change in plain language: *"I need to change the data model for the payment processing part of the system"* or *"the open banking integration assumptions have changed"*
2. The command runs a semantic search against the project's Graphiti graph using the description as the query
3. It surfaces the closest matching artefacts — ranked by relevance, capped at a small number to avoid noise — and says: *"I think you're referring to these artefacts: [list]. Is that right?"*
4. You confirm, correct, or expand the scope before anything is touched
5. Only after confirmation does the command proceed to impact analysis and then changes

The confirmation step does double duty: it's both a disambiguation layer and the first part of the impact analysis gate. Getting it wrong at step 3 is cheap — you just correct it. Getting it wrong silently and proceeding would be expensive.

### 6.3 Structural Anchors Work Without DDD

DDD bounded context names make natural anchors when they exist — *"the Payment context"* maps cleanly to a graph node. But the same principle works with whatever structural vocabulary the project actually used:

- Service or module names: *"the auth service"*, *"the reporting module"*
- API resource names: *"the /transactions endpoints"*, *"the user profile API"*
- Database or storage concepts: *"the orders table"*, *"the event store"*
- Team or domain language: *"the checkout flow"*, *"the onboarding journey"*

Graphiti stores artefacts with the names and language used when they were seeded. If `/system-arch` recorded a module called "PaymentProcessor" and you say "payment processing", semantic search will find it. The command doesn't require DDD — it requires that whatever language was used in the original artefacts is close enough to what you use now.

### 6.4 Optional Explicit Scoping

For cases where the semantic search is likely to be ambiguous — a large system where multiple areas share vocabulary (e.g., "user" appears in auth, billing, and profile contexts) — the command should support optional scope hints that skip or narrow the search:

```bash
/arch-refine --scope "payment processing"
/design-refine --scope "open banking integration"
/arch-refine --adr ADR-004
/design-refine --ddr DDR-007,DDR-008
```

These are optional overrides, not requirements. The command must be fully usable without ever specifying an ID. Explicit scoping is an escape hatch for experienced users or for cases where natural language alone is genuinely ambiguous — not the primary interaction model.

### 6.5 Handling Over-Retrieval

The main failure mode to design against is the semantic search returning too many loosely related artefacts, making the confirmation step noisy and the impact analysis overwhelming. The mitigation is:

- Surface only the top N results by relevance score (suggested: 3-5 artefacts maximum in the initial confirmation)
- Group related artefacts together rather than listing them individually (e.g., "ADR-003 and its associated C4 diagram and data model" as one confirmation item)
- Provide a *"show more related artefacts"* option rather than dumping everything tangentially connected
- After confirmation, the full impact graph can be expanded — but the initial question should be focused enough to answer in a few seconds

### 6.6 What This Means for Graphiti Seeding Quality

This approach only works well if the artefacts were seeded with rich, descriptive content — not just file references or IDs. An ADR that says *"Use modular monolith pattern"* with a rationale paragraph about the specific domain context will be found by semantic search when someone says *"I want to change the architectural structure"*. An ADR that says *"ADR-001: Architecture"* with minimal content will not.

This is a quality constraint on `/system-arch` and `/system-design`: their Graphiti seeding step must produce semantically rich nodes, not just file-path references. The richer the seeding, the better the refinement commands work months later when the original context is no longer fresh.

---

## 7. C4 Diagramming as a First-Class Pattern

### 7.1 Justification
The task-review debugging pattern proves it: forcing diagrammatic thinking changes the analysis. The mechanism is that diagrams require *explicit* representation of every connection, flow, and dependency — you cannot hand-wave a diagram the way you can hand-wave a verbal description. This exposes:
- Missing integration points
- Unclear ownership of data
- Circular dependencies between bounded contexts
- Implicit assumptions about who calls whom

### 7.2 Integration with Existing Commands
An audit should be done of which existing commands already include diagramming instructions (believed to be `/task-review`, possibly `/feature-plan` or `/feature-spec`). The `/system-arch` command should reference and extend the established pattern, not invent a competing one. The goal is consistency: diagramming is a cross-cutting discipline that appears at the appropriate granularity in each command.

| Command | Diagram Granularity | Type |
|---------|-------------------|------|
| `/system-arch` | System Context, Container | C4 L1/L2 Mermaid |
| `/system-design` | Component (per container) | C4 L3 Mermaid |
| `/arch-refine` / `/design-refine` | Revised diagrams only | Same as parent command |
| `/system-plan` | Container-level flow | C4 L2 or sequence |
| `/feature-spec` | Component interaction | Sequence diagram for complex scenarios |
| `/task-review` | Code flow / call stack | Sequence diagram — root cause analysis |

### 7.3 The Review Gate
C4 diagrams generated by `/system-arch` are not optional outputs. They are a **mandatory review gate**: the command explicitly pauses and asks the human to review and approve each diagram before proceeding. The purpose is to catch structural problems before any downstream work begins. A wrong bounded context boundary caught at this stage costs minutes; caught during AutoBuild implementation it costs hours and potentially requires re-speccing features.

---

## 7. Immediate Context: FinProxy LPA Platform

The first system this command will be applied to is the FinProxy LPA Platform (FIM Proxy MVP). The domain involves open banking integration (MoneyHub as preferred provider, Yappily as alternative), eventual agent-to-agent protocol integration, and a multi-tenanted backend.

When `/system-arch` is run against this project, the clarifying questions will surface decisions including:
- **Structural pattern:** modular monolith (preferred given MVP scale and two-person team) vs microservices
- **Backend stack:** .NET with FastEndpoints (prior successful experience, composable, functional monadic error handling) vs alternatives
- **Frontend stack:** React (AI generation pragmatism) vs alternatives
- **Open banking abstraction:** tight coupling to MoneyHub vs pluggable provider abstraction layer (important given Yappily as fallback)

These are project-level decisions that `/system-arch` elicits and records — they are not defaults baked into the command itself.

The fintech vertical is not the long-term strategic focus (too small as a startup to attract large players). The architecture should therefore be designed around its reusability as a template pattern, not around fintech-specific concerns.

---

## 8. Open Questions for `/feature-spec` Session

These are the areas that need resolution before implementing the `/system-arch` command itself:

1. **Exact Graphiti seeding protocol for architectural artefacts** — what node types, relationship types, and retrieval queries does `/system-plan` need to find architecture context? Should `/system-arch` output structured YAML that matches Graphiti's ingestion format directly?

2. **Interaction model** — full propose-review (like `/feature-spec`) or a more directive "generate and confirm" flow? Architecture has fewer discrete choices than feature scenarios, so the propose-review cycle may need adaptation.

3. **Which existing commands have diagramming instructions?** — audit needed before speccing `/system-arch` to ensure consistency. Check `.guardkit/commands/` for current diagram-related prompt content.

4. **C4 Level 3 trigger conditions** — now assigned to `/system-design` rather than `/system-arch`, but conditions still need defining. Suggested: triggered per-container when the container has significant internal complexity, or when the human explicitly requests it.

5. **Relationship to `/system-plan`** — `/system-arch` and `/system-design` are run at project inception; `/system-plan` is run per feature or sprint. They are complementary, not competing. `/system-plan` reads from Graphiti — it benefits automatically once both upstream commands have seeded their artefacts.

6. **Agent protocol considerations** — which agent-to-agent protocols (MCP, Google A2A, ACP) should be explicitly considered as first-class API consumers in `/system-design`? This shapes OpenAPI and agent schema outputs that would be expensive to retrofit.

7. **`/arch-refine` vs `/design-refine` — one command or two?** A scope flag (`--layer arch|design`) keeps it simple; two commands keeps the impact analysis scope cleaner. Needs decision before speccing the refinement commands.

8. **Graphiti temporal superseding mechanics** — how does the seed script handle a decision that has already been seeded and is now being revised? Does it query for the prior node by ADR ID and create a supersedes relationship, or is this handled automatically by Graphiti's ingestion layer?

---

## 9. What Success Looks Like

After running `/system-arch` and `/system-design` on a new project:

- Graphiti contains bounded context decisions, ADRs, API contracts, data models, and design decisions — all queryable by downstream commands
- Running `/system-plan` on any feature produces responses that already "know" the domain structure, the relevant bounded context, and the API contract without re-explanation
- C4 L1/L2 diagrams (from `/system-arch`) and L3 diagrams (from `/system-design`) have been reviewed and approved — no structural surprises downstream
- A developer joining the project can read the architecture summary and OpenAPI spec and understand the system without archaeological investigation
- `/feature-spec` Gherkin scenarios reference real endpoints and domain entities from the OpenAPI spec rather than inventing contracts
- When the architecture or design evolves, `/arch-refine` or `/design-refine` propagates changes with impact analysis, Graphiti temporal superseding, and downstream staleness flags — nothing silently drifts
