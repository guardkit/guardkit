"""
Unit tests for TASK-FIX-7B74: Phase-specific cache files for multi-phase AI invocation.

Tests the phase-aware cache file naming and isolation between Phase 1 (codebase analysis)
and Phase 5 (agent generation) to prevent cache collisions during checkpoint-resume.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from lib.agent_bridge.invoker import (
    AgentBridgeInvoker,
    AgentInvocationError,
)


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for test files."""
    import os
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)


class TestPhaseSpecificCacheFiles:
    """Test suite for phase-specific cache file naming (TASK-FIX-7B74)."""

    def test_phase1_uses_phase_specific_files(self, temp_dir):
        """Test that Phase 1 invoker uses phase1-specific cache files."""
        invoker = AgentBridgeInvoker(
            phase=1,
            phase_name="ai_analysis"
        )

        assert invoker.request_file == Path(".agent-request-phase1.json")
        assert invoker.response_file == Path(".agent-response-phase1.json")

    def test_phase5_uses_phase_specific_files(self, temp_dir):
        """Test that Phase 5 invoker uses phase5-specific cache files."""
        invoker = AgentBridgeInvoker(
            phase=5,
            phase_name="agent_generation"
        )

        assert invoker.request_file == Path(".agent-request-phase5.json")
        assert invoker.response_file == Path(".agent-response-phase5.json")

    def test_phase6_uses_phase_specific_files(self, temp_dir):
        """Test that Phase 6 invoker uses phase6-specific cache files (default phase)."""
        invoker = AgentBridgeInvoker(
            phase=6,
            phase_name="default"
        )

        assert invoker.request_file == Path(".agent-request-phase6.json")
        assert invoker.response_file == Path(".agent-response-phase6.json")

    def test_explicit_paths_override_phase_defaults(self, temp_dir):
        """Test that explicit file paths override phase-based defaults."""
        custom_request = Path("custom-request.json")
        custom_response = Path("custom-response.json")

        invoker = AgentBridgeInvoker(
            request_file=custom_request,
            response_file=custom_response,
            phase=1,
            phase_name="ai_analysis"
        )

        assert invoker.request_file == custom_request
        assert invoker.response_file == custom_response

    def test_string_paths_are_converted_to_path(self, temp_dir):
        """Test that string file paths are converted to Path objects."""
        invoker = AgentBridgeInvoker(
            request_file="my-request.json",
            response_file="my-response.json",
            phase=1
        )

        assert isinstance(invoker.request_file, Path)
        assert isinstance(invoker.response_file, Path)
        assert invoker.request_file == Path("my-request.json")
        assert invoker.response_file == Path("my-response.json")

    def test_phase1_and_phase5_use_different_files(self, temp_dir):
        """Test that Phase 1 and Phase 5 invokers use different cache files."""
        phase1 = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")
        phase5 = AgentBridgeInvoker(phase=5, phase_name="agent_generation")

        # Verify different request files
        assert phase1.request_file != phase5.request_file
        assert "phase1" in str(phase1.request_file)
        assert "phase5" in str(phase5.request_file)

        # Verify different response files
        assert phase1.response_file != phase5.response_file
        assert "phase1" in str(phase1.response_file)
        assert "phase5" in str(phase5.response_file)


