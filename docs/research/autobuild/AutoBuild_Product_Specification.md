# AutoBuild: Product Specification

**Product:** AutoBuild  
**Type:** Standalone LangGraph-based autonomous development tool  
**Status:** Specification for RequireKit epic/feature generation  
**Date:** December 19, 2025

---

## Product Vision

AutoBuild is a **standalone, vendor-neutral, autonomous development tool** that implements the proven GuardKit workflow using LangGraph. It adds adversarial cooperation (coach-player dialectical loop) to achieve higher completion rates than single-agent "vibe coding" approaches.

### What AutoBuild Is

- A **new standalone Python CLI tool** (not a Claude Code extension)
- Built on **LangGraph** for workflow orchestration
- **Multi-model**: Works with Claude, Devstral 2, DeepSeek, or any compatible LLM
- **No subscription required**: Not dependent on Claude Max ($200/mo)
- Implements **adversarial cooperation** from Block AI Research's proven g3 framework

### What AutoBuild Is NOT

- NOT an extension to GuardKit
- NOT dependent on Claude Code slash commands
- NOT vendor-locked to Anthropic
- NOT a swarm/hive multi-agent orchestration system

---

## Core Functionality to Replicate from GuardKit

### Commands to Implement

| GuardKit Command | AutoBuild Equivalent | Priority |
|------------------|---------------------|----------|
| `/task-create` | `autobuild task create "description"` | P0 |
| `/task-work` | `autobuild task work TASK-XXX` | P0 |
| `/task-complete` | `autobuild task complete TASK-XXX` | P0 |
| `/task-review` | `autobuild task review TASK-XXX` | P1 |
| `/task-status` | `autobuild task status [TASK-XXX]` | P1 |
| `/feature-plan` | `autobuild feature plan "description"` | P0 |
| `guardkit init` | `autobuild init` | P0 |
| `/template-create` | `autobuild template create` | P1 |
| `/template-init` | `autobuild template apply <name>` | P1 |
| `/agent-enhance` | `autobuild agent enhance` | P1 |
| (new) | `autobuild agent list` | P2 |
| (new) | `autobuild template list` | P2 |
| (new) | `autobuild context show` | P2 |
| (new) | `autobuild context query` | P2 |

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

## Testing Strategy for GuardKit/AutoBuild Hybrid Architecture

### The Integration Seam Problem

GuardKit and AutoBuild have a unique testing challenge: they combine **Claude Code slash commands**, **agent instructions**, **Claude Agent SDK**, and **standard Python code**. Traditional testing approaches (including BDD) test the wrong layer.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Where Bugs Actually Live                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Slash Command ──┬── Claude Code Interpreter (black box)        │
│                  │        ↓                                     │
│                  │   Agent Selection (LLM decision)             │
│                  │        ↓                                     │
│                  │   Agent Instructions → Python call?          │
│                  │        ↓                                     │
│  ══════════════ SEAM: Did it actually call Python? ══════════  │
│                  │        ↓                                     │
│  Python Code ────┴── Works perfectly in pytest                  │
│                                                                 │
│  ══════════════ SEAM: Response back to Claude Code ══════════  │
│                          ↓                                      │
│                    Claude formats/displays                      │
│                          ↓                                      │
│  ══════════════ SEAM: Human sees what they expect? ══════════  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Why BDD Is The Wrong Tool Here

| What BDD Tests | What Actually Breaks |
|----------------|---------------------|
| "Given complexity 7, When coach reviews, Then escalate" | Python logic ✅ |
| Python function returns correct enum | Unit test passes ✅ |
| Mock returns expected value | All green ✅ |
| **Actual slash command invokes Python?** | Never tested ❌ |
| **Claude Code parses response correctly?** | Never tested ❌ |
| **Agent actually calls function vs doing its own thing?** | Never tested ❌ |

**Real-world failure modes from GuardKit development:**
1. Python code written and tested, but never integrated with slash command
2. Agent instructions called mocks instead of real functions
3. Claude Code interpreted the command and "did its own thing" ignoring agent instructions
4. Python function worked, but agent didn't call it (implemented logic inline)

**BDD scenarios test the logic. The bugs are in the wiring.**

### Testing Approach for Hybrid Architecture

#### 1. Unit Tests (Python Logic)

Standard pytest for pure Python functions. These will pass. The logic isn't the problem.

```python
# ✅ This works fine
def test_evaluate_checkpoint_escalates_on_high_complexity():
    result = evaluate_checkpoint(complexity=8, changes=["auth.py"])
    assert result.action == CheckpointAction.ESCALATE
```

#### 2. Integration Smoke Tests (Actually Run Commands)

Use Claude Agent SDK to invoke real commands and verify real outcomes:

```python
# tests/integration/test_slash_commands.py
import pytest
from claude_code_sdk import query, ClaudeCodeOptions

@pytest.mark.integration
async def test_task_work_creates_implementation():
    """Actually run /task-work and verify real files created."""
    options = ClaudeCodeOptions(cwd="/tmp/test-project")
    
    result = await query(
        prompt="/task-work TASK-001",
        options=options
    )
    
    # Verify real outcomes, not mocked responses
    assert Path("/tmp/test-project/src/feature.py").exists()
    assert "def " in Path("/tmp/test-project/src/feature.py").read_text()

@pytest.mark.integration  
async def test_review_agent_escalates_breaking_changes():
    """Verify Review Agent actually escalates, not just that logic works."""
    result = await query(
        prompt="/autobuild FEAT-001 --orchestrate --review-agent",
        options=ClaudeCodeOptions(cwd="/tmp/test-project")
    )
    
    # Check that escalation actually happened
    assert "ESCALATED" in result.output or "Awaiting human" in result.output
```

#### 3. Agent Contract Tests

Explicit contracts in agent instructions that can be verified:

```markdown
# .claude/agents/review-agent.md
---
name: review-agent
contracts:
  - must_call: guardkit.review.evaluate_checkpoint
  - must_not: implement checkpoint logic directly
  - must_log: all escalation decisions
---

## Required Python Calls

You MUST call these functions - do NOT implement this logic yourself:

- `guardkit.review.evaluate_checkpoint(complexity, changes)` - Returns APPROVE/ESCALATE
- `guardkit.review.log_decision(task_id, decision, rationale)` - Audit trail

## Contract Verification

After completing your review, output a contract verification block:

```json
{
  "contracts_honored": {
    "evaluate_checkpoint_called": true,
    "decision_logged": true,
    "no_inline_logic": true
  }
}
```
```

#### 4. Trace-Based Validation

Log what actually happened and verify against expectations:

```python
# guardkit/tracing.py
from dataclasses import dataclass, field
from typing import List
import json

@dataclass
class WorkflowTrace:
    task_id: str
    python_calls: List[str] = field(default_factory=list)
    agent_invocations: dict = field(default_factory=dict)
    llm_calls: int = 0
    
    def verify_contract(self, expected_calls: List[str]) -> bool:
        return all(call in self.python_calls for call in expected_calls)

# In tests
def test_review_agent_honors_contract():
    trace = load_workflow_trace("TASK-001")
    
    assert trace.verify_contract([
        "evaluate_checkpoint",
        "log_decision"
    ])
    assert trace.agent_invocations.get("review-agent", 0) >= 1
    assert "inline_checkpoint_logic" not in trace.python_calls
```

#### 5. Golden Path Tests

Record expected outcomes for key workflows, alert on deviation:

```python
# tests/golden/test_orchestrator_workflow.py

GOLDEN_ORCHESTRATOR_TRACE = {
    "stages": ["planning", "implementation", "validation", "merge"],
    "agents_used": ["player", "coach"],
    "python_functions_called": [
        "create_worktrees",
        "evaluate_checkpoint", 
        "merge_worktree"
    ],
    "human_checkpoints": ["final_merge"]
}

@pytest.mark.golden
async def test_orchestrator_follows_golden_path():
    trace = await run_orchestrator_workflow("FEAT-test")
    
    assert trace.stages == GOLDEN_ORCHESTRATOR_TRACE["stages"]
    assert set(trace.agents_used) == set(GOLDEN_ORCHESTRATOR_TRACE["agents_used"])
    
    for func in GOLDEN_ORCHESTRATOR_TRACE["python_functions_called"]:
        assert func in trace.python_calls, f"Expected {func} to be called"
```

### Testing Pyramid for Hybrid Architecture

```
                    ┌─────────────┐
                    │   Golden    │  ← Few, expensive, catch regressions
                    │    Path     │
                    └─────────────┘
                   ┌───────────────┐
                   │  Integration  │  ← Actually run commands
                   │    Smoke      │
                   └───────────────┘
                  ┌─────────────────┐
                  │    Contract     │  ← Verify agents call Python
                  │   Validation    │
                  └─────────────────┘
                 ┌───────────────────┐
                 │    Trace-Based    │  ← Log & verify what happened
                 │    Validation     │
                 └───────────────────┘
                ┌─────────────────────┐
                │     Unit Tests      │  ← Python logic (passes easily)
                │     (pytest)        │
                └─────────────────────┘
```

### When BDD IS Appropriate

BDD still has value for **pure application logic** in traditional stacks:

- FastAPI endpoints with clear request/response contracts
- React components with defined behavior
- .NET MAUI mobile app features (your MyDrive example)
- Any code where the test can directly invoke the code being tested

**BDD is NOT appropriate when:**
- LLM interpretation sits between test and code
- Agent instructions may or may not be followed
- The "wiring" between components is the failure mode
- You can't directly invoke the code path from tests

### Practical Guidance for AutoBuild Development

1. **Write Python logic with unit tests** - This will pass, it's not where bugs hide
2. **Add contract requirements to agent instructions** - Make expectations explicit
3. **Build tracing from day one** - Log what actually happens
4. **Integration smoke tests for key paths** - Actually run `/autobuild` commands
5. **Golden path tests for critical workflows** - Catch regressions in the wiring
6. **Skip BDD for Claude Code integration** - It tests the wrong layer

---

## New Capability: Adversarial Cooperation

### The Pattern (from Block AI Research)

Instead of a single agent implementing and self-validating, AutoBuild uses two cooperating agents:

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

AutoBuild supports flexible deployment from solo developer to team scale.

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
# autobuild.toml (solo dev)
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
autobuild init
```

### Small Team (Shared Cloud)

FalkorDB Cloud + shared API keys:

```toml
# autobuild.toml (team - shared)
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

  autobuild-api:  # Optional: shared API for team
    image: autobuild/server:latest
    environment:
      - FALKORDB_URL=redis://falkordb:6379
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
    ports:
      - "8080:8080"
```

```toml
# autobuild.toml (enterprise)
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
# autobuild.toml (MCP mode)
[mcp]
enabled = true
port = 3000

[mcp.tools]
# Expose AutoBuild as MCP tools
task_create = true
task_work = true
context_query = true
```

This would allow:
- Using AutoBuild's knowledge graph from Claude Code
- Hybrid workflow: Claude Code for interaction, AutoBuild for context
- Best of both worlds: slash commands + knowledge graph

---

## Authentication & Security

### Security Considerations

AutoBuild handles sensitive data:
- **Source code patterns** - Proprietary architectural decisions
- **API keys** - LLM provider credentials
- **Knowledge graph** - Accumulated project intelligence
- **Task history** - Implementation details, decisions

### Authentication Tiers

| Deployment | Auth Required | Method |
|------------|---------------|--------|
| Solo (Local) | Optional | None or local keyring |
| Team (Cloud) | Required | API keys + RBAC |
| Enterprise | Required | SSO/OIDC + RBAC + Audit |

### Solo Developer (Local)

Minimal auth - rely on filesystem permissions:

```toml
# autobuild.toml (solo)
[security]
mode = "local"

[security.secrets]
# Use system keyring for API keys
provider = "keyring"  # macOS Keychain, Windows Credential Manager, Linux Secret Service
```

```bash
# Store API keys securely
autobuild config set-secret ANTHROPIC_API_KEY "sk-..."
autobuild config set-secret MISTRAL_API_KEY "..."

# Keys retrieved from system keyring, never stored in plaintext
```

### Team (Cloud) - API Key + RBAC

```toml
# autobuild.toml (team)
[security]
mode = "team"

[security.auth]
provider = "api_key"
# Each team member gets unique API key
# Keys managed via autobuild admin CLI or web UI

[security.rbac]
enabled = true
default_role = "developer"

[security.rbac.roles]
admin = ["*"]  # Full access
developer = ["task.*", "feature.*", "context.show"]
viewer = ["task.status", "feature.status", "context.show"]
```

```bash
# Admin creates team keys
autobuild admin create-key --user "alice@company.com" --role developer
# Output: ab_key_a1b2c3d4e5f6...

# Team member configures
export AUTOBUILD_API_KEY="ab_key_a1b2c3d4e5f6..."
autobuild task create "Add feature X"
```

### Enterprise - SSO/OIDC + Full Audit

```toml
# autobuild.toml (enterprise)
[security]
mode = "enterprise"

[security.auth]
provider = "oidc"
issuer = "https://auth.company.com"
client_id = "autobuild-prod"
client_secret_env = "OIDC_CLIENT_SECRET"
scopes = ["openid", "profile", "email", "groups"]

[security.rbac]
enabled = true
# Map OIDC groups to roles
group_mapping = {
    "engineering-leads" = "admin",
    "engineers" = "developer",
    "contractors" = "developer",
    "stakeholders" = "viewer"
}

[security.audit]
enabled = true
destination = "s3://company-logs/autobuild/"
# Or: destination = "https://splunk.company.com/autobuild"
events = ["auth", "task.*", "context.query", "admin.*"]
```

### Knowledge Graph Security

```toml
# autobuild.toml
[graph.security]
# Encrypt sensitive nodes
encryption = true
encryption_key_env = "AUTOBUILD_GRAPH_KEY"

# Redact patterns in logs
redact_patterns = [
    "api_key",
    "password",
    "secret",
    "token"
]

# Access control on graph queries
acl_enabled = true  # Enterprise only
```

**Graph-level access control (Enterprise):**

```python
# Example: Restrict context queries by project/team
class SecureContextSelector(ContextSelector):
    def get_context(self, job_type: str, user: User, **kwargs) -> JobContext:
        # Filter graph queries by user's project access
        allowed_projects = user.get_allowed_projects()
        
        return self.graph.query("""
            MATCH (t:Task {id: $task_id})-[:BELONGS_TO]->(p:Project)
            WHERE p.id IN $allowed_projects
            ...
        """, task_id=kwargs["task_id"], allowed_projects=allowed_projects)
```

### Secrets Management

| Secret Type | Solo | Team | Enterprise |
|-------------|------|------|------------|
| LLM API keys | System keyring | Vault/env | HashiCorp Vault |
| Graph connection | Local config | Env vars | Secrets manager |
| Encryption keys | Keyring | KMS | AWS KMS / Azure Key Vault |

```toml
# Enterprise secrets management
[security.secrets]
provider = "vault"  # HashiCorp Vault
vault_addr = "https://vault.company.com"
vault_path = "secret/autobuild"
# Or: provider = "aws_secrets_manager"
# Or: provider = "azure_keyvault"
```

### Network Security (Team/Enterprise)

```toml
[security.network]
# TLS for all connections
tls_enabled = true
tls_cert_file = "/etc/autobuild/cert.pem"
tls_key_file = "/etc/autobuild/key.pem"

# Restrict allowed origins (for MCP server mode)
cors_origins = ["https://claude.ai", "https://cursor.com"]

