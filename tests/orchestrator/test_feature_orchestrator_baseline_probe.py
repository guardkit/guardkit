"""Wave-0 baseline-green probe (red-baseline retro, L12 item 1).

After bootstrap / before wave 1, the orchestrator runs the suite once, records
baseline.json, and warns (report-only) when the base suite is already red — so
a pre-existing failure is a wave-0 warning, never attributed to the first
task's Coach.

Which suite it runs is Rich's ruling of 2026-09-10: the feature's own smoke
command when it declares one, and otherwise the repository's declared test
command, so a repair — which declares no smoke command — measures its base
too. With neither, nothing runs and nothing is written, exactly as before.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from guardkit.orchestrator.baseline import (
    SOURCE_FEATURE_SMOKE,
    SOURCE_REPOSITORY_TEST,
    compute_charged_failures,
    feature_baseline_path,
    read_baseline_from_worktree,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureExecution,
    FeatureOrchestration,
    FeatureTask,
    SmokeGates,
)
from guardkit.orchestrator.feature_orchestrator import (
    _BASELINE_DECLARED_SUITE_TIMEOUT,
    FeatureOrchestrator,
)
from guardkit.orchestrator.smoke_gates import SmokeGateResult
from guardkit.worktrees import Worktree


def _orchestrator(tmp_path):
    return FeatureOrchestrator(
        repo_root=tmp_path,
        worktree_manager=MagicMock(),
        task_timeout=3000,
        timeout_multiplier=1.0,
        max_turns=5,
    )


def _feature(smoke_command):
    return Feature(
        id="FEAT-X",
        name="F",
        description="d",
        created="2026-07-09T00:00:00Z",
        status="in_progress",
        complexity=5,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-A-001", name="a",
                file_path=Path("tasks/backlog/TASK-A-001.md"),
                complexity=3, dependencies=[], status="pending",
                implementation_mode="task-work", estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-A-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
        smoke_gates=SmokeGates(after_wave="all", command=smoke_command, expected_exit=0),
    )


def _worktree(path):
    return Worktree(
        task_id="FEAT-X", branch_name="autobuild/FEAT-X",
        path=path, base_branch="main",
    )


def _pytest_command(target: str) -> str:
    """A real pytest command, run by the interpreter running these tests.

    A bare ``python`` here resolves off PATH, which in this checkout is a
    virtual environment that has no pytest in it — so the probe measured
    "could not import pytest" instead of the failing test the case is about.
    Naming the running interpreter keeps the subprocess real and the
    measurement about the code.
    """
    return f'"{sys.executable}" -m pytest -q {target}'


def test_red_baseline_records_and_warns(tmp_path, caplog):
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_slice.py").write_text(
        "def test_home():\n    assert 'english' == 'maths'\n"
    )
    orch = _orchestrator(tmp_path)
    feature = _feature(_pytest_command("test_slice.py"))

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))

    baseline = orch._measured_baseline
    assert baseline is not None
    assert baseline.passed is False
    assert any("test_home" in nid for nid in baseline.failing_node_ids)

    # baseline.json persisted under the feature dir.
    loaded = read_baseline_from_worktree(wt)
    assert loaded is not None and loaded.passed is False

    # Wave-0 warning fired (report-only).
    assert any(
        "not attributable to any task" in r.getMessage() for r in caplog.records
    )


def test_green_baseline_records_no_warning(tmp_path, caplog):
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    orch = _orchestrator(tmp_path)
    feature = _feature(_pytest_command("test_ok.py"))

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))

    assert orch._measured_baseline is not None
    assert orch._measured_baseline.passed is True
    assert not any(
        "not attributable to any task" in r.getMessage() for r in caplog.records
    )


def test_no_smoke_gates_skips_probe(tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    orch = _orchestrator(tmp_path)
    feature = _feature("python -m pytest -q")
    feature.smoke_gates = None

    orch._run_baseline_probe(feature, _worktree(wt))
    assert orch._measured_baseline is None
    assert read_baseline_from_worktree(wt) is None


# ---------------------------------------------------------------------------
# Rich's ruling, 2026-09-10: measure the base on every build that can be
# measured. When the feature declares no smoke command, the probe runs the
# REPOSITORY's declared test command instead. Still report-only.
# ---------------------------------------------------------------------------


def _declare_test_command(worktree_path: Path, command: str) -> None:
    """Write the repository's own toolchain declaration into the worktree."""
    import yaml

    config_dir = worktree_path / ".guardkit"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": {"test": command}}), encoding="utf-8"
    )


