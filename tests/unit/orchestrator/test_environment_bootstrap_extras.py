"""Bootstrap-extras plumbing for smoke-gate test deps (TASK-GK-BS-001),
extended for the Coach's unconditional pytest need (TASK-FIX-BOOTPYTEST01).

Pins the contract that ``feature.bootstrap_extras`` (or the auto-detected
equivalent for a pytest smoke gate, or — TASK-FIX-BOOTPYTEST01 — a
pytest-providing ``[dev]``/``[test]`` extra even with no smoke gate) gets
threaded into the Python ``pyproject.toml`` install command, so the
worktree's ``.venv`` has the test deps the Coach's independent-test gate
needs.

The defects this guards against:

- FEAT-PEBR run-3 (TASK-GK-BS-001): a pytest smoke gate ran
  ``python -m pytest tests/bdd -m smoke -x`` against a worktree venv
  bootstrapped with a bare ``uv pip install -e .`` (no extras), producing
  ``No module named pytest`` at the gate boundary.
- FEAT-E2CB run-1 (TASK-FIX-BOOTPYTEST01): a feature with NEITHER
  ``bootstrap_extras`` NOR ``smoke_gates`` left the worktree venv without
  pytest, so the Coach's pinned independent-test interpreter could not
  ``import pytest`` on turns 1-2 — burning turns and contributing to a
  timeout. The Coach runs pytest unconditionally, so a pytest-providing
  test extra must be installed regardless of smoke-gate config.

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
    DetectedManifest,
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
        tool name. The ``[dev]`` extra here carries no pytest, so the
        Coach-always-needs-pytest branch (TASK-FIX-BOOTPYTEST01) also stays
        silent — isolating this assertion to the smoke-gate regex.
        """
        _write_pyproject(tmp_path, {"dev": ["ruff"]})
        feature = _make_feature(smoke_command="pytestify-runner --check")
        assert derive_bootstrap_extras(feature, tmp_path) == []

    def test_pytest_match_is_case_insensitive(self, tmp_path: Path) -> None:
        """``Pytest`` / ``PYTEST`` in operator commands also fire auto-detect."""
        _write_pyproject(tmp_path, {"dev": ["pytest"]})
        feature = _make_feature(smoke_command="PYTEST -q")
        assert derive_bootstrap_extras(feature, tmp_path) == ["dev"]

    def test_no_smoke_gate_no_test_extra_returns_empty(self, tmp_path: Path) -> None:
        """No smoke gate AND no pytest-providing extra → ``[]``.

        Supersedes the original TASK-GK-BS-001 AC-6 case (which used a
        ``[dev]=["pytest"]`` fixture and asserted ``[]``): under
        TASK-FIX-BOOTPYTEST01 a ``[dev]`` extra that *provides* pytest is now
        auto-added even without a smoke gate (see ``TestCoachAlwaysNeedsPytest``).
        The residual no-extras guarantee is the genuinely-no-test-deps case
        asserted here.
        """
        _write_pyproject(tmp_path)  # no optional-dependencies at all
        feature = _make_feature()  # no smoke_gates, no bootstrap_extras
        assert derive_bootstrap_extras(feature, tmp_path) == []

    def test_non_pytest_smoke_gate_no_auto_detect(self, tmp_path: Path) -> None:
        """A smoke gate not referencing pytest → no smoke-gate auto-detect.

        The ``[dev]`` extra carries no pytest, so the Coach-always-needs-pytest
        branch (TASK-FIX-BOOTPYTEST01) also stays silent — isolating this
        assertion to branch 2 (the smoke-gate command check).
        """
        _write_pyproject(tmp_path, {"dev": ["ruff"]})
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
# TASK-FIX-BOOTPYTEST01: Coach independent-test gate always needs pytest
# ============================================================================


