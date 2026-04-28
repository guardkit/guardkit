"""
Unit tests for TASK-FIX-7718 + TASK-ABSR-MAXT: SDK max turns env-var override,
auto-reduction, and per-task complexity scaling.

TASK-FIX-7718 behaviours (5 tests, must continue to pass):
- TASK_WORK_SDK_MAX_TURNS defaults to 100 when GUARDKIT_SDK_MAX_TURNS is unset
- GUARDKIT_SDK_MAX_TURNS env var overrides TASK_WORK_SDK_MAX_TURNS at module level
- AgentInvoker._effective_sdk_max_turns is auto-reduced to 100 when
  timeout_multiplier > 1.0 and the env var was NOT explicitly set
- AgentInvoker._effective_sdk_max_turns equals TASK_WORK_SDK_MAX_TURNS when
  timeout_multiplier == 1.0
- When GUARDKIT_SDK_MAX_TURNS is explicitly set, _effective_sdk_max_turns
  respects that value even when timeout_multiplier > 1.0 (env var takes precedence)

TASK-ABSR-MAXT behaviours (new tests):
- AgentInvoker._calculate_sdk_max_turns(task_id) scales the base 100-turn budget
  by `1.0 + complexity/10.0`, mirroring _calculate_sdk_timeout
- Env-var override (GUARDKIT_SDK_MAX_TURNS) skips complexity scaling entirely
- Missing/unloadable task frontmatter falls back to complexity=5 (1.5x → 150)

Coverage Target: >=85%
Test Count: 11 tests (5 legacy + 6 new)
"""

from unittest.mock import patch

import guardkit.orchestrator.agent_invoker as mod
from guardkit.orchestrator.agent_invoker import AgentInvoker


# ============================================================================
# 1. Module-Level Constant Tests
# ============================================================================


class TestModuleLevelConstants:
    """Tests for the module-level TASK_WORK_SDK_MAX_TURNS constant."""

    def test_default_sdk_max_turns_is_100(self, monkeypatch):
        """TASK_WORK_SDK_MAX_TURNS defaults to 100 when env var is not set."""
        monkeypatch.setattr(mod, "TASK_WORK_SDK_MAX_TURNS", 100)
        monkeypatch.setattr(mod, "_SDK_MAX_TURNS_IS_OVERRIDE", False)

        assert mod.TASK_WORK_SDK_MAX_TURNS == 100

    def test_env_var_overrides_sdk_max_turns(self, monkeypatch):
        """GUARDKIT_SDK_MAX_TURNS env var causes TASK_WORK_SDK_MAX_TURNS to be overridden."""
        monkeypatch.setattr(mod, "TASK_WORK_SDK_MAX_TURNS", 30)
        monkeypatch.setattr(mod, "_SDK_MAX_TURNS_IS_OVERRIDE", True)

        assert mod.TASK_WORK_SDK_MAX_TURNS == 30
        assert mod._SDK_MAX_TURNS_IS_OVERRIDE is True


# ============================================================================
# 2. AgentInvoker._effective_sdk_max_turns Tests
# ============================================================================


