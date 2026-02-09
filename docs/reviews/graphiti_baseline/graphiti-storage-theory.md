# Graphiti Storage Theory & Best Practices

> **Purpose**: Explains the data model rationale, episode structure theory, and extension guidelines for GuardKit's Graphiti integration.
> Suitable as `--context` input for `/feature-plan` commands extending Graphiti usage.
>
> **Companion Document**: [Graphiti Technical Reference](graphiti-technical-reference.md)

---

## 1. Why Graphiti? Design Rationale

### The Problem

Claude Code sessions are stateless. Each session starts with zero memory of previous sessions, leading to:
- **Repeated mistakes** - No memory of what failed before
- **Inconsistent decisions** - Same question answered differently each time
- **Lost context** - Architectural decisions made in one session are invisible to the next
- **No learning** - Successful patterns aren't captured for reuse

### Why a Knowledge Graph (Not a Document Store)

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| Flat files | Simple, version-controlled | No semantic search, no relationships | Too limited |
| Vector DB | Semantic search | No relationships, no temporal tracking | Missing structure |
| Knowledge Graph | Semantic search + relationships + temporal | More complex setup | **Chosen** |

Graphiti provides:
1. **Semantic search** - Find relevant knowledge by meaning, not keywords
2. **Temporal tracking** - Know when knowledge was created and if it's still valid
3. **Relationship modeling** - Connect decisions to outcomes, failures to fixes
4. **Group isolation** - Separate system knowledge from project knowledge
5. **Upsert semantics** - Update knowledge without duplicating

### Why `graphiti-core` (Not the REST API)

GuardKit uses the `graphiti-core` Python library directly rather than the Graphiti Docker REST API:

- **Direct Neo4j control** - Better error handling and connection management
- **Fewer moving parts** - No Docker container to manage for Graphiti server
- **Graceful degradation** - Can catch and handle exceptions at the Python level
- **Embedding control** - Configure embedding model directly
- **Still requires**: Neo4j instance + OpenAI API key for embeddings

---

## 2. Episode Structure Theory

### What is an Episode?

In Graphiti, an **episode** is the fundamental unit of knowledge. It's a chunk of text that gets:
1. **Embedded** - Converted to a vector for semantic search
2. **Entity-extracted** - Key entities and relationships identified
3. **Stored** - Persisted in Neo4j with metadata
4. **Grouped** - Assigned to a knowledge group for organization

### How GuardKit Uses Episodes

GuardKit stores everything as episodes, but distinguishes between **types** of knowledge:

```
Episode Types in GuardKit:
├── Static Knowledge (seeded once, rarely changes)
│   ├── Product Knowledge (what GuardKit is)
│   ├── Command Workflows (how commands connect)
│   ├── Quality Gate Phases (5-phase structure)
│   ├── Technology Stack (Python CLI, Claude Code, etc.)
│   ├── Architecture Decisions (key design choices)
│   └── Templates, Agents, Patterns, Rules (reference data)
│
├── Configuration Knowledge (seeded, may evolve)
│   ├── Role Constraints (Player/Coach boundaries)
│   ├── Quality Gate Configs (per-task-type thresholds)
│   └── Feature Overviews (feature identity and invariants)
│
└── Runtime Knowledge (captured during execution)
    ├── Task Outcomes (what happened when tasks completed/failed)
    ├── Turn States (what happened each turn of AutoBuild)
    ├── Failed Approaches (what went wrong and why)
    ├── ADRs (architecture decisions made during sessions)
    └── Interactive Capture (human-provided domain knowledge)
```

### Episode Body Structure

All GuardKit episodes use a JSON body with a consistent structure:

```json
{
  "title": "Human-readable title",
  "content": "The actual knowledge content (can be long)",
  "key_field_1": "Value specific to this entity type",
  "key_field_2": ["List values", "are common"],
  "_metadata": {
    "entity_id": "STABLE-ID-FOR-UPSERT",
    "source": "guardkit_seeding",
    "source_hash": "sha256...",
    "entity_type": "product_knowledge",
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-01-15T10:00:00Z"
  }
}
```

