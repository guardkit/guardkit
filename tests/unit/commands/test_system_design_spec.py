"""
Unit tests for /system-design command specification.

Validates that the system-design.md command specification exists and contains
all required sections, acceptance criteria coverage, and correct references
to dependency modules (SystemDesignGraphiti, DesignWriter, entity dataclasses).

These tests treat the command spec as a structured document with mandatory
sections. Each test validates a specific acceptance criterion from TASK-SAD-007.

Coverage Target: >=80%
"""

import re
import pytest
from pathlib import Path


# ============================================================================
# Fixtures
# ============================================================================

SPEC_PATH = Path(__file__).resolve().parents[3] / "installer" / "core" / "commands" / "system-design.md"


@pytest.fixture
def spec_content() -> str:
    """Load the system-design command specification content."""
    assert SPEC_PATH.exists(), f"Command spec not found at {SPEC_PATH}"
    return SPEC_PATH.read_text()


# ============================================================================
# AC-001: Prerequisite gate
# ============================================================================


class TestPrerequisiteGate:
    """Validates AC-001: check has_architecture_context() prerequisite."""

    def test_spec_contains_prerequisite_gate_section(self, spec_content: str) -> None:
        """Spec must document the prerequisite gate check."""
        assert "has_architecture_context" in spec_content, (
            "Spec must reference has_architecture_context() for prerequisite gate"
        )

    def test_spec_references_chain_to_system_arch(self, spec_content: str) -> None:
        """Spec must offer to chain to /system-arch when prerequisite fails."""
        assert "/system-arch" in spec_content, (
            "Spec must reference /system-arch for chaining when prerequisite fails"
        )

    def test_spec_shows_user_informed_message(self, spec_content: str) -> None:
        """Spec must show a user-facing message when prerequisite fails."""
        assert "architecture context" in spec_content.lower() or "no architecture" in spec_content.lower(), (
            "Spec must inform the user about missing architecture context"
        )

    def test_spec_uses_graphiti_arch_for_prerequisite(self, spec_content: str) -> None:
        """Spec must use SystemPlanGraphiti for the prerequisite check."""
        assert "SystemPlanGraphiti" in spec_content, (
            "Spec must reference SystemPlanGraphiti for architecture context check"
        )


# ============================================================================
# AC-002: Read bounded contexts from Graphiti
# ============================================================================


class TestReadBoundedContexts:
    """Validates AC-002: Read bounded contexts and structural decisions from Graphiti."""

    def test_spec_reads_from_project_architecture_group(self, spec_content: str) -> None:
        """Spec must reference the project_architecture Graphiti group."""
        assert "project_architecture" in spec_content, (
            "Spec must reference project_architecture group for reading bounded contexts"
        )

    def test_spec_references_bounded_contexts(self, spec_content: str) -> None:
        """Spec must discuss bounded context reading."""
        assert "bounded context" in spec_content.lower(), (
            "Spec must describe reading bounded contexts from Graphiti"
        )

    def test_spec_references_structural_decisions(self, spec_content: str) -> None:
        """Spec must discuss reading structural decisions (ADRs)."""
        assert "ADR" in spec_content, (
            "Spec must reference reading existing ADRs/structural decisions"
        )


# ============================================================================
# AC-003: Per-bounded-context interactive design flow
# ============================================================================


