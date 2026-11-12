"""An unreadable verdict is asked for once more, and if it is still unreadable
the look-up pass's findings go to the merge card (TypeScript C, 3 November
2026: the verdict call spent its whole output allowance thinking, wrote
nothing, and the look-up pass's findings were dropped with it).

Async tests use ``asyncio.run`` to stay free of a pytest-asyncio dependency.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from guardkit.orchestrator import build_review
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.harness import AssistantMessageEvent, ResultMessageEvent

LOOKUP = (
    "1. STUB src/foo.py:10: the behaviour returns a fixed answer\n"
    "- NOT_TESTED tests/test_foo.py:4: no test reaches the error branch\n"
    "Some prose the model added between findings.\n"
)


@pytest.fixture(autouse=True)
def _per_task_reviewer_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests are about the per-task reviewer. Feature builds no longer run
    it by default (12 November 2026: one end review instead); the way-back
    setting brings it back, and that is the reviewer tested here."""
    monkeypatch.setenv("GUARDKIT_PER_TASK_REVIEW", "1")


def _make_invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    return invoker


def _bundle():
    from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle

    return CoachEvidenceBundle(gathering_status="complete")


def _events(text: str | None):
    if text is None:  # what the verdict call gave on TypeScript C: no text at all
        return (None, [ResultMessageEvent(session_id=None)])
    return (None, [AssistantMessageEvent(text=text), ResultMessageEvent(session_id=None)])


def _verdict(task_id: str) -> str:
    return (
        "```json\n"
        f'{{"task_id": "{task_id}", "turn": 1, "decision": "approve", '
        '"rationale": "second answer", "issues": []}\n'
        "```"
    )


def _review(tmp_path: Path, task_id: str, verdicts: list[str | None]):
    invoker = _make_invoker(tmp_path)
    calls: list[dict] = []

    async def _iwr(**kwargs):
        calls.append(kwargs)
        if not kwargs.get("synthesis"):
            return _events(LOOKUP)
        return _events(verdicts.pop(0))

    invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
    result = asyncio.run(
        invoker.invoke_coach(
            task_id=task_id,
            turn=1,
            requirements="reqs",
            player_report={"files_modified": ["src/foo.py"]},
            evidence_bundle=_bundle(),
        )
    )
    return result, [c for c in calls if c.get("synthesis")]


def test_an_unreadable_verdict_is_asked_for_once_more(tmp_path: Path) -> None:
    result, verdict_calls = _review(tmp_path, "TASK-EV-001", [None, _verdict("TASK-EV-001")])

    assert len(verdict_calls) == 2
    assert result.success is True
    assert result.report["rationale"] == "second answer"
    assert "lookup_findings" not in result.report


def test_still_unreadable_the_lookup_findings_go_to_the_merge_card(tmp_path: Path) -> None:
    result, verdict_calls = _review(tmp_path, "TASK-EV-002", [None, None])

    assert len(verdict_calls) == 2
    report = result.report
    # Never sent back on findings no verdict checked.
    assert report["decision"] == "approve"
    assert not report.get(build_review.REPAIR_KEY)
    assert report[build_review.LEFTOVERS_KEY] == [
        {"pattern": "STUB", "location": "src/foo.py:10",
         "description": "the behaviour returns a fixed answer"},
        {"pattern": "NOT_TESTED", "location": "tests/test_foo.py:4",
         "description": "no test reaches the error branch"},
    ]
    # The look-up pass's whole text is kept in the review's record.
    assert report["lookup_findings"].strip() == LOOKUP.strip()
    assert "no readable verdict" in report["rationale"]


def test_lookup_findings_reads_only_written_findings() -> None:
    found = build_review.lookup_findings(LOOKUP + "NO FINDINGS\nCRITERION_CONFLICT a.md:2: x\n")

    assert [(f["pattern"], f["location"]) for f in found] == [
        ("STUB", "src/foo.py:10"),
        ("NOT_TESTED", "tests/test_foo.py:4"),
        ("CRITERION_CONFLICT", "a.md:2"),
    ]
    assert build_review.lookup_findings(None) == []
    assert build_review.lookup_findings("NO FINDINGS") == []