**Key design choices**:
- `_metadata` is prefixed with underscore to distinguish from content
- `_metadata` is injected by `GraphitiClient`, not by entity `to_episode_body()` methods (unified in TASK-GBF-001)
- `entity_id` is the stable key used for upsert operations
- `source_hash` enables change detection (skip if content unchanged)
- The episode `name` parameter is separate from the body and used for display

### Episode Size Guidelines

| Category | Typical Size | Notes |
|----------|-------------|-------|
| Product knowledge | 200-500 words | Concise overviews |
| Command workflows | 100-300 words | Step-by-step flows |
| Quality gate phases | 150-400 words | Rules and thresholds |
| Task outcomes | 300-800 words | Detailed metrics and lessons |
| Turn states | 200-600 words | Per-turn progress snapshots |
| Failed approaches | 150-400 words | Symptom → root cause → fix |
| Feature overviews | 400-1000 words | Comprehensive identity docs |
| Role constraints | 200-500 words | Boundary definitions |

**Rule of thumb**: Keep episodes focused on a single concept. If an episode exceeds ~1000 words, consider splitting into multiple episodes.

---

## 3. Data Model Deep Dive

### 3.1 Task Outcomes

**Purpose**: Record what happened when tasks completed or failed, enabling cross-task learning.

**When captured**: At task completion (success or failure) via `capture_task_outcome()`.

**Key fields**:
- `outcome_type` - COMPLETED, FAILED, REVIEW_PASSED, REVIEW_FAILED, etc.
- `success` - Boolean for quick filtering
- `approach_used` - What strategy was employed
- `patterns_used` - Which design patterns were applied
- `problems_encountered` - Issues hit during implementation
- `lessons_learned` - Takeaways for future tasks
- `test_coverage` - Coverage percentage achieved
- `duration_minutes` - How long the task took

**Search usage**: When starting a new task, `find_similar_task_outcomes()` searches for outcomes from similar tasks to inform the approach.

### 3.2 Feature Overviews

**Purpose**: Preserve feature identity and invariants across sessions.

**When captured**: Seeded at system initialization; updated when features evolve.

**Key fields**:
- `purpose` - Why this feature exists
- `what_it_is` / `what_it_is_not` - Positive and negative definitions
- `invariants` - Rules that MUST NOT be violated (critical for preventing drift)
- `key_components` - Architecture components
- `key_decisions` - ADR IDs for decision traceability

**Why invariants matter**: Without invariants, each session may "improve" a feature in ways that violate its core design. Invariants act as guardrails that persist across sessions.

### 3.3 Turn States

**Purpose**: Enable cross-turn learning in AutoBuild's Player-Coach loop.

**When captured**: After each Player-Coach turn via `capture_turn_state()`.

**Key fields**:
- `player_summary` - What the Player implemented
- `player_decision` / `coach_decision` - Outcome of the turn
- `coach_feedback` - What the Coach said (if feedback given)
- `mode` - FRESH_START, RECOVERING_STATE, or CONTINUING_WORK
- `acceptance_criteria_status` - Which criteria are met/unmet
- `files_modified` - What changed
- `lessons_from_turn` - What was learned

**Continuation context**: When Turn N starts, `load_turn_continuation_context()` loads Turn N-1's state, giving the Player context about what happened before.

### 3.4 Failed Approaches

**Purpose**: Prevent repeating mistakes across sessions.

**When captured**: When a significant failure is identified, via `capture_failed_approach()`.

**Key fields**:
- `approach` - What was tried
- `symptom` - What went wrong (observable behavior)
- `root_cause` - Why it failed (underlying reason)
- `fix_applied` - What worked instead
- `prevention` - How to avoid in future
- `severity` - LOW, MEDIUM, HIGH, CRITICAL
- `occurrences` - How many times this has happened
- `related_adrs` - ADR IDs encoding the decision

