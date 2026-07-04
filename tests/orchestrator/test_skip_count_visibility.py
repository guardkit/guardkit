"""TASK-AB-SKIPVIS01 — thread ``tests_skipped`` through the independent-test
oracle as ADVISORY evidence.

From the 2026-07-03 FEAT-ABL-001 retro (R1): a worktree venv missing an
optional extra silently turns N tests into skips, and nothing surfaced
"N tests skipped" to the Coach or the operator — the precondition a Player
exploited by defeating a ``skipif(find_spec(...))`` guard with a sys.modules
stub. These tests pin the visibility fix:

* Parsing — the skip count is captured tri-state (``None`` = unparseable /
  unknown, never 0-coerced; ``0`` = summary parsed cleanly with no skip
  token; ``N`` = N skipped) at every pytest-summary parse site.
* Serialization — ``tests_skipped`` survives ``to_dict()`` (including
  ``None``) and round-trips (the ABFIX-010 lesson: a field omitted from
  serialization makes the downstream surface dead).
* Advisory surface — the Coach-facing evidence render carries an advisory
  line when the count is positive, and omits it for 0 / ``None``.
* No-verdict-change — an ``approve`` outcome is IDENTICAL with
  ``tests_skipped`` 0 vs 50: no gate or verdict branch reads the count
  (``.claude/rules/absence-of-failure-is-not-success.md`` — a skip is an
  ABSENT verdict, never blocking, never a pass-precondition).

The invoke_coach harness pattern mirrors
``tests/orchestrator/test_coach_independent_test_absent_guard.py`` (mocked
harness emits the verdict; parser/loader/validator/guards run for real).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    TaskWorkStreamParser,
)
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
)
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidationResult,
    IndependentTestResult,
    _parse_tests_skipped,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _independent(
    tests_skipped: Optional[int],
    *,
    tests_passed: bool = True,
    signal_absent: bool = False,
) -> IndependentTestResult:
    return IndependentTestResult(
        tests_passed=tests_passed,
        test_command="pytest -q",
        test_output_summary="10 passed",
        duration_seconds=1.0,
        raw_output="===== 10 passed in 0.5s =====",
        signal_absent=signal_absent,
        tests_skipped=tests_skipped,
    )


def _bundle(independent: Optional[IndependentTestResult]) -> CoachEvidenceBundle:
    return CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="complete",
        independent_tests=independent,
    )


# ---------------------------------------------------------------------------
# Parsing — coach_validator._parse_tests_skipped (tri-state)
# ---------------------------------------------------------------------------


class TestParseTestsSkipped:
    @pytest.mark.parametrize(
        "output,expected",
        [
            # skip token present
            ("===== 5 passed, 2 skipped in 1.2s =====", 2),
            # all-skipped run (the FEAT-ABL-001 R1 shape: pytest exits 0)
            ("===== 4 skipped in 0.5s =====", 4),
            # summary parsed cleanly, no skip token => positively zero
            ("3 passed in 0.1s", 0),
            ("===== 1 failed, 2 passed in 0.3s =====", 0),
            # unparseable => None (unknown, never 0-coerced)
            ("", None),
            (None, None),
            ("no recognisable summary here", None),
            ("ImportError while loading conftest", None),
            # reprinted summary — max per class
            ("1 skipped\n===== 5 passed, 2 skipped in 1.2s =====", 2),
        ],
    )
    def test_tri_state(self, output: Optional[str], expected: Optional[int]) -> None:
        assert _parse_tests_skipped(output) == expected


# ---------------------------------------------------------------------------
# Parsing — TaskWorkStreamParser consumes the already-captured skip group
# ---------------------------------------------------------------------------


class TestStreamParserSkipCapture:
    def test_skip_count_captured(self) -> None:
        parser = TaskWorkStreamParser()
        parser.parse_message("===== 5 passed, 2 skipped in 1.2s =====")
        result = parser.to_result()
        # tests_run semantics untouched: passed count excludes skips.
        assert result["tests_passed"] == 5
        assert result["tests_skipped"] == 2

    def test_failing_run_ordering_captures_skip_count(self) -> None:
        """pytest orders failed BEFORE passed on every failing run, which
        the positional skipped group of PYTEST_SUMMARY_PATTERN never matches
        (it only fires in passed-then-failed adjacency). The independent
        token search must still capture the real skip count — the pre-fix
        parser coerced it to a false 'positively zero' here."""
        parser = TaskWorkStreamParser()
        parser.parse_message("===== 2 failed, 3 passed, 1 skipped in 0.5s =====")
        result = parser.to_result()
        assert result["tests_failed"] == 2
        assert result["tests_skipped"] == 1

    def test_failing_run_without_skip_token_is_zero(self) -> None:
        """A failed+passed summary with no skip token is positively zero."""
        parser = TaskWorkStreamParser()
        parser.parse_message("===== 1 failed, 2 passed in 0.3s =====")
        result = parser.to_result()
        assert result["tests_failed"] == 1
        assert result["tests_skipped"] == 0

    def test_clean_summary_without_skip_token_is_zero(self) -> None:
        parser = TaskWorkStreamParser()
        parser.parse_message("===== 5 passed in 1.2s =====")
        assert parser.to_result()["tests_skipped"] == 0

    def test_no_parseable_summary_stays_unknown(self) -> None:
        parser = TaskWorkStreamParser()
        parser.parse_message("Phase 3: Implementation underway")
        # None => omitted (mirrors tests_passed/tests_failed absence handling).
        assert "tests_skipped" not in parser.to_result()

    def test_reset_clears_skip_count(self) -> None:
        parser = TaskWorkStreamParser()
        parser.parse_message("===== 5 passed, 2 skipped in 1.2s =====")
        parser.reset()
        assert "tests_skipped" not in parser.to_result()


# ---------------------------------------------------------------------------
# Serialization — to_dict carries tests_skipped (including None); round-trip
# ---------------------------------------------------------------------------


class TestSerialization:
    def _validation_result(
        self, tests_skipped: Optional[int]
    ) -> CoachValidationResult:
        return CoachValidationResult(
            task_id="TASK-AB-SKIPVIS01",
            turn=1,
            decision="approve",
            independent_tests=_independent(tests_skipped),
        )

    def test_coach_validation_result_to_dict_carries_count(self) -> None:
        d = self._validation_result(2).to_dict()
        assert d["validation_results"]["independent_tests"]["tests_skipped"] == 2

    def test_coach_validation_result_to_dict_preserves_none(self) -> None:
        ind = self._validation_result(None).to_dict()["validation_results"][
            "independent_tests"
        ]
        # The key must be PRESENT and None — an absent skip count stays
        # unknown through serialization, never dropped or 0-coerced.
        assert "tests_skipped" in ind
        assert ind["tests_skipped"] is None

    def test_evidence_bundle_to_dict_carries_count(self) -> None:
        d = _bundle(_independent(3)).to_dict()
        assert d["independent_tests"]["tests_skipped"] == 3
        # JSON round-trip (the shape written to coach_turn_N.json).
        assert json.loads(json.dumps(d))["independent_tests"]["tests_skipped"] == 3

    def test_evidence_bundle_to_dict_preserves_none(self) -> None:
        d = _bundle(_independent(None)).to_dict()
        assert "tests_skipped" in d["independent_tests"]
        assert d["independent_tests"]["tests_skipped"] is None
        assert (
            json.loads(json.dumps(d))["independent_tests"]["tests_skipped"] is None
        )

    @pytest.mark.parametrize("tests_skipped", [None, 0, 7])
    def test_independent_test_result_round_trip(
        self, tests_skipped: Optional[int]
    ) -> None:
        original = _independent(tests_skipped)
        reconstructed = IndependentTestResult(
            **_bundle(original).to_dict()["independent_tests"]
        )
        assert reconstructed == original


# ---------------------------------------------------------------------------
# Advisory surface — Coach-facing evidence render
# ---------------------------------------------------------------------------


class TestAdvisorySurface:
    def _render(self, tests_skipped: Optional[int]) -> str:
        invoker = AgentInvoker.__new__(AgentInvoker)
        return AgentInvoker._render_evidence_bundle_section(
            invoker, _bundle(_independent(tests_skipped))
        )

    def test_positive_count_renders_advisory_line(self) -> None:
        section = self._render(3)
        assert "ADVISORY: tests_skipped: 3" in section
        assert "ABSENT verdicts, not passes" in section
        assert "missing optional extras" in section
        # Advisory means advisory — the line itself must say so.
        assert "never reject the turn on this count alone" in section

    def test_zero_count_omits_advisory_line(self) -> None:
        section = self._render(0)
        assert "ADVISORY: tests_skipped" not in section
        # The count is still visible in the bundle JSON itself.
        assert '"tests_skipped": 0' in section

    def test_none_count_omits_advisory_line(self) -> None:
        section = self._render(None)
        assert "ADVISORY: tests_skipped" not in section
        assert '"tests_skipped": null' in section


# ---------------------------------------------------------------------------
# No-verdict-change — no gate reads tests_skipped
# ---------------------------------------------------------------------------


def _make_invoker(worktree: Path) -> AgentInvoker:
    """Minimal AgentInvoker able to run the full ``invoke_coach`` synthesis
    path (mirrors test_coach_independent_test_absent_guard.py)."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._venv_python = None
    return invoker


