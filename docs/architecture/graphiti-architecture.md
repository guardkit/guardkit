# Graphiti Architecture Documentation

## System Overview

Graphiti provides GuardKit with persistent memory across Claude Code sessions through a temporal knowledge graph. This integration prevents context-less decision making by ensuring sessions have access to architectural decisions, failure patterns, quality gates, and historical outcomes.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code Session                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  GuardKit Command (/task-work, /feature-build, etc.)     │  │
│  │                                                           │  │
│  │  1. Load Context (Phase 1)                               │  │
│  │     ↓                                                     │  │
│  │  ┌─────────────────────────────────────────────────┐     │  │
│  │  │  Context Loader                                 │     │  │
│  │  │  - load_critical_context()                      │     │  │
│  │  │  - load_feature_overview()                      │     │  │
│  │  │  - load_role_context()                          │     │  │
│  │  │  - load_critical_adrs()                         │     │  │
│  │  │  - load_failed_approaches()                     │     │  │
│  │  └─────────────────────────────────────────────────┘     │  │
│  │     ↓                                                     │  │
│  │  ┌─────────────────────────────────────────────────┐     │  │
│  │  │  GraphitiClient                                 │     │  │
│  │  │  - search(query, group_ids, num_results)        │     │  │
│  │  │  - add_episode(name, body, group_id)            │     │  │
│  │  └─────────────────────────────────────────────────┘     │  │
│  │     ↓                                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│        ↓                                                         │
└─────────────────────────────────────────────────────────────────┘
         ↓
    HTTP/REST
         ↓
┌─────────────────────────────────────────────────────────────────┐
│                       Graphiti API                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Entities   │  │   Episodes   │  │   Facts      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         ↓                 ↓                 ↓                   │
│  ┌──────────────────────────────────────────────────┐          │
│  │          OpenAI Embeddings (for search)          │          │
│  └──────────────────────────────────────────────────┘          │
│         ↓                                                       │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│                         Neo4j                                   │
│                    (Graph Database)                             │
└─────────────────────────────────────────────────────────────────┘

Data Flow:
1. Command starts → Context Loader queries Graphiti
2. Graphiti searches knowledge graph → Returns relevant context
3. Context formatted and injected into Claude Code session
4. Task executes with full knowledge of decisions, patterns, failures
5. On completion → Outcome/ADR/TurnState captured back to Graphiti
```

## Knowledge Categories

Complete table of all group_ids used in Graphiti for organizing knowledge:

| Group ID | Contents | Seeded By | Typical Episodes | Context Loader |
|----------|----------|-----------|------------------|----------------|
| `product_knowledge` | GuardKit identity, core principles, workflow philosophy | TASK-GI-001 | ~15 | `load_critical_context()` |
| `command_workflows` | Command patterns, argument flows, state transitions | TASK-GI-001 | ~25 | `load_critical_context()` |
| `quality_gate_phases` | Phase definitions, thresholds, gate criteria | TASK-GI-001 | ~12 | `load_critical_context()` |
| `technology_stack` | Python, CLI, Claude Code, SDK, worktrees | TASK-GI-001 | ~10 | `load_critical_context()` |
| `feature_build_architecture` | Player-Coach delegation, task-work subprocess | TASK-GI-001 | ~20 | `load_critical_context()` (when command="feature-build") |
| `architecture_decisions` | Core ADRs (hash IDs, no task-work, subprocess isolation) | TASK-GI-001 + TASK-GE-007 | ~8 | `load_critical_context()` + `load_critical_adrs()` |
| `failure_patterns` | Known bugs, anti-patterns, fixes | TASK-GI-001 | ~10 | `load_critical_context()` |
| `component_status` | What's complete/incomplete/deprecated | TASK-GI-001 | ~5 | Not loaded (informational) |
| `integration_points` | How components connect | TASK-GI-001 | ~8 | Not loaded (informational) |
| `templates` | Template metadata for semantic search | TASK-GI-001 | ~5 | Not loaded (future feature) |
| `agents` | Agent capabilities and boundaries | TASK-GI-001 | ~15 | Not loaded (future feature) |
| `patterns` | Design pattern knowledge | TASK-GI-001 | ~10 | Not loaded (future feature) |
| `rules` | Rule applicability and code examples | TASK-GI-001 | ~12 | Not loaded (future feature) |
| `adrs` | Dynamic Architecture Decision Records | TASK-GI-004 | Variable | `load_critical_adrs()` |
| `task_outcomes` | Task completion episodes with outcomes | TASK-GI-005 | Variable | Not loaded (similarity search) |
| `feature_overviews` | Feature identity preservation | TASK-GE-001 | ~1 per feature | `load_feature_overview()` |
| `role_constraints` | Player/Coach must-do/must-not-do | TASK-GE-003 | 2 | `load_role_context()` |
| `failed_approaches` | Failed approaches with prevention guidance | TASK-GE-004 | ~10 initial | `load_failed_approaches()` |

**Phase 2 Enhancements (FEAT-GR):**

These additional categories were added in Phase 2 (Graphiti Refinement):

| Group ID | Contents | Added By | Purpose |
|----------|----------|----------|---------|
| `turn_states` | AutoBuild turn-by-turn state | FEAT-GR-005 | Cross-turn learning |
| `captured_knowledge` | Interactively captured facts | FEAT-GR-004 | User knowledge preservation |
| `role_constraints` | Player/Coach role boundaries | FEAT-GR-004 | AutoBuild role customization |
| `quality_gate_configs` | Task-type specific thresholds | FEAT-GR-004 | Quality gate customization |
| `implementation_modes` | Direct vs task-work guidance | FEAT-GR-006 | AutoBuild workflow preferences |

## Python API Reference

### Core Client

#### `GraphitiConfig`

Immutable configuration dataclass for Graphiti connection.

```python
from guardkit.knowledge import GraphitiConfig

config = GraphitiConfig(
    enabled=True,
    host="localhost",
    port=8000,
    timeout=30.0
)
```

**Fields:**
- `enabled` (bool): Whether Graphiti integration is enabled (default: True)
- `host` (str): Graphiti server hostname (default: "localhost")
- `port` (int): Graphiti server port (default: 8000)
- `timeout` (float): Connection timeout in seconds (default: 30.0)

**Raises:** `ValueError` if timeout is zero or negative.

#### `GraphitiClient`

Main client wrapper with graceful degradation.

```python
from guardkit.knowledge import GraphitiClient, GraphitiConfig

