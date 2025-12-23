# GuardKit Agent: Product Specification

**Product:** GuardKit Agent  
**Type:** Standalone LangGraph-based autonomous development tool  
**Status:** Specification for RequireKit epic/feature generation  
**Date:** December 19, 2025

---

## Product Vision

GuardKit Agent is a **standalone, vendor-neutral, autonomous development tool** that implements the proven GuardKit workflow using LangGraph. It adds adversarial cooperation (coach-player dialectical loop) to achieve higher completion rates than single-agent "vibe coding" approaches.

### What GuardKit Agent Is

- A **new standalone Python CLI tool** (not a Claude Code extension)
- Built on **LangGraph** for workflow orchestration
- **Multi-model**: Works with Claude, Devstral 2, DeepSeek, or any compatible LLM
- **No subscription required**: Not dependent on Claude Max ($200/mo)
- Implements **adversarial cooperation** from Block AI Research's proven g3 framework

### What GuardKit Agent Is NOT

- NOT an extension to GuardKit (Claude Code)
- NOT dependent on Claude Code slash commands
- NOT vendor-locked to Anthropic
- NOT a swarm/hive multi-agent orchestration system

---

## Core Functionality to Replicate from GuardKit

### Commands to Implement

| GuardKit Command | GuardKit Agent Equivalent | Priority |
|------------------|---------------------------|----------|
| `/task-create` | `gka task create "description"` | P0 |
| `/task-work` | `gka task work TASK-XXX` | P0 |
| `/task-complete` | `gka task complete TASK-XXX` | P0 |
| `/task-review` | `gka task review TASK-XXX` | P1 |
| `/task-status` | `gka task status [TASK-XXX]` | P1 |
| `/feature-plan` | `gka feature plan "description"` | P0 |
| `guardkit init` | `gka init` | P0 |
| `/template-create` | `gka template create` | P1 |
| `/template-init` | `gka template apply <n>` | P1 |
| `/agent-enhance` | `gka agent enhance` | P1 |
| (new) | `gka agent list` | P2 |
| (new) | `gka template list` | P2 |
| (new) | `gka context show` | P2 |
| (new) | `gka context query` | P2 |

### Workflow Phases to Implement

From existing GuardKit/LangGraph research:

```
Phase 2:    Implementation Planning
Phase 2.5:  Architectural Review (SOLID, DRY, YAGNI scoring)
Phase 2.7:  Complexity Evaluation (1-10 scale)
Phase 2.8:  Human Checkpoint (complexity-gated)
Phase 3:    Implementation (code generation)
Phase 4:    Testing (test execution)
Phase 4.5:  Test Enforcement (retry loop, max 3 attempts)
Phase 5:    Code Review
Phase 5.5:  Plan Audit (scope creep detection)
```

### Quality Gates

| Gate | Threshold | Behavior |
|------|-----------|----------|
| Compilation | 100% | Block if fails |
| Tests Pass | 100% | Auto-retry up to 3 times |
| Line Coverage | ≥80% | Request more tests |
| Branch Coverage | ≥75% | Request more tests |
| Architectural Score | ≥60/100 | Human checkpoint |
| Plan Variance | ±20% LOC, ±30% duration | Flag for review |

---

## New Capability: Adversarial Cooperation

### The Pattern (from Block AI Research)

Instead of a single agent implementing and self-validating, GuardKit Agent uses two cooperating agents:

**Player Agent** (Implementation-focused):
- Reads requirements and implements solutions
- Writes code, runs commands, creates tests
- Responds to coach feedback with targeted improvements
- Does NOT self-validate success

**Coach Agent** (Validation-focused):
- Validates implementation against requirements
- Runs tests, checks edge cases
- Provides specific, actionable feedback
- Approves ONLY when ALL requirements are met
- Does NOT trust player's self-report of success

### Key Insight

> "The key insight in the adversarial dyad is to discard the implementing agent's self-report of success and have the coach perform an independent evaluation of compliance to requirements."
> — Block AI Research

### Bounded Process

| Bound | Value | Purpose |
|-------|-------|---------|
| Turn Limits | 10 max | Prevents infinite loops |
| Fresh Context | Per turn | Prevents context pollution |
| Requirements Contract | Feature plan | Consistent evaluation criteria |
| Approval Gate | Coach approval | Only coach can declare success |

### Dialectical Loop Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DIALECTICAL LOOP                             │
│  ┌─────────────────┐          ┌─────────────────┐              │
│  │     PLAYER      │          │      COACH      │              │
│  │                 │ feedback │                 │              │
│  │  • Implement    │◄────────►│  • Review       │              │
│  │  • Create       │          │  • Test         │              │
│  │  • Execute      │          │  • Critique     │              │
│  │  • Iterate      │          │  • Approve      │              │
│  └─────────────────┘          └─────────────────┘              │
│            │                           │                        │
│            └───────────┬───────────────┘                        │
│                        │                                        │
│              SHARED WORKSPACE                                   │
│     ┌──────────────────┴──────────────────┐                    │
│     │  • Feature Plan / Task (requirements)│                    │
│     │  • Codebase (working directory)      │                    │
│     │  • Quality Gates (validation rules)  │                    │
│     └─────────────────────────────────────┘                    │
│                                                                 │
│     Bounds: Max 10 Turns, Fresh Context Each Turn              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Deployment Options

