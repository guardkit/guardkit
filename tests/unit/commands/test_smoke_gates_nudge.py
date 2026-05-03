"""Tests for installer/core/commands/lib/smoke_gates_nudge.py (TASK-FP-NDG2).

Covers the four AC branches (2 x wave-count x smoke-key-presence):

- Notice fires when feature YAML lacks ``smoke_gates:`` AND has >= 2 waves.
- Notice does not fire when ``smoke_gates:`` is present (even if minimal).
- Notice does not fire for single-wave features.
- Notice is suppressible via ``quiet=True``.

Plus defensive branches (missing file, malformed YAML, non-mapping root,
missing ``orchestration`` block) — the helper must never be the reason
``/feature-plan`` surfaces a traceback.
"""

from pathlib import Path

import pytest

from installer.core.commands.lib.smoke_gates_nudge import (
    check_smoke_gates_activation,
    discover_test_roots,
)


_TWO_WAVE_NO_SMOKE = """\
id: FEAT-T100
name: Example feature
description: Two waves, no smoke_gates configured
orchestration:
  parallel_groups:
    - [TASK-001]
    - [TASK-002, TASK-003]
  estimated_duration_minutes: 30
  recommended_parallel: 2
"""

_TWO_WAVE_WITH_SMOKE = """\
id: FEAT-T101
name: Example feature
description: Two waves with smoke_gates block
smoke_gates:
  after_wave_1:
    - python -c "import example"
orchestration:
  parallel_groups:
    - [TASK-001]
    - [TASK-002]
  estimated_duration_minutes: 30
  recommended_parallel: 2
"""

_TWO_WAVE_EMPTY_SMOKE = """\
id: FEAT-T102
name: Example feature
description: Two waves with smoke_gates present but null
smoke_gates:
orchestration:
  parallel_groups:
    - [TASK-001]
    - [TASK-002]
  estimated_duration_minutes: 30
  recommended_parallel: 2
"""

_ONE_WAVE_NO_SMOKE = """\
id: FEAT-T103
name: Single wave feature
description: Documentation-only, one wave
orchestration:
  parallel_groups:
    - [TASK-001, TASK-002]
  estimated_duration_minutes: 10
  recommended_parallel: 2
"""

_ONE_WAVE_WITH_SMOKE = """\
id: FEAT-T104
name: Single wave with smoke_gates
description: Honour author's config regardless of wave count
smoke_gates:
  after_wave_1:
    - pytest tests/smoke -x
orchestration:
  parallel_groups:
    - [TASK-001]
  estimated_duration_minutes: 10
  recommended_parallel: 1
"""

_THREE_WAVES_NO_SMOKE = """\
id: FEAT-T105
name: Three wave feature
description: Larger feature, no smoke_gates
orchestration:
  parallel_groups:
    - [TASK-001]
    - [TASK-002]
    - [TASK-003]
  estimated_duration_minutes: 60
  recommended_parallel: 2
"""


@pytest.fixture
def yaml_path(tmp_path: Path) -> Path:
    """Path to a feature YAML that does not yet exist (caller writes body)."""
    return tmp_path / "FEAT-T.yaml"


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# AC 1: Notice fires when feature YAML lacks smoke_gates AND has >= 2 waves
# ---------------------------------------------------------------------------


def test_returns_notice_when_two_waves_without_smoke_gates(
    yaml_path: Path,
) -> None:
    _write(yaml_path, _TWO_WAVE_NO_SMOKE)
    result = check_smoke_gates_activation(yaml_path)

    assert result is not None
    assert "Feature-level smoke gates (R3) not configured" in result
    assert "2 waves" in result  # actual wave count interpolated
    assert "smoke_gates:" in result  # copy-pasteable example
    # New (TASK-FIX-B5BF): example uses canonical flat-object schema, not
    # the old after_wave_N dict-of-waves shape that failed validation.
    assert "after_wave:" in result
    assert "command:" in result
    assert "feature-plan.md" in result  # canonical doc pointer


def test_returns_notice_reports_actual_wave_count(yaml_path: Path) -> None:
    _write(yaml_path, _THREE_WAVES_NO_SMOKE)
    result = check_smoke_gates_activation(yaml_path)

    assert result is not None
    assert "3 waves" in result


