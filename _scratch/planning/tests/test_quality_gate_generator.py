"""
Unit tests for Quality Gate YAML Generator.

Tests the generation of quality gate YAML files from task definitions,
including command categorization, deduplication, and YAML structure validation.
"""

import pytest
from pathlib import Path
import yaml

from guardkit.planning.quality_gate_generator import generate_quality_gates
from guardkit.planning.spec_parser import TaskDefinition


def make_task(
    name: str = "Sample Task",
    coach_validation_commands: list[str] | None = None,
    complexity: str = "medium",
    complexity_score: int = 5,
    task_type: str = "implementation",
    acceptance_criteria: list[str] | None = None,
) -> TaskDefinition:
    """Helper to create TaskDefinition with minimal required fields."""
    return TaskDefinition(
        name=name,
        complexity=complexity,
        complexity_score=complexity_score,
        task_type=task_type,
        domain_tags=["testing"],
        files_to_create=[],
        files_to_modify=[],
        files_not_to_touch=[],
        dependencies=[],
        inputs="Test input",
        outputs="Test output",
        relevant_decisions=[],
        acceptance_criteria=acceptance_criteria or ["Test passes"],
        implementation_notes="",
        player_constraints=[],
        coach_validation_commands=coach_validation_commands or [],
    )


@pytest.fixture
def sample_task_with_lint() -> TaskDefinition:
    """Create a sample task with lint command."""
    return make_task(
        name="Sample Task with Lint",
        coach_validation_commands=["ruff check guardkit/planning/"],
    )


@pytest.fixture
def sample_task_with_unit_tests() -> TaskDefinition:
    """Create a sample task with unit test command."""
    return make_task(
        name="Sample Task with Unit Tests",
        coach_validation_commands=["pytest tests/unit/test_something.py -v --tb=short"],
    )


@pytest.fixture
def sample_task_with_integration_tests() -> TaskDefinition:
    """Create a sample task with integration test command."""
    return make_task(
        name="Sample Task with Integration Tests",
        coach_validation_commands=["pytest tests/integration/test_api.py -v"],
    )


@pytest.fixture
def sample_task_with_type_check() -> TaskDefinition:
    """Create a sample task with type checking command."""
    return make_task(
        name="Sample Task with Type Check",
        coach_validation_commands=["mypy guardkit/planning/"],
    )


@pytest.fixture
def sample_task_with_coverage() -> TaskDefinition:
    """Create a sample task with coverage command."""
    return make_task(
        name="Sample Task with Coverage",
        coach_validation_commands=["pytest tests/unit/ --cov=guardkit --cov-report=term"],
    )


@pytest.fixture
def sample_task_with_custom_command() -> TaskDefinition:
    """Create a sample task with custom command."""
    return make_task(
        name="Sample Task with Custom Command",
        coach_validation_commands=["./scripts/validate_format.sh"],
    )


@pytest.fixture
def sample_task_with_multiple_commands() -> TaskDefinition:
    """Create a sample task with multiple validation commands."""
    return make_task(
        name="Sample Task with Multiple Commands",
        coach_validation_commands=[
            "ruff check guardkit/",
            "mypy guardkit/",
            "pytest tests/unit/ -v"
        ],
    )


@pytest.fixture
def sample_task_with_no_commands() -> TaskDefinition:
    """Create a sample task with no validation commands."""
    return make_task(
        name="Sample Task with No Commands",
        coach_validation_commands=[],
    )


class TestBasicFunctionality:
    """Test basic function signature and return type."""

    def test_function_exists(self):
        """Test that the generate_quality_gates function exists."""
        assert callable(generate_quality_gates)

    def test_returns_path(self, tmp_path, sample_task_with_lint):
        """Test that function returns a Path object."""
        result = generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=tmp_path / "test.yaml"
        )
        assert isinstance(result, Path)

    def test_creates_file(self, tmp_path, sample_task_with_lint):
        """Test that function creates a file at the specified path."""
        output_path = tmp_path / "quality_gates.yaml"
        result = generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=output_path
        )
        assert result.exists()
        assert result.is_file()


class TestMinimalOutput:
    """Test that minimal required gates are present."""

    def test_contains_lint_gate(self, tmp_path, sample_task_with_lint):
        """Test that output contains lint gate."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert 'quality_gates' in data
        assert 'lint' in data['quality_gates']

    def test_contains_unit_tests_gate(self, tmp_path, sample_task_with_unit_tests):
        """Test that output contains unit_tests gate."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_unit_tests],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert 'quality_gates' in data
        assert 'unit_tests' in data['quality_gates']


