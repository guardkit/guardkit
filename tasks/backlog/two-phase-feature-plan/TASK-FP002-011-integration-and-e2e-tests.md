---
id: TASK-FP002-011
title: Integration and End-to-End Tests
task_type: testing
parent_review: TASK-REV-FP002
feature_id: FEAT-FP-002
wave: 4
implementation_mode: task-work
complexity: 7
complexity_score: 7
type: integration
domain_tags:
- integration-tests
- end-to-end
- feature-plan-pipeline
- technology-seams
files_to_create:
- tests/integration/test_feature_plan_pipeline.py
- tests/integration/test_planning_module_seams.py
- tests/fixtures/sample-research-spec.md
files_to_modify: []
files_not_to_touch:
- guardkit/planning/
- docs/
dependencies:
- TASK-FP002-001
- TASK-FP002-002
- TASK-FP002-003
- TASK-FP002-004
- TASK-FP002-005
- TASK-FP002-006
relevant_decisions:
- D2
- D6
- D9
turn_budget:
  expected: 3
  max: 5
graphiti_context_budget: 6000
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 25
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-FP-002
  base_branch: main
  started_at: '2026-02-10T18:06:55.496093'
  last_updated: '2026-02-10T18:17:53.251378'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-10T18:06:55.496093'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# TASK-FP002-011: Integration and End-to-End Tests

## Description

Create comprehensive integration and end-to-end tests that validate the full feature-plan pipeline and specifically test the technology seams between modules. This task directly addresses the user's requirement to "include integration and end-to-end tests to try to reduce the errors we typically see at the technology seams when building guardkit features."

## Technology Seams to Test

The following module boundaries are where integration errors typically occur:

1. **SpecParser → ADRGenerator**: `Decision` objects flow from parser to ADR generator
2. **SpecParser → QualityGateGenerator**: `TaskDefinition` objects flow to quality gate generation
3. **SpecParser → TaskMetadataEnricher**: `TaskDefinition` + `TargetConfig` → enriched tasks
4. **SpecParser → WarningsExtractor**: `ParsedSpec.warnings` → warnings markdown
5. **ADRGenerator → SeedScriptGenerator**: ADR file paths flow to seed script generation
6. **TaskMetadataEnricher → TargetMode**: `TargetConfig` influences enrichment behavior
7. **Full Pipeline**: Parse spec → enrich all tasks → generate all artifacts → validate consistency

## Acceptance Criteria (Machine-Verifiable)

- [ ] File exists: `tests/integration/test_feature_plan_pipeline.py`
- [ ] File exists: `tests/integration/test_planning_module_seams.py`
- [ ] File exists: `tests/fixtures/sample-research-spec.md`

### Pipeline Tests (test_feature_plan_pipeline.py)
- [ ] Test: parse sample spec → verify `ParsedSpec` has all sections populated
- [ ] Test: enrich tasks with `local-model` target → verify YAML frontmatter present
- [ ] Test: generate ADRs → verify files created in temp dir with correct naming
- [ ] Test: generate quality gates → verify YAML valid and contains expected gates
- [ ] Test: generate seed script → verify script contains all `add-context` commands
- [ ] Test: full pipeline end-to-end (parse → enrich → ADRs → gates → warnings → seed script)

### Seam Tests (test_planning_module_seams.py)
- [ ] Test: SpecParser Decision output is compatible with ADRGenerator input (field names, types)
- [ ] Test: SpecParser TaskDefinition output is compatible with QualityGateGenerator input
- [ ] Test: SpecParser TaskDefinition + TargetConfig compatible with TaskMetadataEnricher
- [ ] Test: ADRGenerator output paths are valid input for SeedScriptGenerator
- [ ] Test: WarningsExtractor output path is valid input for SeedScriptGenerator
- [ ] Test: TaskMetadataEnricher render output contains valid YAML frontmatter (parseable by pyyaml)
- [ ] Test: Round-trip — parse spec, generate all outputs, re-parse generated task files to verify frontmatter validity

### Cross-Module Consistency Tests
- [ ] Test: Feature ID is consistent across all generated artifacts (ADRs, quality gates, seed script, task files)
- [ ] Test: Decision references in tasks (D1, D2...) all have corresponding ADR files generated
- [ ] Test: All Coach validation commands in tasks appear in quality gate YAML
- [ ] Test: Seed script references all generated ADR files

### Tests Run Successfully
- [ ] Tests pass: `pytest tests/integration/test_feature_plan_pipeline.py tests/integration/test_planning_module_seams.py -v`
- [ ] Lint passes: `ruff check tests/integration/test_feature_plan_pipeline.py tests/integration/test_planning_module_seams.py`

## Coach Validation Commands

```bash
pytest tests/integration/test_feature_plan_pipeline.py tests/integration/test_planning_module_seams.py -v
ruff check tests/integration/test_feature_plan_pipeline.py tests/integration/test_planning_module_seams.py
```

## Player Constraints

- Create files ONLY in `tests/integration/` and `tests/fixtures/`
- Tests must use `tmp_path` for all file output
- Sample spec must be realistic but minimal (3 decisions, 3 tasks)
- Mark integration tests with `@pytest.mark.integration`
- Do NOT modify any source code in `guardkit/planning/`
- Import all modules under test from their public APIs

