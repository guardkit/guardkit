# Unified Data Architecture: Tasks, Features, and Knowledge in Graphiti

> **Purpose**: Analyze whether GuardKit should pivot from separate task storage (markdown files + Beads) to a unified Graphiti-based architecture where tasks, features, and project knowledge live in the same graph.
>
> **Date**: January 2025
> **Status**: Decision Required
> **Recommendation**: **Yes - Pivot to Graphiti as unified data layer**

---

## The Current Fragmentation Problem

Looking at the current/planned architecture:

```
Data Store 1: Markdown Files (tasks/*.md, .guardkit/features/*.yaml)
    └── Source of truth for tasks and features
    └── Human-readable, git-versioned
    └── No relationships, no queryable context

Data Store 2: Beads (proposed .beads/)
    └── Graph-based task dependencies
    └── Cross-session memory
    └── Git-synced JSONL → SQLite
    └── Separate from project knowledge

Data Store 3: Graphiti (proposed)
    └── Project knowledge, patterns, outcomes
    └── Architecture decisions, failure patterns
    └── Temporal knowledge graph
    └── Separate from tasks
```

**Problems with this approach:**

1. **Can't query across domains**: "What patterns worked for tasks like this one?" requires joining across stores
2. **Duplicate sync complexity**: Three different sync mechanisms (file watch, git JSONL, Graphiti episodes)
3. **No task → outcome relationships**: Task completion doesn't link to what patterns were learned
4. **Beads reinvents the wheel**: Graphiti already has temporal entities, relationships, and git-friendly export

---

## What Beads Provides (That Graphiti Also Provides)

| Feature | Beads | Graphiti | Winner |
|---------|-------|----------|--------|
| **Graph-based dependencies** | ✅ 4 dependency types | ✅ Arbitrary edge types | Graphiti (more flexible) |
| **Cross-session memory** | ✅ SQLite + JSONL | ✅ FalkorDB + Episodes | Graphiti (semantic search) |
| **Git-versioned** | ✅ JSONL in git | ✅ Can export to git | Tie |
| **Hash-based IDs** | ✅ `bd-a1b2` | ✅ Entity UUIDs | Tie |
| **Ready work detection** | ✅ `bd ready` | ⚠️ Would need query | Beads (built-in) |
| **CLI for humans** | ✅ Full CLI | ⚠️ SDK only | Beads (CLI) |
| **Temporal invalidation** | ❌ Delete/close | ✅ `valid_at`/`invalid_at` | Graphiti |
| **Semantic search** | ❌ None | ✅ Embedding-based | Graphiti |
| **Entity extraction** | ❌ Manual | ✅ LLM-powered | Graphiti |
| **Cross-domain queries** | ❌ Tasks only | ✅ Tasks + knowledge | Graphiti |

**Key insight**: Graphiti can do everything Beads does, plus semantic search and cross-domain queries. Beads' main advantage is the polished CLI.

---

## The Unified Architecture Proposal

### Store EVERYTHING in Graphiti

```
Graphiti Knowledge Graph
├── Task Entities
│   ├── Properties: id, title, status, priority, complexity, acceptance_criteria
│   ├── Edges: BLOCKS, DEPENDS_ON, PARENT_OF, DISCOVERED_FROM
│   └── Temporal: created_at, updated_at, closed_at, valid_at, invalid_at
│
├── Feature Entities
│   ├── Properties: id, name, description, status
│   ├── Edges: CONTAINS_TASK, DEPENDS_ON_FEATURE
│   └── Temporal: created_at, completed_at
│
├── Outcome Episodes
│   ├── Task outcomes (what was implemented, how it went)
│   ├── Review decisions (what was approved/rejected)
│   ├── Patterns learned (what worked, what didn't)
│   └── Links to Task entities
│
├── Architecture Knowledge
│   ├── Decisions, integration points, patterns
│   ├── Links to Tasks that implemented them
│   └── Links to Outcomes that validated them
│
└── System Context
    ├── Product knowledge
    ├── Command workflows
    ├── Quality gate phases
    └── Technology stack
```

### Benefits of Unified Architecture

#### 1. Rich Cross-Domain Queries

