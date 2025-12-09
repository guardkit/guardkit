"""
Unit tests for AgentBridgeInvoker.

Tests the agent invocation request/response cycle including:
- Request file writing and exit code 42
- Response loading and caching
- Error handling and timeouts
- File cleanup behavior
- Cache clearing (TASK-FIX-29C1)
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from lib.agent_bridge.invoker import (
    AgentBridgeInvoker,
    AgentInvocationError,
    AgentRequest,
    AgentResponse,
)


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for test files."""
    return tmp_path


@pytest.fixture
def invoker(temp_dir):
    """Create AgentBridgeInvoker with temp file paths."""
    request_file = temp_dir / ".agent-request.json"
    response_file = temp_dir / ".agent-response.json"
    return AgentBridgeInvoker(
        request_file=request_file,
        response_file=response_file,
        phase=6,
        phase_name="agent_generation"
    )


class TestAgentBridgeInvoker:
    """Test suite for AgentBridgeInvoker."""

    def test_invoke_writes_request_and_exits_42(self, invoker, temp_dir):
        """Test that invoke() writes request file and exits with code 42."""
        request_file = temp_dir / ".agent-request.json"

        with pytest.raises(SystemExit) as exc_info:
            invoker.invoke("architectural-reviewer", "Test prompt")

        # Verify exit code 42
        assert exc_info.value.code == 42

        # Verify request file written
        assert request_file.exists()

        # Verify request content
        request_data = json.loads(request_file.read_text())
        assert request_data["agent_name"] == "architectural-reviewer"
        assert request_data["prompt"] == "Test prompt"
        assert request_data["version"] == "1.0"
        assert request_data["phase"] == 6
        assert request_data["phase_name"] == "agent_generation"
        assert request_data["timeout_seconds"] == 120
        assert "request_id" in request_data
        assert "created_at" in request_data
        assert isinstance(request_data["context"], dict)

    def test_invoke_with_custom_timeout_and_context(self, invoker, temp_dir):
        """Test that invoke() accepts custom timeout and context."""
        request_file = temp_dir / ".agent-request.json"
        context = {"template_name": "test-template", "language": "Python"}

        with pytest.raises(SystemExit):
            invoker.invoke(
                "test-agent",
                "Test prompt",
                timeout_seconds=300,
                context=context
            )

        request_data = json.loads(request_file.read_text())
        assert request_data["timeout_seconds"] == 300
        assert request_data["context"] == context

    def test_invoke_with_cached_response_returns_immediately(self, invoker):
        """Test that invoke() returns cached response without exiting."""
        # Simulate cached response from previous load_response()
        cached_text = "Cached agent response"
        invoker._cached_response = cached_text

        # Should return cached response without exiting
        result = invoker.invoke("test-agent", "Test prompt")

        assert result == cached_text

    def test_load_response_success(self, invoker, temp_dir):
        """Test that load_response() reads success response correctly."""
        response_file = temp_dir / ".agent-response.json"

        # Create mock success response
        response_data = {
            "request_id": "test-123",
            "version": "1.0",
            "status": "success",
            "response": "Test agent response",
            "error_message": None,
            "error_type": None,
            "created_at": "2025-01-11T10:00:00Z",
            "duration_seconds": 5.234,
            "metadata": {"agent_name": "test-agent", "model": "claude-sonnet-4-5"}
        }
        response_file.write_text(json.dumps(response_data))

        # Load response
        result = invoker.load_response()

        # Verify response
        assert result == "Test agent response"
        assert invoker._cached_response == "Test agent response"

        # Verify file cleaned up
        assert not response_file.exists()

    def test_load_response_error(self, invoker, temp_dir):
        """Test that load_response() raises exception on error response."""
        response_file = temp_dir / ".agent-response.json"

        # Create mock error response
        response_data = {
            "request_id": "test-123",
            "version": "1.0",
            "status": "error",
            "response": None,
            "error_message": "Agent invocation failed",
            "error_type": "InvocationError",
            "created_at": "2025-01-11T10:00:00Z",
            "duration_seconds": 1.5,
            "metadata": {}
        }
        response_file.write_text(json.dumps(response_data))

        # Should raise AgentInvocationError
        with pytest.raises(AgentInvocationError) as exc_info:
            invoker.load_response()

        assert "Agent invocation failed" in str(exc_info.value)
        assert "InvocationError" in str(exc_info.value)

        # Verify file cleaned up even on error
        assert not response_file.exists()

    def test_load_response_timeout(self, invoker, temp_dir):
        """Test that load_response() raises exception on timeout response."""
        response_file = temp_dir / ".agent-response.json"

        # Create mock timeout response
        response_data = {
            "request_id": "test-123",
            "version": "1.0",
            "status": "timeout",
            "response": None,
            "error_message": "Request timed out",
            "error_type": "TimeoutError",
            "created_at": "2025-01-11T10:00:00Z",
            "duration_seconds": 120.0,
            "metadata": {}
        }
        response_file.write_text(json.dumps(response_data))

        # Should raise AgentInvocationError
        with pytest.raises(AgentInvocationError) as exc_info:
            invoker.load_response()

        assert "timed out" in str(exc_info.value).lower()

        # Verify file cleaned up even on timeout
        assert not response_file.exists()

    def test_load_response_missing_file(self, invoker):
        """Test that load_response() raises FileNotFoundError when file missing."""
        # Response file doesn't exist
        with pytest.raises(FileNotFoundError) as exc_info:
            invoker.load_response()

        assert "not found" in str(exc_info.value).lower()

    def test_load_response_malformed_json(self, invoker, temp_dir):
        """Test that load_response() raises ValueError on malformed JSON."""
        response_file = temp_dir / ".agent-response.json"
        response_file.write_text("{ invalid json }")

        with pytest.raises(ValueError) as exc_info:
            invoker.load_response()

        assert "malformed" in str(exc_info.value).lower()

    def test_load_response_invalid_format(self, invoker, temp_dir):
        """Test that load_response() raises ValueError on invalid format."""
        response_file = temp_dir / ".agent-response.json"

        # Missing required fields
        response_data = {
            "request_id": "test-123",
            "version": "1.0",
            # Missing status, response, etc.
        }
        response_file.write_text(json.dumps(response_data))

        with pytest.raises(ValueError) as exc_info:
            invoker.load_response()

        assert "invalid" in str(exc_info.value).lower()

    def test_has_pending_request_true(self, invoker, temp_dir):
        """Test has_pending_request() returns True when request file exists."""
        request_file = temp_dir / ".agent-request.json"
        request_file.write_text("{}")

        assert invoker.has_pending_request() is True

    def test_has_pending_request_false(self, invoker):
        """Test has_pending_request() returns False when request file doesn't exist."""
        assert invoker.has_pending_request() is False

    def test_has_response_true(self, invoker, temp_dir):
        """Test has_response() returns True when response file exists."""
        response_file = temp_dir / ".agent-response.json"
        response_file.write_text("{}")

        assert invoker.has_response() is True

    def test_has_response_false(self, invoker):
        """Test has_response() returns False when response file doesn't exist."""
        assert invoker.has_response() is False

    def test_request_format_matches_spec(self, invoker, temp_dir):
        """Test that request format matches technical specification exactly."""
        request_file = temp_dir / ".agent-request.json"
        context = {"template_name": "test", "language": "Python"}

        with pytest.raises(SystemExit):
            invoker.invoke(
                "architectural-reviewer",
                "Analyze this codebase",
                timeout_seconds=120,
                context=context
            )

        # Verify all required fields present and correct types
        request_data = json.loads(request_file.read_text())

        # Required fields
        assert isinstance(request_data["request_id"], str)
        assert request_data["version"] == "1.0"
        assert request_data["phase"] == 6
        assert request_data["phase_name"] == "agent_generation"
        assert request_data["agent_name"] == "architectural-reviewer"
        assert request_data["prompt"] == "Analyze this codebase"
        assert request_data["timeout_seconds"] == 120
        assert isinstance(request_data["created_at"], str)
        assert request_data["context"] == context

        # Validate ISO 8601 timestamp format (basic check)
        assert "T" in request_data["created_at"]
        assert len(request_data["created_at"]) > 10


