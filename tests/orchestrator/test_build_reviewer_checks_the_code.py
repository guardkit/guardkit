"""The build reviewer checks the change against the code (29 October 2026).

Rich, 29 October 2026: "I expect it's more of a 'paperwork' reviewer than an
actual coach reviewing what has been implemented", then "please proceed with
rebuilding the builder coach reviewer as per your plan" (the build reviewer
design of 29 October 2026).

Caller-level checks of what the design asks for:

* the review's look-up pass, through the real selector, guardkitfactory's
  harness and read-only backend (only the model's HTTP is scripted), is
  offered read-only tools only, is stopped after 40 tool-using turns and asked
  for its answer, and that answer reaches the verdict call;
* the look-up prompt carries the change from git: a function renamed in one
  file whose caller elsewhere was not changed shows the old name, and the
  whole change is written where the reviewer's read_file reads it, outside the
  worktree, without touching the worktree's index;
* a located finding gives exactly one repair turn, with all its findings as
  the builder's feedback; none without a located finding, none with
  ``GUARDKIT_REVIEW_REPAIR_TURN=0`` and none with no turn left; the next
  review checks the findings first and the turn is then approved;
* what the final review leaves reaches the feature's build review notes.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import httpx
import pytest

from guardkit.orchestrator import build_review
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.harness import AssistantMessageEvent, ResultMessageEvent

_TASK = "TASK-BR-001"
_FINDING = (
    "CALLERS_NOT_UPDATED caller.py:3: caller.py still calls old_name, "
    "which lib.py renamed to new_name."
)
_WRITE_TOOLS = {"write_file", "edit_file", "delete", "execute", "task", "write_todos"}
_READ_ONLY = {
    "read_file", "ls", "grep", "glob",
    "code_search", "code_outline", "code_pattern", "code_references",
}


def _git(repo: Path, *args: str) -> str:
    env = {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(repo),
    }
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
        env=env,
    ).stdout.strip()


def _renamed_repo(tmp_path: Path) -> tuple[Path, Path, str]:
    """A build worktree (under ``<root>/.guardkit/worktrees``) whose builder
    renamed ``old_name`` in lib.py and left caller.py calling it."""
    root = tmp_path / "project"
    worktree = root / ".guardkit" / "worktrees" / _TASK
    worktree.mkdir(parents=True)
    _git(worktree, "init", "-q")
    (worktree / "lib.py").write_text("def old_name():\n    return 1\n")
    (worktree / "caller.py").write_text("from lib import old_name\n\nprint(old_name())\n")
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-qm", "base")
    base = _git(worktree, "rev-parse", "HEAD")
    (worktree / "lib.py").write_text("def new_name():\n    return 1\n")
    (worktree / "notes.py").write_text("NOTE = 'new file'\n")  # untracked
    return root, worktree, base


def _response(body: Dict[str, Any], message: Dict[str, Any], finish: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-review",
            "object": "chat.completion",
            "created": 1,
            "model": body.get("model", "qwen36-workhorse"),
            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
        },
    )


class _ReviewModel:
    """Scripted model: the look-up pass reads the whole change, then keeps
    asking for (different) tools until they are taken away; its final call
    gives the finding; the verdict call turns it into an issue."""

    def __init__(self, diff_file: Path, worktree: Path) -> None:
        self.diff_file = diff_file
        self.worktree = worktree
        self.requests: List[Dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append(body)
        text = json.dumps(body["messages"])
        if body.get("tools"):
            index = sum(1 for b in self.requests if b.get("tools")) - 1
            if index == 0:
                name, args = "read_file", {"file_path": str(self.diff_file)}
            else:
                name, args = "grep", {"pattern": f"name_{index}", "path": str(self.worktree)}
            return _response(
                body,
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": f"call-{index}",
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args)},
                    }],
                },
                "tool_calls",
            )
        if "Tool use has ended for this answer" in text:
            return _response(body, {"role": "assistant", "content": _FINDING}, "stop")
        verdict = {
            "task_id": _TASK, "turn": 1, "decision": "feedback",
            "issues": [{
                "pattern": "CALLERS_NOT_UPDATED", "severity": "major",
                "location": "caller.py:3",
                "description": "caller.py still calls old_name, renamed to new_name.",
            }],
            "rationale": "One caller was not updated.",
        }
        return _response(
            body,
            {"role": "assistant", "content": "```json\n" + json.dumps(verdict) + "\n```"},
            "stop",
        )


def _install_transport(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    from langchain_openai.chat_models import _client_utils

    monkeypatch.setattr(
        _client_utils, "_build_sync_httpx_client",
        lambda *a, **k: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(
        _client_utils, "_build_async_httpx_client",
        lambda *a, **k: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def _user_text(body: Dict[str, Any]) -> str:
    return json.dumps([m for m in body["messages"] if m.get("role") == "user"])


@pytest.mark.asyncio
async def test_the_review_reads_the_change_with_read_only_tools_and_ends_with_an_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, m0_routine_fleet_route: str
) -> None:
    pytest.importorskip("guardkitfactory")
    from guardkitfactory.harness.tool_loop import MAX_TOOL_TURNS_PER_RUN

    root, worktree, base = _renamed_repo(tmp_path)
    diff_file = build_review.diff_path(_TASK, 1, worktree)
    model = _ReviewModel(diff_file, worktree)
    _install_transport(monkeypatch, model)
    monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    for name in ("LANGCHAIN_TRACING", "LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING",
                 "GUARDKIT_REVIEW_REPAIR_TURN"):
        monkeypatch.delenv(name, raising=False)

    invoker = AgentInvoker(worktree_path=worktree, model_name=m0_routine_fleet_route)
    invoker._baseline_commit = base
    invoker._calculate_sdk_timeout = MagicMock(return_value=300)  # type: ignore[method-assign]
    result = await invoker.invoke_coach(
        task_id=_TASK,
        turn=1,
        requirements="Rename old_name to new_name.",
        player_report={"files_modified": ["lib.py"], "files_created": ["notes.py"]},
        turn_left=True,
    )

    lookup = [b for b in model.requests if b.get("tools")]
    # Read-only tools only, and the limit: 40 tool-using turns, then the
    # tools are withdrawn and the answer asked for.
    assert MAX_TOOL_TURNS_PER_RUN == 40
    assert len(lookup) == MAX_TOOL_TURNS_PER_RUN
    for body in lookup:
        offered = {tool["function"]["name"] for tool in body["tools"]}
        assert offered <= _READ_ONLY and "read_file" in offered, offered
        assert not offered & _WRITE_TOOLS
    final_lookup = model.requests[MAX_TOOL_TURNS_PER_RUN]
    assert not final_lookup.get("tools")
    assert "Tool use has ended for this answer" in json.dumps(final_lookup["messages"])

    # The change: the old name is in the reviewer's input, with the untracked
    # file, and the whole change's path is named.
    prompt = _user_text(lookup[0])
    assert "-def old_name():" in prompt and "+def new_name():" in prompt
    assert "notes.py" in prompt
    assert str(diff_file) in prompt
    # The whole change is outside the worktree, the read-only read_file
    # reaches it, and the worktree's own index was never written.
    assert not diff_file.is_relative_to(worktree)
    assert "def old_name" in diff_file.read_text()
    tool_results = [m for m in lookup[1]["messages"] if m.get("role") == "tool"]
    assert tool_results and "def old_name" in json.dumps(tool_results[0])
    assert "Error" not in str(tool_results[0].get("content"))[:20]
    assert _git(worktree, "diff", "--cached", "--name-only") == ""

    # The answer (not a discard) reaches the verdict call, whose issue carries
    # the pattern and the place; a located finding gets the repair turn.
    verdict = model.requests[-1]
    assert verdict is not final_lookup and not verdict.get("tools")
    assert "CALLERS_NOT_UPDATED caller.py:3" in json.dumps(verdict["messages"])
    assert result.success is True
    report = result.report
    assert report["decision"] == "feedback"
    assert report[build_review.REPAIR_KEY] is True
    (issue,) = report["issues"]
    assert issue["pattern"] == "CALLERS_NOT_UPDATED" and issue["location"] == "caller.py:3"


# ---------------------------------------------------------------------------
# The repair turn, through invoke_coach with the model calls scripted
# ---------------------------------------------------------------------------


def _verdict(issues: List[Dict[str, Any]], turn: int = 1) -> tuple:
    body = {"task_id": _TASK, "turn": turn, "decision": "feedback" if issues else "approve",
            "issues": issues, "rationale": "r"}
    return (None, [
        AssistantMessageEvent(text="```json\n" + json.dumps(body) + "\n```"),
        ResultMessageEvent(session_id=None),
    ])


def _located(n: int) -> List[Dict[str, Any]]:
    return [
        {"pattern": "NOT_TESTED", "severity": "major", "location": f"src/a{i}.py:{i + 1}",
         "description": f"criterion {i} has no test"}
        for i in range(n)
    ]


def _invoker(tmp_path: Path, issues_by_turn: Dict[int, List[Dict[str, Any]]]) -> tuple:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = tmp_path
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    prompts: List[Dict[str, Any]] = []

    async def _iwr(**kwargs: Any) -> tuple:
        prompts.append(kwargs)
        if not kwargs.get("synthesis"):
            return (None, [AssistantMessageEvent(text="findings"),
                           ResultMessageEvent(session_id=None)])
        return _verdict(issues_by_turn[kwargs["turn"]], kwargs["turn"])

    invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
    return invoker, prompts


def _review(invoker: AgentInvoker, turn: int, *, turn_left: bool = True) -> Dict[str, Any]:
    from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle

    result = asyncio.run(invoker.invoke_coach(
        task_id=_TASK, turn=turn, requirements="reqs",
        player_report={"files_modified": []},
        evidence_bundle=CoachEvidenceBundle(gathering_status="complete"),
        turn_left=turn_left,
    ))
    assert result.success is True
    return result.report


def test_a_located_finding_gives_exactly_one_repair_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(build_review.REPAIR_TURN_ENV, raising=False)
    invoker, calls = _invoker(tmp_path, {1: _located(4), 2: _located(2), 3: _located(2)})

    first = _review(invoker, 1)
    assert first["decision"] == "feedback"
    assert first[build_review.REPAIR_KEY] is True
    assert [i["location"] for i in first["issues"]] == [f"src/a{i}.py:{i + 1}" for i in range(4)]
    assert first[build_review.LEFTOVERS_KEY] == []

    # The next review checks the findings first, and is approved whatever
    # remains; what remains is recorded for the merge card.
    second = _review(invoker, 2)
    lookup_prompt = calls[2]["prompt"]
    assert "Findings the builder was sent back to fix" in lookup_prompt
    assert "src/a3.py:4" in lookup_prompt
    assert second["decision"] == "approve"
    assert build_review.REPAIR_KEY not in second
    assert [n["location"] for n in second[build_review.LEFTOVERS_KEY]] == [
        "src/a0.py:1", "src/a1.py:2",
    ]
    assert _review(invoker, 3)["decision"] == "approve"

    # The builder is shown every finding, not the top three.
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    text = orchestrator._extract_feedback(first)
    assert all(f"src/a{i}.py:{i + 1}" in text for i in range(4))
    assert "more issues" not in text


def test_a_resumed_task_keeps_its_one_repair_turn_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex review R2: after the repair turn, a resume (a new process, so a
    new invoker with nothing in memory) reads the task's own recorded reviews.
    Its next review checks the sent-back findings first, and any located
    findings that remain are advice: the task is approved."""
    monkeypatch.delenv(build_review.REPAIR_TURN_ENV, raising=False)
    first, _ = _invoker(tmp_path, {1: _located(2)})
    assert _review(first, 1)["decision"] == "feedback"

    resumed, calls = _invoker(tmp_path, {2: _located(2)})
    assert "_review_repair_sent" not in resumed.__dict__
    report = _review(resumed, 2)

    assert report["decision"] == "approve"
    assert build_review.REPAIR_KEY not in report
    assert [n["location"] for n in report[build_review.LEFTOVERS_KEY]] == [
        "src/a0.py:1", "src/a1.py:2",
    ]
    lookup_prompt = calls[0]["prompt"]
    assert "Findings the builder was sent back to fix" in lookup_prompt
    assert "- NOT_TESTED src/a1.py:2: criterion 1 has no test" in lookup_prompt


