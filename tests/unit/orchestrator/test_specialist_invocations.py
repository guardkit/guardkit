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

import asyncio
import time

from guardkit.orchestrator import specialist_invocations
from guardkit.orchestrator.specialist_invocations import (
    SpecialistInvocationResult,
    _no_activity_watchdog_exceeded,
    invoke_code_reviewer,
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "specialist_name",
    ["test-orchestrator", "code-reviewer"],
)
async def test_run_specialist_heartbeat_label_includes_specialist_name(
    tmp_path: Path, specialist_name: str
) -> None:
    """run_specialist must thread a ``heartbeat_label_override`` kwarg
    containing ``"specialist:{name}"`` into ``_invoke_with_role`` so
    orchestrator-driven specialists are visually distinct from the
    actual task-work Player in heartbeat logs (TASK-ABSR-DIAG).
    """
    invoker = _make_fake_agent_invoker()

    await run_specialist(
        specialist_name=specialist_name,
        worktree_path=tmp_path,
        task_id="TASK-ABSR-DIAG",
        sdk_timeout=42,
        prompt="do the thing",
        allowed_tools=["Read"],
        agent_invoker=invoker,
    )

    invoker._invoke_with_role.assert_awaited_once()
    kwargs = invoker._invoke_with_role.await_args.kwargs
    assert "heartbeat_label_override" in kwargs, (
        "run_specialist must pass heartbeat_label_override to _invoke_with_role"
    )
    override = kwargs["heartbeat_label_override"]
    assert isinstance(override, str)
    assert f"specialist:{specialist_name}" in override
    assert "invocation" in override


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


# =============================================================================
# invoke_test_orchestrator timeout cap (TASK-FIX-SPECHANG)
# =============================================================================
#
# The Phase 4 runner must clamp caller-supplied sdk_timeout to a
# specialist-specific ceiling so a polling LLM cannot consume the full
# Player/Coach budget. Verified by capturing what the SDK actually saw
# during _invoke_with_role.


@pytest.mark.asyncio
async def test_invoke_test_orchestrator_caps_sdk_timeout_above_ceiling(
    tmp_path: Path,
) -> None:
    """Caller passes sdk_timeout > 600s; SDK call sees the capped value."""
    _seed_task_markdown(tmp_path, _TASK_ID_OSI_004)

    captured: dict[str, object] = {}

    async def _capture(**_: object) -> None:
        # run_specialist sets sdk_timeout_seconds on the invoker before
        # calling _invoke_with_role; that is the value the SDK sees.
        captured["timeout"] = invoker.sdk_timeout_seconds

    invoker = _make_fake_agent_invoker(invoke_side_effect=_capture)

    await invoke_test_orchestrator(
        worktree_path=tmp_path,
        task_id=_TASK_ID_OSI_004,
        sdk_timeout=2340,
        agent_invoker=invoker,
    )

    assert captured["timeout"] == 600


@pytest.mark.asyncio
async def test_invoke_test_orchestrator_passes_smaller_sdk_timeout_through(
    tmp_path: Path,
) -> None:
    """Caller passes sdk_timeout < 600s; cap is a no-op."""
    _seed_task_markdown(tmp_path, _TASK_ID_OSI_004)

    captured: dict[str, object] = {}

    async def _capture(**_: object) -> None:
        captured["timeout"] = invoker.sdk_timeout_seconds

    invoker = _make_fake_agent_invoker(invoke_side_effect=_capture)

    await invoke_test_orchestrator(
        worktree_path=tmp_path,
        task_id=_TASK_ID_OSI_004,
        sdk_timeout=300,
        agent_invoker=invoker,
    )

    assert captured["timeout"] == 300


# =============================================================================
# invoke_code_reviewer (TASK-OSI-005)
# =============================================================================
#
# These tests exercise the orchestrator-side Phase 5 runner. The SDK
# boundary is the AgentInvoker._invoke_with_role mock — code-reviewer
# runs without ``Write``, so review output flows through the runner's
# phase_5 block (default placeholders) rather than via a sidecar file.
# We test (a) success path appends phase_5 while preserving phase_4,
# (b) SDK failure records a failed phase_5 block without raising,
# (c) caller bug — ValueError when phase4_result.status != "passed",
# (d) prompt contains the contractual "Phase 4 summary" string.


