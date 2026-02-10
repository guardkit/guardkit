# Research-to-Implementation Handoff Template

## How to Use This Template

This template structures the output of exploratory research sessions (Phase 1 — Claude Desktop with extended thinking) so that GuardKit's `/feature-plan` and AutoBuild's Player-Coach workflow (Phase 2 — local LLM on DGX Spark) can execute implementation with minimal ambiguity.

**The principle:** Every decision that requires intelligence should be made here. Every action that requires execution should be left to Phase 2. The local model should never need to *choose* — only *do*.

**How GuardKit consumes this:** The Decision Log (Section 2) becomes Architecture Decision Records seeded into Graphiti's temporal knowledge graph. The Implementation Tasks (Section 5) feed into `/feature-plan` which creates FEAT-XXX with subtasks. AutoBuild's Player-Coach loop then executes each task, with Graphiti providing semantic context retrieval at each turn — the Player only sees decisions relevant to the current task, not the entire project history.

Copy everything below the line into a new file for each feature/project, fill in the sections, and commit to your repo before switching to Phase 2.

---

# Feature Specification: [Feature Name]

**Date:** [YYYY-MM-DD]
**Author:** [Your Name]
**Status:** Ready for Implementation
**Research Method:** Claude Desktop (extended thinking) → GuardKit `/feature-plan`
**Target Repo:** [repo path or name]
**Target Branch:** `feature/[branch-name]`
**Feature ID:** FEAT-XXX *(assigned by `/feature-plan`)*

---

## 1. Problem Statement

*What problem does this solve? Why does it matter? Keep this to 2-3 sentences — it grounds the local model on "why" without requiring it to reason about motivation.*

[Write problem statement here. Example: "Our agents currently cannot communicate with each other or request human approval, forcing them to work in isolation and preventing autonomous workflows. We need a lightweight message bus with built-in persistence and approval workflow support."]

---

## 2. Decision Log

*Every architectural decision made during research. These become ADRs seeded into Graphiti via `guardkit graphiti add-context`. The local model must NOT revisit these — they are settled. During AutoBuild execution, Graphiti retrieves relevant decisions semantically based on the current task's domain tags and file paths.*

| # | Decision | Rationale | Alternatives Rejected | ADR Status |
|---|----------|-----------|----------------------|------------|
| D1 | [PLACEHOLDER: e.g., "Use NATS JetStream for messaging"] | [PLACEHOLDER: e.g., "Sub-millisecond latency, built-in persistence, single binary"] | [PLACEHOLDER: e.g., "Kafka (overkill), Redis Streams (no KV store)"] | Accepted |
| D2 | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] | Accepted |
| D3 | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] | Accepted |

**Warnings & Constraints** *(seeded as Graphiti warning nodes — retrieved when tasks touch related areas):*
- [PLACEHOLDER: e.g., "NATS JetStream must be enabled explicitly with `-js` flag"]
- [PLACEHOLDER: e.g., "FastStream 0.5.x has breaking changes from 0.4.x — pin exact version"]
- [PLACEHOLDER: e.g., "SDK requires Python 3.10+, not compatible with 3.12 yet"]

---

## 3. Architecture

### 3.1 System Context

*Where does this feature sit within the broader system? What does it connect to?*

```
[PLACEHOLDER: ASCII diagram showing component relationships]

Example:
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│ Component A  │───────▶│ Message Bus  │◀───────│ Component B  │
│              │        │              │        │              │
└──────────────┘        └──────────────┘        └──────────────┘
```

### 3.2 Component Design

*List every component that needs to be created or modified. Be explicit about file paths.*

| Component | File Path | Purpose | New/Modified |
|-----------|-----------|---------|-------------|
| [PLACEHOLDER: e.g., "Base Agent"] | `[PLACEHOLDER: e.g., "src/agents/base_agent.py"]` | [PLACEHOLDER: e.g., "Template for message-bus agents"] | New |
| [PLACEHOLDER] | `[PLACEHOLDER]` | [PLACEHOLDER] | New/Modified |
| [PLACEHOLDER] | `[PLACEHOLDER]` | [PLACEHOLDER] | New/Modified |