# ---------------------------------------------------------------------------
# AC 2: Notice does not fire when smoke_gates: is present (even if minimal)
# ---------------------------------------------------------------------------


def test_returns_none_when_smoke_gates_configured(yaml_path: Path) -> None:
    _write(yaml_path, _TWO_WAVE_WITH_SMOKE)
    assert check_smoke_gates_activation(yaml_path) is None


def test_returns_none_when_smoke_gates_key_present_but_null(
    yaml_path: Path,
) -> None:
    # "even if minimal" — author has signalled awareness with just the key.
    _write(yaml_path, _TWO_WAVE_EMPTY_SMOKE)
    assert check_smoke_gates_activation(yaml_path) is None


# ---------------------------------------------------------------------------
# AC 3: Notice does not fire for single-wave features
# ---------------------------------------------------------------------------


def test_returns_none_for_single_wave_without_smoke_gates(
    yaml_path: Path,
) -> None:
    _write(yaml_path, _ONE_WAVE_NO_SMOKE)
    assert check_smoke_gates_activation(yaml_path) is None


def test_returns_none_for_single_wave_with_smoke_gates(
    yaml_path: Path,
) -> None:
    _write(yaml_path, _ONE_WAVE_WITH_SMOKE)
    assert check_smoke_gates_activation(yaml_path) is None


# ---------------------------------------------------------------------------
# AC 4: Notice is suppressible via quiet=True
# ---------------------------------------------------------------------------


def test_quiet_suppresses_notice_when_would_fire(yaml_path: Path) -> None:
    _write(yaml_path, _TWO_WAVE_NO_SMOKE)
    assert check_smoke_gates_activation(yaml_path, quiet=True) is None


def test_quiet_is_noop_when_single_wave(yaml_path: Path) -> None:
    _write(yaml_path, _ONE_WAVE_NO_SMOKE)
    assert check_smoke_gates_activation(yaml_path, quiet=True) is None


# ---------------------------------------------------------------------------
# Defensive: helper must never surface a traceback
# ---------------------------------------------------------------------------


def test_returns_none_when_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.yaml"
    assert check_smoke_gates_activation(missing) is None


def test_returns_none_when_yaml_is_malformed(yaml_path: Path) -> None:
    _write(yaml_path, ":\n  - [this is not: valid yaml\n")
    assert check_smoke_gates_activation(yaml_path) is None


def test_returns_none_when_yaml_root_is_not_mapping(yaml_path: Path) -> None:
    _write(yaml_path, "- just\n- a\n- list\n")
    assert check_smoke_gates_activation(yaml_path) is None


def test_returns_none_when_orchestration_missing(yaml_path: Path) -> None:
    _write(
        yaml_path,
        "id: FEAT-T\nname: No orchestration block\n",
    )
    assert check_smoke_gates_activation(yaml_path) is None


def test_returns_none_when_parallel_groups_missing(yaml_path: Path) -> None:
    _write(
        yaml_path,
        "id: FEAT-T\nname: Orchestration without parallel_groups\n"
        "orchestration:\n  recommended_parallel: 2\n",
    )
    assert check_smoke_gates_activation(yaml_path) is None


def test_returns_none_when_parallel_groups_not_a_list(yaml_path: Path) -> None:
    _write(
        yaml_path,
        "id: FEAT-T\nname: Malformed parallel_groups\n"
        "orchestration:\n  parallel_groups: not-a-list\n",
    )
    assert check_smoke_gates_activation(yaml_path) is None


# ---------------------------------------------------------------------------
# AC-4 (TASK-FIX-B5BF): The example block in the nudge MUST round-trip
# through SmokeGates.model_validate cleanly. Pins the example string to the
# Pydantic schema so this class of drift cannot recur.
# ---------------------------------------------------------------------------


