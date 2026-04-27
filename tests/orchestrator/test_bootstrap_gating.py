"""Tests for TASK-FIX-7A04: bootstrap hard-fail gate (``bootstrap_failure_mode``).

Covers the four AC branches from the task:
  1. ``mode=block`` + zero-success + essential stack → raises.
  2. ``mode=block`` + partial success → proceeds (warning logged).
  3. ``mode=warn``  + zero-success → proceeds (today's behavior).
  4. CLI flag override wins over ``.guardkit/config.yaml``.

Plus the supporting surface: config loader, optional-stacks filter, and the
actionable error message (stacks, PEP-668 excerpt, requires-python, hint).
"""

from __future__ import annotations

from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.environment_bootstrap import (
    BootstrapFailureDetail,
    BootstrapResult,
    RequiresPythonMismatch,
    check_requires_python_precheck,
    format_requires_python_remediation,
)
from guardkit.orchestrator.feature_orchestrator import (
    BOOTSTRAP_FAILURE_MODES,
    DEFAULT_BOOTSTRAP_FAILURE_MODE,
    FeatureOrchestrationError,
    FeatureOrchestrator,
    _format_bootstrap_hardfail_message,
    compute_default_bootstrap_failure_mode,
    load_bootstrap_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    *,
    installs_attempted: int,
    installs_failed: int,
    stacks_detected: List[str],
    failure_details: List[BootstrapFailureDetail] | None = None,
    skipped: bool = False,
) -> BootstrapResult:
    """Build a BootstrapResult with just enough fields for gate tests."""
    return BootstrapResult(
        success=installs_failed == 0,
        skipped=skipped,
        stacks_detected=list(stacks_detected),
        manifests_found=[],
        installs_attempted=installs_attempted,
        installs_failed=installs_failed,
        error=(
            f"{installs_failed}/{installs_attempted} install(s) failed"
            if installs_failed
            else None
        ),
        failure_details=list(failure_details or []),
    )


def _build_orchestrator(
    tmp_path: Path,
    *,
    failure_mode: str | None = None,
    write_config: dict | None = None,
) -> FeatureOrchestrator:
    """
    Instantiate FeatureOrchestrator with the repo_root pinned to ``tmp_path``.

    Optionally writes a ``.guardkit/config.yaml`` before construction so the
    loader sees it.
    """
    if write_config is not None:
        import yaml

        cfg_dir = tmp_path / ".guardkit"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.yaml").write_text(
            yaml.safe_dump(write_config), encoding="utf-8"
        )

    # WorktreeManager validates that repo_root is a real git checkout during
    # __init__; in these unit tests tmp_path is not a repo, so inject a
    # MagicMock in its place — these tests never exercise the manager.
    return FeatureOrchestrator(
        repo_root=tmp_path,
        bootstrap_failure_mode=failure_mode,
        skip_validation=True,
        worktree_manager=MagicMock(),
    )


# ---------------------------------------------------------------------------
# AC-1: mode=block + zero-success + essential stack → raises
# ---------------------------------------------------------------------------