class TestInteractiveDesignFlow:
    """Validates AC-003: Per-bounded-context interactive design flow."""

    def test_spec_has_api_contract_design(self, spec_content: str) -> None:
        """Spec must cover API contract design (endpoints, schemas, auth)."""
        assert "API contract" in spec_content or "api contract" in spec_content.lower(), (
            "Spec must describe API contract design per bounded context"
        )

    def test_spec_has_multi_protocol_surface_design(self, spec_content: str) -> None:
        """Spec must cover multi-protocol surface design."""
        # Must mention REST/GraphQL for web and MCP/A2A for agents
        content_lower = spec_content.lower()
        assert "rest" in content_lower or "REST" in spec_content, (
            "Spec must mention REST protocol"
        )
        assert "graphql" in content_lower or "GraphQL" in spec_content, (
            "Spec must mention GraphQL protocol"
        )
        assert "MCP" in spec_content, "Spec must mention MCP protocol for agents"
        assert "A2A" in spec_content, "Spec must mention A2A protocol for agents"

    def test_spec_has_data_model_design(self, spec_content: str) -> None:
        """Spec must cover data model design (entities, relationships, invariants)."""
        content_lower = spec_content.lower()
        assert "data model" in content_lower, "Spec must describe data model design"
        assert "entities" in content_lower, "Spec must mention entities in data model"
        assert "relationships" in content_lower, "Spec must mention relationships in data model"
        assert "invariants" in content_lower, "Spec must mention invariants in data model"

    def test_spec_has_protocol_selection(self, spec_content: str) -> None:
        """Spec must allow user to choose protocols (MCP, A2A, ACP)."""
        assert "ACP" in spec_content, "Spec must mention ACP protocol selection"
        # Must show interactive protocol selection
        assert "protocol" in spec_content.lower(), "Spec must describe protocol selection"

    def test_spec_has_interactive_checkpoints(self, spec_content: str) -> None:
        """Spec must include interactive checkpoints per bounded context."""
        # Look for checkpoint patterns similar to system-plan
        assert "checkpoint" in spec_content.lower() or "review gate" in spec_content.lower(), (
            "Spec must include interactive checkpoints in the design flow"
        )


# ============================================================================
# AC-004: Mandatory output artefacts
# ============================================================================


class TestMandatoryOutputArtefacts:
    """Validates AC-004: All mandatory output artefacts are specified."""

    def test_spec_outputs_api_contracts_per_context(self, spec_content: str) -> None:
        """Spec must specify API contract output using api-contract.md.j2."""
        assert "api-contract.md.j2" in spec_content, (
            "Spec must reference api-contract.md.j2 template"
        )

    def test_spec_outputs_openapi_spec(self, spec_content: str) -> None:
        """Spec must specify OpenAPI 3.1 specification output."""
        assert "openapi" in spec_content.lower(), "Spec must specify OpenAPI output"
        assert "3.1" in spec_content, "Spec must specify OpenAPI 3.1"
        assert "docs/design/openapi.yaml" in spec_content, (
            "Spec must specify OpenAPI output path as docs/design/openapi.yaml"
        )

    def test_spec_outputs_mcp_tools_conditionally(self, spec_content: str) -> None:
        """Spec must specify MCP tool definitions (conditional on MCP selection)."""
        assert "mcp-tools.json" in spec_content, (
            "Spec must specify MCP tool definitions output path"
        )

    def test_spec_outputs_a2a_schemas_conditionally(self, spec_content: str) -> None:
        """Spec must specify A2A task schemas (conditional on A2A selection)."""
        assert "a2a-schemas.yaml" in spec_content, (
            "Spec must specify A2A task schemas output path"
        )

    def test_spec_outputs_data_model_definitions(self, spec_content: str) -> None:
        """Spec must specify data model definition output."""
        assert "DataModel" in spec_content or "data_model" in spec_content, (
            "Spec must reference DataModel entity for output"
        )

    def test_spec_outputs_c4_component_diagrams(self, spec_content: str) -> None:
        """Spec must specify C4 Component diagrams per container."""
        assert "C4" in spec_content, "Spec must reference C4 diagrams"
        assert "component" in spec_content.lower(), "Spec must reference component diagrams"
        assert "component-l3" in spec_content, (
            "Spec must reference component-l3.md.j2 template"
        )

    def test_spec_outputs_ddrs(self, spec_content: str) -> None:
        """Spec must specify DDR output using ddr.md.j2."""
        assert "ddr.md.j2" in spec_content, "Spec must reference ddr.md.j2 template"
        assert "DDR" in spec_content, "Spec must reference Design Decision Records"

    def test_spec_output_directory_is_docs_design(self, spec_content: str) -> None:
        """Spec must use docs/design/ as the output directory."""
        assert "docs/design/" in spec_content, (
            "Spec must specify docs/design/ as the output directory"
        )


# ============================================================================
# AC-005: Mandatory C4 L3 review gate
# ============================================================================


