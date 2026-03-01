# Feature Specification: Three-Layer Build Defence — guardkit

**Date:** March 2026  
**Author:** Rich (with Claude AI assistance)  
**Status:** Ready for Implementation  
**Research Method:** Claude Desktop (extended thinking) → GuardKit `/feature-plan`  
**Target Repo:** `appmilla/guardkit`  
**Target Branch:** `feature/three-layer-defence-telemetry`  
**Feature ID:** FEAT-XXX *(assigned by `/feature-plan`)*  
**Parent Spec:** `docs/research/three-layer-defence/feature-spec.md`

---

## 1. Problem Statement

GuardKit's AutoBuild Player-Coach loop currently produces a summary display at completion but captures no structured telemetry during execution. When builds fail at the 5-turn limit, the failure is reported but not categorised — there's no data to understand why builds fail, which tasks struggle most, or how model capability affects convergence. As implementation moves to open-weight models on the Dell ProMax, we need: (a) per-turn telemetry collection during Player-Coach execution, (b) stack-aware failure categorisation when turns are exhausted, (c) NATS event publishing for pipeline coordination with resolver agents, and (d) fine-tuning data export to improve local model performance over time.

## 2. Decision Log

*Subset of decisions from the parent spec relevant to this repo.*

| # | Decision | Rationale | Alternatives Rejected | ADR Status |
|---|----------|-----------|----------------------|------------|
| D1 | Instrument build telemetry as structured events, not just log output | Telemetry serves three purposes: resolver routing, fine-tuning datasets, empirical evidence. Structured data is queryable; logs are not. | Unstructured logging, external APM tools | Accepted |
| D2 | Categorise failures into three typed categories: knowledge-gap, context-overflow, specification-ambiguity | Each failure type needs a different resolution path. Typed categories enable targeted resolver selection. | Single generic resolver, more granular categories, no categorisation | Accepted |
| D5 | Build telemetry publishes via extended `pipeline.build-progress` events, plus new `pipeline.build-blocked` event | Extends existing schema. Follows nats-core additive-only versioning. | Separate telemetry namespace, sidecar metrics, in-process only | Accepted |
| D7 | Collect telemetry from day one, defer resolver agents until empirical data reveals which failure category dominates | Avoids speculative engineering. Instrumentation is cheap and immediately useful for fine-tuning. | Build everything at once, no instrumentation | Accepted |
| D8 | Telemetry includes per-turn exchange summaries (not full transcripts) | Summaries capture essential signal within 64KB NATS payload limit. Full transcripts in local logs for deep debugging. | Full transcripts in events, only final error | Accepted |
| D11 | Failure categorisation uses structured heuristics first, LLM classification second | Heuristics are deterministic and fast. LLM handles ambiguous cases. Mirrors "never trust self-reported uncertainty" principle. | LLM-only, keyword matching only, human classification | Accepted |
| D13 | All telemetry and failure categorisation must be technology-stack agnostic | Platform builds Python, TypeScript, Go, C#, Rust. Heuristics use per-stack patterns with generic fallbacks. `detected_stack` propagated through all telemetry. | Python-only patterns, no stack tracking | Accepted |

**Warnings & Constraints:**
- Telemetry hooks must be lightweight — must not slow down the Player-Coach loop
- Use async publishing (fire-and-forget) for progress telemetry
- When `--nats` is NOT active: zero NATS overhead, no NATS imports, collector still runs for local summary
- nats-core is an optional dependency — GuardKit must import and run without it installed (lazy imports)
- Failure heuristics are a YAML config file — new patterns are config changes, not code changes
- Heuristics must cover Python, TypeScript, Go, C#, Rust with generic fallback
- Fine-tuning export must strip sensitive data (API keys, credentials, tokens)
- `detected_stack` must be resolved from codebase signals at build start and flow through all telemetry
- Telemetry storage starts simple (JSON files in `.guardkit/telemetry/`) — no external database dependency

## 3. Architecture

### 3.1 Where This Fits

