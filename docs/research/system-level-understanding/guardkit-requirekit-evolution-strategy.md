# GuardKit + RequireKit Evolution Strategy
## Bridging the Gap: From Task Execution to Full Project Lifecycle

**Date**: February 2026
**Context**: Post-AutoBuild implementation, Graphiti integration complete, preparing for multi-project usage
**Inputs**: TASK-REV-1505 architectural review, TASK-REV-7549 AutoBuild retrospective, ongoing workflow analysis

---

## 1. Where You Are Now

### What's Working Well
- **GuardKit core workflow**: task-create → task-work → task-complete with quality gates is solid
- **AutoBuild with player-coach**: adversarial cooperation produces high-quality output despite the painful 3-4 week build
- **Graphiti integration**: Job-specific context retrieval replacing monolithic context loading
- **Progressive disclosure**: Core/ext file splits, frontmatter-based agent selection
- **Feature-plan / feature-build**: Decomposition from features into tasks with staged execution
- **Task-review as discovery tool**: Evolved from plan-mode conversations into a standard workflow for bug analysis, implementation review, and idea refinement

### The Gaps You've Identified
1. **No big-picture architectural context** — Claude doesn't understand how the whole system fits together, leading to task-reviews and tasks undoing each other's work
2. **No product-level requirements flow** — jumping straight to feature-plan without captured epics, domain models, or system design
3. **RequireKit is underused** — James couldn't distinguish commands from conversation, no refinement commands
4. **BDD scenarios aren't feeding back** — living documentation that could prevent Claude from reinventing or misunderstanding existing behaviour
5. **Multi-project cognitive overload** — the human developer is carrying system-level context that should live in the knowledge graph
6. **Missing Graphiti entities** — TASK-REV-1505 identified 5 of 11 context loss scenarios unaddressed by current design

---

## 2. The Missing Layer: System Understanding

The core problem is that GuardKit operates at **task and feature level** but lacks **project and system level** knowledge. When AutoBuild hits a complex feature, the coach reviews individual tasks but has no anchoring in:

- What bounded contexts exist and their boundaries
- How services/modules relate to each other
- What the domain model looks like
- What acceptance criteria exist at the epic level
- What BDD scenarios already validate existing behaviour

This is why tasks "go in the wrong direction" — they're locally correct but globally wrong.

### The Cognitive Load Problem

The human developer currently acts as the substitute for missing system-level context. Every project switch requires mentally reloading architecture, domain relationships, recent decisions, and in-progress work. This creates a bottleneck: the developer can only effectively work on one project at a time because the context lives in their head rather than in queryable knowledge.

Solving the big-picture gap doesn't just improve AutoBuild quality — it fundamentally enables multi-project work by offloading system context to Graphiti. The knowledge graph holds the context instead of the developer's head.

### TASK-REV-1505: Validated Context Loss Scenarios

The architectural review of the Graphiti Refinement roadmap (TASK-REV-1505) cross-referenced against AutoBuild lessons (TASK-REV-7549) and found:

**Addressed by current Graphiti design:**
| Scenario | Solution |
|----------|----------|
| No "North Star" context | GR-001 (project_overview) |
| Context loss across sessions | GR-006 (job-specific retrieval) |
| Repeated mistakes | GR-001 (failure_patterns) + GR-006 (warnings) |
| Task type confusion | GR-006 (TaskAnalyzer) |
| Implementation plan forgotten | GR-003 (feature spec integration) |

**Gaps requiring additional Graphiti entities:**
| Scenario | Missing Entity | Priority |
|----------|---------------|----------|
| Player-Coach role reversal | `role_constraints` | Critical |
| Quality gate threshold drift | `quality_gate_configs` | Critical |
| Cross-turn learning failure | `turn_states` | Critical |
| Direct vs task-work confusion | `implementation_modes` | Moderate |
| State recovery confusion | Turn state tracking | Moderate |

These gaps feed directly into the Phase 1 implementation priorities below.

---

## 3. The Command Evolution: From Review to Planning

### How the Workflow Has Naturally Evolved

A clear pattern has emerged in how GuardKit's interactive commands are used:

1. **Started with plan-mode conversations** — ad hoc discovery, exploration, and refinement in Claude Code's plan mode
2. **Formalised into `/task-review`** — structured review workflow for implementations, bugs, and ideas. Now the standard approach for investigating issues
3. **Specialised into `/feature-plan`** — decomposition-focused review that takes a feature and produces tasks. Itself a refinement of the task-review pattern

