"""Producer-side: orchestrator-invoked Phase 4/5 records merge cleanly.

TASK-OSI-002 adds ``AgentInvoker._inject_specialist_records_into_task_work_results``
so the agent-invocations validation gate credits orchestrator-invoked
specialists (Phase 4 test-orchestrator, Phase 5 code-reviewer) the same way
it credits Player-invoked phases. This test pins the contract surface:

1. Empty starting ledger → orchestrator records inserted, validation passes
   for ``workflow_mode == "implement-only"``.
2. Stale Player-emitted Phase 4/5 entries → dropped during merge,
   orchestrator entries replace them (no double-count).
3. ``workflow_mode == "direct"`` → Phase 3 only is expected, so a missing
   ``specialist_results.json`` produces no false Phase 4/5 violation.
4. Absent ``specialist_results.json`` → method records skipped Phase 4/5
   entries and a structured validation block; never raises.

The companion seam test pins the JSON contract from the producer
(TASK-OSI-004) so the integration boundary stays explicit.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.paths import TaskArtifactPaths


TASK_ID = "TASK-OSI-002-TEST"


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """Isolated worktree root for the producer-side writes."""
    return tmp_path


@pytest.fixture
def invoker(worktree: Path) -> AgentInvoker:
    return AgentInvoker(worktree_path=worktree)


def _seed_task_work_results(
    worktree: Path,
    *,
    agent_invocations: list | None = None,
    workflow_mode: str | None = None,
) -> Path:
    """Write a minimal task_work_results.json the merge can read."""
    TaskArtifactPaths.ensure_autobuild_dir(TASK_ID, worktree)
    results_path = TaskArtifactPaths.task_work_results_path(TASK_ID, worktree)
    payload: dict = {
        "task_id": TASK_ID,
        "completed": True,
        "files_modified": [],
        "files_created": [],
    }
    if agent_invocations is not None:
        payload["agent_invocations"] = agent_invocations
    if workflow_mode is not None:
        payload["workflow_mode"] = workflow_mode
    results_path.write_text(json.dumps(payload, indent=2))
    return results_path


def _seed_specialist_results(
    worktree: Path,
    *,
    phase_4: dict | None = None,
    phase_5: dict | None = None,
) -> Path:
    """Write the specialist_results.json contract from TASK-OSI-004."""
    autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(TASK_ID, worktree)
    specialist_path = autobuild_dir / "specialist_results.json"
    payload: dict = {}
    if phase_4 is not None:
        payload["phase_4"] = phase_4
    if phase_5 is not None:
        payload["phase_5"] = phase_5
    specialist_path.write_text(json.dumps(payload, indent=2))
    return specialist_path


def _passed_phase_block(duration: float) -> dict:
    return {
        "status": "passed",
        "duration_seconds": duration,
        "error": None,
    }


class TestMergeWithoutPriorPhase45Entries:
    """AC (a): merge into a ledger that has no prior Phase 4/5 entries."""

    def test_inserts_orchestrator_records_and_passes_gate(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # Player ran Phase 3 only (implement-only would expect 3/4/5).
        _seed_task_work_results(
            worktree,
            agent_invocations=[
                {"phase": "3", "agent": "player-implementer", "status": "completed"},
            ],
        )
        _seed_specialist_results(
            worktree,
            phase_4=_passed_phase_block(142.3),
            phase_5=_passed_phase_block(38.1),
        )

        results_path = invoker._inject_specialist_records_into_task_work_results(
            TASK_ID
        )

        assert results_path is not None
        on_disk = json.loads(results_path.read_text())

        invocations = on_disk["agent_invocations"]
        # Player Phase 3 preserved + orchestrator Phase 4/5 appended.
        assert len(invocations) == 3
        phases = {(inv["phase"], inv.get("source")) for inv in invocations}
        assert ("3", None) in phases  # Player entry untouched
        assert ("4", "orchestrator") in phases
        assert ("5", "orchestrator") in phases

        # Both orchestrator entries are completed (status: passed → completed).
        orchestrator_entries = [i for i in invocations if i.get("source") == "orchestrator"]
        assert {e["status"] for e in orchestrator_entries} == {"completed"}
        # Duration carried through from the specialist block.
        durations = {e["phase"]: e["duration_seconds"] for e in orchestrator_entries}
        assert durations == {"4": 142.3, "5": 38.1}

        # Gate sees 3 completed invocations against 3 expected for
        # implement-only → passed.
        gate = on_disk["agent_invocations_validation"]
        assert gate["status"] == "passed"
        assert gate["expected_phases"] == 3
        assert gate["actual_invocations"] == 3
        assert gate["missing_phases"] == []


class TestStalePlayerEntriesAreDropped:
    """AC (b): stale Player-emitted Phase 4/5 entries are deduped during merge."""

    def test_player_phase45_entries_replaced_by_orchestrator_records(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # Player falsely claims Phase 4 and 5 completed (no source tag,
        # which is the structural fingerprint of a Player-emitted entry).
        _seed_task_work_results(
            worktree,
            agent_invocations=[
                {"phase": "3", "agent": "player-implementer", "status": "completed"},
                {"phase": "4", "agent": "player-claim-tests", "status": "completed"},
                {"phase": "5", "agent": "player-claim-review", "status": "completed"},
            ],
        )
        _seed_specialist_results(
            worktree,
            phase_4=_passed_phase_block(75.5),
            phase_5=_passed_phase_block(22.7),
        )

        results_path = invoker._inject_specialist_records_into_task_work_results(
            TASK_ID
        )

        assert results_path is not None
        on_disk = json.loads(results_path.read_text())

        invocations = on_disk["agent_invocations"]
        # Phase 3 retained; Phase 4/5 deduped to one orchestrator entry each.
        phase_counts: dict = {}
        for inv in invocations:
            phase_counts.setdefault(inv["phase"], []).append(inv)
        assert len(phase_counts["3"]) == 1, "Phase 3 should be preserved"
        assert len(phase_counts["4"]) == 1, (
            "stale Player Phase 4 entry must be dropped, not duplicated"
        )
        assert len(phase_counts["5"]) == 1, (
            "stale Player Phase 5 entry must be dropped, not duplicated"
        )
        assert phase_counts["4"][0]["source"] == "orchestrator"
        assert phase_counts["5"][0]["source"] == "orchestrator"
        # The replacement carries the orchestrator agent name, not the
        # Player's claimed name.
        assert phase_counts["4"][0]["agent"] == "test-orchestrator"
        assert phase_counts["5"][0]["agent"] == "code-reviewer"

        # Player entries explicitly tagged source: "player" are also dropped.
    def test_explicit_player_source_tag_also_dropped(
        self, invoker: AgentInvoker, worktree: Path
    ):
        _seed_task_work_results(
            worktree,
            agent_invocations=[
                {"phase": "3", "agent": "player", "status": "completed"},
                {
                    "phase": "4",
                    "agent": "player-claim",
                    "status": "completed",
                    "source": "player",
                },
            ],
        )
        _seed_specialist_results(
            worktree, phase_4=_passed_phase_block(10.0), phase_5=_passed_phase_block(5.0)
        )

        results_path = invoker._inject_specialist_records_into_task_work_results(
            TASK_ID
        )
        assert results_path is not None
        on_disk = json.loads(results_path.read_text())
        sources_for_phase_4 = [
            inv.get("source")
            for inv in on_disk["agent_invocations"]
            if inv["phase"] == "4"
        ]
        assert sources_for_phase_4 == ["orchestrator"]


class TestDirectModeBypass:
    """AC (c): workflow_mode == "direct" expects Phase 3 only — no false violation."""

    def test_direct_mode_passes_with_phase_3_only_and_no_specialist_file(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # Direct-mode task — Player ran Phase 3, no specialist file written.
        _seed_task_work_results(
            worktree,
            agent_invocations=[
                {"phase": "3", "agent": "direct-mode-impl", "status": "completed"},
            ],
            workflow_mode="direct",
        )
        # NOTE: no _seed_specialist_results call — file is intentionally absent.

        results_path = invoker._inject_specialist_records_into_task_work_results(
            TASK_ID
        )

        assert results_path is not None
        on_disk = json.loads(results_path.read_text())

        gate = on_disk["agent_invocations_validation"]
        # Direct mode expects Phase 3 only; Phase 4/5 skipped records are
        # present in the ledger but don't count as completed — and don't
        # need to, because the expected count is 1.
        assert gate["status"] == "passed", (
            "direct-mode Phase 3 ledger must not trigger a Phase 4/5 violation"
        )
        assert gate["expected_phases"] == 1
        # actual_invocations counts only "completed"; skipped Phase 4/5
        # records do not inflate the count.
        assert gate["actual_invocations"] == 1
        assert gate["missing_phases"] == []


class TestAbsentSpecialistResultsProducesStructuredBlock:
    """AC (d): missing specialist_results.json → structured block, never raises."""

    def test_absent_file_yields_skipped_records_and_structured_validation(
        self, invoker: AgentInvoker, worktree: Path
    ):
        _seed_task_work_results(
            worktree,
            agent_invocations=[
                {"phase": "3", "agent": "player-implementer", "status": "completed"},
            ],
        )
        # No _seed_specialist_results call — the file is absent.

        # Method must not raise.
        results_path = invoker._inject_specialist_records_into_task_work_results(
            TASK_ID
        )

        assert results_path is not None, (
            "method must rewrite task_work_results even without specialist file"
        )
        on_disk = json.loads(results_path.read_text())

        # Phase 4 and 5 entries inserted as skipped, tagged orchestrator,
        # carry an explanatory error message.
        invocations = on_disk["agent_invocations"]
        skipped_phases = {
            inv["phase"]
            for inv in invocations
            if inv.get("source") == "orchestrator" and inv["status"] == "skipped"
        }
        assert skipped_phases == {"4", "5"}
        for inv in invocations:
            if inv.get("source") == "orchestrator":
                assert inv.get("error"), (
                    "skipped orchestrator records must explain why they're skipped"
                )

        # Validation block is structured (one of the four documented
        # statuses) — never an exception.
        gate = on_disk["agent_invocations_validation"]
        assert gate["status"] in {"passed", "violation", "no_data", "validator_error"}
        # implement-only expects 3 completed invocations; only Phase 3 is
        # completed → violation block names the missing phases.
        assert gate["status"] == "violation"
        assert set(gate["missing_phases"]) == {"4", "5"}


class TestNoTaskWorkResultsFile:
    """Robustness: no task_work_results.json → returns None, never raises."""

    def test_returns_none_when_results_file_absent(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # Don't seed anything. Method must handle absence quietly.
        result = invoker._inject_specialist_records_into_task_work_results(
            TASK_ID
        )
        assert result is None


# -------- Seam test: producer→consumer JSON contract (TASK-OSI-004) --------

@pytest.mark.seam
@pytest.mark.integration_contract("SPECIALIST_RESULTS_JSON")
def test_specialist_results_json_format(tmp_path: Path):
    """Verify specialist_results.json matches the expected format.

    Contract: JSON object with phase_4 and phase_5 keys; each block has
              status/duration_seconds/error and phase-specific output fields.
    Producer: TASK-OSI-004 (test-orchestrator runner) and TASK-OSI-005
              (code-reviewer runner).
    """
    autobuild_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-TEST-001"
    autobuild_dir.mkdir(parents=True)
    results_file = autobuild_dir / "specialist_results.json"
    results_file.write_text(json.dumps({
        "phase_4": {
            "status": "passed",
            "duration_seconds": 142.3,
            "error": None,
            "tests_run": 45,
            "tests_failed": 0,
            "coverage_pct": 87.0,
        },
        "phase_5": {
            "status": "passed",
            "duration_seconds": 38.1,
            "error": None,
            "issues": [],
            "quality_score": 8.5,
        },
    }))

    data = json.loads(results_file.read_text())
    assert "phase_4" in data, "specialist_results.json must contain phase_4 block"
    assert "phase_5" in data, "specialist_results.json must contain phase_5 block"
    for block_name in ("phase_4", "phase_5"):
        block = data[block_name]
        assert "status" in block, f"{block_name} must have status field"
        assert block["status"] in ("passed", "failed", "skipped"), \
            f"{block_name}.status must be passed/failed/skipped"
        assert "duration_seconds" in block, f"{block_name} must have duration_seconds"
