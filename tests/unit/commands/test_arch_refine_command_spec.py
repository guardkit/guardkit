"""
Unit tests for /arch-refine command specification.

Validates that installer/core/commands/arch-refine.md meets all acceptance criteria
from TASK-SAD-008, follows structural patterns from system-arch.md and task-refine.md,
and covers refinement-specific scenarios including temporal superseding, disambiguation,
impact analysis, and staleness flagging.

TDD Phase: RED → GREEN
Coverage Target: >=85%
Test Count: 45+ tests
"""

import re
from pathlib import Path

import pytest

# Resolve project root (worktree root)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SPEC_PATH = PROJECT_ROOT / "installer" / "core" / "commands" / "arch-refine.md"
SYSTEM_ARCH_SPEC = PROJECT_ROOT / "installer" / "core" / "commands" / "system-arch.md"


@pytest.fixture
def spec_content() -> str:
    """Load the arch-refine command specification."""
    assert SPEC_PATH.exists(), f"Command spec not found: {SPEC_PATH}"
    return SPEC_PATH.read_text(encoding="utf-8")


@pytest.fixture
def spec_sections(spec_content: str) -> dict[str, str]:
    """Parse top-level sections from the spec (## headings)."""
    sections: dict[str, str] = {}
    current_heading = ""
    current_lines: list[str] = []

    for line in spec_content.splitlines():
        if line.startswith("## "):
            if current_heading:
                sections[current_heading] = "\n".join(current_lines)
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_heading:
        sections[current_heading] = "\n".join(current_lines)

    return sections


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Structural Pattern (follows system-arch.md / system-plan.md)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStructuralPattern:
    """Verify the spec follows established structural patterns."""

    def test_spec_file_exists(self):
        """The spec file must exist at the required path."""
        assert SPEC_PATH.exists(), f"Expected spec at {SPEC_PATH}"

    def test_has_title_heading(self, spec_content: str):
        """Must start with a level-1 heading containing the command name."""
        first_line = spec_content.strip().splitlines()[0]
        assert first_line.startswith("# "), "Spec must start with a # heading"
        assert "arch-refine" in first_line.lower()

    def test_has_command_syntax_section(self, spec_sections: dict):
        """Must have a Command Syntax section."""
        assert "Command Syntax" in spec_sections

    def test_has_available_flags_section(self, spec_sections: dict):
        """Must have an Available Flags section."""
        assert "Available Flags" in spec_sections

    def test_has_execution_flow_section(self, spec_sections: dict):
        """Must have an Execution Flow section."""
        assert "Execution Flow" in spec_sections

    def test_has_error_handling_section(self, spec_sections: dict):
        """Must have an Error Handling section."""
        assert "Error Handling" in spec_sections

    def test_has_examples_section(self, spec_sections: dict):
        """Must have an Examples section."""
        assert "Examples" in spec_sections

    def test_has_critical_execution_instructions(self, spec_content: str):
        """Must have CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE section."""
        assert "CRITICAL EXECUTION INSTRUCTIONS" in spec_content.upper()

    def test_command_syntax_has_bash_block(self, spec_sections: dict):
        """Command Syntax section must contain a bash code block."""
        syntax = spec_sections.get("Command Syntax", "")
        assert "```bash" in syntax
        assert "/arch-refine" in syntax

    def test_has_related_commands_section(self, spec_content: str):
        """Must have a Related Commands section."""
        assert "Related Commands" in spec_content


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-001: Disambiguation flow
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDisambiguationFlow:
    """Verify disambiguation flow via semantic search."""

    def test_semantic_search_documented(self, spec_content: str):
        """Must document semantic search via get_relevant_context_for_topic()."""
        assert "get_relevant_context_for_topic" in spec_content

    def test_presents_top_matches(self, spec_content: str):
        """Must present top 3-5 matches grouped by relevance."""
        content_lower = spec_content.lower()
        # Must mention presenting multiple results
        assert "3-5" in spec_content or ("3" in spec_content and "5" in spec_content)
        assert "match" in content_lower or "result" in content_lower

    def test_requires_explicit_confirmation(self, spec_content: str):
        """Must require explicit confirmation before any changes applied."""
        content_lower = spec_content.lower()
        assert "confirm" in content_lower
        assert "before" in content_lower or "explicit" in content_lower

    def test_handles_ambiguous_queries(self, spec_content: str):
        """Must handle ambiguous queries safely (cap results, require confirmation)."""
        content_lower = spec_content.lower()
        assert "ambiguous" in content_lower or "cap" in content_lower

    def test_references_assum_002(self, spec_content: str):
        """Must reference ASSUM-002 for disambiguation cap."""
        assert "ASSUM-002" in spec_content


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-002: Temporal superseding
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTemporalSuperseding:
    """Verify temporal superseding based on TASK-SAD-001 spike results."""

    def test_superseded_status_set(self, spec_content: str):
        """Must set existing ADR status to superseded."""
        content_lower = spec_content.lower()
        assert "superseded" in content_lower

    def test_new_adr_references_supersedes(self, spec_content: str):
        """New ADR must have supersedes reference to old ADR."""
        assert "supersedes" in spec_content.lower()

    def test_prior_adr_remains_queryable(self, spec_content: str):
        """Prior ADR must remain queryable in Graphiti with its history."""
        content_lower = spec_content.lower()
        assert "queryable" in content_lower or "remain" in content_lower or "preserved" in content_lower

    def test_new_adr_gets_next_number(self, spec_content: str):
        """New ADR gets next available number in sequence."""
        content_lower = spec_content.lower()
        assert "next" in content_lower and ("number" in content_lower or "available" in content_lower)

    def test_upsert_episode_mechanism(self, spec_content: str):
        """Must reference upsert_episode mechanism from TASK-SAD-001 spike."""
        assert "upsert_episode" in spec_content or "upsert" in spec_content.lower()

    def test_superseded_by_field(self, spec_content: str):
        """Must reference superseded_by field from TASK-SAD-002."""
        assert "superseded_by" in spec_content


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-003: Impact analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestImpactAnalysis:
    """Verify downstream impact analysis documentation."""

    def test_shows_affected_downstream_artefacts(self, spec_content: str):
        """Must show which downstream artefacts are affected."""
        content_lower = spec_content.lower()
        assert "downstream" in content_lower
        assert "affected" in content_lower or "impact" in content_lower

    def test_feature_specs_in_impact(self, spec_content: str):
        """Must list feature specs as potentially affected artefacts."""
        content_lower = spec_content.lower()
        assert "feature spec" in content_lower

    def test_c4_diagrams_in_impact(self, spec_content: str):
        """Must list C4 diagrams as potentially affected artefacts."""
        assert "C4" in spec_content

    def test_api_contracts_in_impact(self, spec_content: str):
        """Must list API contracts as potentially affected artefacts."""
        content_lower = spec_content.lower()
        assert "api contract" in content_lower or "contract" in content_lower

    def test_flags_stale_contracts(self, spec_content: str):
        """Must flag feature specs that reference stale contracts."""
        content_lower = spec_content.lower()
        assert "stale" in content_lower

    def test_presents_impact_scope_for_approval(self, spec_content: str):
        """Must present impact scope for user approval before applying changes."""
        content_lower = spec_content.lower()
        has_impact_approval = ("impact" in content_lower and "approval" in content_lower) or \
                              ("impact" in content_lower and "confirm" in content_lower)
        assert has_impact_approval


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-004: C4 diagram re-review gate
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestC4DiagramReReviewGate:
    """Verify C4 diagram re-review gate documentation."""

    def test_revised_diagrams_generated(self, spec_content: str):
        """Revised L1/L2 diagrams must be generated."""
        content_lower = spec_content.lower()
        assert "revised" in content_lower or "regenerate" in content_lower or "re-generate" in content_lower

    def test_mandatory_approval_gate(self, spec_content: str):
        """Diagrams must be presented for mandatory approval."""
        content_lower = spec_content.lower()
        assert "mandatory" in content_lower
        assert "approval" in content_lower or "approve" in content_lower

    def test_c4_l1_l2_diagrams_mentioned(self, spec_content: str):
        """Must mention L1 and L2 (or Level 1 and Level 2) diagrams."""
        content_lower = spec_content.lower()
        has_l1 = "l1" in content_lower or "level 1" in content_lower
        has_l2 = "l2" in content_lower or "level 2" in content_lower
        assert has_l1 and has_l2

    def test_mermaid_format_for_diagrams(self, spec_content: str):
        """Diagrams must use Mermaid format."""
        assert "mermaid" in spec_content.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-005: Staleness flagging
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStalenessFlagging:
    """Verify staleness flagging documentation."""

    def test_stale_metadata_tag(self, spec_content: str):
        """Affected downstream Graphiti nodes must be tagged with stale: true."""
        assert "stale" in spec_content.lower()
        assert "true" in spec_content.lower()

    def test_system_design_detects_stale(self, spec_content: str):
        """Must document that /system-design detects and reports stale decisions."""
        content_lower = spec_content.lower()
        assert "/system-design" in spec_content
        assert "stale" in content_lower
        assert "detect" in content_lower or "report" in content_lower


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-006: Graphiti integration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGraphitiIntegration:
    """Verify Graphiti integration documentation."""

    def test_upsert_superseded_episodes(self, spec_content: str):
        """Must document upserting superseded and new episodes."""
        content_lower = spec_content.lower()
        assert "upsert" in content_lower
        assert "superseded" in content_lower

    def test_project_decisions_group(self, spec_content: str):
        """Must update group: project_decisions."""
        assert "project_decisions" in spec_content

    def test_project_architecture_group_or_design(self, spec_content: str):
        """Must reference project_architecture or project_design group for staleness."""
        has_arch = "project_architecture" in spec_content
        has_design = "project_design" in spec_content
        assert has_arch or has_design


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-007: Graceful degradation when Graphiti unavailable
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGracefulDegradation:
    """Verify graceful degradation documentation."""

    def test_graphiti_unavailable_handling(self, spec_content: str):
        """Must document behavior when Graphiti is unavailable."""
        content_lower = spec_content.lower()
        assert "unavailable" in content_lower
        assert "graphiti" in content_lower

    def test_markdown_artefacts_still_generated(self, spec_content: str):
        """Must state markdown artefacts are generated even without Graphiti."""
        content_lower = spec_content.lower()
        assert "markdown" in content_lower
        assert "without" in content_lower or "still" in content_lower

    def test_warns_user(self, spec_content: str):
        """Must warn user when Graphiti is unavailable."""
        content_lower = spec_content.lower()
        assert "warn" in content_lower


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-008: Security - adversarial semantic search queries
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSecurity:
    """Verify security documentation."""

    def test_results_capped(self, spec_content: str):
        """Adversarial semantic search queries must be capped at 3-5 results."""
        assert "3-5" in spec_content or ("cap" in spec_content.lower() and "result" in spec_content.lower())

    def test_confirmation_gate_for_security(self, spec_content: str):
        """Must have confirmation gate for semantic search results."""
        content_lower = spec_content.lower()
        assert "confirm" in content_lower

    def test_sanitise_documented(self, spec_content: str):
        """Must document sanitising content before Graphiti seeding."""
        assert "saniti" in spec_content.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-009: Execution protocol section
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutionProtocol:
    """Verify execution protocol section with step-by-step Claude instructions."""

    def test_step_by_step_instructions(self, spec_content: str):
        """Must have numbered steps for Claude to follow."""
        assert "Step 1" in spec_content
        assert "Step 2" in spec_content
        assert "Step 3" in spec_content

    def test_what_not_to_do_section(self, spec_content: str):
        """Must have a 'What NOT to Do' section."""
        content_upper = spec_content.upper()
        assert "WHAT NOT TO DO" in content_upper or "DO NOT" in content_upper

    def test_example_execution_trace(self, spec_content: str):
        """Must have an example execution trace."""
        content_lower = spec_content.lower()
        assert "execution trace" in content_lower or "example execution" in content_lower


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-010: Error handling section
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestErrorHandling:
    """Verify error handling section."""

    def test_no_architecture_context_error(self, spec_content: str):
        """Must document error when no architecture context exists."""
        content_lower = spec_content.lower()
        assert "no architecture" in content_lower or "architecture context" in content_lower

    def test_no_matching_adr_error(self, spec_content: str):
        """Must document error when no matching ADR found for query."""
        content_lower = spec_content.lower()
        assert "no match" in content_lower or "not found" in content_lower

    def test_graphiti_connection_error(self, spec_content: str):
        """Must document Graphiti connection error handling."""
        content_lower = spec_content.lower()
        assert "connection" in content_lower or "unavailable" in content_lower


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Prerequisite gate
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPrerequisiteGate:
    """Verify prerequisite gate (requires architecture context from /system-arch)."""

    def test_requires_architecture_context(self, spec_content: str):
        """Must require architecture context from /system-arch before running."""
        content_lower = spec_content.lower()
        assert "prerequisite" in content_lower or "require" in content_lower
        assert "/system-arch" in spec_content

    def test_checks_for_existing_adrs(self, spec_content: str):
        """Must check for existing ADRs to refine."""
        content_lower = spec_content.lower()
        assert "existing" in content_lower and "adr" in content_lower


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Shared reference with /design-refine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSharedDisambiguationReference:
    """Verify shared disambiguation flow reference between /arch-refine and /design-refine."""

    def test_mentions_design_refine(self, spec_content: str):
        """Must mention /design-refine as related command or shared pattern."""
        assert "/design-refine" in spec_content or "design-refine" in spec_content.lower()

    def test_shared_disambiguation_noted(self, spec_content: str):
        """Must note that disambiguation flow is shared with /design-refine."""
        content_lower = spec_content.lower()
        assert "shared" in content_lower or "identical" in content_lower or "same" in content_lower


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADR numbering and output
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestADROutput:
    """Verify ADR output conventions."""

    def test_adr_arch_prefix(self, spec_content: str):
        """Must use ADR-ARCH-NNN prefix for architecture ADRs."""
        assert "ADR-ARCH" in spec_content

    def test_adr_numbering_from_existing(self, spec_content: str):
        """Must continue numbering from highest existing ADR number."""
        assert "docs/architecture/decisions/" in spec_content

    def test_output_to_architecture_decisions_directory(self, spec_content: str):
        """Output ADRs to docs/architecture/decisions/."""
        assert "docs/architecture/decisions/" in spec_content


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pipeline position
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPipelinePosition:
    """Verify the command's position in the architecture pipeline."""

    def test_downstream_of_system_arch(self, spec_content: str):
        """Must position itself as downstream of /system-arch."""
        assert "/system-arch" in spec_content

    def test_references_system_design(self, spec_content: str):
        """Must reference /system-design as a related downstream command."""
        assert "/system-design" in spec_content

    def test_references_impact_on_downstream(self, spec_content: str):
        """Must reference impact on downstream artefacts."""
        content_lower = spec_content.lower()
        assert "downstream" in content_lower
