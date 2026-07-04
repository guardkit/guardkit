"""
Unit tests for TASK-AB-WAVECTL01 — concurrency affordances.

Covers:
- Max-parallel precedence chain: GUARDKIT_MAX_PARALLEL_TASKS env var >
  --max-parallel flag > feature-YAML orchestration.recommended_parallel >
  auto-detect (cloud unbounded, local capped 1 — both pinned).
- ``apply_feature_recommended_parallel``: the feature-YAML tier only BOUNDS
  an auto-detected value (min(yaml, auto-detect) — it may lower, never raise;
  the local TASK-VPT-001 cap of 1 can never be lifted, while a ``None``
  unlimited auto-detect takes the YAML value as-is); invalid YAML values
  (0, negative, bool, absent) are ignored.
- Single-resolution invariant: the YAML tier is applied ONCE to the shared
  ParallelConfig in ``_setup_phase``, so the display (log=False) and executor
  ``resolve_max_parallel`` call sites consume the identical decision
  (.claude/rules/display-must-derive-from-enforcement-source-not-proxy.md).
- Final-wave smoke-gate coverage: loader warns when an int/list ``after_wave``
  misses the final wave; stays silent for ``"all"``/covering configs.

Coverage Target: >=85%
"""

import logging
import re
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner
from rich.console import Console

from guardkit.cli.display import WaveProgressDisplay
from guardkit.cli.main import cli
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
    FeatureOrchestration,
    FeatureTask,
    SmokeGates,
)
from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.parallel_strategy import (
    PARALLEL_SOURCE_AUTO_DETECT,
    PARALLEL_SOURCE_ENV,
    PARALLEL_SOURCE_FEATURE_YAML,
    PARALLEL_SOURCE_FLAG,
    MaxParallelMode,
    ParallelConfig,
    apply_feature_recommended_parallel,
    bound_concurrency,
    resolve_max_parallel,
)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text for easier testing."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


# ============================================================================
# 1. CLI precedence: env > flag > (YAML applied later) > auto-detect
# ============================================================================