**Occurrence tracking**: If the same failure is encountered again, `increment_occurrence()` updates the count and timestamp rather than creating a duplicate.

### 3.5 Role Constraints

**Purpose**: Define hard boundaries for Player and Coach roles in AutoBuild.

**Structure**: Each constraint specifies:
- `must_do` - Actions the role is required to take
- `must_not_do` - Actions the role must never take
- `ask_before` - Actions requiring confirmation before proceeding
- `good_examples` / `bad_examples` - Concrete illustrations

**Predefined**:
- `PLAYER_CONSTRAINTS` - "Implement code changes, run tests, fix errors"
- `COACH_CONSTRAINTS` - "Review quality, provide feedback, approve/reject"

### 3.6 Quality Gate Configs

**Purpose**: Define quality thresholds that vary by task type and complexity.

**Structure**: Each config specifies which gates apply and their thresholds:
- `arch_review_required` / `arch_review_threshold` - Architecture review gate
- `test_pass_required` - All tests must pass
- `coverage_required` / `coverage_threshold` - Minimum test coverage
- `lint_required` - Linting must pass

**Predefined configs** (6):
- Scaffolding tasks (complexity 1-3): Minimal gates
- Feature tasks (complexity 1-3, 4-6, 7-10): Progressive gates
- Testing tasks: Standard test gates
- Documentation tasks: No code quality gates

---

## 4. Group ID Design

### Design Principles

1. **System vs Project separation**: System knowledge is global; project knowledge is namespaced
2. **Automatic prefixing**: Project groups get `{project_id}__` prefix automatically
3. **Semantic grouping**: Episodes are grouped by purpose, not by source
4. **Searchable**: Groups are used as filters in search queries

### How Group Selection Works

When calling `client.get_group_id()`:

```python
# System group (known list) - no prefix
client.get_group_id("product_knowledge")
# → "product_knowledge"

# Project group (known list) - auto-prefixed
client.get_group_id("project_overview")
# → "guardkit__project_overview"  (when project_id="guardkit")

# Explicit scope override
client.get_group_id("custom_group", scope="project")
# → "guardkit__custom_group"

client.get_group_id("custom_group", scope="system")
# → "custom_group"
```

### Known Project Groups

These group names are automatically detected as project-scoped:
- `project_overview`
- `project_architecture`
- `feature_specs`
- `project_decisions`
- `project_constraints`
- `domain_knowledge`

Any group not in this list defaults to system scope unless explicitly overridden.

---

## 5. Upsert Strategy

### The Problem

Seeding runs multiple times (re-seeding, updates). We need to:
1. Skip episodes that haven't changed (avoid noise in the graph)
2. Update episodes whose content has changed (keep knowledge current)
3. Create new episodes that don't exist yet

### The Solution: Content-Hash Upsert

```
For each episode to seed:
  1. Compute SHA256 of episode body → source_hash
  2. Search for existing episode with same entity_id in same group
  3. If found AND source_hash matches → SKIP (no change)
  4. If found AND source_hash differs → UPDATE (content changed)
  5. If not found → CREATE (new episode)
```

**Implementation**:

```python
# In graphiti_client.py
async def upsert_episode(self, name, episode_body, group_id, entity_id, ...):
    # Step 1: Check if exists
    exists_result = await self.episode_exists(entity_id, group_id, source_hash)

    if exists_result.exists and exists_result.exact_match:
        return UpsertResult(skipped=True)  # No change

    # Step 2: Create/update
    episode_id = await self.add_episode(name, episode_body, group_id, ...)
    return UpsertResult(
        created=not exists_result.exists,
        updated=exists_result.exists,
        uuid=episode_id
    )
```

### Why Content-Hash (Not Timestamps)

