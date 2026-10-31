"""The Coach turn: the project's own checks, then the reviewer (27 October 2026).

``AutoBuildOrchestrator._invoke_coach_safely`` gathers the project's own check
results (``CoachValidator.gather_evidence``) and invokes the reviewer (the LLM
Coach, ``AgentInvoker.invoke_coach``) on every turn with them. The reviewer's
verdict is advice: its findings are kept in ``coach_turn_N.json`` and the
turn is sent back only when the project's own checks ran and failed.

Checked here:

* the seam: ``gather_evidence`` once, the reviewer once, the bundle passed
  through unchanged, the log line; a gathering error leaves the reviewer to
  run without a bundle; the reviewer's own failures pass through unchanged;
  the input bundle is persisted beside the turn;
* end to end, through the real ``_invoke_coach_safely`` →
  ``CoachValidator.gather_evidence`` over a declared test command →
  ``AgentInvoker.invoke_coach`` with only the model call stubbed: a reviewer
  ``feedback`` verdict over a passing run is approved and its findings are
  kept in ``coach_turn_N.json``; a required suite that ran and failed is sent
  back; a reviewer that gives no readable verdict leaves the turn approved.

The verbatim log line ``"Using LLM Coach (primary)"`` is the operational
signal operators use to confirm the Coach path; it must not drift.
"""

from __future__ import annotations

import json
import logging
import stat
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.agent_invoker import AgentInvocationResult, AgentInvoker
from guardkit.orchestrator.harness.adapter import AssistantMessageEvent
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
    RuntimeParityResult,
)
from guardkit.orchestrator.quality_gates.coach_validator import IndependentTestResult
from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain
from guardkit.worktrees.manager import Worktree


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_worktree() -> Worktree:
    worktree = MagicMock(spec=Worktree)
    worktree.task_id = "TASK-LCP-001"
    worktree.path = Path("/tmp/worktrees/TASK-LCP-001")
    worktree.branch_name = "autobuild/TASK-LCP-001"
    worktree.base_branch = "main"
    return worktree


@pytest.fixture
def mock_worktree_manager(mock_worktree) -> MagicMock:
    manager = MagicMock()
    manager.create.return_value = mock_worktree
    manager.preserve_on_failure.return_value = None
    manager.worktrees_dir = Path("/tmp/worktrees")
    return manager


@pytest.fixture
def mock_agent_invoker() -> MagicMock:
    """Mock AgentInvoker whose invoke_coach has the REAL signature attached.

    The autobuild primary path uses ``inspect.signature`` to probe whether the
    target accepts ``evidence_bundle`` / ``coach_context`` kwargs before
    threading them through (defensive guard added in Part B for the
    transitional window where Part C had not yet landed). A bare ``AsyncMock``
    has an empty signature, so the probe drops the kwargs silently — which
    would mean the test never proves the bundle flows through. We copy the
    real signature onto the mock so the probe sees the correct kwargs.

    The annotation-stripping below is needed for Python 3.14 compatibility
    (``inspect.signature`` chokes on ``AsyncMock.__annotate__``).
    """
    import inspect

    real_sig = inspect.signature(AgentInvoker.invoke_coach)
    invoker = MagicMock()
    invoker.invoke_player = AsyncMock()
    invoker.invoke_coach = AsyncMock(
        return_value=AgentInvocationResult(
            task_id="TASK-LCP-001",
            turn=1,
            agent_type="coach",
            success=True,
            report={"decision": "approve", "rationale": "primary path test stub"},
            duration_seconds=0.0,
        ),
    )
    invoker.invoke_coach.__signature__ = real_sig.replace(
        # Drop `self` so the probe sees an unbound-method-like signature.
        parameters=[
            p for p in real_sig.parameters.values() if p.name != "self"
        ]
    )
    return invoker


@pytest.fixture
def mock_progress_display() -> MagicMock:
    display = MagicMock()
    display.__enter__ = MagicMock(return_value=display)
    display.__exit__ = MagicMock(return_value=False)
    display.start_turn = MagicMock()
    display.complete_turn = MagicMock()
    display.render_summary = MagicMock()
    return display


@pytest.fixture
def orchestrator(
    mock_worktree_manager: MagicMock,
    mock_agent_invoker: MagicMock,
    mock_progress_display: MagicMock,
) -> AutoBuildOrchestrator:
    return AutoBuildOrchestrator(
        repo_root=Path("/tmp/test-repo"),
        max_turns=5,
        worktree_manager=mock_worktree_manager,
        agent_invoker=mock_agent_invoker,
        progress_display=mock_progress_display,
        enable_context=False,
    )