```python
# "Find tasks similar to this one that succeeded"
results = await graphiti.search(
    query=f"task {task.description}",
    group_ids=["tasks", "task_outcomes", "successful_patterns"],
    num_results=10
)
# Returns: Similar tasks AND what patterns worked for them

# "What architecture decisions affect this feature?"
results = await graphiti.search(
    query=f"architecture {feature.name}",
    group_ids=["features", "architecture_decisions", "integration_points"]
)
# Returns: Feature details AND relevant architecture context
```

#### 2. Automatic Relationship Discovery

Graphiti's LLM-powered entity extraction can discover implicit relationships:

```python
# When a task is created with description "Add OAuth2 like we did for payments"
# Graphiti can extract: SIMILAR_TO relationship to previous OAuth task
# AND: Link to patterns that worked for payments auth
```

#### 3. Temporal Task History

```python
# "What was the task status a week ago?"
results = await graphiti.search(
    query=f"task {task_id}",
    reference_time=datetime(2025, 1, 4)  # Last week
)
# Returns: Task as it was at that point in time

# "Show me how this feature evolved"
# Returns: All task state changes, decisions made, patterns learned
```

#### 4. Ready Work with Context

```python
# Enhanced "ready" query
ready_tasks = await graphiti.search(
    query="task status:pending no-blockers",
    group_ids=["tasks"]
)

# For each ready task, get relevant context
for task in ready_tasks:
    context = await graphiti.search(
        query=task.description,
        group_ids=["task_outcomes", "patterns", "warnings"]
    )
    # Now we know: What worked for similar tasks, what to avoid
```

---

## Implementation Strategy

### Phase 1: Task Entities in Graphiti (Replace Markdown)

```python
@dataclass
class TaskEntity:
    """Task stored as Graphiti entity."""
    
    # Core fields (same as markdown frontmatter)
    id: str  # TASK-XXXX
    title: str
    status: TaskStatus
    priority: int
    complexity: int
    
    # Requirements (formerly markdown body)
    requirements: str
    acceptance_criteria: List[str]
    implementation_notes: Optional[str]
    
    # Relationships (formerly manual dependencies)
    blocks: List[str]  # Task IDs this blocks
    blocked_by: List[str]  # Task IDs blocking this
    parent_id: Optional[str]  # Feature or epic
    discovered_from: Optional[str]  # Source task
    
    # GuardKit-specific
    autobuild_state: Optional[Dict]
    quality_gate_results: Optional[Dict]
    
    # Temporal
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]

async def create_task(task: TaskEntity) -> str:
    """Create task as Graphiti entity."""
    
    await graphiti.add_episode(
        name=f"task_{task.id}",
        episode_body=json.dumps(asdict(task)),
        group_id="tasks"
    )
    
    # Add dependency edges
    for blocked_id in task.blocks:
        await graphiti.add_edge(
            source_id=task.id,
            target_id=blocked_id,
            edge_type="BLOCKS"
        )
    
    return task.id
```

### Phase 2: Feature Entities (Replace YAML)

```python
@dataclass
class FeatureEntity:
    """Feature stored as Graphiti entity."""
    
    id: str  # FEAT-XXXX
    name: str
    description: str
    status: FeatureStatus
    
    # Task relationships
    task_ids: List[str]
    parallel_groups: List[List[str]]
    
    # Metrics
    complexity: int
    estimated_hours: float
    actual_hours: Optional[float]

async def create_feature(feature: FeatureEntity) -> str:
    """Create feature with task relationships."""
    
    await graphiti.add_episode(
        name=f"feature_{feature.id}",
        episode_body=json.dumps(asdict(feature)),
        group_id="features"
    )
    
    # Add CONTAINS edges to tasks
    for task_id in feature.task_ids:
        await graphiti.add_edge(
            source_id=feature.id,
            target_id=task_id,
            edge_type="CONTAINS_TASK"
        )
    
    return feature.id
```

### Phase 3: Unified Query Interface