- Timestamps change even if content doesn't → false positives
- Content hash is deterministic → same content = same hash = skip
- Enables idempotent re-seeding without database state

---

## 6. Graceful Degradation Pattern

### Design Principle

> Graphiti is an **enhancement**, not a requirement. GuardKit must function fully without it.

### Implementation Pattern

Every function that touches Graphiti follows this pattern:

```python
async def some_operation(client: GraphitiClient, ...):
    """Operation with graceful degradation."""
    if not client or not client.enabled:
        logger.debug("Graphiti not available, skipping operation")
        return None  # or empty list, or default value

    try:
        result = await client.some_graphiti_call(...)
        return result
    except Exception as e:
        logger.warning(f"Graphiti operation failed: {e}")
        return None  # or empty list, or default value
```

### What This Means for Extensions

When adding new Graphiti functionality:
1. **Always check `client.enabled`** before operations
2. **Always wrap in try/except** with fallback return values
3. **Never raise exceptions** from Graphiti operations
4. **Log at debug/warning level** (not error) for Graphiti issues
5. **Provide meaningful defaults** when Graphiti is unavailable

---

## 7. Best Practices for Extending Graphiti Usage

### Adding a New Entity Type

1. **Create entity dataclass** in `guardkit/knowledge/entities/`:
   ```python
   @dataclass
   class NewEntity:
       id: str                     # Stable identifier
       # ... entity fields
       created_at: datetime = field(default_factory=datetime.now)
       updated_at: datetime = field(default_factory=datetime.now)

       def to_episode_body(self) -> dict:
           """Return domain data only. GraphitiClient injects _metadata."""
           return {
               "id": self.id,
               # ... domain fields only (no _metadata block)
           }
   ```

   > **Convention (TASK-GBF-001)**: `to_episode_body()` must return **domain data only**. The `_metadata` block (entity_type, created_at, updated_at, source_hash) is injected by `GraphitiClient`, not by the entity.

2. **Create operations module** in `guardkit/knowledge/`:
   ```python
   async def capture_new_entity(client, entity: NewEntity) -> Optional[str]:
       if not client or not client.enabled:
           return None
       try:
           body = json.dumps(entity.to_episode_body())
           return await client.upsert_episode(
               name=f"New Entity: {entity.id}",
               episode_body=body,
               group_id="new_entities",
               entity_id=entity.id,
               entity_type="new_entity",
           )
       except Exception as e:
           logger.warning(f"Failed to capture new entity: {e}")
           return None
   ```

3. **Register group ID** in `graphiti_client.py` system groups list (if system-scoped)

4. **Add to `__init__.py`** exports

5. **Create seed function** if initial data is needed

### Choosing a Group ID

- Use descriptive, snake_case names
- Match the entity type being stored
- Keep groups focused (one entity type per group when possible)
- For system knowledge: add to the system groups list in `graphiti_client.py`
- For project knowledge: add to the project groups list in `graphiti_client.py`

### Episode Content Guidelines

1. **Use JSON format** for structured data (enables field-level access)
2. **`_metadata` is injected by GraphitiClient** - do NOT include it in `to_episode_body()` (TASK-GBF-001 convention)
3. **Keep episodes focused** - one concept per episode
4. **Use meaningful names** - the `name` parameter is used in search results
5. **Provide entity_type** - enables type-specific formatting in CLI
6. **Use `to_episode_body()`** method on entities returning domain data only

### Search Query Patterns

```python
# Search by semantic meaning
results = await client.search("quality gate thresholds", group_ids=["quality_gate_configs"])

# Search across multiple groups
results = await client.search("authentication patterns", group_ids=[
    "architecture_decisions",
    "patterns",
    "task_outcomes"
])

# Search with relevance scoring
for r in results:
    if r["score"] > 0.8:
        # High relevance - include in context
        pass
    elif r["score"] > 0.5:
        # Medium relevance - include if budget allows
        pass
```

### Testing Conventions

