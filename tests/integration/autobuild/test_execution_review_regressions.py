"""Connected R1 regressions: command lifetime, markers and claims.

The writer keeps the builder's claimed files apart from what git observed.
The checks that used to read those claims (the honesty check, promise
matching and validate_requirements) were removed by the 27 October 2026
cull (628d22ac), and their tests with them.

Only temporary Git repositories, deterministic fakes and owned Python children.
"""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from guardkit.orchestrator import task_work_scope
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.task_work_scope import checkout_lease

_spec = importlib.util.spec_from_file_location(
    "execution_scope_test_helpers",
    Path(__file__).with_name("test_execution_scope_contract.py"),
)
_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helpers)


def _task_runner(root, callback):
    runner = FeatureOrchestrator.__new__(FeatureOrchestrator)
    runner._evidence_repos_resolved = []
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


def test_written_observations_do_not_replace_fabricated_or_unstaged_claims(tmp_path):
    # The writer keeps what git observed apart from what the builder claimed.
    # (The honesty check that then read the claims, CoachValidator
    # ._verify_honesty, was removed by the 27 October 2026 cull, 628d22ac.)
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
