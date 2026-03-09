"""
Unit tests for command failure classifier (TASK-RFX-F7F5).

Tests failure classification into environment, implementation, transient,
and unknown categories, plus advisory text generation.

Coverage Target: >=85%
Test Count: 24 tests
"""

import subprocess
from dataclasses import asdict
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from guardkit.orchestrator.quality_gates.command_failure_classifier import (
    classify_command_failure,
    build_command_failure_advisory,
    CommandFailureRecord,
)


# ============================================================================
# 1. classify_command_failure Tests
# ============================================================================


class TestClassifyCommandFailure:
    """Tests for the classify_command_failure function."""

    # --- Environment classification ---

    def test_exit_127_classified_as_environment(self):
        """Exit code 127 (command not found) → environment."""
        result = classify_command_failure(
            returncode=127,
            stderr="bash: mycommand: command not found",
            stdout="",
            command="mycommand --version",
        )
        assert result == "environment"

    def test_command_not_found_stderr(self):
        """'command not found' in stderr → environment."""
        result = classify_command_failure(
            returncode=1,
            stderr="zsh: command not found: mytool",
            stdout="",
            command="mytool --check",
        )
        assert result == "environment"

    def test_module_not_found_system_tool(self):
        """ModuleNotFoundError for pip/setuptools → environment."""
        result = classify_command_failure(
            returncode=1,
            stderr="ModuleNotFoundError: No module named 'pip'",
            stdout="",
            command="pip install requests",
        )
        assert result == "environment"

    def test_module_not_found_virtualenv(self):
        """ModuleNotFoundError for virtualenv → environment."""
        result = classify_command_failure(
            returncode=1,
            stderr="ModuleNotFoundError: No module named 'virtualenv'",
            stdout="",
            command="virtualenv .venv",
        )
        assert result == "environment"

    def test_not_found_in_path(self):
        """'not found in PATH' → environment."""
        result = classify_command_failure(
            returncode=1,
            stderr="error: tool not found in PATH",
            stdout="",
            command="sometool",
        )
        assert result == "environment"

    # --- Implementation classification ---

    def test_traceback_classified_as_implementation(self):
        """Python traceback → implementation."""
        result = classify_command_failure(
            returncode=1,
            stderr=(
                "Traceback (most recent call last):\n"
                '  File "src/app.py", line 42, in main\n'
                "    result = process_data(input)\n"
                "TypeError: process_data() missing 1 required argument"
            ),
            stdout="",
            command="python -c 'import src.app; src.app.main()'",
        )
        assert result == "implementation"

    def test_import_error_project_module(self):
        """ImportError for project module → implementation."""
        result = classify_command_failure(
            returncode=1,
            stderr="ImportError: cannot import name 'MyClass' from 'myproject.models'",
            stdout="",
            command="python -c 'from myproject.models import MyClass'",
        )
        assert result == "implementation"

    def test_module_not_found_project_module(self):
        """ModuleNotFoundError for non-system module → implementation."""
        result = classify_command_failure(
            returncode=1,
            stderr="ModuleNotFoundError: No module named 'myproject'",
            stdout="",
            command="python -c 'import myproject'",
        )
        assert result == "implementation"

    def test_syntax_error_classified_as_implementation(self):
        """SyntaxError → implementation."""
        result = classify_command_failure(
            returncode=1,
            stderr=(
                '  File "src/app.py", line 10\n'
                "    def foo(\n"
                "           ^\n"
                "SyntaxError: unexpected EOF while parsing"
            ),
            stdout="",
            command="python -c 'import src.app'",
        )
        assert result == "implementation"

    def test_name_error_classified_as_implementation(self):
        """NameError → implementation."""
        result = classify_command_failure(
            returncode=1,
            stderr="NameError: name 'undefined_var' is not defined",
            stdout="",
            command="python -c 'print(undefined_var)'",
        )
        assert result == "implementation"

    def test_attribute_error_classified_as_implementation(self):
        """AttributeError → implementation."""
        result = classify_command_failure(
            returncode=1,
            stderr="AttributeError: 'NoneType' object has no attribute 'run'",
            stdout="",
            command="python -c 'None.run()'",
        )
        assert result == "implementation"

    # --- Transient classification ---

    def test_connection_refused_classified_as_transient(self):
        """ConnectionRefused → transient."""
        result = classify_command_failure(
            returncode=1,
            stderr="ConnectionRefusedError: [Errno 111] Connection refused",
            stdout="",
            command="python -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:9999\")'",
        )
        assert result == "transient"

    def test_timeout_classified_as_transient(self):
        """Timeout → transient."""
        result = classify_command_failure(
            returncode=1,
            stderr="urllib.error.URLError: <urlopen error timeout>",
            stdout="",
            command="curl http://example.com",
        )
        assert result == "transient"

    def test_dns_resolution_classified_as_transient(self):
        """DNS resolution failure → transient."""
        result = classify_command_failure(
            returncode=1,
            stderr="DNS resolution failed for host 'nonexistent.example.com'",
            stdout="",
            command="curl http://nonexistent.example.com",
        )
        assert result == "transient"

    def test_name_resolution_failure_transient(self):
        """Name or service not known → transient."""
        result = classify_command_failure(
            returncode=1,
            stderr="Name or service not known",
            stdout="",
            command="ping badhost",
        )
        assert result == "transient"

    def test_network_unreachable_transient(self):
        """Network is unreachable → transient."""
        result = classify_command_failure(
            returncode=1,
            stderr="Network is unreachable",
            stdout="",
            command="curl http://10.0.0.1:8080",
        )
        assert result == "transient"

    # --- Unknown classification ---

    def test_generic_failure_classified_as_unknown(self):
        """No matching pattern → unknown."""
        result = classify_command_failure(
            returncode=1,
            stderr="some unrecognized error output",
            stdout="",
            command="custom-tool --check",
        )
        assert result == "unknown"

    def test_empty_output_classified_as_unknown(self):
        """Empty stderr and stdout → unknown."""
        result = classify_command_failure(
            returncode=1,
            stderr="",
            stdout="",
            command="false",
        )
        assert result == "unknown"

    # --- Edge cases ---

    def test_stdout_checked_when_stderr_empty(self):
        """Implementation error in stdout (not stderr) → implementation."""
        result = classify_command_failure(
            returncode=1,
            stderr="",
            stdout="Traceback (most recent call last):\n  TypeError: bad args",
            command="python script.py",
        )
        assert result == "implementation"

    def test_environment_takes_precedence_over_implementation(self):
        """Exit 127 wins even if traceback also present in output."""
        result = classify_command_failure(
            returncode=127,
            stderr="bash: python: command not found",
            stdout="",
            command="python script.py",
        )
        assert result == "environment"


