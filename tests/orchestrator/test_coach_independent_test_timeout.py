"""Regression tests for TASK-FIX-COACHTESTTO.

Coach independent-test (trust-but-verify) execution timed out at 300s under
the LangGraph harness because the SDK path runs pytest through a one-turn LLM
agent invocation against a slow local model (run-19, FEAT-AOF). The fix has
two load-bearing parts:

  AC-2 — under the LangGraph harness, ``run_independent_tests`` forces the
          deterministic subprocess path (``_is_langgraph_harness`` gate),
          bypassing the LLM turn entirely.
  AC-3 — every non-completion path (SDK timeout, SDK API error, subprocess
          timeout, isolated-test timeout, generic execution error) marks the
          result ``signal_absent=True`` (with ``tests_passed=False``) so the
          LLM Coach treats it as ABSENT SIGNAL via the sixth absence-of-failure
          guard rather than approving on the Player's self-reported tests.

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
from guardkit.orchestrator.coach_verification import HonestyVerification
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
# AC-2: LangGraph harness forces the subprocess path
# ---------------------------------------------------------------------------


class TestLangGraphForcesSubprocess:
    """Under ``GUARDKIT_HARNESS=langgraph`` the Coach must run pytest via
    subprocess, never via the LLM-mediated SDK path that timed out in run-19.
    """

    def test_is_langgraph_harness_detects_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        validator = CoachValidator(str(tmp_path), task_id="TASK-T")

        monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")
        assert validator._is_langgraph_harness() is True

        monkeypatch.setenv("GUARDKIT_HARNESS", "LangGraph")  # case-insensitive
        assert validator._is_langgraph_harness() is True

        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
        assert validator._is_langgraph_harness() is False

        monkeypatch.delenv("GUARDKIT_HARNESS", raising=False)
        assert validator._is_langgraph_harness() is False  # default "sdk"

    def test_langgraph_dispatch_skips_sdk_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """coach_test_execution='sdk' + LangGraph harness ⇒ subprocess path,
        and ``_run_tests_via_sdk`` is NOT called."""
        monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)

        validator = CoachValidator(
            str(tmp_path),
            task_id="TASK-T",
            test_command="pytest tests/x.py",
            coach_test_execution="sdk",
        )

        sdk_spy = MagicMock(
            side_effect=AssertionError("SDK path must not run under LangGraph")
        )
        completed = subprocess.CompletedProcess(
            args=["pytest"], returncode=0, stdout="1 passed", stderr=""
        )
        with patch.object(validator, "_run_tests_via_sdk", sdk_spy), patch(
            f"{_CV_MOD}.subprocess.run", return_value=completed
        ) as run_mock:
            result = validator.run_independent_tests()

        sdk_spy.assert_not_called()
        run_mock.assert_called_once()
        assert result.tests_passed is True
        assert result.signal_absent is False

    def test_sdk_harness_still_uses_sdk_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Negative control: with the default SDK harness (no LangGraph, no
        custom API base), the SDK path is still selected."""
        monkeypatch.delenv("GUARDKIT_HARNESS", raising=False)
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)

        validator = CoachValidator(
            str(tmp_path),
            task_id="TASK-T",
            test_command="pytest tests/x.py",
            coach_test_execution="sdk",
        )

        sentinel = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/x.py",
            test_output_summary="sdk ran",
            duration_seconds=1.0,
        )
        with patch.object(
            validator, "_run_tests_via_sdk", AsyncMock(return_value=sentinel)
        ) as sdk_mock:
            result = validator.run_independent_tests()

        sdk_mock.assert_called_once()
        assert result is sentinel


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

    def test_subprocess_timeout_marks_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")  # force subprocess
        validator = CoachValidator(
            str(tmp_path),
            task_id="TASK-T",
            test_command="pytest tests/x.py",
            coach_test_execution="sdk",
            test_timeout=5,
        )
        timeout_exc = subprocess.TimeoutExpired(cmd="pytest", timeout=5)
        with patch(f"{_CV_MOD}.subprocess.run", side_effect=timeout_exc):
            result = validator.run_independent_tests()

        assert result.signal_absent is True
        assert result.tests_passed is False
        assert "timed out" in result.test_output_summary.lower()

    def test_subprocess_generic_error_marks_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")  # force subprocess
        validator = CoachValidator(
            str(tmp_path),
            task_id="TASK-T",
            test_command="pytest tests/x.py",
            coach_test_execution="sdk",
        )
        with patch(
            f"{_CV_MOD}.subprocess.run", side_effect=OSError("boom")
        ):
            result = validator.run_independent_tests()

        assert result.signal_absent is True
        assert result.tests_passed is False

    @pytest.mark.skipif(
        sys.version_info < (3, 11),
        reason=(
            "_run_tests_via_sdk uses asyncio.timeout(), added in Python 3.11; "
            "the SDK path is exercised only on 3.11+ (run-19/production). The "
            "subprocess path — the default under LangGraph after this fix — has "
            "no such dependency and is covered by the tests above."
        ),
    )
    def test_sdk_asyncio_timeout_marks_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The original run-19 failure mode: the harness LLM turn exceeds
        ``test_timeout``. The SDK path must return an ABSENT result, not a
        silent fail that could read as a real verdict."""
        monkeypatch.delenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", raising=False)

        validator = CoachValidator(
            str(tmp_path),
            task_id="TASK-T",
            coach_test_execution="sdk",
            test_timeout=1,  # tiny budget so the hang trips the timeout fast
        )

        class _HangingHarness:
            async def invoke(self, *args, **kwargs):
                await asyncio.sleep(30)  # never completes within test_timeout
                yield  # pragma: no cover - unreachable

        with patch(f"{_CV_MOD}.select_harness", return_value=_HangingHarness()):
            result = asyncio.run(
                validator._run_tests_via_sdk("pytest tests/x.py")
            )

        assert result.signal_absent is True
        assert result.tests_passed is False
        assert "timed out" in result.test_output_summary.lower()


# ---------------------------------------------------------------------------
# AC-3 (prompt side): the sixth absence-of-failure guard
# ---------------------------------------------------------------------------


class TestIndependentTestAbsentGuard:
    """The Coach prompt must carry the INDEPENDENT-TEST ABSENT GUARD and the
    bundle must serialise ``signal_absent`` so the LLM can apply it."""

    def test_guard_sentence_renders(self, tmp_path: Path) -> None:
        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True),
            gathering_status="complete",
            independent_tests=IndependentTestResult(
                tests_passed=False,
                test_command="pytest",
                test_output_summary="SDK test execution timed out after 300s",
                duration_seconds=300.0,
                signal_absent=True,
            ),
            task_type="feature",
            profile_name="feature",
        )

        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-T",
            turn=1,
            requirements="independent-test absent scenario",
            player_report={"files_modified": []},
            evidence_bundle=bundle,
        )

        assert "INDEPENDENT-TEST ABSENT GUARD" in prompt
        assert "signal_absent" in prompt
        assert "ABSENT SIGNAL" in prompt
        assert "absence-of-failure-is-not-success.md" in prompt

    def test_absent_result_serialised_in_evidence_block(
        self, tmp_path: Path
    ) -> None:
        """The Coach can only apply the guard if ``signal_absent: true`` is in
        the JSON-serialised bundle it reads."""
        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True),
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
    """FEAT-9DDE run-6: the pinned worktree interpreter had no pytest, so
    ``python -m pytest`` exited non-zero in 0.0s with 'No module named pytest'.
    That is the oracle failing to RUN (absent signal), not the Player's tests
    failing — it must set ``signal_absent=True`` so the sixth
    absence-of-failure guard can override an approve, instead of being read as
    a real test failure. Sibling of the timeout/exception paths above.
    """

    def _validator(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CoachValidator:
        monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")  # force subprocess path
        return CoachValidator(
            str(tmp_path),
            task_id="TASK-T",
            test_command="pytest tests/x.py",
            coach_test_execution="sdk",
        )

    def test_no_module_named_pytest_marks_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        validator = self._validator(tmp_path, monkeypatch)
        completed = subprocess.CompletedProcess(
            args=["python", "-m", "pytest"],
            returncode=1,
            stdout="",
            stderr="/wt/.venv/bin/python: No module named pytest\n",
        )
        with patch(f"{_CV_MOD}.subprocess.run", return_value=completed):
            result = validator.run_independent_tests()
        assert result.signal_absent is True
        assert result.tests_passed is False

    def test_no_tests_collected_exit5_marks_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        validator = self._validator(tmp_path, monkeypatch)
        completed = subprocess.CompletedProcess(
            args=["python", "-m", "pytest"],
            returncode=5,  # pytest: no tests collected
            stdout="no tests ran in 0.01s",
            stderr="",
        )
        with patch(f"{_CV_MOD}.subprocess.run", return_value=completed):
            result = validator.run_independent_tests()
        assert result.signal_absent is True
        assert result.tests_passed is False

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
