"""The root check at the end of each build (Rich, 20 November 2026: "yes").

Plain words: during a build each task runs the tests of the parts it changed,
and the root check only when a root file changed. So a build could end without
the root check ever running on its finished tree, and the merge, hours later,
was the first to run it (FEAT-D5BC: its later tasks changed only ``apps/api``,
and at the merge the root check failed). Now the build's final checks are the
root check (the merge's own full check, on the working copy, with the last
task's pinned settings) and the whole-feature check, on the same tree, root
first. Any repair changes the tree, so both run again after it (Codex R1), and
the repairs of the two share one cap of two rounds.

What is proved here, on real git repositories with real shell commands:

1. the FEAT-D5BC case: a later task changes only one part and the root check
   fails on the finished tree. The build runs the root check at the end, sends
   the failure back to the last task with the check's own output, and, when
   the repair does not fix it, fails before any merge offer;
2. the same case, repaired: the root check passes on the repaired tree and the
   whole-feature check then runs on it;
3. a build whose root check passes goes on to the whole-feature check as before;
4. the R1 case: a whole-feature repair that changes only one part and breaks
   the root check is caught by the root check's rerun, and the build goes on
   only when both have passed on the same tree;
5. the shared cap bounds the rounds, whichever check asks for them.

``_execute_wave`` stands in for the builder, so no model is ever called.
"""

from __future__ import annotations

import json
import logging
import subprocess
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.feature_check import RECEIPT_RELATIVE_PATH
from guardkit.orchestrator.feature_orchestrator import (
    END_ROOT_CHECK_GATE,
    END_ROOT_CHECK_RECORD,
    FeatureOrchestrator,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.orchestrator.task_work_scope import checkout_lease, register_fresh_checkout
from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain
from guardkit.worktrees import Worktree


#: The root check: the whole tree must agree with itself. It fails the way
#: FEAT-D5BC's did: a change made in one part only breaks a test at the root.
ROOT_CHECK = """#!/bin/sh
echo "root: collecting the contract tests"
api=$(cat apps/api/VERSION)
contract=$(cat CONTRACT)
if [ "$api" != "$contract" ]; then
  echo "FAILED tests/test_contract.py::test_api_matches_contract - the API says $api, the contract says $contract"
  exit 1
fi
echo "root: 1 passed"
"""

#: The API part's own tests pass whatever its version says.
API_TEST = """#!/bin/sh
echo "apps/api: 3 passed"
"""

#: The whole-feature check: the feature works once the API part has it.
FEATURE_CHECK = """#!/bin/sh
if [ -f apps/api/THE_FEATURE_IS_FIXED ]; then
  exit 0
fi
echo "GET /users/created-per-day answered 404" >&2
exit 1
"""

TOOLCHAIN = """toolchain:
  test: "sh checks/root.sh"
  components:
    api:
      cwd: apps/api
      test: "sh test.sh"
  feature_check: "sh qa/feature-check.sh"
"""

#: The same project, with an install declared for the API part that fails:
#: the full check then cannot run its tests (Codex R2).
TOOLCHAIN_WITH_A_FAILING_INSTALL = TOOLCHAIN.replace(
    '      test: "sh test.sh"\n',
    '      test: "sh test.sh"\n      install: "sh install.sh"\n',
)

API_INSTALL_FAILS = """#!/bin/sh
echo "apps/api: the package registry could not be reached" >&2
exit 3
"""

FIRST, LAST = "TASK-001", "TASK-002"


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(root), check=True, capture_output=True, text=True
    ).stdout.strip()