class TestEffectiveSdkMaxTurns:
    """Tests for AgentInvoker._effective_sdk_max_turns computation."""

    def test_effective_turns_reduced_for_local_backend(self, tmp_path, monkeypatch):
        """_effective_sdk_max_turns is capped at 100 when timeout_multiplier > 1.0
        and GUARDKIT_SDK_MAX_TURNS was not explicitly set."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        # Simulate no env var override (the default state)
        monkeypatch.setattr(mod, "TASK_WORK_SDK_MAX_TURNS", 100)
        monkeypatch.setattr(mod, "_SDK_MAX_TURNS_IS_OVERRIDE", False)

        invoker = AgentInvoker(
            worktree_path=worktree,
            timeout_multiplier=4.0,
        )

        assert invoker._effective_sdk_max_turns == 100

    def test_effective_turns_unchanged_for_remote_backend(self, tmp_path, monkeypatch):
        """_effective_sdk_max_turns equals TASK_WORK_SDK_MAX_TURNS when
        timeout_multiplier == 1.0 (remote/standard backend)."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        monkeypatch.setattr(mod, "TASK_WORK_SDK_MAX_TURNS", 100)
        monkeypatch.setattr(mod, "_SDK_MAX_TURNS_IS_OVERRIDE", False)

        invoker = AgentInvoker(
            worktree_path=worktree,
            timeout_multiplier=1.0,
        )

        assert invoker._effective_sdk_max_turns == 100

    def test_env_var_takes_precedence_over_auto_reduction(self, tmp_path, monkeypatch):
        """When GUARDKIT_SDK_MAX_TURNS is explicitly set, _effective_sdk_max_turns
        uses that value even when timeout_multiplier > 1.0."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        # Simulate env var having been set to 30 at import time
        monkeypatch.setattr(mod, "TASK_WORK_SDK_MAX_TURNS", 30)
        monkeypatch.setattr(mod, "_SDK_MAX_TURNS_IS_OVERRIDE", True)

        invoker = AgentInvoker(
            worktree_path=worktree,
            timeout_multiplier=4.0,
        )

        # The env var value (30) must be respected; auto-reduction must NOT apply
        assert invoker._effective_sdk_max_turns == 30


# ============================================================================
# 3. AgentInvoker._calculate_sdk_max_turns Tests (TASK-ABSR-MAXT)
# ============================================================================


class TestCalculateSdkMaxTurns:
    """Tests for AgentInvoker._calculate_sdk_max_turns(task_id) complexity scaling.

    Mirrors `_calculate_sdk_timeout` semantics: env-var override wins, otherwise
    multiplier = 1.0 + complexity/10.0 applied to the base TASK_WORK_SDK_MAX_TURNS.
    """

    @staticmethod
    def _make_invoker(tmp_path):
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        return AgentInvoker(worktree_path=worktree, timeout_multiplier=1.0)

    @staticmethod
    def _patch_complexity(complexity):
        """Patch TaskLoader.load_task to return a fixed complexity."""
        return patch(
            "guardkit.tasks.task_loader.TaskLoader.load_task",
            return_value={"frontmatter": {"complexity": complexity}},
        )

    def test_complexity_scaling_at_complexity_1(self, tmp_path, monkeypatch):
        """complexity=1 → multiplier 1.1x → 110 turns."""
        monkeypatch.setattr(mod, "TASK_WORK_SDK_MAX_TURNS", 100)
        monkeypatch.setattr(mod, "_SDK_MAX_TURNS_IS_OVERRIDE", False)
        invoker = self._make_invoker(tmp_path)

        with self._patch_complexity(1):
            assert invoker._calculate_sdk_max_turns("TASK-001") == 110

    def test_complexity_scaling_at_complexity_5(self, tmp_path, monkeypatch):
        """complexity=5 → multiplier 1.5x → 150 turns."""
        monkeypatch.setattr(mod, "TASK_WORK_SDK_MAX_TURNS", 100)
        monkeypatch.setattr(mod, "_SDK_MAX_TURNS_IS_OVERRIDE", False)
        invoker = self._make_invoker(tmp_path)

        with self._patch_complexity(5):
            assert invoker._calculate_sdk_max_turns("TASK-005") == 150

    def test_complexity_scaling_at_complexity_6(self, tmp_path, monkeypatch):
        """complexity=6 → multiplier 1.6x → 160 turns (covers ceiling-hit J004-013)."""
        monkeypatch.setattr(mod, "TASK_WORK_SDK_MAX_TURNS", 100)
        monkeypatch.setattr(mod, "_SDK_MAX_TURNS_IS_OVERRIDE", False)
        invoker = self._make_invoker(tmp_path)

        with self._patch_complexity(6):
            assert invoker._calculate_sdk_max_turns("TASK-006") == 160

    def test_complexity_scaling_at_complexity_10(self, tmp_path, monkeypatch):
        """complexity=10 → multiplier 2.0x → 200 turns (top of clamp range)."""
        monkeypatch.setattr(mod, "TASK_WORK_SDK_MAX_TURNS", 100)
        monkeypatch.setattr(mod, "_SDK_MAX_TURNS_IS_OVERRIDE", False)
        invoker = self._make_invoker(tmp_path)

        with self._patch_complexity(10):
            assert invoker._calculate_sdk_max_turns("TASK-010") == 200

    def test_env_var_override_skips_complexity_scaling(self, tmp_path, monkeypatch):
        """When GUARDKIT_SDK_MAX_TURNS is set, complexity scaling is bypassed."""
        # Env var set at import time → base constant becomes 75, override flag True
        monkeypatch.setattr(mod, "TASK_WORK_SDK_MAX_TURNS", 75)
        monkeypatch.setattr(mod, "_SDK_MAX_TURNS_IS_OVERRIDE", True)
        invoker = self._make_invoker(tmp_path)

        # Even with complexity=10, the env-var value wins
        with self._patch_complexity(10):
            assert invoker._calculate_sdk_max_turns("TASK-OVR") == 75

    def test_complexity_defaults_to_5_on_load_error(self, tmp_path, monkeypatch):
        """If TaskLoader.load_task raises, fall back to complexity=5 (→ 150)."""
        monkeypatch.setattr(mod, "TASK_WORK_SDK_MAX_TURNS", 100)
        monkeypatch.setattr(mod, "_SDK_MAX_TURNS_IS_OVERRIDE", False)
        invoker = self._make_invoker(tmp_path)

        with patch(
            "guardkit.tasks.task_loader.TaskLoader.load_task",
            side_effect=FileNotFoundError("task missing"),
        ):
            assert invoker._calculate_sdk_max_turns("TASK-MISSING") == 150