```python
class UnifiedKnowledgeStore:
    """Single interface for all GuardKit data."""
    
    async def get_task(self, task_id: str) -> TaskEntity:
        """Get task by ID."""
        results = await self.graphiti.search(
            query=f"task id:{task_id}",
            group_ids=["tasks"],
            num_results=1
        )
        return TaskEntity(**results[0])
    
    async def get_ready_tasks(self, limit: int = 10) -> List[TaskEntity]:
        """Get tasks with no blockers."""
        # Query for pending tasks
        pending = await self.graphiti.search(
            query="task status:pending",
            group_ids=["tasks"],
            num_results=50
        )
        
        # Filter to those with no blocking edges
        ready = []
        for task in pending:
            blockers = await self.graphiti.search(
                query=f"blocks:{task.id} status:open",
                group_ids=["tasks"]
            )
            if not blockers:
                ready.append(task)
                if len(ready) >= limit:
                    break
        
        return ready
    
    async def get_task_context(self, task_id: str) -> TaskContext:
        """Get task with all relevant knowledge context."""
        
        task = await self.get_task(task_id)
        
        # Get related knowledge in parallel
        similar_outcomes, patterns, warnings, architecture = await asyncio.gather(
            self.graphiti.search(
                query=task.requirements,
                group_ids=["task_outcomes"],
                num_results=5
            ),
            self.graphiti.search(
                query=task.requirements,
                group_ids=["patterns"],
                num_results=5
            ),
            self.graphiti.search(
                query=task.requirements,
                group_ids=["failure_patterns", "warnings"],
                num_results=5
            ),
            self.graphiti.search(
                query=task.requirements,
                group_ids=["architecture_decisions"],
                num_results=3
            )
        )
        
        return TaskContext(
            task=task,
            similar_outcomes=similar_outcomes,
            applicable_patterns=patterns,
            warnings=warnings,
            architecture_context=architecture
        )
```

---

## Migration Path from Markdown

### Backward Compatibility Layer

```python
class TaskStore:
    """Unified interface supporting both backends during migration."""
    
    def __init__(self, backend: str = "auto"):
        if backend == "auto":
            backend = self._detect_backend()
        
        if backend == "graphiti":
            self._store = GraphitiTaskStore()
        else:
            self._store = MarkdownTaskStore()
    
    def _detect_backend(self) -> str:
        """Detect which backend to use."""
        if os.path.exists(".guardkit/knowledge/graphiti.yaml"):
            return "graphiti"
        return "markdown"
    
    async def create_task(self, **kwargs) -> str:
        return await self._store.create_task(**kwargs)
    
    async def get_task(self, task_id: str) -> TaskEntity:
        return await self._store.get_task(task_id)
```

### Migration Command

```bash
# Migrate existing tasks to Graphiti
guardkit migrate --to graphiti

# What it does:
# 1. Reads all tasks/*.md files
# 2. Creates TaskEntity for each
# 3. Extracts and creates edges for dependencies
# 4. Reads all .guardkit/features/*.yaml files
# 5. Creates FeatureEntity for each
# 6. Links features to tasks
# 7. Archives old files (doesn't delete)
```

---

## What Happens to Beads Integration?

### Option A: Don't Integrate Beads (Recommended)

Graphiti provides everything Beads does, plus:
- Semantic search across all knowledge
- Cross-domain queries (tasks + patterns + outcomes)
- Temporal invalidation
- LLM-powered entity extraction

**The only thing we lose**: Beads' polished CLI (`bd ready`, `bd create`, etc.)

**Solution**: Build equivalent CLI commands for Graphiti-backed tasks:
```bash
guardkit task ready          # Equivalent to bd ready
guardkit task create "..."   # Equivalent to bd create
guardkit task show TASK-XXX  # Equivalent to bd show
```

### Option B: Beads as Sync Target (Optional Future)

If team members want to use Beads' CLI:
```
Graphiti (source of truth)
    ↓ sync
Beads (.beads/beads.jsonl)
    ↓
bd CLI for human interaction
```

But this adds complexity without clear benefit.

---

## Decision Matrix

| Approach | Complexity | Query Power | Maintenance | Recommendation |
|----------|------------|-------------|-------------|----------------|
| **Markdown + Beads + Graphiti** | High (3 stores) | Limited | High | ❌ |
| **Markdown + Graphiti** | Medium | Good | Medium | ⚠️ Transitional |
| **Graphiti only** | Low | Excellent | Low | ✅ Recommended |
| **Beads + Graphiti** | Medium | Good | Medium | ❌ Redundant |

