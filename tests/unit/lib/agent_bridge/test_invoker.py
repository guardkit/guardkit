"""
Unit tests for AgentBridgeInvoker.

Tests the agent invocation request/response cycle including:
- Request file writing and exit code 42
- Response loading and caching
- Error handling and timeouts
- File cleanup behavior
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
        assert "--resume" in str(exc_info.value)

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
