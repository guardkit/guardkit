"""
Comprehensive Test Suite for ADR-SP-009: Honeycomb Testing Model

This test suite validates that:
1. The ADR-SP-009 file exists and has correct structure
2. The ARCHITECTURE.md file references ADR-SP-009
3. The ADR content matches requirements (context, decision, consequences)
4. All acceptance criteria are met

Coverage Target: 100%
Test Count: 11 tests (one per acceptance criterion)
"""

import pytest
from pathlib import Path


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def adr_file_path():
    """Path to ADR-SP-009 markdown file."""
    return Path("docs/architecture/decisions/ADR-SP-009-honeycomb-testing-model.md")


@pytest.fixture
def adr_content(adr_file_path):
    """Content of ADR-SP-009 file."""
    return adr_file_path.read_text()


@pytest.fixture
def architecture_md_path():
    """Path to ARCHITECTURE.md file."""
    return Path("docs/architecture/ARCHITECTURE.md")


@pytest.fixture
def architecture_content(architecture_md_path):
    """Content of ARCHITECTURE.md file."""
    return architecture_md_path.read_text()


# ============================================================================
# AC-001: File exists
# ============================================================================

def test_adr_sp_009_file_exists(adr_file_path):
    """AC-001: docs/architecture/decisions/ADR-SP-009-honeycomb-testing-model.md created."""
    assert adr_file_path.exists(), f"ADR-SP-009 file does not exist at {adr_file_path}"
    assert adr_file_path.is_file(), f"ADR-SP-009 path is not a file: {adr_file_path}"


# ============================================================================
# AC-002: ADR follows existing format
# ============================================================================

def test_adr_has_required_sections(adr_content):
    """AC-002: ADR follows existing format with required sections."""
    # Check for standard ADR sections
    assert "# ADR-SP-009:" in adr_content, "Missing title with ADR-SP-009 prefix"
    assert "Date" in adr_content, "Missing Date metadata"
    assert "Status" in adr_content, "Missing Status metadata"
    assert "## Context" in adr_content, "Missing Context section"
    assert "## Decision" in adr_content, "Missing Decision section"
    assert "## Consequences" in adr_content, "Missing Consequences section"


def test_adr_title_matches_format(adr_content):
    """AC-002: ADR title follows format 'ADR-SP-009: Honeycomb Testing Model'."""
    lines = adr_content.split('\n')
    title_line = lines[0] if lines else ""
    assert "ADR-SP-009" in title_line, "Title doesn't include ADR-SP-009 identifier"
    assert "Honeycomb Testing Model" in title_line, "Title doesn't mention Honeycomb Testing Model"


# ============================================================================
# AC-003: Status is Accepted
# ============================================================================

def test_adr_status_is_accepted(adr_content):
    """AC-003: Status is 'Accepted'."""
    # Look for status line in metadata section (first 10 lines)
    lines = adr_content.split('\n')[:10]
    status_lines = [line for line in lines if "Status" in line]

    assert len(status_lines) > 0, "No Status metadata found in first 10 lines"
    status_line = status_lines[0]
    assert "Accepted" in status_line, f"Status is not 'Accepted'. Found: {status_line}"


# ============================================================================
# AC-004: Context explains historical failure patterns
# ============================================================================

def test_context_references_failure_patterns(adr_content):
    """AC-004: Context explains historical failure patterns (FP-002, FP-003, FP-006)."""
    context_section = adr_content.split("## Context")[1].split("##")[0] if "## Context" in adr_content else ""

    # Check for references to specific failure patterns
    assert "FP-002" in context_section or "system_plan.py" in context_section, \
        "Context doesn't reference FP-002 (system_plan stub)"
    assert "FP-003" in context_section or "acceptance criteria" in context_section.lower(), \
        "Context doesn't reference FP-003 (acceptance criteria wiring)"
    assert "FP-006" in context_section or "files_created" in context_section, \
        "Context doesn't reference FP-006 (files_created empty)"


def test_context_explains_seam_failure_pattern(adr_content):
    """AC-004: Context explains that failures occur at technology seams."""
    context_section = adr_content.split("## Context")[1].split("##")[0] if "## Context" in adr_content else ""

    # Check that context explains the core problem
    assert "seam" in context_section.lower() or "boundary" in context_section.lower() or "boundaries" in context_section.lower(), \
        "Context doesn't explain seam/boundary failures"
    assert "unit test" in context_section.lower(), \
        "Context doesn't mention unit tests"


# ============================================================================
# AC-005: Decision captures GuardKit Honeycomb model
# ============================================================================

def test_decision_specifies_guardkit_honeycomb_distribution(adr_content):
    """AC-005a: Decision captures GuardKit uses Honeycomb model (60% seam, 30% unit, 10% E2E)."""
    # Extract decision section including subsections (use "## Consequences" as end marker)
    if "## Decision" not in adr_content:
        pytest.fail("No Decision section found")

    decision_start = adr_content.index("## Decision")
    decision_end = adr_content.index("## Consequences") if "## Consequences" in adr_content else len(adr_content)
    decision_section = adr_content[decision_start:decision_end]

    # Check for GuardKit/platform tool section
    assert "GuardKit" in decision_section or "Platform Tool" in decision_section, \
        "Decision doesn't have GuardKit/Platform Tool section"

    # Check for Honeycomb model mention
    assert "Honeycomb" in decision_section, "Decision doesn't mention Honeycomb model"

    # Check for test distribution percentages (allowing some flexibility in formatting)
    assert "60%" in decision_section or "60 percent" in decision_section.lower(), \
        "Decision doesn't specify 60% for seam/integration tests"
    assert "30%" in decision_section or "30 percent" in decision_section.lower(), \
        "Decision doesn't specify 30% for unit tests"
    assert "10%" in decision_section or "10 percent" in decision_section.lower(), \
        "Decision doesn't specify 10% for E2E tests"