---

## Recommended Path Forward

### Immediate (This Week)

1. **Pause Beads integration tasks** - Don't start TASK-BI-* series
2. **Implement Graphiti task storage** - TaskEntity as described above
3. **Add CLI commands** - `guardkit task ready|create|show|update`
4. **Migration tooling** - Import existing markdown tasks into Graphiti

### Short-Term (Next 2 Weeks)

5. **Feature entities** - FeatureEntity with task relationships
6. **Cross-domain queries** - Task context with patterns and outcomes
7. **Ready work detection** - Blocker-aware task selection

### Medium-Term (With DeepAgents)

8. **Full GraphitiMiddleware** - As designed in architecture doc
9. **Archive Beads tasks** - Mark as superseded
10. **Document the unified architecture** - Update all docs

---

## Impact on Existing Plans

### Beads Integration Tasks

| Task | Status | Action |
|------|--------|--------|
| TASK-BI-001: TaskBackend interface | Backlog | **Supersede** - Use Graphiti entities instead |
| TASK-BI-002: MarkdownBackend | Backlog | **Supersede** - Keep as migration source only |
| TASK-BI-003: BeadsBackend | Backlog | **Cancel** - Not needed |
| TASK-BI-004: Backend registry | Backlog | **Supersede** - Single Graphiti backend |
| TASK-BI-005: Configuration | Backlog | **Adapt** - Configure Graphiti instead |
| TASK-BI-006-011 | Backlog | **Cancel** - Not needed |

### Graphiti Integration Tasks

**Keep all Graphiti integration tasks** - They become MORE important:
- System context seeding ✅
- Session context loading ✅
- Episode capture ✅
- Now ALSO: Task/feature entity storage

---

## Conclusion

**Recommendation: Pivot to Graphiti as unified data layer.**

The insight is correct: having tasks in markdown/Beads while knowledge is in Graphiti creates fragmentation that limits the power of both systems. Graphiti can store tasks as entities with relationships, providing:

1. **Single source of truth** - No sync complexity
2. **Cross-domain queries** - Tasks linked to outcomes and patterns
3. **Semantic search** - Find tasks by meaning, not just ID
4. **Temporal history** - Full task evolution over time
5. **Relationship discovery** - LLM can find implicit connections

The Beads integration effort (~20-28 hours) is better spent building Graphiti task storage + CLI commands, which provides more capability with less architectural complexity.

---

---

## Templates, Agents, and Rules: What Stays Markdown vs Graphiti

You're right to think about `/template-create` and `/agent-enhance`. The key distinction:

### Must Stay as Markdown (Claude Code reads directly)

| Content | Location | Why Markdown |
|---------|----------|-------------|
| **Subagent definitions** | `.claude/agents/*.md` | Claude Code loads these to adopt personas |
| **Slash commands** | `.claude/commands/*.md` | Claude Code loads these as available commands |
| **CLAUDE.md** | `CLAUDE.md` | Claude Code loads this as project context |
| **Rules (glob-matched)** | `.claude/rules/*.md` | Claude Code applies these based on file paths |

These MUST remain as markdown because Claude Code's loader reads them directly. We can't change that.

### Should Move to Graphiti (queryable/searchable metadata)

| Content | Current Location | Why Graphiti |
|---------|-----------------|-------------|
| **Pattern definitions** | manifest.json `patterns[]` | Semantic search for "what patterns apply here?" |
| **Template metadata** | manifest.json | Search across all templates by capability |
| **Framework knowledge** | manifest.json `frameworks[]` | "What templates use SQLAlchemy 2.0?" |
| **Quality scores** | manifest.json `quality_scores` | Track quality evolution over time |
| **Agent capabilities** | Agent file headers | "Which agent handles database migrations?" |
| **Rule applicability** | Rule file frontmatter | "What rules apply to async Python?" |
| **Code examples** | CLAUDE.md sections | Semantic search for "how to do X in this stack" |
| **Anti-patterns** | Various | "What NOT to do" queries |