### 3.3 Data Flow

*Trace the path of data through the system for the primary use case. Number each step.*

```
[PLACEHOLDER: Numbered data flow]

Example:
1. User performs action →
2. Component A processes →
3. Message published to bus →
4. Component B receives →
5. Result returned →
6. UI updated
```

### 3.4 Message Schemas

*Define exact message formats. The local model should copy these verbatim, not design them.*

```json
[PLACEHOLDER: JSON schema with field types]

Example:
{
  "message_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "component_id": "string",
  "event_type": "status | request | response | error",
  "payload": {
    "field1": "type",
    "field2": "type"
  }
}
```

---

## 4. API Contracts

*Every interface between components. Include request/response shapes, error codes, and edge cases.*

### 4.1 [Interface Name]

**Endpoint:** `[METHOD] [path]`
**Request:**
```json
[PLACEHOLDER: Request schema]
{
  "field1": "value1",
  "field2": "value2"
}
```

**Response (success):**
```json
[PLACEHOLDER: Success response schema]
{
  "success": true,
  "data": {}
}
```

**Response (error):**
```json
[PLACEHOLDER: Error response schema]
{
  "success": false,
  "error": "error_code",
  "message": "Human-readable message"
}
```

**Edge cases:**
- [PLACEHOLDER: e.g., "What happens if resource already exists?"]
- [PLACEHOLDER: e.g., "What if request times out?"]

### 4.2 [Interface Name]

[PLACEHOLDER: Repeat pattern for each API contract]

---

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
- **Domain tags:** `[PLACEHOLDER: e.g., "messaging, lifecycle, validation"]`
- **Files to create/modify:** `[PLACEHOLDER: exact file paths]`
- **Files NOT to touch:** `[PLACEHOLDER: explicit exclusions to prevent Player from wandering]`
- **Dependencies:** None (first task) / TASK-XXX
- **Inputs:** [PLACEHOLDER: What exists before this task starts]
- **Outputs:** [PLACEHOLDER: What exists after this task completes]
- **Relevant decisions:** D1, D2 [PLACEHOLDER: Reference Decision Log entries]
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `[PLACEHOLDER: path]`
  - [ ] Class/function exists: `[PLACEHOLDER: name with methods]`
  - [ ] Tests pass: `[PLACEHOLDER: exact test command]`
  - [ ] Lint passes: `[PLACEHOLDER: exact lint command]`
  - [ ] Coverage >= X%: `[PLACEHOLDER: coverage command]`
- **Implementation notes:** [PLACEHOLDER: Prescriptive guidance — the Player follows these, the Coach validates against them. Include code examples, naming conventions, patterns to follow.]
- **Player constraints:** [PLACEHOLDER: What the Player must NOT do — e.g., "Do not modify any files outside src/module/"]
- **Coach validation commands:**
  ```bash
  [PLACEHOLDER: Exact commands the Coach runs to verify implementation]
  # Example:
  # pytest tests/test_module.py -v --tb=short
  # ruff check src/module/
  # python -c "from src.module import ClassName; print('Import OK')"
  ```

### Task 2: [Task Name]

- **Task ID:** TASK-XXX
- **Complexity:** low | medium | high
- **Type:** implementation | refactor | integration | configuration
- **Domain tags:** `[PLACEHOLDER]`
- **Files to create/modify:** `[PLACEHOLDER]`
- **Files NOT to touch:** `[PLACEHOLDER]`
- **Dependencies:** TASK-XXX (Task 1)
- **Inputs:** [PLACEHOLDER: What Task 1 produced]
- **Outputs:** [PLACEHOLDER: What this task produces]
- **Relevant decisions:** [PLACEHOLDER: D-numbers]
- **Acceptance criteria (machine-verifiable):**
  - [ ] [PLACEHOLDER: Specific verifiable condition]
  - [ ] Tests pass: `[PLACEHOLDER: exact command]`
  - [ ] Lint passes: `[PLACEHOLDER: exact command]`
- **Implementation notes:** [PLACEHOLDER]
- **Player constraints:** [PLACEHOLDER]
- **Coach validation commands:**
  ```bash
  [PLACEHOLDER: exact commands]
  ```