# Create and initialize client
config = GraphitiConfig(enabled=True, host="localhost", port=8000)
client = GraphitiClient(config)
await client.initialize()

# Check if enabled before operations
if client.enabled:
    # Search knowledge graph
    results = await client.search(
        query="authentication patterns",
        group_ids=["architecture_decisions"],
        num_results=5
    )

    # Add episode
    episode_id = await client.add_episode(
        name="OAuth2 Implementation",
        episode_body="Decided to use OAuth2 with PKCE flow...",
        group_id="architecture_decisions"
    )
```

**Methods:**

- `initialize() -> bool`: Establish connection (checks config, OPENAI_API_KEY, server)
- `health_check() -> bool`: Verify server is responding
- `search(query, group_ids=None, num_results=10) -> List[Dict]`: Search knowledge graph
- `add_episode(name, episode_body, group_id) -> Optional[str]`: Create episode

**Properties:**

- `enabled`: True only if config enabled AND successfully connected

**Graceful Degradation:** All methods return empty results or None on failure instead of raising exceptions.

#### `init_graphiti` / `get_graphiti` / `get_factory`

Per-thread factory pattern for client access. Each thread gets its own `GraphitiClient` with its own Neo4j driver bound to that thread's event loop. The `GraphitiConfig` (frozen dataclass) is shared across threads.

```python
from guardkit.knowledge import init_graphiti, get_graphiti, get_factory, GraphitiConfig

# Initialize factory + thread client (typically in application startup)
config = GraphitiConfig(enabled=True)
success = await init_graphiti(config)

# Get thread-local client anywhere (lazy-init if needed)
client = get_graphiti()
if client and client.enabled:
    results = await client.search("query")

# Get factory directly (for multi-threaded scenarios)
factory = get_factory()
if factory:
    thread_client = factory.get_thread_client()
```

**Functions:**

- `init_graphiti(config: Optional[GraphitiConfig] = None) -> bool`: Create factory and initialize a client for the current thread
- `get_graphiti() -> Optional[GraphitiClient]`: Get thread-local client (lazy-init from config if no factory exists)
- `get_factory() -> Optional[GraphitiClientFactory]`: Get the global factory (no lazy-init)

#### `GraphitiClientFactory`

Thread-safe factory using `threading.local()` for per-thread client storage (TASK-FIX-GTP1).

```python
from guardkit.knowledge import GraphitiClientFactory, GraphitiConfig

config = GraphitiConfig(enabled=True)
factory = GraphitiClientFactory(config)

# Create uninitialized client
client = factory.create_client()

# Create and initialize client (async)
client = await factory.create_and_init_client()

# Get/set thread-local client
client = factory.get_thread_client()      # Lazy-creates if needed
factory.set_thread_client(client)          # Explicit set (e.g., after async init)
```

**Methods:**

- `create_client() -> GraphitiClient`: Create uninitialized client from shared config
- `create_and_init_client() -> Optional[GraphitiClient]`: Create and initialize (async, binds to current event loop)
- `get_thread_client() -> Optional[GraphitiClient]`: Get or lazily create thread-local client
- `set_thread_client(client) -> None`: Explicitly set thread-local client

### Context Loading

#### `CriticalContext`

Dataclass holding session context loaded from Graphiti.

```python
from guardkit.knowledge import CriticalContext

@dataclass
class CriticalContext:
    system_context: List[Dict[str, Any]]          # What GuardKit is
    quality_gates: List[Dict[str, Any]]           # Quality gate definitions
    architecture_decisions: List[Dict[str, Any]]  # MUST FOLLOW decisions
    failure_patterns: List[Dict[str, Any]]        # DO NOT REPEAT failures
    successful_patterns: List[Dict[str, Any]]     # What worked well
    similar_task_outcomes: List[Dict[str, Any]]   # Similar tasks and results
    relevant_adrs: List[Dict[str, Any]]           # Relevant ADRs
    applicable_patterns: List[Dict[str, Any]]     # Design patterns for context
    relevant_rules: List[Dict[str, Any]]          # Code rules for context
```

#### `load_critical_context`

Load must-know context at session/command start.

```python
from guardkit.knowledge import load_critical_context, format_context_for_injection

# Load context at session start
context = await load_critical_context(command="task-work")

# Load context for specific task
context = await load_critical_context(
    task_id="TASK-001",
    command="feature-build"
)

# Format and inject into session
context_text = format_context_for_injection(context)
# Inject context_text into Claude Code session prompt
```

**Args:**
- `task_id` (Optional[str]): Task ID for task-specific context
- `feature_id` (Optional[str]): Feature ID for feature-specific context
- `command` (Optional[str]): Command name (e.g., "task-work", "feature-build")

**Returns:** `CriticalContext` with loaded knowledge, or empty context if Graphiti unavailable.

**Always Loads:**
1. System context (what GuardKit is)
2. Quality gates (thresholds, phases)
3. Architecture decisions (MUST FOLLOW)
4. Failure patterns (DO NOT REPEAT)

**Command-Specific:**
- When `command="feature-build"`: Loads feature-build specific architecture

#### `load_feature_overview`

Load feature overview for context injection (TASK-GE-001).

```python
from guardkit.knowledge import load_feature_overview

overview = await load_feature_overview("feature-build")
if overview:
    print(f"Feature: {overview.name}")
    print(f"Purpose: {overview.purpose}")
    print(f"Invariants: {overview.invariants}")
```

**Args:**
- `feature_name` (str): Name/ID of feature (e.g., "feature-build")

**Returns:** `FeatureOverviewEntity` if found, None otherwise.

#### `load_critical_adrs`

Load Architecture Decision Records for context injection (TASK-GE-007).

```python
from guardkit.knowledge import load_critical_adrs

adrs = await load_critical_adrs()
for adr in adrs:
    print(f"ADR {adr['id']}: {adr['title']}")
    print(f"Decision: {adr['decision']}")
    print(f"Violation symptoms: {adr.get('violation_symptoms', [])}")
```

**Returns:** List of ADR dictionaries with id, title, decision, violation_symptoms, etc.

#### `load_failed_approaches`

Load failed approaches for warning injection (TASK-GE-004).

```python
from guardkit.knowledge import load_failed_approaches

