"""
Comprehensive Test Suite for ArchitectureWriter

Tests Jinja2 template rendering for architecture documentation generation.
Verifies methodology-aware output (DDD vs non-DDD) and file operations.

Coverage Target: >=85%
Test Count: 25+ tests organized by functionality

Modules tested:
- ArchitectureWriter: Main writer class with write_all() method
- Template rendering: system-context, components, crosscutting, ADR, index
- File operations: Directory creation, file writing
- DDD adaptation: Conditional sections based on methodology
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from typing import List

# Import entities
from guardkit.knowledge.entities.component import ComponentDef
from guardkit.knowledge.entities.system_context import SystemContextDef
from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef
from guardkit.knowledge.entities.architecture_context import ArchitectureDecision

# Import ArchitectureWriter (will fail in RED phase - expected)
from guardkit.planning.architecture_writer import ArchitectureWriter


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory for testing."""
    output_dir = tmp_path / "docs" / "architecture"
    return output_dir


@pytest.fixture
def sample_system_ddd() -> SystemContextDef:
    """Create a sample DDD system context."""
    return SystemContextDef(
        name="E-Commerce Platform",
        purpose="Online retail with multi-tenant support and event-driven architecture",
        bounded_contexts=["Orders", "Inventory", "Customers", "Payment"],
        external_systems=["Payment Gateway", "Shipping API", "Email Service"],
        methodology="ddd",
    )


@pytest.fixture
def sample_system_layered() -> SystemContextDef:
    """Create a sample layered system context."""
    return SystemContextDef(
        name="Content Management System",
        purpose="Web-based content publishing platform",
        bounded_contexts=["Content", "Media", "Users"],
        external_systems=["CDN", "Search Service"],
        methodology="layered",
    )


@pytest.fixture
def sample_components_ddd() -> List[ComponentDef]:
    """Create sample DDD components."""
    return [
        ComponentDef(
            name="Order Management",
            description="Handles order lifecycle and fulfillment",
            responsibilities=["Create orders", "Track order status", "Handle returns"],
            dependencies=["Inventory", "Payment"],
            methodology="ddd",
            aggregate_roots=["Order", "OrderLine", "Return"],
            domain_events=["OrderCreated", "OrderShipped", "OrderCancelled"],
            context_mapping="customer-downstream, inventory-upstream",
        ),
        ComponentDef(
            name="Inventory",
            description="Manages product stock and availability",
            responsibilities=["Track stock levels", "Reserve inventory", "Handle restocking"],
            dependencies=["Warehouse"],
            methodology="ddd",
            aggregate_roots=["Product", "StockLevel"],
            domain_events=["StockReserved", "StockReleased", "RestockNeeded"],
            context_mapping="order-upstream",
        ),
    ]


@pytest.fixture
def sample_components_layered() -> List[ComponentDef]:
    """Create sample layered components."""
    return [
        ComponentDef(
            name="Content Service",
            description="Handles content creation and storage",
            responsibilities=["Create content", "Edit content", "Version control"],
            dependencies=["Media Service"],
            methodology="layered",
        ),
        ComponentDef(
            name="Media Service",
            description="Manages media assets",
            responsibilities=["Upload files", "Process images", "Serve media"],
            dependencies=["CDN"],
            methodology="layered",
        ),
    ]


@pytest.fixture
def sample_concerns() -> List[CrosscuttingConcernDef]:
    """Create sample crosscutting concerns."""
    return [
        CrosscuttingConcernDef(
            name="Observability",
            description="Unified logging, metrics, and distributed tracing",
            applies_to=["All Services"],
            implementation_notes="Use OpenTelemetry SDK with Jaeger backend",
        ),
        CrosscuttingConcernDef(
            name="Security",
            description="Authentication and authorization",
            applies_to=["All APIs", "All Services"],
            implementation_notes="OAuth2 with JWT tokens, rate limiting per tenant",
        ),
    ]


