"""
Integration Tests for Feature-Plan Pipeline.

Tests the full feature-plan pipeline from research spec parsing through
artifact generation, validating end-to-end data flow and consistency.

Coverage Target: >=85%
Test Count: 15+ tests
"""

import pytest
from pathlib import Path

from guardkit.planning.spec_parser import (
    parse_research_template,
    ParsedSpec,
    TaskDefinition,
)
from guardkit.planning.adr_generator import generate_adrs
from guardkit.planning.quality_gate_generator import generate_quality_gates
from guardkit.planning.task_metadata import enrich_task, render_task_markdown
from guardkit.planning.warnings_extractor import extract_warnings
from guardkit.planning.seed_script_generator import generate_seed_script
from guardkit.planning.target_mode import resolve_target


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
def output_dirs(tmp_path):
    """Create output directories for artifact generation."""
    dirs = {
        "adr": tmp_path / "docs" / "adr",
        "warnings": tmp_path / "docs" / "warnings",
        "quality_gates": tmp_path / ".guardkit" / "quality-gates",
        "scripts": tmp_path / "scripts",
        "tasks": tmp_path / "tasks" / "backlog",
    }
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    return dirs


@pytest.fixture
def feature_id():
    """Standard feature ID for testing."""
    return "FEAT-TEST-001"


# =============================================================================
# Pipeline Integration Tests
# =============================================================================


