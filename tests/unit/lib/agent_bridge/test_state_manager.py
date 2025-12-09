"""
Unit tests for StateManager.

Tests the state persistence mechanism including:
- State creation and updates
- Timestamp preservation
- State loading and validation
- Error handling
- Cleanup behavior
"""

import json
import pytest
from pathlib import Path

from lib.agent_bridge.state_manager import (
    StateManager,
    TemplateCreateState,
)


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for test files."""
    return tmp_path


@pytest.fixture
def state_manager(temp_dir):
    """Create StateManager with temp file path."""
    state_file = temp_dir / ".template-create-state.json"
    return StateManager(state_file=state_file)


class TestStateManager:
    """Test suite for StateManager."""

    def test_save_state_creates_new(self, state_manager, temp_dir):
        """Test that save_state() creates new state with created_at."""
        state_file = temp_dir / ".template-create-state.json"

        config = {"codebase_path": "/path/to/code", "output_location": "global"}
        phase_data = {"analysis": {"language": "Python"}, "templates": []}

        # Save state
        state_manager.save_state(
            checkpoint="templates_generated",
            phase=5,
            config=config,
            phase_data=phase_data
        )

        # Verify file created
        assert state_file.exists()

        # Verify content
        state_data = json.loads(state_file.read_text())
        assert state_data["version"] == "1.0"
        assert state_data["checkpoint"] == "templates_generated"
        assert state_data["phase"] == 5
        assert state_data["config"] == config
        assert state_data["phase_data"] == phase_data
        assert "created_at" in state_data
        assert "updated_at" in state_data
        assert state_data["agent_request_pending"] is None

    def test_save_state_updates_existing(self, state_manager, temp_dir):
        """Test that save_state() preserves created_at when updating."""
        state_file = temp_dir / ".template-create-state.json"

        # Create initial state
        state_manager.save_state(
            checkpoint="analysis_complete",
            phase=2,
            config={"test": "config"},
            phase_data={"test": "data"}
        )

        # Read initial timestamps
        initial_data = json.loads(state_file.read_text())
        initial_created_at = initial_data["created_at"]
        initial_updated_at = initial_data["updated_at"]

        # Update state (simulate progression to next phase)
        import time
        time.sleep(0.01)  # Ensure updated_at will be different

        state_manager.save_state(
            checkpoint="templates_generated",
            phase=5,
            config={"test": "config"},
            phase_data={"test": "new data"}
        )

        # Verify created_at preserved, updated_at changed
        updated_data = json.loads(state_file.read_text())
        assert updated_data["created_at"] == initial_created_at
        assert updated_data["updated_at"] != initial_updated_at
        assert updated_data["checkpoint"] == "templates_generated"
        assert updated_data["phase"] == 5

    def test_save_state_with_agent_request_pending(self, state_manager, temp_dir):
        """Test that save_state() handles agent_request_pending field."""
        state_file = temp_dir / ".template-create-state.json"

        agent_request = {
            "request_id": "test-123",
            "created_at": "2025-01-11T10:00:00Z"
        }

        state_manager.save_state(
            checkpoint="agent_generation_pending",
            phase=6,
            config={},
            phase_data={},
            agent_request_pending=agent_request
        )

        state_data = json.loads(state_file.read_text())
        assert state_data["agent_request_pending"] == agent_request

    def test_load_state_round_trip(self, state_manager):
        """Test that state can be saved and loaded correctly."""
        config = {
            "codebase_path": "/path/to/code",
            "output_location": "global",
            "skip_qa": False
        }
        phase_data = {
            "qa_answers": {"template_name": "test"},
            "analysis": {"language": "Python"},
            "templates": [{"name": "test.template"}]
        }

        # Save state
        state_manager.save_state(
            checkpoint="templates_generated",
            phase=5,
            config=config,
            phase_data=phase_data
        )

        # Load state
        state = state_manager.load_state()

        # Verify all fields
        assert isinstance(state, TemplateCreateState)
        assert state.version == "1.0"
        assert state.checkpoint == "templates_generated"
        assert state.phase == 5
        assert state.config == config
        assert state.phase_data == phase_data
        assert isinstance(state.created_at, str)
        assert isinstance(state.updated_at, str)
        assert state.agent_request_pending is None

    def test_load_state_missing_file(self, state_manager):
        """Test that load_state() raises FileNotFoundError when file missing."""
        with pytest.raises(FileNotFoundError) as exc_info:
            state_manager.load_state()

        assert "not found" in str(exc_info.value).lower()
        assert "cannot resume" in str(exc_info.value).lower()

    def test_load_state_malformed_json(self, state_manager, temp_dir):
        """Test that load_state() raises ValueError on malformed JSON."""
        state_file = temp_dir / ".template-create-state.json"
        state_file.write_text("{ invalid json }")

        with pytest.raises(ValueError) as exc_info:
            state_manager.load_state()

        assert "malformed" in str(exc_info.value).lower()

    def test_load_state_invalid_format(self, state_manager, temp_dir):
        """Test that load_state() raises ValueError on invalid format."""
        state_file = temp_dir / ".template-create-state.json"

        # Missing required fields
        state_data = {
            "version": "1.0",
            "checkpoint": "test",
            # Missing phase, created_at, etc.
        }
        state_file.write_text(json.dumps(state_data))

        with pytest.raises(ValueError) as exc_info:
            state_manager.load_state()

        assert "invalid" in str(exc_info.value).lower()

    def test_has_state_true(self, state_manager, temp_dir):
        """Test has_state() returns True when state file exists."""
        state_file = temp_dir / ".template-create-state.json"
        state_file.write_text("{}")

        assert state_manager.has_state() is True

    def test_has_state_false(self, state_manager):
        """Test has_state() returns False when state file doesn't exist."""
        assert state_manager.has_state() is False

    def test_cleanup(self, state_manager, temp_dir):
        """Test cleanup() deletes state file."""
        state_file = temp_dir / ".template-create-state.json"

        # Create state
        state_manager.save_state(
            checkpoint="complete",
            phase=8,
            config={},
            phase_data={}
        )

        assert state_file.exists()

        # Cleanup
        state_manager.cleanup()

        assert not state_file.exists()

    def test_cleanup_missing_file_safe(self, state_manager):
        """Test cleanup() is safe to call on non-existent file."""
        # Should not raise exception
        state_manager.cleanup()

    def test_cleanup_can_be_called_multiple_times(self, state_manager):
        """Test cleanup() can be called multiple times safely."""
        # Should not raise exception on repeated calls
        state_manager.cleanup()
        state_manager.cleanup()
        state_manager.cleanup()

    def test_state_format_matches_spec(self, state_manager, temp_dir):
        """Test that state format matches technical specification exactly."""
        state_file = temp_dir / ".template-create-state.json"

        config = {
            "codebase_path": "/path/to/codebase",
            "output_location": "global",
            "skip_qa": False,
            "max_templates": None,
            "no_agents": False,
            "verbose": False
        }

        phase_data = {
            "qa_answers": {"template_name": "test-template"},
            "analysis": {"language": "Python", "framework": "FastAPI"},
            "manifest": {"name": "test-template", "version": "1.0.0"},
            "settings": {"naming_conventions": {}},
            "templates": [],
            "agent_inventory": {"global_agents": [], "local_agents": []}
        }

        agent_request = {
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "created_at": "2025-01-11T10:30:00.123Z"
        }

        # Save state
        state_manager.save_state(
            checkpoint="agent_generation_pending",
            phase=6,
            config=config,
            phase_data=phase_data,
            agent_request_pending=agent_request
        )

        # Verify format
        state_data = json.loads(state_file.read_text())

        # Required top-level fields
        assert state_data["version"] == "1.0"
        assert state_data["checkpoint"] == "agent_generation_pending"
        assert state_data["phase"] == 6
        assert isinstance(state_data["created_at"], str)
        assert isinstance(state_data["updated_at"], str)
        assert isinstance(state_data["config"], dict)
        assert isinstance(state_data["phase_data"], dict)
        assert isinstance(state_data["agent_request_pending"], dict)

        # Validate timestamp format (basic check)
        assert "T" in state_data["created_at"]
        assert "T" in state_data["updated_at"]

        # Verify config preserved
        assert state_data["config"] == config

        # Verify phase_data preserved
        assert state_data["phase_data"] == phase_data

        # Verify agent_request_pending preserved
        assert state_data["agent_request_pending"] == agent_request

    def test_save_state_handles_corrupted_existing_file(self, state_manager, temp_dir):
        """Test that save_state() handles corrupted existing file gracefully."""
        state_file = temp_dir / ".template-create-state.json"

        # Create corrupted file
        state_file.write_text("{ corrupted json content }")

        # Should not raise exception, should create new state
        state_manager.save_state(
            checkpoint="test",
            phase=1,
            config={},
            phase_data={}
        )

        # Verify new state created
        assert state_file.exists()
        state_data = json.loads(state_file.read_text())
        assert state_data["checkpoint"] == "test"