- Mock `GraphitiClient` for unit tests (async mock)
- Test graceful degradation (client=None, client.enabled=False)
- Test entity serialization (`to_episode_body()` roundtrips)
- Use `guardkit graphiti verify` for integration testing against live Neo4j

---

## 8. Common Pitfalls

### Pitfall 1: Forgetting Graceful Degradation

**Wrong**:
```python
async def load_data(client):
    return await client.search("query")  # Crashes if client is None
```

**Right**:
```python
async def load_data(client):
    if not client or not client.enabled:
        return []
    try:
        return await client.search("query")
    except Exception:
        return []
```

### Pitfall 2: Mutable Default in Dataclass

**Wrong**:
```python
@dataclass
class Entity:
    tags: List[str] = []  # Shared across instances!
```

**Right**:
```python
@dataclass
class Entity:
    tags: List[str] = field(default_factory=list)
```

### Pitfall 3: Missing entity_id for Upsert

**Wrong**:
```python
await client.add_episode(name="data", episode_body=body, group_id="group")
# Creates a new episode every time - duplicates accumulate
```

**Right**:
```python
await client.upsert_episode(
    name="data",
    episode_body=body,
    group_id="group",
    entity_id="stable-unique-id"  # Enables deduplication
)
```

### Pitfall 4: Using System Group for Project Data

**Wrong**:
```python
await client.add_episode(..., group_id="feature_specs")
# Goes to project-prefixed group, even though you may not want that
```

**Right**:
```python
# Be explicit about scope
gid = client.get_group_id("feature_specs", scope="project")
await client.add_episode(..., group_id=gid)
```

### Pitfall 5: Episode Too Large

**Wrong**: Dumping entire file contents into a single episode.
**Right**: Extract key concepts and create focused episodes. If content exceeds ~1000 words, split into multiple related episodes in the same group.

---

## 9. Retrieval Fidelity

> **Key insight**: Graphiti extracts semantic facts, not verbatim content. It is a knowledge graph, not a document store.

Understanding what Graphiti can and cannot retrieve faithfully is critical for choosing the right storage strategy.

### What Graphiti Preserves

| Content Type | Fidelity | Example |
|-------------|----------|---------|
| Conceptual relationships | High | "OrchestrationState uses dataclasses for minimal state objects" |
| Design intent | High | "asdict() supports JSON serialization" |
| Entity/relationship facts | High | "EnhancementResult dataclass has a property called files" |
| Pattern applicability | High | "Use dataclass when simple internal state containers needed" |

### What Graphiti Does NOT Preserve

| Content Type | Fidelity | What Happens |
|-------------|----------|--------------|
| Code blocks | None | Syntax stripped; semantic facts extracted instead |
| Exact formatting | None | Indentation, whitespace, markdown lost |
| Import statements | None | Not preserved as retrievable content |
| Copy-paste usable snippets | None | Cannot reconstruct original code |

### When to Use Graphiti vs Static Files

| Use Case | Recommended Storage | Rationale |
|----------|-------------------|-----------|
| "Which pattern should I use?" | Graphiti | Semantic query → concept match |
| "Show me the code for X pattern" | Static file (path-gated `.md`) | Verbatim code retrieval required |
| "What failed last time?" | Graphiti | Semantic facts about failures |
| "What are the quality gate thresholds?" | Graphiti | Structured data with relationships |
| "Give me the exact dataclass template" | Static file | Copy-paste fidelity required |
| "How do components relate?" | Graphiti | Relationship discovery |

### The Semantic Extraction Pipeline

When an episode is added to Graphiti, it passes through:

```
Input: Raw episode content (text, code, JSON)
   ↓
Step 1: LLM entity/relationship extraction
   ↓
Step 2: Facts stored as graph nodes and edges
   ↓
Step 3: Embeddings generated for semantic search
   ↓
Output: Semantic facts (NOT the original content)
```