def _recording_runner(monkeypatch, result):
    """Replace the one runner with a recorder, and hand back the record.

    The runner is the seam: this proves WHICH command the probe handed it and
    with what settings, without running anything.
    """
    calls = []

    def _fake(config, cwd, wave_number, venv_python=None):
        calls.append(
            {
                "command": config.command,
                "expected_exit": config.expected_exit,
                "timeout": config.timeout,
                "cwd": cwd,
                "wave_number": wave_number,
                "venv_python": venv_python,
            }
        )
        return result

    monkeypatch.setattr(
        "guardkit.orchestrator.feature_orchestrator.run_smoke_gate", _fake
    )
    return calls


def _smoke_result(command, passed=True, exit_code=0, stdout=""):
    return SmokeGateResult(
        passed=passed,
        exit_code=exit_code,
        stdout=stdout,
        stderr="",
        timed_out=False,
        command=command,
        timeout=120,
        after_wave=0,
    )


def test_feature_smoke_command_still_runs_exactly_as_today(tmp_path, monkeypatch):
    """A feature that declares a smoke command is untouched by the ruling.

    Same command, same expected exit, same timeout, same working directory —
    and the repository's declaration is not consulted at all, even when one is
    sitting right there.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    _declare_test_command(wt, "the-repository-command-that-must-not-run")
    orch = _orchestrator(tmp_path)
    smoke_command = _pytest_command("test_slice.py")
    feature = _feature(smoke_command)

    calls = _recording_runner(monkeypatch, _smoke_result(smoke_command))
    orch._run_baseline_probe(feature, _worktree(wt))

    assert len(calls) == 1
    assert calls[0]["command"] == smoke_command
    assert calls[0]["expected_exit"] == 0
    assert calls[0]["timeout"] == 120
    assert Path(calls[0]["cwd"]) == wt
    assert calls[0]["wave_number"] == 0
    assert orch._measured_baseline is not None
    assert orch._measured_baseline.source == SOURCE_FEATURE_SMOKE


def test_no_smoke_command_runs_the_repository_declaration(tmp_path, caplog):
    """A repair declares no smoke command — the repository's suite measures it.

    Real command, real subprocess, real red base: this is the case that could
    never be measured before the ruling.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_slice.py").write_text(
        "def test_home():\n    assert 'english' == 'maths'\n"
    )
    declared = _pytest_command("test_slice.py")
    _declare_test_command(wt, declared)
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))

    baseline = orch._measured_baseline
    assert baseline is not None
    assert baseline.command == declared
    assert baseline.source == SOURCE_REPOSITORY_TEST
    assert baseline.passed is False
    assert any("test_home" in nid for nid in baseline.failing_node_ids)

    # The record is on disk, and it names the command and where it came from.
    loaded = read_baseline_from_worktree(wt)
    assert loaded is not None
    assert loaded.command == declared
    assert loaded.source == SOURCE_REPOSITORY_TEST

    # A red base is still named in today's words — never charged to a task.
    assert any(
        "not attributable to any task" in r.getMessage() for r in caplog.records
    )
    assert any("BASELINE RED" in r.getMessage() for r in caplog.records)


def test_declared_suite_gets_whole_suite_headroom(tmp_path, monkeypatch):
    """The declared command is a whole suite, so it gets a whole suite's time."""
    wt = tmp_path / "wt"
    wt.mkdir()
    _declare_test_command(wt, "python -m pytest -q")
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    calls = _recording_runner(monkeypatch, _smoke_result("python -m pytest -q"))
    orch._run_baseline_probe(feature, _worktree(wt))

    assert calls[0]["command"] == "python -m pytest -q"
    assert calls[0]["expected_exit"] == 0
    assert calls[0]["timeout"] == _BASELINE_DECLARED_SUITE_TIMEOUT
    assert calls[0]["timeout"] > 120


