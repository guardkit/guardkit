# Graphiti Integration Guide

> **What is Graphiti Integration?**
>
> Graphiti is a temporal knowledge graph that gives GuardKit persistent memory across Claude Code sessions. It enables the system to remember architectural decisions, learn from past mistakes, and maintain consistent context - preventing the "stochastic development" problem where each session starts fresh and may repeat the same errors.

---

## Table of Contents

- [The Problem It Solves](#the-problem-it-solves)
- [Quick Start (5-Minute Setup)](#quick-start-5-minute-setup)
- [Init Seeding Workflow](#init-seeding-workflow)
- [What's New in Phase 2](#whats-new-in-phase-2)
- [Core Concepts](#core-concepts)
- [Using Graphiti with GuardKit Commands](#using-graphiti-with-guardkit-commands)
- [Configuration](#configuration)
- [FAQ](#faq)
- [Multi-Project Support](#multi-project-support-project-namespaces)
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

This seeds episodes across 18 knowledge categories:
- `product_knowledge` - What GuardKit is
- `command_workflows` - How commands work together
- `quality_gate_phases` - The 5-phase structure
- `architecture_decisions` - Critical design choices
- `failure_patterns` - What NOT to do
- And 13 more categories (templates, agents, patterns, rules, project overview, etc.)

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

## Init Seeding Workflow

When you run `guardkit init`, project knowledge is **automatically seeded to Graphiti** by default. This ensures your project context is immediately available for AI-assisted development.

### What Gets Seeded

The init command seeds four knowledge components:

| Component | Group ID | Description |
|-----------|----------|-------------|
| **Project Overview** | `project_overview` | Parsed from CLAUDE.md or README.md - project purpose, tech stack, key goals |
| **Role Constraints** | `role_constraints` | Player/Coach behavior boundaries - what AI should ask about before implementing |
| **Quality Gate Configs** | `quality_gate_configs` | Test coverage thresholds, architectural review scores |
| **Implementation Modes** | `implementation_modes` | Guidance on when to use task-work vs direct implementation |

### CLI Options

```bash
# Standard init (seeds to Graphiti by default)
guardkit init fastapi-python

# Interactive mode - prompts for project information
guardkit init --interactive
guardkit init fastapi-python -i

# Skip Graphiti seeding (faster initialization)
guardkit init --skip-graphiti

# Custom project name (overrides directory name)
guardkit init -n my-custom-project-name
guardkit init fastapi-python --project-name my-app

# Combined options
guardkit init react-typescript -i -n frontend-app
```

### Interactive Setup

Interactive mode (`-i` or `--interactive`) prompts you for project information:

```
$ guardkit init --interactive

What is the purpose of this project?
> An e-commerce API for processing orders and payments

What is the primary programming language?
> python

What frameworks are you using? (comma-separated)
> FastAPI, SQLAlchemy, Celery

Enter key goals (empty line to finish):
Goal: High availability (99.9% uptime)
Goal: Sub-100ms response times
Goal: PCI compliance for payment processing
Goal:

Save this information to CLAUDE.md? [Y/n]
```

The captured information is:
1. Saved to CLAUDE.md (if approved)
2. Seeded directly to Graphiti as a `ProjectOverviewEpisode`

### Refining Project Knowledge

After initial seeding, you may need to refine or update your project knowledge. Three methods are available:

#### Method 1: Interactive Knowledge Capture (Recommended)

The most comprehensive refinement method - captures all knowledge categories through guided Q&A:

```bash
# Full interactive session (all categories)
guardkit graphiti capture --interactive

# Focus on specific categories
guardkit graphiti capture --interactive --focus project-overview
guardkit graphiti capture --interactive --focus role-customization
guardkit graphiti capture --interactive --focus quality-gates
guardkit graphiti capture --interactive --focus workflow-preferences
```

**See**: [Interactive Knowledge Capture Guide](graphiti-knowledge-capture.md) for detailed usage.

#### Method 2: Add Context from Documents

Re-parse and seed from an updated CLAUDE.md or other documentation:

```bash
# Re-seed from updated CLAUDE.md
guardkit graphiti add-context CLAUDE.md --force

# Add context from other documentation
guardkit graphiti add-context docs/architecture.md

# Capture full document content (any markdown file)
guardkit graphiti add-context docs/research/notes.md --type full_doc
```

Five parser types are available: `adr`, `feature-spec`, `project_overview`, `project_doc`, and `full_doc`. The first four are auto-detected from filename and content; `full_doc` must be specified explicitly with `--type full_doc`.

**See**: [Add Context Guide](graphiti-add-context.md) for detailed usage and [Parsers Guide](graphiti-parsers.md) for parser detection rules.

#### Method 3: Re-run Interactive Init

Run interactive init again to update project overview:

```bash
# Re-run interactive setup
guardkit init --interactive
```

This will prompt for project information again and update the Graphiti knowledge.

### Refinement Method Comparison

| Method | Project Overview | Role Constraints | Quality Gates | Implementation Modes |
|--------|------------------|------------------|---------------|---------------------|
| **Interactive Capture** | ✅ All categories | ✅ `--focus role-customization` | ✅ `--focus quality-gates` | ✅ `--focus workflow-preferences` |
| **Add Context** | ✅ Re-parses doc | ❌ Not affected | ❌ Not affected | ❌ Not affected |
| **Interactive Init** | ✅ Prompts again | ❌ Not affected | ❌ Not affected | ❌ Not affected |

**Recommendation**: Use `guardkit graphiti capture --interactive` for the most comprehensive refinement, especially when you need to update role constraints, quality gates, or workflow preferences.

### Seeding Output

When init runs with Graphiti enabled, you'll see output like:

```
Initializing GuardKit in /path/to/project
  Project: my-project
  Template: fastapi-python

Step 1: Applying template...
  Applied template: fastapi-python

Step 2: Seeding project knowledge to Graphiti...
  Project knowledge seeded successfully
    OK project_overview: Seeded from CLAUDE.md
    OK role_constraints: Seeded Player and Coach constraints
    OK quality_gate_configs: Seeded quality gate configurations
    OK implementation_modes: Seeded 2 modes

GuardKit initialized successfully!
```

### Graceful Degradation

If Graphiti is unavailable (Docker not running, connection failed, or disabled), init continues normally:

```
Step 2: Seeding project knowledge to Graphiti...
  Warning: Graphiti unavailable, skipping seeding
```

All core GuardKit functionality works without Graphiti - it's an enhancement, not a requirement.

### Best Practices

1. **Run interactive init for new projects** - Capture rich project context from the start:
   ```bash
   guardkit init fastapi-python --interactive
   ```

2. **Update after major changes** - When architecture or goals change significantly:
   ```bash
   guardkit graphiti capture --interactive --focus architecture
   ```

3. **Set role constraints early** - Before running AutoBuild workflows:
   ```bash
   guardkit graphiti capture --interactive --focus role-customization
   ```

4. **Verify seeding worked** - Check Graphiti status:
   ```bash
   guardkit graphiti status
   guardkit graphiti search "project overview"
   ```

---

## What's New in Phase 2

Phase 2 of Graphiti integration brings powerful new capabilities for knowledge management and context-aware development:

### Interactive Knowledge Capture

Capture project knowledge through guided Q&A sessions:

```bash
# Start interactive knowledge capture
guardkit graphiti capture --interactive

# Focus on specific category
guardkit graphiti capture --interactive --focus architecture
guardkit graphiti capture --interactive --focus role-customization
```

**Focus Categories:**
- **Project knowledge**: project-overview, architecture, domain, constraints, decisions, goals
- **AutoBuild customization**: role-customization, quality-gates, workflow-preferences

**See**: [Interactive Knowledge Capture Guide](graphiti-knowledge-capture.md)

### Knowledge Query Commands

Query and inspect stored knowledge:

```bash
# Show specific knowledge
guardkit graphiti show FEAT-SKEL-001

# Search for knowledge
guardkit graphiti search "authentication patterns" --group patterns

# List all in category
guardkit graphiti list features
```

**See**: [Knowledge Query Commands Guide](graphiti-query-commands.md)

### Job-Specific Context Retrieval

Each task receives precisely the knowledge it needs based on:
- **Task complexity** (simple: 2000 tokens, complex: 6000 tokens)
- **Task type** (first-of-type gets +30% budget)
- **Context phase** (planning vs implementation)
- **AutoBuild mode** (role constraints, quality gates, turn history)

**Context Categories:**
- Feature context, similar outcomes, relevant patterns
- Architecture context, warnings, domain knowledge
- AutoBuild: role constraints, quality gate configs, previous turn states

**See**: [Job-Specific Context Retrieval Guide](graphiti-job-context.md)

### Turn State Tracking

AutoBuild captures turn states for cross-turn learning:

```bash
# Query turn history
guardkit graphiti search "turn FEAT-XXX" --group turn_states
```

**Captured per turn:**
- Player decisions and Coach feedback
- Files modified, blockers encountered
- Acceptance criteria status
- Mode (FRESH_START, RECOVERING_STATE, CONTINUING_WORK)

**See**: [Turn State Tracking Guide](graphiti-turn-states.md)

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
| **turn_states** | AutoBuild turn history | "Turn 3: Player implemented OAuth, Coach approved" |

### Job-Specific Context (Phase 2)

Rather than loading all knowledge or none, GuardKit now dynamically retrieves **job-specific context** based on task characteristics:

| Factor | Impact |
|--------|--------|
| **Complexity** | Simple (2K tokens) → Complex (6K tokens) |
| **Task type** | First-of-type gets +30% budget for exploration |
| **Refinement** | Failed attempts get +20% for warnings/patterns |
| **AutoBuild** | Includes role constraints, turn history, quality gates |

**See**: [Job-Specific Context Retrieval](graphiti-job-context.md)

### Interactive Capture (Phase 2)

Project knowledge is captured through guided Q&A sessions:

```bash
guardkit graphiti capture --interactive --focus architecture
```

This captures implicit knowledge (decisions, constraints, goals) and persists it for future sessions.

**See**: [Interactive Knowledge Capture](graphiti-knowledge-capture.md)

### Turn States for AutoBuild (Phase 2)

Each `/feature-build` turn is tracked, enabling cross-turn learning:

- Turn N+1 knows what Turn N learned
- Coach feedback persisted across sessions
- Prevents repeated mistakes

**See**: [Turn State Tracking](graphiti-turn-states.md)

### How Context Loading Works

When you run GuardKit commands, the system uses **job-specific context retrieval**:

```
┌──────────────────────────────────────────────────────────────┐
│ 1. Command Invoked: /task-work TASK-XXX                      │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. Analyze Task Characteristics                              │
│    - Complexity: 6 (medium)                                  │
│    - Type: first-of-type? No                                 │
│    - Refinement? No                                          │
│    - AutoBuild? No                                           │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. Calculate Context Budget                                  │
│    Base: 4000 tokens (medium complexity)                     │
│    Adjustments: None                                         │
│    Final: 4000 tokens                                        │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. Query Graphiti (concurrent, filtered by relevance)        │
│    ├─ Similar outcomes (30%): 3 results, 0.72 avg relevance  │
│    ├─ Relevant patterns (25%): 2 results, 0.81 avg relevance │
│    ├─ Architecture (20%): 2 results, 0.75 avg relevance      │
│    ├─ Warnings (15%): 1 result, 0.68 relevance               │
│    └─ Domain (10%): 1 result, 0.70 relevance                 │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. Format and Inject Context                                 │
│    [INFO] Retrieved job-specific context (3850/4000 tokens)  │
│                                                              │
│    === SYSTEM CONTEXT ===                                    │
│    Similar tasks succeeded with: Repository pattern...       │
│    Relevant patterns: Clean Architecture layers...           │
│    WARNING: Avoid direct DB access in handlers               │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ 6. Claude Receives Precisely Relevant Context                │
│    ✓ Knows what worked before on similar tasks               │
│    ✓ Knows patterns that apply to this work                  │
│    ✓ Knows what approaches to avoid                          │
│    ✓ Has domain context without token waste                  │
└──────────────────────────────────────────────────────────────┘
```

**Key Benefits:**
- ✅ **Precision**: Context matched to task characteristics
- ✅ **Efficiency**: Budget respected, no wasted tokens
- ✅ **Learning**: Past successes and failures inform current work
- ✅ **Transparency**: Context retrieval logged for debugging

**See**: [Job-Specific Context Retrieval](graphiti-job-context.md) for budget details and tuning

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

Job-specific context is **automatically loaded** before Phase 2 planning:

**What Gets Loaded (Phase 2):**
```python
context = await get_job_specific_context(
    task_id="TASK-XXX",
    complexity=task.complexity,
    is_first_of_type=is_first_of_type(task),
    is_refinement=is_refinement(task)
)

# Returns (budget-aware, relevance-filtered):
# - Similar outcomes: What worked on similar tasks
# - Relevant patterns: Codebase patterns that apply
# - Architecture: How this fits into the system
# - Warnings: Approaches to avoid
# - Domain knowledge: Domain-specific context
```

**When It Helps:**
- ✅ Phase 2: Planning with similar task insights
- ✅ Phase 2.5: Architectural review against known patterns
- ✅ Phase 3: Implementation following validated approaches
- ✅ Phase 4: Testing aware of common pitfalls

### `/feature-plan` Integration (Phase 2)

Feature planning now queries Graphiti for enriched context:

```bash
/feature-plan "implement dark mode"

# System automatically:
# ✅ Auto-detects feature spec (if FEAT-XXX in description)
# ✅ Queries Graphiti for enriched context:
#    - Related features
#    - Relevant patterns
#    - Role constraints (Player/Coach boundaries)
#    - Quality gate configs
```

**Context Loading:**
- **Auto-detection**: Searches `docs/features/` for matching FEAT-XXX specs
- **Graphiti queries**: Related features, patterns, AutoBuild constraints
- **Budget-aware**: Smart token allocation for optimal context

### `/feature-build` Integration

The Player-Coach workflow benefits from **job-specific and turn state context**:

**Pre-Loop Context:**
```python
context = await get_job_specific_context(
    task_id="TASK-AUTH-001",
    is_autobuild=True,
    turn_number=1
)

# AutoBuild-specific context:
# - Role constraints: What Player should ask about, what Coach escalates
# - Quality gate configs: Coverage thresholds, arch review scores
# - Implementation modes: Direct vs task-work guidance
```

**Turn State Tracking (Phase 2):**

Each turn captures state for cross-turn learning:

```python
await capture_turn_state(
    feature_id="FEAT-AUTH-001",
    task_id="TASK-AUTH-001",
    turn_number=2,
    player_decision="Implemented OAuth2 token refresh",
    coach_decision="APPROVED",
    files_modified=["src/auth/oauth.py", "tests/test_oauth.py"],
    blockers_found=[],
    acceptance_criteria_status={"token_refresh": "verified"}
)
```

**Turn N+1 receives:**
- Previous turn context (what was implemented)
- Coach feedback history (what was rejected and why)
- Blockers encountered (to avoid repeating)
- Progress against acceptance criteria

**See**: [Turn State Tracking Guide](graphiti-turn-states.md)

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

### Query Commands (Phase 2)

New CLI commands for querying and inspecting stored knowledge:

```bash
# Show specific knowledge by ID
guardkit graphiti show FEAT-SKEL-001    # Feature spec
guardkit graphiti show ADR-001          # Architecture decision

# Search for knowledge
guardkit graphiti search "authentication patterns"
guardkit graphiti search "error handling" --group patterns --limit 20

# List all knowledge in a category
guardkit graphiti list features
guardkit graphiti list adrs
guardkit graphiti list patterns

# View knowledge graph status
guardkit graphiti status
guardkit graphiti status --verbose
```

**Use Cases:**
- ✅ Verify knowledge was captured correctly
- ✅ Debug context loading issues
- ✅ Explore stored patterns and decisions
- ✅ Audit knowledge graph health

**See**: [Knowledge Query Commands Guide](graphiti-query-commands.md)

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

**System Context Seeding** seeds 18 knowledge categories:

| Category | Episodes | Content |
|----------|----------|---------|
| product_knowledge | ~5 | GuardKit overview, philosophy, quality-first approach |
| command_workflows | ~8 | /task-work, /feature-build, /template-create flows |
| quality_gate_phases | ~6 | Phase 2-5.5 details, thresholds, gates |
| technology_stack | ~4 | Python, Claude Code, SDK, async patterns |
| feature_build_architecture | ~5 | Player-Coach, worktrees, delegation |
| architecture_decisions | ~3 | Initial ADRs (SDK vs subprocess, etc.) |
| failure_patterns | ~3 | Known failures and fixes |
| component_status | ~5 | Component completion state |
| integration_points | ~8 | How components connect |
| templates | ~10 | Template metadata for 5 core templates |
| agents | ~12 | Agent capabilities (architectural-reviewer, etc.) |
| patterns | ~6 | Design patterns (repository, service, etc.) |
| rules | ~5 | Code style, testing, architecture rules |
| project_overview | Variable | Project purpose and scope |
| project_architecture | Variable | Project structure |
| failed_approaches | ~5 | Initial failed approach episodes |
| quality_gate_configs | ~6 | Per-task-type quality thresholds |
| pattern_examples | Variable | Pattern code example episodes |

Each category lives in its own `seed_*.py` module. The `seeding.py` orchestrator (194 lines) dispatches to these modules.

**Feature-Build ADRs** (via `guardkit graphiti seed-adrs`):
- ADR-FB-001: Use SDK query() for task-work invocation
- ADR-FB-002: Use FEAT-XXX paths in feature mode
- ADR-FB-003: Pre-loop must invoke real task-work

### Can I query Graphiti directly?

**Yes!** Use the Python API. Note that `get_graphiti()` returns a thread-local client — each thread gets its own `GraphitiClient` with its own Neo4j driver:

```python
from guardkit.knowledge import get_graphiti

client = get_graphiti()  # Thread-local client (lazy-init if needed)

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

### How do I capture project knowledge interactively?

Use the interactive capture command:

```bash
# Start interactive session
guardkit graphiti capture --interactive

# Focus on specific category
guardkit graphiti capture --interactive --focus architecture
guardkit graphiti capture --interactive --focus role-customization

# Limit questions
guardkit graphiti capture --interactive --max-questions 5
```

**Focus Categories:**
- **Project knowledge**: project-overview, architecture, domain, constraints, decisions, goals
- **AutoBuild customization**: role-customization, quality-gates, workflow-preferences

**See**: [Interactive Knowledge Capture Guide](graphiti-knowledge-capture.md)

### How do I query stored knowledge?

Use the query commands:

```bash
# Show specific knowledge by ID
guardkit graphiti show FEAT-SKEL-001
guardkit graphiti show ADR-001

# Search for knowledge
guardkit graphiti search "authentication patterns"
guardkit graphiti search "error handling" --group patterns --limit 20

# List all in category
guardkit graphiti list features
guardkit graphiti list adrs

# Check status
guardkit graphiti status --verbose
```

**See**: [Knowledge Query Commands Guide](graphiti-query-commands.md)

### What is job-specific context?

Job-specific context is a Phase 2 feature that provides each task with precisely the knowledge it needs:

| Task Type | Context Loaded |
|-----------|----------------|
| **Simple (1-3)** | 2000 tokens: patterns (30%), outcomes (25%), architecture (20%) |
| **Medium (4-6)** | 4000 tokens: balanced across categories |
| **Complex (7-10)** | 6000 tokens: architecture (25%), patterns (25%), outcomes (20%) |

**Budget adjustments:**
- First-of-type: +30%
- Refinement: +20%
- AutoBuild Turn >1: +15%

**See**: [Job-Specific Context Retrieval Guide](graphiti-job-context.md)

### How do turn states work in AutoBuild?

Each `/feature-build` turn captures state for cross-turn learning:

**Captured per turn:**
- Player decisions and actions
- Coach feedback and approval status
- Files modified during turn
- Acceptance criteria status (verified/pending/rejected)
- Blockers encountered

**Benefits:**
- Turn N+1 knows what Turn N learned
- Prevents repeated mistakes
- Tracks progress against acceptance criteria
- Provides audit trail for feature development

**Query turn states:**
```bash
guardkit graphiti search "turn FEAT-XXX" --group turn_states
```

**See**: [Turn State Tracking Guide](graphiti-turn-states.md)

---

## Multi-Project Support (Project Namespaces)

**New in v1.0**: Graphiti supports multiple projects sharing a single instance through **project namespaces**.

### The Problem

Without namespacing, multiple projects sharing a Graphiti instance contaminate each other's knowledge:

```
Project A: "Use JWT authentication"
Project B: Searches for "authentication"
Project B: Incorrectly retrieves Project A's decision
```

### The Solution

**Project Namespaces** automatically prefix project-specific knowledge:

```python
# Project A
project_id = "project-a"
group = "project-a__architecture"  # Prefixed

# Project B
project_id = "project-b"
group = "project-b__architecture"  # Different prefix

# System-level (shared)
group = "role_constraints"  # No prefix
```

### Quick Start

**Auto-detection (Recommended)**:
```python
# Uses current directory name as project_id
# Creates a GraphitiClientFactory and initializes a thread-local client
await init_graphiti()

client = get_graphiti()  # Returns thread-local client
print(client.project_id)  # e.g., "guardkit"
```

**Explicit configuration**:
```yaml
# .guardkit/graphiti.yaml
project_id: my-project-name
```

**Environment override**:
```bash
export GUARDKIT_PROJECT_ID=production-deployment
```

### How It Works

**Project Groups** (auto-prefixed):
- `project_overview` → `{project_id}__project_overview`
- `project_architecture` → `{project_id}__project_architecture`
- `project_purpose` → `{project_id}__project_purpose`
- `project_tech_stack` → `{project_id}__project_tech_stack`
- `project_knowledge` → `{project_id}__project_knowledge`
- `project_decisions` → `{project_id}__project_decisions`
- `feature_specs` → `{project_id}__feature_specs`

**System Groups** (never prefixed):
- `role_constraints` - Shared quality gates
- `guardkit_templates` - Shared templates
- `guardkit_patterns` - Shared design patterns

### For More Details

See the complete **[Project Namespaces Guide](graphiti-project-namespaces.md)** for:
- Configuration priority (parameter > env > YAML > auto-detect)
- Project ID normalization rules
- Cross-project search
- Migration strategies
- Best practices

---

## See Also

### Phase 2 Guides

- **[Interactive Knowledge Capture](graphiti-knowledge-capture.md)** - Capture project knowledge through Q&A sessions
- **[Knowledge Query Commands](graphiti-query-commands.md)** - Query and inspect stored knowledge
- **[Job-Specific Context Retrieval](graphiti-job-context.md)** - Budget-aware, precision context loading
- **[Turn State Tracking](graphiti-turn-states.md)** - Cross-turn learning for AutoBuild

### Core Guides

- **[Graphiti Testing and Validation](graphiti-testing-validation.md)** - E2E tests and validation procedures
- **[Graphiti Project Namespaces](graphiti-project-namespaces.md)** - Multi-project isolation guide
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
- ✅ Job-specific context retrieval (Phase 2)
- ✅ Interactive knowledge capture (Phase 2)
- ✅ Turn state tracking for AutoBuild (Phase 2)

**Key Commands:**
```bash
# Setup
docker compose -f docker/docker-compose.graphiti.yml up -d
export OPENAI_API_KEY=sk-your-key-here
guardkit graphiti seed

# Verify
guardkit graphiti status
guardkit graphiti verify

# Query (Phase 2)
guardkit graphiti show FEAT-XXX        # Show specific knowledge
guardkit graphiti search "pattern"     # Search knowledge
guardkit graphiti list features        # List by category

# Capture (Phase 2)
guardkit graphiti capture --interactive              # Full session
guardkit graphiti capture --interactive --focus architecture

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
4. Explore Phase 2 features: [Interactive Capture](graphiti-knowledge-capture.md), [Query Commands](graphiti-query-commands.md)
5. See [Setup Guide](../setup/graphiti-setup.md) for advanced configuration