class TestCacheIsolation:
    """Test suite for cache isolation between phases (TASK-FIX-7B74)."""

    def test_phase1_cache_not_overwritten_by_phase5(self, temp_dir):
        """Test that Phase 1 cache is not overwritten when Phase 5 writes its cache."""
        # Create Phase 1 invoker and simulate cached response
        phase1 = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")

        # Write Phase 1 response (object type)
        phase1_response = {
            "request_id": "phase1-123",
            "version": "1.0",
            "status": "success",
            "response": '{"primary_language": "Python", "framework": "FastAPI"}',
            "error_message": None,
            "error_type": None,
            "created_at": "2025-01-11T10:00:00Z",
            "duration_seconds": 5.0,
            "metadata": {}
        }
        phase1.response_file.write_text(json.dumps(phase1_response))

        # Create Phase 5 invoker
        phase5 = AgentBridgeInvoker(phase=5, phase_name="agent_generation")

        # Write Phase 5 response (array type)
        phase5_response = {
            "request_id": "phase5-456",
            "version": "1.0",
            "status": "success",
            "response": '[{"name": "api-specialist", "priority": 10}]',
            "error_message": None,
            "error_type": None,
            "created_at": "2025-01-11T10:05:00Z",
            "duration_seconds": 8.0,
            "metadata": {}
        }
        phase5.response_file.write_text(json.dumps(phase5_response))

        # Verify Phase 1 cache is still intact
        phase1_data = json.loads(phase1.response_file.read_text())
        assert phase1_data["request_id"] == "phase1-123"
        assert "primary_language" in phase1_data["response"]

        # Verify Phase 5 cache has its own data
        phase5_data = json.loads(phase5.response_file.read_text())
        assert phase5_data["request_id"] == "phase5-456"
        assert "api-specialist" in phase5_data["response"]

    def test_resume_loads_correct_phase_response(self, temp_dir):
        """Test that resume from Phase 1 checkpoint loads Phase 1 cache, not Phase 5."""
        # Setup Phase 1 response (object)
        phase1_response_file = Path(".agent-response-phase1.json")
        phase1_response = {
            "request_id": "phase1-123",
            "version": "1.0",
            "status": "success",
            "response": '{"primary_language": "Python"}',
            "error_message": None,
            "error_type": None,
            "created_at": "2025-01-11T10:00:00Z",
            "duration_seconds": 5.0,
            "metadata": {}
        }
        phase1_response_file.write_text(json.dumps(phase1_response))

        # Setup Phase 5 response (array)
        phase5_response_file = Path(".agent-response-phase5.json")
        phase5_response = {
            "request_id": "phase5-456",
            "version": "1.0",
            "status": "success",
            "response": '[{"name": "agent1"}]',
            "error_message": None,
            "error_type": None,
            "created_at": "2025-01-11T10:05:00Z",
            "duration_seconds": 8.0,
            "metadata": {}
        }
        phase5_response_file.write_text(json.dumps(phase5_response))

        # Create Phase 1 invoker and load response
        phase1 = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")
        response1 = phase1.load_response()

        # Should get Phase 1 response (object)
        assert "Python" in response1

        # Response file should be cleaned up after loading
        assert not phase1_response_file.exists()

        # Phase 5 cache should still exist
        assert phase5_response_file.exists()

        # Create Phase 5 invoker and load response
        phase5 = AgentBridgeInvoker(phase=5, phase_name="agent_generation")
        response5 = phase5.load_response()

        # Should get Phase 5 response (array)
        assert "agent1" in response5


class TestClearCacheDeletesFiles:
    """Test suite for clear_cache() deleting files (TASK-FIX-7B74 enhancement)."""

    def test_clear_cache_deletes_request_file(self, temp_dir):
        """Test that clear_cache() deletes the request file."""
        invoker = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")

        # Create request file
        invoker.request_file.write_text('{"test": true}')
        assert invoker.request_file.exists()

        # Clear cache
        invoker.clear_cache()

        # Request file should be deleted
        assert not invoker.request_file.exists()

    def test_clear_cache_deletes_response_file(self, temp_dir):
        """Test that clear_cache() deletes the response file."""
        invoker = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")

        # Create response file
        invoker.response_file.write_text('{"test": true}')
        assert invoker.response_file.exists()

        # Clear cache
        invoker.clear_cache()

        # Response file should be deleted
        assert not invoker.response_file.exists()

    def test_clear_cache_deletes_both_files(self, temp_dir):
        """Test that clear_cache() deletes both request and response files."""
        invoker = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")

        # Create both files
        invoker.request_file.write_text('{"request": true}')
        invoker.response_file.write_text('{"response": true}')
        assert invoker.request_file.exists()
        assert invoker.response_file.exists()

        # Clear cache
        invoker.clear_cache()

        # Both files should be deleted
        assert not invoker.request_file.exists()
        assert not invoker.response_file.exists()

    def test_clear_cache_safe_when_files_dont_exist(self, temp_dir):
        """Test that clear_cache() doesn't raise error when files don't exist."""
        invoker = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")

        # Files don't exist initially
        assert not invoker.request_file.exists()
        assert not invoker.response_file.exists()

        # Clear cache should not raise error
        invoker.clear_cache()

        # Memory cache should be cleared
        assert invoker._cached_response is None

    def test_clear_cache_clears_memory_and_files(self, temp_dir):
        """Test that clear_cache() clears both memory cache and files."""
        invoker = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")

        # Set memory cache and create files
        invoker._cached_response = "Cached response"
        invoker.request_file.write_text('{"request": true}')
        invoker.response_file.write_text('{"response": true}')

        # Clear cache
        invoker.clear_cache()

        # Memory cache should be cleared
        assert invoker._cached_response is None

        # Files should be deleted
        assert not invoker.request_file.exists()
        assert not invoker.response_file.exists()