_TASK_ID_OSI_005 = "TASK-OSI-005-FAKE"


def _make_passed_phase4_result() -> SpecialistInvocationResult:
    """Build a SpecialistInvocationResult that satisfies the entry guard."""
    return SpecialistInvocationResult(
        specialist_name="test-orchestrator",
        phase="4",
        status="passed",
        duration_seconds=1.5,
        result_file=None,
        error=None,
    )


def _make_failed_phase4_result() -> SpecialistInvocationResult:
    """Build a SpecialistInvocationResult that should trigger the guard."""
    return SpecialistInvocationResult(
        specialist_name="test-orchestrator",
        phase="4",
        status="failed",
        duration_seconds=0.5,
        result_file=None,
        error="SDK exploded",
    )


def _seed_specialist_results_with_phase_4(
    worktree: Path,
    task_id: str,
    phase_4_block: dict | None = None,
) -> Path:
    """Place a minimal specialist_results.json with a ``phase_4`` block.

    Mirrors what :func:`invoke_test_orchestrator` would have written on a
    successful Phase 4 run.
    """
    autobuild_dir = worktree / ".guardkit" / "autobuild" / task_id
    autobuild_dir.mkdir(parents=True, exist_ok=True)
    results_path = autobuild_dir / "specialist_results.json"
    block = phase_4_block or {
        "status": "passed",
        "duration_seconds": 1.5,
        "error": None,
        "tests_run": 12,
        "tests_failed": 0,
        "coverage_pct": 87.3,
        "output_summary": "all tests green",
        "quality_gates_passed": True,
    }
    results_path.write_text(
        json.dumps({"phase_4": block}, indent=2),
        encoding="utf-8",
    )
    return results_path


@pytest.mark.asyncio
async def test_invoke_code_reviewer_success_appends_phase_5_block_with_correct_schema(
    tmp_path: Path,
) -> None:
    """Success path: phase_5 block carries status/duration/error plus the
    Phase 5-specific defaults (issues, quality_score, recommendations,
    output_summary). Phase 4 block is preserved unchanged. Prompt carries
    the structured "Phase 4 summary" section the AC mandates.
    """
    _seed_task_markdown(tmp_path, _TASK_ID_OSI_005)
    seeded_phase_4 = {
        "status": "passed",
        "duration_seconds": 1.5,
        "error": None,
        "tests_run": 12,
        "tests_failed": 0,
        "coverage_pct": 87.3,
        "output_summary": "all tests green",
        "quality_gates_passed": True,
    }
    results_path = _seed_specialist_results_with_phase_4(
        tmp_path, _TASK_ID_OSI_005, seeded_phase_4
    )

    invoker = _make_fake_agent_invoker()

    result = await invoke_code_reviewer(
        worktree_path=tmp_path,
        task_id=_TASK_ID_OSI_005,
        phase4_result=_make_passed_phase4_result(),
        sdk_timeout=42,
        agent_invoker=invoker,
    )

    assert isinstance(result, SpecialistInvocationResult)
    assert result.specialist_name == "code-reviewer"
    assert result.phase == "5"
    assert result.status == "passed"
    assert result.error is None

    # Specialist invoked with the read-only review tool subset and the
    # coach role (review must NOT modify source files).
    invoker._invoke_with_role.assert_awaited_once()
    kwargs = invoker._invoke_with_role.await_args.kwargs
    assert kwargs["allowed_tools"] == ["Read", "Search", "Grep"]
    assert kwargs["agent_type"] == "coach"
    assert kwargs["permission_mode"] == "bypassPermissions"
    # Prompt carries task-specific context and the AC-mandated Phase 4
    # summary section with field values from the seeded block.
    assert _TASK_ID_OSI_005 in kwargs["prompt"]
    assert "Make the fake thing work." in kwargs["prompt"]
    assert "Fake AC 1" in kwargs["prompt"]
    assert "Phase 4 summary" in kwargs["prompt"]
    assert "tests_run: 12" in kwargs["prompt"]
    assert "coverage_pct: 87.3" in kwargs["prompt"]
    assert "quality_gates_passed: True" in kwargs["prompt"]
    assert "all tests green" in kwargs["prompt"]
    # Write tool MUST NOT be granted to the orchestrator-side reviewer.
    assert "Write" not in kwargs["allowed_tools"]

    # On-disk merge: phase_4 preserved verbatim, phase_5 appended.
    on_disk = json.loads(results_path.read_text(encoding="utf-8"))
    assert "phase_4" in on_disk
    assert "phase_5" in on_disk
    assert on_disk["phase_4"] == seeded_phase_4

    block = on_disk["phase_5"]
    assert block["status"] == "passed"
    assert block["error"] is None
    assert block["duration_seconds"] >= 0
    # Phase 5-specific defaults from _PHASE_5_AGENT_FIELD_DEFAULTS.
    assert block["issues"] == []
    assert isinstance(block["quality_score"], float)
    assert block["recommendations"] == []
    assert isinstance(block["output_summary"], str)
    assert block["output_summary"]  # non-empty placeholder


