"""
Unit tests for CoachValidator: the project's own test run and the evidence
it gathers for the reviewer.

Tests cover:
    - IndependentTestVerification: Independent test execution
    - Test command detection (task-specific, recursive glob, task-work
      results, cumulative diff, prior Player reports, collect_ignore_glob)
    - Task type resolution and the profile's tests_required in gather_evidence
    - Test failure classification
    - The SDK / harness test-execution path and its debug preservation
"""

import json
import os
import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

import sys
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.quality_gates import (
    CoachValidator,
    IndependentTestResult,
)
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def tmp_worktree(tmp_path):
    """Create a temporary worktree directory for a PYTHON project.

    TS-lane D.1b: the ``pyproject.toml`` marker is now written explicitly.
    Until the unconditional ``"Could not detect project type, defaulting to
    pytest"`` fallback was deleted, an EMPTY directory silently produced
    ``pytest tests/ -v --tb=short`` — so 14 tests in this file that are about
    timeouts, summaries and gate profiles were riding a stack guess they never
    asked for and never asserted. The marker states the assumption those tests
    always had, and keeps their resolved command byte-identical to before.
    """
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    (worktree / "pyproject.toml").touch()
    return worktree


# Classes that own their own ``select_harness`` patching (TASK-HMIG-006.3).
# The autouse fixture below skips its default patch for these classes so
# their explicit ``with patch("...select_harness", ...)`` blocks govern
# the harness behaviour for those tests.
_HARNESS_OWNING_TEST_CLASSES = frozenset({
    "TestSdkEnvMerge",
    "TestCoachHarnessMigration",
    "TestCoachSdkDebugPreservation",
})


@pytest.fixture(autouse=True)
def _default_coach_harness_simulates_sdk_failure(request):
    """Restore pre-TASK-HMIG-006.3 fallback semantics for unmodified tests.

    Pre-migration, ``CoachValidator._run_tests_via_sdk`` invoked
    ``claude_agent_sdk.query`` directly. In the test environment that
    subprocess reliably failed (no API key / no live CLI), the SDK
    raised, and ``run_independent_tests`` caught the exception and fell
    back to ``subprocess.run`` — which the affected tests mock. Tests
    such as ``TestIndependentTestVerification`` therefore depended on
    that implicit "SDK fails → subprocess fallback" chain even though
    their assertions were entirely about the subprocess path.

    Post-migration, ``_run_tests_via_sdk`` dispatches through
    ``select_harness``. ``ClaudeSDKHarness.invoke`` short-circuits on
    ``ResultMessageEvent``, which means the post-``ResultMessage``
    exception that the pre-migration code surfaced is now invisible to
    the orchestrator. The SDK call returns a result with empty
    ``raw_output`` instead of raising, so the fallback never fires and
    the subprocess mock is never exercised.

    This autouse fixture patches ``select_harness`` at the
    ``coach_validator`` binding to return a harness whose ``invoke()``
    raises :class:`AgentInvocationError`. ``run_independent_tests``
    catches the exception and falls back to subprocess, restoring the
    pre-migration behaviour for every test that does not explicitly
    own the harness boundary. Tests that need the real harness or a
    bespoke fake (``TestSdkEnvMerge``, ``TestCoachHarnessMigration``)
    are skipped via ``_HARNESS_OWNING_TEST_CLASSES`` and rely on their
    own ``with patch(...)`` blocks.
    """
    cls = getattr(request.node, "cls", None)
    if cls is not None and cls.__name__ in _HARNESS_OWNING_TEST_CLASSES:
        yield
        return

    from guardkit.orchestrator.exceptions import AgentInvocationError

    class _SdkFailingHarness:
        supports_resume = False
        session_id = None

        async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
            raise AgentInvocationError(
                "TASK-HMIG-006.3 test fixture: simulated SDK transport "
                "failure to restore pre-migration subprocess-fallback "
                "semantics."
            )
            yield  # unreachable; keeps this an async generator

    with patch(
        "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
        return_value=_SdkFailingHarness(),
    ):
        yield


@pytest.fixture
def task_work_results_dir(tmp_worktree):
    """Create the task-work results directory."""
    results_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-001"
    results_dir.mkdir(parents=True)
    return results_dir


def make_task_work_results(
    tests_passed: bool = True,
    failed_count: int = 0,
    total_tests: int = 15,
    coverage_met: bool = True,
    line_coverage: int = 85,
    arch_score: int = 82,
    violations: int = 0,
    requirements_met: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Helper to create task-work results matching actual writer schema."""
    # If tests_passed is False, we need to set failed_count if it's 0
    # This ensures the schema reflects the actual failure state
    if not tests_passed and failed_count == 0:
        failed_count = 1  # Set to at least 1 to indicate failure

    passed_count = total_tests - failed_count
    return {
        # Quality gates object (what writer actually creates)
        "quality_gates": {
            "tests_passing": tests_passed and failed_count == 0,
            "tests_passed": passed_count,
            "tests_failed": failed_count,
            "coverage": line_coverage,
            "coverage_met": coverage_met,
            "all_passed": tests_passed and coverage_met,
        },
        # Code review (separate from quality_gates)
        "code_review": {
            "score": arch_score,
            "solid": 85,
            "dry": 80,
            "yagni": 82,
        },
        # Plan audit (separate from quality_gates)
        "plan_audit": {
            "violations": violations,
            "file_count_match": True,
        },
        "requirements_met": requirements_met if requirements_met is not None else [
            "OAuth2 authentication flow",
            "Token generation",
            "Token refresh",
        ],
    }


def make_task(acceptance_criteria: Optional[List[str]] = None) -> Dict[str, Any]:
    """Helper to create task data."""
    return {
        "acceptance_criteria": acceptance_criteria or [
            "OAuth2 authentication flow",
            "Token generation",
            "Token refresh",
        ],
    }


def write_task_work_results(results_dir: Path, results: Dict[str, Any]):
    """Helper to write task-work results to file."""
    results_path = results_dir / "task_work_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    return results_path


# ============================================================================
# Test Independent Test Verification
# ============================================================================


class TestIndependentTestVerification:
    """Test independent test running."""

    def test_run_tests_success(self, tmp_worktree):
        """Test successful independent test run."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="15 passed in 1.45s",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        assert result.tests_passed is True
        assert "passed" in result.test_output_summary.lower()
        assert result.duration_seconds > 0

    def test_run_tests_failure(self, tmp_worktree):
        """Test failed independent test run."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="13 passed, 2 failed in 2.3s",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        assert result.tests_passed is False
        assert "failed" in result.test_output_summary.lower()

    def test_run_tests_timeout(self, tmp_worktree):
        """Test test execution timeout."""
        import subprocess

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("pytest", 300)

            validator = CoachValidator(str(tmp_worktree), test_timeout=300)
            result = validator.run_independent_tests()

        assert result.tests_passed is False
        assert "timed out" in result.test_output_summary.lower()

    def test_run_tests_exception(self, tmp_worktree):
        """Test test execution exception handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Command not found")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        assert result.tests_passed is False
        assert "failed" in result.test_output_summary.lower()

    def test_run_tests_uses_custom_command(self, tmp_worktree):
        """Test custom test command is used."""
        custom_cmd = "make test-all"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree), test_command=custom_cmd)
            result = validator.run_independent_tests()

        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == custom_cmd
        assert result.test_command == custom_cmd

    def test_run_tests_auto_detects_python(self, tmp_worktree):
        """Test auto-detection of pytest for Python projects."""
        # Create Python project indicator
        (tmp_worktree / "pyproject.toml").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        assert "pytest" in result.test_command

    def test_run_tests_auto_detects_node(self, tmp_worktree):
        """Test auto-detection of npm test for Node projects."""
        # Create Node project indicator. The fixture's Python marker is
        # removed first — a directory carrying pyproject.toml is not a Node
        # project, and the ladder checks Python first (TS-lane D.1b: the
        # fixture now states the Python assumption the other tests rely on).
        (tmp_worktree / "pyproject.toml").unlink()
        (tmp_worktree / "package.json").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        assert "npm test" in result.test_command

    def test_run_tests_auto_detects_dotnet(self, tmp_worktree):
        """Test auto-detection of dotnet test for .NET projects."""
        # Create .NET project indicator (see the Node test above for why the
        # fixture's Python marker is removed first).
        (tmp_worktree / "pyproject.toml").unlink()
        (tmp_worktree / "Example.csproj").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        assert "dotnet test" in result.test_command


# ============================================================================
# Test Dataclasses
# ============================================================================


class TestDataclasses:
    """Test dataclass initialization and behavior."""

    def test_independent_test_result_fields(self):
        """Test IndependentTestResult has expected fields."""
        result = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/ -v",
            test_output_summary="15 passed in 1.45s",
            duration_seconds=1.45,
        )

        assert result.tests_passed is True
        assert result.test_command == "pytest tests/ -v"
        assert result.test_output_summary == "15 passed in 1.45s"
        assert result.duration_seconds == 1.45


# ============================================================================
# Test Helper Methods
# ============================================================================


class TestCoachValidatorHelpers:
    """Test CoachValidator helper methods."""

    def test_summarize_test_output_truncates(self, tmp_worktree):
        """Test _summarize_test_output truncates long output."""
        validator = CoachValidator(str(tmp_worktree))

        long_output = "line\n" * 1000 + "15 passed in 1.45s"

        summary = validator._summarize_test_output(long_output, max_length=100)

        assert len(summary) <= 100

    def test_summarize_test_output_extracts_summary(self, tmp_worktree):
        """Test _summarize_test_output extracts test summary lines."""
        validator = CoachValidator(str(tmp_worktree))

        output = """
tests/test_one.py::test_example PASSED
tests/test_two.py::test_other PASSED
================
15 passed, 2 failed in 2.34s
================
"""

        summary = validator._summarize_test_output(output)

        assert "passed" in summary.lower()
        assert "failed" in summary.lower()


# ============================================================================
# Test Integration with AutoBuild
# ============================================================================


