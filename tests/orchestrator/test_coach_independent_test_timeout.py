"""Regression tests for TASK-FIX-COACHTESTTO.

The Coach's independent test run: a run that does not produce a verdict
never reads as a pass, and the reviewer sees ``signal_absent`` in the evidence
bundle. (The SDK test path and its LangGraph bypass were removed on 1 November
2026; the declared command always runs through the shell.)

See ``docs/state/TASK-FIX-COACHTESTTO/diagnosis.md`` and
``.claude/rules/absence-of-failure-is-not-success.md``.

Coverage Target: >=85%
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)

_CV_MOD = "guardkit.orchestrator.quality_gates.coach_validator"


def _build_invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    return invoker


# ---------------------------------------------------------------------------
# AC-3: non-completion paths mark the result ABSENT (signal_absent=True)
# ---------------------------------------------------------------------------


class TestAbsentSignalMarking:
    """A run that does not produce a verdict must set ``signal_absent=True``
    and ``tests_passed=False`` so it can never read as a pass."""

    def test_default_present_signal_is_false(self) -> None:
        """A normal result has signal_absent=False (backward compatible)."""
        result = IndependentTestResult(
            tests_passed=True,
            test_command="pytest",
            test_output_summary="ok",
            duration_seconds=1.0,
        )
        assert result.signal_absent is False

    def test_subprocess_timeout_is_a_failure_sent_back(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """31 October 2026: a run that started and did not finish within its
        limit is a failure for the builder (TASK-C2C7-002), not an absence."""
        validator = CoachValidator(
            str(tmp_path),
            task_id="TASK-T",
            test_command="pytest tests/x.py",
            test_timeout=5,
        )
        timeout_exc = subprocess.TimeoutExpired(cmd="pytest", timeout=5)
        with patch(f"{_CV_MOD}.subprocess.run", side_effect=timeout_exc):
            result = validator.run_independent_tests()

        assert result.signal_absent is False
        assert result.tests_passed is False
        assert "timed out" in result.test_output_summary.lower()
        assert "5-second limit" in result.test_output_summary
        assert result.failure_receipt() is not None

    def test_subprocess_generic_error_marks_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        validator = CoachValidator(
            str(tmp_path),
            task_id="TASK-T",
            test_command="pytest tests/x.py",
        )
        with patch(
            f"{_CV_MOD}.subprocess.run", side_effect=OSError("boom")
        ):
            result = validator.run_independent_tests()

        assert result.signal_absent is True
        assert result.tests_passed is False


# ---------------------------------------------------------------------------
# AC-3 (prompt side): the reviewer sees signal_absent in the evidence bundle
# ---------------------------------------------------------------------------


class TestIndependentTestAbsentInEvidence:
    """The bundle must serialise ``signal_absent`` into the reviewer's prompt."""

    def test_absent_result_serialised_in_evidence_block(
        self, tmp_path: Path
    ) -> None:
        """``signal_absent: true`` is in the JSON-serialised bundle the
        reviewer reads."""
        bundle = CoachEvidenceBundle(
            gathering_status="complete",
            independent_tests=IndependentTestResult(
                tests_passed=False,
                test_command="pytest",
                test_output_summary="timed out",
                duration_seconds=300.0,
                signal_absent=True,
            ),
            task_type="feature",
            profile_name="feature",
        )

        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-T",
            turn=1,
            requirements="x",
            player_report={"files_modified": []},
            evidence_bundle=bundle,
        )

        evidence_block = prompt[
            prompt.index("<evidence_bundle>") : prompt.index("</evidence_bundle>")
        ]
        assert '"signal_absent": true' in evidence_block


# ---------------------------------------------------------------------------
# TASK-FIX-BSEXTRAS01: absent test RUNNER (not just timeout) → signal_absent
# ---------------------------------------------------------------------------


class TestAbsentRunnerMarksAbsent:
    """FEAT-9DDE run-6 read 'No module named pytest' and exit 5 as an absent
    runner. Since 31 October 2026 no pytest-shaped reading is applied to a
    command's output (those two tests went with it); what stays is that a
    run that ran and failed is a real failure.
    """

    def _validator(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CoachValidator:
        return CoachValidator(
            str(tmp_path),
            task_id="TASK-T",
            test_command="pytest tests/x.py",
        )

    def test_genuine_test_failure_not_marked_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Negative control: the oracle RAN and the Player's tests failed —
        that is a real signal, NOT absent."""
        validator = self._validator(tmp_path, monkeypatch)
        completed = subprocess.CompletedProcess(
            args=["python", "-m", "pytest"],
            returncode=1,
            stdout="2 failed, 8 passed in 3.2s",
            stderr="",
        )
        with patch(f"{_CV_MOD}.subprocess.run", return_value=completed):
            result = validator.run_independent_tests()
        assert result.signal_absent is False
        assert result.tests_passed is False

    def test_missing_app_module_is_real_failure_not_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A Player test importing a missing APP module is a real defect, not
        an absent runner — only the runner itself ('No module named pytest')
        counts as absent, never an app-level import error."""
        validator = self._validator(tmp_path, monkeypatch)
        completed = subprocess.CompletedProcess(
            args=["python", "-m", "pytest"],
            returncode=2,  # pytest collection error
            stdout="",
            stderr="ModuleNotFoundError: No module named 'myapp'\n",
        )
        with patch(f"{_CV_MOD}.subprocess.run", return_value=completed):
            result = validator.run_independent_tests()
        assert result.signal_absent is False
        assert result.tests_passed is False
