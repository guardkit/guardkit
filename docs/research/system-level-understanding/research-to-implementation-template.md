# Research-to-Implementation Handoff Template

## How to Use This Template

This template structures the output of exploratory research sessions (Phase 1 — Claude Desktop with extended thinking) so that GuardKit's `/feature-plan` and AutoBuild's Player-Coach workflow (Phase 2 — local LLM on DGX Spark) can execute implementation with minimal ambiguity.

**The principle:** Every decision that requires intelligence should be made here. Every action that requires execution should be left to Phase 2. The local model should never need to *choose* — only *do*.

**How GuardKit consumes this:** The Decision Log (Section 2) becomes Architecture Decision Records seeded into Graphiti's temporal knowledge graph. The Implementation Tasks (Section 5) feed into `/feature-plan` which creates FEAT-XXX with subtasks. AutoBuild's Player-Coach loop then executes each task, with Graphiti providing semantic context retrieval at each turn — the Player only sees decisions relevant to the current task, not the entire project history.

Copy everything below the line into a new file for each feature/project, fill in the sections, and commit to your repo before switching to Phase 2.

---

# Feature Specification: [Feature Name]

**Date:** [Date]  
**Author:** Rich  
**Status:** Ready for Implementation  
**Research Method:** Claude Desktop (extended thinking) → GuardKit `/feature-plan`  
**Target Repo:** [repo path]  
**Target Branch:** `feature/[branch-name]`  
**Feature ID:** FEAT-XXX *(assigned by `/feature-plan`)*

---

## 1. Problem Statement

*What problem does this solve? Why does it matter? Keep this to 2-3 sentences — it grounds the local model on "why" without requiring it to reason about motivation.*

[Write problem statement here]

## 2. Decision Log

*Every architectural decision made during research. These become ADRs seeded into Graphiti via `guardkit graphiti add-context`. The local model must NOT revisit these — they are settled. During AutoBuild execution, Graphiti retrieves relevant decisions semantically based on the current task's domain tags and file paths.*

| # | Decision | Rationale | Alternatives Rejected | ADR Status |
|---|----------|-----------|----------------------|------------|
| D1 | [e.g., Use NATS JetStream for messaging] | [e.g., Sub-millisecond latency, built-in persistence, single binary] | [e.g., Kafka (overkill), Redis Streams (no KV store)] | Accepted |
| D2 | [e.g., Pydantic for message validation] | [e.g., Native JSON Schema, FastStream integration] | [e.g., marshmallow, dataclasses] | Accepted |
| D3 | | | | |

**Warnings & Constraints** *(seeded as Graphiti warning nodes — retrieved when tasks touch related areas):*
- [e.g., NATS JetStream must be enabled explicitly with `-js` flag]
- [e.g., FastStream 0.5.x has breaking changes from 0.4.x — pin exact version]
- [e.g., Reachy Mini SDK requires Python 3.10+, not compatible with 3.12 yet]

## 3. Architecture

### 3.1 System Context

*Where does this feature sit within Ship's Computer? What does it connect to?*

```
[ASCII diagram showing component relationships]
```

### 3.2 Component Design

*List every component that needs to be created or modified. Be explicit about file paths.*

| Component | File Path | Purpose | New/Modified |
|-----------|-----------|---------|-------------|
| [e.g., Base Agent] | `src/agents/base_agent.py` | Template for message-bus agents | New |
| [e.g., NATS Config] | `config/nats.yaml` | Message bus configuration | New |
| [e.g., Dashboard API] | `src/dashboard/api.py` | WebSocket endpoint for UI | New |

### 3.3 Data Flow

*Trace the path of data through the system for the primary use case. Number each step.*

```
1. User speaks to Reachy Mini → 
2. Whisper STT transcribes → 
3. Intent router classifies → 
4. [etc.]
```

### 3.4 Message Schemas

*Define exact message formats. The local model should copy these verbatim, not design them.*

```json
{
  "message_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "agent_id": "string",
  "event_type": "status | approval_request | command | result | error",
  "payload": {}
}
```

## 4. API Contracts