### The Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code Session                          │
│                                                                  │
│  1. Load .claude/agents/*.md (direct file read)                  │
│  2. Load .claude/rules/*.md (glob-matched)                       │
│  3. Load CLAUDE.md (project context)                             │
│                                                                  │
│  4. Query Graphiti for ADDITIONAL context:                       │
│     - "What patterns apply to this task?"                        │
│     - "What templates have similar implementations?"             │
│     - "What anti-patterns to avoid?"                             │
│     - "What did we learn from similar tasks?"                    │
└─────────────────────────────────────────────────────────────────┘
```

### Template Entity in Graphiti

```python
@dataclass
class TemplateEntity:
    """Template stored as Graphiti entity for querying."""
    
    # Core identity
    id: str  # "fastapi-python"
    name: str  # "Python FastAPI Backend"
    description: str
    
    # Searchable metadata
    language: str  # "Python"
    frameworks: List[FrameworkInfo]  # [{name: "FastAPI", version: ">=0.104.0"}]
    patterns: List[str]  # ["Dependency Injection", "Repository Pattern"]
    layers: List[str]  # ["api", "crud", "models", "schemas"]
    tags: List[str]  # ["python", "fastapi", "async"]
    
    # Quality tracking
    quality_scores: Dict[str, int]  # {"solid_compliance": 90, "dry_compliance": 85}
    complexity: int
    production_ready: bool
    
    # Relationships (edges in graph)
    # USES_PATTERN -> PatternEntity
    # USES_FRAMEWORK -> FrameworkEntity
    # SIMILAR_TO -> TemplateEntity
    # DERIVED_FROM -> TemplateEntity

async def sync_template_to_graphiti(template_path: Path):
    """Sync template manifest to Graphiti."""
    
    manifest = json.load(open(template_path / "manifest.json"))
    
    entity = TemplateEntity(
        id=manifest["name"],
        name=manifest["display_name"],
        description=manifest["description"],
        language=manifest["language"],
        frameworks=manifest["frameworks"],
        patterns=manifest["patterns"],
        layers=manifest["layers"],
        tags=manifest["tags"],
        quality_scores=manifest["quality_scores"],
        complexity=manifest["complexity"],
        production_ready=manifest["production_ready"]
    )
    
    await graphiti.add_episode(
        name=f"template_{entity.id}",
        episode_body=json.dumps(asdict(entity)),
        group_id="templates"
    )
    
    # Add pattern edges
    for pattern in entity.patterns:
        await graphiti.add_edge(
            source_id=entity.id,
            target_id=f"pattern_{pattern.lower().replace(' ', '_')}",
            edge_type="USES_PATTERN"
        )
```

### Agent Entity in Graphiti

```python
@dataclass
class AgentEntity:
    """Agent metadata stored as Graphiti entity."""
    
    # Core identity
    id: str  # "fastapi-specialist"
    name: str  # "FastAPI Specialist"
    role: str  # "Implements FastAPI routes and dependencies"
    
    # Capabilities (searchable)
    capabilities: List[str]  # ["routing", "dependency injection", "middleware"]
    technologies: List[str]  # ["FastAPI", "Pydantic", "SQLAlchemy"]
    file_patterns: List[str]  # ["router.py", "dependencies.py"]
    
    # Boundaries
    always_do: List[str]  # ["Use async def for routes"]
    never_do: List[str]  # ["Don't use global state"]
    ask_before: List[str]  # ["Adding new middleware"]
    
    # Relationships
    # PART_OF_TEMPLATE -> TemplateEntity
    # HANDLES_PATTERN -> PatternEntity
    # COLLABORATES_WITH -> AgentEntity

async def sync_agent_to_graphiti(agent_path: Path, template_id: str):
    """Extract agent metadata and sync to Graphiti."""
    
    content = agent_path.read_text()
    metadata = extract_agent_metadata(content)  # Parse frontmatter + sections
    
    entity = AgentEntity(
        id=f"{template_id}_{agent_path.stem}",
        name=metadata["name"],
        role=metadata["role"],
        capabilities=metadata.get("capabilities", []),
        technologies=metadata.get("technologies", []),
        file_patterns=metadata.get("file_patterns", []),
        always_do=metadata.get("always_do", []),
        never_do=metadata.get("never_do", []),
        ask_before=metadata.get("ask_before", [])
    )
    
    await graphiti.add_episode(
        name=f"agent_{entity.id}",
        episode_body=json.dumps(asdict(entity)),
        group_id="agents"
    )
```

### Rule Entity in Graphiti

```python
@dataclass
class RuleEntity:
    """Rule metadata for semantic search."""
    
    id: str  # "fastapi-python_code-style"
    name: str  # "Python Code Style"
    template_id: str  # "fastapi-python"
    
    # Applicability (from frontmatter)
    path_patterns: List[str]  # ["**/*.py"]
    
    # Content summary (for semantic search)
    topics: List[str]  # ["naming conventions", "class patterns", "async"]
    key_rules: List[str]  # ["Use snake_case for functions", "PascalCase for classes"]
    
    # Examples (extracted from content)
    code_examples: List[Dict]  # [{pattern: "...", example: "..."}]
