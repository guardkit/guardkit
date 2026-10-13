"""A scratch file written and removed again is not a fabricated claim.

13 October 2026, first web fixture proof (build FEAT-40E8, task 001, turn 4).
The builder wrote ``apps/web/src/zzprobe.test.tsx``, edited it, and removed
it. It never named the file: the path appeared only in the lists the write
tracker builds. The claim audit still raised, word for word (kept in
``turn_state_turn_4.json``)::

    Deterministic honesty record (claim_audit, severity=critical): Player
    claim: Player claimed file apps/web/src/zzprobe.test.tsx. Actual: Path
    absent from 'git status --porcelain' so 'git add -A' would not stage it.
    Probes: path_exists=False; gitignore_match=not checked (file missing);
    tracked=not checked (file missing). Most likely cause: the Player claimed
    work on a file that does not exist on disk.

and the evidence gathering aborted on a turn whose tests passed.

Every test here goes through the whole path: harness events feed the parser,
``_create_player_report_from_task_work`` writes the final report (and
rewrites ``task_work_results.json``, which is what the Coach's own honesty
check reads), and ``CoachVerifier`` checks the claims. Only a write
CONFIRMED by its own successful result, never named by the builder or a
promise, missing on disk and unknown to git is set aside. Every other shape
keeps today's critical finding.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import pytest

from guardkit.orchestrator.coach_verification import CoachVerifier
from guardkit.orchestrator.harness.adapter import (
    AssistantMessageEvent,
    ResultMessageEvent,
    ToolResultEvent,
    ToolUseEvent,
)

PROBE = "apps/web/src/zzprobe.test.tsx"
TRACKED = "apps/web/src/App.tsx"

_FINAL_TEXT = "10 tests passed, 0 tests failed\nAll quality gates passed"


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _invoker(tmp_path: Path) -> Any:
    """An invoker over a real git checkout holding one committed file."""
    from guardkit.orchestrator.agent_invoker import AgentInvoker

    worktree = tmp_path / "worktree"
    (worktree / "apps" / "web" / "src").mkdir(parents=True)
    (worktree / TRACKED).write_text("export const App = () => null;\n")
    _git("init", "--initial-branch=main", cwd=worktree)
    _git("add", "-A", cwd=worktree)
    _git("commit", "-m", "base", cwd=worktree)
    return AgentInvoker(
        worktree_path=worktree, max_turns_per_agent=30, sdk_timeout_seconds=60
    )


def _harness(events: List[Any], final_text: str) -> Any:
    class ReplayHarness:
        supports_resume = False

        async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
            for event in events:
                if callable(event):
                    event()
                    continue
                yield event
            yield AssistantMessageEvent(text=final_text, raw=None)
            yield ResultMessageEvent(session_id=None, raw=None)

        async def cancel(self) -> None:
            return None

    return ReplayHarness()


def _use(call_id: Optional[str], name: str, path: Path) -> ToolUseEvent:
    return ToolUseEvent(
        tool_use_id=call_id,  # type: ignore[arg-type]
        name=name,
        input={"file_path": str(path), "content": "it('probe', () => {});\n"},
    )


def _ok(call_id: str) -> ToolResultEvent:
    return ToolResultEvent(tool_use_id=call_id, content="Updated file")


def _put(path: Path) -> Any:
    def run() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("it('probe', () => {});\n")

    return run


def _remove(path: Path) -> Any:
    return lambda: path.unlink()


def _write_promise(invoker: Any, task_id: str, files: List[str]) -> Any:
    """The builder's own report, naming files in a completion promise."""

    def run() -> None:
        folder = invoker.worktree_path / ".guardkit" / "autobuild" / task_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "player_turn_1.json").write_text(
            json.dumps(
                {
                    "completion_promises": [
                        {
                            "criterion_id": "AC-001",
                            "status": "complete",
                            "implementation_files": files,
                        }
                    ]
                }
            )
        )

    return run