This means a 50-line Python code block becomes a set of facts like "OrchestrationState has a field named strategy" rather than the original `@dataclass` definition.

### Practical Guidance

1. **Store concepts in Graphiti** - "what patterns exist", "what decisions were made", "what failed"
2. **Store code in static files** - Pattern examples, templates, reference implementations
3. **Use Graphiti for routing** - Find the right pattern, then load the static file for code
4. **Path-gate static files** - Use conditional loading (`.claude/rules/patterns/`) to manage token budget

> **Full assessment**: See [Graphiti Code Retrieval Fidelity Assessment](../graphiti_enhancement/graphiti_code_retrieval_fidelity.md) for detailed test methodology and results.

---

## 10. Architecture Decisions

### ADR-1: Episodes Over Entities for Primary Storage

**Decision**: Store all knowledge as Graphiti episodes (not as separate Neo4j entities).

**Rationale**: Episodes provide built-in embedding, semantic search, temporal tracking, and group isolation. Creating custom Neo4j entities would require managing these features manually.

**Trade-off**: Some relational queries are less efficient (e.g., "find all outcomes for feature X" requires search rather than a direct relationship traversal). This is acceptable because semantic search is the primary access pattern.

### ADR-2: System/Project Group Split

**Decision**: Separate system knowledge (global) from project knowledge (namespaced).

**Rationale**: System knowledge about GuardKit itself should be shared across all projects. Project knowledge should be isolated to prevent cross-contamination.

**Implementation**: Automatic prefix with `{project_id}__` for project groups. Known project group names are hardcoded in `is_project_group()`.

### ADR-3: Content-Hash Upsert Over Timestamp Comparison

**Decision**: Use SHA256 content hashing for change detection, not timestamps.

**Rationale**: Timestamps change on every re-seed even if content is identical. Content hashing ensures truly idempotent seeding - same content always produces the same hash.

### ADR-4: Lazy Import for graphiti-core

**Decision**: Use lazy import (`_check_graphiti_core()`) rather than top-level import.

**Rationale**: `graphiti-core` is an optional dependency. Lazy import allows the module to load without it installed, enabling graceful degradation. The check is cached after first call.

### ADR-5: Per-Thread Factory Pattern for Client

**Decision**: Replace shared singleton with `GraphitiClientFactory` using `threading.local()` for per-thread client storage. Module-level `init_graphiti()` / `get_graphiti()` API preserved for backward compatibility.

**Rationale**: The original singleton bound a single Neo4j driver to one event loop. When `FeatureOrchestrator` runs tasks in parallel via `asyncio.to_thread()`, each worker thread creates its own event loop, causing cross-loop errors in the Neo4j driver. The factory pattern gives each thread its own `GraphitiClient` with its own Neo4j driver bound to that thread's event loop, while sharing the immutable `GraphitiConfig` (frozen dataclass) across threads.

**Supersedes**: Original singleton pattern (TASK-FIX-GTP1, resolving BUG-1 from TASK-REV-2AA0).

---

## 11. Extension Planning Checklist

When planning a new Graphiti integration area, consider:

- [ ] **Entity design**: What data needs to be stored? Define a dataclass with `to_episode_body()` returning domain data only
- [ ] **Serialization**: `to_episode_body()` must NOT include `_metadata` - client injects it
- [ ] **Group selection**: System or project scoped? New group or existing?
- [ ] **ID format**: What makes a stable, deterministic entity_id?
- [ ] **Capture timing**: When is the data produced? (task completion, session start, etc.)
- [ ] **Search patterns**: How will this data be retrieved? What queries?
- [ ] **Context loading**: Should this data be auto-loaded at session start?
- [ ] **Seeding**: Is there initial/static data to seed?
- [ ] **CLI exposure**: Should users be able to query this via CLI?
- [ ] **Graceful degradation**: What happens when Graphiti is unavailable?
- [ ] **Testing**: How to test without a live Neo4j instance?
