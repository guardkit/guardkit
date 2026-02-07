# Graphiti Technical Reference - GuardKit Baseline

> **Purpose**: Comprehensive technical reference for how GuardKit uses Graphiti.
> Suitable as `--context` input for `/feature-plan` commands extending Graphiti usage.
>
> **Companion Document**: [Graphiti Storage Theory & Best Practices](graphiti-storage-theory.md)

---

## 1. Module Map

### Core Client Layer

| Module | Responsibility | Key Exports |
|--------|---------------|-------------|
| `guardkit/knowledge/graphiti_client.py` | Graphiti wrapper with graceful degradation | `GraphitiClient`, `GraphitiConfig`, `init_graphiti`, `get_graphiti` |
| `guardkit/knowledge/config.py` | YAML config loading | `GraphitiSettings`, `load_graphiti_config`, `get_config_path` |
| `guardkit/knowledge/__init__.py` | Public API surface (~70 exports) | All public types and functions |

### Entity Layer (`guardkit/knowledge/entities/`)

| Module | Entity | Group ID | Purpose |
|--------|--------|----------|---------|
| `entities/outcome.py` | `TaskOutcome` | `task_outcomes` | Records task completion/failure with metrics |
| `entities/feature_overview.py` | `FeatureOverviewEntity` | `feature_overview` | Feature identity, invariants, architecture |
| `entities/turn_state.py` | `TurnStateEntity` + `TurnMode` | `turn_states` | AutoBuild turn-by-turn progress tracking |
| `entities/failed_approach.py` | `FailedApproachEpisode` + `Severity` | `failed_approaches` | What failed, why, and how to prevent |

### Facts Layer (`guardkit/knowledge/facts/`)

| Module | Fact | Group ID | Purpose |
|--------|------|----------|---------|
| `facts/role_constraint.py` | `RoleConstraintFact` | `role_constraints` | Player/Coach role boundaries |
| `facts/quality_gate_config.py` | `QualityGateConfigFact` | `quality_gate_configs` | Per-task-type quality thresholds |

### Operations Layer

| Module | Responsibility | Key Functions |
|--------|---------------|---------------|
| `outcome_manager.py` | Task outcome CRUD | `capture_task_outcome()`, `OutcomeManager` |
| `outcome_queries.py` | Task outcome search | `find_similar_task_outcomes()`, `OutcomeQueries` |
| `turn_state_operations.py` | Turn state lifecycle | `capture_turn_state()`, `load_turn_continuation_context()`, `create_turn_state_from_autobuild()` |
| `failed_approach_manager.py` | Failed approach lifecycle | `capture_failed_approach()`, `load_relevant_failures()`, `increment_occurrence()` |
| `adr_service.py` | ADR CRUD | `ADRService` (record, update, search) |
| `adr_discovery.py` | ADR pattern detection | Detects decisions in Q&A flow |
| `decision_detector.py` | Decision significance | `DecisionDetector` |

### Context Loading Layer

| Module | Responsibility | Key Exports |
|--------|---------------|-------------|
| `context_loader.py` | Session-start context | `CriticalContext`, `load_critical_context()`, `load_feature_overview()` |
| `context_formatter.py` | Prompt formatting | `format_context_for_injection()`, `ContextFormatterConfig` |
| `autobuild_context_loader.py` | AutoBuild-specific context | `AutoBuildContextLoader`, `AutoBuildContextResult` |
| `job_context_retriever.py` | Task-phase-specific retrieval | `JobContextRetriever`, `RetrievedContext` |
| `task_analyzer.py` | Task classification | `TaskAnalyzer`, `TaskCharacteristics`, `TaskType`, `TaskPhase` |
| `budget_calculator.py` | Dynamic context budgeting | `DynamicBudgetCalculator`, `ContextBudget` |
| `quality_gate_formatter.py` | Quality gate formatting | `format_quality_gates()` |
| `role_constraint_formatter.py` | Role constraint formatting | `format_role_constraints()`, `format_role_constraints_for_actor()` |

### Seeding Layer

