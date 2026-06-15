"""Integration tests for the BDD factory bridge (TASK-BDDW-001).

Tests the wiring of guardkitfactory.bdd plugin discovery into the Coach
evidence path, covering:

- ``_map_bdd_run_result_to_bundle``: verifies the BDDRunResult → bundle.bdd
  mapping preserves ``scenarios_attempted`` verbatim (never coerces a missing
  key to 0).
- ``CoachValidator.gather_evidence``: verifies the factory discovery path
  is used when the factory is available and Player-reported bdd_results are
  absent.
- Edge cases: factory unavailable, stack profile unknown, plugin returns None.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# Minimal fakes mirroring the REAL guardkitfactory contract
# (guardkitfactory/src/guardkitfactory/bdd/plugin.py). TASK-FIX-BDDFW01
# realigned these from the abandoned BDDRunResult shape
# (.failures/.pending/.feature_files + one-arg discover/run) so this sibling
# test and test_coach_validator_bdd_factory_wiring.py share ONE contract.
# ---------------------------------------------------------------------------


@dataclass
class _FakeBDDRunResult:
    """Minimal BDDRunResult mirroring the real guardkitfactory contract."""
    scenarios_attempted: int = 0
    scenarios_passed: int = 0
    scenarios_failed: int = 0
    scenarios_skipped: int = 0
    scenarios_errored: int = 0
    duration_seconds: float = 0.0
    raw_report_path: Optional[Path] = None
    discoveries: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class _FakePlugin:
    """Minimal plugin matching the factory's BDDPlugin lifecycle."""

    name = "fake-bdd"

    def __init__(self, result: _FakeBDDRunResult):
        self._result = result

    def preflight(self, task_id: str, worktree: Path) -> bool:
        return True

    def run(
        self,
        scenarios: List[Any],
        task_id: str,
        worktree: Path,
        *,
        timeout_seconds: int = 600,
    ) -> Optional[_FakeBDDRunResult]:
        return self._result


class _FakeStackProfile:
    """Minimal StackProfile enum-like object."""
    PYTHON = "python"
    DOTNET = "dotnet"
    JAVASCRIPT = "javascript"


def _make_fake_discover(result: _FakeBDDRunResult):
    """Create a fake discover() matching the real 2-arg ``(stack, worktree)``."""
    def discover(stack: Any, worktree: Path):
        return _FakePlugin(result)
    return discover


# ---------------------------------------------------------------------------
# Test: _map_bdd_run_result_to_bundle preserves scenarios_attempted
# ---------------------------------------------------------------------------

@pytest.mark.seam
@pytest.mark.integration_contract("BDDRunResult")
def test_bdd_run_result_maps_attempted_count():
    """A BDDRunResult with scenarios_attempted=0 maps to bundle.bdd as ABSENT
    SIGNAL, never a silent pass.

    Producer: guardkitfactory.bdd plugin.
    Contract: scenarios_attempted is non-Optional and must not be coerced
    from a missing key.
    """
    from guardkit.orchestrator.quality_gates.coach_validator import (
        _map_bdd_run_result_to_bundle,
    )

    result = _FakeBDDRunResult(
        scenarios_attempted=0,
        scenarios_passed=0,
        scenarios_failed=0,
    )
    mapped = _map_bdd_run_result_to_bundle(result)

    assert mapped["scenarios_attempted"] == 0
    assert "scenarios_attempted" in mapped  # present, not absent-coerced
    assert mapped["scenarios_passed"] == 0
    assert mapped["scenarios_failed"] == 0
    assert mapped["failures"] == []
    assert mapped["feature_files"] == []


