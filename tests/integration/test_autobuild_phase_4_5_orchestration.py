"""Pre-merge gate: orchestrator-side Phase 4/5 specialist invocation.

This test suite is the **load-bearing pre-merge gate** for FEAT-AB59
(orchestrator-side specialist invocation). It exercises the wiring that
TASK-OSI-006 added to ``AutoBuildOrchestrator._execute_turn`` (lines
~2625-2748 of ``guardkit/orchestrator/autobuild.py``):

    Player Phase 3 → invoke_test_orchestrator
                  → (if passed) invoke_code_reviewer
                  → _inject_specialist_records_into_task_work_results
                  → Coach reads merged task_work_results.json

The wiring's behaviour is verified deterministically with a stub SDK
(see ``tests/orchestrator/stub_sdk.py``) that records every
``claude_agent_sdk.query(...)`` call without sending traffic to the
Anthropic API. The on-disk ``task_work_results.json`` is asserted at the
end of each scenario — the file Coach actually reads in production.

The full ``_execute_turn`` is **not** invoked because it requires a
heavyweight ``AutoBuildOrchestrator`` setup (Player invocation, Coach
invocation, progress display, cancellation plumbing). Instead, a small
``_drive_orchestrator_phase_4_5`` helper replicates the wiring's
control-flow exactly. The helper is the unit under test — if production
wiring drifts away from this shape, this gate will pass while production
is broken; updates to ``autobuild.py:_execute_turn`` MUST be mirrored
here.

Coverage:
  - ``test_orchestrator_side_invocation_fires_on_non_direct_task``:
    happy path, both specialists called in order, validation passes.
  - ``test_direct_mode_task_skips_specialists``: ``implementation_mode:
    direct`` short-circuits the wiring before any specialist call.
  - ``test_phase4_failure_skips_phase5_and_records_partial``: stubbed
    test-orchestrator failure leaves Phase 5 uninvoked and the
    validation block reports a violation listing phase ``"5"``.
  - ``test_player_emitted_phase_4_markers_are_dropped``: a Player-tagged
    Phase 4 entry pre-populated in ``task_work_results.json`` is
    overwritten by the orchestrator-tagged entry during the merge step.

References:

* TASK-OSI-007 (this test).
* TASK-OSI-006 (turn-loop wiring).
* TASK-OSI-002 (gate-credit injection).
* TASK-REV-119C1 (review that scoped the redesign).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Add repo root to sys.path so guardkit imports resolve when pytest runs
# from a different cwd. Mirrors the convention in test_sdk_delegation.py.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.agent_invoker import AgentInvoker  # noqa: E402
from tests.orchestrator.stub_sdk import (  # noqa: E402
    StubSDKRecorder,
    build_mock_sdk_module,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


TASK_ID = "TASK-OSI-STUB"


def _write_task_markdown(
    worktree: Path,
    task_id: str,
    *,
    implementation_mode: str = "task-work",
) -> Path:
    """Create a minimal task markdown the runner can read for context."""
    task_dir = worktree / "tasks" / "in_progress"
    task_dir.mkdir(parents=True, exist_ok=True)
    task_file = task_dir / f"{task_id}-stub-fixture.md"
    task_file.write_text(
        (
            "---\n"
            f"id: {task_id}\n"
            "title: Stub Task\n"
            "status: in_progress\n"
            "priority: medium\n"
            f"implementation_mode: {implementation_mode}\n"
            "---\n\n"
            "# Task\n\n"
            "## Description\n\n"
            "Stub task used by the orchestrator-side Phase 4/5 test "
            "suite. Real-world behaviour is irrelevant — only the file "
            "needs to exist for `_load_task_context`.\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] Stub criterion (not asserted)\n"
        ),
        encoding="utf-8",
    )
    return task_file


def _write_initial_task_work_results(
    worktree: Path,
    task_id: str,
    *,
    extra_invocations: list[dict[str, Any]] | None = None,
) -> Path:
    """Pre-populate ``task_work_results.json`` with a Phase 3 entry.

    The injector preserves non-Phase-4/5 entries verbatim, so a Phase 3
    record here represents the Player's completed implementation work.
    Tests that need to verify Player-emitted Phase 4 dedup pass an extra
    invocation via ``extra_invocations``.
    """
    autobuild_dir = worktree / ".guardkit" / "autobuild" / task_id
    autobuild_dir.mkdir(parents=True, exist_ok=True)
    results_path = autobuild_dir / "task_work_results.json"

    invocations: list[dict[str, Any]] = [
        {
            "phase": "3",
            "agent": "python-api-specialist",
            "status": "completed",
        }
    ]
    if extra_invocations:
        invocations.extend(extra_invocations)

    payload = {
        "task_id": task_id,
        "workflow_mode": "implement-only",
        "agent_invocations": invocations,
        "files_created": ["src/example.py"],
        "files_modified": [],
    }
    results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return results_path


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """A fresh worktree-shaped tmp dir with a task markdown + Phase 3 result."""
    _write_task_markdown(tmp_path, TASK_ID)
    _write_initial_task_work_results(tmp_path, TASK_ID)
    return tmp_path


@pytest.fixture
def agent_invoker(worktree: Path) -> AgentInvoker:
    """``AgentInvoker`` rooted at the test worktree."""
    return AgentInvoker(
        worktree_path=worktree,
        max_turns_per_agent=5,
        sdk_timeout_seconds=10,
        use_task_work_delegation=False,
        development_mode="standard",
    )


# ---------------------------------------------------------------------------
# Helper: replicate autobuild.py:_execute_turn lines 2625-2748 wiring.
# ---------------------------------------------------------------------------


async def _drive_orchestrator_phase_4_5(
    worktree_path: Path,
    task_id: str,
    agent_invoker: AgentInvoker,
) -> None:
    """Replicate the orchestrator-side Phase 4/5 wiring under test.

    This MUST mirror the control-flow inside ``_execute_turn`` lines
    ~2625-2748. If production wiring changes (e.g. budget guard
    semantics), update this helper accordingly — the gate's value
    depends on it.

    Reads ``implementation_mode`` from the task markdown via the same
    helper the production wiring uses (``_get_implementation_mode``)
    rather than taking it as a parameter, so the impl_mode branch is
    exercised for real instead of mocked.
    """
    from guardkit.orchestrator import specialist_invocations as _si

    impl_mode = agent_invoker._get_implementation_mode(task_id)

    if impl_mode == "direct":
        # Production wiring's early skip — no specialist invocation,
        # no injector call. Coach's gate handling for direct mode is
        # covered by other tests.
        return

    phase4_result = await _si.invoke_test_orchestrator(
        worktree_path=worktree_path,
        task_id=task_id,
        sdk_timeout=agent_invoker.sdk_timeout_seconds,
        agent_invoker=agent_invoker,
    )

    if phase4_result.status == "passed":
        await _si.invoke_code_reviewer(
            worktree_path=worktree_path,
            task_id=task_id,
            phase4_result=phase4_result,
            sdk_timeout=agent_invoker.sdk_timeout_seconds,
            agent_invoker=agent_invoker,
        )
    else:
        # Phase 4 failed/skipped — write the phase_5 skipped block the
        # production wiring writes when invoke_code_reviewer is bypassed.
        specialist_results_path = (
            worktree_path / ".guardkit" / "autobuild" / task_id
            / "specialist_results.json"
        )
        _si._merge_specialist_block(
            specialist_results_path,
            "phase_5",
            {
                "status": "skipped",
                "duration_seconds": 0.0,
                "error": f"phase_4 status={phase4_result.status}",
                **_si._PHASE_5_AGENT_FIELD_DEFAULTS,
            },
        )

    # Always run the gate-credit injector (TASK-OSI-002) so Coach reads
    # an up-to-date task_work_results.json.
    agent_invoker._inject_specialist_records_into_task_work_results(task_id)


def _read_task_work_results(worktree: Path, task_id: str) -> dict[str, Any]:
    """Load ``task_work_results.json`` from the autobuild dir."""
    path = (
        worktree / ".guardkit" / "autobuild" / task_id
        / "task_work_results.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_orchestrator_side_invocation_fires_on_non_direct_task(
    worktree: Path,
    agent_invoker: AgentInvoker,
) -> None:
    """Happy path: both specialists fire in order, validation passes.

    Asserts every contract the wiring promises Coach:

    * Exactly one ``test-orchestrator`` invocation.
    * Followed by exactly one ``code-reviewer`` invocation.
    * Each specialist receives the documented ``allowed_tools`` list.
    * After the merge, ``agent_invocations_validation.status`` is
      ``"passed"`` and ``missing_phases`` is empty.
    """
    recorder = StubSDKRecorder(worktree, TASK_ID)
    mock_sdk = build_mock_sdk_module(recorder)

    with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
        await _drive_orchestrator_phase_4_5(worktree, TASK_ID, agent_invoker)

    # Specialist invocation order — phase_4 before phase_5.
    assert len(recorder.invocations) == 2, (
        f"expected exactly two SDK calls, got "
        f"{len(recorder.invocations)}: {recorder.invocations!r}"
    )
    assert recorder.invocations[0].agent_type == "test-orchestrator"
    assert recorder.invocations[1].agent_type == "code-reviewer"

    # Allowed-tools per specialist, per the OSI-004/005 contract.
    assert recorder.invocations[0].allowed_tools == [
        "Read", "Write", "Bash", "Search"
    ]
    assert recorder.invocations[1].allowed_tools == [
        "Read", "Search", "Grep"
    ]

    # Validation gate verdict on the merged ledger.
    results = _read_task_work_results(worktree, TASK_ID)
    validation = results["agent_invocations_validation"]
    assert validation["status"] == "passed", (
        f"validation status was {validation['status']!r}, "
        f"violation_message={validation.get('violation_message')!r}"
    )
    assert validation["missing_phases"] == []


@pytest.mark.integration
async def test_direct_mode_task_skips_specialists(
    tmp_path: Path,
) -> None:
    """``implementation_mode: direct`` blocks all specialist invocation.

    The task markdown is rewritten with ``implementation_mode: direct``
    and a fresh ``task_work_results.json`` is produced so the Phase 3
    record is preserved. After driving the wiring, the recorder must
    show zero SDK calls — neither test-orchestrator nor code-reviewer.
    """
    _write_task_markdown(tmp_path, TASK_ID, implementation_mode="direct")
    _write_initial_task_work_results(tmp_path, TASK_ID)
    invoker = AgentInvoker(
        worktree_path=tmp_path,
        max_turns_per_agent=5,
        sdk_timeout_seconds=10,
        use_task_work_delegation=False,
        development_mode="standard",
    )

    recorder = StubSDKRecorder(tmp_path, TASK_ID)
    mock_sdk = build_mock_sdk_module(recorder)

    with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
        await _drive_orchestrator_phase_4_5(tmp_path, TASK_ID, invoker)

    test_orch_calls = [
        inv for inv in recorder.invocations
        if inv.agent_type == "test-orchestrator"
    ]
    code_reviewer_calls = [
        inv for inv in recorder.invocations
        if inv.agent_type == "code-reviewer"
    ]
    assert test_orch_calls == [], (
        f"direct-mode task triggered test-orchestrator: {test_orch_calls!r}"
    )
    assert code_reviewer_calls == [], (
        f"direct-mode task triggered code-reviewer: {code_reviewer_calls!r}"
    )


@pytest.mark.integration
async def test_phase4_failure_skips_phase5_and_records_partial(
    worktree: Path,
    agent_invoker: AgentInvoker,
) -> None:
    """Phase 4 SDK failure leaves Phase 5 uninvoked; validator flags ``"5"``.

    The recorder is configured to raise inside the test-orchestrator
    call. ``run_specialist`` catches the exception and returns
    ``status="failed"``; the wiring then writes a ``phase_5`` skipped
    block instead of invoking the code-reviewer. The validator's
    ``missing_phases`` MUST list ``"5"`` so Coach blocks the turn.
    """
    recorder = StubSDKRecorder(
        worktree, TASK_ID, fail_test_orchestrator=True
    )
    mock_sdk = build_mock_sdk_module(recorder)

    with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
        await _drive_orchestrator_phase_4_5(worktree, TASK_ID, agent_invoker)

    # The code-reviewer must NOT have been called.
    code_reviewer_calls = [
        inv for inv in recorder.invocations
        if inv.agent_type == "code-reviewer"
    ]
    assert code_reviewer_calls == [], (
        f"code-reviewer fired despite phase_4 failure: {code_reviewer_calls!r}"
    )

    # The validator must record a violation naming phase 5.
    results = _read_task_work_results(worktree, TASK_ID)
    validation = results["agent_invocations_validation"]
    assert validation["status"] == "violation", (
        f"expected status='violation', got {validation['status']!r}"
    )
    assert "5" in validation["missing_phases"], (
        f"expected '5' in missing_phases, got "
        f"{validation['missing_phases']!r}"
    )


@pytest.mark.integration
async def test_player_emitted_phase_4_markers_are_dropped(
    tmp_path: Path,
) -> None:
    """Player-tagged Phase 4 entry is replaced by the orchestrator-tagged one.

    Pre-populates ``task_work_results.json`` with a Phase 4 entry that
    has no ``source`` field (i.e. Player-emitted). After the injector
    runs, the merged ledger must contain exactly one Phase 4 entry, and
    that entry must be the orchestrator's
    (``source == "orchestrator"``).
    """
    _write_task_markdown(tmp_path, TASK_ID)
    _write_initial_task_work_results(
        tmp_path,
        TASK_ID,
        extra_invocations=[
            # Player's discretionary Phase 4 marker — no `source` tag.
            {
                "phase": "4",
                "agent": "test-orchestrator",
                "status": "completed",
            },
        ],
    )
    invoker = AgentInvoker(
        worktree_path=tmp_path,
        max_turns_per_agent=5,
        sdk_timeout_seconds=10,
        use_task_work_delegation=False,
        development_mode="standard",
    )

    recorder = StubSDKRecorder(tmp_path, TASK_ID)
    mock_sdk = build_mock_sdk_module(recorder)

    with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
        await _drive_orchestrator_phase_4_5(tmp_path, TASK_ID, invoker)

    results = _read_task_work_results(tmp_path, TASK_ID)
    invocations = results["agent_invocations"]

    phase_4_entries = [
        inv for inv in invocations if str(inv.get("phase")) == "4"
    ]
    assert len(phase_4_entries) == 1, (
        f"expected exactly one Phase 4 entry after dedup, got "
        f"{len(phase_4_entries)}: {phase_4_entries!r}"
    )
    assert phase_4_entries[0].get("source") == "orchestrator", (
        f"surviving Phase 4 entry was not orchestrator-tagged: "
        f"{phase_4_entries[0]!r}"
    )
