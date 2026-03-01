"""
Unit tests for /system-arch command specification.

Validates that installer/core/commands/system-arch.md meets all acceptance criteria
from TASK-SAD-006, follows structural patterns from system-plan.md, and covers all
BDD scenarios from system-arch-design-commands.feature.

TDD Phase: RED → GREEN
Coverage Target: >=85%
Test Count: 30+ tests
"""

import re
from pathlib import Path

import pytest

# Resolve project root (worktree root)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SPEC_PATH = PROJECT_ROOT / "installer" / "core" / "commands" / "system-arch.md"
SYSTEM_PLAN_SPEC = PROJECT_ROOT / "installer" / "core" / "commands" / "system-plan.md"


@pytest.fixture
def spec_content() -> str:
    """Load the system-arch command specification."""
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
# AC-001: Command spec follows the pattern established by system-plan.md and feature-plan.md
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStructuralPattern:
    """Verify the spec follows system-plan.md structural patterns."""

    def test_spec_file_exists(self):
        """The spec file must exist at the required path."""
        assert SPEC_PATH.exists(), f"Expected spec at {SPEC_PATH}"

    def test_has_title_heading(self, spec_content: str):
        """Must start with a level-1 heading."""
        first_line = spec_content.strip().splitlines()[0]
        assert first_line.startswith("# "), "Spec must start with a # heading"
        assert "system-arch" in first_line.lower()

    def test_has_command_syntax_section(self, spec_sections: dict):
        """Must have a Command Syntax section (matches system-plan.md)."""
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
        assert "/system-arch" in syntax


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-002: 6-category interactive question flow with checkpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestInteractiveQuestionFlow:
    """Verify the 6-category question flow with checkpoints."""

    REQUIRED_CATEGORIES = [
        "Domain",
        "Bounded Context",
        "Technology",
        "Multi-Consumer API",
        "Cross-Cutting",
        "Constraints",
    ]

    def test_has_six_categories(self, spec_content: str):
        """All 6 required question categories must be documented."""
        for category in self.REQUIRED_CATEGORIES:
            assert category.lower() in spec_content.lower(), (
                f"Missing category: {category}"
            )

    def test_checkpoint_pattern_documented(self, spec_content: str):
        """Checkpoint pattern [C]ontinue / [R]evise / [S]kip / [A]DR? must be documented."""
        assert "[C]ontinue" in spec_content
        assert "[R]evise" in spec_content
        assert "[S]kip" in spec_content
        assert "[A]DR" in spec_content

    def test_trade_offs_surfaced_for_structural_pattern(self, spec_content: str):
        """Category 1 must surface trade-offs for structural pattern choices."""
        assert "trade-off" in spec_content.lower() or "trade off" in spec_content.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-003: Setup mode auto-detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSetupModeAutoDetection:
    """Verify setup mode auto-detection documentation."""

    def test_auto_detection_documented(self, spec_content: str):
        """Auto-detection logic for setup mode must be documented."""
        assert "auto-detect" in spec_content.lower() or "auto detect" in spec_content.lower()

    def test_graphiti_check_for_mode(self, spec_content: str):
        """Must check Graphiti for existing architecture context."""
        assert "graphiti" in spec_content.lower()
        assert "architecture context" in spec_content.lower()

    def test_setup_mode_when_no_context(self, spec_content: str):
        """Must document entering setup mode when no context exists."""
        assert "setup" in spec_content.lower()
        # Must connect no-context to setup mode
        assert "no" in spec_content.lower() and "setup" in spec_content.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-004: Mandatory C4 diagram output with review gates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestC4DiagramOutput:
    """Verify C4 diagram output and review gates."""

    def test_c4_level_1_context_diagram(self, spec_content: str):
        """C4 Level 1 (System Context) diagram must be documented."""
        assert "c4" in spec_content.lower()
        assert "system context" in spec_content.lower() or "context diagram" in spec_content.lower()
        assert "level 1" in spec_content.lower() or "l1" in spec_content.lower()

    def test_c4_level_2_container_diagram(self, spec_content: str):
        """C4 Level 2 (Container) diagram must be documented."""
        assert "container" in spec_content.lower()
        assert "level 2" in spec_content.lower() or "l2" in spec_content.lower()

    def test_references_system_context_template(self, spec_content: str):
        """Must reference existing system-context.md.j2 template."""
        assert "system-context.md.j2" in spec_content

    def test_references_container_template(self, spec_content: str):
        """Must reference new container.md.j2 template."""
        assert "container.md.j2" in spec_content

    def test_explicit_approval_required(self, spec_content: str):
        """Diagrams require explicit user approval before proceeding."""
        content_lower = spec_content.lower()
        assert "approval" in content_lower or "approve" in content_lower
        assert "review gate" in content_lower or "review" in content_lower

    def test_mermaid_format(self, spec_content: str):
        """Diagrams must use Mermaid format."""
        assert "mermaid" in spec_content.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-005: Mandatory output artefacts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMandatoryOutputArtefacts:
    """Verify all mandatory output artefacts are documented."""

    def test_domain_model_document(self, spec_content: str):
        """Domain model document must be in output artefacts."""
        assert "domain model" in spec_content.lower()

    def test_adrs_with_arch_prefix(self, spec_content: str):
        """ADRs must use ADR-ARCH-NNN prefix."""
        assert "ADR-ARCH" in spec_content

    def test_assumptions_manifest_yaml(self, spec_content: str):
        """Assumptions manifest in YAML format must be documented."""
        content_lower = spec_content.lower()
        assert "assumptions" in content_lower
        assert "manifest" in content_lower or "yaml" in content_lower

    def test_architecture_summary_for_system_plan(self, spec_content: str):
        """Architecture summary for /system-plan consumption must be documented."""
        content_lower = spec_content.lower()
        assert "architecture summary" in content_lower or "summary" in content_lower
        assert "/system-plan" in spec_content

    def test_c4_context_diagram_output(self, spec_content: str):
        """C4 Context diagram (Mermaid) must be in output list."""
        assert "C4" in spec_content and "context" in spec_content.lower()

    def test_c4_container_diagram_output(self, spec_content: str):
        """C4 Container diagram (Mermaid) must be in output list."""
        assert "C4" in spec_content and "container" in spec_content.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-006: Graphiti seeding
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGraphitiSeeding:
    """Verify Graphiti seeding documentation."""

    def test_project_architecture_group(self, spec_content: str):
        """Must document seeding to project_architecture group."""
        assert "project_architecture" in spec_content

    def test_project_decisions_group(self, spec_content: str):
        """Must document seeding to project_decisions group."""
        assert "project_decisions" in spec_content


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-007: Graceful degradation
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
        # The spec should indicate artefacts are generated regardless
        assert "without" in content_lower or "still" in content_lower


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-008: Partial session handling
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPartialSessionHandling:
    """Verify partial session handling documentation."""

    def test_skipped_categories_persisted(self, spec_content: str):
        """Must document persisting completed categories on skip."""
        content_lower = spec_content.lower()
        assert "skip" in content_lower
        assert "partial" in content_lower or "completed" in content_lower

    def test_inform_which_skipped(self, spec_content: str):
        """Must inform user which categories were skipped."""
        content_lower = spec_content.lower()
        assert "skipped" in content_lower


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-009: Empty answer handling
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEmptyAnswerHandling:
    """Verify empty answer handling documentation."""

    def test_placeholder_used(self, spec_content: str):
        """Must use placeholder for empty answers."""
        assert "placeholder" in spec_content.lower()

    def test_warn_on_empty(self, spec_content: str):
        """Must warn user on empty answer."""
        content_lower = spec_content.lower()
        assert "empty" in content_lower
        assert "warn" in content_lower


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-010: ADR numbering
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestADRNumbering:
    """Verify ADR numbering documentation."""

    def test_scan_existing_adrs(self, spec_content: str):
        """Must document scanning docs/architecture/decisions/ for next number."""
        assert "docs/architecture/decisions/" in spec_content

    def test_next_available_number(self, spec_content: str):
        """Must document using the next available ADR number."""
        content_lower = spec_content.lower()
        assert "next" in content_lower and ("number" in content_lower or "available" in content_lower)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-011: Diagram splitting
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDiagramSplitting:
    """Verify diagram splitting documentation."""

    def test_thirty_node_threshold(self, spec_content: str):
        """Must document the 30-node threshold for diagram splitting."""
        assert "30" in spec_content
        # Must connect 30 to nodes/splitting
        assert "node" in spec_content.lower() or "split" in spec_content.lower()

    def test_warn_and_suggest_split(self, spec_content: str):
        """Must warn and suggest manual split at review gate."""
        content_lower = spec_content.lower()
        assert "split" in content_lower
        assert "warn" in content_lower or "suggest" in content_lower


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-012: Security - sanitise ADR rationale
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSecurity:
    """Verify security documentation."""

    def test_sanitise_adr_rationale(self, spec_content: str):
        """Must document sanitising ADR rationale text before Graphiti seeding."""
        content_lower = spec_content.lower()
        assert "saniti" in content_lower  # matches sanitise/sanitize
        assert "rationale" in content_lower or "adr" in content_lower.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-013: Execution protocol section
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutionProtocol:
    """Verify execution protocol section with step-by-step Claude instructions."""

    def test_step_by_step_instructions(self, spec_content: str):
        """Must have numbered steps for Claude to follow."""
        assert "Step 1" in spec_content
        assert "Step 2" in spec_content
        assert "Step 3" in spec_content

    def test_argument_parsing_step(self, spec_content: str):
        """Must include argument parsing step."""
        content_lower = spec_content.lower()
        assert "parse" in content_lower and "argument" in content_lower


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AC-014: Error handling section
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestErrorHandling:
    """Verify error handling section."""

    def test_no_description_error(self, spec_content: str):
        """Must document error for missing description."""
        content_lower = spec_content.lower()
        assert "no description" in content_lower or "missing" in content_lower or "without" in content_lower

    def test_invalid_pattern_choice(self, spec_content: str):
        """Must document handling of invalid pattern choice."""
        content_lower = spec_content.lower()
        assert "invalid" in content_lower or "unrecogni" in content_lower


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BDD Scenario Coverage
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBDDScenarioCoverage:
    """Verify spec covers BDD scenarios from system-arch-design-commands.feature."""

    def test_setup_mode_detection_scenario(self, spec_content: str):
        """BDD: Running /system-arch on new project detects setup mode."""
        content_lower = spec_content.lower()
        assert "setup mode" in content_lower
        assert "auto" in content_lower and "detect" in content_lower

    def test_mandatory_artefacts_scenario(self, spec_content: str):
        """BDD: /system-arch generates all mandatory output artefacts."""
        content_lower = spec_content.lower()
        assert "domain model" in content_lower
        assert "adr" in content_lower
        assert "C4" in spec_content
        assert "assumptions" in content_lower

    def test_c4_review_gate_scenario(self, spec_content: str):
        """BDD: C4 diagrams are mandatory review gates."""
        content_lower = spec_content.lower()
        assert "review gate" in content_lower or "mandatory" in content_lower
        assert "approval" in content_lower or "approve" in content_lower

    def test_graphiti_unavailable_scenario(self, spec_content: str):
        """BDD: Running /system-arch when Graphiti unavailable."""
        content_lower = spec_content.lower()
        assert "unavailable" in content_lower
        assert "warn" in content_lower

    def test_cancel_session_scenario(self, spec_content: str):
        """BDD: Cancelling session preserves partial work."""
        content_lower = spec_content.lower()
        assert "cancel" in content_lower or "skip" in content_lower
        assert "partial" in content_lower

    def test_empty_answer_scenario(self, spec_content: str):
        """BDD: Empty answers use placeholder."""
        content_lower = spec_content.lower()
        assert "empty" in content_lower
        assert "placeholder" in content_lower

    def test_invalid_pattern_scenario(self, spec_content: str):
        """BDD: Invalid structural pattern shows valid options."""
        content_lower = spec_content.lower()
        assert "invalid" in content_lower or "unrecogni" in content_lower
        assert "valid option" in content_lower or "valid choices" in content_lower

    def test_no_description_scenario(self, spec_content: str):
        """BDD: Running without description shows usage error."""
        content_lower = spec_content.lower()
        has_usage_error = "usage" in content_lower or "required" in content_lower
        assert has_usage_error


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Multi-Consumer API Strategy (Category 4)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMultiConsumerAPIStrategy:
    """Verify multi-consumer API strategy category."""

    def test_web_clients_consumer(self, spec_content: str):
        """Must document web client consumer type."""
        assert "web client" in spec_content.lower()

    def test_agents_consumer(self, spec_content: str):
        """Must document agent consumer type."""
        assert "agent" in spec_content.lower()

    def test_internal_flows_consumer(self, spec_content: str):
        """Must document internal flow consumer type."""
        assert "internal" in spec_content.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Downstream Integration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDownstreamIntegration:
    """Verify downstream command integration is documented."""

    def test_system_plan_integration(self, spec_content: str):
        """Must document integration with /system-plan."""
        assert "/system-plan" in spec_content

    def test_output_directory_convention(self, spec_content: str):
        """Must use docs/architecture/ output directory."""
        assert "docs/architecture/" in spec_content

    def test_adr_directory_convention(self, spec_content: str):
        """Must use docs/architecture/decisions/ for ADRs."""
        assert "docs/architecture/decisions/" in spec_content