# ============================================================================
# 2. CommandFailureRecord Tests
# ============================================================================


class TestCommandFailureRecord:
    """Tests for CommandFailureRecord dataclass."""

    def test_basic_construction(self):
        """Create a basic failure record."""
        record = CommandFailureRecord(
            command="python -c 'import foo'",
            criterion_text="`python -c 'import foo'` succeeds",
            returncode=1,
            stderr="ModuleNotFoundError: No module named 'foo'",
            stdout="",
            classification="implementation",
        )
        assert record.classification == "implementation"
        assert record.timed_out is False

    def test_timeout_record(self):
        """Create a timeout failure record."""
        record = CommandFailureRecord(
            command="slow-command",
            criterion_text="`slow-command` completes",
            returncode=None,
            stderr="",
            stdout="",
            classification="transient",
            timed_out=True,
        )
        assert record.timed_out is True
        assert record.returncode is None


# ============================================================================
# 3. build_command_failure_advisory Tests
# ============================================================================


class TestBuildCommandFailureAdvisory:
    """Tests for the build_command_failure_advisory function."""

    def test_empty_failures_returns_none(self):
        """No failures → None."""
        assert build_command_failure_advisory([]) is None

    def test_environment_only_suppressed(self):
        """Only environment failures → None (suppressed)."""
        failures = [
            CommandFailureRecord(
                command="mytool",
                criterion_text="`mytool` runs",
                returncode=127,
                stderr="command not found",
                stdout="",
                classification="environment",
            )
        ]
        assert build_command_failure_advisory(failures) is None

    def test_transient_only_suppressed(self):
        """Only transient failures → None (suppressed)."""
        failures = [
            CommandFailureRecord(
                command="curl http://api.example.com",
                criterion_text="`curl http://api.example.com` succeeds",
                returncode=1,
                stderr="Connection refused",
                stdout="",
                classification="transient",
            )
        ]
        assert build_command_failure_advisory(failures) is None

    def test_implementation_failure_included(self):
        """Implementation failure → advisory text."""
        failures = [
            CommandFailureRecord(
                command="python -c 'import myapp'",
                criterion_text="`python -c 'import myapp'` succeeds",
                returncode=1,
                stderr="ImportError: cannot import name 'MyClass'",
                stdout="",
                classification="implementation",
            )
        ]
        result = build_command_failure_advisory(failures)
        assert result is not None
        assert "[Command Execution Advisory]" in result
        assert "implementation" in result
        assert "ImportError" in result

    def test_unknown_failure_included_with_caveat(self):
        """Unknown failure → advisory text with caveat."""
        failures = [
            CommandFailureRecord(
                command="custom-tool",
                criterion_text="`custom-tool` runs",
                returncode=1,
                stderr="some error",
                stdout="",
                classification="unknown",
            )
        ]
        result = build_command_failure_advisory(failures)
        assert result is not None
        assert "unknown (may be implementation-related)" in result

    def test_mixed_failures_only_relevant_shown(self):
        """Mix of environment + implementation → only implementation shown."""
        failures = [
            CommandFailureRecord(
                command="mytool",
                criterion_text="`mytool` runs",
                returncode=127,
                stderr="command not found",
                stdout="",
                classification="environment",
            ),
            CommandFailureRecord(
                command="python -c 'import foo'",
                criterion_text="`python -c 'import foo'` succeeds",
                returncode=1,
                stderr="ImportError: No module named 'foo'",
                stdout="",
                classification="implementation",
            ),
        ]
        result = build_command_failure_advisory(failures)
        assert result is not None
        assert "implementation" in result
        assert "mytool" not in result  # environment failure suppressed

    def test_long_stderr_truncated(self):
        """Long stderr is truncated to 300 chars."""
        failures = [
            CommandFailureRecord(
                command="python script.py",
                criterion_text="`python script.py` runs",
                returncode=1,
                stderr="E" * 500,
                stdout="",
                classification="implementation",
            )
        ]
        result = build_command_failure_advisory(failures)
        assert result is not None
        assert "..." in result