GuardKit Agent supports flexible deployment from solo developer to team scale.

### Solo Developer (Local)

Everything runs on your machine via Docker:

```yaml
# docker-compose.yml (solo dev)
version: '3.8'
services:
  falkordb:
    image: falkordb/falkordb:latest
    ports:
      - "6379:6379"
    volumes:
      - falkordb_data:/data
    command: ["--loadmodule", "/usr/lib/redis/modules/falkordb.so"]

volumes:
  falkordb_data:
```

```toml
# gka.toml (solo dev)
[graph]
backend = "falkordb"
connection = "redis://localhost:6379"

[models]
default = "devstral-local"  # Run locally on RTX 4090

[models.devstral-local]
provider = "mistral"
model = "devstral-small-2"
endpoint = "http://localhost:8000"  # Ollama or vLLM
```

**Cost: $0/month** (excluding hardware/electricity)

**Setup:**
```bash
# One-time setup
docker-compose up -d
ollama pull devstral-small  # Or use vLLM

# Initialize project
gka init
```

### Small Team (Shared Cloud)

FalkorDB Cloud + shared API keys:

```toml
# gka.toml (team - shared)
[graph]
backend = "falkordb"
connection = "redis://user:pass@your-instance.falkordb.cloud:6379"

[models]
default = "devstral-2"

[models.devstral-2]
provider = "mistral"
model = "devstral-2"
api_key_env = "MISTRAL_API_KEY"  # Team shared key
```

**Cost: ~$20-50/month** (FalkorDB Cloud starter + Mistral API usage)

**Benefits:**
- Shared knowledge graph across team
- Decisions and patterns learned by one developer available to all
- No local Docker required
- Works from any machine

### Enterprise Team (Self-Hosted Cloud)

Docker on shared infrastructure (AWS, GCP, Azure):

```yaml
# docker-compose.yml (team - self-hosted)
version: '3.8'
services:
  falkordb:
    image: falkordb/falkordb:latest
    ports:
      - "6379:6379"
    volumes:
      - /mnt/efs/falkordb:/data  # Shared storage
    deploy:
      resources:
        limits:
          memory: 4G

  gka-api:  # Optional: shared API for team
    image: guardkit-agent/server:latest
    environment:
      - FALKORDB_URL=redis://falkordb:6379
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
    ports:
      - "8080:8080"
```

```toml
# gka.toml (enterprise)
[graph]
backend = "falkordb"
connection = "redis://falkordb.internal.company.com:6379"

[models]
default = "devstral-2"
# Or self-hosted models for data security
```

**Benefits:**
- Data stays within company infrastructure
- Shared knowledge graph with access controls
- Can use self-hosted models for sensitive codebases

### Deployment Comparison

| Aspect | Solo (Local) | Team (Cloud) | Enterprise (Self-Hosted) |
|--------|--------------|--------------|--------------------------|
| **Cost** | $0 | $20-50/mo | Infrastructure costs |
| **Setup** | Docker + Ollama | API keys only | DevOps required |
| **Knowledge sharing** | Single user | Team-wide | Team-wide + ACL |
| **Data location** | Local machine | Cloud provider | Your infrastructure |
| **Model options** | Local or API | API | API or self-hosted |
| **Offline capable** | ✅ Yes | ❌ No | ✅ With local models |

### MCP Server Option (Future)

For integration with Claude Code, Cursor, or other MCP-compatible tools:

```toml
# gka.toml (MCP mode)
[mcp]
enabled = true
port = 3000

[mcp.tools]
# Expose GuardKit Agent as MCP tools
task_create = true
task_work = true
context_query = true
```

This would allow:
- Using GuardKit Agent's knowledge graph from Claude Code
- Hybrid workflow: Claude Code for interaction, GuardKit Agent for context
- Best of both worlds: slash commands + knowledge graph

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-19 | Research session | Initial specification: GuardKit workflow + adversarial cooperation |
| 2025-12-20 | Research session | Added: Knowledge graph, job-specific context, project analysis commands |
| 2025-12-20 | Research session | Added: Deployment options, authentication & security |
| 2025-12-20 | Research session | Added: Comprehensive LLM configuration, cost comparison |
| 2025-12-20 | Research session | Added: Knowledge Graph MCP, sub-agent architecture |
| 2025-12-20 | Research session | Added: Orchestrator Mode, Review Agent |
| 2025-12-22 | Research session | **RENAMED**: AutoBuild → GuardKit Agent. CLI: `gka`. Config: `.gka/`, `gka.toml`. Env vars: `GKA_*`. Directory: `guardkit-agent/` |
