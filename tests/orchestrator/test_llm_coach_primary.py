"""AC-015 — _invoke_coach_safely routing decision (TASK-HMIG-008R Part E).

Verifies the Part B inversion: by default the LLM Coach is the primary
decision-maker (CoachValidator.gather_evidence + AgentInvoker.invoke_coach);
``GUARDKIT_COACH_LEGACY=1`` reactivates the legacy flow (CoachValidator.validate
as primary, LLM Coach as exception fallback).

Falsifier shapes:

* **Default flow (env var unset)**:
  - ``CoachValidator.gather_evidence`` is called exactly once.
  - ``CoachValidator.validate`` is NOT called.
  - ``AgentInvoker.invoke_coach`` is called exactly once (the LLM Coach
    runs on every turn, not just on validator exception).
  - The verbatim log line ``"Using LLM Coach (primary)"`` is emitted.
* **Legacy flow (GUARDKIT_COACH_LEGACY=1)**:
  - ``CoachValidator.validate`` is called exactly once.
  - ``CoachValidator.gather_evidence`` is NOT called (the legacy
    branch returns before reaching the primary path).
  - ``AgentInvoker.invoke_coach`` is NOT called when validate succeeds.
    (It IS called only via the legacy except-branch fallback, which is
    a separate test case.)
  - The verbatim log line ``"Using CoachValidator (legacy,
    GUARDKIT_COACH_LEGACY=1)"`` is emitted.

These verbatim log strings are referenced by AC-007 in the task spec and
must not drift — they are the operational signal operators use to confirm
which Coach path is active.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.agent_invoker import AgentInvocationResult, AgentInvoker
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.coach_verification import HonestyVerification
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
    return CoachEvidenceBundle(
        honesty=HonestyVerification(verified=True),
        gathering_status="complete",
        task_type="feature",
        profile_name="feature",
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
# Default flow — LLM Coach as primary decision-maker
# ---------------------------------------------------------------------------


class TestPrimaryFlow:
    """``GUARDKIT_COACH_LEGACY`` unset → LLM Coach is primary."""

    @patch.dict("os.environ", {}, clear=False)
    def test_gather_evidence_called_once(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
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
    def test_validate_not_called(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Falsifier #1: ``autobuild._invoke_coach -> CoachValidator.validate()
        for the decision is GONE`` under the default path."""
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.return_value = _empty_bundle()
            mock_validator_class.return_value = mock_instance

            _invoke_coach(orchestrator, mock_worktree)

            assert mock_instance.validate.call_count == 0, (
                "Falsifier #1: validate() must NOT be called on the primary path. "
                "If this fails, the deterministic CoachValidator has silently "
                "re-become the decision-maker, contradicting the Block "
                "adversarial-cooperation paper."
            )

    @patch.dict("os.environ", {}, clear=False)
    def test_invoke_coach_called_on_every_turn(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Falsifier #1 sibling: the LLM Coach runs on EVERY turn under
        the default path, not just on validator exception."""
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
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
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
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
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
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
# Legacy flow — operator-controlled revert
# ---------------------------------------------------------------------------


class TestLegacyFlow:
    """``GUARDKIT_COACH_LEGACY=1`` → CoachValidator.validate is primary."""

    def test_validate_called_once(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_LEGACY", "1")
        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.to_dict.return_value = {"decision": "approve"}
            mock_instance.validate.return_value = mock_result
            mock_validator_class.return_value = mock_instance

            _invoke_coach(orchestrator, mock_worktree)

            assert mock_instance.validate.call_count == 1

    def test_gather_evidence_not_called(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Legacy branch does NOT enter the primary path at all."""
        monkeypatch.setenv("GUARDKIT_COACH_LEGACY", "1")
        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.to_dict.return_value = {"decision": "approve"}
            mock_instance.validate.return_value = mock_result
            mock_validator_class.return_value = mock_instance

            _invoke_coach(orchestrator, mock_worktree)

            assert mock_instance.gather_evidence.call_count == 0

    def test_invoke_coach_not_called_when_validate_succeeds(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The LLM Coach is only the except-fallback under legacy, so it must
        NOT be invoked when validate() returns cleanly."""
        monkeypatch.setenv("GUARDKIT_COACH_LEGACY", "1")
        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.to_dict.return_value = {"decision": "approve"}
            mock_instance.validate.return_value = mock_result
            mock_validator_class.return_value = mock_instance

            _invoke_coach(orchestrator, mock_worktree)

            assert mock_agent_invoker.invoke_coach.call_count == 0

    def test_legacy_log_line_emitted(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-007: verbatim log line
        `"Using CoachValidator (legacy, GUARDKIT_COACH_LEGACY=1)"`.
        """
        monkeypatch.setenv("GUARDKIT_COACH_LEGACY", "1")
        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.to_dict.return_value = {"decision": "approve"}
            mock_instance.validate.return_value = mock_result
            mock_validator_class.return_value = mock_instance

            with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.autobuild"):
                _invoke_coach(orchestrator, mock_worktree)

        assert any(
            "Using CoachValidator (legacy, GUARDKIT_COACH_LEGACY=1)"
            in record.message
            for record in caplog.records
        ), "AC-007: legacy-path log line missing"


# ---------------------------------------------------------------------------
# Exception handling on the primary path — synthetic feedback, not validate()
# ---------------------------------------------------------------------------


class TestPrimaryFlowExceptionHandling:
    """Per Phase 2.5 review finding #1 and plan §3: unexpected exceptions
    in ``gather_evidence`` MUST NOT fall back to ``validate()`` — that
    would reactivate falsifier #1's forbidden path. Instead, a synthetic
    feedback coach_turn_N.json is written and an AgentInvocationResult
    with decision="feedback" is returned.
    """

    def test_gather_evidence_exception_emits_synthetic_feedback(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
        # Point the mock worktree at a real tmp_path so file writes work.
        mock_worktree.path = tmp_path

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.side_effect = RuntimeError(
                "synthetic_failure"
            )
            mock_validator_class.return_value = mock_instance

            result = _invoke_coach(orchestrator, mock_worktree)

            # Synthetic feedback decision returned
            assert result.report.get("decision") == "feedback"
            assert "synthetic_failure" in result.report.get("rationale", "")
            assert result.report.get("coach_primary_synthetic_feedback") is True

    def test_gather_evidence_exception_does_not_call_validate(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The critical falsifier-#1 protection: on primary-path exception,
        validate() MUST NOT silently re-become the decision-maker."""
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
        mock_worktree.path = tmp_path

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.side_effect = RuntimeError("boom")
            mock_validator_class.return_value = mock_instance

            _invoke_coach(orchestrator, mock_worktree)

            assert mock_instance.validate.call_count == 0, (
                "Falsifier #1: validate() must NOT be called as exception "
                "fallback in the primary path. GUARDKIT_COACH_LEGACY=1 is the "
                "sole operator-controlled mechanism for reactivating validate()."
            )

    def test_synthetic_feedback_written_to_disk(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
        mock_worktree.path = tmp_path

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.side_effect = ValueError("oops")
            mock_validator_class.return_value = mock_instance

            _invoke_coach(orchestrator, mock_worktree)

        decision_path = (
            tmp_path / ".guardkit" / "autobuild" / "TASK-LCP-001" / "coach_turn_1.json"
        )
        assert decision_path.exists(), (
            "Synthetic feedback must write coach_turn_N.json to disk so the "
            "downstream consumer chain (_display_criteria_progress, "
            "_count_criteria_passed) sees a consistent shape."
        )


# ---------------------------------------------------------------------------
# TASK-FIX-COACHSF01 — soft-fail on Coach verdict-emission failures
# ---------------------------------------------------------------------------


class TestPrimaryFlowVerdictEmissionSoftFail:
    """TASK-FIX-COACHSF01 regression: when ``invoke_coach`` catches
    ``CoachDecisionNotFoundError`` / ``CoachDecisionInvalidError`` internally
    and returns ``success=False`` with the exception text in ``error``,
    ``_invoke_coach_primary`` MUST convert that into a synthetic feedback
    decision (so the Player gets a turn N+1 with Coach's feedback) instead of
    surfacing ``success=False`` to the wave loop and hard-failing the turn.

    Falsifier (from the task spec): "After landing, ... if Coach LLM
    completes its invocation but does NOT write coach_turn_N.json
    (qwen36-workhorse F2-at-Coach-level substrate behaviour),
    ``_invoke_coach_primary`` MUST emit a synthetic feedback decision
    (writes coach_turn_N.json with rationale naming the failure mode) and
    return success=True."

    Other ``success=False`` outcomes (``SDKTimeoutError``, generic
    ``Unexpected error``) MUST continue to propagate as-is (AC-003) — the
    soft-fail is narrowly scoped to verdict-emission failures.
    """

    def test_decision_not_found_emits_synthetic_feedback(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-002 + AC-004: ``invoke_coach`` returns success=False with
        "Coach decision not found" → synthetic feedback fires.
        """
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
        mock_worktree.path = tmp_path

        # Simulate invoke_coach catching CoachDecisionNotFoundError internally.
        mock_agent_invoker.invoke_coach.return_value = AgentInvocationResult(
            task_id="TASK-LCP-001",
            turn=1,
            agent_type="coach",
            success=False,
            report={},
            duration_seconds=0.0,
            error="Coach decision not found: coach_turn_1.json missing",
        )

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.return_value = _empty_bundle()
            mock_validator_class.return_value = mock_instance

            result = _invoke_coach(orchestrator, mock_worktree)

        # Synthetic feedback fired: success=True, decision=feedback, on-disk.
        assert result.success is True, (
            "AC-004: verdict-emission failure must be soft-failed as "
            "synthetic feedback (success=True), not hard-failed as "
            "success=False (which the wave loop reads as coach_decision=error)."
        )
        assert result.report.get("decision") == "feedback"
        assert result.report.get("coach_primary_synthetic_feedback") is True
        # Rationale names the failure mode so future runs / Graphiti can
        # distinguish this class from other Coach-side errors.
        assert "verdict-emission failed" in result.report.get("rationale", "")
        assert "Coach decision not found" in result.report.get("rationale", "")

        # coach_turn_1.json was written.
        decision_path = (
            tmp_path / ".guardkit" / "autobuild" / "TASK-LCP-001" / "coach_turn_1.json"
        )
        assert decision_path.exists(), (
            "Synthetic feedback must write coach_turn_N.json so downstream "
            "consumers see a consistent shape."
        )

    def test_decision_invalid_emits_synthetic_feedback(
        self,
        orchestrator: AutoBuildOrchestrator,
        mock_worktree: Worktree,
        mock_agent_invoker: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-002 sibling: ``CoachDecisionInvalidError`` (malformed JSON) is
        the same failure class as not-found and must also soft-fail.
        """
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
        mock_worktree.path = tmp_path

        mock_agent_invoker.invoke_coach.return_value = AgentInvocationResult(
            task_id="TASK-LCP-001",
            turn=2,
            agent_type="coach",
            success=False,
            report={},
            duration_seconds=0.0,
            error="Coach decision invalid: missing 'decision' field",
        )

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as mock_validator_class:
            mock_instance = MagicMock()
            mock_instance.gather_evidence.return_value = _empty_bundle()
            mock_validator_class.return_value = mock_instance

            result = orchestrator._invoke_coach_safely(
                task_id="TASK-LCP-001",
                turn=2,
                requirements="Test requirements",
                player_report={
                    "status": "completed",
                    "files_modified": [],
                    "files_created": [],
                },
                worktree=mock_worktree,
            )

        assert result.success is True
        assert result.report.get("decision") == "feedback"
        assert result.report.get("coach_primary_synthetic_feedback") is True
        assert "Coach decision invalid" in result.report.get("rationale", "")

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
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
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
            tmp_path / ".guardkit" / "autobuild" / "TASK-LCP-001" / "coach_turn_1.json"
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
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
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
            tmp_path / ".guardkit" / "autobuild" / "TASK-LCP-001" / "coach_turn_1.json"
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
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
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
