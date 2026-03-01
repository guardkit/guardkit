# Feature Specification: Three-Layer Build Defence with Resolver Agents

**Date:** March 2026  
**Author:** Rich (with Claude AI assistance)  
**Status:** Ready for Implementation  
**Research Method:** Claude Desktop (extended thinking) → GuardKit `/feature-plan`  
**Target Repo:** `appmilla/guardkit` (instrumentation, resolver framework) + `appmilla/dev-pipeline` (NATS events, resolver agents)  
**Target Branch:** `feature/three-layer-defence`  
**Feature ID:** FEAT-XXX *(assigned by `/feature-plan`)*

---

## 1. Problem Statement

AutoBuild's Player-Coach loop caps at 5 turns per task before escalation, but "escalation" currently means the build stops and waits for manual human intervention. This creates a pipeline bottleneck — particularly as implementation moves to less capable open-weight models (Qwen3-Coder-Next on Dell ProMax GB10) where turn inflation is expected. The system needs (a) instrumented build telemetry to understand failure patterns empirically, (b) typed failure categorisation to enable targeted automated resolution, and (c) specialised resolver agents that can provide targeted assistance via NATS events, extending convergence windows without resorting to uncontrolled agent swarms.

## 2. Decision Log

| # | Decision | Rationale | Alternatives Rejected | ADR Status |
|---|----------|-----------|----------------------|------------|
| D1 | Instrument build telemetry as structured events, not just log output | Telemetry data serves three purposes: resolver agent routing decisions, fine-tuning dataset for vLLM models, and empirical evidence for which defence layer to invest in next. Structured data is queryable; logs are not. | Unstructured logging (not queryable), external APM tools (overkill, adds cloud dependency) | Accepted |
| D2 | Categorise failures into three typed categories: knowledge-gap, context-overflow, specification-ambiguity | Each failure type has a fundamentally different resolution path. A single generic "help" agent would be as inefficient as a human debugging blindly. Typed categories enable targeted resolver selection. | Single generic resolver (inefficient, can't specialise), more granular categories (premature — let data reveal subcategories), no categorisation (no routing basis) | Accepted |
| D3 | Resolver agents communicate exclusively via NATS events, not direct function calls | Keeps resolvers loosely coupled, auditable, and deployable independently. A resolver on the Dell ProMax can assist a build on the same machine or (future) a remote build node. Consistent with the existing `pipeline.*` topic namespace design. | Direct subprocess invocation (tight coupling, no audit trail), shared memory/state (breaks distributed model), REST APIs between agents (unnecessary complexity for internal coordination) | Accepted |
| D4 | Resolvers provide augmented context back to the Build Agent — they never modify the codebase directly | Preserves the Player-Coach loop as the single point of code modification. Resolvers are advisory, not executive. This maintains the existing audit trail and prevents emergent behaviour. | Resolvers write code directly (breaks audit trail, introduces emergent behaviour), resolvers modify feature plans (scope creep, plan is a human-approved artifact) | Accepted |
| D5 | Build telemetry publishes via existing `pipeline.build-progress` events with extended payload, plus new `pipeline.build-blocked` event | Extends the existing schema rather than creating a parallel telemetry system. The `build-blocked` event is the trigger for resolver agents. Schema extension follows nats-core's additive-only versioning policy (new optional fields, existing consumers unaffected). | Separate telemetry topic namespace (fragmentation), sidecar metrics service (over-engineered), in-process only logging (not available to other agents) | Accepted |
| D6 | Human-in-the-loop clarification surfaces via `pipeline.build-needs-clarification` event, rendered in Ship's Computer dashboard and optionally via Reachy voice | Specification ambiguity that resolvers can't handle must reach the human efficiently. The dashboard is the primary interface; Reachy voice is a natural extension of the Ship's Computer architecture for ambient awareness. | Email/Slack notifications (context switching, loses pipeline context), block indefinitely (pipeline stalls), auto-resolve with best guess (defeats the purpose of catching ambiguity) | Accepted |
| D7 | Collect telemetry data from day one, but defer resolver agent implementation until empirical data reveals which failure category dominates | Avoids speculative engineering. The instrumentation is cheap and immediately useful (for fine-tuning data). Resolver agents are more expensive and should target the actual bottleneck, not the assumed one. | Build everything at once (may build the wrong resolver first), no instrumentation (flying blind when resolvers are needed) | Accepted |
| D8 | Telemetry includes per-turn Player-Coach exchange summaries (not full transcripts) for failure analysis | Full transcripts would blow up event payloads and storage. Summaries capture the essential signal — what was attempted, what error occurred, what the Coach flagged — without the noise. Full transcripts remain in local build logs for deep debugging. | Full transcripts in events (payload too large, storage cost), no exchange data (insufficient for failure analysis), only final error (loses the convergence trajectory information) | Accepted |
| D9 | Knowledge-gap resolver uses Graphiti-first lookup, then Context7 documentation search, then web search as fallback layers | Graphiti may already contain the answer from a previous build. Context7 provides structured framework documentation. Web search is the broadest net but noisiest. Layered lookup avoids unnecessary external calls and token spend. | Web search only (misses project-specific knowledge), Graphiti only (insufficient for unknown libraries), RAG against local docs only (doesn't cover third-party libraries) | Accepted |
| D10 | Context-overflow resolver builds focused context packages by analysing the codebase dependency graph using tree-sitter for universal language support, not just file proximity | A file that's "nearby" in the directory tree may be irrelevant; a file three directories away may define a critical interface. Dependency analysis (imports, type references, test fixtures) produces better context than grep or directory walking. Tree-sitter provides grammar-based parsing for Python, TypeScript, Go, C#, Rust and others through a single interface — consistent with the stack-agnostic principle established in `/feature-spec`. | File proximity heuristic (misses cross-module dependencies), full codebase summary (still too large), manual context specification (doesn't scale, defeats automation), Python `ast` module (single-language, violates stack-agnostic principle) | Accepted |
| D11 | Failure categorisation uses structured heuristics first, LLM classification second | Structured heuristics are deterministic and fast — e.g., "ImportError" or "ModuleNotFoundError" in the error log strongly indicates knowledge-gap. LLM classification handles ambiguous cases. This mirrors the "never trust self-reported uncertainty" principle from structured-uncertainty-handling. | LLM-only classification (non-deterministic, expensive per failure), keyword matching only (too brittle for nuanced failures), human classification (defeats automation) | Accepted |
| D12 | Resolver agents run as optional Docker containers alongside the Build Agent on Dell ProMax | Same deployment model as other dev-pipeline services. Optional means the pipeline works without them — the Build Agent just fails as it does today. This follows the opt-in integration pattern from GuardKit's `--nats` flag. | Mandatory deployment (breaks standalone use), cloud-hosted resolvers (adds latency and cost), embedded in Build Agent process (coupling, harder to develop independently) | Accepted |
| D13 | All telemetry, failure categorisation, and resolver analysis must be technology-stack agnostic | The platform builds Python, TypeScript, Go, C#, Rust and potentially other stacks. Every component — from failure heuristics to dependency analysis — must work across all supported stacks using pluggable, stack-detected patterns. This is consistent with the stack-agnostic principle established in `/feature-spec` (D3, D10) and `/feature-plan`. Stack detection reuses the same codebase signals (pyproject.toml, package.json, go.mod, .csproj, Cargo.toml). | Python-only analysis (excludes client projects, violates platform principle), per-language hardcoding (unmaintainable), language-agnostic-only heuristics (too imprecise for useful categorisation) | Accepted |

**Warnings & Constraints:**
- nats-core schema changes must be additive only (new optional fields with defaults) — existing consumers must not break
- Build telemetry payloads must stay under 64KB per event (NATS default max payload) — use summaries, not full transcripts
- Resolver agents must have configurable timeouts — a resolver that hangs is worse than no resolver at all
- The knowledge-gap resolver's web search capability must respect the same network allowlist as Claude's environment
- Context-overflow resolver must not read files outside the build's worktree — security boundary
- Fine-tuning data export must strip any sensitive information (API keys, credentials) that may appear in error logs
- Failure categorisation heuristics should be maintained as a configurable YAML file, not hardcoded — patterns will evolve as we observe real failures
- ALL components must be technology-stack agnostic — failure heuristics must have per-stack patterns with generic fallbacks, context analysis must use tree-sitter (not Python ast), telemetry must record the detected stack for every build
- tree-sitter grammar packages must be treated as optional — if a grammar isn't installed, the context-overflow resolver should degrade gracefully (skip dependency analysis, provide file-listing-only context)

## 3. Architecture

### 3.1 System Context

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Dell ProMax GB10                                   │
│                                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────┐  │
│  │ Build Agent  │───▶│ GuardKit    │    │      Resolver Agents        │  │
│  │             │    │ AutoBuild   │    │  ┌──────────┐               │  │
│  │ Subscribes: │    │             │    │  │Knowledge │ Subscribes:   │  │
│  │ ready-for-  │    │ Player-Coach│    │  │Gap       │ build-blocked │  │
│  │ dev         │    │ Loop (≤5    │    │  │Resolver  │ .knowledge-gap│  │
│  │             │    │ turns/task) │    │  └──────────┘               │  │
│  │ Publishes:  │    │             │    │  ┌──────────┐               │  │
│  │ build-      │    │ Publishes:  │    │  │Context   │ Subscribes:   │  │
│  │ started     │    │ build-      │    │  │Overflow  │ build-blocked │  │
│  │ build-      │    │ progress    │    │  │Resolver  │ .context-     │  │
│  │ complete    │    │ (with       │    │  └──────────┘ overflow      │  │
│  │ build-      │    │ telemetry)  │    │  ┌──────────┐               │  │
│  │ failed      │    │             │    │  │Spec      │ Subscribes:   │  │
│  │ build-      │◀───│             │    │  │Ambiguity │ build-blocked │  │
│  │ blocked     │    └─────────────┘    │  │Resolver  │ .spec-        │  │
│  └──────┬──────┘                       │  └──────────┘ ambiguity     │  │
│         │                              │        │                     │  │
│         │    ┌─────────────────────┐   │        │                     │  │
│         └───▶│      NATS Bus       │◀──┘────────┘                     │  │
│              │  pipeline.*         │                                   │  │
│              │  resolver.*         │                                   │  │
│              └─────────┬───────────┘                                   │  │
│                        │                                               │  │
│              ┌─────────▼───────────┐                                   │  │
│              │ Graphiti Knowledge  │                                   │  │
│              │ Graph (FalkorDB)    │                                   │  │
│              │ - Resolution history│                                   │  │
│              │ - Build patterns    │                                   │  │
│              │ - ADRs & context    │                                   │  │
│              └─────────────────────┘                                   │  │
└──────────────────────────────────────────────────────────────────────────┘
         │
         │ pipeline.build-needs-clarification
         ▼
┌──────────────────────┐     ┌──────────────────────┐
│ Ship's Computer      │     │ Reachy Mini          │
│ Dashboard            │     │ (Voice notification) │
│ (Human review UI)    │     │ "Build blocked on    │
│                      │     │  auth strategy —     │
│ [Approve] [Override] │     │  need your input"    │
└──────────────────────┘     └──────────────────────┘
         │
         │ pipeline.clarification-response
         ▼
    Back to Build Agent → Player-Coach resumes with augmented context
```

### 3.2 The Three-Layer Defence Model

```
┌───────────────────────────────────────────────────────────────────┐
│  LAYER 1 — PREVENTION (Already Built / In Progress)              │
│                                                                   │
│  /feature-spec → comprehensive Gherkin + assumptions manifest     │
│  /feature-plan → task decomposition with manageable scope         │
│  /system-plan  → architectural context with library guidance      │
│  Graphiti      → job-specific context retrieval per task          │
│                                                                   │
│  Goal: Reduce the ambiguity surface BEFORE implementation starts  │
│  Metric: Tasks completing in 1 turn (clean execution rate)        │
└───────────────────────────────────────────┬───────────────────────┘
                                            │ What slips through
                                            ▼
┌───────────────────────────────────────────────────────────────────┐
│  LAYER 2 — RECOVERY (Existing Player-Coach Loop)                 │
│                                                                   │
│  Coach catches errors → Player retries with feedback              │
│  Up to 5 turns per task before escalation                         │
│  Works when the model CAN solve the problem but made a wrong     │
│  first attempt                                                    │
│                                                                   │
│  Goal: Self-correct within the existing loop                      │
│  Metric: Tasks recovering in turns 2-5 (recovery rate)            │
└───────────────────────────────────────────┬───────────────────────┘
                                            │ What exhausts retries
                                            ▼
┌───────────────────────────────────────────────────────────────────┐
│  LAYER 3 — ASSISTED RESOLUTION (This Feature)                    │
│                                                                   │
│  Build Agent categorises failure → publishes build-blocked event  │
│  Resolver agents provide targeted assistance via NATS             │
│  Build Agent restarts Player-Coach with augmented context         │
│                                                                   │
│  Three resolver types:                                            │
│  ├── Knowledge-Gap: Library docs, API examples, Graphiti lookup   │
│  ├── Context-Overflow: Focused context package from dep analysis  │
│  └── Spec-Ambiguity: Draft clarification → human or auto-resolve │
│                                                                   │
│  Goal: Extend convergence window for less capable models          │
│  Metric: Tasks recovering after resolver assistance               │
└───────────────────────────────────────────────────────────────────┘
```

### 3.3 Component Design

| Component | Repository | File Path | Purpose | New/Modified |
|-----------|-----------|-----------|---------|-------------|
| Build Telemetry Schema | nats-core | `schemas/telemetry.py` | Pydantic models for telemetry events | New |
| Build Blocked Schema | nats-core | `schemas/resolver.py` | Pydantic models for resolver events | New |
| Topic Registry Extension | nats-core | `topics.py` | New resolver.* and extended pipeline.* topics | Modified |
| Failure Categoriser | guardkit | `src/guardkit/telemetry/categoriser.py` | Heuristic + LLM failure classification | New |
| Turn Telemetry Collector | guardkit | `src/guardkit/telemetry/collector.py` | Per-turn data collection during Player-Coach | New |
| Telemetry Publisher | guardkit | `src/guardkit/telemetry/publisher.py` | NATS event publishing for telemetry | New |
| Fine-Tuning Data Exporter | guardkit | `src/guardkit/telemetry/export.py` | Export telemetry as fine-tuning JSONL | New |
| Failure Heuristics Config | guardkit | `config/failure_heuristics.yaml` | Configurable pattern→category mapping | New |
| Resolver Base Class | dev-pipeline | `resolver_agents/base.py` | Common resolver agent pattern | New |
| Knowledge Gap Resolver | dev-pipeline | `resolver_agents/knowledge_gap.py` | Documentation lookup and context augmentation | New |
| Context Overflow Resolver | dev-pipeline | `resolver_agents/context_overflow.py` | Dependency analysis and context packaging | New |
| Spec Ambiguity Resolver | dev-pipeline | `resolver_agents/spec_ambiguity.py` | Clarification drafting and human routing | New |
| Resolver Orchestrator | dev-pipeline | `resolver_agents/orchestrator.py` | Routes build-blocked events to appropriate resolver | New |
| Docker Compose Extension | dev-pipeline | `docker-compose.resolvers.yaml` | Optional resolver container definitions | New |

### 3.4 Data Flow — Build Failure with Resolution

```
1. Build Agent starts AutoBuild for FEAT-XXX, TASK-YYY
2. Player-Coach loop runs, collecting per-turn telemetry:
   - Turn number, duration, token usage
   - Player action summary (files touched, approach taken)
   - Coach feedback summary (errors found, suggestions)
   - Error classification hints (error type, stack trace signature)
3. Player-Coach exhausts 5 turns without convergence
4. Failure Categoriser analyses the turn telemetry:
   a. Resolve detected_stack from build context (codebase signals)
   b. Heuristic pass: check error patterns against failure_heuristics.yaml
      - Select stack-specific patterns using detected_stack, fall back to generic
      - Python ImportError → knowledge-gap (via KG-002 python pattern)
      - TypeScript "Cannot find module" → knowledge-gap (via KG-001 typescript pattern)
      - Go "undefined:" referencing other package → context-overflow (via CO-001 go pattern)
      - Approach oscillation → spec-ambiguity (via SA-001, stack_independent)
   c. If heuristics inconclusive: LLM classification of turn summaries
   d. Assigns primary category + confidence + heuristic_id
5. Build Agent publishes pipeline.build-blocked.{feature_id}:
   - Failure category (knowledge-gap | context-overflow | spec-ambiguity)
   - Task context (task_id, domain_tags, files_touched)
   - Turn summaries (last 3-5 turns condensed)
   - Error signature (deduplicated error + stack trace hash)
   - Categorisation confidence
6. Resolver Orchestrator routes to appropriate resolver based on category
7. Resolver executes targeted resolution:

   [Knowledge Gap Path]
   a. Query Graphiti for task domain tags → check for existing resolution
   b. If miss: search Context7 for library/framework documentation
   c. If miss: web search for specific error + library combination
   d. Compile augmented context package with relevant docs/examples
   e. Publish resolver.knowledge-assist.{feature_id}

   [Context Overflow Path]
   a. Select LanguageAnalyser based on detected_stack (tree-sitter grammar or GenericAnalyser fallback)
   b. Analyse task's file dependencies using tree-sitter AST (imports, type refs, test fixtures)
   c. Identify files critical to the failing operation via dependency graph traversal
   d. Build focused context summary (interfaces, types, key function signatures)
   e. Publish resolver.context-assist.{feature_id}

   [Spec Ambiguity Path]
   a. Identify the specific ambiguity from turn analysis
   b. Draft a clarification question with proposed options
   c. Check Graphiti for similar past decisions
   d. If high-confidence match in Graphiti → auto-resolve, publish assist
   e. If low-confidence → publish pipeline.build-needs-clarification.{feature_id}
   f. Human responds via dashboard → pipeline.clarification-response.{feature_id}
   g. Publish resolver.clarification-assist.{feature_id}

8. Build Agent receives assist event
9. Build Agent restarts Player-Coach for TASK-YYY with augmented context
   - Original task spec + resolver's augmented context injected as additional context
   - Turn counter resets (fresh 5-turn budget with better information)
10. If second attempt also fails → build-failed event (escalate to human)
    - Maximum one resolver-assisted retry per task to prevent infinite loops
```

### 3.5 Message Schemas

#### Extended Build Progress (telemetry enrichment)

```python
class TurnTelemetry(BaseModel):
    """Per-turn data collected during Player-Coach loop."""
    turn_number: int
    duration_seconds: float
    player_action_summary: str          # ~100 words: what the Player did
    coach_feedback_summary: str         # ~100 words: what the Coach found
    files_touched: list[str]            # files the Player modified
    error_type: Optional[str] = None    # e.g., "ImportError", "AssertionError", "TypeError"
    error_signature: Optional[str] = None  # hash of deduplicated stack trace
    tokens_used: Optional[int] = None   # total tokens for this turn
    model_id: Optional[str] = None      # e.g., "qwen3-coder-next", "claude-sonnet-4-5"

class TaskTelemetry(BaseModel):
    """Telemetry for a completed or failed task."""
    task_id: str
    feature_id: str
    build_id: str
    status: str                         # "success" | "failed" | "blocked"
    turns_used: int
    turns_max: int
    total_duration_seconds: float
    total_tokens: Optional[int] = None
    model_id: Optional[str] = None
    detected_stack: Optional[str] = None  # "python" | "typescript" | "go" | "csharp" | "rust" | "generic"
    complexity: str                     # "low" | "medium" | "high"
    domain_tags: list[str]
    turn_telemetry: list[TurnTelemetry]
    failure_category: Optional[str] = None  # "knowledge-gap" | "context-overflow" | "spec-ambiguity" | None
    failure_category_confidence: Optional[float] = None  # 0.0 - 1.0
    clean_execution: bool               # True if succeeded on first turn
    recovery_turn: Optional[int] = None # Turn number where it recovered (if turns > 1 but succeeded)
```

#### Build Blocked Event (new)

```python
class BuildBlockedPayload(BaseModel):
    """Published when Player-Coach exhausts turns without convergence."""
    feature_id: str
    build_id: str
    task_id: str
    repo: str
    branch: str
    detected_stack: str                 # "python" | "typescript" | "go" | "csharp" | "rust" | "generic"
    failure_category: str               # "knowledge-gap" | "context-overflow" | "spec-ambiguity"
    category_confidence: float          # 0.0 - 1.0
    category_basis: str                 # Human-readable explanation of classification
    task_context: TaskContext
    turn_summaries: list[TurnSummary]   # Last 3-5 turns condensed
    error_signature: Optional[str] = None
    error_message: Optional[str] = None # Last error, truncated to 1000 chars
    domain_tags: list[str]
    files_touched: list[str]
    worktree_path: str
    resolver_attempt: int = 0           # 0 = first block, 1 = blocked after resolver assist
    timestamp: datetime

class TaskContext(BaseModel):
    """Subset of task spec relevant to resolvers."""
    task_id: str
    description: str
    complexity: str
    acceptance_criteria: list[str]
    implementation_notes: Optional[str] = None
    relevant_decisions: list[str]       # D1, D2, etc.
    
class TurnSummary(BaseModel):
    """Condensed Player-Coach exchange for resolver analysis."""
    turn_number: int
    player_approach: str                # ~50 words
    coach_finding: str                  # ~50 words
    error_type: Optional[str] = None
    key_files: list[str]               # Most relevant files this turn
```

#### Resolver Assist Events (new)

```python
class ResolverAssistPayload(BaseModel):
    """Published by resolver agents with augmented context."""
    feature_id: str
    build_id: str
    task_id: str
    resolver_type: str                  # "knowledge-gap" | "context-overflow" | "spec-ambiguity"
    resolver_id: str                    # agent identifier
    augmented_context: str              # The actual content to inject into Player-Coach
    context_sources: list[ContextSource]
    resolution_summary: str             # What the resolver found/decided
    confidence: float                   # How confident the resolver is in its assist
    duration_seconds: float
    timestamp: datetime

class ContextSource(BaseModel):
    """Provenance for augmented context."""
    source_type: str                    # "graphiti" | "context7" | "web_search" | "codebase_analysis" | "human_clarification"
    source_reference: str               # URL, Graphiti node ID, file path, etc.
    relevance_summary: str              # Why this source was included

class ClarificationRequestPayload(BaseModel):
    """Published when spec-ambiguity resolver needs human input."""
    feature_id: str
    build_id: str
    task_id: str
    question: str                       # The specific question for the human
    options: list[ClarificationOption]  # Proposed answers with rationale
    context_summary: str                # What the build was trying to do
    urgency: str                        # "blocking" (pipeline paused) | "advisory" (can auto-resolve)
    auto_resolve_option: Optional[int] = None  # Index of option to use if human doesn't respond within timeout
    timeout_minutes: int = 60           # How long to wait for human response
    timestamp: datetime

class ClarificationOption(BaseModel):
    option_id: int
    description: str
    rationale: str
    graphiti_precedent: Optional[str] = None  # Similar past decision, if found

class ClarificationResponsePayload(BaseModel):
    """Published by dashboard when human responds to clarification."""
    feature_id: str
    build_id: str
    task_id: str
    selected_option: Optional[int] = None  # If chose a proposed option
    custom_response: Optional[str] = None  # If provided a different answer
    respondent: str                     # "rich" | "james" | "auto-timeout"
    seed_to_graphiti: bool = True       # Whether to store this decision for future reference
    timestamp: datetime
```

### 3.6 Topic Registry Extensions

```python
class Topics:
    class Pipeline:
        # ... existing topics ...
        BUILD_BLOCKED = "pipeline.build-blocked.{feature_id}"
        BUILD_NEEDS_CLARIFICATION = "pipeline.build-needs-clarification.{feature_id}"
        CLARIFICATION_RESPONSE = "pipeline.clarification-response.{feature_id}"
    
    class Resolver:
        """Resolver agent events."""
        KNOWLEDGE_ASSIST = "resolver.knowledge-assist.{feature_id}"
        CONTEXT_ASSIST = "resolver.context-assist.{feature_id}"
        CLARIFICATION_ASSIST = "resolver.clarification-assist.{feature_id}"
        
        # Typed build-blocked subscriptions (resolvers subscribe to their category)
        BLOCKED_KNOWLEDGE_GAP = "pipeline.build-blocked.*.knowledge-gap"
        BLOCKED_CONTEXT_OVERFLOW = "pipeline.build-blocked.*.context-overflow"
        BLOCKED_SPEC_AMBIGUITY = "pipeline.build-blocked.*.spec-ambiguity"
        
        # Wildcard
        ALL = "resolver.>"
    
    class Telemetry:
        """Build telemetry for analysis and fine-tuning."""
        TASK_COMPLETE = "telemetry.task-complete.{feature_id}"
        BUILD_SUMMARY = "telemetry.build-summary.{feature_id}"
        EXPORT_REQUEST = "telemetry.export-request"
        EXPORT_COMPLETE = "telemetry.export-complete"
```

## 4. API Contracts

### 4.1 Failure Categoriser Interface

```python
class FailureCategoriser:
    """Analyses Player-Coach turn history to categorise failures."""
    
    def __init__(self, heuristics_path: str = "config/failure_heuristics.yaml"):
        """Load configurable heuristics from YAML."""
    
    def categorise(
        self, 
        turn_telemetry: list[TurnTelemetry],
        task_context: TaskContext,
        detected_stack: str = "generic"
    ) -> FailureCategory:
        """
        Args:
            turn_telemetry: Per-turn data from the Player-Coach loop
            task_context: Task metadata including domain tags and acceptance criteria
            detected_stack: Technology stack detected from codebase signals
                           ("python", "typescript", "go", "csharp", "rust", "generic")
        
        Returns:
            FailureCategory with category, confidence, and basis.
        
        Algorithm:
            1. Select stack-specific heuristic patterns (fall back to generic)
            2. Apply heuristic rules (fast, deterministic)
            3. If heuristics confident (>0.8): return immediately
            4. If inconclusive: use LLM classification on turn summaries
            5. If LLM also low confidence: default to spec-ambiguity 
               (safest — triggers human review path)
        """

class FailureCategory(BaseModel):
    category: Literal["knowledge-gap", "context-overflow", "spec-ambiguity"]
    confidence: float  # 0.0 - 1.0
    basis: str         # Human-readable explanation
    heuristic_id: Optional[str] = None    # Which heuristic rule matched (e.g., "KG-001")
    detected_stack: str = "generic"       # Stack used for pattern selection
```

### 4.2 Failure Heuristics Configuration

```yaml
# config/failure_heuristics.yaml
# Configurable pattern → category mapping
# Patterns are evaluated in order; first match wins
# Stack-specific patterns use the detected_stack from the build context
# Generic patterns serve as fallback when no stack-specific match

version: "1.0"

# Supported stacks (must align with /feature-spec StackDetector)
supported_stacks:
  - python
  - typescript
  - go
  - csharp
  - rust
  - generic  # fallback for unknown/undetected stacks

heuristics:
  # ─── Knowledge Gap: Missing library or wrong API usage ───

  - id: KG-001
    description: "Missing module/package — model doesn't know how to import it"
    category: knowledge-gap
    confidence: 0.9
    pattern_type: error_message
    match_by_stack:
      python: "No module named '(.+)'"
      typescript: "Cannot find module '(.+)'"
      go: 'cannot find package "(.+)"'
      csharp: "The type or namespace name '(.+)' could not be found"
      rust: "can't find crate for `(.+)`"
      generic: "(not found|missing|cannot find).*(module|package|crate|namespace|import)"

  - id: KG-002
    description: "Missing module/package — error type classification"
    category: knowledge-gap
    confidence: 0.9
    pattern_type: error_type
    match_by_stack:
      python: ["ImportError", "ModuleNotFoundError"]
      typescript: ["MODULE_NOT_FOUND", "ERR_MODULE_NOT_FOUND"]
      go: ["ImportPathError"]
      csharp: ["CS0246", "CS0234"]  # compiler error codes
      rust: ["E0432", "E0433"]       # unresolved import, failed to resolve
      generic: ["ImportError", "ModuleNotFoundError", "MODULE_NOT_FOUND"]

  - id: KG-003
    description: "Wrong API usage — model knows the library but not the correct API"
    category: knowledge-gap
    confidence: 0.8
    pattern_type: error_message
    match_by_stack:
      python: "(has no attribute|is not callable|unexpected keyword argument|takes \\d+ positional arguments? but \\d+ (?:was|were) given)"
      typescript: "(is not a function|Property '.+' does not exist on type|is not assignable to parameter)"
      go: "(undefined: .+|has no field or method|cannot use .+ as type)"
      csharp: "(does not contain a definition for|no overload for method|cannot convert from)"
      rust: "(no method named|no field .+ on type|expected .+ found)"
      generic: "(has no attribute|is not a function|undefined|does not contain|no method named)"

  - id: KG-004
    description: "Player repeating same mistake — lacks the knowledge to fix it"
    category: knowledge-gap
    confidence: 0.85
    pattern_type: turn_pattern
    match: "same_error_repeated_3_turns"
    stack_independent: true  # This pattern applies regardless of stack

  # ─── Context Overflow: Reference to symbols outside context window ───

  - id: CO-001
    description: "Reference to symbol defined in a file not in context"
    category: context-overflow
    confidence: 0.7
    pattern_type: error_message
    match_by_stack:
      python: "(NameError: name '.+' is not defined|ImportError: cannot import name '.+' from)"
      typescript: "(Cannot find name '.+'|has no exported member '.+')"
      go: "(undefined: .+|imported and not used)"
      csharp: "(The name '.+' does not exist in the current context|are you missing a using directive)"
      rust: "(cannot find value .+ in this scope|unresolved import)"
      generic: "(not defined|cannot find name|undefined reference|does not exist in the current context)"

  - id: CO-002
    description: "Player's fix breaks something in a file they can't see"
    category: context-overflow
    confidence: 0.8
    pattern_type: turn_pattern
    match: "fix_introduces_new_break_different_file"
    stack_independent: true

  - id: CO-003
    description: "Player reimplements something that already exists — didn't see it"
    category: context-overflow
    confidence: 0.75
    pattern_type: turn_pattern
    match: "player_recreates_existing_code"
    stack_independent: true

  # ─── Spec Ambiguity: Unclear specification causing oscillation ───

  - id: SA-001
    description: "Player alternates between approaches — no clear spec guidance"
    category: spec-ambiguity
    confidence: 0.8
    pattern_type: turn_pattern
    match: "approach_oscillation"
    stack_independent: true

  - id: SA-002
    description: "Coach gives conflicting guidance — spec doesn't resolve the conflict"
    category: spec-ambiguity
    confidence: 0.75
    pattern_type: turn_pattern
    match: "coach_contradicts_previous_feedback"
    stack_independent: true

  - id: SA-003
    description: "Player fills a spec gap with an assumption not in context"
    category: spec-ambiguity
    confidence: 0.7
    pattern_type: assumption_detected
    match: "player_makes_ungrounded_assumption"
    stack_independent: true
```

### 4.3 Fine-Tuning Data Export Interface

```python
class FineTuningExporter:
    """Export build telemetry as training data for vLLM model fine-tuning."""
    
    def export_jsonl(
        self,
        output_path: str,
        filter_model: Optional[str] = None,     # e.g., "qwen3-coder-next"
        filter_status: Optional[str] = None,     # "success" | "failed" | "blocked"
        filter_stack: Optional[str] = None,      # e.g., "python", "typescript", "go"
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
        strip_sensitive: bool = True,            # Remove API keys, credentials from logs
    ) -> ExportResult:
        """
        Export format (JSONL, one record per task):
        {
            "task_id": "TASK-XXX",
            "feature_id": "FEAT-XXX",
            "model_id": "qwen3-coder-next",
            "detected_stack": "python",     # Technology stack of the project
            "task_spec": { ... },           # The input task specification
            "turns": [                       # The conversation trajectory
                {
                    "turn": 1,
                    "player_action": "...",
                    "coach_feedback": "...",
                    "outcome": "error" | "partial" | "success"
                }
            ],
            "final_status": "success" | "failed",
            "resolution": {                  # If resolver-assisted
                "resolver_type": "knowledge-gap",
                "augmented_context": "...",
                "post_resolution_turns": 2
            }
        }
        """

class ExportResult(BaseModel):
    records_exported: int
    output_path: str
    filters_applied: dict
    date_range: tuple[datetime, datetime]
    sensitive_items_stripped: int
```

### 4.4 Resolver Base Interface

```python
class BaseResolver(ABC):
    """Base class for all resolver agents."""
    
    def __init__(self, resolver_id: str, nats_client: NATSClient, graphiti_client: GraphitiClient):
        self.resolver_id = resolver_id
        self.nats = nats_client
        self.graphiti = graphiti_client
        self.timeout_seconds = 300  # 5 minute default timeout per resolution
    
    @abstractmethod
    async def resolve(self, blocked_event: BuildBlockedPayload) -> ResolverAssistPayload:
        """
        Analyse the blocked build and produce augmented context.
        Must complete within self.timeout_seconds.
        """
    
    async def check_graphiti_precedent(self, error_signature: str, domain_tags: list[str]) -> Optional[str]:
        """Check if we've successfully resolved a similar failure before."""
    
    async def record_resolution(self, resolution: ResolverAssistPayload, outcome: str):
        """Record this resolution in Graphiti for future reference."""
```

## 5. Implementation Tasks

### Phase A: Instrumentation (Implement First — Provides Data for Everything Else)

#### Task 1: Build Telemetry Schema (nats-core)
- **Task ID:** TASK-XXX
- **Complexity:** low
- **Type:** implementation
- **Domain tags:** `nats, schema, pydantic, telemetry`
- **Files to create/modify:**
  - `schemas/telemetry.py` (new)
  - `schemas/__init__.py` (modified — add exports)
  - `tests/test_telemetry_schemas.py` (new)
- **Files NOT to touch:** Existing schema files (pipeline.py, agents.py)
- **Dependencies:** None
- **Inputs:** Existing nats-core schema patterns (MessageEnvelope, Pydantic BaseModel conventions)
- **Outputs:** TurnTelemetry, TaskTelemetry Pydantic models with validation
- **Relevant decisions:** D1, D5, D8
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `schemas/telemetry.py`
  - [ ] Classes `TurnTelemetry`, `TaskTelemetry` importable
  - [ ] All fields have type annotations and appropriate defaults
  - [ ] Validation: `TurnTelemetry(turn_number=0)` raises ValidationError (turn_number must be >= 1)
  - [ ] Validation: `TaskTelemetry` requires feature_id, task_id, build_id, status
  - [ ] Serialisation roundtrip: model → JSON → model preserves all fields
  - [ ] Tests pass: `pytest tests/test_telemetry_schemas.py -v`
  - [ ] Lint passes: `ruff check schemas/telemetry.py`
- **Implementation notes:** Follow the exact field definitions from Section 3.5 of this spec. Use Pydantic v2 model_config with `extra="ignore"` for forward compatibility. The `model_id` field is Optional because early builds may not report it.
- **Player constraints:** Do not modify any existing schema files. Import only from pydantic and standard library.
- **Coach validation commands:**
  ```bash
  pytest tests/test_telemetry_schemas.py -v
  ruff check schemas/
  python -c "from schemas.telemetry import TurnTelemetry, TaskTelemetry; print('Import OK')"
  ```

#### Task 2: Build Blocked and Resolver Schemas (nats-core)
- **Task ID:** TASK-XXX
- **Complexity:** medium
- **Type:** implementation
- **Domain tags:** `nats, schema, pydantic, resolver, events`
- **Files to create/modify:**
  - `schemas/resolver.py` (new)
  - `schemas/__init__.py` (modified — add exports)
  - `topics.py` (modified — add Resolver and Telemetry topic classes)
  - `tests/test_resolver_schemas.py` (new)
- **Files NOT to touch:** Existing schema files except __init__.py
- **Dependencies:** Task 1 (uses TurnTelemetry types)
- **Inputs:** Task 1 telemetry models, existing topic registry pattern
- **Outputs:** BuildBlockedPayload, ResolverAssistPayload, ClarificationRequestPayload, ClarificationResponsePayload, TaskContext, TurnSummary, ContextSource, ClarificationOption, plus topic registry extensions
- **Relevant decisions:** D2, D3, D4, D5, D6
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `schemas/resolver.py`
  - [ ] All 8 model classes importable from `schemas.resolver`
  - [ ] `BuildBlockedPayload.failure_category` validates against literal values only
  - [ ] `ClarificationRequestPayload.timeout_minutes` has default of 60
  - [ ] `Topics.Resolver` class exists with all topic constants from Section 3.6
  - [ ] `Topics.Telemetry` class exists with all topic constants from Section 3.6
  - [ ] Tests pass: `pytest tests/test_resolver_schemas.py -v`
  - [ ] Lint passes: `ruff check schemas/resolver.py topics.py`
- **Implementation notes:** Follow schema definitions from Section 3.5 exactly. The topic registry must use the `{feature_id}` placeholder pattern consistent with existing `Topics.Pipeline`. Resolver topics use a separate namespace (`resolver.*`) from pipeline topics because they are internal coordination, not pipeline state transitions.
- **Player constraints:** Do not modify existing topic constants in `Topics.Pipeline` or `Topics.Agents`. Only add new classes/constants.
- **Coach validation commands:**
  ```bash
  pytest tests/test_resolver_schemas.py -v
  ruff check schemas/ topics.py
  python -c "from schemas.resolver import BuildBlockedPayload, ResolverAssistPayload; print('Import OK')"
  python -c "from topics import Topics; assert hasattr(Topics, 'Resolver'); print('Topics OK')"
  ```

#### Task 3: Turn Telemetry Collector (guardkit)
- **Task ID:** TASK-XXX
- **Complexity:** medium
- **Type:** implementation
- **Domain tags:** `telemetry, player-coach, autobuild, data-collection`
- **Files to create/modify:**
  - `src/guardkit/telemetry/__init__.py` (new)
  - `src/guardkit/telemetry/collector.py` (new)
  - `tests/test_telemetry_collector.py` (new)
- **Files NOT to touch:** `src/guardkit/orchestrator/feature_orchestrator.py` (will be integrated in Task 5), `src/guardkit/autobuild/` (will be integrated in Task 5)
- **Dependencies:** Task 1 (uses TurnTelemetry, TaskTelemetry models from nats-core)
- **Inputs:** nats-core telemetry schemas
- **Outputs:** TelemetryCollector class that accumulates turn data during Player-Coach execution
- **Relevant decisions:** D1, D8
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `src/guardkit/telemetry/collector.py`
  - [ ] Class `TelemetryCollector` with methods: `start_task()`, `record_turn()`, `complete_task()`, `get_task_telemetry()`, `get_summary()`
  - [ ] `record_turn()` accepts: turn_number, duration, player_summary, coach_summary, files_touched, optional error info
  - [ ] `complete_task()` computes: clean_execution (bool), recovery_turn (Optional[int]), total_duration, total_tokens
  - [ ] `get_task_telemetry()` returns a valid `TaskTelemetry` instance
  - [ ] `get_summary()` returns aggregated stats: mean turns, clean execution rate, failure category distribution
  - [ ] Thread-safe: multiple calls to `record_turn()` don't corrupt state
  - [ ] Tests pass: `pytest tests/test_telemetry_collector.py -v`
  - [ ] Lint passes: `ruff check src/guardkit/telemetry/`
- **Implementation notes:** The collector is a stateful object that lives for the duration of a task's Player-Coach loop. It accumulates turn data in memory and produces a TaskTelemetry on completion. It does NOT publish events — that's the publisher's job (Task 4). Keep the collector pure (no I/O, no NATS dependency) so it works in standalone mode.
- **Player constraints:** Do not import nats-py or FastStream. The collector depends only on nats-core schemas (Pydantic models) and standard library.
- **Coach validation commands:**
  ```bash
  pytest tests/test_telemetry_collector.py -v
  ruff check src/guardkit/telemetry/
  python -c "from guardkit.telemetry.collector import TelemetryCollector; print('Import OK')"
  ```

#### Task 4: Failure Categoriser (guardkit)
- **Task ID:** TASK-XXX
- **Complexity:** high
- **Type:** implementation
- **Domain tags:** `telemetry, failure-analysis, heuristics, classification, stack-detection`
- **Files to create/modify:**
  - `src/guardkit/telemetry/categoriser.py` (new)
  - `config/failure_heuristics.yaml` (new)
  - `tests/test_failure_categoriser.py` (new)
- **Files NOT to touch:** Any existing guardkit source files
- **Dependencies:** Task 3 (uses TelemetryCollector output)
- **Inputs:** TurnTelemetry list, TaskContext, detected_stack, failure_heuristics.yaml
- **Outputs:** FailureCategoriser class, FailureCategory result, stack-aware configurable heuristics
- **Relevant decisions:** D2, D11, D13
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `src/guardkit/telemetry/categoriser.py`
  - [ ] File exists: `config/failure_heuristics.yaml`
  - [ ] Class `FailureCategoriser` with method: `categorise(turn_telemetry, task_context, detected_stack="generic") -> FailureCategory`
  - [ ] `FailureCategory` has fields: category (literal), confidence (float), basis (str), heuristic_id (Optional[str]), detected_stack (str)
  - [ ] Heuristic-only mode works without LLM (for testing and when LLM unavailable)
  - [ ] Heuristics YAML contains `match_by_stack` entries for: python, typescript, go, csharp, rust, generic
  - [ ] Heuristics YAML contains `stack_independent: true` entries for turn-pattern heuristics
  - [ ] Categoriser selects stack-specific patterns when detected_stack matches, falls back to generic
  - [ ] Loading invalid heuristics YAML raises clear error with line number
  - [ ] Test: Python ImportError in turn data with detected_stack="python" → categorised as "knowledge-gap" with confidence >= 0.8
  - [ ] Test: TypeScript "Cannot find module" with detected_stack="typescript" → categorised as "knowledge-gap" with confidence >= 0.8
  - [ ] Test: Go "cannot find package" with detected_stack="go" → categorised as "knowledge-gap" with confidence >= 0.8
  - [ ] Test: C# "CS0246" error code with detected_stack="csharp" → categorised as "knowledge-gap" with confidence >= 0.8
  - [ ] Test: Unknown error with detected_stack="generic" → uses generic fallback patterns
  - [ ] Test: Oscillating approaches across turns → categorised as "spec-ambiguity" (stack_independent)
  - [ ] Test: Reference to undefined symbol with detected_stack="typescript" → categorised as "context-overflow"
  - [ ] Tests pass: `pytest tests/test_failure_categoriser.py -v`
  - [ ] Lint passes: `ruff check src/guardkit/telemetry/categoriser.py`
- **Implementation notes:** Implement heuristic classification FIRST and completely before any LLM classification. The heuristic engine should be thoroughly tested and reliable on its own. LLM classification is a fallback for cases where heuristics are inconclusive (confidence < 0.6). Use the exact heuristics from Section 4.2 as the initial configuration. The `match_by_stack` field is a dict keyed by stack name — the categoriser looks up `detected_stack` in the dict, falling back to `generic` if the stack isn't present. Heuristics with `stack_independent: true` are evaluated regardless of detected stack. The "turn_pattern" heuristic type requires analysing sequences of turns — e.g., "same_error_repeated_3_turns" means the same error_type appears in 3+ consecutive turns. Default to "spec-ambiguity" when uncertain — it's the safest category because it routes to human review. The `heuristic_id` field (e.g., "KG-001", "CO-002") enables traceability from a categorisation decision back to the specific rule that fired.
- **Player constraints:** LLM classification can be a stub (raise NotImplementedError) in this task — heuristics must be fully functional. Do not import any LLM libraries. Must test with at least 3 different stacks.
- **Coach validation commands:**
  ```bash
  pytest tests/test_failure_categoriser.py -v
  ruff check src/guardkit/telemetry/
  python -c "from guardkit.telemetry.categoriser import FailureCategoriser, FailureCategory; print('Import OK')"
  python -c "
  import yaml
  with open('config/failure_heuristics.yaml') as f:
      data = yaml.safe_load(f)
      assert 'heuristics' in data
      assert 'supported_stacks' in data
      assert len(data['supported_stacks']) >= 6
      # Verify all heuristics have either match_by_stack or stack_independent
      for h in data['heuristics']:
          assert 'match_by_stack' in h or h.get('stack_independent', False), f'Heuristic {h.get(\"id\", \"unknown\")} missing stack config'
      print(f'Loaded {len(data[\"heuristics\"])} stack-aware heuristics OK')
  "
  ```

#### Task 5: Telemetry Integration with AutoBuild (guardkit)
- **Task ID:** TASK-XXX
- **Complexity:** high
- **Type:** integration
- **Domain tags:** `telemetry, autobuild, player-coach, nats, integration`
- **Files to create/modify:**
  - `src/guardkit/telemetry/publisher.py` (new)
  - `src/guardkit/orchestrator/feature_orchestrator.py` (modified — add telemetry hooks)
  - `tests/test_telemetry_publisher.py` (new)
  - `tests/test_telemetry_integration.py` (new)
- **Dependencies:** Tasks 1, 2, 3, 4
- **Inputs:** All telemetry components from Tasks 1-4, existing feature_orchestrator
- **Outputs:** TelemetryPublisher (NATS event publishing), integration hooks in feature_orchestrator
- **Relevant decisions:** D1, D5, D7
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `src/guardkit/telemetry/publisher.py`
  - [ ] Class `TelemetryPublisher` with methods: `publish_task_telemetry()`, `publish_build_blocked()`, `publish_build_summary()`
  - [ ] Publisher is opt-in: instantiated only when `--nats` flag is active
  - [ ] When `--nats` is NOT active: zero telemetry overhead, no NATS imports
  - [ ] feature_orchestrator calls `collector.record_turn()` after each Player-Coach turn
  - [ ] feature_orchestrator calls `collector.complete_task()` and optionally `publisher.publish_task_telemetry()` after each task
  - [ ] When task fails at turn limit: feature_orchestrator calls `categoriser.categorise()` with `detected_stack` from build context, then `publisher.publish_build_blocked()`
  - [ ] `detected_stack` is resolved from codebase signals at build start and propagated through all telemetry
  - [ ] Integration test: mock NATS, run AutoBuild on a simple task, verify telemetry events published
  - [ ] Tests pass: `pytest tests/test_telemetry_publisher.py tests/test_telemetry_integration.py -v`
  - [ ] Lint passes: `ruff check src/guardkit/telemetry/ src/guardkit/orchestrator/`
- **Implementation notes:** This is the critical integration task. The telemetry hooks must be lightweight — they should not slow down the Player-Coach loop. Use async publishing (fire-and-forget) for progress telemetry. The build-blocked event is synchronous because the Build Agent needs to wait for resolver response. When `--nats` is not active, the collector still runs (data is useful locally for the summary display) but the publisher is not instantiated. The feature_orchestrator changes should be minimal — inject telemetry collector and publisher via dependency injection, call hooks at the right points.
- **Player constraints:** Minimal changes to feature_orchestrator — add hook calls, do not restructure the existing orchestration logic. All new logic goes in the telemetry package.
- **Coach validation commands:**
  ```bash
  pytest tests/test_telemetry_publisher.py tests/test_telemetry_integration.py -v
  ruff check src/guardkit/telemetry/ src/guardkit/orchestrator/
  # Verify standalone mode still works
  python -c "
  from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
  # Should import without nats-py installed
  print('Standalone import OK')
  "
  ```

#### Task 6: Fine-Tuning Data Exporter (guardkit)
- **Task ID:** TASK-XXX
- **Complexity:** medium
- **Type:** implementation
- **Domain tags:** `telemetry, fine-tuning, data-export, jsonl`
- **Files to create/modify:**
  - `src/guardkit/telemetry/export.py` (new)
  - `tests/test_fine_tuning_export.py` (new)
- **Files NOT to touch:** Any files modified in Task 5
- **Dependencies:** Task 3 (uses TaskTelemetry model)
- **Inputs:** Collected TaskTelemetry data (from local storage or NATS JetStream replay)
- **Outputs:** FineTuningExporter class producing JSONL files
- **Relevant decisions:** D1, D7
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `src/guardkit/telemetry/export.py`
  - [ ] Class `FineTuningExporter` with method: `export_jsonl(output_path, **filters) -> ExportResult`
  - [ ] Output is valid JSONL (one JSON object per line)
  - [ ] Each record contains: task_id, feature_id, model_id, detected_stack, task_spec, turns, final_status, optional resolution
  - [ ] `strip_sensitive=True` removes patterns matching: API keys, tokens, passwords, credentials (regex-based)
  - [ ] Filter by model_id, status, stack, date range works correctly
  - [ ] ExportResult includes record count and filters applied
  - [ ] Tests pass: `pytest tests/test_fine_tuning_export.py -v`
  - [ ] Lint passes: `ruff check src/guardkit/telemetry/export.py`
- **Implementation notes:** The exporter reads from a local telemetry store (SQLite file or JSON files in `.guardkit/telemetry/`). Start with the simplest viable storage — JSON files, one per build. The sensitive data stripping should use a configurable regex list, not hardcoded patterns. Include a `--dry-run` option that reports what would be exported without writing files.
- **Player constraints:** Do not create any database dependencies beyond what's in standard library (sqlite3 is fine). Do not import any ML/training libraries.
- **Coach validation commands:**
  ```bash
  pytest tests/test_fine_tuning_export.py -v
  ruff check src/guardkit/telemetry/
  python -c "from guardkit.telemetry.export import FineTuningExporter, ExportResult; print('Import OK')"
  ```

### Phase B: Resolver Framework (Implement After Empirical Data Collected)

#### Task 7: Resolver Base Class and Orchestrator (dev-pipeline)
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
- **Dependencies:** Task 2 (uses resolver schemas from nats-core)
- **Inputs:** nats-core resolver schemas, NATSClient
- **Outputs:** BaseResolver abstract class, ResolverOrchestrator routing class
- **Relevant decisions:** D3, D4, D12
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `resolver_agents/base.py`
  - [ ] Abstract class `BaseResolver` with abstract method: `resolve(BuildBlockedPayload) -> ResolverAssistPayload`
  - [ ] BaseResolver includes: `check_graphiti_precedent()`, `record_resolution()`, timeout enforcement
  - [ ] File exists: `resolver_agents/orchestrator.py`
  - [ ] Class `ResolverOrchestrator` subscribes to `pipeline.build-blocked.*` and routes to appropriate resolver
  - [ ] Orchestrator handles: unknown category (logs warning, does not crash), resolver timeout (publishes failure), resolver error (publishes failure)
  - [ ] Tests pass: `pytest tests/test_resolver_base.py tests/test_resolver_orchestrator.py -v`
  - [ ] Lint passes: `ruff check resolver_agents/`
- **Implementation notes:** The orchestrator subscribes to `pipeline.build-blocked.>` (wildcard). It inspects the `failure_category` field and routes to the registered resolver for that category. If no resolver is registered for a category (e.g., resolver container not running), the orchestrator publishes a `pipeline.build-failed` event with reason "no resolver available for {category}". The timeout on resolver execution is critical — a hanging resolver must not block the pipeline indefinitely.
- **Player constraints:** Do not implement concrete resolvers (Tasks 8-10). Only the abstract base and routing orchestrator.
- **Coach validation commands:**
  ```bash
  pytest tests/test_resolver_base.py tests/test_resolver_orchestrator.py -v
  ruff check resolver_agents/
  python -c "from resolver_agents.base import BaseResolver; from resolver_agents.orchestrator import ResolverOrchestrator; print('Import OK')"
  ```

#### Task 8: Knowledge Gap Resolver (dev-pipeline)
- **Task ID:** TASK-XXX
- **Complexity:** high
- **Type:** implementation
- **Domain tags:** `resolver, knowledge-gap, graphiti, context7, documentation, search`
- **Files to create/modify:**
  - `resolver_agents/knowledge_gap.py` (new)
  - `tests/test_knowledge_gap_resolver.py` (new)
- **Files NOT to touch:** resolver_agents/base.py, resolver_agents/orchestrator.py (import only)
- **Dependencies:** Task 7 (extends BaseResolver)
- **Inputs:** BuildBlockedPayload with category "knowledge-gap", Graphiti client, Context7 client
- **Outputs:** ResolverAssistPayload with augmented documentation context
- **Relevant decisions:** D4, D9
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `resolver_agents/knowledge_gap.py`
  - [ ] Class `KnowledgeGapResolver` extends `BaseResolver`
  - [ ] Implements three-layer lookup: Graphiti → Context7 → web search
  - [ ] Each lookup layer only executes if previous layer returned insufficient results
  - [ ] Augmented context includes: relevant documentation excerpts, code examples, source provenance
  - [ ] Context sources list tracks which layer provided each piece of context
  - [ ] Handles: Graphiti unavailable (skip to Context7), Context7 unavailable (skip to web search), all unavailable (return empty assist with low confidence)
  - [ ] Tests pass: `pytest tests/test_knowledge_gap_resolver.py -v`
  - [ ] Lint passes: `ruff check resolver_agents/knowledge_gap.py`
- **Implementation notes:** The resolver extracts the library/module name from the error message and domain tags. For Graphiti lookup, search for nodes tagged with the library name and "documentation" or "api-usage". For Context7, use the `resolve-library-id` and `get-library-docs` pattern. For web search, construct a targeted query: "{library} {error_message} python example". Compile results into a coherent augmented context document, not a raw dump of search results. Limit augmented context to ~4000 tokens to leave room in the Player's context window.
- **Player constraints:** External API calls (Context7, web search) must be wrapped in try/except with timeouts. Do not hardcode any API keys.
- **Coach validation commands:**
  ```bash
  pytest tests/test_knowledge_gap_resolver.py -v
  ruff check resolver_agents/
  python -c "from resolver_agents.knowledge_gap import KnowledgeGapResolver; print('Import OK')"
  ```

#### Task 9: Context Overflow Resolver (dev-pipeline)
- **Task ID:** TASK-XXX
- **Complexity:** high
- **Type:** implementation
- **Domain tags:** `resolver, context-overflow, dependency-analysis, codebase, tree-sitter, stack-agnostic`
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
- **Files NOT to touch:** resolver_agents/base.py, resolver_agents/orchestrator.py (import only)
- **Dependencies:** Task 7 (extends BaseResolver)
- **Inputs:** BuildBlockedPayload with category "context-overflow" and detected_stack, access to build worktree
- **Outputs:** ResolverAssistPayload with focused context package, LanguageAnalyser interface with per-stack implementations
- **Relevant decisions:** D4, D10, D13
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `resolver_agents/context_overflow.py`
  - [ ] File exists: `resolver_agents/language_analysers/base.py`
  - [ ] Abstract class `LanguageAnalyser` with methods: `extract_imports(file_path) -> list[ImportRef]`, `extract_signatures(file_path) -> list[Signature]`, `trace_dependencies(entry_files, worktree) -> DependencyGraph`
  - [ ] Class `ContextOverflowResolver` extends `BaseResolver`
  - [ ] Resolver uses `detected_stack` from BuildBlockedPayload to select the appropriate LanguageAnalyser
  - [ ] Concrete analysers exist for: Python (tree-sitter-python), TypeScript (tree-sitter-typescript), Go (tree-sitter-go), C# (tree-sitter-c-sharp)
  - [ ] GenericAnalyser provides regex-based fallback for unsupported stacks (extracts import-like patterns, function/class definitions)
  - [ ] Identifies files critical to the failing task that weren't in the Player's context via dependency graph traversal
  - [ ] Produces a focused context summary: interfaces, types, key function signatures (not full file contents)
  - [ ] Context package stays within configurable token limit (default: 4000 tokens)
  - [ ] Handles: tree-sitter grammar not installed (falls back to GenericAnalyser with warning), unparseable files (skip with warning), circular imports (detect and break cycle), binary files (skip)
  - [ ] Test: Python project — traces imports to find missing dependency context
  - [ ] Test: TypeScript project — traces import/require statements to find missing type definitions
  - [ ] Test: Go project — traces package imports to find missing interface definitions
  - [ ] Test: Unknown stack — GenericAnalyser provides file-listing-based context
  - [ ] Tests pass: `pytest tests/test_context_overflow_resolver.py tests/test_language_analysers.py -v`
  - [ ] Lint passes: `ruff check resolver_agents/context_overflow.py resolver_agents/language_analysers/`
- **Implementation notes:** Use tree-sitter for all language analysis — it provides consistent AST parsing across languages with a single interface pattern. Each LanguageAnalyser implementation wraps the stack-specific tree-sitter grammar. The pattern is: (1) ContextOverflowResolver receives BuildBlockedPayload with detected_stack, (2) selects the matching LanguageAnalyser (or GenericAnalyser for unknown stacks), (3) for each file the Player touched, the analyser traces imports/dependencies to find files not in the Player's file list, (4) for each dependency file found, extract: class/function signatures, type annotations/interfaces, docstrings/comments, (5) prioritise files that appear in the error trace. The output should read like a reference card — "Here are the interfaces you need to know about" — not a code dump. Tree-sitter grammars should be imported with try/except — if a grammar package isn't installed, log a warning and fall back to GenericAnalyser for that stack. GenericAnalyser uses regex patterns to find import statements and function/class definitions — less precise than tree-sitter but better than nothing. Start with Python and TypeScript analysers as highest priority (most likely project stacks), then Go and C#.
- **Player constraints:** All language analysis must go through the LanguageAnalyser interface — no direct use of Python's `ast` module. Do not read files outside the worktree_path. Respect the token limit configuration. Tree-sitter grammar packages are optional dependencies — resolver must not crash if they're missing.
- **Coach validation commands:**
  ```bash
  pytest tests/test_context_overflow_resolver.py tests/test_language_analysers.py -v
  ruff check resolver_agents/
  python -c "from resolver_agents.context_overflow import ContextOverflowResolver; print('Import OK')"
  python -c "from resolver_agents.language_analysers.base import LanguageAnalyser; print('Interface OK')"
  # Verify graceful degradation without tree-sitter grammars
  python -c "
  from resolver_agents.language_analysers.generic_analyser import GenericAnalyser
  a = GenericAnalyser()
  print(f'Generic analyser OK: supports {a.supported_extensions}')
  "
  ```

#### Task 10: Spec Ambiguity Resolver (dev-pipeline)
- **Task ID:** TASK-XXX
- **Complexity:** high
- **Type:** implementation
- **Domain tags:** `resolver, spec-ambiguity, clarification, graphiti, human-in-the-loop`
- **Files to create/modify:**
  - `resolver_agents/spec_ambiguity.py` (new)
  - `tests/test_spec_ambiguity_resolver.py` (new)
- **Files NOT to touch:** resolver_agents/base.py, resolver_agents/orchestrator.py (import only)
- **Dependencies:** Task 7 (extends BaseResolver)
- **Inputs:** BuildBlockedPayload with category "spec-ambiguity", Graphiti client, NATS client
- **Outputs:** ResolverAssistPayload (if auto-resolved) OR ClarificationRequestPayload (if needs human)
- **Relevant decisions:** D4, D6
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `resolver_agents/spec_ambiguity.py`
  - [ ] Class `SpecAmbiguityResolver` extends `BaseResolver`
  - [ ] Identifies the specific ambiguity from turn analysis (what decision the Player couldn't make)
  - [ ] Searches Graphiti for similar past decisions/ADRs
  - [ ] If high-confidence Graphiti match (>0.8): auto-resolves and publishes ResolverAssistPayload
  - [ ] If low-confidence: publishes ClarificationRequestPayload with structured options
  - [ ] Subscribes to `pipeline.clarification-response.{feature_id}` for human answers
  - [ ] Handles timeout: uses auto_resolve_option if set, otherwise publishes failure
  - [ ] When human responds: stores decision in Graphiti if `seed_to_graphiti=True`
  - [ ] Tests pass: `pytest tests/test_spec_ambiguity_resolver.py -v`
  - [ ] Lint passes: `ruff check resolver_agents/spec_ambiguity.py`
- **Implementation notes:** This is the most complex resolver because it has two paths: auto-resolve (fast, no human) and human-clarification (slow, blocking). The Graphiti precedent search should look for: ADR nodes matching the ambiguity domain, previous clarification responses for similar features, and architecture decision nodes. The clarification question should be specific and actionable — "Should authentication use JWT or session cookies? Here are the tradeoffs in your codebase context..." not "What should I do?". Always provide at least 2 options with rationale. The auto_resolve_option provides a sensible default for overnight runs when no human is available.
- **Player constraints:** The clarification timeout must be configurable (default 60 minutes). Do not block the NATS event loop while waiting for human response — use async wait with timeout.
- **Coach validation commands:**
  ```bash
  pytest tests/test_spec_ambiguity_resolver.py -v
  ruff check resolver_agents/
  python -c "from resolver_agents.spec_ambiguity import SpecAmbiguityResolver; print('Import OK')"
  ```

#### Task 11: Docker Compose for Resolver Agents (dev-pipeline)
- **Task ID:** TASK-XXX
- **Complexity:** low
- **Type:** configuration
- **Domain tags:** `docker, deployment, resolver, infrastructure`
- **Files to create/modify:**
  - `docker-compose.resolvers.yaml` (new)
  - `resolver_agents/Dockerfile` (new)
- **Files NOT to touch:** `docker-compose.yaml` (main pipeline compose file)
- **Dependencies:** Tasks 7-10
- **Inputs:** Existing docker-compose.yaml patterns from dev-pipeline
- **Outputs:** Optional Docker Compose overlay for resolver containers
- **Relevant decisions:** D12
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `docker-compose.resolvers.yaml`
  - [ ] File exists: `resolver_agents/Dockerfile`
  - [ ] Compose file defines services: `resolver-orchestrator`, `knowledge-gap-resolver`, `context-overflow-resolver`, `spec-ambiguity-resolver`
  - [ ] Each service connects to the existing NATS network
  - [ ] Services can be started with: `docker compose -f docker-compose.yaml -f docker-compose.resolvers.yaml up`
  - [ ] Resolver services are independently startable (can run just knowledge-gap if that's the only one needed)
  - [ ] Environment variables for: NATS_URL, GRAPHITI_URL, RESOLVER_TIMEOUT, LOG_LEVEL
  - [ ] Dockerfile installs tree-sitter and grammar packages for Python, TypeScript, Go, C# (configurable via build args)
  - [ ] Grammar packages are installed as optional — Dockerfile should not fail if a grammar fails to install
- **Implementation notes:** Use Docker Compose override pattern — `docker-compose.resolvers.yaml` extends the base `docker-compose.yaml`. This keeps resolvers truly optional. Each resolver runs as a separate container for independent scaling and restart. Share a common base image built from `resolver_agents/Dockerfile` with the specific resolver class as an entrypoint argument.
- **Player constraints:** Do not modify the base docker-compose.yaml. Use only the override/extend pattern.
- **Coach validation commands:**
  ```bash
  # Validate compose file syntax
  docker compose -f docker-compose.yaml -f docker-compose.resolvers.yaml config > /dev/null 2>&1 && echo "Compose config valid" || echo "Compose config invalid"
  # Validate Dockerfile syntax
  docker build --check -f resolver_agents/Dockerfile . 2>/dev/null || echo "Dockerfile check not supported, manual review needed"
  ```

## 6. Test Strategy

### Unit Tests
| Test File | Covers | Key Assertions |
|-----------|--------|---------------|
| `tests/test_telemetry_schemas.py` (nats-core) | TurnTelemetry, TaskTelemetry models | Validation, serialisation roundtrip, required fields |
| `tests/test_resolver_schemas.py` (nats-core) | All resolver event schemas | Validation, literal field constraints, defaults |
| `tests/test_telemetry_collector.py` (guardkit) | TelemetryCollector state management | Turn recording, task completion, summary stats |
| `tests/test_failure_categoriser.py` (guardkit) | Heuristic and LLM classification | Stack-specific pattern matching (Python, TS, Go, C#), generic fallback, confidence thresholds, default category |
| `tests/test_fine_tuning_export.py` (guardkit) | JSONL export with filtering | Valid JSONL, detected_stack field present, sensitive data stripping, filter by stack/model/status |
| `tests/test_resolver_base.py` (dev-pipeline) | BaseResolver contract | Timeout enforcement, Graphiti precedent lookup |
| `tests/test_resolver_orchestrator.py` (dev-pipeline) | Event routing | Category → resolver mapping, unknown category handling, timeout |
| `tests/test_knowledge_gap_resolver.py` (dev-pipeline) | Three-layer documentation lookup | Layer fallback, context compilation, token limits |
| `tests/test_context_overflow_resolver.py` (dev-pipeline) | Dependency analysis and context packaging | Import tracing per-stack (Python, TS, Go, C#), signature extraction, token limits, graceful grammar degradation |
| `tests/test_language_analysers.py` (dev-pipeline) | tree-sitter language analysers and generic fallback | Python import extraction, TypeScript import/require, Go package imports, C# using statements, generic regex fallback |
| `tests/test_spec_ambiguity_resolver.py` (dev-pipeline) | Clarification flow | Auto-resolve path, human-clarification path, timeout handling |

### Integration Tests
| Test File | Covers | Prerequisites |
|-----------|--------|--------------|
| `tests/test_telemetry_integration.py` (guardkit) | Telemetry hooks in AutoBuild flow | Mock NATS, sample feature YAML |
| `tests/integration/test_resolver_flow.py` (dev-pipeline) | Full blocked → resolver → assist → resume flow | NATS running, mock Graphiti |

### Manual Verification
- [ ] Run AutoBuild on a deliberately failing task, verify telemetry events in NATS monitoring
- [ ] Verify build-blocked event appears with correct failure category
- [ ] Verify fine-tuning export produces valid JSONL that can be loaded by a training script
- [ ] Verify resolver assist injects context and Player-Coach resumes
- [ ] Verify human clarification surfaces in dashboard (when dashboard is available)
- [ ] Verify standalone mode: AutoBuild works without NATS, telemetry collector still populates summary display

## 7. Dependencies & Setup

### Python Dependencies (nats-core additions)
```
# No new dependencies — uses existing Pydantic v2
```

### Python Dependencies (guardkit additions)
```
# requirements.txt additions
pyyaml>=6.0      # For failure_heuristics.yaml parsing (may already be present)
```

### Python Dependencies (dev-pipeline resolver additions)
```
# requirements.txt additions
nats-core @ git+ssh://git@github.com/appmilla/nats-core.git

# Tree-sitter for stack-agnostic code analysis (Context Overflow Resolver)
tree-sitter>=0.21.0
tree-sitter-python>=0.21.0      # Python grammar
tree-sitter-typescript>=0.21.0  # TypeScript/JavaScript grammar
tree-sitter-go>=0.21.0          # Go grammar
tree-sitter-c-sharp>=0.21.0     # C# grammar
# tree-sitter-rust>=0.21.0      # Rust grammar (add when needed)

# Note: tree-sitter grammars are optional dependencies.
# The resolver degrades gracefully to GenericAnalyser (regex-based)
# if a grammar is not installed. Install only the grammars you need.
```

### System Dependencies
```bash
# Resolver agents run in Docker alongside existing pipeline services
# No new system dependencies beyond existing Docker + NATS setup
```

### Environment Variables (resolver agents)
```bash
NATS_URL=nats://100.x.y.z:4222        # Tailscale NATS address
GRAPHITI_URL=http://100.x.y.z:8000     # Graphiti API on NAS
RESOLVER_TIMEOUT=300                    # Seconds before resolver gives up
CONTEXT7_ENABLED=true                   # Enable Context7 lookups
LOG_LEVEL=INFO
```

## 8. File Tree (Target State)

```
# nats-core additions
nats-core/
├── schemas/
│   ├── telemetry.py                    # Task 1
│   ├── resolver.py                     # Task 2
│   └── __init__.py                     # Modified
├── topics.py                           # Modified (Task 2)
└── tests/
    ├── test_telemetry_schemas.py       # Task 1
    └── test_resolver_schemas.py        # Task 2

# guardkit additions
guardkit/
├── src/guardkit/
│   ├── telemetry/
│   │   ├── __init__.py                 # Task 3
│   │   ├── collector.py               # Task 3
│   │   ├── categoriser.py             # Task 4
│   │   ├── publisher.py               # Task 5
│   │   └── export.py                  # Task 6
│   └── orchestrator/
│       └── feature_orchestrator.py     # Modified (Task 5)
├── config/
│   └── failure_heuristics.yaml         # Task 4
└── tests/
    ├── test_telemetry_collector.py     # Task 3
    ├── test_failure_categoriser.py     # Task 4
    ├── test_telemetry_publisher.py     # Task 5
    ├── test_telemetry_integration.py   # Task 5
    └── test_fine_tuning_export.py      # Task 6

# dev-pipeline additions
dev-pipeline/
├── resolver_agents/
│   ├── __init__.py                     # Task 7
│   ├── base.py                         # Task 7
│   ├── orchestrator.py                 # Task 7
│   ├── knowledge_gap.py               # Task 8
│   ├── context_overflow.py            # Task 9
│   ├── language_analysers/            # Task 9
│   │   ├── __init__.py
│   │   ├── base.py                    # LanguageAnalyser interface
│   │   ├── python_analyser.py         # tree-sitter-python
│   │   ├── typescript_analyser.py     # tree-sitter-typescript
│   │   ├── go_analyser.py            # tree-sitter-go
│   │   ├── csharp_analyser.py        # tree-sitter-c-sharp
│   │   └── generic_analyser.py       # regex-based fallback
│   ├── spec_ambiguity.py              # Task 10
│   └── Dockerfile                      # Task 11
├── docker-compose.resolvers.yaml       # Task 11
└── tests/
    ├── test_resolver_base.py           # Task 7
    ├── test_resolver_orchestrator.py   # Task 7
    ├── test_knowledge_gap_resolver.py  # Task 8
    ├── test_context_overflow_resolver.py # Task 9
    ├── test_language_analysers.py      # Task 9
    ├── test_spec_ambiguity_resolver.py # Task 10
    └── integration/
        └── test_resolver_flow.py       # Integration
```

## 9. Out of Scope

- **Dashboard UI for clarification** — The `pipeline.build-needs-clarification` event is defined, but the dashboard rendering is a separate feature. Initially, clarifications can be answered via the Pipeline CLI tool.
- **Reachy Mini voice notifications** — Reachy announcing blocked builds is a Ship's Computer integration, not part of this feature.
- **Automatic fine-tuning pipeline** — The exporter produces JSONL; actually running the fine-tuning job on vLLM is a separate workflow.
- **Rust tree-sitter grammar** — Start with Python, TypeScript, Go, C# analysers. Rust grammar is an additional tree-sitter-rust dependency when needed.
- **Multi-resolver collaboration** — A single resolver handles each blocked event. If that resolver fails, it escalates to human. No chaining of resolvers.
- **Cost tracking per resolution** — Token usage tracking for resolver LLM calls is deferred. The telemetry captures tokens at the Player-Coach level.
- **Retry budget configuration** — V1 allows exactly one resolver-assisted retry per task. Configurable retry budgets are a future enhancement based on empirical data.

## 10. Open Questions (Resolved)

| Question | Resolution |
|----------|-----------|
| Should resolvers run on the same machine as the Build Agent? | Yes — Dell ProMax has sufficient resources, and local execution avoids network latency. Resolvers use lightweight LLM calls (classification, not code generation) or external API lookups. |
| Should the telemetry store use a database or files? | Start with JSON files in `.guardkit/telemetry/`. Migrate to SQLite if querying becomes a bottleneck. Avoid external database dependency for something that's primarily a data collection feature. |
| How do we prevent the resolver from making things worse? | Resolvers provide context, never modify code. The Player-Coach loop remains the sole code modification path. If the assisted retry also fails, it's a hard stop — no infinite loops. |
| Should the build-blocked event include the full codebase state? | No — only turn summaries, error info, and task context. The resolver can read the worktree directly if it needs file contents (it runs on the same machine). |
| What happens if multiple tasks in the same feature get blocked? | Each blocked task gets its own resolver cycle. They're independent — different tasks may have different failure categories. The Build Agent processes them sequentially (existing behaviour). |
| Should resolved augmented context be persisted in Graphiti? | Yes — successful resolutions (where the assisted retry succeeds) are recorded as knowledge nodes in Graphiti. This means the same problem won't require a resolver the second time — it becomes Layer 1 prevention. |
| Should the context-overflow resolver support only Python initially? | No — the platform is stack-agnostic by design. Use tree-sitter for universal language analysis with a LanguageAnalyser interface and per-stack implementations. GenericAnalyser (regex-based) provides fallback for stacks without tree-sitter grammars. Tree-sitter grammars are optional dependencies — missing grammars degrade to GenericAnalyser, not failure. |
| How should failure heuristics handle multiple technology stacks? | Heuristics YAML uses `match_by_stack` dicts keyed by stack name, with `generic` as mandatory fallback. Turn-pattern heuristics (approach oscillation, contradicting feedback) are marked `stack_independent: true`. The categoriser receives `detected_stack` from the build context and selects appropriate patterns. |

---

## 11. Graphiti ADR Seeding

### ADR Documents to Generate

```markdown
# docs/adr/ADR-TLD-001-three-layer-defence.md
Status: Accepted
Decision: Implement three-layer build defence: prevention (feature-spec, feature-plan, Graphiti), 
recovery (Player-Coach loop), assisted resolution (resolver agents via NATS).
Context: AutoBuild fails silently when Player-Coach exhausts turns. Moving to open-weight models 
will increase failure rates. Need automated resolution without uncontrolled agent swarms.

# docs/adr/ADR-TLD-002-typed-failure-categories.md
Status: Accepted
Decision: Categorise build failures as knowledge-gap, context-overflow, or spec-ambiguity with 
heuristic-first classification.
Context: Different failure types need different resolution strategies. Generic "help" is inefficient.

# docs/adr/ADR-TLD-003-resolvers-advisory-only.md
Status: Accepted
Decision: Resolver agents provide augmented context via NATS events. They never modify the codebase.
Context: Preserving Player-Coach as sole code modification path maintains audit trail and prevents 
emergent behaviour.

# docs/adr/ADR-TLD-004-instrumentation-before-resolution.md
Status: Accepted
Decision: Ship telemetry instrumentation (Phase A) before resolver agents (Phase B). Let data 
reveal which resolver to prioritise.
Context: Avoids building the wrong resolver first. Telemetry also serves fine-tuning dataset needs.

# docs/adr/ADR-TLD-005-stack-agnostic-analysis.md
Status: Accepted
Decision: All telemetry, failure categorisation, and resolver analysis must be technology-stack 
agnostic. Use tree-sitter for universal code analysis, per-stack failure heuristics with generic 
fallbacks, and detected_stack propagation through all telemetry.
Context: Platform builds Python, TypeScript, Go, C#, Rust projects. Python-only tooling would 
exclude client projects and violate the stack-agnostic principle established in /feature-spec.
```

### Seeding Commands

```bash
guardkit graphiti add-context docs/adr/ADR-TLD-001-three-layer-defence.md
guardkit graphiti add-context docs/adr/ADR-TLD-002-typed-failure-categories.md
guardkit graphiti add-context docs/adr/ADR-TLD-003-resolvers-advisory-only.md
guardkit graphiti add-context docs/adr/ADR-TLD-004-instrumentation-before-resolution.md
guardkit graphiti add-context docs/adr/ADR-TLD-005-stack-agnostic-analysis.md
guardkit graphiti add-context docs/research/three-layer-defence/feature-spec.md
guardkit graphiti verify --verbose
```

### Quality Gate Configuration

```yaml
# .guardkit/quality-gates/FEAT-XXX.yaml
feature_id: FEAT-XXX
quality_gates:
  lint:
    command: "ruff check src/guardkit/telemetry/"
    required: true
  unit_tests:
    command: "pytest tests/test_telemetry_collector.py tests/test_failure_categoriser.py tests/test_fine_tuning_export.py tests/test_telemetry_publisher.py -v --tb=short"
    required: true
  integration_tests:
    command: "pytest tests/test_telemetry_integration.py -v"
    required: true
  import_check:
    command: "python -c \"from guardkit.telemetry.collector import TelemetryCollector; from guardkit.telemetry.categoriser import FailureCategoriser; from guardkit.telemetry.publisher import TelemetryPublisher; from guardkit.telemetry.export import FineTuningExporter; print('All imports OK')\""
    required: true
```

## 12. Implementation Phasing

### Phase A: Instrumentation (Weeks 1-3) — BUILD THIS FIRST

Tasks 1-6. Delivers: build telemetry collection, failure categorisation, NATS event publishing, fine-tuning data export. This phase is independently valuable — it provides the empirical data needed to make informed decisions about Phase B, AND produces training data for vLLM fine-tuning.

**Success criteria:** Run 20+ AutoBuild features on Dell ProMax with Qwen3-Coder-Next. Analyse telemetry to determine: mean turns per task, failure rate, failure category distribution, correlation between task complexity and turns.

### Phase B: Resolver Framework (Weeks 4-7) — BUILD BASED ON DATA

Tasks 7-11. Build the resolver framework (Task 7) and Docker infrastructure (Task 11) first, then implement resolvers in priority order based on Phase A data. If 70% of failures are knowledge-gap, build Task 8 first. If context-overflow dominates, build Task 9 first.

**Success criteria:** Resolver-assisted retry succeeds for >50% of previously-failing tasks. No increase in total build time for tasks that succeed without resolvers.

### Evaluation Milestone: guardkit_vs_vanilla with Resolvers

Once Phase B is operational, extend the existing `guardkit_vs_vanilla` evaluation to include a third condition: GuardKit with resolvers enabled. This provides scientific evidence for the value of each defence layer.