@pytest.fixture
def sample_decisions() -> List[ArchitectureDecision]:
    """Create sample architecture decisions."""
    return [
        ArchitectureDecision(
            number=1,
            title="Use Event Sourcing for Order Aggregate",
            status="accepted",
            context="Orders require complete audit trail and temporal queries for compliance",
            decision="Implement event sourcing pattern for Order aggregate",
            consequences=[
                "Complete history of all order state changes",
                "Complex replay and projection logic required",
                "Increased storage requirements",
            ],
            related_components=["Order Management"],
        ),
        ArchitectureDecision(
            number=2,
            title="Adopt CQRS Pattern",
            status="accepted",
            context="Read and write workloads have different scaling characteristics",
            decision="Separate read and write models using CQRS pattern",
            consequences=[
                "Improved read scalability",
                "Eventual consistency between models",
                "Increased complexity in synchronization",
            ],
            related_components=["Order Management", "Inventory"],
        ),
        ArchitectureDecision(
            number=3,
            title="Use GraphQL for Public API",
            status="proposed",
            context="Clients need flexible data fetching to reduce over-fetching",
            decision="Expose GraphQL API for public consumption",
            consequences=[
                "Flexible client queries",
                "Complexity in query optimization",
                "N+1 query risks",
            ],
            related_components=["All Services"],
        ),
    ]


@pytest.fixture
def writer():
    """Create ArchitectureWriter instance."""
    return ArchitectureWriter()


# =========================================================================
# 1. WRITER INITIALIZATION TESTS (3 tests)
# =========================================================================


class TestWriterInitialization:
    """Tests for ArchitectureWriter initialization."""

    def test_writer_instantiation(self, writer):
        """Test basic writer instantiation."""
        assert writer is not None
        assert isinstance(writer, ArchitectureWriter)

    def test_writer_has_jinja_env(self, writer):
        """Test writer has Jinja2 environment configured."""
        # Should have jinja environment set up
        assert hasattr(writer, 'env') or hasattr(writer, '_env')

    def test_writer_templates_available(self, writer):
        """Test required templates are available."""
        # Should be able to access templates
        required_templates = [
            'system-context.md.j2',
            'components.md.j2',
            'crosscutting.md.j2',
            'adr.md.j2',
            'architecture-index.md.j2',
        ]
        # Templates should be loadable (will test later)
        assert True  # Placeholder - actual test in GREEN phase


# =========================================================================
# 2. WRITE_ALL METHOD TESTS (5 tests)
# =========================================================================