def test_neither_command_declared_runs_nothing_and_writes_nothing(
    tmp_path, monkeypatch
):
    """No smoke command and no declaration: byte for byte as before.

    The runner is never called, no baseline is held, nothing is written.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    calls = _recording_runner(monkeypatch, _smoke_result("never-run"))
    orch._run_baseline_probe(feature, _worktree(wt))

    assert calls == []
    assert orch._measured_baseline is None
    assert read_baseline_from_worktree(wt) is None
    assert not (wt / ".guardkit" / "autobuild").exists()


def test_empty_declaration_is_the_same_as_none(tmp_path, monkeypatch):
    """A repository whose declaration carries no test command changes nothing."""
    wt = tmp_path / "wt"
    wt.mkdir()
    config_dir = wt / ".guardkit"
    config_dir.mkdir(parents=True)
    (config_dir / "config.yaml").write_text(
        'toolchain:\n  lint: "ruff check ."\n', encoding="utf-8"
    )
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    calls = _recording_runner(monkeypatch, _smoke_result("never-run"))
    orch._run_baseline_probe(feature, _worktree(wt))

    assert calls == []
    assert orch._measured_baseline is None
    assert read_baseline_from_worktree(wt) is None


def test_probe_command_that_cannot_start_warns_and_does_not_block(
    tmp_path, caplog
):
    """A command that is not there is one warning line — never a stopped build."""
    wt = tmp_path / "wt"
    wt.mkdir()
    _declare_test_command(wt, "guardkit-no-such-command-exists-here --run")
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))  # must not raise

    assert any(
        "not attributable to any task" in r.getMessage() for r in caplog.records
    )


def test_probe_runner_blowing_up_is_one_warning_and_nothing_else(
    tmp_path, caplog, monkeypatch
):
    """If the runner itself raises, the probe is silent about everything else."""
    wt = tmp_path / "wt"
    wt.mkdir()
    _declare_test_command(wt, "python -m pytest -q")
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    def _boom(config, cwd, wave_number, venv_python=None):
        raise RuntimeError("the runner fell over")

    monkeypatch.setattr(
        "guardkit.orchestrator.feature_orchestrator.run_smoke_gate", _boom
    )

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))  # must not raise

    assert orch._measured_baseline is None
    assert read_baseline_from_worktree(wt) is None
    assert any(
        "Baseline probe could not run" in r.getMessage() for r in caplog.records
    )


def test_the_coach_still_receives_what_it_received_before(tmp_path):
    """The Coach's baseline diff reads the same record, with one line added.

    It reads ``read_baseline_from_worktree``; the fields its diff uses are
    unchanged, and a baseline.json written before the source line existed
    still loads.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_slice.py").write_text(
        "def test_home():\n    assert 'english' == 'maths'\n"
    )
    _declare_test_command(wt, _pytest_command("test_slice.py"))
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    orch._run_baseline_probe(feature, _worktree(wt))

    loaded = read_baseline_from_worktree(wt)
    assert loaded is not None
    assert loaded.passed is False
    assert loaded.failing_count == len(loaded.failing_node_ids) >= 1
    # The diff's own input: a failure the base already had is not charged.
    charged = compute_charged_failures(
        observed_node_ids=list(loaded.failing_node_ids) + ["test_new.py::test_new"],
        baseline_node_ids=loaded.failing_node_ids,
        ledger_ids=set(),
    )
    assert charged == ["test_new.py::test_new"]

    # An older record, written before the source line existed, still loads.
    path = feature_baseline_path(wt, "FEAT-X")
    older = json.loads(path.read_text(encoding="utf-8"))
    older.pop("source")
    path.write_text(json.dumps(older), encoding="utf-8")
    reread = read_baseline_from_worktree(wt)
    assert reread is not None
    assert reread.source == ""
    assert reread.failing_node_ids == loaded.failing_node_ids
