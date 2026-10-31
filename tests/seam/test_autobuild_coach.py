"""
Seam tests for AutoBuild → Coach Agent wiring.

This module verifies the data flow between the AutoBuild orchestrator,
CoachValidator (which runs the project's own checks) and the reviewer:
1. Player task-work results files are actually read (not mocked away)
2. A missing results file does not stop the project's checks
3. Acceptance criteria reach the reviewer on the default path

Since the cull (27 October 2026) ``CoachValidator.validate`` and its quality
gates, requirements matching and zero-test check are gone, with their tests.

Historical Context:
    From failure pattern FP-002: Player self-report unreliability. In the g3
    ablation study, removing Coach made output non-functional despite Player
    claiming success. These seam tests ensure Coach actually receives the
    data it needs to validate independently.

Seam Definition:
    Layer A: AutoBuild orchestrator (_execute_turn(), turn loop)
    Layer B: Coach turn (CoachValidator.gather_evidence(), _invoke_coach_safely())
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.quality_gates import CoachValidator
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.worktrees import Worktree

import subprocess

_REAL_SUBPROCESS_RUN = subprocess.run


def _canned_except_git(canned: MagicMock):
    """A ``subprocess.run`` stand-in that lets git run for real.

    Since 4 October 2026 (73705b64) the orchestrator reads the Coach's
    project documents from the build's source commit with git before it calls
    the Coach. The worktree here is not a git checkout, so real git says so
    and nothing is captured: the documented behaviour for a project that
    declares no documents. Every other command still gets ``canned``.
    """

    def run(args, *a, **kw):
        if args and os.path.basename(str(args[0])) == "git":
            return _REAL_SUBPROCESS_RUN(args, *a, **kw)
        return canned

    return run

pytestmark = pytest.mark.seam


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def tmp_worktree(tmp_path: Path) -> Path:
    """Create a temporary worktree directory with required structure."""
    worktree = tmp_path / "worktrees" / "TASK-S6-001"
    worktree.mkdir(parents=True)

    # Create required directories
    (worktree / ".guardkit" / "autobuild" / "TASK-S6-001").mkdir(parents=True)
    (worktree / "tests").mkdir(parents=True)

    # Create pyproject.toml to trigger pytest detection
    (worktree / "pyproject.toml").write_text("[tool.pytest]\n")

    # WS3-S1 Q1 SPLIT: this fixture drives the real autobuild Coach path
    # (in_autobuild_context=True), where a Python-project worktree with NO
    # resolvable interpreter now HARD-ABORTS (InterpreterResolutionError). Give
    # it a resolvable .venv interpreter (existence is all probe_worktree_venv
    # checks) so the seam test exercises its intended path instead of the abort.
    venv_python = worktree / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True, exist_ok=True)
    venv_python.symlink_to(sys.executable)

    return worktree


@pytest.fixture
def task_work_results_dir(tmp_worktree: Path) -> Path:
    """Return the task-work results directory."""
    return tmp_worktree / ".guardkit" / "autobuild" / "TASK-S6-001"


@pytest.fixture
def mock_worktree(tmp_worktree: Path) -> Mock:
    """Create a mock Worktree that points to our temp directory."""
    worktree = Mock(spec=Worktree)
    worktree.task_id = "TASK-S6-001"
    worktree.path = tmp_worktree
    worktree.branch_name = "autobuild/TASK-S6-001"
    worktree.base_branch = "main"
    return worktree


def make_task_work_results(
    tests_passed: bool = True,
    failed_count: int = 0,
    total_tests: int = 15,
    coverage_met: bool = True,
    line_coverage: int = 85,
    arch_score: int = 82,
    violations: int = 0,
    requirements_met: Optional[List[str]] = None,
    tests_written: Optional[List[str]] = None,
    files_created: Optional[List[str]] = None,
    task_id: str = "TASK-S6-001",
) -> Dict[str, Any]:
    """Create task-work results matching actual schema."""
    if not tests_passed and failed_count == 0:
        failed_count = 1

    passed_count = total_tests - failed_count
    return {
        "task_id": task_id,
        "quality_gates": {
            "tests_passing": tests_passed and failed_count == 0,
            "tests_passed": passed_count,
            "tests_failed": failed_count,
            "coverage": line_coverage,
            "coverage_met": coverage_met,
            "all_passed": tests_passed and coverage_met,
        },
        "code_review": {
            "score": arch_score,
            "solid": 85,
            "dry": 80,
            "yagni": 82,
        },
        "plan_audit": {
            "violations": violations,
            "file_count_match": True,
        },
        "requirements_met": requirements_met or [
            "OAuth2 authentication flow",
            "Token generation",
            "Token refresh",
        ],
        "tests_written": tests_written if tests_written is not None else ["tests/test_auth.py"],
        "files_created": (
            files_created
            if files_created is not None
            else ["src/auth.py", "tests/test_auth.py"]
        ),
        "files_modified": [],
    }


def materialize_claimed_files(worktree: Path, results: Dict[str, Any]) -> None:
    """
    Create, on disk, every file the results claim the Player produced.

    STALENESS REPAIR (2026-08-21). These tests were written 2026-02-16
    (commit de1ce9b8). On 2026-05-06, commit b9a45694 (TASK-AB-FIX-INVAB1,
    "wire CoachVerifier into deterministic Coach path") added an ADVERSARIAL
    HONESTY CHECK as step 1.4 of CoachValidator.validate(): before any quality
    gate is consulted, the Coach checks that every file the Player claims to
    have created/modified/tested actually exists in the worktree. If any claim
    is false, the Coach returns decision="feedback" immediately with
    quality_gates=None, requirements=None, independent_tests=None.

    The fixtures here claimed "src/auth.py" and "tests/test_auth.py" but never
    wrote them, so from 2026-05-06 onward every test in this file was stopped
    at the honesty check and never reached the seam it was written to test.
    That is the Coach working correctly — a lying Player report is exactly what
    it is now built to reject. The fixture was the thing that was wrong.

    The honesty check was removed in the cull (27 October 2026); the files
    are still materialised so the fixture describes a real worktree.
    """
    claimed = (
        list(results.get("files_created", []))
        + list(results.get("files_modified", []))
        + list(results.get("tests_written", []))
    )
    for rel in claimed:
        target = worktree / rel
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.name.startswith("test_") and target.suffix == ".py":
            target.write_text("def test_placeholder():\n    assert True\n")
        else:
            target.write_text("# fixture-materialised claim\n")


def write_task_work_results(results_dir: Path, results: Dict[str, Any]) -> Path:
    """
    Write task-work results to file AND materialise the files they claim.

    ``results_dir`` is ``<worktree>/.guardkit/autobuild/<TASK-ID>``, so the
    worktree root is three levels up. See ``materialize_claimed_files`` for
    why the claims must exist on disk (honesty verifier, 2026-05-06).
    """
    results_path = results_dir / "task_work_results.json"
    results_path.write_text(json.dumps(results, indent=2))
    materialize_claimed_files(results_dir.parents[2], results)
    return results_path


def make_player_report(
    task_id: str = "TASK-S6-001",
    turn: int = 1,
    tests_passed: bool = True,
    completion_promises: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Create a Player report for Coach validation."""
    return {
        "task_id": task_id,
        "turn": turn,
        "files_modified": ["src/auth.py"],
        "files_created": ["tests/test_auth.py"],
        "tests_written": ["tests/test_auth.py"],
        "tests_run": True,
        "tests_passed": tests_passed,
        "test_output_summary": "15 tests passed",
        "implementation_notes": "Implemented OAuth2 flow",
        "concerns": [],
        "requirements_addressed": ["OAuth2 authentication"],
        "requirements_remaining": [],
        "completion_promises": completion_promises or [
            {
                "criterion_id": "AC-001",
                "criterion_text": "OAuth2 authentication flow",
                "status": "complete",
                "evidence": "Implemented in src/auth.py",
                "test_file": "tests/test_auth.py",
                "implementation_files": ["src/auth.py"],
            }
        ],
    }


