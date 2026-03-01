# Feature Specification: Three-Layer Build Defence — nats-core

**Date:** March 2026  
**Author:** Rich (with Claude AI assistance)  
**Status:** Ready for Implementation  
**Research Method:** Claude Desktop (extended thinking) → GuardKit `/feature-plan`  
**Target Repo:** `appmilla/nats-core`  
**Target Branch:** `feature/three-layer-defence-schemas`  
**Feature ID:** FEAT-XXX *(assigned by `/feature-plan`)*  
**Parent Spec:** `docs/research/three-layer-defence/feature-spec.md`

---

## 1. Problem Statement

The dev pipeline's nats-core shared contract layer needs new message schemas and topic registry extensions to support build telemetry collection, failure categorisation events, and resolver agent coordination. These schemas are the foundation — guardkit and dev-pipeline both depend on them. Without typed, validated message contracts for telemetry and resolver events, the three-layer defence system cannot communicate across its components.

## 2. Decision Log

*Subset of decisions from the parent spec relevant to this repo.*

| # | Decision | Rationale | Alternatives Rejected | ADR Status |
|---|----------|-----------|----------------------|------------|
| D1 | Instrument build telemetry as structured events, not just log output | Telemetry data serves three purposes: resolver agent routing, fine-tuning datasets, empirical evidence for investment decisions. Structured data is queryable; logs are not. | Unstructured logging, external APM tools | Accepted |
| D2 | Categorise failures into three typed categories: knowledge-gap, context-overflow, specification-ambiguity | Each failure type has a fundamentally different resolution path. Typed categories enable targeted resolver selection. | Single generic resolver, more granular categories, no categorisation | Accepted |
| D5 | Build telemetry publishes via existing `pipeline.build-progress` events with extended payload, plus new `pipeline.build-blocked` event | Extends the existing schema rather than creating a parallel telemetry system. Schema extension follows nats-core's additive-only versioning policy. | Separate telemetry namespace, sidecar metrics service, in-process only logging | Accepted |
| D6 | Human-in-the-loop clarification surfaces via `pipeline.build-needs-clarification` event | Specification ambiguity that resolvers can't handle must reach the human efficiently via dashboard or Reachy voice. | Email/Slack notifications, block indefinitely, auto-resolve with best guess | Accepted |
| D8 | Telemetry includes per-turn Player-Coach exchange summaries (not full transcripts) | Full transcripts would blow up event payloads. Summaries capture essential signal within NATS 64KB payload limit. | Full transcripts, only final error, no exchange data | Accepted |
| D13 | All schemas must be technology-stack agnostic | The platform builds Python, TypeScript, Go, C#, Rust. Telemetry and blocked events carry `detected_stack` so downstream components can select stack-appropriate behaviour. | Python-only fields, no stack tracking | Accepted |

**Warnings & Constraints:**
- Schema changes must be additive only — new optional fields with defaults, never remove or rename existing fields
- All payloads must stay under 64KB (NATS default max payload)
- Use Pydantic v2 `model_config` with `extra="ignore"` for forward compatibility
- `detected_stack` must use the same literal values as `/feature-spec` StackDetector: `"python"`, `"typescript"`, `"go"`, `"csharp"`, `"rust"`, `"generic"`
- Topic registry must use `{feature_id}` placeholder pattern consistent with existing `Topics.Pipeline`
- Resolver topics use a separate namespace (`resolver.*`) from pipeline topics — different concerns (internal coordination vs pipeline state transitions)

## 3. Architecture

### 3.1 Where This Fits

```
┌─────────────────────────────────────────────────────────────┐
│                        nats-core                             │
│              (Shared Contract Layer)                          │
│                                                              │
│  schemas/                                                    │
│  ├── pipeline.py          ← existing pipeline event schemas  │
│  ├── agents.py            ← existing agent event schemas     │
│  ├── telemetry.py         ← NEW: turn/task telemetry models  │
│  └── resolver.py          ← NEW: blocked/assist/clarify      │
│                                                              │
│  topics.py                ← MODIFIED: +Resolver, +Telemetry  │
│                                                              │
│              ▼ consumed by ▼                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   guardkit    │  │ dev-pipeline │  │  future      │       │
│  │  (publisher)  │  │  (consumer)  │  │  consumers   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Message Schemas

#### Telemetry Models (schemas/telemetry.py)

```python
class TurnTelemetry(BaseModel):
    """Per-turn data collected during Player-Coach loop."""
    turn_number: int                        # >= 1
    duration_seconds: float
    player_action_summary: str              # ~100 words: what the Player did
    coach_feedback_summary: str             # ~100 words: what the Coach found
    files_touched: list[str]                # files the Player modified
    error_type: Optional[str] = None        # e.g., "ImportError", "CS0246", "Cannot find module"
    error_signature: Optional[str] = None   # hash of deduplicated stack trace
    tokens_used: Optional[int] = None       # total tokens for this turn
    model_id: Optional[str] = None          # e.g., "qwen3-coder-next", "claude-sonnet-4-5"

