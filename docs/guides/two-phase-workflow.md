# Two-Phase Workflow Guide

**Version**: 1.0.0
**Last Updated**: 2026-02-10
**Audience**: Developers using GuardKit for AI-assisted feature development

---

## Overview

The **two-phase workflow** is GuardKit's approach for developing complex features when you need to leverage different AI models for different stages of work:

- **Phase 1 (Research & Planning)**: High-quality reasoning with a frontier model (e.g., Claude on MacBook)
- **Phase 2 (Implementation)**: Autonomous code generation with a local model (e.g., Claude on Dell ProMax or local LLM)

This workflow is particularly valuable when:

1. You want to capture complex architectural decisions during research
2. You need to hand off implementation to autonomous agents
3. You're working across machines or environments
4. You want clear separation between "thinking" and "doing"

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TWO-PHASE WORKFLOW OVERVIEW                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 1: Research & Planning (Frontier Model)                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                                                                    │     │
│  │  🧠 Extended Thinking → 📋 Research Template → 📊 Decision Log    │     │
│  │                                                                    │     │
│  │  - Architectural decisions (D1, D2, D3...)                        │     │
│  │  - Technology choices with rationale                               │     │
│  │  - Task breakdown with acceptance criteria                         │     │
│  │  - Risk assessment and warnings                                    │     │
│  │                                                                    │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                              │                                               │
│                              ▼                                               │
│                    /feature-plan --from-spec                                 │
│                              │                                               │
│                              ▼                                               │
│  PHASE 2: Implementation (Local Model / AutoBuild)                          │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                                                                    │     │
│  │  📁 Tasks (design_approved) → 🤖 Player-Coach Loop → ✅ Complete  │     │
│  │                                                                    │     │
│  │  - Autonomous implementation via guardkit feature-build           │     │
│  │  - Graphiti provides semantic context per task                    │     │
│  │  - Quality gates enforce test coverage and architecture           │     │
│  │                                                                    │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Research & Planning

Phase 1 is where you leverage a frontier model's reasoning capabilities to make all architectural decisions **before** any code is written. The goal is to produce a comprehensive specification that enables autonomous execution in Phase 2.

### When to Use Phase 1

Use Phase 1 when you have:

- A new feature requiring architectural decisions
- Complex requirements that need exploration
- Technical trade-offs to evaluate
- Multi-task features requiring dependency ordering

### The Research Template

The **Research-to-Implementation Template** structures your exploratory research output so that GuardKit's autonomous systems can execute without ambiguity.

**Core principle**: Every decision that requires intelligence should be made during research. Every action that requires execution should be left to implementation. The local model should never need to *choose* — only *do*.

**Create a spec file**: `docs/research/FEAT-XXX-spec.md`

```markdown
# Feature Specification: [Feature Name]

## 1. Problem Statement
Ship's Computer agents currently have no standardized way to communicate
with each other or request human approval. This prevents autonomous workflows
and forces agents to work in isolation.

## 2. Decision Log

| # | Decision | Rationale | Alternatives Rejected | ADR Status |
|---|----------|-----------|----------------------|------------|
| D1 | Use NATS JetStream | Sub-ms latency, persistence | Kafka (overkill), Redis | Accepted |
| D2 | Pydantic for validation | Native FastAPI support | Marshmallow | Accepted |

### Warnings & Constraints
- NATS JetStream requires `-js` flag
- FastStream 0.5.x has breaking changes from 0.4.x — pin exact version

## 3. Architecture

### 3.1 System Context
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│ Agent A      │───────▶│ NATS Bus     │◀───────│ Agent B      │
│              │ pub    │              │ sub    │              │
└──────────────┘        └──────────────┘        └──────────────┘

### 3.2 Component Design

| Component | File Path | Purpose | New/Modified |
|-----------|-----------|---------|--------------|
| Base Agent | `src/agents/base_agent.py` | Message bus template | New |
| NATS Config | `config/nats.yaml` | Bus configuration | New |

## 4. API Contracts

### POST /api/agent/status
**Request:** { "agent_id": "string", "status": "busy|idle" }
**Response:** { "success": true, "timestamp": "ISO-8601" }

## 5. Implementation Tasks

### Task 1: Create Base Agent Class
- **Complexity:** medium
- **Domain tags:** `agent-lifecycle, nats, messaging`
- **Files to create:** `src/agents/base_agent.py`
- **Files NOT to touch:** Any files outside `src/agents/`
- **Relevant decisions:** D1, D2
- **Acceptance criteria:**
  - [ ] File exists: `src/agents/base_agent.py`
  - [ ] Tests pass: `pytest tests/test_base_agent.py -v`
- **Coach validation commands:**
  ```bash
  pytest tests/test_base_agent.py -v
  ruff check src/agents/
  ```

## 6. Test Strategy

| Test File | Covers | Key Assertions |
|-----------|--------|----------------|
| `tests/test_base_agent.py` | Agent lifecycle | Publishes status on connect |

## 7. Dependencies & Setup
```
faststream[nats]==0.5.x
pydantic>=2.0
```

## 8. Out of Scope
- Authentication/authorization
- Production deployment configuration
```

