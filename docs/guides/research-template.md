# Research-to-Implementation Template Guide

## Introduction

The Research-to-Implementation Template structures the output of exploratory research sessions so that GuardKit's `/feature-plan` and AutoBuild's Player-Coach workflow can execute implementation with minimal ambiguity.

**When to use this template:**

- Starting a new feature that requires architectural decisions
- After deep research/exploration with extended thinking
- Before switching from design (Claude Desktop) to execution (local LLM)
- When you need to hand off implementation to autonomous agents

**Core principle:** Every decision that requires intelligence should be made during research. Every action that requires execution should be left to implementation. The local model should never need to *choose* — only *do*.

## How GuardKit Consumes This Template

The template feeds into GuardKit's workflow at multiple stages:

1. **Decision Log (Section 2)** → ADRs seeded into Graphiti's temporal knowledge graph
2. **Implementation Tasks (Section 5)** → Feed into `/feature-plan` which creates FEAT-XXX with subtasks
3. **AutoBuild Execution** → Player-Coach loop executes each task with Graphiti providing semantic context retrieval
4. **Quality Gates** → Acceptance criteria become automated validation checkpoints

During AutoBuild execution, the Player only sees decisions relevant to the current task (via Graphiti semantic search), not the entire project history. This prevents context window bloat and improves focus.

## Section-by-Section Explanation

### Section 1: Problem Statement

**Purpose:** Ground the implementation team on the "why" without requiring reasoning about motivation.

**What to include:**
- The problem being solved (2-3 sentences)
- Why it matters
- Clear scope boundaries

**Example:**
```markdown
Ship's Computer agents currently have no standardized way to communicate
with each other or request human approval. This prevents autonomous workflows
and forces agents to work in isolation. We need a lightweight message bus
with built-in persistence and approval workflow support.
```

**Common mistakes to avoid:**
- Writing a novel (keep it brief)
- Mixing problem statement with solution details
- Leaving motivation implicit

---

### Section 2: Decision Log

**Purpose:** Capture every architectural decision made during research. These become ADRs seeded into Graphiti, ensuring the local model never revisits settled decisions.

**What to include:**
- Each decision with a unique ID (D1, D2, D3...)
- Rationale explaining why this choice was made
- Alternatives that were considered and rejected
- ADR status (typically "Accepted")
- Warnings & Constraints subsection for gotchas

**Format:**

| # | Decision | Rationale | Alternatives Rejected | ADR Status |
|---|----------|-----------|----------------------|------------|
| D1 | Use NATS JetStream for messaging | Sub-millisecond latency, built-in persistence, single binary | Kafka (overkill), Redis Streams (no KV store) | Accepted |

**Warnings & Constraints example:**
```markdown
- NATS JetStream must be enabled explicitly with `-js` flag
- FastStream 0.5.x has breaking changes from 0.4.x — pin exact version
- Reachy Mini SDK requires Python 3.10+, not compatible with 3.12 yet
```

