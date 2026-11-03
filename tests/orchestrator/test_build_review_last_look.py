"""One last look at the build reviewer's notes before the merge card (Rich,
3 November 2026, decision 5).

TypeScript C (FEAT-8AB6) did finished, correct work and was declined at merge
over four notes written before later tasks changed the code: one untrue, one
settled by a later task's full check, two minor. Now, when every task
completed and a note exists, the same look-up pass and verdict review the
feature's whole change once, given the notes to check again. A note reported
again stays on the card; the others are only counted. Any failure leaves the
notes file exactly as before.

Async calls use ``asyncio.run`` to stay free of a pytest-asyncio dependency.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from guardkit.orchestrator import build_review
from guardkit.orchestrator.agent_invoker import AgentInvoker, SDKTimeoutError
from guardkit.orchestrator.harness import AssistantMessageEvent, ResultMessageEvent
from guardkit.orchestrator.paths import TaskArtifactPaths

FEATURE = "FEAT-LL1"
NOTES = {
    "TASK-LL1-001": [
        {"pattern": "NOT_TESTED", "location": "src/a.ts:14",
         "description": "no test covers the empty list"},
        {"pattern": "STUB", "location": "src/b.ts:3",
         "description": "count() returns a fixed answer"},
    ],
    "TASK-LL1-002": [
        {"pattern": "OUTSIDE_TASK", "location": "scripts/check.sh:9",
         "description": "lint and typecheck never ran"},
    ],
}
TASKS = [*NOTES, "TASK-LL1-003"]


def _seed(root: Path, notes: Dict[str, List[Dict[str, str]]] = NOTES) -> None:
    for task_id, left in notes.items():
        folder = TaskArtifactPaths.task_private_dir(task_id, root)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "coach_turn_1.json").write_text(
            json.dumps({"decision": "approve", build_review.LEFTOVERS_KEY: left}),
            encoding="utf-8",
        )


def _events(text: Optional[str]):
    if text is None:
        return (None, [ResultMessageEvent(session_id=None)])
    return (None, [AssistantMessageEvent(text=text), ResultMessageEvent(session_id=None)])


def _verdict(issues: List[Dict[str, str]]) -> str:
    body = {"task_id": FEATURE, "turn": 1, "decision": "feedback", "issues": issues,
            "rationale": "checked again"}
    return f"```json\n{json.dumps(body)}\n```"


def _reviewer(root: Path, lookup: Any, verdicts: List[Any]):
    """A real AgentInvoker whose model calls are faked: ``lookup`` answers the
    look-up pass, ``verdicts`` the verdict calls in turn (an exception is
    raised)."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = root
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    calls: List[Dict[str, Any]] = []

    async def _iwr(**kwargs):
        calls.append(kwargs)
        answer = verdicts.pop(0) if kwargs.get("synthesis") else lookup
        if isinstance(answer, BaseException):
            raise answer
        return _events(answer)

    invoker._invoke_with_role = _iwr  # type: ignore[method-assign]

    def look(notes):
        return asyncio.run(
            invoker.invoke_last_look(feature_id=FEATURE, base=None, notes=notes)
        )

    return look, calls


def _today(root: Path) -> bytes:
    """What write_feature_notes wrote before the last look existed."""
    path = build_review.write_feature_notes(FEATURE, TASKS, root)
    return path.read_bytes()


@pytest.fixture(autouse=True)
def _default_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GUARDKIT_COACH_CONTRACT", raising=False)


def test_a_note_reported_again_stays_and_the_others_are_counted(tmp_path: Path) -> None:
    _seed(tmp_path)
    look, calls = _reviewer(
        tmp_path,
        "STUB src/b.ts:7: count() still returns a fixed answer\n",
        [_verdict([{"pattern": "STUB", "severity": "major", "location": "src/b.ts:7",
                    "description": "count() still returns a fixed answer"}])],
    )

    path = build_review.write_feature_notes(FEATURE, TASKS, tmp_path, last_look=look)

    record = json.loads(path.read_text())
    assert record["notes"] == [{"task_id": "TASK-LL1-001", **NOTES["TASK-LL1-001"][1]}]
    assert record["total"] == 1
    assert record["rechecked"] == {"still_true": 1, "no_longer_apply": 2}
    # One look-up pass (read-only tools) and one verdict call, no more.
    assert [bool(c.get("synthesis")) for c in calls] == [False, True]
    assert calls[0]["allowed_tools"] == list(build_review.LOOKUP_TOOLS)
    assert calls[1]["allowed_tools"] == []
    lookup_prompt = calls[0]["prompt"]
    assert build_review.RECHECK_SENTENCE in lookup_prompt
    assert build_review.MERGE_CHECK_RULE in lookup_prompt
    for left in NOTES.values():
        for note in left:
            assert f"{note['pattern']} {note['location']}: {note['description']}" in lookup_prompt
    assert build_review.MERGE_CHECK_RULE in calls[1]["prompt"]


def test_a_finding_the_verdict_dropped_still_keeps_its_note(tmp_path: Path) -> None:
    """The look-up pass's own lines count too: a verdict that loses one must
    not take a true note off the card."""
    _seed(tmp_path)
    look, _calls = _reviewer(
        tmp_path, "NOT_TESTED src/a.ts:20: still no test\n", [_verdict([])]
    )

    path = build_review.write_feature_notes(FEATURE, TASKS, tmp_path, last_look=look)

    record = json.loads(path.read_text())
    assert [n["pattern"] for n in record["notes"]] == ["NOT_TESTED"]
    assert record["rechecked"] == {"still_true": 1, "no_longer_apply": 2}