class TaskTelemetry(BaseModel):
    """Telemetry for a completed or failed task."""
    task_id: str
    feature_id: str
    build_id: str
    status: str                             # "success" | "failed" | "blocked"
    turns_used: int
    turns_max: int
    total_duration_seconds: float
    total_tokens: Optional[int] = None
    model_id: Optional[str] = None
    detected_stack: Optional[str] = None    # "python" | "typescript" | "go" | "csharp" | "rust" | "generic"
    complexity: str                         # "low" | "medium" | "high"
    domain_tags: list[str]
    turn_telemetry: list[TurnTelemetry]
    failure_category: Optional[str] = None  # "knowledge-gap" | "context-overflow" | "spec-ambiguity"
    failure_category_confidence: Optional[float] = None  # 0.0 - 1.0
    clean_execution: bool                   # True if succeeded on first turn
    recovery_turn: Optional[int] = None     # Turn where it recovered (if turns > 1 but succeeded)
```

#### Resolver Models (schemas/resolver.py)

```python
class TaskContext(BaseModel):
    """Subset of task spec relevant to resolvers."""
    task_id: str
    description: str
    complexity: str
    acceptance_criteria: list[str]
    implementation_notes: Optional[str] = None
    relevant_decisions: list[str]           # D1, D2, etc.

class TurnSummary(BaseModel):
    """Condensed Player-Coach exchange for resolver analysis."""
    turn_number: int
    player_approach: str                    # ~50 words
    coach_finding: str                      # ~50 words
    error_type: Optional[str] = None
    key_files: list[str]                    # Most relevant files this turn

class BuildBlockedPayload(BaseModel):
    """Published when Player-Coach exhausts turns without convergence."""
    feature_id: str
    build_id: str
    task_id: str
    repo: str
    branch: str
    detected_stack: str                     # "python" | "typescript" | "go" | "csharp" | "rust" | "generic"
    failure_category: str                   # "knowledge-gap" | "context-overflow" | "spec-ambiguity"
    category_confidence: float              # 0.0 - 1.0
    category_basis: str                     # Human-readable explanation
    task_context: TaskContext
    turn_summaries: list[TurnSummary]       # Last 3-5 turns condensed
    error_signature: Optional[str] = None
    error_message: Optional[str] = None     # Last error, truncated to 1000 chars
    domain_tags: list[str]
    files_touched: list[str]
    worktree_path: str
    resolver_attempt: int = 0               # 0 = first block, 1 = blocked after resolver assist
    timestamp: datetime

class ContextSource(BaseModel):
    """Provenance for augmented context."""
    source_type: str                        # "graphiti" | "context7" | "web_search" | "codebase_analysis" | "human_clarification"
    source_reference: str                   # URL, Graphiti node ID, file path, etc.
    relevance_summary: str                  # Why this source was included

class ResolverAssistPayload(BaseModel):
    """Published by resolver agents with augmented context."""
    feature_id: str
    build_id: str
    task_id: str
    resolver_type: str                      # "knowledge-gap" | "context-overflow" | "spec-ambiguity"
    resolver_id: str                        # agent identifier
    augmented_context: str                  # The actual content to inject into Player-Coach
    context_sources: list[ContextSource]
    resolution_summary: str                 # What the resolver found/decided
    confidence: float                       # How confident the resolver is in its assist
    duration_seconds: float
    timestamp: datetime

class ClarificationOption(BaseModel):
    option_id: int
    description: str
    rationale: str
    graphiti_precedent: Optional[str] = None

