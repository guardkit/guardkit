"""The review's look-up pass runs on every review (the build reviewer design
of 29 October 2026; it was the opt-in "B-full gather", TASK-ARCH-COACHBFULL).

Covers the GuardKit-orchestrator side:

* every review runs the read-only look-up pass first, asking only for
  ``["Read", "Search", "Grep", "Glob"]`` (no shell), then the toolless verdict
  call, which carries its findings;
* a failed or empty look-up pass leaves the verdict call to run without it;
* a CancelledError in the look-up pass propagates; the pass has its slice of
  the review's time and the verdict call keeps the full time;
* acceptance criteria reach the verdict prompt;
* the look-up pass carries the per-tool-result cut and no step ceiling (its
  bound is guardkitfactory's shared tool limit, which ends with an answer);
* the findings text in the verdict prompt is capped with a visible marker.

Async tests use ``asyncio.run`` to stay free of a pytest-asyncio dependency.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_invoker(worktree: Path) -> AgentInvoker:
    """Minimal AgentInvoker for routing tests (mirrors
    test_coach_synthesis_split.py::_make_invoker_for_routing)."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    return invoker


def _make_bundle():
    """Minimal complete CoachEvidenceBundle so invoke_coach takes the synthesis
    path."""
    from guardkit.orchestrator.quality_gates.coach_evidence import (
        CoachEvidenceBundle,
    )

    return CoachEvidenceBundle(gathering_status="complete")


def _verdict_events(task_id: str, turn: int = 1, decision: str = "approve"):
    """A harness event stream carrying a schema-valid fenced JSON verdict."""
    verdict = (
        "Reasoning prose here.\n\n"
        "```json\n"
        f'{{"task_id": "{task_id}", "turn": {turn}, '
        f'"decision": "{decision}", "rationale": "deterministic test verdict"}}\n'
        "```"
    )
    return (None, [
        AssistantMessageEvent(text=verdict),
        ResultMessageEvent(session_id=None),
    ])


def _findings_events(text: str):
    return (None, [
        AssistantMessageEvent(text=text),
        ResultMessageEvent(session_id=None),
    ])


# ---------------------------------------------------------------------------
# The look-up prompt (build_review.build_lookup_prompt)
# ---------------------------------------------------------------------------


class TestLookupPrompt:
    def test_lookup_prompt_asks_the_five_questions_not_for_a_verdict(
        self, tmp_path: Path
    ) -> None:
        from guardkit.orchestrator.build_review import ReviewChange

        prompt = _make_invoker(tmp_path)._build_coach_gather_prompt(
            task_id="TASK-GA-001",
            turn=1,
            requirements="do the thing",
            player_report={"files_modified": ["src/foo.py"], "concerns": ["slow"]},
            evidence_bundle=_make_bundle(),
            acceptance_criteria=[
                {"id": "AC-001", "text": "feature works"},
                {"id": "AC-002", "text": "edge case handled"},
            ],
            change=ReviewChange("diff --git a/src/foo.py b/src/foo.py\n", None, "a" * 40),
        )
        for pattern in ("NOT_IMPLEMENTED", "NOT_TESTED", "CALLERS_NOT_UPDATED",
                        "STUB", "OUTSIDE_TASK", "CRITERION_CONFLICT"):
            assert pattern in prompt
        assert "AC-001" in prompt and "AC-002" in prompt
        assert "Do not write a JSON verdict" in prompt
        assert "<evidence_bundle>" in prompt
        assert "diff --git a/src/foo.py" in prompt
        assert '"concerns"' in prompt
        # No shell, and the not-findings list.
        assert "There is no shell" in prompt
        assert "not independently verified" in prompt
        for tool in ("code_search", "code_outline", "code_pattern", "code_references"):
            assert tool in prompt
        # The old investigation framing is gone.
        assert "INVESTIGATION" not in prompt
        assert "Bash" not in prompt


# ---------------------------------------------------------------------------
# invoke_coach: the look-up pass, then the verdict
# ---------------------------------------------------------------------------