# Rate limiting
rate_limit_enabled = true
rate_limit_requests = 100
rate_limit_window = "1m"
```

### Security Checklist by Deployment

**Solo (Local):**
- [ ] Use system keyring for API keys (not plaintext in config)
- [ ] Keep `.autobuild/` in `.gitignore`
- [ ] Don't commit `autobuild.toml` with secrets

**Team (Cloud):**
- [ ] Unique API keys per team member
- [ ] RBAC roles configured
- [ ] TLS enabled for FalkorDB connection
- [ ] Regular key rotation

**Enterprise:**
- [ ] SSO/OIDC integration
- [ ] Audit logging enabled
- [ ] Graph encryption at rest
- [ ] Secrets in Vault/KMS
- [ ] Network policies (firewall, VPC)
- [ ] Regular security reviews

---

## Knowledge Graph MCP Architecture

### The Insight: Shared Brain for Multiple Consumers

By extracting the knowledge graph into a **standalone MCP server**, it becomes a shared resource that can serve:
- **Claude Code** (markdown-based slash commands)
- **AutoBuild** (LangGraph agentic workflows)
- **Other tools** (Cursor, Codex CLI, any MCP-compatible client)

This **enhances** GuardKit's existing file structure (agents, rules, commands) with a **queryable metadata layer** that enables intelligent agent selection, learning, and cross-project patterns.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Knowledge Graph MCP                          │
│                   (Standalone Server)                           │
│                                                                 │
│  Storage: FalkorDB (graph) + SQLite (metadata)                 │
│  Deployment: Local Docker | Cloud | Sidecar                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Tools (MCP Interface):                                         │
│  ├── context_query(job_type, task_id) → job-specific context   │
│  ├── agent_get(name, stack) → agent config + instructions      │
│  ├── agent_search(stack, phase, patterns) → matching agents    │
│  ├── pattern_search(query) → relevant patterns                 │
│  ├── rule_get(stack, phase) → applicable rules                 │
│  ├── decision_log(task_id, decision, rationale) → store        │
│  ├── project_analyze(path) → populate graph from codebase      │
│  └── template_get(name) → template definition                  │
│                                                                 │
│  Resources (MCP Interface):                                     │
│  ├── project://structure → project file tree                   │
│  ├── agents://list → available agents                          │
│  └── patterns://stack/{stack} → patterns for stack             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                    │
                    │ MCP Protocol (stdio or HTTP/SSE)
                    │
        ┌───────────┴───────────┬───────────────────┐
        │                       │                   │
        ▼                       ▼                   ▼
┌───────────────┐      ┌───────────────┐   ┌───────────────┐
│  Claude Code  │      │   AutoBuild   │   │  Other Tools  │
│  (Markdown)   │      │  (LangGraph)  │   │ (Cursor, etc) │
│               │      │               │   │               │
│ /task-work    │      │ Nodes query   │   │ MCP client    │
│ calls MCP     │      │ MCP for ctx   │   │               │
└───────────────┘      └───────────────┘   └───────────────┘
```

### Benefits of MCP Extraction

| Benefit | Description |
|---------|-------------|
| **Single source of truth** | One knowledge graph, multiple consumers |
| **Gradual migration** | Start with Claude Code + MCP, migrate to AutoBuild later |
| **Tool agnostic** | Works with any MCP-compatible AI tool |
| **Dynamic context** | Replaces static markdown with queryable intelligence |
| **Learning persists** | Decisions learned in Claude Code available in AutoBuild |
| **Separation of concerns** | Graph logic independent of workflow orchestration |

### MCP Server Implementation

```python
# knowledge_graph_mcp/server.py
from mcp.server import Server
from mcp.types import Tool, Resource

class KnowledgeGraphMCP:
    """MCP server exposing knowledge graph capabilities."""
    
    def __init__(self, graph_client: FalkorDBClient):
        self.graph = graph_client
        self.server = Server("knowledge-graph")
        self._register_tools()
        self._register_resources()
    
    def _register_tools(self):
        @self.server.tool()
        async def context_query(
            job_type: str,
            task_id: str | None = None,
            stack: str | None = None,
            max_tokens: int = 2000
        ) -> str:
            """Get job-specific context for current task."""
            return await self._get_context_for_job(job_type, task_id, stack, max_tokens)
        
        @self.server.tool()
        async def agent_get(name: str) -> dict:
            """Get agent configuration and instructions."""
            return await self._get_agent(name)
        
        @self.server.tool()
        async def agent_search(
            stack: str,
            phase: str | None = None,
            file_patterns: list[str] | None = None,
            keywords: list[str] | None = None
        ) -> list[dict]:
            """Find agents matching criteria."""
            return await self._search_agents(stack, phase, file_patterns, keywords)
        
        @self.server.tool()
        async def decision_log(
            task_id: str,
            decision_type: str,
            decision: str,
            rationale: str
        ) -> dict:
            """Log a decision for future reference."""
            return await self._log_decision(task_id, decision_type, decision, rationale)
        
        @self.server.tool()
        async def project_analyze(path: str) -> dict:
            """Analyze codebase and populate knowledge graph."""
            return await self._analyze_project(path)
```

### Claude Code Integration

```json
// .claude/mcp.json (in user's project)
{
  "mcpServers": {
    "knowledge-graph": {
      "command": "knowledge-graph-mcp",
      "args": ["--db", ".autobuild/graph.db"],
      "env": {
        "FALKORDB_URL": "redis://localhost:6379"
      }
    }
  }
}
```

```markdown
# .claude/commands/task-work.md (updated to use MCP)

## Phase 2: Implementation Planning

Before planning, retrieve context from knowledge graph:

<mcp:knowledge-graph>
tool: context_query
args:
  job_type: "planning"
  task_id: "$TASK_ID"
  stack: "$DETECTED_STACK"
</mcp:knowledge-graph>

Use the returned context to inform your implementation plan.

## Phase 3: Implementation

Select appropriate sub-agent:

<mcp:knowledge-graph>
tool: agent_search
args:
  stack: "$DETECTED_STACK"
  phase: "implementation"
  file_patterns: $AFFECTED_FILES
</mcp:knowledge-graph>

Use the agent's instructions and model preference.
```

### AutoBuild Integration

```python
# src/autobuild/context/mcp_client.py
from mcp import ClientSession

class KnowledgeGraphClient:
    """AutoBuild's interface to Knowledge Graph MCP."""
    
    def __init__(self, mcp_session: ClientSession):
        self.session = mcp_session
    
    async def get_context(self, job_type: str, task_id: str) -> str:
        """Get job-specific context."""
        result = await self.session.call_tool(
            "context_query",
            {"job_type": job_type, "task_id": task_id}
        )
        return result.content
    
    async def get_agent(self, name: str) -> AgentConfig:
        """Get agent configuration."""
        result = await self.session.call_tool("agent_get", {"name": name})
        return AgentConfig(**result.content)
    
    async def search_agents(
        self, 
        stack: str, 
        phase: str,
        file_patterns: list[str]
    ) -> list[AgentConfig]:
        """Find matching agents for task."""
        result = await self.session.call_tool(
            "agent_search",
            {"stack": stack, "phase": phase, "file_patterns": file_patterns}
        )
        return [AgentConfig(**a) for a in result.content]
```

---

## Sub-Agent Architecture

### Current GuardKit Approach

GuardKit uses sub-agents with different models for cost/performance optimization:

```markdown
# .claude/agents/react-component-specialist.md
---
name: react-component-specialist
model: haiku           # Cheaper for implementation
stack: react-typescript
phase: implementation
triggers:
  - "*.tsx"
  - "components/**"
collaborates_with:
  - react-testing-specialist
---

## Instructions
You are a React component specialist...
```

```markdown
# .claude/agents/software-architect.md
---
name: software-architect
model: sonnet          # More expensive, better reasoning
stack: "*"             # All stacks
phase: planning
triggers:
  - complexity >= 7
  - architectural_decision
---

## Instructions
You evaluate architectural decisions using SOLID, DRY, YAGNI...
```

### Knowledge Graph Storage: Hybrid Approach

**Store metadata in graph, instructions in files:**

```cypher
// Agent node in knowledge graph
CREATE (:Agent {
    name: "react-component-specialist",
    model: "haiku",
    model_override_allowed: true,
    stack: "react-typescript",
    phase: "implementation",
    triggers: ["*.tsx", "components/**"],
    instruction_file: "agents/stack/react-component.md",
    tools: ["read_file", "write_file", "run_tests"],
    collaborates_with: ["react-testing-specialist"],
    avg_tokens_per_task: 15000,
    success_rate: 0.94
})

// Relationships
MATCH (a:Agent {name: "react-component-specialist"})
MATCH (s:Stack {name: "react-typescript"})
CREATE (a)-[:SPECIALIZES_IN]->(s)

// Track which agents work well together
MATCH (a1:Agent {name: "react-component-specialist"})
MATCH (a2:Agent {name: "react-testing-specialist"})
CREATE (a1)-[:COLLABORATES_WITH {success_rate: 0.96}]->(a2)
```

