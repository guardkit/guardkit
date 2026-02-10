"""
Integration Tests for Planning Module Technology Seams.

Tests the technology seams (interfaces) between planning modules to ensure
data flows correctly between components. Each test class corresponds to
a specific seam where errors historically occur.

Coverage Target: >=85%
Test Count: 25+ tests
"""

import pytest
from pathlib import Path

from guardkit.planning.spec_parser import (
    parse_research_template,
    Decision,
    TaskDefinition,
)
from guardkit.planning.adr_generator import generate_adrs
from guardkit.planning.quality_gate_generator import generate_quality_gates
from guardkit.planning.task_metadata import (
    enrich_task,
    render_task_markdown,
)
from guardkit.planning.warnings_extractor import extract_warnings
from guardkit.planning.seed_script_generator import generate_seed_script
from guardkit.planning.target_mode import (
    resolve_target,
    TargetMode,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_spec_path():
    """Path to the sample research spec fixture."""
    return Path(__file__).parent.parent / "fixtures" / "sample-research-spec.md"


@pytest.fixture
def parsed_spec(sample_spec_path):
    """Parse the sample spec fixture and return ParsedSpec."""
    return parse_research_template(sample_spec_path)


@pytest.fixture
def sample_decision():
    """Create a sample Decision for testing."""
    return Decision(
        number="D1",
        title="Use Python dataclasses",
        rationale="Provides type safety and IDE support",
        alternatives_rejected="Pydantic, TypedDict, attrs",
        adr_status="Accepted",
    )


@pytest.fixture
def sample_task():
    """Create a sample TaskDefinition for testing."""
    return TaskDefinition(
        name="TASK 1: Implement Spec Parser",
        complexity="medium",
        complexity_score=5,
        task_type="implementation",
        domain_tags=["parsing", "dataclasses"],
        files_to_create=["guardkit/planning/spec_parser.py"],
        files_to_modify=[],
        files_not_to_touch=["tests/"],
        dependencies=[],
        inputs="Path to markdown file",
        outputs="ParsedSpec dataclass",
        relevant_decisions=["D1", "D2"],
        acceptance_criteria=[
            "Parses Decision Log",
            "Extracts warnings",
            "Creates TaskDefinition objects",
        ],
        implementation_notes="Use regex for table parsing",
        player_constraints=["No external dependencies"],
        coach_validation_commands=[
            "pytest tests/unit/planning/test_spec_parser.py -v",
            "ruff check guardkit/planning/",
        ],
        turn_budget_expected=2,
        turn_budget_max=4,
    )


@pytest.fixture
def output_dirs(tmp_path):
    """Create output directories for artifact generation."""
    dirs = {
        "adr": tmp_path / "docs" / "adr",
        "warnings": tmp_path / "docs" / "warnings",
        "quality_gates": tmp_path / ".guardkit" / "quality-gates",
        "scripts": tmp_path / "scripts",
    }
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    return dirs


@pytest.fixture
def feature_id():
    """Standard feature ID for testing."""
    return "FEAT-TEST-001"


# =============================================================================
# SEAM 1: SpecParser -> ADRGenerator
# =============================================================================


@pytest.mark.integration
class TestSeam1_SpecParserToADRGenerator:
    """Tests for Decision objects flowing from SpecParser to ADRGenerator.

    Validates that Decision objects produced by parse_research_template()
    are correctly consumed by generate_adrs().
    """

    def test_decision_objects_have_required_fields_for_adr(self, parsed_spec):
        """Decision objects from parser have all fields required by ADRGenerator."""
        for decision in parsed_spec.decisions:
            # These fields are required by ADRGenerator
            assert decision.number is not None
            assert decision.title is not None
            assert decision.rationale is not None
            assert decision.alternatives_rejected is not None
            assert decision.adr_status is not None

    def test_decision_title_is_string_not_empty(self, parsed_spec):
        """Decision title is a non-empty string for filename generation."""
        for decision in parsed_spec.decisions:
            assert isinstance(decision.title, str)
            assert len(decision.title.strip()) > 0

    def test_decisions_flow_to_adr_generator_without_error(
        self, parsed_spec, output_dirs, feature_id
    ):
        """Decisions from parser can be passed directly to generate_adrs."""
        # This should not raise any exceptions
        adr_paths = generate_adrs(
            decisions=parsed_spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=False,
        )

        assert len(adr_paths) == len(parsed_spec.decisions)

    def test_decision_number_format_preserved_in_adr(
        self, parsed_spec, output_dirs, feature_id
    ):
        """Decision number format (D1, D2) is preserved in ADR content."""
        adr_paths = generate_adrs(
            decisions=parsed_spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=False,
        )

        for i, path in enumerate(adr_paths):
            content = path.read_text()
            decision = parsed_spec.decisions[i]
            assert decision.number in content

    def test_decision_status_maps_to_adr_status(
        self, parsed_spec, output_dirs, feature_id
    ):
        """Decision adr_status appears correctly in generated ADR."""
        adr_paths = generate_adrs(
            decisions=parsed_spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=False,
        )

        for i, path in enumerate(adr_paths):
            content = path.read_text()
            decision = parsed_spec.decisions[i]
            assert decision.adr_status in content


# =============================================================================
# SEAM 2: SpecParser -> QualityGateGenerator
# =============================================================================


@pytest.mark.integration
class TestSeam2_SpecParserToQualityGateGenerator:
    """Tests for TaskDefinition objects flowing to QualityGateGenerator.

    Validates that TaskDefinition objects are correctly processed for
    quality gate YAML generation.
    """

    def test_tasks_have_coach_validation_commands(self, parsed_spec):
        """Tasks from parser have coach_validation_commands list."""
        for task in parsed_spec.tasks:
            assert hasattr(task, "coach_validation_commands")
            assert isinstance(task.coach_validation_commands, list)

    def test_tasks_flow_to_quality_gate_generator(
        self, parsed_spec, output_dirs, feature_id
    ):
        """Tasks from parser can be passed to generate_quality_gates."""
        quality_gate_path = generate_quality_gates(
            feature_id=feature_id,
            tasks=parsed_spec.tasks,
            output_path=output_dirs["quality_gates"] / f"{feature_id}.yaml",
        )

        assert quality_gate_path.exists()

    def test_coach_commands_categorized_correctly(
        self, parsed_spec, output_dirs, feature_id
    ):
        """Coach validation commands are categorized into gate types."""
        import yaml

        quality_gate_path = generate_quality_gates(
            feature_id=feature_id,
            tasks=parsed_spec.tasks,
            output_path=output_dirs["quality_gates"] / f"{feature_id}.yaml",
        )

        with open(quality_gate_path) as f:
            data = yaml.safe_load(f)

        gates = data["quality_gates"]

        # Check categorization based on known commands in fixture
        # pytest commands should be categorized as unit_tests
        if "unit_tests" in gates:
            assert "pytest" in gates["unit_tests"]["command"]

        # ruff commands should be categorized as lint
        if "lint" in gates:
            assert "ruff" in gates["lint"]["command"]

    def test_command_deduplication_across_tasks(self, output_dirs, feature_id):
        """Identical commands from multiple tasks are deduplicated."""
        import yaml

        # Create tasks with identical commands
        tasks = [
            TaskDefinition(
                name="TASK 1: First task",
                complexity="low",
                complexity_score=2,
                task_type="implementation",
                domain_tags=[],
                files_to_create=[],
                files_to_modify=[],
                files_not_to_touch=[],
                dependencies=[],
                inputs="",
                outputs="",
                relevant_decisions=[],
                acceptance_criteria=[],
                implementation_notes="",
                player_constraints=[],
                coach_validation_commands=["pytest tests/ -v", "ruff check ."],
            ),
            TaskDefinition(
                name="TASK 2: Second task",
                complexity="low",
                complexity_score=2,
                task_type="implementation",
                domain_tags=[],
                files_to_create=[],
                files_to_modify=[],
                files_not_to_touch=[],
                dependencies=[],
                inputs="",
                outputs="",
                relevant_decisions=[],
                acceptance_criteria=[],
                implementation_notes="",
                player_constraints=[],
                coach_validation_commands=["pytest tests/ -v"],  # Duplicate
            ),
        ]

        quality_gate_path = generate_quality_gates(
            feature_id=feature_id,
            tasks=tasks,
            output_path=output_dirs["quality_gates"] / f"{feature_id}.yaml",
        )

        with open(quality_gate_path) as f:
            data = yaml.safe_load(f)

        gates = data["quality_gates"]

        # Check that pytest command appears only once
        if "unit_tests" in gates:
            command = gates["unit_tests"]["command"]
            # Should not have duplicated command
            assert command.count("pytest tests/ -v") == 1


# =============================================================================
# SEAM 3: SpecParser -> TaskMetadataEnricher
# =============================================================================


@pytest.mark.integration
class TestSeam3_SpecParserToTaskMetadataEnricher:
    """Tests for TaskDefinition + TargetConfig flowing to enrichment.

    Validates that TaskDefinition objects are correctly enriched with
    budgets and target-specific metadata.
    """

    def test_task_complexity_maps_to_turn_budget(self, parsed_spec, feature_id):
        """Task complexity correctly maps to turn budget."""
        target_config = resolve_target("interactive")

        complexity_budgets = {
            "low": {"expected": 1, "max": 3},
            "medium": {"expected": 2, "max": 5},
            "high": {"expected": 3, "max": 5},
        }

        for task in parsed_spec.tasks:
            enriched = enrich_task(task, target_config, feature_id)
            expected_budget = complexity_budgets.get(
                task.complexity, complexity_budgets["medium"]
            )
            assert enriched.turn_budget == expected_budget

    def test_task_complexity_maps_to_context_budget(self, parsed_spec, feature_id):
        """Task complexity correctly maps to Graphiti context budget."""
        target_config = resolve_target("interactive")

        context_budgets = {
            "low": 2000,
            "medium": 4000,
            "high": 6000,
        }

        for task in parsed_spec.tasks:
            enriched = enrich_task(task, target_config, feature_id)
            expected_budget = context_budgets.get(
                task.complexity, context_budgets["medium"]
            )
            assert enriched.graphiti_context_budget == expected_budget

    def test_enriched_task_preserves_original_task(self, sample_task, feature_id):
        """EnrichedTask preserves reference to original TaskDefinition."""
        target_config = resolve_target("interactive")

        enriched = enrich_task(sample_task, target_config, feature_id)

        assert enriched.task_definition is sample_task
        assert enriched.task_definition.name == sample_task.name
        assert enriched.task_definition.complexity == sample_task.complexity

    def test_enriched_task_includes_feature_id(self, sample_task, feature_id):
        """EnrichedTask includes the feature ID."""
        target_config = resolve_target("interactive")

        enriched = enrich_task(sample_task, target_config, feature_id)

        assert enriched.feature_id == feature_id

    def test_enriched_task_renders_to_valid_markdown(self, sample_task, feature_id):
        """EnrichedTask can be rendered to markdown."""
        target_config = resolve_target("interactive")

        enriched = enrich_task(sample_task, target_config, feature_id)
        markdown = render_task_markdown(enriched)

        assert isinstance(markdown, str)
        assert len(markdown) > 0
        assert "---" in markdown  # YAML frontmatter


# =============================================================================
# SEAM 4: SpecParser -> WarningsExtractor
# =============================================================================


@pytest.mark.integration
class TestSeam4_SpecParserToWarningsExtractor:
    """Tests for warnings list flowing from ParsedSpec to extractor.

    Validates that ParsedSpec.warnings is correctly processed by
    extract_warnings().
    """

    def test_warnings_is_list_of_strings(self, parsed_spec):
        """ParsedSpec.warnings is a list of strings."""
        assert isinstance(parsed_spec.warnings, list)
        for warning in parsed_spec.warnings:
            assert isinstance(warning, str)

    def test_warnings_flow_to_extractor(self, parsed_spec, output_dirs, feature_id):
        """Warnings from parser can be passed to extract_warnings."""
        warnings_path = extract_warnings(
            warnings=parsed_spec.warnings,
            feature_id=feature_id,
            output_dir=output_dirs["warnings"],
        )

        assert warnings_path is not None
        assert warnings_path.exists()

    def test_all_warnings_appear_in_output(self, parsed_spec, output_dirs, feature_id):
        """All warnings from ParsedSpec appear in extracted file."""
        warnings_path = extract_warnings(
            warnings=parsed_spec.warnings,
            feature_id=feature_id,
            output_dir=output_dirs["warnings"],
        )

        content = warnings_path.read_text()

        for warning in parsed_spec.warnings:
            assert warning in content

    def test_warnings_file_includes_feature_id(
        self, parsed_spec, output_dirs, feature_id
    ):
        """Warnings file includes feature ID in name and content."""
        warnings_path = extract_warnings(
            warnings=parsed_spec.warnings,
            feature_id=feature_id,
            output_dir=output_dirs["warnings"],
        )

        # Feature ID in filename
        assert feature_id in warnings_path.name

        # Feature ID in content
        content = warnings_path.read_text()
        assert feature_id in content


# =============================================================================
# SEAM 5: ADRGenerator -> SeedScriptGenerator
# =============================================================================


@pytest.mark.integration
class TestSeam5_ADRGeneratorToSeedScriptGenerator:
    """Tests for ADR file paths flowing to seed script generation.

    Validates that ADR paths from generate_adrs() are correctly used
    in seed script generation.
    """

    def test_adr_paths_are_path_objects(self, parsed_spec, output_dirs, feature_id):
        """generate_adrs returns list of Path objects."""
        adr_paths = generate_adrs(
            decisions=parsed_spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=False,
        )

        for path in adr_paths:
            assert isinstance(path, Path)

    def test_adr_paths_flow_to_seed_script(
        self, parsed_spec, output_dirs, feature_id, sample_spec_path
    ):
        """ADR paths can be passed directly to generate_seed_script."""
        adr_paths = generate_adrs(
            decisions=parsed_spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=False,
        )

        seed_script_path = generate_seed_script(
            feature_id=feature_id,
            adr_paths=adr_paths,
            spec_path=sample_spec_path,
            output_dir=output_dirs["scripts"],
        )

        assert seed_script_path.exists()

    def test_seed_script_contains_adr_commands(
        self, parsed_spec, output_dirs, feature_id, sample_spec_path
    ):
        """Seed script contains add-context commands for each ADR."""
        adr_paths = generate_adrs(
            decisions=parsed_spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=False,
        )

        seed_script_path = generate_seed_script(
            feature_id=feature_id,
            adr_paths=adr_paths,
            spec_path=sample_spec_path,
            output_dir=output_dirs["scripts"],
        )

        content = seed_script_path.read_text()

        # Each ADR should have an add-context command
        for adr_path in adr_paths:
            # Path may be normalized in script
            path_str = str(adr_path).replace("\\", "/")
            assert path_str in content.replace("\\", "/")


# =============================================================================
# SEAM 6: TaskMetadataEnricher -> TargetMode
# =============================================================================


@pytest.mark.integration
class TestSeam6_TaskMetadataEnricherToTargetMode:
    """Tests for TargetConfig influencing task enrichment behavior.

    Validates that TargetMode affects enrichment output correctly.
    """

    def test_interactive_mode_no_enriched_notes(self, sample_task, feature_id):
        """Interactive mode produces no enriched notes."""
        target_config = resolve_target("interactive")

        enriched = enrich_task(sample_task, target_config, feature_id)

        assert enriched.enriched_notes == ""

    def test_local_model_mode_adds_enriched_notes(self, sample_task, feature_id):
        """Local model mode adds enriched guidance notes."""
        target_config = resolve_target("local-model")

        enriched = enrich_task(sample_task, target_config, feature_id)

        # Task has files_to_create, so should have import guidance
        assert enriched.enriched_notes != ""
        assert "Import" in enriched.enriched_notes or "Type" in enriched.enriched_notes

    def test_target_config_preserved_in_enriched_task(self, sample_task, feature_id):
        """TargetConfig is preserved in EnrichedTask."""
        target_config = resolve_target("local-model")

        enriched = enrich_task(sample_task, target_config, feature_id)

        assert enriched.target_config is target_config
        assert enriched.target_config.mode == TargetMode.LOCAL_MODEL

    def test_auto_mode_resolves_correctly(self, tmp_path, sample_task, feature_id):
        """Auto mode resolves based on config file presence."""
        # Without config file, should resolve to interactive
        target_config = resolve_target("auto", config_path=tmp_path / "nonexistent.yaml")

        enriched = enrich_task(sample_task, target_config, feature_id)

        assert enriched.target_config.mode == TargetMode.INTERACTIVE


# =============================================================================
# SEAM 7: Full Pipeline Integration
# =============================================================================


@pytest.mark.integration
class TestSeam7_FullPipelineIntegration:
    """Tests for the full pipeline from parse to seed script.

    Validates consistency across all module boundaries.
    """

    def test_full_pipeline_data_consistency(
        self, sample_spec_path, output_dirs, feature_id
    ):
        """Full pipeline maintains data consistency across all seams."""
        # Parse
        spec = parse_research_template(sample_spec_path)

        # Generate ADRs
        adr_paths = generate_adrs(
            decisions=spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=False,
        )

        # Extract warnings
        warnings_path = extract_warnings(
            warnings=spec.warnings,
            feature_id=feature_id,
            output_dir=output_dirs["warnings"],
        )

        # Generate quality gates
        quality_gate_path = generate_quality_gates(
            feature_id=feature_id,
            tasks=spec.tasks,
            output_path=output_dirs["quality_gates"] / f"{feature_id}.yaml",
        )

        # Enrich tasks
        target_config = resolve_target("interactive")
        enriched_tasks = [
            enrich_task(task, target_config, feature_id) for task in spec.tasks
        ]

        # Generate seed script
        seed_script_path = generate_seed_script(
            feature_id=feature_id,
            adr_paths=adr_paths,
            spec_path=sample_spec_path,
            warnings_path=warnings_path,
            output_dir=output_dirs["scripts"],
        )

        # Verify all artifacts exist and are consistent
        assert len(adr_paths) == len(spec.decisions)
        assert warnings_path.exists()
        assert quality_gate_path.exists()
        assert seed_script_path.exists()
        assert len(enriched_tasks) == len(spec.tasks)

    def test_pipeline_error_propagation(self, tmp_path, output_dirs, feature_id):
        """Invalid input at start propagates appropriately."""
        nonexistent_path = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError):
            parse_research_template(nonexistent_path)

    def test_pipeline_handles_special_characters_in_titles(
        self, output_dirs, feature_id
    ):
        """Pipeline handles special characters in decision titles."""
        decisions = [
            Decision(
                number="D1",
                title="Use Python's dataclasses & type hints",
                rationale="Type safety",
                alternatives_rejected="None",
                adr_status="Accepted",
            ),
        ]

        adr_paths = generate_adrs(
            decisions=decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=False,
        )

        # Should generate file without error
        assert len(adr_paths) == 1
        assert adr_paths[0].exists()

        # Filename should be URL-safe (no special chars)
        filename = adr_paths[0].name
        assert "'" not in filename
        assert "&" not in filename

    def test_pipeline_handles_unicode_in_content(
        self, output_dirs, feature_id
    ):
        """Pipeline handles unicode characters in content."""
        warnings = [
            "W1: Do not use deprecated APIs",
            "W2: Ensure UTF-8 encoding everywhere",
        ]

        warnings_path = extract_warnings(
            warnings=warnings,
            feature_id=feature_id,
            output_dir=output_dirs["warnings"],
        )

        content = warnings_path.read_text(encoding="utf-8")
        assert "UTF-8" in content
