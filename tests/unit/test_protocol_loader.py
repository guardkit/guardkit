"""
Unit tests for protocol loader module.

Tests protocol loading utilities for AutoBuild prompt builders, including
caching, error handling, and protocol content validation.

Coverage Target: >=85%
Test Count: 30+ tests
"""

import re
import sys
from pathlib import Path

import pytest

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.prompts import clear_cache, load_protocol


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear protocol cache before each test."""
    clear_cache()
    yield
    clear_cache()


# ============================================================================
# Test Load Protocol Functionality
# ============================================================================


class TestLoadProtocol:
    """Test protocol loading functionality."""

    def test_load_execution_protocol_returns_content(self):
        """Test loading execution protocol returns non-empty string."""
        content = load_protocol("autobuild_execution_protocol")
        assert isinstance(content, str)
        assert len(content) > 0
        assert "Phase 3" in content

    def test_load_design_protocol_returns_content(self):
        """Test loading design protocol returns non-empty string."""
        content = load_protocol("autobuild_design_protocol")
        assert isinstance(content, str)
        assert len(content) > 0
        assert "Phase 1.5" in content

    def test_protocol_not_found_raises_file_not_found_error(self):
        """Test that loading nonexistent protocol raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_protocol("nonexistent_protocol")

        error_msg = str(exc_info.value)
        assert "nonexistent_protocol" in error_msg
        assert "not found" in error_msg.lower()

    def test_error_message_lists_available_protocols(self):
        """Test that FileNotFoundError message lists available protocol names."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_protocol("missing_protocol")

        error_msg = str(exc_info.value)
        assert "Available protocols:" in error_msg
        assert "autobuild_execution_protocol" in error_msg
        assert "autobuild_design_protocol" in error_msg

    def test_caching_returns_same_object(self):
        """Test that second load returns cached content (same string object)."""
        first_load = load_protocol("autobuild_execution_protocol")
        second_load = load_protocol("autobuild_execution_protocol")

        # Same content
        assert first_load == second_load
        # Same object (cached)
        assert first_load is second_load

    def test_clear_cache_forces_reload(self):
        """Test that clear_cache() causes next load to read from disk."""
        first_load = load_protocol("autobuild_execution_protocol")
        clear_cache()
        second_load = load_protocol("autobuild_execution_protocol")

        # Same content but different objects (reloaded)
        assert first_load == second_load
        assert first_load is not second_load


# ============================================================================
# Test Execution Protocol Content
# ============================================================================


class TestExecutionProtocolContent:
    """Validate execution protocol contains required sections."""

    @pytest.fixture
    def execution_protocol(self):
        """Load execution protocol once for content tests."""
        return load_protocol("autobuild_execution_protocol")

    def test_contains_phase_3(self, execution_protocol):
        """Execution protocol must contain Phase 3 implementation section."""
        assert "Phase 3" in execution_protocol
        assert "Implementation" in execution_protocol

    def test_contains_phase_4(self, execution_protocol):
        """Execution protocol must contain Phase 4 testing section."""
        assert "Phase 4" in execution_protocol
        assert "Testing" in execution_protocol

    def test_contains_phase_4_5(self, execution_protocol):
        """Execution protocol must contain Phase 4.5 fix loop."""
        assert "Phase 4.5" in execution_protocol
        assert "Test Enforcement Loop" in execution_protocol or "Fix Loop" in execution_protocol

    def test_contains_phase_5(self, execution_protocol):
        """Execution protocol must contain Phase 5 code review."""
        assert "Phase 5" in execution_protocol
        assert "Code Review" in execution_protocol

    def test_contains_player_report_schema(self, execution_protocol):
        """Execution protocol must contain PLAYER_REPORT_SCHEMA."""
        assert "PLAYER_REPORT_SCHEMA" in execution_protocol

    def test_contains_quality_gate_thresholds(self, execution_protocol):
        """Execution protocol must contain all quality gate threshold values."""
        # Coverage thresholds
        assert "80%" in execution_protocol  # Line coverage
        assert "75%" in execution_protocol  # Branch coverage
        # Test pass threshold
        assert "100%" in execution_protocol
        # Compilation check
        assert "Compilation" in execution_protocol or "compilation" in execution_protocol

    def test_contains_anti_stub_rules(self, execution_protocol):
        """Execution protocol must contain anti-stub rules with stub definition."""
        assert "Anti-Stub" in execution_protocol or "stub" in execution_protocol.lower()
        # Check for key stub patterns
        assert "pass" in execution_protocol
        assert "NotImplementedError" in execution_protocol or "not implemented" in execution_protocol.lower()

    def test_contains_file_count_constraints(self, execution_protocol):
        """Execution protocol must reference minimal/standard/comprehensive levels."""
        assert "minimal" in execution_protocol.lower()
        assert "standard" in execution_protocol.lower()
        assert "comprehensive" in execution_protocol.lower()

    def test_player_report_has_required_fields(self, execution_protocol):
        """Verify all PLAYER_REPORT_SCHEMA fields appear in the protocol."""
        required_fields = [
            "task_id",
            "turn",
            "files_modified",
            "files_created",
            "tests_written",
            "tests_run",
            "tests_passed",
            "implementation_notes",
            "concerns",
            "requirements_addressed",
            "requirements_remaining"
        ]

        for field in required_fields:
            assert field in execution_protocol, f"Missing required field: {field}"

    def test_size_within_limit(self, execution_protocol):
        """Execution protocol must be <= 20KB (20480 bytes)."""
        size = len(execution_protocol.encode("utf-8"))
        assert size <= 20480, f"Execution protocol size {size} exceeds 20KB limit (20480 bytes)"


# ============================================================================
# Test Design Protocol Content
# ============================================================================


class TestDesignProtocolContent:
    """Validate design protocol contains required sections."""

    @pytest.fixture
    def design_protocol(self):
        """Load design protocol once for content tests."""
        return load_protocol("autobuild_design_protocol")

    def test_contains_phase_1_5(self, design_protocol):
        """Design protocol must contain Phase 1.5 task context loading."""
        assert "Phase 1.5" in design_protocol
        assert "task" in design_protocol.lower()

    def test_contains_phase_2(self, design_protocol):
        """Design protocol must contain Phase 2 implementation planning."""
        assert "Phase 2" in design_protocol
        assert "Implementation Planning" in design_protocol or "planning" in design_protocol.lower()

    def test_contains_phase_2_5b(self, design_protocol):
        """Design protocol must contain Phase 2.5B architectural review."""
        assert "Phase 2.5" in design_protocol or "2.5B" in design_protocol
        assert "Architectural Review" in design_protocol or "architectural" in design_protocol.lower()

    def test_contains_phase_2_7(self, design_protocol):
        """Design protocol must contain Phase 2.7 complexity evaluation."""
        assert "Phase 2.7" in design_protocol or "2.7" in design_protocol
        assert "Complexity" in design_protocol

    def test_contains_phase_2_8(self, design_protocol):
        """Design protocol must contain Phase 2.8 design checkpoint."""
        assert "Phase 2.8" in design_protocol or "2.8" in design_protocol
        assert "checkpoint" in design_protocol.lower() or "Checkpoint" in design_protocol

    def test_contains_skipped_phases(self, design_protocol):
        """Design protocol must document skipped phases (1.6, 2.1, 2.5A)."""
        # Look for documentation of skipped phases
        assert "skip" in design_protocol.lower() or "Skipped" in design_protocol
        # Should mention at least one skipped phase number
        assert "1.6" in design_protocol or "2.1" in design_protocol or "2.5A" in design_protocol

    def test_contains_output_markers(self, design_protocol):
        """Design protocol must contain parseable output marker formats."""
        # Plan saved marker
        assert "Plan saved to:" in design_protocol
        # Complexity marker
        assert "Complexity:" in design_protocol
        # Checkpoint markers
        assert "checkpoint approved" in design_protocol.lower() or "DESIGN_APPROVED" in design_protocol

    def test_size_within_limit(self, design_protocol):
        """Design protocol must be <= 15360 bytes (15KB)."""
        size = len(design_protocol.encode("utf-8"))
        assert size <= 15360, f"Design protocol size {size} exceeds 15KB limit (15360 bytes)"


# ============================================================================
# Test Output Marker Compatibility
# ============================================================================


class TestOutputMarkerCompatibility:
    """Verify output markers match TaskWorkStreamParser regex patterns."""

    # Patterns from agent_invoker.py
    PHASE_MARKER_PATTERN = re.compile(r"Phase\s+(\d+(?:\.\d+)?)[:\s]+(.+)")
    TESTS_PASSED_PATTERN = re.compile(r"(\d+)\s+tests?\s+passed", re.IGNORECASE)
    TESTS_FAILED_PATTERN = re.compile(r"(\d+)\s+tests?\s+failed", re.IGNORECASE)
    COVERAGE_PATTERN = re.compile(r"[Cc]overage[:\s]+(\d+(?:\.\d+)?)%")
    QUALITY_GATES_PASSED_PATTERN = re.compile(
        r"[Qq]uality\s+gates[:\s]*PASSED|all\s+quality\s+gates\s+passed",
        re.IGNORECASE
    )
    ARCH_SCORE_PATTERN = re.compile(
        r"[Aa]rchitectural.*?[Ss]core[:\s]+(\d+)(?:/100)?",
        re.IGNORECASE
    )

    @pytest.fixture
    def execution_protocol(self):
        """Load execution protocol."""
        return load_protocol("autobuild_execution_protocol")

    @pytest.fixture
    def design_protocol(self):
        """Load design protocol."""
        return load_protocol("autobuild_design_protocol")

    def test_phase_marker_format_matches(self, execution_protocol, design_protocol):
        """Output markers like 'Phase 3: Implementation' match PHASE_MARKER_PATTERN."""
        # Test execution protocol
        match = self.PHASE_MARKER_PATTERN.search("Phase 3: Implementation")
        assert match is not None
        assert match.group(1) == "3"

        # Test with decimal phases
        match = self.PHASE_MARKER_PATTERN.search("Phase 4.5: Test Enforcement Loop")
        assert match is not None
        assert match.group(1) == "4.5"

        # Verify protocol contains phase markers
        assert self.PHASE_MARKER_PATTERN.search(execution_protocol) is not None
        assert self.PHASE_MARKER_PATTERN.search(design_protocol) is not None

    def test_coverage_format_matches(self, execution_protocol):
        """'Coverage: N.N%' format matches COVERAGE_PATTERN."""
        # Test various formats with actual numbers
        assert self.COVERAGE_PATTERN.search("Coverage: 85.7%") is not None
        assert self.COVERAGE_PATTERN.search("coverage: 80%") is not None
        assert self.COVERAGE_PATTERN.search("Coverage:90.5%") is not None

        # Verify protocol contains coverage format specification
        # The protocol contains "Coverage: N.N%" as a template, not actual numbers
        assert "Coverage:" in execution_protocol
        # Check that the table references coverage thresholds
        assert "80%" in execution_protocol  # Line coverage threshold

    def test_quality_gates_format_matches(self, execution_protocol):
        """'Quality gates: PASSED' matches QUALITY_GATES_PASSED_PATTERN."""
        assert self.QUALITY_GATES_PASSED_PATTERN.search("Quality gates: PASSED") is not None
        assert self.QUALITY_GATES_PASSED_PATTERN.search("quality gates: PASSED") is not None
        assert self.QUALITY_GATES_PASSED_PATTERN.search("All quality gates passed") is not None

        # Verify protocol contains quality gates references
        assert "Quality gates" in execution_protocol or "quality gates" in execution_protocol

    def test_arch_score_format_matches(self, design_protocol):
        """'Architectural Score: N/100' matches ARCH_SCORE_PATTERN."""
        assert self.ARCH_SCORE_PATTERN.search("Architectural Score: 85/100") is not None
        assert self.ARCH_SCORE_PATTERN.search("architectural score: 90") is not None
        assert self.ARCH_SCORE_PATTERN.search("Architectural Score:75/100") is not None

        # Verify protocol contains arch score references
        assert self.ARCH_SCORE_PATTERN.search(design_protocol) is not None

    def test_complexity_format_matches(self, design_protocol):
        """'Complexity: N/10' is parseable."""
        # Simple pattern for complexity
        complexity_pattern = re.compile(r"Complexity:\s*(\d+)/10")

        assert complexity_pattern.search("Complexity: 5/10") is not None
        assert complexity_pattern.search("Complexity:8/10") is not None

        # Verify protocol contains complexity format
        assert complexity_pattern.search(design_protocol) is not None


# ============================================================================
# Test Total Protocol Size
# ============================================================================


class TestTotalProtocolSize:
    """Verify total combined size constraint."""

    def test_combined_size_between_25_and_35_kb(self):
        """Combined protocol files must be 25-35KB total."""
        execution = load_protocol("autobuild_execution_protocol")
        design = load_protocol("autobuild_design_protocol")

        execution_size = len(execution.encode("utf-8"))
        design_size = len(design.encode("utf-8"))
        total_size = execution_size + design_size

        # 25KB = 25600 bytes, 35KB = 35840 bytes
        assert 25600 <= total_size <= 35840, (
            f"Combined protocol size {total_size} bytes is outside 25-35KB range. "
            f"Execution: {execution_size}, Design: {design_size}"
        )


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