@pytest.mark.asyncio
async def test_invoke_code_reviewer_failure_writes_failed_block_without_raising(
    tmp_path: Path,
) -> None:
    """SDK exception path: runner returns failed result, writes a failed
    phase_5 block, preserves phase_4, and does NOT propagate the
    exception. The phase_4 preservation is critical — a flaky review
    must not roll back a successful test run.
    """
    _seed_task_markdown(tmp_path, _TASK_ID_OSI_005)
    seeded_phase_4 = {
        "status": "passed",
        "duration_seconds": 1.5,
        "error": None,
        "tests_run": 7,
        "tests_failed": 0,
        "coverage_pct": 81.0,
        "output_summary": "ok",
        "quality_gates_passed": True,
    }
    results_path = _seed_specialist_results_with_phase_4(
        tmp_path, _TASK_ID_OSI_005, seeded_phase_4
    )

    invoker = _make_fake_agent_invoker(
        invoke_side_effect=RuntimeError("SDK exploded"),
    )

    result = await invoke_code_reviewer(
        worktree_path=tmp_path,
        task_id=_TASK_ID_OSI_005,
        phase4_result=_make_passed_phase4_result(),
        sdk_timeout=42,
        agent_invoker=invoker,
    )

    assert result.status == "failed"
    assert result.error is not None
    assert "SDK exploded" in result.error
    # Cleanup invariant inherited from run_specialist.
    invoker._kill_child_claude_processes.assert_called_once()

    on_disk = json.loads(results_path.read_text(encoding="utf-8"))
    # phase_4 preserved verbatim — no rollback on Phase 5 failure.
    assert on_disk["phase_4"] == seeded_phase_4

    phase_5 = on_disk["phase_5"]
    assert phase_5["status"] == "failed"
    assert phase_5["error"] is not None
    assert "SDK exploded" in phase_5["error"]
    # Phase 5 placeholder fields still well-formed even on failure.
    assert phase_5["issues"] == []
    assert isinstance(phase_5["quality_score"], float)
    assert phase_5["recommendations"] == []
    assert isinstance(phase_5["output_summary"], str)