class TestAutoBuildIntegration:
    """Test CoachValidator integration with AutoBuild orchestrator."""

    def test_validator_can_be_instantiated(self, tmp_worktree):
        """Test CoachValidator can be instantiated."""
        validator = CoachValidator(str(tmp_worktree))

        assert hasattr(validator, "gather_evidence")
        assert hasattr(validator, "read_quality_gate_results")
        assert hasattr(validator, "run_independent_tests")

    def test_validator_returns_expected_type(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test gather_evidence returns a CoachEvidenceBundle."""
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.gather_evidence("TASK-001", 1, make_task())

        assert isinstance(result, CoachEvidenceBundle)
        assert result.gathering_status == "complete"
        assert result.independent_tests is not None
        assert result.task_type == "feature"

    def test_validator_result_can_serialize_to_json(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test the evidence bundle can be serialized to JSON."""
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.gather_evidence("TASK-001", 1, make_task())

        # Should not raise
        d = result.to_dict()
        json_str = json.dumps(d)

        assert len(json_str) > 0
        assert '"independent_tests"' in json_str


# ============================================================================
# Test Task Type Profile Support (TASK-FBSDK-021)
# ============================================================================


class TestTaskTypeProfileResolution:
    """Test task type resolution from task metadata."""

    def test_resolve_task_type_default_no_type_specified(self, tmp_worktree):
        """Test default resolution when no task_type specified."""
        from guardkit.models.task_types import TaskType

        validator = CoachValidator(str(tmp_worktree))
        task = {"acceptance_criteria": []}

        task_type = validator._resolve_task_type(task)

        assert task_type == TaskType.FEATURE

    def test_resolve_task_type_scaffolding(self, tmp_worktree):
        """Test resolution of scaffolding task type."""
        from guardkit.models.task_types import TaskType

        validator = CoachValidator(str(tmp_worktree))
        task = {"task_type": "scaffolding", "acceptance_criteria": []}

        task_type = validator._resolve_task_type(task)

        assert task_type == TaskType.SCAFFOLDING

    def test_resolve_task_type_feature(self, tmp_worktree):
        """Test resolution of feature task type."""
        from guardkit.models.task_types import TaskType

        validator = CoachValidator(str(tmp_worktree))
        task = {"task_type": "feature", "acceptance_criteria": []}

        task_type = validator._resolve_task_type(task)

        assert task_type == TaskType.FEATURE

    def test_resolve_task_type_infrastructure(self, tmp_worktree):
        """Test resolution of infrastructure task type."""
        from guardkit.models.task_types import TaskType

        validator = CoachValidator(str(tmp_worktree))
        task = {"task_type": "infrastructure", "acceptance_criteria": []}

        task_type = validator._resolve_task_type(task)

        assert task_type == TaskType.INFRASTRUCTURE

    def test_resolve_task_type_documentation(self, tmp_worktree):
        """Test resolution of documentation task type."""
        from guardkit.models.task_types import TaskType

        validator = CoachValidator(str(tmp_worktree))
        task = {"task_type": "documentation", "acceptance_criteria": []}

        task_type = validator._resolve_task_type(task)

        assert task_type == TaskType.DOCUMENTATION

    def test_resolve_task_type_integration(self, tmp_worktree):
        """AC-010: _resolve_task_type accepts 'integration' as valid task_type."""
        from guardkit.models.task_types import TaskType

        validator = CoachValidator(str(tmp_worktree))
        task = {"task_type": "integration", "acceptance_criteria": []}

        task_type = validator._resolve_task_type(task)

        assert task_type == TaskType.INTEGRATION

    def test_resolve_task_type_invalid(self, tmp_worktree):
        """Test error handling for invalid task_type."""
        validator = CoachValidator(str(tmp_worktree))
        task = {"task_type": "invalid_type", "acceptance_criteria": []}

        with pytest.raises(ValueError) as exc_info:
            validator._resolve_task_type(task)

        assert "Invalid task_type value" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)


class TestQualityGateProfileApplication:
    """The task type's profile decides whether gather_evidence runs the tests."""

    def test_scaffolding_profile_skips_independent_test_verification(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that scaffolding profile skips independent test verification.

        Scaffolding tasks (task_type: scaffolding) should skip independent test
        verification because they CREATE the test infrastructure. Tests don't
        exist yet during scaffolding tasks.

        This is the fix for TASK-FIX-SCAF where quality gates passed but then
        independent test verification failed because tests didn't exist.
        """
        # Write results that pass quality gates for scaffolding
        results = make_task_work_results(
            tests_passed=True,  # Quality gates passed
            requirements_met=["Create test infrastructure"],
        )
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "scaffolding",
            "acceptance_criteria": ["Create test infrastructure"],
        }

        validator = CoachValidator(str(tmp_worktree))
        with patch.object(validator, "run_independent_tests") as run_mock:
            result = validator.gather_evidence("TASK-001", 1, task)

        run_mock.assert_not_called()
        assert result.independent_tests is not None
        # Verify test verification was skipped (not actually run)
        assert result.independent_tests.test_command == "skipped"
        assert "skipped" in result.independent_tests.test_output_summary.lower()
        assert result.independent_tests.tests_passed is True
        assert result.independent_tests.duration_seconds == 0.0

    def test_feature_profile_runs_independent_test_verification(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that feature profile runs independent test verification.

        Feature tasks with tests_required=True should still run independent
        test verification (trust but verify behavior).
        """
        results = make_task_work_results(
            tests_passed=True,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "feature",
            "acceptance_criteria": ["Criterion 1"],
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="All passed", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.gather_evidence("TASK-001", 1, task)

        # Should run independent tests
        assert result.independent_tests is not None
        # Verify test verification was actually run (not skipped)
        assert result.independent_tests.test_command != "skipped"
        assert "skipped" not in result.independent_tests.test_output_summary.lower()
        # Verify subprocess.run was called (tests were actually run)
        mock_run.assert_called_once()


# ============================================================================
# Test Task-Specific Test Detection (TASK-FIX-INDTEST)
# ============================================================================


class TestTaskSpecificTestDetection:
    """Test task-specific test detection and filtering.

    These tests verify the fix for TASK-FIX-INDTEST where independent test
    verification in shared worktrees was discovering ALL tests from ALL tasks
    instead of just the specific task being validated.
    """

    def test_task_id_to_pattern_prefix_basic(self, tmp_worktree):
        """Test basic task_id to pattern conversion."""
        validator = CoachValidator(str(tmp_worktree))

        assert validator._task_id_to_pattern_prefix("TASK-FHA-002") == "task_fha_002"
        assert validator._task_id_to_pattern_prefix("TASK-001") == "task_001"
        assert validator._task_id_to_pattern_prefix("TASK-AB-001") == "task_ab_001"

    def test_task_id_to_pattern_prefix_lowercase_preserved(self, tmp_worktree):
        """Test that already lowercase IDs are preserved."""
        validator = CoachValidator(str(tmp_worktree))

        # Already lowercase should work
        assert validator._task_id_to_pattern_prefix("task-001") == "task_001"

    def test_detect_test_command_finds_task_specific_tests(self, tmp_worktree):
        """Test detection of task-specific test files."""
        # Create Python project indicator
        (tmp_worktree / "pyproject.toml").touch()

        # Create test directory and task-specific test file
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_fha_002_auth.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FHA-002")
        test_cmd = validator._detect_test_command("TASK-FHA-002")

        assert "test_task_fha_002_auth.py" in test_cmd
        assert "pytest" in test_cmd
        assert "tests/ " not in test_cmd  # Should NOT include full directory

    def test_detect_test_command_returns_none_when_no_task_tests(self, tmp_worktree):
        """Test that None is returned when no task-specific tests found.

        When task_id is provided but no matching test files exist, _detect_test_command
        should return None to signal that independent verification should be skipped.
        This prevents running all tests from parallel tasks in shared worktrees.

        Replaces old fallback behavior (TASK-FIX-INDFB).
        """
        (tmp_worktree / "pyproject.toml").touch()

        # Create tests directory with other tests (not task-specific)
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_other_feature.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-XYZ-999")
        test_cmd = validator._detect_test_command("TASK-XYZ-999")

        # Should return None (skip verification) instead of falling back to full suite
        assert test_cmd is None

    def test_detect_test_command_without_task_id(self, tmp_worktree):
        """Test original behavior when task_id is None."""
        (tmp_worktree / "pyproject.toml").touch()

        validator = CoachValidator(str(tmp_worktree))  # No task_id
        test_cmd = validator._detect_test_command(None)

        assert test_cmd == "pytest tests/ -v --tb=short"

    def test_detect_test_command_multiple_matching_files(self, tmp_worktree):
        """Test handling of multiple task-specific test files."""
        (tmp_worktree / "pyproject.toml").touch()

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_fha_002_auth.py").touch()
        (tests_dir / "test_task_fha_002_validation.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FHA-002")
        test_cmd = validator._detect_test_command("TASK-FHA-002")

        # Both files should be included
        assert "test_task_fha_002_auth.py" in test_cmd
        assert "test_task_fha_002_validation.py" in test_cmd

    def test_run_independent_tests_uses_task_specific_command(self, tmp_worktree):
        """Test that run_independent_tests uses task-specific command when available."""
        (tmp_worktree / "pyproject.toml").touch()

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_abc_001.py").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1 passed", stderr="")

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-ABC-001")
            result = validator.run_independent_tests()

        # Verify task-specific test file was used.
        # pytest commands are now passed as a list (sys.executable -m pytest ...) so
        # we check membership across the joined string.
        call_args = mock_run.call_args[0][0]
        call_args_str = " ".join(call_args) if isinstance(call_args, list) else call_args
        assert "test_task_abc_001.py" in call_args_str
        assert "tests/ " not in call_args_str  # Full directory not used

    def test_constructor_stores_task_id(self, tmp_worktree):
        """Test that CoachValidator stores task_id in constructor."""
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-TEST-001")

        assert validator.task_id == "TASK-TEST-001"

    def test_constructor_task_id_defaults_to_none(self, tmp_worktree):
        """Test that task_id defaults to None."""
        validator = CoachValidator(str(tmp_worktree))

        assert validator.task_id is None

    def test_detect_test_command_with_special_characters_in_task_id(self, tmp_worktree):
        """Test task ID conversion handles various formats."""
        validator = CoachValidator(str(tmp_worktree))

        # Test various task ID formats
        assert validator._task_id_to_pattern_prefix("TASK-FIX-INDTEST") == "task_fix_indtest"
        assert validator._task_id_to_pattern_prefix("TASK-REV-FB25") == "task_rev_fb25"
        assert validator._task_id_to_pattern_prefix("TASK-E01-A3F2") == "task_e01_a3f2"

    def test_run_independent_tests_skips_when_no_task_tests(self, tmp_worktree):
        """Test that run_independent_tests skips when no task-specific tests found.

        When task_id is provided but no matching test files exist, independent test
        verification should be skipped instead of running all tests (which would
        include tests from other parallel tasks).

        This is the fix for TASK-FIX-INDFB.
        """
        (tmp_worktree / "pyproject.toml").touch()

        # Create tests directory with other tests (not task-specific)
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_other_feature.py").touch()

        # DO NOT mock subprocess.run - we want to verify tests are NOT run
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-XYZ-999")
        result = validator.run_independent_tests()

        # Should skip verification with descriptive result
        assert result.tests_passed is True
        assert result.test_command == "skipped"
        assert "no task-specific tests found" in result.test_output_summary.lower()
        assert "TASK-XYZ-999" in result.test_output_summary
        assert result.duration_seconds == 0.0

    def test_run_independent_tests_still_runs_when_task_tests_exist(self, tmp_worktree):
        """Test that run_independent_tests runs when task-specific tests ARE found.

        Ensure the skip behavior doesn't affect normal operation when tests exist.
        """
        (tmp_worktree / "pyproject.toml").touch()

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_xyz_999_feature.py").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1 passed", stderr="")

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-XYZ-999")
            result = validator.run_independent_tests()

        # Should actually run the tests
        assert result.test_command != "skipped"
        assert "test_task_xyz_999_feature.py" in result.test_command
        mock_run.assert_called_once()

    def test_run_independent_tests_without_task_id_runs_full_suite(self, tmp_worktree):
        """Test that run_independent_tests runs full suite when task_id is None.

        When no task_id is provided (standalone mode), should run full test suite.
        """
        (tmp_worktree / "pyproject.toml").touch()

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_something.py").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="5 passed", stderr="")

            validator = CoachValidator(str(tmp_worktree))  # No task_id
            result = validator.run_independent_tests()

        # Should run full test suite
        assert result.test_command == "pytest tests/ -v --tb=short"
        mock_run.assert_called_once()