# ============================================================================
# Test: Player Results File Reading
# ============================================================================


class TestPlayerResultsFileReading:
    """Verify Player task-work results file is actually read by Coach."""

    def test_task_work_results_file_is_read(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        AC: Player task-work results file is actually read by Coach (not mocked away).

        This is the critical seam test: we write real data to disk and verify
        CoachValidator reads it. No mocking of the file read operation.
        """
        # Arrange: Write specific identifiable data
        unique_requirements = [
            "UNIQUE_REQ_A_12345",
            "UNIQUE_REQ_B_67890",
        ]
        results = make_task_work_results(requirements_met=unique_requirements)
        results_path = write_task_work_results(task_work_results_dir, results)

        # Verify file exists on disk
        assert results_path.exists(), "Results file must exist on disk"

        task = {"acceptance_criteria": unique_requirements}

        # Act: Use real CoachValidator (no mocking of read_quality_gate_results)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")

            # Directly call read_quality_gate_results to verify file read
            loaded_results = validator.read_quality_gate_results("TASK-S6-001")

        # Assert: Verify our unique data was read from the actual file
        assert "error" not in loaded_results, f"Failed to read results: {loaded_results.get('error')}"
        assert loaded_results.get("requirements_met") == unique_requirements, (
            "Requirements from file don't match what we wrote"
        )

    def test_missing_results_file_does_not_stop_the_projects_checks(
        self,
        tmp_worktree: Path,
    ):
        """No results file: the project's tests still run (it is treated as
        empty), and the bundle carries their result."""
        task = {"acceptance_criteria": ["Some criterion"], "task_type": "feature"}

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = _canned_except_git(
                MagicMock(returncode=0, stdout="1 passed in 0.10s", stderr="")
            )
            validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
            assert "error" in validator.read_quality_gate_results("TASK-S6-001")
            bundle = validator.gather_evidence(
                task_id="TASK-S6-001", turn=1, task=task,
            )

        assert bundle.gathering_status == "complete"
        assert bundle.independent_tests is not None
        assert bundle.task_type == "feature"


# ============================================================================
# Test: the reviewer is given the acceptance criteria
# ============================================================================


class TestRealCoachValidatorIntegration:
    """The real CoachValidator, with the reviewer's model call stubbed."""

    def test_default_path_passes_acceptance_criteria_to_llm_coach(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
        mock_worktree: Mock,
    ):
        """
        The DEFAULT Coach path hands the acceptance criteria to the LLM Coach.

        The language-model call itself is mocked (no model is invoked); what is
        asserted is the wiring — that ``invoke_coach`` is called at all, and
        that the criteria arrive with it.
        """
        criteria_to_test = ["Criterion Alpha", "Criterion Beta", "Criterion Gamma"]
        results = make_task_work_results(requirements_met=criteria_to_test)
        write_task_work_results(task_work_results_dir, results)

        mock_worktree_manager = Mock()
        mock_worktree_manager.create.return_value = mock_worktree
        mock_progress_display = Mock()
        mock_progress_display.__enter__ = Mock(return_value=mock_progress_display)
        mock_progress_display.__exit__ = Mock(return_value=False)
        mock_progress_display.start_turn = Mock()
        mock_progress_display.complete_turn = Mock()
        mock_progress_display.console = Mock()
        mock_progress_display.console.print = Mock()

        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_worktree.parent.parent,
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            progress_display=mock_progress_display,
            enable_context=False,
        )

        # Stand in for the SDK invoker. The real signature is probed by
        # _invoke_coach_primary via inspect.signature, so the stub must
        # declare the kwargs it wants to receive.
        captured: Dict[str, Any] = {}

        def fake_invoke_coach(
            task_id: str,
            turn: int,
            requirements: str,
            player_report: Dict[str, Any],
            remaining_budget: Any = None,
            evidence_bundle: Any = None,
            coach_context: Any = None,
            acceptance_criteria: Any = None,
            **kwargs: Any,
        ) -> AgentInvocationResult:
            captured["acceptance_criteria"] = acceptance_criteria
            captured["evidence_bundle"] = evidence_bundle
            return AgentInvocationResult(
                success=True,
                agent_type="coach",
                report={"decision": "approve", "rationale": "stub"},
                duration_seconds=0.0,
            )

        invoker = Mock()
        invoker.invoke_coach = fake_invoke_coach
        orchestrator._agent_invoker = invoker

        # The project declares its test command (an undeclared project's
        # check could not run, which stops the task before the reviewer).
        from guardkit.orchestrator.toolchain_declaration import ToolchainDeclaration

        real_init = CoachValidator.__init__

        def declared_init(self, *args, **kwargs):
            kwargs.setdefault("toolchain", ToolchainDeclaration(test="make test"))
            real_init(self, *args, **kwargs)

        with patch("subprocess.run") as mock_run, patch.object(
            CoachValidator, "__init__", declared_init
        ):
            mock_run.side_effect = _canned_except_git(
                MagicMock(returncode=0, stdout="ok", stderr="")
            )

            orchestrator._invoke_coach_safely(
                task_id="TASK-S6-001",
                turn=1,
                requirements="Test requirements",
                player_report=make_player_report(),
                worktree=mock_worktree,
                acceptance_criteria=criteria_to_test,
            )

        assert "acceptance_criteria" in captured, (
            "The default path never called invoke_coach — the LLM Coach was "
            "not reached at all."
        )
        received = captured["acceptance_criteria"]
        assert received is not None, "Acceptance criteria did not reach the LLM Coach"
        assert len(received) == 3, f"Expected 3 criteria, got {received}"
        assert [c["text"] for c in received] == criteria_to_test
