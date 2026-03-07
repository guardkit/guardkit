"""Tests for TASK-FIX-VL05: timeout scaling for local backends.

Verifies:
- detect_timeout_multiplier() auto-detection from ANTHROPIC_BASE_URL
- GUARDKIT_TIMEOUT_MULTIPLIER env var override
- AgentInvoker applies multiplier to SDK timeout calculations
- FeatureOrchestrator scales task_timeout by multiplier
- Default behaviour unchanged (multiplier=1.0) for Anthropic API
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import (
    DEFAULT_SDK_TIMEOUT,
    MAX_SDK_TIMEOUT,
    AgentInvoker,
    detect_timeout_multiplier,
)


# ============================================================================
# detect_timeout_multiplier() tests
# ============================================================================


class TestDetectTimeoutMultiplier:
    """Tests for auto-detection of timeout multiplier from environment."""

    def test_default_returns_1(self, monkeypatch):
        """No ANTHROPIC_BASE_URL set → multiplier=1.0."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        assert detect_timeout_multiplier() == 1.0

    def test_anthropic_api_returns_1(self, monkeypatch):
        """ANTHROPIC_BASE_URL=https://api.anthropic.com → multiplier=1.0."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        assert detect_timeout_multiplier() == 1.0

    def test_localhost_returns_3(self, monkeypatch):
        """ANTHROPIC_BASE_URL=http://localhost:8000 → multiplier=3.0."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:8000")
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        assert detect_timeout_multiplier() == 3.0

    def test_127_0_0_1_returns_3(self, monkeypatch):
        """ANTHROPIC_BASE_URL=http://127.0.0.1:8000 → multiplier=3.0."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:8000")
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        assert detect_timeout_multiplier() == 3.0

    def test_remote_host_returns_1(self, monkeypatch):
        """ANTHROPIC_BASE_URL=http://remote-host:8000 → multiplier=1.0."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://remote-host:8000")
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        assert detect_timeout_multiplier() == 1.0

    def test_empty_base_url_returns_1(self, monkeypatch):
        """ANTHROPIC_BASE_URL='' → multiplier=1.0."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "")
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        assert detect_timeout_multiplier() == 1.0

    def test_explicit_env_override(self, monkeypatch):
        """GUARDKIT_TIMEOUT_MULTIPLIER=2.5 overrides auto-detection."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:8000")
        monkeypatch.setenv("GUARDKIT_TIMEOUT_MULTIPLIER", "2.5")
        assert detect_timeout_multiplier() == 2.5

    def test_explicit_env_override_with_anthropic_url(self, monkeypatch):
        """GUARDKIT_TIMEOUT_MULTIPLIER overrides even for Anthropic URL."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        monkeypatch.setenv("GUARDKIT_TIMEOUT_MULTIPLIER", "3.0")
        assert detect_timeout_multiplier() == 3.0

    def test_explicit_env_min_clamped(self, monkeypatch):
        """GUARDKIT_TIMEOUT_MULTIPLIER below 0.1 is clamped to 0.1."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.setenv("GUARDKIT_TIMEOUT_MULTIPLIER", "0.01")
        assert detect_timeout_multiplier() == 0.1

    def test_explicit_env_invalid_falls_back(self, monkeypatch):
        """Invalid GUARDKIT_TIMEOUT_MULTIPLIER falls back to auto-detection."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:8000")
        monkeypatch.setenv("GUARDKIT_TIMEOUT_MULTIPLIER", "not-a-number")
        assert detect_timeout_multiplier() == 3.0  # Falls back to localhost detection


# ============================================================================
# AgentInvoker timeout multiplier tests
# ============================================================================


class TestAgentInvokerTimeoutMultiplier:
    """Tests for AgentInvoker applying timeout_multiplier."""

    @pytest.fixture
    def worktree_path(self, tmp_path):
        """Create a minimal worktree directory."""
        wt = tmp_path / "worktree"
        wt.mkdir()
        return wt

    def test_default_multiplier_auto_detected(self, worktree_path, monkeypatch):
        """AgentInvoker auto-detects multiplier when not provided."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        invoker = AgentInvoker(worktree_path=worktree_path)
        assert invoker.timeout_multiplier == 1.0

    def test_explicit_multiplier_stored(self, worktree_path, monkeypatch):
        """AgentInvoker stores explicit multiplier."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        invoker = AgentInvoker(worktree_path=worktree_path, timeout_multiplier=4.0)
        assert invoker.timeout_multiplier == 4.0

    def test_localhost_auto_detects_3x(self, worktree_path, monkeypatch):
        """AgentInvoker auto-detects 3x multiplier for localhost."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:8000")
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        invoker = AgentInvoker(worktree_path=worktree_path)
        assert invoker.timeout_multiplier == 3.0

    def test_calculate_sdk_timeout_applies_multiplier(self, worktree_path, monkeypatch):
        """_calculate_sdk_timeout applies timeout_multiplier."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)

        invoker_1x = AgentInvoker(worktree_path=worktree_path, timeout_multiplier=1.0)
        invoker_4x = AgentInvoker(worktree_path=worktree_path, timeout_multiplier=4.0)

        timeout_1x = invoker_1x._calculate_sdk_timeout("TASK-TEST")
        timeout_4x = invoker_4x._calculate_sdk_timeout("TASK-TEST")

        # 4x multiplier should produce a larger timeout
        assert timeout_4x > timeout_1x
        # With default base (1200s), mode=task-work (1.5x), complexity=5 (1.5x):
        # 1x: min(1200*1.5*1.5, 3600) = min(2700, 3600) = 2700
        # 4x: min(2700*4, 3600*4) = min(10800, 14400) = 10800
        assert timeout_4x == timeout_1x * 4

    def test_calculate_sdk_timeout_cap_scaled(self, worktree_path, monkeypatch):
        """MAX_SDK_TIMEOUT cap is also scaled by multiplier."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)

        invoker = AgentInvoker(
            worktree_path=worktree_path,
            timeout_multiplier=4.0,
            sdk_timeout_seconds=3600,  # Start at max
        )
        # With 3600 base * 1.5 mode * 1.5 complexity = 8100
        # Scaled: 8100 * 4 = 32400, but capped at 3600 * 4 = 14400
        timeout = invoker._calculate_sdk_timeout("TASK-TEST")
        assert timeout <= MAX_SDK_TIMEOUT * 4

    def test_multiplier_1_unchanged_behaviour(self, worktree_path, monkeypatch):
        """Multiplier=1.0 produces identical results to pre-VL05 behaviour."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)

        invoker = AgentInvoker(worktree_path=worktree_path, timeout_multiplier=1.0)
        timeout = invoker._calculate_sdk_timeout("TASK-TEST")

        # Should be same as before VL05: base * mode * complexity, capped
        assert timeout <= MAX_SDK_TIMEOUT
        assert timeout > 0

    def test_cli_override_ignores_multiplier(self, worktree_path, monkeypatch):
        """CLI override (sdk_timeout_seconds != DEFAULT) skips multiplier."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)

        # Use non-default timeout (CLI override)
        invoker = AgentInvoker(
            worktree_path=worktree_path,
            sdk_timeout_seconds=900,
            timeout_multiplier=4.0,
        )
        timeout = invoker._calculate_sdk_timeout("TASK-TEST")

        # CLI override should be returned unchanged
        assert timeout == 900


