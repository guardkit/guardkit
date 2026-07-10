"""Tests for the task-complete demotion build (scope §7 Phases 0-2).

Covers the shared atomic completion routine + the Phase 6 decision:

  * **Atomicity** — the flip+move is one commit; ``status: completed`` is NEVER
    observable under a non-completed directory (a crash before OR after the
    single ``os.replace`` cannot leave a completed-in-backlog state).
  * **Carve-outs** — autobuild / operator_handoff refuse.
  * **Tri-state routing** — ``decide_finalize`` Green/Amber/Red/Skip.
  * **Enforcement call site** — ``qa.enforce_tier1`` fires (fail-closed) when the
    repo flag is on.
  * **CLI** — ``guardkit task complete`` pause / autobuild-refuse / happy paths.
"""

from __future__ import annotations

import os as _os
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from installer.core.commands.lib import task_completion_helper as tch
from installer.core.commands.lib.task_completion_helper import (
    CompletionRefused,
    atomic_flip_and_move,
    complete_task,
    _apply_completion_frontmatter,
    _enforce_tier1_completion,
)
from installer.core.commands.lib.task_finalize import (
    AMBER,
    GREEN,
    RED,
    SKIP,
    carveout_refusal,
    decide_finalize,
)
from guardkit.cli.task import task as task_group


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_task(path: Path, task_id: str, *, status: str = "in_review", task_type: str = "feature") -> None:
    path.write_text(
        f"---\n"
        f"id: {task_id}\n"
        f"title: Demo completion task\n"
        f"status: {status}\n"
        f"task_type: {task_type}\n"
        f"---\n\n"
        f"# Demo completion task\n\n"
        f"## Acceptance Criteria\n- [ ] does the thing\n",
        encoding="utf-8",
    )


def _status_of(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    fm = text.split("---", 2)[1]
    return (yaml.safe_load(fm) or {}).get("status")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A git repo with the task-dir skeleton; cwd set to its root."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo_dir, check=True, capture_output=True)
    for d in ("backlog", "in_progress", "in_review", "completed"):
        (repo_dir / "tasks" / d).mkdir(parents=True)
    (repo_dir / ".claude" / "task-plans").mkdir(parents=True)
    (repo_dir / "README.md").write_text("x")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True, capture_output=True)
    monkeypatch.chdir(repo_dir)
    # A clean baseline: enforcement OFF unless a test opts in.
    monkeypatch.delenv("GUARDKIT_QA_ENFORCE_TIER1", raising=False)
    return repo_dir


@pytest.fixture
def in_review_task(repo):
    task_id = "TASK-DEMO-01"
    path = repo / "tasks" / "in_review" / f"{task_id}.md"
    _write_task(path, task_id)
    return path, task_id


# ---------------------------------------------------------------------------
# 1. Atomicity — the load-bearing invariant
# ---------------------------------------------------------------------------


def test_happy_atomic_flip_and_move(repo, in_review_task):
    path, task_id = in_review_task
    result = complete_task(task_id)

    assert not path.exists()  # source gone
    dest = Path(result["new_path"])
    assert dest.exists()
    assert "completed" in str(dest)
    assert dest.parent.name == __import__("datetime").datetime.now().strftime("%Y-%m")
    assert _status_of(dest) == "completed"
    assert result["status_flipped"] is True
    assert result["task_type"] == "feature"


def test_apply_completion_frontmatter_is_pure(in_review_task):
    """The flip is a pure string transform — it touches no file."""
    path, _ = in_review_task
    before = path.read_text(encoding="utf-8")
    flipped = _apply_completion_frontmatter(before, completed_timestamp="2026-07-10T00:00:00Z")
    assert "status: completed" in flipped
    assert path.read_text(encoding="utf-8") == before  # source untouched


def test_crash_before_replace_leaves_source_untouched(repo, in_review_task, monkeypatch):
    """A crash at the atomic commit point → task simply not completed."""
    path, task_id = in_review_task

    def boom(*a, **k):
        raise OSError("simulated crash at os.replace")

    monkeypatch.setattr(tch.os, "replace", boom)

    with pytest.raises(OSError):
        complete_task(task_id)

    # Source is untouched: still in_review, still in in_review/, no dest, and no
    # completed-status file leaked into a non-completed dir.
    assert path.exists()
    assert _status_of(path) == "in_review"
    completed_root = repo / "tasks" / "completed"
    leaked = [p for p in completed_root.rglob("*.md")]
    assert leaked == []
    # No stray temp file left behind in the destination month dir.
    assert not list(completed_root.rglob("*.tmp"))


def test_crash_after_replace_never_completed_in_backlog(repo, in_review_task, monkeypatch):
    """A crash AFTER the atomic replace but before source removal: the dest is
    authoritative and the lingering source keeps its ORIGINAL status — so
    ``status: completed`` is never observable under a non-completed dir."""
    path, task_id = in_review_task
    real_unlink = Path.unlink

    def failing_unlink(self, *a, **k):
        # Fail ONLY the removal of the original source (in in_review/).
        if self.name == path.name and self.parent.name == "in_review":
            raise OSError("simulated crash after replace, before source removal")
        return real_unlink(self, *a, **k)

    monkeypatch.setattr(Path, "unlink", failing_unlink)

    result = complete_task(task_id)  # completion SUCCEEDS despite the failure

    dest = Path(result["new_path"])
    assert dest.exists() and _status_of(dest) == "completed"
    # The source lingers (stale duplicate) but is NOT completed → invariant holds.
    assert path.exists()
    assert _status_of(path) == "in_review"


# ---------------------------------------------------------------------------
# 2. Carve-outs
# ---------------------------------------------------------------------------


