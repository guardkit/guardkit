"""Skeleton tests for guardkit.orchestrator.specialist_invocations.

Pins the contract that TASK-OSI-004 / TASK-OSI-005 build on:

* :func:`run_specialist` delegates to ``AgentInvoker._invoke_with_role``
  with the right agent_type / permission_mode for each specialist.
* The runner restores ``sdk_timeout_seconds`` and ``_cancellation_event``
  on the AgentInvoker after the call, even when the call raises.
* On exception, the runner returns ``status="failed"`` with ``error``
  populated and reaps child claude processes — it never propagates the
  exception.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardkit.orchestrator.specialist_invocations import (
    SpecialistInvocationResult,
    invoke_test_orchestrator,
    run_specialist,
)


def _make_fake_agent_invoker(
    *,
    invoke_side_effect=None,
    sdk_timeout_seconds: int = 1200,
    cancellation_event: threading.Event | None = None,
) -> MagicMock:
    """Return a MagicMock that mimics the AgentInvoker surface we touch.

    Only the attributes/methods :func:`run_specialist` reads or writes are
    populated. Pulling in the real AgentInvoker would require the SDK and
    a real worktree, neither of which this skeleton-level test needs.
    """
    invoker = MagicMock(name="AgentInvoker")
    invoker.sdk_timeout_seconds = sdk_timeout_seconds
    invoker._cancellation_event = cancellation_event
    invoker._invoke_with_role = AsyncMock(side_effect=invoke_side_effect)
    invoker._kill_child_claude_processes = MagicMock()
    return invoker


@pytest.mark.asyncio
async def test_run_specialist_happy_path_returns_passed(tmp_path: Path) -> None:
    """Successful delegation produces a passed result with phase derived
    from specialist_name and the conventional result_file path filled in.
    """
    invoker = _make_fake_agent_invoker()

    result = await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=42,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
    )

    assert isinstance(result, SpecialistInvocationResult)
    assert result.specialist_name == "test-orchestrator"
    assert result.phase == "4"
    assert result.status == "passed"
    assert result.error is None
    assert result.result_file == (
        tmp_path / ".guardkit" / "autobuild" / "TASK-OSI-001" / "specialist_results.json"
    )
    assert result.duration_seconds >= 0

    invoker._invoke_with_role.assert_awaited_once()
    kwargs = invoker._invoke_with_role.await_args.kwargs
    assert kwargs["prompt"] == "run the tests"
    assert kwargs["agent_type"] == "player"
    assert kwargs["permission_mode"] == "acceptEdits"
    assert kwargs["allowed_tools"] == ["Read", "Bash", "Write"]
    assert kwargs["task_id"] == "TASK-OSI-001"

    invoker._kill_child_claude_processes.assert_not_called()


@pytest.mark.asyncio
async def test_run_specialist_code_reviewer_runs_as_coach(tmp_path: Path) -> None:
    """code-reviewer must run as agent_type=coach with bypassPermissions
    so the existing read-only invariant the gate enforces holds.
    """
    invoker = _make_fake_agent_invoker()

    result = await run_specialist(
        specialist_name="code-reviewer",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=42,
        prompt="review the diff",
        allowed_tools=["Read", "Grep"],
        agent_invoker=invoker,
    )

    assert result.phase == "5"
    assert result.status == "passed"

    kwargs = invoker._invoke_with_role.await_args.kwargs
    assert kwargs["agent_type"] == "coach"
    assert kwargs["permission_mode"] == "bypassPermissions"


@pytest.mark.asyncio
async def test_run_specialist_failure_returns_failed_and_reaps(tmp_path: Path) -> None:
    """When ``_invoke_with_role`` raises, the runner must return a failed
    result, populate ``error``, and reap child claude processes — never
    propagate.
    """
    boom = RuntimeError("SDK exploded")
    invoker = _make_fake_agent_invoker(invoke_side_effect=boom)

    result = await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=42,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
    )

    assert result.status == "failed"
    assert result.error is not None
    assert "RuntimeError" in result.error
    assert "SDK exploded" in result.error
    # On failure we leave result_file unset so callers cannot assume the
    # specialist actually wrote the conventional file.
    assert result.result_file is None
    invoker._kill_child_claude_processes.assert_called_once()


@pytest.mark.asyncio
async def test_run_specialist_restores_state_after_call(tmp_path: Path) -> None:
    """The runner must restore ``sdk_timeout_seconds`` and
    ``_cancellation_event`` on the AgentInvoker on both the success and
    the failure paths so subsequent invocations see the original state.
    """
    original_timeout = 1234
    original_event = threading.Event()
    invoker = _make_fake_agent_invoker(
        sdk_timeout_seconds=original_timeout,
        cancellation_event=original_event,
    )
    override_event = threading.Event()

    # Inside the call, sdk_timeout_seconds must reflect the override.
    captured: dict[str, object] = {}

    async def _capture(**_: object) -> None:
        captured["timeout"] = invoker.sdk_timeout_seconds
        captured["cancellation"] = invoker._cancellation_event

    invoker._invoke_with_role = AsyncMock(side_effect=_capture)

    await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=99,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
        cancellation_event=override_event,
    )

    assert captured["timeout"] == 99
    assert captured["cancellation"] is override_event
    # State must be restored after the call, regardless of success.
    assert invoker.sdk_timeout_seconds == original_timeout
    assert invoker._cancellation_event is original_event


@pytest.mark.asyncio
async def test_run_specialist_restores_state_on_failure(tmp_path: Path) -> None:
    """Same restore invariant on the failure path."""
    original_timeout = 1234
    original_event = threading.Event()
    invoker = _make_fake_agent_invoker(
        invoke_side_effect=RuntimeError("boom"),
        sdk_timeout_seconds=original_timeout,
        cancellation_event=original_event,
    )

    result = await run_specialist(
        specialist_name="code-reviewer",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=77,
        prompt="review",
        allowed_tools=["Read"],
        agent_invoker=invoker,
        cancellation_event=threading.Event(),
    )

    assert result.status == "failed"
    assert invoker.sdk_timeout_seconds == original_timeout
    assert invoker._cancellation_event is original_event


# =============================================================================
# invoke_test_orchestrator (TASK-OSI-004)
# =============================================================================
#
# These tests exercise the orchestrator-side Phase 4 runner. The SDK
# boundary is the AgentInvoker._invoke_with_role mock — when the run is
# "successful" we simulate the real test-orchestrator agent by writing
# phase_4_summary.json from the side-effect callable. When the run
# "fails" we raise from the side-effect to mimic an SDK exception.


_TASK_ID_OSI_004 = "TASK-OSI-004-FAKE"


def _seed_task_markdown(worktree: Path, task_id: str) -> Path:
    """Place a minimal task markdown the runner can parse."""
    task_dir = worktree / "tasks" / "in_progress" / "fake-feature"
    task_dir.mkdir(parents=True, exist_ok=True)
    task_file = task_dir / f"{task_id}-fake.md"
    task_file.write_text(
        "---\n"
        f"id: {task_id}\n"
        "status: in_progress\n"
        "---\n\n"
        "# Task: Fake task\n\n"
        "## Description\n\n"
        "Make the fake thing work.\n\n"
        "## Acceptance Criteria\n\n"
        "- [ ] Fake AC 1\n"
        "- [ ] Fake AC 2\n\n"
        "## Notes\n\n"
        "Trailing section that must NOT leak into the prompt block.\n",
        encoding="utf-8",
    )
    return task_file


def _seed_task_work_results(worktree: Path, task_id: str) -> Path:
    """Place a minimal task_work_results.json for the Phase 3 summary."""
    autobuild_dir = worktree / ".guardkit" / "autobuild" / task_id
    autobuild_dir.mkdir(parents=True, exist_ok=True)
    results_path = autobuild_dir / "task_work_results.json"
    results_path.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "files_created": ["src/foo.py"],
                "files_modified": ["src/bar.py"],
                "test_files_created": ["tests/test_foo.py"],
            }
        ),
        encoding="utf-8",
    )
    return results_path


def _make_summary_writer(
    worktree: Path,
    task_id: str,
    summary_payload: dict,
):
    """Return an _invoke_with_role side-effect that writes phase_4_summary.json."""

    summary_path = (
        worktree
        / ".guardkit"
        / "autobuild"
        / task_id
        / "phase_4_summary.json"
    )

    async def _write_summary(**_: object) -> None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary_payload), encoding="utf-8")

    return _write_summary


@pytest.mark.asyncio
async def test_invoke_test_orchestrator_success_writes_phase_4_block_with_correct_schema(
    tmp_path: Path,
) -> None:
    """Success path: phase_4 block includes status/duration/error plus all
    five agent-derived fields read from phase_4_summary.json.
    """
    _seed_task_markdown(tmp_path, _TASK_ID_OSI_004)
    _seed_task_work_results(tmp_path, _TASK_ID_OSI_004)

    summary_payload = {
        "tests_run": 10,
        "tests_failed": 0,
        "coverage_pct": 85.5,
        "output_summary": "all tests passed",
        "quality_gates_passed": True,
    }
    invoker = _make_fake_agent_invoker(
        invoke_side_effect=_make_summary_writer(
            tmp_path, _TASK_ID_OSI_004, summary_payload
        ),
    )

    result = await invoke_test_orchestrator(
        worktree_path=tmp_path,
        task_id=_TASK_ID_OSI_004,
        sdk_timeout=42,
        agent_invoker=invoker,
    )

    assert isinstance(result, SpecialistInvocationResult)
    assert result.specialist_name == "test-orchestrator"
    assert result.phase == "4"
    assert result.status == "passed"
    assert result.error is None

    # Specialist invoked with the agent-declared tools.
    invoker._invoke_with_role.assert_awaited_once()
    kwargs = invoker._invoke_with_role.await_args.kwargs
    assert kwargs["allowed_tools"] == ["Read", "Write", "Bash", "Search"]
    assert kwargs["agent_type"] == "player"
    assert kwargs["permission_mode"] == "acceptEdits"
    # Prompt carries task-specific context, not the agent system prompt.
    assert _TASK_ID_OSI_004 in kwargs["prompt"]
    assert "Make the fake thing work." in kwargs["prompt"]
    assert "Fake AC 1" in kwargs["prompt"]
    assert "phase_4_summary.json" in kwargs["prompt"]
    # Phase 3 summary leaked from task_work_results.
    assert "src/foo.py" in kwargs["prompt"]

    # Specialist results file written with the §4.1 schema.
    results_path = (
        tmp_path
        / ".guardkit"
        / "autobuild"
        / _TASK_ID_OSI_004
        / "specialist_results.json"
    )
    assert results_path.exists()
    on_disk = json.loads(results_path.read_text(encoding="utf-8"))
    assert "phase_4" in on_disk
    block = on_disk["phase_4"]
    assert block["status"] == "passed"
    assert block["error"] is None
    assert block["duration_seconds"] >= 0
    assert block["tests_run"] == 10
    assert block["tests_failed"] == 0
    assert block["coverage_pct"] == 85.5
    assert block["output_summary"] == "all tests passed"
    assert block["quality_gates_passed"] is True


@pytest.mark.asyncio
async def test_invoke_test_orchestrator_failure_writes_failed_block_without_raising(
    tmp_path: Path,
) -> None:
    """SDK exception path: runner returns failed result and writes a
    failed phase_4 block with default agent-derived fields. Must NOT
    propagate the exception.
    """
    _seed_task_markdown(tmp_path, _TASK_ID_OSI_004)

    invoker = _make_fake_agent_invoker(
        invoke_side_effect=RuntimeError("SDK exploded"),
    )

    result = await invoke_test_orchestrator(
        worktree_path=tmp_path,
        task_id=_TASK_ID_OSI_004,
        sdk_timeout=42,
        agent_invoker=invoker,
    )

    assert result.status == "failed"
    assert result.error is not None
    assert "SDK exploded" in result.error

    results_path = (
        tmp_path
        / ".guardkit"
        / "autobuild"
        / _TASK_ID_OSI_004
        / "specialist_results.json"
    )
    assert results_path.exists()
    on_disk = json.loads(results_path.read_text(encoding="utf-8"))
    block = on_disk["phase_4"]
    assert block["status"] == "failed"
    assert block["error"] is not None
    assert "SDK exploded" in block["error"]
    # Defaults applied because there is no phase_4_summary.json.
    assert block["tests_run"] == 0
    assert block["tests_failed"] == 0
    assert block["coverage_pct"] == 0.0
    assert block["output_summary"] == ""
    assert block["quality_gates_passed"] is False
    # Cleanup invariant from run_specialist.
    invoker._kill_child_claude_processes.assert_called_once()


@pytest.mark.asyncio
async def test_invoke_test_orchestrator_timeout_writes_failed_block_with_timeout_error(
    tmp_path: Path,
) -> None:
    """Timeout path: TimeoutError surfaces as status='failed' with a
    timeout-mentioning error string, both on the result and on disk.
    """
    _seed_task_markdown(tmp_path, _TASK_ID_OSI_004)

    invoker = _make_fake_agent_invoker(
        invoke_side_effect=TimeoutError("SDK call timed out after 60s"),
    )

    result = await invoke_test_orchestrator(
        worktree_path=tmp_path,
        task_id=_TASK_ID_OSI_004,
        sdk_timeout=42,
        agent_invoker=invoker,
    )

    assert result.status == "failed"
    assert result.error is not None
    assert "timeout" in result.error.lower()

    results_path = (
        tmp_path
        / ".guardkit"
        / "autobuild"
        / _TASK_ID_OSI_004
        / "specialist_results.json"
    )
    assert results_path.exists()
    on_disk = json.loads(results_path.read_text(encoding="utf-8"))
    block = on_disk["phase_4"]
    assert block["status"] == "failed"
    assert block["error"] is not None
    assert "timeout" in block["error"].lower()


@pytest.mark.asyncio
async def test_invoke_test_orchestrator_preserves_existing_phase_5_block(
    tmp_path: Path,
) -> None:
    """Idempotent partial write: a pre-existing phase_5 block (e.g. from
    a prior interrupted turn) survives the phase_4 write unchanged.
    """
    _seed_task_markdown(tmp_path, _TASK_ID_OSI_004)
    autobuild_dir = (
        tmp_path / ".guardkit" / "autobuild" / _TASK_ID_OSI_004
    )
    autobuild_dir.mkdir(parents=True, exist_ok=True)
    results_path = autobuild_dir / "specialist_results.json"
    seeded_phase_5 = {
        "status": "passed",
        "duration_seconds": 5.0,
        "error": None,
        "approval_decision": "approved",
    }
    results_path.write_text(
        json.dumps({"phase_5": seeded_phase_5}, indent=2),
        encoding="utf-8",
    )

    summary_payload = {
        "tests_run": 3,
        "tests_failed": 0,
        "coverage_pct": 90.0,
        "output_summary": "ok",
        "quality_gates_passed": True,
    }
    invoker = _make_fake_agent_invoker(
        invoke_side_effect=_make_summary_writer(
            tmp_path, _TASK_ID_OSI_004, summary_payload
        ),
    )

    result = await invoke_test_orchestrator(
        worktree_path=tmp_path,
        task_id=_TASK_ID_OSI_004,
        sdk_timeout=42,
        agent_invoker=invoker,
    )

    assert result.status == "passed"

    on_disk = json.loads(results_path.read_text(encoding="utf-8"))
    # Both blocks present.
    assert "phase_4" in on_disk
    assert "phase_5" in on_disk
    # Phase 5 untouched (deep equality with seeded value).
    assert on_disk["phase_5"] == seeded_phase_5
    # Phase 4 reflects the just-written run.
    assert on_disk["phase_4"]["status"] == "passed"
    assert on_disk["phase_4"]["tests_run"] == 3
    assert on_disk["phase_4"]["coverage_pct"] == 90.0