@pytest.mark.parametrize(
    "issues",
    [
        [],
        # No place, or not one of the five kinds: no repair turn.
        [{"pattern": "NOT_TESTED", "severity": "major", "location": "",
          "description": "a criterion has no test"}],
        [{"pattern": "EVIDENCE", "severity": "critical", "location": "src/a.py:1",
          "description": "not independently verified"}],
        [{"pattern": "CRITERION_CONFLICT", "severity": "minor",
          "location": "docs/design.md:4", "description": "the criterion and the design differ"}],
    ],
)
def test_no_repair_turn_without_a_located_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, issues: List[Dict[str, Any]]
) -> None:
    monkeypatch.delenv(build_review.REPAIR_TURN_ENV, raising=False)
    invoker, _ = _invoker(tmp_path, {1: issues})
    report = _review(invoker, 1)
    assert report["decision"] == "approve"
    assert build_review.REPAIR_KEY not in report


def test_the_setting_off_and_no_turn_left_give_no_repair_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(build_review.REPAIR_TURN_ENV, "0")
    invoker, _ = _invoker(tmp_path, {1: _located(2)})
    off = _review(invoker, 1)
    assert off["decision"] == "approve"
    assert len(off[build_review.LEFTOVERS_KEY]) == 2

    monkeypatch.delenv(build_review.REPAIR_TURN_ENV)
    invoker, _ = _invoker(tmp_path / "last", {1: _located(2)})
    (tmp_path / "last").mkdir()
    assert _review(invoker, 1, turn_left=False)["decision"] == "approve"


def test_leftovers_reach_the_feature_build_review_notes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The final review's record is what the notes read, at most ten in all."""
    monkeypatch.setenv(build_review.REPAIR_TURN_ENV, "0")
    invoker, _ = _invoker(tmp_path, {1: _located(3), 2: _located(12)})
    _review(invoker, 1)
    _review(invoker, 2)

    path = build_review.write_feature_notes("FEAT-BR", [_TASK, "TASK-NONE"], tmp_path)

    assert path == tmp_path / ".guardkit" / "autobuild-private" / "build_review_notes.json"
    notes = json.loads(path.read_text())
    assert notes["feature"] == "FEAT-BR"
    assert notes["total"] == 10  # the final review left ten (its cap)
    assert len(notes["notes"]) == 10
    assert notes["notes"][0] == {
        "task_id": _TASK, "pattern": "NOT_TESTED", "location": "src/a0.py:1",
        "description": "criterion 0 has no test",
    }