Each step has been a **specialisation** of the same interactive review loop, tuned for a specific level of abstraction:

```
/task-review    → "Is this implementation correct?"     → Code/test level
/feature-plan   → "How should we decompose this?"       → Feature/task level  
     ???        → "How does this fit the bigger picture?" → System/architecture level
```

### The Missing Third Specialisation: `/system-plan`

The gap is a command that operates at the level above `/feature-plan`. Where `/feature-plan` asks "how do we break this feature into tasks?", `/system-plan` asks "how does this fit into the system architecture, what does it affect, and what design decisions should we make?"

**`/system-plan` would answer questions like:**
- How do the bounded contexts relate to this piece of work?
- What existing BDD scenarios validate related behaviour?
- What ADRs constrain implementation choices?
- What domain model entities are involved?
- What are the cross-cutting concerns (auth, logging, error handling)?
- What services/modules will this touch?

**When you'd use it:**
- **Before `/feature-plan`** when starting a substantial piece of work — establish context before decomposition
- **When switching projects** — reorient yourself in the system architecture
- **Mid-build when something feels wrong** — "show me the big picture, am I still aligned?"
- **When reviewing architectural decisions** — evaluate options against existing constraints and patterns

**How it differs from `/system-overview`:**
`/system-overview` (proposed in Phase 1 below) is a **read-only query** — it shows the current state of architecture knowledge. `/system-plan` is an **interactive planning session** that:
- Queries Graphiti for architectural context, domain models, BDD scenarios, and ADRs
- Walks through architectural considerations interactively
- Produces or updates architecture documentation
- Pushes decisions and design context to Graphiti
- Can generate a system-context diagram (C4 Level 1) as markdown

**Example workflow for the PoA project:**
```
/system-plan "Power of Attorney platform"
  → Interactive session establishing bounded contexts
  → Domain model exploration (LPA types, attorney roles, Moneyhub integration)  
  → ADR generation for key decisions
  → Architecture context pushed to Graphiti
  → Output: system-context markdown + Graphiti knowledge

/feature-plan FEAT-POA-001 "Attorney Management"
  → Reads architectural context from /system-plan output
  → Decomposes into tasks with domain model awareness
  → Tasks inherit bounded context knowledge

/feature-build FEAT-POA-001
  → Coach receives system context + domain model + BDD
  → Player receives task-specific implementation context
  → Both anchored in big-picture understanding
```

---

## 4. Proposed Solution: Four Interconnected Additions

### 4.1 `/system-plan` — Interactive Architecture Planning (NEW — Highest Leverage)

An interactive planning command that establishes and maintains system-level context in Graphiti.

**Modes of operation:**
- **Initial setup**: Interactive session for new projects. Explores domain, bounded contexts, service relationships, key decisions. Produces architecture documentation and seeds Graphiti.
- **Refinement**: Updates existing architecture context. Adds new bounded contexts, revises decisions, captures new patterns or constraints.
- **Review**: Evaluates a proposed change against existing architecture. Shows impact, identifies conflicts with ADRs, highlights affected BDD scenarios.

**What it queries/produces:**
- Reads: existing Graphiti episodes for `project_architecture`, `project_decisions`, `bdd_scenarios`, `domain_knowledge`
- Writes: updated architecture context, ADRs, domain model relationships, bounded context definitions
- Displays: system context diagram, bounded context map, decision log, relevant BDD coverage

**Integration with Graphiti:**
- Seeds/updates `{project}__project_architecture` group
- Creates ADR episodes in `{project}__project_decisions` group
- Cross-references `{project}__domain_knowledge` for entity relationships
- Queries `{project}__bdd_scenarios` for coverage gaps

### 4.2 RequireKit v2: Graphiti-Backed Requirements + Refinement Commands

**New commands (minimal ceremony):**
- `/epic-refine EPIC-XXX` — Interactive refinement of existing epics (scope, success criteria, constraints)
- `/feature-refine FEAT-XXX` — Refine feature scope, acceptance criteria, dependencies
- `/domain-model [bounded-context]` — Interactive DDD domain modelling (entities, aggregates, value objects)

