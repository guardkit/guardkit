"""The review's look-up pass is not abandoned while its answer is being written
(5 November 2026).

Tool use in the look-up pass ends before its time is up and the model is asked
for its answer from what it read. Under shared load on the model server that
answer alone took 507 s, past the pass's time, and everything the pass had
found was thrown away: the verdict then ran without it. The answer now gets
half the pass's time again before the pass is abandoned; when tool use ends is
unchanged, because the harness is still given the pass's own time.

Async calls use ``asyncio.run`` to stay free of a pytest-asyncio dependency.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

import pytest

from guardkit.orchestrator import agent_invoker as invoker_module
from guardkit.orchestrator.agent_invoker import AgentInvoker, SDKTimeoutError
from guardkit.orchestrator.harness import AssistantMessageEvent, ResultMessageEvent


class _SlowAnswer:
    """A harness whose answer arrives ``delay`` seconds after it is asked."""

    def __init__(self, delay: float) -> None:
        self.delay = delay
        self.timeouts: List[float] = []

    async def invoke(self, *, prompt: str, role: str, tools: list, cwd: Path,
                     timeout_seconds: float):
        self.timeouts.append(timeout_seconds)
        await asyncio.sleep(self.delay)
        yield AssistantMessageEvent(text="NOT_TESTED src/a.py:3: nothing tests it")
        yield ResultMessageEvent(session_id=None)


def _invoker(tmp_path: Path, timeout: float) -> AgentInvoker:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    invoker = AgentInvoker(worktree_path=worktree, max_turns_per_agent=30,
                           sdk_timeout_seconds=60)
    invoker.sdk_timeout_seconds = timeout  # type: ignore[assignment]
    return invoker


def _invoke(invoker: AgentInvoker, grace: float):
    return asyncio.run(invoker._invoke_with_role(
        prompt="TASK-GRACE-001 look", agent_type="coach", allowed_tools=["Read"],
        permission_mode="bypassPermissions", return_events=True,
        answer_grace_seconds=grace,  # type: ignore[arg-type]
    ))


def test_an_answer_inside_the_grace_is_kept(tmp_path: Path, monkeypatch) -> None:
    harness = _SlowAnswer(delay=0.4)
    monkeypatch.setattr(invoker_module, "select_harness", lambda **kw: harness)
    invoker = _invoker(tmp_path, timeout=0.2)

    _, events = _invoke(invoker, grace=2)

    assert any(isinstance(e, AssistantMessageEvent) and "NOT_TESTED" in e.text for e in events)
    assert harness.timeouts == [0.2]  # tool use still ends at the pass's own time


def test_without_grace_the_same_answer_is_abandoned(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(invoker_module, "select_harness", lambda **kw: _SlowAnswer(delay=0.4))
    invoker = _invoker(tmp_path, timeout=0.2)

    with pytest.raises(SDKTimeoutError):
        _invoke(invoker, grace=0)


def test_the_lookup_pass_gives_its_answer_half_its_time_again(tmp_path: Path) -> None:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = tmp_path
    invoker.sdk_timeout_seconds = 3600
    seen: List[Dict[str, Any]] = []

    async def _iwr(**kwargs):
        seen.append({**kwargs, "sdk_timeout_seconds": invoker.sdk_timeout_seconds})
        return (None, [AssistantMessageEvent(text="NO FINDINGS"),
                       ResultMessageEvent(session_id=None)])

    invoker._invoke_with_role = _iwr  # type: ignore[method-assign]

    found = asyncio.run(invoker._invoke_coach_gather(
        task_id="TASK-GRACE-001", turn=1, requirements="Do it.", player_report={},
        evidence_bundle=None, acceptance_criteria=None, gather_timeout=1440, prompt="look",
    ))

    assert found == "NO FINDINGS"
    assert seen[0]["sdk_timeout_seconds"] == 1440
    assert seen[0]["answer_grace_seconds"] == 720
    assert invoker.sdk_timeout_seconds == 3600