def test_block_mode_all_failed_essential_stack_raises(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(tmp_path, failure_mode="block")

    result = _make_result(
        installs_attempted=1,
        installs_failed=1,
        stacks_detected=["python"],
        failure_details=[
            BootstrapFailureDetail(
                stack="python",
                manifest_path=str(tmp_path / "pyproject.toml"),
                stderr_excerpt="ERROR: externally-managed-environment",
                is_pep668=True,
                requires_python=">=3.13",
                essential=True,
            )
        ],
    )

    with pytest.raises(FeatureOrchestrationError) as exc:
        orchestrator._maybe_hardfail_bootstrap(result)

    msg = str(exc.value)
    # The message must cite the attempted stacks, the stderr excerpt, the
    # requires-python, and the override hint (AC-2 points).
    assert "python" in msg
    assert "0/1" in msg
    assert "externally-managed-environment" in msg
    assert ">=3.13" in msg
    assert "bootstrap_failure_mode: warn" in msg


# ---------------------------------------------------------------------------
# AC-2: mode=block + partial success → proceeds
# ---------------------------------------------------------------------------


def test_block_mode_partial_success_does_not_raise(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(tmp_path, failure_mode="block")

    result = _make_result(
        installs_attempted=2,
        installs_failed=1,
        stacks_detected=["python", "node"],
    )

    # Must NOT raise — at least one install succeeded.
    orchestrator._maybe_hardfail_bootstrap(result)


# ---------------------------------------------------------------------------
# AC-3: mode=warn + zero-success → proceeds (no regression)
# ---------------------------------------------------------------------------


def test_warn_mode_all_failed_proceeds(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(tmp_path, failure_mode="warn")
    assert orchestrator.bootstrap_failure_mode == "warn"

    result = _make_result(
        installs_attempted=1,
        installs_failed=1,
        stacks_detected=["python"],
    )

    # Today's behavior preserved: warn mode never raises on zero-success.
    orchestrator._maybe_hardfail_bootstrap(result)


def test_init_baseline_is_warn_when_no_config_no_override(tmp_path: Path) -> None:
    """
    At ``__init__`` time (before manifest detection) the baseline default
    is still ``"warn"`` and the orchestrator records that the user did
    NOT set the mode explicitly. The smart default fires later, in
    :meth:`FeatureOrchestrator._bootstrap_environment`.
    """
    orchestrator = _build_orchestrator(tmp_path)
    assert orchestrator.bootstrap_failure_mode == "warn"
    assert orchestrator._bootstrap_failure_mode_explicit is False
    # Baseline constant is preserved (kept-and-supplemented per AC).
    assert DEFAULT_BOOTSTRAP_FAILURE_MODE == "warn"


# ---------------------------------------------------------------------------
# AC-4: CLI flag overrides yaml default
# ---------------------------------------------------------------------------


def test_cli_override_beats_yaml_default(tmp_path: Path) -> None:
    # yaml says warn, CLI passes block → block wins.
    orchestrator = _build_orchestrator(
        tmp_path,
        failure_mode="block",
        write_config={"autobuild": {"bootstrap": {"failure_mode": "warn"}}},
    )
    assert orchestrator.bootstrap_failure_mode == "block"


def test_yaml_block_no_cli_override_picks_yaml(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(
        tmp_path,
        failure_mode=None,
        write_config={"autobuild": {"bootstrap": {"failure_mode": "block"}}},
    )
    assert orchestrator.bootstrap_failure_mode == "block"


# ---------------------------------------------------------------------------
# Gate: attempted=0 must never raise (skipped/no-manifest worktrees)
# ---------------------------------------------------------------------------


def test_block_mode_nothing_attempted_does_not_raise(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(tmp_path, failure_mode="block")

    result = _make_result(
        installs_attempted=0,
        installs_failed=0,
        stacks_detected=[],
    )

    # No installs attempted → gate is a no-op even in block mode.
    orchestrator._maybe_hardfail_bootstrap(result)


# ---------------------------------------------------------------------------
# Gate: all detected stacks listed optional → don't block
# ---------------------------------------------------------------------------


def test_block_mode_all_stacks_optional_does_not_raise(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(
        tmp_path,
        failure_mode="block",
        write_config={
            "autobuild": {
                "bootstrap": {
                    "failure_mode": "block",
                    "optional_stacks": ["python", "node"],
                }
            }
        },
    )
    assert orchestrator.bootstrap_optional_stacks == ["python", "node"]

    result = _make_result(
        installs_attempted=1,
        installs_failed=1,
        stacks_detected=["python"],
    )

    # Stack is declared optional → no hard-fail even with 0/1.
    orchestrator._maybe_hardfail_bootstrap(result)


def test_block_mode_mixed_optional_still_blocks_on_essential(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(
        tmp_path,
        failure_mode="block",
        write_config={
            "autobuild": {
                "bootstrap": {
                    "failure_mode": "block",
                    "optional_stacks": ["node"],
                }
            }
        },
    )

    result = _make_result(
        installs_attempted=2,
        installs_failed=2,
        stacks_detected=["python", "node"],
        failure_details=[
            BootstrapFailureDetail(
                stack="python",
                manifest_path="/tmp/pyproject.toml",
                stderr_excerpt="pip install failed",
                essential=True,
            ),
            BootstrapFailureDetail(
                stack="node",
                manifest_path="/tmp/package.json",
                stderr_excerpt="npm failed",
                essential=False,
            ),
        ],
    )

    with pytest.raises(FeatureOrchestrationError) as exc:
        orchestrator._maybe_hardfail_bootstrap(result)
    # Only python survives the optional filter.
    assert "python" in str(exc.value)


# ---------------------------------------------------------------------------
# Config loader: robustness
# ---------------------------------------------------------------------------


def test_load_bootstrap_config_missing_file_returns_default(tmp_path: Path) -> None:
    cfg = load_bootstrap_config(tmp_path)
    assert cfg["failure_mode"] == "warn"
    assert cfg["optional_stacks"] == []
    # TASK-ABSR-A1B2: when no yaml/CLI value, the resolved baseline is NOT
    # explicit — the smart default applies later, after manifest detection.
    assert cfg["failure_mode_explicit"] is False


def test_load_bootstrap_config_invalid_mode_falls_back(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    import yaml

    (tmp_path / ".guardkit").mkdir()
    (tmp_path / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump(
            {"autobuild": {"bootstrap": {"failure_mode": "nonsense"}}}
        )
    )

    with caplog.at_level("WARNING"):
        cfg = load_bootstrap_config(tmp_path)
    assert cfg["failure_mode"] == "warn"
    assert any("nonsense" in rec.message for rec in caplog.records)


def test_load_bootstrap_config_invalid_override_falls_back(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("WARNING"):
        cfg = load_bootstrap_config(tmp_path, override_failure_mode="maybe")
    assert cfg["failure_mode"] == "warn"


def test_load_bootstrap_config_optional_stacks_filters_non_strings(
    tmp_path: Path,
) -> None:
    import yaml

    (tmp_path / ".guardkit").mkdir()
    (tmp_path / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "autobuild": {
                    "bootstrap": {
                        "failure_mode": "block",
                        "optional_stacks": ["python", 42, None, "node"],
                    }
                }
            }
        )
    )

    cfg = load_bootstrap_config(tmp_path)
    assert cfg["failure_mode"] == "block"
    assert cfg["optional_stacks"] == ["python", "node"]


def test_load_bootstrap_config_corrupt_yaml_returns_default(tmp_path: Path) -> None:
    (tmp_path / ".guardkit").mkdir()
    (tmp_path / ".guardkit" / "config.yaml").write_text("not: valid: yaml: :\n-")
    cfg = load_bootstrap_config(tmp_path)
    # Either defaults returned or at least failure_mode normalized; loader
    # never raises.
    assert cfg["failure_mode"] in BOOTSTRAP_FAILURE_MODES


# ---------------------------------------------------------------------------
# Message formatter
# ---------------------------------------------------------------------------


def test_format_message_without_failure_details_still_cites_stacks() -> None:
    result = _make_result(
        installs_attempted=1,
        installs_failed=1,
        stacks_detected=["python"],
    )
    msg = _format_bootstrap_hardfail_message(result, ["python"])
    assert "0/1" in msg
    assert "python" in msg
    assert "bootstrap_failure_mode: warn" in msg


def test_format_message_includes_pep668_marker() -> None:
    detail = BootstrapFailureDetail(
        stack="python",
        manifest_path="/repo/pyproject.toml",
        stderr_excerpt="externally-managed-environment",
        is_pep668=True,
        requires_python=">=3.13",
        essential=True,
    )
    result = _make_result(
        installs_attempted=1,
        installs_failed=1,
        stacks_detected=["python"],
        failure_details=[detail],
    )
    msg = _format_bootstrap_hardfail_message(result, ["python"])
    assert "PEP 668" in msg
    assert ">=3.13" in msg
    assert "/repo/pyproject.toml" in msg


# ---------------------------------------------------------------------------
# TASK-REV-JMBP Workstream E — requires-python pre-check
# ---------------------------------------------------------------------------


def test_precheck_returns_empty_when_interpreter_satisfies_specifier(
    tmp_path: Path,
) -> None:
    # Specifier accepts the active version → no mismatches.
    manifest = _FakeManifest("python", requires_python=">=3.0,<4.0")
    mismatches = check_requires_python_precheck([manifest])
    assert mismatches == []


def test_precheck_flags_jarvis_like_mismatch() -> None:
    # Integration-style fixture: jarvis's real pyproject constraint vs a
    # fabricated Python 3.14 — the exact shape that triggered TASK-REV-JMBP.
    manifest = _FakeManifest("python", requires_python="<3.13,>=3.12")
    mismatches = check_requires_python_precheck(
        [manifest], active_version="3.14.2"
    )
    assert len(mismatches) == 1
    m = mismatches[0]
    assert m.specifier == "<3.13,>=3.12"
    assert m.active_version == "3.14.2"


def test_precheck_returns_empty_when_python_3_12_meets_jarvis_constraint() -> None:
    manifest = _FakeManifest("python", requires_python="<3.13,>=3.12")
    assert (
        check_requires_python_precheck(
            [manifest], active_version="3.12.6"
        )
        == []
    )


def test_precheck_skips_manifest_without_requires_python() -> None:
    manifest = _FakeManifest("python", requires_python=None)
    assert check_requires_python_precheck([manifest]) == []


def test_precheck_skips_non_python_stack() -> None:
    # Node / dotnet / etc never have requires-python.
    manifest = _FakeManifest("node", requires_python=None)
    assert check_requires_python_precheck([manifest]) == []


def test_precheck_skips_invalid_specifier_gracefully(
    caplog: pytest.LogCaptureFixture,
) -> None:
    manifest = _FakeManifest("python", requires_python=">>>garbage<<<")
    with caplog.at_level("DEBUG"):
        mismatches = check_requires_python_precheck([manifest])
    # Invalid specifier → pip remains authoritative; pre-check returns empty.
    assert mismatches == []


def test_format_remediation_includes_uv_pyenv_conda_and_version_example() -> None:
    mismatch = RequiresPythonMismatch(
        manifest_path="/repo/pyproject.toml",
        specifier="<3.13,>=3.12",
        active_version="3.14.2",
    )
    msg = format_requires_python_remediation(mismatch)
    assert "uv python install" in msg
    assert "pyenv install" in msg
    assert "conda create" in msg
    assert "3.12" in msg  # example version picked from specifier
    assert "/repo/pyproject.toml" in msg


def test_hardfail_requires_python_block_mode_raises_with_hint(
    tmp_path: Path,
) -> None:
    orchestrator = _build_orchestrator(tmp_path, failure_mode="block")

    manifest = _FakeManifest("python", requires_python="<3.13,>=3.12")
    # Patch the module-level pre-check so we don't depend on the runner's
    # actual Python version.
    with patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[
            RequiresPythonMismatch(
                manifest_path="/repo/pyproject.toml",
                specifier="<3.13,>=3.12",
                active_version="3.14.2",
            )
        ],
    ):
        with pytest.raises(FeatureOrchestrationError) as exc:
            orchestrator._maybe_hardfail_requires_python([manifest])

    msg = str(exc.value)
    assert "requires-python" in msg
    assert "<3.13,>=3.12" in msg
    assert "uv python install" in msg  # remediation hint
    assert "bootstrap_failure_mode: warn" in msg  # override hint


def test_hardfail_requires_python_warn_mode_logs_structured_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    orchestrator = _build_orchestrator(tmp_path, failure_mode="warn")

    manifest = _FakeManifest("python", requires_python="<3.13,>=3.12")
    with patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[
            RequiresPythonMismatch(
                manifest_path="/repo/pyproject.toml",
                specifier="<3.13,>=3.12",
                active_version="3.14.2",
            )
        ],
    ):
        with caplog.at_level("WARNING"):
            orchestrator._maybe_hardfail_requires_python([manifest])

    # Warn mode must not raise and must emit the structured warning shape
    # specified by AC-REQPY-PRECHECK.
    assert any(
        "does not satisfy requires-python=" in rec.message
        for rec in caplog.records
    )
    assert any(
        "3.14.2" in rec.message and "<3.13,>=3.12" in rec.message
        for rec in caplog.records
    )


def test_hardfail_requires_python_no_mismatch_is_noop(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(tmp_path, failure_mode="block")
    # Empty mismatches → method does nothing (neither raises nor logs).
    with patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[],
    ):
        orchestrator._maybe_hardfail_requires_python([])


def test_hardfail_requires_python_block_reports_additional_manifests(
    tmp_path: Path,
) -> None:
    orchestrator = _build_orchestrator(tmp_path, failure_mode="block")
    with patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[
            RequiresPythonMismatch("/a/pyproject.toml", ">=3.12", "3.11.9"),
            RequiresPythonMismatch("/b/pyproject.toml", ">=3.13", "3.11.9"),
        ],
    ):
        with pytest.raises(FeatureOrchestrationError) as exc:
            orchestrator._maybe_hardfail_requires_python([])
    assert "+1 additional manifest" in str(exc.value)


# ---------------------------------------------------------------------------
# End-to-end: _bootstrap_environment wires the gate through a mocked bootstrapper
# ---------------------------------------------------------------------------


class _FakeManifest:
    """
    Minimal DetectedManifest stand-in.

    Exposes the three surface points the pre-check + gate need: ``stack``
    (detector branch), ``path`` (used in mismatch records and debug logs),
    and ``get_requires_python()`` (pre-check — ``None`` = no constraint
    declared, making the pre-check a silent no-op).
    """

    def __init__(
        self,
        stack: str,
        requires_python: "str | None" = None,
        path: "Path | None" = None,
    ) -> None:
        self.stack = stack
        self._requires_python = requires_python
        self.path = path or Path(f"/tmp/fake-{stack}-manifest")

    def get_requires_python(self) -> "str | None":
        return self._requires_python


class _FakeWorktree:
    def __init__(self, path: Path) -> None:
        self.path = path


def test_bootstrap_environment_raises_in_block_mode(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(tmp_path, failure_mode="block")

    fake_result = _make_result(
        installs_attempted=1,
        installs_failed=1,
        stacks_detected=["python"],
        failure_details=[
            BootstrapFailureDetail(
                stack="python",
                manifest_path=str(tmp_path / "pyproject.toml"),
                stderr_excerpt="ERROR: externally-managed-environment",
                is_pep668=True,
                requires_python=">=3.13",
                essential=True,
            )
        ],
    )

    with patch(
        "guardkit.orchestrator.feature_orchestrator.ProjectEnvironmentDetector"
    ) as det_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.EnvironmentBootstrapper"
    ) as boot_cls:
        det_cls.return_value.detect.return_value = [_FakeManifest("python")]
        boot_cls.return_value.bootstrap.return_value = fake_result

        worktree = _FakeWorktree(tmp_path)
        with pytest.raises(FeatureOrchestrationError):
            orchestrator._bootstrap_environment(worktree)


def test_bootstrap_environment_returns_result_in_warn_mode(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(tmp_path, failure_mode="warn")

    fake_result = _make_result(
        installs_attempted=1,
        installs_failed=1,
        stacks_detected=["python"],
    )

    with patch(
        "guardkit.orchestrator.feature_orchestrator.ProjectEnvironmentDetector"
    ) as det_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.EnvironmentBootstrapper"
    ) as boot_cls:
        det_cls.return_value.detect.return_value = [_FakeManifest("python")]
        boot_cls.return_value.bootstrap.return_value = fake_result

        worktree = _FakeWorktree(tmp_path)
        got = orchestrator._bootstrap_environment(worktree)

    assert got is fake_result


def test_bootstrap_environment_requires_python_precheck_blocks_before_pip(
    tmp_path: Path,
) -> None:
    """
    End-to-end wire check: when the pre-check finds a mismatch in block mode,
    ``_bootstrap_environment`` must raise BEFORE the bootstrapper runs pip.
    """
    orchestrator = _build_orchestrator(tmp_path, failure_mode="block")

    with patch(
        "guardkit.orchestrator.feature_orchestrator.ProjectEnvironmentDetector"
    ) as det_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.EnvironmentBootstrapper"
    ) as boot_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[
            RequiresPythonMismatch(
                manifest_path=str(tmp_path / "pyproject.toml"),
                specifier="<3.13,>=3.12",
                active_version="3.14.2",
            )
        ],
    ):
        det_cls.return_value.detect.return_value = [_FakeManifest("python")]
        worktree = _FakeWorktree(tmp_path)

        with pytest.raises(FeatureOrchestrationError) as exc:
            orchestrator._bootstrap_environment(worktree)

    # The bootstrapper.bootstrap() method must NOT have been invoked — the
    # whole point of the pre-check is to skip the wasted pip round-trip.
    boot_cls.return_value.bootstrap.assert_not_called()
    msg = str(exc.value)
    assert "<3.13,>=3.12" in msg
    assert "uv python install" in msg


# ---------------------------------------------------------------------------
# TASK-ABSR-A1B2 — smart-default bootstrap_failure_mode
# ---------------------------------------------------------------------------


def test_compute_default_blocks_when_any_manifest_declares_requires_python() -> None:
    manifests = [
        _FakeManifest("python", requires_python=">=3.12"),
        _FakeManifest("node"),
    ]
    assert compute_default_bootstrap_failure_mode(manifests) == "block"


def test_compute_default_warns_when_no_requires_python() -> None:
    manifests = [
        _FakeManifest("python", requires_python=None),
        _FakeManifest("node"),
    ]
    assert compute_default_bootstrap_failure_mode(manifests) == "warn"


def test_compute_default_warns_for_empty_manifests() -> None:
    assert compute_default_bootstrap_failure_mode([]) == "warn"


def test_compute_default_ignores_objects_without_get_requires_python() -> None:
    class _NoAccessor:
        stack = "python"

    assert compute_default_bootstrap_failure_mode([_NoAccessor()]) == "warn"


def test_smart_default_blocks_when_requires_python_declared(tmp_path: Path) -> None:
    """
    AC: with no yaml and no CLI override, a manifest declaring
    ``requires-python`` must flip the resolved mode to ``"block"`` after
    manifest detection — and the resolution must fire BEFORE the
    requires-python pre-check / pip call.
    """
    orchestrator = _build_orchestrator(tmp_path)
    # Baseline at __init__ — still warn, not yet resolved.
    assert orchestrator.bootstrap_failure_mode == "warn"
    assert orchestrator._bootstrap_failure_mode_explicit is False

    fake_result = _make_result(
        installs_attempted=1,
        installs_failed=0,
        stacks_detected=["python"],
    )

    with patch(
        "guardkit.orchestrator.feature_orchestrator.ProjectEnvironmentDetector"
    ) as det_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.EnvironmentBootstrapper"
    ) as boot_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[],
    ):
        det_cls.return_value.detect.return_value = [
            _FakeManifest("python", requires_python=">=3.12")
        ]
        boot_cls.return_value.bootstrap.return_value = fake_result

        orchestrator._bootstrap_environment(_FakeWorktree(tmp_path))

    # After resolution: smart default flipped to block, and the orchestrator
    # is now treating the choice as explicit (so a between-wave second pass
    # does not re-evaluate).
    assert orchestrator.bootstrap_failure_mode == "block"
    assert orchestrator._bootstrap_failure_mode_explicit is True