def test_notice_example_validates_against_smoke_gates_schema(
    yaml_path: Path,
) -> None:
    """The "Minimal example" block emitted by the nudge must parse as YAML
    and validate against the canonical ``SmokeGates`` model.

    Regression for TASK-FIX-B5BF: previously the example used an
    ``after_wave_N`` dict-of-waves shape with ``- command`` lists, which
    raised ``SchemaValidationError`` against ``SmokeGates`` (which has
    ``extra="forbid"`` plus required ``after_wave``/``command`` fields).
    Authors who copied the example verbatim hit ``FeatureLoader._parse_feature``
    failures before ``/feature-build`` ever started.
    """
    import yaml as yaml_module

    from guardkit.orchestrator.feature_loader import SmokeGates

    _write(yaml_path, _TWO_WAVE_NO_SMOKE)
    notice = check_smoke_gates_activation(yaml_path)
    assert notice is not None

    # Slice between the "Minimal example:" line and the "See ..." pointer.
    lines = notice.splitlines()
    start = next(
        (i + 1 for i, line in enumerate(lines) if "Minimal example:" in line),
        None,
    )
    assert start is not None, "Notice missing 'Minimal example:' anchor"

    end = next(
        (
            i
            for i, line in enumerate(lines[start:], start=start)
            if line.lstrip().startswith("See ")
        ),
        None,
    )
    assert end is not None, "Notice missing 'See ...' anchor after example"

    raw_block = lines[start:end]
    # The notice indents the example by 4 spaces for visual alignment;
    # strip that prefix so YAML sees a top-level mapping.
    dedented = "\n".join(
        line[4:] if line.startswith("    ") else line for line in raw_block
    )

    parsed = yaml_module.safe_load(dedented)
    assert isinstance(parsed, dict), "Example must parse as a YAML mapping"
    assert "smoke_gates" in parsed, "Example must contain a smoke_gates key"

    # Load-bearing check: the SmokeGates model has extra="forbid" and
    # requires after_wave + command. If this raises, the nudge is once
    # again handing users a config that fails AutoBuild validation.
    SmokeGates.model_validate(parsed["smoke_gates"])


# ---------------------------------------------------------------------------
# TASK-FPSG-003 (L3c): discover_test_roots helper
# ---------------------------------------------------------------------------


