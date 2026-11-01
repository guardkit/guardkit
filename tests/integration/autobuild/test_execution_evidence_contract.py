"""Real report writer -> persisted feedback contract.

The requirements gate these tests once drove (validate_requirements, promise
matching and the direct-mode evidence gate) was removed by the 27 October 2026
cull (628d22ac); its tests went with it.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.schemas import (
    CriterionVerification,
    format_verification_summary,
)


def test_known_and_malformed_typed_states_do_not_change_verification():
    values = [
        "verified",
        "rejected",
        "claimed",
        "pending",
        "unverified",
        "cannot_verify",
        {},
        "invented",
    ]
    served = {
        "validation_results": {
            "requirements": {
                "criteria_results": [
                    {"criterion_id": f"AC-{i}", "result": v}
                    for i, v in enumerate(values)
                ]
            }
        }
    }
    fallback = AutoBuildOrchestrator._criteria_verifications_from_report(served)
    rows = [CriterionVerification.from_dict(row) for row in fallback]
    assert [r.result.value for r in rows] == [
        "verified",
        "rejected",
        "claimed",
        "pending",
        "pending",
        "pending",
        "rejected",
        "rejected",
    ]
    assert "Unknown verification state" in rows[-1].notes
    summary = format_verification_summary(rows)
    assert "CLAIMED" in summary and "PENDING" in summary


def test_original_required_read_failure_is_first_feedback_and_not_timeout(tmp_path):
    task = "TASK-READ"
    invoker = AgentInvoker(worktree_path=tmp_path)
    report = {
        "original_failure": {
            "type": "SelectedSkillReadError",
            "message": "Read the declared document before execute",
            "phase": "player",
        },
        "files_created": [],
        "files_modified": [],
        "completion_promises": [],
    }
    invoker._write_recovered_task_work_failure(
        task, report, report["original_failure"]["message"]
    )
    receipt = json.loads(
        (tmp_path / ".guardkit/autobuild" / task / "task_work_results.json").read_text()
    )
    assert receipt["success"] is False and receipt["completed"] is False
    assert receipt["error_type"] == "SelectedSkillReadError"
    issues = AutoBuildOrchestrator._why_no_player_report_issues(task, 1, report)
    assert issues[0]["category"] == "player_execution_failure"
    assert "SelectedSkillReadError" in issues[0]["description"]


def test_nine_approved_one_deferred_finalizes_without_double_count(tmp_path):
    from pathlib import Path
    from unittest.mock import Mock
    from guardkit.orchestrator.feature_loader import (
        Feature,
        FeatureTask,
        FeatureOrchestration,
        FeatureExecution,
        FeatureLoader,
    )
    from guardkit.orchestrator.feature_orchestrator import (
        FeatureOrchestrator,
        TaskExecutionResult,
        WaveExecutionResult,
    )
    from guardkit.worktrees import Worktree

    tasks = [
        FeatureTask(
            id=f"TASK-{i}",
            name=f"task {i}",
            file_path=Path(f"tasks/TASK-{i}.md"),
            complexity=1,
            dependencies=[],
            status="completed" if i < 9 else "deferred",
        )
        for i in range(10)
    ]
    feature = Feature(
        id="FEAT-COUNT",
        name="counts",
        description="counts",
        created="2026-10-24",
        status="in_progress",
        complexity=1,
        estimated_tasks=10,
        tasks=tasks,
        orchestration=FeatureOrchestration(parallel_groups=[[t.id for t in tasks]]),
        execution=FeatureExecution(),
    )
    manager = Mock()
    orch = FeatureOrchestrator(
        repo_root=tmp_path, worktree_manager=manager, quiet=True, enable_context=False
    )
    worktree = Worktree("FEAT-COUNT", "main", tmp_path, "main")
    first = [
        TaskExecutionResult(
            task_id=t.id,
            success=True,
            total_turns=1 if i < 9 else 0,
            final_decision="approved" if i < 9 else "deferred",
        )
        for i, t in enumerate(tasks)
    ]
    # Duplicate earlier repair result cannot add another completed task.
    wave = WaveExecutionResult(
        wave_number=1,
        task_ids=[t.id for t in tasks],
        results=first + [first[0]],
        all_succeeded=True,
    )
    result = orch._finalize_phase(feature, [wave], worktree)
    assert result.success
    assert (result.tasks_completed, result.tasks_deferred) == (9, 1)
    saved = FeatureLoader._feature_to_dict(feature)
    assert saved["execution"]["tasks_completed"] == 9
    assert saved["execution"]["tasks_deferred"] == 1


def test_execute_turn_required_read_failure_recovers_scoped_partial_work(tmp_path):
    import subprocess
    from unittest.mock import MagicMock, Mock, AsyncMock
    from guardkit.orchestrator.agent_invoker import AgentInvocationResult
    from guardkit.orchestrator.task_work_scope import (
        register_fresh_checkout,
        checkout_lease,
    )

    subprocess.run(
        ["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True
    )
    for key, value in [
        ("user.name", "Fixture"),
        ("user.email", "fixture@example.invalid"),
    ]:
        subprocess.run(["git", "-C", str(tmp_path), "config", key, value], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "--allow-empty", "-m", "source"],
        check=True,
        capture_output=True,
    )
    pin = subprocess.check_output(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True
    ).strip()
    register_fresh_checkout(tmp_path, pin)
    task = "TASK-READ"
    criteria = ["AC-001: required behavior exists"]
    with checkout_lease(tmp_path) as lease:
        scope = lease.admit(task)
        invoker = AgentInvoker(worktree_path=tmp_path)
        invoker._get_implementation_mode = lambda _: "direct"

        async def player(**kwargs):
            (tmp_path / "partial.source").write_text("useful partial work")
            report = {
                "task_id": task,
                "files_created": ["partial.source"],
                "files_modified": [],
                "error_type": "SelectedSkillReadError",
            }
            invoker._write_direct_mode_results(
                task, report, success=False, error="required read missing"
            )
            return AgentInvocationResult(
                task_id=task,
                turn=1,
                agent_type="player",
                success=False,
                report=report,
                duration_seconds=0.0,
                error="required read missing",
            )

        invoker.invoke_player = AsyncMock(side_effect=player)
        orch = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=Mock(),
            agent_invoker=invoker,
            progress_display=MagicMock(),
            enable_pre_loop=False,
            enable_context=False,
            enable_checkpoints=False,
        )
        orch.task_work_scope = scope
        def coach(**kwargs):
            # The reviewer sends the turn back with nothing of its own to
            # add: the feedback must still carry the builder's own failure.
            return AgentInvocationResult(
                task_id=task,
                turn=1,
                agent_type="coach",
                success=True,
                report={"decision": "feedback", "issues": [], "rationale": ""},
                duration_seconds=0.0,
            )

        with patch.object(orch, "_invoke_coach_safely", side_effect=coach):
            record = orch._execute_turn(
                turn=1,
                task_id=task,
                requirements="implement behavior",
                worktree=SimpleNamespace(path=tmp_path),
                previous_feedback=None,
                acceptance_criteria=criteria,
                task_type="feature",
            )
        assert not record.player_result.success
        assert (
            record.player_result.report["_recovery_metadata"]["original_failure"][
                "type"
            ]
            == "SelectedSkillReadError"
        )
        assert "partial.source" in record.player_result.report["files_created"]
        assert record.feedback.count("SelectedSkillReadError") == 1
        assert "required read missing" in record.feedback
        orch._turn_history = [record]
        assert "SelectedSkillReadError" in orch._get_last_feedback()