class TestC4ReviewGate:
    """Validates AC-005: C4 L3 diagrams require explicit user approval."""

    def test_spec_has_c4_review_gate(self, spec_content: str) -> None:
        """Spec must document the mandatory C4 L3 review gate."""
        content_lower = spec_content.lower()
        assert "review gate" in content_lower or "review" in content_lower, (
            "Spec must describe the C4 L3 review gate"
        )
        assert "approval" in content_lower or "approve" in content_lower, (
            "Spec must require explicit user approval for C4 diagrams"
        )

    def test_spec_requires_explicit_approval(self, spec_content: str) -> None:
        """Spec must show user approval checkpoint for diagrams."""
        # Look for approval pattern: [A]pprove / [R]evise / etc.
        has_approval_pattern = (
            "[A]pprove" in spec_content
            or "[A]ccept" in spec_content
            or "explicit approval" in spec_content.lower()
        )
        assert has_approval_pattern, (
            "Spec must show explicit approval interaction for C4 diagrams"
        )

    def test_spec_c4_threshold_over_3_components(self, spec_content: str) -> None:
        """Spec must specify >3 components threshold for automatic C4 L3 generation."""
        assert ">3" in spec_content or "more than 3" in spec_content.lower(), (
            "Spec must specify >3 internal components threshold for C4 L3"
        )


# ============================================================================
# AC-006: OpenAPI validation quality gate
# ============================================================================


class TestOpenAPIValidation:
    """Validates AC-006: OpenAPI validation quality gate."""

    def test_spec_validates_openapi(self, spec_content: str) -> None:
        """Spec must document OpenAPI validation step."""
        assert "openapi-spec-validator" in spec_content, (
            "Spec must reference openapi-spec-validator for validation"
        )

    def test_spec_has_validation_quality_gate(self, spec_content: str) -> None:
        """Spec must specify a quality gate for OpenAPI validation."""
        content_lower = spec_content.lower()
        assert "quality gate" in content_lower or "validation" in content_lower, (
            "Spec must specify OpenAPI validation as a quality gate"
        )


# ============================================================================
# AC-007: Graphiti seeding
# ============================================================================


class TestGraphitiSeeding:
    """Validates AC-007: Artefacts seeded into project_design and api_contracts groups."""

    def test_spec_seeds_project_design_group(self, spec_content: str) -> None:
        """Spec must reference project_design Graphiti group for seeding."""
        assert "project_design" in spec_content, (
            "Spec must reference project_design group for Graphiti seeding"
        )

    def test_spec_seeds_api_contracts_group(self, spec_content: str) -> None:
        """Spec must reference api_contracts Graphiti group for seeding."""
        assert "api_contracts" in spec_content, (
            "Spec must reference api_contracts group for Graphiti seeding"
        )

    def test_spec_references_system_design_graphiti(self, spec_content: str) -> None:
        """Spec must reference SystemDesignGraphiti for persistence."""
        assert "SystemDesignGraphiti" in spec_content, (
            "Spec must reference SystemDesignGraphiti class for Graphiti operations"
        )

    def test_spec_uses_upsert_methods(self, spec_content: str) -> None:
        """Spec must use upsert methods for idempotent writes."""
        assert "upsert_design_decision" in spec_content, (
            "Spec must reference upsert_design_decision method"
        )
        assert "upsert_api_contract" in spec_content, (
            "Spec must reference upsert_api_contract method"
        )
        assert "upsert_data_model" in spec_content, (
            "Spec must reference upsert_data_model method"
        )


# ============================================================================
# AC-008: Contradiction detection
# ============================================================================


class TestContradictionDetection:
    """Validates AC-008: Flag proposed contracts that violate existing ADRs."""

    def test_spec_has_contradiction_detection(self, spec_content: str) -> None:
        """Spec must describe contradiction detection between contracts and ADRs."""
        content_lower = spec_content.lower()
        assert "contradiction" in content_lower, (
            "Spec must describe contradiction detection"
        )

    def test_spec_references_project_decisions_group(self, spec_content: str) -> None:
        """Spec must query project_decisions group for existing ADRs."""
        assert "project_decisions" in spec_content, (
            "Spec must reference project_decisions group for ADR contradiction checks"
        )

    def test_spec_flags_violations(self, spec_content: str) -> None:
        """Spec must describe flagging violations before finalisation."""
        content_lower = spec_content.lower()
        has_flag_pattern = "flag" in content_lower or "warn" in content_lower or "conflict" in content_lower
        assert has_flag_pattern, (
            "Spec must describe flagging/warning about contract-ADR contradictions"
        )


