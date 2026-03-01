"""
Unit tests for /design-refine command specification.

Validates that the design-refine.md command specification exists and contains
all required sections, acceptance criteria coverage, and correct references
to dependency modules (SystemDesignGraphiti, DesignWriter, entity dataclasses).

These tests treat the command spec as a structured document with mandatory
sections. Each test validates a specific acceptance criterion from TASK-SAD-009.

Coverage Target: >=80%
"""

import re
import pytest
from pathlib import Path


# ============================================================================
# Fixtures
# ============================================================================

SPEC_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "commands"
    / "design-refine.md"
)


@pytest.fixture
def spec_content() -> str:
    """Load the design-refine command specification content."""
    assert SPEC_PATH.exists(), f"Command spec not found at {SPEC_PATH}"
    return SPEC_PATH.read_text()


# ============================================================================
# AC-001: Disambiguation flow (identical pattern to /arch-refine)
# ============================================================================


class TestDisambiguationFlow:
    """Validates AC-001: Disambiguation flow using semantic search."""

    def test_spec_references_search_design_context(self, spec_content: str) -> None:
        """Spec must reference SystemDesignGraphiti.search_design_context()."""
        assert "search_design_context" in spec_content, (
            "Spec must reference search_design_context() for disambiguation"
        )

    def test_spec_presents_top_matches(self, spec_content: str) -> None:
        """Spec must present top 3-5 matches grouped by relevance."""
        content_lower = spec_content.lower()
        has_match_count = (
            "3-5" in spec_content
            or "top 3" in content_lower
            or "top 5" in content_lower
            or "3 to 5" in content_lower
        )
        assert has_match_count, (
            "Spec must present top 3-5 matches grouped by relevance"
        )

    def test_spec_requires_explicit_confirmation(self, spec_content: str) -> None:
        """Spec must require explicit confirmation before any changes applied."""
        content_lower = spec_content.lower()
        has_confirmation = (
            "explicit confirmation" in content_lower
            or "confirm" in content_lower
        )
        assert has_confirmation, (
            "Spec must require explicit confirmation before applying changes"
        )

    def test_spec_references_system_design_graphiti(self, spec_content: str) -> None:
        """Spec must reference SystemDesignGraphiti for disambiguation."""
        assert "SystemDesignGraphiti" in spec_content, (
            "Spec must reference SystemDesignGraphiti class"
        )

    def test_spec_groups_by_relevance(self, spec_content: str) -> None:
        """Spec must describe grouping results by relevance."""
        content_lower = spec_content.lower()
        assert "relevance" in content_lower, (
            "Spec must describe grouping matches by relevance"
        )


# ============================================================================
# AC-002: Temporal superseding for DDRs
# ============================================================================


class TestTemporalSuperseding:
    """Validates AC-002: Temporal superseding for Design Decision Records."""

    def test_spec_describes_ddr_superseding(self, spec_content: str) -> None:
        """Spec must describe DDR temporal superseding mechanism."""
        content_lower = spec_content.lower()
        assert "supersed" in content_lower, (
            "Spec must describe temporal superseding for DDRs"
        )

    def test_spec_sets_existing_ddr_status_to_superseded(self, spec_content: str) -> None:
        """Spec must set existing DDR status to 'superseded'."""
        assert "superseded" in spec_content, (
            "Spec must describe setting existing DDR status to 'superseded'"
        )

    def test_spec_creates_new_ddr_with_supersedes_reference(self, spec_content: str) -> None:
        """Spec must create new DDR with supersedes reference to old DDR."""
        content_lower = spec_content.lower()
        has_supersedes_ref = "supersedes" in content_lower
        assert has_supersedes_ref, (
            "Spec must create new DDR with 'supersedes' reference"
        )

    def test_spec_prior_ddr_remains_queryable(self, spec_content: str) -> None:
        """Spec must keep prior DDR queryable after superseding."""
        content_lower = spec_content.lower()
        has_queryable = (
            "queryable" in content_lower
            or "remains" in content_lower
            or "preserved" in content_lower
        )
        assert has_queryable, (
            "Spec must describe that prior DDR remains queryable"
        )

    def test_spec_references_scan_next_ddr_number(self, spec_content: str) -> None:
        """Spec must reference scan_next_ddr_number for DDR numbering."""
        assert "scan_next_ddr_number" in spec_content, (
            "Spec must reference scan_next_ddr_number helper"
        )