def test_smart_default_warns_when_no_requires_python(tmp_path: Path) -> None:
    """AC: no manifest declares requires-python → resolved mode stays warn."""
    orchestrator = _build_orchestrator(tmp_path)

    fake_result = _make_result(
        installs_attempted=1,
        installs_failed=0,
        stacks_detected=["python"],
    )

    with patch(
        "guardkit.orchestrator.feature_orchestrator.ProjectEnvironmentDetector"
    ) as det_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.EnvironmentBootstrapper"
    ) as boot_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[],
    ):
        det_cls.return_value.detect.return_value = [
            _FakeManifest("python", requires_python=None),
            _FakeManifest("node"),
        ]
        boot_cls.return_value.bootstrap.return_value = fake_result

        orchestrator._bootstrap_environment(_FakeWorktree(tmp_path))

    assert orchestrator.bootstrap_failure_mode == "warn"
    assert orchestrator._bootstrap_failure_mode_explicit is True


def test_explicit_yaml_warn_overrides_smart_default_block(tmp_path: Path) -> None:
    """
    AC: an explicit yaml ``warn`` wins over the smart default that would
    otherwise have produced ``"block"``. The smart default is only applied
    when the user has not provided a value.
    """
    orchestrator = _build_orchestrator(
        tmp_path,
        write_config={"autobuild": {"bootstrap": {"failure_mode": "warn"}}},
    )
    # Yaml made the choice explicit — orchestrator records that.
    assert orchestrator.bootstrap_failure_mode == "warn"
    assert orchestrator._bootstrap_failure_mode_explicit is True

    fake_result = _make_result(
        installs_attempted=1,
        installs_failed=0,
        stacks_detected=["python"],
    )

    with patch(
        "guardkit.orchestrator.feature_orchestrator.ProjectEnvironmentDetector"
    ) as det_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.EnvironmentBootstrapper"
    ) as boot_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[],
    ):
        det_cls.return_value.detect.return_value = [
            _FakeManifest("python", requires_python=">=3.12")
        ]
        boot_cls.return_value.bootstrap.return_value = fake_result

        orchestrator._bootstrap_environment(_FakeWorktree(tmp_path))

    # Explicit yaml warn must NOT be flipped to block by the smart default.
    assert orchestrator.bootstrap_failure_mode == "warn"