def test_complete_task_refuses_autobuild(repo, in_review_task):
    path, task_id = in_review_task
    with pytest.raises(CompletionRefused):
        complete_task(task_id, refuse_autobuild=True)
    # File untouched — a refusal never half-completes.
    assert path.exists() and _status_of(path) == "in_review"


def test_complete_task_refuses_operator_handoff(repo):
    task_id = "TASK-OH-01"
    path = repo / "tasks" / "in_review" / f"{task_id}.md"
    _write_task(path, task_id, task_type="operator_handoff")
    with pytest.raises(CompletionRefused):
        complete_task(task_id, refuse_operator_handoff=True)
    assert path.exists() and _status_of(path) == "in_review"


def test_operator_handoff_refusal_ignored_for_feature_task(repo, in_review_task):
    """refuse_operator_handoff only bites operator_handoff tasks (entry B still
    completes a normal task)."""
    path, task_id = in_review_task
    result = complete_task(task_id, refuse_operator_handoff=True)
    assert not path.exists() and Path(result["new_path"]).exists()


def test_operator_handoff_completes_via_routine_by_default(repo):
    """The manual/CLI path (entry B) DOES complete operator_handoff tasks."""
    task_id = "TASK-OH-02"
    path = repo / "tasks" / "in_review" / f"{task_id}.md"
    _write_task(path, task_id, task_type="operator_handoff")
    result = complete_task(task_id)  # no refuse flag → completes
    assert not path.exists() and Path(result["new_path"]).exists()


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        (dict(autobuild_mode=True, task_type="feature"), True),
        (dict(autobuild_mode=False, task_type="operator_handoff"), True),
        (dict(autobuild_mode=False, task_type="operator_handoff", allow_operator_handoff=True), False),
        (dict(autobuild_mode=False, task_type="feature"), False),
        (dict(autobuild_mode=False, task_type=None), False),
    ],
)
def test_carveout_refusal(kwargs, expected):
    reason = carveout_refusal(**kwargs)
    assert (reason is not None) is expected


# ---------------------------------------------------------------------------
# 3. Tri-state routing (decide_finalize)
# ---------------------------------------------------------------------------

_BASE = dict(
    complete_flag=True,
    pause_flag=False,
    autobuild_mode=False,
    task_type="feature",
    reached_in_review=True,
    audit_clean=True,
    review_clean=True,
    blocked=False,
)


@pytest.mark.parametrize(
    "override,verdict",
    [
        ({}, GREEN),
        ({"reached_in_review": False}, SKIP),
        ({"autobuild_mode": True}, SKIP),
        ({"task_type": "operator_handoff"}, SKIP),
        ({"complete_flag": False}, SKIP),
        ({"blocked": True}, RED),
        ({"pause_flag": True}, AMBER),
        ({"audit_clean": False}, AMBER),
        ({"review_clean": False}, AMBER),
    ],
)
def test_decide_finalize_tri_state(override, verdict):
    decision = decide_finalize(**{**_BASE, **override})
    assert decision.verdict == verdict
    assert decision.should_complete is (verdict == GREEN)
    assert decision.reason  # always explains itself


def test_carveouts_win_over_pause_and_block():
    """A carve-out SKIPs even when pause/block would otherwise apply."""
    d = decide_finalize(**{**_BASE, "autobuild_mode": True, "pause_flag": True, "blocked": True})
    assert d.verdict == SKIP


# ---------------------------------------------------------------------------
# 4. Enforcement call site (qa.enforce_tier1) — fires when flagged
# ---------------------------------------------------------------------------


def test_enforce_tier1_off_is_noop(repo, in_review_task):
    path, task_id = in_review_task
    # No env, no config → flag off → completes.
    result = complete_task(task_id, enforce_tier1=True)
    assert Path(result["new_path"]).exists()


def test_enforce_tier1_on_no_passbar_refuses(repo, in_review_task, monkeypatch):
    path, task_id = in_review_task
    monkeypatch.setenv("GUARDKIT_QA_ENFORCE_TIER1", "1")
    with pytest.raises(CompletionRefused) as exc:
        complete_task(task_id, enforce_tier1=True)
    assert "enforce_tier1" in str(exc.value)
    # Fail-closed → task untouched.
    assert path.exists() and _status_of(path) == "in_review"


def test_enforce_helper_reason_when_flag_on_off(repo, in_review_task, monkeypatch):
    _, task_id = in_review_task
    assert _enforce_tier1_completion(repo, task_id) is None  # off
    monkeypatch.setenv("GUARDKIT_QA_ENFORCE_TIER1", "1")
    assert _enforce_tier1_completion(repo, task_id) is not None  # on + no pass bar


# ---------------------------------------------------------------------------
# 5. CLI — guardkit task complete
# ---------------------------------------------------------------------------


def test_cli_pause_leaves_task_in_review(repo, in_review_task):
    path, task_id = in_review_task
    result = CliRunner().invoke(task_group, ["complete", task_id, "--pause"])
    assert result.exit_code == 0, result.output
    assert "IN_REVIEW" in result.output
    assert path.exists() and _status_of(path) == "in_review"


def test_cli_autobuild_mode_refuses(repo, in_review_task):
    path, task_id = in_review_task
    result = CliRunner().invoke(task_group, ["complete", task_id, "--autobuild-mode"])
    assert result.exit_code != 0
    assert path.exists() and _status_of(path) == "in_review"


def test_cli_happy_completes(repo, in_review_task):
    path, task_id = in_review_task
    result = CliRunner().invoke(
        task_group, ["complete", task_id, "--no-capture", "--no-git-commit"]
    )
    assert result.exit_code == 0, result.output
    assert not path.exists()
    completed = list((repo / "tasks" / "completed").rglob(f"{task_id}.md"))
    assert len(completed) == 1
    assert _status_of(completed[0]) == "completed"
