"""
Unit tests for Feature CLI commands (guardkit feature validate).

Test Coverage:
- Valid feature: success output, exit code 0
- Invalid feature (schema): error output, exit code 1
- Structural errors: error output, exit code 1
- Missing feature: error output, exit code 2
- YAML parse error: error output, exit code 2
- --json flag: JSON output format
- Help text display
- Registration in main CLI

Coverage Target: >=85%
"""

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from guardkit.cli.feature import feature, validate
from guardkit.cli.main import cli


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def runner():
    """Provide a Click CliRunner."""
    return CliRunner()


@pytest.fixture
def valid_feature_dir(tmp_path):
    """Create temp dir with valid feature YAML and task files."""
    features_dir = tmp_path / ".guardkit" / "features"
    features_dir.mkdir(parents=True)

    # Create task files
    tasks_dir = tmp_path / "tasks" / "backlog"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "TASK-001.md").write_text("# Task 001\nSample task.")
    (tasks_dir / "TASK-002.md").write_text("# Task 002\nSample task.")

    # Create valid feature YAML
    feature_data = {
        "id": "FEAT-TEST",
        "name": "Test Feature",
        "description": "A test feature for validation",
        "status": "planned",
        "tasks": [
            {
                "id": "TASK-001",
                "name": "Task 1",
                "file_path": "tasks/backlog/TASK-001.md",
            },
            {
                "id": "TASK-002",
                "name": "Task 2",
                "file_path": "tasks/backlog/TASK-002.md",
                "dependencies": ["TASK-001"],
            },
        ],
        "orchestration": {
            "parallel_groups": [["TASK-001"], ["TASK-002"]],
        },
    }
    with open(features_dir / "FEAT-TEST.yaml", "w") as f:
        yaml.dump(feature_data, f)

    return tmp_path


@pytest.fixture
def invalid_status_feature_dir(tmp_path):
    """Create temp dir with feature YAML that has invalid status."""
    features_dir = tmp_path / ".guardkit" / "features"
    features_dir.mkdir(parents=True)

    feature_data = {
        "id": "FEAT-BAD",
        "name": "Bad Feature",
        "status": "invalid_status",
        "tasks": [],
    }
    with open(features_dir / "FEAT-BAD.yaml", "w") as f:
        yaml.dump(feature_data, f)

    return tmp_path


@pytest.fixture
def missing_field_feature_dir(tmp_path):
    """Create temp dir with feature YAML missing required 'name' field."""
    features_dir = tmp_path / ".guardkit" / "features"
    features_dir.mkdir(parents=True)

    feature_data = {
        "id": "FEAT-NONAME",
        "status": "planned",
        "tasks": [],
    }
    with open(features_dir / "FEAT-NONAME.yaml", "w") as f:
        yaml.dump(feature_data, f)

    return tmp_path


@pytest.fixture
def missing_task_file_dir(tmp_path):
    """Create temp dir with feature YAML referencing non-existent task file."""
    features_dir = tmp_path / ".guardkit" / "features"
    features_dir.mkdir(parents=True)

    feature_data = {
        "id": "FEAT-MISSING",
        "name": "Missing Task Files",
        "status": "planned",
        "tasks": [
            {
                "id": "TASK-GHOST",
                "name": "Ghost Task",
                "file_path": "tasks/backlog/TASK-GHOST.md",
            },
        ],
        "orchestration": {
            "parallel_groups": [["TASK-GHOST"]],
        },
    }
    with open(features_dir / "FEAT-MISSING.yaml", "w") as f:
        yaml.dump(feature_data, f)

    return tmp_path


@pytest.fixture
def bad_yaml_dir(tmp_path):
    """Create temp dir with malformed YAML file."""
    features_dir = tmp_path / ".guardkit" / "features"
    features_dir.mkdir(parents=True)

    (features_dir / "FEAT-BROKEN.yaml").write_text(
        "id: FEAT-BROKEN\nname: broken\ntasks:\n  - invalid: [unterminated"
    )

    return tmp_path