**Why refinement commands matter for James:**
James's problem was that `/epic-create` felt like a one-shot operation. With `/epic-refine`, he can start rough and iterate — exactly how product owners actually work. The command should:
- Show current state of the epic
- Ask targeted questions about gaps (missing success criteria, unclear scope boundaries)
- Update the epic markdown and push changes to Graphiti
- Never require CLI knowledge beyond typing the slash command

**Graphiti integration for RequireKit:**
- Epics, features, requirements stored as episodes with `group_id: "requirements"`
- Domain model entities stored with relationships (Aggregate → Entity → Value Object)
- ADRs stored with temporal validity (superseded decisions remain queryable)
- Cross-reference: GuardKit tasks query RequireKit's Graphiti store for context

### 4.3 BDD Living Documentation → Graphiti

**The value proposition:**
When a BDD scenario passes, it becomes a fact about the system's current behaviour. When Claude starts a new task, it can query: "What scenarios already validate authentication?" and avoid breaking or duplicating existing behaviour.

**Implementation (lightweight):**
1. `/generate-bdd` already exists in RequireKit — enhance it to push scenarios to Graphiti
2. Add a `group_id: "bdd_scenarios"` namespace
3. GuardKit's task-work Phase 2 (implementation planning) queries relevant BDD scenarios
4. AutoBuild coach queries BDD scenarios during validation loops
5. When tests pass, mark scenarios as "verified" in Graphiti with timestamp

**The living documentation feedback loop:**
```
RequireKit: /generate-bdd → creates .feature files + Graphiti episodes
GuardKit: /task-work reads BDD context → implements respecting existing behaviour  
GuardKit: /task-complete verifies BDD scenarios still pass → updates Graphiti
RequireKit: /feature-status shows which scenarios are green/red
```

### 4.4 System Context Commands for GuardKit

**Read-only commands that consume the knowledge `/system-plan` produces:**

- `/system-overview` — Query Graphiti for project architecture, display bounded contexts, service map, key decisions
- `/impact-analysis TASK-XXX` — Before task-work, show what components/services/BDD scenarios this task might affect
- `/context-switch [project]` — When switching between projects, load the right Graphiti group_ids and display a quick orientation summary

**These solve the "wrong direction" problem directly:**
Before AutoBuild starts a feature, `/system-overview` provides the coach with architectural context. During player-coach loops, `/impact-analysis` tells the coach which existing behaviour to protect. After completion, BDD scenarios validate nothing was broken.

**Relationship between system commands:**
```
/system-plan     → Interactive, writes to Graphiti (planning sessions)
/system-overview → Read-only, queries Graphiti (quick reference)
/impact-analysis → Read-only, queries Graphiti (pre-task validation)
/context-switch  → Read-only, loads project context (multi-project navigation)
```

---

## 5. Critical Graphiti Entity Gaps (from TASK-REV-1505)

The architectural review identified entities that must be added to the Graphiti Refinement roadmap:

### 5.1 Role Constraints (Critical — addresses top-5 AutoBuild problem)

Player-Coach role reversal was a recurring problem. Explicit role boundaries must be seeded in Graphiti:

```
role_constraints:
  player:
    must_do: [Implement code, Read implementation plans, Write tests]
    must_not_do: [Validate quality gates, Make architectural decisions]
    ask_before: [Changing architecture, Modifying quality profiles]
  coach:
    must_do: [Validate against acceptance criteria, Run quality gates]
    must_not_do: [Write code, Modify implementation]
    escalate_when: [Test failures persist, Architecture violations detected]
```

### 5.2 Quality Gate Configurations (Critical — prevents threshold drift)

Quality gate thresholds changed mid-session during AutoBuild. Task-type-specific configurations prevent this:

```
quality_gate_configs:
  scaffolding: {arch_review: false, coverage: false, tests: false}
  feature: {arch_review: true, threshold: 60, coverage: 0.80}
  bugfix: {arch_review: false, coverage: true, regression_test: true}
```

### 5.3 Turn States (Critical — enables cross-turn learning)

Feature-build loses context between turns. Turn state tracking preserves decisions and progress:

```
turn_states:
  turn_number: int
  player_decision: str
  coach_decision: str
  blockers_found: [str]
  progress_summary: str
  acceptance_criteria_status: {criterion: verified|pending|rejected}
  mode: FRESH_START | RECOVERING_STATE | CONTINUING_WORK
```

