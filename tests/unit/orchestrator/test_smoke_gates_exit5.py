"""Exit-code-aware smoke-gate outcomes (TASK-FIX-SG05).

Pins the distinction between three pytest exit codes the smoke-gate runner
must NOT conflate:

- exit 0 — tests passed. ``passed=True``, ``gate_not_wired=False``.
- exit 1 — tests ran and failed. ``passed=False``, ``gate_not_wired=False``.
- exit 5 — pytest collected zero tests (gate-config gap). By default this
  is a soft warning (``passed=True``, ``gate_not_wired=True``); per-feature
  ``exit5_is_hard_fail=True`` flips it to a blocking failure
  (``passed=False``, ``gate_not_wired=True``).

Without these distinctions, a mis-registered marker silently fails a
feature-build that was, in fact, fully implemented — see the study-tutor
TASK-DSP-008 post-mortem cited in the originating task.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.feature_loader import SmokeGates
from guardkit.orchestrator.smoke_gates import (
    GATE_NOT_WIRED_HINT,
    PYTEST_EXIT_NO_TESTS_COLLECTED,
    run_smoke_gate,
)


def _patch_subprocess_returncode(
    monkeypatch: pytest.MonkeyPatch, returncode: int
) -> None:
    """Replace subprocess.run with a stub that returns ``returncode``."""

    def fake_run(cmd, *, shell, cwd, capture_output, text, timeout, env=None):
        return subprocess.CompletedProcess(
            args=cmd, returncode=returncode, stdout="", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)


def test_pytest_no_tests_collected_constant_matches_pytest_convention() -> None:
    """Guards against drift if anyone redefines the constant.

    pytest documents exit code 5 as "no tests were collected"
    (https://docs.pytest.org/en/stable/reference/exit-codes.html).
    The whole point of TASK-FIX-SG05 is to treat that code specially, so
    if the constant is silently changed we want the test suite to flag it.
    """
    assert PYTEST_EXIT_NO_TESTS_COLLECTED == 5


def test_exit_zero_passes_unchanged_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit 0 must remain the success path with no gate_not_wired flag.

    AC constraint: "Do NOT alter the exit-0 success path."
    """
    _patch_subprocess_returncode(monkeypatch, 0)
    config = SmokeGates(after_wave=1, command="pytest", expected_exit=0)

    result = run_smoke_gate(config, cwd=tmp_path, wave_number=1)

    assert result.passed is True
    assert result.exit_code == 0
    assert result.gate_not_wired is False
    assert result.timed_out is False


def test_exit_one_fails_as_genuine_regression(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit 1 (tests ran and failed) keeps current FAILED semantics.

    AC constraint: "Do NOT change exit-1 semantics — a genuine test
    failure must still fail the gate."
    """
    _patch_subprocess_returncode(monkeypatch, 1)
    config = SmokeGates(after_wave=1, command="pytest", expected_exit=0)

    result = run_smoke_gate(config, cwd=tmp_path, wave_number=1)

    assert result.passed is False
    assert result.exit_code == 1
    assert result.gate_not_wired is False, (
        "Exit 1 is a real test failure, not an unwired gate"
    )


def test_exit_five_soft_warning_is_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Exit 5 with default config: soft warning, build continues.

    AC: ``exit5_is_hard_fail`` defaults to False — an unwired gate is a
    test-authoring gap, not a code regression. ``passed`` stays True so
    the orchestrator does NOT halt the feature build, but
    ``gate_not_wired`` is True so the orchestrator can surface a distinct
    warning, and the log line carries the hint.
    """
    _patch_subprocess_returncode(monkeypatch, PYTEST_EXIT_NO_TESTS_COLLECTED)
    config = SmokeGates(after_wave=1, command="pytest -m smoke", expected_exit=0)
    # Confirm the default — this is a contract, not just an implementation
    # detail. Changing the default is a breaking change for every project
    # already relying on the soft-warn behaviour.
    assert config.exit5_is_hard_fail is False

    with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.smoke_gates"):
        result = run_smoke_gate(config, cwd=tmp_path, wave_number=1)

    assert result.passed is True, "Soft mode must not halt the feature build"
    assert result.gate_not_wired is True
    assert result.exit_code == 5

    # The log line must be distinct from a real failure AND must carry the
    # hint, so a post-mortem lands on the actionable diagnosis rather than
    # a generic "exit=5, expected=0" failure message.
    log_text = caplog.text
    assert "unwired" in log_text
    assert "config gap, not regression" in log_text
    assert GATE_NOT_WIRED_HINT in log_text


def test_exit_five_hard_fail_when_opted_in(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Exit 5 with ``exit5_is_hard_fail=True``: blocking failure.

    AC: a project that wants strict gate enforcement can set this knob to
    True. The result must block the feature build (``passed=False``) but
    must STILL be distinguishable from a real test failure
    (``gate_not_wired=True``) so post-mortems still land on the
    marker-config diagnosis.
    """
    _patch_subprocess_returncode(monkeypatch, PYTEST_EXIT_NO_TESTS_COLLECTED)
    config = SmokeGates(
        after_wave=1,
        command="pytest -m smoke",
        expected_exit=0,
        exit5_is_hard_fail=True,
    )

    with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.smoke_gates"):
        result = run_smoke_gate(config, cwd=tmp_path, wave_number=1)

    assert result.passed is False, "Hard-fail mode must halt the feature build"
    assert result.gate_not_wired is True, (
        "Even in hard-fail mode the result must remain distinguishable "
        "from a real test failure"
    )
    assert result.exit_code == 5

    log_text = caplog.text
    assert "unwired" in log_text
    assert "exit5_is_hard_fail=True" in log_text
    assert GATE_NOT_WIRED_HINT in log_text


def test_exit_five_when_expected_exit_is_five_passes_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If a feature genuinely expects exit 5 (e.g. a "should match nothing"
    sanity check), that's a real success — not "gate not wired".

    Without this branch, a deliberately-empty matcher would be flagged as
    unwired even though it matched its declared expected_exit.
    """
    _patch_subprocess_returncode(monkeypatch, PYTEST_EXIT_NO_TESTS_COLLECTED)
    config = SmokeGates(after_wave=1, command="pytest -m never", expected_exit=5)

    result = run_smoke_gate(config, cwd=tmp_path, wave_number=1)

    assert result.passed is True
    assert result.gate_not_wired is False, (
        "If the operator declared exit=5 as success, it is not 'unwired'"
    )