*Every interface between components. Include request/response shapes, error codes, and edge cases.*

### 4.1 [Interface Name]

**Endpoint:** `[method] [path]`  
**Request:**
```json
{}
```
**Response (success):**
```json
{}
```
**Response (error):**
```json
{}
```
**Edge cases:**
- [e.g., What happens if the agent is already paused?]
- [e.g., What if approval expires before response?]

## 5. Implementation Tasks

*Ordered list of atomic tasks. Each task should be completable in a single AutoBuild Player-Coach cycle. The Player implements code with full file system access. The Coach validates with read-only access, running test commands. Tasks are consumed by `/feature-build FEAT-XXX` (autonomous) or individually via `/task-work TASK-XXX` (interactive).*

### Task Metadata Guide

Each task includes metadata that drives GuardKit's job-specific context retrieval pipeline:

1. **Complexity** → determines Graphiti token budget (low: ~2000, medium: ~4000, high: ~6000+ tokens)
2. **Type** → influences which context categories are prioritised
3. **Domain tags** → semantic search keys for retrieving relevant ADRs, patterns, and warnings from Graphiti
4. **Relevant decisions** → explicit cross-references to Decision Log entries (Graphiti also retrieves these via semantic search, but explicit links ensure critical decisions are never missed)

### Task 1: [Task Name]
- **Task ID:** TASK-XXX *(assigned by `/feature-plan`)*
- **Complexity:** low | medium | high
- **Type:** implementation | refactor | integration | configuration
- **Domain tags:** `[e.g., nats, messaging, agent-lifecycle]`
- **Files to create/modify:** `[exact paths]`
- **Files NOT to touch:** `[explicit exclusions — prevents Player from wandering]`
- **Dependencies:** None (first task) / TASK-XXX
- **Inputs:** [What exists before this task]
- **Outputs:** [What exists after this task]
- **Relevant decisions:** D1, D2
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `src/agents/base_agent.py`
  - [ ] Class `BaseAgent` has methods: `publish_status`, `request_approval`, `run`
  - [ ] Tests pass: `pytest tests/test_base_agent.py -v`
  - [ ] Lint passes: `ruff check src/agents/base_agent.py`
- **Implementation notes:** [Prescriptive guidance — the Player follows these, the Coach validates against them.]
- **Player constraints:** [What the Player must NOT do — e.g., "Do not modify any files outside `src/agents/`"]
- **Coach validation commands:**
  ```bash
  pytest tests/test_base_agent.py -v
  ruff check src/agents/
  python -c "from src.agents.base_agent import BaseAgent; print('Import OK')"
  ```

### Task 2: [Task Name]
- **Task ID:** TASK-XXX
- **Complexity:** [low | medium | high]
- **Type:** [implementation | refactor | integration | configuration]
- **Domain tags:** `[tags]`
- **Files to create/modify:** `[exact paths]`
- **Files NOT to touch:** `[exclusions]`
- **Dependencies:** TASK-XXX (Task 1)
- **Inputs:** [What Task 1 produced]
- **Outputs:** [What this task produces]
- **Relevant decisions:** [D-numbers]
- **Acceptance criteria (machine-verifiable):**
  - [ ] [Specific file/class/function exists]
  - [ ] Tests pass: `[exact test command]`
  - [ ] Lint passes: `[exact lint command]`
- **Player constraints:** [Boundaries]
- **Coach validation commands:**
  ```bash
  [exact commands]
  ```

### Task 3: [Task Name]
[Continue pattern...]

## 6. Test Strategy

*What tests should exist when implementation is complete?*

### Unit Tests
| Test File | Covers | Key Assertions |
|-----------|--------|---------------|
| `tests/test_base_agent.py` | Base agent lifecycle | Publishes status on connect, handles commands |
| | | |

### Integration Tests
| Test File | Covers | Prerequisites |
|-----------|--------|--------------|
| `tests/integration/test_nats_flow.py` | End-to-end message flow | NATS running locally |
| | | |

### Manual Verification
- [ ] [e.g., Start agent, verify status appears on dashboard]
- [ ] [e.g., Send approval request, verify Reachy notification]

