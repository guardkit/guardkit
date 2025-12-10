"""
Unit tests for AgentEnhanceOrchestrator

Tests the checkpoint-resume orchestration pattern for agent enhancement.

TASK-UX-FIX-E42: Implement orchestrator loop for automatic checkpoint-resume
"""

import pytest
from pathlib import Path
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

# Import the orchestrator
import sys
import importlib

# Add repository root to path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

# Import using importlib to handle 'global' keyword
orchestrator_module = importlib.import_module('installer.core.lib.agent_enhancement.orchestrator')
AgentEnhanceOrchestrator = orchestrator_module.AgentEnhanceOrchestrator
OrchestrationState = orchestrator_module.OrchestrationState


@dataclass
class MockEnhancementResult:
    """Mock EnhancementResult for testing."""
    success: bool
    agent_name: str
    sections: list
    templates: list
    examples: list
    diff: str
    error: str = None
    strategy_used: str = None
    core_file: Path = None
    extended_file: Path = None
    split_output: bool = False


class TestOrchestrationState:
    """Test OrchestrationState dataclass."""

    def test_state_creation(self):
        """Test that OrchestrationState can be created."""
        state = OrchestrationState(
            agent_file="/path/to/agent.md",
            template_dir="/path/to/template",
            strategy="ai",
            dry_run=False,
            verbose=True,
            timestamp="2025-11-24T18:00:00"
        )

        assert state.agent_file == "/path/to/agent.md"
        assert state.template_dir == "/path/to/template"
        assert state.strategy == "ai"
        assert state.dry_run is False
        assert state.verbose is True
        assert state.timestamp == "2025-11-24T18:00:00"