def _project(
    tmp_path: Path, *, feature_works: bool = True, toolchain: str = TOOLCHAIN
) -> tuple[Path, Path]:
    """The main checkout (where the whole-feature check is declared) and the
    build's worktree: a root check, an API part, and the feature check."""
    repo_root, worktree = tmp_path / "main", tmp_path / "worktree"
    _write(repo_root, ".guardkit/config.yaml", toolchain)
    _write(worktree, ".guardkit/config.yaml", toolchain)
    _write(worktree, "apps/api/install.sh", API_INSTALL_FAILS)
    _write(worktree, ".gitignore", ".guardkit/autobuild-private/\n")
    _write(worktree, "checks/root.sh", ROOT_CHECK)
    _write(worktree, "CONTRACT", "v1\n")
    _write(worktree, "apps/api/test.sh", API_TEST)
    _write(worktree, "apps/api/VERSION", "v1\n")
    _write(worktree, "qa/feature-check.sh", FEATURE_CHECK)
    if feature_works:
        _write(worktree, "apps/api/THE_FEATURE_IS_FIXED", "yes\n")
    for task in (FIRST, LAST):
        _write(worktree, f"tasks/{task}.md", f"# {task}\n\nShow me users per day.\n")
    _git(worktree, "init", "-q", "-b", "main")
    _git(worktree, "config", "user.email", "test@example.com")
    _git(worktree, "config", "user.name", "Test")
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-q", "-m", "the project before the build")
    return repo_root, worktree


def _feature(worktree: Path):
    feature = MagicMock()
    feature.id = "FEAT-D5BC"
    feature.name = "Users per day"
    feature.description = "Show me how many users were created per day"
    feature.status = "in_progress"
    feature.smoke_gates = None
    feature.estimated_minutes = None
    feature.feature_files = []
    feature.file_path = str(worktree / ".guardkit/features/FEAT-D5BC.yaml")
    feature.scenarios = {}
    tasks = []
    for task_id in (FIRST, LAST):
        task = MagicMock()
        task.id = task_id
        task.name = task_id
        task.dependencies = []
        task.status = "pending"
        task.file_path = str(worktree / f"tasks/{task_id}.md")
        tasks.append(task)
    feature.tasks = tasks
    feature.orchestration.parallel_groups = [[FIRST], [LAST]]
    feature.execution.current_wave = 0
    feature.execution.completed_waves = []
    return feature


class _Builder:
    """Stands in for the builder. ``changes[n]`` is what its n-th call (from 0)
    writes into the worktree, committed through the task executor's own lease
    the way a real approved turn is; every call's task completes."""

    def __init__(self, worktree: Path, changes: Dict[int, Callable[[Path], None]]) -> None:
        self.worktree = worktree
        self.changes = changes
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, wave_number, task_ids, feature, worktree, seed_feedback=None, attempt=0):
        index = len(self.calls)
        self.calls.append({"wave": wave_number, "tasks": list(task_ids),
                           "feedback": seed_feedback, "attempt": attempt})
        for task in feature.tasks:
            if task.id in task_ids:
                task.status = "completed"
        change = self.changes.get(index)
        if change is not None:
            with checkout_lease(self.worktree) as lease:
                lease.admit(str(task_ids[0]))
                change(self.worktree)
                _git(self.worktree, "add", "-A")
                _git(self.worktree, "commit", "-q", "-m", f"call {index}: {task_ids[0]}")
                lease.checkpoint_completed()
        return WaveExecutionResult(
            wave_number=wave_number,
            task_ids=list(task_ids),
            results=[TaskExecutionResult(task_id=t, success=True, total_turns=1,
                                         final_decision="approved") for t in task_ids],
            all_succeeded=True,
        )

    def repairs(self) -> List[Dict[str, Any]]:
        return [c for c in self.calls if c["feedback"] is not None]


def _api_only_change(worktree: Path) -> None:
    """FEAT-D5BC's later task: it changes the API part only."""
    _write(worktree, "apps/api/VERSION", "v2\n")


def _contract_fix(worktree: Path) -> None:
    _write(worktree, "CONTRACT", "v2\n")


def _orchestrator(repo_root: Path) -> FeatureOrchestrator:
    return FeatureOrchestrator(repo_root=repo_root, max_turns=1,
                               worktree_manager=MagicMock(), quiet=True)


