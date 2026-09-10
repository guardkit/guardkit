"""Wave-0 baseline-green probe (red-baseline retro, L12 item 1).

After bootstrap / before wave 1, the orchestrator runs the suite once, records
baseline.json, and warns (report-only) when the base suite is already red — so
a pre-existing failure is a wave-0 warning, never attributed to the first
task's Coach.

Which suite it runs is Rich's ruling of 2026-09-10: the feature's own smoke
command when it declares one, and otherwise the repository's declared test
command, so a repair — which declares no smoke command — measures its base
too. With neither, nothing runs and nothing is written, exactly as before.

Three rules these tests pin, because all three decide what the Coach and the
work leg subtract before charging a task with a failure:

* the declaration is read from the REPOSITORY ROOT, never from the copy inside
  the worktree the model edits;
* a worktree is measured ONCE — a base already recorded there is kept, never
  re-measured, because on a resumed build the probe would otherwise file this
  build's own breakage as pre-existing; and
* a run that measured nothing writes no record at all — a record is written
  only when the run named a failing test, or passed with evidence tests ran.
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


def _declare_test_command(root: Path, command: str) -> None:
    """Write a repository's toolchain declaration under ``root``.

    Tests pass the REPOSITORY ROOT for the real declaration, and the worktree
    path only when they are deliberately planting one the probe must ignore.
    """
    import yaml

    config_dir = root / ".guardkit"
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
    _declare_test_command(tmp_path, "the-repository-command-that-must-not-run")
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
    _declare_test_command(tmp_path, declared)
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
    _declare_test_command(tmp_path, "python -m pytest -q")
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
    config_dir = tmp_path / ".guardkit"
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


def test_probe_command_that_cannot_start_records_nothing(tmp_path, caplog):
    """A command that is not there measured nothing, so nothing is written.

    Before this rule it was written down as "BASELINE RED — pre-existing test
    failures" with no test names at all, and finalize then re-ran the same
    missing command, found no failing ids in "command not found", and called
    the branch clean. One warning line, no record, no stopped build.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    _declare_test_command(tmp_path, "guardkit-no-such-command-exists-here --run")
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))  # must not raise

    assert orch._measured_baseline is None
    assert read_baseline_from_worktree(wt) is None
    assert not (wt / ".guardkit" / "autobuild").exists()
    assert any(
        "did not measure the base" in r.getMessage() for r in caplog.records
    )
    # And it is NOT dressed up as a measured red base.
    assert not any(
        "BASELINE RED" in r.getMessage() for r in caplog.records
    )


def test_probe_that_collected_no_tests_records_nothing(tmp_path, caplog):
    """A declared suite that collected nothing is not a green base.

    Real pytest, real subprocess, exit 5. The runner soft-passes that code, so
    without this rule the build was told "the base is GREEN" on the strength
    of a suite that never ran a test.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "nothing_here").mkdir()
    _declare_test_command(tmp_path, _pytest_command("nothing_here"))
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))

    assert orch._measured_baseline is None
    assert read_baseline_from_worktree(wt) is None
    assert any(
        "did not measure the base" in r.getMessage() for r in caplog.records
    )


def test_probe_that_timed_out_records_nothing(tmp_path, caplog, monkeypatch):
    """A suite that ran out of time measured nothing either.

    The declared command gets ten minutes; a repository whose own suite takes
    longer will hit this on every build, so it must be ordinary and quiet
    rather than a red base nobody can explain.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    _declare_test_command(tmp_path, "python -m pytest -q")
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    timed_out = SmokeGateResult(
        passed=False, exit_code=-1, stdout="", stderr="",
        timed_out=True, command="python -m pytest -q",
        timeout=_BASELINE_DECLARED_SUITE_TIMEOUT, after_wave=0,
    )
    _recording_runner(monkeypatch, timed_out)

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))

    assert orch._measured_baseline is None
    assert read_baseline_from_worktree(wt) is None
    assert any(
        "ran out of its" in r.getMessage() for r in caplog.records
    )


