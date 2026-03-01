# Ship's Computer Platform — System Architecture Intent

**Date:** March 2026  
**Author:** Rich Wainwright  
**Status:** Ideation Complete — Ready for `/system-arch`  
**Source:** Research docs synthesis + architectural conversations  
**Target Commands:** `/system-arch` → `/system-design` (once FEAT-E4F5 lands)

---

## 1. What This Document Is

This is the architectural intent document for the Ship's Computer platform — the distributed
agent orchestration system that spans Appmilla's compute infrastructure and provides the
automated development pipeline, agent fleet coordination, and multi-project build automation.

It is structured to feed directly into `/system-arch` once FEAT-E4F5 (system architecture
and design commands) completes. The intent is to run `/system-arch` against this document
to produce: formal ADRs, bounded context map, C4 L1/L2 diagrams, and Graphiti seeding —
grounding all downstream `/system-plan` and `/feature-spec` work in explicit decisions
rather than regenerated assumptions.

---

## 2. The Problem This Platform Solves

Today, moving a feature from idea to pull request requires:
- Manual setup of development environments per feature
- Manually triggering GuardKit AutoBuild runs
- Manually updating Linear/GitHub tickets with status
- Manually deciding which machine and which model to use for each build

The platform automates all of this while keeping humans in control of the two decisions
that matter: approving what gets built (moving a ticket to "Ready for Dev") and reviewing
what was built (PR review). Everything between those two gates is automated, observable,
and recoverable.

Beyond the pipeline, the same NATS event infrastructure coordinates the broader agent
fleet — Reachy Mini robots, potential drone integration, GCSE tutor agents, and future
Ship's Computer capabilities — through a shared message bus and topic hierarchy.

---

## 3. The Multi-Build-Agent Topology (Critical New Decision)

**This is the most important architectural decision not yet formally captured.**

The Build Agent is not a singleton service tied to a single machine and model. It is a
**pattern** that can be instantiated multiple times with different model backends. The
NATS event bus provides the routing abstraction — a `ready-for-dev` event carries project
and routing metadata that determines which Build Agent instance picks it up.

### 3.1 Agent Instances

| Instance | Machine | Model Backend | Projects | Subscription |
|----------|---------|---------------|----------|-------------|
| **MacBook Build Agent** | MacBook Pro M2 Max | Anthropic API (Claude Sonnet/Opus) | FinProxy LPA Platform | FinProxy's own Claude Max 20x |
| **Dell ProMax Build Agent** | Dell ProMax GB10 (DGX Spark) | vLLM + Qwen3-Coder-Next (local) | GuardKit, RequireKit, GCSE Tutor, Ship's Computer | No per-build cost |
| *(Future)* | Drone / edge compute | TBD | TBD | TBD |

### 3.2 Model Subscription Split

Rich maintains two Claude Max 20x subscriptions:

| Subscription | Owner | Used For |
|-------------|-------|----------|
| **Appmilla personal** | Rich | Planning, speccing all projects; MyDrive .NET MAUI development; ship's computer architecture and design work in Claude Desktop |
| **FinProxy project** | FinProxy (client) | MacBook Build Agent AutoBuild runs against Claude API for FinProxy features |

The vLLM + Qwen3-Coder-Next model on the Dell ProMax handles all non-FinProxy AutoBuild
work at zero per-token cost, with the tradeoff of less capable generation that the
three-layer-defence resolver framework is designed to compensate for.

### 3.3 Routing Mechanism

When a `pipeline.ready-for-dev.{feature_id}` event is published, the routing decision
(which Build Agent picks it up) is governed by the **project routing configuration**
resolved by the PM Adapter before publishing. The tier is never hardcoded.

**Option A — Subject-based routing (preferred):**
```
pipeline.ready-for-dev.anthropic.{feature_id}   →  MacBook Build Agent
pipeline.ready-for-dev.local.{feature_id}        →  Dell ProMax Build Agent
```
Each agent subscribes to its model-tier subject only. The PM Adapter looks up the
configured tier for the project (or feature override) and constructs the subject
accordingly — no routing logic lives in the agents themselves.