**Why hybrid?**
- Graph stores **queryable metadata** (model, triggers, relationships)
- Files store **lengthy instructions** (don't bloat graph)
- Files are **version controlled** and **IDE-editable**
- Graph enables **intelligent routing** based on patterns

### Model Selection by Role/Phase

```toml
# autobuild.toml

[agents.model_defaults]
# Default model per phase (can be overridden by agent definition)
planning = "sonnet"           # Better reasoning for architecture
implementation = "haiku"      # Cost-efficient for coding
testing = "haiku"             # Cost-efficient for test generation
review = "sonnet"             # Better for code review
coach = "sonnet"              # Needs strong validation reasoning
player = "haiku"              # Implementation-focused, volume work

[agents.model_overrides]
# Specific agents can override defaults
software-architect = "opus"   # Critical decisions need best model
security-reviewer = "sonnet"  # Security needs careful analysis
```

### Sub-Agent Routing in LangGraph

```python
# src/autobuild/agents/router.py
from dataclasses import dataclass
from typing import Literal

@dataclass
class AgentConfig:
    name: str
    model: str
    instructions: str
    tools: list[str]
    
class SubAgentRouter:
    """Routes to appropriate sub-agent based on task context."""
    
    def __init__(self, kg_client: KnowledgeGraphClient):
        self.kg = kg_client
    
    async def select_agent(
        self, 
        task: Task, 
        phase: Literal["planning", "implementation", "testing", "review"]
    ) -> AgentConfig:
        """Select best agent for current task and phase."""
        
        # Query knowledge graph for matching agents
        candidates = await self.kg.search_agents(
            stack=task.stack,
            phase=phase,
            file_patterns=task.affected_files,
            keywords=task.keywords
        )
        
        if not candidates:
            return await self._get_default_agent(phase)
        
        # Score candidates based on:
        # - Trigger match strength
        # - Historical success rate
        # - Collaboration compatibility (if other agents involved)
        best = self._score_and_select(candidates, task)
        
        # Load full instructions
        instructions = await self.kg.get_agent_instructions(best.name)
        
        return AgentConfig(
            name=best.name,
            model=best.model,
            instructions=instructions,
            tools=best.tools
        )
    
    def _score_and_select(
        self, 
        candidates: list[AgentConfig], 
        task: Task
    ) -> AgentConfig:
        """Score candidates and return best match."""
        scored = []
        for agent in candidates:
            score = 0
            
            # Trigger match score
            for trigger in agent.triggers:
                if self._trigger_matches(trigger, task):
                    score += 10
            
            # Historical success rate
            score += agent.success_rate * 20
            
            # Prefer specialists over generalists
            if agent.stack != "*":
                score += 5
            
            scored.append((score, agent))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]
```

### LangGraph Node with Sub-Agent Selection

```python
# src/autobuild/graph/nodes.py

async def implementation_node(state: AutoBuildState) -> dict:
    """Implementation phase with dynamic sub-agent selection."""
    
    # Get knowledge graph client
    kg = get_knowledge_graph_client()
    router = SubAgentRouter(kg)
    
    # Select appropriate agent for this task
    agent_config = await router.select_agent(
        task=state["task"],
        phase="implementation"
    )
    
    # Get LLM with agent's preferred model
    llm = get_llm(model=agent_config.model)  # e.g., "haiku"
    
    # Get job-specific context from knowledge graph
    context = await kg.get_context(
        job_type="player_implementation",
        task_id=state["task_id"]
    )
    
    # Build prompt with agent instructions + context
    prompt = f"""
{agent_config.instructions}

## Project Context
{context}

## Task
{state['task']['description']}

## Requirements
{state['requirements']}

## Previous Feedback
{state.get('coach_feedback', 'First turn - no feedback yet')}
"""
    
    # Execute with agent's tools
    result = await llm.invoke(
        prompt, 
        tools=get_tools(agent_config.tools)
    )
    
    # Log decision for learning
    await kg.decision_log(
        task_id=state["task_id"],
        decision_type="agent_selection",
        decision=agent_config.name,
        rationale=f"Selected for {state['task']['stack']} implementation"
    )
    
    return {
        "player_output": result,
        "selected_agent": agent_config.name,
        "loop_status": "reviewing"
    }
```

### Coach with Different Model

```python
async def coach_node(state: AutoBuildState) -> dict:
    """Coach validation - uses stronger model for reasoning."""
    
    kg = get_knowledge_graph_client()
    router = SubAgentRouter(kg)
    
    # Coach typically uses stronger model (sonnet vs haiku)
    agent_config = await router.select_agent(
        task=state["task"],
        phase="review"  # Coach uses review-phase agents
    )
    
    # Likely returns sonnet-based agent
    llm = get_llm(model=agent_config.model)  # e.g., "sonnet"
    
    # Coach-specific context (requirements-focused)
    context = await kg.get_context(
        job_type="coach_validation",
        task_id=state["task_id"]
    )
    
    prompt = f"""
{agent_config.instructions}

## Requirements (Your Validation Criteria)
{state['requirements']}

## Implementation to Validate
{state['player_output']}

## Your Task
Validate against EVERY requirement. Do NOT trust self-reported success.
Run tests. Check edge cases. Be rigorous.

Respond with:
- APPROVED: All requirements verified
- FEEDBACK: Specific issues (be actionable)
"""
    
    result = await llm.invoke(prompt)
    approved = "APPROVED" in result.upper()
    
    return {
        "coach_feedback": result,
        "coach_approved": approved,
        "turn_number": state["turn_number"] + 1,
        "loop_status": "approved" if approved else "implementing"
    }
```

### Cost Optimization Example

```
Task: "Add user avatar upload component"
Stack: react-typescript

Phase          Agent Selected              Model    Cost/1M tokens
─────────────────────────────────────────────────────────────────
Planning       software-architect          sonnet   $3/$15
Arch Review    software-architect          sonnet   $3/$15
Implementation react-component-specialist  haiku    $0.25/$1.25
Testing        react-testing-specialist    haiku    $0.25/$1.25
Coach Turn 1   code-reviewer               sonnet   $3/$15
Player Turn 2  react-component-specialist  haiku    $0.25/$1.25
Coach Turn 2   code-reviewer               sonnet   $3/$15
Final Review   code-reviewer               sonnet   $3/$15

Estimated cost: ~$0.15 per task (vs ~$0.50 if all sonnet)
Savings: 70% while maintaining quality where it matters
```

### Agent Learning (Future Enhancement)

The knowledge graph enables agent learning over time:

```cypher
// Track agent performance
MATCH (a:Agent {name: "react-component-specialist"})
MATCH (t:Task {id: "TASK-a3f8"})
CREATE (a)-[:WORKED_ON {
    success: true,
    turns_needed: 2,
    tokens_used: 12500,
    timestamp: datetime()
}]->(t)

// Query for agent effectiveness
MATCH (a:Agent)-[w:WORKED_ON]->(t:Task)
WHERE a.stack = "react-typescript"
RETURN a.name, 
       avg(w.turns_needed) as avg_turns,
       count(CASE WHEN w.success THEN 1 END) * 100.0 / count(*) as success_rate
ORDER BY success_rate DESC
```

This allows AutoBuild to:
- Recommend better agents based on historical performance
- Identify agents that need instruction improvements
- Optimize model selection based on actual cost/quality tradeoffs

---

## Knowledge Graph Context Layer

### The Key Insight: Job-Specific Context Assembly

GuardKit already uses progressive disclosure (core/ext splits, frontmatter triggers) to manage context. But there's a fundamental limitation: **context is selected at load time, not at job time**.

As Kris Wong (ClosedLoop) notes about their 59-agent system:

> "Just giving the LLM all the context for everything in every prompt isn't super effective in my experience. We are focused on optimizing context for specific jobs at specific moments."

### What "Job-Specific Context" Actually Means

In GuardKit (current state):
- You run `/task-work TASK-001`
- Claude Code loads the task file + relevant agents based on frontmatter triggers
- The **same context** is used for the entire task (planning → implementing → testing → reviewing)

In AutoBuild (with Knowledge Graph):
- The orchestrator runs a task through multiple **job types**
- **Each job type gets different context** assembled from the knowledge graph
- Context is assembled **at the moment the job runs**, not at task start

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TASK EXECUTION: Context Per Job                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  GuardKit (Current)                                                         │
│  ─────────────────                                                          │
│  /task-work TASK-001                                                        │
│       │                                                                     │
│       └── Load task + triggered agents (5-8k tokens)                        │
│           └── Plan (same context)                                           │
│           └── Implement (same context)                                      │
│           └── Test (same context)                                           │
│           └── Review (same context)                                         │
│                                                                             │
│  AutoBuild (Job-Specific)                                                   │
│  ─────────────────────────                                                  │
│  autobuild task TASK-001                                                    │
│       │                                                                     │
│       ├── Player Job 1: Implement                                           │
│       │   └── Graph query: requirements + implementation patterns (~1.5k)   │
│       │                                                                     │
│       ├── Coach Job 1: Validate                                             │
│       │   └── Graph query: requirements + modified files + tests (~1.2k)    │
│       │                                                                     │
│       ├── Player Job 2: Address feedback                                    │
│       │   └── Graph query: feedback + specific failing patterns (~1.0k)     │
│       │                                                                     │
│       └── Coach Job 2: Final validation                                     │
│           └── Graph query: all requirements + full test results (~1.5k)     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why This Matters

| Aspect | GuardKit (Load-Time Context) | AutoBuild (Job-Time Context) |
|--------|----------------------------|------------------------------|
| **When context is assembled** | Once, at task start | Each job within task |
| **What's included** | All potentially relevant agents/rules | Only what THIS job needs |
| **Token usage per job** | 5-8k (full context) | 1-2k (job-specific) |
| **Context freshness** | Static for task duration | Fresh each job (includes results from previous jobs) |
| **Feedback incorporation** | Manual (re-run with edits) | Automatic (coach feedback → player context) |
| **Learning** | None | Graph stores what worked |

### Concrete Example: Implementing a React Component

**GuardKit Context (loaded once):**
```markdown
# Task Context (~6000 tokens)
- Task: Add UserAvatar component
- EARS specification
- Gherkin scenarios
- react-component-specialist.md (full file)
- react-testing-specialist.md (full file)  
- implementation.md rules
- testing.md rules
- Project patterns
```

**AutoBuild Context (per job):**

```python
# Job 1: Player Implementation (~1500 tokens)
{
    "requirements": ["Display user avatar with fallback initials", ...],
    "patterns": ["Component pattern from UserCard.tsx", "Avatar sizing from Theme.tsx"],
    "implementation_rules": ["Use TypeScript strict mode", "Export named components"],
    "relevant_files": ["src/components/UserCard.tsx", "src/theme/index.ts"]
}

# Job 2: Coach Validation (~1200 tokens)  
{
    "requirements": ["Display user avatar with fallback initials", ...],
    "modified_files": ["src/components/UserAvatar.tsx", "src/components/UserAvatar.test.tsx"],
    "test_results": {"passing": 5, "failing": 1, "error": "Fallback initials not rendered"},
    "validation_rules": ["All acceptance criteria must have tests", "No TypeScript errors"]
}

# Job 3: Player Fix (~1000 tokens)
{
    "coach_feedback": "Fallback initials not rendering when image fails to load",
    "failing_test": "should show initials when image src is invalid",
    "relevant_pattern": "Error boundary pattern from ImageLoader.tsx",
    "specific_fix_guidance": ["Add onError handler", "Track loading state"]
}
```

### AutoBuild's Enhancement: Queryable Metadata Layer

AutoBuild adds a **knowledge graph** on top of GuardKit's file structure to enable:
1. **Queryable agent selection** - Find agents by triggers, success rate, stack
2. **Learning over time** - Track which agents work well for which tasks
3. **Cross-project patterns** - Decisions learned in one project available in others
4. **Dynamic context assembly** - Combine relevant agents/rules/patterns per-job

**Key principle:** Files remain the source of truth. The graph indexes and enhances them.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AutoBuild Context Layer                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │  Knowledge Graph │     │  Job Context    │                   │
│  │  (Graphiti +    │────►│  Selector       │                   │
│  │   FalkorDB)     │     │                 │                   │
│  └─────────────────┘     └────────┬────────┘                   │
│                                   │                             │
│  Stores:                          │ Provides:                   │
│  • Project structure              │ • Phase-specific context    │
│  • Architectural patterns         │ • Agent-specific context    │
│  • Stack/framework info           │ • Task-specific context     │
│  • Previous decisions             │                             │
│  • Template patterns              │                             │
│  • Agent definitions              │                             │
│  • Rule sets                      │                             │
│                                   ▼                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Current Job Context                      ││
│  │  (Only what's needed for THIS phase/task/agent)            ││
│  │  Target: <2000 tokens per job context                      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Knowledge Graph Schema

Using **Graphiti + FalkorDB**:

```python
# Entity types
entities = {
    "Project": {
        "properties": ["name", "path", "created_at", "description"]
    },
    "Stack": {
        "properties": ["name", "version", "framework", "language"]
    },
    "Pattern": {
        "properties": ["name", "type", "description", "example"]
    },
    "Agent": {
        "properties": ["name", "specialization", "instructions", "tools"]
    },
    "Template": {
        "properties": ["name", "stack", "structure", "patterns"]
    },
    "Rule": {
        "properties": ["name", "category", "condition", "action"]
    },
    "File": {
        "properties": ["path", "type", "purpose", "last_modified"]
    },
    "Task": {
        "properties": ["id", "description", "status", "complexity"]
    },
    "Decision": {
        "properties": ["type", "rationale", "timestamp", "outcome"]
    },
    "Requirement": {
        "properties": ["id", "description", "type", "priority"]
    }
}

# Relationships
relationships = [
    ("Project", "USES_STACK", "Stack"),
    ("Stack", "HAS_PATTERN", "Pattern"),
    ("Pattern", "IMPLEMENTED_IN", "File"),
    ("Agent", "SPECIALIZES_IN", "Stack"),
    ("Agent", "FOLLOWS", "Rule"),
    ("Template", "DEFINES", "Pattern"),
    ("Template", "FOR_STACK", "Stack"),
    ("Task", "MODIFIES", "File"),
    ("Task", "REQUIRES", "Pattern"),
    ("Task", "HAS_REQUIREMENT", "Requirement"),
    ("Decision", "AFFECTS", "Pattern"),
    ("Decision", "MADE_FOR", "Task"),
    ("Rule", "APPLIES_TO", "Stack"),
    ("Rule", "ENFORCES", "Pattern"),
]
```

### Job-Specific Context Retrieval

```python
class ContextSelector:
    """Retrieves only relevant context for current job."""
    
    def __init__(self, graph: GraphitiClient):
        self.graph = graph
    
    def get_context(self, job_type: str, **kwargs) -> JobContext:
        """Route to appropriate context retrieval method."""
        retrievers = {
            "player_implementation": self._player_context,
            "coach_validation": self._coach_context,
            "architectural_review": self._architecture_context,
            "agent_discovery": self._agent_context,
            "template_generation": self._template_context,
        }
        return retrievers[job_type](**kwargs)
    
    def _player_context(self, task_id: str) -> JobContext:
        """Context for player agent during implementation."""
        return self.graph.query("""
            MATCH (t:Task {id: $task_id})-[:HAS_REQUIREMENT]->(r:Requirement)
            MATCH (t)-[:REQUIRES]->(p:Pattern)-[:IMPLEMENTED_IN]->(f:File)
            MATCH (proj:Project)-[:USES_STACK]->(s:Stack)
            MATCH (rule:Rule)-[:APPLIES_TO]->(s)
            WHERE rule.category = 'implementation'
            RETURN r.description AS requirements,
                   collect(DISTINCT p.description) AS patterns,
                   collect(DISTINCT f.path) AS relevant_files,
                   collect(DISTINCT rule.action) AS rules
            LIMIT 5
        """, task_id=task_id)
    
    def _coach_context(self, task_id: str) -> JobContext:
        """Context for coach agent during validation."""
        return self.graph.query("""
            MATCH (t:Task {id: $task_id})-[:HAS_REQUIREMENT]->(r:Requirement)
            MATCH (t)-[:MODIFIES]->(f:File)
            OPTIONAL MATCH (t)-[:HAS_TEST]->(test:Test)
            RETURN r.description AS requirements,
                   collect(DISTINCT f.path) AS modified_files,
                   collect(DISTINCT test.status) AS test_results
        """, task_id=task_id)
    
    def _architecture_context(self, task_id: str) -> JobContext:
        """Context for architectural review phase."""
        return self.graph.query("""
            MATCH (proj:Project)-[:USES_STACK]->(s:Stack)
            MATCH (s)-[:HAS_PATTERN]->(p:Pattern)
            MATCH (rule:Rule)-[:ENFORCES]->(p)
            WHERE rule.category IN ['solid', 'dry', 'yagni']
            RETURN s.name AS stack,
                   collect(DISTINCT p.name) AS established_patterns,
                   collect(DISTINCT rule.description) AS architecture_rules
        """)
    
    def _agent_context(self, stack: str) -> JobContext:
        """Context for agent discovery/enhancement."""
        return self.graph.query("""
            MATCH (s:Stack {name: $stack})
            MATCH (a:Agent)-[:SPECIALIZES_IN]->(s)
            MATCH (p:Pattern)<-[:HAS_PATTERN]-(s)
            RETURN collect(DISTINCT a.name) AS existing_agents,
                   collect(DISTINCT p.name) AS stack_patterns
        """, stack=stack)
    
    def _template_context(self) -> JobContext:
        """Context for template generation."""
        return self.graph.query("""
            MATCH (proj:Project)-[:USES_STACK]->(s:Stack)
            MATCH (s)-[:HAS_PATTERN]->(p:Pattern)-[:IMPLEMENTED_IN]->(f:File)
            RETURN s.name AS stack,
                   collect(DISTINCT {
                       pattern: p.name,
                       files: collect(f.path)
                   }) AS pattern_files
        """)
```

### Context by Job Type

| Job/Phase | Context Retrieved | Token Target |
|-----------|-------------------|--------------|
| Player (implementing) | Requirements, coach feedback, relevant patterns, implementation rules | <2000 |
| Coach (validating) | Requirements, modified files, test results | <1500 |
| Architectural Review | Stack patterns, SOLID/DRY/YAGNI rules | <1500 |
| Complexity Evaluation | Task description, similar past tasks, complexity factors | <1000 |
| Agent Discovery | Stack info, existing agents, patterns | <1500 |
| Template Generation | Project structure, patterns, file organization | <2000 |

### Graph Population (During `autobuild init`)

```python
async def populate_knowledge_graph(project_path: str, graph: GraphitiClient):
    """Analyze project and populate knowledge graph."""
    
    # 1. Create project node
    project = await analyze_project_metadata(project_path)
    await graph.add_entity("Project", project)
    
    # 2. Detect and add stack
    stack = await detect_stack(project_path)
    await graph.add_entity("Stack", stack)
    await graph.add_relationship(project.id, "USES_STACK", stack.id)
    
    # 3. Discover patterns
    patterns = await discover_patterns(project_path, stack)
    for pattern in patterns:
        await graph.add_entity("Pattern", pattern)
        await graph.add_relationship(stack.id, "HAS_PATTERN", pattern.id)
    
    # 4. Index important files
    files = await index_key_files(project_path, patterns)
    for file in files:
        await graph.add_entity("File", file)
        # Link to patterns
        for pattern_id in file.implements_patterns:
            await graph.add_relationship(pattern_id, "IMPLEMENTED_IN", file.id)
    
    # 5. Load default rules for stack
    rules = await load_stack_rules(stack.name)
    for rule in rules:
        await graph.add_entity("Rule", rule)
        await graph.add_relationship(rule.id, "APPLIES_TO", stack.id)
    
    # 6. Discover/create agents
    agents = await discover_agents(stack, patterns)
    for agent in agents:
        await graph.add_entity("Agent", agent)
        await graph.add_relationship(agent.id, "SPECIALIZES_IN", stack.id)
```

### Benefits of Job-Time Context Assembly

| Aspect | Load-Time Context (GuardKit) | Job-Time Context (AutoBuild) |
|--------|----------------------------|------------------------------|
| Token usage | 5k-8k per task | 1-2k per job |
| Relevance | Good (progressive disclosure) | Excellent (job-specific queries) |
| Learning | None | Decisions and outcomes stored |
| Scalability | Good for single tasks | Better for multi-turn workflows |
| Feedback loop | Manual re-run needed | Automatic context update between jobs |
| Cross-project | Copy files manually | Shared graph patterns |

---

## Multi-Model Support

### The Claude Code Subscription Problem

**Important Limitation:** Claude Code subscription ($200/mo Claude Max) provides access to the *interactive Claude Code tool*, but **does NOT provide API access** for programmatic use.

| What You Get | Claude Max ($200/mo) | Anthropic API |
|--------------|---------------------|---------------|
| Claude Code CLI | ✅ Unlimited | ❌ Not included |
| API calls from code | ❌ Not included | ✅ Pay per token |
| AutoBuild integration | ❌ Cannot use | ✅ Works |

**This is a key value proposition of AutoBuild:** Break free from the $200/mo subscription by using:
- Anthropic API (pay per use, often cheaper for moderate usage)
- Devstral 2 (7x cheaper than Claude)
- Local models ($0)
- AWS Bedrock, OpenRouter, etc.

### Supported LLM Providers

| Provider | Models | Use Case | Pricing |
|----------|--------|----------|---------|
| **Anthropic API** | Claude Sonnet 4, Opus 4 | High quality, direct | $3/$15 per M tokens |
| **Mistral** | Devstral 2 (123B), Small (24B) | Cost-efficient, coding | $0.40/$2.00 (FREE preview) |
| **AWS Bedrock** | Claude, Llama, Mistral | Enterprise, existing AWS | AWS pricing + markup |
| **Azure OpenAI** | GPT-4, GPT-4o | Enterprise, existing Azure | Azure pricing |
| **OpenAI** | GPT-4o, o1 | Alternative to Claude | $2.50/$10 per M tokens |
| **OpenRouter** | Any model | Aggregator, fallbacks | Varies by model |
| **DeepSeek** | DeepSeek R1, Coder | Open weights, cheap | ~$0.14/$0.28 per M |
| **Local (Ollama)** | Devstral Small, Codestral, Qwen | Offline, free | $0 (hardware only) |
| **Local (vLLM)** | Any supported model | High performance local | $0 (hardware only) |

### LLM Configuration

```toml
# autobuild.toml

[models]
# Default model for all roles
default = "devstral-2"

# Override per role (optional)
player = "devstral-2"      # Implementation - cost-efficient
coach = "claude-sonnet"    # Validation - stronger reasoning
architect = "claude-sonnet" # Architectural review

# Fallback chain (if primary fails)
fallback_chain = ["devstral-2", "deepseek", "local"]

#=============================================================================
# ANTHROPIC (Direct API - NOT Claude Code subscription)
#=============================================================================
[models.claude-sonnet]
provider = "anthropic"
model = "claude-sonnet-4-20250514"
api_key_env = "ANTHROPIC_API_KEY"
max_tokens = 8192

[models.claude-opus]
provider = "anthropic"
model = "claude-opus-4-20250514"
api_key_env = "ANTHROPIC_API_KEY"
max_tokens = 8192
# Use for complex architectural decisions only (expensive)

#=============================================================================
# MISTRAL (Devstral - Recommended for cost efficiency)
#=============================================================================
[models.devstral-2]
provider = "mistral"
model = "devstral-2"
api_key_env = "MISTRAL_API_KEY"
max_tokens = 32768
# Currently FREE during preview, then $0.40/$2.00 per M

[models.devstral-small]
provider = "mistral"
model = "devstral-small-2"
api_key_env = "MISTRAL_API_KEY"
# 24B model - can also run locally

#=============================================================================
# AWS BEDROCK (Enterprise - uses existing AWS credentials)
#=============================================================================
[models.bedrock-claude]
provider = "bedrock"
model = "anthropic.claude-sonnet-4-20250514-v1:0"
region = "us-east-1"
# Uses AWS credentials from environment/IAM role
# aws_profile = "production"  # Optional: specific profile

[models.bedrock-llama]
provider = "bedrock"
model = "meta.llama3-70b-instruct-v1:0"
region = "us-east-1"

[models.bedrock-mistral]
provider = "bedrock"
model = "mistral.mistral-large-2407-v1:0"
region = "us-east-1"

#=============================================================================
# AZURE OPENAI (Enterprise - uses existing Azure credentials)
#=============================================================================
[models.azure-gpt4]
provider = "azure"
model = "gpt-4o"
api_key_env = "AZURE_OPENAI_API_KEY"
endpoint = "https://your-resource.openai.azure.com"
api_version = "2024-02-15-preview"
deployment = "gpt-4o-deployment"

#=============================================================================
# OPENAI (Direct)
#=============================================================================
[models.openai-gpt4]
provider = "openai"
model = "gpt-4o"
api_key_env = "OPENAI_API_KEY"
max_tokens = 4096

[models.openai-o1]
provider = "openai"
model = "o1-preview"
api_key_env = "OPENAI_API_KEY"
# Reasoning model - good for complex problems

#=============================================================================
# OPENROUTER (Aggregator - access any model)
#=============================================================================
[models.openrouter-claude]
provider = "openrouter"
model = "anthropic/claude-sonnet-4"
api_key_env = "OPENROUTER_API_KEY"
# Useful for: fallbacks, trying different models, unified billing

[models.openrouter-devstral]
provider = "openrouter"
model = "mistralai/devstral-2"
api_key_env = "OPENROUTER_API_KEY"

#=============================================================================
# DEEPSEEK (Open weights, very cheap)
#=============================================================================
[models.deepseek]
provider = "deepseek"
model = "deepseek-coder"
api_key_env = "DEEPSEEK_API_KEY"
endpoint = "https://api.deepseek.com"
max_tokens = 8192

[models.deepseek-r1]
provider = "deepseek"
model = "deepseek-reasoner"
api_key_env = "DEEPSEEK_API_KEY"
# Reasoning model - alternative to o1

#=============================================================================
# LOCAL - OLLAMA (Free, offline capable)
#=============================================================================
[models.local-devstral]
provider = "ollama"
model = "devstral:24b"
endpoint = "http://localhost:11434"
# Requires: ollama pull devstral:24b

[models.local-codestral]
provider = "ollama"
model = "codestral:22b"
endpoint = "http://localhost:11434"

[models.local-qwen]
provider = "ollama"
model = "qwen2.5-coder:32b"
endpoint = "http://localhost:11434"

#=============================================================================
# LOCAL - vLLM (High performance, production local)
#=============================================================================
[models.vllm-devstral]
provider = "vllm"
model = "mistralai/Devstral-Small-2505"
endpoint = "http://localhost:8000"
# Requires: vllm serve mistralai/Devstral-Small-2505

[models.vllm-custom]
provider = "vllm"
model = "your-finetuned-model"
endpoint = "http://gpu-server.internal:8000"
```

### Provider Implementation

```python
# src/autobuild/models/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def complete(
        self, 
        messages: list[dict], 
        tools: list[dict] | None = None,
        max_tokens: int = 4096
    ) -> str:
        """Generate completion."""
        pass
    
    @abstractmethod
    async def stream(
        self, 
        messages: list[dict],
        tools: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream completion tokens."""
        pass

# Provider implementations
class AnthropicProvider(LLMProvider):
    """Direct Anthropic API (NOT Claude Code subscription)."""
    pass

class MistralProvider(LLMProvider):
    """Mistral API for Devstral models."""
    pass

class BedrockProvider(LLMProvider):
    """AWS Bedrock - uses boto3 credentials."""
    pass

class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI Service."""
    pass

class OpenAIProvider(LLMProvider):
    """Direct OpenAI API."""
    pass

class OpenRouterProvider(LLMProvider):
    """OpenRouter aggregator - unified API for any model."""
    pass

class DeepSeekProvider(LLMProvider):
    """DeepSeek API."""
    pass

class OllamaProvider(LLMProvider):
    """Local Ollama server."""
    pass

class VLLMProvider(LLMProvider):
    """Local vLLM server."""
    pass
```

### Model Selection Strategy

```toml
# autobuild.toml

[models.strategy]
# Cost optimization: use cheaper models for routine work
routine_tasks = "devstral-2"        # Simple implementations
complex_tasks = "claude-sonnet"     # Complex reasoning needed
architectural = "claude-opus"        # Critical decisions (use sparingly)

# Automatic selection based on task complexity
auto_select = true
complexity_thresholds = {
    low = "devstral-2",      # Complexity 1-3
    medium = "devstral-2",   # Complexity 4-6  
    high = "claude-sonnet",  # Complexity 7-8
    critical = "claude-opus" # Complexity 9-10
}

# Budget controls
[models.budget]
daily_limit_usd = 10.0
warn_at_percent = 80
# Actions: "warn", "switch_to_cheaper", "stop"
on_limit_reached = "switch_to_cheaper"
fallback_model = "local-devstral"
```

### Cost Comparison (Typical Task)

Assuming ~50k input tokens, ~10k output tokens per task:

| Provider/Model | Input Cost | Output Cost | Total | vs Claude |
|----------------|------------|-------------|-------|-----------|
| Claude Sonnet 4 | $0.15 | $0.15 | **$0.30** | Baseline |
| Claude Opus 4 | $0.75 | $0.75 | **$1.50** | 5x more |
| Devstral 2 | $0.02 | $0.02 | **$0.04** | 7x cheaper |
| DeepSeek Coder | $0.007 | $0.003 | **$0.01** | 30x cheaper |
| Local (Ollama) | $0 | $0 | **$0** | Free |

**Monthly estimate (100 tasks):**
- Claude Sonnet only: ~$30/month
- Devstral 2 only: ~$4/month
- Mixed (Devstral + Claude for complex): ~$10/month
- Local only: $0/month

### Claude Code CLI Integration (Limited)

While you can't use your Claude Max subscription for API calls, AutoBuild can optionally integrate with Claude Code CLI for specific use cases:

```toml
# autobuild.toml
[claude_code]
# Use Claude Code CLI for interactive tasks (requires Claude Max subscription)
enabled = false  # Disabled by default

# When enabled, these operations use Claude Code CLI instead of API:
use_for = [
    # "interactive_review",  # Human-in-the-loop review sessions
    # "debugging",           # Interactive debugging
]

# Note: This spawns Claude Code CLI subprocess, not API calls
# Useful if you already have Claude Max and want hybrid workflow
```

**Recommendation:** For most users, direct API access (Anthropic, Mistral, etc.) is more flexible and often cheaper than maintaining a Claude Max subscription just for AutoBuild.

---

## LangGraph State Schema

Based on existing research, extended for adversarial cooperation:

```python
from typing import TypedDict, Literal, Annotated, Optional
from langgraph.graph.message import add_messages
import operator

class AutoBuildState(TypedDict):
    """Core state schema for AutoBuild workflow."""
    
    # === Task Metadata ===
    task_id: str
    description: str
    requirements: str  # The "requirements contract" for coach validation
    created_at: str
    
    # === Dialectical Loop State ===
    turn_number: int              # Current turn (max 10)
    player_output: str            # Last implementation attempt
    coach_feedback: str           # Last review/critique
    coach_approved: bool          # Only coach can set this True
    loop_status: Literal["implementing", "reviewing", "approved", "failed"]
    
    # === Phase 2: Planning ===
    implementation_plan: dict
    
    # === Phase 2.5: Architectural Review ===
    architectural_score: int      # 0-100
    architectural_notes: str
    architecture_approved: bool
    
    # === Phase 2.7: Complexity ===
    complexity_score: int         # 1-10
    complexity_factors: list[str]
    approval_level: Literal["auto", "optional", "required"]
    
    # === Phase 2.8: Human Checkpoint ===
    design_approved: bool
    approval_timestamp: Optional[str]
    approval_notes: str
    
    # === Phase 3: Implementation ===
    selected_agent: str           # For future specialist routing
    code_changes: Annotated[list[dict], operator.add]
    
    # === Phase 4/4.5: Testing ===
    test_results: dict
    test_attempt_count: int       # Max 3
    
    # === Phase 5/5.5: Review ===
    review_result: dict
    plan_variance: dict           # LOC, duration variance
    final_status: Literal["complete", "failed", "aborted"]
    
    # === Cross-cutting ===
    messages: Annotated[list, add_messages]
    model_config: dict            # Which LLM to use
    workspace_path: str           # Working directory
    events: Annotated[list[dict], operator.add]  # Audit trail
```

---

## Graph Architecture

### High-Level Flow

```
START
  │
  ▼
┌─────────────────┐
│  task_create    │ (or load existing task)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  phase_2_plan   │  Implementation Planning
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ phase_2_5_arch  │  Architectural Review
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ phase_2_7_cmplx │  Complexity Evaluation
└────────┬────────┘
         │
    [complexity routing]
         │
    ┌────┴────┐
    │         │
auto │    required
    │         │
    ▼         ▼
continue   ┌─────────────────┐
    │      │ phase_2_8_chkpt │  Human Checkpoint (interrupt)
    │      └────────┬────────┘
    │               │
    └───────┬───────┘
            │
            ▼
┌───────────────────────────────────────────┐
│         DIALECTICAL LOOP                  │
│  ┌─────────────┐      ┌─────────────┐    │
│  │   player    │─────►│   coach     │    │
│  │ (implement) │◄─────│ (validate)  │    │
│  └─────────────┘      └─────────────┘    │
│         │                    │            │
│    [turn_limit or approved]              │
└───────────────────┬───────────────────────┘
                    │
           [coach_approved?]
                    │
        ┌───────────┴───────────┐
        │                       │
       Yes                     No
        │                       │
        ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│ phase_5_review  │    │     failed      │
└────────┬────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│ phase_5_5_audit │  Plan Audit
└────────┬────────┘
         │
         ▼
       END
```

### Dialectical Loop Detail

```python
def player_node(state: AutoBuildState) -> dict:
    """Player: Implement based on requirements + coach feedback.
    
    CRITICAL: Fresh LLM instance each turn to prevent context pollution.
    """
    llm = get_llm(state["model_config"])  # Fresh instance
    
    prompt = f"""
    ## Requirements (Your Goal)
    {state['requirements']}
    
    ## Previous Coach Feedback
    {state['coach_feedback'] or 'First turn - no feedback yet'}
    
    ## Your Task
    Implement the requirements. Address ALL feedback points.
    Run tests to verify your implementation.
    
    DO NOT claim success. The coach will validate independently.
    """
    
    result = llm.invoke(prompt, tools=[...])
    
    return {
        "player_output": result,
        "loop_status": "reviewing"
    }


def coach_node(state: AutoBuildState) -> dict:
    """Coach: Validate against requirements, NOT player's claims.
    
    CRITICAL: 
    - Fresh LLM instance each turn
    - Do NOT trust player's self-report
    - Validate EVERY requirement independently
    """
    llm = get_llm(state["model_config"])  # Fresh instance
    
    prompt = f"""
    ## Requirements (Validation Criteria)
    {state['requirements']}
    
    ## Player's Implementation
    {state['player_output']}
    
    ## Your Task
    Validate this implementation against EVERY requirement.
    Run the tests. Check edge cases. Be rigorous.
    
    IGNORE the player's claims of success. Verify independently.
    
    Respond with ONE of:
    - APPROVED: All requirements verified as met
    - FEEDBACK: Specific issues that must be fixed
    
    If providing feedback, be specific and actionable.
    """
    
    validation = llm.invoke(prompt, tools=[...])
    
    approved = "APPROVED" in validation.upper()
    
    return {
        "coach_feedback": validation,
        "coach_approved": approved,
        "turn_number": state["turn_number"] + 1,
        "loop_status": "approved" if approved else "implementing"
    }


def should_continue_loop(state: AutoBuildState) -> str:
    """Routing logic for dialectical loop."""
    if state["coach_approved"]:
        return "review"  # Move to Phase 5
    if state["turn_number"] >= 10:
        return "failed"  # Max turns exceeded
    return "player"  # Continue loop
```

---

## CLI Interface Design

### Command Structure

```bash
autobuild [OPTIONS] COMMAND [ARGS]

Commands:
  init        Initialize AutoBuild in a project
  task        Task management commands
  feature     Feature planning commands
  config      Configuration management
  status      Show current state

Options:
  --model     Override default model
  --local     Use local model endpoint
  --verbose   Show detailed output
  --version   Show version
```

### Task Commands

```bash
autobuild task create "Add user authentication with JWT"
# Creates: TASK-a3f8 (hash-based ID)
# Output: tasks/backlog/TASK-a3f8.md

autobuild task work TASK-a3f8
# Runs full workflow: plan → arch review → complexity → checkpoint → implement → test → review
# Uses dialectical loop for implementation phase

autobuild task work TASK-a3f8 --design-only
# Stops at Phase 2.8 checkpoint

autobuild task work TASK-a3f8 --implement-only
# Resumes from approved design

autobuild task complete TASK-a3f8
# Finalizes task, moves to completed

autobuild task status
# Shows all tasks by state

autobuild task status TASK-a3f8
# Shows detailed status for specific task
```

### Feature Commands

```bash
autobuild feature plan "Add dark mode for settings page"
# Creates:
#   - Feature directory: features/FEAT-b7c2/
#   - Feature README with overview
#   - Implementation guide
#   - Subtasks: TASK-001, TASK-002, TASK-003...

autobuild feature work FEAT-b7c2
# Runs all subtasks (sequential or parallel based on dependencies)
# Uses dialectical loop for each task

autobuild feature status FEAT-b7c2
# Shows feature progress
```

### Project Analysis Commands

```bash
autobuild init
# Analyzes codebase and initializes AutoBuild:
#   - Detects stack (React, Python, .NET, etc.)
#   - Discovers architectural patterns
#   - Populates knowledge graph
#   - Creates .autobuild/ configuration
#   - Generates initial agents for detected stack
#   - Creates rules based on detected conventions

autobuild init --stack react-typescript
# Force specific stack detection

autobuild init --minimal
# Minimal setup without full analysis
```

```bash
autobuild template create
# Generates reusable template from current codebase:
#   - Extracts patterns and structure
#   - Creates template definition
#   - Stores in .autobuild/templates/
#   - Links patterns to knowledge graph

autobuild template create --name "my-react-template"
# Named template

autobuild template create --export ./templates/
# Export to shareable location
```

```bash
autobuild agent enhance
# Discovers and creates specialist agents:
#   - Analyzes stack and patterns
#   - Identifies missing specializations
#   - Generates agent definitions
#   - Updates knowledge graph with agent capabilities

autobuild agent enhance --stack react
# Focus on specific stack

autobuild agent list
# List all available agents

autobuild agent show react-component-specialist
# Show agent details and when it's used
```

```bash
autobuild template apply <template-name>
# Applies template to current project:
#   - Copies structure and patterns
#   - Configures agents for template stack
#   - Updates knowledge graph
#   - Initializes rules

autobuild template apply react-typescript --merge
# Merge with existing project (don't overwrite)

autobuild template list
# List available templates
```

### Context Commands (Debugging)

```bash
autobuild context show
# Shows what context would be retrieved for current state

autobuild context show --job player --task TASK-a3f8
# Show context for specific job type

autobuild context query "react patterns"
# Query knowledge graph directly

autobuild context stats
# Show knowledge graph statistics (nodes, relationships, size)
```

---

## Configuration Structure

### GuardKit's Current Architecture (What AutoBuild Builds On)

GuardKit already uses a **distributed, progressive disclosure** architecture - NOT a monolithic file:

```
.claude/
├── CLAUDE.md                    # Project context (broken into sections)
├── settings.json                # Configuration
│
├── agents/                      # Sub-agents with frontmatter
│   ├── react-component-specialist.md
│   ├── react-testing-specialist.md
│   ├── python-api-specialist.md
│   └── software-architect.md
│
├── rules/                       # Rules structure
│   ├── implementation.md
│   ├── testing.md
│   └── quality-gates.md
│
├── commands/                    # Slash commands
│   ├── task-create.md
│   ├── task-work.md
│   └── feature-plan.md
│
└── stacks/                      # Stack-specific context
    ├── react/
    │   ├── agents/
    │   └── rules/
    └── python/
```

**GuardKit Agent Frontmatter (Current):**
```markdown
---
name: react-component-specialist
description: Expert at creating React components with TypeScript
model: haiku                    # Cost-efficient for implementation
triggers:
  - "*.tsx"
  - "components/**"
stack: react-typescript
phase: implementation
collaborates_with:
  - react-testing-specialist
---

## Core Responsibilities
[Core instructions - always loaded]

---
## Extended Capabilities  
[Extended instructions - loaded on demand via progressive disclosure]
```

**Progressive Disclosure Pattern:**
- **Core content**: Always loaded (essential instructions)
- **Extended content**: Loaded only when relevant (detailed patterns, examples)
- Reduces token usage while maintaining depth when needed

### What AutoBuild Adds: Queryable Metadata Layer

AutoBuild doesn't replace GuardKit's file structure - it **enhances it with a knowledge graph**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTOBUILD ENHANCEMENT                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  GuardKit Files (Source of Truth)     Knowledge Graph (Queryable Index)    │
│  ─────────────────────────────────    ─────────────────────────────────    │
│                                                                             │
│  .claude/agents/                      ┌─────────────────────────────────┐  │
│  ├── react-component.md         ───►  │ (:Agent {                       │  │
│  │   (frontmatter + content)          │   name: "react-component",      │  │
│  │                                    │   model: "haiku",               │  │
│  │                                    │   triggers: ["*.tsx"],          │  │
│  │                                    │   success_rate: 0.94,           │  │
│  │                                    │   avg_turns: 2.3,               │  │
│  │                                    │   file: "agents/react-..."      │  │
│  │                                    │ })                              │  │
│  │                                    └─────────────────────────────────┘  │
│  │                                              │                          │
│  │                                              │ :SPECIALIZES_IN          │
│  │                                              ▼                          │
│  .claude/stacks/react/            ───►  (:Stack {name: "react-ts"})       │
│                                                                             │
│  .claude/rules/                                 │                          │
│  ├── quality-gates.md             ───►  (:Rule)-[:APPLIES_TO]->(:Stack)   │
│                                                                             │
│  Project decisions                              │                          │
│  (learned during work)            ───►  (:Decision)-[:MADE_FOR]->(:Task)  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**What the Knowledge Graph Enables:**
1. **Agent Selection** - Query by triggers, stack, phase, success rate
2. **Learning** - Track which agents work well for which tasks
3. **Cross-Project** - Patterns learned in one project available in others
4. **Dynamic Context** - Assemble job-specific context from graph queries
5. **Debugging** - `autobuild context show` reveals exactly what's loaded

### AutoBuild Directory Structure

```
.autobuild/
├── autobuild.toml              # Main configuration
├── graph.db                    # FalkorDB knowledge graph (or remote connection)
├── state.db                    # SQLite workflow state (LangGraph checkpoints)
│
├── agents/                     # Agent definitions (loaded per-job)
│   ├── _base.md                # Base instructions for all agents
│   ├── player.md               # Player agent (implementation)
│   ├── coach.md                # Coach agent (validation)
│   ├── architect.md            # Architectural review agent
│   └── stack/                  # Stack-specific specialists
│       ├── react-component.md
│       ├── react-hooks.md
│       ├── python-api.md
│       ├── python-testing.md
│       └── ...
│
├── rules/                      # Rules loaded per-context
│   ├── global/                 # Always-active rules
│   │   ├── quality-gates.md
│   │   └── code-style.md
│   ├── stack/                  # Stack-specific rules
│   │   ├── react.md
│   │   ├── python.md
│   │   └── dotnet.md
│   └── phase/                  # Phase-specific rules
│       ├── implementation.md
│       ├── testing.md
│       └── review.md
│
├── templates/                  # Project templates
│   ├── react-typescript/
│   │   ├── template.toml
│   │   ├── structure/
│   │   └── patterns/
│   └── ...
│
└── prompts/                    # Custom prompt overrides (optional)
    ├── player-system.md
    └── coach-system.md
```

### Configuration File (`autobuild.toml`)

```toml
[project]
name = "my-app"
stack = "react-typescript"  # Auto-detected or manual
description = "E-commerce application"

[models]
default = "devstral-2"
player = "devstral-2"       # Can use different models per role
coach = "claude"            # Coach might benefit from stronger reasoning

[models.claude]
provider = "anthropic"
model = "claude-sonnet-4-20250514"
api_key_env = "ANTHROPIC_API_KEY"

[models.devstral-2]
provider = "mistral"
model = "devstral-2"
api_key_env = "MISTRAL_API_KEY"

[models.devstral-local]
provider = "mistral"
model = "devstral-small-2"
endpoint = "http://localhost:8000"

[graph]
backend = "falkordb"        # or "sqlite" for simpler setup
connection = "redis://localhost:6379"
# For cloud: connection = "redis://user:pass@falkordb.cloud:6379"

[workflow]
max_turns = 10              # Dialectical loop limit
test_retry_max = 3          # Test enforcement retries
complexity_checkpoint = 7   # Require approval above this

[quality_gates]
line_coverage = 80
branch_coverage = 75
architectural_score = 60

[context]
max_tokens_per_job = 2000   # Token budget per context retrieval
cache_ttl = 3600            # Cache context for 1 hour
```

### Agent Definition Format

Agents are loaded dynamically based on the current job. Each agent file follows this structure:

```markdown
# .autobuild/agents/stack/react-component.md

---
name: react-component-specialist
stack: react-typescript
triggers:
  - file_pattern: "*.tsx"
  - file_pattern: "components/**"
  - task_keywords: ["component", "ui", "interface"]
tools:
  - read_file
  - write_file
  - execute_command
  - run_tests
collaborates_with:
  - react-hooks-specialist
  - react-testing-specialist
---

## Role

You are a React component specialist focusing on building reusable, 
accessible, and performant UI components.

## Principles

1. **Composition over inheritance** - Build small, composable components
2. **Single responsibility** - Each component does one thing well
3. **Accessibility first** - ARIA labels, keyboard navigation, screen readers
4. **Performance aware** - Memoization, lazy loading, bundle size

## Patterns

### Component Structure
\`\`\`tsx
// Props interface first
interface ButtonProps {
  variant: 'primary' | 'secondary';
  // ...
}

// Named export for component
export function Button({ variant, ...props }: ButtonProps) {
  // ...
}
\`\`\`

### State Management
- Local state: useState for component-specific state
- Shared state: Context or state library based on project setup
- Server state: React Query / SWR patterns

## Anti-patterns to Avoid

- Prop drilling beyond 2 levels
- Business logic in components
- Inline styles (use CSS modules or Tailwind)
- Missing error boundaries
```

### Rules Format

Rules are loaded based on stack and phase:

```markdown
# .autobuild/rules/stack/react.md

---
stack: react-typescript
applies_to:
  - implementation
  - review
priority: high
---

## File Organization

- Components in `src/components/` with PascalCase naming
- Hooks in `src/hooks/` prefixed with `use`
- Utils in `src/utils/` with camelCase naming
- Types in `src/types/` or co-located with components

## Import Order

1. React and framework imports
2. Third-party libraries
3. Internal absolute imports
4. Relative imports
5. Styles

## Testing Requirements

- Every component must have a test file: `ComponentName.test.tsx`
- Test user interactions, not implementation details
- Use React Testing Library, not Enzyme
- Minimum 80% coverage for new components

## Code Style

- Functional components only (no class components)
- TypeScript strict mode enabled
- No `any` types without justification
- Prefer named exports over default exports
```

### How Context is Assembled

```python
def assemble_context(job_type: str, task: Task, state: AutoBuildState) -> str:
    """Assemble context from multiple sources for current job."""
    
    context_parts = []
    
    # 1. Base agent instructions (always included)
    base_agent = load_agent("_base.md")
    context_parts.append(base_agent)
    
    # 2. Role-specific agent (player or coach)
    role_agent = load_agent(f"{job_type}.md")
    context_parts.append(role_agent)
    
    # 3. Stack-specific agents (if triggered)
    stack = state["project_stack"]
    triggered_agents = find_triggered_agents(task, stack)
    for agent in triggered_agents[:2]:  # Limit to 2 specialists
        context_parts.append(load_agent(f"stack/{agent}.md"))
    
    # 4. Global rules (always)
    global_rules = load_rules("global/")
    context_parts.append(global_rules)
    
    # 5. Stack-specific rules
    stack_rules = load_rules(f"stack/{stack}.md")
    context_parts.append(stack_rules)
    
    # 6. Phase-specific rules
    phase = get_current_phase(job_type)
    phase_rules = load_rules(f"phase/{phase}.md")
    context_parts.append(phase_rules)
    
    # 7. Knowledge graph context (job-specific)
    graph_context = context_selector.get_context(job_type, task_id=task.id)
    context_parts.append(format_graph_context(graph_context))
    
    # Combine and check token budget
    full_context = "\n\n".join(context_parts)
    return truncate_to_budget(full_context, max_tokens=2000)
```

### Comparison: GuardKit (Current) vs AutoBuild Enhancement

| Aspect | GuardKit (Current) | AutoBuild (Enhanced) |
|--------|-------------------|----------------------|
| **Structure** | Distributed files with frontmatter | Same + queryable graph index |
| **Agent Selection** | Trigger patterns in frontmatter | Graph query by triggers, success rate, stack |
| **Model Config** | Frontmatter `model: haiku/sonnet` | Same + per-role defaults in config |
| **Progressive Disclosure** | Core/ext file split | Same + graph tracks usage patterns |
| **Context Loading** | Manual via slash commands | Automatic per-job assembly |
| **Token Usage** | Reduced via progressive disclosure | Further optimized via graph queries |
| **Learning** | None | Graph stores decisions, success rates |
| **Cross-Project** | Copy files manually | Shared graph patterns |
| **Debugging** | Review loaded files | `autobuild context show` |

---

## File Structure

### Project Structure

```
autobuild/
├── pyproject.toml
├── README.md
├── src/
│   └── autobuild/
│       ├── __init__.py
│       ├── cli.py              # Click/Typer CLI
│       ├── config.py           # Configuration management
│       │
│       ├── models/             # LLM integrations
│       │   ├── __init__.py
│       │   ├── base.py         # Abstract LLM interface
│       │   ├── anthropic.py    # Claude
│       │   ├── mistral.py      # Devstral
│       │   └── deepseek.py     # DeepSeek
│       │
│       ├── graph/              # LangGraph workflow
│       │   ├── __init__.py
│       │   ├── state.py        # AutoBuildState TypedDict
│       │   ├── nodes.py        # All node implementations
│       │   ├── edges.py        # Routing functions
│       │   └── builder.py      # Graph construction
│       │
│       ├── knowledge/          # Knowledge graph (Graphiti + FalkorDB)
│       │   ├── __init__.py
│       │   ├── schema.py       # Entity and relationship definitions
│       │   ├── client.py       # FalkorDB/Graphiti client wrapper
│       │   ├── populate.py     # Graph population during init
│       │   └── queries.py      # Cypher query templates
│       │
│       ├── context/            # Job-specific context retrieval
│       │   ├── __init__.py
│       │   ├── selector.py     # ContextSelector class
│       │   ├── assembler.py    # Context assembly from multiple sources
│       │   └── loaders.py      # Agent/rule file loaders
│       │
│       ├── agents/             # Player/Coach logic
│       │   ├── __init__.py
│       │   ├── player.py       # Implementation agent
│       │   ├── coach.py        # Validation agent
│       │   └── discovery.py    # Agent enhancement/discovery
│       │
│       ├── quality/            # Quality gates
│       │   ├── __init__.py
│       │   ├── gates.py        # Gate definitions
│       │   └── enforcement.py  # Test retry logic
│       │
│       ├── tasks/              # Task management
│       │   ├── __init__.py
│       │   ├── create.py
│       │   ├── work.py
│       │   └── complete.py
│       │
│       ├── templates/          # Template management
│       │   ├── __init__.py
│       │   ├── create.py       # Template creation from codebase
│       │   ├── apply.py        # Template application
│       │   └── detect.py       # Stack/pattern detection
│       │
│       └── init/               # Project initialization
│           ├── __init__.py
│           ├── analyzer.py     # Codebase analysis
│           ├── setup.py        # .autobuild directory setup
│           └── defaults.py     # Default agents/rules
│
├── defaults/                   # Shipped default configurations
│   ├── agents/
│   │   ├── _base.md
│   │   ├── player.md
│   │   ├── coach.md
│   │   └── stack/
│   │       ├── react-component.md
│   │       ├── python-api.md
│   │       └── ...
│   └── rules/
│       ├── global/
│       ├── stack/
│       └── phase/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── docs/
```

### User Project Structure (after `autobuild init`)

```
your-project/
├── .autobuild/
│   ├── autobuild.toml          # Project configuration
│   ├── graph.db                # FalkorDB knowledge graph
│   ├── state.db                # SQLite workflow state
│   │
│   ├── agents/                 # Agent definitions
│   │   ├── _base.md            # Base agent instructions
│   │   ├── player.md           # Player agent
│   │   ├── coach.md            # Coach agent
│   │   ├── architect.md        # Architectural review
│   │   └── stack/              # Stack specialists (auto-generated)
│   │       ├── react-component.md
│   │       └── react-hooks.md
│   │
│   ├── rules/                  # Rules by context
│   │   ├── global/
│   │   │   └── quality-gates.md
│   │   ├── stack/
│   │   │   └── react.md        # Detected/generated
│   │   └── phase/
│   │       ├── implementation.md
│   │       └── testing.md
│   │
│   └── templates/              # Project templates
│       └── (imported templates)
│
├── tasks/
│   ├── backlog/
│   │   └── TASK-a3f8.md
│   ├── in_progress/
│   ├── in_review/
│   └── completed/
│
└── features/
    └── FEAT-b7c2/
        ├── README.md
        ├── implementation-guide.md
        └── subtasks/
```

---

## Phased Development Strategy

### The Insight: Prove Before Building

Instead of building the full LangGraph implementation upfront, we take a pragmatic approach:

1. **Prototype** adversarial cooperation with Claude Agent SDK (extension to GuardKit)
2. **Extract** learnings into Knowledge Graph MCP
3. **Build** full AutoBuild on proven foundations

This minimizes risk and maximizes learning.

### Why This Order?

| Phase | Risk | Investment | Learning |
|-------|------|------------|----------|
| **A: SDK Prototype** | Low | 1-2 weeks | Proves pattern works |
| **B: Knowledge Graph MCP** | Medium | 2-3 weeks | Informed by real usage |
| **C: AutoBuild (LangGraph)** | Higher | 4-6 weeks | Built on proven foundations |

**Key benefits:**
- Validate adversarial cooperation before committing to LangGraph
- GuardKit users get value immediately (new `/autobuild` command)
- Knowledge Graph MCP design informed by prototype learnings
- Lower total risk, faster time to first value

---

## Phase A: Claude Agent SDK Prototype (Week 1-2)

### Goal

Prove adversarial cooperation works by extending GuardKit with a new `/autobuild` command that orchestrates coach-player sessions using the Claude Agent SDK.

### Supported Execution Modes

| Mode | Command | Scope |
|------|---------|-------|
| **Task** | `/autobuild TASK-XXX` | Single task, one coach-player loop |
| **Feature** | `/autobuild FEAT-XXX` | Full feature, orchestrates all subtasks |

---

## Formalized Feature Structure

### Current Structure (Informal)

```
backlog/FEAT-XXX/
├── README.md              # Informal overview
├── implementation-guide.md
└── tasks/
    ├── TASK-001.md
    ├── TASK-002.md
    └── TASK-003.md
```

### New Structure (Formalized)

```
backlog/FEAT-XXX/
├── FEATURE.md             # Formalized feature spec with frontmatter
├── implementation-guide.md
└── tasks/
    ├── TASK-001.md
    ├── TASK-002.md
    └── TASK-003.md
```

### Feature Spec Format (FEATURE.md)

```markdown
---
# Feature Metadata
id: FEAT-a3f8
title: Add Dark Mode Support
status: backlog  # backlog | in_progress | in_review | completed | blocked
priority: high   # critical | high | medium | low
complexity: 7    # 1-10 scale
created: 2025-12-20T09:00:00Z
updated: 2025-12-20T14:30:00Z

# Ownership
author: rich
assignee: autobuild

# Dependencies
dependencies: []  # Other FEAT-XXX or external blockers
blocked_by: []

# Task Tracking
tasks:
  - id: TASK-001
    title: Create ThemeContext provider
    status: completed
    complexity: 3
  - id: TASK-002
    title: Add theme toggle component
    status: in_progress
    complexity: 4
  - id: TASK-003
    title: Update all components for dark mode
    status: backlog
    complexity: 6
    depends_on: [TASK-001, TASK-002]

# Execution Configuration
autobuild:
  mode: sequential  # sequential | parallel | auto
  max_parallel: 2   # For parallel mode
  checkpoint_after: [TASK-002]  # Human review points
  
# Acceptance Criteria (Feature-Level)
acceptance_criteria:
  - id: AC-01
    description: Users can toggle dark mode in settings
    verified: false
  - id: AC-02
    description: Theme preference persists across browser sessions
    verified: false
  - id: AC-03
    description: All existing components render correctly in dark mode
    verified: false
  - id: AC-04
    description: No accessibility contrast violations in dark mode
    verified: false
---

# Feature: Add Dark Mode Support

## Overview

Enable users to switch between light and dark color themes across the 
application, with preference persistence.

## User Stories

**As a** user who works late at night,
**I want** to switch to a dark color theme,
**So that** the screen doesn't strain my eyes.

**As a** user with light sensitivity,
**I want** the app to remember my theme preference,
**So that** I don't have to change it every session.

## Technical Approach

1. Create React Context for theme state management
2. Implement CSS custom properties for theme colors
3. Add toggle component to settings page
4. Store preference in localStorage
5. Update all existing components to use theme tokens

## Out of Scope

- System preference detection (follow-up feature)
- Per-page theme overrides
- Theme customization beyond light/dark

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Component visual regressions | High | Visual regression tests |
| Contrast accessibility issues | Medium | Automated WCAG checks |
| localStorage not available | Low | Fallback to light theme |

## Definition of Done

- [ ] All acceptance criteria verified by coach
- [ ] All tasks completed
- [ ] No failing tests
- [ ] Visual regression tests pass
- [ ] Accessibility audit passes
```

### Task Spec Format (TASK-XXX.md)

```markdown
---
# Task Metadata
id: TASK-001
feature: FEAT-a3f8
title: Create ThemeContext provider
status: backlog  # backlog | in_progress | implementing | validating | completed | failed
priority: high
complexity: 3
created: 2025-12-20T09:00:00Z
updated: 2025-12-20T14:30:00Z

# Dependencies
depends_on: []  # Other TASK-XXX within this feature
blocks: [TASK-003]

# Autobuild Execution Tracking
autobuild:
  turns_used: 0
  max_turns: 10
  last_run: null
  player_model: haiku
  coach_model: sonnet

# Requirements Contract (for coach validation)
requirements:
  - id: REQ-01
    description: ThemeContext provides 'theme' and 'toggleTheme' values
    type: functional
    verified: false
  - id: REQ-02  
    description: Theme state persists to localStorage on change
    type: functional
    verified: false
  - id: REQ-03
    description: Context uses 'light' as default theme
    type: functional
    verified: false
  - id: REQ-04
    description: TypeScript types exported for theme values
    type: technical
    verified: false
  - id: REQ-05
    description: Unit tests cover toggle and persistence
    type: testing
    verified: false

# Affected Files (for agent routing)
affected_files:
  - src/contexts/ThemeContext.tsx
  - src/contexts/ThemeContext.test.tsx
  - src/types/theme.ts
---

# Task: Create ThemeContext Provider

## Description

Create a React Context that manages the application's color theme state,
providing theme value and toggle function to all components.

## Technical Details

### Implementation

```typescript
// src/contexts/ThemeContext.tsx
type Theme = 'light' | 'dark';

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

export const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    return localStorage.getItem('theme') as Theme || 'light';
  });
  
  const toggleTheme = useCallback(() => {
    setTheme(prev => {
      const next = prev === 'light' ? 'dark' : 'light';
      localStorage.setItem('theme', next);
      return next;
    });
  }, []);
  
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
```

## Acceptance Criteria

1. ThemeContext exports `theme` (current theme) and `toggleTheme` (function)
2. Theme defaults to 'light' if no localStorage value
3. Theme changes persist to localStorage immediately
4. TypeScript types are properly exported
5. Unit tests verify toggle and persistence behavior
```