**See**: [Research Template Guide](research-template.md) for complete section-by-section guidance.

### Running Feature-Plan with From-Spec

Once your research template is complete, use `/feature-plan --from-spec` to generate tasks:

```bash
# Basic from-spec mode
/feature-plan --from-spec docs/research/FEAT-GR-003-spec.md

# With target optimization for local model execution
/feature-plan --from-spec docs/research/FEAT-GR-003-spec.md --target local-model

# Generate ADRs and quality gates
/feature-plan --from-spec docs/research/FEAT-GR-003-spec.md \
              --target interactive \
              --generate-adrs \
              --generate-quality-gates
```

**Output structure:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE PLANNING: From Research-to-Implementation Template
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Parsing spec file...
✅ Spec parsed: 5 tasks, 3 decisions, 2 warnings

Step 2: Resolving target configuration...
✅ Target: local-model (optimized verbosity)

Step 3: Enriching tasks...
✅ Enriched 5 tasks with target-specific details

Step 4: Rendering task files...
✅ Created tasks/design_approved/TASK-FP002-001-task-title.md
✅ Created tasks/design_approved/TASK-FP002-002-task-title.md
✅ Created tasks/design_approved/TASK-FP002-003-task-title.md
✅ Created tasks/design_approved/TASK-FP002-004-task-title.md
✅ Created tasks/design_approved/TASK-FP002-005-task-title.md

Step 5: Generating seed script...
✅ Created .guardkit/seed/FEAT-FP002-seed.sh

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ FEATURE PLANNING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Tasks: 5 (in design_approved state)
📁 ADRs: 3
⚠️  Warnings: 2

Next steps:
  1. Review tasks in tasks/design_approved/
  2. Run seed script: bash .guardkit/seed/FEAT-FP002-seed.sh
  3. Begin implementation: guardkit feature-build FEAT-FP002
```

---

## Feature-Plan Flags Reference

### --from-spec

Parse a Research-to-Implementation Template file and generate tasks directly (bypasses standard review flow).

```bash
/feature-plan --from-spec path/to/spec.md
```

**What it does:**
1. Parses the template sections (Decision Log, Tasks, etc.)
2. Creates tasks in `design_approved` state (ready for implementation)
3. Generates ADRs if `--generate-adrs` flag is set
4. Creates a seed script for Graphiti

### --target

Set output verbosity optimized for the target executor.

| Value | Description | Use Case |
|-------|-------------|----------|
| `interactive` | Full detail, human-readable | Human execution via Claude Code |
| `local-model` | Optimized for Claude-level models | Local LLM on DGX/ProMax |
| `auto` | Minimal detail for autonomous systems | AutoBuild with Player-Coach |

```bash
# For local model execution (recommended for Phase 2)
/feature-plan --from-spec spec.md --target local-model
```

### --generate-adrs

Generate Architecture Decision Record (ADR) files from the Decision Log.

```bash
/feature-plan --from-spec spec.md --generate-adrs
```

**Creates**: `.guardkit/adrs/ADR-{feature_id}-{slug}.md` for each decision

### --generate-quality-gates

Generate per-feature quality gate YAML configuration.

```bash
/feature-plan --from-spec spec.md --generate-quality-gates
```

**Creates**: `.guardkit/quality-gates/{feature_id}.yaml`

### Combined Example

```bash
/feature-plan --from-spec docs/research/FEAT-AUTH-spec.md \
              --target local-model \
              --generate-adrs \
              --generate-quality-gates