**Common mistakes to avoid:**
- Decisions without rationale ("because I said so")
- Missing alternatives (shows you didn't evaluate options)
- Vague warnings that don't prevent specific errors

**Graphiti integration:** During AutoBuild execution, Graphiti retrieves relevant decisions semantically based on the current task's domain tags and file paths. Warnings are seeded as high-priority nodes and retrieved when tasks touch related areas.

---

### Section 3: Architecture

**Purpose:** Define the system structure before implementation begins. Prevents architectural drift.

#### 3.1 System Context

**What to include:**
- ASCII diagram showing how this feature fits into the broader system
- External dependencies (APIs, services, databases)
- Component boundaries

**Example:**
```
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│ Agent A      │───────▶│ NATS Bus     │◀───────│ Agent B      │
│              │ pub    │              │ sub    │              │
└──────────────┘        └──────────────┘        └──────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │ Dashboard UI │
                        │              │
                        └──────────────┘
```

#### 3.2 Component Design

**What to include:**
- Every component (new or modified)
- Exact file paths
- Purpose of each component
- New/Modified status

**Example:**

| Component | File Path | Purpose | New/Modified |
|-----------|-----------|---------|-------------|
| Base Agent | `src/agents/base_agent.py` | Template for message-bus agents | New |
| NATS Config | `config/nats.yaml` | Message bus configuration | New |
| Dashboard API | `src/dashboard/api.py` | WebSocket endpoint for UI | New |

**Common mistakes to avoid:**
- Vague file paths ("somewhere in the agent folder")
- Missing components (forces Player to make design choices)
- Unclear whether to create or modify files

#### 3.3 Data Flow

**What to include:**
- Step-by-step trace of data through the system
- Numbered steps for clarity
- Primary use case (happy path)

**Example:**
```
1. User speaks to Reachy Mini →
2. Whisper STT transcribes →
3. Intent router classifies →
4. Task agent executes →
5. Result published to NATS →
6. Dashboard receives WebSocket update
```

#### 3.4 Message Schemas

**Purpose:** Define exact message formats that the local model copies verbatim, not designs.

**What to include:**
- JSON schemas with field types
- Required vs optional fields
- Example values
- Validation rules

**Example:**
```json
{
  "message_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "agent_id": "string",
  "event_type": "status | approval_request | command | result | error",
  "payload": {
    "status": "idle | busy | waiting",
    "message": "string"
  }
}
```

**Common mistakes to avoid:**
- Leaving field types ambiguous
- Missing required fields
- No validation constraints

---

### Section 4: API Contracts

**Purpose:** Define every interface between components with exact request/response shapes.

**What to include:**
- Endpoint path and HTTP method
- Request schema
- Success response schema
- Error response schema
- Edge cases and how to handle them

**Example:**
```markdown
### 4.1 Agent Status Update

**Endpoint:** `POST /api/agent/status`
**Request:**
{
  "agent_id": "twitter-agent",
  "status": "busy",
  "message": "Processing tweet queue"
}

**Response (success):**
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00Z"
}

**Response (error):**
{
  "success": false,
  "error": "invalid_agent_id",
  "message": "Agent 'twitter-agent' not registered"
}

**Edge cases:**
- If agent is already at the requested status → return success (idempotent)
- If agent sends malformed status → return 400 with validation error
```

**Common mistakes to avoid:**
- Missing error cases
- No edge case handling
- Ambiguous response formats

---

### Section 5: Implementation Tasks

**Purpose:** Break down implementation into atomic, ordered tasks that AutoBuild can execute autonomously.

**What to include for each task:**
- **Task ID:** TASK-XXX (assigned by `/feature-plan`)
- **Complexity:** low | medium | high (determines Graphiti token budget)
- **Type:** implementation | refactor | integration | configuration
- **Domain tags:** Semantic search keys for Graphiti (e.g., `nats, messaging, agent-lifecycle`)
- **Files to create/modify:** Exact paths
- **Files NOT to touch:** Explicit exclusions (prevents wandering)
- **Dependencies:** Which prior tasks must complete first
- **Inputs:** What exists before this task
- **Outputs:** What exists after this task
- **Relevant decisions:** Cross-references to Decision Log (D1, D2...)
- **Acceptance criteria:** Machine-verifiable checkpoints
- **Implementation notes:** Prescriptive guidance the Player follows
- **Player constraints:** What the Player must NOT do
- **Coach validation commands:** Exact commands the Coach runs

**Example:**
```markdown
### Task 1: Create Base Agent Class

- **Task ID:** TASK-001
- **Complexity:** medium
- **Type:** implementation
- **Domain tags:** `agent-lifecycle, nats, messaging`
- **Files to create/modify:** `src/agents/base_agent.py`, `src/agents/__init__.py`
- **Files NOT to touch:** Any files outside `src/agents/`
- **Dependencies:** None (first task)
- **Inputs:** Empty `src/agents/` directory
- **Outputs:** BaseAgent class with publish/subscribe methods
- **Relevant decisions:** D1 (NATS JetStream), D2 (Pydantic validation)
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `src/agents/base_agent.py`
  - [ ] Class `BaseAgent` has methods: `publish_status`, `request_approval`, `run`
  - [ ] Tests pass: `pytest tests/test_base_agent.py -v`
  - [ ] Lint passes: `ruff check src/agents/base_agent.py`
- **Implementation notes:**
  - Inherit from `faststream.nats.NatsBroker`
  - Use Pydantic models for message validation
  - Implement graceful shutdown in `run()` method
- **Player constraints:**
  - Do not modify any files outside `src/agents/`
  - Do not add dependencies beyond faststream and pydantic
- **Coach validation commands:**
  ```bash
  pytest tests/test_base_agent.py -v
  ruff check src/agents/
  python -c "from src.agents.base_agent import BaseAgent; print('Import OK')"
  ```
```

**Common mistakes to avoid:**
- Tasks that are too large (>1 AutoBuild cycle)
- Vague acceptance criteria ("code should work")
- Missing constraints (Player implements extra features)
- No validation commands (Coach can't verify)

**Task metadata drives Graphiti retrieval:**
- **Complexity** → token budget (low: ~2000, medium: ~4000, high: ~6000+)
- **Type** → which context categories are prioritized
- **Domain tags** → semantic search keys for relevant ADRs/patterns/warnings
- **Relevant decisions** → explicit cross-references (Graphiti also does semantic search, but explicit links ensure critical decisions are never missed)

---

### Section 6: Test Strategy

**Purpose:** Define what tests should exist when implementation is complete.

**What to include:**
- Unit tests table (file, what it covers, key assertions)
- Integration tests table (file, what it covers, prerequisites)
- Manual verification checklist

**Example:**

**Unit Tests:**

| Test File | Covers | Key Assertions |
|-----------|--------|---------------|
| `tests/test_base_agent.py` | Base agent lifecycle | Publishes status on connect, handles commands |
| `tests/test_message_validation.py` | Pydantic schemas | Rejects invalid messages, validates field types |

**Integration Tests:**

| Test File | Covers | Prerequisites |
|-----------|--------|--------------|
| `tests/integration/test_nats_flow.py` | End-to-end message flow | NATS running locally |

**Manual Verification:**
- [ ] Start agent, verify status appears on dashboard
- [ ] Send approval request, verify Reachy notification
- [ ] Shut down agent, verify graceful cleanup

**Common mistakes to avoid:**
- No integration tests (unit tests don't catch real-world issues)
- Missing prerequisites (tests fail in CI)
- No manual verification (some things need human eyes)

---

### Section 7: Dependencies & Setup

**Purpose:** Provide exact packages, versions, and configuration the local model needs.

**What to include:**
- Python dependencies with version constraints
- System dependencies (Docker, databases, etc.)
- Environment variables
- Setup commands

**Example:**

**Python Dependencies:**
```
# requirements.txt additions
faststream[nats]==0.5.x
pydantic>=2.0
pytest-asyncio>=0.21.0
```

**System Dependencies:**
```bash
# Commands to run before implementation
docker run -d --name nats -p 4222:4222 nats:latest -js
```

**Environment Variables:**
```bash
NATS_URL=nats://localhost:4222
LOG_LEVEL=INFO
```

**Common mistakes to avoid:**
- No version constraints (dependency hell)
- Missing system dependencies (implementation fails)
- Hardcoded secrets (use environment variables)

---

### Section 8: File Tree (Target State)

**Purpose:** Show what the directory structure should look like after all tasks are complete.

**What to include:**
- Complete directory tree
- Comments indicating which task creates each file
- All new files, not just source code

**Example:**
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

**Common mistakes to avoid:**
- Incomplete tree (missing directories)
- No task annotations (unclear what creates what)
- Missing test files

---

### Section 9: Out of Scope

**Purpose:** Explicitly state what this feature does NOT include to prevent scope creep.

**What to include:**
- Features deliberately excluded
- Future enhancements
- Separate features that might be confused with this one

**Example:**
```markdown
- Authentication/authorization — separate FEAT-XXX
- Production deployment configuration — handled by DevOps
- Performance optimization — will be a follow-up after baseline implementation
- Multi-tenancy support — not needed for MVP
```

**Common mistakes to avoid:**
- No out-of-scope section (Player adds extra features)
- Vague exclusions ("other stuff")
- Missing related features that could be confused

---

### Section 10: Open Questions (Resolved)

**Purpose:** Document questions that came up during research with their resolutions. Stored in Graphiti as domain knowledge nodes.

**Format:**

| Question | Resolution |
|----------|-----------|
| Should we use WebSockets or SSE for dashboard? | WebSockets — need bidirectional for commands |
| How to handle agent crashes? | Implement heartbeat + auto-restart via supervisor |

**Common mistakes to avoid:**
- Unresolved questions (research isn't done)
- Missing the decision rationale
- Questions that should be in Decision Log

---

### Section 11: Graphiti ADR Seeding

**Purpose:** Explain how to seed architectural decisions into Graphiti's temporal knowledge graph for semantic retrieval during AutoBuild.

**Why Graphiti Instead of CLAUDE.md:**

Traditional CLAUDE.md files:
- Static file loaded in full every time
- Wastes tokens on irrelevant information
- Grows linearly with project size
- No semantic retrieval

Graphiti approach:
- Temporal knowledge graph with semantic search
- Task-specific context retrieval
- Dynamic token budget based on complexity (2000-6000+ tokens)
- Only relevant ADRs/patterns/warnings per task

**How Context Flows Through AutoBuild:**

```
Phase 1 (Research)          Graphiti Knowledge Graph          Phase 2 (AutoBuild)
┌─────────────────────┐    ┌───────────────────┐            ┌─────────────────────┐
│ Decision Log (§2)   │───▶│ architecture_     │            │                     │
│                     │    │ decisions          │──────┐     │  Player receives    │
│ Warnings (§2)       │───▶│ warnings           │──┐   │     │  task-relevant      │
│                     │    │                    │  │   │     │  context at each    │
│ Architecture (§3)   │───▶│ feature_context    │  │   ├────▶│  turn, not the      │
│                     │    │                    │  │   │     │  whole project       │
│ Dependencies (§7)   │───▶│ technology_stack   │  │   │     │                     │
│                     │    │                    │  │   │     │  Coach validates     │
│ API Contracts (§4)  │───▶│ integration_points │──┘   │     │  against acceptance │
│                     │    │                    │      │     │  criteria            │
│ Task Notes (§5)     │───▶│ patterns           │──────┘     │                     │
└─────────────────────┘    └───────────────────┘            └─────────────────────┘
```

**ADR File Format:**

Create these files in `docs/adr/` before seeding:

```markdown
# ADR-001: [Decision Title from D1]

**Status:** Accepted
**Date:** [Date]
**Context:** [Why this decision was needed]
**Decision:** [What was decided]
**Rationale:** [Why this option]
**Alternatives Rejected:** [What else was considered and why]
**Consequences:** [What this means for implementation]
```

**Seeding Commands:**

```bash
# 1. Ensure Graphiti + Neo4j are running
guardkit graphiti status

# 2. Seed ADR files into knowledge graph
guardkit graphiti add-context docs/adr/ADR-*.md

# 3. Seed this feature specification
guardkit graphiti add-context docs/features/FEAT-XXX-spec.md

# 4. Seed warnings/constraints as separate nodes (higher retrieval priority)
guardkit graphiti add-context docs/warnings/[feature-name]-warnings.md

# 5. Verify seeding was successful
guardkit graphiti verify --verbose
```

**Graphiti Context Categories:**

After seeding, these categories become available to AutoBuild's context retrieval pipeline:

| Category | Source Section | Retrieved When | Token Priority |
|----------|---------------|---------------|---------------|
| `architecture_decisions` | Decision Log (§2) + ADR files | Tasks referencing related components | High |
| `feature_context` | Full spec file | All tasks in FEAT-XXX | Medium |
| `warnings` | Warnings & Constraints (§2) | Tasks touching warned-about areas | High |
| `technology_stack` | Dependencies (§7) | Tasks using listed libraries | Low |
| `integration_points` | API Contracts (§4) | Cross-component tasks | Medium |
| `patterns` | Implementation notes (§5) | Similar task types | Medium |
| `domain_knowledge` | Open Questions (§10) | Semantic match to task content | Low |

**AutoBuild Turn State Context:**

During Player-Coach execution:
- **Turn 1:** Player receives ADRs, warnings, feature context, and patterns
- **Turn 2+:** Player also receives previous turn states (what was rejected, Coach's feedback), with adjusted token allocation
- **Max 5 turns** before escalation to human review

---

## Tips for Local Model Execution

Writing specs that execute well with autonomous agents:

### 1. Be Prescriptive, Not Descriptive

**Bad:**
```markdown
Create a message bus system that allows agents to communicate.
```

**Good:**
```markdown
Create a BaseAgent class in `src/agents/base_agent.py` that:
- Inherits from faststream.nats.NatsBroker
- Has a `publish_status(status: str, message: str)` method
- Has a `request_approval(action: str, context: dict)` method
- Uses Pydantic models for message validation
```

### 2. Every Decision Should Be Made Upfront

Don't leave choices to the Player:
- Which library to use → Decision Log
- How to structure classes → Implementation notes
- What to name variables → Code examples in task notes
- Error handling strategy → API Contracts section

### 3. Use Machine-Verifiable Acceptance Criteria

**Bad:**
```markdown
- [ ] Code should work correctly
- [ ] Agent communicates properly
```

**Good:**
```markdown
- [ ] File exists: `src/agents/base_agent.py`
- [ ] Class `BaseAgent` has methods: `publish_status`, `request_approval`, `run`
- [ ] Tests pass: `pytest tests/test_base_agent.py -v`
- [ ] Lint passes: `ruff check src/agents/`
- [ ] Coverage >= 80%: `pytest --cov=src/agents --cov-fail-under=80`
```

### 4. Keep Files to Touch Explicit

**Bad:**
```markdown
Files to modify: The agent directory
```

**Good:**
```markdown
Files to create/modify:
- `src/agents/base_agent.py`
- `src/agents/__init__.py`
- `tests/test_base_agent.py`

Files NOT to touch:
- Any files outside `src/agents/`
- `src/agents/legacy_agent.py` (deprecated, will be removed separately)
```

### 5. Define Clear Boundaries (What NOT to Do)

Use "Out of Scope" and "Player Constraints" sections:

```markdown
## Player Constraints
- Do not add authentication (separate FEAT-XXX)
- Do not modify database schema
- Do not add new dependencies beyond those listed in Section 7
- Do not implement caching (will be added later)
```

### 6. Provide Coach Validation Commands

Give the Coach exact commands to run:

```bash
# Not this:
pytest

# This:
pytest tests/test_base_agent.py -v --tb=short
ruff check src/agents/
mypy src/agents/ --ignore-missing-imports
python -c "from src.agents.base_agent import BaseAgent; print('Import OK')"
```

### 7. Use Examples Liberally

Show, don't just tell:

```markdown
**Implementation notes:**
The publish_status method should look like this:

def publish_status(self, status: str, message: str) -> None:
    """Publish agent status to the message bus."""
    payload = StatusMessage(
        agent_id=self.agent_id,
        status=status,
        message=message,
        timestamp=datetime.utcnow()
    )
    self.publish("agent.status", payload.model_dump_json())
```

---

## Integration with GuardKit

**From Research to Implementation:**

1. **Research Phase** (Claude Desktop with extended thinking)
   - Fill out this template
   - Make all architectural decisions
   - Create ADR files

2. **Graphiti Seeding**
   ```bash
   guardkit graphiti add-context docs/adr/ADR-*.md
   guardkit graphiti add-context docs/features/FEAT-XXX-spec.md
   ```

3. **Feature Planning**
   ```bash
   guardkit feature-plan docs/features/FEAT-XXX-spec.md
   # → Creates FEAT-XXX with subtasks from Section 5
   ```

4. **AutoBuild Execution** (local LLM on DGX Spark)
   ```bash
   # Option A: Full autonomous build
   guardkit feature-build FEAT-XXX

   # Option B: Interactive task-by-task
   guardkit task-work TASK-001
   guardkit task-complete TASK-001
   ```

5. **Review and Merge**
   ```bash
   cd .guardkit/worktrees/FEAT-XXX
   git diff main
   # Review, then merge if approved
   ```

**The full workflow ensures:**
- All decisions made during research are preserved in Graphiti
- Implementation is autonomous with semantic context retrieval
- Quality gates enforce the test strategy
- No scope creep (Player constraints + Out of Scope section)
- Traceability from decision to implementation

---

## Summary

The Research-to-Implementation Template bridges the gap between exploratory research and autonomous execution. By making all decisions upfront and providing machine-verifiable acceptance criteria, you enable local LLMs to execute complex implementations without requiring human-level reasoning.

**Key success factors:**
1. Complete Decision Log (no open questions)
2. Prescriptive implementation notes (not descriptive)
3. Machine-verifiable acceptance criteria
4. Clear boundaries (files to touch, out of scope, constraints)
5. Graphiti seeding for semantic context retrieval

When used with GuardKit's AutoBuild, this template enables autonomous multi-task feature implementation with quality gates, test enforcement, and architectural validation — all while keeping the local model focused on execution, not decision-making.