warnings = await load_failed_approaches("subprocess task-work", limit=5)
for warning in warnings:
    print(f"Warning: {warning['symptom']}")
    print(f"Prevention: {warning['prevention']}")
    print(f"Related ADRs: {warning.get('related_adrs', [])}")
```

**Args:**
- `query_context` (str): Context to search for (e.g., "subprocess task-work")
- `limit` (int): Maximum results to return (default: 5)

**Returns:** List of warning dictionaries with symptom, prevention, related_adrs.

#### `load_role_context`

Load role constraints for Player/Coach agents (TASK-GE-003).

```python
from guardkit.knowledge import load_role_context

player_context = await load_role_context("player", "feature-build")
if player_context:
    # Returns formatted markdown:
    # # PLAYER Role Constraints
    #
    # **Primary responsibility**: Implement the task
    #
    # ## MUST DO
    # - Write comprehensive tests
    # - Run tests and verify they pass
    # ...
    print(player_context)
```

**Args:**
- `role` (str): Role name ("player" | "coach")
- `context` (str): Usage context (default: "feature-build")

**Returns:** Formatted markdown string with role constraints, or None if unavailable.

#### `format_context_for_injection`

Format loaded context into markdown for session injection.

```python
from guardkit.knowledge import load_critical_context, format_context_for_injection, ContextFormatterConfig

context = await load_critical_context(command="feature-build")

# Default formatting
context_text = format_context_for_injection(context)

# Custom formatting
config = ContextFormatterConfig(
    include_system_context=True,
    include_quality_gates=True,
    include_adrs=True,
    include_failures=True,
    max_items_per_section=10
)
context_text = format_context_for_injection(context, config)
```

**Args:**
- `context` (CriticalContext): Loaded context
- `config` (Optional[ContextFormatterConfig]): Formatting configuration

**Returns:** Formatted markdown string ready for injection.

### ADR Service

#### `ADREntity`

Architecture Decision Record dataclass.

```python
from guardkit.knowledge import ADREntity, ADRStatus, ADRTrigger
from datetime import datetime

adr = ADREntity(
    id="ADR-0001",
    title="Use hash-based task IDs",
    status=ADRStatus.ACCEPTED,
    trigger=ADRTrigger.TASK_REVIEW,
    source_task_id="TASK-001",
    context="Need concurrent-safe task creation",
    decision="Use SHA256 hash of title + timestamp",
    rationale="Eliminates race conditions, works offline",
    alternatives_considered=["Sequential IDs", "UUID"],
    consequences=["Cannot predict ID", "Slightly longer IDs"],
    tags=["task-management", "concurrency"],
    confidence=0.9
)
```

**Fields:**
- `id` (str): ADR ID (e.g., "ADR-0001")
- `title` (str): Decision title
- `status` (ADRStatus): ACCEPTED | SUPERSEDED | DEPRECATED
- `trigger` (ADRTrigger): What triggered the ADR
- `source_task_id` (Optional[str]): Related task
- `source_feature_id` (Optional[str]): Related feature
- `source_command` (Optional[str]): Command that created ADR
- `context` (str): Why this decision was needed
- `decision` (str): What was decided
- `rationale` (str): Why this decision was made
- `alternatives_considered` (List[str]): Alternatives evaluated
- `consequences` (List[str]): Trade-offs and impacts
- `supersedes` (Optional[str]): ADR ID this replaces
- `superseded_by` (Optional[str]): ADR ID that replaces this
- `related_adrs` (List[str]): Related ADR IDs
- `created_at` (datetime): When created
- `decided_at` (Optional[datetime]): When decision finalized
- `deprecated_at` (Optional[datetime]): When deprecated
- `tags` (List[str]): Tags for categorization
- `confidence` (float): Confidence in decision (0-1)

#### `ADRStatus`

ADR lifecycle status enum.

```python
from guardkit.knowledge import ADRStatus

ADRStatus.ACCEPTED    # Active decision
ADRStatus.SUPERSEDED  # Replaced by newer ADR
ADRStatus.DEPRECATED  # No longer applicable
```

#### `ADRTrigger`

ADR trigger source enum.

```python
from guardkit.knowledge import ADRTrigger

ADRTrigger.MANUAL               # Manually created
ADRTrigger.CLARIFYING_QUESTION  # From clarification Q&A
ADRTrigger.TASK_REVIEW          # From task review
ADRTrigger.ARCHITECTURE_REVIEW  # From architectural review
ADRTrigger.DECISION_CHECKPOINT  # From decision checkpoint
```

#### `ADRService`

Service for creating and managing ADRs.

```python
from guardkit.knowledge import ADRService, ADREntity, ADRTrigger, ADRStatus, get_graphiti

client = get_graphiti()
service = ADRService(client, significance_threshold=0.4)

# Create ADR
adr = ADREntity(
    id="ADR-0001",
    title="Use PostgreSQL",
    trigger=ADRTrigger.MANUAL,
    decision="Use PostgreSQL for primary database"
)
adr_id = await service.create_adr(adr)

# Search ADRs
results = await service.search_adrs("database decisions", status=ADRStatus.ACCEPTED)

# Get specific ADR
adr = await service.get_adr("ADR-0001")

# Supersede ADR
new_adr = ADREntity(id="ADR-0002", title="Use MongoDB instead")
new_id = await service.supersede_adr("ADR-0001", new_adr)

# Record decision from Q&A (convenience method)
adr_id = await service.record_decision(
    question="Which database?",
    answer="PostgreSQL for ACID compliance",
    trigger=ADRTrigger.CLARIFYING_QUESTION,
    source_task_id="TASK-001"
)
```

**Methods:**
- `create_adr(adr: ADREntity) -> Optional[str]`: Create new ADR
- `search_adrs(query: str, status: Optional[ADRStatus] = None, num_results: int = 10) -> List[ADREntity]`: Search ADRs
- `get_adr(adr_id: str) -> Optional[ADREntity]`: Get specific ADR
- `supersede_adr(old_adr_id: str, new_adr: ADREntity) -> Optional[str]`: Create superseding ADR
- `deprecate_adr(adr_id: str) -> Optional[bool]`: Mark ADR deprecated
- `record_decision(question, answer, trigger, **kwargs) -> Optional[str]`: Convenience method for Q&A decisions

### Outcome Capture

#### `OutcomeType`

Enum for outcome types.

```python
from guardkit.knowledge import OutcomeType