# ============================================================================
# 4. Integration: _execute_command_criteria captures failures
# ============================================================================


class TestExecuteCommandCriteriaFailureCapture:
    """Integration tests for failure capture in _execute_command_criteria."""

    @pytest.fixture
    def orchestrator(self):
        """Create a minimal AutoBuildOrchestrator mock for testing."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orch = object.__new__(AutoBuildOrchestrator)
        return orch

    @pytest.fixture
    def worktree_path(self, tmp_path):
        """Create a valid worktree path."""
        wt = tmp_path / ".guardkit" / "worktrees" / "test"
        wt.mkdir(parents=True)
        sentinel = tmp_path / ".guardkit" / "worktrees"
        sentinel.mkdir(parents=True, exist_ok=True)
        return wt

    @patch("guardkit.orchestrator.quality_gates.criteria_classifier.classify_acceptance_criteria")
    @patch("subprocess.run")
    def test_failed_command_recorded_in_synthetic_report(
        self, mock_run, mock_classify, orchestrator, worktree_path
    ):
        """Failed command is classified and stored in command_failures."""
        from guardkit.orchestrator.quality_gates.criteria_classifier import (
            ClassificationResult,
            ClassifiedCriterion,
            CriterionType,
        )

        mock_classify.return_value = ClassificationResult(
            criteria=[
                ClassifiedCriterion(
                    text="`python -c 'import myapp'` succeeds",
                    criterion_type=CriterionType.COMMAND_EXECUTION,
                    confidence=0.9,
                    extracted_command="python -c 'import myapp'",
                )
            ]
        )

        mock_run.return_value = Mock(
            returncode=1,
            stderr="ImportError: cannot import name 'MyClass' from 'myapp'",
            stdout="",
        )

        report = {"_synthetic": True}
        orchestrator._execute_command_criteria(
            synthetic_report=report,
            acceptance_criteria=["`python -c 'import myapp'` succeeds"],
            worktree_path=worktree_path,
        )

        assert "command_failures" in report
        assert len(report["command_failures"]) == 1
        failure = report["command_failures"][0]
        assert failure.classification == "implementation"
        assert "ImportError" in failure.stderr

    @patch("guardkit.orchestrator.quality_gates.criteria_classifier.classify_acceptance_criteria")
    @patch("subprocess.run")
    def test_successful_command_not_recorded_as_failure(
        self, mock_run, mock_classify, orchestrator, worktree_path
    ):
        """Successful command is not stored in command_failures."""
        from guardkit.orchestrator.quality_gates.criteria_classifier import (
            ClassificationResult,
            ClassifiedCriterion,
            CriterionType,
        )

        mock_classify.return_value = ClassificationResult(
            criteria=[
                ClassifiedCriterion(
                    text="`python -c 'print(1)'` succeeds",
                    criterion_type=CriterionType.COMMAND_EXECUTION,
                    confidence=0.9,
                    extracted_command="python -c 'print(1)'",
                )
            ]
        )

        mock_run.return_value = Mock(returncode=0, stderr="", stdout="1\n")

        report = {"_synthetic": True}
        orchestrator._execute_command_criteria(
            synthetic_report=report,
            acceptance_criteria=["`python -c 'print(1)'` succeeds"],
            worktree_path=worktree_path,
        )

        assert "command_failures" not in report
        assert "requirements_addressed" in report

    @patch("guardkit.orchestrator.quality_gates.criteria_classifier.classify_acceptance_criteria")
    @patch("subprocess.run")
    def test_timeout_recorded_as_transient(
        self, mock_run, mock_classify, orchestrator, worktree_path
    ):
        """Timed-out command recorded as transient failure."""
        from guardkit.orchestrator.quality_gates.criteria_classifier import (
            ClassificationResult,
            ClassifiedCriterion,
            CriterionType,
        )

        mock_classify.return_value = ClassificationResult(
            criteria=[
                ClassifiedCriterion(
                    text="`slow-cmd` completes",
                    criterion_type=CriterionType.COMMAND_EXECUTION,
                    confidence=0.9,
                    extracted_command="slow-cmd",
                )
            ]
        )

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="slow-cmd", timeout=60)

        report = {"_synthetic": True}
        orchestrator._execute_command_criteria(
            synthetic_report=report,
            acceptance_criteria=["`slow-cmd` completes"],
            worktree_path=worktree_path,
        )

        assert "command_failures" in report
        assert len(report["command_failures"]) == 1
        failure = report["command_failures"][0]
        assert failure.classification == "transient"
        assert failure.timed_out is True

    @patch("guardkit.orchestrator.quality_gates.criteria_classifier.classify_acceptance_criteria")
    @patch("subprocess.run")
    def test_environment_failure_in_report_suppressed_in_advisory(
        self, mock_run, mock_classify, orchestrator, worktree_path
    ):
        """Environment failure is stored but suppressed in advisory."""
        from guardkit.orchestrator.quality_gates.criteria_classifier import (
            ClassificationResult,
            ClassifiedCriterion,
            CriterionType,
        )

        mock_classify.return_value = ClassificationResult(
            criteria=[
                ClassifiedCriterion(
                    text="`mytool` runs",
                    criterion_type=CriterionType.COMMAND_EXECUTION,
                    confidence=0.9,
                    extracted_command="mytool",
                )
            ]
        )

        mock_run.return_value = Mock(
            returncode=127,
            stderr="bash: mytool: command not found",
            stdout="",
        )

        report = {"_synthetic": True}
        orchestrator._execute_command_criteria(
            synthetic_report=report,
            acceptance_criteria=["`mytool` runs"],
            worktree_path=worktree_path,
        )

        assert "command_failures" in report
        failure = report["command_failures"][0]
        assert failure.classification == "environment"

        # Advisory should suppress environment failures
        advisory = build_command_failure_advisory(report["command_failures"])
        assert advisory is None


# ============================================================================
# 5. Integration: Advisory injection into feedback
# ============================================================================


class TestAdvisoryInjectionIntoFeedback:
    """Tests for advisory text injection into Coach feedback."""

    def test_implementation_failure_appears_in_feedback(self):
        """Implementation-classified failure text appears in Coach feedback."""
        failures = [
            CommandFailureRecord(
                command="python -c 'from myapp import handler'",
                criterion_text="`python -c 'from myapp import handler'` succeeds",
                returncode=1,
                stderr="ImportError: cannot import name 'handler' from 'myapp'",
                stdout="",
                classification="implementation",
            )
        ]

        advisory = build_command_failure_advisory(failures)
        assert advisory is not None

        # Simulate feedback construction as done in autobuild.py
        base_feedback = "- Tests did not pass during task-work execution"
        feedback_text = base_feedback + "\n\n" + advisory

        assert "[Command Execution Advisory]" in feedback_text
        assert "ImportError" in feedback_text
        assert "implementation" in feedback_text

    def test_environment_failure_not_in_feedback(self):
        """Environment-classified failure does NOT appear in Coach feedback."""
        failures = [
            CommandFailureRecord(
                command="mytool",
                criterion_text="`mytool` runs",
                returncode=127,
                stderr="bash: mytool: command not found",
                stdout="",
                classification="environment",
            )
        ]

        advisory = build_command_failure_advisory(failures)
        assert advisory is None

        # Simulate feedback construction
        base_feedback = "- Tests did not pass during task-work execution"
        # advisory is None, so no injection happens
        feedback_text = base_feedback
        assert "mytool" not in feedback_text
        assert "command not found" not in feedback_text