class TestAgentEnhanceOrchestrator:
    """Test AgentEnhanceOrchestrator class."""

    @pytest.fixture
    def tmp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            yield Path(tmpdirname)

    @pytest.fixture
    def mock_enhancer(self):
        """Create a mock SingleAgentEnhancer."""
        enhancer = Mock()
        enhancer.strategy = "ai"
        enhancer.dry_run = False
        enhancer.verbose = False
        return enhancer

    @pytest.fixture
    def mock_bridge_invoker(self):
        """Create a mock AgentBridgeInvoker."""
        invoker = Mock()
        invoker.has_response.return_value = False
        return invoker

    def test_orchestrator_creation(self, mock_enhancer):
        """Test that orchestrator can be created."""
        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )

        assert orchestrator.enhancer == mock_enhancer
        assert orchestrator.resume is False
        assert orchestrator.verbose is False
        # TASK-FIX-STATE01: State file now uses absolute path in ~/.agentecflow/state/
        expected_state_file = Path.home() / ".agentecflow" / "state" / ".agent-enhance-state.json"
        assert orchestrator.state_file == expected_state_file

    def test_save_state_creates_valid_json(self, tmp_dir, mock_enhancer, monkeypatch):
        """Test that _save_state() creates valid JSON file."""
        monkeypatch.chdir(tmp_dir)

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        agent_file = Path("/path/to/agent.md")
        template_dir = Path("/path/to/template")

        orchestrator._save_state(agent_file, template_dir)

        assert orchestrator.state_file.exists()
        state_data = json.loads(orchestrator.state_file.read_text())

        assert "agent_file" in state_data
        assert "template_dir" in state_data
        assert "strategy" in state_data
        assert "dry_run" in state_data
        assert "verbose" in state_data
        assert "timestamp" in state_data

        assert state_data["agent_file"] == str(agent_file.absolute())
        assert state_data["template_dir"] == str(template_dir.absolute())
        assert state_data["strategy"] == "ai"
        assert state_data["dry_run"] is False
        assert state_data["verbose"] is False

    def test_load_state_reads_valid_json(self, tmp_dir, mock_enhancer, monkeypatch):
        """Test that _load_state() reads and validates state file."""
        monkeypatch.chdir(tmp_dir)

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        # Create a valid state file
        state = OrchestrationState(
            agent_file="/path/to/agent.md",
            template_dir="/path/to/template",
            strategy="ai",
            dry_run=False,
            verbose=False,
            timestamp="2025-11-24T18:00:00"
        )

        orchestrator.state_file.write_text(
            json.dumps(state.__dict__, indent=2)
        )

        loaded_state = orchestrator._load_state()

        assert loaded_state.agent_file == "/path/to/agent.md"
        assert loaded_state.template_dir == "/path/to/template"
        assert loaded_state.strategy == "ai"
        assert loaded_state.dry_run is False
        assert loaded_state.verbose is False

    def test_load_state_handles_corrupted_file(self, tmp_dir, mock_enhancer, monkeypatch):
        """Test that _load_state() raises error on corrupt file."""
        monkeypatch.chdir(tmp_dir)

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        # Write invalid JSON
        orchestrator.state_file.write_text("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            orchestrator._load_state()

    def test_load_state_handles_missing_fields(self, tmp_dir, mock_enhancer, monkeypatch):
        """Test that _load_state() raises error on missing required fields."""
        monkeypatch.chdir(tmp_dir)

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        # Write JSON with missing fields
        orchestrator.state_file.write_text(
            json.dumps({"agent_file": "/path/to/agent.md"}, indent=2)
        )

        with pytest.raises(TypeError):
            orchestrator._load_state()

    def test_cleanup_state_removes_state_file(self, tmp_dir, mock_enhancer, monkeypatch):
        """Test that _cleanup_state() removes state file."""
        monkeypatch.chdir(tmp_dir)

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        # Create state file
        orchestrator.state_file.write_text("{}")

        orchestrator._cleanup_state()

        assert not orchestrator.state_file.exists()

    # =====================================================================
    # TASK-FIX-INV01: Phase-Specific File Path Tests
    # =====================================================================

    def test_cleanup_state_uses_phase_specific_response_file(self, tmp_dir, mock_enhancer, monkeypatch):
        """
        TASK-FIX-INV01: Test that _cleanup_state() uses phase-specific response file.

        Verifies that _cleanup_state() uses self.bridge_invoker.response_file
        instead of hardcoded ".agent-response.json".

        Expected: Uses phase 8 specific file (.agent-response-phase8.json)
        """
        monkeypatch.chdir(tmp_dir)

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        # Mock bridge invoker with phase-specific file paths
        orchestrator.bridge_invoker = Mock()
        orchestrator.bridge_invoker.response_file = Path(tmp_dir / ".agent-response-phase8.json")
        orchestrator.bridge_invoker.request_file = Path(tmp_dir / ".agent-request-phase8.json")

        # Create phase-specific files
        orchestrator.state_file.write_text("{}")
        orchestrator.bridge_invoker.response_file.write_text("{}")
        orchestrator.bridge_invoker.request_file.write_text("{}")

        # Verify files exist before cleanup
        assert orchestrator.bridge_invoker.response_file.exists()
        assert orchestrator.bridge_invoker.request_file.exists()

        orchestrator._cleanup_state()

        # Verify phase-specific files are deleted
        assert not orchestrator.bridge_invoker.response_file.exists()
        assert not orchestrator.bridge_invoker.request_file.exists()

    def test_cleanup_state_handles_none_bridge_invoker(self, tmp_dir, mock_enhancer, monkeypatch):
        """
        TASK-FIX-INV01: Test that _cleanup_state() handles None bridge_invoker.

        Verifies null check defensive programming when bridge_invoker is None.

        Expected: No AttributeError when bridge_invoker is None
        """
        monkeypatch.chdir(tmp_dir)

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"
        orchestrator.bridge_invoker = None  # Explicitly set to None

        # Create state file
        orchestrator.state_file.write_text("{}")

        # Should not raise AttributeError
        orchestrator._cleanup_state()

        # State file should still be cleaned
        assert not orchestrator.state_file.exists()

    def test_run_with_resume_error_message_uses_phase_specific_file(self, tmp_dir, mock_enhancer, monkeypatch):
        """
        TASK-FIX-INV01: Test that error message references phase-specific response file.

        Verifies that _run_with_resume() error message uses
        self.bridge_invoker.response_file instead of hardcoded ".agent-response.json".

        Expected: Error message contains ".agent-response-phase8.json"
        """
        monkeypatch.chdir(tmp_dir)

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=True,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        # Mock bridge invoker with phase-specific file path
        orchestrator.bridge_invoker = Mock()
        orchestrator.bridge_invoker.response_file = Path(".agent-response-phase8.json")
        orchestrator.bridge_invoker.has_response.return_value = False

        # Create valid state file
        state = OrchestrationState(
            agent_file=str(tmp_dir / "agent.md"),
            template_dir=str(tmp_dir / "template"),
            strategy="ai",
            dry_run=False,
            verbose=False,
            timestamp="2025-11-24T18:00:00"
        )
        orchestrator.state_file.write_text(
            json.dumps(state.__dict__, indent=2)
        )

        agent_file = tmp_dir / "agent.md"
        template_dir = tmp_dir / "template"

        # Capture the error message
        with pytest.raises(ValueError) as exc_info:
            orchestrator._run_with_resume(agent_file, template_dir)

        error_message = str(exc_info.value)

        # Verify error message contains phase-specific file
        assert ".agent-response-phase8.json" in error_message
        assert "Expected:" in error_message

    def test_run_with_resume_error_not_hardcoded_filename(self, tmp_dir, mock_enhancer, monkeypatch):
        """
        TASK-FIX-INV01: Test that error message does NOT contain hardcoded filename.

        Verifies regression: error message should not reference hardcoded
        ".agent-response.json" but instead use bridge_invoker.response_file.

        Expected: Error message does NOT contain hardcoded ".agent-response.json"
        """
        monkeypatch.chdir(tmp_dir)

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=True,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        # Mock bridge invoker with phase-specific file path
        orchestrator.bridge_invoker = Mock()
        orchestrator.bridge_invoker.response_file = Path(".agent-response-phase8.json")
        orchestrator.bridge_invoker.has_response.return_value = False

        # Create valid state file
        state = OrchestrationState(
            agent_file=str(tmp_dir / "agent.md"),
            template_dir=str(tmp_dir / "template"),
            strategy="ai",
            dry_run=False,
            verbose=False,
            timestamp="2025-11-24T18:00:00"
        )
        orchestrator.state_file.write_text(
            json.dumps(state.__dict__, indent=2)
        )

        agent_file = tmp_dir / "agent.md"
        template_dir = tmp_dir / "template"

        # Capture the error message
        with pytest.raises(ValueError) as exc_info:
            orchestrator._run_with_resume(agent_file, template_dir)

        error_message = str(exc_info.value)

        # Regression test: should NOT contain hardcoded filename
        # The hardcoded version would show ".agent-response.json"
        # The fixed version shows the phase-specific path from bridge_invoker
        assert ".agent-response.json" not in error_message or \
               ".agent-response-phase8.json" in error_message

    def test_run_initial_saves_state(self, tmp_dir, mock_enhancer, monkeypatch):
        """Test that _run_initial() saves state before calling enhancer."""
        monkeypatch.chdir(tmp_dir)

        # Mock enhancer to return success immediately
        mock_result = MockEnhancementResult(
            success=True,
            agent_name="test-agent",
            sections=["section1"],
            templates=["template1"],
            examples=["example1"],
            diff="diff"
        )
        mock_enhancer.enhance.return_value = mock_result

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        agent_file = tmp_dir / "agent.md"
        template_dir = tmp_dir / "template"
        agent_file.touch()
        template_dir.mkdir()

        result = orchestrator._run_initial(agent_file, template_dir)

        # State file should be created then cleaned up after success
        assert not orchestrator.state_file.exists()  # Cleaned up after success
        assert result.success is True
        mock_enhancer.enhance.assert_called_once()

    def test_run_initial_handles_exit_42(self, tmp_dir, mock_enhancer, monkeypatch):
        """Test that _run_initial() preserves state on exit 42."""
        monkeypatch.chdir(tmp_dir)

        # Mock enhancer to exit with code 42
        mock_enhancer.enhance.side_effect = SystemExit(42)

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        agent_file = tmp_dir / "agent.md"
        template_dir = tmp_dir / "template"
        agent_file.touch()
        template_dir.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            orchestrator._run_initial(agent_file, template_dir)

        assert exc_info.value.code == 42
        assert orchestrator.state_file.exists()  # State preserved for resume

    def test_run_with_resume_validates_state_file(self, tmp_dir, mock_enhancer, monkeypatch):
        """Test that _run_with_resume() validates state file exists."""
        monkeypatch.chdir(tmp_dir)

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=True,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        agent_file = tmp_dir / "agent.md"
        template_dir = tmp_dir / "template"

        with pytest.raises(ValueError, match="Cannot resume - no state file found"):
            orchestrator._run_with_resume(agent_file, template_dir)

    def test_run_with_resume_validates_response_file(self, tmp_dir, mock_enhancer, monkeypatch):
        """Test that _run_with_resume() validates response file exists."""
        monkeypatch.chdir(tmp_dir)

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=True,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        # Mock bridge invoker to return False for has_response
        orchestrator.bridge_invoker = Mock()
        orchestrator.bridge_invoker.has_response.return_value = False
        orchestrator.bridge_invoker.response_file = Path(".agent-response-phase8.json")

        # Create valid state file
        state = OrchestrationState(
            agent_file=str(tmp_dir / "agent.md"),
            template_dir=str(tmp_dir / "template"),
            strategy="ai",
            dry_run=False,
            verbose=False,
            timestamp="2025-11-24T18:00:00"
        )
        orchestrator.state_file.write_text(
            json.dumps(state.__dict__, indent=2)
        )

        agent_file = tmp_dir / "agent.md"
        template_dir = tmp_dir / "template"

        with pytest.raises(ValueError, match="Cannot resume - no agent response file found"):
            orchestrator._run_with_resume(agent_file, template_dir)

    def test_run_with_resume_succeeds(self, tmp_dir, mock_enhancer, monkeypatch):
        """Test that _run_with_resume() succeeds with valid state and response."""
        monkeypatch.chdir(tmp_dir)

        # Mock enhancer to return success
        mock_result = MockEnhancementResult(
            success=True,
            agent_name="test-agent",
            sections=["section1"],
            templates=["template1"],
            examples=["example1"],
            diff="diff"
        )
        mock_enhancer.enhance.return_value = mock_result

        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=True,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        # Mock bridge invoker to return True for has_response
        orchestrator.bridge_invoker = Mock()
        orchestrator.bridge_invoker.has_response.return_value = True
        orchestrator.bridge_invoker.request_file = Path(tmp_dir / ".agent-request-phase8.json")
        orchestrator.bridge_invoker.response_file = Path(tmp_dir / ".agent-response-phase8.json")

        # Create valid state file
        agent_file = tmp_dir / "agent.md"
        template_dir = tmp_dir / "template"
        agent_file.touch()
        template_dir.mkdir()

        state = OrchestrationState(
            agent_file=str(agent_file.absolute()),
            template_dir=str(template_dir.absolute()),
            strategy="ai",
            dry_run=False,
            verbose=False,
            timestamp="2025-11-24T18:00:00"
        )
        orchestrator.state_file.write_text(
            json.dumps(state.__dict__, indent=2)
        )

        result = orchestrator._run_with_resume(agent_file, template_dir)

        assert result.success is True
        assert not orchestrator.state_file.exists()  # Cleaned up after success
        mock_enhancer.enhance.assert_called_once()

    def test_checkpoint_resume_full_cycle(self, tmp_dir, mock_enhancer, monkeypatch):
        """Test full checkpoint-resume cycle with mocked exit 42."""
        monkeypatch.chdir(tmp_dir)

        # First call: exit 42
        # Second call: success
        mock_result = MockEnhancementResult(
            success=True,
            agent_name="test-agent",
            sections=["section1"],
            templates=["template1"],
            examples=["example1"],
            diff="diff"
        )

        mock_enhancer.enhance.side_effect = [
            SystemExit(42),  # First call exits
            mock_result      # Second call succeeds
        ]

        # First invocation (initial)
        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )
        orchestrator.state_file = tmp_dir / ".agent-enhance-state.json"

        agent_file = tmp_dir / "agent.md"
        template_dir = tmp_dir / "template"
        agent_file.touch()
        template_dir.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            orchestrator.run(agent_file, template_dir)

        assert exc_info.value.code == 42
        assert orchestrator.state_file.exists()

        # Simulate agent response creation
        (tmp_dir / ".agent-response.json").write_text(
            json.dumps({"status": "success", "response": "{}"})
        )

        # Second invocation (resume)
        orchestrator2 = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=True,
            verbose=False
        )
        orchestrator2.state_file = tmp_dir / ".agent-enhance-state.json"

        # Mock bridge invoker to return True for has_response
        orchestrator2.bridge_invoker = Mock()
        orchestrator2.bridge_invoker.has_response.return_value = True
        orchestrator2.bridge_invoker.request_file = Path(tmp_dir / ".agent-request-phase8.json")
        orchestrator2.bridge_invoker.response_file = Path(tmp_dir / ".agent-response-phase8.json")

        result = orchestrator2.run(agent_file, template_dir)

        assert result.success is True
        assert not orchestrator2.state_file.exists()  # Cleaned up