OutcomeType.TASK_COMPLETED   # Task finished successfully
OutcomeType.TASK_BLOCKED     # Task blocked by issue
OutcomeType.TASK_CANCELLED   # Task cancelled
OutcomeType.PHASE_COMPLETED  # Workflow phase completed
```

#### `TaskOutcome`

Dataclass for task outcomes.

```python
from guardkit.knowledge import TaskOutcome, OutcomeType
from datetime import datetime

outcome = TaskOutcome(
    id="OUT-A1B2C3D4",
    outcome_type=OutcomeType.TASK_COMPLETED,
    task_id="TASK-001",
    task_title="Implement OAuth2",
    task_requirements="Add OAuth2 authentication with PKCE flow",
    success=True,
    summary="Successfully implemented OAuth2",
    approach_used="Used passport.js library with custom strategy",
    patterns_used=["Strategy Pattern", "Dependency Injection"],
    problems_encountered=["CORS issues with redirect URIs"],
    lessons_learned=["Always test redirect URIs in production-like env"],
    tests_written=15,
    test_coverage=0.92,
    review_cycles=2,
    started_at=datetime(2024, 1, 15, 10, 0),
    completed_at=datetime(2024, 1, 15, 14, 30),
    duration_minutes=270,
    feature_id="FEAT-AUTH",
    related_adr_ids=["ADR-0042"]
)
```

**Fields:**
- `id` (str): Unique outcome ID
- `outcome_type` (OutcomeType): Type of outcome
- `task_id` (str): Related task ID
- `task_title` (str): Task title
- `task_requirements` (str): Task requirements
- `success` (bool): Whether outcome was successful
- `summary` (str): Brief summary
- `approach_used` (Optional[str]): Approach description
- `patterns_used` (Optional[List[str]]): Design patterns applied
- `problems_encountered` (Optional[List[str]]): Problems faced
- `lessons_learned` (Optional[List[str]]): Lessons learned
- `tests_written` (Optional[int]): Number of tests
- `test_coverage` (Optional[float]): Coverage percentage
- `review_cycles` (Optional[int]): Number of review cycles
- `started_at` (Optional[datetime]): Start time
- `completed_at` (Optional[datetime]): Completion time
- `duration_minutes` (Optional[int]): Duration in minutes
- `feature_id` (Optional[str]): Related feature ID
- `related_adr_ids` (Optional[List[str]]): Related ADR IDs

#### `capture_task_outcome`

Capture task outcome as episode.

```python
from guardkit.knowledge import capture_task_outcome, OutcomeType

outcome_id = await capture_task_outcome(
    outcome_type=OutcomeType.TASK_COMPLETED,
    task_id="TASK-001",
    task_title="Implement OAuth2",
    task_requirements="Add OAuth2 authentication",
    success=True,
    summary="Successfully implemented OAuth2 with PKCE",
    approach_used="passport.js with custom strategy",
    patterns_used=["Strategy Pattern"],
    problems_encountered=["CORS issues"],
    lessons_learned=["Test redirects in prod-like env"],
    tests_written=15,
    test_coverage=0.92
)
```

**Returns:** Unique outcome ID (format: OUT-XXXXXXXX)

**Graceful Degradation:** Returns ID even if Graphiti unavailable.

#### `find_similar_task_outcomes`

Search for similar task outcomes (future feature).

```python
from guardkit.knowledge import find_similar_task_outcomes

similar = await find_similar_task_outcomes(
    task_requirements="Implement OAuth2 authentication",
    limit=5
)

for outcome in similar:
    print(f"Task {outcome['task_id']}: {outcome['summary']}")
    print(f"Lessons: {outcome.get('lessons_learned', [])}")
```

## Integration Points

### task-work Integration (Phase 1)

Context loading happens at the start of Phase 1 (Planning):

```python
# In task-work command
from guardkit.knowledge import load_critical_context, format_context_for_injection

context = await load_critical_context(
    task_id=task_id,
    command="task-work"
)

context_text = format_context_for_injection(context)

# Inject context_text into planning phase prompt
# This ensures planning considers:
# - Quality gate requirements
# - Architectural constraints
# - Known failure patterns
# - Similar task outcomes
```

### feature-build Integration

Context loading happens before the Player-Coach loop:

```python
# In feature-build command
from guardkit.knowledge import (
    load_critical_context,
    load_feature_overview,
    load_role_context,
    load_failed_approaches,
    format_context_for_injection
)

# Load system context
system_context = await load_critical_context(
    task_id=task_id,
    feature_id=feature_id,
    command="feature-build"
)

# Load feature-build overview
overview = await load_feature_overview("feature-build")

# Load role constraints
player_constraints = await load_role_context("player", "feature-build")
coach_constraints = await load_role_context("coach", "feature-build")

# Load failure warnings
warnings = await load_failed_approaches("feature-build subprocess")

# Format and inject into Player and Coach agents
```

### Outcome Capture on Completion

When tasks complete, outcomes are captured:

```python
# In /task-complete command
from guardkit.knowledge import capture_task_outcome, OutcomeType

outcome_id = await capture_task_outcome(
    outcome_type=OutcomeType.TASK_COMPLETED,
    task_id=task_id,
    task_title=task_title,
    task_requirements=task_requirements,
    success=True,
    summary=summary,
    # ... additional fields from task metadata
)
```

### Turn State Capture (TASK-GE-002)

AutoBuild captures turn state for cross-turn learning:

```python
from guardkit.knowledge import capture_turn_state, create_turn_state_from_autobuild

# Create turn state from AutoBuild results
entity = create_turn_state_from_autobuild(
    feature_id="FEAT-GE",
    task_id="TASK-GE-001",
    turn_number=1,
    player_summary="Implemented feature",
    player_decision="implemented",
    coach_decision="approved"
)

# Capture to Graphiti
await capture_turn_state(graphiti, entity)
```

### /feature-plan Integration (FEAT-GR-003)

Context loading with Graphiti-enhanced context:

```python
# In /feature-plan command
from guardkit.knowledge.feature_detector import FeatureDetector
from guardkit.knowledge.job_context_retriever import JobContextRetriever

# Detect feature from description
detector = FeatureDetector(project_root)
feature_id = detector.detect_feature_id(description)

# Find feature spec and related features
feature_spec = detector.find_feature_spec(feature_id)
related_features = detector.find_related_features(feature_id)