### 5.4 Implementation Modes (Moderate — clarifies direct vs task-work)

```
implementation_modes:
  direct: {when: "Simple changes, < 30 min", ceremony: minimal}
  task_work: {when: "Feature work, needs quality gates", ceremony: standard}
  autobuild: {when: "Multi-task features, needs player-coach", ceremony: full}
```

### 5.5 Required Graphiti Group IDs (Full List)

| Group ID | Source | Purpose |
|----------|--------|---------|
| `{project}__project_overview` | GR-001 | Project purpose, goals |
| `{project}__project_architecture` | GR-001 / system-plan | System architecture |
| `{project}__feature_specs` | GR-002/003 | Feature specifications |
| `{project}__project_decisions` | GR-002 / system-plan | ADRs |
| `{project}__project_constraints` | GR-002 | Constraints and limitations |
| `{project}__domain_knowledge` | GR-002/004 / system-plan | Domain terminology |
| `{project}__bdd_scenarios` | generate-bdd | Living test documentation |
| `role_constraints` | GR-001 (NEW) | Player/Coach boundaries |
| `quality_gate_configs` | GR-001 (NEW) | Threshold configurations |
| `turn_states` | GR-005 (NEW) | Feature-build turn history |
| `implementation_modes` | GR-001 (NEW) | Direct vs task-work patterns |

---

## 6. DDD for Power of Attorney Platform

For the PoA/Moneyhub project specifically, DDD makes strong sense because:

- **Legal domain is complex** — Power of Attorney types (LPA Property/Financial, LPA Health/Welfare), donor/attorney relationships, certificate providers, OPG registration
- **Open Banking integration** — Moneyhub API has its own bounded context around accounts, transactions, consents
- **Clear bounded contexts emerge naturally:**
  - **Attorney Management** — donor, attorney, replacement attorney, certificate provider
  - **Document Generation** — LPA forms, instructions, preferences
  - **Financial Oversight** — account access, transaction monitoring, spending limits (Moneyhub integration)
  - **Compliance** — OPG registration, identity verification, capacity assessment

**This is where `/system-plan` would first prove its value:**
1. `/system-plan "Power of Attorney platform"` — interactive session establishing bounded contexts and domain model
2. Domain entities and relationships pushed to Graphiti
3. `/feature-plan` per bounded context inherits domain context automatically
4. All GuardKit tasks receive domain-aware context from Graphiti

---

## 7. Implementation Priority

Ordered by impact vs effort, keeping to the "walk before running" principle:

### Phase 1: System Context + Critical Entities (2-3 weeks)
**Goal**: Stop tasks going in the wrong direction. Reduce human cognitive load.

1. Add `/system-plan` to GuardKit — interactive architecture planning that seeds Graphiti
2. Add `/system-overview` to GuardKit — read-only query of architecture context
3. Add `/impact-analysis TASK-XXX` — pre-task validation against known components and BDD
4. Add critical Graphiti entities: `role_constraints`, `quality_gate_configs`, `turn_states`
5. Wire system context into AutoBuild coach validation — coach receives architecture + role constraints

**This directly addresses both the painful AutoBuild experience and multi-project cognitive load.**

**Note on estimates**: TASK-REV-1505 recommends adding 20% buffer to all estimates. The original Graphiti Refinement roadmap was 125h; revised estimate is 140-150h.

### Phase 2: RequireKit Refinement (1-2 weeks)
**Goal**: Make RequireKit usable for James and product-centric workflows

6. Add `/epic-refine` and `/feature-refine` commands — iterative refinement with clear prompts
7. Add Graphiti backing for epics/features — store in knowledge graph alongside task outcomes
8. Enhance `/generate-bdd` to push to Graphiti — creates the living documentation foundation

### Phase 3: BDD Feedback Loop (1 week)
**Goal**: Living documentation prevents regression

9. GuardKit task-work Phase 2 queries BDD scenarios from Graphiti
10. AutoBuild coach receives BDD context during validation
11. Task-complete updates BDD scenario status in Graphiti

### Phase 4: DDD and System Design (as needed per project)
**Goal**: Domain modelling for complex projects like PoA

12. Add `/domain-model` command to RequireKit — interactive domain exploration
13. Wire domain model into GuardKit context — tasks in a bounded context receive domain entities
14. Add `implementation_modes` entity to Graphiti

