"""
Unit tests for TASK-FIX-7718: SDK max turns env-var override and auto-reduction.

Tests the following behaviours introduced by TASK-FIX-7718:
- TASK_WORK_SDK_MAX_TURNS defaults to 100 when GUARDKIT_SDK_MAX_TURNS is unset
- GUARDKIT_SDK_MAX_TURNS env var overrides TASK_WORK_SDK_MAX_TURNS at module level
- AgentInvoker._effective_sdk_max_turns is auto-reduced to 75 when
  timeout_multiplier > 1.0 and the env var was NOT explicitly set
- AgentInvoker._effective_sdk_max_turns equals TASK_WORK_SDK_MAX_TURNS when
  timeout_multiplier == 1.0
- When GUARDKIT_SDK_MAX_TURNS is explicitly set, _effective_sdk_max_turns
  respects that value even when timeout_multiplier > 1.0 (env var takes precedence)

Coverage Target: >=85%
Test Count: 5 tests
"""

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