class TestStateFilePersistence:
    """
    TASK-FIX-STATE01: Tests for state file persistence with absolute paths.

    These tests verify that state files are written to ~/.agentecflow/state/
    for CWD independence, ensuring checkpoint-resume works across directory changes.
    """

    def test_default_state_file_uses_home_directory(self):
        """Test that default state file is created in ~/.agentecflow/state/."""
        manager = StateManager()  # No explicit state_file provided

        expected_dir = Path.home() / ".agentecflow" / "state"
        assert manager.state_file.parent == expected_dir
        assert manager.state_file.name == ".template-create-state.json"

    def test_state_directory_created_automatically(self):
        """Test that state directory is created if it doesn't exist."""
        manager = StateManager()  # Default path

        # Verify the state directory exists
        assert manager.state_file.parent.exists()
        assert manager.state_file.parent.is_dir()

    def test_explicit_path_overrides_default(self, temp_dir):
        """Test that explicit path overrides the default home directory path."""
        custom_path = temp_dir / "custom-state.json"
        manager = StateManager(state_file=custom_path)

        assert manager.state_file == custom_path
        assert manager.state_file.parent == temp_dir

    def test_error_message_shows_absolute_path(self):
        """Test that error messages show absolute paths for debugging."""
        manager = StateManager()  # Default path

        # State file doesn't exist, so load_state should fail
        with pytest.raises(FileNotFoundError) as exc_info:
            manager.load_state()

        error_message = str(exc_info.value)
        # Error should contain absolute path
        assert str(Path.home()) in error_message
        assert ".agentecflow/state" in error_message