def test_explicit_cli_warn_overrides_smart_default_block(tmp_path: Path) -> None:
    """
    AC: a CLI ``--bootstrap-failure-mode warn`` wins over both the yaml
    value and the smart default. Demonstrated against a yaml that says
    ``block`` and a manifest that would otherwise drive the smart default
    to ``block``.
    """
    orchestrator = _build_orchestrator(
        tmp_path,
        failure_mode="warn",
        write_config={"autobuild": {"bootstrap": {"failure_mode": "block"}}},
    )
    assert orchestrator.bootstrap_failure_mode == "warn"
    assert orchestrator._bootstrap_failure_mode_explicit is True

    fake_result = _make_result(
        installs_attempted=1,
        installs_failed=0,
        stacks_detected=["python"],
    )

    with patch(
        "guardkit.orchestrator.feature_orchestrator.ProjectEnvironmentDetector"
    ) as det_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.EnvironmentBootstrapper"
    ) as boot_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[],
    ):
        det_cls.return_value.detect.return_value = [
            _FakeManifest("python", requires_python=">=3.12")
        ]
        boot_cls.return_value.bootstrap.return_value = fake_result

        orchestrator._bootstrap_environment(_FakeWorktree(tmp_path))

    assert orchestrator.bootstrap_failure_mode == "warn"