```
┌─────────────────────────────────────────────────────────────────┐
│                           guardkit                               │
│                                                                  │
│  src/guardkit/                                                   │
│  ├── orchestrator/                                               │
│  │   └── feature_orchestrator.py  ← MODIFIED: telemetry hooks   │
│  ├── autobuild/                   ← UNCHANGED (hooks injected)  │
│  └── telemetry/                   ← NEW PACKAGE                 │
│      ├── collector.py             ← Accumulates per-turn data   │
│      ├── categoriser.py           ← Classifies failures         │
│      ├── publisher.py             ← Publishes to NATS           │
│      └── export.py                ← Fine-tuning JSONL output    │
│                                                                  │
│  config/                                                         │
│  └── failure_heuristics.yaml      ← Stack-aware pattern config  │
│                                                                  │
│  .guardkit/telemetry/             ← Local storage (JSON files)  │
│                                                                  │
│           ▼ publishes via NATS (when --nats active) ▼            │
│  ┌────────────────────────────────────────────────────────┐      │
│  │ pipeline.build-progress.{feature_id}  (enriched)      │      │
│  │ pipeline.build-blocked.{feature_id}   (new)           │      │
│  │ telemetry.task-complete.{feature_id}  (new)           │      │
│  │ telemetry.build-summary.{feature_id}  (new)           │      │
│  └────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Integration with Existing AutoBuild Flow

```
Current flow:
  Feature YAML → Player implements → Coach validates → iterate (≤5 turns) → complete/fail

Enhanced flow:
  Feature YAML
    → Detect stack from codebase signals
    → Start TelemetryCollector for task
    → Player implements
    → collector.record_turn(turn_data)  ← NEW HOOK
    → Coach validates
    → collector.record_turn(turn_data)  ← NEW HOOK
    → iterate (≤5 turns)
    → IF success:
        collector.complete_task(status="success")
        publisher.publish_task_telemetry()         ← NEW (opt-in via --nats)
    → IF turns exhausted:
        categoriser.categorise(turns, context, detected_stack)  ← NEW
        collector.complete_task(status="blocked")
        publisher.publish_build_blocked()          ← NEW (opt-in via --nats)
    → Store telemetry locally (.guardkit/telemetry/)  ← NEW (always)
```

### 3.3 Failure Categorisation Flow

```
Turn telemetry + Task context + detected_stack
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  1. Load failure_heuristics.yaml                     │
│  2. Select stack-specific patterns for detected_stack│
│     (fall back to "generic" if stack not in config)  │
│  3. Evaluate heuristics in order:                    │
│     a. error_type match (e.g., Python ImportError,   │
│        TS MODULE_NOT_FOUND, Go ImportPathError)      │
│     b. error_message regex (stack-specific patterns) │
│     c. turn_pattern analysis (stack_independent)     │
│     d. assumption_detected (stack_independent)       │
│  4. First match with confidence > 0.8 → return       │
│  5. No confident match → LLM classification (stub)   │
│  6. Still uncertain → default to "spec-ambiguity"    │
└───────────────┬─────────────────────────────────────┘
                │
                ▼
  FailureCategory(category, confidence, basis, heuristic_id, detected_stack)
```

### 3.4 Failure Heuristics Configuration

```yaml
# config/failure_heuristics.yaml
version: "1.0"

supported_stacks:
  - python
  - typescript
  - go
  - csharp
  - rust
  - generic