## Implementation Notes (Prescriptive)

### Sample Research Spec (tests/fixtures/sample-research-spec.md)

Create a minimal but realistic research spec fixture with:
- 3 decisions in the Decision Log table
- 2-3 warnings in the Warnings section
- 3 tasks with full metadata (domain_tags, files_to_create, acceptance_criteria, etc.)
- Simple architecture and data flow sections
- Basic test strategy table

### Seam Test Pattern

For each technology seam, the test should:
1. Create output from the "producer" module (e.g., SpecParser)
2. Pass that output directly to the "consumer" module (e.g., ADRGenerator)
3. Verify the consumer produces valid output without errors
4. Verify specific fields are correctly propagated

Example:
```python
@pytest.mark.integration
class TestSpecParserToADRGeneratorSeam:
    """Tests the data flow from SpecParser → ADRGenerator."""

    def test_parsed_decisions_produce_valid_adrs(self, tmp_path, sample_spec_path):
        """Verify Decision objects from parser are accepted by ADR generator."""
        parsed = parse_research_template(sample_spec_path)
        assert len(parsed.decisions) > 0

        adr_paths = generate_adrs(
            decisions=parsed.decisions,
            feature_id="FEAT-TEST-001",
            output_dir=tmp_path / "adrs",
        )

        assert len(adr_paths) == len(parsed.decisions)
        for path in adr_paths:
            assert path.exists()
            content = path.read_text()
            assert "Status:" in content
            assert "FEAT-TEST-001" in content

    def test_decision_number_preserved_in_adr(self, tmp_path, sample_spec_path):
        """Verify decision numbers (D1, D2...) appear in generated ADRs."""
        parsed = parse_research_template(sample_spec_path)
        adr_paths = generate_adrs(parsed.decisions, "FEAT-TEST-001", tmp_path)

        for decision, adr_path in zip(parsed.decisions, adr_paths):
            content = adr_path.read_text()
            assert decision.number in content
```

### End-to-End Pipeline Test Pattern

```python
@pytest.mark.integration
class TestFullPipeline:
    """End-to-end test: parse → enrich → generate all artifacts."""

    def test_complete_pipeline(self, tmp_path, sample_spec_path):
        """Full pipeline from spec file to all generated artifacts."""
        # 1. Parse
        parsed = parse_research_template(sample_spec_path)
        assert parsed.problem_statement
        assert len(parsed.decisions) >= 3
        assert len(parsed.tasks) >= 3

        # 2. Resolve target
        target_config = resolve_target("local-model")
        assert target_config.output_verbosity == "explicit"

        # 3. Enrich tasks
        feature_id = "FEAT-TEST-001"
        enriched_tasks = []
        for task in parsed.tasks:
            enriched = enrich_task(task, target_config, feature_id)
            enriched_tasks.append(enriched)

        # 4. Render task markdown
        for enriched in enriched_tasks:
            markdown = render_task_markdown(enriched)
            assert "---" in markdown  # YAML frontmatter delimiters
            assert feature_id in markdown

        # 5. Generate ADRs
        adr_dir = tmp_path / "adrs"
        adr_paths = generate_adrs(parsed.decisions, feature_id, adr_dir)
        assert len(adr_paths) == len(parsed.decisions)

        # 6. Generate quality gates
        qg_path = generate_quality_gates(feature_id, parsed.tasks, tmp_path / "qg.yaml")
        assert qg_path.exists()

        # 7. Extract warnings
        warnings_path = extract_warnings(parsed.warnings, feature_id, tmp_path / "warnings")

        # 8. Generate seed script
        seed_path = generate_seed_script(
            feature_id, adr_paths, sample_spec_path, warnings_path, tmp_path / "scripts"
        )
        assert seed_path.exists()
        script_content = seed_path.read_text()
        for adr_path in adr_paths:
            assert str(adr_path) in script_content or adr_path.name in script_content
```

### Cross-Module Consistency Test

```python
@pytest.mark.integration
class TestCrossModuleConsistency:
    """Verify consistency across all generated artifacts."""

    def test_feature_id_consistent_everywhere(self, tmp_path, sample_spec_path):
        """Feature ID appears in all generated files."""
        parsed = parse_research_template(sample_spec_path)
        feature_id = "FEAT-TEST-001"

        # Generate all artifacts
        adr_paths = generate_adrs(parsed.decisions, feature_id, tmp_path / "adrs")
        qg_path = generate_quality_gates(feature_id, parsed.tasks, tmp_path / "qg.yaml")
        warnings_path = extract_warnings(parsed.warnings, feature_id, tmp_path / "warnings")
        seed_path = generate_seed_script(feature_id, adr_paths, sample_spec_path, warnings_path, tmp_path / "scripts")

        # Verify feature_id in all outputs
        for adr in adr_paths:
            assert feature_id in adr.read_text()
        assert feature_id in qg_path.read_text()
        if warnings_path:
            assert feature_id in warnings_path.read_text()
        assert feature_id in seed_path.read_text()
```
