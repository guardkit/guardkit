"""Connected R1 regressions: aliases, command lifetime, markers and claims.

Only temporary Git repositories, deterministic fakes and owned Python children.
"""

import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from guardkit.orchestrator import process_group, task_work_scope
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.coach_verification import CoachVerifier
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.state_detection import detect_test_results
from guardkit.orchestrator.task_work_scope import (
    checkout_lease,
    current_lease,
    ScopeUnavailable,
)

_spec = importlib.util.spec_from_file_location(
    "execution_scope_test_helpers",
    Path(__file__).with_name("test_execution_scope_contract.py"),
)
_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helpers)


@pytest.mark.parametrize(
    "statuses",
    [("complete", "partial"), ("partial", "complete"), ("complete", "incomplete")],
)
@pytest.mark.parametrize("partial_has_text", [True, False])
def test_writer_and_validator_keep_natural_alias_noncompletion(
    tmp_path, statuses, partial_has_text
):
    root = _helpers.repository(tmp_path / "repo")
    criterion = "AC-NAMED-01: implemented"
    rows = []
    for status in statuses:
        row = {"criterion_id": "AC-001", "status": status, "evidence": status}
        if status == "complete" or partial_has_text:
            row["criterion_text"] = criterion
        rows.append(row)
    with checkout_lease(root) as lease:
        lease.admit("TASK-ALIASES")
        invoker = AgentInvoker(worktree_path=root)
        report = {
            "task_id": "TASK-ALIASES",
            "files_created": [],
            "files_modified": [],
            "tests_written": [],
            "requirements_addressed": [criterion],
            "completion_promises": rows,
        }
        invoker._write_player_report_for_direct_mode("TASK-ALIASES", 1, report)
        invoker._write_direct_mode_results("TASK-ALIASES", report, success=True)
        validator = CoachValidator(str(root), task_id="TASK-ALIASES")
        written = validator.read_quality_gate_results("TASK-ALIASES")
        result = validator.validate_requirements(
            {"acceptance_criteria": [criterion]}, written, turn=1
        )
        assert result.criteria_met == 0
        assert result.missing == [criterion]
        assert result.criteria_results[0].completion_status in {"partial", "incomplete"}


@pytest.mark.parametrize("reverse", [False, True])
def test_numeric_text_fallback_cannot_hide_explicit_noncompletion(tmp_path, reverse):
    validator = CoachValidator(str(tmp_path))
    rows = [
        {"criterion_id": "AC-001", "status": "partial"},
        {
            "criterion_id": "AC-OTHER",
            "criterion_text": "AC-1: implemented",
            "status": "complete",
        },
    ]
    result = validator._match_by_promises(
        ["AC-1: implemented"], list(reversed(rows)) if reverse else rows
    )
    assert result.criteria_met == 0
    assert result.criteria_results[0].completion_status == "partial"


def _task_runner(root, callback):
    runner = FeatureOrchestrator.__new__(FeatureOrchestrator)
    runner._evidence_repos_resolved = []
    runner._timeout_fence_is_set = lambda: False
    runner._update_task_started = lambda *args: None
    entered = []

    def owned(task, feature, worktree, **kwargs):
        entered.append(task.id)
        callback()
        return TaskExecutionResult(
            task_id=task.id, success=True, total_turns=1, final_decision="approved"
        )

    runner._execute_task_owned = owned
    return runner, entered


def _execute(runner, root, task_id):
    return runner._execute_task(
        SimpleNamespace(id=task_id),
        SimpleNamespace(id="FEAT"),
        SimpleNamespace(path=root),
    )


@pytest.mark.parametrize("consumer", ["runtime", "independent", "recovery"])
def test_unknown_child_blocks_approval_and_successor_through_real_consumers(
    tmp_path, monkeypatch, consumer
):
    import guardkit.orchestrator.quality_gates.coach_validator as cv
    import guardkit.orchestrator.project_command_env as command_env

    root = _helpers.repository(tmp_path / "repo")
    children = []

    def unknown(*args, **kwargs):
        children.append(
            subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        )
        raise process_group.CleanupUnavailableError("fixture child termination unknown")

    monkeypatch.setattr(process_group, "run_project_command", unknown)
    monkeypatch.setattr(cv, "_checker_env", lambda *args, **kwargs: {})
    monkeypatch.setattr(cv, "_checker_declared_env", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        command_env, "main_checkout_environment", lambda *args, **kwargs: {}
    )
    validator = CoachValidator(
        str(root),
        smoke_command="fixture",
        test_command="fixture",
        wave_size=1,
        coach_test_execution="subprocess",
    )

    def check():
        if consumer == "runtime":
            assert validator._gather_runtime_parity().ran is False
        elif consumer == "independent":
            assert validator.run_independent_tests().tests_passed is False
        else:
            result = detect_test_results(root, "TASK-A", 1)
            assert result.tests_passed is False
            assert "fixture child termination unknown" in result.error

    runner, entered = _task_runner(root, check)
    try:
        first = _execute(runner, root, "TASK-A")
        assert len(children) == 1
        assert children[0].poll() is None
        assert first.success is False
        assert "CleanupUnavailableError" in first.error
        second = _execute(runner, root, "TASK-B")
        assert second.success is False
        assert entered == ["TASK-A"]
        assert current_lease() is None
    finally:
        for child in children:
            child.terminate()
            child.wait(timeout=5)