# Retrieve enhanced context from Graphiti
retriever = JobContextRetriever(graphiti)
context = await retriever.retrieve(
    task={
        "id": feature_id,
        "description": description,
        "is_autobuild": True,
    },
    phase=TaskPhase.PLAN
)

# Context includes:
# - Related features from Graphiti
# - Relevant patterns for the task type
# - Role constraints for Player/Coach
# - Quality gate configs for this task type
# - Implementation mode guidance
```

### Interactive Knowledge Capture Integration (FEAT-GR-004)

Interactive capture in `/task-review --capture-knowledge`:

```python
from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
from guardkit.knowledge.gap_analyzer import KnowledgeCategory

# Run interactive capture session
session = InteractiveCaptureSession()
captured = await session.run_session(
    focus=KnowledgeCategory.ARCHITECTURE,
    max_questions=5,
    ui_callback=cli_callback
)

# Or run abbreviated capture after review
result = await session.run_abbreviated(
    questions=review_generated_questions,
    task_context={'task_id': task_id, 'review_mode': 'architectural'}
)

# Captured knowledge is automatically stored in Graphiti
# - Group ID mapped from category (e.g., ARCHITECTURE → project_architecture)
# - Facts extracted and prefixed with category context
# - Structured metadata includes entity_type, source, captured_at
```

### Job-Specific Context Retrieval Integration (FEAT-GR-006)

Context retrieval in `/task-work` and `/feature-build`:

```python
from guardkit.knowledge.job_context_retriever import JobContextRetriever
from guardkit.knowledge.task_analyzer import TaskPhase

# In task-work or feature-build
retriever = JobContextRetriever(graphiti)

# Retrieve context with characteristics-based allocation
context = await retriever.retrieve_parallel(
    task={
        "id": task_id,
        "description": task_description,
        "tech_stack": detected_stack,
        "complexity": complexity_score,
        "is_autobuild": is_autobuild_mode,
        "feature_id": feature_id,
        "turn_number": current_turn,
        "has_previous_turns": turn_number > 1,
    },
    phase=TaskPhase.IMPLEMENT,
    collect_metrics=True,  # For quality monitoring
)

# Budget automatically allocated based on:
# - Task complexity (2000-6000 base tokens)
# - Novelty adjustments (+30% first-of-type, +15% few similar)
# - Refinement adjustments (+20% for refinement attempts)
# - AutoBuild adjustments (+15% later turns, +10% with history)

# Inject context into prompt
prompt = f"""
{system_prompt}

{context.to_prompt()}

Task: {task_description}
"""
```

## Entity Models

### ADREntity

Complete field reference:

```python
@dataclass
class ADREntity:
    id: str                              # ADR-0001
    title: str                           # Decision title
    status: ADRStatus                    # ACCEPTED | SUPERSEDED | DEPRECATED
    trigger: ADRTrigger                  # What triggered this ADR
    source_task_id: Optional[str]        # Related task
    source_feature_id: Optional[str]     # Related feature
    source_command: Optional[str]        # Command that created ADR
    context: str                         # Why needed
    decision: str                        # What was decided
    rationale: str                       # Why this decision
    alternatives_considered: List[str]   # Alternatives evaluated
    consequences: List[str]              # Trade-offs
    supersedes: Optional[str]            # ADR ID this replaces
    superseded_by: Optional[str]         # ADR ID replacing this
    related_adrs: List[str]              # Related ADR IDs
    created_at: datetime                 # Creation time
    decided_at: Optional[datetime]       # Decision time
    deprecated_at: Optional[datetime]    # Deprecation time
    tags: List[str]                      # Categorization
    confidence: float                    # 0-1 confidence
```

### TaskOutcome

Complete field reference:

```python
@dataclass
class TaskOutcome:
    id: str                              # OUT-A1B2C3D4
    outcome_type: OutcomeType            # TASK_COMPLETED, etc.
    task_id: str                         # TASK-001
    task_title: str                      # Human-readable title
    task_requirements: str               # Original requirements
    success: bool                        # Outcome success
    summary: str                         # Brief summary
    approach_used: Optional[str]         # Approach description
    patterns_used: Optional[List[str]]   # Design patterns
    problems_encountered: Optional[List[str]]  # Problems faced
    lessons_learned: Optional[List[str]]       # Lessons learned
    tests_written: Optional[int]         # Number of tests
    test_coverage: Optional[float]       # Coverage (0-1)
    review_cycles: Optional[int]         # Review cycles
    started_at: Optional[datetime]       # Start time
    completed_at: Optional[datetime]     # End time
    duration_minutes: Optional[int]      # Duration
    feature_id: Optional[str]            # Related feature
    related_adr_ids: Optional[List[str]] # Related ADRs
    created_at: datetime                 # Record creation
```

### CriticalContext

Complete field reference:

```python
@dataclass
class CriticalContext:
    system_context: List[Dict[str, Any]]          # GuardKit identity
    quality_gates: List[Dict[str, Any]]           # Gate definitions
    architecture_decisions: List[Dict[str, Any]]  # MUST FOLLOW
    failure_patterns: List[Dict[str, Any]]        # DO NOT REPEAT
    successful_patterns: List[Dict[str, Any]]     # What worked
    similar_task_outcomes: List[Dict[str, Any]]   # Similar tasks
    relevant_adrs: List[Dict[str, Any]]           # Relevant ADRs
    applicable_patterns: List[Dict[str, Any]]     # Design patterns
    relevant_rules: List[Dict[str, Any]]          # Code rules
```

### FeatureOverviewEntity (TASK-GE-001)

Feature identity preservation:

```python
@dataclass
class FeatureOverviewEntity:
    id: str                    # feature-build
    name: str                  # Feature Build
    tagline: str               # One-line description
    purpose: str               # Why it exists
    what_it_is: List[str]      # Defining characteristics
    what_it_is_not: List[str]  # Explicit boundaries
    invariants: List[str]      # Never-violate rules
    architecture_summary: str  # High-level design
    key_components: List[str]  # Core components
    key_decisions: List[str]   # Critical design choices
    created_at: datetime       # Creation time
    updated_at: datetime       # Last update
```

### TurnStateEntity (TASK-GE-002)

Turn-by-turn state capture:

```python
@dataclass
class TurnStateEntity:
    turn_number: int           # Turn number
    mode: TurnMode             # standard | tdd | bdd
    player_summary: str        # What Player did
    player_decision: str       # Player's conclusion
    coach_decision: str        # Coach's verdict
    # ... additional fields
