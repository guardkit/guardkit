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
from guardkit.orchestrator.toolchain_declaration import ToolchainDeclaration


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

            validator = CoachValidator(str(tmp_worktree), toolchain=ToolchainDeclaration(test="make test"))
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

            validator = CoachValidator(str(tmp_worktree), toolchain=ToolchainDeclaration(test="make test"))
            result = validator.run_independent_tests()

        assert result.tests_passed is False
        assert "failed" in result.test_output_summary.lower()

    def test_run_tests_timeout(self, tmp_worktree):
        """Test test execution timeout."""
        import subprocess

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("pytest", 300)

            validator = CoachValidator(
                str(tmp_worktree),
                test_timeout=300,
                toolchain=ToolchainDeclaration(test="make test"),
            )
            result = validator.run_independent_tests()

        assert result.tests_passed is False
        assert "timed out" in result.test_output_summary.lower()

    def test_run_tests_exception(self, tmp_worktree):
        """Test test execution exception handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Command not found")

            validator = CoachValidator(str(tmp_worktree), toolchain=ToolchainDeclaration(test="make test"))
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

    @pytest.mark.parametrize("marker", ["pyproject.toml", "package.json", "Example.csproj"])
    def test_nothing_declared_runs_no_guessed_command(self, tmp_worktree, marker):
        """31 October 2026: a marker file is not a declaration. Nothing runs,
        and the check could not run, saying so."""
        (tmp_worktree / marker).touch()

        with patch("subprocess.run") as mock_run:
            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        mock_run.assert_not_called()
        assert result.test_command == "<nothing declared>"
        assert result.check_could_not_run is True
        assert result.tests_passed is False


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
    """The task type no longer decides whether the tests run (31 October
    2026): the parts the task changed do."""

    @pytest.mark.parametrize("task_type", ["scaffolding", "feature", "documentation"])
    def test_every_task_type_runs_the_changed_parts_tests(
        self, tmp_worktree, task_work_results_dir, task_type
    ):
        results = make_task_work_results(tests_passed=True)
        results["files_modified"] = ["src/app.py"]
        write_task_work_results(task_work_results_dir, results)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="All passed", stderr="")
            validator = CoachValidator(
                str(tmp_worktree), toolchain=ToolchainDeclaration(test="make test")
            )
            result = validator.gather_evidence(
                "TASK-001", 1, {"task_type": task_type, "acceptance_criteria": []}
            )

        mock_run.assert_called_once()
        assert result.independent_tests.test_command == "make test"
        assert result.independent_tests.tests_passed is True


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

        validator = CoachValidator(
            str(tmp_worktree), toolchain=ToolchainDeclaration(test="make test")
        )
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

        validator = CoachValidator(
            str(tmp_worktree), toolchain=ToolchainDeclaration(test="make test")
        )
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