**Option B — Payload-based routing:**
```json
{
  "feature_id": "FEAT-XXX",
  "build_agent_tier": "anthropic" | "local",
  "repo": "appmilla/finproxy-lpa"
}
```
The orchestrator inspects the payload and routes.

**Recommendation for `/system-arch` to resolve:** Option A is simpler and leverages
NATS's native subject routing without requiring orchestrator logic. The tradeoff is a
slightly longer subject hierarchy. Decision needed before NATS topic registry is finalised
in nats-core.

### 3.4 Configuration-Driven Project-to-Agent Routing

**Critical design principle: routing is runtime configuration, not hardcoded.**

The mapping of project → agent tier must be changeable without code changes or
redeployment. Reasons this matters in practice:

- A side project may temporarily want the Anthropic tier for faster turnaround or a
  feature that needs frontier model quality, then switch back to local afterwards
- FinProxy might eventually move to local models if Qwen3-Coder-Next improves sufficiently
- New projects should be routable to either tier without touching any code
- Rich may want to route specific high-complexity features to Anthropic even within an
  otherwise local project, without changing the project default

**Routing configuration format (proposed):**

```toml
# dev-pipeline/config/routing.toml

[defaults]
tier = "local"          # fallback if project has no explicit config

[projects.finproxy-lpa]
tier = "anthropic"
subscription = "finproxy"   # NATS account credentials to use

[projects.guardkit]
tier = "local"

[projects.requirekit]
tier = "local"

[projects.gcse-tutor]
tier = "local"

[projects.dev-pipeline]
tier = "local"

[projects.mydrive]
tier = "manual"         # not pipeline-automated yet

# Feature-level override — one-off, doesn't change project default:
# [features.FEAT-XXX]
# tier = "anthropic"
```

This config is read by the PM Adapter when constructing the `ready-for-dev` subject.
Changing a project's tier is a config file edit and a service reload — no code change,
no redeployment of the Build Agents themselves.

**Feature-level overrides** provide an escape hatch for individual features that warrant
a different tier than their project default — useful when a particularly complex or
unfamiliar feature needs frontier model quality without permanently changing the project
configuration.

**Current default routing (as of March 2026):**

| Project | Default Tier | Subscription | Notes |
|---------|-------------|-------------|-------|
| FinProxy LPA Platform | anthropic | finproxy | Client project, dedicated subscription |
| GuardKit | local | appmilla | Internal tooling |
| RequireKit | local | appmilla | Internal tooling |
| GCSE English Tutor | local | appmilla | Personal project |
| Ship's Computer / dev-pipeline | local | appmilla | Meta — building with the pipeline |
| MyDrive .NET MAUI | manual | — | Not yet pipeline-automated |

These are defaults in the config file. Any can be changed at any time.

---

## 4. System Boundary

### 4.1 What Is "Ship's Computer"

Ship's Computer is the name for the distributed AI agent orchestration platform running
across Rich's compute infrastructure. It encompasses:

- The **dev pipeline** (automated feature building from PM trigger to PR)
- The **agent fleet** (Reachy Mini robots, potential drone nodes)
- The **NATS event bus** (the coordination backbone)
- The **Graphiti knowledge graph** (temporal memory for the fleet)
- Future **Ship's Computer dashboard** (situational awareness UI)

GuardKit and RequireKit are **tools** that optionally participate in the fleet via NATS
integration. They are not core Ship's Computer components — they work standalone without it.

### 4.2 What Is Out of Scope for This Architecture

- GuardKit internals (Player-Coach loop, quality gates, command implementations)
- RequireKit internals (feature planning, spec generation)
- FinProxy LPA Platform application architecture (separate `/system-arch` session)
- MyDrive .NET MAUI application architecture (separate session)
- GCSE English Tutor application architecture (separate session)

---