```

---

## Graphiti Seeding

After `/feature-plan --from-spec` generates tasks, you need to seed the knowledge graph with your architectural decisions. This enables semantic context retrieval during Phase 2 implementation.

### What Gets Seeded

| Content | Source | Purpose |
|---------|--------|---------|
| ADRs | Decision Log (§2) | Architectural decisions for context retrieval |
| Feature Spec | Full template | Feature context and success criteria |
| Warnings | Warnings (§2) | High-priority retrieval during related tasks |
| Patterns | Implementation notes | Reusable patterns for similar tasks |

### The Seed Script

`/feature-plan --from-spec` generates a seed script at:
```
scripts/seed-FEAT-XXX.sh
```

This can also be located at `.guardkit/seed/FEAT-{id}-seed.sh` depending on your project configuration.

**Example seed script (`scripts/seed-FEAT-FP002.sh`):**

```bash
#!/bin/bash
# Seed script for FEAT-FP002

# Ensure Graphiti is running
guardkit graphiti status || exit 1

# Seed ADRs
guardkit graphiti add-context .guardkit/adrs/ADR-FP002-*.md

# Seed feature specification
guardkit graphiti add-context docs/research/FEAT-FP002-spec.md

# Seed warnings with high priority
guardkit graphiti add-context .guardkit/warnings/FEAT-FP002.md

# Verify seeding
guardkit graphiti verify --verbose

echo "✅ Graphiti seeding complete for FEAT-FP002"
```

### Running the Seed Script

```bash
# Execute the seed script
bash scripts/seed-FEAT-FP002.sh

# Alternative location
bash .guardkit/seed/FEAT-FP002-seed.sh

# Or seed manually
guardkit graphiti add-context docs/research/FEAT-FP002-spec.md
guardkit graphiti add-context .guardkit/adrs/ADR-FP002-*.md
```

### Verifying Seeding

```bash
# Check Graphiti status
guardkit graphiti status

# Search for seeded content
guardkit graphiti search "NATS messaging agent"

# Verify specific entities
guardkit graphiti verify --verbose
```

**Expected output:**
```
[Graphiti] Status: Connected (Neo4j localhost:7687)
[Graphiti] Entities: 45
[Graphiti] Relationships: 112

Recent additions (last 24h):
  ✓ ADR-FP002-001-nats-messaging (architecture_decisions)
  ✓ ADR-FP002-002-pydantic-validation (architecture_decisions)
  ✓ FEAT-FP002-spec (feature_specs)
  ✓ Warning: FastStream version pinning (warnings)
```

---

## Phase 2: Implementation

Phase 2 is where the autonomous implementation happens. The local model (or AutoBuild system) executes tasks using the decisions and context from Phase 1.

### The Player-Coach Loop

GuardKit's AutoBuild uses an **adversarial cooperation** pattern with two agents:

```
┌─────────────────────────────────────────────────────────────────┐
│                     PLAYER-COACH LOOP                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐                    ┌──────────────┐          │
│  │   PLAYER     │                    │    COACH     │          │
│  │   Agent      │───────────────────▶│    Agent     │          │
│  └──────────────┘   Implementation   └──────────────┘          │
│        │            Report                  │                   │
│        │                                    │                   │
│        │            Feedback                │                   │
│        │◀───────────────────────────────────│                   │
│        │            or Approval             │                   │
│                                                                 │
│  Player: Full file access      Coach: Read-only access         │
│  - Implements code            - Runs tests independently        │
│  - Creates tests              - Validates acceptance criteria   │
│  - Gets Graphiti context      - Ignores Player's self-reports  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key insight**: The Coach **ignores** what the Player says it did and verifies independently. This prevents premature success declarations.

