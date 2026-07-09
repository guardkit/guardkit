"""TASK-AB-RESUMEVENV01 — resume-path venv resolution.

FEAT-ABL-005 run 4: ``guardkit autobuild feature --resume`` skipped bootstrap
(hash match), ``BootstrapResult.venv_python`` was never threaded, and
``_resolve_venv_python``'s filesystem recovery probed ONLY the legacy
``<worktree>/.guardkit/venv/bin/python`` while current bootstrap creates
``<worktree>/.venv`` — silent fallback to ``sys.executable`` → pytest
collected 0 tests → 8 turns of absent signals that looked like quality
rejections.

Pins the fix hop by hop:

1. ``probe_worktree_venv`` / ``_resolve_venv_python`` probe BOTH layouts,
   current (``.venv``) first, legacy (``.guardkit/venv``) second (AC-001).
2. The hash-match bootstrap-skip path re-resolves a usable ``venv_python``
   from disk when the saved state carries none / a stale one (AC-002).
3. No silent ``sys.executable`` fallback for a Python project worktree —
   ONE WARNING naming the probed locations and the fallback interpreter
   (AC-003).
4. ``resolved_interpreter`` forensic evidence lands on
   ``IndependentTestResult`` → ``CoachValidationResult.to_dict`` (including
   None) and on the deterministic Phase-4 block (AC-003/AC-004).

Coverage Target: >=85%
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator import specialist_invocations as si
from guardkit.orchestrator.coach_verification import (
    CoachVerifier,
    InterpreterResolutionError,
    _resolve_venv_python,
)
from guardkit.orchestrator.environment_bootstrap import (
    DetectedManifest,
    EnvironmentBootstrapper,
    probe_worktree_venv,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidationResult,
    CoachValidator,
    IndependentTestResult,
)


# ---------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------


def _make_venv(root: Path, layout: str) -> Path:
    """Create a fake venv interpreter on disk for the given layout."""
    if layout == "current":
        interpreter = root / ".venv" / "bin" / "python"
    elif layout == "legacy":
        interpreter = root / ".guardkit" / "venv" / "bin" / "python"
    else:  # pragma: no cover - test misuse
        raise ValueError(layout)
    interpreter.parent.mkdir(parents=True, exist_ok=True)
    interpreter.touch()
    return interpreter


def _python_manifest(path: Path) -> DetectedManifest:
    return DetectedManifest(
        path=path,
        stack="python",
        is_lock_file=False,
        install_command=[sys.executable, "-m", "pip", "install", "-e", "."],
    )


def _seed_skip_state(
    bootstrapper: EnvironmentBootstrapper,
    manifests,
    venv_python: Optional[str] = None,
) -> None:
    """Write a bootstrap_state.json that makes ``bootstrap()`` hash-match skip."""
    state = {
        "content_hash": bootstrapper._compute_hash(manifests),
        "success": True,
        "timestamp": "2026-07-04T00:00:00",
    }
    if venv_python is not None:
        state["venv_python"] = venv_python
    bootstrapper._state_file.parent.mkdir(parents=True, exist_ok=True)
    bootstrapper._state_file.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# AC-001 — probe order: .venv first, legacy .guardkit/venv second
# ---------------------------------------------------------------------------


class TestProbeWorktreeVenv:
    def test_current_layout_wins_when_both_exist(self, tmp_path: Path) -> None:
        current = _make_venv(tmp_path, "current")
        _make_venv(tmp_path, "legacy")
        assert probe_worktree_venv(tmp_path) == current

    def test_legacy_layout_still_found(self, tmp_path: Path) -> None:
        legacy = _make_venv(tmp_path, "legacy")
        assert probe_worktree_venv(tmp_path) == legacy

    def test_neither_layout_returns_none(self, tmp_path: Path) -> None:
        assert probe_worktree_venv(tmp_path) is None


class TestResolveVenvPythonProbeOrder:
    def test_dot_venv_wins_when_both_exist(self, tmp_path: Path) -> None:
        current = _make_venv(tmp_path, "current")
        _make_venv(tmp_path, "legacy")
        assert _resolve_venv_python(tmp_path, None) == current

    def test_legacy_guardkit_venv_still_resolves(self, tmp_path: Path) -> None:
        legacy = _make_venv(tmp_path, "legacy")
        assert _resolve_venv_python(tmp_path, None) == legacy

    def test_resume_shaped_call_resolves_dot_venv(self, tmp_path: Path) -> None:
        """explicit=None (the --resume shape) with .venv on disk resolves it."""
        current = _make_venv(tmp_path, "current")
        assert _resolve_venv_python(tmp_path, None) == current

    def test_fresh_run_explicit_path_unchanged(self, tmp_path: Path) -> None:
        """An existing explicit interpreter wins over any filesystem probe."""
        _make_venv(tmp_path, "current")
        explicit = tmp_path / "elsewhere" / "python"
        explicit.parent.mkdir(parents=True)
        explicit.touch()
        assert _resolve_venv_python(tmp_path, str(explicit)) == explicit

    def test_stale_explicit_falls_through_to_probe(self, tmp_path: Path) -> None:
        current = _make_venv(tmp_path, "current")
        assert (
            _resolve_venv_python(tmp_path, str(tmp_path / "gone" / "python"))
            == current
        )

    def test_neither_python_project_warns_once(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC-003: Python project + no venv → None + exactly ONE WARNING
        naming the probed locations and the fallback interpreter."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        with caplog.at_level(logging.WARNING):
            assert _resolve_venv_python(tmp_path, None) is None
        warnings = [
            r
            for r in caplog.records
            if r.levelno == logging.WARNING
            and "TASK-AB-RESUMEVENV01" in r.getMessage()
        ]
        assert len(warnings) == 1
        message = warnings[0].getMessage()
        assert str(tmp_path / ".venv" / "bin" / "python") in message
        assert str(tmp_path / ".guardkit" / "venv" / "bin" / "python") in message
        assert sys.executable in message

    def test_neither_non_python_project_is_silent(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Non-Python worktree keeps the pre-existing silent-None contract."""
        with caplog.at_level(logging.WARNING):
            assert _resolve_venv_python(tmp_path, None) is None
        assert not [
            r
            for r in caplog.records
            if r.levelno == logging.WARNING
            and "TASK-AB-RESUMEVENV01" in r.getMessage()
        ]


