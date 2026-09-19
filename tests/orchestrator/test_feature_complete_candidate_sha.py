"""The feature-complete runtime-surface gate is asked about THIS candidate.

19 September 2026 (B9 corrections, coordinator integration fix). Lane C made
``check_runtime_surface_gate`` refuse a gate that is not green for the
candidate commit under check; ``guardkit feature-complete`` therefore has to
say which commit that is. It reads the build worktree's HEAD, else the
``autobuild/<feature>`` branch, and hands it to the check; with neither it
passes ``None`` and the check fails closed rather than guessing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.feature_complete import (
    FeatureCompleteError,
    FeatureCompleteOrchestrator,
)
from guardkit.worktrees import Worktree


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(root), check=True, capture_output=True, text=True
    ).stdout.strip()


def _repo_with_candidate(tmp_path: Path) -> tuple[Path, Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    (repo / "README").write_text("main\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "main")
    _git(repo, "checkout", "-q", "-b", "autobuild/FEAT-X")
    (repo / "README").write_text("candidate\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "candidate")
    candidate = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "main")
    worktree = tmp_path / "wt"
    _git(repo, "worktree", "add", "-q", str(worktree), "autobuild/FEAT-X")
    return repo, worktree, candidate


def test_the_candidate_sha_is_the_worktree_head(tmp_path: Path) -> None:
    repo, worktree, candidate = _repo_with_candidate(tmp_path)
    orch = FeatureCompleteOrchestrator(repo_root=repo, worktree_manager=MagicMock())
    wt = Worktree(task_id="FEAT-X", branch_name="autobuild/FEAT-X", path=worktree, base_branch="main")
    assert orch._candidate_sha("FEAT-X", wt) == candidate


def test_the_candidate_sha_falls_back_to_the_build_branch(tmp_path: Path) -> None:
    repo, _worktree, candidate = _repo_with_candidate(tmp_path)
    orch = FeatureCompleteOrchestrator(repo_root=repo, worktree_manager=MagicMock())
    assert orch._candidate_sha("FEAT-X", None) == candidate


def test_no_candidate_is_none_not_a_guess(tmp_path: Path) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    orch = FeatureCompleteOrchestrator(repo_root=repo, worktree_manager=MagicMock())
    assert orch._candidate_sha("FEAT-NONE", None) is None


def test_the_gate_receives_the_candidate_sha_and_a_failed_gate_refuses(tmp_path: Path) -> None:
    repo, worktree, candidate = _repo_with_candidate(tmp_path)
    orch = FeatureCompleteOrchestrator(repo_root=repo, worktree_manager=MagicMock())
    feature = MagicMock()
    feature.id = "FEAT-X"
    feature.tasks = [MagicMock(id="TASK-X-001")]
    seen = {}

    def fake_check(repo_root, task_ids, candidate_sha=None):
        seen["candidate_sha"] = candidate_sha
        result = MagicMock()
        result.status = "fail"
        result.passed = False
        result.runtime_surface = True
        result.detail = "gate last_green is for another commit"
        return result

    with patch("guardkit.qa.enforcement.is_tier1_enforced", return_value=True), patch(
        "guardkit.qa.enforcement.check_runtime_surface_gate", side_effect=fake_check
    ):
        with pytest.raises(FeatureCompleteError):
            orch._check_runtime_surface_gate(
                feature,
                candidate_sha=orch._candidate_sha(
                    "FEAT-X",
                    Worktree(task_id="FEAT-X", branch_name="autobuild/FEAT-X", path=worktree, base_branch="main"),
                ),
            )
    assert seen["candidate_sha"] == candidate