## 5. Infrastructure Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│  TAILSCALE MESH VPN                                                  │
│                                                                      │
│  ┌──────────────────────────┐   ┌──────────────────────────────┐   │
│  │  MacBook Pro M2 Max      │   │  Dell ProMax GB10            │   │
│  │                          │   │  (DGX Spark)                 │   │
│  │  Planning & Speccing:    │   │                              │   │
│  │  • Claude Desktop        │   │  Services (Docker Compose):  │   │
│  │  • RequireKit            │   │  • NATS Server + JetStream   │   │
│  │  • GuardKit commands     │   │  • Dell ProMax Build Agent   │   │
│  │  • MyDrive development   │   │  • PM Adapters (Linear etc.) │   │
│  │                          │   │  • vLLM + Qwen3-Coder-Next  │   │
│  │  MacBook Build Agent:    │   │  • Resolver Agents (opt-in)  │   │
│  │  • Anthropic API client  │   │                              │   │
│  │  • For FinProxy builds   │   │  Graphiti knowledge graph    │   │
│  │  • FinProxy subscription │   │  (local FalkorDB instance)   │   │
│  └──────────────────────────┘   └──────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────┐   ┌──────────────────────────────┐   │
│  │  Synology DS918+ NAS     │   │  Reachy Mini (×2)            │   │
│  │                          │   │                              │   │
│  │  • FalkorDB (Graphiti)   │   │  "Scholar" — GCSE Tutor      │   │
│  │  • Shared storage        │   │  "Bridge" — Ship's Computer  │   │
│  │  • Private package repo  │   │  interface / orchestrator    │   │
│  │    (potential)           │   │                              │   │
│  └──────────────────────────┘   └──────────────────────────────┘   │
│                                                                      │
│  James's MacBook (added to Tailscale for FinProxy work)             │
└─────────────────────────────────────────────────────────────────────┘

Future: AWS ECS/Fargate for client-facing NATS + adapters
```

---

## 6. Repository Architecture

### 6.1 The Four Repos

```
appmilla/
├── nats-core      — Shared message schemas, topic registry, Python client
├── guardkit       — AI-augmented development CLI (existing, gains optional NATS)
├── requirekit     — Requirements & feature planning CLI (existing, gains optional NATS)
└── dev-pipeline   — NATS infra, Build Agents (both), PM adapters, dashboard
```

### 6.2 Bounded Contexts

| Bounded Context | Repo | Responsibility |
|----------------|------|---------------|
| **Messaging Contract** | nats-core | Message schemas, topic hierarchy, client library — the shared language of the fleet |
| **Build Orchestration** | dev-pipeline | NATS infrastructure, Build Agent instances, PM adapters, routing logic |
| **Build Execution** | guardkit | AutoBuild Player-Coach loop, quality gates, telemetry — invoked by Build Agents |
| **Feature Planning** | requirekit | Feature specs, system plans, YAML generation — publishes feature-planned events |
| **Resolver Fleet** | dev-pipeline | Three-layer defence resolver agents (knowledge-gap, context-overflow, spec-ambiguity) |
| **Agent Fleet** | dev-pipeline (initially) | Ship's Computer coordination, Reachy integration, agent registry |

### 6.3 Dependency Graph

```
nats-core  (Python package — shared schemas + client)
    │
    ├── guardkit      (optional dep: --nats flag activates)
    │     └── publishes: pipeline.build-progress.*, pipeline.build-complete.*
    │
    ├── requirekit    (optional dep: --nats flag activates)
    │     └── publishes: pipeline.feature-planned.*
    │
    └── dev-pipeline  (hard dep: nats-core is mandatory)
          ├── MacBook Build Agent    (subscribes: pipeline.ready-for-dev.anthropic.*)
          ├── Dell Build Agent       (subscribes: pipeline.ready-for-dev.local.*)
          ├── PM Adapters            (publishes: pipeline.ready-for-dev.{tier}.*)
          ├── Resolver Agents        (subscribes: pipeline.build-blocked.*)
          └── NATS Server Config