# ============================================================================
# AC-003: API contract update flow
# ============================================================================


class TestAPIContractUpdateFlow:
    """Validates AC-003: API contract update flow with diff and validation."""

    def test_spec_presents_current_contract(self, spec_content: str) -> None:
        """Spec must present the current API contract."""
        content_lower = spec_content.lower()
        has_current = (
            "current contract" in content_lower
            or "existing contract" in content_lower
        )
        assert has_current, (
            "Spec must present the current API contract to the user"
        )

    def test_spec_shows_proposed_changes(self, spec_content: str) -> None:
        """Spec must show proposed changes."""
        content_lower = spec_content.lower()
        assert "proposed change" in content_lower or "proposed" in content_lower, (
            "Spec must show proposed changes to the user"
        )

    def test_spec_shows_diff(self, spec_content: str) -> None:
        """Spec must show a diff between current and proposed contract."""
        content_lower = spec_content.lower()
        assert "diff" in content_lower, (
            "Spec must show a diff between current and proposed contract"
        )

    def test_spec_regenerates_openapi(self, spec_content: str) -> None:
        """Spec must regenerate OpenAPI spec section for affected context."""
        content_lower = spec_content.lower()
        assert "openapi" in content_lower, (
            "Spec must describe regenerating OpenAPI spec section"
        )

    def test_spec_validates_openapi(self, spec_content: str) -> None:
        """Spec must validate updated OpenAPI spec."""
        content_lower = spec_content.lower()
        has_validation = "validate" in content_lower and "openapi" in content_lower
        assert has_validation, (
            "Spec must describe validating the updated OpenAPI spec"
        )


# ============================================================================
# AC-004: Feature spec staleness detection
# ============================================================================


class TestFeatureSpecStaleness:
    """Validates AC-004: Feature spec staleness detection."""

    def test_spec_queries_feature_specs_group(self, spec_content: str) -> None:
        """Spec must query feature_specs group."""
        assert "feature_specs" in spec_content, (
            "Spec must reference feature_specs Graphiti group"
        )

    def test_spec_detects_stale_scenarios(self, spec_content: str) -> None:
        """Spec must flag affected feature specs as potentially stale."""
        content_lower = spec_content.lower()
        has_staleness = "stale" in content_lower or "staleness" in content_lower
        assert has_staleness, (
            "Spec must describe detecting stale feature specs"
        )

    def test_spec_offers_rerun_or_accept_choice(self, spec_content: str) -> None:
        """Spec must offer choice: re-run /feature-spec or accept delta."""
        content_lower = spec_content.lower()
        has_feature_spec_ref = "/feature-spec" in spec_content
        assert has_feature_spec_ref, (
            "Spec must offer choice to re-run /feature-spec on affected areas"
        )

    def test_spec_references_changed_contracts(self, spec_content: str) -> None:
        """Spec must query for scenarios referencing changed API contracts."""
        content_lower = spec_content.lower()
        has_contract_ref = (
            "changed" in content_lower and "contract" in content_lower
        ) or "api contract" in content_lower
        assert has_contract_ref, (
            "Spec must reference changed API contracts for staleness detection"
        )


# ============================================================================
# AC-005: C4 L3 diagram re-review gate
# ============================================================================