heuristics:
  # ─── Knowledge Gap ───

  - id: KG-001
    description: "Missing module/package import"
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
    description: "Missing module/package — error type"
    category: knowledge-gap
    confidence: 0.9
    pattern_type: error_type
    match_by_stack:
      python: ["ImportError", "ModuleNotFoundError"]
      typescript: ["MODULE_NOT_FOUND", "ERR_MODULE_NOT_FOUND"]
      go: ["ImportPathError"]
      csharp: ["CS0246", "CS0234"]
      rust: ["E0432", "E0433"]
      generic: ["ImportError", "ModuleNotFoundError", "MODULE_NOT_FOUND"]

  - id: KG-003
    description: "Wrong API usage — correct library, wrong method/attribute"
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
    description: "Same error repeated 3+ turns — model lacks knowledge to fix"
    category: knowledge-gap
    confidence: 0.85
    pattern_type: turn_pattern
    match: "same_error_repeated_3_turns"
    stack_independent: true

  # ─── Context Overflow ───

  - id: CO-001
    description: "Reference to undefined symbol — likely in file outside context"
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
    description: "Fix breaks something in an unseen file"
    category: context-overflow
    confidence: 0.8
    pattern_type: turn_pattern
    match: "fix_introduces_new_break_different_file"
    stack_independent: true

  - id: CO-003
    description: "Player reimplements existing code it can't see"
    category: context-overflow
    confidence: 0.75
    pattern_type: turn_pattern
    match: "player_recreates_existing_code"
    stack_independent: true

  # ─── Spec Ambiguity ───

  - id: SA-001
    description: "Player oscillates between approaches"
    category: spec-ambiguity
    confidence: 0.8
    pattern_type: turn_pattern
    match: "approach_oscillation"
    stack_independent: true

  - id: SA-002
    description: "Coach gives conflicting guidance across turns"
    category: spec-ambiguity
    confidence: 0.75
    pattern_type: turn_pattern
    match: "coach_contradicts_previous_feedback"
    stack_independent: true

  - id: SA-003
    description: "Player fills spec gap with ungrounded assumption"
    category: spec-ambiguity
    confidence: 0.7
    pattern_type: assumption_detected
    match: "player_makes_ungrounded_assumption"
    stack_independent: true
```

## 4. API Contracts

### 4.1 TelemetryCollector Interface

```python
class TelemetryCollector:
    """Accumulates per-turn data during Player-Coach execution. Pure — no I/O."""

    def start_task(self, task_id: str, feature_id: str, build_id: str,
                   complexity: str, domain_tags: list[str],
                   detected_stack: str = "generic") -> None: ...

    def record_turn(self, turn_number: int, duration_seconds: float,
                    player_action_summary: str, coach_feedback_summary: str,
                    files_touched: list[str],
                    error_type: Optional[str] = None,
                    error_signature: Optional[str] = None,
                    tokens_used: Optional[int] = None,
                    model_id: Optional[str] = None) -> None: ...

    def complete_task(self, status: str) -> TaskTelemetry:
        """Finalise and return telemetry. Computes clean_execution, recovery_turn, totals."""

    def get_task_telemetry(self) -> TaskTelemetry: ...

    def get_summary(self) -> dict:
        """Aggregated stats: mean turns, clean execution rate, failure category distribution."""
```

### 4.2 FailureCategoriser Interface

```python
class FailureCategoriser:
    def __init__(self, heuristics_path: str = "config/failure_heuristics.yaml"): ...

    def categorise(self, turn_telemetry: list[TurnTelemetry],
                   task_context: TaskContext,
                   detected_stack: str = "generic") -> FailureCategory: ...

class FailureCategory(BaseModel):
    category: Literal["knowledge-gap", "context-overflow", "spec-ambiguity"]
    confidence: float
    basis: str
    heuristic_id: Optional[str] = None
    detected_stack: str = "generic"
```

### 4.3 TelemetryPublisher Interface

```python
class TelemetryPublisher:
    """Publishes telemetry events to NATS. Only instantiated when --nats is active."""

    def __init__(self, nats_client: NATSClient): ...

    async def publish_task_telemetry(self, telemetry: TaskTelemetry) -> None:
        """Fire-and-forget: publishes to telemetry.task-complete.{feature_id}"""

    async def publish_build_blocked(self, blocked: BuildBlockedPayload) -> None:
        """Synchronous: publishes to pipeline.build-blocked.{feature_id}"""

    async def publish_build_summary(self, feature_id: str, tasks: list[TaskTelemetry]) -> None:
        """End-of-build: publishes to telemetry.build-summary.{feature_id}"""