```

### FailedApproachEpisode (TASK-GE-004)

Failed approach capture:

```python
@dataclass
class FailedApproachEpisode:
    id: str                    # FAIL-001
    approach: str              # What was tried
    symptom: str               # Observable symptom
    root_cause: str            # Why it failed
    prevention: str            # How to prevent
    severity: Severity         # CRITICAL | HIGH | MEDIUM | LOW
    occurrence_count: int      # Times observed
    related_adrs: List[str]    # Related ADRs
    # ... additional fields
```

## Phase 2 Entity Models

### TaskCharacteristics (FEAT-GR-006)

Analyzed task properties for context retrieval decisions:

```python
from guardkit.knowledge.task_analyzer import TaskCharacteristics, TaskType, TaskPhase

@dataclass
class TaskCharacteristics:
    # Basic info
    task_id: str               # Task identifier (e.g., "TASK-001")
    description: str           # Task description text
    tech_stack: str            # Technology stack (e.g., "python", "typescript")

    # Classification
    task_type: TaskType        # IMPLEMENTATION | REVIEW | PLANNING | REFINEMENT | DOCUMENTATION
    current_phase: TaskPhase   # LOAD | PLAN | IMPLEMENT | TEST | REVIEW
    complexity: int            # Complexity score (1-10)

    # Novelty indicators
    is_first_of_type: bool     # True if no similar tasks exist in history
    similar_task_count: int    # Number of similar tasks found

    # Context indicators
    feature_id: Optional[str]  # Associated feature identifier
    is_refinement: bool        # True if refinement of previous attempt
    refinement_attempt: int    # Which refinement attempt (0 = first try)
    previous_failure_type: Optional[str]  # Type of previous failure (if refinement)

    # Historical performance
    avg_turns_for_type: float  # Historical average turns for this task type
    success_rate_for_type: float  # Historical success rate for this task type

    # AutoBuild context
    current_actor: str = "player"  # Current actor ("player" or "coach")
    turn_number: int = 0           # Current turn number
    is_autobuild: bool = False     # True if running in AutoBuild mode
    has_previous_turns: bool = False  # True if previous turns exist
```

### TaskType and TaskPhase Enums (FEAT-GR-006)

```python
from guardkit.knowledge.task_analyzer import TaskType, TaskPhase

class TaskType(str, Enum):
    """Classification of task types."""
    IMPLEMENTATION = "implementation"  # Building features, fixing bugs
    REVIEW = "review"                  # Analyzing architecture, making decisions
    PLANNING = "planning"              # Designing implementation approach
    REFINEMENT = "refinement"          # Improving or fixing previous attempt
    DOCUMENTATION = "documentation"    # Writing or updating documentation

class TaskPhase(str, Enum):
    """Execution phase within a task."""
    LOAD = "load"        # Initial context loading phase
    PLAN = "plan"        # Implementation planning phase
    IMPLEMENT = "implement"  # Code implementation phase
    TEST = "test"        # Testing and verification phase
    REVIEW = "review"    # Code review phase
```

### ContextBudget (FEAT-GR-006)

Budget allocation for context retrieval:

```python
from guardkit.knowledge.budget_calculator import ContextBudget

@dataclass
class ContextBudget:
    total_tokens: int          # Total token budget for context retrieval

    # Standard allocation percentages (must sum to 1.0)
    feature_context: float     # Allocation for feature context (0.0-1.0)
    similar_outcomes: float    # Allocation for similar task outcomes (0.0-1.0)
    relevant_patterns: float   # Allocation for relevant patterns (0.0-1.0)
    architecture_context: float  # Allocation for architecture context (0.0-1.0)
    warnings: float            # Allocation for warnings/failures (0.0-1.0)
    domain_knowledge: float    # Allocation for domain knowledge (0.0-1.0)

    # AutoBuild allocations (default to 0.0 for standard tasks)
    role_constraints: float = 0.0       # Allocation for role constraints
    quality_gate_configs: float = 0.0   # Allocation for quality gate configs
    turn_states: float = 0.0            # Allocation for turn states
    implementation_modes: float = 0.0   # Allocation for implementation modes

    def get_allocation(self, category: str) -> int:
        """Get token allocation for a category."""
        ...
```

### RetrievedContext (FEAT-GR-006)

Retrieved context data from Graphiti:

```python
from guardkit.knowledge.job_context_retriever import RetrievedContext

@dataclass
class RetrievedContext:
    task_id: str               # Task identifier
    budget_used: int           # Tokens used for context retrieval
    budget_total: int          # Total token budget available

    # Standard context categories
    feature_context: List[Dict[str, Any]]       # Feature-related context
    similar_outcomes: List[Dict[str, Any]]      # Similar task outcomes
    relevant_patterns: List[Dict[str, Any]]     # Relevant patterns
    architecture_context: List[Dict[str, Any]]  # Architecture context
    warnings: List[Dict[str, Any]]              # Warning/failure patterns
    domain_knowledge: List[Dict[str, Any]]      # Domain knowledge

    # AutoBuild context categories
    role_constraints: List[Dict[str, Any]] = field(default_factory=list)
    quality_gate_configs: List[Dict[str, Any]] = field(default_factory=list)
    turn_states: List[Dict[str, Any]] = field(default_factory=list)
    implementation_modes: List[Dict[str, Any]] = field(default_factory=list)

    # Quality metrics (optional, from TASK-GR6-011)
    quality_metrics: Optional[ContextQualityMetrics] = None

    def to_prompt(self) -> str:
        """Format retrieved context as a prompt string."""
        ...
```

### KnowledgeGap (FEAT-GR-004)

Represents a gap in project knowledge:

```python
from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

@dataclass
class KnowledgeGap:
    category: KnowledgeCategory  # Knowledge category this gap belongs to
    question: str                # Question to ask the user
    importance: str              # Priority level (high/medium/low)
    context: str                 # Explanation of why this question matters
    example_answer: Optional[str] = None  # Optional example of a good answer
```

### KnowledgeCategory Enum (FEAT-GR-004)

```python
from guardkit.knowledge.gap_analyzer import KnowledgeCategory