```

---

## 7. NATS Topic Hierarchy

The full topic hierarchy requires formal design in `/system-design`, but the high-level
structure is known and should inform the ADR decisions in `/system-arch`:

```
pipeline/
├── feature-planned.{feature_id}                 ← RequireKit publishes
├── ready-for-dev.anthropic.{feature_id}         ← PM Adapter publishes (Anthropic tier)
├── ready-for-dev.local.{feature_id}             ← PM Adapter publishes (local tier)
├── build-started.{feature_id}                   ← Build Agent publishes
├── build-progress.{feature_id}                  ← GuardKit publishes (via Build Agent)
├── build-complete.{feature_id}                  ← Build Agent publishes
├── build-failed.{feature_id}                    ← Build Agent publishes
├── build-blocked.{feature_id}                   ← Build Agent publishes (resolver trigger)
├── build-needs-clarification.{feature_id}       ← Spec-ambiguity resolver publishes
└── clarification-response.{feature_id}          ← Human (dashboard) publishes

resolver/
├── knowledge-assist.{feature_id}                ← Knowledge-gap resolver
├── context-assist.{feature_id}                  ← Context-overflow resolver
└── clarification-assist.{feature_id}            ← Spec-ambiguity resolver

telemetry/
├── task-complete.{feature_id}                   ← GuardKit telemetry
├── build-summary.{feature_id}                   ← Build Agent aggregates
└── export-request / export-complete             ← Fine-tuning data pipeline

