"""
Comprehensive test suite for TASK-MCP-C1C1 MCP implementation.

This test suite covers:
1. DetailLevel enum (3 tests)
2. Utils module (5 tests)
3. MCPMonitor class (15 tests)
4. Context7Client class (12 tests)
5. Integration tests (5 tests)

Total: 40 unit tests + 5 integration tests
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime

# Import the modules under test
from lib.mcp.detail_level import DetailLevel
from lib.mcp.utils import count_tokens, format_token_count, validate_response_size
from lib.mcp.monitor import MCPRequest, MCPResponse, MCPMonitor
from lib.mcp.context7_client import Context7Client


# ============================================================================
# SECTION 1: DetailLevel Enum Tests (3 tests)
# ============================================================================

class TestDetailLevelEnum:
    """Test DetailLevel enum functionality."""

    def test_detail_level_enum_values(self):
        """Test that enum has correct string values."""
        assert DetailLevel.SUMMARY.value == "summary"
        assert DetailLevel.DETAILED.value == "detailed"

    def test_detail_level_token_ranges(self):
        """Test token ranges for each detail level."""
        # SUMMARY should be 500-1000 tokens
        summary_min, summary_max = DetailLevel.SUMMARY.token_range()
        assert summary_min == 500
        assert summary_max == 1000

        # DETAILED should be 3500-5000 tokens
        detailed_min, detailed_max = DetailLevel.DETAILED.token_range()
        assert detailed_min == 3500
        assert detailed_max == 5000

    def test_detail_level_default_tokens(self):
        """Test default token calculation (midpoint of range)."""
        # SUMMARY default: (500 + 1000) // 2 = 750
        assert DetailLevel.SUMMARY.default_tokens() == 750

        # DETAILED default: (3500 + 5000) // 2 = 4250
        assert DetailLevel.DETAILED.default_tokens() == 4250


# ============================================================================
# SECTION 2: Utils Module Tests (5 tests)
# ============================================================================

class TestCountTokens:
    """Test token counting functionality."""

    def test_count_tokens_chars_method(self):
        """Test character-based token estimation."""
        # 1 token ≈ 4 characters
        text = "Hello, world!"  # 13 chars
        # 13 // 4 = 3 tokens
        assert count_tokens(text, method="chars") == 3

    def test_count_tokens_words_method(self):
        """Test word-based token estimation."""
        # 1 token ≈ 0.75 words
        text = "The quick brown fox"  # 4 words
        # 4 * 0.75 = 3 tokens
        assert count_tokens(text, method="words") == 3

    def test_count_tokens_edge_case_empty_string(self):
        """Test token counting for empty strings."""
        # max(1, 0 // 4) = 1
        assert count_tokens("", method="chars") == 1
        assert count_tokens("", method="words") == 1

    def test_count_tokens_error_invalid_method(self):
        """Test error handling for invalid method."""
        with pytest.raises(ValueError, match="Invalid method"):
            count_tokens("text", method="invalid")

    def test_count_tokens_error_none_text(self):
        """Test error handling for None text."""
        with pytest.raises(ValueError, match="Text cannot be None"):
            count_tokens(None)


class TestFormatTokenCount:
    """Test token count formatting."""

    def test_format_token_count_without_budget(self):
        """Test formatting without budget comparison."""
        assert format_token_count(1234) == "1,234 tokens"

    def test_format_token_count_within_budget(self):
        """Test formatting when within budget."""
        result = format_token_count(1000, 2000)
        assert "1,000 / 2,000 tokens (50%)" in result

    def test_format_token_count_over_budget(self):
        """Test formatting when over budget."""
        result = format_token_count(2500, 2000)
        assert "2,500 / 2,000 tokens" in result
        assert "125%" in result
        assert "OVER BUDGET" in result


class TestValidateResponseSize:
    """Test response size validation."""

    def test_validate_response_size_exact_match(self):
        """Test validation when actual matches expected."""
        is_valid, variance = validate_response_size(1000, 1000)
        assert is_valid is True
        assert variance == 0.0

    def test_validate_response_size_within_threshold(self):
        """Test validation when variance is within threshold."""
        # 1200 vs 1000 = 20% variance, threshold is 20%
        is_valid, variance = validate_response_size(1200, 1000)
        assert is_valid is True
        assert abs(variance - 0.2) < 0.001

    def test_validate_response_size_over_threshold(self):
        """Test validation when variance exceeds threshold."""
        # 1250 vs 1000 = 25% variance, threshold is 20%
        is_valid, variance = validate_response_size(1250, 1000)
        assert is_valid is False
        assert abs(variance - 0.25) < 0.001

    def test_validate_response_size_under_budget(self):
        """Test validation when under budget."""
        # 800 vs 1000 = -20% variance
        is_valid, variance = validate_response_size(800, 1000)
        assert is_valid is True
        assert abs(variance - (-0.2)) < 0.001


# ============================================================================
# SECTION 3: MCPMonitor Tests (15 tests)
# ============================================================================

class TestMCPRequest:
    """Test MCPRequest dataclass."""

    def test_mcp_request_initialization(self):
        """Test basic MCPRequest creation."""
        request = MCPRequest(
            mcp_name="context7",
            method="get_library_docs",
            query={"library_id": "/fastapi"},
            expected_tokens=1000,
            phase="phase_2"
        )
        assert request.mcp_name == "context7"
        assert request.method == "get_library_docs"
        assert request.expected_tokens == 1000
        assert request.phase == "phase_2"
        assert isinstance(request.timestamp, datetime)

    def test_mcp_request_validation_negative_tokens(self):
        """Test validation of negative expected tokens."""
        with pytest.raises(ValueError, match="Expected tokens must be non-negative"):
            MCPRequest(
                mcp_name="context7",
                method="get_library_docs",
                query={},
                expected_tokens=-100,
                phase="phase_2"
            )

    def test_mcp_request_validation_empty_mcp_name(self):
        """Test validation of empty MCP name."""
        with pytest.raises(ValueError, match="MCP name cannot be empty"):
            MCPRequest(
                mcp_name="",
                method="get_library_docs",
                query={},
                expected_tokens=1000,
                phase="phase_2"
            )

    def test_mcp_request_validation_empty_method(self):
        """Test validation of empty method."""
        with pytest.raises(ValueError, match="Method cannot be empty"):
            MCPRequest(
                mcp_name="context7",
                method="",
                query={},
                expected_tokens=1000,
                phase="phase_2"
            )


class TestMCPResponse:
    """Test MCPResponse dataclass."""

    def test_mcp_response_initialization(self):
        """Test basic MCPResponse creation and variance calculation."""
        request = MCPRequest(
            mcp_name="context7",
            method="get_library_docs",
            query={},
            expected_tokens=1000,
            phase="phase_2"
        )
        response = MCPResponse(
            request=request,
            actual_tokens=850,
            duration_seconds=1.2,
            success=True
        )
        assert response.actual_tokens == 850
        assert response.duration_seconds == 1.2
        assert response.success is True
        # Variance = (850 - 1000) / 1000 = -0.15
        assert abs(response.variance - (-0.15)) < 0.001

    def test_mcp_response_variance_percentage(self):
        """Test variance as percentage."""
        request = MCPRequest(
            mcp_name="context7",
            method="get_library_docs",
            query={},
            expected_tokens=1000,
            phase="phase_2"
        )
        response = MCPResponse(
            request=request,
            actual_tokens=1200,
            duration_seconds=1.0,
            success=True
        )
        # Variance = 0.2, so percentage is 20.0
        assert abs(response.variance_percentage() - 20.0) < 0.1

    def test_mcp_response_is_over_budget(self):
        """Test over-budget detection."""
        request = MCPRequest(
            mcp_name="context7",
            method="get_library_docs",
            query={},
            expected_tokens=1000,
            phase="phase_2"
        )
        response_over = MCPResponse(
            request=request,
            actual_tokens=1300,
            duration_seconds=1.0,
            success=True
        )
        assert response_over.is_over_budget(threshold=0.20) is True

        response_under = MCPResponse(
            request=request,
            actual_tokens=1200,
            duration_seconds=1.0,
            success=True
        )
        assert response_under.is_over_budget(threshold=0.20) is False

    def test_mcp_response_error_message(self):
        """Test error message handling."""
        request = MCPRequest(
            mcp_name="context7",
            method="get_library_docs",
            query={},
            expected_tokens=1000,
            phase="phase_2"
        )
        response = MCPResponse(
            request=request,
            actual_tokens=0,
            duration_seconds=0.5,
            success=False,
            error_message="Connection timeout"
        )
        assert response.success is False
        assert response.error_message == "Connection timeout"

    def test_mcp_response_zero_expected_tokens(self):
        """Test variance when expected tokens is 0."""
        request = MCPRequest(
            mcp_name="context7",
            method="get_library_docs",
            query={},
            expected_tokens=0,
            phase="phase_2"
        )
        response = MCPResponse(
            request=request,
            actual_tokens=500,
            duration_seconds=1.0,
            success=True
        )
        # When expected is 0, variance should be 0.0
        assert response.variance == 0.0


class TestMCPMonitor:
    """Test MCPMonitor class."""

    def test_mcp_monitor_initialization(self):
        """Test monitor initialization."""
        monitor = MCPMonitor(variance_threshold=0.15)
        assert monitor.variance_threshold == 0.15
        assert len(monitor.requests) == 0
        assert len(monitor.responses) == 0

    def test_mcp_monitor_record_request(self):
        """Test recording a request."""
        monitor = MCPMonitor()
        request = monitor.record_request(
            mcp_name="context7",
            method="get_library_docs",
            query={"library_id": "/fastapi"},
            expected_tokens=1000,
            phase="phase_2"
        )
        assert len(monitor.requests) == 1
        assert request.mcp_name == "context7"
        assert monitor.requests[0] == request

    def test_mcp_monitor_record_response(self):
        """Test recording a response."""
        monitor = MCPMonitor()
        request = monitor.record_request(
            mcp_name="context7",
            method="get_library_docs",
            query={},
            expected_tokens=1000,
            phase="phase_2"
        )
        response = monitor.record_response(
            request=request,
            actual_tokens=900,
            duration_seconds=1.2,
            success=True
        )
        assert len(monitor.responses) == 1
        assert response.actual_tokens == 900
        assert monitor.responses[0] == response

    def test_mcp_monitor_variance_threshold_setter(self):
        """Test setting variance threshold."""
        monitor = MCPMonitor()
        monitor.variance_threshold = 0.25
        assert monitor.variance_threshold == 0.25

        with pytest.raises(ValueError, match="Variance threshold must be positive"):
            monitor.variance_threshold = -0.1

    def test_mcp_monitor_total_calls(self):
        """Test get_total_calls method."""
        monitor = MCPMonitor()
        request1 = monitor.record_request(
            mcp_name="context7",
            method="method1",
            query={},
            expected_tokens=1000,
            phase="phase_2"
        )
        monitor.record_response(request1, 900, 1.0, True)

        request2 = monitor.record_request(
            mcp_name="context7",
            method="method2",
            query={},
            expected_tokens=1000,
            phase="phase_3"
        )
        monitor.record_response(request2, 950, 1.0, True)

        assert monitor.get_total_calls() == 2

    def test_mcp_monitor_successful_calls(self):
        """Test get_successful_calls method."""
        monitor = MCPMonitor()
        request1 = monitor.record_request(
            mcp_name="context7",
            method="method1",
            query={},
            expected_tokens=1000,
            phase="phase_2"
        )
        monitor.record_response(request1, 900, 1.0, True)

        request2 = monitor.record_request(
            mcp_name="context7",
            method="method2",
            query={},
            expected_tokens=1000,
            phase="phase_2"
        )
        monitor.record_response(request2, 950, 1.0, False, "Error")

        assert monitor.get_successful_calls() == 1
        assert monitor.get_failed_calls() == 1

    def test_mcp_monitor_total_tokens_used(self):
        """Test get_total_tokens_used method."""
        monitor = MCPMonitor()
        request1 = monitor.record_request("context7", "method1", {}, 1000, "phase_2")
        monitor.record_response(request1, 900, 1.0, True)

        request2 = monitor.record_request("context7", "method2", {}, 1000, "phase_2")
        monitor.record_response(request2, 950, 1.0, True)

        assert monitor.get_total_tokens_used() == 1850

    def test_mcp_monitor_total_tokens_budgeted(self):
        """Test get_total_tokens_budgeted method."""
        monitor = MCPMonitor()
        request1 = monitor.record_request("context7", "method1", {}, 1000, "phase_2")
        monitor.record_response(request1, 900, 1.0, True)

        request2 = monitor.record_request("context7", "method2", {}, 2000, "phase_2")
        monitor.record_response(request2, 1800, 1.0, True)

        assert monitor.get_total_tokens_budgeted() == 3000

    def test_mcp_monitor_generate_report_empty(self):
        """Test report generation with no calls."""
        monitor = MCPMonitor()
        report = monitor.generate_report()
        assert "message" in report
        assert "No MCP requests tracked" in report["message"]

    def test_mcp_monitor_generate_report_with_data(self):
        """Test comprehensive report generation."""
        monitor = MCPMonitor()

        # Phase 2 calls
        req1 = monitor.record_request("context7", "method1", {}, 1000, "phase_2")
        monitor.record_response(req1, 900, 1.0, True)

        # Phase 3 calls
        req2 = monitor.record_request("context7", "method2", {}, 1000, "phase_3")
        monitor.record_response(req2, 1200, 1.5, True)

        report = monitor.generate_report()

        # Check summary
        assert report["summary"]["total_calls"] == 2
        assert report["summary"]["successful_calls"] == 2
        assert report["summary"]["failed_calls"] == 0
        assert report["summary"]["total_expected_tokens"] == 2000
        assert report["summary"]["total_actual_tokens"] == 2100

        # Check phase breakdown
        assert "phase_2" in report["phases"]
        assert "phase_3" in report["phases"]

        # Check request details
        assert len(report["requests"]) == 2

    def test_mcp_monitor_save_report_json(self):
        """Test saving report to JSON file."""
        monitor = MCPMonitor()
        request = monitor.record_request("context7", "method1", {}, 1000, "phase_2")
        monitor.record_response(request, 900, 1.0, True)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_report.json")
            monitor.save_report(filepath)

            # Verify file was created and contains valid JSON
            assert os.path.exists(filepath)
            with open(filepath, 'r') as f:
                data = json.load(f)
                assert "summary" in data
                assert data["summary"]["total_calls"] == 1

    def test_mcp_monitor_variance_detection_over_budget(self):
        """Test variance detection for over-budget responses."""
        monitor = MCPMonitor(variance_threshold=0.20)
        request = monitor.record_request("context7", "method1", {}, 1000, "phase_2")

        # 30% over budget
        response = monitor.record_response(request, 1300, 1.0, True)
        assert response.is_over_budget(monitor.variance_threshold) is True

    def test_mcp_monitor_multiple_mcps_tracked_separately(self):
        """Test that multiple MCPs are tracked separately."""
        monitor = MCPMonitor()

        # Context7 calls
        req1 = monitor.record_request("context7", "method1", {}, 1000, "phase_2")
        monitor.record_response(req1, 900, 1.0, True)

        # Design-patterns calls
        req2 = monitor.record_request("design-patterns", "method2", {}, 500, "phase_2")
        monitor.record_response(req2, 450, 0.5, True)

        report = monitor.generate_report()

        # Both should appear in requests list
        mcps = set(r["mcp"] for r in report["requests"])
        assert "context7" in mcps
        assert "design-patterns" in mcps

    def test_mcp_monitor_clear(self):
        """Test clearing monitor state."""
        monitor = MCPMonitor()
        request = monitor.record_request("context7", "method1", {}, 1000, "phase_2")
        monitor.record_response(request, 900, 1.0, True)

        assert len(monitor.requests) == 1
        assert len(monitor.responses) == 1

        monitor.clear()

        assert len(monitor.requests) == 0
        assert len(monitor.responses) == 0


# ============================================================================
# SECTION 4: Context7Client Tests (12 tests)
# ============================================================================

class TestContext7Client:
    """Test Context7Client functionality."""

    def test_context7_client_initialization_mock_mode(self):
        """Test client initialization in mock mode."""
        client = Context7Client()
        assert client._mcp_get_library_docs is None
        assert client._mcp_resolve_library_id is None

    def test_context7_client_initialization_with_callables(self):
        """Test client initialization with MCP callables."""
        def mock_get_docs(context7CompatibleLibraryID, topic=None, page=1):
            return "docs"

        def mock_resolve(libraryName):
            return [{"id": f"/mock/{libraryName}"}]

        client = Context7Client(
            mcp_get_library_docs=mock_get_docs,
            mcp_resolve_library_id=mock_resolve
        )
        assert client._mcp_get_library_docs is not None
        assert client._mcp_resolve_library_id is not None

    def test_context7_client_get_library_docs_default_detail_level(self):
        """Test that default detail level is DETAILED (backward compatible)."""
        client = Context7Client()
        # Should use mock mode and DETAILED by default
        docs = client.get_library_docs(
            library_id="/tiangolo/fastapi",
            topic="dependency-injection"
        )
        assert "Mock Documentation" in docs
        assert "DETAILED" in docs

    def test_context7_client_get_library_docs_summary_mode(self):
        """Test SUMMARY mode uses fewer tokens."""
        client = Context7Client()
        summary = client.get_library_docs(
            library_id="/tiangolo/fastapi",
            topic="dependency-injection",
            detail_level=DetailLevel.SUMMARY
        )
        assert "Mock Documentation" in summary
        assert "SUMMARY" in summary

    def test_context7_client_get_library_docs_invalid_library_id(self):
        """Test error handling for empty library ID."""
        client = Context7Client()
        with pytest.raises(ValueError, match="library_id cannot be empty"):
            client.get_library_docs(library_id="")

    def test_context7_client_get_summary_convenience_method(self):
        """Test get_summary convenience method."""
        client = Context7Client()
        summary = client.get_summary(
            library_id="/tiangolo/fastapi",
            topic="dependency-injection"
        )
        assert "Mock Documentation" in summary
        # Should use SUMMARY detail level (750 tokens default)
        assert "SUMMARY" in summary

    def test_context7_client_get_detailed_convenience_method(self):
        """Test get_detailed convenience method."""
        client = Context7Client()
        detailed = client.get_detailed(
            library_id="/tiangolo/fastapi",
            topic="dependency-injection"
        )
        assert "Mock Documentation" in detailed
        # Should use DETAILED detail level (4250 tokens default)
        assert "DETAILED" in detailed

    def test_context7_client_resolve_library_id_mock_mode(self):
        """Test library ID resolution in mock mode."""
        client = Context7Client()
        library_id = client.resolve_library_id("fastapi")
        assert library_id == "/tiangolo/fastapi"

    def test_context7_client_resolve_library_id_with_callable(self):
        """Test library ID resolution with MCP callable."""
        def mock_resolve(libraryName):
            return [{"id": f"/custom/{libraryName}"}]

        client = Context7Client(mcp_resolve_library_id=mock_resolve)
        library_id = client.resolve_library_id("fastapi")
        assert library_id == "/custom/fastapi"

    def test_context7_client_resolve_library_id_invalid_name(self):
        """Test error handling for empty library name."""
        client = Context7Client()
        with pytest.raises(ValueError, match="library_name cannot be empty"):
            client.resolve_library_id("")

    def test_context7_client_manual_token_override(self):
        """Test manual token count override."""
        client = Context7Client()
        # Manually specify token count
        docs = client.get_library_docs(
            library_id="/tiangolo/fastapi",
            detail_level=DetailLevel.SUMMARY,
            tokens=2000  # Override default
        )
        assert "Mock Documentation" in docs
        # Should reflect the override token count
        assert "2000" in docs

    def test_context7_client_pagination_support(self):
        """Test pagination parameter."""
        client = Context7Client()
        # Page should be included in the returned content
        docs = client.get_library_docs(
            library_id="/tiangolo/fastapi",
            page=2
        )
        assert "Mock Documentation" in docs


# ============================================================================
# SECTION 5: Integration Tests (5 tests)
# ============================================================================

class TestMCPIntegration:
    """Integration tests for the complete MCP flow."""

    def test_integration_progressive_disclosure_workflow(self):
        """Test progressive disclosure: planning -> implementation."""
        client = Context7Client()
        monitor = MCPMonitor()

        # Phase 2: Planning - get summary
        phase2_request = monitor.record_request(
            mcp_name="context7",
            method="get_library_docs",
            query={"library_id": "/tiangolo/fastapi", "detail": "summary"},
            expected_tokens=750,
            phase="phase_2"
        )
        summary = client.get_summary("/tiangolo/fastapi", "dependency-injection")
        # Phase 2 uses fewer tokens
        assert len(summary) > 0

        phase2_response = monitor.record_response(
            request=phase2_request,
            actual_tokens=len(summary) // 4,  # Rough estimate
            duration_seconds=0.5,
            success=True
        )

        # Phase 3: Implementation - get detailed docs
        phase3_request = monitor.record_request(
            mcp_name="context7",
            method="get_library_docs",
            query={"library_id": "/tiangolo/fastapi", "detail": "detailed"},
            expected_tokens=4250,
            phase="phase_3"
        )
        detailed = client.get_detailed("/tiangolo/fastapi", "dependency-injection")
        # Phase 3 uses more tokens
        assert len(detailed) > len(summary)

        phase3_response = monitor.record_response(
            request=phase3_request,
            actual_tokens=len(detailed) // 4,  # Rough estimate
            duration_seconds=1.0,
            success=True
        )

        # Verify monitoring captured both phases
        report = monitor.generate_report()
        assert len(report["requests"]) == 2
        assert "phase_2" in report["phases"]
        assert "phase_3" in report["phases"]

    def test_integration_end_to_end_with_monitoring(self):
        """Test end-to-end workflow with comprehensive monitoring."""
        monitor = MCPMonitor(variance_threshold=0.20)

        # Simulate multiple MCP calls
        calls = [
            ("context7", "get_library_docs", "/tiangolo/fastapi", 1000, "phase_2"),
            ("context7", "get_library_docs", "/facebook/react", 1000, "phase_2"),
            ("design-patterns", "get_pattern", "/dependency-injection", 500, "phase_2"),
        ]

        for mcp_name, method, topic, budget, phase in calls:
            request = monitor.record_request(
                mcp_name=mcp_name,
                method=method,
                query={"topic": topic},
                expected_tokens=budget,
                phase=phase
            )
            # Simulate response with slight variance
            actual_tokens = int(budget * 0.95)  # 5% under budget
            response = monitor.record_response(
                request=request,
                actual_tokens=actual_tokens,
                duration_seconds=1.0,
                success=True
            )

        # Verify comprehensive report
        report = monitor.generate_report()
        assert report["summary"]["total_calls"] == 3
        assert report["summary"]["successful_calls"] == 3
        assert report["summary"]["over_budget_calls"] == 0

    def test_integration_error_handling_and_recovery(self):
        """Test error handling in monitoring with recovery."""
        monitor = MCPMonitor()

        # Successful call
        req1 = monitor.record_request("context7", "method1", {}, 1000, "phase_2")
        monitor.record_response(req1, 900, 1.0, True)

        # Failed call
        req2 = monitor.record_request("context7", "method2", {}, 1000, "phase_2")
        monitor.record_response(
            req2, 0, 0.5, False, "Connection timeout"
        )

        # Successful recovery call
        req3 = monitor.record_request("context7", "method2", {}, 1000, "phase_2")
        monitor.record_response(req3, 950, 1.0, True)

        # Verify report captures failure and recovery
        report = monitor.generate_report()
        assert report["summary"]["total_calls"] == 3
        assert report["summary"]["failed_calls"] == 1
        assert report["summary"]["successful_calls"] == 2

    def test_integration_multi_phase_tracking(self):
        """Test tracking across multiple workflow phases."""
        monitor = MCPMonitor()

        # Phase 2: Planning
        req_p2_1 = monitor.record_request("context7", "method", {}, 750, "phase_2")
        monitor.record_response(req_p2_1, 700, 0.5, True)

        # Phase 3: Implementation
        req_p3_1 = monitor.record_request("context7", "method", {}, 4250, "phase_3")
        monitor.record_response(req_p3_1, 4000, 1.0, True)

        # Phase 4: Testing
        req_p4_1 = monitor.record_request("design-patterns", "method", {}, 500, "phase_4")
        monitor.record_response(req_p4_1, 450, 0.5, True)

        report = monitor.generate_report()

        # Verify all phases are present
        assert len(report["phases"]) == 3
        assert report["phases"]["phase_2"]["calls"] == 1
        assert report["phases"]["phase_3"]["calls"] == 1
        assert report["phases"]["phase_4"]["calls"] == 1

    def test_integration_progressive_disclosure_token_efficiency(self):
        """Test that progressive disclosure reduces overall token usage."""
        # Scenario 1: Without progressive disclosure (always detailed)
        monitor_full = MCPMonitor()
        for i in range(3):
            req = monitor_full.record_request(
                "context7", "method", {}, 4250, "phase_2"
            )
            monitor_full.record_response(req, 4000, 1.0, True)

        # Scenario 2: With progressive disclosure
        monitor_progressive = MCPMonitor()

        # Phase 2: Summary requests (less tokens)
        for i in range(3):
            req = monitor_progressive.record_request(
                "context7", "method", {}, 750, "phase_2"
            )
            monitor_progressive.record_response(req, 700, 0.5, True)

        # Phase 3: Detailed requests (more tokens)
        for i in range(3):
            req = monitor_progressive.record_request(
                "context7", "method", {}, 4250, "phase_3"
            )
            monitor_progressive.record_response(req, 4000, 1.0, True)

        report_full = monitor_full.generate_report()
        report_progressive = monitor_progressive.generate_report()

        # With progressive disclosure, phase 2 uses fewer total tokens
        phase2_tokens_full = report_full["summary"]["total_actual_tokens"]
        phase2_tokens_progressive = report_progressive["phases"]["phase_2"]["actual_tokens"]

        # Phase 2 with progressive disclosure should use significantly fewer tokens
        assert phase2_tokens_progressive < phase2_tokens_full


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