| Module | Responsibility |
|--------|---------------|
| `seeding.py` | Orchestrator only (194 lines) - 18 categories, marker management, `getattr()` dispatch |
| `seed_helpers.py` | Shared `_add_episodes()` utility, `SEEDING_VERSION` constant |
| `seed_product_knowledge.py` | Product knowledge episodes |
| `seed_command_workflows.py` | Command workflow episodes |
| `seed_quality_gate_phases.py` | Quality gate phase episodes |
| `seed_technology_stack.py` | Technology stack episodes |
| `seed_feature_build_architecture.py` | Feature-build architecture episodes |
| `seed_architecture_decisions.py` | Architecture decision episodes |
| `seed_failure_patterns.py` | Failure pattern episodes |
| `seed_component_status.py` | Component status episodes |
| `seed_integration_points.py` | Integration point episodes |
| `seed_templates.py` | Template metadata episodes |
| `seed_agents.py` | Agent capability episodes |
| `seed_patterns.py` | Design pattern episodes |
| `seed_rules.py` | Code style rule episodes |
| `seed_project_overview.py` | Project overview episodes (TASK-CR-005) |
| `seed_project_architecture.py` | Project architecture episodes (TASK-CR-005) |
| `seed_feature_overviews.py` | Feature overview episodes |
| `seed_role_constraints.py` | Role constraint episodes |
| `seed_quality_gate_configs.py` | Quality gate config episodes |
| `seed_feature_build_adrs.py` | Feature-build ADR episodes |
| `seed_failed_approaches.py` | Initial failed approach episodes |
| `seed_pattern_examples.py` | Pattern code example episodes (TASK-CR-006) |
| `template_sync.py` | Template → knowledge graph sync |

### Analysis Layer

| Module | Responsibility | Key Exports |
|--------|---------------|-------------|
| `feature_detector.py` | Detect feature from task | `FeatureDetector` |
| `gap_analyzer.py` | Knowledge gap analysis | `KnowledgeGapAnalyzer`, `KnowledgeGap`, `KnowledgeCategory` |
| `interactive_capture.py` | Interactive Q&A session | `InteractiveCaptureSession`, `CapturedKnowledge` |

### CLI Layer

| Module | Responsibility |
|--------|---------------|
| `guardkit/cli/graphiti.py` | Click command group (10 commands) |
| `guardkit/cli/graphiti_query_commands.py` | Shared formatting for show/search/list |

---

## 2. GraphitiClient API

### Connection Lifecycle

```python
# Configuration
config = GraphitiConfig(
    enabled=True,                          # Master switch
    neo4j_uri="bolt://localhost:7687",      # Neo4j connection
    neo4j_user="neo4j",
    neo4j_password="password123",
    timeout=30.0,                          # Operation timeout
    project_id="guardkit"                  # Namespace prefix
)

# Initialization
client = GraphitiClient(config)
await client.initialize()       # Connects to Neo4j, builds indices

# Health check
healthy = await client.health_check()  # Returns bool

# Cleanup
await client.close()

# Singleton pattern
await init_graphiti(config)     # Initialize once
client = get_graphiti()          # Get anywhere
```

### Episode Operations

#### add_episode()

Creates a new episode in the knowledge graph.

```python
episode_id = await client.add_episode(
    name="GuardKit Overview",               # Episode title
    episode_body="GuardKit is a...",         # Content (str or JSON)
    group_id="product_knowledge",            # Knowledge group
    scope=None,                              # "project" | "system" | None
    metadata=None,                           # Optional EpisodeMetadata
    source="user_added",                     # Source identifier
    entity_type="generic"                    # Entity classification
)
# Returns: Optional[str] - Episode UUID or None on failure
```

#### upsert_episode()

Creates or updates an episode using content-hash change detection.

```python
result = await client.upsert_episode(
    name="Quality Gate: Feature Low",
    episode_body='{"id": "QG-FEATURE-LOW", ...}',
    group_id="quality_gate_configs",
    entity_id="QG-FEATURE-LOW",             # Stable identifier for upsert
    source="guardkit_seeding",
    entity_type="quality_gate_config",
    scope=None,
    source_hash=None                         # Auto-computed if None
)
# Returns: Optional[UpsertResult] with fields: created, updated, skipped, uuid
```

#### episode_exists()

Checks if an episode already exists by entity_id.

```python
result = await client.episode_exists(
    entity_id="QG-FEATURE-LOW",
    group_id="quality_gate_configs",
    source_hash="abc123..."                  # Optional: check content match
)
# Returns: ExistsResult with fields: exists, exact_match, uuid, episode
```

#### search()

Semantic search across the knowledge graph.

```python
results = await client.search(
    query="quality gate thresholds for testing tasks",
    group_ids=["quality_gate_configs", "quality_gate_phases"],
    num_results=10,
    scope=None
)
# Returns: List[Dict[str, Any]]
# Each result: {"uuid": "...", "fact": "...", "name": "...",
#               "created_at": "...", "valid_at": "...", "score": 0.85}
```

#### Content Preservation Warning