class TestC4L3ReviewGate:
    """Validates AC-005: C4 L3 diagram re-review gate."""

    def test_spec_has_c4_review_gate(self, spec_content: str) -> None:
        """Spec must document mandatory C4 L3 review gate."""
        assert "C4" in spec_content, "Spec must reference C4 diagrams"

    def test_spec_requires_mandatory_approval(self, spec_content: str) -> None:
        """Spec must require mandatory approval for revised diagrams."""
        content_lower = spec_content.lower()
        has_approval = "approval" in content_lower or "approve" in content_lower
        assert has_approval, (
            "Spec must require mandatory approval for C4 L3 diagrams"
        )

    def test_spec_generates_revised_diagrams(self, spec_content: str) -> None:
        """Spec must generate revised Component diagrams."""
        content_lower = spec_content.lower()
        has_component = "component" in content_lower and "diagram" in content_lower
        assert has_component, (
            "Spec must describe generating revised Component diagrams"
        )

    def test_spec_presents_diagrams_for_review(self, spec_content: str) -> None:
        """Spec must present diagrams for user review before proceeding."""
        has_approve_pattern = (
            "[A]pprove" in spec_content
            or "[A]ccept" in spec_content
        )
        assert has_approve_pattern, (
            "Spec must present diagrams with [A]pprove / [R]evise interaction"
        )


# ============================================================================
# AC-006: Staleness flagging on downstream Graphiti nodes
# ============================================================================


class TestDownstreamStaleness:
    """Validates AC-006: Staleness flagging on downstream Graphiti nodes."""

    def test_spec_describes_downstream_staleness(self, spec_content: str) -> None:
        """Spec must describe flagging downstream nodes as stale."""
        content_lower = spec_content.lower()
        has_downstream = "downstream" in content_lower
        assert has_downstream, (
            "Spec must describe staleness flagging on downstream Graphiti nodes"
        )

    def test_spec_flags_affected_nodes(self, spec_content: str) -> None:
        """Spec must flag nodes that reference changed entities."""
        content_lower = spec_content.lower()
        has_flag = "flag" in content_lower and "stale" in content_lower
        assert has_flag, (
            "Spec must describe flagging affected nodes as stale"
        )


# ============================================================================
# AC-007: Graphiti integration (project_design and api_contracts groups)
# ============================================================================


class TestGraphitiIntegration:
    """Validates AC-007: Graphiti integration with correct groups."""

    def test_spec_updates_project_design_group(self, spec_content: str) -> None:
        """Spec must update project_design Graphiti group."""
        assert "project_design" in spec_content, (
            "Spec must reference project_design group for Graphiti updates"
        )

    def test_spec_updates_api_contracts_group(self, spec_content: str) -> None:
        """Spec must update api_contracts Graphiti group."""
        assert "api_contracts" in spec_content, (
            "Spec must reference api_contracts group for Graphiti updates"
        )

    def test_spec_uses_upsert_methods(self, spec_content: str) -> None:
        """Spec must use upsert methods for idempotent updates."""
        assert "upsert_design_decision" in spec_content, (
            "Spec must reference upsert_design_decision method"
        )

    def test_spec_references_get_graphiti(self, spec_content: str) -> None:
        """Spec must reference get_graphiti() for client initialization."""
        assert "get_graphiti" in spec_content, (
            "Spec must reference get_graphiti() for Graphiti client initialization"
        )


# ============================================================================
# AC-008: Graceful degradation when Graphiti unavailable
# ============================================================================


