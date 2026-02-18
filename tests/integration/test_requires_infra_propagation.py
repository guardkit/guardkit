"""
Integration tests for cross-component requires_infrastructure propagation.

Addresses Finding 9 (F9) from TASK-REV-C9E5 Revision 3: unit tests verified
each component in isolation, but no test exercised the full chain:

    FeatureOrchestrator → AutoBuildOrchestrator → CoachValidator

with requires_infrastructure flowing through. The propagation gap (F3) went
undetected despite comprehensive unit test coverage.

Tests:
1. FeatureOrchestrator._execute_task() passes requires_infrastructure to
   AutoBuildOrchestrator.orchestrate() (validates R1/TASK-BOOT-B032)
2. AutoBuildOrchestrator._invoke_coach_safely() puts requires_infrastructure
   in the task dict passed to CoachValidator.validate()
3. CoachValidator.run_independent_tests() receives the value and enters the
   Docker lifecycle guard when requires_infrastructure is truthy
4. AutoBuildOrchestrator.orchestrate() falls back to frontmatter when the
   requires_infrastructure parameter is None (single-task mode)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.feature_loader import FeatureTask
from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_GENERIC_SERVICE = "test-service"
_REQUIRES_INFRA = [_GENERIC_SERVICE]


def _make_autobuild_orchestrator(tmp_path: Path) -> AutoBuildOrchestrator:
    """Create a minimal AutoBuildOrchestrator suitable for testing."""
    return AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=3,
        enable_context=False,
        enable_pre_loop=False,
        worktree_manager=Mock(),
        agent_invoker=Mock(),
        progress_display=Mock(),
    )


def _make_mock_worktree(tmp_path: Path) -> Mock:
    worktree = Mock()
    worktree.path = tmp_path
    return worktree


# ---------------------------------------------------------------------------
# Test 1: FeatureOrchestrator._execute_task → AutoBuildOrchestrator.orchestrate
# ---------------------------------------------------------------------------


class TestFeatureOrchestratorPassesRequiresInfrastructure:
    """FeatureOrchestrator._execute_task() must forward requires_infrastructure."""

    def test_requires_infrastructure_propagates_from_feature_task_to_orchestrate(
        self, tmp_path: Path
    ) -> None:
        """
        Verify requires_infrastructure flows:
        FeatureTask → _execute_task() → AutoBuildOrchestrator.orchestrate().

        Validates R1/TASK-BOOT-B032: the propagation gap that allowed
        requires_infrastructure to be silently dropped.
        """
        # Feature task carrying requires_infrastructure from YAML
        feature_task = FeatureTask(
            id="TASK-INTEG-001",
            name="test task",
            requires_infrastructure=_REQUIRES_INFRA,
        )

        mock_feature = Mock()
        mock_feature.id = "FEAT-TEST"
        mock_feature.autobuild_config = None  # avoid attribute error

        mock_worktree = _make_mock_worktree(tmp_path)

        # Mock TaskLoader response – no requires_infrastructure in frontmatter
        # so the value MUST come from the FeatureTask object
        mock_task_data = {
            "requirements": "some requirements",
            "acceptance_criteria": ["criterion A"],
            "frontmatter": {},
            "file_path": None,
        }

        mock_orch_result = Mock()
        mock_orch_result.success = True
        mock_orch_result.total_turns = 1
        mock_orch_result.final_decision = "approved"
        mock_orch_result.error = None
        mock_orch_result.recovery_count = 0

        with patch(
            "guardkit.orchestrator.feature_orchestrator.TaskLoader"
        ) as MockTaskLoader:
            MockTaskLoader.load_task.return_value = mock_task_data

            with patch(
                "guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator"
            ) as MockABO:
                MockABO.return_value.orchestrate.return_value = mock_orch_result

                orchestrator = FeatureOrchestrator(
                    repo_root=tmp_path,
                    worktree_manager=Mock(),
                )
                orchestrator._execute_task(feature_task, mock_feature, mock_worktree)

        call_kwargs = MockABO.return_value.orchestrate.call_args.kwargs
        assert "requires_infrastructure" in call_kwargs, (
            "orchestrate() must receive requires_infrastructure kwarg"
        )
        assert call_kwargs["requires_infrastructure"] == _REQUIRES_INFRA, (
            f"Expected {_REQUIRES_INFRA!r}, got {call_kwargs['requires_infrastructure']!r}"
        )

    def test_empty_requires_infrastructure_propagated_as_empty_list(
        self, tmp_path: Path
    ) -> None:
        """Empty requires_infrastructure list is forwarded (not dropped)."""
        feature_task = FeatureTask(
            id="TASK-INTEG-002",
            name="test task",
            requires_infrastructure=[],
        )
        mock_feature = Mock()
        mock_feature.id = "FEAT-TEST"
        mock_feature.autobuild_config = None

        mock_worktree = _make_mock_worktree(tmp_path)
        mock_task_data = {
            "requirements": "reqs",
            "acceptance_criteria": ["ok"],
            "frontmatter": {},
            "file_path": None,
        }
        mock_result = Mock()
        mock_result.success = True
        mock_result.total_turns = 1
        mock_result.final_decision = "approved"
        mock_result.error = None
        mock_result.recovery_count = 0

        with patch("guardkit.orchestrator.feature_orchestrator.TaskLoader") as MockTL:
            MockTL.load_task.return_value = mock_task_data

            with patch(
                "guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator"
            ) as MockABO:
                MockABO.return_value.orchestrate.return_value = mock_result

                orchestrator = FeatureOrchestrator(
                    repo_root=tmp_path,
                    worktree_manager=Mock(),
                )
                orchestrator._execute_task(feature_task, mock_feature, mock_worktree)

        call_kwargs = MockABO.return_value.orchestrate.call_args.kwargs
        assert call_kwargs["requires_infrastructure"] == []


# ---------------------------------------------------------------------------
# Test 2: AutoBuildOrchestrator._invoke_coach_safely → CoachValidator task dict
# ---------------------------------------------------------------------------


class TestAutoBuiltPutsRequiresInfrastructureInCoachTaskDict:
    """_invoke_coach_safely() must include requires_infrastructure in task dict."""

    def test_requires_infrastructure_present_in_task_dict_passed_to_validate(
        self, tmp_path: Path
    ) -> None:
        """
        Verify _invoke_coach_safely(requires_infrastructure=[...]) propagates
        the value to CoachValidator.validate(task={"requires_infrastructure": [...]}).
        """
        orchestrator = _make_autobuild_orchestrator(tmp_path)
        worktree = _make_mock_worktree(tmp_path)

        captured_task_dict: Dict[str, Any] = {}

        def fake_validate(task_id, turn, task, skip_arch_review=False, context=None):
            captured_task_dict.update(task)
            result = Mock()
            result.to_dict.return_value = {}
            return result

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as MockValidator:
            instance = MockValidator.return_value
            instance._is_docker_available.return_value = True
            instance.validate.side_effect = fake_validate
            instance.save_decision = Mock()

            orchestrator._load_coach_config = Mock(
                return_value={"test_execution": "subprocess"}
            )

            orchestrator._invoke_coach_safely(
                task_id="TASK-INTEG-003",
                turn=1,
                requirements="test requirements",
                player_report={},
                worktree=worktree,
                requires_infrastructure=_REQUIRES_INFRA,
            )

        assert "requires_infrastructure" in captured_task_dict, (
            "requires_infrastructure key must be present in task dict passed to validate()"
        )
        assert captured_task_dict["requires_infrastructure"] == _REQUIRES_INFRA


# ---------------------------------------------------------------------------
# Test 3: CoachValidator.run_independent_tests() enters Docker lifecycle guard
# ---------------------------------------------------------------------------


class TestCoachValidatorEntersDockerLifecycleGuard:
    """CoachValidator must enter Docker lifecycle when requires_infrastructure is set."""

    def test_docker_lifecycle_guard_entered_for_generic_service(
        self, tmp_path: Path
    ) -> None:
        """
        run_independent_tests() with requires_infrastructure=["test-service"]
        must call _is_docker_available() (entering the Docker lifecycle guard).
        Uses a generic service name to keep the test stack-agnostic.
        """
        validator = CoachValidator(
            worktree_path=str(tmp_path),
            coach_test_execution="subprocess",
            test_command="pytest tests/",
        )
        task = {"requires_infrastructure": _REQUIRES_INFRA}

        with patch.object(
            validator, "_is_docker_available", return_value=True
        ) as mock_docker_check:
            with patch.object(validator, "_start_infrastructure_containers") as mock_start:
                with patch.object(validator, "_stop_infrastructure_containers"):
                    with patch(
                        "subprocess.run",
                        return_value=Mock(returncode=0, stdout="1 passed", stderr=""),
                    ):
                        validator.run_independent_tests(task_work_results={}, task=task)

        mock_docker_check.assert_called_once()
        mock_start.assert_called_once_with(_REQUIRES_INFRA)

    def test_docker_lifecycle_guard_not_entered_when_no_requires_infrastructure(
        self, tmp_path: Path
    ) -> None:
        """
        When requires_infrastructure is absent, _is_docker_available() must NOT
        be called (guard is not entered).
        """
        validator = CoachValidator(
            worktree_path=str(tmp_path),
            coach_test_execution="subprocess",
            test_command="pytest tests/",
        )
        task: Dict[str, Any] = {}

        with patch.object(validator, "_is_docker_available") as mock_docker_check:
            with patch(
                "subprocess.run",
                return_value=Mock(returncode=0, stdout="1 passed", stderr=""),
            ):
                validator.run_independent_tests(task_work_results={}, task=task)

        mock_docker_check.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: Frontmatter fallback when requires_infrastructure parameter is None
# ---------------------------------------------------------------------------


class TestFrontmatterFallbackInOrchestrate:
    """AutoBuildOrchestrator.orchestrate() must fall back to task frontmatter."""

    def test_frontmatter_requires_infrastructure_used_when_parameter_is_none(
        self, tmp_path: Path
    ) -> None:
        """
        When orchestrate() is called without requires_infrastructure (None),
        the value from task frontmatter is forwarded to the loop phase.

        This covers the single-task mode where FeatureOrchestrator is not involved
        and requires_infrastructure comes only from the task markdown frontmatter.
        """
        orchestrator = _make_autobuild_orchestrator(tmp_path)
        mock_worktree = _make_mock_worktree(tmp_path)

        captured_loop_ri: List[Optional[List[str]]] = []

        def capture_loop_phase(*args, **kwargs):
            captured_loop_ri.append(kwargs.get("requires_infrastructure"))
            return [], "approved"

        with patch("guardkit.orchestrator.autobuild.TaskLoader") as MockTL:
            MockTL.load_task.return_value = {
                "frontmatter": {
                    "requires_infrastructure": _REQUIRES_INFRA,
                },
            }

            with patch.object(
                orchestrator, "_setup_phase", return_value=mock_worktree
            ):
                with patch.object(
                    orchestrator,
                    "_loop_phase",
                    side_effect=capture_loop_phase,
                ):
                    with patch.object(orchestrator, "_finalize_phase"):
                        orchestrator.orchestrate(
                            task_id="TASK-INTEG-004",
                            requirements="test requirements",
                            acceptance_criteria=["criterion A"],
                            # requires_infrastructure intentionally omitted (None)
                        )

        assert len(captured_loop_ri) == 1, "_loop_phase must be called exactly once"
        assert captured_loop_ri[0] == _REQUIRES_INFRA, (
            f"Expected frontmatter value {_REQUIRES_INFRA!r}, "
            f"got {captured_loop_ri[0]!r}"
        )

    def test_explicit_caller_value_overrides_frontmatter(
        self, tmp_path: Path
    ) -> None:
        """
        When orchestrate() is called with an explicit requires_infrastructure,
        it must take precedence over the frontmatter value.
        """
        orchestrator = _make_autobuild_orchestrator(tmp_path)
        mock_worktree = _make_mock_worktree(tmp_path)

        explicit_service = ["explicit-service"]
        frontmatter_service = ["frontmatter-service"]

        captured_loop_ri: List[Optional[List[str]]] = []

        def capture_loop_phase(*args, **kwargs):
            captured_loop_ri.append(kwargs.get("requires_infrastructure"))
            return [], "approved"

        with patch("guardkit.orchestrator.autobuild.TaskLoader") as MockTL:
            MockTL.load_task.return_value = {
                "frontmatter": {
                    "requires_infrastructure": frontmatter_service,
                },
            }

            with patch.object(
                orchestrator, "_setup_phase", return_value=mock_worktree
            ):
                with patch.object(
                    orchestrator,
                    "_loop_phase",
                    side_effect=capture_loop_phase,
                ):
                    with patch.object(orchestrator, "_finalize_phase"):
                        orchestrator.orchestrate(
                            task_id="TASK-INTEG-005",
                            requirements="test requirements",
                            acceptance_criteria=["criterion A"],
                            requires_infrastructure=explicit_service,
                        )

        assert captured_loop_ri[0] == explicit_service, (
            "Explicit caller value must override frontmatter"
        )