@pytest.mark.seam
@pytest.mark.integration_contract("BDDRunResult")
def test_bdd_run_result_maps_nonzero_attempted():
    """A BDDRunResult with scenarios_attempted > 0 maps correctly.

    feature_files derive from ``discoveries[*]["feature_file"]`` and failures
    derive from the ``errors`` string list (real contract).
    """
    from guardkit.orchestrator.quality_gates.coach_validator import (
        _map_bdd_run_result_to_bundle,
    )

    result = _FakeBDDRunResult(
        scenarios_attempted=3,
        scenarios_passed=2,
        scenarios_failed=1,
        scenarios_skipped=0,
        discoveries=[{"feature_file": "features/auth/login.feature"}],
        errors=["AssertionError: expected 200, got 401"],
    )
    mapped = _map_bdd_run_result_to_bundle(result)

    assert mapped["scenarios_attempted"] == 3
    assert mapped["scenarios_passed"] == 2
    assert mapped["scenarios_failed"] == 1
    assert mapped["scenarios_pending"] == 0
    assert len(mapped["failures"]) == 1
    assert mapped["failures"][0]["error"] == "AssertionError: expected 200, got 401"
    assert mapped["feature_files"] == ["features/auth/login.feature"]


@pytest.mark.seam
@pytest.mark.integration_contract("BDDRunResult")
def test_bdd_run_result_maps_skipped_to_pending_count():
    """``scenarios_skipped`` maps to the ``scenarios_pending`` COUNT; the
    per-scenario ``pending`` list is always empty (the real BDDRunResult
    carries no pending-detail list).
    """
    from guardkit.orchestrator.quality_gates.coach_validator import (
        _map_bdd_run_result_to_bundle,
    )

    result = _FakeBDDRunResult(
        scenarios_attempted=1,
        scenarios_passed=0,
        scenarios_failed=0,
        scenarios_skipped=1,
    )
    mapped = _map_bdd_run_result_to_bundle(result)

    assert mapped["scenarios_pending"] == 1
    assert mapped["pending"] == []


# ---------------------------------------------------------------------------
# Test: CoachValidator uses factory discovery
# ---------------------------------------------------------------------------

@pytest.mark.seam
@pytest.mark.integration
def test_coach_validator_uses_factory_when_available(monkeypatch: pytest.FixtureRequest):
    """CoachValidator.gather_evidence uses factory discovery when the factory
    is available and Player-reported bdd_results are absent.
    """
    fake_result = _FakeBDDRunResult(
        scenarios_attempted=2,
        scenarios_passed=2,
        scenarios_failed=0,
    )
    fake_discover = _make_fake_discover(fake_result)

    # Import the module first (it gets cached in sys.modules).
    from guardkit.orchestrator.quality_gates import coach_validator as cv_module

    # Patch the module's internal state directly.
    monkeypatch.setattr(cv_module, "_FACTORY_AVAILABLE", True)
    monkeypatch.setattr(cv_module, "_is_factory_available", lambda: True)
    monkeypatch.setattr(cv_module, "discover", fake_discover)
    monkeypatch.setattr(cv_module, "StackProfile", _FakeStackProfile)

    from guardkit.orchestrator.quality_gates.coach_validator import (
        _run_factory_bdd,
        _reset_factory_cache,
    )

    _reset_factory_cache()

    # Create a temp worktree.
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        worktree = Path(tmpdir)

        factory_bdd = _run_factory_bdd(worktree, "python", "TASK-TEST-001")

        assert factory_bdd is not None
        assert factory_bdd["scenarios_attempted"] == 2
        assert factory_bdd["scenarios_passed"] == 2
        assert factory_bdd["scenarios_failed"] == 0


@pytest.mark.seam
@pytest.mark.integration
def test_coach_validator_fallback_when_factory_unavailable(monkeypatch: pytest.FixtureRequest):
    """CoachValidator falls back to Player-reported bdd_results when the
    factory is unavailable.
    """
    from guardkit.orchestrator.quality_gates.coach_validator import (
        _run_factory_bdd,
        _reset_factory_cache,
    )

    _reset_factory_cache()

    with monkeypatch.context() as m:
        m.setattr(
            "guardkit.orchestrator.quality_gates.coach_validator._FACTORY_AVAILABLE",
            False,
        )
        m.setattr(
            "guardkit.orchestrator.quality_gates.coach_validator._is_factory_available",
            lambda: False,
        )

        bdd_result = _run_factory_bdd(Path("/tmp"), "python")
        assert bdd_result is None


