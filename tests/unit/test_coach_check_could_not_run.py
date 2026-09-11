"""A CHECK THAT COULD NOT RUN IS AN ESTATE FAULT, AND THE ISOLATED COPY
CARRIES WHAT THE COMMAND NEEDS.

What happened on 2026-09-11, in one paragraph. A plan put two tasks in the
same wave, so the Coach took its parallel-wave path: copy the worktree into a
temporary directory and run the repository's declared test command there. The
copy deliberately leaves out the heavy directories — which is where the thing
that RUNS the declared command lived — so the command died in a tenth of a
second without testing anything. That non-result was then handed to the coder
as a must-fix, five turns running, for a defect it did not cause and could not
fix; on turn five it deleted two working functions from a module its task never
mentioned. Meanwhile the quality gate recorded the tests as passed.

Three things are pinned here, and none of them mentions a language:

1. **The rule.** "The check ran and the result is bad" and "the check could
   not run" are different outcomes. A check that could not run never reaches
   the builder's feedback, never lets a gate report a pass, and is reported in
   plain words to the operator and the receipt.
2. **The fallback.** When the isolated copy cannot start the check, it runs in
   the real worktree — the run a wave of one already uses. A wave of two must
   not be worse than a wave of one. Only when THAT cannot run either does the
   turn end as an estate fault.
3. **The mechanism.** The copy carries, or reaches, whatever the declared
   command needs, by asking the two things that already know: the repository's
   own toolchain declaration and guardkit's environment bootstrap. Nothing is
   guessed — a guess is shaped like one language and is wrong for the next.

Every test here declares its test command as a plain shell script that needs a
sibling file, so the fix is proved to be stack-agnostic by construction: the
same shape is a missing ``node_modules`` in a TypeScript repository and a
missing module cache in a Go one. No pytest, no interpreter, no package
manager anywhere in the fixtures. Real directories, real subprocesses, in
temporary directories; no network, no broker, no estate service.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
    QualityGateStatus,
)
from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain

_TASK_ID = "TASK-ISO-001"
_DECLARED_COMMAND = "qa/run-suite.sh"


# ---------------------------------------------------------------------------
# A repository that declares a shell test command needing a sibling file
# ---------------------------------------------------------------------------


def _executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)


def _make_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Repo root plus the worktree beneath it, with the command declared."""
    root = tmp_path / "product"
    worktree = root / ".guardkit" / "worktrees" / _TASK_ID
    worktree.mkdir(parents=True)
    (root / ".guardkit").mkdir(parents=True, exist_ok=True)
    (root / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": {"test": _DECLARED_COMMAND}}),
        encoding="utf-8",
    )
    snapshot_task_toolchain(_TASK_ID, worktree, root)
    return root, worktree


def _suite_needing(relative_tool: str) -> str:
    """A test command that needs a sibling file to exist where it runs."""
    return (
        "#!/bin/sh\n"
        'here=$(cd "$(dirname "$0")/.." && pwd)\n'
        f'tool="$here/{relative_tool}"\n'
        'if [ ! -x "$tool" ]; then\n'
        '  echo "run-suite: no runner at $tool" >&2\n'
        "  exit 127\n"
        "fi\n"
        'exec "$tool"\n'
    )


_RUNNER = "#!/bin/sh\necho '3 checks passed'\n"


def _validator(worktree: Path, wave_size: int) -> CoachValidator:
    validator = CoachValidator(
        str(worktree), task_id=_TASK_ID, wave_size=wave_size
    )
    validator._coach_test_execution = "subprocess"
    return validator


# ---------------------------------------------------------------------------
# 1. THE MECHANISM — the copy reaches what the declared command needs
# ---------------------------------------------------------------------------


class TestTheCopyCarriesWhatTheCommandNeeds:
    def test_a_wave_of_two_reaches_a_directory_the_copy_does_not_carry(
        self, tmp_path: Path
    ) -> None:
        """The runner lives in a directory the snapshot never copies. Before
        this fix the isolated run died in a tenth of a second; now it reaches
        the real one and produces a verdict."""
        _root, worktree = _make_repo(tmp_path)
        _executable(worktree / "qa" / "run-suite.sh", _suite_needing("dist/toolbox/runner"))
        _executable(worktree / "dist" / "toolbox" / "runner", _RUNNER)

        result = _validator(worktree, wave_size=2).run_independent_tests()

        assert result.tests_passed is True
        assert result.check_could_not_run is False
        assert result.signal_absent is False
        assert "3 checks passed" in (result.raw_output or "")
        # It ran in the isolated copy: no fallback was needed.
        assert result.isolation_fallback_reason is None

    def test_it_reaches_what_the_bootstrap_recorded_for_this_build(
        self, tmp_path: Path
    ) -> None:
        """ASK WHAT BUILT IT. The runner lives inside guardkit's own state
        directory, which is never carried wholesale — the only way to reach it
        is to read the bootstrap's record of where it put this build's
        environment."""
        _root, worktree = _make_repo(tmp_path)
        _executable(
            worktree / "qa" / "run-suite.sh",
            _suite_needing(".guardkit/buildenv/bin/runner"),
        )
        _executable(worktree / ".guardkit" / "buildenv" / "bin" / "runner", _RUNNER)
        (worktree / ".guardkit" / "bootstrap_state.json").write_text(
            json.dumps(
                {
                    "content_hash": "irrelevant",
                    "success": True,
                    "venv_python": str(
                        worktree / ".guardkit" / "buildenv" / "bin" / "runner"
                    ),
                }
            ),
            encoding="utf-8",
        )

        result = _validator(worktree, wave_size=2).run_independent_tests()

        assert result.tests_passed is True
        assert result.check_could_not_run is False
        assert result.isolation_fallback_reason is None

    def test_a_repository_whose_bootstrap_built_nothing_is_untouched(
        self, tmp_path: Path
    ) -> None:
        """No record, nothing skipped worth reaching: the run is what it was
        before, and a real red is still a real red."""
        _root, worktree = _make_repo(tmp_path)
        _executable(
            worktree / "qa" / "run-suite.sh",
            "#!/bin/sh\necho '1 of 3 checks failed' >&2\nexit 1\n",
        )

        validator = _validator(worktree, wave_size=2)
        assert validator._paths_the_snapshot_must_reach() == []

        result = validator.run_independent_tests()
        assert result.tests_passed is False
        assert result.check_could_not_run is False
        assert result.signal_absent is False


