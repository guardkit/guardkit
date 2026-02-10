# Research Spec: Sample Feature for Integration Testing

## 1. Problem Statement

This is a sample research specification used for integration testing of the
feature-plan pipeline. It contains all required sections with valid data
for testing the technology seams between modules.

## 2. Decision Log

| # | Decision | Rationale | Alternatives Rejected | Status |
|---|----------|-----------|----------------------|---------|
| D1 | Use Python dataclasses | Provides type safety and IDE support without external dependencies | Pydantic (too heavy), TypedDict (less features), attrs (extra dependency) | Accepted |
| D2 | Parse markdown with regex | Simple and dependency-free approach for structured markdown | markdown-it (overkill), mistune (extra dependency), commonmark (complex) | Accepted |
| D3 | Generate YAML for quality gates | YAML is human-readable and widely supported for configuration | JSON (less readable), TOML (less common), INI (limited structure) | Proposed |

## 3. Warnings & Constraints

- W1: Do not modify existing spec_parser tests - they are stable and cover edge cases
- W2: Maintain backward compatibility with existing ParsedSpec consumers
- W3: All generated files must be deterministic for reproducible builds

## 4. Architecture

### 4.1 Component Design

| Component | File Path | Purpose | Status |
|-----------|-----------|---------|--------|
| SpecParser | guardkit/planning/spec_parser.py | Parses research templates into structured data | Modified |
| ADRGenerator | guardkit/planning/adr_generator.py | Generates ADR files from decisions | New |
| QualityGateGenerator | guardkit/planning/quality_gate_generator.py | Creates quality gate YAML configs | New |
| TaskMetadataEnricher | guardkit/planning/task_metadata.py | Enriches tasks with budgets and metadata | New |
| WarningsExtractor | guardkit/planning/warnings_extractor.py | Extracts warnings to separate markdown | New |
| SeedScriptGenerator | guardkit/planning/seed_script_generator.py | Generates Graphiti seeding scripts | New |

### 4.2 Data Flow

```
research-spec.md
      |
      v
  parse_research_template()
      |
      v
  ParsedSpec
      |
      +---> decisions ---> generate_adrs() ---> ADR files
      |                         |
      |                         +---> generate_seed_script()
      |
      +---> warnings ---> extract_warnings() ---> warnings.md
      |
      +---> tasks ---> enrich_task() ---> EnrichedTask
      |                    |
      |                    +---> render_task_markdown()
      |
      +---> tasks ---> generate_quality_gates() ---> quality-gates.yaml
```

## 5. API Contracts

### parse_research_template

```python
def parse_research_template(path: Path) -> ParsedSpec:
    """Parse a research template markdown file into structured data."""
    ...
```

### generate_adrs

```python
def generate_adrs(
    decisions: list[Decision],
    feature_id: str,
    output_dir: Path,
    check_duplicates: bool = True,
) -> list[Path]:
    """Generate ADR files from decision log entries."""
    ...
```

## 6. Out of Scope

- Database integration
- Web UI components
- Real-time collaboration features

## 7. Open Questions

| Question | Resolution |
|----------|-----------|
| Should ADR files include timestamps? | Yes, include ISO date in header |
| What format for quality gate YAML? | Standard YAML with feature_id and gates dict |

## 8. Test Strategy

### Unit Tests

1. **Test:** parse_research_template with valid input
   **Expected:** Returns ParsedSpec with all fields populated

2. **Test:** generate_adrs with multiple decisions
   **Expected:** Creates one ADR file per decision

### Integration Tests

1. **Test:** Full pipeline from parse to artifact generation
   **Expected:** All artifacts created in correct locations

### Manual Verification

- Verify generated ADR files are valid markdown
- Check that quality gate YAML is parseable
- Confirm seed script is executable

## 9. Dependencies

### Python Packages

- pyyaml>=6.0
- pathlib (stdlib)

### System Dependencies

- None required

### Environment Variables

- GUARDKIT_OUTPUT_DIR: Optional output directory override

## 10. File Tree

```
guardkit/planning/
├── __init__.py
├── spec_parser.py
├── adr_generator.py
├── quality_gate_generator.py
├── task_metadata.py
├── warnings_extractor.py
├── seed_script_generator.py
└── target_mode.py
```

## 11. Implementation Tasks

### TASK 1: Implement Spec Parser Core

- **Complexity:** medium (5/10)
- **Type:** implementation
- **Domain Tags:** [parsing, dataclasses, regex]
- **Files to Create:** [guardkit/planning/spec_parser.py]
- **Files to Modify:** []
- **Files NOT to Touch:** [tests/unit/planning/]
- **Dependencies:** None
- **Inputs:** Path to research template markdown file
- **Outputs:** ParsedSpec dataclass with all parsed sections
- **Relevant Decisions:** D1, D2
- **Acceptance Criteria:**
  1. Parses Decision Log table into Decision objects
  2. Extracts warnings from Warnings section
  3. Parses Implementation Tasks into TaskDefinition objects
  4. Returns ParsedSpec with all fields populated
- **Implementation Notes:** Use regex-based parsing for markdown tables
- **Player Constraints:**
  - Do not add external markdown parsing libraries
  - Keep the parser stateless
- **Coach Validation:**
  - pytest tests/unit/planning/test_spec_parser.py -v
  - ruff check guardkit/planning/spec_parser.py
- **Turn Budget:** 2 expected, 4 max

### TASK 2: Implement ADR Generator

- **Complexity:** low (3/10)
- **Type:** implementation
- **Domain Tags:** [adr, markdown, file-generation]
- **Files to Create:** [guardkit/planning/adr_generator.py]
- **Files to Modify:** []
- **Files NOT to Touch:** [guardkit/planning/spec_parser.py]
- **Dependencies:** TASK 1
- **Inputs:** List of Decision objects, feature ID, output directory
- **Outputs:** List of Path objects for generated ADR files
- **Relevant Decisions:** D1
- **Acceptance Criteria:**
  1. Generates one ADR file per Decision
  2. Uses slugified title for filename
  3. Includes all decision metadata in ADR content
  4. Skips duplicate files if check_duplicates is True
- **Implementation Notes:** Follow Nygard ADR format
- **Player Constraints:**
  - Filename must be URL-safe
  - Include date in ADR content
- **Coach Validation:**
  - pytest tests/unit/planning/test_adr_generator.py -v
  - ruff check guardkit/planning/adr_generator.py
- **Turn Budget:** 1 expected, 3 max

### TASK 3: Implement Quality Gate Generator

- **Complexity:** medium (4/10)
- **Type:** implementation
- **Domain Tags:** [quality-gates, yaml, validation]
- **Files to Create:** [guardkit/planning/quality_gate_generator.py]
- **Files to Modify:** []
- **Files NOT to Touch:** [guardkit/planning/spec_parser.py, guardkit/planning/adr_generator.py]
- **Dependencies:** TASK 1
- **Inputs:** Feature ID, list of TaskDefinition objects
- **Outputs:** Path to generated quality gates YAML file
- **Relevant Decisions:** D3
- **Acceptance Criteria:**
  1. Extracts coach_validation_commands from all tasks
  2. Categorizes commands into lint, test, coverage gates
  3. Generates valid YAML with feature_id and gates
  4. Deduplicates identical commands
- **Implementation Notes:** Use pyyaml for YAML generation
- **Player Constraints:**
  - Output must be valid YAML
  - Maintain command order for reproducibility
- **Coach Validation:**
  - pytest tests/unit/planning/test_quality_gate_generator.py -v
  - ruff check guardkit/planning/quality_gate_generator.py
- **Turn Budget:** 2 expected, 4 max
