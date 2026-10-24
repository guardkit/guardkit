"""Step 1 of the factory simplification (24 October 2026).

Checks that refused good work become advice, bookkeeping never ends work, and
the approved part of a feature that did not finish reaches Forge on GuardKit's
stdout line as ``approved_head``. Real checks that ran and failed still block.

Network-free: tmp_path git repositories only.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator import task_work_scope
from guardkit.orchestrator.failing_test_feedback import SUITE_RECEIPT_KEY
from guardkit.orchestrator.feature_check import (
    STOPPED_BECAUSE_MARKER,
    completion_verdict,
)
from guardkit.orchestrator.feature_loader import FeatureLoader
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
    WaveExecutionResult,
    terminal_real_check_failed,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    QualityGateStatus,
)
from guardkit.orchestrator.task_work_scope import (
    approved_head,
    checkout_lease,
    register_fresh_checkout,
)
from guardkit.worktrees import Worktree


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "wt"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("start\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "start")
    register_fresh_checkout(root, _git(root, "rev-parse", "HEAD"))
    return root


def _approve_task_a(root: Path) -> str:
    with checkout_lease(root) as lease:
        lease.admit("TASK-A", "FEAT-S1")
        (root / "a.txt").write_text("a\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "task A")
        lease.checkpoint_completed()
    return _git(root, "rev-parse", "HEAD")


# ============================================================================
# 1. Advice instead of refusals
# ============================================================================


def _gates(**overrides) -> QualityGateStatus:
    values = dict(
        tests_passed=True,
        coverage_met=None,
        arch_review_passed=True,
        plan_audit_passed=True,
    )
    values.update(overrides)
    return QualityGateStatus(**values)


def test_unmeasured_coverage_passes_the_gate_with_advice() -> None:
    gates = _gates(coverage_met=None)
    assert gates.all_gates_passed is True
    advice = CoachValidator._unmeasured_coverage_advice(gates)
    assert [a["category"] for a in advice] == ["coverage_unknown"]
    assert advice[0]["severity"] == "should_fix"


def test_measured_low_coverage_still_fails_the_gate() -> None:
    gates = _gates(coverage_met=False)
    assert gates.all_gates_passed is False
    assert CoachValidator._unmeasured_coverage_advice(gates) == []


def test_high_plan_audit_passes_with_advice(tmp_path: Path) -> None:
    validator = CoachValidator(str(tmp_path))
    results = {
        "quality_gates": {"tests_passed": True, "coverage_met": True},
        "code_review": {"score": 90},
        "plan_audit": {
            "status": "violation",
            "severity": "high",
            "violations": 2,
            "extra_files": ["src/unplanned.py"],
        },
    }
    status = validator.verify_quality_gates(results)
    assert status.plan_audit_passed is True
    assert [a["category"] for a in status.advisories] == ["plan_audit"]
    assert status.advisories[0]["severity"] == "should_fix"
    assert "src/unplanned.py" in status.advisories[0]["description"]


def test_test_command_exit_zero_without_test_names_keeps_the_approval(
    tmp_path: Path,
) -> None:
    from guardkit.orchestrator.agent_invoker import AgentInvoker

    invoker = AgentInvoker.__new__(AgentInvoker)
    decision = {"decision": "approve", "rationale": "fine", "issues": []}
    independent = SimpleNamespace(
        signal_absent=True,
        check_could_not_run=False,
        exit_code=0,
        test_command="make test",
        test_output_summary="ok",
    )
    bundle = SimpleNamespace(independent_tests=independent)
    path = tmp_path / "coach_turn_1.json"
    path.write_text(json.dumps(decision))

    invoker._reconcile_absent_independent_test_signal(
        decision=decision,
        evidence_bundle=bundle,
        task_id="TASK-A",
        turn=1,
        coach_output_path=path,
    )

    assert decision["decision"] == "approve"
    assert [i["severity"] for i in decision["issues"]] == ["should_fix"]
    assert json.loads(path.read_text())["decision"] == "approve"


def test_missing_frontmatter_fields_are_advice(tmp_path: Path) -> None:
    from guardkit.orchestrator.feature_validator import validate_feature_preflight

    task_file = tmp_path / "tasks" / "TASK-A.md"
    task_file.parent.mkdir(parents=True)
    task_file.write_text("---\nid: TASK-A\ntitle: A\ntask_type: feature\n---\nbody\n")
    feature = SimpleNamespace(
        tasks=[SimpleNamespace(id="TASK-A", file_path="tasks/TASK-A.md")]
    )
    result = validate_feature_preflight(feature, tmp_path)
    assert result.is_valid
    assert [w.field for w in result.warnings] == ["complexity"]
    assert "default" in result.warnings[0].message


# ============================================================================
# 2. Bookkeeping never ends work
# ============================================================================


def test_a_moved_head_is_noted_not_fatal(repo: Path) -> None:
    with checkout_lease(repo) as lease:
        lease.admit("TASK-A", "FEAT-S1")
        (repo / "b.txt").write_text("b\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "the builder committed by itself")
        lease.verify()
        assert any("HEAD moved" in note for note in lease.notes)
    assert approved_head(repo) == _git(repo, "rev-parse", "HEAD")


def test_save_feature_never_raises(tmp_path: Path) -> None:
    blocker = tmp_path / "file-not-dir"
    blocker.write_text("x")
    feature = MagicMock()
    feature.id = "FEAT-S1"
    feature.file_path = blocker / "FEAT-S1.yaml"
    with patch.object(FeatureLoader, "_feature_to_dict", return_value={}):
        FeatureLoader.save_feature(feature, tmp_path)  # must not raise


def test_task_state_move_failure_keeps_the_real_path(tmp_path: Path) -> None:
    from guardkit.tasks.state_bridge import TaskStateBridge

    task_file = tmp_path / "tasks" / "backlog" / "TASK-A.md"
    task_file.parent.mkdir(parents=True)
    task_file.write_text("---\nid: TASK-A\nstatus: backlog\n---\n")
    (tmp_path / "tasks" / "design_approved").write_text("a file, not a folder")
    bridge = TaskStateBridge("TASK-A", tmp_path)
    assert bridge._move_task_to_state(task_file, "design_approved") == task_file
    assert task_file.exists()


def test_frontmatter_write_failure_does_not_raise(tmp_path: Path) -> None:
    from guardkit.tasks.state_bridge import TaskStateBridge

    bridge = TaskStateBridge("TASK-A", tmp_path)
    bridge._update_task_frontmatter(tmp_path / "missing.md", {"status": "x"})


def _feature_check_project(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path / "main"
    (repo_root / ".guardkit").mkdir(parents=True)
    (repo_root / ".guardkit" / "config.yaml").write_text(
        'toolchain:\n  test: "make test"\n  feature_check: "sh check.sh"\n'
    )
    worktree = tmp_path / "candidate"
    worktree.mkdir()
    return repo_root, worktree


def test_missing_whole_feature_receipt_is_advice(tmp_path: Path) -> None:
    repo_root, worktree = _feature_check_project(tmp_path)
    feature = SimpleNamespace(tasks=[], scenarios={})
    verdict = completion_verdict(
        repo_root=repo_root, worktree_root=worktree, feature=feature
    )
    assert verdict.blocks is False
    assert "no receipt" in verdict.reason


def test_failed_whole_feature_check_still_blocks(tmp_path: Path) -> None:
    from guardkit.orchestrator.feature_check import RECEIPT_RELATIVE_PATH

    repo_root, worktree = _feature_check_project(tmp_path)
    receipt = worktree / RECEIPT_RELATIVE_PATH
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({"status": "failed"}))
    feature = SimpleNamespace(tasks=[], scenarios={})
    verdict = completion_verdict(
        repo_root=repo_root, worktree_root=worktree, feature=feature
    )
    assert verdict.blocks is True


# ============================================================================
# 3. The task's terminal real test outcome
# ============================================================================


def _turn(report):
    return SimpleNamespace(coach_result=SimpleNamespace(report=report))


def test_last_turn_with_a_failed_test_run_counts() -> None:
    history = [_turn({SUITE_RECEIPT_KEY: {"command": "make test", "exit_code": 1}})]
    assert terminal_real_check_failed(history) is True


def test_red_test_fixed_on_the_last_turn_does_not_count() -> None:
    history = [
        _turn({SUITE_RECEIPT_KEY: {"command": "make test", "exit_code": 1}}),
        _turn({"validation_results": {"quality_gates": {"tests_passed": True}}}),
    ]
    assert terminal_real_check_failed(history) is False


def test_absent_test_signal_does_not_count() -> None:
    history = [
        _turn(
            {
                "validation_results": {
                    "independent_tests": {"signal_absent": True},
                    "quality_gates": {"tests_passed": None},
                }
            }
        )
    ]
    assert terminal_real_check_failed(history) is False


def test_measured_failing_test_phase_counts() -> None:
    history = [_turn({"validation_results": {"quality_gates": {"tests_passed": False}}})]
    assert terminal_real_check_failed(history) is True


# ============================================================================
# 4. approved_head: in memory, through finalisation, onto stdout
# ============================================================================


def test_b_fails_before_admission_keeps_a(repo: Path) -> None:
    head_a = _approve_task_a(repo)
    with checkout_lease(repo) as lease:
        lease.poison("Task TASK-B was refused before admission")
    assert approved_head(repo) == head_a


def test_b_scope_record_write_failure_keeps_a(repo: Path) -> None:
    head_a = _approve_task_a(repo)
    from guardkit.orchestrator.paths import TaskArtifactPaths

    with patch.object(
        TaskArtifactPaths, "private_artifact_path", side_effect=OSError("disk full")
    ):
        with checkout_lease(repo) as lease:
            scope = lease.admit("TASK-B", "FEAT-S1")
            assert scope.task_id == "TASK-B"
            lease.poison("Task TASK-B was not approved")
    assert approved_head(repo) == head_a


def _orchestrator(tmp_path: Path) -> FeatureOrchestrator:
    repo_root = tmp_path / "main"
    repo_root.mkdir(exist_ok=True)
    return FeatureOrchestrator(
        repo_root=repo_root, max_turns=1, worktree_manager=MagicMock(), quiet=True
    )


def _feature(statuses: dict):
    feature = MagicMock()
    feature.id = "FEAT-S1"
    feature.scenarios = {}
    tasks = []
    for task_id, status in statuses.items():
        task = MagicMock()
        task.id = task_id
        task.status = status
        tasks.append(task)
    feature.tasks = tasks
    return feature


def _waves(b_real_check_failed=False, smoke_passed=None):
    results = [
        TaskExecutionResult("TASK-A", True, 1, "approved"),
        TaskExecutionResult(
            "TASK-B", False, 2, "max_turns_exceeded",
            error="not approved", real_check_failed=b_real_check_failed,
        ),
    ]
    wave = WaveExecutionResult(
        wave_number=1, task_ids=["TASK-A", "TASK-B"], results=results,
        all_succeeded=False,
    )
    if smoke_passed is not None:
        wave.smoke_gate_result = SimpleNamespace(
            passed=smoke_passed, command="make smoke", stderr="",
            exit_code=0 if smoke_passed else 1, timed_out=False,
        )
    return [wave]


def _stop_lines(out: str):
    prefix = STOPPED_BECAUSE_MARKER + " "
    return [json.loads(l[len(prefix):]) for l in out.splitlines() if l.startswith(prefix)]


def _finalize(tmp_path, repo, waves, capsys, write_feature=None):
    orchestrator = _orchestrator(tmp_path)
    worktree = Worktree(
        task_id="FEAT-S1", branch_name="autobuild/FEAT-S1", path=repo,
        base_branch="main",
    )
    feature = _feature({"TASK-A": "completed", "TASK-B": "failed"})
    with patch.object(
        FeatureLoader, "_write_feature", side_effect=write_feature or (lambda *a: None)
    ):
        result = orchestrator._finalize_phase(feature, waves, worktree)
    return result, _stop_lines(capsys.readouterr().out)


def test_a_approved_b_failed_prints_a_commit(tmp_path, repo, capsys) -> None:
    head_a = _approve_task_a(repo)
    result, lines = _finalize(tmp_path, repo, _waves(), capsys)
    assert result.success is False
    assert [line["approved_head"] for line in lines] == [head_a]
    assert lines[0]["feature_id"] == "FEAT-S1" and lines[0]["sentence"]


def test_failing_record_writes_still_give_a_result(tmp_path, repo, capsys) -> None:
    head_a = _approve_task_a(repo)
    result, lines = _finalize(
        tmp_path, repo, _waves(), capsys, write_feature=OSError("read-only")
    )
    assert result.success is False
    assert [line["approved_head"] for line in lines] == [head_a]


def test_b_red_task_test_withholds_approved_head(tmp_path, repo, capsys) -> None:
    _approve_task_a(repo)
    _, lines = _finalize(tmp_path, repo, _waves(b_real_check_failed=True), capsys)
    assert lines == []


def test_red_smoke_check_withholds_approved_head(tmp_path, repo, capsys) -> None:
    _approve_task_a(repo)
    _, lines = _finalize(tmp_path, repo, _waves(smoke_passed=False), capsys)
    assert lines == []


def test_no_approved_task_prints_nothing(tmp_path, repo, capsys) -> None:
    _, lines = _finalize(tmp_path, repo, _waves(), capsys)
    assert lines == []
