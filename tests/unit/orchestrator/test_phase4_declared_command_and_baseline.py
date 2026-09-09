"""The work leg runs what the repository declares, and judges it ZERO NET-NEW.

Rich's two rulings of 2026-09-09, pinned:

1. **A work leg checks its work with the command the repository declares.**
   Before this, the leg ran a bare venv-pinned pytest while the merge-ready
   checkpoint ran the declared command — so a database test failed in the leg
   and passed at the checkpoint, and one fix journey died in that fork
   twenty-six times.
2. **The bar is zero net-new, not all green.** No real repository is all
   green. A leg that demanded green would fail on every red repository for
   ever, and one that cannot tell new red from old red teaches everybody to
   ignore red.

Everything here runs for real: real temporary repositories, and a real
subprocess wherever the runner is the seam — the declared command is an
ordinary shell script that prints pytest-shaped output and exits with a code
we choose. There is no database anywhere, and no model is called.
"""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import pytest
import yaml

from guardkit.orchestrator import specialist_invocations as si
from guardkit.orchestrator.quality_gates import coach_validator as cv
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain


_TASK_ID = "TASK-LEG-0001"
_FEATURE_ID = "FEAT-LEG"
_DECLARED = "bash qa/run-suite.sh"


# ---------------------------------------------------------------------------
# a real little repository
# ---------------------------------------------------------------------------


def _worktree(tmp_path: Path) -> tuple[Path, Path]:
    """Repo root + the worktree beneath it, laid out as autobuild does."""
    root = tmp_path / "target-repo"
    worktree = root / ".guardkit" / "worktrees" / _TASK_ID
    worktree.mkdir(parents=True)
    return root, worktree


def _declare(root: Path, worktree: Path, command: str = _DECLARED) -> None:
    """Write ``.guardkit/config.yaml`` and take the pre-turn-1 snapshot — the
    real sequence, so these tests exercise the snapshot seam too."""
    cfg = root / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": {"test": command}}), encoding="utf-8"
    )
    snapshot_task_toolchain(_TASK_ID, worktree, root)


def _suite_script(worktree: Path, output: str, exit_code: int) -> None:
    """A real ``qa/run-suite.sh``: prints pytest-shaped output, exits as told.

    This stands in for api_test's own script, which brings up a throwaway
    PostgreSQL, runs the suite and takes it down. Nothing is stood up here —
    the point being pinned is which command runs and how its result is read.
    """
    qa = worktree / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    script = qa / "run-suite.sh"
    body = "\n".join(f"echo {line!r}" for line in output.splitlines())
    script.write_text(f"#!/bin/sh\n{body}\nexit {exit_code}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)


def _ledger(worktree: Path, test_ids: list) -> None:
    """The repository's own known-failure ledger, ``qa/known-failures.yaml``."""
    qa = worktree / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "known-failures.yaml").write_text(
        yaml.safe_dump(
            {
                "suite_id": "leg-test",
                "framework": "pytest",
                "language": "python",
                "expected": {"passed": 3},
                "known_failures": [
                    {
                        "test_id": tid,
                        "reason": "triaged, tracked, stable",
                        "since": {"date": "2026-09-01", "sha": "abc1234"},
                        "owner": "rich",
                        "review_by": "2026-10-01",
                    }
                    for tid in test_ids
                ],
            }
        ),
        encoding="utf-8",
    )


def _measured_baseline(worktree: Path, failing: list) -> None:
    """The build's wave-0 baseline: the suite run once on this branch's base."""
    path = worktree / ".guardkit" / "autobuild" / _FEATURE_ID / "baseline.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "command": _DECLARED,
                "expected_exit": 0,
                "passed": not failing,
                "exit_code": 1 if failing else 0,
                "failing_node_ids": failing,
                "failing_count": len(failing),
                "timestamp": "2026-09-09T00:00:00",
            }
        ),
        encoding="utf-8",
    )


def _task_work_results(worktree: Path, authored: Optional[list] = None) -> None:
    path = worktree / ".guardkit" / "autobuild" / _TASK_ID / "task_work_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"files_modified": list(authored or [])}), encoding="utf-8"
    )


