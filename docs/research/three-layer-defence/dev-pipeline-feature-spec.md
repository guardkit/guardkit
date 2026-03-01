# Feature Specification: Three-Layer Build Defence — dev-pipeline

**Date:** March 2026  
**Author:** Rich (with Claude AI assistance)  
**Status:** Ready for Implementation (Phase B — after empirical data from guardkit instrumentation)  
**Research Method:** Claude Desktop (extended thinking) → GuardKit `/feature-plan`  
**Target Repo:** `appmilla/dev-pipeline`  
**Target Branch:** `feature/three-layer-defence-resolvers`  
**Feature ID:** FEAT-XXX *(assigned by `/feature-plan`)*  
**Parent Spec:** `docs/research/three-layer-defence/feature-spec.md`

---

## 1. Problem Statement

When AutoBuild's Player-Coach loop exhausts its 5-turn limit, the `pipeline.build-blocked` event fires but nothing responds — the build simply fails and waits for human intervention. This creates an overnight/unattended pipeline bottleneck, particularly critical as implementation shifts to less capable open-weight models. The dev-pipeline needs specialised resolver agents that subscribe to build-blocked events via NATS, provide targeted assistance based on the failure category, and publish augmented context that enables the Build Agent to restart the Player-Coach loop with a better chance of convergence. All resolvers must be technology-stack agnostic, supporting Python, TypeScript, Go, C#, and Rust projects.

**Important:** This spec should only be implemented after guardkit's telemetry instrumentation (Phase A) has collected sufficient empirical data to reveal which failure category dominates. Build the resolver framework (Task 1) and Docker infrastructure (Task 5) first, then implement individual resolvers in priority order based on the data.

## 2. Decision Log

*Subset of decisions from the parent spec relevant to this repo.*

| # | Decision | Rationale | Alternatives Rejected | ADR Status |
|---|----------|-----------|----------------------|------------|
| D3 | Resolver agents communicate exclusively via NATS events | Loosely coupled, auditable, deployable independently. Consistent with `pipeline.*` topic namespace. | Direct subprocess invocation, shared state, REST APIs | Accepted |
| D4 | Resolvers provide augmented context — never modify the codebase | Player-Coach remains sole code modification path. Resolvers are advisory, not executive. Preserves audit trail. | Resolvers write code, resolvers modify feature plans | Accepted |
| D6 | Spec-ambiguity clarification surfaces via `pipeline.build-needs-clarification` | Must reach human efficiently via dashboard or Reachy voice. | Email/Slack, block indefinitely, auto-resolve | Accepted |
| D9 | Knowledge-gap resolver uses Graphiti → Context7 → web search (layered lookup) | Graphiti may have the answer from a previous build. Context7 provides structured docs. Web search is broadest but noisiest. Avoids unnecessary external calls. | Web search only, Graphiti only, local docs only | Accepted |
| D10 | Context-overflow resolver uses tree-sitter for universal language analysis | Tree-sitter provides grammar-based parsing for Python, TypeScript, Go, C#, Rust through a single interface. Consistent with stack-agnostic principle. | Python `ast` module (single-language), file proximity heuristic | Accepted |
| D12 | Resolver agents run as optional Docker containers alongside Build Agent | Same deployment model as other dev-pipeline services. Optional — pipeline works without them. | Mandatory deployment, cloud-hosted, embedded in Build Agent | Accepted |
| D13 | All resolver analysis must be technology-stack agnostic | Platform builds multiple stacks. Context-overflow resolver uses LanguageAnalyser interface with per-stack tree-sitter implementations. GenericAnalyser provides regex fallback. | Python-only analysis, per-language hardcoding | Accepted |

**Warnings & Constraints:**
- Resolver agents must have configurable timeouts — a hanging resolver is worse than no resolver
- Maximum one resolver-assisted retry per task — prevents infinite loops
- Context-overflow resolver must not read files outside the build's worktree — security boundary
- tree-sitter grammar packages are optional — missing grammars degrade to GenericAnalyser, not failure
- Knowledge-gap resolver's web search must respect network allowlists
- Resolver augmented context must stay under ~4000 tokens to leave room in Player's context window
- All resolvers must handle external service unavailability gracefully (Graphiti down, Context7 down, etc.)

## 3. Architecture

### 3.1 Where This Fits