@pytest.mark.asyncio
async def test_invoke_code_reviewer_raises_value_error_when_phase_4_failed(
    tmp_path: Path,
) -> None:
    """Defensive guard: caller bug surfaces as ValueError, not as a
    silent phase_5 write keyed off a stale Phase 4 outcome. The SDK is
    NOT invoked and the on-disk specialist_results.json is NOT mutated.
    """
    _seed_task_markdown(tmp_path, _TASK_ID_OSI_005)
    seeded_phase_4 = {
        "status": "failed",
        "duration_seconds": 0.5,
        "error": "tests blew up",
        "tests_run": 0,
        "tests_failed": 0,
        "coverage_pct": 0.0,
        "output_summary": "",
        "quality_gates_passed": False,
    }
    results_path = _seed_specialist_results_with_phase_4(
        tmp_path, _TASK_ID_OSI_005, seeded_phase_4
    )
    invoker = _make_fake_agent_invoker()

    with pytest.raises(ValueError) as exc_info:
        await invoke_code_reviewer(
            worktree_path=tmp_path,
            task_id=_TASK_ID_OSI_005,
            phase4_result=_make_failed_phase4_result(),
            sdk_timeout=42,
            agent_invoker=invoker,
        )

    # Error message names the offending status so the caller can debug.
    assert "phase4_result.status" in str(exc_info.value)
    assert "passed" in str(exc_info.value)
    # SDK NOT invoked — guard runs before any side effect.
    invoker._invoke_with_role.assert_not_awaited()
    invoker._kill_child_claude_processes.assert_not_called()
    # On-disk file unchanged — no phase_5 block written.
    on_disk = json.loads(results_path.read_text(encoding="utf-8"))
    assert on_disk == {"phase_4": seeded_phase_4}
    assert "phase_5" not in on_disk


@pytest.mark.asyncio
async def test_invoke_code_reviewer_prompt_contains_phase_4_summary_string(
    tmp_path: Path,
) -> None:
    """AC (d): the prompt MUST contain the literal string "Phase 4 summary"
    when introspected. This is the single most important piece of context
    for the code-reviewer — without it the review is blind to test
    outcomes. Pinned as a separate test so future prompt edits can't
    silently drop the contract.
    """
    _seed_task_markdown(tmp_path, _TASK_ID_OSI_005)
    _seed_specialist_results_with_phase_4(tmp_path, _TASK_ID_OSI_005)
    invoker = _make_fake_agent_invoker()

    await invoke_code_reviewer(
        worktree_path=tmp_path,
        task_id=_TASK_ID_OSI_005,
        phase4_result=_make_passed_phase4_result(),
        sdk_timeout=42,
        agent_invoker=invoker,
    )

    invoker._invoke_with_role.assert_awaited_once()
    rendered_prompt = invoker._invoke_with_role.await_args.kwargs["prompt"]
    assert "Phase 4 summary" in rendered_prompt


# =============================================================================
# No-model-activity watchdog (TASK-FIX-SPECHANG2)
# =============================================================================
#
# The 600s duration cap (TASK-FIX-SPECHANG) bounds a hang but does not
# eliminate it. Run-9 turn-2 showed the test-orchestrator make zero
# /v1/responses calls for ~480s before the cap fired. The watchdog detects
# that no-model-activity gap and terminates with a distinct reason BEFORE the
# blunt cap, while a normally-progressing specialist (continuous activity)
# is never killed.


def test_no_activity_watchdog_exceeded_predicate() -> None:
    """Pure threshold predicate: gap >= threshold fires; disabled when <= 0."""
    # Gap exactly at threshold → exceeded.
    assert _no_activity_watchdog_exceeded(100.0, 250.0, 150.0) is True
    # Gap beyond threshold → exceeded.
    assert _no_activity_watchdog_exceeded(100.0, 300.0, 150.0) is True
    # Gap below threshold → not exceeded (AC-2: don't kill progressing run).
    assert _no_activity_watchdog_exceeded(100.0, 200.0, 150.0) is False
    # Watchdog disabled (0 or negative threshold) → never fires.
    assert _no_activity_watchdog_exceeded(0.0, 10_000.0, 0.0) is False
    assert _no_activity_watchdog_exceeded(0.0, 10_000.0, -1.0) is False