class TestClearCacheMethod:
    """Test suite for clear_cache() method (TASK-FIX-29C1)."""

    def test_clear_cache_sets_cached_response_to_none(self, invoker):
        """Test that clear_cache() sets _cached_response to None."""
        # Set up cached response
        invoker._cached_response = "Cached response text"
        assert invoker._cached_response is not None

        # Clear cache
        invoker.clear_cache()

        # Verify cache is cleared
        assert invoker._cached_response is None

    def test_clear_cache_allows_new_invocation(self, invoker, temp_dir):
        """Test that after clear_cache(), next invoke() writes new request."""
        request_file = temp_dir / ".agent-request.json"

        # Set cached response
        invoker._cached_response = "Cached response"

        # Clear cache
        invoker.clear_cache()

        # Now invoke should write request and exit (not return cached)
        with pytest.raises(SystemExit) as exc_info:
            invoker.invoke("test-agent", "New prompt")

        # Should exit with code 42 (not return cached response)
        assert exc_info.value.code == 42
        assert request_file.exists()

        # Verify request was written with new prompt
        request_data = json.loads(request_file.read_text())
        assert request_data["prompt"] == "New prompt"

    def test_clear_cache_multiple_times(self, invoker):
        """Test that calling clear_cache() multiple times is safe."""
        # Set cache
        invoker._cached_response = "Response"

        # Clear multiple times
        invoker.clear_cache()
        assert invoker._cached_response is None

        invoker.clear_cache()
        assert invoker._cached_response is None

        invoker.clear_cache()
        assert invoker._cached_response is None

    def test_clear_cache_on_already_empty_cache(self, invoker):
        """Test that clear_cache() on empty cache doesn't raise error."""
        # Cache is already None by default
        assert invoker._cached_response is None

        # Should not raise error
        invoker.clear_cache()

        # Cache should still be None
        assert invoker._cached_response is None

    def test_clear_cache_different_cache_values(self, invoker):
        """Test clear_cache() with different types of cached values."""
        test_values = [
            "Simple string response",
            "Multi-line\nresponse\ntext",
            "",  # Empty string
            "Very long response " * 100,  # Long response
        ]

        for test_value in test_values:
            invoker._cached_response = test_value
            assert invoker._cached_response == test_value

            invoker.clear_cache()
            assert invoker._cached_response is None

    def test_clear_cache_in_multi_phase_workflow(self, invoker, temp_dir):
        """Test clear_cache() enables multi-phase invocation pattern."""
        request_file1 = temp_dir / ".agent-request.json"
        request_file2 = temp_dir / ".agent-request.json"

        # Phase 1: First invocation with cache
        invoker._cached_response = "Phase 1 response"
        result1 = invoker.invoke("phase1-agent", "Phase 1 prompt")
        assert result1 == "Phase 1 response"

        # Clear cache to allow Phase 5 invocation
        invoker.clear_cache()
        assert invoker._cached_response is None

        # Phase 5: New invocation should write request
        with pytest.raises(SystemExit) as exc_info:
            invoker.invoke("phase5-agent", "Phase 5 prompt")

        assert exc_info.value.code == 42

    def test_clear_cache_preserves_other_state(self, invoker):
        """Test that clear_cache() doesn't affect other invoker state."""
        # Set multiple attributes
        invoker._cached_response = "Cached"
        original_phase = invoker.phase
        original_phase_name = invoker.phase_name
        original_request_file = invoker.request_file
        original_response_file = invoker.response_file

        # Clear cache
        invoker.clear_cache()

        # Verify only cache was cleared, other state preserved
        assert invoker._cached_response is None
        assert invoker.phase == original_phase
        assert invoker.phase_name == original_phase_name
        assert invoker.request_file == original_request_file
        assert invoker.response_file == original_response_file

    def test_clear_cache_returns_none(self, invoker):
        """Test that clear_cache() returns None (implicit return)."""
        invoker._cached_response = "Cached"
        result = invoker.clear_cache()
        assert result is None

    def test_clear_cache_with_special_characters(self, invoker):
        """Test clear_cache() with special characters in cached response."""
        special_responses = [
            'Response with "quotes"',
            "Response with 'apostrophes'",
            "Response with\ttabs\tand\nnewlines",
            "Response with unicode: café, 中文, 😀",
            'Response with \\ backslashes',
        ]

        for response in special_responses:
            invoker._cached_response = response
            assert invoker._cached_response == response

            invoker.clear_cache()
            assert invoker._cached_response is None

    def test_clear_cache_and_load_response_sequence(self, invoker, temp_dir):
        """Test clear_cache() followed by load_response() works correctly."""
        response_file = temp_dir / ".agent-response.json"

        # Set cached response
        invoker._cached_response = "Old cached response"

        # Clear cache
        invoker.clear_cache()
        assert invoker._cached_response is None

        # Create new response file
        response_data = {
            "request_id": "new-123",
            "version": "1.0",
            "status": "success",
            "response": "New response from file",
            "error_message": None,
            "error_type": None,
            "created_at": "2025-01-11T10:00:00Z",
            "duration_seconds": 3.5,
            "metadata": {}
        }
        response_file.write_text(json.dumps(response_data))

        # Load new response
        result = invoker.load_response()

        # Should have new response, not old cached one
        assert result == "New response from file"
        assert invoker._cached_response == "New response from file"