class ClarificationRequestPayload(BaseModel):
    """Published when spec-ambiguity resolver needs human input."""
    feature_id: str
    build_id: str
    task_id: str
    question: str
    options: list[ClarificationOption]
    context_summary: str
    urgency: str                            # "blocking" | "advisory"
    auto_resolve_option: Optional[int] = None
    timeout_minutes: int = 60
    timestamp: datetime

class ClarificationResponsePayload(BaseModel):
    """Published by dashboard when human responds to clarification."""
    feature_id: str
    build_id: str
    task_id: str
    selected_option: Optional[int] = None
    custom_response: Optional[str] = None
    respondent: str                         # "rich" | "james" | "auto-timeout"
    seed_to_graphiti: bool = True
    timestamp: datetime
```

#### Topic Registry Extensions (topics.py)

```python
class Topics:
    class Pipeline:
        # ... existing topics unchanged ...
        BUILD_BLOCKED = "pipeline.build-blocked.{feature_id}"
        BUILD_NEEDS_CLARIFICATION = "pipeline.build-needs-clarification.{feature_id}"
        CLARIFICATION_RESPONSE = "pipeline.clarification-response.{feature_id}"

    class Resolver:
        """Resolver agent events."""
        KNOWLEDGE_ASSIST = "resolver.knowledge-assist.{feature_id}"
        CONTEXT_ASSIST = "resolver.context-assist.{feature_id}"
        CLARIFICATION_ASSIST = "resolver.clarification-assist.{feature_id}"
        ALL = "resolver.>"

    class Telemetry:
        """Build telemetry for analysis and fine-tuning."""
        TASK_COMPLETE = "telemetry.task-complete.{feature_id}"
        BUILD_SUMMARY = "telemetry.build-summary.{feature_id}"
        EXPORT_REQUEST = "telemetry.export-request"
        EXPORT_COMPLETE = "telemetry.export-complete"