def _approve_events(task_id: str, turn: int) -> list:
    verdict = {
        "task_id": task_id,
        "turn": turn,
        "decision": "approve",
        "rationale": "All gates pass; independent tests green.",
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
):
    iwr = AsyncMock(return_value=(None, _approve_events(task_id, turn)))
    with patch.object(invoker, "_invoke_with_role", iwr):
        return asyncio.run(
            invoker.invoke_coach(
                task_id=task_id,
                turn=turn,
                requirements="reqs",
                player_report={"files_modified": [], "tests_passed": True},
                evidence_bundle=bundle,
            )
        )


class TestNoVerdictChange:
    def test_approve_identical_with_0_and_50_skips(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A green run with 50 skips must approve exactly like a green run
        with 0 skips — the skip count is advisory and no deterministic guard
        (signal-absent, null-evidence, runtime-parity, code-failure) may key
        on it. A regression here means someone made the count turn-rejecting."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        results = {}
        for label, skipped in (("zero", 0), ("many", 50)):
            invoker = _make_invoker(tmp_path)
            results[label] = _run_coach(
                invoker,
                task_id=f"TASK-SKIPVIS-{label.upper()}",
                turn=1,
                bundle=_bundle(_independent(skipped)),
            )

        assert results["zero"].report["decision"] == "approve"
        assert results["many"].report["decision"] == "approve"
        assert (
            results["zero"].report["decision"]
            == results["many"].report["decision"]
        )
        # No new issue category may be introduced by the skip count.
        assert not any(
            "skip" in (issue.get("category") or "").lower()
            for issue in results["many"].report.get("issues", [])
        )