## 7. Dependencies & Setup

*Exact packages, versions, and configuration the local model will need.*

### Python Dependencies
```
# requirements.txt additions
faststream[nats]==0.5.x
pydantic>=2.0
```

### System Dependencies
```bash
# Commands to run before implementation
docker run -d --name nats -p 4222:4222 nats:latest -js
```

### Environment Variables
```bash
NATS_URL=nats://localhost:4222
```

## 8. File Tree (Target State)

*What the directory structure should look like after all tasks are complete.*

```
project-root/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py        # Task 1
│   │   └── twitter_agent.py     # Task 3
│   ├── dashboard/
│   │   ├── api.py               # Task 4
│   │   └── websocket.py         # Task 4
│   └── config/
│       └── nats.yaml            # Task 1
├── tests/
│   ├── test_base_agent.py       # Task 2
│   └── integration/
│       └── test_nats_flow.py    # Task 5
├── docs/
│   └── adr/
│       ├── ADR-001-nats-messaging.md    # Seeded to Graphiti
│       └── ADR-002-pydantic-validation.md
└── requirements.txt             # Updated in Task 1
```

## 9. Out of Scope

*Explicitly state what this feature does NOT include. Prevents the local model from scope-creeping.*

- [e.g., Authentication/authorization — separate feature]
- [e.g., Production deployment configuration]
- [e.g., Performance optimization — will be a follow-up]

## 10. Open Questions (Resolved)

*Questions that came up during research, with their resolutions. Stored in Graphiti as domain knowledge nodes for future retrieval.*

| Question | Resolution |
|----------|-----------|
| [e.g., Should we use WebSockets or SSE for dashboard?] | [WebSockets — need bidirectional for commands] |
| | |

---

## 11. Graphiti ADR Seeding

*This section replaces the old "CLAUDE.md Context" approach. Instead of a static context file at the repo root, decisions and project context are seeded into Graphiti's temporal knowledge graph via `guardkit graphiti add-context`. This gives AutoBuild semantic, task-relevant context retrieval — each task only receives the context it actually needs, within a dynamic token budget, rather than dumping the entire project history into every context window.*

### Why Graphiti Instead of CLAUDE.md

CLAUDE.md is a static file that gets loaded in full every time, regardless of what the current task needs. As projects grow, it bloats the context window and wastes tokens on irrelevant information. Graphiti stores knowledge as a temporal graph with semantic search — the job-specific context retrieval pipeline analyses each task's complexity, type, and domain tags, then queries Graphiti for only the relevant ADRs, patterns, warnings, and architecture context, allocating a dynamic token budget (2000-6000+ tokens) based on task complexity.

### How Context Flows Through AutoBuild

```
Phase 1 (This Template)          Graphiti Knowledge Graph          Phase 2 (AutoBuild)
┌─────────────────────┐          ┌───────────────────┐          ┌─────────────────────┐
│ Decision Log (§2)   │─ADRs────▶│ architecture_     │          │                     │
│                     │          │ decisions          │──────┐   │  Player receives    │
│ Warnings (§2)       │─────────▶│ warnings           │──┐   │   │  task-relevant      │
│                     │          │                    │  │   │   │  context at each    │
│ Architecture (§3)   │─────────▶│ feature_context    │  │   ├──▶│  turn, not the      │
│                     │          │                    │  │   │   │  whole project       │
│ Dependencies (§7)   │─────────▶│ technology_stack   │  │   │   │                     │
│                     │          │                    │  │   │   │  Coach validates     │
│ API Contracts (§4)  │─────────▶│ integration_points │──┘   │   │  against acceptance │
│                     │          │                    │      │   │  criteria            │
│ Task Notes (§5)     │─────────▶│ patterns           │──────┘   │                     │
└─────────────────────┘          └───────────────────┘          └─────────────────────┘
                                         ▲
                                         │
                                  TaskAnalyzer examines:
                                  - task type & complexity
                                  - domain tags
                                  - novelty (first time?)
                                  - AutoBuild turn number
```