def test_smart_default_logs_resolved_value_at_info(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The resolved smart default is logged at INFO once per orchestration run."""
    orchestrator = _build_orchestrator(tmp_path)

    fake_result = _make_result(
        installs_attempted=1,
        installs_failed=0,
        stacks_detected=["python"],
    )

    with patch(
        "guardkit.orchestrator.feature_orchestrator.ProjectEnvironmentDetector"
    ) as det_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.EnvironmentBootstrapper"
    ) as boot_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[],
    ):
        det_cls.return_value.detect.return_value = [
            _FakeManifest("python", requires_python=">=3.12")
        ]
        boot_cls.return_value.bootstrap.return_value = fake_result

        with caplog.at_level("INFO"):
            orchestrator._bootstrap_environment(_FakeWorktree(tmp_path))

    assert any(
        "smart default" in rec.message and "block" in rec.message
        for rec in caplog.records
    )


def test_replay_feat_j004_702c_preflight_blocks_before_wave1(tmp_path: Path) -> None:
    """
    Replay TASK-REV-FA04 / FEAT-J004-702C: a worktree whose pyproject
    declares a ``requires-python`` the active interpreter cannot satisfy,
    with no explicit ``bootstrap_failure_mode`` set. The smart default
    must flip to ``"block"`` and the requires-python pre-check must raise
    ``FeatureOrchestrationError`` *before* the bootstrapper runs pip,
    closing the silent-continue trapdoor that produced the original stall.
    """
    orchestrator = _build_orchestrator(tmp_path)
    # Confirm baseline pre-resolution.
    assert orchestrator.bootstrap_failure_mode == "warn"
    assert orchestrator._bootstrap_failure_mode_explicit is False

    with patch(
        "guardkit.orchestrator.feature_orchestrator.ProjectEnvironmentDetector"
    ) as det_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.EnvironmentBootstrapper"
    ) as boot_cls, patch(
        "guardkit.orchestrator.feature_orchestrator.check_requires_python_precheck",
        return_value=[
            RequiresPythonMismatch(
                manifest_path=str(tmp_path / "pyproject.toml"),
                specifier="<3.13,>=3.12",
                active_version="3.14.2",
            )
        ],
    ):
        det_cls.return_value.detect.return_value = [
            _FakeManifest("python", requires_python="<3.13,>=3.12")
        ]

        with pytest.raises(FeatureOrchestrationError) as exc:
            orchestrator._bootstrap_environment(_FakeWorktree(tmp_path))

    # The bootstrapper.bootstrap() must NOT have been invoked — preflight
    # caught it and saved the wasted wave.
    boot_cls.return_value.bootstrap.assert_not_called()
    msg = str(exc.value)
    assert "<3.13,>=3.12" in msg
    assert "uv python install" in msg
    # Smart default flipped the mode to block during resolution.
    assert orchestrator.bootstrap_failure_mode == "block"