class TestTemplateCreateStateDataclass:
    """Test suite for TemplateCreateState dataclass."""

    def test_template_create_state_creation(self):
        """Test that TemplateCreateState can be created with all fields."""
        state = TemplateCreateState(
            version="1.0",
            checkpoint="templates_generated",
            phase=5,
            created_at="2025-01-11T10:00:00Z",
            updated_at="2025-01-11T10:05:00Z",
            config={"test": "config"},
            phase_data={"test": "data"},
            agent_request_pending=None
        )

        assert state.version == "1.0"
        assert state.checkpoint == "templates_generated"
        assert state.phase == 5
        assert state.config == {"test": "config"}
        assert state.phase_data == {"test": "data"}
        assert state.agent_request_pending is None

    def test_template_create_state_with_agent_request(self):
        """Test that TemplateCreateState handles agent_request_pending."""
        agent_request = {"request_id": "test-123"}

        state = TemplateCreateState(
            version="1.0",
            checkpoint="agent_generation_pending",
            phase=6,
            created_at="2025-01-11T10:00:00Z",
            updated_at="2025-01-11T10:00:00Z",
            config={},
            phase_data={},
            agent_request_pending=agent_request
        )

        assert state.agent_request_pending == agent_request

    def test_template_create_state_serialization(self):
        """Test that TemplateCreateState can be serialized to dict."""
        from dataclasses import asdict

        state = TemplateCreateState(
            version="1.0",
            checkpoint="test",
            phase=1,
            created_at="2025-01-11T10:00:00Z",
            updated_at="2025-01-11T10:00:00Z",
            config={"key": "value"},
            phase_data={"data": "value"}
        )

        state_dict = asdict(state)

        assert isinstance(state_dict, dict)
        assert state_dict["version"] == "1.0"
        assert state_dict["checkpoint"] == "test"
        assert state_dict["config"] == {"key": "value"}