# ---------------------------------------------------------------------------
# WS3-S1 — Q1 SPLIT posture: hard-abort inside autobuild, warn+fallback
# interactive. Decided by Rich 2026-07-09 (WS3 §7). The interactive path is
# already covered above via the default ``in_autobuild_context=False``; these
# pin the autobuild-context branch and the explicit (not heuristic) split.
# ---------------------------------------------------------------------------


class TestInterpreterResolutionSplitPosture:
    def test_autobuild_context_python_project_hard_aborts(
        self, tmp_path: Path
    ) -> None:
        """Python project + no venv + autobuild context → HARD-ABORT."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        with pytest.raises(InterpreterResolutionError) as exc_info:
            _resolve_venv_python(tmp_path, None, in_autobuild_context=True)
        message = str(exc_info.value)
        # GATE: the message names the remediation.
        assert "HARD-ABORT" in message
        assert "re-run environment bootstrap" in message
        assert str(tmp_path / ".venv" / "bin" / "python") in message

    def test_interactive_default_still_warns_and_falls_back(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The DEFAULT (interactive) path is unchanged: WARNING + None,
        never a raise. The split is an explicit flag, not a heuristic."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        with caplog.at_level(logging.WARNING):
            # No in_autobuild_context → warn-and-fallback preserved.
            assert _resolve_venv_python(tmp_path, None) is None
            assert (
                _resolve_venv_python(
                    tmp_path, None, in_autobuild_context=False
                )
                is None
            )

    def test_autobuild_context_non_python_project_is_silent_none(
        self, tmp_path: Path
    ) -> None:
        """Non-Python worktree never hard-aborts even inside autobuild —
        there is no project venv to miss."""
        assert (
            _resolve_venv_python(tmp_path, None, in_autobuild_context=True)
            is None
        )

    def test_autobuild_context_resolves_when_venv_exists(
        self, tmp_path: Path
    ) -> None:
        """A healthy autobuild worktree (venv present) resolves normally and
        never raises — the hard-abort fires ONLY on the genuinely-broken env."""
        current = _make_venv(tmp_path, "current")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        assert (
            _resolve_venv_python(tmp_path, None, in_autobuild_context=True)
            == current
        )

    def test_coach_verifier_autobuild_context_propagates_raise(
        self, tmp_path: Path
    ) -> None:
        """CoachVerifier(in_autobuild_context=True) hard-aborts in __init__."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        with pytest.raises(InterpreterResolutionError):
            CoachVerifier(tmp_path, in_autobuild_context=True)
        # Default construction (interactive) still succeeds.
        assert CoachVerifier(tmp_path)._venv_python is None

    def test_coach_validator_autobuild_context_propagates_raise(
        self, tmp_path: Path
    ) -> None:
        """CoachValidator(in_autobuild_context=True) hard-aborts in __init__;
        the default construction is unchanged."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        with pytest.raises(InterpreterResolutionError):
            CoachValidator(str(tmp_path), in_autobuild_context=True)
        # Default (interactive) construction still succeeds.
        CoachValidator(str(tmp_path))

    def test_deterministic_phase4_reraises_hard_abort(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The deterministic Phase-4 runner must PROPAGATE the hard-abort, not
        degrade to the LLM specialist (which would run under the broken
        interpreter and re-open the DD4F soft-fail)."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        monkeypatch.setenv("GUARDKIT_PHASE4_TEST_EXECUTION", "subprocess")
        agent_invoker = MagicMock()
        agent_invoker._venv_python = None
        with pytest.raises(InterpreterResolutionError):
            si._run_deterministic_phase_4(
                worktree_path=tmp_path,
                task_id="TASK-TEST-0001",
                agent_invoker=agent_invoker,
                sdk_timeout=300,
                turn=1,
                wave_size=1,
            )


# ---------------------------------------------------------------------------
# AC-002 — hash-match skip path threads a usable venv_python
# ---------------------------------------------------------------------------


class TestBootstrapSkipPathVenvThreading:
    def _bootstrapper_and_manifests(self, tmp_path: Path):
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text("[project]\nname = 'demo'\n")
        bootstrapper = EnvironmentBootstrapper(tmp_path)
        manifests = [_python_manifest(manifest_path)]
        return bootstrapper, manifests

    def test_skip_returns_saved_venv_when_valid(self, tmp_path: Path) -> None:
        bootstrapper, manifests = self._bootstrapper_and_manifests(tmp_path)
        saved = _make_venv(tmp_path, "current")
        _seed_skip_state(bootstrapper, manifests, venv_python=str(saved))

        result = bootstrapper.bootstrap(manifests)

        assert result.skipped is True
        assert result.venv_python == str(saved)

    def test_skip_reprobes_when_state_has_no_venv(self, tmp_path: Path) -> None:
        """The FEAT-ABL-005 run-4 shape: hash-match skip, state predates venv
        persistence, but the worktree venv exists on disk — must re-resolve."""
        bootstrapper, manifests = self._bootstrapper_and_manifests(tmp_path)
        on_disk = _make_venv(tmp_path, "current")
        _seed_skip_state(bootstrapper, manifests, venv_python=None)

        result = bootstrapper.bootstrap(manifests)

        assert result.skipped is True
        assert result.venv_python == str(on_disk)

    def test_skip_reprobes_stale_saved_venv_to_legacy_layout(
        self, tmp_path: Path
    ) -> None:
        bootstrapper, manifests = self._bootstrapper_and_manifests(tmp_path)
        legacy = _make_venv(tmp_path, "legacy")
        _seed_skip_state(
            bootstrapper,
            manifests,
            venv_python=str(tmp_path / ".venv" / "bin" / "gone-python"),
        )

        result = bootstrapper.bootstrap(manifests)

        assert result.skipped is True
        assert result.venv_python == str(legacy)

    def test_skip_discards_outside_worktree_saved_venv(
        self, tmp_path: Path
    ) -> None:
        """FFC6 invariant on the skip path: a saved interpreter OUTSIDE the
        worktree (the historical sys.executable leak) is discarded in favour
        of the on-disk worktree venv."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        manifest_path = worktree / "pyproject.toml"
        manifest_path.write_text("[project]\nname = 'demo'\n")
        bootstrapper = EnvironmentBootstrapper(worktree)
        manifests = [_python_manifest(manifest_path)]

        outside = tmp_path / "parent-venv" / "bin" / "python"
        outside.parent.mkdir(parents=True)
        outside.touch()
        on_disk = _make_venv(worktree, "current")
        _seed_skip_state(bootstrapper, manifests, venv_python=str(outside))

        result = bootstrapper.bootstrap(manifests)

        assert result.skipped is True
        assert result.venv_python == str(on_disk)

    def test_skip_rejects_sibling_worktree_sharing_a_path_prefix(
        self, tmp_path: Path
    ) -> None:
        """A saved interpreter in a SIBLING worktree whose path merely shares
        a string prefix (FEAT-AB vs FEAT-AB2) must be discarded — a stale
        state file must never pin the Coach to ANOTHER worktree's venv
        (Path.is_relative_to on resolved paths, not str.startswith;
        2026-07-04 review, FIX 5). The genuine-child direction is pinned by
        ``test_skip_returns_saved_venv_when_valid``."""
        worktree = tmp_path / "FEAT-AB"
        worktree.mkdir()
        sibling = tmp_path / "FEAT-AB2"
        sibling.mkdir()
        manifest_path = worktree / "pyproject.toml"
        manifest_path.write_text("[project]\nname = 'demo'\n")
        bootstrapper = EnvironmentBootstrapper(worktree)
        manifests = [_python_manifest(manifest_path)]

        # str(sibling_venv).startswith(str(worktree)) is True — the prefix trap.
        sibling_venv = _make_venv(sibling, "current")
        assert str(sibling_venv).startswith(str(worktree))
        on_disk = _make_venv(worktree, "current")
        _seed_skip_state(bootstrapper, manifests, venv_python=str(sibling_venv))

        result = bootstrapper.bootstrap(manifests)

        assert result.skipped is True
        assert result.venv_python == str(on_disk)

    def test_skip_yields_none_when_no_venv_anywhere(self, tmp_path: Path) -> None:
        """Genuinely no worktree venv (e.g. non-Python) — behaviour unchanged."""
        bootstrapper, manifests = self._bootstrapper_and_manifests(tmp_path)
        _seed_skip_state(bootstrapper, manifests, venv_python=None)

        result = bootstrapper.bootstrap(manifests)

        assert result.skipped is True
        assert result.venv_python is None


