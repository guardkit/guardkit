"""TS-lane D.1a — SOLDER THE DEAD WIRE: behavioural_oracle threading.

Before D.1a the declared-oracle executor
(``CoachValidator._run_shell_command``) was built, unit tested and landed —
and completely unreachable. No production caller anywhere in ``guardkit/`` or
``installer/`` ever put ``behavioural_oracle`` into the task dict; the
``gather_evidence`` call site was a hand-built six-key literal. Only its own
unit test wrote the key.

These tests pin the wire end to end:

  1. task frontmatter -> ``orchestrate()`` -> the task dict handed to the
     Coach, on BOTH Coach paths (``gather_evidence`` primary and legacy
     ``validate()``);
  2. the feature-level declaration threaded by the caller, and the
     precedence law (design §B.1): the per-task frontmatter declaration
     WINS over the feature/repo-level one;
  3. the ABSENCE regression pin — a task with no declaration hands over a
     task dict byte-identical to the pre-D.1a six-key literal;
  4. the declared command reaches ``_run_shell_command`` intact, with the
     declared bounded timeout honoured and the declared ``expected_exit``
     deciding the verdict (LAW §B.4: the exit code IS the verdict);
  5. a failing DECLARED oracle NAMES ITSELF in the approve-override
     rationale instead of saying ``<unknown>``.

Network-free and broker-free by construction: every subprocess is a shell
builtin (``true`` / ``false`` / ``sleep``), and no Coach LLM is invoked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult, AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.feature_loader import BehaviouralOracle
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.worktrees import Worktree


# ============================================================================
# Harness — modelled on tests/unit/test_requires_infra_propagation.py, which
# pins the sibling `requires_infrastructure` thread through the same chain.
# ============================================================================


@pytest.fixture
def mock_worktree() -> Mock:
    worktree = Mock(spec=Worktree)
    worktree.task_id = "TASK-TSD1A-001"
    worktree.path = Path("/tmp/worktrees/TASK-TSD1A-001")
    worktree.branch_name = "autobuild/TASK-TSD1A-001"
    worktree.base_branch = "main"
    return worktree


@pytest.fixture
def mock_worktree_manager(mock_worktree: Mock) -> Mock:
    manager = Mock()
    manager.create.return_value = mock_worktree
    manager.preserve_on_failure.return_value = None
    manager.worktrees_dir = Path("/tmp/worktrees")
    return manager


@pytest.fixture
def mock_agent_invoker() -> Mock:
    invoker = Mock()
    invoker.invoke_player = AsyncMock()
    invoker.invoke_coach = AsyncMock()
    return invoker


@pytest.fixture
def mock_progress_display() -> Mock:
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.render_summary = Mock()
    display.render_blocked_report = Mock()
    display.console = Mock()
    return display


@pytest.fixture
def mock_pre_loop_gates() -> MagicMock:
    gates = MagicMock()
    from guardkit.orchestrator.quality_gates.pre_loop import PreLoopResult

    async def mock_execute(*args: Any, **kwargs: Any) -> PreLoopResult:
        return PreLoopResult(
            plan={"steps": ["Step 1"]},
            plan_path="/tmp/plan.md",
            complexity=3,
            max_turns=3,
            checkpoint_passed=True,
            architectural_score=85,
            clarifications={},
        )

    gates.execute = mock_execute
    return gates


@pytest.fixture
def orchestrator(
    mock_worktree_manager: Mock,
    mock_agent_invoker: Mock,
    mock_progress_display: Mock,
    mock_pre_loop_gates: MagicMock,
) -> AutoBuildOrchestrator:
    return AutoBuildOrchestrator(
        repo_root=Path("/tmp/repo"),
        max_turns=3,
        enable_pre_loop=False,
        enable_checkpoints=False,
        worktree_manager=mock_worktree_manager,
        agent_invoker=mock_agent_invoker,
        progress_display=mock_progress_display,
        pre_loop_gates=mock_pre_loop_gates,
    )


def _player_result(task_id: str) -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=task_id,
        turn=1,
        agent_type="player",
        success=True,
        report={
            "files_modified": [],
            "files_created": ["impl.py"],
            "tests_written": [],
            "tests_passed": True,
        },
        duration_seconds=5.0,
        error=None,
    )


def _coach_approve_result(task_id: str) -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=task_id,
        turn=1,
        agent_type="coach",
        success=True,
        report={"decision": "approve", "rationale": "Looks good"},
        duration_seconds=3.0,
        error=None,
    )


def _task_data(task_id: str, frontmatter: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_id": task_id,
        "requirements": "req",
        "acceptance_criteria": ["AC1"],
        "frontmatter": frontmatter,
        "content": "",
        "file_path": Path("/tmp/task.md"),
    }


def _capture_loop_kwargs(
    orchestrator: AutoBuildOrchestrator,
    task_id: str,
    frontmatter: Dict[str, Any],
    *,
    behavioural_oracle: Any = None,
) -> Dict[str, Any]:
    """Run ``orchestrate()`` far enough to see what it resolved and threaded.

    Phases 1/3/4 are stubbed on the instance: this test is about the LIFT and
    the PRECEDENCE, not about the turn machinery (whose full-orchestrate unit
    harness is quarantined red on main — see
    ``tests/unit/test_requires_infra_propagation.py``).
    """
    captured: List[Dict[str, Any]] = []

    orchestrator._setup_phase = Mock(  # type: ignore[method-assign]
        return_value=orchestrator._worktree_manager.create.return_value
    )
    orchestrator._finalize_phase = Mock()  # type: ignore[method-assign]

    def _loop(**kwargs: Any) -> Any:
        captured.append(kwargs)
        return [], "approved"

    orchestrator._loop_phase = _loop  # type: ignore[method-assign]

    with patch("guardkit.orchestrator.autobuild.TaskLoader") as mock_task_loader:
        mock_task_loader.load_task.return_value = _task_data(task_id, frontmatter)
        orchestrator.orchestrate(
            task_id=task_id,
            requirements="req",
            acceptance_criteria=["AC1"],
            behavioural_oracle=behavioural_oracle,
        )

    assert len(captured) == 1, "_loop_phase was not reached exactly once"
    return captured[0]


def _capture_coach_task_dict(
    orchestrator: AutoBuildOrchestrator,
    mock_worktree: Mock,
    *,
    behavioural_oracle: Any = None,
    legacy: bool = False,
) -> Dict[str, Any]:
    """Return the task dict ``_invoke_coach_safely`` hands to CoachValidator.

    ``legacy=False`` exercises the primary Coach path (``gather_evidence``);
    ``legacy=True`` exercises the legacy ``validate()`` path via
    ``GUARDKIT_COACH_LEGACY=1``. The D.1a spec calls for the mirror
    explicitly, so both are pinned.
    """
    captured: List[Dict[str, Any]] = []

    mock_validator = MagicMock()
    mock_validator._is_docker_available.return_value = False

    def _capture(**kwargs: Any) -> Any:
        captured.append(kwargs["task"])
        raise RuntimeError("stop after the task dict is built")

    mock_validator.gather_evidence.side_effect = _capture
    mock_validator.validate.side_effect = _capture

    env = {"GUARDKIT_COACH_LEGACY": "1"} if legacy else {}
    with patch("guardkit.orchestrator.autobuild.CoachValidator") as mock_cv, patch.dict(
        "os.environ", env, clear=False
    ):
        mock_cv.return_value = mock_validator
        orchestrator._invoke_coach_safely(
            task_id="TASK-TSD1A-COACH",
            turn=1,
            requirements="req",
            player_report={"files_modified": [], "tests_passed": True},
            worktree=mock_worktree,
            acceptance_criteria=["AC1"],
            behavioural_oracle=behavioural_oracle,
        )

    assert captured, "the Coach validator was never handed a task dict"
    return captured[0]


# ============================================================================
# 1. frontmatter -> the chain, and the caller's value as the fallback
# ============================================================================


class TestFrontmatterLift:
    """The wire the D.1a spec calls dead, at its source: nothing in
    ``orchestrate()`` had ever read ``frontmatter.behavioural_oracle``."""

    def test_frontmatter_declaration_is_lifted(
        self, orchestrator: AutoBuildOrchestrator
    ) -> None:
        kwargs = _capture_loop_kwargs(
            orchestrator,
            "TASK-TSD1A-001",
            {"behavioural_oracle": {"command": "npm test"}},
        )
        # The lift VALIDATES and normalizes through BehaviouralOracle
        # (coordinator cure): the dump carries the schema defaults.
        assert kwargs["behavioural_oracle"] == {"command": "npm test", "expected_exit": 0}

    def test_string_shortcut_survives_the_lift(
        self, orchestrator: AutoBuildOrchestrator
    ) -> None:
        kwargs = _capture_loop_kwargs(
            orchestrator, "TASK-TSD1A-002", {"behavioural_oracle": "npm test"}
        )
        # String shortcut normalizes to the validated dict shape.
        assert kwargs["behavioural_oracle"] == {"command": "npm test", "expected_exit": 0}

    def test_absent_frontmatter_threads_none(
        self, orchestrator: AutoBuildOrchestrator
    ) -> None:
        kwargs = _capture_loop_kwargs(orchestrator, "TASK-TSD1A-003", {})
        assert kwargs["behavioural_oracle"] is None


# ============================================================================
# 2. Precedence: task frontmatter WINS over the caller's feature-level value
# ============================================================================


class TestPrecedence:
    """Design §B.1: task frontmatter is the escape hatch above every
    feature/repo-level declaration — the INVERSE of requires_infrastructure,
    where the caller wins."""

    def test_caller_value_used_when_frontmatter_silent(
        self, orchestrator: AutoBuildOrchestrator
    ) -> None:
        oracle = BehaviouralOracle(command="npm test")
        kwargs = _capture_loop_kwargs(
            orchestrator, "TASK-TSD1A-004", {}, behavioural_oracle=oracle
        )
        assert kwargs["behavioural_oracle"] is oracle

    def test_frontmatter_overrides_caller(
        self, orchestrator: AutoBuildOrchestrator
    ) -> None:
        kwargs = _capture_loop_kwargs(
            orchestrator,
            "TASK-TSD1A-005",
            {"behavioural_oracle": {"command": "npm run test:task"}},
            behavioural_oracle=BehaviouralOracle(command="npm test"),
        )
        assert kwargs["behavioural_oracle"] == {"command": "npm run test:task", "expected_exit": 0}

    def test_model_instance_is_readable_by_extract_command(self) -> None:
        """``_extract_command`` accepts the schema model, not only dict/str."""
        validator = CoachValidator(worktree_path=Path("/tmp"))
        task = {"behavioural_oracle": BehaviouralOracle(command="npm test")}
        assert validator._extract_command(task) == "npm test"


# ============================================================================
# 3. The task dict handed to the Coach — BOTH paths
# ============================================================================


class TestCoachTaskDict:
    """``autobuild.py``'s two hand-built task-dict literals — the
    ``gather_evidence`` one and the legacy ``validate()`` mirror — are the
    exact place the declaration went missing."""

    def test_gather_evidence_path_carries_the_declaration(
        self, orchestrator: AutoBuildOrchestrator, mock_worktree: Mock
    ) -> None:
        task = _capture_coach_task_dict(
            orchestrator,
            mock_worktree,
            behavioural_oracle={"command": "npm test"},
        )
        assert task["behavioural_oracle"] == {"command": "npm test"}

    def test_legacy_validate_path_carries_the_declaration(
        self, orchestrator: AutoBuildOrchestrator, mock_worktree: Mock
    ) -> None:
        task = _capture_coach_task_dict(
            orchestrator,
            mock_worktree,
            behavioural_oracle={"command": "npm test"},
            legacy=True,
        )
        assert task["behavioural_oracle"] == {"command": "npm test"}

    def test_model_declaration_survives_to_the_task_dict(
        self, orchestrator: AutoBuildOrchestrator, mock_worktree: Mock
    ) -> None:
        oracle = BehaviouralOracle(command="npm test", timeout=600)
        task = _capture_coach_task_dict(
            orchestrator, mock_worktree, behavioural_oracle=oracle
        )
        assert task["behavioural_oracle"] is oracle
        validator = CoachValidator(worktree_path=Path("/tmp"))
        assert validator._extract_command(task) == "npm test"


# ============================================================================
# 4. THE ABSENCE REGRESSION PIN
# ============================================================================


class TestAbsenceIsUnchanged:
    """Backwards compatibility is the prime invariant: a repo/task with NO
    declaration must behave byte-for-byte as before D.1a."""

    _PRE_D1A_KEYS = {
        "acceptance_criteria",
        "task_type",
        "requires_infrastructure",
        "_docker_available",
        "consumer_context",
        "description",
    }

    def test_no_declaration_yields_the_original_six_key_task_dict(
        self, orchestrator: AutoBuildOrchestrator, mock_worktree: Mock
    ) -> None:
        task = _capture_coach_task_dict(orchestrator, mock_worktree)
        # Not merely "behavioural_oracle is None" — the KEY IS ABSENT, so the
        # dict is the exact six-key literal the pre-D.1a code built.
        assert set(task) == self._PRE_D1A_KEYS
        assert "behavioural_oracle" not in task

    def test_no_declaration_legacy_path_too(
        self, orchestrator: AutoBuildOrchestrator, mock_worktree: Mock
    ) -> None:
        task = _capture_coach_task_dict(orchestrator, mock_worktree, legacy=True)
        assert set(task) == self._PRE_D1A_KEYS

    def test_falsy_declaration_is_treated_as_absent(
        self, orchestrator: AutoBuildOrchestrator, mock_worktree: Mock
    ) -> None:
        """A falsy value must not manufacture a key."""
        task = _capture_coach_task_dict(
            orchestrator, mock_worktree, behavioural_oracle=None
        )
        assert "behavioural_oracle" not in task

    def test_extract_command_absent_paths(self) -> None:
        validator = CoachValidator(worktree_path=Path("/tmp"))
        assert validator._extract_command(None) is None
        assert validator._extract_command({}) is None
        assert validator._extract_command({"behavioural_oracle": None}) is None
        assert validator._extract_command({"behavioural_oracle": ""}) is None
        assert validator._extract_command({"behavioural_oracle": {}}) is None


# ============================================================================
# 4. The executor honours what the declaration says
# ============================================================================


class TestExecutorHonoursTheDeclaration:
    """``_run_shell_command`` is reached with the command intact, the declared
    bounded timeout applied, and the declared expected_exit deciding."""

    def test_declared_command_reaches_run_shell_command_intact(
        self, tmp_path: Path
    ) -> None:
        validator = CoachValidator(worktree_path=tmp_path)
        seen: Dict[str, Any] = {}
        real = validator._run_shell_command

        def spy(command: str, task: Optional[Dict[str, Any]]) -> Any:
            seen["command"] = command
            return real(command, task)

        validator._run_shell_command = spy  # type: ignore[method-assign]
        result = validator._produce_behavioural_oracle(
            authored_files=[],
            task={"behavioural_oracle": {"command": "true"}},
        )
        assert seen["command"] == "true"
        assert result is not None
        assert result["status"] == "ran"
        assert result["passed"] is True
        assert result["command"] == "true"

    def test_model_declaration_reaches_the_executor(self, tmp_path: Path) -> None:
        validator = CoachValidator(worktree_path=tmp_path)
        result = validator._produce_behavioural_oracle(
            authored_files=[],
            task={"behavioural_oracle": BehaviouralOracle(command="true")},
        )
        assert result is not None
        assert result["passed"] is True
        assert result["command"] == "true"

    def test_declared_timeout_is_honoured_and_bounds_the_run(
        self, tmp_path: Path
    ) -> None:
        """A 1s declared timeout kills a 30s command — and the declaration
        beats the GUARDKIT_ORACLE_TIMEOUT env default."""
        validator = CoachValidator(worktree_path=tmp_path)
        with patch.dict("os.environ", {"GUARDKIT_ORACLE_TIMEOUT": "300"}):
            result = validator._produce_behavioural_oracle(
                authored_files=[],
                task={
                    "behavioural_oracle": {"command": "sleep 30", "timeout": 1}
                },
            )
        assert result is not None
        assert result["timed_out"] is True
        assert result["passed"] is False
        assert result["duration"] < 20

    def test_env_timeout_still_applies_when_declaration_omits_it(
        self, tmp_path: Path
    ) -> None:
        """Absence path for the timeout: unchanged env-var behaviour."""
        validator = CoachValidator(worktree_path=tmp_path)
        with patch.dict("os.environ", {"GUARDKIT_ORACLE_TIMEOUT": "1"}):
            result = validator._produce_behavioural_oracle(
                authored_files=[],
                task={"behavioural_oracle": {"command": "sleep 30"}},
            )
        assert result is not None
        assert result["timed_out"] is True

    def test_expected_exit_decides_the_verdict(self, tmp_path: Path) -> None:
        """LAW §B.4 — the exit code IS the verdict, against the declared
        expected_exit (default 0)."""
        validator = CoachValidator(worktree_path=tmp_path)
        passing = validator._produce_behavioural_oracle(
            authored_files=[],
            task={
                "behavioural_oracle": {"command": "exit 3", "expected_exit": 3}
            },
        )
        assert passing is not None
        assert passing["passed"] is True
        assert passing["exit_code"] == 3

        failing = validator._produce_behavioural_oracle(
            authored_files=[],
            task={"behavioural_oracle": {"command": "exit 3"}},
        )
        assert failing is not None
        assert failing["passed"] is False


# ============================================================================
# 5. A failing DECLARED oracle names itself
# ============================================================================


def _guard_decision(oracle: Dict[str, Any]) -> Dict[str, Any]:
    """Run the approve-override guard over a bundle carrying *oracle*."""
    from guardkit.orchestrator.coach_verification import HonestyVerification
    from guardkit.orchestrator.quality_gates.coach_evidence import (
        CoachEvidenceBundle,
    )

    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker._persist_coach_decision = MagicMock()  # type: ignore[method-assign]
    bundle = CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="complete",
        behavioural_oracle=oracle,
    )
    decision: Dict[str, Any] = {"decision": "approve", "rationale": "looks fine"}
    invoker._apply_behavioural_oracle_guard(
        decision=decision,
        evidence_bundle=bundle,
        task_id="TASK-TSD1A-010",
        turn=1,
        coach_output_path=Path("/tmp/coach_turn_1.json"),
    )
    return decision


class TestDeclaredOracleNamesItself:
    """Before D.1a a declared oracle's failure rationale said ``<unknown>``:
    the result dict of a declared command carries ``command``, never
    ``oracle_path``, and the guard only read ``oracle_path``."""

    def test_failing_declared_command_is_named_in_the_override(self) -> None:
        decision = _guard_decision(
            {
                "status": "ran",
                "passed": False,
                "command": "npm test",
                "exit_code": 1,
                "duration": 4.2,
                "timed_out": False,
                "output_tail": "1 failed",
                "provenance": "yaml_command:npm test",
            }
        )
        assert decision["decision"] == "feedback"
        issue = next(
            i
            for i in decision["issues"]
            if i["category"] == "behavioural_oracle_failure"
        )
        assert "npm test" in issue["description"]
        assert "<unknown>" not in issue["description"]
        assert issue["details"]["oracle_path"] == "npm test"

    def test_timed_out_declared_command_is_named(self) -> None:
        decision = _guard_decision(
            {
                "status": "ran",
                "passed": False,
                "command": "npm test",
                "exit_code": None,
                "duration": 600.0,
                "timed_out": True,
                "output_tail": "",
                "provenance": "yaml_command:npm test",
            }
        )
        assert decision["decision"] == "feedback"
        issue = next(
            i
            for i in decision["issues"]
            if i["category"] == "behavioural_oracle_failure"
        )
        assert "npm test" in issue["description"]
        assert "<unknown>" not in issue["description"]

    def test_python_oracle_still_named_by_path(self) -> None:
        """Regression pin: the artefact oracle keeps naming itself by path."""
        decision = _guard_decision(
            {
                "status": "ran",
                "passed": False,
                "oracle_path": "tests/acceptance/x_roundtrip.py",
                "exit_code": 1,
                "duration": 1.0,
                "timed_out": False,
                "output_tail": "boom",
                "provenance": "discovered_artifact",
            }
        )
        issue = next(
            i
            for i in decision["issues"]
            if i["category"] == "behavioural_oracle_failure"
        )
        assert issue["details"]["oracle_path"] == "tests/acceptance/x_roundtrip.py"

    def test_truly_unknown_oracle_still_says_unknown(self) -> None:
        """The ``<unknown>`` fallback survives — it is only bypassed when the
        declaration actually names something."""
        decision = _guard_decision(
            {
                "status": "ran",
                "passed": False,
                "exit_code": 1,
                "duration": 1.0,
                "timed_out": False,
                "output_tail": "",
                "provenance": "unknown",
            }
        )
        issue = next(
            i
            for i in decision["issues"]
            if i["category"] == "behavioural_oracle_failure"
        )
        assert issue["details"]["oracle_path"] == "<unknown>"


# ============================================================================
# 6. End to end at this altitude: declaration -> executor -> approve override
# ============================================================================


class TestDeclarationOverridesApprove:
    """The D.1a exit bar at unit/integration altitude: a task declaring
    ``behavioural_oracle: {command: ...}`` runs the command, and a failing
    command overrides an approving Coach verdict to feedback.

    The REAL-BUILD receipt (a live green build whose oracle was ``npm test``
    on ts-api-test) is D.4's, not this lane's — see the report.
    """

    def test_failing_declared_command_flips_approve_to_feedback(
        self, tmp_path: Path
    ) -> None:
        validator = CoachValidator(worktree_path=tmp_path)
        oracle = validator._produce_behavioural_oracle(
            authored_files=[],
            task={"behavioural_oracle": {"command": "echo boom >&2; exit 1"}},
        )
        assert oracle is not None
        assert oracle["passed"] is False

        decision = _guard_decision(oracle)
        assert decision["decision"] == "feedback"
        issue = next(
            i
            for i in decision["issues"]
            if i["category"] == "behavioural_oracle_failure"
        )
        assert "echo boom" in issue["description"]

    def test_passing_declared_command_leaves_approve_alone(
        self, tmp_path: Path
    ) -> None:
        validator = CoachValidator(worktree_path=tmp_path)
        oracle = validator._produce_behavioural_oracle(
            authored_files=[],
            task={"behavioural_oracle": {"command": "true"}},
        )
        assert oracle is not None
        decision = _guard_decision(oracle)
        assert decision["decision"] == "approve"
        assert "issues" not in decision


class TestFrontmatterValidationIsLoud:
    """Coordinator-cure pins (D.1a coach): the HIGHEST-precedence declaration
    path runs the schema — a typo or an unbounded timeout is LOUD, never a
    silent absence."""

    def test_typo_key_fails_the_task_load_loudly(
        self, orchestrator: AutoBuildOrchestrator
    ) -> None:
        import pydantic
        import pytest as _pytest

        with _pytest.raises(pydantic.ValidationError):
            _capture_loop_kwargs(
                orchestrator,
                "TASK-TSD1A-010",
                {"behavioural_oracle": {"commnad": "npm test"}},
            )

    def test_out_of_bound_timeout_fails_loudly(
        self, orchestrator: AutoBuildOrchestrator
    ) -> None:
        import pydantic
        import pytest as _pytest

        with _pytest.raises(pydantic.ValidationError):
            _capture_loop_kwargs(
                orchestrator,
                "TASK-TSD1A-011",
                {"behavioural_oracle": {"command": "npm test", "timeout": 999999}},
            )