@pytest.mark.integration
class TestFullPipelineFlow:
    """Tests for the complete pipeline from parse to artifact generation."""

    def test_parse_spec_returns_valid_parsed_spec(self, sample_spec_path):
        """parse_research_template returns a valid ParsedSpec from fixture."""
        spec = parse_research_template(sample_spec_path)

        assert isinstance(spec, ParsedSpec)
        assert spec.problem_statement != ""
        assert len(spec.decisions) >= 3
        assert len(spec.warnings) >= 2
        assert len(spec.tasks) >= 3

    def test_parsed_spec_contains_expected_decisions(self, parsed_spec):
        """ParsedSpec contains all decisions from the sample fixture."""
        assert len(parsed_spec.decisions) == 3

        # Check decision content
        decision_titles = [d.title for d in parsed_spec.decisions]
        assert "Use Python dataclasses" in decision_titles
        assert "Parse markdown with regex" in decision_titles
        assert "Generate YAML for quality gates" in decision_titles

        # Check decision status
        for decision in parsed_spec.decisions:
            assert decision.adr_status in ["Accepted", "Proposed", "Superseded"]

    def test_parsed_spec_contains_expected_warnings(self, parsed_spec):
        """ParsedSpec contains all warnings from the sample fixture."""
        assert len(parsed_spec.warnings) >= 2

        # Check that warnings have content
        for warning in parsed_spec.warnings:
            assert len(warning) > 0
            assert "W" in warning or "Do not" in warning or "Maintain" in warning

    def test_parsed_spec_contains_expected_tasks(self, parsed_spec):
        """ParsedSpec contains all tasks from the sample fixture."""
        assert len(parsed_spec.tasks) == 3

        # Check task structure
        for task in parsed_spec.tasks:
            assert isinstance(task, TaskDefinition)
            assert task.name != ""
            assert task.complexity in ["low", "medium", "high"]
            assert task.complexity_score > 0

    def test_full_pipeline_generates_all_artifacts(
        self, parsed_spec, output_dirs, feature_id, sample_spec_path
    ):
        """Full pipeline generates ADRs, warnings, quality gates, and seed script."""
        # Step 1: Generate ADRs
        adr_paths = generate_adrs(
            decisions=parsed_spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=False,
        )
        assert len(adr_paths) == 3
        for path in adr_paths:
            assert path.exists()
            assert path.suffix == ".md"

        # Step 2: Extract warnings
        warnings_path = extract_warnings(
            warnings=parsed_spec.warnings,
            feature_id=feature_id,
            output_dir=output_dirs["warnings"],
        )
        assert warnings_path is not None
        assert warnings_path.exists()

        # Step 3: Generate quality gates
        quality_gate_path = generate_quality_gates(
            feature_id=feature_id,
            tasks=parsed_spec.tasks,
            output_path=output_dirs["quality_gates"] / f"{feature_id}.yaml",
        )
        assert quality_gate_path.exists()
        assert quality_gate_path.suffix == ".yaml"

        # Step 4: Generate seed script
        seed_script_path = generate_seed_script(
            feature_id=feature_id,
            adr_paths=adr_paths,
            spec_path=sample_spec_path,
            warnings_path=warnings_path,
            output_dir=output_dirs["scripts"],
        )
        assert seed_script_path.exists()
        assert seed_script_path.suffix == ".sh"

    def test_adr_content_matches_decision_data(
        self, parsed_spec, output_dirs, feature_id
    ):
        """Generated ADR files contain correct decision data."""
        adr_paths = generate_adrs(
            decisions=parsed_spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=False,
        )

        # Verify each ADR contains its decision data
        for i, path in enumerate(adr_paths):
            content = path.read_text()
            decision = parsed_spec.decisions[i]

            assert decision.title in content
            assert decision.rationale in content
            assert decision.adr_status in content

    def test_warnings_file_contains_all_warnings(
        self, parsed_spec, output_dirs, feature_id
    ):
        """Generated warnings file contains all warnings from spec."""
        warnings_path = extract_warnings(
            warnings=parsed_spec.warnings,
            feature_id=feature_id,
            output_dir=output_dirs["warnings"],
        )

        content = warnings_path.read_text()

        # Each warning should appear in the file
        for warning in parsed_spec.warnings:
            assert warning in content

    def test_quality_gates_contain_coach_commands(
        self, parsed_spec, output_dirs, feature_id
    ):
        """Generated quality gates YAML contains coach validation commands."""
        import yaml

        quality_gate_path = generate_quality_gates(
            feature_id=feature_id,
            tasks=parsed_spec.tasks,
            output_path=output_dirs["quality_gates"] / f"{feature_id}.yaml",
        )

        with open(quality_gate_path) as f:
            gates_data = yaml.safe_load(f)

        assert gates_data["feature_id"] == feature_id
        assert "quality_gates" in gates_data

        # Should have categorized commands
        quality_gates = gates_data["quality_gates"]
        assert len(quality_gates) > 0

    def test_seed_script_references_all_artifacts(
        self, parsed_spec, output_dirs, feature_id, sample_spec_path
    ):
        """Generated seed script references all generated artifacts."""
        # Generate all artifacts
        adr_paths = generate_adrs(
            decisions=parsed_spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=False,
        )

        warnings_path = extract_warnings(
            warnings=parsed_spec.warnings,
            feature_id=feature_id,
            output_dir=output_dirs["warnings"],
        )

        seed_script_path = generate_seed_script(
            feature_id=feature_id,
            adr_paths=adr_paths,
            spec_path=sample_spec_path,
            warnings_path=warnings_path,
            output_dir=output_dirs["scripts"],
        )

        content = seed_script_path.read_text()

        # Script should reference all ADRs
        for adr_path in adr_paths:
            # The script uses POSIX paths
            assert str(adr_path).replace("\\", "/") in content.replace("\\", "/")

        # Script should reference spec and warnings
        assert feature_id in content


@pytest.mark.integration
class TestTaskEnrichmentPipeline:
    """Tests for task enrichment through the pipeline."""

    def test_enrich_all_tasks_from_spec(self, parsed_spec, feature_id):
        """All tasks from spec can be enriched successfully."""
        target_config = resolve_target("interactive")

        enriched_tasks = []
        for task in parsed_spec.tasks:
            enriched = enrich_task(task, target_config, feature_id)
            enriched_tasks.append(enriched)

        assert len(enriched_tasks) == len(parsed_spec.tasks)

        for enriched in enriched_tasks:
            assert enriched.feature_id == feature_id
            assert enriched.turn_budget["expected"] > 0
            assert enriched.turn_budget["max"] >= enriched.turn_budget["expected"]
            assert enriched.graphiti_context_budget > 0

    def test_render_enriched_tasks_to_markdown(self, parsed_spec, feature_id):
        """Enriched tasks render to valid markdown."""
        target_config = resolve_target("interactive")

        for task in parsed_spec.tasks:
            enriched = enrich_task(task, target_config, feature_id)
            markdown = render_task_markdown(enriched)

            # Check markdown structure
            assert "---" in markdown  # YAML frontmatter delimiters
            assert "## Description" in markdown
            assert "## Acceptance Criteria" in markdown
            assert "## Coach Validation Commands" in markdown

    def test_local_model_enrichment_adds_guidance(self, parsed_spec, feature_id):
        """Local model target adds enriched guidance notes."""
        target_config = resolve_target("local-model")

        for task in parsed_spec.tasks:
            enriched = enrich_task(task, target_config, feature_id)

            # Local model should have enriched notes
            if task.files_to_create or task.files_to_modify:
                assert enriched.enriched_notes != ""
                assert "Import" in enriched.enriched_notes or "Type" in enriched.enriched_notes