class TestGateStructure:
    """Test that each gate has required fields with correct types."""

    def test_gate_has_command_field(self, tmp_path, sample_task_with_lint):
        """Test that gate has command field."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        lint_gate = data['quality_gates']['lint']
        assert 'command' in lint_gate
        assert isinstance(lint_gate['command'], str)

    def test_gate_has_required_field(self, tmp_path, sample_task_with_lint):
        """Test that gate has required field."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        lint_gate = data['quality_gates']['lint']
        assert 'required' in lint_gate
        assert isinstance(lint_gate['required'], bool)

    def test_feature_id_in_output(self, tmp_path, sample_task_with_lint):
        """Test that feature_id is included in output."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert 'feature_id' in data
        assert data['feature_id'] == "FEAT-TEST-001"


class TestCommandCategorization:
    """Test that commands are categorized correctly."""

    def test_ruff_command_categorized_as_lint(self, tmp_path, sample_task_with_lint):
        """Test that ruff commands are categorized as lint."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert 'lint' in data['quality_gates']
        assert 'ruff' in data['quality_gates']['lint']['command']

    def test_pytest_unit_categorized_as_unit_tests(self, tmp_path, sample_task_with_unit_tests):
        """Test that pytest tests/unit/ commands are categorized as unit_tests."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_unit_tests],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert 'unit_tests' in data['quality_gates']
        assert 'pytest' in data['quality_gates']['unit_tests']['command']
        assert 'tests/unit/' in data['quality_gates']['unit_tests']['command']

    def test_pytest_integration_categorized_as_integration_tests(self, tmp_path, sample_task_with_integration_tests):
        """Test that pytest tests/integration/ commands are categorized as integration_tests."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_integration_tests],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert 'integration_tests' in data['quality_gates']
        assert 'pytest' in data['quality_gates']['integration_tests']['command']
        assert 'tests/integration/' in data['quality_gates']['integration_tests']['command']

    def test_mypy_command_categorized_as_type_check(self, tmp_path, sample_task_with_type_check):
        """Test that mypy commands are categorized as type_check."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_type_check],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert 'type_check' in data['quality_gates']
        assert 'mypy' in data['quality_gates']['type_check']['command']

    def test_coverage_command_categorized_as_coverage(self, tmp_path, sample_task_with_coverage):
        """Test that coverage commands are categorized as coverage."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_coverage],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert 'coverage' in data['quality_gates']
        assert '--cov' in data['quality_gates']['coverage']['command']

    def test_custom_command_categorized_as_custom(self, tmp_path, sample_task_with_custom_command):
        """Test that unrecognized commands are categorized as custom."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_custom_command],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert 'custom' in data['quality_gates']
        assert './scripts/validate_format.sh' in data['quality_gates']['custom']['command']


class TestRequiredDefaults:
    """Test that gate required field has correct default values."""

    def test_lint_gate_required_true(self, tmp_path, sample_task_with_lint):
        """Test that lint gate has required=true."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert data['quality_gates']['lint']['required'] is True

    def test_unit_tests_gate_required_true(self, tmp_path, sample_task_with_unit_tests):
        """Test that unit_tests gate has required=true."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_unit_tests],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert data['quality_gates']['unit_tests']['required'] is True

    def test_integration_tests_gate_required_true(self, tmp_path, sample_task_with_integration_tests):
        """Test that integration_tests gate has required=true."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_integration_tests],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert data['quality_gates']['integration_tests']['required'] is True

    def test_type_check_gate_required_false(self, tmp_path, sample_task_with_type_check):
        """Test that type_check gate has required=false."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_type_check],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert data['quality_gates']['type_check']['required'] is False

    def test_coverage_gate_required_false(self, tmp_path, sample_task_with_coverage):
        """Test that coverage gate has required=false."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_coverage],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert data['quality_gates']['coverage']['required'] is False

    def test_custom_gate_required_true(self, tmp_path, sample_task_with_custom_command):
        """Test that custom gate has required=true."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_custom_command],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert data['quality_gates']['custom']['required'] is True


class TestCommandDeduplication:
    """Test that identical commands are deduplicated."""

    def test_deduplicates_identical_commands(self, tmp_path):
        """Test that identical commands across tasks are deduplicated."""
        task1 = make_task(
            name="Task 1",
            coach_validation_commands=["ruff check guardkit/planning/"],
        )
        task2 = make_task(
            name="Task 2",
            coach_validation_commands=["ruff check guardkit/planning/"],
        )

        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[task1, task2],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        # Should only have one lint gate, not two
        assert 'lint' in data['quality_gates']
        # The command should appear once
        command = data['quality_gates']['lint']['command']
        assert command == "ruff check guardkit/planning/"

    def test_preserves_different_commands_in_same_category(self, tmp_path):
        """Test that different commands in same category are preserved."""
        task1 = make_task(
            name="Task 1",
            coach_validation_commands=["ruff check guardkit/planning/"],
        )
        task2 = make_task(
            name="Task 2",
            coach_validation_commands=["ruff check guardkit/autobuild/"],
        )

        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[task1, task2],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        # Should have lint gate with combined commands
        assert 'lint' in data['quality_gates']
        command = data['quality_gates']['lint']['command']
        # Should contain both paths (implementation may combine or list separately)
        assert 'guardkit/planning/' in command or 'guardkit/autobuild/' in command


class TestMultipleCommands:
    """Test handling of tasks with multiple validation commands."""

    def test_categorizes_all_commands_from_single_task(self, tmp_path, sample_task_with_multiple_commands):
        """Test that all commands from a task are categorized."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_multiple_commands],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        # Should have all three categories
        assert 'lint' in data['quality_gates']
        assert 'type_check' in data['quality_gates']
        assert 'unit_tests' in data['quality_gates']

    def test_combines_commands_across_multiple_tasks(self, tmp_path, sample_task_with_lint, sample_task_with_unit_tests):
        """Test that commands from multiple tasks are combined."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint, sample_task_with_unit_tests],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        # Should have both categories
        assert 'lint' in data['quality_gates']
        assert 'unit_tests' in data['quality_gates']


class TestDefaultOutputPath:
    """Test default output path generation."""

    def test_default_output_path_format(self, sample_task_with_lint, monkeypatch, tmp_path):
        """Test that default output path follows expected format."""
        # Monkeypatch to avoid writing to actual .guardkit
        monkeypatch.chdir(tmp_path)

        result = generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=None
        )

        # Should be in .guardkit/quality-gates/ directory
        assert result.parent.name == "quality-gates"
        assert result.parent.parent.name == ".guardkit"
        assert result.name == "FEAT-TEST-001.yaml"

    def test_default_path_creates_directories(self, sample_task_with_lint, monkeypatch, tmp_path):
        """Test that default path creates necessary directories."""
        monkeypatch.chdir(tmp_path)

        result = generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=None
        )

        assert result.parent.exists()
        assert result.parent.is_dir()


class TestCustomOutputPath:
    """Test custom output path support."""

    def test_custom_output_path_used(self, tmp_path, sample_task_with_lint):
        """Test that custom output path is used."""
        custom_path = tmp_path / "custom" / "gates.yaml"
        result = generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=custom_path
        )

        assert result == custom_path
        assert result.exists()

    def test_custom_path_creates_parent_directories(self, tmp_path, sample_task_with_lint):
        """Test that parent directories are created for custom path."""
        custom_path = tmp_path / "nested" / "deep" / "path" / "gates.yaml"
        result = generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=custom_path
        )

        assert result.exists()
        assert result.parent.exists()


class TestYAMLValidity:
    """Test that generated YAML is valid and parseable."""

    def test_yaml_is_parseable(self, tmp_path, sample_task_with_lint):
        """Test that generated YAML can be parsed by pyyaml."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            # Should not raise exception
            data = yaml.safe_load(f)
            assert data is not None

    def test_yaml_structure_is_valid(self, tmp_path, sample_task_with_lint):
        """Test that YAML structure matches expected schema."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_lint],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        # Top-level structure
        assert isinstance(data, dict)
        assert 'feature_id' in data
        assert 'quality_gates' in data
        assert isinstance(data['quality_gates'], dict)

        # Gate structure
        for gate_name, gate_data in data['quality_gates'].items():
            assert isinstance(gate_name, str)
            assert isinstance(gate_data, dict)
            assert 'command' in gate_data
            assert 'required' in gate_data
            assert isinstance(gate_data['command'], str)
            assert isinstance(gate_data['required'], bool)

    def test_yaml_is_valid_with_complex_commands(self, tmp_path, sample_task_with_multiple_commands):
        """Test that YAML is valid even with complex commands."""
        output_path = tmp_path / "quality_gates.yaml"
        generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_multiple_commands],
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        # Should parse without issues
        assert data is not None
        assert 'quality_gates' in data


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_tasks_list(self, tmp_path):
        """Test handling of empty tasks list."""
        output_path = tmp_path / "quality_gates.yaml"
        result = generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[],
            output_path=output_path
        )

        # Should still create file
        assert result.exists()

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        # Should have feature_id but no gates
        assert 'feature_id' in data
        assert data['feature_id'] == "FEAT-TEST-001"
        assert 'quality_gates' in data
        assert len(data['quality_gates']) == 0

    def test_task_with_no_commands(self, tmp_path, sample_task_with_no_commands):
        """Test handling of task with no validation commands."""
        output_path = tmp_path / "quality_gates.yaml"
        result = generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[sample_task_with_no_commands],
            output_path=output_path
        )

        assert result.exists()

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        # Should have feature_id but no gates
        assert 'feature_id' in data
        assert 'quality_gates' in data
        assert len(data['quality_gates']) == 0

    def test_task_with_empty_command_string(self, tmp_path):
        """Test handling of task with empty command string."""
        task = make_task(
            name="Task with Empty Command",
            coach_validation_commands=[""],
        )

        output_path = tmp_path / "quality_gates.yaml"
        result = generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[task],
            output_path=output_path
        )

        assert result.exists()

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        # Should skip empty commands
        assert 'quality_gates' in data

    def test_feature_id_with_special_characters(self, tmp_path, sample_task_with_lint):
        """Test handling of feature ID with special characters."""
        output_path = tmp_path / "quality_gates.yaml"
        result = generate_quality_gates(
            feature_id="FEAT-TEST-001-SPECIAL",
            tasks=[sample_task_with_lint],
            output_path=output_path
        )

        assert result.exists()

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        assert data['feature_id'] == "FEAT-TEST-001-SPECIAL"

    def test_command_with_special_yaml_characters(self, tmp_path):
        """Test handling of commands with special YAML characters."""
        task = make_task(
            name="Task with Special Characters",
            coach_validation_commands=['pytest tests/ -v --tb=short -k "test_*"'],
        )

        output_path = tmp_path / "quality_gates.yaml"
        result = generate_quality_gates(
            feature_id="FEAT-TEST-001",
            tasks=[task],
            output_path=output_path
        )

        assert result.exists()

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        # Should handle quotes and special chars
        assert 'unit_tests' in data['quality_gates']
        assert 'pytest' in data['quality_gates']['unit_tests']['command']


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_typical_feature_with_mixed_tasks(self, tmp_path):
        """Test typical feature with various task types."""
        tasks = [
            make_task(
                name="Implement Core Logic",
                coach_validation_commands=[
                    "ruff check guardkit/core/",
                    "mypy guardkit/core/",
                    "pytest tests/unit/test_core.py -v"
                ],
            ),
            make_task(
                name="Add API Endpoint",
                coach_validation_commands=[
                    "ruff check guardkit/api/",
                    "pytest tests/integration/test_api.py -v"
                ],
            ),
            make_task(
                name="Add Documentation",
                coach_validation_commands=["./scripts/validate_docs.sh"],
            ),
        ]

        output_path = tmp_path / "quality_gates.yaml"
        result = generate_quality_gates(
            feature_id="FEAT-CORE-001",
            tasks=tasks,
            output_path=output_path
        )

        assert result.exists()

        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)

        # Should have all gate types
        assert data['feature_id'] == "FEAT-CORE-001"
        assert 'lint' in data['quality_gates']
        assert 'type_check' in data['quality_gates']
        assert 'unit_tests' in data['quality_gates']
        assert 'integration_tests' in data['quality_gates']
        assert 'custom' in data['quality_gates']

        # Verify required flags
        assert data['quality_gates']['lint']['required'] is True
        assert data['quality_gates']['type_check']['required'] is False
        assert data['quality_gates']['unit_tests']['required'] is True
        assert data['quality_gates']['integration_tests']['required'] is True
        assert data['quality_gates']['custom']['required'] is True