class TestGracefulDegradation:
    """Validates AC-008: Graceful degradation when Graphiti unavailable."""

    def test_spec_has_graceful_degradation(self, spec_content: str) -> None:
        """Spec must have a graceful degradation section."""
        content_lower = spec_content.lower()
        assert "graceful degradation" in content_lower or "graphiti unavailable" in content_lower, (
            "Spec must describe graceful degradation when Graphiti is unavailable"
        )

    def test_spec_continues_without_graphiti(self, spec_content: str) -> None:
        """Spec must allow operation without Graphiti (markdown-only fallback)."""
        content_lower = spec_content.lower()
        has_fallback = (
            "without persistence" in content_lower
            or "markdown" in content_lower
        )
        assert has_fallback, (
            "Spec must describe continuing with markdown artefacts when Graphiti unavailable"
        )

    def test_spec_warns_user_about_degradation(self, spec_content: str) -> None:
        """Spec must warn the user about degraded mode."""
        content_lower = spec_content.lower()
        assert "warning" in content_lower or "warn" in content_lower or "WARNING" in spec_content, (
            "Spec must warn the user when operating in degraded mode"
        )


# ============================================================================
# AC-009: Contradiction detection against existing ADRs
# ============================================================================


class TestContradictionDetection:
    """Validates AC-009: Contradiction detection against existing ADRs."""

    def test_spec_has_contradiction_detection(self, spec_content: str) -> None:
        """Spec must describe contradiction detection."""
        content_lower = spec_content.lower()
        assert "contradiction" in content_lower, (
            "Spec must describe contradiction detection"
        )

    def test_spec_queries_project_decisions_group(self, spec_content: str) -> None:
        """Spec must query project_decisions group for existing ADRs."""
        assert "project_decisions" in spec_content, (
            "Spec must reference project_decisions group for ADR checks"
        )

    def test_spec_flags_adr_violations(self, spec_content: str) -> None:
        """Spec must flag proposed changes that contradict existing ADRs."""
        content_lower = spec_content.lower()
        has_adr_check = "adr" in content_lower and (
            "contradict" in content_lower
            or "conflict" in content_lower
            or "violat" in content_lower
        )
        assert has_adr_check, (
            "Spec must flag proposed design changes that contradict existing ADRs"
        )

    def test_spec_offers_resolution_options(self, spec_content: str) -> None:
        """Spec must offer resolution options for contradictions."""
        content_lower = spec_content.lower()
        has_resolution = (
            "revise" in content_lower
            or "supersede" in content_lower
            or "accept" in content_lower
        )
        assert has_resolution, (
            "Spec must offer resolution options for ADR contradictions"
        )


# ============================================================================
# AC-010: Execution protocol section
# ============================================================================


class TestExecutionProtocol:
    """Validates AC-010: Spec has execution protocol section."""

    def test_spec_has_execution_instructions(self, spec_content: str) -> None:
        """Spec must have critical execution instructions for Claude."""
        assert "CRITICAL EXECUTION INSTRUCTIONS" in spec_content or "EXECUTION INSTRUCTIONS" in spec_content, (
            "Spec must contain CRITICAL EXECUTION INSTRUCTIONS section"
        )

    def test_spec_has_step_by_step_instructions(self, spec_content: str) -> None:
        """Spec must contain numbered steps for Claude to follow."""
        assert "Step 1" in spec_content, "Spec must have Step 1 in execution instructions"
        assert "Step 2" in spec_content, "Spec must have Step 2 in execution instructions"

    def test_spec_has_what_not_to_do(self, spec_content: str) -> None:
        """Spec must have a What NOT to Do section."""
        assert "What NOT to Do" in spec_content or "DO NOT" in spec_content, (
            "Spec must have a 'What NOT to Do' section or DO NOT instructions"
        )


# ============================================================================
# AC-011: Error handling section
# ============================================================================