def _invoker() -> MagicMock:
    invoker = MagicMock()
    invoker._venv_python = None
    return invoker


def _leg(worktree: Path, **kwargs):
    return si._run_deterministic_phase_4(
        worktree_path=worktree,
        task_id=_TASK_ID,
        agent_invoker=_invoker(),
        sdk_timeout=120,
        turn=1,
        **kwargs,
    )


# Two failures, three passes: a suite that visibly did work.
_TWO_RED = (
    "FAILED tests/test_users.py::test_delete_twice - AssertionError\n"
    "FAILED tests/test_orders.py::test_totals - AssertionError\n"
    "2 failed, 3 passed in 1.20s\n"
)


# =========================================================================
# 1. The leg runs the DECLARED command — and so does the Coach, the same one
# =========================================================================


class TestTheLegRunsWhatTheRepositoryDeclares:
    def test_the_declared_command_is_the_one_that_runs(self, tmp_path: Path):
        root, worktree = _worktree(tmp_path)
        _declare(root, worktree)
        _suite_script(worktree, "3 passed in 0.40s", 0)

        block = _leg(worktree)

        assert block is not None
        assert block["status"] == "passed"
        assert block["test_command"] == _DECLARED
        assert block["test_command_source"] == "repository toolchain declaration"

    def test_the_leg_and_the_coach_run_ONE_command(self, tmp_path: Path):
        """(b) The identity is the reason the deterministic phase exists.

        Both sides ask the same method for the command, so they cannot
        disagree. Proved by running both for real against the same worktree
        and comparing what each says it ran.
        """
        root, worktree = _worktree(tmp_path)
        _declare(root, worktree)
        _suite_script(worktree, "3 passed in 0.40s", 0)

        leg_block = _leg(worktree)

        coach = CoachValidator(
            worktree_path=str(worktree),
            task_id=_TASK_ID,
            coach_test_execution="subprocess",
            test_timeout=120,
        )
        coach_result = coach.run_independent_tests(turn=1)

        assert leg_block is not None
        assert leg_block["test_command"] == coach_result.test_command == _DECLARED

    def test_a_repository_declaring_nothing_is_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """(f) Nothing declared ⇒ the venv-pinned pytest on the task's own
        test files, the same argv as before this lane existed."""
        root, worktree = _worktree(tmp_path)
        (worktree / "pyproject.toml").write_text("[project]\nname='x'\n")
        tests_dir = worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_leg_0001_thing.py").write_text("def test_x():\n    pass\n")
        _task_work_results(worktree, ["tests/test_leg_0001_thing.py"])
        venv_python = worktree / ".venv" / "bin" / "python"
        venv_python.parent.mkdir(parents=True)
        venv_python.symlink_to(sys.executable)

        # The runner is the seam: record the argv, then let the REAL
        # subprocess run — this is a genuine pytest run on a real file.
        seen: list = []
        real_run = cv.subprocess.run

        def _capture(cmd, *args, **kwargs):
            seen.append((cmd, kwargs.get("shell", False)))
            return real_run(cmd, *args, **kwargs)

        monkeypatch.setattr(cv.subprocess, "run", _capture)

        block = _leg(worktree)

        assert block is not None
        assert block["test_command_source"] != "repository toolchain declaration"
        assert block["test_command"].startswith("pytest ")
        assert "test_leg_0001_thing.py" in block["test_command"]
        # The pytest run itself, past any interpreter probes the runner makes.
        runs = [
            (argv, shell)
            for argv, shell in seen
            if isinstance(argv, list) and argv[1:3] == ["-m", "pytest"]
        ]
        assert len(runs) == 1
        argv, shell = runs[0]
        assert shell is False
        # The argv, word for word: the pinned interpreter, ``-m pytest``, the
        # chosen command's own words, and then only the isolation/timeout
        # flags the runner has always appended.
        chosen = block["test_command"].split()
        head = [str(venv_python), "-m", "pytest"] + chosen[1:]
        assert argv[: len(head)] == head
        tail = argv[len(head):]
        assert set(a for a in tail if a.startswith("-")) <= {
            "--basetemp",
            "--timeout",
        }
        # Nothing was forgiven, because nothing was compared: the task's own
        # tests are the task's own responsibility.
        assert block.get("failures_total") in (None, 0)


