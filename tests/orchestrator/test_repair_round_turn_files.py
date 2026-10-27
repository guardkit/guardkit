"""A repair round keeps the earlier round's turn files (18 October 2026).

Each repair round numbers its turns from 1 again and writes the same file
names, so FEAT-15DD's repair round overwrote the first round's approving
``coach_turn_1.json`` and ``player_turn_1.json``. Now, when a gate re-opens an
approved task, its ``*_turn_*.json`` files are MOVED, names unchanged, into
``round-<N>/`` beside them, in every folder the task writes to. The live names
are always the latest round, so every writer and reader is unchanged.

Driven through the real re-open in ``FeatureOrchestrator._execute_wave_parallel``
and the real ``_execute_task`` (which moves the files under the checkout's
writer lease), with only ``_execute_task_owned`` standing in for the repair
round's turns.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.code_checks import latest_review_record
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
)
from guardkit.orchestrator.turn_rounds import archive_turn_files
from guardkit.worktrees import Worktree

TASK_ID = "TASK-RND-001"
FEATURE_ID = "FEAT-RND"


class _Layout:
    """The three folders a feature-mode task writes turn files into."""

    def __init__(self, tmp_path: Path) -> None:
        self.repo = tmp_path / "main"
        self.worktree = self.repo / ".guardkit" / "worktrees" / FEATURE_ID
        # The task runs as the checkout's writer, which reads its git identity.
        from tests.task_scope_fixtures import init_checkout

        init_checkout(self.worktree)
        # turn_state the late-approval reader looks for, in the main checkout
        self.root_public = self.repo / ".guardkit" / "autobuild" / TASK_ID
        # the Player's records, in the build's worktree
        self.wt_public = self.worktree / ".guardkit" / "autobuild" / TASK_ID
        # the Coach's records, outside the shared worktree
        self.private = self.repo / ".guardkit" / "autobuild-private" / TASK_ID
        for folder in (self.root_public, self.wt_public, self.private):
            folder.mkdir(parents=True, exist_ok=True)

    def write_round(self, label: str, turns: int) -> Dict[str, bytes]:
        written: Dict[str, bytes] = {}
        for turn in range(1, turns + 1):
            files = {
                self.root_public / f"turn_state_turn_{turn}.json": {"turn_number": turn},
                self.wt_public / f"player_turn_{turn}.json": {"turn": turn},
                self.wt_public / f"turn_state_turn_{turn}.json": {"turn_number": turn},
                self.private / f"coach_turn_{turn}.json": {"decision": "approve"},
                self.private / f"coach_evidence_turn_{turn}.json": {"turn": turn},
            }
            for path, body in files.items():
                body = dict(body, round=label)
                data = (json.dumps(body, indent=2) + "\n").encode()
                path.write_bytes(data)
                written[str(path)] = data
        # Not turn files: they stay where they are.
        (self.wt_public / "task_work_results.json").write_text("{}")
        (self.wt_public / "checkpoints.json").write_text("[]")
        return written

    def folders(self) -> List[Path]:
        return [self.root_public, self.wt_public, self.private]


def _feature() -> MagicMock:
    feature = MagicMock()
    feature.id = FEATURE_ID
    task = MagicMock()
    task.id = TASK_ID
    task.status = "completed"
    task.dependencies = []
    task.turns_completed = 3
    task.estimated_minutes = None
    feature.tasks = [task]
    return feature


def _reopen(layout: _Layout, feature: MagicMock, repair_turns: int, label: str) -> None:
    """Run the real gate-driven re-entry; the repair round writes its turns."""
    fo = FeatureOrchestrator(
        repo_root=layout.repo, worktree_manager=MagicMock(), quiet=True
    )
    worktree = Worktree(
        task_id=FEATURE_ID, branch_name="autobuild/FEAT-RND",
        path=layout.worktree, base_branch="main",
    )

    def _execute_task_owned(task, feature_, worktree_, **_kwargs):
        layout.write_round(label, repair_turns)
        return TaskExecutionResult(
            task_id=task.id, success=True, total_turns=repair_turns,
            final_decision="approved",
        )

    feature.tasks[0].status = "completed"
    with patch.object(fo, "_execute_task_owned", side_effect=_execute_task_owned), \
            patch("guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
                  side_effect=lambda f, tid: f.tasks[0]), \
            patch("guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"), \
            patch("guardkit.orchestrator.feature_orchestrator.TaskLoader.load_task",
                  side_effect=Exception("no task file")), \
            patch.object(fo, "_update_task_started"), \
            patch.object(fo, "_update_feature"):
        asyncio.run(
            fo._execute_wave_parallel(
                1, [TASK_ID], feature, worktree, seed_feedback="the gate failed"
            )
        )
    return fo


class TestTheEarlierRoundIsKept:
    def test_round_1_holds_the_first_round_byte_identical(self, tmp_path: Path) -> None:
        layout = _Layout(tmp_path)
        first = layout.write_round("first", 3)
        feature = _feature()
        _reopen(layout, feature, repair_turns=1, label="repair-1")

        for path_str, data in first.items():
            path = Path(path_str)
            archived = path.parent / "round-1" / path.name
            assert archived.read_bytes() == data, archived
        for folder in layout.folders():
            live = sorted(p.name for p in folder.glob("*_turn_*.json"))
            # Only the repair round's one turn is live.
            assert all("_turn_1.json" in name for name in live), live
            for path in folder.glob("*_turn_*.json"):
                assert json.loads(path.read_text())["round"] == "repair-1"
        # Files that are not turn files never move.
        assert (layout.wt_public / "task_work_results.json").exists()
        assert (layout.wt_public / "checkpoints.json").exists()
        assert not (layout.wt_public / "round-1" / "checkpoints.json").exists()

    def test_a_second_repair_round_makes_round_2(self, tmp_path: Path) -> None:
        layout = _Layout(tmp_path)
        layout.write_round("first", 3)
        feature = _feature()
        _reopen(layout, feature, repair_turns=2, label="repair-1")
        _reopen(layout, feature, repair_turns=1, label="repair-2")
        for folder in layout.folders():
            assert sorted(p.name for p in folder.iterdir() if p.is_dir()) == [
                "round-1", "round-2",
            ]
            round_2 = sorted(p.name for p in (folder / "round-2").iterdir())
            assert any("_turn_2.json" in name for name in round_2), round_2
            for path in (folder / "round-2").iterdir():
                assert json.loads(path.read_text())["round"] == "repair-1"
            for path in (folder / "round-1").iterdir():
                assert json.loads(path.read_text())["round"] == "first"

    def test_every_listed_reader_returns_the_repair_round(self, tmp_path: Path) -> None:
        layout = _Layout(tmp_path)
        layout.write_round("first", 3)
        fo = _reopen(layout, _feature(), repair_turns=1, label="repair-1")

        # The latest-Coach-turn reader.
        latest = fo._latest_coach_turn_path(TASK_ID)
        assert latest == layout.private / "coach_turn_1.json"
        assert json.loads(latest.read_text())["round"] == "repair-1"
        # The turn-state recovery: the repair round's one turn, not turn 3.
        assert fo._read_total_turns(TASK_ID) == 1
        # The code-checks reader.
        review = latest_review_record(layout.private)
        assert review == layout.private / "coach_evidence_turn_1.json"

    def test_a_task_that_is_not_reopened_keeps_its_files(self, tmp_path: Path) -> None:
        """No gate re-entry (seed_feedback None): nothing is moved."""
        layout = _Layout(tmp_path)
        first = layout.write_round("first", 2)
        fo = FeatureOrchestrator(repo_root=layout.repo, worktree_manager=MagicMock(), quiet=True)
        feature = _feature()
        with patch("guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
                   side_effect=lambda f, tid: f.tasks[0]):
            asyncio.run(
                fo._execute_wave_parallel(
                    1, [TASK_ID], feature,
                    Worktree(task_id=FEATURE_ID, branch_name="b", path=layout.worktree,
                             base_branch="main"),
                )
            )
        for path_str in first:
            assert Path(path_str).exists()
        assert not any((f / "round-1").exists() for f in layout.folders())


class TestAFailedMoveNeverStopsTheRound:
    def test_a_failed_move_leaves_todays_behaviour(self, tmp_path: Path) -> None:
        layout = _Layout(tmp_path)
        layout.write_round("first", 1)
        feature = _feature()
        with patch("guardkit.orchestrator.turn_rounds.shutil.move",
                   side_effect=OSError("read-only")):
            _reopen(layout, feature, repair_turns=1, label="repair-1")
        # The round still ran and wrote its files over the old names, as today.
        assert json.loads(
            (layout.private / "coach_turn_1.json").read_text()
        )["round"] == "repair-1"

    def test_the_helper_never_raises(self, tmp_path: Path) -> None:
        assert archive_turn_files(TASK_ID, [tmp_path / "missing"]) is None
        with patch("guardkit.orchestrator.turn_rounds._unique_folders",
                   side_effect=RuntimeError("boom")):
            assert archive_turn_files(TASK_ID, [tmp_path]) is None

    def test_an_empty_folder_makes_no_round(self, tmp_path: Path) -> None:
        folder = tmp_path / "TASK"
        folder.mkdir()
        assert archive_turn_files(TASK_ID, [folder]) is None
        assert not (folder / "round-1").exists()