@pytest.mark.parametrize("entrypoint", ["run_project_command", "run_in_own_group"])
def test_command_boundary_preserves_typed_cleanup_failure_before_advisory_catch(
    tmp_path, monkeypatch, entrypoint
):
    root = _helpers.repository(tmp_path / "repo")
    children = []
    failure = process_group.CleanupUnavailableError("fixture cleanup unavailable")

    def interrupted(proc, *args, **kwargs):
        children.append(proc)
        raise failure

    monkeypatch.setattr(process_group, "_check_capability", lambda: None)
    monkeypatch.setattr(process_group, "_run", interrupted)
    try:
        with checkout_lease(root) as lease:
            lease.admit("TASK-CHILD")
            with pytest.raises(process_group.CleanupUnavailableError) as caught:
                getattr(process_group, entrypoint)(
                    [sys.executable, "-c", "import time; time.sleep(30)"],
                    cwd=root,
                    env={},
                    timeout=5,
                )
            assert caught.value is failure
            assert children[0].poll() is None
            assert "CleanupUnavailableError" in lease.failure
            # An advisory catcher cannot launch another command afterwards.
            with pytest.raises(ScopeUnavailable):
                process_group.run_project_command("ignored", cwd=root, env={})
            assert len(children) == 1
        with pytest.raises(ScopeUnavailable):
            with checkout_lease(root):
                pass
    finally:
        for child in children:
            child.terminate()
            child.wait(timeout=5)
            for stream in (child.stdout, child.stderr):
                if stream:
                    stream.close()


@pytest.mark.parametrize("operation", ["write_text", "unlink"])
@pytest.mark.parametrize("fail_member", [0, 1])
def test_marker_failure_unwinds_and_denies_complete_sibling_footprint(
    tmp_path, monkeypatch, operation, fail_member
):
    sibling = _helpers.repository(tmp_path / "sibling")
    root, repos = _helpers.fresh_with_sibling(
        tmp_path / "source", sibling, "FEAT-MARKER"
    )
    original = getattr(Path, operation)
    calls = []
    failure = OSError("fixture marker I/O failure")

    def fail_once(path, *args, **kwargs):
        if path.name == "guardkit-writer-unsettled":
            calls.append(path)
            if len(calls) == fail_member + 1:
                raise failure
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, operation, fail_once)
    with pytest.raises(OSError) as caught:
        with checkout_lease(root, repos) as lease:
            lease.admit("TASK-MARKER")
    assert caught.value is failure
    assert current_lease() is None
    for member in (root, sibling):
        _, git_dir = task_work_scope.identity(member)
        assert task_work_scope._locks[str(git_dir)].locked() is False
        assert (
            "fixture marker I/O failure"
            in task_work_scope._history[str(git_dir)]["failed"]
        )
        assert (git_dir / "guardkit-writer-unsettled").exists()
    with pytest.raises(ScopeUnavailable):
        with checkout_lease(root, repos):
            pass
    with pytest.raises(ScopeUnavailable):
        with checkout_lease(sibling):
            pass