# =========================================================================
# 2. The verdict is ZERO NET-NEW
# =========================================================================


class TestZeroNetNew:
    def test_all_failures_already_on_the_base_pass_the_leg(self, tmp_path: Path):
        """(f) Every failure inherited ⇒ the leg passes, and the record says
        how many it forgave and on whose word."""
        root, worktree = _worktree(tmp_path)
        _declare(root, worktree)
        _suite_script(worktree, _TWO_RED, 1)
        _ledger(
            worktree,
            [
                "tests/test_users.py::test_delete_twice",
                "tests/test_orders.py::test_totals",
            ],
        )
        _task_work_results(worktree, ["app/users.py"])

        block = _leg(worktree)

        assert block is not None
        assert block["status"] == "passed"
        assert block["failures_total"] == 2
        assert block["failures_inherited"] == 2
        assert block["failures_new"] == 0
        assert block["new_failing_tests"] == []
        assert "known-failure ledger" in block["baseline_source"]
        assert "already failing on the base" in block["baseline_note"]

    def test_one_failure_outside_the_base_fails_naming_only_that_one(
        self, tmp_path: Path
    ):
        """(a4) A red leg naming twenty failures of which nineteen are
        inherited is a leg nobody reads."""
        root, worktree = _worktree(tmp_path)
        _declare(root, worktree)
        _suite_script(worktree, _TWO_RED, 1)
        _measured_baseline(worktree, ["tests/test_orders.py::test_totals"])
        _task_work_results(worktree, ["app/users.py"])

        block = _leg(worktree)

        assert block is not None
        assert block["status"] == "failed"
        assert block["failures_total"] == 2
        assert block["failures_inherited"] == 1
        assert block["failures_new"] == 1
        assert block["new_failing_tests"] == [
            "tests/test_users.py::test_delete_twice"
        ]
        assert "tests/test_users.py::test_delete_twice" in block["error"]
        assert "tests/test_orders.py::test_totals" not in block["error"]

    def test_a_base_failure_that_passes_now_is_a_stale_record_not_a_failure(
        self, tmp_path: Path
    ):
        """(a3) The record has gone stale in the good direction — one plain
        line, never a failure."""
        root, worktree = _worktree(tmp_path)
        _declare(root, worktree)
        _suite_script(worktree, "5 passed in 0.80s", 0)
        _ledger(worktree, ["tests/test_orders.py::test_totals"])

        block = _leg(worktree)

        assert block is not None
        assert block["status"] == "passed"
        assert block["stale_base_entries"] == [
            "tests/test_orders.py::test_totals"
        ]
        assert "stale in the good direction" in block["baseline_note"]

    def test_an_entirely_red_run_is_never_forgiven(self, tmp_path: Path):
        """(f) A suite where NOTHING passed proves nothing. Even when the
        base's list covers every failure, the leg stays red and says why —
        otherwise a collapsed run (no database, a broken import) would be
        waved through by a long enough ledger."""
        root, worktree = _worktree(tmp_path)
        _declare(root, worktree)
        _suite_script(
            worktree,
            "FAILED tests/test_users.py::test_delete_twice - db is down\n"
            "FAILED tests/test_orders.py::test_totals - db is down\n"
            "2 failed in 0.30s\n",
            1,
        )
        _ledger(
            worktree,
            [
                "tests/test_users.py::test_delete_twice",
                "tests/test_orders.py::test_totals",
            ],
        )

        block = _leg(worktree)

        assert block is not None
        assert block["status"] == "failed"
        assert block["quality_gates_passed"] is False
        assert "nothing passed" in block["baseline_note"]

    def test_with_no_base_on_record_only_this_task_s_own_tests_are_charged(
        self, tmp_path: Path
    ):
        """No measured baseline and no ledger: the leg cannot tell new red
        from old red, says so, and charges only the test files this task
        wrote — exactly what it saw before this lane existed."""
        root, worktree = _worktree(tmp_path)
        _declare(root, worktree)
        _suite_script(worktree, _TWO_RED, 1)
        _task_work_results(worktree, ["tests/test_users.py"])

        block = _leg(worktree)

        assert block is not None
        assert block["status"] == "failed"
        assert block["failures_total"] == 2
        assert block["new_failing_tests"] == [
            "tests/test_users.py::test_delete_twice"
        ]
        assert "not on record" in block["baseline_note"]

    def test_with_no_base_on_record_a_stranger_s_defect_is_not_this_leg_s(
        self, tmp_path: Path
    ):
        """The other half of the fallback: with nothing on record and no
        failure in a file this task touched, the leg does not go red for
        somebody else's defect — it says what it could not compare."""
        root, worktree = _worktree(tmp_path)
        _declare(root, worktree)
        _suite_script(worktree, _TWO_RED, 1)
        _task_work_results(worktree, ["app/pricing.py"])

        block = _leg(worktree)

        assert block is not None
        assert block["status"] == "passed"
        assert block["failures_total"] == 2
        assert block["failures_new"] == 0
        assert "not on record" in block["baseline_note"]

    def test_the_operator_can_turn_every_subtraction_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """The existing kill switch still means what it says: with it off,
        nothing is forgiven anywhere in the build."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_BASELINE_DIFF", "0")
        root, worktree = _worktree(tmp_path)
        _declare(root, worktree)
        _suite_script(worktree, _TWO_RED, 1)
        _ledger(
            worktree,
            [
                "tests/test_users.py::test_delete_twice",
                "tests/test_orders.py::test_totals",
            ],
        )

        block = _leg(worktree)

        assert block is not None
        assert block["status"] == "failed"
        assert block["failures_total"] is None

    def test_a_task_cannot_hide_behind_the_base_for_a_test_it_wrote(
        self, tmp_path: Path
    ):
        """The existing re-charge rule, unchanged: a ledgered failure in a
        file this task itself changed is still this task's."""
        root, worktree = _worktree(tmp_path)
        _declare(root, worktree)
        _suite_script(worktree, _TWO_RED, 1)
        _ledger(
            worktree,
            [
                "tests/test_users.py::test_delete_twice",
                "tests/test_orders.py::test_totals",
            ],
        )
        _task_work_results(worktree, ["tests/test_users.py"])

        block = _leg(worktree)

        assert block is not None
        assert block["status"] == "failed"
        assert block["new_failing_tests"] == [
            "tests/test_users.py::test_delete_twice"
        ]