def _build(repo_root: Path, worktree_path: Path, feature, builder: _Builder, *, end_review: bool):
    """The build with no model: the waves, then (with ``end_review``) the
    whole ``orchestrate`` route, else the per-task-reviewer route's
    ``_wave_phase``; then the finaliser."""
    # What the last task's run pinned before its first turn: main's commands.
    assert snapshot_task_toolchain(LAST, worktree_path, repo_root, "main") is not None
    register_fresh_checkout(worktree_path, "HEAD")
    orchestrator = _orchestrator(repo_root)
    worktree = Worktree(task_id="FEAT-D5BC", branch_name="autobuild/FEAT-D5BC",
                        path=worktree_path, base_branch="main")
    with ExitStack() as stack:
        stack.enter_context(patch.object(orchestrator, "_bootstrap_environment"))
        stack.enter_context(patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
            side_effect=lambda f, tid: f))
        stack.enter_context(patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"))
        stack.enter_context(patch.object(orchestrator, "_execute_wave", side_effect=builder))
        stack.enter_context(patch.object(orchestrator, "_display_summary"))
        if end_review:
            stack.enter_context(patch.object(
                orchestrator, "_setup_phase", return_value=(feature, worktree)))
            return orchestrator.orchestrate("FEAT-D5BC")
        wave_results = orchestrator._wave_phase(feature, worktree)
        return orchestrator._finalize_phase(feature, wave_results, worktree)


def _root_record(worktree: Path) -> Dict[str, Any]:
    return json.loads((worktree / END_ROOT_CHECK_RECORD).read_text())


def _feature_check_record(worktree: Path) -> Optional[Dict[str, Any]]:
    path = worktree / RECEIPT_RELATIVE_PATH
    return json.loads(path.read_text()) if path.exists() else None


def _head(worktree: Path) -> str:
    return _git(worktree, "rev-parse", "HEAD")


@pytest.fixture(autouse=True)
def _no_ambient_flags(monkeypatch: pytest.MonkeyPatch):
    """The estate's own environment must not decide what these tests prove."""
    monkeypatch.delenv("GUARDKIT_FEATURE_CHECK_MAX_RETRIES", raising=False)
    monkeypatch.delenv("GUARDKIT_QA_ENFORCE_TWIN_COVERAGE", raising=False)


# ---------------------------------------------------------------------------
# 1 and 2. The FEAT-D5BC case
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("end_review", [True, False], ids=["end-review route", "per-task route"])
def test_a_root_check_broken_by_one_part_fails_the_build_before_any_merge_offer(
    tmp_path: Path, capsys: pytest.CaptureFixture, caplog: pytest.LogCaptureFixture,
    end_review: bool,
) -> None:
    repo_root, worktree = _project(tmp_path)
    feature = _feature(worktree)
    # The waves, then two repairs that do not fix it.
    builder = _Builder(worktree, {1: _api_only_change})

    with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.feature_orchestrator"):
        result = _build(repo_root, worktree, feature, builder, end_review=end_review)

    # The failure went back to the last task with the root check's own output.
    repairs = builder.repairs()
    assert [r["tasks"] for r in repairs] == [[LAST], [LAST]], "the shared cap: two rounds"
    assert [r["attempt"] for r in repairs] == [301, 302]
    feedback = repairs[0]["feedback"]
    assert "The project's full check failed on the finished feature" in feedback
    assert "=== root: sh checks/root.sh" in feedback
    assert "FAILED tests/test_contract.py::test_api_matches_contract - the API says v2" in feedback

    # Every run is recorded beside the whole-feature check's record and logged.
    record = _root_record(worktree)
    assert record["status"] == "failed"
    assert [r["status"] for r in record["runs"]] == ["failed", "failed", "failed"]
    assert [r["repair_follows"] for r in record["runs"]] == [True, True, False]
    assert record["runs"][-1]["candidate_sha"] == _head(worktree)
    assert record["runs"][0]["failing_output"][0] == "=== root: sh checks/root.sh"
    logged = [r.getMessage() for r in caplog.records
              if r.getMessage().startswith("Root check at the end of the build failed in")]
    assert len(logged) == 3, logged

    # The build fails with the check's output, and nothing is offered.
    assert result.status == "failed" and result.success is False
    assert result.error.startswith("the root check at the end of the build failed")
    gate = result.wave_results[-1].smoke_gate_result
    assert gate is not None and gate.passed is False
    assert gate.command == END_ROOT_CHECK_GATE
    assert "the API says v2, the contract says v1" in gate.stdout
    assert _feature_check_record(worktree) is None, "the whole-feature check never ran"
    assert "GUARDKIT_STOPPED_BECAUSE" not in capsys.readouterr().out


def test_a_repaired_root_check_goes_on_to_the_whole_feature_check(tmp_path: Path) -> None:
    repo_root, worktree = _project(tmp_path)
    feature = _feature(worktree)
    builder = _Builder(worktree, {1: _api_only_change, 2: _contract_fix})

    result = _build(repo_root, worktree, feature, builder, end_review=True)

    assert len(builder.repairs()) == 1
    runs = _root_record(worktree)["runs"]
    assert [r["status"] for r in runs] == ["failed", "passed"]
    assert runs[0]["repair"]["succeeded"] is True
    check = _feature_check_record(worktree)
    assert check["status"] == "passed"
    # Both passed on the same final tree.
    assert check["attempts"][-1]["candidate_sha"] == runs[-1]["candidate_sha"] == _head(worktree)
    assert result.status == "completed", result.error


# ---------------------------------------------------------------------------
# 3. A root check that passes changes nothing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("end_review", [True, False], ids=["end-review route", "per-task route"])
def test_a_passing_root_check_goes_on_to_the_whole_feature_check_unchanged(
    tmp_path: Path, end_review: bool
) -> None:
    repo_root, worktree = _project(tmp_path)
    feature = _feature(worktree)
    builder = _Builder(worktree, {})

    result = _build(repo_root, worktree, feature, builder, end_review=end_review)

    assert builder.repairs() == []
    runs = _root_record(worktree)["runs"]
    assert [(r["status"], r["repair_follows"]) for r in runs] == [("passed", False)]
    assert runs[0]["failing_output"] == []
    check = _feature_check_record(worktree)
    assert check["status"] == "passed" and len(check["attempts"]) == 1
    assert result.status == "completed", result.error


# ---------------------------------------------------------------------------
# 4. The R1 case: a whole-feature repair that breaks the root check
# ---------------------------------------------------------------------------


def _feature_fix_that_breaks_the_root(worktree: Path) -> None:
    """The whole-feature repair: it fixes the feature in the API part only,
    and in passing breaks the root check."""
    _write(worktree, "apps/api/THE_FEATURE_IS_FIXED", "yes\n")
    _write(worktree, "apps/api/VERSION", "v2\n")


def test_a_whole_feature_repair_that_breaks_the_root_check_is_caught(tmp_path: Path) -> None:
    repo_root, worktree = _project(tmp_path, feature_works=False)
    feature = _feature(worktree)
    # Call 2 is the whole-feature repair, call 3 the root check's repair.
    builder = _Builder(worktree, {2: _feature_fix_that_breaks_the_root, 3: _contract_fix})

    result = _build(repo_root, worktree, feature, builder, end_review=True)

    repairs = builder.repairs()
    assert len(repairs) == 2
    assert "=== root:" not in repairs[0]["feedback"], "the first repair is the whole-feature check's"
    assert "=== root: sh checks/root.sh" in repairs[1]["feedback"]
    assert [r["status"] for r in _root_record(worktree)["runs"]] == ["passed", "failed", "passed"]
    check = _feature_check_record(worktree)
    assert [a["passed"] for a in check["attempts"]] == [False, True]
    # The whole-feature check's last pass and the root check's last pass were
    # on the same tree, the one the build ends on.
    last_root = _root_record(worktree)["runs"][-1]
    assert check["attempts"][-1]["candidate_sha"] == last_root["candidate_sha"] == _head(worktree)
    assert result.status == "completed", result.error


def test_a_root_check_broken_by_the_last_repair_fails_the_build(tmp_path: Path) -> None:
    """The same R1 break with no round left to repair it: the build fails on
    the root check, though the whole-feature check passed on that tree."""
    repo_root, worktree = _project(tmp_path, feature_works=False)
    feature = _feature(worktree)
    builder = _Builder(worktree, {2: _feature_fix_that_breaks_the_root})

    result = _build(repo_root, worktree, feature, builder, end_review=True)

    assert len(builder.repairs()) == 2
    statuses = [r["status"] for r in _root_record(worktree)["runs"]]
    assert statuses == ["passed", "failed", "failed"]
    assert result.status == "failed"
    assert result.error.startswith("the root check at the end of the build failed")


# ---------------------------------------------------------------------------
# 5. One cap for both checks
# ---------------------------------------------------------------------------


def test_the_two_checks_share_one_cap_of_two_rounds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole-feature check's own budget allows five repairs here, but the
    root check's repair took one of the two shared rounds, so the
    whole-feature check gets one and the build then fails on it."""
    monkeypatch.setenv("GUARDKIT_FEATURE_CHECK_MAX_RETRIES", "5")
    repo_root, worktree = _project(tmp_path, feature_works=False)
    feature = _feature(worktree)
    builder = _Builder(worktree, {1: _api_only_change, 2: _contract_fix})

    result = _build(repo_root, worktree, feature, builder, end_review=True)

    repairs = builder.repairs()
    assert len(repairs) == 2, "one root repair and one whole-feature repair, then the cap"
    assert "=== root:" in repairs[0]["feedback"] and "=== root:" not in repairs[1]["feedback"]
    assert [r["status"] for r in _root_record(worktree)["runs"]] == ["failed", "passed", "passed"]
    check = _feature_check_record(worktree)
    assert check["status"] == "failed" and len(check["attempts"]) == 2
    assert result.status == "failed"


# ---------------------------------------------------------------------------
# 6. A check that could not run is not a pass (Codex R2)
# ---------------------------------------------------------------------------


def test_a_root_check_that_could_not_run_fails_the_build_before_any_merge_offer(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A declared part's install fails, so the full check cannot run its
    tests; the whole-feature check would pass. The build must not complete or
    offer a merge: it goes through the same repairs under the same cap, then
    fails with the reason."""
    repo_root, worktree = _project(tmp_path, toolchain=TOOLCHAIN_WITH_A_FAILING_INSTALL)
    feature = _feature(worktree)
    builder = _Builder(worktree, {})

    result = _build(repo_root, worktree, feature, builder, end_review=True)

    repairs = builder.repairs()
    assert [r["tasks"] for r in repairs] == [[LAST], [LAST]], "the shared cap: two rounds"
    feedback = repairs[0]["feedback"]
    assert "The project's full check could not run on the finished feature" in feedback
    assert "the declared install (`sh install.sh`) for part api (in apps/api)" in feedback
    assert "the package registry could not be reached" in feedback
    runs = _root_record(worktree)["runs"]
    assert [r["status"] for r in runs] == ["unverified"] * 3
    assert [r["repair_follows"] for r in runs] == [True, True, False]

    assert result.status == "failed" and result.success is False
    assert result.error.startswith("the root check at the end of the build could not run")
    assert "the package registry could not be reached" in result.error
    gate = result.wave_results[-1].smoke_gate_result
    assert gate is not None and gate.passed is False and gate.timed_out is False
    assert gate.command == END_ROOT_CHECK_GATE
    assert _feature_check_record(worktree) is None, "the whole-feature check never ran"
    assert "GUARDKIT_STOPPED_BECAUSE" not in capsys.readouterr().out


def test_a_root_check_that_could_not_run_and_is_repaired_goes_on(tmp_path: Path) -> None:
    repo_root, worktree = _project(tmp_path, toolchain=TOOLCHAIN_WITH_A_FAILING_INSTALL)
    feature = _feature(worktree)
    builder = _Builder(worktree, {2: lambda wt: _write(wt, "apps/api/install.sh", "exit 0\n")})

    result = _build(repo_root, worktree, feature, builder, end_review=True)

    assert len(builder.repairs()) == 1
    assert [r["status"] for r in _root_record(worktree)["runs"]] == ["unverified", "passed"]
    assert _feature_check_record(worktree)["status"] == "passed"
    assert result.status == "completed", result.error
