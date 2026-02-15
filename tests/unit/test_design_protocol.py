"""
Unit tests for design_protocol module.

Tests the inline design phase execution protocol builder that replaces
the /task-work --design-only skill invocation (TASK-POF-003).

Coverage Target: >=85%
Test Count: 12+ tests
"""

import sys
from pathlib import Path

import pytest

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.quality_gates.design_protocol import (
    MAX_PROTOCOL_SIZE,
    build_inline_design_protocol,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def worktree(tmp_path):
    """Create a temporary worktree directory."""
    wt = tmp_path / "worktrees" / "TASK-001"
    wt.mkdir(parents=True)
    return wt


# ============================================================================
# Test Protocol Content
# ============================================================================


class TestProtocolContent:
    """Test that the inline protocol includes required content."""

    def test_includes_task_id(self, worktree):
        """Test task ID appears in the protocol."""
        protocol = build_inline_design_protocol("TASK-ABC-123", {}, worktree)

        assert "TASK-ABC-123" in protocol

    def test_includes_phase_15_instructions(self, worktree):
        """Test Phase 1.5 (task loading) instructions are present."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert "Phase 1.5" in protocol
        assert "task file" in protocol.lower()

    def test_includes_phase_2_instructions(self, worktree):
        """Test Phase 2 (implementation planning) instructions are present."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert "Implementation Planning" in protocol
        assert "implementation plan" in protocol.lower()

    def test_includes_phase_27_instructions(self, worktree):
        """Test Phase 2.7 (complexity evaluation) instructions are present."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert "Complexity" in protocol

    def test_includes_phase_28_instructions(self, worktree):
        """Test Phase 2.8 (checkpoint) instructions are present."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert "Phase 2.8" in protocol or "checkpoint" in protocol.lower()


# ============================================================================
# Test Output Markers
# ============================================================================


class TestOutputMarkers:
    """Test that the protocol instructs the agent to output parseable markers."""

    def test_plan_save_marker(self, worktree):
        """Test 'Plan saved to:' marker is in protocol."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert "Plan saved to:" in protocol

    def test_plan_path_in_marker(self, worktree):
        """Test plan path uses .claude/task-plans/ convention."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert ".claude/task-plans/TASK-001-implementation-plan.md" in protocol

    def test_complexity_marker(self, worktree):
        """Test 'Complexity: N/10' marker format is specified."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert "Complexity:" in protocol
        assert "/10" in protocol

    def test_checkpoint_approved_marker(self, worktree):
        """Test checkpoint approved marker is in protocol."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert "checkpoint approved" in protocol.lower()

    def test_design_approved_state_marker(self, worktree):
        """Test DESIGN_APPROVED state marker is in protocol."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert "DESIGN_APPROVED" in protocol

    def test_arch_score_marker_when_included(self, worktree):
        """Test architectural score markers when Phase 2.5B is included."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert "Architectural Score:" in protocol
        assert "SOLID:" in protocol
        assert "DRY:" in protocol
        assert "YAGNI:" in protocol


# ============================================================================
# Test Architectural Review Control
# ============================================================================


class TestArchReviewControl:
    """Test Phase 2.5B inclusion/exclusion based on options."""

    def test_arch_review_included_by_default(self, worktree):
        """Test Phase 2.5B is included by default."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert "Architectural Review" in protocol
        assert "SOLID" in protocol

    def test_arch_review_excluded_with_skip_flag(self, worktree):
        """Test Phase 2.5B is excluded when skip_arch_review is True."""
        protocol = build_inline_design_protocol(
            "TASK-001", {"skip_arch_review": True}, worktree
        )

        assert "Phase 2.5B" not in protocol
        assert "Architectural Review" not in protocol

    def test_arch_review_excluded_markers_not_present(self, worktree):
        """Test SOLID/DRY/YAGNI markers are absent when arch review skipped."""
        protocol = build_inline_design_protocol(
            "TASK-001", {"skip_arch_review": True}, worktree
        )

        assert "SOLID" not in protocol
        assert "DRY" not in protocol
        assert "YAGNI" not in protocol


# ============================================================================
# Test Documentation Level
# ============================================================================


class TestDocsLevel:
    """Test documentation level embedding in protocol."""

    def test_default_docs_level_is_minimal(self, worktree):
        """Test default documentation level is minimal."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert "minimal" in protocol

    def test_custom_docs_level(self, worktree):
        """Test custom documentation level is embedded."""
        protocol = build_inline_design_protocol(
            "TASK-001", {"docs": "comprehensive"}, worktree
        )

        assert "comprehensive" in protocol

    def test_standard_docs_level(self, worktree):
        """Test standard documentation level is embedded."""
        protocol = build_inline_design_protocol(
            "TASK-001", {"docs": "standard"}, worktree
        )

        assert "standard" in protocol


# ============================================================================
# Test Size Constraint
# ============================================================================


class TestSizeConstraint:
    """Test protocol size stays within the 20KB limit."""

    def test_protocol_within_20kb(self, worktree):
        """Test basic protocol is within 20KB."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        size = len(protocol.encode("utf-8"))
        assert size <= MAX_PROTOCOL_SIZE, f"Protocol size {size} exceeds {MAX_PROTOCOL_SIZE}"

    def test_protocol_with_all_options_within_20kb(self, worktree):
        """Test protocol with all options enabled stays within 20KB."""
        protocol = build_inline_design_protocol(
            "TASK-VERY-LONG-ID-001",
            {"autobuild_mode": True, "docs": "comprehensive"},
            worktree,
        )

        size = len(protocol.encode("utf-8"))
        assert size <= MAX_PROTOCOL_SIZE, f"Protocol size {size} exceeds {MAX_PROTOCOL_SIZE}"

    def test_protocol_without_arch_review_is_smaller(self, worktree):
        """Test skipping arch review reduces protocol size."""
        full = build_inline_design_protocol("TASK-001", {}, worktree)
        slim = build_inline_design_protocol(
            "TASK-001", {"skip_arch_review": True}, worktree
        )

        assert len(slim) < len(full)


# ============================================================================
# Test Not a Skill Invocation
# ============================================================================


class TestNotSkillInvocation:
    """Test that the protocol is NOT a /task-work skill invocation."""

    def test_does_not_start_with_slash_command(self, worktree):
        """Test protocol does not start with /task-work."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert not protocol.strip().startswith("/task-work")

    def test_does_not_contain_design_only_flag(self, worktree):
        """Test protocol does not contain --design-only flag."""
        protocol = build_inline_design_protocol("TASK-001", {}, worktree)

        assert "--design-only" not in protocol

    def test_does_not_contain_autobuild_mode_flag(self, worktree):
        """Test protocol does not contain --autobuild-mode flag."""
        protocol = build_inline_design_protocol(
            "TASK-001", {"autobuild_mode": True}, worktree
        )

        assert "--autobuild-mode" not in protocol


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