# ============================================================================
# Recursive Test Glob Tests (TASK-FIX-93B1)
# ============================================================================


class TestRecursiveTestGlob:
    """Test recursive glob pattern for task-specific test detection.

    Verifies that _detect_test_command finds tests in nested subdirectories
    (e.g., tests/health/, tests/api/, tests/unit/) via the recursive
    tests/**/test_{prefix}*.py glob pattern.

    Fix for: TASK-FIX-93B1 (P0 from TASK-REV-93E1)
    """

    def test_finds_tests_in_nested_health_directory(self, tmp_worktree):
        """Test that tests in tests/health/ subdirectory are found."""
        (tmp_worktree / "pyproject.toml").touch()

        # Create nested test directory
        health_dir = tmp_worktree / "tests" / "health"
        health_dir.mkdir(parents=True)
        (health_dir / "test_task_db_006_database_health.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DB-006")
        test_cmd = validator._detect_test_command("TASK-DB-006")

        assert test_cmd is not None
        assert "test_task_db_006_database_health.py" in test_cmd
        assert "pytest" in test_cmd

    def test_finds_tests_in_nested_api_directory(self, tmp_worktree):
        """Test that tests in tests/api/ subdirectory are found."""
        (tmp_worktree / "pyproject.toml").touch()

        api_dir = tmp_worktree / "tests" / "api"
        api_dir.mkdir(parents=True)
        (api_dir / "test_task_foo_001_endpoints.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FOO-001")
        test_cmd = validator._detect_test_command("TASK-FOO-001")

        assert test_cmd is not None
        assert "test_task_foo_001_endpoints.py" in test_cmd

    def test_finds_tests_in_deeply_nested_directory(self, tmp_worktree):
        """Test that tests in deeply nested directories are found."""
        (tmp_worktree / "pyproject.toml").touch()

        deep_dir = tmp_worktree / "tests" / "unit" / "models"
        deep_dir.mkdir(parents=True)
        (deep_dir / "test_task_abc_001_model.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-ABC-001")
        test_cmd = validator._detect_test_command("TASK-ABC-001")

        assert test_cmd is not None
        assert "test_task_abc_001_model.py" in test_cmd

    def test_still_finds_tests_in_flat_directory(self, tmp_worktree):
        """Test that flat tests/ directory tests are still found (** matches zero dirs)."""
        (tmp_worktree / "pyproject.toml").touch()

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_foo_001_basic.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FOO-001")
        test_cmd = validator._detect_test_command("TASK-FOO-001")

        assert test_cmd is not None
        assert "test_task_foo_001_basic.py" in test_cmd

    def test_finds_tests_across_multiple_nested_dirs(self, tmp_worktree):
        """Test that tests spread across multiple nested dirs are all found."""
        (tmp_worktree / "pyproject.toml").touch()

        # Create tests in multiple subdirectories
        for subdir in ["unit", "integration"]:
            nested = tmp_worktree / "tests" / subdir
            nested.mkdir(parents=True)

        (tmp_worktree / "tests" / "unit" / "test_task_xyz_001_unit.py").touch()
        (tmp_worktree / "tests" / "integration" / "test_task_xyz_001_integ.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-XYZ-001")
        test_cmd = validator._detect_test_command("TASK-XYZ-001")

        assert test_cmd is not None
        assert "test_task_xyz_001_unit.py" in test_cmd
        assert "test_task_xyz_001_integ.py" in test_cmd

    def test_no_match_in_nested_returns_none(self, tmp_worktree):
        """Test that no matches in any directory still returns None."""
        (tmp_worktree / "pyproject.toml").touch()

        # Create nested dirs with non-matching tests
        health_dir = tmp_worktree / "tests" / "health"
        health_dir.mkdir(parents=True)
        (health_dir / "test_task_other_999.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DB-006")
        test_cmd = validator._detect_test_command("TASK-DB-006")

        assert test_cmd is None


# ============================================================================
# Primary Test Detection via task_work_results (TASK-FIX-TDPR)
# ============================================================================


