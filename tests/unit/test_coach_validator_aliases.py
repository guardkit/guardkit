"""Unit tests for CoachValidator task_type alias resolution.

Tests the TASK_TYPE_ALIASES constant and _resolve_task_type() method
to ensure legacy task_type values are gracefully handled.

See: TASK-IMP-ALIAS for implementation details
"""

import logging
import pytest
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    TASK_TYPE_ALIASES,
)
from guardkit.models.task_types import TaskType


class TestTaskTypeAliasResolution:
    """Test suite for task_type alias resolution in CoachValidator._resolve_task_type()."""

    @pytest.fixture
    def validator(self, tmp_path):
        """Create CoachValidator instance for testing."""
        return CoachValidator(str(tmp_path))

    def test_valid_enum_value_feature(self, validator):
        """Test that valid 'feature' enum value works without alias."""
        task = {"task_type": "feature"}
        result = validator._resolve_task_type(task)
        assert result == TaskType.FEATURE

    def test_valid_enum_value_scaffolding(self, validator):
        """Test that valid 'scaffolding' enum value works without alias."""
        task = {"task_type": "scaffolding"}
        result = validator._resolve_task_type(task)
        assert result == TaskType.SCAFFOLDING

    def test_valid_enum_value_testing(self, validator):
        """Test that valid 'testing' enum value works without alias."""
        task = {"task_type": "testing"}
        result = validator._resolve_task_type(task)
        assert result == TaskType.TESTING

    def test_alias_implementation_to_feature(self, validator):
        """Test 'implementation' alias maps to FEATURE (161 task files use this)."""
        task = {"task_type": "implementation"}
        result = validator._resolve_task_type(task)
        assert result == TaskType.FEATURE

    def test_alias_bug_fix_hyphen_to_feature(self, validator):
        """Test 'bug-fix' alias maps to FEATURE."""
        task = {"task_type": "bug-fix"}
        result = validator._resolve_task_type(task)
        assert result == TaskType.FEATURE

    def test_alias_bug_fix_underscore_to_feature(self, validator):
        """Test 'bug_fix' alias maps to FEATURE."""
        task = {"task_type": "bug_fix"}
        result = validator._resolve_task_type(task)
        assert result == TaskType.FEATURE

    def test_alias_benchmark_to_testing(self, validator):
        """Test 'benchmark' alias maps to TESTING."""
        task = {"task_type": "benchmark"}
        result = validator._resolve_task_type(task)
        assert result == TaskType.TESTING

    def test_alias_research_to_documentation(self, validator):
        """Test 'research' alias maps to DOCUMENTATION."""
        task = {"task_type": "research"}
        result = validator._resolve_task_type(task)
        assert result == TaskType.DOCUMENTATION

    def test_none_task_type_defaults_to_feature(self, validator):
        """Test that None/missing task_type defaults to FEATURE."""
        task = {}
        result = validator._resolve_task_type(task)
        assert result == TaskType.FEATURE

    def test_explicit_none_task_type_defaults_to_feature(self, validator):
        """Test that explicit None task_type defaults to FEATURE."""
        task = {"task_type": None}
        result = validator._resolve_task_type(task)
        assert result == TaskType.FEATURE

    def test_invalid_task_type_raises_error(self, validator):
        """Test that invalid task_type (not enum or alias) raises ValueError."""
        task = {"task_type": "invalid_value"}
        with pytest.raises(ValueError) as exc_info:
            validator._resolve_task_type(task)

        error_msg = str(exc_info.value)
        assert "Invalid task_type value: invalid_value" in error_msg
        assert "Must be one of:" in error_msg
        assert "or valid alias:" in error_msg

    def test_all_aliases_defined_correctly(self, validator):
        """Test all aliases in TASK_TYPE_ALIASES mapping work correctly."""
        expected_mappings = {
            "implementation": TaskType.FEATURE,
            "bug-fix": TaskType.FEATURE,
            "bug_fix": TaskType.FEATURE,
            "benchmark": TaskType.TESTING,
            "research": TaskType.DOCUMENTATION,
        }

        for alias, expected_type in expected_mappings.items():
            task = {"task_type": alias}
            result = validator._resolve_task_type(task)
            assert result == expected_type, f"Alias '{alias}' should map to {expected_type.value}"

    def test_alias_logging(self, validator, caplog):
        """Test that using alias logs info message for transparency."""
        caplog.set_level(logging.INFO)

        task = {"task_type": "implementation"}
        validator._resolve_task_type(task)

        # Check log message contains expected content
        info_logs = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_logs) >= 1, "Expected at least one INFO log message"

        log_message = info_logs[-1].message
        assert "task_type alias" in log_message
        assert "'implementation'" in log_message
        assert "'feature'" in log_message