```
┌─────────────────────────────────────────────────────────────────────┐
│                          dev-pipeline                                │
│                                                                      │
│  build_agent/              ← EXISTING: subscribes to ready-for-dev   │
│  │                              NOW ALSO: handles build-blocked       │
│  │                              responses (resolver.*.{feature_id})   │
│  │                                                                    │
│  resolver_agents/          ← NEW PACKAGE                             │
│  ├── base.py               ← BaseResolver abstract class            │
│  ├── orchestrator.py       ← Routes build-blocked → resolver        │
│  ├── knowledge_gap.py      ← Graphiti → Context7 → web search      │
│  ├── context_overflow.py   ← tree-sitter dependency analysis        │
│  ├── spec_ambiguity.py     ← Clarification drafting + human routing │
│  ├── language_analysers/   ← Stack-agnostic code analysis           │
│  │   ├── base.py           ← LanguageAnalyser interface             │
│  │   ├── python_analyser.py                                          │
│  │   ├── typescript_analyser.py                                      │
│  │   ├── go_analyser.py                                              │
│  │   ├── csharp_analyser.py                                          │
│  │   └── generic_analyser.py  ← regex-based fallback                │
│  └── Dockerfile                                                      │
│                                                                      │
│  docker-compose.resolvers.yaml  ← Optional overlay                  │
│                                                                      │
│           NATS Event Flow:                                           │
│  ┌────────────────────────────────────────────────┐                  │
│  │ SUBSCRIBES TO:                                  │                  │
│  │   pipeline.build-blocked.>                      │                  │
│  │   pipeline.clarification-response.{feature_id}  │                  │
│  │                                                  │                  │
│  │ PUBLISHES:                                       │                  │
│  │   resolver.knowledge-assist.{feature_id}         │                  │
│  │   resolver.context-assist.{feature_id}           │                  │
│  │   resolver.clarification-assist.{feature_id}     │                  │
│  │   pipeline.build-needs-clarification.{feature_id}│                  │
│  └────────────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Resolver Orchestration Flow

```
pipeline.build-blocked.{feature_id}
    │
    ▼
┌──────────────────────────────────┐
│ ResolverOrchestrator             │
│                                  │
│ 1. Inspect failure_category      │
│ 2. Check resolver_attempt        │
│    (if >= 1 → publish            │
│     build-failed, stop)          │
│ 3. Route to registered resolver  │
│ 4. Enforce timeout               │
│ 5. If resolver errors/times out  │
│    → publish build-failed        │
└──────────┬───────────────────────┘
           │
    ┌──────┴──────┬───────────────┐
    ▼             ▼               ▼
┌────────┐  ┌──────────┐  ┌───────────┐
│Knowledge│  │ Context  │  │   Spec    │
│  Gap   │  │ Overflow │  │ Ambiguity │
│Resolver│  │ Resolver │  │ Resolver  │
└───┬────┘  └────┬─────┘  └─────┬─────┘
    │            │              │
    ▼            ▼              ▼
resolver.*-assist.{feature_id}
    │
    ▼
Build Agent receives assist → restarts Player-Coach with augmented context
```

### 3.3 LanguageAnalyser Architecture (Context Overflow Resolver)

```
BuildBlockedPayload.detected_stack
    │
    ▼
┌──────────────────────────────────────────────────┐
│ LanguageAnalyserFactory                           │
│                                                   │
│   "python"     → PythonAnalyser (tree-sitter)    │
│   "typescript" → TypeScriptAnalyser (tree-sitter)│
│   "go"         → GoAnalyser (tree-sitter)        │
│   "csharp"     → CSharpAnalyser (tree-sitter)    │
│   "rust"       → (future — use GenericAnalyser)  │
│   "generic"    → GenericAnalyser (regex-based)   │
│                                                   │
│   Grammar not installed? → GenericAnalyser + warn │
└──────────┬───────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────┐
│ LanguageAnalyser Interface                        │
│                                                   │
│  extract_imports(file) → list[ImportRef]          │
│  extract_signatures(file) → list[Signature]      │
│  trace_dependencies(files, worktree) → DepGraph  │
│                                                   │
│  Output: Focused context package (≤4000 tokens)  │
│  - Interface/type signatures from missing deps   │
│  - Function signatures with docstrings           │
│  - Key constants and configuration               │
└──────────────────────────────────────────────────┘
```

## 4. API Contracts

### 4.1 BaseResolver Interface

```python
class BaseResolver(ABC):
    def __init__(self, resolver_id: str, nats_client: NATSClient,
                 graphiti_client: GraphitiClient):
        self.resolver_id = resolver_id
        self.nats = nats_client
        self.graphiti = graphiti_client
        self.timeout_seconds = 300  # 5 minute default

    @abstractmethod
    async def resolve(self, blocked_event: BuildBlockedPayload) -> ResolverAssistPayload: ...

    async def check_graphiti_precedent(self, error_signature: str,
                                       domain_tags: list[str]) -> Optional[str]: ...

    async def record_resolution(self, resolution: ResolverAssistPayload,
                                outcome: str) -> None: ...