### Starting Implementation

#### Using guardkit feature-build (Recommended)

```bash
# Build entire feature with wave orchestration
guardkit feature-build FEAT-FP002

# With verbose output
guardkit feature-build FEAT-FP002 --verbose

# Resume interrupted build
guardkit feature-build FEAT-FP002 --resume
```

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE BUILD: FEAT-FP002
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Loading feature: .guardkit/features/FEAT-FP002.yaml
Tasks: 5
Parallel groups: 3 waves

Wave 1: [TASK-FP002-001]
  ▶ Starting Player-Coach loop for TASK-FP002-001...
  [Turn 1] Player: Implementing base agent class...
  [Turn 1] Coach: Tests failing - missing publish_status method
  [Turn 2] Player: Added publish_status method...
  [Turn 2] Coach: ✅ APPROVED - All criteria met

Wave 2: [TASK-FP002-002, TASK-FP002-003]
  ▶ Executing 2 tasks in parallel...
  ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ FEATURE BUILD COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tasks completed: 5/5
Worktree: .guardkit/worktrees/FEAT-FP002/

Next steps:
  1. Review changes: cd .guardkit/worktrees/FEAT-FP002 && git diff main
  2. Complete feature: guardkit feature-complete FEAT-FP002
```

#### Using /task-work with --implement-only

For individual task execution via Claude Code:

```bash
# Execute single task (must be in design_approved state)
/task-work TASK-FP002-001 --implement-only

# With TDD mode
/task-work TASK-FP002-001 --implement-only --mode=tdd
```

### Context Retrieval During Implementation

During each Player turn, Graphiti retrieves relevant context:

| Context Category | Source | When Retrieved |
|------------------|--------|----------------|
| `architecture_decisions` | ADRs (D1, D2...) | Tasks referencing related components |
| `feature_context` | Spec file | All tasks in feature |
| `warnings` | Warnings section | Tasks touching warned areas |
| `patterns` | Implementation notes | Similar task types |
| `role_constraints` | AutoBuild config | Every turn (Player boundaries) |
| `quality_gates` | Quality gate YAML | Every turn (thresholds) |

**Token budget by complexity:**
- Simple (1-3): ~2000 tokens
- Medium (4-6): ~4000 tokens
- Complex (7-10): ~6000+ tokens

---

## Complete Workflow Example

Here's a complete example from research to implementation:

### Step 1: Create Research Specification (Phase 1)

```bash
# Create spec file with extended thinking
# (Use Claude Desktop or Claude Code with frontier model)
```

Create `docs/research/FEAT-AUTH-spec.md`:

```markdown
# Feature Specification: OAuth2 Authentication

## 1. Problem Statement
Users cannot currently log in via social providers. We need OAuth2
integration with Google and GitHub.

## 2. Decision Log

| # | Decision | Rationale | Alternatives Rejected |
|---|----------|-----------|----------------------|
| D1 | Use FastAPI OAuth2 library | Native integration | Authlib (complex) |
| D2 | JWT with refresh tokens | Stateless, scalable | Session cookies |
| D3 | Store tokens in httpOnly cookies | XSS protection | localStorage |

### Warnings
- Refresh token rotation must be implemented to prevent replay attacks
- PKCE flow required for public clients

## 3. Architecture
...

## 5. Implementation Tasks

### Task 1: Create OAuth2 Service Interface
- **Complexity:** medium
- **Files to create:** `src/auth/oauth2.py`, `src/auth/__init__.py`
- **Acceptance criteria:**
  - [ ] File exists: `src/auth/oauth2.py`
  - [ ] Class `OAuth2Service` has methods: `authenticate`, `refresh`, `revoke`
  - [ ] Tests pass: `pytest tests/test_oauth2.py -v`