# ---------------------------------------------------------------------------
# AC-003/AC-004 — resolved_interpreter forensic evidence
# ---------------------------------------------------------------------------


def _independent(resolved_interpreter: Optional[str]) -> IndependentTestResult:
    return IndependentTestResult(
        tests_passed=True,
        test_command="pytest -q",
        test_output_summary="5 passed",
        duration_seconds=1.0,
        resolved_interpreter=resolved_interpreter,
    )


class TestResolvedInterpreterEvidence:
    def test_to_dict_carries_resolved_interpreter(self) -> None:
        result = CoachValidationResult(
            task_id="TASK-AB-RESUMEVENV01",
            turn=1,
            decision="approve",
            independent_tests=_independent("/wt/.venv/bin/python"),
        )
        d = result.to_dict()
        assert (
            d["validation_results"]["independent_tests"]["resolved_interpreter"]
            == "/wt/.venv/bin/python"
        )

    def test_to_dict_preserves_none_resolved_interpreter(self) -> None:
        result = CoachValidationResult(
            task_id="TASK-AB-RESUMEVENV01",
            turn=1,
            decision="approve",
            independent_tests=_independent(None),
        )
        ind = result.to_dict()["validation_results"]["independent_tests"]
        # Key PRESENT and None — unknown stays unknown through serialization.
        assert "resolved_interpreter" in ind
        assert ind["resolved_interpreter"] is None

    def test_subprocess_run_records_resolved_interpreter(
        self, tmp_path: Path
    ) -> None:
        """run_independent_tests (subprocess path) records the pinned
        interpreter it actually ran pytest under."""
        validator = CoachValidator(
            str(tmp_path),
            test_command="pytest -q",
            coach_test_execution="subprocess",
        )
        proc = MagicMock(returncode=0, stdout="5 passed in 0.1s", stderr="")
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.subprocess.run",
            return_value=proc,
        ):
            result = validator.run_independent_tests()
        assert result.resolved_interpreter == validator._pytest_interpreter()

    def test_deterministic_phase_4_block_carries_resolved_interpreter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The Phase-4 specialist record carries the interpreter for both a
        pass and a genuine ran-and-failed verdict (one-grep forensics)."""

        outcomes = {
            "passed": IndependentTestResult(
                tests_passed=True,
                test_command="pytest -q",
                test_output_summary="4 passed",
                duration_seconds=0.2,
                raw_output="4 passed",
                resolved_interpreter="/wt/.venv/bin/python",
            ),
            "failed": IndependentTestResult(
                tests_passed=False,
                test_command="pytest -q",
                test_output_summary="1 failed, 3 passed",
                duration_seconds=0.2,
                raw_output="1 failed, 3 passed",
                resolved_interpreter="/wt/.venv/bin/python",
            ),
        }

        for expected_status, outcome in outcomes.items():

            class _FakeCoachValidator:
                def __init__(self, **kwargs):
                    pass

                def run_independent_tests(self, **kwargs):
                    return outcome

            monkeypatch.setattr(
                "guardkit.orchestrator.quality_gates.coach_validator."
                "CoachValidator",
                _FakeCoachValidator,
            )
            invoker = MagicMock()
            invoker._venv_python = None
            block = si._run_deterministic_phase_4(
                worktree_path=tmp_path,
                task_id="TASK-AB-RESUMEVENV01",
                agent_invoker=invoker,
                sdk_timeout=300,
                turn=1,
            )
            assert block is not None
            assert block["status"] == expected_status
            assert block["resolved_interpreter"] == "/wt/.venv/bin/python"