### ADR File Format

*Create these files in `docs/adr/` before seeding. Each maps to a decision from Section 2:*

```markdown
# ADR-001: [Decision Title from D1]

**Status:** Accepted  
**Date:** [Date]  
**Context:** [Why this decision was needed — the problem being solved]  
**Decision:** [What was decided — the choice made]  
**Rationale:** [Why this option — the reasoning]  
**Alternatives Rejected:** [What else was considered and why it lost]  
**Consequences:** [What this means for implementation — constraints, patterns to follow]
```

*Repeat for each decision D1, D2, D3...*

### Seeding Commands

```bash
# 1. Ensure Graphiti + Neo4j are running
guardkit graphiti status

# 2. Seed ADR files into knowledge graph
guardkit graphiti add-context docs/adr/ADR-*.md

# 3. Seed this feature specification (architecture context, component design)
guardkit graphiti add-context docs/features/FEAT-XXX-spec.md

# 4. Seed warnings/constraints as separate nodes (higher retrieval priority)
guardkit graphiti add-context docs/warnings/[feature-name]-warnings.md

# 5. Verify seeding was successful
guardkit graphiti verify --verbose

# 6. Check graph contents
guardkit graphiti status
```

### Graphiti Context Categories Populated

After seeding, these categories become available to AutoBuild's context retrieval pipeline:

| Category | Source Section | Retrieved When | Token Priority |
|----------|---------------|---------------|---------------|
| `architecture_decisions` | Decision Log (§2) + ADR files | Tasks referencing related components | High |
| `feature_context` | Full spec file | All tasks in FEAT-XXX | Medium |
| `warnings` | Warnings & Constraints (§2) | Tasks touching warned-about areas | High |
| `technology_stack` | Dependencies (§7) | Tasks using listed libraries | Low |
| `integration_points` | API Contracts (§4) | Cross-component tasks | Medium |
| `patterns` | Implementation notes in tasks (§5) | Similar task types | Medium |
| `domain_knowledge` | Open Questions (§10) | Semantic match to task content | Low |

### AutoBuild Turn State Context

During Player-Coach execution, Graphiti also tracks turn states — what the Player attempted, what the Coach rejected, and why. On subsequent turns:

- **Turn 1:** Player receives ADRs, warnings, feature context, and patterns
- **Turn 2+:** Player also receives previous turn states (what was rejected, the Coach's feedback), with adjusted token allocation (more turn states, fewer general patterns)
- **Max 5 turns** before escalation to human review

### Quality Gate Configuration

*Define per-feature quality gate settings that AutoBuild's Coach uses:*

```yaml
# .guardkit/quality-gates/FEAT-XXX.yaml
feature_id: FEAT-XXX
quality_gates:
  lint:
    command: "ruff check src/"
    required: true
  type_check:
    command: "mypy src/ --ignore-missing-imports"
    required: false  # Enable once types are stable
  unit_tests:
    command: "pytest tests/ -v --tb=short"
    required: true
  integration_tests:
    command: "pytest tests/integration/ -v"
    required: false  # Only for integration tasks
  coverage:
    command: "pytest --cov=src --cov-fail-under=80"
    required: false  # Enable after Task 2
```

---

## Phase 2 Execution Workflow

*After Graphiti is seeded and `/feature-plan` has created FEAT-XXX:*

```bash
# On DGX Spark — vLLM serving local model

# Option A: Full autonomous build (Player-Coach loop)
guardkit feature-build FEAT-XXX
# → Player implements each task with Graphiti context
# → Coach validates against acceptance criteria + quality gates
# → Up to 5 turns per task before escalation
# → Work preserved in .guardkit/worktrees/FEAT-XXX/

# Review the diff
cd .guardkit/worktrees/FEAT-XXX && git diff main

# Accept and merge
guardkit feature-complete FEAT-XXX

# Option B: Interactive task-by-task (human-in-the-loop)
guardkit task-work TASK-001
# → Review output
guardkit task-complete TASK-001
guardkit task-work TASK-002
# → Continue sequentially
```