class TestDiscoverTestRoots:
    """Cover the four branches of ``discover_test_roots``."""

    def test_returns_empty_when_no_tests_dir(self, tmp_path: Path) -> None:
        assert discover_test_roots(tmp_path) == []

    def test_returns_empty_when_tests_dir_is_a_file(self, tmp_path: Path) -> None:
        # tests/ exists but is a file, not a directory.
        (tmp_path / "tests").write_text("not a directory")
        assert discover_test_roots(tmp_path) == []

    def test_returns_empty_when_tests_dir_has_no_subdirs(
        self, tmp_path: Path,
    ) -> None:
        (tmp_path / "tests").mkdir()
        # Loose files at the top of tests/ are not test roots.
        (tmp_path / "tests" / "conftest.py").write_text("# noqa")
        assert discover_test_roots(tmp_path) == []

    def test_returns_sorted_tests_prefixed_paths(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        for name in ("unit", "forge", "integration"):
            (tests_dir / name).mkdir()

        result = discover_test_roots(tmp_path)

        assert result == ["tests/forge", "tests/integration", "tests/unit"]

    def test_skips_cache_and_hidden_directories(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        for name in (
            "unit",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".hidden",
            "integration",
        ):
            (tests_dir / name).mkdir()

        result = discover_test_roots(tmp_path)

        assert result == ["tests/integration", "tests/unit"]

    def test_skips_loose_files_alongside_subdirs(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "unit").mkdir()
        (tests_dir / "conftest.py").write_text("# noqa")

        assert discover_test_roots(tmp_path) == ["tests/unit"]


# ---------------------------------------------------------------------------
# TASK-FPSG-003 (L3c): banner uses discovered roots when repo_root supplied
# ---------------------------------------------------------------------------


class TestBannerGroundedInRepo:
    """The notice surfaces real ``tests/`` subdirs when repo_root is passed."""

    def test_banner_lists_discovered_roots_when_present(
        self, tmp_path: Path,
    ) -> None:
        # Build a target repo with two test roots.
        repo_root = tmp_path / "target_repo"
        (repo_root / "tests" / "forge").mkdir(parents=True)
        (repo_root / "tests" / "unit").mkdir(parents=True)

        # And a feature YAML that triggers the nudge.
        yaml_path = tmp_path / "FEAT-T.yaml"
        _write(yaml_path, _TWO_WAVE_NO_SMOKE)

        notice = check_smoke_gates_activation(yaml_path, repo_root=repo_root)

        assert notice is not None
        assert "Available test roots in this repo" in notice
        assert "tests/forge" in notice
        assert "tests/unit" in notice
        # Example pytest command should use the discovered roots, not the
        # generic placeholder.
        assert "pytest tests/forge tests/unit -x" in notice
        assert "tests/smoke" not in notice

    def test_banner_falls_back_to_generic_when_no_tests_dir(
        self, tmp_path: Path,
    ) -> None:
        # Target repo has no tests/ tree at all.
        repo_root = tmp_path / "target_repo"
        repo_root.mkdir()

        yaml_path = tmp_path / "FEAT-T.yaml"
        _write(yaml_path, _TWO_WAVE_NO_SMOKE)

        notice = check_smoke_gates_activation(yaml_path, repo_root=repo_root)

        assert notice is not None
        assert "Available test roots in this repo" not in notice
        assert "no `tests/` directory discovered" in notice
        # Falls back to the historical generic placeholder.
        assert "pytest tests/smoke -x" in notice

    def test_banner_falls_back_to_generic_when_repo_root_omitted(
        self, yaml_path: Path,
    ) -> None:
        # No repo_root → no discovery → generic placeholder, no roots block.
        _write(yaml_path, _TWO_WAVE_NO_SMOKE)

        notice = check_smoke_gates_activation(yaml_path)

        assert notice is not None
        assert "Available test roots in this repo" not in notice
        assert "pytest tests/smoke -x" in notice

    def test_banner_truncates_when_more_than_twelve_roots(
        self, tmp_path: Path,
    ) -> None:
        repo_root = tmp_path / "target_repo"
        tests_dir = repo_root / "tests"
        tests_dir.mkdir(parents=True)
        # Create 15 test roots; the banner should cap at 12 and surface the
        # remainder via a "… (3 more)" line.
        for i in range(15):
            (tests_dir / f"suite_{i:02d}").mkdir()

        yaml_path = tmp_path / "FEAT-T.yaml"
        _write(yaml_path, _TWO_WAVE_NO_SMOKE)

        notice = check_smoke_gates_activation(yaml_path, repo_root=repo_root)

        assert notice is not None
        assert "tests/suite_00" in notice
        assert "tests/suite_11" in notice
        # 12, 13, 14 are over the cap.
        assert "tests/suite_14" not in notice
        assert "… (3 more)" in notice

    def test_grounded_banner_still_validates_against_smoke_gates_schema(
        self, tmp_path: Path,
    ) -> None:
        """The grounded example block must round-trip through the
        ``SmokeGates`` Pydantic model — same load-bearing check as the
        legacy ``test_notice_example_validates_against_smoke_gates_schema``,
        but exercised against the discovery-grounded variant.
        """
        import yaml as yaml_module

        from guardkit.orchestrator.feature_loader import SmokeGates

        repo_root = tmp_path / "target_repo"
        (repo_root / "tests" / "forge").mkdir(parents=True)
        (repo_root / "tests" / "unit").mkdir(parents=True)

        yaml_path = tmp_path / "FEAT-T.yaml"
        _write(yaml_path, _TWO_WAVE_NO_SMOKE)

        notice = check_smoke_gates_activation(yaml_path, repo_root=repo_root)
        assert notice is not None

        lines = notice.splitlines()
        start = next(
            (i + 1 for i, line in enumerate(lines) if "Minimal example:" in line),
            None,
        )
        assert start is not None
        end = next(
            (
                i
                for i, line in enumerate(lines[start:], start=start)
                if line.lstrip().startswith("See ")
            ),
            None,
        )
        assert end is not None

        raw_block = lines[start:end]
        dedented = "\n".join(
            line[4:] if line.startswith("    ") else line for line in raw_block
        )

        parsed = yaml_module.safe_load(dedented)
        assert isinstance(parsed, dict)
        assert "smoke_gates" in parsed

        SmokeGates.model_validate(parsed["smoke_gates"])
