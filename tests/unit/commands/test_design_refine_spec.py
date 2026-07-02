"""
Unit tests for /design-refine command specification.

Validates that the design-refine.md command specification exists and contains
all required sections, acceptance criteria coverage, and correct references
to dependency modules (fleet-memory MCP tools, DesignWriter, entity dataclasses).

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

    def test_spec_references_memory_search_for_disambiguation(self, spec_content: str) -> None:
        """Spec must reference fleet-memory search for disambiguation."""
        assert "memory_search" in spec_content or "mcp__fleet_memory__memory_search" in spec_content, (
            "Spec must reference fleet-memory memory_search for disambiguation"
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

    def test_spec_disambiguation_scoped_to_design_tag(self, spec_content: str) -> None:
        """Spec must scope disambiguation search to the design domain tag."""
        assert '"design"' in spec_content, (
            "Spec must scope fleet-memory disambiguation search to domain_tags=[design]"
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

    def test_spec_queries_feature_spec_artefacts(self, spec_content: str) -> None:
        """Spec must search fleet-memory for feature-spec artefacts."""
        assert "feature_spec" in spec_content or "feature spec" in spec_content.lower(), (
            "Spec must reference fleet-memory feature-spec staleness search"
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
# AC-006: Staleness flagging on downstream fleet-memory artefacts
# ============================================================================


class TestDownstreamStaleness:
    """Validates AC-006: Staleness flagging on downstream fleet-memory artefacts."""

    def test_spec_describes_downstream_staleness(self, spec_content: str) -> None:
        """Spec must describe flagging downstream artefacts as stale."""
        content_lower = spec_content.lower()
        has_downstream = "downstream" in content_lower
        assert has_downstream, (
            "Spec must describe staleness flagging on downstream fleet-memory artefacts"
        )

    def test_spec_flags_affected_nodes(self, spec_content: str) -> None:
        """Spec must flag nodes that reference changed entities."""
        content_lower = spec_content.lower()
        has_flag = "flag" in content_lower and "stale" in content_lower
        assert has_flag, (
            "Spec must describe flagging affected nodes as stale"
        )


# ============================================================================
# AC-007: Fleet-memory integration (design / api_contract seeding)
# ============================================================================


class TestFleetMemoryIntegration:
    """Validates AC-007: Fleet-memory integration with typed payloads."""

    def test_spec_seeds_design_domain_tag(self, spec_content: str) -> None:
        """Spec must seed design artefacts with the design domain tag."""
        assert '"design"' in spec_content, (
            "Spec must reference the design domain_tag for fleet-memory seeding"
        )

    def test_spec_seeds_api_contract_domain_tag(self, spec_content: str) -> None:
        """Spec must seed API contracts with the api_contract domain tag."""
        assert "api_contract" in spec_content, (
            "Spec must reference the api_contract domain_tag for contract seeding"
        )

    def test_spec_uses_typed_payloads(self, spec_content: str) -> None:
        """Spec must seed via typed payloads (adr for DDRs, document for artefacts)."""
        assert '"payload_type": "adr"' in spec_content, (
            "Spec must reference the adr payload_type for DDRs"
        )
        assert '"payload_type": "document"' in spec_content, (
            "Spec must reference the document payload_type for contracts and models"
        )

    def test_spec_references_memory_write_payload(self, spec_content: str) -> None:
        """Spec must reference the fleet-memory write tool for persistence."""
        assert "mcp__fleet_memory__memory_write_payload" in spec_content, (
            "Spec must reference mcp__fleet_memory__memory_write_payload for seeding"
        )

    def test_spec_supersession_re_writes_old_and_links_new(self, spec_content: str) -> None:
        """Spec must supersede via a status re-write plus a supersedes reference."""
        assert '"status": "superseded"' in spec_content, (
            "Spec must re-write the old DDR payload with status superseded"
        )
        assert "supersedes" in spec_content, (
            "Spec must write the new DDR payload with a supersedes reference"
        )


# ============================================================================
# AC-008: Graceful degradation when fleet-memory unavailable
# ============================================================================


class TestGracefulDegradation:
    """Validates AC-008: Graceful degradation when fleet-memory unavailable."""

    def test_spec_has_graceful_degradation(self, spec_content: str) -> None:
        """Spec must have a graceful degradation section."""
        content_lower = spec_content.lower()
        assert "graceful degradation" in content_lower or "fleet-memory unavailable" in content_lower, (
            "Spec must describe graceful degradation when fleet-memory is unavailable"
        )

    def test_spec_continues_without_memory(self, spec_content: str) -> None:
        """Spec must allow operation without fleet-memory (markdown-only fallback)."""
        content_lower = spec_content.lower()
        has_fallback = (
            "without persistence" in content_lower
            or "markdown" in content_lower
        )
        assert has_fallback, (
            "Spec must describe continuing with markdown artefacts when fleet-memory unavailable"
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

    def test_spec_queries_architecture_adrs_for_contradiction(self, spec_content: str) -> None:
        """Spec must search fleet-memory architecture ADRs for contradiction checks."""
        assert 'payload_types=["adr"]' in spec_content or '"architecture"' in spec_content, (
            "Spec must reference fleet-memory ADR search (adr payload / architecture tag) for contradiction checks"
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

    def test_spec_handles_memory_errors(self, spec_content: str) -> None:
        """Spec must handle fleet-memory-specific errors."""
        content_lower = spec_content.lower()
        has_memory_error = "fleet-memory" in content_lower and "error" in content_lower
        assert has_memory_error, (
            "Spec must describe handling fleet-memory errors"
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

    def test_spec_references_fleet_memory_access(self, spec_content: str) -> None:
        """Spec must reference the fleet-memory access path (MCP tool / preamble)."""
        assert "mcp__fleet_memory__memory_write_payload" in spec_content or "memory-preamble" in spec_content, (
            "Spec must reference fleet-memory access (MCP write tool or memory-preamble)"
        )

    def test_spec_has_no_graphiti_references(self, spec_content: str) -> None:
        """Spec must not reference the removed Graphiti backend (case-insensitive)."""
        assert "graphiti" not in spec_content.lower(), (
            "Spec must not contain any Graphiti references after the fleet-memory cutover"
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