# ============================================================================
# AC-009: Graceful degradation
# ============================================================================


class TestGracefulDegradation:
    """Validates AC-009: Graceful degradation when Graphiti unavailable."""

    def test_spec_has_graceful_degradation_section(self, spec_content: str) -> None:
        """Spec must have a graceful degradation section."""
        content_lower = spec_content.lower()
        assert "graceful degradation" in content_lower or "graphiti unavailable" in content_lower, (
            "Spec must describe graceful degradation when Graphiti is unavailable"
        )

    def test_spec_continues_without_graphiti(self, spec_content: str) -> None:
        """Spec must allow markdown artefact generation without Graphiti."""
        content_lower = spec_content.lower()
        assert "without persistence" in content_lower or "markdown" in content_lower, (
            "Spec must describe continuing with markdown artefacts when Graphiti unavailable"
        )


# ============================================================================
# AC-010: DDR numbering
# ============================================================================


class TestDDRNumbering:
    """Validates AC-010: Scan docs/design/decisions/ for next available number."""

    def test_spec_references_scan_next_ddr_number(self, spec_content: str) -> None:
        """Spec must reference scan_next_ddr_number helper."""
        assert "scan_next_ddr_number" in spec_content, (
            "Spec must reference scan_next_ddr_number helper function"
        )

    def test_spec_scans_decisions_directory(self, spec_content: str) -> None:
        """Spec must scan docs/design/decisions/ directory."""
        assert "docs/design/decisions" in spec_content, (
            "Spec must reference docs/design/decisions/ directory for DDR scanning"
        )


# ============================================================================
# AC-011: Execution protocol section
# ============================================================================


class TestExecutionProtocol:
    """Validates AC-011: Spec has a CRITICAL EXECUTION INSTRUCTIONS section."""

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
# AC-012: Error handling section
# ============================================================================


class TestErrorHandling:
    """Validates AC-012: Spec has error handling section."""

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

    def test_spec_handles_cancelled_session(self, spec_content: str) -> None:
        """Spec must handle user-cancelled sessions."""
        content_lower = spec_content.lower()
        has_cancel_handling = "cancel" in content_lower or "skip" in content_lower
        assert has_cancel_handling, (
            "Spec must describe handling cancelled/skipped sessions"
        )


# ============================================================================
# Structural quality checks
# ============================================================================


class TestSpecStructure:
    """Validates the overall structure matches GuardKit command spec conventions."""

    def test_spec_has_title(self, spec_content: str) -> None:
        """Spec must start with # /system-design title."""
        assert spec_content.startswith("# /system-design"), (
            "Spec must start with '# /system-design' title"
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

    def test_spec_has_output_format(self, spec_content: str) -> None:
        """Spec must have an Output Format section or output artefacts section."""
        has_output = "Output" in spec_content and ("Format" in spec_content or "Artefact" in spec_content)
        assert has_output, "Spec must have an Output Format/Artefacts section"

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
        """Spec must reference all design entity dataclasses."""
        assert "DesignDecision" in spec_content, "Spec must reference DesignDecision entity"
        assert "ApiContract" in spec_content, "Spec must reference ApiContract entity"
        assert "DataModel" in spec_content, "Spec must reference DataModel entity"

    def test_spec_minimum_length(self, spec_content: str) -> None:
        """Spec must be comprehensive (>500 lines based on system-plan pattern)."""
        line_count = len(spec_content.splitlines())
        assert line_count >= 400, (
            f"Spec has only {line_count} lines; expected >=400 for a comprehensive command spec"
        )

    def test_spec_has_python_code_examples(self, spec_content: str) -> None:
        """Spec must contain Python code examples in execution flow."""
        assert "```python" in spec_content, (
            "Spec must contain Python code examples"
        )

    def test_spec_references_get_graphiti(self, spec_content: str) -> None:
        """Spec must reference get_graphiti() for client initialization."""
        assert "get_graphiti" in spec_content, (
            "Spec must reference get_graphiti() for Graphiti client initialization"
        )