def test_marker_setup_error_cannot_reenter_unlocked_normal_task(tmp_path, monkeypatch):
    root = _helpers.repository(tmp_path / "repo")
    original = Path.write_text
    failed = False

    def fail_once(path, *args, **kwargs):
        nonlocal failed
        if path.name == "guardkit-writer-unsettled" and not failed:
            failed = True
            raise OSError("fixture marker failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_once)
    runner, entered = _task_runner(root, lambda: None)
    with pytest.raises(OSError):
        _execute(runner, root, "TASK-A")
    assert current_lease() is None
    assert _execute(runner, root, "TASK-B").success is False
    assert entered == []


def test_written_observations_do_not_replace_fabricated_or_unstaged_claims(tmp_path):
    root = _helpers.repository(tmp_path / "repo")
    with checkout_lease(root) as lease:
        lease.admit("TASK-CLAIM")
        # The ignored path exists but cannot enter a checkpoint. It must still
        # reach staging feedback, alongside the nonexistent file claim.
        git_dir = task_work_scope.identity(root)[1]
        (git_dir / "info/exclude").write_text("ignored-claim\n")
        (root / "ignored-claim").write_text("ignored")
        (root / "real-source").write_text("owned")
        report = {
            "task_id": "TASK-CLAIM",
            "files_created": ["fabricated.py", "ignored-claim"],
            "files_modified": [],
            "tests_written": [],
        }
        invoker = AgentInvoker(worktree_path=root)
        invoker._write_direct_mode_results("TASK-CLAIM", report, success=True)
        validator = CoachValidator(str(root), task_id="TASK-CLAIM")
        written = validator.read_quality_gate_results("TASK-CLAIM")
        assert written["files_created"] == ["real-source"]
        assert written["claimed_files_created"] == ["fabricated.py", "ignored-claim"]
        checked = validator._verify_honesty(written)
        assert checked.verified is False
        assert any("fabricated.py" in str(d) for d in checked.discrepancies)
        assert any(
            "ignored-claim" in str(d) and d.claim_type == "claim_audit_gitignored"
            for d in checked.discrepancies
        )
        assert CoachVerifier(root)._count_verifiable_claims(written) == 2
        assert checked.honesty_score < 1.0
        assert written["files_created"] == ["real-source"]


@pytest.mark.parametrize("named_scratch", [False, True])
def test_task_work_report_rewrites_preserve_claims_and_existing_scratch_policy(
    tmp_path, named_scratch
):
    import json
    from guardkit.orchestrator.paths import TaskArtifactPaths

    root = _helpers.repository(tmp_path / "repo")
    with checkout_lease(root) as lease:
        lease.admit("TASK-REWRITE")
        invoker = AgentInvoker(worktree_path=root)
        (root / "real-source").write_text("observed")
        # The actual writer has already separated these claims from the
        # observed inventory before the task-work report bridge runs.
        report = {
            "task_id": "TASK-REWRITE",
            "files_created": ["fabricated.py", "scratch.py"],
            "files_modified": [],
            "tests_written": [],
        }
        results_path = invoker._write_direct_mode_results(
            "TASK-REWRITE", report, success=True
        )
        results = json.loads(results_path.read_text())
        results.update(
            confirmed_write_paths=["scratch.py"],
            named_in_words_paths=["scratch.py"] if named_scratch else [],
            unconfirmed_write_paths=[],
        )
        results_path.write_text(json.dumps(results))
        invoker._create_player_report_from_task_work(
            "TASK-REWRITE", 1, SimpleNamespace(output={})
        )
        player_path = TaskArtifactPaths.player_report_path("TASK-REWRITE", 1, root)
        player = json.loads(player_path.read_text())
        expected_claims = (
            ["fabricated.py", "scratch.py"] if named_scratch else ["fabricated.py"]
        )
        for written in (json.loads(results_path.read_text()), player):
            assert written["files_created"] == ["real-source"]
            assert written["claimed_files_created"] == expected_claims
        # Direct-mode reserialization must not replace claims with observed
        # ownership either, even when given the previously written report.
        invoker._write_direct_mode_results("TASK-REWRITE", player, success=True)
        invoker._write_player_report_for_direct_mode("TASK-REWRITE", 2, player)
        for written in (
            json.loads(results_path.read_text()),
            json.loads(
                TaskArtifactPaths.player_report_path(
                    "TASK-REWRITE", 2, root
                ).read_text()
            ),
        ):
            assert written["files_created"] == ["real-source"]
            assert written["claimed_files_created"] == expected_claims
            checked = CoachValidator(str(root), task_id="TASK-REWRITE")._verify_honesty(
                written
            )
            assert any("fabricated.py" in str(d) for d in checked.discrepancies)
            assert (
                any("scratch.py" in str(d) for d in checked.discrepancies)
                is named_scratch
            )


@pytest.mark.parametrize("kind", ["created", "modified"])
def test_raw_report_cannot_hide_fabricated_claim_with_empty_claim_split(tmp_path, kind):
    root = _helpers.repository(tmp_path / "repo")
    with checkout_lease(root) as lease:
        scope = lease.admit("TASK-SPOOF-CLAIM")
        (root / "real-source").write_text("observed")
        invoker = AgentInvoker(worktree_path=root)
        report = {
            "task_id": "TASK-SPOOF-CLAIM",
            "files_created": [],
            "files_modified": [],
            "tests_written": [],
            "claimed_files_created": [],
            "claimed_files_modified": [],
            "scope_id": scope.scope_id,
            "file_inventory_available": True,
        }
        report["files_" + kind] = ["fabricated.py"]
        invoker._write_direct_mode_results("TASK-SPOOF-CLAIM", report, success=True)
        validator = CoachValidator(str(root), task_id="TASK-SPOOF-CLAIM")
        written = validator.read_quality_gate_results("TASK-SPOOF-CLAIM")
        assert written["files_created"] == ["real-source"]
        assert written["files_modified"] == []
        assert written["claimed_files_" + kind] == ["fabricated.py"]
        assert any(
            "fabricated.py" in str(d)
            for d in validator._verify_honesty(written).discrepancies
        )