class TestInvokeCoachGatherRouting:
    def test_every_review_runs_the_read_only_lookup_then_the_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no setting at all: the first call is the read-only look-up
        pass (Read/Search/Grep/Glob, no shell), the second the toolless
        verdict call, which carries the look-up findings."""
        invoker = _make_invoker(tmp_path)

        calls: list[dict] = []

        async def _iwr(**kwargs):
            calls.append(kwargs)
            if not kwargs.get("synthesis"):
                # The look-up pass: findings text.
                return _findings_events(
                    "STUB src/foo.py:10: the behaviour returns a fixed answer"
                )
            return _verdict_events("TASK-ON-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        result = asyncio.run(
            invoker.invoke_coach(
                task_id="TASK-ON-001",
                turn=1,
                requirements="reqs",
                player_report={"files_modified": ["src/foo.py"]},
                evidence_bundle=_make_bundle(),
            )
        )

        assert result.success is True
        assert len(calls) == 2

        gather, synth = calls[0], calls[1]
        # The look-up pass: read-only tools.
        assert gather["synthesis"] is False
        assert gather["allowed_tools"] == ["Read", "Search", "Grep", "Glob"]
        assert gather["agent_type"] == "coach"
        assert "The five questions" in gather["prompt"]
        # The verdict — toolless grammar call, now carrying the findings.
        assert synth["synthesis"] is True
        assert synth["allowed_tools"] == []
        assert "## Look-up findings" in synth["prompt"]
        assert "STUB src/foo.py:10" in synth["prompt"]

    def test_lookup_failure_leaves_the_verdict_to_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A look-up pass exception (e.g. tool-parse 500): the verdict call
        still runs, a valid verdict emerges, the turn is NOT failed, and the
        verdict prompt says the look-up pass gave no findings."""
        invoker = _make_invoker(tmp_path)

        calls: list[dict] = []

        async def _iwr(**kwargs):
            calls.append(kwargs)
            if not kwargs.get("synthesis"):
                raise RuntimeError("HTTP 500 Failed to parse input")  # run-18 class
            return _verdict_events("TASK-DEG-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        result = asyncio.run(
            invoker.invoke_coach(
                task_id="TASK-DEG-001",
                turn=1,
                requirements="reqs",
                player_report={"files_modified": []},
                evidence_bundle=_make_bundle(),
            )
        )

        assert result.success is True  # turn not failed
        assert result.report["decision"] == "approve"
        assert len(calls) == 2  # gather (raised, caught) + synthesis
        assert calls[1]["synthesis"] is True
        assert "The look-up pass gave no findings" in calls[1]["prompt"]

    def test_empty_lookup_answer_is_no_findings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty look-up answer (whitespace only) is said as no findings:
        absent evidence is not dressed up as a positive signal."""
        invoker = _make_invoker(tmp_path)

        calls: list[dict] = []

        async def _iwr(**kwargs):
            calls.append(kwargs)
            if not kwargs.get("synthesis"):
                return _findings_events("   \n  \t ")  # whitespace-only
            return _verdict_events("TASK-EMPTY-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        result = asyncio.run(
            invoker.invoke_coach(
                task_id="TASK-EMPTY-001",
                turn=1,
                requirements="reqs",
                player_report={"files_modified": []},
                evidence_bundle=_make_bundle(),
            )
        )

        assert result.success is True
        assert len(calls) == 2
        assert "The look-up pass gave no findings" in calls[1]["prompt"]

    def test_cancellation_during_lookup_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A genuine CancelledError in the look-up pass is NOT swallowed (it
        is BaseException, not Exception): it propagates and the verdict call
        is never made."""
        invoker = _make_invoker(tmp_path)

        calls: list[dict] = []

        async def _iwr(**kwargs):
            calls.append(kwargs)
            if not kwargs.get("synthesis"):
                raise asyncio.CancelledError()
            return _verdict_events("TASK-CANC-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(
                invoker.invoke_coach(
                    task_id="TASK-CANC-001",
                    turn=1,
                    requirements="reqs",
                    player_report={"files_modified": []},
                    evidence_bundle=_make_bundle(),
                )
            )

        assert len(calls) == 1  # only the gather; synthesis never reached
        assert calls[0]["synthesis"] is False

    def test_lookup_time_is_a_slice_and_the_verdict_keeps_full(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The look-up pass runs under a bounded slice (40% of the effective
        time, floored at 60s); the verdict keeps the full effective time.
        effective=600 ⇒ look-up sees 240, verdict sees 600."""
        invoker = _make_invoker(tmp_path)  # _calculate_sdk_timeout → 600

        seen: list[tuple[bool, int]] = []

        async def _iwr(**kwargs):
            seen.append((bool(kwargs.get("synthesis")), invoker.sdk_timeout_seconds))
            if not kwargs.get("synthesis"):
                return _findings_events("NO FINDINGS")
            return _verdict_events("TASK-BUD-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        asyncio.run(
            invoker.invoke_coach(
                task_id="TASK-BUD-001",
                turn=1,
                requirements="reqs",
                player_report={"files_modified": []},
                evidence_bundle=_make_bundle(),
            )
        )

        assert seen == [(False, 240), (True, 600)]
        # Timeout restored after the turn.
        assert invoker.sdk_timeout_seconds == 600


# ---------------------------------------------------------------------------
# Acceptance-criteria threading into the synthesis prompt (AC-4)
# ---------------------------------------------------------------------------


class TestCriteriaThreading:
    def test_synthesis_prompt_carries_per_ac_checklist_and_example(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-4 root-cause fix: when acceptance_criteria are threaded, the
        synthesis prompt gains the 'verify EACH criterion' section AND the
        criteria_verification example — the absence of which produced run-19's
        empty criteria_verification arrays.

        Pinned to the ``coachsplit`` contract, because
        ``criteria_verification`` is a key of the LEGACY Decision Format. The
        v4 contract (TASK-CMIR-002) deliberately emits only ``verdict`` +
        ``findings`` and names no other key, and guardkit's own
        ``.guardkit/config.yaml`` has selected v4 since the 2026-07-26 flip
        (754ce150) — so unpinned, this test asserted the legacy example
        against a v4 prompt and failed on the repo's configuration rather
        than on any regression. The per-criterion SECTION itself
        ("Acceptance Criteria to Verify" + each AC id) is threaded under both
        contracts; only the JSON-key example is coachsplit-specific.
        """
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "coachsplit")
        prompt = _make_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-AC4-001",
            turn=1,
            requirements="do the thing",
            player_report={"files_modified": []},
            acceptance_criteria=[
                {"id": "AC-001", "text": "feature works"},
                {"id": "AC-002", "text": "edge case handled"},
            ],
            evidence_bundle=_make_bundle(),
        )
        assert "Acceptance Criteria to Verify" in prompt
        assert "AC-001" in prompt and "AC-002" in prompt
        assert "criteria_verification" in prompt
        assert '"criterion_id"' in prompt

    def test_no_criteria_section_when_acs_absent(self, tmp_path: Path) -> None:
        """Omitting acceptance_criteria gives no per-criterion section."""
        prompt = _make_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-AC4-002",
            turn=1,
            requirements="do the thing",
            player_report={"files_modified": []},
            evidence_bundle=_make_bundle(),
        )
        assert "Acceptance Criteria to Verify" not in prompt