class TestCLIPrecedenceRecordsSource:
    """The CLI resolves env/flag/auto-detect and records the source so the
    orchestrator can apply the feature-YAML tier only when nothing was
    operator-set."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    @pytest.fixture(autouse=True)
    def _clear_env(self, monkeypatch):
        monkeypatch.delenv("GUARDKIT_MAX_PARALLEL_TASKS", raising=False)

    @staticmethod
    def _invoke(cli_runner, mock_orch_cls, args):
        mock_orch = MagicMock()
        mock_orch.orchestrate.return_value = MagicMock(success=True)
        mock_orch_cls.return_value = mock_orch
        cli_runner.invoke(cli, ["autobuild", "feature", "FEAT-TEST", *args])
        return mock_orch_cls.call_args[1]

    @patch("guardkit.cli.autobuild._require_sdk")
    @patch("guardkit.cli.autobuild.FeatureOrchestrator")
    def test_env_wins_over_flag(
        self, mock_orch_cls, mock_sdk, cli_runner, monkeypatch
    ):
        monkeypatch.setenv("GUARDKIT_MAX_PARALLEL_TASKS", "4")
        kwargs = self._invoke(cli_runner, mock_orch_cls, ["--max-parallel", "2"])

        config = kwargs["parallel_config"]
        assert kwargs["max_parallel"] == 4
        assert config.static_value == 4
        assert config.source == PARALLEL_SOURCE_ENV

    @patch("guardkit.cli.autobuild._require_sdk")
    @patch("guardkit.cli.autobuild.FeatureOrchestrator")
    def test_flag_records_flag_source(
        self, mock_orch_cls, mock_sdk, cli_runner
    ):
        kwargs = self._invoke(cli_runner, mock_orch_cls, ["--max-parallel", "3"])

        config = kwargs["parallel_config"]
        assert config.static_value == 3
        assert config.source == PARALLEL_SOURCE_FLAG

    @patch("guardkit.cli.autobuild._require_sdk")
    @patch("guardkit.cli.autobuild.FeatureOrchestrator")
    @patch(
        "guardkit.orchestrator.agent_invoker.detect_timeout_multiplier",
        return_value=1.0,
    )
    def test_nothing_set_cloud_stays_unbounded(
        self, mock_detect, mock_orch_cls, mock_sdk, cli_runner
    ):
        """Auto-detect unchanged: remote/cloud backend resolves to None."""
        kwargs = self._invoke(cli_runner, mock_orch_cls, [])

        config = kwargs["parallel_config"]
        assert config.static_value is None
        assert config.source == PARALLEL_SOURCE_AUTO_DETECT

    @patch("guardkit.cli.autobuild._require_sdk")
    @patch("guardkit.cli.autobuild.FeatureOrchestrator")
    @patch(
        "guardkit.orchestrator.agent_invoker.detect_timeout_multiplier",
        return_value=4.0,
    )
    def test_nothing_set_local_stays_capped_at_1(
        self, mock_detect, mock_orch_cls, mock_sdk, cli_runner
    ):
        """Auto-detect unchanged: local backend keeps the TASK-VPT-001 cap."""
        kwargs = self._invoke(cli_runner, mock_orch_cls, [])

        config = kwargs["parallel_config"]
        assert config.static_value == 1
        assert config.source == PARALLEL_SOURCE_AUTO_DETECT

    @patch("guardkit.cli.autobuild._require_sdk")
    @patch("guardkit.cli.autobuild.FeatureOrchestrator")
    def test_dynamic_strategy_carries_source(
        self, mock_orch_cls, mock_sdk, cli_runner
    ):
        kwargs = self._invoke(
            cli_runner,
            mock_orch_cls,
            ["--max-parallel", "2", "--max-parallel-strategy", "dynamic"],
        )

        config = kwargs["parallel_config"]
        assert config.mode == MaxParallelMode.DYNAMIC
        assert config.static_value == 2
        assert config.source == PARALLEL_SOURCE_FLAG


# ============================================================================
# 2. apply_feature_recommended_parallel — the feature-YAML tier
# ============================================================================


class TestApplyFeatureRecommendedParallel:
    """The YAML tier only BOUNDS an auto-detected value — min(yaml,
    auto-detect): it may lower concurrency, never raise it. env/flag always
    win; invalid YAML values are ignored (absent signal, no effect)."""

    def test_env_source_is_never_overridden(self):
        config = ParallelConfig(
            mode=MaxParallelMode.STATIC, static_value=4, source=PARALLEL_SOURCE_ENV
        )
        result = apply_feature_recommended_parallel(config, 1)
        assert result is config
        assert result.static_value == 4

    def test_flag_source_is_never_overridden(self):
        config = ParallelConfig(
            mode=MaxParallelMode.STATIC, static_value=3, source=PARALLEL_SOURCE_FLAG
        )
        result = apply_feature_recommended_parallel(config, 1)
        assert result is config
        assert result.static_value == 3

    def test_auto_detect_none_takes_yaml_value(self):
        """Cloud auto-detect (unbounded) + YAML recommended_parallel=1 → 1.
        A ``None`` auto-detect is unlimited, so the YAML applies as-is —
        the retro-motivating use (bounding the unlimited cloud default)."""
        config = ParallelConfig.from_legacy(None)
        result = apply_feature_recommended_parallel(config, 1)
        assert result.static_value == 1
        assert result.source == PARALLEL_SOURCE_FEATURE_YAML

    def test_auto_detect_none_bounded_by_yaml_2(self):
        """Cloud auto-detect (unbounded) + YAML recommended_parallel=2 → 2."""
        config = ParallelConfig.from_legacy(None)
        result = apply_feature_recommended_parallel(config, 2)
        assert result.static_value == 2
        assert result.source == PARALLEL_SOURCE_FEATURE_YAML

    def test_auto_detect_local_cap_is_never_raised(self):
        """The local auto-detect cap of 1 (TASK-VPT-001 KV-cache safety) is
        NOT raised by a higher YAML value — generate_feature_yaml has always
        emitted recommended_parallel as a machine default (min(max wave
        size, 4)), so ~20 existing YAMLs carry 2-5 as previously-inert
        metadata that must not resurrect parallel contention. The value is
        unchanged, so the source stays auto-detect."""
        config = ParallelConfig(
            mode=MaxParallelMode.STATIC,
            static_value=1,
            source=PARALLEL_SOURCE_AUTO_DETECT,
        )
        result = apply_feature_recommended_parallel(config, 2)
        assert result is config
        assert result.static_value == 1
        assert result.source == PARALLEL_SOURCE_AUTO_DETECT

    def test_yaml_lower_than_finite_auto_detect_bounds_it(self):
        """min(yaml, auto-detect): a YAML value below a finite auto-detect
        result lowers it and stamps the feature-yaml source."""
        config = ParallelConfig(
            mode=MaxParallelMode.STATIC,
            static_value=4,
            source=PARALLEL_SOURCE_AUTO_DETECT,
        )
        result = apply_feature_recommended_parallel(config, 2)
        assert result.static_value == 2
        assert result.source == PARALLEL_SOURCE_FEATURE_YAML

    def test_yaml_equal_to_auto_detect_keeps_auto_detect_source(self):
        """An equal YAML value changes nothing — the feature-yaml source is
        stamped ONLY when the YAML actually changed the value."""
        config = ParallelConfig(
            mode=MaxParallelMode.STATIC,
            static_value=1,
            source=PARALLEL_SOURCE_AUTO_DETECT,
        )
        result = apply_feature_recommended_parallel(config, 1)
        assert result is config
        assert result.static_value == 1
        assert result.source == PARALLEL_SOURCE_AUTO_DETECT

    def test_original_config_is_not_mutated(self):
        config = ParallelConfig.from_legacy(None)
        apply_feature_recommended_parallel(config, 2)
        assert config.static_value is None
        assert config.source == PARALLEL_SOURCE_AUTO_DETECT

    @pytest.mark.parametrize("invalid", [None, 0, -1, -5, True, False, "2", 2.0])
    def test_invalid_yaml_values_are_ignored(self, invalid):
        """Absent/invalid YAML tier falls through to auto-detect unchanged."""
        config = ParallelConfig.from_legacy(None)
        result = apply_feature_recommended_parallel(config, invalid)
        assert result is config
        assert result.static_value is None
        assert result.source == PARALLEL_SOURCE_AUTO_DETECT

    def test_from_legacy_int_is_operator_set(self):
        """Programmatic legacy callers passing an int keep their value."""
        config = ParallelConfig.from_legacy(2)
        assert config.source == PARALLEL_SOURCE_FLAG
        result = apply_feature_recommended_parallel(config, 1)
        assert result.static_value == 2


# ============================================================================
# 3. Single-resolution invariant: _setup_phase applies the tier ONCE
# ============================================================================


def _write_feature_repo(
    repo_root: Path,
    feature_id: str = "FEAT-WCTL",
    recommended_parallel=1,
    include_recommended: bool = True,
) -> None:
    """Write a minimal two-task/one-wave feature repo for _setup_phase."""
    features_dir = repo_root / ".guardkit" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)

    orchestration = {
        "parallel_groups": [["TASK-W-001", "TASK-W-002"]],
        "estimated_duration_minutes": 60,
    }
    if include_recommended:
        orchestration["recommended_parallel"] = recommended_parallel

    data = {
        "id": feature_id,
        "name": "Wave control test feature",
        "description": "TASK-AB-WAVECTL01 fixture",
        "created": "2026-07-04T00:00:00Z",
        "status": "planned",
        "complexity": 3,
        "estimated_tasks": 2,
        "tasks": [
            {
                "id": "TASK-W-001",
                "name": "First",
                "file_path": "tasks/backlog/TASK-W-001.md",
                "complexity": 2,
                "dependencies": [],
                "status": "pending",
                "implementation_mode": "task-work",
                "estimated_minutes": 30,
            },
            {
                "id": "TASK-W-002",
                "name": "Second",
                "file_path": "tasks/backlog/TASK-W-002.md",
                "complexity": 2,
                "dependencies": [],
                "status": "pending",
                "implementation_mode": "task-work",
                "estimated_minutes": 30,
            },
        ],
        "orchestration": orchestration,
    }
    with open(features_dir / f"{feature_id}.yaml", "w") as f:
        yaml.dump(data, f, sort_keys=False)

    for task_id in ("TASK-W-001", "TASK-W-002"):
        task_file = repo_root / "tasks" / "backlog" / f"{task_id}.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            f"---\nid: {task_id}\ntitle: {task_id}\nstatus: pending\n"
            f"task_type: feature\ncomplexity: 2\n---\n\n# {task_id}\n"
        )


@pytest.fixture
def mock_worktree_manager(tmp_path):
    """MagicMock manager returning a real-shaped worktree object."""
    from guardkit.worktrees import Worktree

    worktree_path = tmp_path / ".guardkit" / "worktrees" / "FEAT-WCTL"
    worktree_path.mkdir(parents=True, exist_ok=True)
    worktree = Worktree(
        task_id="FEAT-WCTL",
        branch_name="autobuild/FEAT-WCTL",
        path=worktree_path,
        base_branch="main",
    )
    manager = MagicMock()
    manager.create.return_value = worktree
    manager.worktrees_dir = worktree_path.parent
    return manager


class TestSetupPhaseAppliesYamlTier:
    """_setup_phase applies the feature-YAML tier once to the shared config,
    so both resolve_max_parallel call sites consume one decision."""

    @patch(
        "guardkit.orchestrator.agent_invoker.detect_timeout_multiplier",
        return_value=1.0,
    )
    def test_yaml_recommended_parallel_1_bounds_executor_and_display(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        """Only YAML recommended_parallel=1 set → executor bound is 1 AND the
        wave banner shows serial — both derived from the SAME decision."""
        _write_feature_repo(tmp_path, recommended_parallel=1)

        orch = FeatureOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            quiet=True,
            skip_validation=True,
        )
        # Nothing operator-set: cloud auto-detect leaves None/auto-detect.
        assert orch._parallel_config.static_value is None
        assert orch._parallel_config.source == PARALLEL_SOURCE_AUTO_DETECT

        orch._setup_phase("FEAT-WCTL", "main")

        # The tier was applied once, to the shared config.
        assert orch._parallel_config.static_value == 1
        assert orch._parallel_config.source == PARALLEL_SOURCE_FEATURE_YAML

        # Both call sites resolve the identical decision from that config.
        display_value = resolve_max_parallel(
            orch._parallel_config, wave_number=1, wave_size=2, log=False
        )
        executor_value = resolve_max_parallel(
            orch._parallel_config, wave_number=1, wave_size=2
        )
        assert display_value == executor_value == 1

        # Executor side: bound_concurrency wraps (serialises) the wave.
        async def _noop():
            return None

        coros = [_noop(), _noop()]
        bounded = bound_concurrency(coros, executor_value)
        assert bounded != coros  # wrapped, not returned unchanged
        for c in coros:
            c.close()

        # Display side: the banner renders serial for a 2-task wave.
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        display = WaveProgressDisplay(total_waves=1, console=console)
        display.start_wave(1, ["TASK-W-001", "TASK-W-002"], max_parallel=display_value)
        assert "(parallel: 1)" in strip_ansi(output.getvalue())

    @patch(
        "guardkit.orchestrator.agent_invoker.detect_timeout_multiplier",
        return_value=1.0,
    )
    def test_operator_set_value_wins_over_yaml(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        """env/flag (operator-set) config passes through _setup_phase intact
        even when the YAML recommends something else."""
        _write_feature_repo(tmp_path, recommended_parallel=1)

        orch = FeatureOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            quiet=True,
            skip_validation=True,
            parallel_config=ParallelConfig(
                mode=MaxParallelMode.STATIC,
                static_value=3,
                source=PARALLEL_SOURCE_FLAG,
            ),
        )

        orch._setup_phase("FEAT-WCTL", "main")

        assert orch._parallel_config.static_value == 3
        assert orch._parallel_config.source == PARALLEL_SOURCE_FLAG

    @patch(
        "guardkit.orchestrator.agent_invoker.detect_timeout_multiplier",
        return_value=4.0,
    )
    def test_local_backend_cap_survives_machine_default_yaml(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        """The live-defect scenario: a local-backend run (auto-detect capped
        at 1, TASK-VPT-001) with no env/flag and a machine-default YAML
        recommended_parallel=3 must stay serial — the YAML tier may only
        lower concurrency, never raise it."""
        _write_feature_repo(tmp_path, recommended_parallel=3)

        orch = FeatureOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            quiet=True,
            skip_validation=True,
            parallel_config=ParallelConfig(
                mode=MaxParallelMode.STATIC,
                static_value=1,
                source=PARALLEL_SOURCE_AUTO_DETECT,
            ),
        )

        orch._setup_phase("FEAT-WCTL", "main")

        assert orch._parallel_config.static_value == 1
        assert orch._parallel_config.source == PARALLEL_SOURCE_AUTO_DETECT
        executor_value = resolve_max_parallel(
            orch._parallel_config, wave_number=1, wave_size=2, log=False
        )
        assert executor_value == 1

    @patch(
        "guardkit.orchestrator.agent_invoker.detect_timeout_multiplier",
        return_value=1.0,
    )
    def test_yaml_absent_leaves_auto_detect_unchanged(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        """No env, no flag, no YAML recommended_parallel → auto-detect result
        (cloud unbounded here) is untouched."""
        _write_feature_repo(tmp_path, include_recommended=False)

        orch = FeatureOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            quiet=True,
            skip_validation=True,
        )

        orch._setup_phase("FEAT-WCTL", "main")

        assert orch._parallel_config.static_value is None
        assert orch._parallel_config.source == PARALLEL_SOURCE_AUTO_DETECT

    @pytest.mark.parametrize("invalid", [0, -2])
    @patch(
        "guardkit.orchestrator.agent_invoker.detect_timeout_multiplier",
        return_value=1.0,
    )
    def test_yaml_invalid_values_are_ignored(
        self, mock_detect, tmp_path, mock_worktree_manager, invalid
    ):
        """recommended_parallel < 1 in the YAML is ignored — auto-detect
        result stands."""
        _write_feature_repo(tmp_path, recommended_parallel=invalid)

        orch = FeatureOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            quiet=True,
            skip_validation=True,
        )

        orch._setup_phase("FEAT-WCTL", "main")

        assert orch._parallel_config.static_value is None
        assert orch._parallel_config.source == PARALLEL_SOURCE_AUTO_DETECT

    def test_authoritative_log_names_the_source(self, caplog):
        """The executor-side resolution (log=True) logs the chosen source;
        the display resolution (log=False) stays silent."""
        config = ParallelConfig(
            mode=MaxParallelMode.STATIC,
            static_value=1,
            source=PARALLEL_SOURCE_FEATURE_YAML,
        )
        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.parallel_strategy"
        ):
            resolve_max_parallel(config, wave_number=1, wave_size=2, log=False)
            assert "source" not in caplog.text
            resolve_max_parallel(config, wave_number=1, wave_size=2)
        assert "max_parallel=1 (static) [source: feature-yaml]" in caplog.text


# ============================================================================
# 4. Loader unset-default: absence must survive save/load
# ============================================================================


class TestRecommendedParallelAbsenceSurvives:
    """Unset recommended_parallel stays None (never coerced to an int), so a
    save/load round-trip cannot manufacture an operator intent that was
    never expressed."""

    def test_unset_recommended_parallel_defaults_to_none(self):
        orch = FeatureOrchestration(parallel_groups=[["TASK-A"]])
        assert orch.recommended_parallel is None

    def test_unset_survives_save_load_round_trip(self, tmp_path):
        _write_feature_repo(tmp_path, include_recommended=False)
        feature = FeatureLoader.load_feature("FEAT-WCTL", repo_root=tmp_path)
        assert feature.orchestration.recommended_parallel is None

        FeatureLoader.save_feature(feature, repo_root=tmp_path)
        reloaded = FeatureLoader.load_feature("FEAT-WCTL", repo_root=tmp_path)
        assert reloaded.orchestration.recommended_parallel is None

    def test_explicit_value_survives_round_trip(self, tmp_path):
        _write_feature_repo(tmp_path, recommended_parallel=2)
        feature = FeatureLoader.load_feature("FEAT-WCTL", repo_root=tmp_path)
        assert feature.orchestration.recommended_parallel == 2


# ============================================================================
# 5. Final-wave smoke-gate coverage warning (loader, warn-only)
# ============================================================================


def _feature_with_gate(after_wave, n_waves=3, smoke_gates=True) -> Feature:
    tasks = [
        FeatureTask(
            id=f"TASK-G-{i:03d}",
            name=f"Task {i}",
            file_path=Path(f"tasks/backlog/TASK-G-{i:03d}.md"),
        )
        for i in range(1, n_waves + 1)
    ]
    return Feature(
        id="FEAT-GATE",
        name="Gate coverage feature",
        tasks=tasks,
        orchestration=FeatureOrchestration(
            parallel_groups=[[t.id] for t in tasks],
        ),
        smoke_gates=(
            SmokeGates(after_wave=after_wave, command="pytest tests/ -q")
            if smoke_gates
            else None
        ),
    )


class TestSmokeGateFinalWaveCoverage:
    """AC-004: warn (never error) when after_wave misses the final wave."""

    def test_list_missing_final_wave_warns(self):
        feature = _feature_with_gate([1, 2], n_waves=3)
        msg = FeatureLoader.check_smoke_gate_final_wave_coverage(feature)
        assert msg is not None
        assert "wave 3" in msg
        assert 'after_wave: "all"' in msg

    def test_int_missing_final_wave_warns(self):
        feature = _feature_with_gate(1, n_waves=2)
        msg = FeatureLoader.check_smoke_gate_final_wave_coverage(feature)
        assert msg is not None
        assert "wave 2" in msg

    def test_all_is_silent(self):
        feature = _feature_with_gate("all", n_waves=3)
        assert FeatureLoader.check_smoke_gate_final_wave_coverage(feature) is None

    def test_covering_list_is_silent(self):
        feature = _feature_with_gate([2, 3], n_waves=3)
        assert FeatureLoader.check_smoke_gate_final_wave_coverage(feature) is None

    def test_int_equal_to_final_wave_is_silent(self):
        feature = _feature_with_gate(2, n_waves=2)
        assert FeatureLoader.check_smoke_gate_final_wave_coverage(feature) is None

    def test_no_smoke_gates_is_silent(self):
        feature = _feature_with_gate(1, n_waves=2, smoke_gates=False)
        assert FeatureLoader.check_smoke_gate_final_wave_coverage(feature) is None

    def test_empty_parallel_groups_is_silent(self):
        """No wave layout → absent signal: neither warn nor block."""
        feature = Feature(
            id="FEAT-GATE",
            name="No waves",
            tasks=[],
            orchestration=FeatureOrchestration(parallel_groups=[]),
            smoke_gates=SmokeGates(after_wave=1, command="pytest tests/ -q"),
        )
        assert FeatureLoader.check_smoke_gate_final_wave_coverage(feature) is None

    def test_load_feature_emits_warning_via_logger(self, tmp_path, caplog):
        """load_feature logs the coverage gap as a WARNING, not an error."""
        _write_feature_repo(tmp_path)
        # Rewrite the YAML with a two-wave layout and a gate that misses
        # wave 2. (smoke_gates command paths must exist for the L4
        # pre-flight — point it at an existing dir.)
        (tmp_path / "tests").mkdir(exist_ok=True)
        feature_file = tmp_path / ".guardkit" / "features" / "FEAT-WCTL.yaml"
        data = yaml.safe_load(feature_file.read_text())
        data["orchestration"]["parallel_groups"] = [
            ["TASK-W-001"],
            ["TASK-W-002"],
        ]
        data["smoke_gates"] = {
            "after_wave": 1,
            "command": "pytest tests/ -q",
        }
        feature_file.write_text(yaml.dump(data, sort_keys=False))

        with caplog.at_level(
            logging.WARNING, logger="guardkit.orchestrator.feature_loader"
        ):
            feature = FeatureLoader.load_feature("FEAT-WCTL", repo_root=tmp_path)

        assert feature.smoke_gates is not None
        assert "does not cover the final wave" in caplog.text
        assert "wave 2" in caplog.text

    def test_load_feature_silent_for_all(self, tmp_path, caplog):
        _write_feature_repo(tmp_path)
        (tmp_path / "tests").mkdir(exist_ok=True)
        feature_file = tmp_path / ".guardkit" / "features" / "FEAT-WCTL.yaml"
        data = yaml.safe_load(feature_file.read_text())
        data["smoke_gates"] = {
            "after_wave": "all",
            "command": "pytest tests/ -q",
        }
        feature_file.write_text(yaml.dump(data, sort_keys=False))

        with caplog.at_level(
            logging.WARNING, logger="guardkit.orchestrator.feature_loader"
        ):
            FeatureLoader.load_feature("FEAT-WCTL", repo_root=tmp_path)

        assert "does not cover the final wave" not in caplog.text