```

### 4.4 FineTuningExporter Interface

```python
class FineTuningExporter:
    def __init__(self, telemetry_dir: str = ".guardkit/telemetry/"): ...

    def export_jsonl(self, output_path: str,
                     filter_model: Optional[str] = None,
                     filter_status: Optional[str] = None,
                     filter_stack: Optional[str] = None,
                     min_date: Optional[datetime] = None,
                     max_date: Optional[datetime] = None,
                     strip_sensitive: bool = True) -> ExportResult: ...

class ExportResult(BaseModel):
    records_exported: int
    output_path: str
    filters_applied: dict
    date_range: tuple[datetime, datetime]
    sensitive_items_stripped: int
```

## 5. Implementation Tasks

### Task 1: Turn Telemetry Collector
- **Task ID:** TASK-XXX
- **Complexity:** medium
- **Type:** implementation
- **Domain tags:** `telemetry, player-coach, autobuild, data-collection`
- **Files to create/modify:**
  - `src/guardkit/telemetry/__init__.py` (new)
  - `src/guardkit/telemetry/collector.py` (new)
  - `tests/test_telemetry_collector.py` (new)
- **Files NOT to touch:** `src/guardkit/orchestrator/feature_orchestrator.py` (integrated in Task 3), `src/guardkit/autobuild/`
- **Dependencies:** nats-core telemetry schemas (must be installed)
- **Inputs:** nats-core TurnTelemetry, TaskTelemetry models
- **Outputs:** TelemetryCollector class
- **Relevant decisions:** D1, D8, D13
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `src/guardkit/telemetry/collector.py`
  - [ ] Class `TelemetryCollector` with methods: `start_task()`, `record_turn()`, `complete_task()`, `get_task_telemetry()`, `get_summary()`
  - [ ] `start_task()` accepts `detected_stack` parameter
  - [ ] `record_turn()` accepts: turn_number, duration, player_summary, coach_summary, files_touched, optional error info
  - [ ] `complete_task()` computes: clean_execution (bool), recovery_turn (Optional[int]), total_duration, total_tokens
  - [ ] `get_task_telemetry()` returns a valid `TaskTelemetry` instance with `detected_stack` populated
  - [ ] `get_summary()` returns aggregated stats: mean turns, clean execution rate, failure category distribution
  - [ ] Thread-safe: multiple calls to `record_turn()` don't corrupt state
  - [ ] Tests pass: `pytest tests/test_telemetry_collector.py -v`
  - [ ] Lint passes: `ruff check src/guardkit/telemetry/`
- **Implementation notes:** The collector is a stateful object that lives for the duration of a task's Player-Coach loop. It accumulates turn data in memory and produces a TaskTelemetry on completion. It does NOT publish events — that's the publisher's job (Task 3). Keep the collector pure (no I/O, no NATS dependency) so it works in standalone mode. The `detected_stack` received at `start_task()` is stored and included in the final TaskTelemetry.
- **Player constraints:** Do not import nats-py or FastStream. The collector depends only on nats-core schemas (Pydantic models) and standard library.
- **Coach validation commands:**
  ```bash
  pytest tests/test_telemetry_collector.py -v
  ruff check src/guardkit/telemetry/
  python -c "from guardkit.telemetry.collector import TelemetryCollector; print('Import OK')"
  ```

### Task 2: Failure Categoriser
- **Task ID:** TASK-XXX
- **Complexity:** high
- **Type:** implementation
- **Domain tags:** `telemetry, failure-analysis, heuristics, classification, stack-detection`
- **Files to create/modify:**
  - `src/guardkit/telemetry/categoriser.py` (new)
  - `config/failure_heuristics.yaml` (new)
  - `tests/test_failure_categoriser.py` (new)
- **Files NOT to touch:** Any existing guardkit source files
- **Dependencies:** Task 1 (uses TelemetryCollector output)
- **Inputs:** TurnTelemetry list, TaskContext, detected_stack, failure_heuristics.yaml
- **Outputs:** FailureCategoriser class, FailureCategory result, stack-aware configurable heuristics
- **Relevant decisions:** D2, D11, D13
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `src/guardkit/telemetry/categoriser.py`
  - [ ] File exists: `config/failure_heuristics.yaml`
  - [ ] Class `FailureCategoriser` with method: `categorise(turn_telemetry, task_context, detected_stack="generic") -> FailureCategory`
  - [ ] `FailureCategory` has fields: category (literal), confidence (float), basis (str), heuristic_id (Optional[str]), detected_stack (str)
  - [ ] Heuristic-only mode works without LLM
  - [ ] Heuristics YAML contains `match_by_stack` entries for: python, typescript, go, csharp, rust, generic
  - [ ] Heuristics YAML contains `stack_independent: true` entries for turn-pattern heuristics
  - [ ] Categoriser selects stack-specific patterns when detected_stack matches, falls back to generic
  - [ ] Loading invalid heuristics YAML raises clear error with line number
  - [ ] Test: Python ImportError with detected_stack="python" → "knowledge-gap" with confidence >= 0.8
  - [ ] Test: TypeScript "Cannot find module" with detected_stack="typescript" → "knowledge-gap" with confidence >= 0.8
  - [ ] Test: Go "cannot find package" with detected_stack="go" → "knowledge-gap" with confidence >= 0.8
  - [ ] Test: C# "CS0246" error code with detected_stack="csharp" → "knowledge-gap" with confidence >= 0.8
  - [ ] Test: Unknown error with detected_stack="generic" → uses generic fallback patterns
  - [ ] Test: Oscillating approaches across turns → "spec-ambiguity" (stack_independent)
  - [ ] Test: Reference to undefined symbol with detected_stack="typescript" → "context-overflow"
  - [ ] Tests pass: `pytest tests/test_failure_categoriser.py -v`
  - [ ] Lint passes: `ruff check src/guardkit/telemetry/categoriser.py`
- **Implementation notes:** Implement heuristic classification FIRST — fully tested before any LLM code. LLM classification is a stub (raise NotImplementedError). Use Section 3.4 heuristics exactly. The `match_by_stack` field is a dict keyed by stack name — categoriser looks up `detected_stack`, falls back to `generic`. Heuristics with `stack_independent: true` are evaluated regardless of stack. Turn-pattern heuristics require sequence analysis (e.g., "same_error_repeated_3_turns" = same error_type in 3+ consecutive turns). Default to "spec-ambiguity" when uncertain. The `heuristic_id` (e.g., "KG-001") enables traceability.
- **Player constraints:** LLM classification = stub only. Do not import LLM libraries. Must test with at least 4 different stacks.
- **Coach validation commands:**
  ```bash
  pytest tests/test_failure_categoriser.py -v
  ruff check src/guardkit/telemetry/
  python -c "from guardkit.telemetry.categoriser import FailureCategoriser, FailureCategory; print('Import OK')"
  python -c "
  import yaml
  with open('config/failure_heuristics.yaml') as f:
      data = yaml.safe_load(f)
      assert 'supported_stacks' in data
      assert len(data['supported_stacks']) >= 6
      for h in data['heuristics']:
          assert 'match_by_stack' in h or h.get('stack_independent', False), f'{h[\"id\"]} missing stack config'
      print(f'Loaded {len(data[\"heuristics\"])} stack-aware heuristics OK')
  "
  ```

### Task 3: Telemetry Publisher and AutoBuild Integration
- **Task ID:** TASK-XXX
- **Complexity:** high
- **Type:** integration
- **Domain tags:** `telemetry, autobuild, player-coach, nats, integration`
- **Files to create/modify:**
  - `src/guardkit/telemetry/publisher.py` (new)
  - `src/guardkit/orchestrator/feature_orchestrator.py` (modified — add telemetry hooks)
  - `tests/test_telemetry_publisher.py` (new)
  - `tests/test_telemetry_integration.py` (new)
- **Dependencies:** Tasks 1, 2
- **Inputs:** All telemetry components, existing feature_orchestrator
- **Outputs:** TelemetryPublisher (NATS event publishing), integration hooks in feature_orchestrator
- **Relevant decisions:** D1, D5, D7, D13
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `src/guardkit/telemetry/publisher.py`
  - [ ] Class `TelemetryPublisher` with methods: `publish_task_telemetry()`, `publish_build_blocked()`, `publish_build_summary()`
  - [ ] Publisher is opt-in: instantiated only when `--nats` flag is active
  - [ ] When `--nats` is NOT active: zero telemetry overhead, no NATS imports
  - [ ] feature_orchestrator detects stack from codebase signals at build start
  - [ ] feature_orchestrator calls `collector.start_task()` with `detected_stack`
  - [ ] feature_orchestrator calls `collector.record_turn()` after each Player-Coach turn
  - [ ] feature_orchestrator calls `collector.complete_task()` and optionally `publisher.publish_task_telemetry()` after each task
  - [ ] When task fails at turn limit: calls `categoriser.categorise()` with `detected_stack`, then `publisher.publish_build_blocked()`
  - [ ] `detected_stack` is resolved from codebase signals at build start and propagated through all telemetry
  - [ ] Telemetry stored locally in `.guardkit/telemetry/` as JSON files (always, regardless of --nats)
  - [ ] Integration test: mock NATS, run AutoBuild on a simple task, verify telemetry events published
  - [ ] Standalone test: run AutoBuild without --nats, verify local telemetry stored, no NATS errors
  - [ ] Tests pass: `pytest tests/test_telemetry_publisher.py tests/test_telemetry_integration.py -v`
  - [ ] Lint passes: `ruff check src/guardkit/telemetry/ src/guardkit/orchestrator/`
- **Implementation notes:** This is the critical integration task. Telemetry hooks must be lightweight — async fire-and-forget for progress, synchronous only for build-blocked (Build Agent needs to wait for resolver). When `--nats` is not active, the collector still runs (data is useful locally) but the publisher is not instantiated. Stack detection reuses the same codebase signal logic from `/feature-spec` StackDetector if available, otherwise a lightweight version checking for pyproject.toml, package.json, go.mod, .csproj, Cargo.toml. Minimal changes to feature_orchestrator — inject via dependency injection, call hooks at the right points.
- **Player constraints:** Minimal changes to feature_orchestrator — add hook calls, do not restructure existing orchestration logic. All new logic in the telemetry package. nats-py/FastStream must be lazy-imported.
- **Coach validation commands:**
  ```bash
  pytest tests/test_telemetry_publisher.py tests/test_telemetry_integration.py -v
  ruff check src/guardkit/telemetry/ src/guardkit/orchestrator/
  python -c "
  from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
  print('Standalone import OK — no NATS required')
  "
  ```

### Task 4: Fine-Tuning Data Exporter
- **Task ID:** TASK-XXX
- **Complexity:** medium
- **Type:** implementation
- **Domain tags:** `telemetry, fine-tuning, data-export, jsonl`
- **Files to create/modify:**
  - `src/guardkit/telemetry/export.py` (new)
  - `tests/test_fine_tuning_export.py` (new)
- **Files NOT to touch:** Any files modified in Task 3
- **Dependencies:** Task 1 (uses TaskTelemetry model)
- **Inputs:** Collected TaskTelemetry data from `.guardkit/telemetry/`
- **Outputs:** FineTuningExporter class producing JSONL files
- **Relevant decisions:** D1, D7, D13
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `src/guardkit/telemetry/export.py`
  - [ ] Class `FineTuningExporter` with method: `export_jsonl(output_path, **filters) -> ExportResult`
  - [ ] Output is valid JSONL (one JSON object per line)
  - [ ] Each record contains: task_id, feature_id, model_id, detected_stack, task_spec, turns, final_status, optional resolution
  - [ ] `strip_sensitive=True` removes patterns matching: API keys, tokens, passwords, credentials
  - [ ] Filter by model_id, status, stack, date range works correctly
  - [ ] `--dry-run` option reports what would be exported without writing
  - [ ] ExportResult includes record count and filters applied
  - [ ] Tests pass: `pytest tests/test_fine_tuning_export.py -v`
  - [ ] Lint passes: `ruff check src/guardkit/telemetry/export.py`
- **Implementation notes:** Reads from `.guardkit/telemetry/` JSON files (one per build). Sensitive data stripping uses a configurable regex list. Include `detected_stack` in every record — this enables filtering training data by language when fine-tuning for specific project types.
- **Player constraints:** No database dependencies beyond standard library. No ML/training library imports.
- **Coach validation commands:**
  ```bash
  pytest tests/test_fine_tuning_export.py -v
  ruff check src/guardkit/telemetry/
  python -c "from guardkit.telemetry.export import FineTuningExporter, ExportResult; print('Import OK')"
  ```

## 6. Test Strategy

### Unit Tests
| Test File | Covers | Key Assertions |
|-----------|--------|---------------|
| `tests/test_telemetry_collector.py` | TelemetryCollector state management | Turn recording, task completion with detected_stack, summary stats, thread safety |
| `tests/test_failure_categoriser.py` | Stack-aware heuristic classification | Per-stack pattern matching (Python, TS, Go, C#), generic fallback, stack_independent patterns, confidence thresholds, heuristic_id traceability |
| `tests/test_telemetry_publisher.py` | NATS event publishing | Correct topic routing, payload validation, opt-in behaviour |
| `tests/test_fine_tuning_export.py` | JSONL export | Valid JSONL, detected_stack field, sensitive stripping, filter by stack/model/status |

### Integration Tests
| Test File | Covers | Prerequisites |
|-----------|--------|--------------|
| `tests/test_telemetry_integration.py` | End-to-end: AutoBuild → telemetry → NATS events | Mock NATS, sample feature YAML |

### Manual Verification
- [ ] Run AutoBuild on fastapi-python test, verify telemetry JSON written to `.guardkit/telemetry/`
- [ ] Run AutoBuild with `--nats`, verify events appear in NATS monitoring
- [ ] Run `guardkit telemetry export --output training.jsonl`, verify valid JSONL output
- [ ] Verify standalone mode: AutoBuild works without NATS installed

## 7. Dependencies & Setup

### Python Dependencies
```
# requirements.txt additions
pyyaml>=6.0      # For failure_heuristics.yaml (may already be present)