---

## /autobuild Command Specification

### Command Syntax

```bash
# Single task
/autobuild TASK-XXX [options]

# Full feature
/autobuild FEAT-XXX [options]

# Options
--max-turns N       # Override max turns per task (default: 10)
--mode MODE         # sequential | parallel | auto (feature only)
--checkpoint        # Pause after each task for review (feature only)
--dry-run           # Show execution plan without running
--verbose           # Show detailed coach-player exchanges
--resume            # Resume from last checkpoint
```

### Task Execution Flow

```
/autobuild TASK-001

┌─────────────────────────────────────────────────────────────────┐
│                      TASK EXECUTION                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Load Task                                                   │
│     └── Parse TASK-001.md frontmatter                          │
│     └── Extract requirements contract                           │
│     └── Identify affected files (for agent routing)            │
│                                                                 │
│  2. Setup Worktrees                                             │
│     └── Create player worktree: autobuild-player-TASK-001      │
│     └── Create coach worktree: autobuild-coach-TASK-001        │
│                                                                 │
│  3. Dialectical Loop                                            │
│     ┌─────────────────────────────────────────────────────────┐│
│     │  while turn < max_turns and not approved:               ││
│     │      player implements (uses requirements + feedback)    ││
│     │      sync changes to coach worktree                      ││
│     │      coach validates (uses requirements contract)        ││
│     │      if approved: break                                  ││
│     │      else: feedback → next turn                          ││
│     └─────────────────────────────────────────────────────────┘│
│                                                                 │
│  4. Update Task Status                                          │
│     └── Mark requirements as verified: true/false              │
│     └── Update status: completed | failed                      │
│     └── Record turns_used, timestamps                          │
│                                                                 │
│  5. Merge & Cleanup                                             │
│     └── If approved: merge player worktree → main              │
│     └── Cleanup worktrees                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Feature Execution Flow

```
/autobuild FEAT-a3f8

