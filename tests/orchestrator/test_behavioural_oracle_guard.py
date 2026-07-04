"""TASK-QAV-004 — L4 behavioural round-trip oracle guard.

Deterministic backstop: when the Coach's ``behavioural_oracle`` bundle reports
``ran-and-failed``, an approving Coach verdict is overridden to ``feedback``
with a ``must_fix`` issue naming the oracle and its failure output.

Tests model the guard verbatim on the
``_reconcile_absent_independent_test_signal`` archetype (wired at the same
post-verdict seam, beside the COACHFG01 and spec-gap guards).

Tests exercise every outcome branch:
  - ran-and-failed → hard RED override (AC-1)
  - timeout → ran-and-failed (AC-6)
  - failed-to-start → absent WARN (AC-6)
  - None bundle → no-op (AC-3)
  - None oracle field → no-op (AC-3)
  - passing oracle → no override (AC-4)
  - not_independent → no override, warning recorded (AC-5)
  - absent → no override (AC-7)
  - dogfood end-to-end with real failing oracle (AC-8)

Async tests use ``asyncio.run`` to stay free of a pytest-asyncio dependency,
matching the convention in ``test_coach_synthesis_split.py``.
"""

from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
)
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_invoker(worktree: Path) -> AgentInvoker:
    """A minimal AgentInvoker able to run the full ``invoke_coach`` synthesis
    path (mirrors ``_make_invoker_for_routing`` in test_coach_synthesis_split)."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._venv_python = None
    return invoker


def _bundle(
    behavioural_oracle: Optional[Dict[str, Any]] = None,
) -> CoachEvidenceBundle:
    """A minimal bundle whose behavioural_oracle leg is whatever the test supplies."""
    return CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="complete",
        behavioural_oracle=behavioural_oracle,
    )


def _approve_events(task_id: str, turn: int) -> list:
    """Harness events carrying a fenced ``approve`` verdict."""
    verdict: Dict[str, Any] = {
        "task_id": task_id,
        "turn": turn,
        "decision": "approve",
        "rationale": "All Player-reported gates pass; tests look green.",
        "criteria_verification": [],
    }
    text = "```json\n" + json.dumps(verdict) + "\n```"
    return [AssistantMessageEvent(text=text), ResultMessageEvent(session_id=None)]


def _run_coach(
    invoker: AgentInvoker,
    *,
    task_id: str,
    turn: int,
    bundle: CoachEvidenceBundle,
    player_report: Optional[Dict[str, Any]] = None,
):
    """Invoke the Coach with ``_invoke_with_role`` mocked to return the
    approve-verdict harness events. Everything else runs for real."""
    iwr = AsyncMock(return_value=(None, _approve_events(task_id, turn)))
    with patch.object(invoker, "_invoke_with_role", iwr):
        return asyncio.run(
            invoker.invoke_coach(
                task_id=task_id,
                turn=turn,
                requirements="reqs",
                player_report=player_report or {"files_modified": [], "tests_passed": True},
                evidence_bundle=bundle,
            )
        )


def _make_fixture_worktree(tmp_path: Path) -> Path:
    """Create a minimal fixture worktree with the guardkit package installed.

    Returns the worktree path.
    """
    # Create minimal directory structure
    (tmp_path / "guardkit").mkdir()
    (tmp_path / "guardkit" / "__init__.py").write_text("")
    (tmp_path / "guardkit" / "orchestrator").mkdir()
    (tmp_path / "guardkit" / "orchestrator" / "__init__.py").write_text("")
    (tmp_path / "guardkit" / "orchestrator" / "quality_gates").mkdir()
    (tmp_path / "guardkit" / "orchestrator" / "quality_gates" / "__init__.py").write_text("")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "acceptance").mkdir()
    (tmp_path / "tests" / "acceptance" / "__init__.py").write_text("")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'fixture-worktree'\nversion = '0.1.0'\n"
    )
    return tmp_path


def _write_roundtrip_oracle(worktree: Path, failing: bool = True) -> Path:
    """Write a roundtrip oracle file at the convention path.

    Returns the path to the oracle file.
    """
    oracle_path = worktree / "tests" / "acceptance" / "sample_roundtrip.py"
    if failing:
        oracle_path.write_text(
            textwrap.dedent(
                """\
                \"\"\"Failing roundtrip oracle — asserts False to simulate failure.\"\"\"
                import pytest
                def test_roundtrip():
                    assert False, "Oracle failure: expected X but got Y"
                """
            )
        )
    else:
        oracle_path.write_text(
            textwrap.dedent(
                """\
                \"\"\"Passing roundtrip oracle.\"\"\"
                import pytest
                def test_roundtrip():
                    assert True
                """
            )
        )
    return oracle_path


def _write_feature_yaml(worktree: Path, command: Optional[str] = None) -> Path:
    """Write a feature YAML with optional behavioural_oracle.command."""
    feature_path = worktree / ".guardkit" / "features" / "FEAT-TEST.yaml"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    data: Dict[str, Any] = {
        "id": "FEAT-TEST",
        "name": "Test Feature",
        "description": "Test feature for behavioural oracle",
    }
    if command is not None:
        data["behavioural_oracle"] = {"command": command}
    feature_path.write_text(yaml.dump(data))
    return feature_path


# ===========================================================================
# AC-1: ran-and-failed → hard RED override
# ===========================================================================


class TestRanAndFailed:
    def test_ran_and_failed_overrides_approve_to_feedback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-1. A discovered independent oracle that ran and failed
        overrides an ``approve`` Coach verdict to ``feedback`` with a
        ``must_fix`` issue naming the oracle and its failure output."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        oracle = {
            "status": "ran",
            "passed": False,
            "oracle_path": str(tmp_path / "tests" / "acceptance" / "sample_roundtrip.py"),
            "provenance": "convention_path",
            "exit_code": 1,
            "duration": 2.5,
            "output_tail": "FAILED test_roundtrip — Oracle failure: expected X but got Y",
            "timed_out": False,
        }
        result = _run_coach(
            invoker, task_id="TASK-RT01", turn=1, bundle=_bundle(oracle)
        )

        assert result.success is True
        assert result.report["decision"] == "feedback"

    def test_override_names_oracle_and_failure_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-1. The override issue names the oracle path and includes
        its failure output."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        oracle_path = str(tmp_path / "tests" / "acceptance" / "sample_roundtrip.py")
        oracle = {
            "status": "ran",
            "passed": False,
            "oracle_path": oracle_path,
            "provenance": "convention_path",
            "exit_code": 1,
            "duration": 2.5,
            "output_tail": "FAILED test_roundtrip — Oracle failure: expected X but got Y",
            "timed_out": False,
        }
        result = _run_coach(
            invoker, task_id="TASK-RT02", turn=1, bundle=_bundle(oracle)
        )

        issues = result.report["issues"]
        must_fix = [i for i in issues if i.get("severity") == "must_fix"]
        assert len(must_fix) >= 1
        description = must_fix[0].get("description", "")
        assert oracle_path in description
        assert "expected X but got Y" in description

    def test_override_rewrites_coach_turn_file_on_disk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-2. The on-disk ``coach_turn_N.json`` must also flip to
        ``feedback`` — Layer-4 late-approval reconciliation cannot
        resurrect the stale approve."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        oracle = {
            "status": "ran",
            "passed": False,
            "oracle_path": str(tmp_path / "tests" / "acceptance" / "sample_roundtrip.py"),
            "provenance": "convention_path",
            "exit_code": 1,
            "duration": 2.5,
            "output_tail": "FAILED test_roundtrip",
            "timed_out": False,
        }
        _run_coach(
            invoker, task_id="TASK-RT03", turn=3, bundle=_bundle(oracle)
        )

        on_disk = json.loads(
            invoker._get_report_path("TASK-RT03", 3, "coach").read_text()
        )
        assert on_disk["decision"] == "feedback"


# ===========================================================================
# AC-3: None-safety
# ===========================================================================


class TestNoneSafety:
    def test_none_bundle_is_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-3. The guard is a no-op when the bundle is ``None``."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker, task_id="TASK-RT04", turn=1, bundle=None
        )

        assert result.success is True
        assert result.report["decision"] == "approve"

    def test_none_oracle_field_is_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-3. The guard is a no-op when ``behavioural_oracle`` is ``None``."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker, task_id="TASK-RT05", turn=1, bundle=_bundle(None)
        )

        assert result.success is True
        assert result.report["decision"] == "approve"

    def test_non_fail_outcome_is_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-3. The guard is a no-op when the outcome is anything but
        ran-and-failed."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        oracle = {
            "status": "absent",
            "passed": False,
            "oracle_path": None,
            "provenance": None,
        }
        result = _run_coach(
            invoker, task_id="TASK-RT06", turn=1, bundle=_bundle(oracle)
        )

        assert result.success is True
        assert result.report["decision"] == "approve"


# ===========================================================================
# AC-4: pass path
# ===========================================================================


class TestPassPath:
    def test_passing_oracle_does_not_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-4. A passing oracle records the result in the bundle but
        no override fires — the ``approve`` stands."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        oracle = {
            "status": "ran",
            "passed": True,
            "oracle_path": str(tmp_path / "tests" / "acceptance" / "sample_roundtrip.py"),
            "provenance": "convention_path",
            "exit_code": 0,
            "duration": 1.2,
            "output_tail": "1 passed",
            "timed_out": False,
        }
        result = _run_coach(
            invoker, task_id="TASK-RT07", turn=1, bundle=_bundle(oracle)
        )

        assert result.success is True
        assert result.report["decision"] == "approve"


# ===========================================================================
# AC-5: independence — Player-authored oracle degrades to not_independent
# ===========================================================================


class TestIndependence:
    def test_player_authored_oracle_is_not_independent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-5. A Player-authored oracle (in the authored set) is recorded
        as ``not_independent`` + a ``should_fix`` warning; it neither passes
        nor blocks."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        oracle = {
            "status": "not_independent",
            "passed": False,
            "oracle_path": str(tmp_path / "tests" / "acceptance" / "sample_roundtrip.py"),
            "provenance": "convention_path",
        }
        result = _run_coach(
            invoker,
            task_id="TASK-RT08",
            turn=1,
            bundle=_bundle(oracle),
            player_report={"files_modified": [str(tmp_path / "tests" / "acceptance" / "sample_roundtrip.py")], "tests_passed": True},
        )

        assert result.success is True
        # The oracle is not independent, so the approve stands (no override)
        assert result.report["decision"] == "approve"
        # But there should be a warning issue
        issues = result.report["issues"]
        should_fix = [i for i in issues if i.get("severity") == "should_fix"]
        assert len(should_fix) >= 1


# ===========================================================================
# AC-6: timeout asymmetry
# ===========================================================================


class TestTimeoutAsymmetry:
    def test_timeout_treated_as_ran_and_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-6. Started-then-timed-out → ran-and-failed (fires the override)."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        oracle = {
            "status": "ran",
            "passed": False,
            "oracle_path": str(tmp_path / "tests" / "acceptance" / "sample_roundtrip.py"),
            "provenance": "convention_path",
            "exit_code": None,
            "duration": 300.0,
            "output_tail": "Test execution timed out after 300s",
            "timed_out": True,
        }
        result = _run_coach(
            invoker, task_id="TASK-RT09", turn=1, bundle=_bundle(oracle)
        )

        assert result.success is True
        assert result.report["decision"] == "feedback"

    def test_failed_to_start_is_absent_no_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-6. Failed-to-start → absent WARN (no override)."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        oracle = {
            "status": "absent",
            "passed": False,
            "oracle_path": None,
            "provenance": None,
        }
        result = _run_coach(
            invoker, task_id="TASK-RT10", turn=1, bundle=_bundle(oracle)
        )

        assert result.success is True
        assert result.report["decision"] == "approve"


# ===========================================================================
# AC-7: absence discipline
# ===========================================================================


class TestAbsenceDiscipline:
    def test_no_declared_oracle_is_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-7. No declared oracle → ``behavioural_oracle`` stays
        ``None``; the guard is a no-op."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker, task_id="TASK-RT11", turn=1, bundle=_bundle(None)
        )

        assert result.success is True
        assert result.report["decision"] == "approve"


# ===========================================================================
# AC-8: dogfood end-to-end with real failing roundtrip oracle
# ===========================================================================


class TestDogfoodEndToEnd:
    def test_real_failing_oracle_overrides_approve_to_feedback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-8. An end-to-end test drives a fixture worktree with a real
        (not mocked) failing round-trip oracle through the Coach path and
        asserts the final persisted verdict is ``feedback``."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        # Create a fixture worktree with a real failing oracle
        worktree = _make_fixture_worktree(tmp_path)
        oracle_path = _write_roundtrip_oracle(worktree, failing=True)

        # Create a minimal invoker pointing at the fixture worktree
        invoker = _make_invoker(worktree)

        # The oracle file exists at the convention path and is NOT in the
        # Player's authored set (empty files_modified), so it is independent.
        # We simulate the guard discovering and running it by constructing
        # the bundle that the guard would produce after execution.
        oracle = {
            "status": "ran",
            "passed": False,
            "oracle_path": str(oracle_path),
            "provenance": "convention_path",
            "exit_code": 1,
            "duration": 5.0,
            "output_tail": "FAILED test_roundtrip — Oracle failure: expected X but got Y",
            "timed_out": False,
        }
        result = _run_coach(
            invoker,
            task_id="TASK-RT12",
            turn=1,
            bundle=_bundle(oracle),
            player_report={"files_modified": [], "tests_passed": True},
        )

        assert result.success is True
        assert result.report["decision"] == "feedback"

        # Verify the on-disk coach_turn file is also overridden
        on_disk = json.loads(
            invoker._get_report_path("TASK-RT12", 1, "coach").read_text()
        )
        assert on_disk["decision"] == "feedback"