class KnowledgeCategory(str, Enum):
    """Categories of project knowledge."""
    PROJECT_OVERVIEW = "project_overview"
    ARCHITECTURE = "architecture"
    DOMAIN = "domain"
    CONSTRAINTS = "constraints"
    DECISIONS = "decisions"
    GOALS = "goals"
    # AutoBuild workflow customization categories
    ROLE_CUSTOMIZATION = "role_customization"
    QUALITY_GATES = "quality_gates"
    WORKFLOW_PREFERENCES = "workflow_preferences"
```

### CapturedKnowledge (FEAT-GR-004)

Represents captured knowledge from user input:

```python
from guardkit.knowledge.interactive_capture import CapturedKnowledge

@dataclass
class CapturedKnowledge:
    category: KnowledgeCategory  # Knowledge category this belongs to
    question: str                # Question that was asked
    answer: str                  # User's answer
    extracted_facts: List[str] = field(default_factory=list)  # Facts extracted from answer
    confidence: float = 1.0      # Confidence score (0.0-1.0)
```

## Phase 2 API Reference

### TaskAnalyzer (FEAT-GR-006)

Analyzes task characteristics for context retrieval decisions:

```python
from guardkit.knowledge.task_analyzer import TaskAnalyzer, TaskPhase, TaskCharacteristics

# Initialize with Graphiti client
analyzer = TaskAnalyzer(graphiti_client)

# Analyze task
task = {
    "id": "TASK-001",
    "description": "Implement user authentication",
    "tech_stack": "python",
    "complexity": 6,
}

characteristics = await analyzer.analyze(task, TaskPhase.IMPLEMENT)

# Check task properties
if characteristics.is_first_of_type:
    print("Novel task type - load more examples")

if characteristics.is_refinement:
    print(f"Refinement attempt {characteristics.refinement_attempt}")
```

**Methods:**

- `analyze(task: Dict, phase: TaskPhase) -> TaskCharacteristics`: Analyze task to determine characteristics

**Class Attributes:**

- `SIMILARITY_THRESHOLD = 0.7`: Threshold for counting similar tasks
- `DEFAULT_AVG_TURNS = 3.0`: Default average turns when no history
- `DEFAULT_SUCCESS_RATE = 0.8`: Default success rate when no history

### DynamicBudgetCalculator (FEAT-GR-006)

Calculates context budget based on task characteristics:

```python
from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator, ContextBudget

calculator = DynamicBudgetCalculator()
budget = calculator.calculate(characteristics)

# Get token allocation for a category
pattern_tokens = budget.get_allocation("relevant_patterns")
print(f"Pattern budget: {pattern_tokens} tokens")
```

**Methods:**

- `calculate(characteristics: TaskCharacteristics) -> ContextBudget`: Calculate budget based on characteristics

**Budget Adjustments:**

| Condition | Adjustment |
|-----------|------------|
| First-of-type (novelty) | +30% |
| Few similar tasks (<3) | +15% |
| Refinement attempt | +20% |
| AutoBuild later turns (>1) | +15% |
| Has previous turn history | +10% |

**Base Budgets by Complexity:**

| Complexity | Base Budget |
|------------|-------------|
| 1-3 (Simple) | 2000 tokens |
| 4-6 (Medium) | 4000 tokens |
| 7-10 (Complex) | 6000 tokens |

### JobContextRetriever (FEAT-GR-006)

Retrieves job-specific context from Graphiti:

```python
from guardkit.knowledge.job_context_retriever import JobContextRetriever, RetrievedContext
from guardkit.knowledge.task_analyzer import TaskPhase
from guardkit.knowledge.relevance_tuning import RelevanceConfig

# Default thresholds
retriever = JobContextRetriever(graphiti_client)

# Custom thresholds and cache TTL
config = RelevanceConfig(standard_threshold=0.7)
retriever = JobContextRetriever(graphiti_client, relevance_config=config, cache_ttl=600)

# Retrieve context
task = {
    "id": "TASK-001",
    "description": "Implement user authentication",
    "is_autobuild": True,
}

context = await retriever.retrieve(
    task,
    TaskPhase.IMPLEMENT,
    collect_metrics=True,  # Collect quality metrics
    early_termination=True,  # Stop when budget 95% full
)

# Use context in prompt
prompt_text = context.to_prompt()

# Check quality metrics
if context.quality_metrics and context.quality_metrics.is_quality_acceptable():
    print("Good quality context retrieved")

# Parallel retrieval (faster for multiple categories)
context = await retriever.retrieve_parallel(task, TaskPhase.IMPLEMENT)
```

**Methods:**

- `retrieve(task, phase, collect_metrics=False, early_termination=False) -> RetrievedContext`: Sequential retrieval
- `retrieve_parallel(task, phase, collect_metrics=False, early_termination=False) -> RetrievedContext`: Parallel retrieval using asyncio.gather()

**Features:**

- **Caching**: LRU cache with configurable TTL (default: 300s)
- **Relevance Filtering**: Configurable thresholds (standard: 0.6, first-of-type: 0.5)
- **Early Termination**: Stop when budget >= 95% full
- **Quality Metrics**: Optional collection for monitoring

### KnowledgeGapAnalyzer (FEAT-GR-004)

Identifies gaps in project knowledge:

```python
from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeCategory

analyzer = KnowledgeGapAnalyzer()

# Get all gaps (sorted by importance: high → medium → low)
gaps = await analyzer.analyze_gaps()

# Focus on specific category
arch_gaps = await analyzer.analyze_gaps(
    focus=KnowledgeCategory.ARCHITECTURE,
    max_questions=5
)

# Check gaps
for gap in gaps:
    print(f"[{gap.importance}] {gap.category}: {gap.question}")
```

**Methods:**

- `analyze_gaps(focus=None, max_questions=10) -> List[KnowledgeGap]`: Analyze and return knowledge gaps

**Supported Categories:**

- `PROJECT_OVERVIEW`, `ARCHITECTURE`, `DOMAIN`, `CONSTRAINTS`, `DECISIONS`, `GOALS`
- AutoBuild customization: `ROLE_CUSTOMIZATION`, `QUALITY_GATES`, `WORKFLOW_PREFERENCES`

### InteractiveCaptureSession (FEAT-GR-004)

Manages interactive knowledge capture sessions:

```python
from guardkit.knowledge.interactive_capture import InteractiveCaptureSession, CapturedKnowledge
from guardkit.knowledge.gap_analyzer import KnowledgeCategory