---

## 8. What NOT to Do

- **Don't build a full PM tool** — epics/features are specs, not project management. Keep that in GitHub/Linear
- **Don't require RequireKit for GuardKit to work** — maintain the optional integration with `spec_ref`
- **Don't add ceremony to simple tasks** — complexity scoring should gate when big-picture context is loaded. Simple bug fixes don't need system overview
- **Don't duplicate Graphiti data** — single source: markdown files are authoritative, Graphiti provides queryability
- **Don't build all of Phase 4 before you need it** — implement `/domain-model` when you actually start the PoA project, not before
- **Don't over-engineer the context budget** — TASK-REV-1505 recommends starting with fixed allocations, adding telemetry, and tuning based on real usage

---

## 9. Architecture: How It Fits Together

```
                    Product Owner (James)
                           │
                    RequireKit v2
                    ├── /epic-create + /epic-refine
                    ├── /feature-create + /feature-refine  
                    ├── /generate-bdd (→ Graphiti)
                    └── /domain-model (for complex projects)
                           │
                     ┌─────┴─────┐
                     │  Graphiti  │  ← Shared knowledge graph
                     │  (Neo4j)  │     per-project isolation
                     └─────┬─────┘
                           │
                    GuardKit (enhanced)
                    ├── /system-plan (interactive → writes Graphiti)
                    ├── /system-overview (read-only → queries Graphiti)
                    ├── /impact-analysis (read-only → queries Graphiti)
                    ├── /context-switch (loads project context)
                    ├── /feature-plan (reads epic/BDD/architecture context)
                    ├── /feature-build + AutoBuild
                    │   ├── Coach receives: system overview + role constraints +
                    │   │   BDD scenarios + domain model + quality gate configs
                    │   └── Player receives: task-specific context + turn states
                    ├── /task-review (implementation/bug review)
                    ├── /task-work (BDD-aware implementation)
                    └── /task-complete (updates BDD status + turn states)
```

### The Command Hierarchy

```
Planning Level          Command              Abstraction
─────────────          ─────────             ──────────
System/Architecture  →  /system-plan       →  "How does this system work?"
                        /system-overview   →  "Show me the current architecture"
Feature/Decomposition→  /feature-plan      →  "How do we break this down?"
Task/Implementation  →  /task-review       →  "Is this correct? What's wrong?"
                        /task-work         →  "Build this specific thing"
```

**Key principle**: RequireKit captures WHAT and WHY. GuardKit executes HOW. `/system-plan` bridges the gap between requirements and execution. Graphiti connects them all with queryable, temporal knowledge.

---

## 10. For the Projects Ahead

| Project | First Action | RequireKit Focus | GuardKit Focus | DDD Needed? |
|---------|-------------|-----------------|----------------|-------------|
| GuardKit itself | `/system-plan` to capture current architecture | Feature specs, BDD for CLI | AutoBuild with system context | No |
| Reachy GCSE Tutor | `/system-plan` to establish tutor domain | Epic for curriculum, BDD for interactions | Feature-build for agents | Light |
| PoA/Moneyhub | `/system-plan` + `/domain-model` before any code | Full domain model, legal requirements, compliance BDD | Full stack with system overview | Yes (essential) |

---

## 11. TASK-REV-1505 Key Metrics

For reference, the architectural review provided these quantitative assessments:

- **Architecture Score**: 78/100 (up from 45/100 current state, potential 85/100 with all recommendations)
- **Context Reduction Target**: 25-40% reduction in Phase 2 prompt size (from ~25-40KB to ~15-30KB per task)
- **Revised Estimate**: 140-150h total Graphiti Refinement roadmap (original 125h + 20% buffer)
- **SOLID Compliance**: Current 63% → projected 76% after refinement

---

## 12. Next Steps

1. ✅ **Strategy validated** — overall direction confirmed
2. **Decide Phase 1 scope** — `/system-plan` + `/system-overview` + `/impact-analysis` + critical Graphiti entities
3. **Plan Phase 1 as a feature-plan** — dogfood the process by using GuardKit to build these improvements
4. **Start the PoA project with `/system-plan`** — establish domain before code
5. **Consider folding `/architecture-decision` into `/system-plan`** — ADRs as a natural output of system planning rather than a separate command