┌─────────────────────────────────────────────────────────────────┐
│                     FEATURE EXECUTION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Load Feature                                                │
│     └── Parse FEATURE.md frontmatter                           │
│     └── Extract task list with dependencies                    │
│     └── Build execution DAG                                     │
│     └── Extract feature-level acceptance criteria              │
│                                                                 │
│  2. Plan Execution                                              │
│     ┌─────────────────────────────────────────────────────────┐│
│     │  Execution Plan for FEAT-a3f8:                          ││
│     │                                                          ││
│     │  Stage 1 (parallel):                                     ││
│     │    └── TASK-001: Create ThemeContext provider           ││
│     │    └── TASK-002: Add theme toggle component             ││
│     │                                                          ││
│     │  [CHECKPOINT - Human Review]                             ││
│     │                                                          ││
│     │  Stage 2:                                                 ││
│     │    └── TASK-003: Update all components (depends: 1,2)   ││
│     │                                                          ││
│     │  Final: Feature-level validation                         ││
│     └─────────────────────────────────────────────────────────┘│
│                                                                 │
│  3. Execute Tasks                                               │
│     └── For each stage:                                         │
│         └── Run tasks (sequential or parallel per config)      │
│         └── Each task uses dialectical loop (see above)        │
│         └── Update FEATURE.md task statuses                    │
│         └── If checkpoint: pause for human review              │
│                                                                 │
│  4. Feature-Level Validation                                    │
│     ┌─────────────────────────────────────────────────────────┐│
│     │  Feature Coach validates acceptance criteria:            ││
│     │                                                          ││
│     │  ✓ AC-01: Users can toggle dark mode in settings        ││
│     │  ✓ AC-02: Theme preference persists across sessions     ││
│     │  ✓ AC-03: All components render correctly in dark mode  ││
│     │  ✓ AC-04: No accessibility contrast violations          ││
│     │                                                          ││
│     │  Feature APPROVED                                        ││
│     └─────────────────────────────────────────────────────────┘│
│                                                                 │
│  5. Update Feature Status                                       │
│     └── Mark acceptance_criteria as verified                   │
│     └── Update status: completed                               │
│     └── Record completion timestamp                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Dependency-Aware Execution