def test_feature_smoke_path_is_untouched_by_the_did_not_measure_rule(
    tmp_path, monkeypatch
):
    """The rule is scoped to the declared path; the smoke path is as it was.

    A feature smoke gate that collects no tests is soft-passed by the runner
    today and recorded as a green base. That is existing behaviour for every
    feature that declares a smoke command, and this lane does not change it.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    feature = _feature("pytest -q features/FEAT-X.feature")
    orch = _orchestrator(tmp_path)

    _recording_runner(
        monkeypatch,
        _smoke_result("pytest -q features/FEAT-X.feature", passed=True, exit_code=5),
    )
    orch._run_baseline_probe(feature, _worktree(wt))

    assert orch._measured_baseline is not None
    assert orch._measured_baseline.passed is True
    assert orch._measured_baseline.source == SOURCE_FEATURE_SMOKE


def test_a_declaration_planted_in_the_worktree_is_ignored(tmp_path, caplog):
    """The model's own copy of the declaration cannot decide the base.

    The worktree is the tree the model edits, and on a resumed build the probe
    runs over a worktree that has already had turns in it. A planted command
    that prints a failing test id and exits 1 would otherwise write a base
    naming that test as already broken — and the Coach and the work leg
    subtract exactly that list before charging a task.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    _declare_test_command(
        wt, 'echo "FAILED tests/payments.py::test_refund"; exit 1'
    )
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))

    # The repository root declares nothing, so nothing ran and nothing is held.
    assert orch._measured_baseline is None
    assert read_baseline_from_worktree(wt) is None


def test_the_repository_root_declaration_wins_over_the_worktree_copy(tmp_path):
    """Both copies exist and disagree: the root's command is the one that runs."""
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_slice.py").write_text(
        "def test_home():\n    assert 'english' == 'maths'\n"
    )
    honest = _pytest_command("test_slice.py")
    _declare_test_command(tmp_path, honest)
    _declare_test_command(
        wt, 'echo "FAILED tests/payments.py::test_refund"; exit 1'
    )
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    orch._run_baseline_probe(feature, _worktree(wt))

    baseline = orch._measured_baseline
    assert baseline is not None
    assert baseline.command == honest
    assert any("test_home" in nid for nid in baseline.failing_node_ids)
    assert not any(
        "test_refund" in nid for nid in baseline.failing_node_ids
    )


def test_probe_runner_blowing_up_is_one_warning_and_nothing_else(
    tmp_path, caplog, monkeypatch
):
    """If the runner itself raises, the probe is silent about everything else."""
    wt = tmp_path / "wt"
    wt.mkdir()
    _declare_test_command(tmp_path, "python -m pytest -q")
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
    _declare_test_command(tmp_path, _pytest_command("test_slice.py"))
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


# ---------------------------------------------------------------------------
# What "measured nothing" really covers. Not a list of exit codes to distrust:
# the shapes below all look like ordinary runs by their exit code alone, and
# every one of them would otherwise be written down as a base the Coach
# subtracts and finalize re-runs.
# ---------------------------------------------------------------------------


def test_a_declared_command_that_cannot_import_pytest_records_nothing(
    tmp_path, caplog
):
    """Exit 1 with no test named is nothing measured, not a red base.

    The commonest "the test runner never started" shape in Python: a declared
    command whose interpreter has no pytest in it prints "No module named
    pytest" and exits 1 — indistinguishable by exit code from a suite that ran
    and failed. Written down, that is a red base naming nothing; finalize then
    re-runs the same command, reads no failing ids out of it and reports the
    branch clean, turning "a person must look" into "nothing to see".

    Real subprocess, real interpreter: ``-S -E`` starts the project's own
    python without its site-packages, so the import genuinely fails.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_slice.py").write_text("def test_ok():\n    assert True\n")
    _declare_test_command(tmp_path, f'"{sys.executable}" -S -E -m pytest -q')
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))

    assert orch._measured_baseline is None
    assert read_baseline_from_worktree(wt) is None
    assert not (wt / ".guardkit" / "autobuild").exists()
    assert any(
        "did not measure the base" in r.getMessage() for r in caplog.records
    )
    assert not any("BASELINE RED" in r.getMessage() for r in caplog.records)


def test_a_declared_command_that_exits_clean_without_testing_records_nothing(
    tmp_path, caplog
):
    """Exit 0 with no evidence a test ran is not a green base.

    The estate's own rule for a clean exit with nothing to show for it:
    unverified, never a pass. A green base invented this way is the quiet
    version of the same damage — finalize re-runs the same do-nothing command,
    finds no reds, and calls the branch clean.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    _declare_test_command(tmp_path, 'echo "nothing to do here"')
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))

    assert orch._measured_baseline is None
    assert read_baseline_from_worktree(wt) is None
    assert any(
        "did not measure the base" in r.getMessage() for r in caplog.records
    )


def test_a_real_green_suite_is_still_recorded(tmp_path):
    """The rule must not swallow an honest pass: real pytest, real "1 passed"."""
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    _declare_test_command(tmp_path, _pytest_command("test_ok.py"))
    orch = _orchestrator(tmp_path)
    feature = _feature("unused")
    feature.smoke_gates = None

    orch._run_baseline_probe(feature, _worktree(wt))

    baseline = orch._measured_baseline
    assert baseline is not None
    assert baseline.passed is True
    assert baseline.source == SOURCE_REPOSITORY_TEST
    assert read_baseline_from_worktree(wt) is not None