```

### Pattern Entity in Graphiti

```python
@dataclass
class PatternEntity:
    """Design pattern knowledge."""
    
    id: str  # "dependency_injection"
    name: str  # "Dependency Injection"
    category: str  # "structural"
    
    # Knowledge
    description: str
    benefits: List[str]
    use_when: List[str]
    avoid_when: List[str]
    
    # Examples per stack
    examples: Dict[str, str]  # {"fastapi": "def get_db(): yield session"}
    
    # Relationships
    # USED_BY_TEMPLATE -> TemplateEntity
    # RELATED_TO -> PatternEntity
    # SUCCESSFUL_IN_TASK -> TaskEntity (from outcomes)
```

### How This Enables Better Queries

```python
# "What template should I use for a Python async API?"
results = await graphiti.search(
    query="Python async API REST",
    group_ids=["templates"],
    num_results=5
)
# Returns: fastapi-python, flask-async, etc. with quality scores

# "What patterns does this template use?"
results = await graphiti.search(
    query=f"template {template_id} patterns",
    group_ids=["templates", "patterns"]
)
# Returns: Template with linked patterns and their descriptions

# "Which agent handles database migrations?"
results = await graphiti.search(
    query="database migrations alembic",
    group_ids=["agents"]
)
# Returns: fastapi-database-specialist with capabilities

# "What rules apply to async Python code?"
results = await graphiti.search(
    query="async await Python rules",
    group_ids=["rules"]
)
# Returns: Relevant rules from all templates

# "Show me dependency injection examples for FastAPI"
results = await graphiti.search(
    query="dependency injection FastAPI example",
    group_ids=["patterns", "rules"]
)
# Returns: Pattern definition + code examples from rules
```

### Integration with `/template-create`

```python
# After template-create generates files:
async def post_template_create(template_path: Path):
    """Sync new template to Graphiti."""
    
    # 1. Sync template manifest
    await sync_template_to_graphiti(template_path)
    
    # 2. Sync all agents
    for agent_path in (template_path / "agents").glob("*.md"):
        await sync_agent_to_graphiti(agent_path, template_path.name)
    
    # 3. Sync all rules
    for rule_path in (template_path / ".claude" / "rules").rglob("*.md"):
        await sync_rule_to_graphiti(rule_path, template_path.name)
    
    # 4. Extract and sync patterns (from manifest + CLAUDE.md)
    await extract_and_sync_patterns(template_path)
```

### Integration with `/agent-enhance`

```python
# When enhancing an agent:
async def enhance_agent_with_graphiti(agent_path: Path, template_id: str):
    """Use Graphiti to inform agent enhancement."""
    
    # 1. Get current agent metadata
    current = await graphiti.search(
        query=f"agent {template_id}_{agent_path.stem}",
        group_ids=["agents"]
    )
    
    # 2. Find related agents for inspiration
    related = await graphiti.search(
        query=f"agent {current.capabilities} {current.technologies}",
        group_ids=["agents"],
        num_results=5
    )
    
    # 3. Get successful patterns from outcomes
    patterns = await graphiti.search(
        query=f"pattern successful {current.technologies}",
        group_ids=["task_outcomes", "patterns"]
    )
    
    # 4. Enhance agent with discovered knowledge
    enhancements = generate_enhancements(current, related, patterns)
    
    # 5. Update agent file (still markdown for Claude Code)
    update_agent_file(agent_path, enhancements)
    
    # 6. Sync updated metadata to Graphiti
    await sync_agent_to_graphiti(agent_path, template_id)