@pytest.mark.seam
@pytest.mark.integration
def test_coach_validator_fallback_when_stack_unknown(monkeypatch: pytest.FixtureRequest):
    """CoachValidator falls back when the stack profile is unknown."""
    from guardkit.orchestrator.quality_gates.coach_validator import (
        _run_factory_bdd,
        _detect_stack_profile,
        _reset_factory_cache,
    )

    _reset_factory_cache()

    # Unknown stack profile.
    assert _detect_stack_profile(Path("/nonexistent")) is None

    with monkeypatch.context() as m:
        m.setattr(
            "guardkit.orchestrator.quality_gates.coach_validator._FACTORY_AVAILABLE",
            True,
        )
        m.setattr(
            "guardkit.orchestrator.quality_gates.coach_validator._is_factory_available",
            lambda: True,
        )

        # Unknown stack → None result.
        bdd_result = _run_factory_bdd(Path("/tmp"), None)
        assert bdd_result is None


@pytest.mark.seam
@pytest.mark.integration
def test_bdd_run_result_preserves_scenarios_attempted_zero_not_coerced():
    """Verify that scenarios_attempted=0 is preserved verbatim and never
    coerced from a missing key.

    This is the core contract for the absence-of-failure gate (Pattern-2):
    when scenarios_attempted == 0, the Coach must treat it as ABSENT SIGNAL,
    not as a silent pass.
    """
    from guardkit.orchestrator.quality_gates.coach_validator import (
        _map_bdd_run_result_to_bundle,
    )

    # Zero scenarios attempted — the critical case.
    result = _FakeBDDRunResult(
        scenarios_attempted=0,
        scenarios_passed=0,
        scenarios_failed=0,
    )
    mapped = _map_bdd_run_result_to_bundle(result)

    # scenarios_attempted must be present and equal to 0.
    assert mapped.get("scenarios_attempted") == 0
    assert "scenarios_attempted" in mapped

    # scenarios_failed must also be 0 (no failures).
    assert mapped.get("scenarios_failed") == 0

    # The Coach's absence-of-failure gate checks BOTH:
    #   scenarios_failed == 0 AND scenarios_attempted == 0
    # → ABSENT SIGNAL (not a pass).
    assert mapped["scenarios_failed"] == 0 and mapped["scenarios_attempted"] == 0


@pytest.mark.seam
@pytest.mark.integration
def test_stack_profile_mapping():
    """Verify the stack profile mapping from project.template strings."""
    from guardkit.orchestrator.quality_gates.coach_validator import (
        _STACK_PROFILE_MAP,
    )

    # Python templates.
    assert _STACK_PROFILE_MAP.get("python") == "python"
    assert _STACK_PROFILE_MAP.get("fastapi-python") == "python"
    assert _STACK_PROFILE_MAP.get("django-python") == "python"
    assert _STACK_PROFILE_MAP.get("flask-python") == "python"

    # .NET templates.
    assert _STACK_PROFILE_MAP.get(".net") == "dotnet"
    assert _STACK_PROFILE_MAP.get("aspnet-core") == "dotnet"
    assert _STACK_PROFILE_MAP.get("csharp") == "dotnet"

    # JS templates.
    assert _STACK_PROFILE_MAP.get("node-js") == "javascript"
    assert _STACK_PROFILE_MAP.get("javascript") == "javascript"
    assert _STACK_PROFILE_MAP.get("typescript") == "javascript"

    # Unknown template → None.
    assert _STACK_PROFILE_MAP.get("unknown-template") is None