> **WARNING**: Graphiti does not preserve verbatim content. When episodes are added, the content passes through an LLM-based entity/relationship extraction pipeline. The `search()` method returns **semantic facts extracted from the original content**, not the original text itself.
>
> **Implications for API consumers**:
> - `add_episode()` and `upsert_episode()` accept any text, but it will be decomposed into facts
> - `search()` returns extracted facts, not the original `episode_body` content
> - Code blocks, exact formatting, and syntax are **not retrievable** after storage
> - For content requiring verbatim retrieval, use static files instead
>
> See [Graphiti Code Retrieval Fidelity Assessment](../graphiti_enhancement/graphiti_code_retrieval_fidelity.md) for detailed testing results.

#### Clearing Operations

```python
# Clear everything
result = await client.clear_all()

# Clear only system-level groups
result = await client.clear_system_groups()

# Clear only project-specific groups
result = await client.clear_project_groups(project_name="guardkit")

# Preview what would be cleared
preview = await client.get_clear_preview(system_only=False, project_only=True)
```

### Group ID Management

```python
# Get group ID with automatic project prefixing
gid = client.get_group_id("feature_overview", scope="project")
# Returns: "guardkit__feature_overview" (if project_id="guardkit")

gid = client.get_group_id("product_knowledge", scope="system")
# Returns: "product_knowledge" (no prefix for system groups)

gid = client.get_group_id("feature_overview", scope="auto")
# Returns: "guardkit__feature_overview" (auto-detected as project group)

# Check if a group is project-scoped
client.is_project_group("project_overview")     # True
client.is_project_group("product_knowledge")    # False
```

---

## 3. Metadata Conventions

### Episode Content Metadata Block

All seeded episodes include a `_metadata` block injected into the episode body:

```json
{
  "title": "Episode Title",
  "content": "The actual content...",
  "_metadata": {
    "entity_id": "STABLE-IDENTIFIER",
    "source": "guardkit_seeding",
    "source_hash": "sha256_of_content",
    "entity_type": "product_knowledge",
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-01-15T10:00:00Z",
    "project_id": "guardkit",
    "source_description": "GuardKit system knowledge seeding"
  }
}
```

### Standard Metadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entity_id` | str | Yes | Stable identifier for upsert (e.g., `QG-FEATURE-LOW`, `FAIL-abc123`) |
| `source` | str | Yes | Origin: `guardkit_seeding`, `user_added`, `autobuild`, `interactive_capture` |
| `source_hash` | str | Yes | SHA256 of content for change detection |
| `entity_type` | str | Yes | Classification: `outcome`, `turn_state`, `failed_approach`, `feature_overview`, `role_constraint`, `quality_gate_config`, `product_knowledge`, `generic` |
| `created_at` | str | Yes | ISO 8601 timestamp of first creation |
| `updated_at` | str | Yes | ISO 8601 timestamp of last update |
| `project_id` | str | No | Project namespace (omitted for system knowledge) |
| `source_description` | str | No | Human-readable origin description |

### Unified Serialization Convention (TASK-GBF-001)

All entity types implement `to_episode_body()` returning **domain data only** (no `_metadata` block). The `GraphitiClient` is solely responsible for injecting the `_metadata` block when storing episodes. This ensures a single, consistent metadata path:

```python
# Entity returns domain data only
body = entity.to_episode_body()  # {"id": "...", "name": "...", ...}

# Client wraps with metadata before storage
await client.upsert_episode(
    name="...",
    episode_body=json.dumps(body),  # Client injects _metadata
    ...
)
```

### Entity-Specific ID Patterns

| Entity Type | ID Format | Example |
|-------------|-----------|---------|
| Task Outcome | `OUT-{8char_hash}` | `OUT-a3f8b2c1` |
| Feature Overview | Feature name slug | `feature-build` |
| Turn State | `TURN-{feature_id}-{turn_number}` | `TURN-FEAT-GE-3` |
| Failed Approach | `FAIL-{8char_hash}` | `FAIL-d7e2f9a0` |
| Role Constraint | `{role}-{context}` | `player-feature-build` |
| Quality Gate Config | `QG-{task_type}-{range}` | `QG-FEATURE-MED` |
| ADR | `ADR-{prefix}-{number}` | `ADR-FB-001` |

---

## 4. Group ID Organization

### System Groups (18 - No Prefix)