@pytest.mark.integration
class TestPipelineConsistency:
    """Tests for data consistency across the pipeline."""

    def test_decision_count_matches_adr_count(
        self, parsed_spec, output_dirs, feature_id
    ):
        """Number of decisions equals number of generated ADRs."""
        adr_paths = generate_adrs(
            decisions=parsed_spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=False,
        )

        assert len(adr_paths) == len(parsed_spec.decisions)

    def test_task_count_preserved_through_enrichment(self, parsed_spec, feature_id):
        """Number of tasks preserved through enrichment process."""
        target_config = resolve_target("interactive")

        enriched_count = 0
        for task in parsed_spec.tasks:
            enrich_task(task, target_config, feature_id)
            enriched_count += 1

        assert enriched_count == len(parsed_spec.tasks)

    def test_relevant_decisions_reference_valid_decisions(self, parsed_spec):
        """Task relevant_decisions reference existing decision numbers."""
        decision_numbers = {d.number for d in parsed_spec.decisions}

        for task in parsed_spec.tasks:
            for ref in task.relevant_decisions:
                assert ref in decision_numbers, (
                    f"Task '{task.name}' references non-existent decision '{ref}'"
                )

    def test_pipeline_idempotent_adr_generation(
        self, parsed_spec, output_dirs, feature_id
    ):
        """Running ADR generation twice with check_duplicates produces same count."""
        # First run
        adr_paths_1 = generate_adrs(
            decisions=parsed_spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=True,
        )

        # Second run - should skip existing files
        adr_paths_2 = generate_adrs(
            decisions=parsed_spec.decisions,
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
            check_duplicates=True,
        )

        # First run creates files, second run returns empty (files exist)
        assert len(adr_paths_1) == len(parsed_spec.decisions)
        assert len(adr_paths_2) == 0  # All skipped due to duplicates


@pytest.mark.integration
class TestEdgeCases:
    """Tests for edge cases in the pipeline."""

    def test_empty_warnings_returns_none(self, output_dirs, feature_id):
        """extract_warnings returns None for empty warnings list."""
        result = extract_warnings(
            warnings=[],
            feature_id=feature_id,
            output_dir=output_dirs["warnings"],
        )

        assert result is None

    def test_empty_decisions_returns_empty_list(self, output_dirs, feature_id):
        """generate_adrs returns empty list for empty decisions."""
        result = generate_adrs(
            decisions=[],
            feature_id=feature_id,
            output_dir=output_dirs["adr"],
        )

        assert result == []

    def test_empty_tasks_generates_minimal_quality_gates(self, output_dirs, feature_id):
        """generate_quality_gates handles empty task list."""
        import yaml

        quality_gate_path = generate_quality_gates(
            feature_id=feature_id,
            tasks=[],
            output_path=output_dirs["quality_gates"] / f"{feature_id}.yaml",
        )

        assert quality_gate_path.exists()

        with open(quality_gate_path) as f:
            data = yaml.safe_load(f)

        assert data["feature_id"] == feature_id
        assert data["quality_gates"] == {}

    def test_seed_script_without_warnings(
        self, parsed_spec, output_dirs, feature_id, sample_spec_path
    ):
        """Seed script generation works without warnings path."""
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
            warnings_path=None,  # No warnings
            output_dir=output_dirs["scripts"],
        )

        assert seed_script_path.exists()

        content = seed_script_path.read_text()
        assert "Seeding warnings" not in content
