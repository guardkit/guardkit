# Feature Specification: Enhanced `/feature-plan` for Two-Phase AI Workflows

**Date:** February 10, 2026  
**Author:** Rich  
**Status:** Ready for Implementation  
**Research Method:** Claude Desktop (extended thinking) → GuardKit `/feature-plan`  
**Target Repo:** GuardKit  
**Target Branch:** `feature/two-phase-feature-plan`  
**Feature ID:** FEAT-FP-002 *(assigned by `/feature-plan`)*

---

## 1. Problem Statement

GuardKit's `/feature-plan` currently produces task specifications optimised for interactive human-AI collaboration via `/task-work`, where a frontier model like Claude reasons about ambiguity in real time. When the implementation target is a local model (Qwen3-Coder-30B, Nemotron-3-Nano-30B) executing autonomously via `/feature-build`, the current output lacks the explicitness, structured metadata, and machine-parseable constraints needed for reliable unattended execution. The gap between "what the plan says" and "what the Player needs to know" is bridged by human intelligence in the interactive workflow — but there is no human in the autonomous loop.

This enhancement makes `/feature-plan` aware of its implementation target, producing richer output when the executor is a local model operating within the Player-Coach adversarial loop with Graphiti-backed context retrieval.

## 2. Decision Log

| # | Decision | Rationale | Alternatives Rejected | ADR Status |
|---|----------|-----------|----------------------|------------|
| D1 | Add `--target` flag with values `interactive`, `local-model`, `auto` (default) | Clean separation of output modes without breaking existing behaviour. `auto` detects from `.guardkit/config.yaml` whether a local model endpoint is configured | Single verbosity slider (too coarse), separate command like `/feature-plan-local` (fragments the command surface) | Accepted |
| D2 | Research template as recognised input schema via `--from-spec` flag | `/feature-plan` can parse the Research-to-Implementation Template sections directly, extracting decisions, tasks, file constraints, and domain tags rather than requiring the user to re-describe everything | Free-form text only (loses structure), JSON schema (unfamiliar authoring experience) | Accepted |
| D3 | Generate ADR files automatically from Decision Log section | Each decision D1..Dn in the spec becomes a file in `docs/adr/ADR-FP-NNN-{slug}.md` formatted for `guardkit graphiti add-context` | Inline ADRs only in spec (not individually seedable), manual ADR creation (defeats automation) | Accepted |
| D4 | Per-feature quality gate YAML generation | `/feature-plan` creates `.guardkit/quality-gates/FEAT-XXX.yaml` with test commands derived from task acceptance criteria, enabling the Coach to run deterministic validation | Global quality gates only (too coarse per feature), no quality gate output (requires manual creation every time) | Accepted |
| D5 | Task metadata must include domain tags, file constraints, turn budget hints, and Coach validation blocks | This metadata directly feeds Graphiti's `JobContextRetriever` (domain tags → semantic search keys), Player constraints (file paths), and Coach validation (structured command blocks) | Prose-only task descriptions (Player must infer structure), separate metadata files per task (too many files) | Accepted |
| D6 | Adopt the Research Template's 11-section structure as the canonical `/feature-plan --from-spec` input format | The template already captures everything needed: problem statement, decisions, architecture, API contracts, tasks with metadata, test strategy, dependencies, file tree, exclusions, resolved questions, and Graphiti seeding. Standardising on this avoids format proliferation | Ad-hoc markdown (unpredictable parsing), custom DSL (learning curve), YAML input (verbose for humans) | Accepted |
| D7 | Generate Graphiti seeding script alongside plan output | `/feature-plan` produces `scripts/seed-FEAT-XXX.sh` with the exact `guardkit graphiti add-context` commands for all ADRs, the spec file, and warnings — ready to execute before Phase 2 | Manual seeding (error-prone, steps get missed), auto-seed on plan creation (may not be desired if spec is draft) | Accepted |
| D8 | Documentation updates as required deliverables in every task | Each implementation task that changes behaviour or adds features must include corresponding documentation updates to guardkit.ai site content and inline command help | Documentation as separate follow-up feature (historically gets deprioritised and forgotten) | Accepted |
| D9 | Backward compatibility via additive-only changes | Existing `/feature-plan "description"` behaviour unchanged. All enhancements are behind new flags (`--target`, `--from-spec`, `--generate-adrs`, `--generate-quality-gates`) or are additive metadata fields in task output | Breaking change to existing output format (disrupts current users) | Accepted |
| D10 | Task turn budget hints based on complexity scoring | Tasks include `turn_budget: {expected: N, max: M}` where expected is the typical turns for this complexity level and max is the hard limit before escalation. Simple (1-2 expected, 3 max), medium (2-3 expected, 5 max), complex (3-4 expected, 5 max) | Fixed turn budget for all tasks (wastes cycles on simple tasks, insufficient for complex ones), no hints (Player can't self-calibrate) | Accepted |

**Warnings & Constraints** *(seeded as Graphiti warning nodes):*
- The `--from-spec` parser must handle incomplete templates gracefully — not every section will be filled for every feature. Missing sections should produce warnings, not errors.
- Quality gate YAML must use `required: true/false` to distinguish mandatory gates from optional ones. The Coach must not fail a task because an optional gate didn't pass.
- ADR file generation must check for existing ADRs with the same decision title to avoid duplicates. Use `ADR-FP-NNN` prefix to namespace feature-plan-generated ADRs.
- Domain tags must use lowercase hyphenated format (e.g., `agent-lifecycle`, `nats-messaging`) for consistent Graphiti semantic search.
- The `--target local-model` output should assume the Player has NO implicit knowledge — every import path, every class name, every test command must be explicitly stated.
- Turn budget hints are advisory, not enforced by `/feature-plan`. Enforcement remains in the AutoBuild orchestrator's `should_continue_loop()` function.
- File path constraints use glob patterns (e.g., `src/agents/**/*.py`) for flexibility. The Player-Coach framework must interpret these correctly.

## 3. Architecture

### 3.1 System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                     Two-Phase Workflow                          │
│                                                                 │
│  Phase 1 (MacBook + Frontier Model)                            │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  Research Template    →  /feature-plan --from-spec   │      │
│  │  (11 sections)           --target local-model        │      │
│  │                          --generate-adrs             │      │
│  │                          --generate-quality-gates     │      │
│  └───────────────┬──────────────────────────────────────┘      │
│                  │ produces                                     │
│                  ▼                                              │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  FEAT-XXX/                                           │      │
│  │  ├── FEATURE.md          (feature spec + tasks)      │      │
│  │  ├── implementation-guide.md                         │      │
│  │  ├── tasks/TASK-001.md ... TASK-NNN.md               │      │
│  │  ├── .guardkit/quality-gates/FEAT-XXX.yaml           │      │
│  │  ├── docs/adr/ADR-FP-001-*.md ... ADR-FP-NNN-*.md   │      │
│  │  ├── docs/warnings/FEAT-XXX-warnings.md              │      │
│  │  └── scripts/seed-FEAT-XXX.sh                        │      │
│  └───────────────┬──────────────────────────────────────┘      │
│                  │ commit + push                                │
│                  ▼                                              │
│  Phase 2 (Dell ProMax + Local vLLM)                            │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  scripts/seed-FEAT-XXX.sh  →  Graphiti seeding       │      │
│  │  /feature-build FEAT-XXX   →  AutoBuild Player-Coach │      │
│  │                                                      │      │
│  │  Player reads:  task metadata + Graphiti context      │      │
│  │  Coach reads:   acceptance criteria + quality gates   │      │
│  │  Output:        .guardkit/worktrees/FEAT-XXX/         │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Design

| Component | File Path | Purpose | New/Modified |
|-----------|-----------|---------|-------------|
| FeaturePlanCommand | `.claude/commands/feature-plan.md` | Command prompt with new flags and output sections | Modified |
| SpecParser | `guardkit/planning/spec_parser.py` | Parses Research Template markdown into structured data | New |
| ADRGenerator | `guardkit/planning/adr_generator.py` | Creates ADR files from Decision Log entries | New |
| QualityGateGenerator | `guardkit/planning/quality_gate_generator.py` | Creates per-feature quality gate YAML from acceptance criteria | New |
| TaskMetadataEnricher | `guardkit/planning/task_metadata.py` | Adds domain tags, file constraints, turn budgets, Coach blocks to tasks | New |
| SeedScriptGenerator | `guardkit/planning/seed_script_generator.py` | Creates `scripts/seed-FEAT-XXX.sh` with Graphiti seeding commands | New |
| WarningsExtractor | `guardkit/planning/warnings_extractor.py` | Extracts warnings/constraints into separate seedable document | New |
| TargetModeConfig | `guardkit/planning/target_mode.py` | Handles `--target` flag logic and output verbosity adjustment | New |
| Two-Phase Workflow Guide | `docs/guides/two-phase-workflow.md` | Documentation for the two-phase planning and execution model | New |
| Feature-Plan Reference | `docs/reference/feature-plan.md` | Updated command reference with new flags and output format | Modified |
| Research Template Guide | `docs/guides/research-template.md` | Guide for using the Research-to-Implementation Template with GuardKit | New |
| Graphiti Seeding Guide | `docs/guides/graphiti-seeding.md` | Updated guide covering ADR seeding and feature context patterns | Modified |

### 3.3 Data Flow

```
1. User completes Phase 1 research in Claude Desktop →
2. Fills Research-to-Implementation Template (11 sections) →
3. Saves as docs/features/FEAT-XXX-spec.md →
4. Runs: /feature-plan --from-spec docs/features/FEAT-XXX-spec.md --target local-model --generate-adrs --generate-quality-gates →
5. SpecParser extracts structured data from template sections →
6. TargetModeConfig adjusts output verbosity for local model →
7. TaskMetadataEnricher adds domain tags, file constraints, turn budgets, Coach validation blocks →
8. ADRGenerator creates docs/adr/ADR-FP-NNN-*.md files from Decision Log →
9. WarningsExtractor creates docs/warnings/FEAT-XXX-warnings.md →
10. QualityGateGenerator creates .guardkit/quality-gates/FEAT-XXX.yaml →
11. SeedScriptGenerator creates scripts/seed-FEAT-XXX.sh →
12. Standard feature-plan output: FEATURE.md + task files + implementation guide →
13. User reviews, commits, pushes to repo →
14. On Dell ProMax: bash scripts/seed-FEAT-XXX.sh (seeds Graphiti) →
15. guardkit feature-build FEAT-XXX (AutoBuild executes with enriched context)
```

### 3.4 Task Output Schema (Local Model Target)

When `--target local-model` is active, each task markdown file includes these structured blocks that AutoBuild's `JobContextRetriever` and Coach can parse:

```yaml
# Task frontmatter (YAML block at top of task file)
---
task_id: TASK-001
feature_id: FEAT-XXX
title: "Create base agent message bus integration"
complexity: medium  # low | medium | high
complexity_score: 5  # 1-10 numeric
type: implementation  # implementation | refactor | integration | configuration | documentation
domain_tags:
  - nats-messaging
  - agent-lifecycle
  - base-agent
files_to_create:
  - src/agents/base_agent.py
  - src/agents/__init__.py
files_to_modify:
  - requirements.txt
files_not_to_touch:
  - src/dashboard/**
  - src/config/nats.yaml  # created in separate task
dependencies: []  # or [TASK-001, TASK-002]
relevant_decisions:
  - D1  # Use NATS JetStream
  - D2  # Pydantic validation
turn_budget:
  expected: 2
  max: 5
graphiti_context_budget: 4000  # tokens, based on complexity
---
```

```markdown
## Acceptance Criteria (Machine-Verifiable)

- [ ] File exists: `src/agents/base_agent.py`
- [ ] File exists: `src/agents/__init__.py`
- [ ] Class `BaseAgent` has methods: `publish_status`, `request_approval`, `run`
- [ ] `BaseAgent.__init__` accepts `agent_id: str` and `nats_url: str` parameters
- [ ] Tests pass: `pytest tests/test_base_agent.py -v`
- [ ] Lint passes: `ruff check src/agents/`
- [ ] Import succeeds: `python -c "from src.agents.base_agent import BaseAgent; print('OK')"`

## Coach Validation Commands

```bash
# Run in order — all must pass for Coach approval
pytest tests/test_base_agent.py -v
ruff check src/agents/
python -c "from src.agents.base_agent import BaseAgent; print('Import OK')"
```

## Player Constraints

- Create files ONLY in `src/agents/` and update `requirements.txt`
- Do NOT modify any files outside these paths
- Do NOT create configuration files (handled by TASK-003)
- Use Pydantic v2 for all message models (Decision D2)
- Follow existing project patterns for async/await (see Graphiti context)

## Implementation Notes (Prescriptive)

The Player should implement `BaseAgent` as an abstract base class with:
1. An async `connect()` method that establishes NATS connection using `nats-py`
2. A `publish_status()` method that publishes `AgentStatus` Pydantic model to `agent.{agent_id}.status`
3. A `request_approval()` method that publishes `ApprovalRequest` to `agent.{agent_id}.approval` and awaits response on `agent.{agent_id}.approval.response`
4. An abstract `run()` method that subclasses implement

Import `nats` from `nats-py` package, not the deprecated `asyncio-nats-client`.
```

## 4. API Contracts

### 4.1 SpecParser Interface

```python
@dataclass
class ParsedSpec:
    """Structured data extracted from Research-to-Implementation Template."""
    problem_statement: str
    decisions: list[Decision]
    warnings: list[str]
    components: list[Component]
    data_flow: str
    message_schemas: dict[str, Any]
    api_contracts: list[APIContract]
    tasks: list[TaskDefinition]
    test_strategy: TestStrategy
    dependencies: DependencySet
    file_tree: str
    out_of_scope: list[str]
    resolved_questions: list[ResolvedQuestion]
    
@dataclass
class Decision:
    number: str  # "D1", "D2", etc.
    title: str
    rationale: str
    alternatives_rejected: str
    adr_status: str  # "Accepted", "Proposed", "Superseded"

@dataclass
class TaskDefinition:
    """Task as defined in the Research Template Section 5."""
    name: str
    complexity: str  # "low", "medium", "high"
    task_type: str
    domain_tags: list[str]
    files_to_create: list[str]
    files_to_modify: list[str]
    files_not_to_touch: list[str]
    dependencies: list[str]  # task references
    inputs: str
    outputs: str
    relevant_decisions: list[str]  # "D1", "D2" references
    acceptance_criteria: list[str]
    implementation_notes: str
    player_constraints: list[str]
    coach_validation_commands: list[str]

def parse_research_template(filepath: Path) -> ParsedSpec:
    """
    Parse a Research-to-Implementation Template markdown file.
    
    Handles incomplete templates gracefully — missing sections
    produce warnings in the returned ParsedSpec, not exceptions.
    
    Returns ParsedSpec with all extractable structured data.
    """
```

### 4.2 Target Mode Interface

```python
class TargetMode(Enum):
    INTERACTIVE = "interactive"     # Current behaviour — human + frontier model
    LOCAL_MODEL = "local-model"     # Explicit, verbose, machine-parseable
    AUTO = "auto"                   # Detect from .guardkit/config.yaml

@dataclass
class TargetConfig:
    mode: TargetMode
    model_name: str | None  # e.g., "Qwen3-Coder-30B-A3B"
    output_verbosity: str   # "standard" or "explicit"
    include_imports: bool   # Include exact import statements in notes
    include_type_hints: bool  # Include full type signatures
    structured_coach_blocks: bool  # Emit Coach blocks as structured YAML

def resolve_target(
    flag_value: str | None,
    config_path: Path = Path(".guardkit/config.yaml")
) -> TargetConfig:
    """Resolve target mode from flag or config file."""
```

### 4.3 ADR Generator Interface

```python
def generate_adrs(
    decisions: list[Decision],
    feature_id: str,
    output_dir: Path = Path("docs/adr"),
    check_duplicates: bool = True,
) -> list[Path]:
    """
    Generate ADR markdown files from Decision Log entries.
    
    Returns list of created file paths.
    Skips generation if an ADR with matching title already exists
    (when check_duplicates=True).
    
    File naming: ADR-FP-{feature_number}-{slug}.md
    e.g., ADR-FP-002-nats-jetstream-messaging.md
    """
```

### 4.4 Quality Gate Generator Interface

```python
def generate_quality_gates(
    feature_id: str,
    tasks: list[TaskDefinition],
    output_path: Path | None = None,
) -> Path:
    """
    Generate quality gate YAML from task acceptance criteria.
    
    Scans all tasks for test/lint/check commands in acceptance criteria
    and Coach validation blocks. Deduplicates and organises into
    quality gate categories.
    
    Default output: .guardkit/quality-gates/{feature_id}.yaml
    """
```

### 4.5 Seed Script Generator Interface

```python
def generate_seed_script(
    feature_id: str,
    adr_paths: list[Path],
    spec_path: Path,
    warnings_path: Path | None,
    output_dir: Path = Path("scripts"),
) -> Path:
    """
    Generate bash script for Graphiti seeding.
    
    Creates scripts/seed-{feature_id}.sh with:
    1. Graphiti status check
    2. ADR seeding commands
    3. Spec file seeding
    4. Warnings seeding (if present)
    5. Verification step
    
    Script is idempotent — safe to run multiple times.
    """
```

## 5. Implementation Tasks

### Task 1: Research Template Spec Parser

- **Task ID:** TASK-001
- **Complexity:** medium
- **Complexity Score:** 5
- **Type:** implementation
- **Domain tags:** `spec-parser, markdown-parsing, data-extraction`
- **Files to create:**
  - `guardkit/planning/spec_parser.py`
  - `tests/unit/test_spec_parser.py`
- **Files to modify:** None
- **Files NOT to touch:** `.claude/commands/feature-plan.md`, `guardkit/cli/`
- **Dependencies:** None (first task)
- **Inputs:** Research-to-Implementation Template markdown format (Section 6 of this spec)
- **Outputs:** `ParsedSpec` dataclass with structured data from all 11 template sections
- **Relevant decisions:** D2, D6
- **Turn budget:** expected: 2, max: 5
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `guardkit/planning/spec_parser.py`
  - [ ] File exists: `tests/unit/test_spec_parser.py`
  - [ ] Function `parse_research_template(Path) -> ParsedSpec` exists
  - [ ] Parses Decision Log table into `list[Decision]` with fields: number, title, rationale, alternatives_rejected, adr_status
  - [ ] Parses Implementation Tasks section into `list[TaskDefinition]` with all metadata fields
  - [ ] Handles missing sections gracefully (returns warnings, not exceptions)
  - [ ] Tests pass: `pytest tests/unit/test_spec_parser.py -v`
  - [ ] Lint passes: `ruff check guardkit/planning/spec_parser.py`
- **Player constraints:**
  - Create files ONLY in `guardkit/planning/` and `tests/unit/`
  - Do NOT modify any existing files
  - Use standard library `re` and `dataclasses` — no external markdown parsing libraries
  - Parse markdown tables using regex, not a full AST parser
- **Coach validation commands:**
  ```bash
  pytest tests/unit/test_spec_parser.py -v
  ruff check guardkit/planning/spec_parser.py
  python -c "from guardkit.planning.spec_parser import parse_research_template; print('Import OK')"
  ```
- **Implementation notes:** Use regex-based section extraction keyed on `## N. Section Title` headers. The Decision Log is a markdown table starting with `| # | Decision |`. Each task block starts with `### Task N:`. Warnings are a bullet list under `**Warnings & Constraints**`. The parser should be lenient — sections may use slightly different heading levels or have extra whitespace.

---

### Task 2: Target Mode Configuration

- **Task ID:** TASK-002
- **Complexity:** low
- **Complexity Score:** 3
- **Type:** implementation
- **Domain tags:** `target-mode, configuration, output-formatting`
- **Files to create:**
  - `guardkit/planning/target_mode.py`
  - `tests/unit/test_target_mode.py`
- **Files to modify:** None
- **Files NOT to touch:** `.claude/commands/feature-plan.md`, `guardkit/cli/`
- **Dependencies:** None (can run in parallel with TASK-001)
- **Inputs:** `--target` flag value, `.guardkit/config.yaml`
- **Outputs:** `TargetConfig` dataclass driving output verbosity
- **Relevant decisions:** D1, D9
- **Turn budget:** expected: 1, max: 3
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `guardkit/planning/target_mode.py`
  - [ ] `TargetMode` enum has values: `INTERACTIVE`, `LOCAL_MODEL`, `AUTO`
  - [ ] `resolve_target("local-model")` returns config with `output_verbosity="explicit"`
  - [ ] `resolve_target("interactive")` returns config with `output_verbosity="standard"`
  - [ ] `resolve_target("auto")` reads `.guardkit/config.yaml` for `autobuild.endpoint` presence
  - [ ] `resolve_target(None)` defaults to `AUTO`
  - [ ] Tests pass: `pytest tests/unit/test_target_mode.py -v`
  - [ ] Lint passes: `ruff check guardkit/planning/target_mode.py`
- **Player constraints:**
  - Create files ONLY in `guardkit/planning/` and `tests/unit/`
  - Do NOT read or modify `.guardkit/config.yaml` in tests — use mock/fixture
- **Coach validation commands:**
  ```bash
  pytest tests/unit/test_target_mode.py -v
  ruff check guardkit/planning/target_mode.py
  python -c "from guardkit.planning.target_mode import TargetMode, resolve_target; print('OK')"
  ```

---

### Task 3: ADR File Generator

- **Task ID:** TASK-003
- **Complexity:** medium
- **Complexity Score:** 4
- **Type:** implementation
- **Domain tags:** `adr-generation, documentation, graphiti-seeding`
- **Files to create:**
  - `guardkit/planning/adr_generator.py`
  - `tests/unit/test_adr_generator.py`
- **Files to modify:** None
- **Files NOT to touch:** `docs/adr/` (test creates temp dirs)
- **Dependencies:** TASK-001 (uses `Decision` dataclass)
- **Inputs:** `list[Decision]` from SpecParser, feature ID
- **Outputs:** ADR markdown files in `docs/adr/` following canonical ADR format
- **Relevant decisions:** D3
- **Turn budget:** expected: 2, max: 4
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `guardkit/planning/adr_generator.py`
  - [ ] Function `generate_adrs(decisions, feature_id, output_dir)` returns `list[Path]`
  - [ ] Generated ADR files follow format: `ADR-FP-{feature_number}-{slug}.md`
  - [ ] ADR content includes: Status, Date, Context, Decision, Rationale, Alternatives Rejected, Consequences
  - [ ] Duplicate detection: skips if ADR with same title exists in output_dir
  - [ ] Tests pass: `pytest tests/unit/test_adr_generator.py -v`
  - [ ] Lint passes: `ruff check guardkit/planning/adr_generator.py`
- **Player constraints:**
  - Create files ONLY in `guardkit/planning/` and `tests/unit/`
  - Tests must use `tmp_path` fixture for output, never write to actual `docs/adr/`
  - ADR format must match the canonical format from Research Template Section 11
- **Coach validation commands:**
  ```bash
  pytest tests/unit/test_adr_generator.py -v
  ruff check guardkit/planning/adr_generator.py
  python -c "from guardkit.planning.adr_generator import generate_adrs; print('Import OK')"
  ```

---

### Task 4: Quality Gate YAML Generator

- **Task ID:** TASK-004
- **Complexity:** medium
- **Complexity Score:** 5
- **Type:** implementation
- **Domain tags:** `quality-gates, yaml-generation, coach-validation`
- **Files to create:**
  - `guardkit/planning/quality_gate_generator.py`
  - `tests/unit/test_quality_gate_generator.py`
- **Files to modify:** None
- **Files NOT to touch:** `.guardkit/quality-gates/`
- **Dependencies:** TASK-001 (uses `TaskDefinition` dataclass)
- **Inputs:** Feature ID, `list[TaskDefinition]` with acceptance criteria and Coach validation commands
- **Outputs:** `.guardkit/quality-gates/FEAT-XXX.yaml`
- **Relevant decisions:** D4
- **Turn budget:** expected: 2, max: 4
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `guardkit/planning/quality_gate_generator.py`
  - [ ] Function `generate_quality_gates(feature_id, tasks)` returns `Path`
  - [ ] Output YAML contains gates: `lint`, `unit_tests` (at minimum)
  - [ ] Each gate has: `command` (str), `required` (bool)
  - [ ] Integration test gates have `required: false` by default
  - [ ] Deduplicates commands across tasks (e.g., multiple tasks with `ruff check src/`)
  - [ ] Tests pass: `pytest tests/unit/test_quality_gate_generator.py -v`
  - [ ] Lint passes: `ruff check guardkit/planning/quality_gate_generator.py`
- **Player constraints:**
  - Create files ONLY in `guardkit/planning/` and `tests/unit/`
  - Use `pyyaml` for YAML generation (already in project dependencies)
  - Tests must use `tmp_path`, never write to actual `.guardkit/`
- **Coach validation commands:**
  ```bash
  pytest tests/unit/test_quality_gate_generator.py -v
  ruff check guardkit/planning/quality_gate_generator.py
  python -c "from guardkit.planning.quality_gate_generator import generate_quality_gates; print('OK')"
  ```

---

### Task 5: Task Metadata Enricher

- **Task ID:** TASK-005
- **Complexity:** medium
- **Complexity Score:** 5
- **Type:** implementation
- **Domain tags:** `task-metadata, graphiti-integration, turn-budget, domain-tags`
- **Files to create:**
  - `guardkit/planning/task_metadata.py`
  - `tests/unit/test_task_metadata.py`
- **Files to modify:** None
- **Files NOT to touch:** `guardkit/orchestrator/`, `guardkit/knowledge/`
- **Dependencies:** TASK-001 (uses `TaskDefinition`), TASK-002 (uses `TargetConfig`)
- **Inputs:** `TaskDefinition` from SpecParser, `TargetConfig` from target mode
- **Outputs:** Enriched task markdown with YAML frontmatter, structured Coach blocks, Player constraints
- **Relevant decisions:** D5, D10
- **Turn budget:** expected: 3, max: 5
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `guardkit/planning/task_metadata.py`
  - [ ] Function `enrich_task(task, target_config) -> EnrichedTask` exists
  - [ ] Function `render_task_markdown(enriched_task) -> str` produces valid markdown with YAML frontmatter
  - [ ] YAML frontmatter includes: task_id, feature_id, complexity, complexity_score, type, domain_tags, files_to_create, files_to_modify, files_not_to_touch, dependencies, relevant_decisions, turn_budget, graphiti_context_budget
  - [ ] Turn budget follows rules: low → {expected:1, max:3}, medium → {expected:2, max:5}, high → {expected:3, max:5}
  - [ ] Graphiti context budget follows rules: low → 2000, medium → 4000, high → 6000
  - [ ] `local-model` target adds explicit import paths and type hints to implementation notes
  - [ ] Tests pass: `pytest tests/unit/test_task_metadata.py -v`
  - [ ] Lint passes: `ruff check guardkit/planning/task_metadata.py`
- **Player constraints:**
  - Create files ONLY in `guardkit/planning/` and `tests/unit/`
  - Do NOT import from `guardkit/orchestrator/` or `guardkit/knowledge/` — this module is consumed by the planning layer only
  - Complexity score calculation uses the existing `ComplexityFactors` logic from `guardkit/planning/complexity.py` if available, otherwise inline simple rules
- **Coach validation commands:**
  ```bash
  pytest tests/unit/test_task_metadata.py -v
  ruff check guardkit/planning/task_metadata.py
  python -c "from guardkit.planning.task_metadata import enrich_task, render_task_markdown; print('OK')"
  ```

---

### Task 6: Warnings Extractor and Seed Script Generator

- **Task ID:** TASK-006
- **Complexity:** low
- **Complexity Score:** 3
- **Type:** implementation
- **Domain tags:** `warnings, graphiti-seeding, shell-scripts`
- **Files to create:**
  - `guardkit/planning/warnings_extractor.py`
  - `guardkit/planning/seed_script_generator.py`
  - `tests/unit/test_warnings_extractor.py`
  - `tests/unit/test_seed_script_generator.py`
- **Files to modify:** None
- **Files NOT to touch:** `scripts/`, `docs/warnings/`
- **Dependencies:** TASK-001 (uses `ParsedSpec.warnings`), TASK-003 (uses ADR paths)
- **Inputs:** Warnings from ParsedSpec, ADR file paths, spec file path
- **Outputs:** `docs/warnings/FEAT-XXX-warnings.md`, `scripts/seed-FEAT-XXX.sh`
- **Relevant decisions:** D7
- **Turn budget:** expected: 1, max: 3
- **Acceptance criteria (machine-verifiable):**
  - [ ] Files exist: `guardkit/planning/warnings_extractor.py`, `guardkit/planning/seed_script_generator.py`
  - [ ] `extract_warnings(parsed_spec, feature_id)` creates warnings markdown file
  - [ ] `generate_seed_script(feature_id, adr_paths, spec_path, warnings_path)` creates executable bash script
  - [ ] Seed script includes: `guardkit graphiti status`, `guardkit graphiti add-context` for each ADR, spec, and warnings file, `guardkit graphiti verify --verbose`
  - [ ] Seed script is idempotent (contains `set -e` and checks)
  - [ ] Tests pass: `pytest tests/unit/test_warnings_extractor.py tests/unit/test_seed_script_generator.py -v`
  - [ ] Lint passes: `ruff check guardkit/planning/warnings_extractor.py guardkit/planning/seed_script_generator.py`
- **Player constraints:**
  - Create files ONLY in `guardkit/planning/` and `tests/unit/`
  - Seed script must use `#!/usr/bin/env bash` shebang
  - Seed script must have `set -e` for fail-fast behaviour
- **Coach validation commands:**
  ```bash
  pytest tests/unit/test_warnings_extractor.py tests/unit/test_seed_script_generator.py -v
  ruff check guardkit/planning/warnings_extractor.py guardkit/planning/seed_script_generator.py
  ```

---

### Task 7: Feature-Plan Command Integration

- **Task ID:** TASK-007
- **Complexity:** high
- **Complexity Score:** 7
- **Type:** integration
- **Domain tags:** `feature-plan, command-integration, orchestration`
- **Files to create:** None
- **Files to modify:**
  - `.claude/commands/feature-plan.md` (add new flags and output sections)
- **Files NOT to touch:** `guardkit/orchestrator/`, `guardkit/knowledge/`, `guardkit/cli/autobuild.py`
- **Dependencies:** TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-006 (all components)
- **Inputs:** All modules from Tasks 1-6
- **Outputs:** Updated `/feature-plan` command that accepts `--from-spec`, `--target`, `--generate-adrs`, `--generate-quality-gates` flags
- **Relevant decisions:** D1, D2, D6, D9
- **Turn budget:** expected: 3, max: 5
- **Acceptance criteria (machine-verifiable):**
  - [ ] `.claude/commands/feature-plan.md` updated with new flag descriptions
  - [ ] When `--from-spec` is provided, command instructs Claude to use `SpecParser` to extract data
  - [ ] When `--target local-model` is set, task output includes YAML frontmatter and structured Coach blocks
  - [ ] When `--generate-adrs` is set, command produces ADR files from Decision Log
  - [ ] When `--generate-quality-gates` is set, command produces quality gate YAML
  - [ ] Existing behaviour (no flags) unchanged
  - [ ] Integration test: parse sample spec → generate all outputs → validate file existence
  - [ ] Lint passes: `ruff check guardkit/planning/`
- **Player constraints:**
  - Modify ONLY `.claude/commands/feature-plan.md`
  - Do NOT modify any Python code in orchestrator or CLI layers
  - The command file instructs Claude Code how to use the modules — it does not implement them
  - Preserve all existing content in feature-plan.md; add new sections, don't replace
- **Coach validation commands:**
  ```bash
  # Verify command file is valid markdown
  python -c "
  from pathlib import Path
  content = Path('.claude/commands/feature-plan.md').read_text()
  assert '--from-spec' in content
  assert '--target' in content
  assert '--generate-adrs' in content
  assert '--generate-quality-gates' in content
  assert 'SpecParser' in content or 'spec_parser' in content
  print('Command file validation OK')
  "
  ruff check guardkit/planning/
  ```

---

### Task 8: Documentation — Two-Phase Workflow Guide

- **Task ID:** TASK-008
- **Complexity:** medium
- **Complexity Score:** 4
- **Type:** documentation
- **Domain tags:** `documentation, two-phase-workflow, guides`
- **Files to create:**
  - `docs/guides/two-phase-workflow.md`
- **Files to modify:** None
- **Files NOT to touch:** `guardkit/`, `tests/`
- **Dependencies:** TASK-007 (needs finalized command design)
- **Inputs:** This feature spec, Research Template, existing AutoBuild docs
- **Outputs:** Comprehensive guide explaining the two-phase workflow end-to-end
- **Relevant decisions:** D1, D2, D6, D7, D8
- **Turn budget:** expected: 2, max: 4
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `docs/guides/two-phase-workflow.md`
  - [ ] Document contains sections: Overview, Phase 1 (Research & Planning), Phase 2 (Implementation), Research Template Guide, Feature-Plan Flags Reference, Graphiti Seeding, Troubleshooting
  - [ ] Contains at least 2 complete command examples showing the full workflow
  - [ ] References `/feature-plan --from-spec` and `--target local-model` flags
  - [ ] References `scripts/seed-FEAT-XXX.sh` and `guardkit feature-build`
  - [ ] Contains Mermaid or ASCII diagram showing the two-phase data flow
  - [ ] Word count > 1500 (comprehensive guide, not a stub)
- **Player constraints:**
  - Create files ONLY in `docs/guides/`
  - Do NOT create or modify any code files
  - Use Markdown with MkDocs-compatible formatting (admonitions, code blocks with language tags)
  - Reference existing documentation pages by relative link, not absolute URL
- **Coach validation commands:**
  ```bash
  python -c "
  from pathlib import Path
  content = Path('docs/guides/two-phase-workflow.md').read_text()
  assert len(content.split()) > 1500, f'Too short: {len(content.split())} words'
  for section in ['Phase 1', 'Phase 2', '--from-spec', '--target', 'seed-FEAT', 'feature-build']:
      assert section in content, f'Missing section/reference: {section}'
  print('Documentation validation OK')
  "
  ```

---

### Task 9: Documentation — Updated Feature-Plan Reference

- **Task ID:** TASK-009
- **Complexity:** low
- **Complexity Score:** 3
- **Type:** documentation
- **Domain tags:** `documentation, command-reference, feature-plan`
- **Files to create:** None
- **Files to modify:**
  - `docs/reference/feature-plan.md` (or create if doesn't exist)
- **Files NOT to touch:** `guardkit/`, `tests/`, `.claude/commands/`
- **Dependencies:** TASK-007 (needs finalized flags)
- **Inputs:** Updated `/feature-plan` command specification from TASK-007
- **Outputs:** Complete command reference page with all flags, examples, and output format documentation
- **Relevant decisions:** D1, D8, D9
- **Turn budget:** expected: 1, max: 3
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `docs/reference/feature-plan.md`
  - [ ] Documents all flags: `--from-spec`, `--target`, `--generate-adrs`, `--generate-quality-gates`
  - [ ] Includes usage examples for each flag
  - [ ] Includes output format description for both `interactive` and `local-model` targets
  - [ ] Includes table of task metadata fields produced in `local-model` mode
- **Player constraints:**
  - Modify/create ONLY `docs/reference/feature-plan.md`
  - Follow existing command reference page patterns if available
  - Use MkDocs-compatible formatting
- **Coach validation commands:**
  ```bash
  python -c "
  from pathlib import Path
  content = Path('docs/reference/feature-plan.md').read_text()
  for flag in ['--from-spec', '--target', '--generate-adrs', '--generate-quality-gates']:
      assert flag in content, f'Missing flag: {flag}'
  print('Reference doc validation OK')
  "
  ```

---

### Task 10: Documentation — Research Template Guide

- **Task ID:** TASK-010
- **Complexity:** low
- **Complexity Score:** 3
- **Type:** documentation
- **Domain tags:** `documentation, research-template, guides`
- **Files to create:**
  - `docs/guides/research-template.md`
  - `docs/templates/research-to-implementation-template.md` (canonical copy of the template)
- **Files to modify:** None
- **Files NOT to touch:** `guardkit/`, `tests/`
- **Dependencies:** TASK-001 (needs parser to understand what format matters)
- **Inputs:** Research-to-Implementation Template, this feature spec
- **Outputs:** Guide explaining how to fill in the template, what each section is for, and tips for making specs that local models execute well
- **Relevant decisions:** D6, D8
- **Turn budget:** expected: 1, max: 3
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `docs/guides/research-template.md`
  - [ ] File exists: `docs/templates/research-to-implementation-template.md`
  - [ ] Guide explains all 11 template sections with examples
  - [ ] Guide includes "Tips for Local Model Execution" section
  - [ ] Template file is a clean, fillable version (no example data except placeholders)
- **Player constraints:**
  - Create files ONLY in `docs/guides/` and `docs/templates/`
  - Do NOT modify any code files
  - The template copy must be identical in structure to the uploaded template, with placeholder text
- **Coach validation commands:**
  ```bash
  python -c "
  from pathlib import Path
  assert Path('docs/guides/research-template.md').exists()
  assert Path('docs/templates/research-to-implementation-template.md').exists()
  template = Path('docs/templates/research-to-implementation-template.md').read_text()
  for section in ['Problem Statement', 'Decision Log', 'Architecture', 'Implementation Tasks', 'Graphiti ADR Seeding']:
      assert section in template, f'Missing section: {section}'
  print('Template validation OK')
  "
  ```

---

### Task 11: Integration Tests

- **Task ID:** TASK-011
- **Complexity:** high
- **Complexity Score:** 7
- **Type:** integration
- **Domain tags:** `integration-tests, end-to-end, feature-plan-pipeline`
- **Files to create:**
  - `tests/integration/test_feature_plan_pipeline.py`
  - `tests/fixtures/sample-research-spec.md` (test fixture)
- **Files to modify:** None
- **Files NOT to touch:** `guardkit/planning/` (read-only for tests), `docs/`
- **Dependencies:** TASK-001 through TASK-007 (all implementation tasks)
- **Inputs:** Sample research spec (test fixture), all planning modules
- **Outputs:** Integration tests validating the full pipeline: parse → enrich → generate ADRs → generate quality gates → generate seed script
- **Relevant decisions:** D2, D6, D9
- **Turn budget:** expected: 3, max: 5
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `tests/integration/test_feature_plan_pipeline.py`
  - [ ] File exists: `tests/fixtures/sample-research-spec.md`
  - [ ] Test: parse sample spec → verify `ParsedSpec` has all sections populated
  - [ ] Test: enrich tasks with `local-model` target → verify YAML frontmatter present
  - [ ] Test: generate ADRs → verify files created in temp dir
  - [ ] Test: generate quality gates → verify YAML valid and contains expected gates
  - [ ] Test: generate seed script → verify script contains all `add-context` commands
  - [ ] Tests pass: `pytest tests/integration/test_feature_plan_pipeline.py -v`
  - [ ] Lint passes: `ruff check tests/integration/test_feature_plan_pipeline.py`
- **Player constraints:**
  - Create files ONLY in `tests/integration/` and `tests/fixtures/`
  - Tests must use `tmp_path` for all file output
  - Sample spec must be realistic but minimal (3 decisions, 3 tasks)
  - Mark integration tests with `@pytest.mark.integration`
- **Coach validation commands:**
  ```bash
  pytest tests/integration/test_feature_plan_pipeline.py -v
  ruff check tests/integration/test_feature_plan_pipeline.py
  ```

## 6. Test Strategy

### Unit Tests

| Test File | Covers | Key Assertions |
|-----------|--------|---------------|
| `tests/unit/test_spec_parser.py` | Spec parsing, section extraction | Parses all 11 sections, handles missing sections, correct Decision extraction |
| `tests/unit/test_target_mode.py` | Target resolution | Enum values, config file reading, default behaviour |
| `tests/unit/test_adr_generator.py` | ADR file creation | File naming, content format, duplicate detection |
| `tests/unit/test_quality_gate_generator.py` | Quality gate YAML | YAML structure, command deduplication, required/optional gates |
| `tests/unit/test_task_metadata.py` | Task enrichment | YAML frontmatter, turn budgets, context budgets, Coach blocks |
| `tests/unit/test_warnings_extractor.py` | Warning extraction | Markdown formatting, feature ID in filename |
| `tests/unit/test_seed_script_generator.py` | Seed script generation | Bash syntax, idempotency, all ADR commands present |

### Integration Tests

| Test File | Covers | Prerequisites |
|-----------|--------|--------------|
| `tests/integration/test_feature_plan_pipeline.py` | Full parse → generate pipeline | All planning modules importable |

### Manual Verification

- [ ] Run `/feature-plan --from-spec` against the Research Template used to create this very feature — verify it produces correct output (self-referential validation)
- [ ] Run generated `seed-FEAT-FP-002.sh` against a local Graphiti instance — verify ADRs and warnings appear in graph
- [ ] Run `/feature-build FEAT-FP-002` with a local model — verify tasks execute with enriched metadata

## 7. Dependencies & Setup

### Python Dependencies

```
# requirements.txt additions (if not already present)
pyyaml>=6.0    # Quality gate YAML generation
```

### System Dependencies

None beyond existing GuardKit requirements.

### Environment Variables

No new environment variables required. Target mode auto-detection uses `.guardkit/config.yaml`:

```yaml
# .guardkit/config.yaml (existing file, new optional section)
autobuild:
  endpoint: "http://dell-promax:8000/v1"  # presence triggers auto-detection
  model: "Qwen3-Coder-30B-A3B"
```

## 8. File Tree (Target State)

```
guardkit/
├── planning/
│   ├── __init__.py                    # Updated with new exports
│   ├── spec_parser.py                 # Task 1
│   ├── target_mode.py                 # Task 2
│   ├── adr_generator.py              # Task 3
│   ├── quality_gate_generator.py     # Task 4
│   ├── task_metadata.py              # Task 5
│   ├── warnings_extractor.py         # Task 6
│   ├── seed_script_generator.py      # Task 6
│   ├── complexity.py                  # Existing
│   ├── dependencies.py               # Existing
│   └── feature_writer.py             # Existing
├── .claude/commands/
│   └── feature-plan.md               # Task 7 (modified)
├── docs/
│   ├── guides/
│   │   ├── two-phase-workflow.md      # Task 8
│   │   └── research-template.md      # Task 10
│   ├── reference/
│   │   └── feature-plan.md           # Task 9
│   └── templates/
│       └── research-to-implementation-template.md  # Task 10
├── tests/
│   ├── unit/
│   │   ├── test_spec_parser.py       # Task 1
│   │   ├── test_target_mode.py       # Task 2
│   │   ├── test_adr_generator.py     # Task 3
│   │   ├── test_quality_gate_generator.py  # Task 4
│   │   ├── test_task_metadata.py     # Task 5
│   │   ├── test_warnings_extractor.py      # Task 6
│   │   └── test_seed_script_generator.py   # Task 6
│   ├── integration/
│   │   └── test_feature_plan_pipeline.py   # Task 11
│   └── fixtures/
│       └── sample-research-spec.md         # Task 11
```

## 9. Out of Scope

- AutoBuild orchestrator changes — the orchestrator already reads task metadata; this feature only enriches what `/feature-plan` produces
- Graphiti schema changes — uses existing context categories and seeding commands
- Coach validation logic changes — Coach already runs commands from task files; this feature structures them more explicitly
- `/feature-build` command changes — no modifications needed, consumes enriched task files transparently
- Local model fine-tuning or prompt optimisation — out of scope for this feature
- Multi-model target profiles (e.g., different output for Qwen vs Nemotron) — single `local-model` profile is sufficient initially
- CI/CD integration for automated Phase 1 → Phase 2 handoff
- Web UI for research template editing
- RequireKit integration (separate feature track)

## 10. Open Questions (Resolved)

| Question | Resolution |
|----------|-----------|
| Should `--from-spec` be required or can `/feature-plan` still accept free-form text? | Both modes supported. `--from-spec` is additive — free-form text input unchanged (Decision D9) |
| Should ADRs be generated as separate files or inline? | Separate files for individual Graphiti seeding. The spec file itself is also seeded for feature-level context (Decision D3) |
| What happens if the Research Template has sections the parser can't parse? | Graceful degradation — unparseable sections produce warnings in output, not errors. Parser extracts what it can (Warning in D6) |
| Should the quality gate YAML override or supplement global quality gates? | Supplement. Feature-specific gates merge with global `.guardkit/quality-gates/default.yaml` (Decision D4) |
| How do we handle cross-feature ADRs? | ADR files include `applies_to: [FEAT-XXX, FEAT-YYY]` frontmatter. Graphiti's semantic search handles cross-feature retrieval naturally |
| Should turn budget hints be enforced by feature-plan or advisory? | Advisory only. Enforcement remains in AutoBuild orchestrator (Decision D10, Warning) |
| What's the right task granularity for 5-turn Coach validation? | Tasks should be scoped to 1-5 files and one logical unit of work. If a task requires more than 5 files, split it. If the Coach can't validate within 5 turns, the spec was under-specified |

---

## 11. Graphiti ADR Seeding

### ADR Files to Generate

From the Decision Log (Section 2), generate these ADR files:

```
docs/adr/ADR-FP-002-target-mode-flag.md            # D1
docs/adr/ADR-FP-002-research-template-input.md      # D2, D6
docs/adr/ADR-FP-002-automatic-adr-generation.md     # D3
docs/adr/ADR-FP-002-per-feature-quality-gates.md    # D4
docs/adr/ADR-FP-002-task-metadata-enrichment.md     # D5
docs/adr/ADR-FP-002-graphiti-seed-scripts.md        # D7
docs/adr/ADR-FP-002-documentation-as-deliverable.md # D8
docs/adr/ADR-FP-002-backward-compatibility.md       # D9
docs/adr/ADR-FP-002-turn-budget-hints.md            # D10
```

### Seeding Commands

```bash
#!/usr/bin/env bash
# scripts/seed-FEAT-FP-002.sh
set -e

echo "=== Seeding FEAT-FP-002: Two-Phase Feature Plan Enhancements ==="

# 1. Check Graphiti status
guardkit graphiti status

# 2. Seed ADR files
echo "Seeding ADR files..."
guardkit graphiti add-context docs/adr/ADR-FP-002-*.md

# 3. Seed feature specification
echo "Seeding feature specification..."
guardkit graphiti add-context docs/features/FEAT-FP-002-two-phase-feature-plan-enhancements.md

# 4. Seed warnings
echo "Seeding warnings..."
guardkit graphiti add-context docs/warnings/FEAT-FP-002-warnings.md

# 5. Verify
echo "Verifying seeding..."
guardkit graphiti verify --verbose

echo "=== Seeding complete ==="
```

### Context Categories Populated

| Category | Source Section | Retrieved When | Token Priority |
|----------|---------------|---------------|---------------|
| `architecture_decisions` | Decision Log (§2) + ADR files | Tasks referencing planning, spec parsing, or output formatting | High |
| `feature_context` | Full spec file | All tasks in FEAT-FP-002 | Medium |
| `warnings` | Warnings & Constraints (§2) | Tasks touching parser, quality gates, or ADR generation | High |
| `technology_stack` | Dependencies (§7) | Tasks using pyyaml | Low |
| `patterns` | Implementation notes in tasks (§5) | Similar parsing or generation tasks | Medium |
| `domain_knowledge` | Resolved Questions (§10) | Semantic match to task content | Low |

### Quality Gate Configuration

```yaml
# .guardkit/quality-gates/FEAT-FP-002.yaml
feature_id: FEAT-FP-002
quality_gates:
  lint:
    command: "ruff check guardkit/planning/"
    required: true
  unit_tests:
    command: "pytest tests/unit/test_spec_parser.py tests/unit/test_target_mode.py tests/unit/test_adr_generator.py tests/unit/test_quality_gate_generator.py tests/unit/test_task_metadata.py tests/unit/test_warnings_extractor.py tests/unit/test_seed_script_generator.py -v --tb=short"
    required: true
  integration_tests:
    command: "pytest tests/integration/test_feature_plan_pipeline.py -v"
    required: true
  type_check:
    command: "mypy guardkit/planning/ --ignore-missing-imports"
    required: false  # Enable once type stubs are stable
  coverage:
    command: "pytest tests/unit/ --cov=guardkit/planning --cov-fail-under=80"
    required: false  # Enable after all unit test tasks complete
```

---

## Phase 2 Execution Workflow

```bash
# On Dell ProMax — vLLM serving local model

# 1. Pull latest from repo (Phase 1 commits)
git pull origin feature/two-phase-feature-plan

# 2. Seed Graphiti with feature context
bash scripts/seed-FEAT-FP-002.sh

# 3. Option A: Full autonomous build
guardkit feature-build FEAT-FP-002
# → Executes TASK-001 through TASK-011 sequentially (respecting dependencies)
# → Player-Coach loop for each task with Graphiti context
# → Work preserved in .guardkit/worktrees/FEAT-FP-002/

# 4. Review
cd .guardkit/worktrees/FEAT-FP-002 && git diff main

# 5. Accept and merge
guardkit feature-complete FEAT-FP-002

# Option B: Interactive task-by-task
guardkit task-work TASK-001  # Spec Parser
guardkit task-complete TASK-001
guardkit task-work TASK-002  # Target Mode
# ... continue sequentially
```

---

## Appendix A: Dependency Graph

```
TASK-001 (Spec Parser) ──────┬──→ TASK-003 (ADR Gen) ──────┐
                             ├──→ TASK-004 (QG Gen) ───────┤
                             ├──→ TASK-005 (Metadata) ──────┤
                             ├──→ TASK-006 (Warnings+Seed)──┤
                             │                               ├──→ TASK-007 (Command Integration) ──→ TASK-008 (Docs: Workflow)
TASK-002 (Target Mode) ──────┼──→ TASK-005 (Metadata) ──────┤                                    ──→ TASK-009 (Docs: Reference)
                             │                               │
                             └──→ TASK-010 (Docs: Template)──┘
                                                              └──→ TASK-011 (Integration Tests)
```

Parallel execution groups:
- **Group 1** (no dependencies): TASK-001, TASK-002
- **Group 2** (depends on Group 1): TASK-003, TASK-004, TASK-005, TASK-006, TASK-010
- **Group 3** (depends on Group 2): TASK-007
- **Group 4** (depends on Group 3): TASK-008, TASK-009, TASK-011

## Appendix B: Research Template Section ↔ Task Metadata Mapping

This table shows how each section of the Research-to-Implementation Template maps to task metadata fields that drive Graphiti's `JobContextRetriever`:

| Template Section | Task Metadata Field | Graphiti Context Category | Purpose |
|-----------------|--------------------|-----------------------------|---------|
| §1 Problem Statement | Feature description in FEATURE.md | `feature_context` | Grounds the Player on "why" |
| §2 Decision Log | `relevant_decisions` field per task | `architecture_decisions` | Explicit decision cross-references |
| §2 Warnings | Seeded as warning nodes | `warnings` | High-priority retrieval for related tasks |
| §3 Architecture | Feature context + component tags | `feature_context` | System-level understanding |
| §4 API Contracts | Implementation notes per task | `integration_points` | Cross-component interface specs |
| §5 Task Metadata | YAML frontmatter per task | Direct parsing by AutoBuild | Task-level configuration |
| §5 Domain Tags | `domain_tags` field per task | Semantic search keys for Graphiti | Context retrieval targeting |
| §5 File Constraints | `files_to_create/modify/not_to_touch` | Player constraint enforcement | Prevents file-scope drift |
| §5 Coach Commands | `coach_validation_commands` block | Quality gate execution | Deterministic validation |
| §6 Test Strategy | Quality gate YAML | `quality_gate_configs` | Coach validation configuration |
| §7 Dependencies | Implementation notes | `technology_stack` | Library/version context |
| §8 File Tree | Feature context | `feature_context` | Target state reference |
| §9 Out of Scope | Player constraints | `warnings` | Prevents scope creep |
| §10 Resolved Questions | Feature context | `domain_knowledge` | Future retrieval for similar questions |