# Optional (only needed when --nats is active):
# nats-core @ git+ssh://git@github.com/appmilla/nats-core.git
```

## 8. File Tree (Target State)

```
guardkit/
├── src/guardkit/
│   ├── telemetry/
│   │   ├── __init__.py             # NEW (Task 1)
│   │   ├── collector.py            # NEW (Task 1)
│   │   ├── categoriser.py          # NEW (Task 2)
│   │   ├── publisher.py            # NEW (Task 3)
│   │   └── export.py               # NEW (Task 4)
│   └── orchestrator/
│       └── feature_orchestrator.py  # MODIFIED (Task 3) — minimal hook additions
├── config/
│   └── failure_heuristics.yaml      # NEW (Task 2)
└── tests/
    ├── test_telemetry_collector.py   # NEW (Task 1)
    ├── test_failure_categoriser.py   # NEW (Task 2)
    ├── test_telemetry_publisher.py   # NEW (Task 3)
    ├── test_telemetry_integration.py # NEW (Task 3)
    └── test_fine_tuning_export.py    # NEW (Task 4)
```

## 9. Out of Scope

- Resolver agents — those live in dev-pipeline
- NATS infrastructure — that's dev-pipeline
- Dashboard UI for viewing telemetry — future feature
- LLM-based failure classification — heuristics only in v1 (LLM stub for future)
- Modifying AutoBuild's core Player-Coach logic — only adding hooks
- Real-time telemetry streaming dashboard — local JSON storage sufficient for now

## 10. Sequencing

This repo implements **Phase A** of the parent spec and is the highest-value deliverable — it provides empirical data for all subsequent decisions. Must be implemented after nats-core schemas are merged but can proceed in parallel with dev-pipeline resolver work.

**Dependencies:**
- Requires: nats-core three-layer-defence schemas (Tasks 1-2 of nats-core spec)
- Enables: dev-pipeline resolver agents (which consume build-blocked events)
- Enables: Fine-tuning vLLM models on Dell ProMax (via exported JSONL)

**Estimated effort:** 1-2 weeks  
**Phase:** A (Instrumentation — build first)
