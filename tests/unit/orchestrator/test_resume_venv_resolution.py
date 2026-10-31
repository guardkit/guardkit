"""TASK-AB-RESUMEVENV01 — resume-path venv resolution.

FEAT-ABL-005 run 4: ``guardkit autobuild feature --resume`` skipped bootstrap
(hash match), ``BootstrapResult.venv_python`` was never threaded, and
``_resolve_venv_python``'s filesystem recovery probed ONLY the legacy
``<worktree>/.guardkit/venv/bin/python`` while current bootstrap creates
``<worktree>/.venv`` — silent fallback to ``sys.executable`` → pytest
collected 0 tests → 8 turns of absent signals that looked like quality
rejections.

Pins the fix hop by hop. (31 October 2026: the Coach's own venv resolution,
``_resolve_venv_python``, and its hard-abort were removed with the opt-in SDK
test path and state recovery's pytest run; the declared command runs as
declared. Their tests went with them. The bootstrap's own venv probe and
skip path stay until the bootstrap's Python inference is decided.)

1. ``probe_worktree_venv`` / ``_resolve_venv_python`` probe BOTH layouts,
   current (``.venv``) first, legacy (``.guardkit/venv``) second (AC-001).
2. The hash-match bootstrap-skip path re-resolves a usable ``venv_python``
   from disk when the saved state carries none / a stale one (AC-002).
3. No silent ``sys.executable`` fallback for a Python project worktree —
   ONE WARNING naming the probed locations and the fallback interpreter
   (AC-003).
4. ``resolved_interpreter`` forensic evidence lands on
   ``IndependentTestResult`` → ``CoachEvidenceBundle.to_dict`` (including
   None) (AC-003/AC-004).

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

from guardkit.orchestrator.environment_bootstrap import (
    DetectedManifest,
    EnvironmentBootstrapper,
    probe_worktree_venv,
)
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import (
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
        bundle = CoachEvidenceBundle(
            independent_tests=_independent("/wt/.venv/bin/python"),
        )
        d = bundle.to_dict()
        assert (
            d["independent_tests"]["resolved_interpreter"]
            == "/wt/.venv/bin/python"
        )

    def test_to_dict_preserves_none_resolved_interpreter(self) -> None:
        bundle = CoachEvidenceBundle(independent_tests=_independent(None))
        ind = bundle.to_dict()["independent_tests"]
        # Key PRESENT and None — unknown stays unknown through serialization.
        assert "resolved_interpreter" in ind
        assert ind["resolved_interpreter"] is None