class TestRegressionCacheCollision:
    """Regression tests for the original cache collision bug (TASK-FIX-7B74)."""

    def test_regression_phase5_array_doesnt_corrupt_phase1_resume(self, temp_dir):
        """
        Regression test: Phase 5 writing array response should not affect
        Phase 1 resume which expects object response.

        Original bug: AttributeError: 'list' object has no attribute 'keys'
        """
        # Create Phase 1 invoker and write object response
        phase1 = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")
        phase1_response = {
            "request_id": "phase1-123",
            "version": "1.0",
            "status": "success",
            "response": '{"primary_language": "Python", "framework": "FastAPI"}',
            "error_message": None,
            "error_type": None,
            "created_at": "2025-01-11T10:00:00Z",
            "duration_seconds": 5.0,
            "metadata": {}
        }
        phase1.response_file.write_text(json.dumps(phase1_response))

        # Create Phase 5 invoker and write array response
        phase5 = AgentBridgeInvoker(phase=5, phase_name="agent_generation")
        phase5_response = {
            "request_id": "phase5-456",
            "version": "1.0",
            "status": "success",
            "response": '[{"name": "api-specialist", "priority": 10}]',
            "error_message": None,
            "error_type": None,
            "created_at": "2025-01-11T10:05:00Z",
            "duration_seconds": 8.0,
            "metadata": {}
        }
        phase5.response_file.write_text(json.dumps(phase5_response))

        # Now simulate resuming from Phase 1 checkpoint
        # This should load Phase 1's object response, not Phase 5's array response
        new_phase1_invoker = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")
        response = new_phase1_invoker.load_response()

        # Response should be Phase 1's object (as string), not Phase 5's array
        assert "primary_language" in response
        assert "Python" in response

        # Should NOT contain Phase 5's array data
        assert "api-specialist" not in response

    def test_regression_original_shared_invoker_pattern_no_longer_fails(self, temp_dir):
        """
        Regression test: Simulates the original pattern that caused the bug.

        Old pattern:
        1. Phase 1 invokes AI -> writes response to shared file
        2. Resume -> loads response (object)
        3. Phase 5 invokes AI -> overwrites same file with array response
        4. Resume -> loads array, expects object -> AttributeError

        New pattern with separate invokers:
        1. Phase 1 invokes AI -> writes to phase1-specific file
        2. Resume -> loads phase1 response (object)
        3. Phase 5 invokes AI -> writes to phase5-specific file
        4. Resume -> loads phase5 response (array) - correct!
        """
        # Phase 1: Write object response
        phase1 = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")
        phase1_response = {
            "request_id": "p1",
            "version": "1.0",
            "status": "success",
            "response": '{"type": "object_data"}',
            "error_message": None,
            "error_type": None,
            "created_at": "2025-01-11T10:00:00Z",
            "duration_seconds": 1.0,
            "metadata": {}
        }
        phase1.response_file.write_text(json.dumps(phase1_response))

        # Resume Phase 1: Load response
        r1 = phase1.load_response()
        assert "object_data" in r1

        # Phase 5: Write array response (to different file!)
        phase5 = AgentBridgeInvoker(phase=5, phase_name="agent_generation")
        phase5_response = {
            "request_id": "p5",
            "version": "1.0",
            "status": "success",
            "response": '[{"type": "array_item"}]',
            "error_message": None,
            "error_type": None,
            "created_at": "2025-01-11T10:05:00Z",
            "duration_seconds": 1.0,
            "metadata": {}
        }
        phase5.response_file.write_text(json.dumps(phase5_response))

        # Resume Phase 5: Load response (should get array, not object)
        r5 = phase5.load_response()
        assert "array_item" in r5


class TestInvokerInvokeCacheBehavior:
    """Test suite for invoke() method with phase-specific caching."""

    def test_invoke_exits_42_and_writes_to_phase_specific_file(self, temp_dir):
        """Test that invoke() writes to phase-specific request file."""
        phase1 = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")

        with pytest.raises(SystemExit) as exc_info:
            phase1.invoke("test-agent", "Test prompt")

        assert exc_info.value.code == 42

        # Verify phase-specific request file was written
        assert phase1.request_file.exists()
        assert phase1.request_file.name == ".agent-request-phase1.json"

        request_data = json.loads(phase1.request_file.read_text())
        assert request_data["phase"] == 1
        assert request_data["phase_name"] == "ai_analysis"

    def test_invoke_uses_cached_response_if_available(self, temp_dir):
        """Test that invoke() returns cached response without exiting."""
        phase1 = AgentBridgeInvoker(phase=1, phase_name="ai_analysis")
        phase1._cached_response = "Cached Phase 1 response"

        # Should return cached response immediately
        result = phase1.invoke("test-agent", "Test prompt")

        assert result == "Cached Phase 1 response"
        # No request file should be created
        assert not phase1.request_file.exists()