class TestErrorHandling:
    """Validates AC-011: Spec has error handling section."""

    def test_spec_has_error_handling_section(self, spec_content: str) -> None:
        """Spec must have an error handling section."""
        assert "Error Handling" in spec_content or "error handling" in spec_content.lower(), (
            "Spec must have an Error Handling section"
        )

    def test_spec_handles_graphiti_errors(self, spec_content: str) -> None:
        """Spec must handle Graphiti-specific errors."""
        content_lower = spec_content.lower()
        has_graphiti_error = "graphiti" in content_lower and "error" in content_lower
        assert has_graphiti_error, (
            "Spec must describe handling Graphiti errors"
        )

    def test_spec_handles_no_design_context(self, spec_content: str) -> None:
        """Spec must handle case where no design context exists."""
        content_lower = spec_content.lower()
        has_no_context = (
            "no design context" in content_lower
            or "design context" in content_lower
        )
        assert has_no_context, (
            "Spec must handle the case where no design context exists"
        )

    def test_spec_handles_cancelled_session(self, spec_content: str) -> None:
        """Spec must handle user-cancelled sessions."""
        content_lower = spec_content.lower()
        has_cancel = "cancel" in content_lower
        assert has_cancel, (
            "Spec must handle user-cancelled sessions"
        )


# ============================================================================
# Structural quality checks
# ============================================================================


class TestSpecStructure:
    """Validates overall structure matches GuardKit command spec conventions."""

    def test_spec_has_title(self, spec_content: str) -> None:
        """Spec must start with # /design-refine title."""
        assert spec_content.startswith("# /design-refine"), (
            "Spec must start with '# /design-refine' title"
        )

    def test_spec_has_command_syntax(self, spec_content: str) -> None:
        """Spec must have a Command Syntax section."""
        assert "## Command Syntax" in spec_content, (
            "Spec must have a Command Syntax section"
        )

    def test_spec_has_available_flags(self, spec_content: str) -> None:
        """Spec must have an Available Flags section."""
        assert "## Available Flags" in spec_content, (
            "Spec must have an Available Flags section"
        )

    def test_spec_has_execution_flow(self, spec_content: str) -> None:
        """Spec must have an Execution Flow section."""
        assert "Execution Flow" in spec_content, (
            "Spec must have an Execution Flow section"
        )

    def test_spec_has_examples(self, spec_content: str) -> None:
        """Spec must have an Examples section."""
        assert "## Examples" in spec_content or "### Example" in spec_content, (
            "Spec must have an Examples section"
        )

    def test_spec_has_related_commands(self, spec_content: str) -> None:
        """Spec must have a Related Commands section."""
        assert "Related Commands" in spec_content, (
            "Spec must have a Related Commands section"
        )

    def test_spec_references_design_writer(self, spec_content: str) -> None:
        """Spec must reference DesignWriter for output generation."""
        assert "DesignWriter" in spec_content, (
            "Spec must reference DesignWriter class"
        )

    def test_spec_references_design_entities(self, spec_content: str) -> None:
        """Spec must reference relevant design entity dataclasses."""
        assert "DesignDecision" in spec_content, (
            "Spec must reference DesignDecision entity"
        )
        assert "ApiContract" in spec_content, (
            "Spec must reference ApiContract entity"
        )

    def test_spec_minimum_length(self, spec_content: str) -> None:
        """Spec must be comprehensive (>=400 lines)."""
        line_count = len(spec_content.splitlines())
        assert line_count >= 400, (
            f"Spec has only {line_count} lines; expected >=400 for a comprehensive command spec"
        )

    def test_spec_has_python_code_examples(self, spec_content: str) -> None:
        """Spec must contain Python code examples in execution flow."""
        assert "```python" in spec_content, (
            "Spec must contain Python code examples"
        )

    def test_spec_references_prerequisite_gate(self, spec_content: str) -> None:
        """Spec must reference prerequisite check for design context."""
        content_lower = spec_content.lower()
        has_prereq = (
            "prerequisite" in content_lower
            or "has_design_context" in spec_content
        )
        assert has_prereq, (
            "Spec must reference prerequisite check for existing design context"
        )

    def test_spec_references_design_refine_in_pipeline(self, spec_content: str) -> None:
        """Spec must position /design-refine in the command pipeline."""
        assert "/system-design" in spec_content, (
            "Spec must reference /system-design in the pipeline context"
        )
        assert "/system-arch" in spec_content, (
            "Spec must reference /system-arch in the pipeline context"
        )