```python
def build_execution_dag(feature: Feature) -> list[list[Task]]:
    """Build stages based on task dependencies."""
    
    remaining = set(feature.tasks)
    completed = set()
    stages = []
    
    while remaining:
        # Find tasks with all dependencies satisfied
        ready = [
            task for task in remaining
            if all(dep in completed for dep in task.depends_on)
        ]
        
        if not ready:
            raise CyclicDependencyError(remaining)
        
        stages.append(ready)
        completed.update(t.id for t in ready)
        remaining -= set(ready)
    
    return stages

# Example result for FEAT-a3f8:
# [
#   [TASK-001, TASK-002],  # Stage 1: can run in parallel
#   [TASK-003],            # Stage 2: depends on 1 and 2
# ]
```

### Coach Prompts

**Task-Level Coach:**
```python
TASK_COACH_PROMPT = """
## Your Role: TASK COACH (Validation)

You are validating implementation of a specific task.

## Requirements Contract
{requirements_yaml}

## Your Validation Process
1. For EACH requirement in the contract:
   - Verify the implementation satisfies it
   - Run relevant tests
   - Check edge cases
   
2. Mark each requirement as:
   - ✓ VERIFIED: Implementation satisfies requirement
   - ✗ FAILED: Specific issue (provide actionable feedback)

## Response Format

```yaml
requirements:
  REQ-01:
    status: verified
    evidence: "ThemeContext.tsx exports theme and toggleTheme"
  REQ-02:
    status: failed
    issue: "localStorage.setItem called but not tested"
    feedback: "Add test case for localStorage persistence"
```

If ALL requirements verified:
  APPROVED

If ANY requirements failed:
  FEEDBACK: [consolidated actionable feedback]
"""
```

**Feature-Level Coach:**
```python
FEATURE_COACH_PROMPT = """
## Your Role: FEATURE COACH (Final Validation)

You are performing final validation of a complete feature.

## Feature Acceptance Criteria
{acceptance_criteria_yaml}

## All Tasks Completed
{task_summary}

## Your Validation Process
1. For EACH acceptance criterion:
   - Test the feature end-to-end
   - Verify user-facing behavior
   - Check integration between components
   
2. This is FINAL validation - be thorough

## Response Format

```yaml
acceptance_criteria:
  AC-01:
    status: verified
    evidence: "Toggle in settings changes theme immediately"
  AC-02:
    status: verified
    evidence: "Refreshed page, theme persisted"
  AC-03:
    status: failed
    issue: "Modal component still uses hardcoded colors"
    feedback: "Update Modal.tsx to use theme tokens"