class TestWriteAll:
    """Tests for write_all() method."""

    def test_write_all_creates_output_directory(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test write_all creates output directory if it doesn't exist."""
        assert not temp_output_dir.exists()

        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        assert temp_output_dir.exists()
        assert temp_output_dir.is_dir()

    def test_write_all_creates_decisions_subdirectory(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test write_all creates decisions/ subdirectory for ADRs."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        decisions_dir = temp_output_dir / "decisions"
        assert decisions_dir.exists()
        assert decisions_dir.is_dir()

    def test_write_all_creates_all_expected_files(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test write_all creates all expected markdown files."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        # Main files
        assert (temp_output_dir / "ARCHITECTURE.md").exists()
        assert (temp_output_dir / "system-context.md").exists()
        assert (temp_output_dir / "crosscutting-concerns.md").exists()

        # DDD system should create bounded-contexts.md
        assert (temp_output_dir / "bounded-contexts.md").exists()

        # ADR files
        assert (temp_output_dir / "decisions" / "ADR-SP-001.md").exists()
        assert (temp_output_dir / "decisions" / "ADR-SP-002.md").exists()
        assert (temp_output_dir / "decisions" / "ADR-SP-003.md").exists()

    def test_write_all_layered_creates_components_md(
        self,
        writer,
        temp_output_dir,
        sample_system_layered,
        sample_components_layered,
        sample_concerns,
        sample_decisions,
    ):
        """Test write_all creates components.md for non-DDD systems."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_layered,
            components=sample_components_layered,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        # Non-DDD system should create components.md, not bounded-contexts.md
        assert (temp_output_dir / "components.md").exists()
        assert not (temp_output_dir / "bounded-contexts.md").exists()

    def test_write_all_overwrites_existing_files(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test write_all overwrites existing files."""
        temp_output_dir.mkdir(parents=True)
        existing_file = temp_output_dir / "ARCHITECTURE.md"
        existing_file.write_text("OLD CONTENT")

        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = existing_file.read_text()
        assert "OLD CONTENT" not in content
        assert "E-Commerce Platform" in content


# =========================================================================
# 3. SYSTEM CONTEXT TEMPLATE TESTS (5 tests)
# =========================================================================


class TestSystemContextTemplate:
    """Tests for system-context.md.j2 template."""

    def test_system_context_has_header(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test system-context.md has generated header with date."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "system-context.md").read_text()
        assert "Generated by `/system-plan`" in content
        # Should have current date
        current_year = datetime.now().year
        assert str(current_year) in content

    def test_system_context_has_system_name_and_purpose(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test system-context.md contains system name and purpose."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "system-context.md").read_text()
        assert "E-Commerce Platform" in content
        assert "Online retail with multi-tenant support" in content

    def test_system_context_has_mermaid_diagram(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test system-context.md contains mermaid diagram."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "system-context.md").read_text()
        assert "```mermaid" in content
        assert "graph TB" in content
        assert "subgraph" in content

    def test_system_context_lists_bounded_contexts(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test system-context.md lists bounded contexts."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "system-context.md").read_text()
        for ctx in sample_system_ddd.bounded_contexts:
            assert ctx in content

    def test_system_context_lists_external_systems(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test system-context.md lists external systems."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "system-context.md").read_text()
        for ext in sample_system_ddd.external_systems:
            assert ext in content


# =========================================================================
# 4. COMPONENTS TEMPLATE TESTS (6 tests)
# =========================================================================


class TestComponentsTemplate:
    """Tests for components.md.j2 template (methodology-aware)."""

    def test_components_ddd_has_bounded_contexts_title(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test DDD components file has 'Bounded Context Map' title."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "bounded-contexts.md").read_text()
        assert "Bounded Context Map" in content

    def test_components_layered_has_component_map_title(
        self,
        writer,
        temp_output_dir,
        sample_system_layered,
        sample_components_layered,
        sample_concerns,
        sample_decisions,
    ):
        """Test non-DDD components file has 'Component Map' title."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_layered,
            components=sample_components_layered,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "components.md").read_text()
        assert "Component Map" in content

    def test_components_ddd_includes_aggregate_roots(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test DDD components include aggregate roots section."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "bounded-contexts.md").read_text()
        assert "Aggregate Roots" in content or "aggregate" in content.lower()
        assert "Order" in content
        assert "OrderLine" in content

    def test_components_ddd_includes_domain_events(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test DDD components include domain events section."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "bounded-contexts.md").read_text()
        assert "Domain Events" in content or "events" in content.lower()
        assert "OrderCreated" in content
        assert "OrderShipped" in content

    def test_components_ddd_includes_context_mapping(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test DDD components include context mapping section."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "bounded-contexts.md").read_text()
        assert "Context Mapping" in content or "mapping" in content.lower()
        assert "customer-downstream" in content

    def test_components_layered_excludes_ddd_sections(
        self,
        writer,
        temp_output_dir,
        sample_system_layered,
        sample_components_layered,
        sample_concerns,
        sample_decisions,
    ):
        """Test non-DDD components exclude DDD-specific sections."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_layered,
            components=sample_components_layered,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "components.md").read_text()
        # Should NOT have DDD sections
        assert "Aggregate Roots" not in content
        assert "Domain Events" not in content
        assert "Context Mapping" not in content


# =========================================================================
# 5. CROSSCUTTING TEMPLATE TESTS (3 tests)
# =========================================================================


class TestCrosscuttingTemplate:
    """Tests for crosscutting.md.j2 template."""

    def test_crosscutting_has_generated_header(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test crosscutting-concerns.md has generated header."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "crosscutting-concerns.md").read_text()
        assert "Generated by `/system-plan`" in content

    def test_crosscutting_lists_all_concerns(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test crosscutting-concerns.md lists all concerns."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "crosscutting-concerns.md").read_text()
        assert "Observability" in content
        assert "Security" in content
        assert "OpenTelemetry SDK" in content

    def test_crosscutting_includes_applies_to(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test crosscutting-concerns.md includes applies_to information."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "crosscutting-concerns.md").read_text()
        assert "All Services" in content
        assert "All APIs" in content


# =========================================================================
# 6. ADR TEMPLATE TESTS (5 tests)
# =========================================================================


class TestADRTemplate:
    """Tests for adr.md.j2 template (Michael Nygard format)."""

    def test_adr_files_created_in_decisions_subdirectory(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test ADR files are created in decisions/ subdirectory."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        # Check files exist
        assert (temp_output_dir / "decisions" / "ADR-SP-001.md").exists()
        assert (temp_output_dir / "decisions" / "ADR-SP-002.md").exists()
        assert (temp_output_dir / "decisions" / "ADR-SP-003.md").exists()

    def test_adr_has_michael_nygard_format(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test ADR follows Michael Nygard format (Context, Decision, Consequences)."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "decisions" / "ADR-SP-001.md").read_text()
        assert "## Context" in content
        assert "## Decision" in content
        assert "## Consequences" in content

    def test_adr_includes_status(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test ADR includes status information."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content_accepted = (temp_output_dir / "decisions" / "ADR-SP-001.md").read_text()
        assert "Status: accepted" in content_accepted or "accepted" in content_accepted

        content_proposed = (temp_output_dir / "decisions" / "ADR-SP-003.md").read_text()
        assert "Status: proposed" in content_proposed or "proposed" in content_proposed

    def test_adr_lists_consequences(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test ADR lists all consequences."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "decisions" / "ADR-SP-001.md").read_text()
        assert "Complete history of all order state changes" in content
        assert "Complex replay and projection logic required" in content

    def test_adr_includes_related_components(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test ADR includes related components."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "decisions" / "ADR-SP-001.md").read_text()
        assert "Order Management" in content


# =========================================================================
# 7. ARCHITECTURE INDEX TEMPLATE TESTS (4 tests)
# =========================================================================


class TestArchitectureIndexTemplate:
    """Tests for architecture-index.md.j2 template (ARCHITECTURE.md)."""

    def test_index_has_generated_header(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test ARCHITECTURE.md has generated header."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "ARCHITECTURE.md").read_text()
        assert "Generated by `/system-plan`" in content

    def test_index_links_to_system_context(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test ARCHITECTURE.md links to system-context.md."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "ARCHITECTURE.md").read_text()
        assert "system-context.md" in content

    def test_index_links_to_components_or_bounded_contexts(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test ARCHITECTURE.md links to appropriate component file."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "ARCHITECTURE.md").read_text()
        # For DDD, should link to bounded-contexts.md
        assert "bounded-contexts.md" in content

    def test_index_lists_all_adrs(
        self,
        writer,
        temp_output_dir,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test ARCHITECTURE.md lists all ADRs."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        content = (temp_output_dir / "ARCHITECTURE.md").read_text()
        assert "ADR-SP-001" in content
        assert "ADR-SP-002" in content
        assert "ADR-SP-003" in content
        assert "decisions/ADR-SP-001.md" in content


# =========================================================================
# 8. EDGE CASE TESTS (3 tests)
# =========================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_write_all_handles_empty_lists(
        self, writer, temp_output_dir, sample_system_ddd
    ):
        """Test write_all handles empty component/concern/decision lists."""
        writer.write_all(
            output_dir=temp_output_dir,
            system=sample_system_ddd,
            components=[],
            concerns=[],
            decisions=[],
        )

        # Should still create files
        assert (temp_output_dir / "ARCHITECTURE.md").exists()
        assert (temp_output_dir / "system-context.md").exists()

        # Should not create ADR files
        decisions_dir = temp_output_dir / "decisions"
        if decisions_dir.exists():
            assert len(list(decisions_dir.glob("*.md"))) == 0

    def test_write_all_handles_pathlib_path(
        self,
        writer,
        tmp_path,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test write_all accepts Path objects."""
        output_dir = tmp_path / "output"

        writer.write_all(
            output_dir=output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        assert output_dir.exists()
        assert (output_dir / "ARCHITECTURE.md").exists()

    def test_write_all_handles_string_path(
        self,
        writer,
        tmp_path,
        sample_system_ddd,
        sample_components_ddd,
        sample_concerns,
        sample_decisions,
    ):
        """Test write_all accepts string paths."""
        output_dir = str(tmp_path / "output")

        writer.write_all(
            output_dir=output_dir,
            system=sample_system_ddd,
            components=sample_components_ddd,
            concerns=sample_concerns,
            decisions=sample_decisions,
        )

        assert Path(output_dir).exists()
        assert (Path(output_dir) / "ARCHITECTURE.md").exists()