```

---

---

## Strategic Context and Constraints

### Why We're Doing This

The primary motivation for Graphiti integration is **NOT** to replace markdown task files or build elaborate CLI tooling. It's to solve a specific problem:

> Claude Code sessions lose context about what GuardKit is, how it works, and what decisions were made - causing them to make locally-optimal choices that break the overall system.

This has been painfully evident in attempts to build the `/feature-build` command using the Claude Agents SDK, where sessions repeatedly:
- Chose subprocess CLI invocation instead of SDK `query()`
- Used wrong worktree path structures (TASK-XXX instead of FEAT-XXX)
- Reimplemented functionality instead of delegating to existing commands
- Lost track of architectural decisions made in previous sessions

### Strategic Goals

1. **Fix the memory/context problem** so `/feature-build` can successfully build Deep Agents GuardKit
2. **Don't over-invest** in Claude Code GuardKit - it may become a legacy project
3. **Learn and prepare** for Deep Agents version (LangChain/LangGraph)
4. **Exit strategy** from Claude Max subscription dependency

### Why Deep Agents GuardKit?

The Claude Code markdown-based GuardKit is a stepping stone. The real target is **Deep Agents GuardKit** built on LangChain/LangGraph, motivated by:

1. **Subscription Risk**: Need a way off Claude Max subscription if prices rise too high
2. **Data Security**: For enterprise work, need private LLM deployment (local or Amazon Bedrock)
3. **Learning**: Gaining agentic development experience with production-grade frameworks
4. **Independence**: Model-agnostic architecture that isn't locked to Anthropic

The frustrating experience building `/feature-build` has been valuable learning - it exposed exactly what context and memory systems are needed for multi-session agentic workflows.

### What This Means for Scope

**We do NOT need:**
- ❌ Task storage in Graphiti (markdown tasks work fine)
- ❌ Feature storage in Graphiti (YAML features work fine)
- ❌ CLI commands (we use Claude Code, not CLI)
- ❌ Migration tooling (nothing to migrate)
- ❌ Elaborate entity management

**We DO need:**
- ✅ Graphiti running and queryable
- ✅ System context seeded (what GuardKit IS, how commands flow)
- ✅ Session context loading (so Claude Code sessions start informed)
- ✅ ADRs captured (so decisions aren't lost between sessions)
- ✅ Outcomes captured (so we learn from what worked/didn't)
- ✅ Template/agent metadata queryable (for context-aware development)

---

## Revised Feature List (Minimal Viable Scope)

Based on the strategic context, here are the **7 features** actually needed:

| # | Feature | Why We Need It |
|---|---------|----------------|
| 1 | **Graphiti Core Infrastructure** | Foundation - need Graphiti running |
| 2 | **System Context Seeding** | Seeds "what GuardKit is" so sessions have big picture |
| 3 | **Session Context Loading** | Injects context at session start - THE ACTUAL FIX |
| 4 | **ADR Lifecycle Management** | Captures decisions so they're not lost |
| 5 | **Episode Capture (Outcomes)** | Records what worked/didn't for future sessions |
| 6 | **Template/Agent Sync** | Keeps template knowledge queryable |
| 7 | **ADR Discovery from Code** | Discovers implicit decisions from /template-create |

### Implementation Priority

```
Feature 1: Core Infrastructure (foundation)
    ↓
Feature 2: System Context Seeding (seed the knowledge)
    ↓
Feature 3: Session Context Loading (USE the knowledge) ← THIS IS THE FIX
    ↓
Feature 4: ADR Lifecycle (capture new decisions)
    ↓
Feature 5: Episode Capture (learn from outcomes)
    ↓
Feature 6: Template/Agent Sync (keep templates queryable)
    ↓