class TestStateFilePersistence:
    """
    TASK-FIX-STATE01: Tests for state file persistence with absolute paths.

    These tests verify that state files are written to ~/.agentecflow/state/
    for CWD independence, ensuring checkpoint-resume works across directory changes.
    """

    @pytest.fixture
    def mock_enhancer(self):
        """Create a mock SingleAgentEnhancer."""
        enhancer = Mock()
        enhancer.strategy = "ai"
        enhancer.dry_run = False
        enhancer.verbose = False
        return enhancer

    def test_state_file_uses_home_directory(self, mock_enhancer):
        """Test that state file is created in ~/.agentecflow/state/."""
        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )

        # Verify state file path is under home directory
        expected_dir = Path.home() / ".agentecflow" / "state"
        assert orchestrator.state_file.parent == expected_dir
        assert orchestrator.state_file.name == ".agent-enhance-state.json"

    def test_state_directory_created_automatically(self, mock_enhancer, tmp_path, monkeypatch):
        """Test that state directory is created if it doesn't exist."""
        # The directory should be created during orchestrator initialization
        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=False,
            verbose=False
        )

        # Verify the state directory exists
        assert orchestrator.state_file.parent.exists()
        assert orchestrator.state_file.parent.is_dir()

    def test_error_message_shows_absolute_path(self, mock_enhancer):
        """Test that error messages show absolute paths for debugging."""
        orchestrator = AgentEnhanceOrchestrator(
            enhancer=mock_enhancer,
            resume=True,  # resume mode
            verbose=False
        )

        # Create a temp directory for agent/template paths
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            agent_file = tmp_path / "agent.md"
            template_dir = tmp_path / "template"

            # Try to resume without state file
            with pytest.raises(ValueError) as exc_info:
                orchestrator._run_with_resume(agent_file, template_dir)

            error_message = str(exc_info.value)
            # Error should contain absolute path
            assert str(Path.home()) in error_message
            assert ".agentecflow/state" in error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