class TestCoachAlwaysNeedsPytest:
    """``derive_bootstrap_extras`` branch 3 — the Coach runs pytest
    unconditionally, so a ``[dev]``/``[test]`` extra that provides pytest is
    installed even without an operator declaration or a pytest smoke gate.

    Defect this guards against: FEAT-E2CB run-1 (2026-06-12). The feature
    yaml declared neither ``bootstrap_extras`` nor a ``smoke_gates`` block,
    so ``derive_bootstrap_extras`` returned ``[]`` and the worktree
    ``.venv`` was bootstrapped with ``pip install -e .`` (runtime deps
    only). The Coach pinned its independent-test interpreter to that venv
    and could not ``import pytest`` on turns 1-2.
    """

    def test_no_smoke_gate_auto_adds_dev_when_dev_provides_pytest(
        self, tmp_path: Path
    ) -> None:
        """AC-2 core: no smoke gate, ``[dev]`` carries pytest → ``[dev]``.

        This is the exact FEAT-E2CB shape — a Python project (guardkit
        itself) whose ``[dev]`` extra declares pytest, built by a feature
        with no smoke gate. Before the fix this returned ``[]``.
        """
        _write_pyproject(tmp_path, {"dev": ["pytest>=7.4.3", "pytest-bdd>=8.1,<9"]})
        feature = _make_feature()  # no smoke_gates, no bootstrap_extras
        assert derive_bootstrap_extras(feature, tmp_path) == ["dev"]

    def test_pytest_plugin_only_extra_counts_as_test_extra(
        self, tmp_path: Path
    ) -> None:
        """A ``[dev]`` with only a pytest *plugin* (no bare pytest) still counts.

        ``\\bpytest\\b`` matches ``pytest-bdd`` / ``pytest-asyncio`` — a
        plugin pulls pytest transitively, so the extra is test-capable.
        """
        _write_pyproject(tmp_path, {"dev": ["pytest-asyncio>=0.23.0"]})
        feature = _make_feature()
        assert derive_bootstrap_extras(feature, tmp_path) == ["dev"]

    def test_dev_without_pytest_is_not_force_added(self, tmp_path: Path) -> None:
        """Precision guard: a ``[dev]`` of only linters is NOT auto-added.

        The unconditional branch installs an extra only when it demonstrably
        provides pytest — it must not drag in unrelated dev tooling the
        Coach doesn't need.
        """
        _write_pyproject(tmp_path, {"dev": ["ruff>=0.1", "mypy>=1.0"]})
        feature = _make_feature()
        assert derive_bootstrap_extras(feature, tmp_path) == []

    def test_prefers_first_candidate_that_provides_pytest(
        self, tmp_path: Path
    ) -> None:
        """``[dev]`` without pytest but ``[test]`` with it → ``[test]``.

        The content-aware filter skips a pytest-less ``[dev]`` and finds the
        ``[test]`` extra that actually carries pytest — stricter (and more
        correct for the Coach) than the smoke-gate branch's name-only probe.
        """
        _write_pyproject(tmp_path, {"dev": ["ruff"], "test": ["pytest>=7.4.3"]})
        feature = _make_feature()
        assert derive_bootstrap_extras(feature, tmp_path) == ["test"]

    def test_dev_preferred_over_test_when_both_provide_pytest(
        self, tmp_path: Path
    ) -> None:
        """Both extras carry pytest → ``[dev]`` wins (candidate order)."""
        _write_pyproject(tmp_path, {"dev": ["pytest"], "test": ["pytest"]})
        feature = _make_feature()
        assert derive_bootstrap_extras(feature, tmp_path) == ["dev"]

    def test_emits_info_log_explaining_coach_pytest(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The auto-add logs an INFO breadcrumb naming the Coach rationale.

        Future "why did [dev] get installed?" diagnostics should find the
        reason in the log rather than re-deriving it.
        """
        _write_pyproject(tmp_path, {"dev": ["pytest"]})
        feature = _make_feature()
        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.feature_loader"
        ):
            extras = derive_bootstrap_extras(feature, tmp_path)
        assert extras == ["dev"]
        assert any(
            "Coach runs independent pytest" in r.getMessage()
            and "[dev]" in r.getMessage()
            for r in caplog.records
        ), f"expected Coach-pytest INFO log; got {[r.getMessage() for r in caplog.records]}"

    def test_no_pyproject_returns_empty(self, tmp_path: Path) -> None:
        """No pyproject at all (e.g. a non-Python worktree) → ``[]``."""
        feature = _make_feature()  # no smoke gate, no extras
        assert derive_bootstrap_extras(feature, tmp_path) == []

    def test_explicit_extras_still_win_without_smoke_gate(
        self, tmp_path: Path
    ) -> None:
        """Operator-declared extras short-circuit branch 3 too (AC-5 preserved)."""
        _write_pyproject(tmp_path, {"dev": ["pytest"], "test": ["pytest"]})
        feature = _make_feature(bootstrap_extras=["test"])
        assert derive_bootstrap_extras(feature, tmp_path) == ["test"]


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

    def test_no_smoke_gate_pytest_extra_threads_to_install_command(
        self, tmp_path: Path
    ) -> None:
        """AC-3 chain: Coach-needs-pytest derive → detector → ``.[dev]`` command.

        Proves end-to-end that a Python project declaring a pytest-providing
        ``[dev]`` extra, built by a feature with NO smoke gate, produces an
        install command carrying ``.[dev]`` — i.e. the worktree venv the
        Coach pins to (``BootstrapResult.venv_python``) will have pytest
        before the first independent-test run. This is the regression that
        directly closes the FEAT-E2CB run-1 gap (TASK-FIX-BOOTPYTEST01).
        """
        _write_pyproject(tmp_path, {"dev": ["pytest>=7.4.3"]})
        feature = _make_feature()  # no smoke_gates, no bootstrap_extras
        extras = derive_bootstrap_extras(feature, tmp_path)
        assert extras == ["dev"]
        detector = ProjectEnvironmentDetector(
            tmp_path,
            python_extras=tuple(extras),
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


# ============================================================================
# TASK-FIX-BSEXTRAS01 — the INCOMPLETE-project per-dependency install path
# must honour requested extras too. FEAT-9DDE run-6: guardkit-py's import name
# (guardkit_py) does not match the guardkit/ dir, so
# ``_python_pyproject_is_complete()`` is False → the editable ``.[dev]`` path
# above is skipped and the per-dep path ran instead — which dropped pytest
# ([dev]) entirely. The worktree venv then lacked pytest and the Coach
# independent test failed 0.0s with "No module named pytest".
# ============================================================================


def _write_incomplete_pyproject_with_base_and_dev(directory: Path) -> Path:
    """pyproject with a base dep AND a [dev] extra whose ``name`` has no
    matching source dir → ``_python_pyproject_is_complete()`` is False (the
    incomplete-project per-dependency install path is taken)."""
    pyproject = directory / "pyproject.toml"
    pyproject.write_text(
        "[build-system]\n"
        'requires = ["setuptools>=61"]\n'
        'build-backend = "setuptools.build_meta"\n'
        "\n"
        "[project]\n"
        'name = "fixture-pkg"\n'  # no fixture_pkg/ dir → incomplete
        'version = "0.0.0"\n'
        'dependencies = ["click>=8.0.0"]\n'
        "\n"
        "[project.optional-dependencies]\n"
        'dev = ["pytest>=7.4.3", "pytest-cov"]\n',
        encoding="utf-8",
    )
    return pyproject


class TestPerDepPathHonoursExtras:
    """The incomplete-project per-dependency install path installs base deps
    AND requested extras; the default (no extras) is unchanged."""

    def test_per_dep_commands_include_requested_extra(self, tmp_path: Path) -> None:
        pyproject = _write_incomplete_pyproject_with_base_and_dev(tmp_path)
        manifest = DetectedManifest(
            path=pyproject,
            stack="python",
            is_lock_file=False,
            install_command=[sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
            python_extras=("dev",),
        )
        # Confirm we are exercising the per-dep (incomplete) path.
        assert manifest.is_project_complete() is False
        cmds = manifest.get_dependency_install_commands()
        assert cmds is not None
        targets = [c[-1] for c in cmds]
        assert any(t.startswith("pytest") for t in targets), targets  # extra installed
        assert any(t.startswith("click") for t in targets), targets   # base dep kept

    def test_no_extras_installs_only_base_deps(self, tmp_path: Path) -> None:
        pyproject = _write_incomplete_pyproject_with_base_and_dev(tmp_path)
        manifest = DetectedManifest(
            path=pyproject,
            stack="python",
            is_lock_file=False,
            install_command=[sys.executable, "-m", "pip", "install", "-e", "."],
            python_extras=(),  # backward-compat: no extras requested
        )
        targets = [c[-1] for c in manifest.get_dependency_install_commands()]
        assert any(t.startswith("click") for t in targets)
        assert not any(t.startswith("pytest") for t in targets)  # extra NOT pulled

    def test_missing_extra_group_warns_and_skips(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\n"
            'name = "fixture-pkg"\n'
            'version = "0.0.0"\n'
            'dependencies = ["click"]\n',
            encoding="utf-8",
        )
        manifest = DetectedManifest(
            path=pyproject,
            stack="python",
            is_lock_file=False,
            install_command=[sys.executable, "-m", "pip", "install", "-e", "."],
            python_extras=("dev",),  # requested but not declared
        )
        with caplog.at_level(
            logging.WARNING, logger="guardkit.orchestrator.environment_bootstrap"
        ):
            targets = [c[-1] for c in manifest.get_dependency_install_commands()]
        assert targets == ["click"]  # base only; missing extra skipped, not fatal
        assert any(
            "optional-dependency group 'dev'" in r.getMessage()
            for r in caplog.records
        ), [r.getMessage() for r in caplog.records]

    def test_detector_threads_extras_onto_incomplete_manifest(
        self, tmp_path: Path
    ) -> None:
        """End-to-end guard for the construction-site threading: a detector
        built with ``python_extras=('dev',)`` stamps them onto the pyproject
        manifest, so the per-dep path can see them."""
        _write_incomplete_pyproject_with_base_and_dev(tmp_path)
        detector = ProjectEnvironmentDetector(tmp_path, python_extras=("dev",))
        python = [
            m
            for m in detector.detect()
            if m.stack == "python" and m.path.name == "pyproject.toml"
        ]
        assert len(python) == 1
        assert python[0].python_extras == ("dev",)
        assert python[0].is_project_complete() is False
        targets = [c[-1] for c in python[0].get_dependency_install_commands()]
        assert any(t.startswith("pytest") for t in targets), targets