# ---------------------------------------------------------------------------
# The look-up pass's bounds: the tool-result cut, and no step ceiling (its
# bound is the shared tool limit, which ends with an answer); the verdict
# call carries neither.
# ---------------------------------------------------------------------------


class TestLookupBoundPlumbing:
    def test_lookup_call_carries_the_cut_and_no_step_ceiling(
        self, tmp_path: Path
    ) -> None:
        from guardkit.orchestrator.agent_invoker import (
            _COACH_GATHER_MAX_TOOL_RESULT_CHARS,
        )

        invoker = _make_invoker(tmp_path)

        calls: list[dict] = []

        async def _iwr(**kwargs):
            calls.append(kwargs)
            if not kwargs.get("synthesis"):
                return _findings_events("NO FINDINGS")
            return _verdict_events("TASK-BND-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        asyncio.run(
            invoker.invoke_coach(
                task_id="TASK-BND-001",
                turn=1,
                requirements="reqs",
                player_report={"files_modified": ["src/foo.py"]},
                evidence_bundle=_make_bundle(),
            )
        )

        assert len(calls) == 2
        lookup, verdict = calls[0], calls[1]
        assert lookup.get("recursion_limit") is None
        assert lookup["max_tool_result_chars"] == _COACH_GATHER_MAX_TOOL_RESULT_CHARS == 12000
        assert verdict.get("recursion_limit") is None
        assert verdict.get("max_tool_result_chars") is None


class TestGatherFindingsTruncation:
    """The look-up findings in the verdict prompt are capped, with a visible
    marker."""

    def test_under_limit_passthrough(self) -> None:
        small = "STUB src/a.py:1: x\nNOT_TESTED src/b.py:2: y"
        assert AgentInvoker._truncate_gather_findings(small) == small

    def test_over_limit_is_capped_and_marked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            AgentInvoker, "_COACH_GATHER_FINDINGS_LIMIT_CHARS", 100
        )
        big = "F" * 5000
        out = AgentInvoker._truncate_gather_findings(big)
        assert len(out) < len(big)
        assert out.startswith("F" * 100)
        # The marker is load-bearing: the cut is never silent.
        assert "look-up findings cut here" in out

    def test_truncation_applied_in_synthesis_prompt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            AgentInvoker, "_COACH_GATHER_FINDINGS_LIMIT_CHARS", 200
        )
        prompt = _make_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-TRC-001",
            turn=1,
            requirements="reqs",
            player_report={"files_modified": []},
            evidence_bundle=_make_bundle(),
            gather_findings="G" * 8000,
        )
        # The findings section is present but bounded + marked.
        assert "## Look-up findings" in prompt
        assert "look-up findings cut here" in prompt
        # The full 8000-char blob must NOT appear verbatim.
        assert "G" * 8000 not in prompt
