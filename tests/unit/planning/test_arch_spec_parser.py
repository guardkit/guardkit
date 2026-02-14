"""Tests for architecture spec parser."""

from pathlib import Path

import pytest

from guardkit.planning.arch_spec_parser import (
    ArchSpecResult,
    _extract_field,
    _extract_field_list,
    _extract_section,
    _parse_components,
    _parse_crosscutting,
    _parse_decisions,
    _parse_external_systems,
    _parse_system_context,
    _split_subsections,
    parse_architecture_spec,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_SPEC = """\
# Architecture Spec

## 1. System Context

### Identity

- **Name**: TestSystem
- **Purpose**: A test system for unit testing
- **Methodology**: Modular (not DDD)

### External Systems

| System | Integration | Purpose |
|--------|-------------|---------|
| **Redis** | Direct | Cache |
| **S3** | SDK | Storage |

## 2. Components

### COMP-api: API Gateway

- **Purpose**: Handles HTTP requests
- **Responsibilities**: Routing, auth, rate limiting
- **Dependencies**: Database, Cache

### COMP-db: Database Layer

- **Purpose**: Data persistence
- **Responsibilities**: CRUD, migrations
- **Dependencies**: None

## 4. Cross-Cutting Concerns

### XC-logging: Logging

- **Approach**: Structured JSON logging
- **Affected Components**: API Gateway, Database Layer
- **Constraints**: No PII in logs

## 5. Architecture Decisions

### ADR-SP-001: Use PostgreSQL

- **Status**: Accepted
- **Context**: Need relational database
- **Decision**: Use PostgreSQL for all data
- **Consequences**: +Mature ecosystem, +ACID compliance, -Operational overhead

### ADR-SP-002: REST over GraphQL

- **Status**: Accepted
- **Context**: Team familiarity
- **Decision**: Use REST endpoints
- **Consequences**: +Simple, -Multiple round trips
"""


@pytest.fixture
def spec_file(tmp_path):
    """Write minimal spec to a temp file."""
    p = tmp_path / "spec.md"
    p.write_text(MINIMAL_SPEC)
    return p


@pytest.fixture
def empty_spec_file(tmp_path):
    """Write an empty spec to a temp file."""
    p = tmp_path / "empty.md"
    p.write_text("# Empty Spec\n\nNo sections here.\n")
    return p


# ---------------------------------------------------------------------------
# _extract_section tests
# ---------------------------------------------------------------------------


class TestExtractSection:
    def test_extracts_section_by_pattern(self):
        content = "## 1. Foo\nFoo body\n## 2. Bar\nBar body\n"
        result = _extract_section(content, r"^##\s+\d+\.\s+Foo")
        assert "Foo body" in result
        assert "Bar body" not in result

    def test_returns_empty_for_missing_section(self):
        content = "## 1. Foo\nFoo body\n"
        result = _extract_section(content, r"^##\s+\d+\.\s+Missing")
        assert result == ""

    def test_extracts_last_section(self):
        content = "## 1. Foo\nFoo body\n## 2. Last\nLast content here"
        result = _extract_section(content, r"^##\s+\d+\.\s+Last")
        assert "Last content here" in result


# ---------------------------------------------------------------------------
# _extract_field tests
# ---------------------------------------------------------------------------


class TestExtractField:
    def test_extracts_simple_field(self):
        text = "- **Name**: TestSystem\n- **Purpose**: Testing\n"
        assert _extract_field(text, "Name") == "TestSystem"
        assert _extract_field(text, "Purpose") == "Testing"

    def test_returns_empty_for_missing_field(self):
        text = "- **Name**: TestSystem\n"
        assert _extract_field(text, "Missing") == ""


class TestExtractFieldList:
    def test_extracts_comma_separated(self):
        text = "- **Dependencies**: Foo, Bar, Baz\n"
        result = _extract_field_list(text, "Dependencies")
        assert result == ["Foo", "Bar", "Baz"]

    def test_returns_empty_for_missing(self):
        text = "- **Name**: Test\n"
        assert _extract_field_list(text, "Dependencies") == []


# ---------------------------------------------------------------------------
# _split_subsections tests
# ---------------------------------------------------------------------------


class TestSplitSubsections:
    def test_splits_comp_subsections(self):
        body = (
            "### COMP-a: Alpha\nAlpha body\n"
            "### COMP-b: Beta\nBeta body\n"
        )
        result = _split_subsections(body, "COMP-")
        assert len(result) == 2
        assert "COMP-a: Alpha" in result[0][0]
        assert "Alpha body" in result[0][1]
        assert "COMP-b: Beta" in result[1][0]

    def test_returns_empty_for_no_match(self):
        body = "Some text without subsections\n"
        result = _split_subsections(body, "COMP-")
        assert result == []


# ---------------------------------------------------------------------------
# Component parsing tests
# ---------------------------------------------------------------------------


class TestParseComponents:
    def test_parses_components_from_spec(self):
        components = _parse_components(MINIMAL_SPEC)
        assert len(components) == 2
        assert components[0].name == "API Gateway"
        assert components[0].description == "Handles HTTP requests"
        assert "Routing" in components[0].responsibilities
        assert "Database" in components[0].dependencies

    def test_second_component(self):
        components = _parse_components(MINIMAL_SPEC)
        assert components[1].name == "Database Layer"
        assert components[1].description == "Data persistence"

    def test_returns_empty_for_missing_section(self):
        content = "# Spec\n## 1. Foo\nNo components here\n"
        assert _parse_components(content) == []


# ---------------------------------------------------------------------------
# External systems parsing tests
# ---------------------------------------------------------------------------


class TestParseExternalSystems:
    def test_parses_external_systems_table(self):
        systems = _parse_external_systems(MINIMAL_SPEC)
        assert "Redis" in systems
        assert "S3" in systems

    def test_returns_empty_for_no_table(self):
        content = "# Spec\n## 1. System Context\nNo table\n"
        assert _parse_external_systems(content) == []


# ---------------------------------------------------------------------------
# System context parsing tests
# ---------------------------------------------------------------------------


class TestParseSystemContext:
    def test_parses_system_context(self):
        components = _parse_components(MINIMAL_SPEC)
        comp_names = [c.name for c in components]
        ext_systems = _parse_external_systems(MINIMAL_SPEC)
        ctx = _parse_system_context(MINIMAL_SPEC, comp_names, ext_systems)

        assert ctx is not None
        assert ctx.name == "TestSystem"
        assert ctx.purpose == "A test system for unit testing"
        assert ctx.methodology == "modular"
        assert "API Gateway" in ctx.bounded_contexts
        assert "Redis" in ctx.external_systems

    def test_returns_none_for_missing_section(self):
        content = "# No context\n"
        assert _parse_system_context(content, [], []) is None


# ---------------------------------------------------------------------------
# Crosscutting concern parsing tests
# ---------------------------------------------------------------------------


class TestParseCrosscutting:
    def test_parses_crosscutting_concerns(self):
        concerns = _parse_crosscutting(MINIMAL_SPEC)
        assert len(concerns) == 1
        assert concerns[0].name == "Logging"
        assert concerns[0].description == "Structured JSON logging"
        assert "API Gateway" in concerns[0].applies_to
        assert concerns[0].implementation_notes == "No PII in logs"

    def test_returns_empty_for_missing_section(self):
        content = "# Spec\n"
        assert _parse_crosscutting(content) == []


# ---------------------------------------------------------------------------
# Decision parsing tests
# ---------------------------------------------------------------------------


class TestParseDecisions:
    def test_parses_decisions(self):
        decisions = _parse_decisions(MINIMAL_SPEC)
        assert len(decisions) == 2

    def test_first_decision_fields(self):
        decisions = _parse_decisions(MINIMAL_SPEC)
        adr = decisions[0]
        assert adr.number == 1
        assert adr.title == "Use PostgreSQL"
        assert adr.status == "accepted"
        assert adr.context == "Need relational database"
        assert adr.decision == "Use PostgreSQL for all data"
        assert adr.entity_id == "ADR-SP-001"

    def test_consequences_parsed(self):
        decisions = _parse_decisions(MINIMAL_SPEC)
        adr = decisions[0]
        assert len(adr.consequences) == 3
        assert any("+Mature ecosystem" in c for c in adr.consequences)
        assert any("-Operational overhead" in c for c in adr.consequences)

    def test_returns_empty_for_missing_section(self):
        content = "# Spec\n"
        assert _parse_decisions(content) == []


# ---------------------------------------------------------------------------
# Full parse_architecture_spec tests
# ---------------------------------------------------------------------------


class TestParseArchitectureSpec:
    def test_full_parse(self, spec_file):
        result = parse_architecture_spec(spec_file)

        assert isinstance(result, ArchSpecResult)
        assert result.system_context is not None
        assert result.system_context.name == "TestSystem"
        assert len(result.components) == 2
        assert len(result.concerns) == 1
        assert len(result.decisions) == 2
        assert result.parse_warnings == []

    def test_methodology_propagated_to_components(self, spec_file):
        result = parse_architecture_spec(spec_file)
        for comp in result.components:
            assert comp.methodology == "modular"

    def test_empty_spec_produces_warnings(self, empty_spec_file):
        result = parse_architecture_spec(empty_spec_file)
        assert result.system_context is None
        assert result.components == []
        assert result.concerns == []
        assert result.decisions == []
        assert len(result.parse_warnings) == 4  # 4 missing sections

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_architecture_spec(tmp_path / "nonexistent.md")

    def test_entity_ids_correct(self, spec_file):
        result = parse_architecture_spec(spec_file)
        assert result.system_context.entity_id.startswith("SYS-")
        assert result.components[0].entity_id.startswith("COMP-")
        assert result.concerns[0].entity_id.startswith("XC-")
        assert result.decisions[0].entity_id == "ADR-SP-001"

    def test_to_episode_body_works(self, spec_file):
        result = parse_architecture_spec(spec_file)
        # Verify all entities can produce episode bodies
        body = result.system_context.to_episode_body()
        assert body["name"] == "TestSystem"

        body = result.components[0].to_episode_body()
        assert body["name"] == "API Gateway"

        body = result.concerns[0].to_episode_body()
        assert body["name"] == "Logging"

        body = result.decisions[0].to_episode_body()
        assert body["title"] == "Use PostgreSQL"


# ---------------------------------------------------------------------------
# Real spec file test
# ---------------------------------------------------------------------------


class TestRealSpecFile:
    """Test against the actual guardkit-system-spec.md if available."""

    @pytest.fixture
    def real_spec(self):
        path = Path("docs/architecture/guardkit-system-spec.md")
        if not path.exists():
            pytest.skip("Real spec file not available")
        return path

    def test_parses_real_spec(self, real_spec):
        result = parse_architecture_spec(real_spec)
        assert result.system_context is not None
        assert result.system_context.name == "GuardKit"
        assert len(result.components) >= 5
        assert len(result.decisions) >= 5
        assert len(result.concerns) >= 3

    def test_real_spec_no_critical_warnings(self, real_spec):
        result = parse_architecture_spec(real_spec)
        # Should have no warnings about missing sections
        for w in result.parse_warnings:
            assert "No system context" not in w
            assert "No components" not in w