class TestPrimaryTestDetection:
    """Tests for detecting test files from task_work_results (primary path).

    The primary detection path extracts test files from task_work_results
    files_created/files_modified lists (already in memory). The task-ID
    glob pattern is kept as a fallback for when results aren't available.
    """

    def test_detect_tests_from_results_finds_created_tests(self, tmp_worktree):
        """Test that test files in files_created list are detected."""
        # Create the test file in the worktree
        test_dir = tmp_worktree / "tests" / "orchestrator"
        test_dir.mkdir(parents=True)
        (test_dir / "test_mcp_design_extractor.py").write_text("def test_x(): pass")

        task_work_results = {
            "files_created": [
                "guardkit/orchestrator/mcp_design_extractor.py",
                "tests/orchestrator/test_mcp_design_extractor.py",
            ],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-002")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is not None
        assert "test_mcp_design_extractor.py" in result
        assert "pytest" in result

    def test_detect_tests_from_results_finds_modified_tests(self, tmp_worktree):
        """Test that test files in files_modified list are detected."""
        test_dir = tmp_worktree / "tests" / "unit"
        test_dir.mkdir(parents=True)
        (test_dir / "test_design_integration.py").write_text("def test_y(): pass")

        task_work_results = {
            "files_created": [],
            "files_modified": ["tests/unit/test_design_integration.py"],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-007")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is not None
        assert "test_design_integration.py" in result

    def test_detect_tests_from_results_ignores_nonexistent_files(self, tmp_worktree):
        """Test that test files listed but not present on disk are skipped."""
        # Don't create the file on disk
        task_work_results = {
            "files_created": ["tests/test_nonexistent.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-003")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is None

    def test_detect_tests_from_results_returns_none_when_no_tests(self, tmp_worktree):
        """Test that None is returned when results have no test files."""
        task_work_results = {
            "files_created": ["guardkit/models/frontmatter.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-001")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is None

    def test_detect_tests_from_results_handles_suffix_test_naming(self, tmp_worktree):
        """Test detection of *_test.py naming convention."""
        test_dir = tmp_worktree / "tests"
        test_dir.mkdir(parents=True)
        (test_dir / "browser_verifier_test.py").write_text("def test_a(): pass")

        task_work_results = {
            "files_created": ["tests/browser_verifier_test.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-009")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is not None
        assert "browser_verifier_test.py" in result

    def test_detect_tests_from_results_deduplicates_files(self, tmp_worktree):
        """Test that duplicate test files across created/modified are deduplicated."""
        test_dir = tmp_worktree / "tests"
        test_dir.mkdir(parents=True)
        (test_dir / "test_detector.py").write_text("def test_a(): pass")

        task_work_results = {
            "files_created": ["tests/test_detector.py"],
            "files_modified": ["tests/test_detector.py"],  # Same file in both lists
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-010")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is not None
        # Should appear only once
        assert result.count("test_detector.py") == 1

    def test_detect_test_command_uses_results_as_primary(self, tmp_worktree):
        """Test that _detect_test_command uses task_work_results as primary source."""
        (tmp_worktree / "pyproject.toml").touch()

        # No task-ID-named tests exist
        tests_dir = tmp_worktree / "tests" / "unit"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_mcp_extractor.py").write_text("def test_x(): pass")

        task_work_results = {
            "files_created": ["tests/unit/test_mcp_extractor.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-002")
        test_cmd = validator._detect_test_command(
            "TASK-DM-002", task_work_results=task_work_results
        )

        assert test_cmd is not None
        assert "test_mcp_extractor.py" in test_cmd
        assert "pytest" in test_cmd

    def test_detect_test_command_falls_back_to_glob_when_no_results(self, tmp_worktree):
        """Test that _detect_test_command falls back to glob when task_work_results is None."""
        (tmp_worktree / "pyproject.toml").touch()

        # Create task-ID-named test file (matches glob pattern)
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_task_dm_002_main.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-002")
        test_cmd = validator._detect_test_command("TASK-DM-002", task_work_results=None)

        assert test_cmd is not None
        assert "test_task_dm_002_main.py" in test_cmd

    def test_detect_test_command_falls_back_to_glob_when_results_have_no_tests(self, tmp_worktree):
        """Test that _detect_test_command falls back to glob when results have no test files."""
        (tmp_worktree / "pyproject.toml").touch()

        # Create task-ID-named test file (matches glob pattern)
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_task_dm_002_main.py").touch()

        # Results have no test files
        task_work_results = {
            "files_created": ["guardkit/models/frontmatter.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-002")
        test_cmd = validator._detect_test_command(
            "TASK-DM-002", task_work_results=task_work_results
        )

        # Should fall back to glob pattern since results had no tests
        assert test_cmd is not None
        assert "test_task_dm_002_main.py" in test_cmd

    def test_detect_test_command_results_take_priority_over_glob(self, tmp_worktree):
        """Test that task_work_results take priority over task-ID glob pattern."""
        (tmp_worktree / "pyproject.toml").touch()

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir(parents=True)

        # Create task-ID-named test file (matches glob pattern)
        (tests_dir / "test_task_dm_002_main.py").touch()

        # Create a different test file referenced in results
        (tests_dir / "test_mcp_extractor.py").write_text("def test_x(): pass")

        task_work_results = {
            "files_created": ["tests/test_mcp_extractor.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-002")
        test_cmd = validator._detect_test_command(
            "TASK-DM-002", task_work_results=task_work_results
        )

        # Should use the results-based test, not the glob pattern
        assert "test_mcp_extractor.py" in test_cmd
        assert "test_task_dm_002_main.py" not in test_cmd

    def test_detect_test_command_returns_none_when_no_tests_anywhere(self, tmp_worktree):
        """Test None returned when neither results nor glob find tests."""
        (tmp_worktree / "pyproject.toml").touch()

        # No tests exist at all
        task_work_results = {
            "files_created": ["guardkit/models/frontmatter.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-002")
        test_cmd = validator._detect_test_command(
            "TASK-DM-002", task_work_results=task_work_results
        )

        assert test_cmd is None


# ============================================================================
# collect_ignore_glob filtering (TASK-FIX-7F48)
# ============================================================================


class TestCollectIgnoreGlobFiltering:
    """Tests for _load_collect_ignore_glob and collect_ignore_glob filtering in _detect_tests_from_results."""

    def _make_conftest(self, worktree: Path, patterns: list) -> None:
        patterns_repr = ", ".join(f'"{p}"' for p in patterns)
        (worktree / "conftest.py").write_text(
            f'collect_ignore_glob = [{patterns_repr}]\n'
        )

    def test_load_collect_ignore_glob_returns_patterns(self, tmp_worktree):
        """Patterns are extracted from root conftest.py."""
        self._make_conftest(
            tmp_worktree,
            ["guardkit/eval/workspaces/*/tests/*", "templates/*/tests/*"],
        )
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FIX-7F48")
        patterns = validator._load_collect_ignore_glob()
        assert patterns == [
            "guardkit/eval/workspaces/*/tests/*",
            "templates/*/tests/*",
        ]

    def test_load_collect_ignore_glob_no_conftest(self, tmp_worktree):
        """Returns empty list when conftest.py does not exist."""
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FIX-7F48")
        assert validator._load_collect_ignore_glob() == []

    def test_load_collect_ignore_glob_no_assignment(self, tmp_worktree):
        """Returns empty list when conftest.py has no collect_ignore_glob."""
        (tmp_worktree / "conftest.py").write_text(
            "import sys\ncollect_ignore = ['some_file.py']\n"
        )
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FIX-7F48")
        assert validator._load_collect_ignore_glob() == []

    def test_load_collect_ignore_glob_empty_list(self, tmp_worktree):
        """Returns empty list when collect_ignore_glob is assigned an empty list."""
        (tmp_worktree / "conftest.py").write_text("collect_ignore_glob = []\n")
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FIX-7F48")
        assert validator._load_collect_ignore_glob() == []

    def test_load_collect_ignore_glob_bad_syntax(self, tmp_worktree):
        """Returns empty list (no crash) when conftest.py has a syntax error."""
        (tmp_worktree / "conftest.py").write_text("collect_ignore_glob = [unterminated\n")
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FIX-7F48")
        assert validator._load_collect_ignore_glob() == []

    def test_detect_tests_filters_excluded_paths(self, tmp_worktree):
        """Test files matching collect_ignore_glob are excluded from pytest command."""
        # Set up conftest with exclusion patterns
        self._make_conftest(
            tmp_worktree,
            ["guardkit/eval/workspaces/*/tests/*", "templates/*/tests/*"],
        )
        # Create two test files: one legitimate, one matching exclusion
        legit_dir = tmp_worktree / "tests" / "unit"
        legit_dir.mkdir(parents=True)
        (legit_dir / "test_feature.py").write_text("def test_x(): pass")

        workspace_dir = tmp_worktree / "guardkit" / "eval" / "workspaces" / "TASK-001" / "tests"
        workspace_dir.mkdir(parents=True)
        (workspace_dir / "test_workspace.py").write_text("def test_y(): pass")

        task_work_results = {
            "files_created": [
                "tests/unit/test_feature.py",
                "guardkit/eval/workspaces/TASK-001/tests/test_workspace.py",
            ],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FIX-7F48")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is not None
        assert "test_feature.py" in result
        assert "test_workspace.py" not in result

    def test_detect_tests_no_filtering_without_conftest(self, tmp_worktree):
        """Without conftest.py all matching test files are included."""
        workspace_dir = tmp_worktree / "guardkit" / "eval" / "workspaces" / "TASK-001" / "tests"
        workspace_dir.mkdir(parents=True)
        (workspace_dir / "test_workspace.py").write_text("def test_y(): pass")

        task_work_results = {
            "files_created": [
                "guardkit/eval/workspaces/TASK-001/tests/test_workspace.py",
            ],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FIX-7F48")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is not None
        assert "test_workspace.py" in result

    def test_detect_tests_no_filtering_with_empty_patterns(self, tmp_worktree):
        """Empty collect_ignore_glob means no files are filtered."""
        (tmp_worktree / "conftest.py").write_text("collect_ignore_glob = []\n")
        test_dir = tmp_worktree / "tests"
        test_dir.mkdir(parents=True)
        (test_dir / "test_something.py").write_text("def test_a(): pass")

        task_work_results = {
            "files_created": ["tests/test_something.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FIX-7F48")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is not None
        assert "test_something.py" in result

    def test_detect_tests_returns_none_when_all_excluded(self, tmp_worktree):
        """Returns None when all test files are excluded by collect_ignore_glob."""
        self._make_conftest(tmp_worktree, ["guardkit/eval/workspaces/*/tests/*"])
        workspace_dir = tmp_worktree / "guardkit" / "eval" / "workspaces" / "X" / "tests"
        workspace_dir.mkdir(parents=True)
        (workspace_dir / "test_only.py").write_text("def test_z(): pass")

        task_work_results = {
            "files_created": ["guardkit/eval/workspaces/X/tests/test_only.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FIX-7F48")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is None

    def test_detect_tests_normalises_absolute_paths_before_matching(self, tmp_worktree):
        """Absolute paths are normalised to relative before fnmatch pattern matching."""
        self._make_conftest(tmp_worktree, ["guardkit/eval/workspaces/*/tests/*"])
        workspace_dir = tmp_worktree / "guardkit" / "eval" / "workspaces" / "ABS" / "tests"
        workspace_dir.mkdir(parents=True)
        (workspace_dir / "test_abs.py").write_text("def test_abs(): pass")

        # Pass as absolute path (as the Player would emit)
        abs_path = str(workspace_dir / "test_abs.py")
        task_work_results = {
            "files_created": [abs_path],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FIX-7F48")
        result = validator._detect_tests_from_results(task_work_results)

        # Absolute path normalised → matches pattern → excluded
        assert result is None


# ============================================================================
# Test Cumulative Diff Fallback (TASK-ABF-004)
# ============================================================================


class TestCumulativeDiffFallback:
    """Test cumulative git diff fallback for test detection across checkpoints."""

    def test_cumulative_diff_finds_tests_across_checkpoints(self, tmp_worktree):
        """Cumulative diff finds test files created in earlier turns."""
        # Set up checkpoints.json
        checkpoints_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-CD-001"
        checkpoints_dir.mkdir(parents=True)
        checkpoints_data = {
            "checkpoints": [
                {"commit_hash": "abc123", "turn": 1, "phase": "implementation"}
            ]
        }
        (checkpoints_dir / "checkpoints.json").write_text(
            json.dumps(checkpoints_data, indent=2)
        )

        # Create test files on disk
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir(parents=True)
        test_file = tests_dir / "test_oauth.py"
        test_file.write_text("def test_oauth(): pass")

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-CD-001")

        # Mock git commands
        with patch("subprocess.run") as mock_run:
            # First call: git rev-parse abc123~1 -> returns parent hash
            # Second call: git diff --name-only parent HEAD -> returns test files
            mock_run.side_effect = [
                MagicMock(
                    returncode=0,
                    stdout="parent_hash_xyz",
                    stderr="",
                ),
                MagicMock(
                    returncode=0,
                    stdout="tests/test_oauth.py\n",
                    stderr="",
                ),
            ]

            # Call with NO task_work_results (primary fails)
            # and pattern that won't match (glob fails)
            cmd = validator._detect_test_command(task_id="TASK-CD-001")

            # Should find test via cumulative diff
            assert cmd is not None
            assert "pytest" in cmd
            assert "tests/test_oauth.py" in cmd
            assert "-v" in cmd
            assert "--tb=short" in cmd

    def test_cumulative_diff_excludes_pre_task_files(self, tmp_worktree):
        """Cumulative diff excludes files that don't exist on disk."""
        # Set up checkpoints.json
        checkpoints_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-CD-002"
        checkpoints_dir.mkdir(parents=True)
        checkpoints_data = {
            "checkpoints": [
                {"commit_hash": "def456", "turn": 1, "phase": "implementation"}
            ]
        }
        (checkpoints_dir / "checkpoints.json").write_text(
            json.dumps(checkpoints_data, indent=2)
        )

        # NOTE: test file is NOT created on disk

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-CD-002")

        with patch("subprocess.run") as mock_run:
            # Mock git to return test file that doesn't exist on disk
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="parent_hash_456", stderr=""),
                MagicMock(returncode=0, stdout="tests/test_deleted.py\n", stderr=""),
            ]

            cmd = validator._detect_test_command(task_id="TASK-CD-002")

            # Should return None because file doesn't exist
            assert cmd is None

    def test_cumulative_diff_handles_no_checkpoints(self, tmp_worktree):
        """Cumulative diff gracefully handles missing checkpoints file."""
        # NOTE: No checkpoints.json created

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-CD-003")

        # No mocking needed - should fail gracefully
        cmd = validator._detect_test_command(task_id="TASK-CD-003")

        # Should return None (no checkpoints file)
        assert cmd is None

    def test_cumulative_diff_handles_git_failure(self, tmp_worktree):
        """Cumulative diff gracefully handles git command failures."""
        # Set up checkpoints.json
        checkpoints_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-CD-004"
        checkpoints_dir.mkdir(parents=True)
        checkpoints_data = {
            "checkpoints": [
                {"commit_hash": "ghi789", "turn": 1, "phase": "implementation"}
            ]
        }
        (checkpoints_dir / "checkpoints.json").write_text(
            json.dumps(checkpoints_data, indent=2)
        )

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-CD-004")

        with patch("subprocess.run") as mock_run:
            # Mock git rev-parse to fail
            mock_run.return_value = MagicMock(
                returncode=128,
                stdout="",
                stderr="fatal: bad revision",
            )

            cmd = validator._detect_test_command(task_id="TASK-CD-004")

            # Should return None (git command failed)
            assert cmd is None


# ============================================================================
# Test Player Report Accumulation (TASK-FIX-70F3)
# ============================================================================


class TestPlayerReportAccumulation:
    """Tests for quinary fallback: scan prior player_turn_N.json reports.

    Source: TASK-FIX-70F3 — finding F5 from TASK-REV-7EB05.

    On iterative fix turns (turn >= 2) the Player modifies source files but
    does not re-create the test file, so files_created/files_modified in the
    current task_work_results will not contain the test file.  The quinary
    fallback scans prior player_turn_N.json files to recover the test file
    list accumulated from earlier turns.
    """

    def _make_player_report(self, files_created=None, files_modified=None):
        """Return a minimal player report dict."""
        return {
            "files_created": files_created or [],
            "files_modified": files_modified or [],
            "completion_promises": [],
        }

    def test_turn2_finds_test_from_turn1_player_report(self, tmp_worktree):
        """AC: turn 2 reuses test file detected on turn 1 via player_turn_1.json."""
        task_id = "TASK-PA-001"
        player_dir = tmp_worktree / ".guardkit" / "autobuild" / task_id
        player_dir.mkdir(parents=True)

        # Test file was created on turn 1
        tests_dir = tmp_worktree / "tests" / "users"
        tests_dir.mkdir(parents=True)
        test_file = tests_dir / "test_users.py"
        test_file.write_text("def test_users(): pass")

        # Write player_turn_1.json with the test file in files_created
        report = self._make_player_report(files_created=["tests/users/test_users.py"])
        (player_dir / "player_turn_1.json").write_text(json.dumps(report))

        # Current turn 2: task_work_results has no test files (only source fix)
        current_results = {
            "files_created": [],
            "files_modified": ["guardkit/users/service.py"],
            "completion_promises": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id=task_id)
        cmd = validator._detect_test_command(
            task_id=task_id,
            task_work_results=current_results,
            turn=2,
        )

        assert cmd is not None, "Expected test command from prior player report"
        assert "pytest" in cmd
        assert "tests/users/test_users.py" in cmd

    def test_turn1_does_not_scan_prior_reports(self, tmp_worktree):
        """On turn 1 there are no prior reports to scan; quinary fallback is a no-op."""
        task_id = "TASK-PA-002"
        player_dir = tmp_worktree / ".guardkit" / "autobuild" / task_id
        player_dir.mkdir(parents=True)

        # Even if a stale player_turn_0.json existed, it should never be read
        # (range(0, 0, -1) is empty).  No test files on disk either.
        current_results = {
            "files_created": [],
            "files_modified": ["guardkit/users/service.py"],
            "completion_promises": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id=task_id)
        cmd = validator._detect_test_command(
            task_id=task_id,
            task_work_results=current_results,
            turn=1,
        )

        # No test files anywhere → should return None
        assert cmd is None

    def test_accumulated_test_file_must_exist_on_disk(self, tmp_worktree):
        """AC: accumulated test files are only used if they still exist on disk."""
        task_id = "TASK-PA-003"
        player_dir = tmp_worktree / ".guardkit" / "autobuild" / task_id
        player_dir.mkdir(parents=True)

        # Write player_turn_1.json referencing a file that no longer exists
        report = self._make_player_report(
            files_created=["tests/test_deleted.py"]
        )
        (player_dir / "player_turn_1.json").write_text(json.dumps(report))

        # File is NOT present on disk
        current_results = {
            "files_created": [],
            "files_modified": ["guardkit/models/user.py"],
            "completion_promises": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id=task_id)
        cmd = validator._detect_test_command(
            task_id=task_id,
            task_work_results=current_results,
            turn=2,
        )

        assert cmd is None, "Should not reference deleted test files"

    def test_accumulation_is_per_task(self, tmp_worktree):
        """AC: accumulated test files from a different task are not used."""
        # Create player report for TASK-PA-OTHER with a test file
        other_task_id = "TASK-PA-OTHER"
        other_dir = tmp_worktree / ".guardkit" / "autobuild" / other_task_id
        other_dir.mkdir(parents=True)
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir(parents=True)
        other_test = tests_dir / "test_other.py"
        other_test.write_text("def test_other(): pass")
        report = self._make_player_report(files_created=["tests/test_other.py"])
        (other_dir / "player_turn_1.json").write_text(json.dumps(report))

        # Our task has no player report
        our_task_id = "TASK-PA-004"
        current_results = {
            "files_created": [],
            "files_modified": ["guardkit/models/user.py"],
            "completion_promises": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id=our_task_id)
        cmd = validator._detect_test_command(
            task_id=our_task_id,
            task_work_results=current_results,
            turn=2,
        )

        # Should not find TASK-PA-OTHER's report; our task directory is empty
        assert cmd is None

    def test_turn_not_provided_quinary_skipped(self, tmp_worktree):
        """When turn is not provided, quinary fallback is not attempted."""
        task_id = "TASK-PA-005"
        player_dir = tmp_worktree / ".guardkit" / "autobuild" / task_id
        player_dir.mkdir(parents=True)

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir(parents=True)
        test_file = tests_dir / "test_feature.py"
        test_file.write_text("def test_feature(): pass")

        report = self._make_player_report(files_created=["tests/test_feature.py"])
        (player_dir / "player_turn_1.json").write_text(json.dumps(report))

        current_results = {
            "files_created": [],
            "files_modified": ["guardkit/feature.py"],
            "completion_promises": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id=task_id)
        # No `turn` argument → quinary fallback is skipped
        cmd = validator._detect_test_command(
            task_id=task_id,
            task_work_results=current_results,
        )

        assert cmd is None

    def test_scans_multiple_prior_turns_newest_first(self, tmp_worktree):
        """Scans turns in descending order; uses the most recent report with tests."""
        task_id = "TASK-PA-006"
        player_dir = tmp_worktree / ".guardkit" / "autobuild" / task_id
        player_dir.mkdir(parents=True)

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir(parents=True)

        # Turn 1: test file A
        test_a = tests_dir / "test_feature_a.py"
        test_a.write_text("def test_a(): pass")
        report1 = self._make_player_report(files_created=["tests/test_feature_a.py"])
        (player_dir / "player_turn_1.json").write_text(json.dumps(report1))

        # Turn 2: no test files (fix turn), but turn 2 report exists
        report2 = self._make_player_report(files_modified=["guardkit/feature.py"])
        (player_dir / "player_turn_2.json").write_text(json.dumps(report2))

        # Current is turn 3; no test in current results either
        current_results = {
            "files_created": [],
            "files_modified": ["guardkit/feature.py"],
            "completion_promises": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id=task_id)
        cmd = validator._detect_test_command(
            task_id=task_id,
            task_work_results=current_results,
            turn=3,
        )

        # Should fall through turn_2 (no tests there) and find test from turn_1
        assert cmd is not None
        assert "tests/test_feature_a.py" in cmd

    def test_current_turn_results_take_priority_over_prior_reports(self, tmp_worktree):
        """AC: existing test detection priority is preserved (current-turn wins)."""
        task_id = "TASK-PA-007"
        player_dir = tmp_worktree / ".guardkit" / "autobuild" / task_id
        player_dir.mkdir(parents=True)

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir(parents=True)

        # Prior turn 1 report references test_old.py
        test_old = tests_dir / "test_old.py"
        test_old.write_text("def test_old(): pass")
        report1 = self._make_player_report(files_created=["tests/test_old.py"])
        (player_dir / "player_turn_1.json").write_text(json.dumps(report1))

        # Current turn 2: task_work_results has test_new.py in files_created
        test_new = tests_dir / "test_new.py"
        test_new.write_text("def test_new(): pass")
        current_results = {
            "files_created": ["tests/test_new.py"],
            "files_modified": [],
            "completion_promises": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id=task_id)
        cmd = validator._detect_test_command(
            task_id=task_id,
            task_work_results=current_results,
            turn=2,
        )

        # Primary (current results) should win; test_old.py should NOT appear
        assert cmd is not None
        assert "tests/test_new.py" in cmd
        assert "tests/test_old.py" not in cmd

    def test_corrupted_player_report_skipped_gracefully(self, tmp_worktree):
        """Corrupted player_turn_N.json is skipped without crashing."""
        task_id = "TASK-PA-008"
        player_dir = tmp_worktree / ".guardkit" / "autobuild" / task_id
        player_dir.mkdir(parents=True)

        # Write corrupt JSON
        (player_dir / "player_turn_1.json").write_text("not valid json {")

        current_results = {
            "files_created": [],
            "files_modified": ["guardkit/feature.py"],
            "completion_promises": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id=task_id)
        # Should not raise; should just return None
        cmd = validator._detect_test_command(
            task_id=task_id,
            task_work_results=current_results,
            turn=2,
        )

        assert cmd is None


# ============================================================================
# Test _classify_test_failure — psycopg2 misclassification fix (TASK-FIX-A7F1)
# ============================================================================


class TestClassifyTestFailurePsycopg2:
    """Tests for the psycopg2 misclassification fix in _classify_test_failure.

    Source: TASK-FIX-A7F1 — finding F2 from TASK-REV-7EB05.
    """

    def test_psycopg2_module_not_found_no_context_is_ambiguous(self, tmp_worktree):
        """AC2: psycopg2 ModuleNotFoundError with no bootstrap context → ambiguous.

        Previously classified as ("infrastructure", "high"), which gave the
        Player wrong advice (mock fixtures / SQLite) instead of telling them to
        remove the wrong import.
        """
        validator = CoachValidator(str(tmp_worktree))
        output = (
            "FAILED tests/test_db.py::test_connect\n"
            "ModuleNotFoundError: No module named 'psycopg2'\n"
        )

        result = validator._classify_test_failure(output)

        assert result == ("infrastructure", "ambiguous"), (
            f"Expected ('infrastructure', 'ambiguous'), got {result!r}. "
            "psycopg2 ModuleNotFoundError without bootstrap context should not "
            "trigger conditional approval."
        )

    def test_psycopg2_module_not_found_with_bootstrap_context_is_code_error(
        self, tmp_worktree
    ):
        """AC3: psycopg2 ModuleNotFoundError + bootstrap context → code error.

        When the task declares infrastructure requirements (e.g. postgresql),
        a missing psycopg2 import is a Player code-choice error — they should
        be using asyncpg, not psycopg2.
        """
        validator = CoachValidator(str(tmp_worktree))
        output = (
            "FAILED tests/test_db.py::test_connect\n"
            "ModuleNotFoundError: No module named 'psycopg2'\n"
        )

        result = validator._classify_test_failure(
            output, requires_infrastructure=["postgresql"]
        )

        assert result == ("code", "high"), (
            f"Expected ('code', 'high'), got {result!r}. "
            "psycopg2 missing when bootstrap declares postgresql means the "
            "Player chose the wrong driver."
        )

    def test_asyncpg_module_not_found_is_infrastructure_high(self, tmp_worktree):
        """AC5: asyncpg ModuleNotFoundError → ('infrastructure', 'high').

        asyncpg remains in _KNOWN_SERVICE_CLIENT_LIBS so its absence is
        treated as a genuine infra/env issue regardless of bootstrap context.
        """
        validator = CoachValidator(str(tmp_worktree))
        output = (
            "FAILED tests/test_db.py::test_connect\n"
            "ModuleNotFoundError: No module named 'asyncpg'\n"
        )

        result = validator._classify_test_failure(output)

        assert result == ("infrastructure", "high"), (
            f"Expected ('infrastructure', 'high'), got {result!r}. "
            "asyncpg missing is a genuine infra dep issue."
        )

    def test_asyncpg_module_not_found_with_bootstrap_still_infrastructure(
        self, tmp_worktree
    ):
        """AC5: asyncpg missing + bootstrap context → still infrastructure high.

        asyncpg is the correct driver for the project (it's in
        _KNOWN_SERVICE_CLIENT_LIBS), so bootstrap context does not change the
        classification.
        """
        validator = CoachValidator(str(tmp_worktree))
        output = (
            "FAILED tests/test_db.py::test_connect\n"
            "ModuleNotFoundError: No module named 'asyncpg'\n"
        )

        result = validator._classify_test_failure(
            output, requires_infrastructure=["postgresql"]
        )

        assert result == ("infrastructure", "high"), (
            f"Expected ('infrastructure', 'high'), got {result!r}. "
            "asyncpg is the expected driver — bootstrap context should not "
            "downgrade to code error."
        )

    def test_psycopg2_connection_error_still_infrastructure_high(
        self, tmp_worktree
    ):
        """psycopg2 connection errors (not ModuleNotFoundError) remain high.

        When psycopg2 IS installed but the DB is unreachable, the error
        contains e.g. 'psycopg2.OperationalError' which should still be
        classified as infrastructure/high via _INFRA_HIGH_CONFIDENCE.
        """
        validator = CoachValidator(str(tmp_worktree))
        output = (
            "psycopg2.OperationalError: could not connect to server: "
            "Connection refused\n"
        )

        result = validator._classify_test_failure(output)

        assert result == ("infrastructure", "high"), (
            f"Expected ('infrastructure', 'high'), got {result!r}. "
            "A psycopg2 connection error (DB unreachable) is a genuine "
            "infrastructure failure."
        )

    def test_psycopg2_not_in_known_service_client_libs(self, tmp_worktree):
        """AC1: psycopg2 is no longer in _KNOWN_SERVICE_CLIENT_LIBS."""
        validator = CoachValidator(str(tmp_worktree))

        assert "psycopg2" not in validator._KNOWN_SERVICE_CLIENT_LIBS, (
            "psycopg2 must be removed from _KNOWN_SERVICE_CLIENT_LIBS to prevent "
            "ModuleNotFoundError from being auto-promoted to high confidence."
        )


# ============================================================================
# Test _classify_test_failure — SDK API error classification (TASK-FIX-d5e6)
# ============================================================================


class TestClassifyTestFailureSdkApiError:
    """Tests for SDK API error pattern matching in _classify_test_failure.

    Source: TASK-FIX-d5e6 — from TASK-REV-ED10.
    """

    def test_sdk_api_error_classified_correctly(self, tmp_worktree):
        """SDK API error: invalid_request → ('sdk_api_error', 'high')."""
        validator = CoachValidator(str(tmp_worktree))
        output = (
            "Error: SDK API error: invalid_request\n"
            "The model name is not valid for this endpoint.\n"
        )

        result = validator._classify_test_failure(output)

        assert result == ("sdk_api_error", "high"), (
            f"Expected ('sdk_api_error', 'high'), got {result!r}. "
            "SDK API error should be classified as sdk_api_error, not code."
        )

    def test_invalid_request_error_classified(self, tmp_worktree):
        """invalid_request_error pattern → ('sdk_api_error', 'high')."""
        validator = CoachValidator(str(tmp_worktree))
        output = "anthropic.BadRequestError: invalid_request_error: model not found"

        result = validator._classify_test_failure(output)

        assert result == ("sdk_api_error", "high"), (
            f"Expected ('sdk_api_error', 'high'), got {result!r}."
        )

    def test_assistant_message_error_classified(self, tmp_worktree):
        """AssistantMessage.error pattern → ('sdk_api_error', 'high')."""
        validator = CoachValidator(str(tmp_worktree))
        output = "AssistantMessage.error: The request was rejected by the API"

        result = validator._classify_test_failure(output)

        assert result == ("sdk_api_error", "high"), (
            f"Expected ('sdk_api_error', 'high'), got {result!r}."
        )

    def test_unrelated_error_not_classified_as_sdk(self, tmp_worktree):
        """Unrelated test failure should NOT match SDK API error patterns."""
        validator = CoachValidator(str(tmp_worktree))
        output = "AssertionError: expected 5, got 3"

        result = validator._classify_test_failure(output)

        assert result == ("code", "n/a"), (
            f"Expected ('code', 'n/a'), got {result!r}. "
            "Non-SDK errors should fall through to code classification."
        )


# ============================================================================
# Custom API Base URL Tests (TASK-FIX-f1a2)
# ============================================================================


class TestCustomApiBase:
    """Test _is_custom_api_base() and use_sdk bypass for non-Anthropic endpoints.

    When ANTHROPIC_BASE_URL points to a non-Anthropic server (e.g. vLLM),
    the SDK path should be bypassed in favour of the subprocess path.

    Fix for: TASK-FIX-f1a2 (from TASK-REV-ED10)
    """

    def test_custom_base_url_detected(self, tmp_worktree, monkeypatch):
        """ANTHROPIC_BASE_URL=http://localhost:8000 → _is_custom_api_base() returns True."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:8000")
        validator = CoachValidator(str(tmp_worktree))
        assert validator._is_custom_api_base() is True

    def test_anthropic_url_not_custom(self, tmp_worktree, monkeypatch):
        """ANTHROPIC_BASE_URL=https://api.anthropic.com → returns False."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        validator = CoachValidator(str(tmp_worktree))
        assert validator._is_custom_api_base() is False

    def test_anthropic_url_with_path_not_custom(self, tmp_worktree, monkeypatch):
        """ANTHROPIC_BASE_URL=https://api.anthropic.com/v1 → returns False."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
        validator = CoachValidator(str(tmp_worktree))
        assert validator._is_custom_api_base() is False

    def test_unset_base_url_not_custom(self, tmp_worktree, monkeypatch):
        """ANTHROPIC_BASE_URL unset → returns False."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        validator = CoachValidator(str(tmp_worktree))
        assert validator._is_custom_api_base() is False

    def test_empty_base_url_not_custom(self, tmp_worktree, monkeypatch):
        """ANTHROPIC_BASE_URL='' → returns False."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "")
        validator = CoachValidator(str(tmp_worktree))
        assert validator._is_custom_api_base() is False

    def test_use_sdk_false_when_custom_base(self, tmp_worktree, monkeypatch):
        """use_sdk is False when ANTHROPIC_BASE_URL points to a custom endpoint."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:8000")
        (tmp_worktree / "pyproject.toml").touch()
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_something.py").touch()

        validator = CoachValidator(str(tmp_worktree))
        validator._coach_test_execution = "sdk"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="5 passed", stderr="")
            result = validator.run_independent_tests()

        # Should have used subprocess path (not SDK) due to custom base URL
        mock_run.assert_called_once()
        assert result.tests_passed is True

    def test_use_sdk_true_when_no_custom_base(self, tmp_worktree, monkeypatch):
        """use_sdk remains True when ANTHROPIC_BASE_URL is unset (default Anthropic API)."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        (tmp_worktree / "pyproject.toml").touch()
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_something.py").touch()

        validator = CoachValidator(str(tmp_worktree))
        validator._coach_test_execution = "sdk"

        # When SDK path is taken, it will try to import claude_agent_sdk
        # which won't be available in test environment, so it raises.
        # The fact that it attempts the SDK path confirms use_sdk=True.
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="5 passed", stderr="")
            # Mock the SDK import to verify it's attempted
            with patch.object(validator, "_run_tests_via_sdk", side_effect=Exception("SDK mock")):
                # SDK fails, falls through to subprocess
                result = validator.run_independent_tests()

        # The subprocess fallback should have been used after SDK failure
        mock_run.assert_called_once()


# ============================================================================
# Coach Test Model Configuration (TASK-FIX-g7h8)
# ============================================================================


class TestCoachTestModelEnvVar:
    """Test GUARDKIT_COACH_TEST_MODEL environment variable support."""

    def test_get_coach_test_model_returns_none_when_unset(self, tmp_worktree):
        """When env var is not set, _get_coach_test_model returns None."""
        validator = CoachValidator(str(tmp_worktree))
        with patch.dict("os.environ", {}, clear=True):
            result = validator._get_coach_test_model()
        assert result is None

    def test_get_coach_test_model_returns_value_when_set(self, tmp_worktree):
        """When env var is set, _get_coach_test_model returns the value."""
        validator = CoachValidator(str(tmp_worktree))
        with patch.dict("os.environ", {"GUARDKIT_COACH_TEST_MODEL": "claude-haiku-4-5-20251001"}):
            result = validator._get_coach_test_model()
        assert result == "claude-haiku-4-5-20251001"

    def test_get_coach_test_model_returns_none_for_empty_string(self, tmp_worktree):
        """When env var is set to empty string, _get_coach_test_model returns None."""
        validator = CoachValidator(str(tmp_worktree))
        with patch.dict("os.environ", {"GUARDKIT_COACH_TEST_MODEL": ""}):
            result = validator._get_coach_test_model()
        assert result is None

    # ------------------------------------------------------------------
    # TASK-FIX-LGFM3: orchestrator model_name threaded through CoachValidator
    # ------------------------------------------------------------------

    def test_get_coach_test_model_falls_back_to_orchestrator_model(
        self, tmp_worktree
    ):
        """When env var is unset, falls back to ``model_name`` passed by orchestrator.

        Regression for F12 — without this fallback the LangGraph harness gets
        ``model=None`` for ``role='coach_test'`` even though the orchestrator
        was launched with ``--model qwen36-workhorse``.
        """
        validator = CoachValidator(
            str(tmp_worktree), model_name="openai:qwen36-workhorse"
        )
        with patch.dict("os.environ", {}, clear=True):
            result = validator._get_coach_test_model()
        assert result == "openai:qwen36-workhorse"

    def test_get_coach_test_model_env_var_overrides_orchestrator_model(
        self, tmp_worktree
    ):
        """Env var keeps precedence over orchestrator-supplied ``model_name``.

        Operators must be able to override the orchestrator-wide model for
        Coach test execution alone (e.g. to use a cheap Anthropic model for
        Coach tests while the main loop runs against vLLM).
        """
        validator = CoachValidator(
            str(tmp_worktree), model_name="openai:qwen36-workhorse"
        )
        with patch.dict(
            "os.environ", {"GUARDKIT_COACH_TEST_MODEL": "claude-haiku-4-5-20251001"}
        ):
            result = validator._get_coach_test_model()
        assert result == "claude-haiku-4-5-20251001"

    def test_get_coach_test_model_returns_none_when_no_source_set(
        self, tmp_worktree
    ):
        """Returns None when neither env var nor orchestrator model is provided.

        Pins that omitting ``model_name`` from construction does NOT introduce
        a hardcoded default — the no-orchestrator-model path stays a clean
        ``None``, matching the LGFM2 precedent for the inline-implement site.
        """
        validator = CoachValidator(str(tmp_worktree))
        with patch.dict("os.environ", {}, clear=True):
            result = validator._get_coach_test_model()
        assert result is None


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ============================================================================
# SDK env merge (TASK-EMB-004) — revalidated under TASK-HMIG-006.3
# ============================================================================


class _FakeHarness:
    """HarnessAdapter stub for the TASK-HMIG-006.3 test surface.

    Snapshots ``os.environ`` at ``invoke()`` time and records the kwargs
    so tests can assert on Coach's harness dispatch + env contract.

    The snapshot shows what the shared process environment held during
    ``invoke()``. Since 3 October 2026 (concurrent builds) the Coach no
    longer swaps ``PYTHONPATH``/``PATH`` into ``os.environ`` there; it hands
    them to ``select_harness`` as ``env=`` overrides, which
    ``ClaudeSDKHarness`` passes as ``ClaudeAgentOptions.env``. Tests assert
    both: the overrides on the ``select_harness`` call, and an unchanged
    process environment in the snapshot.
    """

    def __init__(self, events: Optional[List[Any]] = None) -> None:
        self.events = list(events or [])
        self.invoke_calls: List[dict] = []
        self.env_snapshots: List[Dict[str, str]] = []
        self.supports_resume = False
        self.session_id: Optional[str] = None

    async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
        self.invoke_calls.append(
            {
                "prompt": prompt,
                "role": role,
                "tools": list(tools),
                "cwd": cwd,
                "timeout_seconds": timeout_seconds,
            }
        )
        self.env_snapshots.append(dict(os.environ))
        for event in self.events:
            yield event


class TestSdkEnvMerge:
    """Verify _run_tests_via_sdk preserves env contract (TASK-EMB-004).

    3 October 2026 (concurrent builds): ``PYTHONPATH`` is no longer swapped
    into ``os.environ`` around ``harness.invoke()`` — parallel wave tasks
    share that — but handed to ``select_harness`` as ``env=`` overrides,
    which the SDK merges over the inherited environment for its own
    subprocess. The asserted contract is unchanged: API keys are inherited
    (the process environment is left as it is), and ``PYTHONPATH`` is
    prepended with the worktree root.
    """

    def test_sdk_env_inherits_os_environ_keys(self, tmp_worktree, monkeypatch):
        """At harness.invoke() time, os.environ carries inherited keys + PYTHONPATH override."""
        import asyncio

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
        monkeypatch.delenv("PYTHONPATH", raising=False)

        validator = CoachValidator(str(tmp_worktree))
        fake = _FakeHarness(events=[])

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            return_value=fake,
        ) as select:
            asyncio.run(validator._run_tests_via_sdk("pytest tests/"))

        assert len(fake.env_snapshots) == 1, "harness.invoke must be called exactly once"
        env = fake.env_snapshots[0]
        assert env.get("ANTHROPIC_API_KEY") == "test-api-key", "API key must be inherited"
        assert env.get("EMBEDDING_PROVIDER") == "openai", "EMBEDDING_PROVIDER must be inherited"
        assert "PYTHONPATH" not in env, "the shared process environment is not changed"
        overrides = select.call_args.kwargs["env"]
        assert overrides["PYTHONPATH"] == str(tmp_worktree), "PYTHONPATH must be set to worktree root"

    def test_the_test_run_asks_for_the_checkers_shell(self, tmp_worktree):
        """19 October 2026: the Coach's test run is the checker's shell.

        ``harness_role="coach"`` makes the selector ask the factory for the
        checker's own home and temporary folders, never the builder's.
        """
        import asyncio

        validator = CoachValidator(str(tmp_worktree))
        fake = _FakeHarness(events=[])

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            return_value=fake,
        ) as select:
            asyncio.run(validator._run_tests_via_sdk("pytest tests/"))

        assert select.call_args.kwargs["harness_role"] == "coach"

    def test_sdk_env_pythonpath_prepends_worktree(self, tmp_worktree, monkeypatch):
        """PYTHONPATH at harness.invoke() time includes the worktree root as a prefix."""
        import asyncio

        monkeypatch.setenv("PYTHONPATH", "/some/existing/path")

        validator = CoachValidator(str(tmp_worktree))
        fake = _FakeHarness(events=[])

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            return_value=fake,
        ) as select:
            asyncio.run(validator._run_tests_via_sdk("pytest tests/"))

        assert fake.env_snapshots[0].get("PYTHONPATH") == "/some/existing/path"
        pythonpath = select.call_args.kwargs["env"].get("PYTHONPATH", "")
        assert str(tmp_worktree) in pythonpath, "worktree path must appear in PYTHONPATH"
        assert "/some/existing/path" in pythonpath, "existing PYTHONPATH must be preserved"
        assert pythonpath.startswith(str(tmp_worktree)), "worktree must have priority (be first)"

    def test_pythonpath_restored_after_invoke(self, tmp_worktree, monkeypatch):
        """The PYTHONPATH context manager must restore the original after invoke()."""
        import asyncio

        monkeypatch.setenv("PYTHONPATH", "/pre-existing")
        validator = CoachValidator(str(tmp_worktree))
        fake = _FakeHarness(events=[])

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            return_value=fake,
        ):
            asyncio.run(validator._run_tests_via_sdk("pytest tests/"))

        # The process environment is never changed, during or after.
        assert fake.env_snapshots[0].get("PYTHONPATH") == "/pre-existing"
        assert os.environ.get("PYTHONPATH") == "/pre-existing", (
            "the SDK test run must leave PYTHONPATH as it was"
        )


# ============================================================================
# Coach harness migration (TASK-HMIG-006.3) — AC-004 dispatch surface
# ============================================================================


class TestCoachHarnessMigration:
    """TASK-HMIG-006.3: Coach's independent SDK call dispatches through HarnessAdapter.

    These tests cover the AC-004 surface: ``_run_tests_via_sdk`` uses
    ``select_harness`` so ``GUARDKIT_HARNESS`` routes the same way it
    does for the Player path migrated in TASK-HMIG-006/006.2.
    Behavioural parity for the LangGraph substrate is out of scope per
    Section 8 of the implementation plan; only the dispatch boundary
    and event-loop translation are asserted here.
    """

    def test_dispatches_through_select_harness_with_coach_kwargs(
        self, tmp_worktree
    ):
        """select_harness is called once with Coach-specific kwargs (AC-001, AC-002)."""
        import asyncio
        from guardkit.orchestrator.harness import ResultMessageEvent

        validator = CoachValidator(str(tmp_worktree))
        fake = _FakeHarness(events=[ResultMessageEvent(session_id=None)])
        captured_kwargs: dict = {}

        def _capture(**kwargs):
            captured_kwargs.update(kwargs)
            return fake

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            side_effect=_capture,
        ):
            asyncio.run(validator._run_tests_via_sdk("pytest tests/"))

        # AC-001: select_harness is the dispatch boundary
        assert captured_kwargs, "select_harness must be called"
        # AC-002: Coach-specific verifier constraints stay orchestrator-side
        assert captured_kwargs["allowed_tools"] == ["Bash"]
        assert captured_kwargs["permission_mode"] == "bypassPermissions"
        assert captured_kwargs["max_turns"] == 1
        assert captured_kwargs["sdk_timeout_seconds"] == validator.test_timeout
        assert captured_kwargs["cwd"] == validator.worktree_path
        # harness.invoke receives the same Coach-side tool set + role
        assert fake.invoke_calls[0]["tools"] == ["Bash"]
        assert fake.invoke_calls[0]["role"] == "coach_test"
        assert fake.invoke_calls[0]["timeout_seconds"] == validator.test_timeout

    def test_consumes_tool_result_event_is_error_true(self, tmp_worktree):
        """ToolResultEvent(is_error=True) -> bash_is_error=True -> failure result."""
        import asyncio
        from guardkit.orchestrator.harness import (
            ResultMessageEvent,
            ToolResultEvent,
        )

        validator = CoachValidator(str(tmp_worktree))
        fake = _FakeHarness(events=[
            ToolResultEvent(
                tool_use_id="x",
                content="error: command not found",
                is_error=True,
            ),
            ResultMessageEvent(session_id=None),
        ])

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            return_value=fake,
        ):
            result = asyncio.run(validator._run_tests_via_sdk("pytest tests/"))

        assert result.tests_passed is False
        assert "error" in result.raw_output.lower()
        assert result.test_command == "pytest tests/"

    def test_consumes_tool_result_event_is_error_false_falls_through_to_heuristic(
        self, tmp_worktree
    ):
        """ToolResultEvent(is_error=False) intentionally maps to heuristic branch.

        The False->None mapping is documented in coach_validator: is_error=False
        means "tool ran cleanly" not "tests passed", so the heuristic
        branch on the output text decides.
        """
        import asyncio
        from guardkit.orchestrator.harness import (
            ResultMessageEvent,
            ToolResultEvent,
        )

        validator = CoachValidator(str(tmp_worktree))
        fake = _FakeHarness(events=[
            ToolResultEvent(
                tool_use_id="x",
                content="5 passed in 0.12s",
                is_error=False,
            ),
            ResultMessageEvent(session_id=None),
        ])

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            return_value=fake,
        ):
            result = asyncio.run(validator._run_tests_via_sdk("pytest tests/"))

        # Heuristic detects "passed" without "failed/error" → tests_passed=True
        assert result.tests_passed is True
        assert "5 passed" in result.raw_output

    def test_consumes_assistant_message_then_heuristic_pass(self, tmp_worktree):
        """AssistantMessageEvent text feeds the heuristic when no ToolResultEvent fires.

        SDK-harness path contract (per coach_validator NOTE in
        _run_tests_via_sdk): ClaudeSDKHarness does not yield
        ToolResultEvent, so bash_is_error stays None and the heuristic
        on ``collected_text`` is the effective pass/fail determination.
        """
        import asyncio
        from guardkit.orchestrator.harness import (
            AssistantMessageEvent,
            ResultMessageEvent,
        )

        validator = CoachValidator(str(tmp_worktree))
        fake = _FakeHarness(events=[
            AssistantMessageEvent(text="Test run complete. 5 passed in 0.12s", raw=None),
            ResultMessageEvent(session_id=None),
        ])

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            return_value=fake,
        ):
            result = asyncio.run(validator._run_tests_via_sdk("pytest tests/"))

        assert result.tests_passed is True
        assert "5 passed" in result.raw_output

    def test_honours_langgraph_env_var(self, tmp_worktree, monkeypatch):
        """GUARDKIT_HARNESS=langgraph routes through select_harness (dispatch only).

        Asserts that the Coach path does not hardcode the SDK; the
        env-var-driven select_harness factory is the only dispatch
        boundary. Behavioural parity for LangGraph is out of scope per
        AC-004 / Section 8.
        """
        import asyncio
        from guardkit.orchestrator.harness import ResultMessageEvent

        monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")
        validator = CoachValidator(str(tmp_worktree))
        fake = _FakeHarness(events=[ResultMessageEvent(session_id=None)])
        call_count = 0

        def _capture(**kwargs):
            nonlocal call_count
            call_count += 1
            return fake

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            side_effect=_capture,
        ):
            asyncio.run(validator._run_tests_via_sdk("pytest tests/"))

        assert call_count == 1, "select_harness must be the dispatch boundary regardless of substrate"

    def test_agent_invocation_error_is_reraised(self, tmp_worktree):
        """AgentInvocationError from harness.invoke surfaces to the caller."""
        import asyncio
        from guardkit.orchestrator.exceptions import AgentInvocationError

        validator = CoachValidator(str(tmp_worktree))

        class _ExplodingHarness:
            supports_resume = False
            session_id = None

            async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
                raise AgentInvocationError("simulated transport failure")
                yield  # unreachable; keeps this an async generator

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            return_value=_ExplodingHarness(),
        ):
            with pytest.raises(AgentInvocationError, match="simulated transport"):
                asyncio.run(validator._run_tests_via_sdk("pytest tests/"))


# ============================================================================
# Coach sdk_debug preservation (TASK-HMIG-006.5) — restore TASK-DIAG-F4A2
# diagnostic surface dropped by TASK-HMIG-006.3 harness migration.
# ============================================================================


class TestCoachSdkDebugPreservation:
    """TASK-HMIG-006.5: ``_run_tests_via_sdk`` preserves prompt + harness
    event stream under ``sdk_debug/turn_<n>/coach/test_run/`` when
    ``GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1``.

    The pre-migration shape (TASK-DIAG-F4A2) wrote three files per
    coach test turn:

    * ``prompt.txt`` — byte-equal to the prompt the SDK saw.
    * ``options.json`` — JSON dump of the ``ClaudeAgentOptions`` dataclass.
    * ``messages.jsonl`` — one JSON line per SDK message consumed.

    Post-migration the harness owns the message stream, so this class
    asserts the equivalent shape against (a) the synthesised
    options-snapshot dict the new call site builds and (b) the
    ``HarnessEvent`` typed records yielded by the substrate.

    Lives in ``_HARNESS_OWNING_TEST_CLASSES`` so the autouse
    SDK-failure fixture does not clobber the explicit
    ``select_harness`` patch installed below.
    """

    @staticmethod
    def _read_jsonl(path):
        return [json.loads(line) for line in path.read_text().splitlines() if line]

    def test_no_files_when_env_var_unset(self, tmp_worktree, monkeypatch):
        """AC-003: zero overhead in production — no sdk_debug dir created."""
        import asyncio
        from guardkit.orchestrator.harness import (
            AssistantMessageEvent,
            ResultMessageEvent,
        )

        monkeypatch.delenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", raising=False)

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-001", turn=1)
        fake = _FakeHarness(events=[
            AssistantMessageEvent(text="5 passed in 0.1s", raw=None),
            ResultMessageEvent(session_id=None),
        ])

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            return_value=fake,
        ):
            asyncio.run(validator._run_tests_via_sdk("pytest tests/"))

        sdk_debug_root = tmp_worktree / ".guardkit" / "autobuild" / "TASK-001" / "sdk_debug"
        assert not sdk_debug_root.exists(), (
            "preserve_prompt must short-circuit when env var is unset"
        )

    def test_preserves_prompt_options_and_events_when_enabled(
        self, tmp_worktree, monkeypatch
    ):
        """AC-001 + AC-002: full triple is written with HarnessEvent shape."""
        import asyncio
        from guardkit.orchestrator.harness import (
            AssistantMessageEvent,
            ResultMessageEvent,
        )

        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")
        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-001", turn=3)
        events = [
            AssistantMessageEvent(text="Running pytest", raw=None),
            AssistantMessageEvent(text="5 passed in 0.1s", raw=None),
            ResultMessageEvent(session_id="sess-xyz", stop_reason="end_turn"),
        ]
        fake = _FakeHarness(events=events)

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            return_value=fake,
        ):
            asyncio.run(validator._run_tests_via_sdk("pytest tests/foo"))

        debug_dir = (
            tmp_worktree
            / ".guardkit" / "autobuild" / "TASK-001" / "sdk_debug"
            / "turn_3" / "coach" / "test_run"
        )
        assert debug_dir.is_dir(), "coach test debug dir must exist under turn_<n>/coach/test_run/"

        # AC-001: prompt.txt is byte-equal to the rendered command prompt
        prompt_text = (debug_dir / "prompt.txt").read_text(encoding="utf-8")
        assert "pytest tests/foo" in prompt_text
        assert prompt_text.startswith("Run the following test command")

        # AC-001: options.json captures the synthesised options-shaped snapshot
        options_payload = json.loads((debug_dir / "options.json").read_text())
        assert options_payload["allowed_tools"] == ["Bash"]
        assert options_payload["permission_mode"] == "bypassPermissions"
        assert options_payload["max_turns"] == 1
        assert options_payload["cwd"] == str(tmp_worktree)
        # GUARDKIT_HARNESS env var is captured so post-mortem can
        # distinguish SDK vs. LangGraph substrate runs.
        assert options_payload["harness"] == "sdk"
        assert options_payload["pythonpath_prepend"] == str(tmp_worktree)

        # AC-002: each HarnessEvent the loop consumed is recorded with
        # its typed class name. messages.jsonl is one JSON line per
        # event in stream order.
        recorded = self._read_jsonl(debug_dir / "messages.jsonl")
        assert len(recorded) == 3, (
            f"expected one JSONL line per harness event, got {len(recorded)}: {recorded}"
        )
        assert [r["type"] for r in recorded] == [
            "AssistantMessageEvent",
            "AssistantMessageEvent",
            "ResultMessageEvent",
        ]
        # First AssistantMessageEvent carries its text field through
        # the dataclass.asdict path (AC-002 typed-event shape).
        assert recorded[0]["text"] == "Running pytest"
        # Terminal ResultMessageEvent carries its session_id field.
        assert recorded[2]["session_id"] == "sess-xyz"

    def test_event_raw_walked_recursively(self, tmp_worktree, monkeypatch):
        """AC-002: ``event.raw`` (SDK Message) is walked, not repr'd.

        Pre-migration the JSONL line was the raw SDK message dumped
        via dataclass.asdict. Post-migration the harness wraps the
        SDK message in ``AssistantMessageEvent.raw``. The preservation
        path must walk that field recursively so post-mortem analysis
        sees the same fields it used to — not a single ``repr()``
        string.
        """
        import asyncio
        from dataclasses import dataclass, field as dc_field
        from typing import List as ListT

        from guardkit.orchestrator.harness import (
            AssistantMessageEvent,
            ResultMessageEvent,
        )

        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        @dataclass
        class _FakeTextBlock:
            text: str = ""
            block_type: str = "text"

        @dataclass
        class _FakeRawSDKMessage:
            """Stands in for ``claude_agent_sdk.AssistantMessage``."""
            content: ListT[_FakeTextBlock] = dc_field(default_factory=list)
            model: str = "claude-sonnet"

        raw_msg = _FakeRawSDKMessage(
            content=[_FakeTextBlock(text="bash output here")],
            model="claude-sonnet",
        )

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-001", turn=1)
        fake = _FakeHarness(events=[
            AssistantMessageEvent(text="bash output here", raw=raw_msg),
            ResultMessageEvent(session_id=None),
        ])

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
            return_value=fake,
        ):
            asyncio.run(validator._run_tests_via_sdk("pytest tests/"))

        debug_dir = (
            tmp_worktree
            / ".guardkit" / "autobuild" / "TASK-001" / "sdk_debug"
            / "turn_1" / "coach" / "test_run"
        )
        recorded = self._read_jsonl(debug_dir / "messages.jsonl")
        first = recorded[0]
        assert first["type"] == "AssistantMessageEvent"
        # ``raw`` is walked recursively, not repr'd — the inner SDK
        # message keeps its fields addressable from the JSONL line.
        assert isinstance(first["raw"], dict), (
            f"raw must be walked into a dict, got {type(first['raw']).__name__}: {first['raw']!r}"
        )
        assert first["raw"]["type"] == "_FakeRawSDKMessage"
        assert first["raw"]["model"] == "claude-sonnet"
        assert first["raw"]["content"][0]["text"] == "bash output here"

    def test_preservation_idempotent_within_turn(self, tmp_worktree, monkeypatch):
        """Re-running ``_run_tests_via_sdk`` for the same turn overwrites,
        matching the pre-migration ``preserve_prompt`` contract that
        wipes stale state from interrupted runs.
        """
        import asyncio
        from guardkit.orchestrator.harness import (
            AssistantMessageEvent,
            ResultMessageEvent,
        )

        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-001", turn=1)

        def _run(events):
            fake = _FakeHarness(events=events)
            with patch(
                "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
                return_value=fake,
            ):
                asyncio.run(validator._run_tests_via_sdk("pytest tests/"))

        _run([AssistantMessageEvent(text="first run", raw=None),
              ResultMessageEvent(session_id=None)])
        _run([AssistantMessageEvent(text="second run", raw=None),
              ResultMessageEvent(session_id=None)])

        debug_dir = (
            tmp_worktree
            / ".guardkit" / "autobuild" / "TASK-001" / "sdk_debug"
            / "turn_1" / "coach" / "test_run"
        )
        recorded = self._read_jsonl(debug_dir / "messages.jsonl")
        # Second run wipes the first — only the second pair survives.
        assert [r["text"] for r in recorded[:1]] == ["second run"], (
            "idempotent re-run must overwrite, not append, the JSONL stream"
        )