def test_no_findings_means_every_note_no_longer_applies(tmp_path: Path) -> None:
    _seed(tmp_path)
    look, _calls = _reviewer(tmp_path, "NO FINDINGS", [_verdict([])])

    record = json.loads(
        build_review.write_feature_notes(FEATURE, TASKS, tmp_path, last_look=look).read_text()
    )

    assert record["notes"] == []
    assert record["total"] == 0
    assert record["rechecked"] == {"still_true": 0, "no_longer_apply": 3}


@pytest.mark.parametrize(
    "lookup, verdicts, expected_calls",
    [
        pytest.param("", [], 1, id="empty-lookup"),
        pytest.param(RuntimeError("model unreachable"), [], 1, id="lookup-fails"),
        pytest.param("STUB src/b.ts:7: x", [SDKTimeoutError("timed out")], 2,
                     id="verdict-times-out"),
        pytest.param("STUB src/b.ts:7: x", [None, None], 3, id="verdict-unreadable-twice"),
        pytest.param("The notes look fine to me.", [_verdict([])], 2,
                     id="neither-findings-nor-no-findings"),
    ],
)
def test_a_reviewer_that_gives_no_answer_leaves_the_notes_byte_identical(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    lookup: Any,
    verdicts: List[Any],
    expected_calls: int,
) -> None:
    _seed(tmp_path)
    today = _today(tmp_path)
    look, calls = _reviewer(tmp_path, lookup, verdicts)

    with caplog.at_level(logging.WARNING, logger=build_review.logger.name):
        path = build_review.write_feature_notes(FEATURE, TASKS, tmp_path, last_look=look)

    assert path.read_bytes() == today
    assert len(calls) == expected_calls
    assert len([r for r in caplog.records if r.name == build_review.logger.name]) == 1


def test_a_last_look_that_raises_leaves_the_notes_byte_identical(tmp_path: Path) -> None:
    _seed(tmp_path)
    today = _today(tmp_path)

    def broken(_notes):
        raise RuntimeError("event loop already running")

    path = build_review.write_feature_notes(FEATURE, TASKS, tmp_path, last_look=broken)

    assert path.read_bytes() == today


def test_no_notes_means_no_extra_review(tmp_path: Path) -> None:
    _seed(tmp_path, {"TASK-LL1-001": []})
    look = MagicMock()

    record = json.loads(
        build_review.write_feature_notes(FEATURE, TASKS, tmp_path, last_look=look).read_text()
    )

    look.assert_not_called()
    assert record == {"feature": FEATURE, "notes": [], "total": 0}


def test_the_feature_hands_the_reviewer_its_starting_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The feature orchestrator's hook: a task review's model and time, the
    feature's recorded starting commit, the notes as given."""
    from types import SimpleNamespace

    from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
    from guardkit.orchestrator.seam_checks import feature_base_path

    base = feature_base_path(tmp_path, FEATURE)
    base.parent.mkdir(parents=True)
    base.write_text(json.dumps({"feature_base_commit": "c0ffee" * 6}), encoding="utf-8")
    seen: Dict[str, Any] = {}

    async def _fake(self, **kwargs):
        seen.update(kwargs, invoker=self)
        return []

    monkeypatch.setattr(AgentInvoker, "invoke_last_look", _fake)
    orchestrator = FeatureOrchestrator.__new__(FeatureOrchestrator)
    orchestrator.sdk_timeout = None
    orchestrator.timeout_multiplier = 1.0
    orchestrator.model = "m"
    orchestrator.coach_model = "c"
    orchestrator._emitter = None
    notes = [{"pattern": "STUB", "location": "src/b.ts:3", "description": "x"}]

    found = orchestrator._last_look(
        SimpleNamespace(id=FEATURE), SimpleNamespace(path=tmp_path)
    )(notes)

    assert found == []
    assert seen["feature_id"] == FEATURE
    assert seen["base"] == "c0ffee" * 6
    assert seen["notes"] == notes
    assert seen["invoker"].worktree_path == tmp_path


def test_the_task_lookup_prompt_is_unchanged() -> None:
    """The last look must not change what the per-task review is asked: its
    look-up prompt is pinned to the text before the last look was added (and
    says nothing yet about what runs at merge; b1's experiment decides that)."""
    prompts = []
    for change in (
        build_review.ReviewChange("diff --git a/x b/x\n+1\n", Path("/r/review.diff"), "a" * 40),
        build_review.ReviewChange("", None, "b" * 40),
    ):
        prompts.append(build_review.build_lookup_prompt(
            task_id="TASK-PIN-001", turn=2, requirements="Do the thing.",
            acceptance_criteria=[{"id": "AC-001", "text": "It works."}],
            change=change, check_section="check ran: 3 passed",
            player_report={"concerns": ["c"]},
            sent_back=[{"pattern": "STUB", "location": "src/a.py:3",
                        "description": "fixed answer"}],
            document_paths=["docs/a.md"], other_tasks="\n## Other tasks\n\nx\n",
        ))

    assert [hashlib.sha256(p.encode()).hexdigest() for p in prompts] == [
        "4bd64000ee0a0628f88ff9d7cd3a2a12ffc2fa32f8ccd0a3d4c821e7c43068bb",
        "2a1a5d53de4c5baa4b6c03186b53165bee0962c1a0106e63273611ca084263c9",
    ]
    assert all(build_review.MERGE_CHECK_RULE not in p for p in prompts)