session = InteractiveCaptureSession()

# Define UI callback
def my_callback(event, data=None):
    if event == 'question':
        print(f"Q: {data['question']}")
    elif event == 'get_input':
        return input("> ")
    elif event == 'intro':
        print(data)
    elif event == 'summary':
        print(data)

# Run full session
captured = await session.run_session(
    focus=KnowledgeCategory.ARCHITECTURE,
    max_questions=5,
    ui_callback=my_callback
)

print(f"Captured {len(captured)} knowledge items")

# Or run abbreviated session with pre-defined questions
result = await session.run_abbreviated(
    questions=["What patterns were identified?", "What should be remembered?"],
    task_context={'task_id': 'TASK-001', 'review_mode': 'architectural'}
)
```

**Methods:**

- `run_session(focus=None, max_questions=10, ui_callback=None) -> List[CapturedKnowledge]`: Run interactive capture
- `run_abbreviated(questions, task_context=None) -> Dict[str, Any]`: Run abbreviated capture with pre-defined questions

**UI Callback Events:**

- `intro`: Session introduction message
- `question`: Question data dict with number, total, category, question, context
- `get_input`: Request user input (return answer string)
- `captured`: Captured knowledge confirmation
- `summary`: Session summary message
- `info`: Informational message

### FeatureDetector (FEAT-GR-003)

Detects feature specs from IDs and descriptions:

```python
from guardkit.knowledge.feature_detector import FeatureDetector
from pathlib import Path

detector = FeatureDetector(project_root=Path("/path/to/project"))

# Extract feature ID from description
feature_id = detector.detect_feature_id("Implement FEAT-GR-001 for graphiti")
# Returns: "FEAT-GR-001"

# Find feature spec file
spec_path = detector.find_feature_spec("FEAT-GR-001")
# Returns: Path to the spec file or None

# Find related features (same prefix)
related = detector.find_related_features("FEAT-GR-001")
# Returns: [Path("FEAT-GR-002-...md"), Path("FEAT-GR-003-...md")]
```

**Methods:**

- `detect_feature_id(description: str) -> Optional[str]`: Extract feature ID from text
- `find_feature_spec(feature_id: str) -> Optional[Path]`: Find feature spec file
- `find_related_features(feature_id: str) -> List[Path]`: Find features with same prefix

**Search Paths:**

- `docs/features`
- `.guardkit/features`
- `features`

## Extending the System

### Adding New Knowledge Categories

1. **Define the group_id:**

```python
# In your module
MY_CATEGORY_GROUP_ID = "my_custom_category"
```

2. **Create seeding function:**

```python
async def seed_my_category(client: GraphitiClient) -> None:
    """Seed my custom knowledge category."""
    episodes = [
        {
            "name": "concept_1",
            "body": "Description of concept 1..."
        },
        # More episodes
    ]

    for episode in episodes:
        await client.add_episode(
            name=episode["name"],
            episode_body=episode["body"],
            group_id=MY_CATEGORY_GROUP_ID
        )
```

3. **Add to orchestrator (optional):**

```python
# Create a new seed_*.py module (e.g., seed_my_category.py)
# Then register in seeding.py's categories list:
categories = [
    # ... existing categories
    ("my_category", "seed_my_category"),
]
# The orchestrator uses getattr() dispatch for testability
```

### Creating Custom Entities

1. **Define entity dataclass:**

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

@dataclass
class MyCustomEntity:
    id: str
    title: str
    content: str
    tags: List[str]
    created_at: datetime = field(default_factory=datetime.now)

    def to_episode_body(self) -> dict:
        """Return domain data only. GraphitiClient injects _metadata."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
        }
```

> **Convention (TASK-GBF-001)**: `to_episode_body()` returns **domain data only** as a dict. The `_metadata` block is injected by `GraphitiClient`, not by the entity.

2. **Create manager class:**

```python
from guardkit.knowledge import get_graphiti

class MyEntityManager:
    def __init__(self):
        self.group_id = "my_entities"

    async def create(self, entity: MyCustomEntity) -> Optional[str]:
        """Create entity in Graphiti."""
        client = get_graphiti()

        if client is None or not client.enabled:
            return None

        try:
            return await client.add_episode(
                name=f"{entity.id}: {entity.title}",
                episode_body=entity.to_episode_body(),
                group_id=self.group_id
            )
        except Exception as e:
            logger.warning(f"Failed to create entity: {e}")
            return None

    async def search(self, query: str, limit: int = 10) -> List[MyCustomEntity]:
        """Search for entities."""
        client = get_graphiti()

        if client is None or not client.enabled:
            return []

        try:
            results = await client.search(
                query=query,
                group_ids=[self.group_id],
                num_results=limit
            )

            # Parse results into entities
            entities = []
            for result in results:
                # Parse result['body'] into MyCustomEntity
                # ... implementation
                pass

            return entities
        except Exception as e:
            logger.warning(f"Failed to search entities: {e}")
            return []
```

### Seeding Custom Knowledge

1. **Create seeding script:**

```python
import asyncio
from guardkit.knowledge import init_graphiti, get_graphiti, GraphitiConfig

async def main():
    # Initialize client
    config = GraphitiConfig(enabled=True)
    await init_graphiti(config)

    client = get_graphiti()

    if client and client.enabled:
        # Seed your custom knowledge
        await seed_my_custom_knowledge(client)
        print("Seeding complete!")
    else:
        print("Graphiti not available")

async def seed_my_custom_knowledge(client):
    """Seed custom knowledge."""
    episodes = [
        {
            "name": "my_concept_1",
            "body": "Description...",
            "group_id": "my_category"
        },
        # More episodes
    ]

    for episode in episodes:
        await client.add_episode(
            name=episode["name"],
            episode_body=episode["body"],
            group_id=episode["group_id"]
        )

if __name__ == "__main__":
    asyncio.run(main())
```

2. **Run seeding:**

```bash
python seed_my_knowledge.py
```

---

**Note**: This architecture documentation reflects the current implementation as of the completion of FEAT-GI (Graphiti Integration), FEAT-GE (Graphiti Enhancements), and FEAT-GBF (Graphiti Baseline Fixes - unified serialization, seeding extraction). For setup instructions, see `docs/setup/graphiti-setup.md`. For usage guidance, see `docs/guides/graphiti-integration-guide.md`.