```
product_knowledge          - What GuardKit is
command_workflows          - How commands connect
quality_gate_phases        - 5-phase quality structure
technology_stack           - Python CLI, Claude Code, SDK
feature_build_architecture - Player-Coach pattern
architecture_decisions     - Key design decisions
failure_patterns           - Known failures and fixes
component_status           - Component completion state
integration_points         - Component connections
templates                  - Template metadata
agents                     - Agent capabilities
patterns                   - Design patterns
rules                      - Code style conventions
guardkit_templates         - Template search index
guardkit_patterns          - Pattern search index
guardkit_workflows         - Workflow search index
failed_approaches          - Failed approaches (TASK-GE-004)
quality_gate_configs       - Quality gate configs (TASK-GE-005)
role_constraints           - Role constraints (TASK-GE-003)
implementation_modes       - Implementation mode configs
```

### Project Groups (6 - Prefixed with `{project_id}__`)

```
{project_id}__project_overview      - Project purpose and scope
{project_id}__project_architecture  - Project structure
{project_id}__feature_specs         - Feature specifications
{project_id}__project_decisions     - Project-level decisions
{project_id}__project_constraints   - Project constraints
{project_id}__domain_knowledge      - Domain-specific knowledge
```

### Learning Groups (Contextual)

```
task_outcomes              - Task completion/failure records
turn_states                - AutoBuild turn-by-turn progress
```

---

## 5. CLI Command Reference

### Lifecycle Commands

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `guardkit graphiti seed` | Seed system context (16 categories) | `--force` (re-seed) |
| `guardkit graphiti seed-adrs` | Seed feature-build ADRs | `--force` |
| `guardkit graphiti clear` | Clear knowledge graph | `--confirm`, `--system-only`, `--project-only`, `--dry-run` |
| `guardkit graphiti status` | Show connection and seeding status | `--verbose` |
| `guardkit graphiti verify` | Run test queries to verify seeding | `--verbose` |

### Content Commands

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `guardkit graphiti add-context <path>` | Add file/directory content | `--type`, `--pattern`, `--dry-run` |
| `guardkit graphiti capture` | Interactive Q&A knowledge capture | `--interactive`, `--focus`, `--max-questions` |

### Query Commands

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `guardkit graphiti search <query>` | Semantic search | `--group`, `--limit` |
| `guardkit graphiti show <id>` | Show specific knowledge item | Auto-detects type from ID |
| `guardkit graphiti list <category>` | List all in category | `features`, `adrs`, `patterns`, `constraints`, `all` |

---

## 6. Context Loading Pipeline

### Layer 1: CriticalContext (Session Start)

Loaded once at the beginning of any command session:

```python
@dataclass
class CriticalContext:
    system_context: List[Dict]           # What GuardKit is
    quality_gates: List[Dict]            # Phase requirements
    architecture_decisions: List[Dict]   # MUST FOLLOW decisions
    failure_patterns: List[Dict]         # DO NOT REPEAT
    successful_patterns: List[Dict]      # What worked well
    similar_task_outcomes: List[Dict]    # Similar task results
    relevant_adrs: List[Dict]           # Architecture Decision Records
    applicable_patterns: List[Dict]     # Relevant design patterns
    relevant_rules: List[Dict]          # Code style rules
```

### Layer 2: AutoBuildContextLoader (Feature-Build Specific)

```python
result = await AutoBuildContextLoader.load(graphiti, feature_id, task_id)
# Returns AutoBuildContextResult with:
#   - feature_overview: FeatureOverviewEntity
#   - role_constraints: formatted player/coach boundaries
#   - quality_gates: applicable gate configs
#   - failed_approaches: relevant failures
#   - previous_turns: turn continuation context
```

### Layer 3: JobContextRetriever (Task-Phase Specific)

Dynamic context retrieval with budget allocation:

```python
retriever = JobContextRetriever(graphiti)
context = await retriever.retrieve(
    task_id="TASK-123",
    task_data={"title": "...", "complexity": 5},
    phase=TaskPhase.IMPLEMENT
)
# Returns RetrievedContext with budget-aware allocation
```

Budget allocation is based on:
- Task complexity (1-10)
- Current phase (LOAD, PLAN, IMPLEMENT, TEST, REVIEW)
- Available context window

### Formatting for Prompt Injection

```python
from guardkit.knowledge import format_context_for_injection

context_text = format_context_for_injection(
    critical_context,
    config=ContextFormatterConfig(
        max_tokens=2000,
        include_system=True,
        include_patterns=True
    )
)
# Returns: formatted markdown string for prompt injection
```

---

## 7. Seeding Architecture

### Orchestrator Function

`seeding.py` is now a pure orchestrator (194 lines). All seed content lives in dedicated `seed_*.py` modules. The orchestrator uses dynamic `getattr()` dispatch to support `unittest.mock.patch`:

```python
async def seed_all_system_context(client: GraphitiClient, force: bool = False) -> bool:
    """Seed all 18 knowledge categories."""
    if not force and is_seeded():
        return True  # Already seeded

    seeding_module = sys.modules[__name__]  # Dynamic lookup for test patching

    categories = [
        ("product_knowledge", "seed_product_knowledge"),
        ("command_workflows", "seed_command_workflows"),
        ("quality_gate_phases", "seed_quality_gate_phases"),
        ("technology_stack", "seed_technology_stack"),
        ("feature_build_architecture", "seed_feature_build_architecture"),
        ("architecture_decisions", "seed_architecture_decisions"),
        ("failure_patterns", "seed_failure_patterns"),
        ("component_status", "seed_component_status"),
        ("integration_points", "seed_integration_points"),
        ("templates", "seed_templates"),
        ("agents", "seed_agents"),
        ("patterns", "seed_patterns"),
        ("rules", "seed_rules"),
        ("project_overview", "seed_project_overview"),
        ("project_architecture", "seed_project_architecture"),
        ("failed_approaches", "seed_failed_approaches_wrapper"),
        ("quality_gate_configs", "seed_quality_gate_configs_wrapper"),
        ("pattern_examples", "seed_pattern_examples_wrapper"),
    ]

    for name, fn_name in categories:
        seed_fn = getattr(seeding_module, fn_name)
        await seed_fn(client)

    mark_seeded()
    return True
```

### Marker File

Located at `.guardkit/seeding/.graphiti_seeded.json`:

```json
{
  "seeded": true,
  "version": "1.0.0",
  "timestamp": "2026-01-15T10:00:00Z"
}
```

### Seeding Pattern (Per Category)

Each seed module uses the shared `_add_episodes()` helper from `seed_helpers.py`:

```python
from guardkit.knowledge.seed_helpers import _add_episodes

async def seed_product_knowledge(client) -> None:
    """Seed product knowledge episodes."""
    episodes = [
        {
            "name": "GuardKit Overview",
            "body": json.dumps({
                "title": "GuardKit Overview",
                "content": "GuardKit is a lightweight...",
                "_metadata": {
                    "entity_id": "guardkit-overview",
                    "source": "guardkit_seeding",
                    "entity_type": "product_knowledge",
                    ...
                }
            }),
            "group_id": "product_knowledge",
        },
        # ... more episodes
    ]

    await _add_episodes(client, episodes)
```

The `_add_episodes()` helper handles batch iteration, error logging, and graceful degradation for all seed modules.

---

## 8. Configuration

### YAML Configuration (`.guardkit/graphiti.yaml`)

```yaml
project_id: guardkit
enabled: true
host: localhost
port: 8000
timeout: 30.0
embedding_model: text-embedding-3-small
group_ids:
  - product_knowledge
  - command_workflows
  - architecture_decisions
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAPHITI_ENABLED` | `true` | Master switch |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `password123` | Neo4j password |
| `GRAPHITI_TIMEOUT` | `30.0` | Operation timeout (seconds) |
| `OPENAI_API_KEY` | (required) | For embedding model |

### Configuration Priority

1. Environment variables (highest)
2. `.guardkit/graphiti.yaml` (project-level)
3. `config/graphiti.yaml` (example/fallback)
4. Hardcoded defaults (lowest)

---

## 9. Dependency Chain

```
graphiti-core (external)
  └── neo4j (database driver)
  └── openai (embedding model)

guardkit/knowledge/graphiti_client.py
  └── graphiti-core.Graphiti (lazy import)
  └── graphiti-core.nodes.EpisodeType

guardkit/knowledge/config.py
  └── PyYAML

guardkit/cli/graphiti.py
  └── click
  └── rich (console output)
  └── guardkit.knowledge.*
```

All external dependencies are lazy-imported for graceful degradation when not installed.

---

## 10. Integration Points

### task-work Integration

```python
# installer/core/commands/lib/graphiti_context_loader.py
from guardkit.knowledge import JobContextRetriever

# Loads context at task start for prompt injection
context = await load_task_context(task_id, task_data, phase="IMPLEMENT")
prompt_text = get_context_for_prompt(context)
```

### feature-build Integration

```python
# AutoBuild orchestrator loads context at feature-build start
from guardkit.knowledge import AutoBuildContextLoader

result = await AutoBuildContextLoader.load(graphiti, feature_id, task_id)
# Injects: feature overview, role constraints, quality gates, failures, previous turns
```

### Interactive Capture Integration

```python
# guardkit graphiti capture --interactive
from guardkit.knowledge import InteractiveCaptureSession

session = InteractiveCaptureSession(graphiti, focus="architecture")
await session.run()
# Q&A flow → parsed answers → seeded to knowledge graph
```