agents/
├── status.{agent_id}                            ← Agent heartbeat
├── approval.requests                            ← Human-in-the-loop gate
└── commands.{agent_id}                          ← Ship's Computer orchestrator
```

**NATS multi-tenancy:** NATS accounts provide per-project isolation. Rich's account has
wildcard access (`>`). James's account is scoped to `finproxy.>` subjects only. This is
enforced at the NATS server level, not by convention.

---

## 8. Architectural Decisions (Pre-Resolved, Ready for ADR Formalisation)

These decisions have been made through research and conversations. `/system-arch` should
formalise them as ADRs with rationale and alternatives rejected, then seed them to Graphiti.

| # | Decision | Rationale | Alternatives Rejected |
|---|----------|-----------|----------------------|
| D1 | NATS as orchestration backbone, not PM tool webhooks | Tool-agnostic; swap Linear for Jira by replacing only the adapter | Direct webhook coupling to Linear/GitHub |
| D2 | Build Agent is a pattern, not a singleton | Enables multiple model-tier instances on different machines | Single Build Agent with model config flag |
| D3 | Subject-based routing for Build Agent tier selection | Leverages native NATS routing; no orchestrator logic needed | Payload-based routing, separate queues |
| D4 | Build Agent bundled in dev-pipeline, not separate repo | Same deployment lifecycle; not complex enough to warrant isolation | Separate build-agent repo |
| D5 | NATS server on Dell ProMax | Use owned hardware; no cloud bills during development | Synology NAS (less GPU), cloud (cost) |
| D6 | GuardKit/RequireKit opt-in NATS integration (--nats flag) | Zero regression for standalone use; NATS is additive | Hard NATS dependency in tools |
| D7 | nats-core as pip-installable git+ssh package initially | Simplest viable approach; private PyPI later if versioning becomes complex | Private PyPI from day one, git submodule |
| D8 | Graphiti writes happen in GuardKit, not via NATS events | Different concerns: Graphiti = knowledge, NATS = orchestration | NATS adapter writes to Graphiti |
| D9 | FinProxy uses MacBook Build Agent + Anthropic API | Client confidence, dedicated subscription, frontier model quality | Same vLLM local model as other projects |
| D10 | Three-layer build defence: prevention, recovery, resolution | Compensates for open-weight model limitations; structured failure analysis | Single retry loop, human escalation only |
| D11 | Failure categorisation: knowledge-gap, context-overflow, spec-ambiguity | Each category has a distinct automated resolution path | Generic resolver, no categorisation |
| D12 | Resolver agents as optional Docker containers | Pipeline works without them; independently deployable | Mandatory, embedded in Build Agent |
| D13 | All failure analysis and resolver logic stack-agnostic | Platform builds Python, TypeScript, Go, C#, Rust projects | Python-only tooling |
| D14 | Project-to-agent routing is configuration-driven, not hardcoded | Projects (and individual features) need to change tiers without code changes; defaults favour local for cost, Anthropic for client projects | Hardcoded project→tier mapping in adapter code |

---

## 9. Multi-Tenancy Design

| Concern | Approach |
|---------|----------|
| **Topic isolation** | NATS subject prefixes per project (e.g., `finproxy.pipeline.*`) |
| **Authentication** | NATS accounts with scoped credentials per project |
| **Visibility** | Rich: wildcard access to all subjects. James: scoped to finproxy.* only |
| **Build Agent routing** | Project config maps project_id → agent tier (anthropic/local) |
| **Graphiti isolation** | Per-project group_id in Graphiti episodes |
| **Future cloud** | AWS ECS for NATS + adapters when client deployments require it |

---

## 10. Integration Points with Existing Systems

| System | Integration | Direction |
|--------|------------|-----------|
| Linear | Webhook → PM Adapter → NATS `ready-for-dev`; NATS `build-complete` → Linear API update | Bidirectional |
| GitHub | PR creation via GitHub API from Build Agent on completion | Build Agent → GitHub |
| Graphiti (FalkorDB on NAS) | GuardKit writes build knowledge; Graphiti nodes queryable by resolver agents | GuardKit writes, resolvers read |
| GCSE Tutor | Uses dev-pipeline for its own feature development; at runtime is a separate system | Pipeline consumer |
| Reachy Mini "Bridge" | Subscribes to `agents.*` topics; voice interface for Ship's Computer events | Future integration |
| MyDrive .NET MAUI | Currently manual (Claude Desktop); pipeline integration deferred | Future |
| Claude API | MacBook Build Agent invokes GuardKit AutoBuild which calls Anthropic API | Per-build calls |
| vLLM / Qwen3-Coder-Next | Dell Build Agent invokes GuardKit AutoBuild which calls local vLLM endpoint | Per-build calls |

---

## 11. Open Questions for `/system-arch` to Resolve

These require explicit decisions before `/system-design` or implementation begins:

1. **Subject-based vs payload-based routing** — D3 above recommends subject-based; confirm this
   is the right tradeoff before it's encoded in the topic registry in nats-core.

2. **MacBook Build Agent deployment model** — Does the MacBook Build Agent run as a persistent
   daemon (launchd service), or is it a manually-started Docker container? The MacBook is a
   laptop that may close/sleep. What is the failure model when it's unavailable?

3. **Build queue behaviour under dual-agent topology** — If the MacBook agent is offline and
   a FinProxy `ready-for-dev` event arrives, does it queue in JetStream and wait, or fail
   immediately? What is the visibility of queued-but-unprocessed events?

4. **FinProxy Graphiti instance** — Does FinProxy get its own isolated Graphiti group_id
   within the NAS instance, or should it eventually get its own Graphiti instance for
   stronger isolation? (James connecting via Tailscale can currently see all Graphiti data
   if he knows the endpoint — is that acceptable?)

5. **MyDrive .NET MAUI pipeline integration** — Does Rich want MyDrive to eventually flow
   through the pipeline (Dell ProMax Build Agent, local model), or remain manual?
   The .NET MAUI stack may have limited support in Qwen3-Coder-Next.

6. **Wave gating default** — Per the earlier architecture doc, wave gating is opt-in via
   `--wave-gating` flag. Should FinProxy builds default to wave-gated (James can review
   between waves) while other projects default to continuous?

7. **Dashboard priority** — A Ship's Computer dashboard is referenced throughout but not
   yet specced. Is this needed before FinProxy goes live, or can Linear visibility plus
   NATS monitoring tools suffice initially?

8. **GitHub Projects adapter** — The architecture notes Linear as primary PM tool. For
   Rich's own Appmilla projects (guardkit, requirekit), should GitHub Projects serve as
   the PM tool to avoid a separate Linear subscription, or use Linear for everything?

---

## 12. The Three-Layer Build Defence (Architectural Context)

This is a significant architectural subsystem that sits within the Build Orchestration
bounded context. Full specs exist in `docs/research/three-layer-defence/`. Summary:

**Layer 1 — Prevention:**  
`/system-arch` → `/system-design` → `/system-plan` → `/feature-spec` → `/feature-plan`
Plus Graphiti context retrieval. Goal: reduce ambiguity before implementation starts.

**Layer 2 — Recovery:**  
Existing Player-Coach loop (≤5 turns per task). Self-correction within the loop.

**Layer 3 — Assisted Resolution (resolver agents):**  
When Player-Coach exhausts turns, GuardKit publishes `pipeline.build-blocked.{feature_id}`
with a typed failure category. Resolver agents in dev-pipeline provide targeted context
augmentation via NATS and restart the loop. Maximum one resolver-assisted retry per task.

**Implementation phasing:**  
Phase A (instrument GuardKit for telemetry) → Phase B (build resolvers based on empirical
failure distribution data from Phase A). Phase A specs are complete and ready for
`/feature-plan`.

---

## 13. Technology Stack Summary

| Component | Technology | Notes |
|-----------|------------|-------|
| Message bus | NATS + JetStream | Persistent, multi-tenant, subject-based routing |
| Message schemas | Pydantic v2 | Typed, validated, stack-agnostic |
| NATS client | FastStream / nats-py | Async Python client with typed pub/sub |
| Build Agent (MacBook) | Python asyncio | Calls Anthropic API via GuardKit |
| Build Agent (Dell) | Python asyncio | Calls local vLLM via GuardKit |
| AutoBuild engine | GuardKit (existing) | Player-Coach adversarial loop |
| Feature planning | RequireKit (existing) | YAML specs, wave structure |
| PM integration | Linear API + webhooks | Bidirectional; adapter pattern for others |
| Knowledge graph | Graphiti + FalkorDB | Temporal memory, ADR storage, context retrieval |
| Local LLM | vLLM + Qwen3-Coder-Next | Dell ProMax DGX Spark, zero per-token cost |
| Frontier LLM | Anthropic Claude (API) | MacBook Build Agent for FinProxy |
| Networking | Tailscale mesh VPN | All machines, including James's MacBook |
| Containerisation | Docker Compose | Services on Dell ProMax |
| Version control | GitHub | All repos, PR workflow |
| Storage (NAS) | Synology DS918+ | FalkorDB, shared storage, potential private PyPI |

---

## 14. What Success Looks Like After `/system-arch` + `/system-design`

- Graphiti contains formal ADRs for all 14+ pre-resolved decisions, queryable by downstream commands
- C4 L1 diagram shows Ship's Computer platform boundary with all external actors (Linear, GitHub, Anthropic API, vLLM, Tailscale nodes)
- C4 L2 diagram shows all containers: NATS Server, MacBook Build Agent, Dell Build Agent, PM Adapters, Resolver Agents, GuardKit, RequireKit, Graphiti
- The dual Build Agent topology is explicitly modelled and the routing mechanism confirmed
- Running `/system-plan` on any feature in any project produces responses that already know which Build Agent tier to target, which bounded context it belongs to, and what the relevant ADRs are
- `/feature-plan` for nats-core schemas can be run immediately, grounded in the confirmed topic hierarchy from `/system-design`
- The three-layer-defence feature specs (already written) are validated against the confirmed architecture — no contract drift

---

## 15. Suggested `/system-arch` Invocation

When FEAT-E4F5 AutoBuild completes and the new commands are available:

```bash
/system-arch \
  --context docs/research/dev-pipeline-system/ships-computer-system-arch-intent.md \
  --project "Ship's Computer Platform" \
  --clarify structural-pattern,routing-mechanism,macbook-agent-deployment
```

The `--clarify` flags surface the three open questions that have the highest downstream
impact and should be resolved early in the propose-review cycle.

After `/system-arch` completes, run:

```bash
/system-design \
  --focus nats-core \
  --context docs/architecture/
```

This produces the formal topic registry and message schema contracts that nats-core
can be implemented against — replacing the current research-doc-level schemas with
formally validated API contracts in Graphiti.