class TestCachingBehavior:
    """Test suite for overall caching behavior with clear_cache()."""

    def test_cache_flow_without_clear(self, invoker):
        """Test caching without clearing (original behavior)."""
        # First response loaded
        invoker._cached_response = "First response"

        # Subsequent invokes return same cached response
        result1 = invoker.invoke("agent1", "prompt1")
        assert result1 == "First response"

        result2 = invoker.invoke("agent2", "prompt2")
        assert result2 == "First response"

    def test_cache_flow_with_clear(self, invoker, temp_dir):
        """Test caching with clearing (TASK-FIX-29C1 feature)."""
        request_file = temp_dir / ".agent-request.json"

        # First response loaded
        invoker._cached_response = "First response"

        # Invoke returns cached response
        result1 = invoker.invoke("agent1", "prompt1")
        assert result1 == "First response"

        # Clear cache to allow new invocation
        invoker.clear_cache()

        # Next invoke should write new request
        with pytest.raises(SystemExit) as exc_info:
            invoker.invoke("agent2", "prompt2")

        assert exc_info.value.code == 42

        # Verify new request was written
        request_data = json.loads(request_file.read_text())
        assert request_data["agent_name"] == "agent2"
        assert request_data["prompt"] == "prompt2"


class TestAgentInvocationError:
    """Test suite for AgentInvocationError exception."""

    def test_exception_can_be_raised(self):
        """Test that AgentInvocationError can be raised and caught."""
        with pytest.raises(AgentInvocationError):
            raise AgentInvocationError("Test error message")

    def test_exception_message(self):
        """Test that AgentInvocationError preserves error message."""
        message = "Agent invocation failed due to timeout"

        with pytest.raises(AgentInvocationError) as exc_info:
            raise AgentInvocationError(message)

        assert str(exc_info.value) == message