@pytest.mark.asyncio
async def test_run_specialist_watchdog_terminates_hung_specialist(
    tmp_path: Path,
) -> None:
    """AC-1/AC-3: a specialist that stops producing harness events (never
    refreshes the activity clock) is terminated with the distinct
    'hang detected (no model activity for Ns)' reason, and child processes
    are reaped — well before the long inner sleep would complete.
    """
    async def _hang(**_: object) -> None:
        # Simulate a genuine hang: no activity updates for far longer than
        # the watchdog window.
        await asyncio.sleep(10.0)

    invoker = _make_fake_agent_invoker(invoke_side_effect=_hang)

    started = time.monotonic()
    result = await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=600,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
        no_activity_watchdog_seconds=0.2,
    )
    elapsed = time.monotonic() - started

    assert result.status == "failed"
    assert result.error is not None
    assert "hang detected (no model activity" in result.error
    assert result.result_file is None
    # Terminated promptly — did NOT wait for the 10s inner sleep.
    assert elapsed < 5.0
    invoker._kill_child_claude_processes.assert_called_once()


@pytest.mark.asyncio
async def test_run_specialist_watchdog_allows_progressing_specialist(
    tmp_path: Path,
) -> None:
    """AC-2: a specialist that keeps refreshing the activity clock
    (continuous model calls) completes normally and is never killed by the
    watchdog.
    """
    async def _progressing(**_: object) -> None:
        # Refresh the activity clock faster than the watchdog window, the way
        # _invoke_with_role does on every harness event.
        for _ in range(8):
            invoker._last_activity_monotonic = time.monotonic()
            await asyncio.sleep(0.05)

    invoker = _make_fake_agent_invoker(invoke_side_effect=_progressing)

    result = await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=600,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
        no_activity_watchdog_seconds=0.2,
    )

    assert result.status == "passed"
    assert result.error is None
    assert result.result_file == (
        tmp_path / ".guardkit" / "autobuild" / "TASK-OSI-001" / "specialist_results.json"
    )
    invoker._kill_child_claude_processes.assert_not_called()


@pytest.mark.asyncio
async def test_run_specialist_watchdog_synthesises_and_restores_cancellation_event(
    tmp_path: Path,
) -> None:
    """When no cancellation_event is supplied, the watchdog synthesises one
    (so the in-flight _cancel_monitor can dispatch harness.cancel() + SIGTERM)
    and restores the invoker's original None afterwards.
    """
    seen: dict[str, object] = {}

    async def _capture_then_hang(**_: object) -> None:
        seen["event_during_call"] = invoker._cancellation_event
        await asyncio.sleep(10.0)

    invoker = _make_fake_agent_invoker(invoke_side_effect=_capture_then_hang)
    assert invoker._cancellation_event is None

    await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=600,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
        no_activity_watchdog_seconds=0.2,
    )

    # A real Event was installed for the duration of the call …
    assert isinstance(seen["event_during_call"], threading.Event)
    # … and it was set when the watchdog fired (cooperative cancel signal).
    assert seen["event_during_call"].is_set()
    # … and the invoker's original (None) is restored afterwards.
    assert invoker._cancellation_event is None


@pytest.mark.asyncio
async def test_invoke_test_orchestrator_wires_watchdog(
    tmp_path: Path, monkeypatch
) -> None:
    """AC-1 wiring: invoke_test_orchestrator runs the test-orchestrator under
    the watchdog, so a hung run is written to disk as a failed phase_4 block
    carrying the distinct hang reason.
    """
    _seed_task_markdown(tmp_path, _TASK_ID_OSI_004)
    monkeypatch.setattr(
        specialist_invocations,
        "_TEST_ORCHESTRATOR_NO_ACTIVITY_WATCHDOG_SECONDS",
        0.2,
    )

    async def _hang(**_: object) -> None:
        await asyncio.sleep(10.0)

    invoker = _make_fake_agent_invoker(invoke_side_effect=_hang)

    result = await invoke_test_orchestrator(
        worktree_path=tmp_path,
        task_id=_TASK_ID_OSI_004,
        sdk_timeout=600,
        agent_invoker=invoker,
    )

    assert result.status == "failed"
    assert "hang detected (no model activity" in (result.error or "")

    results_path = (
        tmp_path / ".guardkit" / "autobuild" / _TASK_ID_OSI_004 / "specialist_results.json"
    )
    on_disk = json.loads(results_path.read_text(encoding="utf-8"))
    assert on_disk["phase_4"]["status"] == "failed"
    assert "hang detected (no model activity" in on_disk["phase_4"]["error"]
