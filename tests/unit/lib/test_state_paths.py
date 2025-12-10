"""
Unit tests for state_paths module.

TASK-FIX-STATE02: Test centralized state file path management
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "installer/core/lib"))

from state_paths import (
    get_state_dir,
    get_state_file,
    get_phase_request_file,
    get_phase_response_file,
    AGENT_ENHANCE_STATE,
    TEMPLATE_CREATE_STATE,
    TEMPLATE_CONFIG,
    TEMPLATE_SESSION,
    TEMPLATE_PARTIAL_SESSION,
)


class TestStatePaths:
    """Test state path helper functions."""

    def test_get_state_dir_creates_directory(self, tmp_path, monkeypatch):
        """Test that get_state_dir creates the directory if it doesn't exist."""
        # Mock home directory
        mock_home = tmp_path / "test_home"
        mock_home.mkdir()
        monkeypatch.setenv("HOME", str(mock_home))

        # Ensure state dir doesn't exist yet
        state_dir = mock_home / ".agentecflow" / "state"
        assert not state_dir.exists()

        # Call get_state_dir - should create directory
        result = get_state_dir()

        assert result.exists()
        assert result.is_dir()
        assert str(result).endswith(".agentecflow/state")

    def test_get_state_dir_returns_existing_directory(self, tmp_path, monkeypatch):
        """Test that get_state_dir returns existing directory."""
        # Mock home directory with existing state dir
        mock_home = tmp_path / "test_home"
        state_dir = mock_home / ".agentecflow" / "state"
        state_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(mock_home))

        # Call get_state_dir
        result = get_state_dir()

        assert result.exists()
        assert result == state_dir

    def test_get_state_file_returns_absolute_path(self, tmp_path, monkeypatch):
        """Test that get_state_file returns absolute path to state file."""
        # Mock home directory
        mock_home = tmp_path / "test_home"
        mock_home.mkdir()
        monkeypatch.setenv("HOME", str(mock_home))

        # Call get_state_file
        result = get_state_file(".test-state.json")

        assert result.is_absolute()
        assert result.name == ".test-state.json"
        assert str(result).endswith(".agentecflow/state/.test-state.json")

    def test_get_state_file_with_constant(self, tmp_path, monkeypatch):
        """Test that get_state_file works with module constants."""
        # Mock home directory
        mock_home = tmp_path / "test_home"
        mock_home.mkdir()
        monkeypatch.setenv("HOME", str(mock_home))

        # Call get_state_file with constant
        result = get_state_file(AGENT_ENHANCE_STATE)

        assert result.name == AGENT_ENHANCE_STATE
        assert str(result).endswith(f".agentecflow/state/{AGENT_ENHANCE_STATE}")

    def test_get_phase_request_file(self, tmp_path, monkeypatch):
        """Test that get_phase_request_file returns correct path."""
        # Mock home directory
        mock_home = tmp_path / "test_home"
        mock_home.mkdir()
        monkeypatch.setenv("HOME", str(mock_home))

        # Call get_phase_request_file
        result = get_phase_request_file(6)

        assert result.is_absolute()
        assert result.name == ".agent-request-phase6.json"
        assert str(result).endswith(".agentecflow/state/.agent-request-phase6.json")

    def test_get_phase_response_file(self, tmp_path, monkeypatch):
        """Test that get_phase_response_file returns correct path."""
        # Mock home directory
        mock_home = tmp_path / "test_home"
        mock_home.mkdir()
        monkeypatch.setenv("HOME", str(mock_home))

        # Call get_phase_response_file
        result = get_phase_response_file(8)

        assert result.is_absolute()
        assert result.name == ".agent-response-phase8.json"
        assert str(result).endswith(".agentecflow/state/.agent-response-phase8.json")

    def test_constants_are_strings(self):
        """Test that all constants are strings."""
        assert isinstance(AGENT_ENHANCE_STATE, str)
        assert isinstance(TEMPLATE_CREATE_STATE, str)
        assert isinstance(TEMPLATE_CONFIG, str)
        assert isinstance(TEMPLATE_SESSION, str)
        assert isinstance(TEMPLATE_PARTIAL_SESSION, str)

    def test_constants_have_leading_dot(self):
        """Test that state file constants start with dot (hidden files)."""
        assert AGENT_ENHANCE_STATE.startswith(".")
        assert TEMPLATE_CREATE_STATE.startswith(".")
        assert TEMPLATE_CONFIG.startswith(".")
        assert TEMPLATE_SESSION.startswith(".")
        assert TEMPLATE_PARTIAL_SESSION.startswith(".")

    def test_all_phase_numbers(self, tmp_path, monkeypatch):
        """Test that phase request/response files work for all phases 1-8."""
        # Mock home directory
        mock_home = tmp_path / "test_home"
        mock_home.mkdir()
        monkeypatch.setenv("HOME", str(mock_home))

        # Test all phases 1-8
        for phase in range(1, 9):
            request_file = get_phase_request_file(phase)
            response_file = get_phase_response_file(phase)

            assert request_file.name == f".agent-request-phase{phase}.json"
            assert response_file.name == f".agent-response-phase{phase}.json"