### Task 3: [Task Name]

[PLACEHOLDER: Repeat pattern for each task. Each task should be atomic and completable in one AutoBuild cycle.]

---

## 6. Test Strategy

*What tests should exist when implementation is complete?*

### Unit Tests

| Test File | Covers | Key Assertions |
|-----------|--------|---------------|
| `[PLACEHOLDER: e.g., "tests/test_module.py"]` | [PLACEHOLDER: What it tests] | [PLACEHOLDER: Key assertions] |
| `[PLACEHOLDER]` | [PLACEHOLDER] | [PLACEHOLDER] |

### Integration Tests

| Test File | Covers | Prerequisites |
|-----------|--------|--------------|
| `[PLACEHOLDER: e.g., "tests/integration/test_flow.py"]` | [PLACEHOLDER: End-to-end scenario] | [PLACEHOLDER: e.g., "Service running locally"] |
| `[PLACEHOLDER]` | [PLACEHOLDER] | [PLACEHOLDER] |

### Manual Verification

- [ ] [PLACEHOLDER: e.g., "Start service, verify endpoint responds"]
- [ ] [PLACEHOLDER: e.g., "Trigger workflow, verify result"]
- [ ] [PLACEHOLDER]

---

## 7. Dependencies & Setup

*Exact packages, versions, and configuration the local model will need.*

### Python Dependencies

```
[PLACEHOLDER: requirements.txt additions with version constraints]
# Example:
# package-name==X.Y.x
# another-package>=X.Y
```

### System Dependencies

```bash
[PLACEHOLDER: Commands to run before implementation]
# Example:
# docker run -d --name service -p 4222:4222 image:latest
```

### Environment Variables

```bash
[PLACEHOLDER: Required environment variables]
# Example:
# SERVICE_URL=http://localhost:4222
# LOG_LEVEL=INFO
```

---

## 8. File Tree (Target State)

*What the directory structure should look like after all tasks are complete.*

```
[PLACEHOLDER: Complete directory tree with task annotations]

Example:
project-root/
├── src/
│   ├── module/
│   │   ├── __init__.py
│   │   ├── core.py              # Task 1
│   │   └── utils.py             # Task 2
│   └── config/
│       └── settings.yaml        # Task 1
├── tests/
│   ├── test_core.py             # Task 2
│   └── integration/
│       └── test_flow.py         # Task 3
├── docs/
│   └── adr/
│       ├── ADR-001-decision.md  # Seeded to Graphiti
│       └── ADR-002-decision.md
└── requirements.txt             # Updated in Task 1
```

---

## 9. Out of Scope

*Explicitly state what this feature does NOT include. Prevents the local model from scope-creeping.*

- [PLACEHOLDER: e.g., "Authentication/authorization — separate feature"]
- [PLACEHOLDER: e.g., "Production deployment configuration"]
- [PLACEHOLDER: e.g., "Performance optimization — will be a follow-up"]
- [PLACEHOLDER]

---

## 10. Open Questions (Resolved)

*Questions that came up during research, with their resolutions. Stored in Graphiti as domain knowledge nodes for future retrieval.*

| Question | Resolution |
|----------|-----------|
| [PLACEHOLDER: e.g., "Should we use WebSockets or SSE?"] | [PLACEHOLDER: e.g., "WebSockets — need bidirectional communication"] |
| [PLACEHOLDER] | [PLACEHOLDER] |

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
**Date:** [YYYY-MM-DD]
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
    command: "[PLACEHOLDER: e.g., 'ruff check src/']"
    required: true
  type_check:
    command: "[PLACEHOLDER: e.g., 'mypy src/ --ignore-missing-imports']"
    required: false  # Enable once types are stable
  unit_tests:
    command: "[PLACEHOLDER: e.g., 'pytest tests/ -v --tb=short']"
    required: true
  integration_tests:
    command: "[PLACEHOLDER: e.g., 'pytest tests/integration/ -v']"
    required: false  # Only for integration tasks
  coverage:
    command: "[PLACEHOLDER: e.g., 'pytest --cov=src --cov-fail-under=80']"
    required: false  # Enable after baseline tests exist
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
