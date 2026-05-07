"""Bootstrap-extras plumbing for smoke-gate test deps (TASK-GK-BS-001).

Pins the contract that ``feature.bootstrap_extras`` (or the auto-detected
equivalent for a pytest smoke gate) gets threaded into the Python
``pyproject.toml`` install command, so the worktree's ``.venv`` has the
test deps the smoke gate needs.

The defect this guards against: FEAT-PEBR run-3, where the smoke gate
ran ``python -m pytest tests/bdd -m smoke -x`` against a worktree venv
that was bootstrapped with a bare ``uv pip install -e .`` (no extras),
producing ``No module named pytest`` at the gate boundary.

Coverage Target: >=85%
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List
from unittest.mock import Mock, patch

import pytest

from guardkit.orchestrator.environment_bootstrap import (
    EnvironmentBootstrapper,
    ProjectEnvironmentDetector,
    _resolve_python_pyproject_install_command,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
    SmokeGates,
    derive_bootstrap_extras,
)


# ============================================================================
# Helpers
# ============================================================================


def _write_pyproject(directory: Path, optional_deps: dict | None = None) -> Path:
    """Write a minimal pyproject.toml with optional optional-dependencies."""
    pyproject = directory / "pyproject.toml"
    lines = [
        "[build-system]",
        'requires = ["setuptools>=61"]',
        'build-backend = "setuptools.build_meta"',
        "",
        "[project]",
        'name = "fixture"',
        'version = "0.0.0"',
        'dependencies = []',
    ]
    if optional_deps:
        lines.append("")
        lines.append("[project.optional-dependencies]")
        for extra_name, deps in optional_deps.items():
            deps_repr = ", ".join(f'"{d}"' for d in deps)
            lines.append(f"{extra_name} = [{deps_repr}]")
    pyproject.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return pyproject


def _make_feature(
    *,
    bootstrap_extras: List[str] | None = None,
    smoke_command: str | None = None,
) -> Feature:
    """Construct a minimal Feature instance for derive_bootstrap_extras tests."""
    smoke_gates = None
    if smoke_command is not None:
        smoke_gates = SmokeGates(
            after_wave=1,
            command=smoke_command,
        )
    return Feature(
        id="FEAT-FIXT",
        name="Fixture",
        bootstrap_extras=bootstrap_extras or [],
        smoke_gates=smoke_gates,
    )


# ============================================================================
# AC-2 / AC-4: _resolve_python_pyproject_install_command honours extras
# ============================================================================


class TestResolveCommandHonoursExtras:
    """``_resolve_python_pyproject_install_command(extras=...)`` contract."""

    def test_pip_no_extras_unchanged(self, tmp_path: Path) -> None:
        """No extras → install target stays ``.`` (regression guard for AC-6)."""
        pyproject = _write_pyproject(tmp_path)
        cmd = _resolve_python_pyproject_install_command(tmp_path, pyproject)
        # Last token is the install target; without extras it must be ``.``
        assert cmd[-1] == "."
        assert cmd == [sys.executable, "-m", "pip", "install", "-e", "."]

    def test_pip_with_single_extra_appends_brackets(self, tmp_path: Path) -> None:
        """``extras=['dev']`` → ``pip install -e .[dev]`` (AC-2 pip variant, AC-4)."""
        pyproject = _write_pyproject(tmp_path, {"dev": ["pytest"]})
        cmd = _resolve_python_pyproject_install_command(
            tmp_path, pyproject, extras=["dev"]
        )
        assert cmd[-1] == ".[dev]"
        assert cmd == [sys.executable, "-m", "pip", "install", "-e", ".[dev]"]

    def test_pip_with_multiple_extras_comma_joined_and_sorted(
        self, tmp_path: Path
    ) -> None:
        """Multiple extras comma-joined, sorted, deduped for deterministic output."""
        pyproject = _write_pyproject(tmp_path)
        cmd = _resolve_python_pyproject_install_command(
            tmp_path, pyproject, extras=["test", "dev", "dev"]
        )
        # Sorted alphabetically + deduped
        assert cmd[-1] == ".[dev,test]"

    def test_uv_sources_with_extras(self, tmp_path: Path) -> None:
        """``[tool.uv.sources]`` path → ``uv pip install -e .[dev]`` (AC-2 uv variant)."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\n"
            'name = "fixture"\n'
            'version = "0.0.0"\n'
            "[tool.uv.sources]\n"
            "lib = { path = '../lib' }\n",
            encoding="utf-8",
        )
        with patch(
            "guardkit.orchestrator.environment_bootstrap._uv_on_path",
            return_value=True,
        ):
            cmd = _resolve_python_pyproject_install_command(
                tmp_path, pyproject, extras=["dev"]
            )
        assert cmd == ["uv", "pip", "install", "-e", ".[dev]"]

    def test_uv_sync_frozen_warns_and_skips_extras(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """``uv.lock`` row warns + skips extras (AC-2 uv sync caveat).

        Extras are baked into the lockfile at ``uv lock --extra`` time, not
        at install time — applying them to ``uv sync --frozen`` would
        diverge from the lock. The warning gives the operator the right
        next step.
        """
        pyproject = _write_pyproject(tmp_path)
        (tmp_path / "uv.lock").write_text("# stub uv.lock", encoding="utf-8")
        with patch(
            "guardkit.orchestrator.environment_bootstrap._uv_on_path",
            return_value=True,
        ):
            with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.environment_bootstrap"):
                cmd = _resolve_python_pyproject_install_command(
                    tmp_path, pyproject, extras=["dev"]
                )
        assert cmd == ["uv", "sync", "--frozen"]
        # Warning surfaces both the extras list and the lock-time fix.
        assert any(
            "uv.lock" in r.getMessage() and "uv lock --extra dev" in r.getMessage()
            for r in caplog.records
        ), f"expected warning about uv.lock + uv lock --extra; got {[r.getMessage() for r in caplog.records]}"

    def test_default_extras_empty_tuple_does_not_modify_target(
        self, tmp_path: Path
    ) -> None:
        """Backward-compatibility: no ``extras`` kwarg → identical to pre-fix call."""
        pyproject = _write_pyproject(tmp_path)
        without_kw = _resolve_python_pyproject_install_command(tmp_path, pyproject)
        with_empty = _resolve_python_pyproject_install_command(
            tmp_path, pyproject, extras=()
        )
        assert without_kw == with_empty


# ============================================================================
# AC-3 / AC-5 / AC-6: derive_bootstrap_extras auto-detection
# ============================================================================


class TestSmokeGateExtraDetection:
    """``derive_bootstrap_extras`` auto-detection from a pytest smoke gate.

    The repro fixture mirrors FEAT-PEBR run-3: a feature yaml whose
    ``smoke_gates.command`` runs ``python -m pytest tests/bdd -m smoke``,
    paired with a project ``pyproject.toml`` that declares
    ``[project.optional-dependencies].dev = ["pytest"]``. Today's bug:
    bootstrap installs without ``[dev]``, smoke gate fails. The fix:
    auto-detect ``[dev]`` and thread it into the install command.
    """

    def test_explicit_bootstrap_extras_wins_over_auto_detect(
        self, tmp_path: Path
    ) -> None:
        """AC-5: explicit list suppresses auto-detection.

        Operator-declared takes precedence — even when a pytest smoke gate
        is present and would otherwise auto-add ``[dev]``.
        """
        _write_pyproject(tmp_path, {"dev": ["pytest"], "test": ["pytest"]})
        feature = _make_feature(
            bootstrap_extras=["test", "integration"],
            smoke_command="pytest tests/bdd -m smoke",
        )
        extras = derive_bootstrap_extras(feature, tmp_path)
        # Explicit declaration preserved verbatim — auto-detection NOT applied.
        assert extras == ["test", "integration"]

    def test_pytest_smoke_gate_auto_adds_dev(self, tmp_path: Path) -> None:
        """AC-3: pytest smoke gate + ``[dev]`` in pyproject → auto-add ``[dev]``.

        FEAT-PEBR run-3 reproducer: this is the exact case that would have
        prevented the smoke-gate failure if the auto-detection had existed.
        """
        _write_pyproject(tmp_path, {"dev": ["pytest", "pytest-bdd"]})
        feature = _make_feature(smoke_command="python -m pytest tests/bdd -m smoke")
        extras = derive_bootstrap_extras(feature, tmp_path)
        assert extras == ["dev"]

    def test_pytest_smoke_gate_falls_back_to_test_extra(
        self, tmp_path: Path
    ) -> None:
        """AC-3: ``[dev]`` absent but ``[test]`` present → auto-add ``[test]``.

        ``[dev]`` is preferred (PyPA convention for "all the things a
        contributor needs") but ``[test]`` is also conventional. The
        candidate list is searched in order; first hit wins.
        """
        _write_pyproject(tmp_path, {"test": ["pytest"]})
        feature = _make_feature(smoke_command="pytest tests/bdd")
        extras = derive_bootstrap_extras(feature, tmp_path)
        assert extras == ["test"]

    def test_pytest_smoke_gate_no_candidate_extras_warns_and_returns_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC-3 final clause: pytest smoke gate but neither ``[dev]`` nor
        ``[test]`` declared → warn + return ``[]``.

        Matches pre-fix behaviour (no extras) but with a useful warning so
        the operator knows why the smoke gate is about to fail.
        """
        _write_pyproject(tmp_path)  # no optional-deps
        feature = _make_feature(smoke_command="pytest tests/bdd")
        with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.feature_loader"):
            extras = derive_bootstrap_extras(feature, tmp_path)
        assert extras == []
        assert any(
            "[dev]" in r.getMessage() and "[test]" in r.getMessage()
            for r in caplog.records
        ), "expected warning naming both [dev] and [test] candidates"

    def test_pytest_word_boundary_does_not_match_substring(
        self, tmp_path: Path
    ) -> None:
        """``\\bpytest\\b`` doesn't trigger on tokens like ``pytestify-runner``.

        Conservative regex prevents over-eager auto-detection on commands
        that happen to contain ``pytest`` as a substring of an unrelated
        tool name.
        """
        _write_pyproject(tmp_path, {"dev": ["pytest"]})
        feature = _make_feature(smoke_command="pytestify-runner --check")
        assert derive_bootstrap_extras(feature, tmp_path) == []

    def test_pytest_match_is_case_insensitive(self, tmp_path: Path) -> None:
        """``Pytest`` / ``PYTEST`` in operator commands also fire auto-detect."""
        _write_pyproject(tmp_path, {"dev": ["pytest"]})
        feature = _make_feature(smoke_command="PYTEST -q")
        assert derive_bootstrap_extras(feature, tmp_path) == ["dev"]

    def test_no_smoke_gate_no_extras(self, tmp_path: Path) -> None:
        """AC-6: no smoke gate AND no explicit extras → ``[]``."""
        _write_pyproject(tmp_path, {"dev": ["pytest"]})
        feature = _make_feature()  # no smoke_gates, no bootstrap_extras
        assert derive_bootstrap_extras(feature, tmp_path) == []

    def test_non_pytest_smoke_gate_no_auto_detect(self, tmp_path: Path) -> None:
        """AC-6: smoke gate that doesn't reference pytest → no auto-detect."""
        _write_pyproject(tmp_path, {"dev": ["pytest"]})
        feature = _make_feature(smoke_command="bash scripts/integration.sh")
        assert derive_bootstrap_extras(feature, tmp_path) == []

    def test_missing_pyproject_returns_empty(self, tmp_path: Path) -> None:
        """No ``pyproject.toml`` in project_dir → no candidate extras → ``[]``."""
        feature = _make_feature(smoke_command="pytest tests/")
        assert derive_bootstrap_extras(feature, tmp_path) == []

    def test_malformed_pyproject_returns_empty(self, tmp_path: Path) -> None:
        """Unparseable ``pyproject.toml`` → swallow + return ``[]``.

        Conservative: detection helpers shouldn't blow up on a malformed
        TOML; the actual install command will surface the real error.
        """
        (tmp_path / "pyproject.toml").write_text(
            "this is not [valid toml ===",
            encoding="utf-8",
        )
        feature = _make_feature(smoke_command="pytest tests/")
        assert derive_bootstrap_extras(feature, tmp_path) == []


# ============================================================================
# AC-1: Feature loader validates bootstrap_extras name regex
# ============================================================================


class TestBootstrapExtrasFieldValidation:
    """``Feature.bootstrap_extras`` field constraints (AC-1)."""

    def test_valid_extras_accepted(self) -> None:
        """Standard PEP 621 names accepted without complaint."""
        feature = Feature(
            id="FEAT-X",
            name="X",
            bootstrap_extras=["dev", "test", "pg-driver", "extra_thing", "v1.0"],
        )
        assert feature.bootstrap_extras == ["dev", "test", "pg-driver", "extra_thing", "v1.0"]

    def test_default_is_empty_list(self) -> None:
        """Field defaults to an empty list (existing yamls behave unchanged)."""
        feature = Feature(id="FEAT-X", name="X")
        assert feature.bootstrap_extras == []

    def test_invalid_name_with_space_rejected(self) -> None:
        """Names with spaces are not valid PEP 621 → rejected at parse time."""
        with pytest.raises(Exception) as exc_info:
            Feature(id="FEAT-X", name="X", bootstrap_extras=["dev things"])
        assert "invalid PEP 621 extra name" in str(exc_info.value)

    def test_invalid_name_with_bracket_rejected(self) -> None:
        """Brackets in the name (likely a copy-paste error) → rejected."""
        with pytest.raises(Exception) as exc_info:
            Feature(id="FEAT-X", name="X", bootstrap_extras=["[dev]"])
        assert "invalid PEP 621 extra name" in str(exc_info.value)

    def test_non_string_entry_rejected(self) -> None:
        """Non-string entries in the list → rejected."""
        with pytest.raises(Exception):
            Feature(id="FEAT-X", name="X", bootstrap_extras=[123])  # type: ignore[list-item]

    def test_empty_extras_load_round_trip(self, tmp_path: Path) -> None:
        """Empty ``bootstrap_extras`` is dropped from YAML on save (round-trip)."""
        feature = Feature(
            id="FEAT-RT",
            name="RT",
            tasks=[],
            bootstrap_extras=[],
        )
        feature.file_path = tmp_path / "FEAT-RT.yaml"
        # Bypass save's validate-tasks check by directly serializing
        data = FeatureLoader._feature_to_dict(feature)
        assert "bootstrap_extras" not in data, (
            "empty bootstrap_extras should be dropped from YAML output"
        )

    def test_non_empty_extras_serialized_to_yaml(self, tmp_path: Path) -> None:
        """Non-empty ``bootstrap_extras`` is preserved in YAML output."""
        feature = Feature(
            id="FEAT-RT",
            name="RT",
            tasks=[],
            bootstrap_extras=["dev", "test"],
        )
        data = FeatureLoader._feature_to_dict(feature)
        assert data.get("bootstrap_extras") == ["dev", "test"]


# ============================================================================
# AC-7: End-to-end through the bootstrap call (mocked subprocess)
# ============================================================================


class TestEndToEndBootstrapWithExtras:
    """End-to-end: detector → bootstrapper → subprocess command line.

    Verifies the actual command line that hits ``subprocess.run`` matches
    the expected ``[..., "-e", ".[dev]"]`` shape when extras are threaded
    through. This is the test that would have caught the FEAT-PEBR run-3
    defect before it shipped.
    """

    def test_python_extras_reach_install_command(self, tmp_path: Path) -> None:
        """Detector with ``python_extras=['dev']`` produces the right install command."""
        _write_pyproject(tmp_path, {"dev": ["pytest"]})
        detector = ProjectEnvironmentDetector(
            tmp_path,
            python_extras=("dev",),
        )
        manifests = detector.detect()
        python = [m for m in manifests if m.stack == "python"]
        assert len(python) == 1
        assert python[0].install_command[-1] == ".[dev]"

    def test_python_extras_empty_default_unchanged(self, tmp_path: Path) -> None:
        """Default ``python_extras=()`` keeps install command as ``.``.

        Backward-compat regression guard: existing call sites that don't
        pass ``python_extras`` see identical behaviour.
        """
        _write_pyproject(tmp_path, {"dev": ["pytest"]})
        detector = ProjectEnvironmentDetector(tmp_path)
        manifests = detector.detect()
        python = [m for m in manifests if m.stack == "python"]
        assert python[0].install_command[-1] == "."

    def test_subprocess_run_receives_extras_install_command(
        self, tmp_path: Path
    ) -> None:
        """Mocked ``subprocess.run`` sees ``[..., '-e', '.[dev]']`` (AC-7).

        Threads the full path: detector builds command with extras →
        bootstrapper hands it to subprocess. Asserts the *actual command
        line* the kernel would run.
        """
        _write_pyproject(tmp_path, {"dev": ["pytest"]})
        # Satisfy ``_python_pyproject_is_complete``: project layout must
        # have an importable package (or no ``name`` field). Test fixture
        # uses ``name = "fixture"`` so create ``src/fixture/`` to make
        # the manifest "complete" and dispatch to the install command.
        (tmp_path / "src" / "fixture").mkdir(parents=True)
        (tmp_path / "src" / "fixture" / "__init__.py").write_text("", encoding="utf-8")
        detector = ProjectEnvironmentDetector(
            tmp_path,
            python_extras=("dev",),
        )
        manifests = detector.detect()

        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            bootstrapper.bootstrap(manifests)

        # At least one subprocess.run call was the install. Find the one
        # that contains the install command (some backends issue extra
        # probe calls — e.g. uv venv creation).
        install_calls = [
            c for c in mock_run.call_args_list
            if c.args and isinstance(c.args[0], list)
            and any(tok == "-e" for tok in c.args[0])
        ]
        assert install_calls, (
            "expected at least one subprocess.run call carrying the "
            f"editable-install command; got: {mock_run.call_args_list}"
        )
        install_cmd = install_calls[0].args[0]
        # Last arg must be ``.[dev]`` — the whole point of the fix.
        assert install_cmd[-1] == ".[dev]", (
            f"install command did not carry [dev] extra: {install_cmd}"
        )