# ---------------------------------------------------------------------------
# A worktree is measured ONCE. On --resume the setup phase hands back the
# worktree the model has already been editing, so a second measurement would
# record this build's own breakage as pre-existing — and the Coach and
# finalize subtract exactly that.
# ---------------------------------------------------------------------------


def test_a_base_already_recorded_in_the_worktree_is_kept_not_re_measured(
    tmp_path, monkeypatch
):
    """The resumed build: the true base survives and nothing runs again.

    Wave 0 measures a green base. Wave 1 breaks a test. The operator resumes,
    and the probe must NOT overwrite the record with the damage the build did
    to itself — otherwise the regression this build introduced is subtracted
    by the Coach and by finalize, and the branch reports clean.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_pay.py").write_text("def test_refund():\n    assert True\n")
    declared = _pytest_command("test_pay.py")
    _declare_test_command(tmp_path, declared)
    feature = _feature("unused")
    feature.smoke_gates = None

    first = _orchestrator(tmp_path)
    first._run_baseline_probe(feature, _worktree(wt))
    measured = read_baseline_from_worktree(wt)
    assert measured is not None
    assert measured.passed is True
    assert measured.failing_node_ids == []

    # Wave 1 breaks the test, then the build is resumed over the same worktree.
    (wt / "test_pay.py").write_text("def test_refund():\n    assert False\n")
    resumed = _orchestrator(tmp_path)
    resumed.resume = True
    calls = _recording_runner(
        monkeypatch, _smoke_result(declared, passed=False, exit_code=1)
    )

    resumed._run_baseline_probe(feature, _worktree(wt))

    assert calls == []  # nothing was measured a second time
    kept = read_baseline_from_worktree(wt)
    assert kept is not None
    assert kept.passed is True
    assert kept.failing_node_ids == []
    assert kept.timestamp == measured.timestamp
    # And the Coach is handed the base that was true before the build began.
    assert resumed._measured_baseline is not None
    assert resumed._measured_baseline.passed is True


def test_the_keep_rule_covers_the_feature_smoke_path_too(tmp_path, monkeypatch):
    """An existing record is kept whichever command would have measured it.

    A feature with a smoke command is resumed the same way and can do the same
    damage, so the keep rule is not scoped to the declared path. Nothing about
    a FIRST run changes: a fresh worktree carries no record.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    smoke_command = _pytest_command("test_ok.py")
    feature = _feature(smoke_command)

    first = _orchestrator(tmp_path)
    first._run_baseline_probe(feature, _worktree(wt))
    measured = read_baseline_from_worktree(wt)
    assert measured is not None
    assert measured.source == SOURCE_FEATURE_SMOKE

    calls = _recording_runner(
        monkeypatch, _smoke_result(smoke_command, passed=False, exit_code=1)
    )
    second = _orchestrator(tmp_path)
    second._run_baseline_probe(feature, _worktree(wt))

    assert calls == []
    kept = read_baseline_from_worktree(wt)
    assert kept is not None
    assert kept.passed is True
    assert kept.timestamp == measured.timestamp


def test_a_resumed_build_with_no_recorded_base_measures_nothing(
    tmp_path, monkeypatch, caplog
):
    """Nothing to keep, and nothing safe to measure — so it measures nothing.

    A repair whose first attempt could not measure its base resumes into a
    worktree the model has already had turns in. There is no honest base left
    to take, so none is taken: the build carries on with no measured base,
    which is where every repair stood before this ruling, and it fails closed —
    finalize makes a person look.
    """
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_pay.py").write_text("def test_refund():\n    assert False\n")
    _declare_test_command(tmp_path, _pytest_command("test_pay.py"))
    orch = _orchestrator(tmp_path)
    orch.resume = True
    feature = _feature("unused")
    feature.smoke_gates = None

    calls = _recording_runner(monkeypatch, _smoke_result("never-run"))
    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))

    assert calls == []
    assert orch._measured_baseline is None
    assert read_baseline_from_worktree(wt) is None
    assert not (wt / ".guardkit" / "autobuild").exists()
    assert any(
        "resumed build" in r.getMessage() for r in caplog.records
    )


def test_a_first_build_still_measures_its_base(tmp_path):
    """The keep rule must not stop a first build measuring: fresh worktree, no record."""
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_pay.py").write_text("def test_refund():\n    assert False\n")
    _declare_test_command(tmp_path, _pytest_command("test_pay.py"))
    orch = _orchestrator(tmp_path)
    assert orch.resume is False
    feature = _feature("unused")
    feature.smoke_gates = None

    orch._run_baseline_probe(feature, _worktree(wt))

    baseline = orch._measured_baseline
    assert baseline is not None
    assert baseline.passed is False
    assert any("test_refund" in nid for nid in baseline.failing_node_ids)