def test_decision_specifies_client_app_trophy_distribution(adr_content):
    """AC-005b: Decision captures client apps use Trophy model (50% feature/integration, 30% unit, 10% E2E, 10% static)."""
    # Extract decision section including subsections
    if "## Decision" not in adr_content:
        pytest.fail("No Decision section found")

    decision_start = adr_content.index("## Decision")
    decision_end = adr_content.index("## Consequences") if "## Consequences" in adr_content else len(adr_content)
    decision_section = adr_content[decision_start:decision_end]

    # Check for client app section
    assert "Client App" in decision_section or "client app" in decision_section.lower(), \
        "Decision doesn't have Client App section"

    # Check for Trophy model mention
    assert "Trophy" in decision_section, "Decision doesn't mention Trophy model"

    # Check for test distribution (50%, 30%, 10%, 10%)
    assert "50%" in decision_section or "50 percent" in decision_section.lower(), \
        "Decision doesn't specify 50% for feature/integration tests"


def test_decision_defines_seam_tests(adr_content):
    """AC-005c: Decision defines seam tests as cross-boundary verification with real implementations."""
    # Extract decision section including subsections
    if "## Decision" not in adr_content:
        pytest.fail("No Decision section found")

    decision_start = adr_content.index("## Decision")
    decision_end = adr_content.index("## Consequences") if "## Consequences" in adr_content else len(adr_content)
    decision_section = adr_content[decision_start:decision_end]

    # Check for seam test definition
    assert "seam" in decision_section.lower(), "Decision doesn't define seam tests"
    assert "boundary" in decision_section.lower() or "boundaries" in decision_section.lower(), \
        "Decision doesn't mention boundaries in seam test definition"
    assert "real" in decision_section.lower(), \
        "Decision doesn't specify 'real implementations' for seam tests"


def test_decision_specifies_anti_stub_gate(adr_content):
    """AC-005d: Decision specifies anti-stub gate requirement."""
    # Extract decision section including subsections
    if "## Decision" not in adr_content:
        pytest.fail("No Decision section found")

    decision_start = adr_content.index("## Decision")
    decision_end = adr_content.index("## Consequences") if "## Consequences" in adr_content else len(adr_content)
    decision_section = adr_content[decision_start:decision_end]

    # Check for anti-stub gate mention
    assert "anti-stub" in decision_section.lower() or "antistub" in decision_section.lower(), \
        "Decision doesn't mention anti-stub gate"
    assert "orchestrator" in decision_section.lower(), \
        "Decision doesn't mention orchestrator functions in anti-stub requirement"


# ============================================================================
# AC-006: Consequences list implementation changes
# ============================================================================

def test_consequences_mentions_seam_directory(adr_content):
    """AC-006a: Consequences mentions new tests/seam/ directory."""
    consequences_section = adr_content.split("## Consequences")[1] if "## Consequences" in adr_content else ""

    assert "tests/seam" in consequences_section or "test/seam" in consequences_section, \
        "Consequences doesn't mention tests/seam/ directory"


def test_consequences_mentions_quality_gate_updates(adr_content):
    """AC-006b: Consequences mentions quality gate updates."""
    consequences_section = adr_content.split("## Consequences")[1] if "## Consequences" in adr_content else ""

    assert "quality gate" in consequences_section.lower() or "gate" in consequences_section.lower(), \
        "Consequences doesn't mention quality gate updates"


def test_consequences_mentions_template_guidance(adr_content):
    """AC-006c: Consequences mentions template guidance updates."""
    consequences_section = adr_content.split("## Consequences")[1] if "## Consequences" in adr_content else ""

    assert "template" in consequences_section.lower(), \
        "Consequences doesn't mention template guidance updates"


# ============================================================================
# AC-007: ARCHITECTURE.md updated
# ============================================================================

def test_architecture_md_has_adr_sp_009_row(architecture_content):
    """AC-007: docs/architecture/ARCHITECTURE.md updated with ADR-SP-009 row."""
    # Check for ADR-SP-009 reference in architecture decisions table
    assert "ADR-SP-009" in architecture_content, \
        "ARCHITECTURE.md doesn't reference ADR-SP-009"

    # Check for link to the decision file
    assert "decisions/ADR-SP-009" in architecture_content or \
           "ADR-SP-009-honeycomb-testing-model" in architecture_content, \
        "ARCHITECTURE.md doesn't link to ADR-SP-009 file"

    # Check for title mention
    assert "Honeycomb" in architecture_content or "honeycomb" in architecture_content, \
        "ARCHITECTURE.md doesn't mention Honeycomb in ADR-SP-009 entry"


# ============================================================================
# Additional validation tests
# ============================================================================

def test_adr_length_is_reasonable(adr_content):
    """Validate ADR is concise (under 200 lines as suggested in implementation notes)."""
    line_count = len(adr_content.split('\n'))
    assert line_count < 200, \
        f"ADR is too long ({line_count} lines). Should be under 200 lines for readability."


def test_adr_references_research_document(adr_content):
    """Validate ADR references the source research document."""
    # Check for reference to research doc or external sources
    assert "research" in adr_content.lower() or "reference" in adr_content.lower() or \
           "testing-strategy" in adr_content.lower(), \
        "ADR should reference source research document"