```

### 4.2 ResolverOrchestrator Interface

```python
class ResolverOrchestrator:
    def __init__(self, nats_client: NATSClient,
                 resolvers: dict[str, BaseResolver]):
        """
        resolvers: maps failure_category → resolver instance
        e.g., {"knowledge-gap": KnowledgeGapResolver(...), ...}
        """

    async def start(self) -> None:
        """Subscribe to pipeline.build-blocked.> and begin routing."""

    async def handle_blocked(self, event: BuildBlockedPayload) -> None:
        """
        1. Check resolver_attempt — if >= 1, publish build-failed
        2. Look up resolver for failure_category
        3. If no resolver registered, publish build-failed with reason
        4. Execute resolver with timeout enforcement
        5. Publish resolver assist event (or build-failed on error/timeout)
        """
```

### 4.3 LanguageAnalyser Interface

```python
class ImportRef(BaseModel):
    module: str                  # e.g., "fastapi", "@nestjs/common", "net/http"
    symbols: list[str]           # e.g., ["FastAPI", "Request"], ["Controller", "Get"]
    file_path: str               # file containing this import
    line_number: int

class Signature(BaseModel):
    name: str                    # function/class/interface name
    kind: str                    # "function" | "class" | "interface" | "type" | "method"
    signature: str               # full signature string
    docstring: Optional[str]     # first paragraph of docstring/jsdoc/godoc
    file_path: str
    line_number: int

class DependencyGraph(BaseModel):
    entry_files: list[str]
    dependencies: dict[str, list[str]]   # file → list of files it depends on
    missing_files: list[str]              # referenced but not found in worktree
    circular: list[tuple[str, str]]       # detected circular dependencies

class LanguageAnalyser(ABC):
    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]: ...

    @abstractmethod
    def extract_imports(self, file_path: str) -> list[ImportRef]: ...

    @abstractmethod
    def extract_signatures(self, file_path: str) -> list[Signature]: ...

    def trace_dependencies(self, entry_files: list[str],
                           worktree: str) -> DependencyGraph: ...