async def _whole_path(
    invoker: Any, task_id: str, events: List[Any], final_text: str = _FINAL_TEXT
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Harness events → parser → final report; returns (report, results)."""
    with patch(
        "guardkit.orchestrator.agent_invoker.select_harness",
        return_value=_harness(events, final_text),
    ):
        result = await invoker._invoke_task_work_implement(
            task_id=task_id, mode="standard"
        )
    assert result.success is True
    invoker._create_player_report_from_task_work(task_id, 1, result)
    folder = invoker.worktree_path / ".guardkit" / "autobuild" / task_id
    report = json.loads((folder / "player_turn_1.json").read_text())
    record = json.loads((folder / "task_work_results.json").read_text())
    return report, record


def _critical_for(worktree: Path, record: Dict[str, Any], path: str) -> List[Any]:
    """The claim check and the existence check, as the Coach runs them."""
    verifier = CoachVerifier(worktree)
    found = verifier._verify_files_exist(record) + verifier._verify_claims_were_staged(
        record
    )
    return [d for d in found if path in d.player_claim and d.severity == "critical"]


def _is_fabricated_claim(discrepancies: List[Any], path: str) -> bool:
    return any(
        d.claim_type == "claim_audit"
        and d.player_claim == f"Player claimed file {path}"
        and "path_exists=False" in d.actual_value
        for d in discrepancies
    )


# ---------------------------------------------------------------------------
# The exemption
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_written_then_removed_probe_is_not_a_critical_claim(
    tmp_path: Path,
) -> None:
    invoker = _invoker(tmp_path)
    wt = invoker.worktree_path
    probe = wt / PROBE
    report, record = await _whole_path(
        invoker,
        "TASK-PROBE",
        [
            _put(probe),
            _use("c1", "Write", probe),
            _ok("c1"),
            _use("c2", "Edit", probe),
            _ok("c2"),
            _remove(probe),
        ],
    )

    # Both the final report and the results file the Coach reads.
    assert _critical_for(wt, report, PROBE) == []
    assert _critical_for(wt, record, PROBE) == []


@pytest.mark.asyncio
async def test_a_confirmed_write_then_deleted_and_never_claimed_is_exempt(
    tmp_path: Path,
) -> None:
    invoker = _invoker(tmp_path)
    wt = invoker.worktree_path
    probe = wt / PROBE
    report, record = await _whole_path(
        invoker,
        "TASK-CONFIRMED",
        [_put(probe), _use("c1", "write_file", probe), _ok("c1"), _remove(probe)],
    )

    for final in (report, record):
        assert final["files_written_then_removed"] == [PROBE]
        assert PROBE in final["files_authored"]
        assert PROBE not in final["files_created"]
        assert _critical_for(wt, final, PROBE) == []


# ---------------------------------------------------------------------------
# Controls: unconfirmed writes stay critical (pass before and after)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_an_unanswered_write_that_is_missing_stays_critical(
    tmp_path: Path,
) -> None:
    invoker = _invoker(tmp_path)
    wt = invoker.worktree_path
    report, record = await _whole_path(
        invoker, "TASK-UNANSWERED", [_use("c1", "write_file", wt / PROBE)]
    )

    for final in (report, record):
        assert PROBE in final["files_created"]
        assert final.get("files_written_then_removed", []) == []
        assert _is_fabricated_claim(_critical_for(wt, final, PROBE), PROBE)


@pytest.mark.asyncio
async def test_a_write_without_a_call_id_that_is_missing_stays_critical(
    tmp_path: Path,
) -> None:
    invoker = _invoker(tmp_path)
    wt = invoker.worktree_path
    probe = wt / PROBE
    report, record = await _whole_path(
        invoker,
        "TASK-NO-ID",
        [_put(probe), _use(None, "write_file", probe), _remove(probe)],
    )

    for final in (report, record):
        assert PROBE in final["files_created"]
        assert final.get("files_written_then_removed", []) == []
        assert _is_fabricated_claim(_critical_for(wt, final, PROBE), PROBE)


# ---------------------------------------------------------------------------
# Kept guards: a named path is a claim (pass before and after)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_confirmed_write_the_builder_names_in_words_stays_critical(
    tmp_path: Path,
) -> None:
    invoker = _invoker(tmp_path)
    wt = invoker.worktree_path
    probe = wt / PROBE
    report, record = await _whole_path(
        invoker,
        "TASK-NAMED",
        [_put(probe), _use("c1", "write_file", probe), _ok("c1"), _remove(probe)],
        final_text=f"Created: {PROBE}\n" + _FINAL_TEXT,
    )

    for final in (report, record):
        assert final.get("files_written_then_removed", []) == []
        assert _is_fabricated_claim(_critical_for(wt, final, PROBE), PROBE)


@pytest.mark.asyncio
async def test_a_confirmed_write_named_in_a_promise_stays_critical(
    tmp_path: Path,
) -> None:
    invoker = _invoker(tmp_path)
    wt = invoker.worktree_path
    probe = wt / PROBE
    task_id = "TASK-PROMISED"
    report, record = await _whole_path(
        invoker,
        task_id,
        [
            _put(probe),
            _use("c1", "write_file", probe),
            _ok("c1"),
            _remove(probe),
            _write_promise(invoker, task_id, [PROBE]),
        ],
    )

    for final in (report, record):
        assert final.get("files_written_then_removed", []) == []
        assert _is_fabricated_claim(_critical_for(wt, final, PROBE), PROBE)


@pytest.mark.asyncio
async def test_a_path_named_in_words_with_no_write_call_stays_critical(
    tmp_path: Path,
) -> None:
    invoker = _invoker(tmp_path)
    wt = invoker.worktree_path
    report, record = await _whole_path(
        invoker,
        "TASK-WORDS-ONLY",
        [],
        final_text=f"Created: {PROBE}\n" + _FINAL_TEXT,
    )

    for final in (report, record):
        assert PROBE in final["files_created"]
        assert final.get("files_written_then_removed", []) == []
        assert _is_fabricated_claim(_critical_for(wt, final, PROBE), PROBE)


# ---------------------------------------------------------------------------
# Authorship is never shortened (pass before and after)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_tracked_file_the_builder_deleted_keeps_its_authorship(
    tmp_path: Path,
) -> None:
    invoker = _invoker(tmp_path)
    wt = invoker.worktree_path
    tracked = wt / TRACKED
    report, record = await _whole_path(
        invoker,
        "TASK-TRACKED-DELETE",
        [_use("c1", "write_file", tracked), _ok("c1"), _remove(tracked)],
    )

    for final in (report, record):
        assert TRACKED in final["files_modified"]
        assert TRACKED in final["files_authored"]
        assert final.get("files_written_then_removed", []) == []


@pytest.mark.asyncio
async def test_contention_still_sees_a_deleted_file(tmp_path: Path) -> None:
    from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator

    invoker = _invoker(tmp_path)
    wt = invoker.worktree_path
    tracked = wt / TRACKED
    probe = wt / PROBE
    _, record = await _whole_path(
        invoker,
        "TASK-CONTENTION",
        [
            _use("c1", "write_file", tracked),
            _ok("c1"),
            _remove(tracked),
            _put(probe),
            _use("c2", "write_file", probe),
            _ok("c2"),
            _remove(probe),
        ],
    )
    assert {TRACKED, PROBE} <= set(record["files_authored"])

    def overlap(peer_files: List[str]) -> Dict[str, frozenset]:
        validator = CoachValidator(
            worktree_path=str(wt),
            task_id="TASK-CONTENTION",
            test_command="true",
            wave_size=2,
            peer_changed_files={"TASK-PEER": peer_files},
        )
        return validator._detect_source_file_contention(record)

    assert overlap([TRACKED]) == {"TASK-PEER": frozenset({TRACKED})}
    assert overlap([PROBE]) == {"TASK-PEER": frozenset({PROBE})}