```

If ALL criteria verified:
  FEATURE APPROVED

If ANY criteria failed:
  FEATURE FEEDBACK: [which tasks need revision]
"""
```

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    /autobuild FEAT-XXX                          │
│                   (New GuardKit Command)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Python Orchestrator (Claude Agent SDK)                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                                                             ││
│  │  feature = load_feature(feat_id)                            ││
│  │  stages = build_execution_dag(feature)                      ││
│  │                                                             ││
│  │  for stage in stages:                                       ││
│  │      if feature.autobuild.mode == "parallel":               ││
│  │          await asyncio.gather(*[                            ││
│  │              run_task_loop(task) for task in stage          ││
│  │          ])                                                 ││
│  │      else:                                                  ││
│  │          for task in stage:                                 ││
│  │              await run_task_loop(task)                      ││
│  │                                                             ││
│  │      if stage_has_checkpoint(stage, feature):               ││
│  │          await human_checkpoint()                           ││
│  │                                                             ││
│  │  # Final feature-level validation                           ││
│  │  await feature_coach.validate(feature)                      ││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│            │                    │                    │          │
│            ▼                    ▼                    ▼          │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐│
│  │  Task Loop       │ │  Task Loop       │ │  Feature Coach   ││
│  │  TASK-001        │ │  TASK-002        │ │  (Final Valid.)  ││
│  │                  │ │                  │ │                  ││
│  │  Player ⟷ Coach  │ │  Player ⟷ Coach  │ │  Validates ACs   ││
│  │  (worktree 1)    │ │  (worktree 2)    │ │                  ││
│  └──────────────────┘ └──────────────────┘ └──────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# scripts/autobuild.py
from claude_code_sdk import query, ClaudeCodeOptions
from dataclasses import dataclass
from pathlib import Path
import asyncio
import yaml

@dataclass
class Task:
    id: str
    feature: str
    title: str
    status: str
    requirements: list[dict]
    depends_on: list[str]
    affected_files: list[str]

@dataclass  
class Feature:
    id: str
    title: str
    status: str
    tasks: list[Task]
    acceptance_criteria: list[dict]
    autobuild_config: dict

def load_feature(feat_id: str) -> Feature:
    """Load feature spec from FEATURE.md."""
    feature_dir = Path(f"backlog/{feat_id}")
    feature_file = feature_dir / "FEATURE.md"
    
    content = feature_file.read_text()
    frontmatter, body = parse_frontmatter(content)
    
    tasks = []
    for task_meta in frontmatter["tasks"]:
        task_file = feature_dir / "tasks" / f"{task_meta['id']}.md"
        task = load_task(task_file)
        tasks.append(task)
    
    return Feature(
        id=frontmatter["id"],
        title=frontmatter["title"],
        status=frontmatter["status"],
        tasks=tasks,
        acceptance_criteria=frontmatter["acceptance_criteria"],
        autobuild_config=frontmatter.get("autobuild", {})
    )

async def run_task_loop(task: Task) -> bool:
    """Execute single task with coach-player loop."""
    
    # Update status
    update_task_status(task.id, "implementing")
    
    # Setup worktrees
    player_wt = setup_worktree(f"autobuild-player-{task.id}")
    coach_wt = setup_worktree(f"autobuild-coach-{task.id}")
    
    player_opts = ClaudeCodeOptions(cwd=player_wt)
    coach_opts = ClaudeCodeOptions(cwd=coach_wt)
    
    max_turns = task.autobuild_config.get("max_turns", 10)
    coach_feedback = ""
    approved = False
    turn = 0
    
    while turn < max_turns and not approved:
        turn += 1
        print(f"\n[{task.id}] Turn {turn}/{max_turns}")
        
        # Player implements
        player_prompt = build_player_prompt(task, coach_feedback)
        player_result = await query(prompt=player_prompt, options=player_opts)
        
        # Sync to coach
        sync_worktrees(player_wt, coach_wt)
        
        # Coach validates against requirements contract
        coach_prompt = build_task_coach_prompt(task)
        coach_result = await query(prompt=coach_prompt, options=coach_opts)
        
        # Parse coach response
        validation = parse_coach_validation(coach_result)
        
        if validation.all_verified:
            approved = True
            update_requirements_status(task.id, validation.requirements)
            print(f"[{task.id}] ✅ Approved!")
        else:
            coach_feedback = validation.feedback
            print(f"[{task.id}] 📝 Feedback received")
    
    # Update task status
    status = "completed" if approved else "failed"
    update_task_status(task.id, status, turns_used=turn)
    
    # Merge if approved
    if approved:
        merge_worktree(player_wt, "main")
    
    cleanup_worktrees([player_wt, coach_wt])
    return approved

async def run_feature(feat_id: str, mode: str = "auto") -> bool:
    """Execute full feature with all tasks."""
    
    feature = load_feature(feat_id)
    update_feature_status(feature.id, "in_progress")
    
    # Build dependency-aware execution stages
    stages = build_execution_dag(feature)
    
    print(f"\n{'='*60}")
    print(f"Executing Feature: {feature.title}")
    print(f"Tasks: {len(feature.tasks)}, Stages: {len(stages)}")
    print(f"{'='*60}")
    
    # Execute each stage
    for stage_num, stage_tasks in enumerate(stages, 1):
        print(f"\n--- Stage {stage_num} ---")
        
        execution_mode = feature.autobuild_config.get("mode", mode)
        
        if execution_mode == "parallel":
            # Run tasks in parallel
            results = await asyncio.gather(*[
                run_task_loop(task) for task in stage_tasks
            ])
            all_passed = all(results)
        else:
            # Run tasks sequentially
            all_passed = True
            for task in stage_tasks:
                passed = await run_task_loop(task)
                if not passed:
                    all_passed = False
                    break
        
        if not all_passed:
            print(f"\n❌ Stage {stage_num} failed")
            update_feature_status(feature.id, "blocked")
            return False
        
        # Check for human checkpoint
        checkpoint_after = feature.autobuild_config.get("checkpoint_after", [])
        stage_task_ids = [t.id for t in stage_tasks]
        if any(tid in checkpoint_after for tid in stage_task_ids):
            print("\n⏸️  CHECKPOINT: Human review required")
            print("Run '/autobuild FEAT-XXX --resume' to continue")
            save_checkpoint(feature.id, stage_num)
            return True  # Paused, not failed
    
    # All tasks complete - feature-level validation
    print(f"\n--- Feature Validation ---")
    
    feature_approved = await run_feature_validation(feature)
    
    if feature_approved:
        update_feature_status(feature.id, "completed")
        print(f"\n🎉 Feature {feature.id} completed!")
    else:
        update_feature_status(feature.id, "in_review")
        print(f"\n📝 Feature needs revision")
    
    return feature_approved

async def run_feature_validation(feature: Feature) -> bool:
    """Final feature-level validation by feature coach."""
    
    coach_prompt = build_feature_coach_prompt(feature)
    coach_result = await query(prompt=coach_prompt)
    
    validation = parse_feature_validation(coach_result)
    
    # Update acceptance criteria
    for ac_id, result in validation.criteria.items():
        update_acceptance_criterion(feature.id, ac_id, result.verified)
    
    return validation.all_verified

# CLI entry point
async def main():
    import sys
    
    target = sys.argv[1]  # TASK-XXX or FEAT-XXX
    
    if target.startswith("FEAT-"):
        await run_feature(target)
    elif target.startswith("TASK-"):
        task = load_task_standalone(target)
        await run_task_loop(task)
    else:
        print(f"Unknown target: {target}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### Updated /feature-plan Command

The existing `/feature-plan` command should be updated to generate the new formalized structure:

```markdown
# .claude/commands/feature-plan.md (updated)

When creating a feature plan, generate:

1. **FEATURE.md** with full frontmatter:
   - Metadata (id, title, status, priority, complexity)
   - Task list with dependencies
   - Autobuild configuration
   - Acceptance criteria (feature-level)

2. **implementation-guide.md** (unchanged)

3. **tasks/TASK-XXX.md** for each task:
   - Metadata (id, feature, status, complexity)
   - Dependencies (depends_on, blocks)
   - Requirements contract (for coach validation)
   - Affected files (for agent routing)
```

### What We Learn from Phase A

| Learning | Informs |
|----------|---------|
| Optimal task turn limits | AutoBuild default config |
| Optimal feature stage parallelism | AutoBuild parallel execution |
| Effective requirements contract format | Task schema in Knowledge Graph |
| Feature-level validation patterns | Feature coach design |
| Checkpoint effectiveness | Human checkpoint strategy |
| Task dependency patterns | DAG execution in LangGraph |
| Git worktree management | AutoBuild parallel architecture |

### Success Criteria for Phase A

- [ ] `/autobuild TASK-XXX` works end-to-end
- [ ] `/autobuild FEAT-XXX` orchestrates all tasks correctly
- [ ] Dependency-aware execution (DAG) working
- [ ] Parallel task execution working
- [ ] Human checkpoints pause execution correctly
- [ ] Feature-level validation catches integration issues
- [ ] Higher completion rate than single-agent approach
- [ ] Documented learnings for Phase B/C
- [ ] Orchestrator mode working with --review-agent flag

---

## Orchestrator Mode: Automating the Human Role

### The Insight

From real-world usage patterns:
- Human checkpoints are rarely invoked (complexity < 7 threshold)
- When they do trigger, the recommendation is almost always accepted
- The human's actual role is: follow implementation guide → run tasks in parallel (Conductor) → approve obvious checkpoints

**Key Question:** Can we automate the human's role with an agent orchestrator?

### Current Human Workflow (What We're Automating)

```
┌─────────────────────────────────────────────────────────────────┐
│            CURRENT: Human as Orchestrator                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. /feature-plan "dark mode support"                          │
│     └── Creates FEATURE.md + tasks                              │
│                                                                 │
│  2. Human reads implementation-guide.md                         │
│     └── Understands task dependencies and parallel groups       │
│                                                                 │
│  3. Human sets up Conductor workspaces                          │
│     └── Creates git worktrees for parallel tasks                │
│                                                                 │
│  4. Human runs tasks (parallel where possible)                  │
│     └── /task-work TASK-001 (worktree 1)                       │
│     └── /task-work TASK-002 (worktree 2)  -- parallel          │
│     └── /task-work TASK-003 (after 1,2 complete)               │
│                                                                 │
│  5. Human handles checkpoints                                   │
│     └── Reviews recommendation                                  │
│     └── Almost always clicks "Approve"                          │
│                                                                 │
│  6. Human merges completed work                                 │
│     └── Merge worktrees → main                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### New: Orchestrator Mode

```bash
# Standard mode: Human checkpoints pause execution
/autobuild FEAT-a3f8

# Orchestrator mode: Agent acts on behalf of human
/autobuild FEAT-a3f8 --orchestrate

# With specific options
/autobuild FEAT-a3f8 --orchestrate --max-parallel 3

# Trust but verify: Review agent handles checkpoints
/autobuild FEAT-a3f8 --orchestrate --review-agent

# Full autonomy: Skip review agent, auto-approve all
/autobuild FEAT-a3f8 --orchestrate --auto-approve
```

### Orchestrator Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR MODE: /autobuild FEAT-XXX --orchestrate     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Orchestrator Agent (replaces human)                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  1. Load feature and implementation guide                           │   │
│  │  2. Build execution DAG from dependencies                           │   │
│  │  3. Identify parallel groups (no file conflicts)                    │   │
│  │  4. For each stage:                                                 │   │
│  │     ├── Create git worktrees (like Conductor)                       │   │
│  │     ├── Run tasks in parallel via asyncio.gather()                  │   │
│  │     ├── Handle checkpoints:                                         │   │
│  │     │   ├── --auto-approve: Accept immediately                      │   │
│  │     │   └── --review-agent: Review Agent decides                    │   │
│  │     └── Sync and merge completed worktrees                          │   │
│  │  5. Run feature-level validation                                    │   │
│  │  6. Final merge (or pause for human if configured)                  │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│        │              │              │                                      │
│        ▼              ▼              ▼                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                                  │
│  │ Worktree │  │ Worktree │  │ Review   │                                  │
│  │ TASK-001 │  │ TASK-002 │  │ Agent    │                                  │
│  │          │  │          │  │          │                                  │
│  │ Player   │  │ Player   │  │ Handles  │                                  │
│  │ ⟷ Coach  │  │ ⟷ Coach  │  │ chkpts   │                                  │
│  └──────────┘  └──────────┘  └──────────┘                                  │
│       │              │              │                                       │
│       └──────────────┴──────────────┘                                       │
│                      │                                                      │
│                      ▼                                                      │
│              ┌──────────────┐                                               │
│              │ Merge to     │                                               │
│              │ main branch  │                                               │
│              └──────────────┘                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Review Agent (Checkpoint Handler)

Instead of always auto-approving, the Review Agent can make intelligent decisions:

```python
REVIEW_AGENT_PROMPT = """
## Your Role: REVIEW AGENT (Checkpoint Handler)

You are reviewing a checkpoint that would normally require human approval.
Your job is to decide: APPROVE or ESCALATE to human.

## Checkpoint Context
{checkpoint_context}

## What Triggered This Checkpoint
{trigger_reason}

## Recommendation Being Reviewed
{recommendation}

## Your Decision Criteria

APPROVE if:
- Recommendation is reasonable and low-risk
- No obvious issues or red flags
- Aligns with project patterns and conventions
- Complexity is manageable

ESCALATE if:
- Recommendation seems risky or unusual
- Breaking changes to existing code
- Security-sensitive changes
- Architectural decisions with long-term impact
- Anything you're uncertain about

## Response Format

DECISION: [APPROVE | ESCALATE]
RATIONALE: [Brief explanation]
CONFIDENCE: [HIGH | MEDIUM | LOW]

If ESCALATE, explain what human should review.
"""

async def handle_checkpoint(
    checkpoint: Checkpoint, 
    mode: str
) -> CheckpointDecision:
    """Handle checkpoint based on orchestrator mode."""
    
    if mode == "auto-approve":
        # Full autonomy - approve everything
        return CheckpointDecision(action="approve", rationale="Auto-approved")
    
    elif mode == "review-agent":
        # Review agent decides
        review_prompt = REVIEW_AGENT_PROMPT.format(
            checkpoint_context=checkpoint.context,
            trigger_reason=checkpoint.trigger,
            recommendation=checkpoint.recommendation
        )
        
        result = await query(prompt=review_prompt)
        decision = parse_review_decision(result)
        
        if decision.action == "ESCALATE" or decision.confidence == "LOW":
            # Pause for human
            return CheckpointDecision(
                action="pause",
                rationale=decision.rationale,
                human_prompt=f"Review Agent escalated: {decision.rationale}"
            )
        else:
            return CheckpointDecision(action="approve", rationale=decision.rationale)
    
    else:
        # Default: pause for human
        return CheckpointDecision(action="pause")
```

### Parallel Execution (Replacing Conductor)

```python
async def run_stage_parallel(
    stage_tasks: list[Task],
    max_parallel: int = 3
) -> list[TaskResult]:
    """Run tasks in parallel using git worktrees (like Conductor)."""
    
    # Create worktrees for each task
    worktrees = []
    for task in stage_tasks:
        wt_path = create_worktree(f"autobuild-{task.id}")
        worktrees.append((task, wt_path))
    
    # Run in parallel with semaphore for resource management
    semaphore = asyncio.Semaphore(max_parallel)
    
    async def run_with_limit(task: Task, worktree: str) -> TaskResult:
        async with semaphore:
            return await run_task_loop(task, worktree)
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*[
        run_with_limit(task, wt) 
        for task, wt in worktrees
    ])
    
    # Merge successful worktrees
    for (task, wt_path), result in zip(worktrees, results):
        if result.success:
            merge_worktree(wt_path, "main")
        cleanup_worktree(wt_path)
    
    return results