```

## 4. Implementation Tasks

### Task 1: Build Telemetry Schema
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
- **Relevant decisions:** D1, D5, D8, D13
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `schemas/telemetry.py`
  - [ ] Classes `TurnTelemetry`, `TaskTelemetry` importable
  - [ ] All fields have type annotations and appropriate defaults
  - [ ] `TaskTelemetry.detected_stack` accepts: "python", "typescript", "go", "csharp", "rust", "generic", None
  - [ ] Validation: `TurnTelemetry(turn_number=0)` raises ValidationError (turn_number must be >= 1)
  - [ ] Validation: `TaskTelemetry` requires feature_id, task_id, build_id, status
  - [ ] Serialisation roundtrip: model → JSON → model preserves all fields
  - [ ] Tests pass: `pytest tests/test_telemetry_schemas.py -v`
  - [ ] Lint passes: `ruff check schemas/telemetry.py`
- **Implementation notes:** Follow the exact field definitions from Section 3.2. Use Pydantic v2 model_config with `extra="ignore"` for forward compatibility. The `model_id` field is Optional because early builds may not report it. The `detected_stack` field is Optional on TaskTelemetry because it may not be available in all contexts.
- **Player constraints:** Do not modify any existing schema files. Import only from pydantic and standard library.
- **Coach validation commands:**
  ```bash
  pytest tests/test_telemetry_schemas.py -v
  ruff check schemas/
  python -c "from schemas.telemetry import TurnTelemetry, TaskTelemetry; print('Import OK')"
  ```

### Task 2: Build Blocked and Resolver Schemas
- **Task ID:** TASK-XXX
- **Complexity:** medium
- **Type:** implementation
- **Domain tags:** `nats, schema, pydantic, resolver, events`
- **Files to create/modify:**
  - `schemas/resolver.py` (new)
  - `schemas/__init__.py` (modified — add exports)
  - `topics.py` (modified — add Resolver and Telemetry topic classes)
  - `tests/test_resolver_schemas.py` (new)
- **Files NOT to touch:** Existing schema files except __init__.py, existing topic constants in Topics.Pipeline or Topics.Agents
- **Dependencies:** Task 1 (uses TurnTelemetry types)
- **Inputs:** Task 1 telemetry models, existing topic registry pattern
- **Outputs:** BuildBlockedPayload, ResolverAssistPayload, ClarificationRequestPayload, ClarificationResponsePayload, TaskContext, TurnSummary, ContextSource, ClarificationOption, plus topic registry extensions
- **Relevant decisions:** D2, D5, D6, D13
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `schemas/resolver.py`
  - [ ] All 8 model classes importable from `schemas.resolver`
  - [ ] `BuildBlockedPayload.failure_category` validates against literal values only ("knowledge-gap", "context-overflow", "spec-ambiguity")
  - [ ] `BuildBlockedPayload.detected_stack` is required (not Optional) — stack must be known by the time a build is blocked
  - [ ] `ClarificationRequestPayload.timeout_minutes` has default of 60
  - [ ] `ClarificationResponsePayload.respondent` accepts "rich", "james", "auto-timeout"
  - [ ] `Topics.Resolver` class exists with: KNOWLEDGE_ASSIST, CONTEXT_ASSIST, CLARIFICATION_ASSIST, ALL
  - [ ] `Topics.Telemetry` class exists with: TASK_COMPLETE, BUILD_SUMMARY, EXPORT_REQUEST, EXPORT_COMPLETE
  - [ ] No existing topic constants in `Topics.Pipeline` or `Topics.Agents` have been modified
  - [ ] Tests pass: `pytest tests/test_resolver_schemas.py -v`
  - [ ] Lint passes: `ruff check schemas/resolver.py topics.py`
- **Implementation notes:** Follow schema definitions from Section 3.2 exactly. The topic registry must use the `{feature_id}` placeholder pattern consistent with existing `Topics.Pipeline`. Resolver topics use a separate namespace (`resolver.*`) from pipeline topics. New Pipeline topics (BUILD_BLOCKED, BUILD_NEEDS_CLARIFICATION, CLARIFICATION_RESPONSE) are additive to the existing Pipeline class.
- **Player constraints:** Do not modify existing topic constants. Only add new classes/constants. Only add new fields to existing classes.
- **Coach validation commands:**
  ```bash
  pytest tests/test_resolver_schemas.py -v
  ruff check schemas/ topics.py
  python -c "from schemas.resolver import BuildBlockedPayload, ResolverAssistPayload; print('Import OK')"
  python -c "from topics import Topics; assert hasattr(Topics, 'Resolver'); assert hasattr(Topics, 'Telemetry'); print('Topics OK')"
  ```

## 5. Test Strategy

### Unit Tests
| Test File | Covers | Key Assertions |
|-----------|--------|---------------|
| `tests/test_telemetry_schemas.py` | TurnTelemetry, TaskTelemetry models | Validation (turn_number >= 1, required fields), serialisation roundtrip, detected_stack literal values, Optional fields default to None |
| `tests/test_resolver_schemas.py` | All resolver event schemas | Validation (failure_category literals, detected_stack required on BuildBlocked), ClarificationOption structure, ClarificationResponse respondent values, Topic constants exist |

### Manual Verification
- [ ] Import all new schemas in a Python REPL — no import errors
- [ ] Create sample instances of each schema with realistic data — no validation errors
- [ ] Verify existing nats-core tests still pass — zero regression

## 6. Dependencies & Setup

### Python Dependencies
```
# No new dependencies — uses existing Pydantic v2
```

## 7. File Tree (Target State)

```
nats-core/
├── schemas/
│   ├── __init__.py              # Modified — add telemetry and resolver exports
│   ├── pipeline.py              # UNCHANGED
│   ├── agents.py                # UNCHANGED
│   ├── telemetry.py             # NEW (Task 1)
│   └── resolver.py              # NEW (Task 2)
├── topics.py                    # Modified — add Resolver and Telemetry classes (Task 2)
└── tests/
    ├── test_telemetry_schemas.py   # NEW (Task 1)
    └── test_resolver_schemas.py    # NEW (Task 2)
```

## 8. Out of Scope

- Any publishing or consuming logic — nats-core defines contracts only
- NATS infrastructure changes — those live in dev-pipeline
- Any business logic — resolvers, categorisation, telemetry collection are downstream concerns
- Changes to existing schemas — this is additive only

## 9. Sequencing

This repo must be implemented **first**. Both guardkit and dev-pipeline depend on these schemas. Once merged and the package is updated (`pip install git+ssh://...`), the other repos can proceed.

**Estimated effort:** 2-3 days  
**Blocking:** guardkit Tasks 3-6, dev-pipeline Tasks 7-11
