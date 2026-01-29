# Graphiti Integration Guide

> **What is Graphiti Integration?**
>
> Graphiti is a temporal knowledge graph that gives GuardKit persistent memory across Claude Code sessions. It enables the system to remember architectural decisions, learn from past mistakes, and maintain consistent context - preventing the "stochastic development" problem where each session starts fresh and may repeat the same errors.

---

## Table of Contents

- [The Problem It Solves](#the-problem-it-solves)
- [Quick Start (5-Minute Setup)](#quick-start-5-minute-setup)
- [Core Concepts](#core-concepts)
- [Using Graphiti with GuardKit Commands](#using-graphiti-with-guardkit-commands)
- [Configuration](#configuration)
- [FAQ](#faq)
- [See Also](#see-also)

---

## The Problem It Solves

Without persistent memory, Claude Code sessions face a fundamental challenge: **every session starts fresh**.

### The Pattern of Repeated Mistakes

```
Session 1: Makes architecture decision A
    ↓
Session 2: Doesn't know about A, makes conflicting decision B
    ↓
Session 3: Finds inconsistency, "fixes" by breaking Session 1's work
    ↓
Session 4: Discovers breakage, doesn't understand why A was chosen
    ↓
[Repeat until human intervention]
```

### Real-World Consequences

Analysis of GuardKit's `/feature-build` command development revealed these recurring issues:

| Issue | Root Cause | Impact |
|-------|------------|--------|
| **Sessions losing context** | No memory of what GuardKit is | System identity forgotten between sessions |
| **Repeated mistakes** | Failed approaches not remembered | Same bugs recreated multiple times |
| **Forgotten decisions** | Architecture choices not tracked | Inconsistent implementations |
| **Scope creep** | Quality gates bypassed | Mock data instead of real integration |

### What Graphiti Prevents

**Before Graphiti:**
- TaskWorkInterface returns mock data (complexity=5, arch_score=80)
- Next session doesn't know it's a stub
- Implementation plan never created
- Player fails because plan doesn't exist

**With Graphiti:**
```
Pre-session context includes:
- Component Status: "TaskWorkInterface.execute_design_phase() is STUB"
- Architecture Decision: "Must invoke /task-work --design-only to generate plan"
- Failure Pattern: "Player fails when pre-loop uses stub data"

Result: Claude knows to implement real SDK integration
```

---

## Quick Start (5-Minute Setup)

### Prerequisites

✅ **Required:**
- Docker Desktop (or Docker Engine + Compose)
- OpenAI API key (for embeddings)
- Python 3.10+
- GuardKit installed

✅ **Recommended:**
- 4GB RAM minimum for FalkorDB
- SSD storage for better graph performance

### Setup Steps

#### 1. Start Graphiti Services

```bash
cd path/to/guardkit
docker compose -f docker/docker-compose.graphiti.yml up -d
```

This starts:
- **FalkorDB**: Graph database (port 6379)
- **Graphiti API**: Query interface (port 8000)

#### 2. Set OpenAI API Key

```bash
export OPENAI_API_KEY=sk-your-key-here
```

> **Note**: Embeddings are cheap - expect <$1/month for typical usage with `text-embedding-3-small`.

#### 3. Seed GuardKit Knowledge

```bash
guardkit graphiti seed
```

This seeds ~67 episodes across 13 knowledge categories:
- `product_knowledge` - What GuardKit is
- `command_workflows` - How commands work together
- `quality_gate_phases` - The 5-phase structure
- `architecture_decisions` - Critical design choices
- `failure_patterns` - What NOT to do
- And 8 more categories...

#### 4. Verify Setup

```bash
guardkit graphiti verify
```

Expected output:
```
✓ What is GuardKit?
✓ How to invoke task-work?
✓ What are the quality phases?
✓ What is the Player-Coach pattern?
✓ How to use SDK vs subprocess?

Results: 5 passed, 0 failed
Verification complete!
```

**Done!** Graphiti is now providing persistent memory to your GuardKit sessions.

---

## Core Concepts

### Knowledge Categories

Graphiti organizes knowledge into semantic groups called **group IDs**:

| Category | What It Contains | Example Content |
|----------|------------------|-----------------|
| **product_knowledge** | GuardKit's identity and philosophy | "Lightweight task workflow with quality gates" |
| **command_workflows** | How commands flow together | "/task-work → Phase 2 → Architectural Review → Phase 3" |
| **quality_gate_phases** | The 5-phase structure details | "Phase 4.5: Auto-fix tests up to 3 attempts" |
| **technology_stack** | Python, Claude Code, SDK | "Use SDK query() not subprocess to CLI" |
| **feature_build_architecture** | Player-Coach workflow | "Player implements, Coach validates, max 5 turns" |
| **architecture_decisions** | ADRs from sessions | "ADR-FB-001: SDK query() for task-work invocation" |
| **failure_patterns** | What NOT to do | "Path construction with task ID fails in feature mode" |
| **component_status** | Implementation status | "TaskWorkInterface.execute_design_phase() is stub" |
| **integration_points** | How components connect | "autobuild → task-work uses sdk_query protocol" |
| **task_outcomes** | What worked/didn't | "TASK-1234: OAuth2 implementation succeeded" |
| **templates** | Template metadata | "react-typescript uses Vite + Vitest + Playwright" |
| **agents** | Agent capabilities | "architectural-reviewer scores SOLID/DRY/YAGNI" |
| **patterns** | Design patterns | "Repository pattern for data access" |

### How Context Loading Works

When you run GuardKit commands, the system follows this flow:

```
┌──────────────────────────────────────────────────────────────┐
│ 1. Command Invoked: /task-work TASK-XXX                      │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. Load Critical Context from Graphiti                       │
│    - Query: "guardkit task workflow phases"                  │
│    - Group IDs: product_knowledge, command_workflows         │
│    - Results: Top 10 relevant episodes                       │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. Format for Session Injection                              │
│    === SYSTEM CONTEXT ===                                    │
│    GuardKit is a lightweight task workflow system...         │
│    /task-work executes Phases 2-5.5 automatically...         │
│    WARNING: TaskWorkInterface.execute_design_phase is stub   │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. Claude Receives Context + Task                            │
│    - Knows what GuardKit is                                  │
│    - Knows how task-work flows                               │
│    - Knows what to avoid                                     │
└──────────────────────────────────────────────────────────────┘
```

**Key Benefits:**
- ✅ Consistent understanding of GuardKit's identity
- ✅ Awareness of past failures to avoid
- ✅ Knowledge of correct integration patterns
- ✅ Context about incomplete implementations

### ADR Lifecycle

Architecture Decision Records (ADRs) are captured automatically:

```
┌─────────────────────────────────────────────────────────┐
│ Trigger Events:                                          │
│ 1. Clarifying questions answered (significant decisions) │
│ 2. Code analysis discovers patterns (/template-create)  │
│ 3. Manual seeding (guardkit graphiti seed-adrs)         │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ ADR Created with:                                        │
│ - Title: "Use SDK query() not subprocess"               │
│ - Rationale: "CLI command doesn't exist"                │
│ - Alternatives rejected: "subprocess to guardkit CLI"   │
│ - Status: ACCEPTED                                       │
│ - Group ID: architecture_decisions                      │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Queryable in Future Sessions:                            │
│ - "How should I invoke task-work?"                       │
│ - → Returns: "Use SDK query(), not subprocess"          │
└─────────────────────────────────────────────────────────┘
```

**Example ADRs:**
- **ADR-FB-001**: Use SDK `query()` for task-work invocation (not subprocess)
- **ADR-FB-002**: Use FEAT-XXX paths in feature mode (not TASK-XXX)
- **ADR-FB-003**: Pre-loop must invoke real `/task-work --design-only`

---

## Using Graphiti with GuardKit Commands

### `/task-work` Integration

Context is **automatically loaded** before Phase 2 planning:

**What Gets Loaded:**
```python
context = await load_critical_context(command="task-work")

# Returns:
# - Product knowledge (what GuardKit is)
# - Command workflow (how phases flow)
# - Quality gate phases (what to expect)
# - Relevant architecture decisions
# - Failure patterns to avoid
```

**When It Helps:**
- ✅ Phase 2: Planning with knowledge of system architecture
- ✅ Phase 2.5: Architectural review against known patterns
- ✅ Phase 3: Implementation following established decisions
- ✅ Phase 4: Testing with awareness of common pitfalls

### `/feature-build` Integration

The Player-Coach workflow benefits from **feature-specific context**:

**Pre-Loop Context:**
```python
context = await pre_feature_build_context(feature_id="FEAT-AUTH-001")

# Returns:
# - Feature-build architecture (Player-Coach pattern)
# - Previous attempts on this feature
# - Similar feature patterns
# - Integration points (autobuild → task-work)
# - Component status (stubs vs implemented)
```

**During Execution:**
- **Player** receives:
  - Architecture decisions (SDK not subprocess)
  - Integration patterns (how to invoke task-work)
  - Failure patterns (what to avoid)

- **Coach** validates against:
  - Known architectural patterns
  - Quality gate requirements
  - Component implementation status

**Post-Execution:**
```python
await capture_feature_outcome(
    feature_id="FEAT-AUTH-001",
    success=True,
    summary="OAuth2 implemented with SDK integration"
)

# Future sessions will know:
# - OAuth2 was successfully implemented
# - SDK integration pattern worked
# - This approach is validated
```

### `/template-create` Integration

Template creation **automatically seeds** template knowledge:

```bash
/template-create --source=./my-app --name=my-template
```

**What Gets Seeded:**
- Template metadata (name, stack, patterns)
- Agent capabilities discovered
- Technology stack information
- Pattern usage (repository, service, controller)

**Query Later:**
```
"What templates support FastAPI?"
→ Returns: "my-template uses FastAPI with async patterns"

"How does my-template handle authentication?"
→ Returns: "Uses OAuth2 with JWT tokens (from agent analysis)"
```

---

## Configuration

### Configuration File

Create or modify `.guardkit/graphiti.yaml`:

```yaml
# Enable/disable Graphiti integration
enabled: true

# Graphiti server connection settings
host: localhost
port: 8000
timeout: 30.0

# OpenAI embedding model for semantic search
# Requires OPENAI_API_KEY environment variable
embedding_model: text-embedding-3-small

# Group IDs for organizing knowledge
# These create separate namespaces in the knowledge graph
group_ids:
  - product_knowledge      # Domain concepts, entities, relationships
  - command_workflows      # GuardKit command patterns and usage
  - architecture_decisions # ADRs and design rationale
```

### Environment Variable Overrides

You can override any setting via environment variables:

```bash
# Enable/disable integration
export GRAPHITI_ENABLED=true

# Connection settings
export GRAPHITI_HOST=localhost
export GRAPHITI_PORT=8000
export GRAPHITI_TIMEOUT=30.0

# Required for embeddings
export OPENAI_API_KEY=sk-your-key-here
```

### Disabling Graphiti

To disable Graphiti (commands will work without persistent memory):

**Option 1: Configuration file**
```yaml
enabled: false
```

**Option 2: Environment variable**
```bash
export GRAPHITI_ENABLED=false
```

**Option 3: Stop Docker services**
```bash
docker compose -f docker/docker-compose.graphiti.yml down
```

---

## FAQ

### Do I need Graphiti to use GuardKit?

**No.** GuardKit works perfectly fine without Graphiti. All commands will function normally.

Graphiti is an **enhancement** for:
- Better cross-session context retention
- Learning from past mistakes
- Consistent architectural decisions
- Persistent memory of what GuardKit is

**Graceful Degradation:** If Graphiti is unavailable (Docker not running, connection failed, disabled in config), GuardKit will:
- Continue functioning normally
- Fall back to training data and CLAUDE.md for context
- Skip context loading and outcome capture
- Log warnings but not fail

### What if Docker isn't available?

GuardKit **gracefully degrades** when Graphiti services are unavailable:

```
$ guardkit graphiti status
Connection: Failed

# All commands still work:
$ /task-work TASK-001        # ✓ Works (without persistent memory)
$ /feature-build FEAT-002    # ✓ Works (without session context)
$ /template-create           # ✓ Works (without template seeding)
```

**Impact:**
- ❌ No persistent memory across sessions
- ❌ No automatic ADR capture
- ❌ No failure pattern learning
- ✅ All core functionality works
- ✅ Quality gates still enforced
- ✅ Commands execute normally

### How much does OpenAI API cost?

**Very little.** Graphiti uses `text-embedding-3-small` which is extremely affordable:

**Pricing (as of 2025):**
- $0.02 per 1M tokens
- Typical usage: ~100K tokens/month
- **Cost: <$1/month**

**What uses embeddings:**
- Initial seeding: ~67 episodes (~50K tokens)
- Query searches: ~100-500 tokens per query
- Outcome capture: ~200-300 tokens per task

**Cost-saving tips:**
- Seed once, query many times (free)
- Verification queries are lightweight
- Disable if not using: `enabled: false`

### What gets seeded during `guardkit graphiti seed`?

**System Context Seeding** seeds 13 knowledge categories with ~67 episodes:

| Category | Episodes | Content |
|----------|----------|---------|
| product_knowledge | ~5 | GuardKit overview, philosophy, quality-first approach |
| command_workflows | ~8 | /task-work, /feature-build, /template-create flows |
| quality_gate_phases | ~6 | Phase 2-5.5 details, thresholds, gates |
| technology_stack | ~4 | Python, Claude Code, SDK, async patterns |
| feature_build_architecture | ~5 | Player-Coach, worktrees, delegation |
| templates | ~10 | Template metadata for 5 core templates |
| agents | ~12 | Agent capabilities (architectural-reviewer, etc.) |
| patterns | ~6 | Design patterns (repository, service, etc.) |
| rules | ~5 | Code style, testing, architecture rules |
| architecture_decisions | ~3 | Initial ADRs (SDK vs subprocess, etc.) |
| failure_patterns | ~3 | Known failures and fixes |
| component_status | 0 | Populated during development |
| task_outcomes | 0 | Populated as tasks complete |

**Feature-Build ADRs** (via `guardkit graphiti seed-adrs`):
- ADR-FB-001: Use SDK query() for task-work invocation
- ADR-FB-002: Use FEAT-XXX paths in feature mode
- ADR-FB-003: Pre-loop must invoke real task-work

### Can I query Graphiti directly?

**Yes!** Use the Python API:

```python
from guardkit.knowledge import get_graphiti

client = get_graphiti()

# Search across categories
results = await client.search(
    query="authentication patterns",
    group_ids=["architecture_decisions", "patterns"],
    num_results=5
)

for result in results:
    print(f"{result['name']}: {result['score']:.2f}")
```

**CLI Verification:**
```bash
guardkit graphiti verify --verbose
```

### How do I troubleshoot connection issues?

**1. Check Docker containers:**
```bash
docker ps | grep graphiti

# Should show:
# guardkit-graphiti-1   (port 8000)
# guardkit-falkordb-1   (port 6379)
```

**2. View logs:**
```bash
docker logs guardkit-graphiti-1
```

**3. Restart services:**
```bash
docker compose -f docker/docker-compose.graphiti.yml restart
```

**4. Check status:**
```bash
guardkit graphiti status

# Should show:
# Connection: OK
# Health: OK
# Seeded: Yes
```

**5. Test queries:**
```bash
guardkit graphiti verify --verbose
```

### Can I re-seed if knowledge becomes stale?

**Yes!** Use the `--force` flag:

```bash
# Re-seed all system context
guardkit graphiti seed --force

# Re-seed feature-build ADRs
guardkit graphiti seed-adrs --force
```

**When to re-seed:**
- After major GuardKit version updates
- If new knowledge categories added
- If seeding failed partially
- If you want to reset to clean state

**Note:** Re-seeding does NOT delete task outcomes or custom ADRs captured during development. It only updates the **system context** categories.

---

## See Also

- [Graphiti Setup Guide](../setup/graphiti-setup.md) - Detailed installation and configuration
- [Graphiti Architecture](../architecture/graphiti-architecture.md) - Technical deep-dive for developers
- [GuardKit Workflow](guardkit-workflow.md) - How Graphiti integrates with the workflow
- [Feature-Build Workflow](autobuild-workflow.md) - Player-Coach pattern with persistent memory

---

## Summary

**Graphiti Integration provides:**
- ✅ Persistent memory across Claude Code sessions
- ✅ Automatic capture of architecture decisions
- ✅ Learning from past mistakes
- ✅ Consistent system context

**Key Commands:**
```bash
# Setup
docker compose -f docker/docker-compose.graphiti.yml up -d
export OPENAI_API_KEY=sk-your-key-here
guardkit graphiti seed

# Verify
guardkit graphiti status
guardkit graphiti verify

# Manage
guardkit graphiti seed-adrs          # Seed feature-build ADRs
guardkit graphiti seed --force       # Re-seed system context
```

**Remember:**
- Graphiti is **optional** - GuardKit works fine without it
- Graceful degradation ensures **zero disruption**
- Cost is **minimal** (<$1/month for embeddings)
- Setup takes **<5 minutes**

**Next Steps:**
1. Follow [Quick Start](#quick-start-5-minute-setup) to enable Graphiti
2. Run `guardkit graphiti verify` to test
3. Use GuardKit commands as normal - context is automatic
4. See [Setup Guide](../setup/graphiti-setup.md) for advanced configuration