```

### Step 2: Generate Tasks and Seed Graphiti

```bash
# Generate tasks from spec
/feature-plan --from-spec docs/research/FEAT-AUTH-spec.md \
              --target local-model \
              --generate-adrs

# Seed knowledge graph
bash .guardkit/seed/FEAT-AUTH-seed.sh

# Verify seeding
guardkit graphiti search "OAuth2 JWT"
```

### Step 3: Execute Implementation (Phase 2)

```bash
# Start autonomous build
guardkit feature-build FEAT-AUTH --verbose

# Monitor progress
guardkit autobuild status FEAT-AUTH
```

### Step 4: Review and Complete

```bash
# Review changes in worktree
cd .guardkit/worktrees/FEAT-AUTH
git diff main

# Run final tests
pytest tests/ -v

# Complete and merge
guardkit feature-complete FEAT-AUTH
```

---

## Troubleshooting

### Tasks Not in design_approved State

**Problem**: `/task-work --implement-only` fails because task is in `backlog` state.

**Solution**: Use `/feature-plan --from-spec` which creates tasks directly in `design_approved` state.

### Graphiti Context Not Retrieved

**Problem**: Player doesn't receive architectural decisions during implementation.

**Solution**:
1. Verify Graphiti is running: `guardkit graphiti status`
2. Run seed script: `bash .guardkit/seed/FEAT-XXX-seed.sh`
3. Check seeding: `guardkit graphiti verify --verbose`

### Coach Repeatedly Rejects

**Problem**: Coach provides feedback but Player doesn't improve.

**Possible causes**:
1. Acceptance criteria too vague (make them machine-verifiable)
2. Missing dependencies in spec (add to Dependencies section)
3. Warnings not seeded (check seed script ran successfully)

**Solution**: Review spec for ambiguity, ensure all decisions are explicit.

### Local Model Wanders from Spec

**Problem**: Implementation includes features not in spec.

**Solution**:
1. Add explicit "Out of Scope" section to spec
2. Add "Files NOT to touch" constraints to tasks
3. Use `--target local-model` for optimized prompts

### Seed Script Fails

**Problem**: `guardkit graphiti add-context` returns errors.

**Solution**:
1. Ensure Neo4j is running: `docker ps | grep neo4j`
2. Check Graphiti connection: `guardkit graphiti status`
3. Verify file paths in seed script exist

---

## Best Practices

### Phase 1 Best Practices

1. **Complete all decisions** before moving to Phase 2
2. **Use machine-verifiable acceptance criteria** (file exists, tests pass, etc.)
3. **Include Coach validation commands** for every task
4. **Document warnings explicitly** - they get high retrieval priority
5. **Keep tasks atomic** - one logical unit per task

### Phase 2 Best Practices

1. **Always seed Graphiti** before starting implementation
2. **Use `--target local-model`** for optimized Phase 2 execution
3. **Review worktree changes** before completing features
4. **Monitor Player-Coach turns** with `--verbose` flag
5. **Resume interrupted builds** with `--resume` flag

### Template Best Practices

1. **Be prescriptive, not descriptive** - show exact code patterns
2. **Include explicit file paths** - no ambiguity about where files go
3. **Cross-reference decisions** - use D1, D2 in relevant task notes
4. **Define clear boundaries** - what NOT to do is as important as what to do

---

## See Also

- [Research Template Guide](research-template.md) - Detailed template section guide
- [AutoBuild Workflow](autobuild-workflow.md) - Player-Coach architecture
- [Graphiti Integration Guide](graphiti-integration-guide.md) - Knowledge graph setup
- [Feature-Plan Command](../../installer/core/commands/feature-plan.md) - Full flag reference
- [Feature-Build Command](../../installer/core/commands/feature-build.md) - AutoBuild CLI

---

**Version**: 1.0.0 | **License**: MIT | **Repository**: https://github.com/guardkit/guardkit