# ---------------------------------------------------------------------------
# 2. THE FALLBACK — a wave of two is never worse than a wave of one
# ---------------------------------------------------------------------------


def _suite_that_only_runs_at_home() -> str:
    """Starts only in its own checkout: in a copy it cannot start at all."""
    return (
        "#!/bin/sh\n"
        'here=$(cd "$(dirname "$0")/.." && pwd)\n'
        'if [ "$here" != "$(cat "$here/qa/home.txt")" ]; then\n'
        '  echo "run-suite: this runner cannot start outside its checkout" >&2\n'
        "  exit 127\n"
        "fi\n"
        "echo '3 checks passed'\n"
    )


class TestTheFallback:
    def test_it_falls_back_to_the_worktree_and_records_why(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        _root, worktree = _make_repo(tmp_path)
        _executable(worktree / "qa" / "run-suite.sh", _suite_that_only_runs_at_home())
        (worktree / "qa" / "home.txt").write_text(str(worktree), encoding="utf-8")

        with caplog.at_level("WARNING"):
            result = _validator(worktree, wave_size=2).run_independent_tests()

        # The verdict a wave of one would have produced.
        assert result.tests_passed is True
        assert result.check_could_not_run is False
        assert result.signal_absent is False
        # And the receipt says plainly that it fell back, and why.
        assert result.isolation_fallback_reason is not None
        assert _DECLARED_COMMAND in result.isolation_fallback_reason
        assert "could not run" in result.isolation_fallback_reason
        assert any(
            "run in the worktree instead" in record.getMessage()
            for record in caplog.records
        )

    def test_when_neither_can_run_the_turn_is_an_estate_fault(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Both runs could not start: the command, both directories and the
        missing thing are named, and nothing reads as a pass."""
        _root, worktree = _make_repo(tmp_path)
        _executable(
            worktree / "qa" / "run-suite.sh", _suite_needing("dist/toolbox/runner")
        )
        # The runner was never built, anywhere.

        with caplog.at_level("ERROR"):
            result = _validator(worktree, wave_size=2).run_independent_tests()

        assert result.check_could_not_run is True
        assert result.tests_passed is False
        assert result.signal_absent is True

        detail = result.check_could_not_run_detail or ""
        assert _DECLARED_COMMAND in detail
        assert "isolated copy" in detail
        assert str(worktree) in detail
        assert "no runner at" in detail
        assert any(
            "could not run" in record.getMessage() for record in caplog.records
        )

    def test_a_wave_of_one_is_unchanged(self, tmp_path: Path) -> None:
        """(d) Nothing about a single-task wave changes: the same unrunnable
        command is the same absent signal it has always been, and it never
        takes the isolated path or the estate-fault path."""
        _root, worktree = _make_repo(tmp_path)
        _executable(
            worktree / "qa" / "run-suite.sh", _suite_needing("dist/toolbox/runner")
        )

        result = _validator(worktree, wave_size=1).run_independent_tests()

        assert result.check_could_not_run is False
        assert result.isolation_fallback_reason is None
        assert result.signal_absent is True
        assert result.tests_passed is False


# ---------------------------------------------------------------------------
# 3. THE RULE — no blame, no pass
# ---------------------------------------------------------------------------


def _task_work_results(all_passed: bool = True) -> Dict[str, Any]:
    return {
        "quality_gates": {
            "tests_run": 12,
            "tests_failed": 0,
            "coverage_met": True,
            "all_passed": all_passed,
        },
        "code_review": {"score": 90},
        "plan_audit": {"violations": 0, "status": "passed"},
        "requirements_met": ["The endpoint answers"],
    }


def _write_task_work_results(worktree: Path) -> None:
    results_dir = worktree / ".guardkit" / "autobuild" / _TASK_ID
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "task_work_results.json").write_text(
        json.dumps(_task_work_results()), encoding="utf-8"
    )


def _could_not_run() -> IndependentTestResult:
    return IndependentTestResult.could_not_run(
        test_command=_DECLARED_COMMAND,
        detail=(
            f"The check could not run. Command: {_DECLARED_COMMAND}. "
            "Directory: an isolated copy of the worktree. What was missing: "
            "the runner the command needs."
        ),
        duration_seconds=0.1,
    )


def _task() -> Dict[str, Any]:
    return {
        "task_type": "feature",
        "acceptance_criteria": ["The endpoint answers"],
    }


class TestTheRule:
    def test_the_quality_gate_does_not_report_a_pass_when_nothing_ran(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The builder's own report says every gate passed. Nothing verified
        it, so the test gate is UNKNOWN — and unknown is not a pass."""
        _root, worktree = _make_repo(tmp_path)
        _write_task_work_results(worktree)
        validator = _validator(worktree, wave_size=2)
        monkeypatch.setattr(
            validator, "run_independent_tests", lambda **kwargs: _could_not_run()
        )

        result = validator.validate(_TASK_ID, 1, _task())

        assert result.quality_gates is not None
        assert result.quality_gates.tests_passed is None
        assert result.quality_gates.all_gates_passed is False
        assert result.decision != "approve"

    def test_the_builders_feedback_says_nothing_about_the_failed_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Assert the ABSENCE. A feedback blob that merely de-emphasises the
        failed check still teaches the coder to chase it, so there must be
        nothing there at all — and the turn must be marked as one the builder
        cannot fix, so the loop stops instead of spending five more turns."""
        _root, worktree = _make_repo(tmp_path)
        _write_task_work_results(worktree)
        validator = _validator(worktree, wave_size=2)
        monkeypatch.setattr(
            validator, "run_independent_tests", lambda **kwargs: _could_not_run()
        )

        result = validator.validate(_TASK_ID, 1, _task())

        assert result.issues == []
        blob = json.dumps(result.issues)
        for word in ("could not run", _DECLARED_COMMAND, "runner", "missing"):
            assert word not in blob
        assert result.is_configuration_error is True

    def test_the_operator_and_the_receipt_are_told_in_plain_words(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        _root, worktree = _make_repo(tmp_path)
        _write_task_work_results(worktree)
        validator = _validator(worktree, wave_size=2)
        monkeypatch.setattr(
            validator, "run_independent_tests", lambda **kwargs: _could_not_run()
        )

        with caplog.at_level("ERROR"):
            result = validator.validate(_TASK_ID, 1, _task())

        assert any(
            "ESTATE FAULT" in record.getMessage() for record in caplog.records
        )
        receipt = result.to_dict()["validation_results"]["independent_tests"]
        assert receipt["check_could_not_run"] is True
        assert _DECLARED_COMMAND in receipt["check_could_not_run_detail"]

    def test_the_evidence_the_coach_reads_carries_the_same_two_facts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The live path is the evidence bundle, not the legacy verdict: the
        gate there must be UNKNOWN too, and nothing may ride to the builder."""
        _root, worktree = _make_repo(tmp_path)
        _write_task_work_results(worktree)
        validator = _validator(worktree, wave_size=2)
        monkeypatch.setattr(
            validator, "run_independent_tests", lambda **kwargs: _could_not_run()
        )

        bundle = validator.gather_evidence(_TASK_ID, 1, _task())

        assert bundle.gathering_status == "complete"
        assert bundle.quality_gates is not None
        assert bundle.quality_gates.tests_passed is None
        assert bundle.quality_gates.all_gates_passed is False
        assert bundle.tests is not None and bundle.tests["tests_passed"] is None
        assert bundle.advisory_issues == []
        serialised = bundle.to_dict()["independent_tests"]
        assert serialised["check_could_not_run"] is True

    def test_a_check_that_ran_and_failed_is_still_the_builders_to_fix(
        self, tmp_path: Path
    ) -> None:
        """The other half of the rule: a real red is untouched by any of this."""
        _root, worktree = _make_repo(tmp_path)
        _executable(
            worktree / "qa" / "run-suite.sh",
            "#!/bin/sh\necho '1 of 3 checks failed' >&2\nexit 1\n",
        )

        result = _validator(worktree, wave_size=2).run_independent_tests()

        assert result.tests_passed is False
        assert result.signal_absent is False
        assert result.check_could_not_run is False


# ---------------------------------------------------------------------------
# 4. The gate helper on its own
# ---------------------------------------------------------------------------


def test_unknown_is_not_a_pass(tmp_path: Path) -> None:
    validator = CoachValidator(str(tmp_path))
    passed = QualityGateStatus(
        tests_passed=True,
        coverage_met=True,
        arch_review_passed=True,
        plan_audit_passed=True,
    )
    assert passed.all_gates_passed is True

    unknown = validator._gates_with_unknown_tests(passed)
    assert unknown.tests_passed is None
    assert unknown.all_gates_passed is False
    # The other gates are untouched.
    assert unknown.coverage_met is True
    assert unknown.arch_review_passed is True