# ============================================================================
# FeatureOrchestrator timeout multiplier tests
# ============================================================================


class TestFeatureOrchestratorTimeoutMultiplier:
    """Tests for FeatureOrchestrator scaling task_timeout by multiplier."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a minimal repo structure."""
        (tmp_path / ".guardkit" / "features").mkdir(parents=True)
        return tmp_path

    @pytest.fixture
    def mock_worktree_manager(self):
        return MagicMock()

    def test_default_task_timeout_unchanged(self, temp_repo, mock_worktree_manager, monkeypatch):
        """Default multiplier=1.0 leaves task_timeout unchanged."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)

        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        orch = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            timeout_multiplier=1.0,
        )
        assert orch.task_timeout == 2400
        assert orch.timeout_multiplier == 1.0

    def test_4x_multiplier_scales_task_timeout(self, temp_repo, mock_worktree_manager, monkeypatch):
        """4x multiplier scales task_timeout from 2400 to 9600."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)

        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        orch = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            timeout_multiplier=4.0,
        )
        assert orch.task_timeout == 9600  # 2400 * 4
        assert orch.timeout_multiplier == 4.0

    def test_custom_task_timeout_also_scaled(self, temp_repo, mock_worktree_manager, monkeypatch):
        """Custom task_timeout is also scaled by multiplier."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)

        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        orch = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            task_timeout=1800,
            timeout_multiplier=2.0,
        )
        assert orch.task_timeout == 3600  # 1800 * 2

    def test_localhost_auto_detects_multiplier(self, temp_repo, mock_worktree_manager, monkeypatch):
        """FeatureOrchestrator auto-detects 3x multiplier for localhost."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:8000")
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)

        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        orch = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
        )
        assert orch.timeout_multiplier == 3.0
        assert orch.task_timeout == 7200  # 2400 * 3
