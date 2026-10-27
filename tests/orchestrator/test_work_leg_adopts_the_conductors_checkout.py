"""A repair's work step adopts the checkout Forge's conductor prepared (26 October 2026).

Since 24 October every repair work step failed at once with "Initial sibling
selection requires an unconsumed fresh primary source"
(build-FEAT-6CE5-20261026132641: nine steps, each refused 2–3 s after
dispatch). The step runs the real orchestrator on a checkout another process
prepared, and the bootstrap tests never saw it because their orchestrator is a
recording double. Here the real ``AutoBuildOrchestrator.orchestrate`` and the
real writer lease run; only the Player–Coach loop itself is stubbed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

from guardkit.orchestrator import task_work_scope, work_runner
from guardkit.orchestrator.task_work_scope import identity
from guardkit.orchestrator.work_runner import run_work_leg

FIX_TASK_ID = "TASK-ROBF-001"
FIX_TASK_BODY = f"""---
id: {FIX_TASK_ID}
title: Declare the dependency
status: backlog
priority: medium
complexity: 2
task_type: fix
---

# Declare the dependency

## Acceptance Criteria

- [ ] AC-1: the dependency is declared
"""


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def prepared(tmp_path: Path) -> Path:
    """The conductor's checkout: committed history, then the review step's own
    untracked output (the fix task and its report), as in the field."""
    root = tmp_path / "conductor-tree"
    root.mkdir()
    (root / "README.md").write_text("seed\n")
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "leg@example.test")
    _git(root, "config", "user.name", "Work Leg")
    _git(root, "add", "-A", ".")
    _git(root, "commit", "-m", "seed")
    task_dir = root / "tasks" / "backlog" / "repair"
    task_dir.mkdir(parents=True)
    (task_dir / f"{FIX_TASK_ID}.md").write_text(FIX_TASK_BODY)
    (root / ".claude" / "reviews").mkdir(parents=True)
    (root / ".claude" / "reviews" / "TASK-FIX1-review-report.md").write_text("review\n")
    return root


@pytest.fixture
def real_orchestrator(monkeypatch):
    """The real orchestrator from the leg's own builder, with only its
    Player–Coach loop replaced by an answer the test chooses."""
    decisions: list = []
    real_build = work_runner._build_orchestrator

    def build(**kwargs):
        orchestrator = real_build(**kwargs)
        decision = decisions.pop(0) if decisions else "approved"
        orchestrator._orchestrate_owned = MethodType(
            lambda self, *a, **k: SimpleNamespace(
                success=decision == "approved",
                final_decision=decision,
                total_turns=1,
                turn_history=[],
                error=None,
            ),
            orchestrator,
        )
        return orchestrator

    monkeypatch.setattr(work_runner, "_build_orchestrator", build)
    return decisions


def _new_process(root: Path) -> None:
    """Each work step is its own ``guardkit task-work`` process: forget this
    process's in-memory writer state for the checkout, as a new process
    would."""
    _, git_dir = identity(root)
    for registry in (task_work_scope._fresh, task_work_scope._selected, task_work_scope._bindings):
        registry.pop(str(git_dir), None)


def _orchestration_error(outcome) -> str:
    return str(getattr(outcome, "error", "") or "")


def test_a_repair_step_runs_in_the_conductors_checkout(prepared, real_orchestrator):
    outcome = run_work_leg(task_id=FIX_TASK_ID, repo_root=prepared)
    # Before the fix: "Initial sibling selection requires an unconsumed fresh primary source".
    assert "unconsumed fresh primary source" not in _orchestration_error(outcome)
    assert outcome.status not in ("failed", "refused"), _orchestration_error(outcome)


def test_the_next_step_starts_from_what_the_last_step_left(prepared, real_orchestrator):
    run_work_leg(task_id=FIX_TASK_ID, repo_root=prepared)
    (prepared / "pyproject.toml").write_text("[project]\nname = 'x'\n")  # step 1's uncommitted work
    _new_process(prepared)
    outcome = run_work_leg(task_id=FIX_TASK_ID, repo_root=prepared)
    assert outcome.status not in ("failed", "refused"), _orchestration_error(outcome)


def test_a_step_after_a_step_that_was_not_approved_still_runs(prepared, real_orchestrator):
    """Step 2 (26 October 2026): one writer at a time is the only rule. A step
    that was not approved leaves its work for the next step, which runs."""
    real_orchestrator.extend(["max_turns_exceeded", "approved"])
    run_work_leg(task_id=FIX_TASK_ID, repo_root=prepared)
    (prepared / "pyproject.toml").write_text("[project]\nname = 'x'\n")  # the failed step's work
    _new_process(prepared)
    outcome = run_work_leg(task_id=FIX_TASK_ID, repo_root=prepared)
    assert outcome.status not in ("failed", "refused"), _orchestration_error(outcome)
    assert (prepared / "pyproject.toml").exists()


def test_a_step_in_the_same_process_after_a_failed_step_still_runs(prepared, real_orchestrator):
    real_orchestrator.extend(["max_turns_exceeded", "approved"])
    run_work_leg(task_id=FIX_TASK_ID, repo_root=prepared)
    outcome = run_work_leg(task_id=FIX_TASK_ID, repo_root=prepared)
    assert outcome.status not in ("failed", "refused"), _orchestration_error(outcome)


def test_a_task_declaring_sibling_repositories_still_runs(prepared, real_orchestrator, tmp_path):
    """Cull (27 October 2026): a repair step whose task declares sibling
    repositories is no longer refused; it runs in the conductor's checkout."""
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    _git(sibling, "init", "-b", "main")
    _git(sibling, "config", "user.email", "leg@example.test")
    _git(sibling, "config", "user.name", "Work Leg")
    (sibling / "base").write_text("sibling\n")
    _git(sibling, "add", "-A", ".")
    _git(sibling, "commit", "-m", "sibling seed")
    task = prepared / "tasks" / "backlog" / "repair" / f"{FIX_TASK_ID}.md"
    task.write_text(FIX_TASK_BODY.replace("task_type: fix\n", f"task_type: fix\nevidence_repos:\n  - {sibling}\n"))

    outcome = run_work_leg(task_id=FIX_TASK_ID, repo_root=prepared)

    assert outcome.status not in ("failed", "refused"), _orchestration_error(outcome)