Feature 7: ADR Discovery (discover implicit decisions)
```

**Features 1-3 are the critical path** to fixing the memory problem.
**Features 4-7 make the system learn and improve** over time.

### What We're NOT Building

| Dropped Capability | Reason |
|-------------------|--------|
| Task Entity Storage | Markdown tasks work fine, not worth investment |
| Feature Entity Storage | YAML features work fine |
| Task CLI Commands | Using Claude Code, not CLI |
| Feature CLI Commands | Using Claude Code, not CLI |
| ADR CLI Commands | Can query via Claude Code sessions |
| Migration Tooling | Nothing to migrate |
| ADR Conflict Detection | Nice-to-have, add later if needed |

---

## Architecture Decision Records (ADRs) in Graphiti

### Two Types of ADRs

| Type | Source | Example | Characteristics |
|------|--------|---------|----------------|
| **Discovered ADR** | `/template-create` analyzing existing code | "We use repository pattern" | Implicit, inferred from code, may lack rationale |
| **Explicit ADR** | Human decision during `/feature-plan` or `/task-review` | "Use repository pattern because..." | Explicit, has rationale, has alternatives considered |

### ADR Entity Structure

```python
@dataclass
class ADREntity:
    id: str  # ADR-XXXX
    title: str
    status: ADRStatus  # PROPOSED, ACCEPTED, DEPRECATED, SUPERSEDED
    
    # Source type
    source_type: ADRSourceType  # DISCOVERED, EXPLICIT
    
    # For DISCOVERED ADRs
    discovered_from: Optional[str]  # "template-create analysis of repo X"
    code_evidence: Optional[List[str]]  # File patterns that support this
    confidence: Optional[float]  # How confident are we this is intentional?
    
    # For EXPLICIT ADRs
    context: Optional[str]
    trigger: Optional[ADRTrigger]  # CLARIFYING_QUESTION, TASK_REVIEW, IMPLEMENTATION_CHOICE
    rationale: Optional[str]
    alternatives_considered: Optional[List[str]]
    
    # Relationships
    validates: Optional[str]  # Discovered ADR validates Explicit ADR
    validated_by: Optional[str]  # Explicit ADR validated by Discovered ADR
    supersedes: Optional[str]
    superseded_by: Optional[str]
    
    # Context
    source_task_id: Optional[str]
    source_feature_id: Optional[str]
    source_template_id: Optional[str]
    
    # Temporal
    created_at: datetime
    decided_at: Optional[datetime]
```

### ADR Creation Triggers

| Trigger Point | Decision Type | Example |
|--------------|---------------|--------|
| `/feature-plan` clarifying question answered | Scope decision | "Include OAuth but defer MFA to Phase 2" |
| `/task-review` acceptance | Implementation approach | "Use repository pattern for data access" |
| `/task-review` rejection with alternative | Rejected approach | "Don't use raw SQL, use ORM instead" |
| `/task-work` Phase 2.8 plan approval | Implementation plan | "Split into 3 components: X, Y, Z" |
| `/task-work` implementation choice | Technical decision | "Use asyncio.gather for parallel calls" |
| `/template-create` code analysis | Discovered pattern | "Codebase uses dependency injection" |

### Decisions Discovered by `/template-create`

When `/template-create` analyzes an existing codebase, it reverse-engineers architectural decisions:

**Structural Decisions** (from directory analysis):
- "We use feature-based organization with standard file naming"
- "We use monorepo structure with shared packages"

**Technology Decisions** (from dependencies/imports):
- "We chose async Python stack with typed ORM"
- "We chose React with server state management (not Redux)"

**Pattern Decisions** (from code analysis):
- "We use dependency injection for database sessions"
- "We use generic CRUD base classes for DRY"

**Convention Decisions** (from naming patterns):
- "Pydantic schemas follow {Entity}{Operation} naming"
- "Dependencies use get_ prefix"

These discovered ADRs are stored with `source_type=DISCOVERED` and can later be linked to explicit ADRs that validate or conflict with them.

---

## Next Steps

1. ✅ **Decision approved** - Proceed with minimal 7-feature scope
2. **Create feature specification documents** for `/feature-plan`:
   - FEAT-GI-001: Graphiti Core Infrastructure
   - FEAT-GI-002: System Context Seeding
   - FEAT-GI-003: Session Context Loading
   - FEAT-GI-004: ADR Lifecycle Management
   - FEAT-GI-005: Episode Capture (Outcomes)
   - FEAT-GI-006: Template/Agent Sync
   - FEAT-GI-007: ADR Discovery from Code
3. Use `/feature-plan` to generate task breakdowns for each feature
4. Build features 1-3 first (critical path to fixing memory problem)