@pytest.fixture
def bad_orchestration_dir(tmp_path):
    """Create temp dir with feature YAML where orchestration references unknown task."""
    features_dir = tmp_path / ".guardkit" / "features"
    features_dir.mkdir(parents=True)

    tasks_dir = tmp_path / "tasks" / "backlog"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "TASK-REAL.md").write_text("# Task\nReal task.")

    feature_data = {
        "id": "FEAT-ORCH",
        "name": "Bad Orchestration",
        "status": "planned",
        "tasks": [
            {
                "id": "TASK-REAL",
                "name": "Real Task",
                "file_path": "tasks/backlog/TASK-REAL.md",
            },
        ],
        "orchestration": {
            "parallel_groups": [["TASK-REAL", "TASK-PHANTOM"]],
        },
    }
    with open(features_dir / "FEAT-ORCH.yaml", "w") as f:
        yaml.dump(feature_data, f)

    return tmp_path


# ============================================================================
# Help Text Tests
# ============================================================================


class TestHelpText:
    """Test CLI help text output."""

    def test_feature_group_help(self, runner):
        """Feature group shows help with validate subcommand."""
        result = runner.invoke(feature, ["--help"])
        assert result.exit_code == 0
        assert "validate" in result.output
        assert "Feature management" in result.output

    def test_validate_help(self, runner):
        """Validate command shows help with --json option."""
        result = runner.invoke(feature, ["validate", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
        assert "FEATURE_ID" in result.output

    def test_feature_registered_in_main_cli(self, runner):
        """Feature command is accessible through main CLI group."""
        result = runner.invoke(cli, ["feature", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.output


# ============================================================================
# Valid Feature Tests (exit code 0)
# ============================================================================


class TestValidFeature:
    """Test validation of valid feature files."""

    def test_validate_valid_feature(self, runner, valid_feature_dir, monkeypatch):
        """Valid feature prints success message with checkmark, exit code 0."""
        monkeypatch.chdir(valid_feature_dir)
        result = runner.invoke(feature, ["validate", "FEAT-TEST"])
        assert result.exit_code == 0
        assert "FEAT-TEST" in result.output
        assert "is valid" in result.output

    def test_validate_valid_feature_json(self, runner, valid_feature_dir, monkeypatch):
        """Valid feature with --json outputs valid JSON with valid=true."""
        monkeypatch.chdir(valid_feature_dir)
        result = runner.invoke(feature, ["validate", "FEAT-TEST", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["valid"] is True
        assert data["feature_id"] == "FEAT-TEST"
        assert data["errors"] == []
        assert data["schema_errors"] == []
        assert data["structural_errors"] == []


# ============================================================================
# Schema Validation Error Tests (exit code 1)
# ============================================================================


class TestSchemaErrors:
    """Test detection of schema validation errors."""

    def test_validate_invalid_status(
        self, runner, invalid_status_feature_dir, monkeypatch
    ):
        """Invalid status field causes validation error, exit code 1."""
        monkeypatch.chdir(invalid_status_feature_dir)
        result = runner.invoke(feature, ["validate", "FEAT-BAD"])
        assert result.exit_code == 1
        assert "validation errors" in result.output
        assert "Schema errors" in result.output

    def test_validate_missing_required_field(
        self, runner, missing_field_feature_dir, monkeypatch
    ):
        """Missing required 'name' field causes validation error, exit code 1."""
        monkeypatch.chdir(missing_field_feature_dir)
        result = runner.invoke(feature, ["validate", "FEAT-NONAME"])
        assert result.exit_code == 1
        assert "validation errors" in result.output

    def test_validate_invalid_status_json(
        self, runner, invalid_status_feature_dir, monkeypatch
    ):
        """Invalid status with --json outputs errors in JSON format."""
        monkeypatch.chdir(invalid_status_feature_dir)
        result = runner.invoke(feature, ["validate", "FEAT-BAD", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["valid"] is False
        assert len(data["schema_errors"]) > 0
        assert data["feature_id"] == "FEAT-BAD"


# ============================================================================
# Structural Validation Error Tests (exit code 1)
# ============================================================================


class TestStructuralErrors:
    """Test detection of structural validation errors."""

    def test_validate_missing_task_file(
        self, runner, missing_task_file_dir, monkeypatch
    ):
        """Missing task file causes structural error, exit code 1."""
        monkeypatch.chdir(missing_task_file_dir)
        result = runner.invoke(feature, ["validate", "FEAT-MISSING"])
        assert result.exit_code == 1
        assert "Structural errors" in result.output or "Task file not found" in result.output

    def test_validate_unknown_task_in_orchestration(
        self, runner, bad_orchestration_dir, monkeypatch
    ):
        """Orchestration referencing unknown task causes structural error."""
        monkeypatch.chdir(bad_orchestration_dir)
        result = runner.invoke(feature, ["validate", "FEAT-ORCH"])
        assert result.exit_code == 1
        assert "TASK-PHANTOM" in result.output

    def test_validate_structural_error_json(
        self, runner, missing_task_file_dir, monkeypatch
    ):
        """Structural errors with --json outputs errors in JSON format."""
        monkeypatch.chdir(missing_task_file_dir)
        result = runner.invoke(feature, ["validate", "FEAT-MISSING", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["valid"] is False
        assert len(data["structural_errors"]) > 0


# ============================================================================
# File-Level Error Tests (exit code 2)
# ============================================================================


class TestFileErrors:
    """Test handling of file-level errors (not found, parse errors)."""

    def test_validate_feature_not_found(self, runner, tmp_path, monkeypatch):
        """Non-existent feature ID causes exit code 2."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(feature, ["validate", "FEAT-NONEXISTENT"])
        assert result.exit_code == 2
        assert "not found" in result.output.lower()

    def test_validate_feature_not_found_json(self, runner, tmp_path, monkeypatch):
        """Non-existent feature with --json outputs error in JSON format."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            feature, ["validate", "FEAT-NONEXISTENT", "--json"]
        )
        assert result.exit_code == 2
        data = json.loads(result.output)
        assert data["valid"] is False
        assert data["error_type"] == "not_found"

    def test_validate_yaml_parse_error(self, runner, bad_yaml_dir, monkeypatch):
        """Malformed YAML file causes exit code 2."""
        monkeypatch.chdir(bad_yaml_dir)
        result = runner.invoke(feature, ["validate", "FEAT-BROKEN"])
        assert result.exit_code == 2

    def test_validate_yaml_parse_error_json(self, runner, bad_yaml_dir, monkeypatch):
        """Malformed YAML with --json outputs parse error in JSON format."""
        monkeypatch.chdir(bad_yaml_dir)
        result = runner.invoke(feature, ["validate", "FEAT-BROKEN", "--json"])
        assert result.exit_code == 2
        data = json.loads(result.output)
        assert data["valid"] is False
        assert data["error_type"] == "parse_error"


# ============================================================================
# YML Extension Test
# ============================================================================


class TestYmlExtension:
    """Test .yml file extension support."""

    def test_validate_yml_extension(self, runner, tmp_path, monkeypatch):
        """Feature files with .yml extension are found and validated."""
        monkeypatch.chdir(tmp_path)
        features_dir = tmp_path / ".guardkit" / "features"
        features_dir.mkdir(parents=True)

        tasks_dir = tmp_path / "tasks" / "backlog"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "TASK-YML.md").write_text("# Task\nYML task.")

        feature_data = {
            "id": "FEAT-YML",
            "name": "YML Feature",
            "tasks": [
                {
                    "id": "TASK-YML",
                    "name": "YML Task",
                    "file_path": "tasks/backlog/TASK-YML.md",
                },
            ],
            "orchestration": {
                "parallel_groups": [["TASK-YML"]],
            },
        }
        with open(features_dir / "FEAT-YML.yml", "w") as f:
            yaml.dump(feature_data, f)

        result = runner.invoke(feature, ["validate", "FEAT-YML"])
        assert result.exit_code == 0
        assert "is valid" in result.output