# =========================================================================
# 3. Absence is never a pass; the record says what ran and what it forgave
# =========================================================================


class TestAbsenceAndTheRecord:
    def test_a_command_that_cannot_start_is_absent_never_a_pass(
        self, tmp_path: Path
    ):
        """(c) The verdict rules do not change. A declared command that is
        not there at all is an absent signal, and absence of failure is not
        success."""
        root, worktree = _worktree(tmp_path)
        _declare(root, worktree, "qa/there-is-no-such-script.sh")
        _ledger(worktree, ["tests/test_users.py::test_delete_twice"])

        block = _leg(worktree)

        assert block is not None
        assert block["status"] == "failed"
        assert block["signal_absent"] is True
        assert block["verifier_infrastructure"] is True
        assert block["quality_gates_passed"] is False

    def test_the_record_names_the_command_its_source_and_the_base(
        self, tmp_path: Path
    ):
        """(d) "What did the verifier actually run, and what did it forgive?"
        is one grep, exactly as the interpreter question already is."""
        root, worktree = _worktree(tmp_path)
        _declare(root, worktree)
        _suite_script(worktree, _TWO_RED, 1)
        _measured_baseline(
            worktree,
            [
                "tests/test_users.py::test_delete_twice",
                "tests/test_orders.py::test_totals",
            ],
        )

        block = _leg(worktree)

        assert block is not None
        assert block["test_command"] == _DECLARED
        assert block["test_command_source"] == "repository toolchain declaration"
        assert "measured baseline" in block["baseline_source"]
        assert block["failures_total"] == 2
        assert block["failures_inherited"] == 2
        assert "resolved_interpreter" in block