class TestAgentRequestDataclass:
    """Test suite for AgentRequest dataclass."""

    def test_agent_request_creation(self):
        """Test that AgentRequest can be created with all fields."""
        request = AgentRequest(
            request_id="test-123",
            version="1.0",
            phase=6,
            phase_name="agent_generation",
            agent_name="test-agent",
            prompt="Test prompt",
            timeout_seconds=120,
            created_at="2025-01-11T10:00:00Z",
            context={"key": "value"}
        )

        assert request.request_id == "test-123"
        assert request.version == "1.0"
        assert request.phase == 6
        assert request.agent_name == "test-agent"


class TestStateFilePersistence:
    """
    TASK-FIX-STATE01: Tests for state file persistence with absolute paths.

    These tests verify that request/response files are written to ~/.agentecflow/state/
    for CWD independence, ensuring checkpoint-resume works across directory changes.
    """

    def test_default_request_file_uses_home_directory(self):
        """Test that default request file is created in ~/.agentecflow/state/."""
        invoker = AgentBridgeInvoker(phase=6, phase_name="test")

        expected_dir = Path.home() / ".agentecflow" / "state"
        assert invoker.request_file.parent == expected_dir
        assert invoker.request_file.name == ".agent-request-phase6.json"

    def test_default_response_file_uses_home_directory(self):
        """Test that default response file is created in ~/.agentecflow/state/."""
        invoker = AgentBridgeInvoker(phase=6, phase_name="test")

        expected_dir = Path.home() / ".agentecflow" / "state"
        assert invoker.response_file.parent == expected_dir
        assert invoker.response_file.name == ".agent-response-phase6.json"

    def test_state_directory_created_automatically(self):
        """Test that state directory is created if it doesn't exist."""
        invoker = AgentBridgeInvoker(phase=6, phase_name="test")

        # Verify the state directory exists
        assert invoker.request_file.parent.exists()
        assert invoker.request_file.parent.is_dir()

    def test_explicit_path_overrides_default(self, temp_dir):
        """Test that explicit paths override the default home directory paths."""
        custom_request = temp_dir / "custom-request.json"
        custom_response = temp_dir / "custom-response.json"

        invoker = AgentBridgeInvoker(
            request_file=custom_request,
            response_file=custom_response,
            phase=6,
            phase_name="test"
        )

        assert invoker.request_file == custom_request
        assert invoker.response_file == custom_response

    def test_phase_specific_files(self):
        """Test that file names include phase number."""
        invoker = AgentBridgeInvoker(phase=8, phase_name="enhancement")

        assert "phase8" in invoker.request_file.name
        assert "phase8" in invoker.response_file.name

    def test_error_message_shows_absolute_path(self):
        """Test that error messages show absolute paths for debugging."""
        invoker = AgentBridgeInvoker(phase=6, phase_name="test")

        # Response file doesn't exist, so load_response should fail
        with pytest.raises(FileNotFoundError) as exc_info:
            invoker.load_response()

        error_message = str(exc_info.value)
        # Error should contain absolute path
        assert str(Path.home()) in error_message
        assert ".agentecflow/state" in error_message


class TestAgentResponseDataclass:
    """Test suite for AgentResponse dataclass."""

    def test_agent_response_creation(self):
        """Test that AgentResponse can be created with all fields."""
        response = AgentResponse(
            request_id="test-123",
            version="1.0",
            status="success",
            response="Test response",
            error_message=None,
            error_type=None,
            created_at="2025-01-11T10:00:00Z",
            duration_seconds=5.234,
            metadata={"model": "claude-sonnet-4-5"}
        )

        assert response.request_id == "test-123"
        assert response.status == "success"
        assert response.response == "Test response"
        assert response.duration_seconds == 5.234