```

## 5. Implementation Tasks

### Task 1: Resolver Base Class and Orchestrator
- **Task ID:** TASK-XXX
- **Complexity:** medium
- **Type:** implementation
- **Domain tags:** `resolver, nats, agent, base-class, orchestration`
- **Files to create/modify:**
  - `resolver_agents/__init__.py` (new)
  - `resolver_agents/base.py` (new)
  - `resolver_agents/orchestrator.py` (new)
  - `tests/test_resolver_base.py` (new)
  - `tests/test_resolver_orchestrator.py` (new)
- **Files NOT to touch:** build_agent/, adapters/, infrastructure/
- **Dependencies:** nats-core resolver schemas
- **Inputs:** nats-core BuildBlockedPayload, ResolverAssistPayload, NATSClient
- **Outputs:** BaseResolver abstract class, ResolverOrchestrator routing class
- **Relevant decisions:** D3, D4, D12
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `resolver_agents/base.py`
  - [ ] Abstract class `BaseResolver` with abstract method: `resolve(BuildBlockedPayload) -> ResolverAssistPayload`
  - [ ] BaseResolver includes: `check_graphiti_precedent()`, `record_resolution()`, timeout enforcement
  - [ ] File exists: `resolver_agents/orchestrator.py`
  - [ ] Class `ResolverOrchestrator` subscribes to `pipeline.build-blocked.>` and routes to appropriate resolver
  - [ ] Orchestrator checks `resolver_attempt` — if >= 1, publishes build-failed (no infinite loops)
  - [ ] Orchestrator handles: unknown category (logs warning, publishes build-failed), resolver timeout (publishes build-failed), resolver error (publishes build-failed)
  - [ ] Tests pass: `pytest tests/test_resolver_base.py tests/test_resolver_orchestrator.py -v`
  - [ ] Lint passes: `ruff check resolver_agents/`
- **Implementation notes:** The orchestrator subscribes to `pipeline.build-blocked.>` (wildcard). Inspects `failure_category` and routes to the registered resolver. If no resolver registered for a category (container not running), publishes `pipeline.build-failed` with reason "no resolver available for {category}". Timeout on resolver execution is critical — use asyncio.wait_for().
- **Player constraints:** Do not implement concrete resolvers (Tasks 2-4). Only abstract base and routing orchestrator.
- **Coach validation commands:**
  ```bash
  pytest tests/test_resolver_base.py tests/test_resolver_orchestrator.py -v
  ruff check resolver_agents/
  python -c "from resolver_agents.base import BaseResolver; from resolver_agents.orchestrator import ResolverOrchestrator; print('Import OK')"
  ```

### Task 2: Knowledge Gap Resolver
- **Task ID:** TASK-XXX
- **Complexity:** high
- **Type:** implementation
- **Domain tags:** `resolver, knowledge-gap, graphiti, context7, documentation, search`
- **Files to create/modify:**
  - `resolver_agents/knowledge_gap.py` (new)
  - `tests/test_knowledge_gap_resolver.py` (new)
- **Files NOT to touch:** resolver_agents/base.py, resolver_agents/orchestrator.py
- **Dependencies:** Task 1
- **Inputs:** BuildBlockedPayload with category "knowledge-gap", Graphiti client, Context7 client
- **Outputs:** ResolverAssistPayload with augmented documentation context
- **Relevant decisions:** D4, D9, D13
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `resolver_agents/knowledge_gap.py`
  - [ ] Class `KnowledgeGapResolver` extends `BaseResolver`
  - [ ] Three-layer lookup: Graphiti → Context7 → web search (each layer only if previous insufficient)
  - [ ] Extracts library/module name from error message and domain tags (stack-aware extraction)
  - [ ] Augmented context includes: relevant documentation excerpts, code examples, source provenance
  - [ ] Context sources list tracks which layer provided each piece of context
  - [ ] Handles: Graphiti unavailable (skip), Context7 unavailable (skip), all unavailable (empty assist with low confidence)
  - [ ] Augmented context ≤ 4000 tokens
  - [ ] Tests pass: `pytest tests/test_knowledge_gap_resolver.py -v`
  - [ ] Lint passes: `ruff check resolver_agents/knowledge_gap.py`
- **Implementation notes:** Extract library/module from error message using stack-aware patterns — Python "No module named 'X'" → library X, TypeScript "Cannot find module 'X'" → library X, Go "cannot find package 'X'" → package X. For Graphiti: search nodes tagged with library name + "documentation" or "api-usage". For Context7: use resolve-library-id then get-library-docs. For web search: "{library} {error_message} {detected_stack} example". Compile into coherent augmented context, not raw dump.
- **Player constraints:** External API calls wrapped in try/except with timeouts. No hardcoded API keys.
- **Coach validation commands:**
  ```bash
  pytest tests/test_knowledge_gap_resolver.py -v
  ruff check resolver_agents/
  python -c "from resolver_agents.knowledge_gap import KnowledgeGapResolver; print('Import OK')"
  ```

### Task 3: Context Overflow Resolver with Language Analysers
- **Task ID:** TASK-XXX
- **Complexity:** high
- **Type:** implementation
- **Domain tags:** `resolver, context-overflow, dependency-analysis, tree-sitter, stack-agnostic`
- **Files to create/modify:**
  - `resolver_agents/context_overflow.py` (new)
  - `resolver_agents/language_analysers/__init__.py` (new)
  - `resolver_agents/language_analysers/base.py` (new)
  - `resolver_agents/language_analysers/python_analyser.py` (new)
  - `resolver_agents/language_analysers/typescript_analyser.py` (new)
  - `resolver_agents/language_analysers/go_analyser.py` (new)
  - `resolver_agents/language_analysers/csharp_analyser.py` (new)
  - `resolver_agents/language_analysers/generic_analyser.py` (new)
  - `tests/test_context_overflow_resolver.py` (new)
  - `tests/test_language_analysers.py` (new)
- **Files NOT to touch:** resolver_agents/base.py, resolver_agents/orchestrator.py
- **Dependencies:** Task 1
- **Inputs:** BuildBlockedPayload with category "context-overflow" and detected_stack, worktree access
- **Outputs:** ResolverAssistPayload with focused context package, LanguageAnalyser interface with per-stack implementations
- **Relevant decisions:** D4, D10, D13
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `resolver_agents/context_overflow.py`
  - [ ] File exists: `resolver_agents/language_analysers/base.py`
  - [ ] Abstract class `LanguageAnalyser` with methods: `extract_imports()`, `extract_signatures()`, `trace_dependencies()`
  - [ ] `ContextOverflowResolver` uses `detected_stack` to select LanguageAnalyser
  - [ ] Concrete analysers: Python (tree-sitter-python), TypeScript (tree-sitter-typescript), Go (tree-sitter-go), C# (tree-sitter-c-sharp)
  - [ ] GenericAnalyser provides regex-based fallback for unsupported/missing stacks
  - [ ] Graceful degradation: missing tree-sitter grammar → GenericAnalyser + warning log
  - [ ] Context package ≤ 4000 tokens (configurable)
  - [ ] Handles: unparseable files (skip), circular imports (detect + break), binary files (skip), files outside worktree (refuse)
  - [ ] Test: Python project — traces imports, finds missing dependencies
  - [ ] Test: TypeScript project — traces import/require, finds missing types
  - [ ] Test: Go project — traces package imports, finds missing interfaces
  - [ ] Test: Unknown stack — GenericAnalyser provides file-listing context
  - [ ] Tests pass: `pytest tests/test_context_overflow_resolver.py tests/test_language_analysers.py -v`
  - [ ] Lint passes: `ruff check resolver_agents/context_overflow.py resolver_agents/language_analysers/`
- **Implementation notes:** Tree-sitter for all language analysis. Pattern: (1) receive BuildBlockedPayload with detected_stack, (2) select LanguageAnalyser (or GenericAnalyser), (3) for each file Player touched, trace imports to find dependencies not in Player's file list, (4) for each dependency, extract signatures/types/docstrings, (5) prioritise files in error trace. Output reads like a reference card. Tree-sitter grammars imported with try/except — missing grammar = GenericAnalyser + warning. GenericAnalyser uses regex for import statements and function/class definitions.
- **Player constraints:** All analysis via LanguageAnalyser interface — no direct Python `ast` usage. No files outside worktree. Tree-sitter grammars are optional.
- **Coach validation commands:**
  ```bash
  pytest tests/test_context_overflow_resolver.py tests/test_language_analysers.py -v
  ruff check resolver_agents/
  python -c "from resolver_agents.context_overflow import ContextOverflowResolver; print('Import OK')"
  python -c "from resolver_agents.language_analysers.base import LanguageAnalyser; print('Interface OK')"
  python -c "from resolver_agents.language_analysers.generic_analyser import GenericAnalyser; print('Fallback OK')"
  ```

### Task 4: Spec Ambiguity Resolver
- **Task ID:** TASK-XXX
- **Complexity:** high
- **Type:** implementation
- **Domain tags:** `resolver, spec-ambiguity, clarification, graphiti, human-in-the-loop`
- **Files to create/modify:**
  - `resolver_agents/spec_ambiguity.py` (new)
  - `tests/test_spec_ambiguity_resolver.py` (new)
- **Files NOT to touch:** resolver_agents/base.py, resolver_agents/orchestrator.py
- **Dependencies:** Task 1
- **Inputs:** BuildBlockedPayload with category "spec-ambiguity", Graphiti client, NATS client
- **Outputs:** ResolverAssistPayload (auto-resolved) OR ClarificationRequestPayload (needs human)
- **Relevant decisions:** D4, D6
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `resolver_agents/spec_ambiguity.py`
  - [ ] Class `SpecAmbiguityResolver` extends `BaseResolver`
  - [ ] Identifies specific ambiguity from turn analysis
  - [ ] Searches Graphiti for similar past decisions/ADRs
  - [ ] High-confidence Graphiti match (>0.8): auto-resolves → publishes ResolverAssistPayload
  - [ ] Low-confidence: publishes ClarificationRequestPayload with structured options (≥2 options with rationale)
  - [ ] Subscribes to `pipeline.clarification-response.{feature_id}` for human answers
  - [ ] Handles timeout: uses auto_resolve_option if set, otherwise publishes failure
  - [ ] When human responds with `seed_to_graphiti=True`: stores decision in Graphiti
  - [ ] Tests pass: `pytest tests/test_spec_ambiguity_resolver.py -v`
  - [ ] Lint passes: `ruff check resolver_agents/spec_ambiguity.py`
- **Implementation notes:** Two paths: auto-resolve (fast) and human-clarification (slow). Graphiti search: ADR nodes matching ambiguity domain, previous clarification responses, architecture decisions. Clarification questions must be specific and actionable with ≥2 options. auto_resolve_option provides sensible default for overnight runs. Timeout is configurable (default 60 minutes).
- **Player constraints:** Do not block NATS event loop waiting for human response — async wait with timeout.
- **Coach validation commands:**
  ```bash
  pytest tests/test_spec_ambiguity_resolver.py -v
  ruff check resolver_agents/
  python -c "from resolver_agents.spec_ambiguity import SpecAmbiguityResolver; print('Import OK')"
  ```

### Task 5: Docker Compose for Resolver Agents
- **Task ID:** TASK-XXX
- **Complexity:** low
- **Type:** configuration
- **Domain tags:** `docker, deployment, resolver, infrastructure`
- **Files to create/modify:**
  - `docker-compose.resolvers.yaml` (new)
  - `resolver_agents/Dockerfile` (new)
- **Files NOT to touch:** `docker-compose.yaml` (main pipeline compose)
- **Dependencies:** Tasks 1-4
- **Inputs:** Existing docker-compose.yaml patterns
- **Outputs:** Optional Docker Compose overlay for resolver containers
- **Relevant decisions:** D12, D13
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `docker-compose.resolvers.yaml`
  - [ ] File exists: `resolver_agents/Dockerfile`
  - [ ] Compose defines services: `resolver-orchestrator`, `knowledge-gap-resolver`, `context-overflow-resolver`, `spec-ambiguity-resolver`
  - [ ] Each service connects to existing NATS network
  - [ ] Startable with: `docker compose -f docker-compose.yaml -f docker-compose.resolvers.yaml up`
  - [ ] Each resolver independently startable
  - [ ] Environment variables: NATS_URL, GRAPHITI_URL, RESOLVER_TIMEOUT, LOG_LEVEL
  - [ ] Dockerfile installs tree-sitter and grammar packages (configurable via build args)
  - [ ] Grammar packages are optional — Dockerfile doesn't fail if a grammar fails to install
- **Implementation notes:** Docker Compose override pattern — extends base `docker-compose.yaml`. Each resolver = separate container for independent scaling/restart. Common base image with resolver class as entrypoint argument. Tree-sitter grammars installed in Dockerfile with `pip install --no-deps` and error tolerance.
- **Player constraints:** Do not modify base docker-compose.yaml. Override/extend pattern only.
- **Coach validation commands:**
  ```bash
  docker compose -f docker-compose.yaml -f docker-compose.resolvers.yaml config > /dev/null 2>&1 && echo "Compose valid"
  ```

## 6. Test Strategy

### Unit Tests
| Test File | Covers | Key Assertions |
|-----------|--------|---------------|
| `tests/test_resolver_base.py` | BaseResolver contract | Timeout enforcement, Graphiti precedent lookup, resolution recording |
| `tests/test_resolver_orchestrator.py` | Event routing | Category→resolver mapping, unknown category handling, resolver_attempt check, timeout |
| `tests/test_knowledge_gap_resolver.py` | Three-layer documentation lookup | Layer fallback, stack-aware library extraction, context compilation, token limits |
| `tests/test_context_overflow_resolver.py` | Dependency analysis + context packaging | Per-stack import tracing (Python, TS, Go, C#), signature extraction, token limits, grammar degradation |
| `tests/test_language_analysers.py` | tree-sitter analysers + generic fallback | Python imports, TS import/require, Go package imports, C# using statements, generic regex, graceful grammar absence |
| `tests/test_spec_ambiguity_resolver.py` | Clarification flow | Auto-resolve path, human-clarification path, timeout, Graphiti seeding |

### Integration Tests
| Test File | Covers | Prerequisites |
|-----------|--------|--------------|
| `tests/integration/test_resolver_flow.py` | Full blocked → resolver → assist → resume flow | NATS running, mock Graphiti |

### Manual Verification
- [ ] Start resolver containers alongside Build Agent
- [ ] Trigger a build that will fail — verify build-blocked event routes to correct resolver
- [ ] Verify resolver publishes assist event with meaningful augmented context
- [ ] Verify Build Agent restarts Player-Coach with augmented context
- [ ] Verify second failure after resolver assist → build-failed (no infinite loop)
- [ ] Verify pipeline works normally when resolver containers are not running

## 7. Dependencies & Setup

### Python Dependencies
```
# requirements.txt
nats-core @ git+ssh://git@github.com/appmilla/nats-core.git