def _empty_bundle() -> CoachEvidenceBundle:
    """A complete bundle whose changed parts' tests ran and passed. A bundle
    with no test result at all now stops the turn (1 November 2026)."""
    return CoachEvidenceBundle(
        gathering_status="complete",
        task_type="feature",
        profile_name="feature",
        independent_tests=IndependentTestResult(
            tests_passed=True,
            test_command="true",
            test_output_summary="passed",
            duration_seconds=0.0,
        ),
    )


def _invoke_coach(
    orch: AutoBuildOrchestrator,
    worktree: Worktree,
    *,
    task_id: str = "TASK-LCP-001",
) -> AgentInvocationResult:
    return orch._invoke_coach_safely(
        task_id=task_id,
        turn=1,
        requirements="Test requirements",
        player_report={"status": "completed", "files_modified": [], "files_created": []},
        worktree=worktree,
    )


# ---------------------------------------------------------------------------
# The Coach turn: gather evidence, then the reviewer
# ---------------------------------------------------------------------------


class TestPrimaryFlow:
    """The reviewer runs on every turn, given the evidence bundle."""

    @patch.dict("os.environ", {}, clear=False)
    def test_gather_evidence_called_once(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.return_value = _empty_bundle()
            mock_validator_class.return_value = mock_instance

            _invoke_coach(orchestrator, mock_worktree)

            assert mock_instance.gather_evidence.call_count == 1, (
                "Primary path must call gather_evidence exactly once"
            )

    @patch.dict("os.environ", {}, clear=False)
    def test_invoke_coach_called_on_every_turn(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The reviewer runs on EVERY turn."""
        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.return_value = _empty_bundle()
            mock_validator_class.return_value = mock_instance

            _invoke_coach(orchestrator, mock_worktree)

            assert mock_agent_invoker.invoke_coach.call_count == 1

    @patch.dict("os.environ", {}, clear=False)
    def test_invoke_coach_receives_evidence_bundle(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Part B/C wiring: the bundle produced by gather_evidence must
        flow to invoke_coach so Part C's prompt renderer can use it."""
        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            sentinel_bundle = _empty_bundle()
            mock_instance = MagicMock()
            mock_instance.gather_evidence.return_value = sentinel_bundle
            mock_validator_class.return_value = mock_instance

            _invoke_coach(orchestrator, mock_worktree)

            call_kwargs = mock_agent_invoker.invoke_coach.call_args.kwargs
            assert "evidence_bundle" in call_kwargs, (
                "invoke_coach must receive the evidence_bundle kwarg under the "
                "primary path (Part C signature extension)."
            )
            assert call_kwargs["evidence_bundle"] is sentinel_bundle, (
                "The exact bundle produced by gather_evidence must reach invoke_coach "
                "— intermediate handling should not replace or rebuild it."
            )

    @patch.dict("os.environ", {}, clear=False)
    def test_primary_log_line_emitted(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-007: verbatim log line `"Using LLM Coach (primary)"`."""
        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.return_value = _empty_bundle()
            mock_validator_class.return_value = mock_instance

            with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.autobuild"):
                _invoke_coach(orchestrator, mock_worktree)

        assert any(
            "Using LLM Coach (primary)" in record.message
            for record in caplog.records
        ), "AC-007: primary-path log line missing"


# ---------------------------------------------------------------------------
# A gathering error: nothing was measured, so the check could not run
# ---------------------------------------------------------------------------


class TestPrimaryFlowGatheringError:
    def test_gather_evidence_exception_stops_the_turn_as_could_not_run(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_worktree.path = tmp_path

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.side_effect = RuntimeError("boom")
            mock_validator_class.return_value = mock_instance

            result = _invoke_coach(orchestrator, mock_worktree)

        # It used to run the reviewer without the bundle and approve the
        # task untested (1 November 2026).
        assert mock_agent_invoker.invoke_coach.call_count == 0
        assert result.success is False
        assert result.error.startswith("The check could not run")
        assert "RuntimeError: boom" in result.error
        evidence_path = TaskArtifactPaths.private_artifact_path(
            "TASK-LCP-001", "coach_evidence_turn_1.json", tmp_path
        )
        assert json.loads(evidence_path.read_text()) is None


# ---------------------------------------------------------------------------
# The reviewer's own failures pass through unchanged
# ---------------------------------------------------------------------------


class TestPrimaryFlowReviewerOutcomes:
    def test_sdk_timeout_propagates_unchanged(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-003: ``SDKTimeoutError`` is NOT a verdict-emission failure
        and must continue to propagate as success=False. The orchestrator's
        wave loop handles timeout distinctly from verdict-emission.
        """
        mock_worktree.path = tmp_path

        # invoke_coach turns SDKTimeoutError into:
        #   error=f"SDK timeout after {self.sdk_timeout_seconds}s: {str(e)}"
        # See agent_invoker.py:1998-2008.
        timeout_result = AgentInvocationResult(
            task_id="TASK-LCP-001",
            turn=1,
            agent_type="coach",
            success=False,
            report={},
            duration_seconds=900.0,
            error="SDK timeout after 900s: query exceeded budget",
        )
        mock_agent_invoker.invoke_coach.return_value = timeout_result

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.return_value = _empty_bundle()
            mock_validator_class.return_value = mock_instance

            result = _invoke_coach(orchestrator, mock_worktree)

        # Propagated as-is, NOT converted to synthetic feedback.
        assert result is timeout_result, (
            "AC-003: SDKTimeoutError outcomes must pass through unchanged. "
            "Only verdict-emission failures (decision not found / invalid) "
            "convert to synthetic feedback."
        )
        assert result.success is False
        # No coach_turn_N.json should have been written by the soft-fail path.
        decision_path = (
            tmp_path / ".guardkit" / "autobuild-private" / "TASK-LCP-001" / "coach_turn_1.json"
        )
        assert not decision_path.exists(), (
            "Soft-fail path must NOT fire for SDKTimeoutError. If "
            "coach_turn_1.json exists, the narrow scope of AC-003 has been "
            "violated."
        )

    def test_unexpected_error_propagates_unchanged(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-003: generic ``Unexpected error`` (the catch-all branch in
        ``invoke_coach``) is not a verdict-emission failure either and
        must propagate as success=False.
        """
        mock_worktree.path = tmp_path

        # invoke_coach's catch-all branch produces:
        #   error=f"Unexpected error: {str(e)}"
        # See agent_invoker.py:2009-2018.
        unexpected_result = AgentInvocationResult(
            task_id="TASK-LCP-001",
            turn=1,
            agent_type="coach",
            success=False,
            report={},
            duration_seconds=12.5,
            error="Unexpected error: ConnectionResetError on httpx stream",
        )
        mock_agent_invoker.invoke_coach.return_value = unexpected_result

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.return_value = _empty_bundle()
            mock_validator_class.return_value = mock_instance

            result = _invoke_coach(orchestrator, mock_worktree)

        assert result is unexpected_result
        assert result.success is False
        # No on-disk synthetic feedback.
        decision_path = (
            tmp_path / ".guardkit" / "autobuild-private" / "TASK-LCP-001" / "coach_turn_1.json"
        )
        assert not decision_path.exists()

    def test_success_true_propagates_unchanged(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Sanity guard: the soft-fail predicate is gated on success=False.
        A normal successful Coach decision MUST flow through untouched and
        NOT be replaced by synthetic feedback.
        """
        mock_worktree.path = tmp_path

        approved_result = AgentInvocationResult(
            task_id="TASK-LCP-001",
            turn=1,
            agent_type="coach",
            success=True,
            report={"decision": "approve", "rationale": "real approval"},
            duration_seconds=4.2,
        )
        mock_agent_invoker.invoke_coach.return_value = approved_result

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.return_value = _empty_bundle()
            mock_validator_class.return_value = mock_instance

            result = _invoke_coach(orchestrator, mock_worktree)

        assert result is approved_result
        assert result.report.get("decision") == "approve"
        # No synthetic-feedback marker on a real approval.
        assert "coach_primary_synthetic_feedback" not in result.report


# ---------------------------------------------------------------------------
# Coach v3 Step 1 — persist the INPUT evidence bundle per turn
# ---------------------------------------------------------------------------


class TestPrimaryFlowEvidenceBundlePersistence:
    """Coach v3 Step 1: the ``CoachEvidenceBundle`` that DROVE the verdict is
    persisted to ``coach_evidence_turn_N.json`` beside ``coach_turn_N.json``.

    ``coach_turn_N.json`` records only the Coach's OUTPUT (decision / issues /
    criteria / rationale); the input bundle was never saved, so the dataset
    harvest had to reconstruct it lossily and ended up training the Coach on
    ``player_report`` ONLY — the train!=serve mismatch behind the rubber-stamp.
    Persisting the bundle yields production-faithful
    ``(prompt-with-bundle -> verdict)`` training pairs for every future run.
    """

    def _rich_bundle(self) -> CoachEvidenceBundle:
        """A bundle carrying the signals reconstruction could NOT recover
        (the Coach's own independent_tests and the smoke command's run)."""
        return CoachEvidenceBundle(
            gathering_status="complete",
            runtime_parity=RuntimeParityResult(
                ran=True, passed=True, command="make smoke", exit_code=0,
            ),
            independent_tests=IndependentTestResult(
                tests_passed=False,
                test_command="pytest -q",
                test_output_summary="3 failed, 27 passed",
                duration_seconds=8.0,
            ),
            task_type="feature",
        )

    def test_evidence_bundle_persisted_to_disk(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_worktree.path = tmp_path

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.return_value = self._rich_bundle()
            mock_validator_class.return_value = mock_instance

            _invoke_coach(orchestrator, mock_worktree)

        evidence_path = (
            tmp_path
            / ".guardkit"
            / "autobuild-private"
            / "TASK-LCP-001"
            / "coach_evidence_turn_1.json"
        )
        assert evidence_path.exists(), (
            "Coach v3 Step 1: the input CoachEvidenceBundle must be persisted to "
            "coach_evidence_turn_N.json so future harvests can build "
            "production-faithful (prompt-with-bundle -> verdict) training pairs."
        )
        saved = json.loads(evidence_path.read_text())
        # The discriminating signals that bundle reconstruction could NOT recover
        # (Coach's own verification) are present verbatim.
        assert saved["runtime_parity"]["command"] == "make smoke"
        assert saved["independent_tests"]["tests_passed"] is False
        assert saved["independent_tests"]["test_output_summary"] == "3 failed, 27 passed"

    def test_persistence_failure_does_not_block_turn(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Best-effort: a serialisation failure when persisting the bundle MUST
        NOT block the turn — the Coach verdict still flows through. (The write
        is wrapped in a guarded try/except.)"""
        mock_worktree.path = tmp_path

        bundle = self._rich_bundle()

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class, patch(
            "guardkit.orchestrator.autobuild.json.dump",
            side_effect=RuntimeError("serialise boom"),
        ):
            mock_instance = MagicMock()
            mock_instance.gather_evidence.return_value = bundle
            mock_validator_class.return_value = mock_instance

            result = _invoke_coach(orchestrator, mock_worktree)

        # Turn completes with the Coach's decision despite the persistence error.
        assert result.report.get("decision") == "approve"
        evidence_path = (
            tmp_path
            / ".guardkit"
            / "autobuild-private"
            / "TASK-LCP-001"
            / "coach_evidence_turn_1.json"
        )
        # The write was attempted but failed — no (or empty) artifact, and crucially
        # no exception escaped to fail the turn.
        assert not evidence_path.exists() or evidence_path.read_text() == ""


# ---------------------------------------------------------------------------
# End to end: the real Coach turn, with only the model call stubbed
# ---------------------------------------------------------------------------

_TASK = "TASK-LCP-E2E"
_FAILING = "tests/test_users.py::test_delete_twice"


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Coach Test",
         "-c", "user.email=coach@example.invalid", *args],
        check=True, capture_output=True, text=True,
    )


def _project(tmp_path: Path, suite_output: str, exit_code: int) -> Path:
    """A git project whose declared test command prints ``suite_output``."""
    root = tmp_path / "project"
    root.mkdir()
    (root / ".guardkit").mkdir()
    (root / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": {"test": "bash qa/run-suite.sh"}}),
        encoding="utf-8",
    )
    (root / ".gitignore").write_text(".guardkit/autobuild-private/\n")
    qa = root / "qa"
    qa.mkdir()
    body = "\n".join(f"echo {line!r}" for line in suite_output.splitlines())
    script = qa / "run-suite.sh"
    script.write_text(f"#!/bin/sh\n{body}\nexit {exit_code}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "start")
    _git(root, "checkout", "-q", "-b", f"autobuild/{_TASK}")
    snapshot_task_toolchain(_TASK, root, root)
    return root


def _reviewer_says(verdict: Optional[Dict[str, Any]]) -> AsyncMock:
    """The model call, stubbed: the reviewer's response text ends with its
    verdict as a fenced json block (or holds no verdict at all)."""
    text = "I read the evidence."
    if verdict is not None:
        text += "\n\n```json\n" + json.dumps(verdict) + "\n```\n"
    return AsyncMock(return_value=(None, [AssistantMessageEvent(text=text)]))


def _real_turn(
    tmp_path: Path, root: Path, reviewer: AsyncMock
) -> AgentInvocationResult:
    invoker = AgentInvoker(worktree_path=root, sdk_timeout_seconds=600)
    orchestrator = AutoBuildOrchestrator(
        repo_root=root,
        max_turns=3,
        worktree_manager=MagicMock(worktrees_dir=tmp_path),
        agent_invoker=invoker,
        enable_context=False,
    )
    worktree = Worktree(
        task_id=_TASK, branch_name=f"autobuild/{_TASK}", path=root, base_branch="main",
    )
    # The task's own change since its starting commit, in the root part, so
    # the root's declared suite is what runs (31 October 2026).
    from types import SimpleNamespace

    start = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    orchestrator.task_work_scope = SimpleNamespace(baseline_commit=start)
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "users.py").write_text("DELETED = set()\n", encoding="utf-8")
    with patch.object(invoker, "_invoke_with_role", reviewer):
        result = orchestrator._invoke_coach_safely(
            task_id=_TASK,
            turn=1,
            requirements="Delete a user twice without an error.",
            player_report={"task_id": _TASK, "turn": 1, "files_modified": []},
            worktree=worktree,
            acceptance_criteria=["Deleting twice answers 404"],
            task_type="feature",
        )
    # The look-up pass, then the verdict call (the build reviewer design of
    # 29 October 2026).
    assert reviewer.await_count == 2
    return result


def _coach_record(root: Path) -> Dict[str, Any]:
    return json.loads(
        TaskArtifactPaths.private_artifact_path(_TASK, "coach_turn_1.json", root).read_text()
    )


_REVIEWER_FINDING = {
    "severity": "must_fix",
    "category": "missing_test",
    "description": "No test covers deleting a user twice.",
}


class TestTheRealCoachTurn:
    def test_a_feedback_verdict_over_a_passing_run_is_approved_and_kept(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path, "5 passed in 0.50s\n", 0)
        reviewer = _reviewer_says({
            "task_id": _TASK, "turn": 1, "decision": "feedback",
            "issues": [_REVIEWER_FINDING],
            "rationale": "A test is missing.",
        })

        result = _real_turn(tmp_path, root, reviewer)

        assert result.success is True, result.error
        assert result.report["decision"] == "approve"
        record = _coach_record(root)
        assert record["decision"] == "approve"
        assert record["issues"] == [_REVIEWER_FINDING]
        independent = result.report["validation_results"]["independent_tests"]
        assert independent["tests_passed"] is True
        assert independent["test_command"] == "bash qa/run-suite.sh"

    def test_a_required_suite_that_ran_and_failed_is_sent_back(
        self, tmp_path: Path
    ) -> None:
        root = _project(
            tmp_path,
            f"FAILED {_FAILING} - AssertionError: deleted twice\n1 failed, 4 passed in 0.50s\n",
            1,
        )
        reviewer = _reviewer_says({
            "task_id": _TASK, "turn": 1, "decision": "approve", "issues": [],
            "rationale": "Looks complete.",
        })

        result = _real_turn(tmp_path, root, reviewer)

        assert result.success is True, result.error
        assert result.report["decision"] == "feedback"
        categories = [i["category"] for i in result.report["issues"]]
        assert categories[0] == "independent_test_code_failure"
        record = _coach_record(root)
        assert record["decision"] == "feedback"
        assert _FAILING in json.dumps(record["issues"])

        from guardkit.orchestrator.failing_test_feedback import SUITE_RECEIPT_KEY

        receipt = result.report[SUITE_RECEIPT_KEY]
        assert receipt["command"] == "bash qa/run-suite.sh"
        assert any(_FAILING in line for line in receipt["failing_lines"])

    def test_no_readable_verdict_leaves_a_green_turn_approved(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path, "5 passed in 0.50s\n", 0)

        result = _real_turn(tmp_path, root, _reviewer_says(None))

        assert result.success is True, result.error
        assert result.report["decision"] == "approve"
        assert result.report["issues"] == []
        assert _coach_record(root)["decision"] == "approve"