```

### Configuration Options

```yaml
# FEATURE.md frontmatter
autobuild:
  mode: parallel              # sequential | parallel | auto
  max_parallel: 3             # Max concurrent tasks
  checkpoint_after: [TASK-002]
  
  # Orchestrator mode settings
  orchestrator:
    enabled: true
    checkpoint_handling: review-agent  # pause | review-agent | auto-approve
    final_merge: human                 # human | auto (safety: always human for now)
    
    # Review agent thresholds
    review_agent:
      auto_approve_complexity_below: 5
      escalate_on_breaking_changes: true
      escalate_on_security_changes: true
```

```toml
# autobuild.toml (global defaults)
[orchestrator]
default_checkpoint_handling = "review-agent"
default_max_parallel = 3
final_merge_requires_human = true  # Safety default

[orchestrator.review_agent]
model = "sonnet"  # Use stronger model for review decisions
auto_approve_complexity_below = 5
escalate_patterns = [
    "security",
    "authentication", 
    "authorization",
    "database migration",
    "breaking change"
]
```

### Execution Modes Comparison

| Mode | Checkpoints | Parallelism | Human Involvement |
|------|-------------|-------------|-------------------|
| **Default** | Pause | Sequential | Every checkpoint |
| **--parallel** | Pause | Yes | Every checkpoint |
| **--orchestrate** | Pause | Yes | Only escalations |
| **--orchestrate --review-agent** | Review Agent | Yes | Only escalations |
| **--orchestrate --auto-approve** | Auto-approve | Yes | Final merge only |

### Safety Guardrails

Even in full orchestrator mode, some things always require human:

```python
ALWAYS_ESCALATE = [
    "production deployment",
    "database migration", 
    "security credential changes",
    "breaking API changes",
    "license changes",
    "dependency major version upgrades",
]

async def should_always_escalate(checkpoint: Checkpoint) -> bool:
    """Some checkpoints ALWAYS need human review."""
    for pattern in ALWAYS_ESCALATE:
        if pattern.lower() in checkpoint.context.lower():
            return True
    return False
```

### What This Enables

```bash
# Morning: Start feature implementation before standup
/autobuild FEAT-dark-mode --orchestrate --review-agent

# Come back to:
# ✅ TASK-001: Create ThemeContext - Completed (3 turns)
# ✅ TASK-002: Add toggle component - Completed (2 turns)  
# ✅ TASK-003: Update components - Completed (5 turns)
# ⏸️ Final merge: Awaiting human approval
#
# Review Agent escalated 0 checkpoints.
# Total time: 45 minutes (vs ~3 hours manual)

# Quick review and merge
/autobuild FEAT-dark-mode --merge
```

---

## Phase B: Knowledge Graph MCP (Week 3-5)

### Goal

Extract shared intelligence layer, informed by Phase A learnings.

### Informed by Phase A

| Phase A Learning | Knowledge Graph MCP Feature |
|------------------|----------------------------|
| What context coach needs | `context_query` for coach job type |
| Effective agent prompts | Agent storage with proven instructions |
| Requirements format | Requirements entity in graph |
| Decision patterns | `decision_log` for learning |
| Failure patterns | Pattern entities to avoid |

### Deliverables

- [ ] Standalone MCP server
- [ ] FalkorDB + SQLite backends
- [ ] Core tools: `context_query`, `agent_search`, `decision_log`, `project_analyze`
- [ ] Claude Code integration (.claude/mcp.json)
- [ ] Docker deployment
- [ ] Migration guide from static CLAUDE.md

**Key change from original plan:** Knowledge Graph MCP design is now informed by real usage data from Phase A, not speculation.

---

## Phase C: AutoBuild (LangGraph) (Week 6-10)

### Goal

Full LangGraph implementation, building on proven foundations.

### Why This is Lower Risk Now

| Risk | Mitigation from Earlier Phases |
|------|-------------------------------|
| Will adversarial cooperation work? | Proven in Phase A |
| What context do agents need? | Validated in Phase A, formalized in Phase B |
| Is Knowledge Graph MCP design right? | Tested with Claude Code users |
| What prompts work for coach/player? | Refined through Phase A iteration |

### Deliverables

- [ ] LangGraph state machine
- [ ] Multi-model provider abstraction
- [ ] Sub-agent routing via Knowledge Graph MCP
- [ ] Full CLI: task, feature, template, agent commands
- [ ] Quality gates
- [ ] Parallel execution

---

## Updated Implementation Timeline

```
Week 1-2:  Phase A - SDK Prototype (/autobuild command)
           └── Proves adversarial cooperation works
           └── Gathers learnings on context, prompts, failure patterns

Week 3-5:  Phase B - Knowledge Graph MCP
           └── Informed by Phase A learnings
           └── Usable immediately with Claude Code
           └── Foundation for AutoBuild

Week 6-10: Phase C - AutoBuild (LangGraph)
           └── Built on proven foundations
           └── Multi-model, sub-agents, full workflow
           └── Production-ready release
```

### Value Delivery Timeline

| Week | Deliverable | Users |
|------|-------------|-------|
| 2 | `/autobuild` command (GuardKit) | Claude Max subscribers |
| 5 | Knowledge Graph MCP | Claude Code users (any) |
| 8 | AutoBuild MVP | All users (API-based) |
| 10 | AutoBuild Production | All users |

---

## Implementation Phases (Detailed)

### Phase 0: Knowledge Graph MCP (Week 1-2) ⭐ NEW

**Goal:** Standalone MCP server that can be used immediately with Claude Code

**Why first?** This provides immediate value to GuardKit users while AutoBuild is being built.

- [ ] MCP server scaffolding (Python + mcp library)
- [ ] FalkorDB client wrapper
- [ ] Knowledge graph schema (entities, relationships)
- [ ] Core MCP tools:
  - [ ] `context_query` - job-specific context retrieval
  - [ ] `agent_get` / `agent_search` - agent routing
  - [ ] `project_analyze` - populate graph from codebase
  - [ ] `decision_log` - store decisions for learning
- [ ] SQLite fallback for simpler setups
- [ ] Docker deployment (local)
- [ ] Integration guide for Claude Code (.claude/mcp.json)

**Deliverable:** `knowledge-graph-mcp` server usable with Claude Code TODAY

```bash
# Install and run
npm install -g knowledge-graph-mcp  # or pip install
knowledge-graph-mcp --db .autobuild/graph.db

# Claude Code can now use it via MCP
```

### Phase 1: AutoBuild Foundation (Week 2-3)

**Goal:** Core CLI infrastructure that consumes Knowledge Graph MCP

**1A: Project Scaffolding (Week 2)**
- [ ] Project scaffolding (pyproject.toml, structure)
- [ ] CLI framework (Typer)
- [ ] Configuration system (autobuild.toml)
- [ ] MCP client for Knowledge Graph

**1B: Project Initialization (Week 3)**
- [ ] `autobuild init` command
- [ ] Calls Knowledge Graph MCP for `project_analyze`
- [ ] Creates .autobuild/ directory structure
- [ ] Default agent/rule file generation

**Deliverable:** `autobuild init` works, backed by Knowledge Graph MCP

### Phase 2: Core Task Workflow (Week 3-4)

**Goal:** Basic task workflow with MCP-backed context

- [ ] LangGraph state schema (AutoBuildState)
- [ ] Context retrieval via MCP (`context_query`)
- [ ] Sub-agent routing via MCP (`agent_search`)
- [ ] Basic nodes: plan → implement → test → review
- [ ] Single model initially
- [ ] SQLite workflow persistence (LangGraph checkpoints)
- [ ] `autobuild task create/work/complete`

**Deliverable:** Working task workflow using Knowledge Graph MCP for context

### Phase 3: Adversarial Cooperation (Week 4-5)

**Goal:** Add coach-player dialectical loop

- [ ] Player agent implementation (uses MCP for context)
- [ ] Coach agent implementation (uses MCP for context)
- [ ] Dialectical loop graph (bounded, max 10 turns)
- [ ] Fresh LLM instance per turn
- [ ] Requirements contract validation
- [ ] Coach-only approval gate
- [ ] Decision logging to MCP (`decision_log`)

**Deliverable:** Coach-player loop achieving higher completion rates

### Phase 4: Multi-Model + Sub-Agents (Week 5-6)

**Goal:** Full model flexibility with intelligent agent routing

**4A: Multi-Model Support**
- [ ] Abstract LLM provider interface
- [ ] Anthropic, Mistral, DeepSeek providers
- [ ] AWS Bedrock, Azure, OpenRouter providers
- [ ] Ollama, vLLM (local) providers
- [ ] Model configuration per role (player/coach)

**4B: Sub-Agent Routing**
- [ ] SubAgentRouter class
- [ ] Model selection by phase (Sonnet for planning, Haiku for implementation)
- [ ] Trigger-based agent matching
- [ ] Agent performance tracking in graph

**Deliverable:** Cost-optimized agent selection (70% savings possible)

### Phase 5: Feature Planning + Templates (Week 6-7)

**Goal:** Higher-level workflows and project analysis

**5A: Feature Planning**
- [ ] `autobuild feature plan` command
- [ ] Subtask decomposition
- [ ] Feature directory structure
- [ ] Sequential subtask execution
- [ ] Feature status tracking

**5B: Template System**
- [ ] `autobuild template create` (extract from codebase)
- [ ] `autobuild template apply` (apply to project)
- [ ] Template storage in Knowledge Graph MCP

**5C: Agent Enhancement**
- [ ] `autobuild agent enhance` (discover/create specialists)
- [ ] Agent storage in Knowledge Graph MCP
- [ ] Agent trigger system (file patterns, keywords)

**Deliverable:** Full feature-plan workflow + template/agent management

### Phase 6: Quality Gates (Week 7-8)

**Goal:** Full quality enforcement

- [ ] Architectural review (SOLID/DRY/YAGNI scoring)
- [ ] Complexity evaluation (1-10 scale)
- [ ] Human checkpoints (LangGraph interrupt)
- [ ] Test enforcement retry loop (max 3)
- [ ] Plan audit (scope creep detection)
- [ ] Coverage threshold enforcement

**Deliverable:** Production-ready quality gates

### Phase 7: Parallel Execution (Week 8+)

**Goal:** Concurrent task implementation

- [ ] Git worktree management
- [ ] Parallel subtask scheduling
- [ ] Dependency-aware ordering
- [ ] Resource management (concurrent LLM calls)
- [ ] Progress tracking across parallel tasks

**Deliverable:** Parallel feature implementation

### Phase 8: Polish + Documentation (Week 9+)

**Goal:** Production readiness

- [ ] Error handling and recovery
- [ ] Comprehensive logging
- [ ] User documentation
- [ ] Example projects
- [ ] Performance optimization
- [ ] `autobuild context show/query/stats` debugging tools
- [ ] Knowledge Graph MCP cloud deployment option

**Deliverable:** Production-ready release

---

## Product Suite Overview

After all phases, the product suite consists of:

| Product | Type | Users | Purpose |
|---------|------|-------|---------|
| **Knowledge Graph MCP** | Standalone MCP server | Claude Code, AutoBuild, any MCP client | Shared brain, context, agents |
| **AutoBuild CLI** | Python CLI | Developers | LangGraph-based autonomous dev |
| **GuardKit** (existing) | Claude Code extension | Claude Max subscribers | Markdown-based slash commands |

**Key insight:** Knowledge Graph MCP is the **foundation** that enables both tools to share intelligence.

---

## Success Metrics

### From Block AI Research (g3 benchmarks)

| Metric | Target | Rationale |
|--------|--------|-----------|
| Completeness | 5/5 | g3 achieved 5/5 vs 1-4.5/5 for single-agent |
| Autonomous turns | 30-60 min | vs ~5 min for vibe coding |
| Human intervention | Minimal | Design checkpoint + final approval only |
| Test pass rate | 100% | Quality gate enforcement |

### Cost Efficiency

| Model | Target Cost | Comparison |
|-------|-------------|------------|
| Claude | Baseline | Current cost |
| Devstral 2 | 7x cheaper | Per Mistral benchmarks |
| Local Devstral | $0/month | Self-hosted |

---

## References

### Primary Sources

- Block AI Research: "Adversarial Cooperation in Code Synthesis" (Dec 8, 2025)
- g3 Implementation: https://github.com/dhanji/g3
- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- Devstral 2: https://mistral.ai/news/devstral-2-vibe-cli

### Knowledge Graph

- Graphiti: https://github.com/getzep/graphiti (temporal knowledge graph)
- FalkorDB: https://www.falkordb.com/ (graph database)
- Kris Wong (ClosedLoop): "Optimizing context for specific jobs at specific moments"

### GuardKit Research (in project knowledge)

- LangGraph-Native Orchestration for TaskWright
- Clarifying Questions and Workflow Automation Research
- Claude Agent SDK Integration Analysis
- AI-Agent Memory Systems Integration Research

---

## Key Design Decision: Job-Specific Context

Based on feedback from Kris Wong (ClosedLoop) who runs 59 agents and 22 commands:

> "Just giving the LLM all the context for everything in every prompt isn't super effective in my experience. We are focused on optimizing context for specific jobs at specific moments."

This insight drives AutoBuild's knowledge graph approach:
- **Store comprehensively** in the graph (builds on GuardKit's file structure)
- **Retrieve selectively** based on current job
- **Target <2000 tokens** per job context
- **Enhance GuardKit's progressive disclosure** with queryable metadata and learning

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-19 | Research session | Initial specification: GuardKit workflow + adversarial cooperation |
| 2025-12-20 | Research session | Added: Knowledge graph, job-specific context, project analysis commands (init, template, agent enhance) |
| 2025-12-20 | Research session | Added: Deployment options (solo/team/enterprise), authentication & security (API keys, RBAC, SSO/OIDC, audit logging) |
| 2025-12-20 | Research session | Added: Comprehensive LLM configuration (Anthropic, Mistral, AWS Bedrock, Azure, OpenAI, OpenRouter, DeepSeek, Ollama, vLLM), Claude Code subscription limitation clarification, cost comparison, budget controls |
| 2025-12-20 | Research session | Added: Knowledge Graph MCP as standalone server (shared brain for Claude Code + AutoBuild), sub-agent architecture with model-per-phase, agent routing in LangGraph, hybrid storage (metadata in graph, instructions in files), cost optimization examples |
| 2025-12-20 | Research session | Added: Orchestrator Mode (--orchestrate flag) to automate human role, Review Agent for intelligent checkpoint handling, parallel execution replacing Conductor, safety guardrails for always-escalate patterns |
| 2025-12-20 | Research session | Corrected: GuardKit architecture description - already uses progressive disclosure (core/ext splits, frontmatter with model selection, distributed rules), NOT monolithic. AutoBuild ENHANCES this with queryable metadata layer, not replaces it |
| 2025-12-20 | Research session | Enhanced: Job-specific context documentation - clarified key difference is load-time (GuardKit) vs job-time (AutoBuild) context assembly. Added concrete examples showing context differences per job type (player implementation, coach validation, etc.). Updated comparison tables to reflect actual GuardKit capabilities |
| 2025-12-20 | Research session | Added: Testing Strategy for Hybrid Architecture - documented why BDD is wrong tool for Claude Code + Python integration (bugs are in wiring, not logic). Added integration smoke tests, agent contract tests, trace-based validation, and golden path testing approaches. Includes testing pyramid and practical guidance |