# Tree-sitter for stack-agnostic code analysis
tree-sitter>=0.21.0
tree-sitter-python>=0.21.0
tree-sitter-typescript>=0.21.0
tree-sitter-go>=0.21.0
tree-sitter-c-sharp>=0.21.0
# tree-sitter-rust>=0.21.0     # Add when needed

# Note: tree-sitter grammars are optional. Missing grammars
# degrade to GenericAnalyser, not failure.
```

## 8. File Tree (Target State)

```
dev-pipeline/
├── resolver_agents/
│   ├── __init__.py                      # NEW (Task 1)
│   ├── base.py                          # NEW (Task 1)
│   ├── orchestrator.py                  # NEW (Task 1)
│   ├── knowledge_gap.py                 # NEW (Task 2)
│   ├── context_overflow.py              # NEW (Task 3)
│   ├── language_analysers/              # NEW (Task 3)
│   │   ├── __init__.py
│   │   ├── base.py                      # LanguageAnalyser interface
│   │   ├── python_analyser.py           # tree-sitter-python
│   │   ├── typescript_analyser.py       # tree-sitter-typescript
│   │   ├── go_analyser.py              # tree-sitter-go
│   │   ├── csharp_analyser.py          # tree-sitter-c-sharp
│   │   └── generic_analyser.py         # regex-based fallback
│   ├── spec_ambiguity.py               # NEW (Task 4)
│   └── Dockerfile                       # NEW (Task 5)
├── docker-compose.resolvers.yaml        # NEW (Task 5)
└── tests/
    ├── test_resolver_base.py            # NEW (Task 1)
    ├── test_resolver_orchestrator.py    # NEW (Task 1)
    ├── test_knowledge_gap_resolver.py   # NEW (Task 2)
    ├── test_context_overflow_resolver.py # NEW (Task 3)
    ├── test_language_analysers.py       # NEW (Task 3)
    ├── test_spec_ambiguity_resolver.py  # NEW (Task 4)
    └── integration/
        └── test_resolver_flow.py        # Integration
```

## 9. Out of Scope

- Build Agent modifications to handle resolver assist events — separate feature, coordinated with Build Agent development
- Dashboard UI for clarification questions — initially answered via Pipeline CLI
- Reachy Mini voice notifications for blocked builds — Ship's Computer integration
- Rust tree-sitter grammar — add when Rust projects are active
- Multi-resolver chaining — one resolver per blocked event
- Cost tracking per resolution — deferred
- Configurable retry budgets — v1 = exactly one retry per task

## 10. Sequencing

This repo implements **Phase B** of the parent spec. Do NOT start implementation until guardkit instrumentation (Phase A) has collected empirical data.

**Build order within this repo:**
1. Task 1 (Resolver framework + orchestrator) — always first
2. Task 5 (Docker infrastructure) — can parallel with Task 1
3. Tasks 2, 3, or 4 — build in priority order based on failure category data from Phase A

**Dependencies:**
- Requires: nats-core three-layer-defence schemas
- Requires: guardkit telemetry instrumentation (for build-blocked events to consume)
- Requires: Empirical data from 20+ AutoBuild runs to determine resolver priority

**Estimated effort:** 2-3 weeks  
**Phase:** B (Resolver Framework — build after data)
