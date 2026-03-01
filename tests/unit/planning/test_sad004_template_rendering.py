"""
Tests for TASK-SAD-004: Template rendering for ADR update and new templates.

Tests cover:
- ADR template update (Alternatives Considered section, backwards compatibility)
- Container template (C4 Level 2 native syntax)
- Component-L3 template (C4 Level 3 native syntax)
- API Contract template (multi-protocol support)
- DDR template (Design Decision Record)

Each template is tested with sample data to verify correct rendering.
"""

import pytest
from datetime import datetime
from pathlib import Path
from typing import List

from jinja2 import Environment, PackageLoader, select_autoescape

from guardkit.knowledge.entities.architecture_context import ArchitectureDecision
from guardkit.planning.architecture_writer import ArchitectureWriter


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def jinja_env():
    """Create Jinja2 environment for template testing."""
    return Environment(
        loader=PackageLoader("guardkit", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


@pytest.fixture
def sample_date():
    """Fixed date for deterministic output."""
    return "2026-03-01"


# ---- ADR Fixtures ----


@pytest.fixture
def adr_with_alternatives():
    """ADR that has alternatives_considered populated."""
    return ArchitectureDecision(
        number=1,
        title="Use Event Sourcing for Order Aggregate",
        status="accepted",
        context="Orders require complete audit trail and temporal queries",
        decision="Implement event sourcing pattern for Order aggregate",
        consequences=[
            "Complete history of all order state changes",
            "Complex replay and projection logic required",
        ],
        related_components=["Order Management"],
        alternatives_considered=[
            "Simple CRUD with audit log table",
            "Change Data Capture (CDC) with Debezium",
            "Temporal tables in PostgreSQL",
        ],
    )


@pytest.fixture
def adr_without_alternatives():
    """ADR that has no alternatives_considered (backwards compatibility)."""
    return ArchitectureDecision(
        number=2,
        title="Adopt CQRS Pattern",
        status="accepted",
        context="Read and write workloads have different scaling characteristics",
        decision="Separate read and write models using CQRS pattern",
        consequences=[
            "Improved read scalability",
            "Eventual consistency between models",
        ],
        related_components=["Order Management", "Inventory"],
    )


# ---- Container Fixtures ----


@pytest.fixture
def container_context():
    """Sample context for C4 Level 2 Container diagram."""
    return {
        "system_name": "E-Commerce Platform",
        "date": "2026-03-01",
        "containers": [
            {
                "id": "web_app",
                "name": "Web Application",
                "technology": "React / TypeScript",
                "description": "Customer-facing single-page application",
                "type": "container",
            },
            {
                "id": "api_gateway",
                "name": "API Gateway",
                "technology": "FastAPI / Python",
                "description": "Central API gateway for all services",
                "type": "container",
            },
            {
                "id": "order_db",
                "name": "Order Database",
                "technology": "PostgreSQL",
                "description": "Stores order and transaction data",
                "type": "container_db",
            },
        ],
        "external_systems": [
            {
                "id": "payment_gw",
                "name": "Payment Gateway",
                "description": "Processes card payments",
            },
            {
                "id": "email_svc",
                "name": "Email Service",
                "description": "Sends transactional emails",
            },
        ],
        "relationships": [
            {
                "from": "web_app",
                "to": "api_gateway",
                "label": "Makes API calls to",
                "technology": "HTTPS/JSON",
            },
            {
                "from": "api_gateway",
                "to": "order_db",
                "label": "Reads from and writes to",
                "technology": "SQL/TCP",
            },
            {
                "from": "api_gateway",
                "to": "payment_gw",
                "label": "Sends payment requests",
                "technology": "HTTPS/REST",
            },
        ],
    }


# ---- Component-L3 Fixtures ----


@pytest.fixture
def component_l3_context():
    """Sample context for C4 Level 3 Component diagram."""
    return {
        "container_name": "API Gateway",
        "container_technology": "FastAPI / Python",
        "date": "2026-03-01",
        "components": [
            {
                "id": "auth_handler",
                "name": "Auth Handler",
                "technology": "OAuth2 / JWT",
                "description": "Handles authentication and token validation",
            },
            {
                "id": "order_controller",
                "name": "Order Controller",
                "technology": "FastAPI Router",
                "description": "Handles order CRUD operations",
            },
            {
                "id": "event_publisher",
                "name": "Event Publisher",
                "technology": "RabbitMQ Client",
                "description": "Publishes domain events to message broker",
            },
            {
                "id": "data_access",
                "name": "Data Access Layer",
                "technology": "SQLAlchemy",
                "description": "ORM and database access layer",
            },
        ],
        "relationships": [
            {
                "from": "order_controller",
                "to": "auth_handler",
                "label": "Validates tokens via",
            },
            {
                "from": "order_controller",
                "to": "data_access",
                "label": "Reads/writes data via",
            },
            {
                "from": "order_controller",
                "to": "event_publisher",
                "label": "Publishes events to",
            },
        ],
    }


# ---- API Contract Fixtures ----


@pytest.fixture
def api_contract_context():
    """Sample context for API contract template."""
    return {
        "bounded_context": "Order Management",
        "date": "2026-03-01",
        "version": "1.0.0",
        "protocol": "REST",
        "base_url": "/api/v1/orders",
        "consumer_types": [
            {"name": "Web Application", "description": "Customer-facing SPA"},
            {"name": "Mobile App", "description": "iOS/Android native app"},
            {"name": "Back Office", "description": "Internal admin dashboard"},
        ],
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/v1/orders",
                "summary": "List orders",
                "auth_required": True,
            },
            {
                "method": "POST",
                "path": "/api/v1/orders",
                "summary": "Create order",
                "auth_required": True,
            },
            {
                "method": "GET",
                "path": "/api/v1/orders/{id}",
                "summary": "Get order by ID",
                "auth_required": True,
            },
        ],
        "request_schemas": [
            {
                "name": "CreateOrderRequest",
                "fields": [
                    {"name": "customer_id", "type": "string", "required": True},
                    {"name": "items", "type": "array[OrderItem]", "required": True},
                    {"name": "notes", "type": "string", "required": False},
                ],
            },
        ],
        "response_schemas": [
            {
                "name": "OrderResponse",
                "fields": [
                    {"name": "id", "type": "string", "required": True},
                    {"name": "status", "type": "string", "required": True},
                    {"name": "created_at", "type": "datetime", "required": True},
                ],
            },
        ],
        "authentication": {
            "type": "OAuth2 Bearer Token",
            "description": "JWT tokens issued by Auth Service",
        },
        "error_codes": [
            {"code": 400, "meaning": "Bad Request - Invalid input"},
            {"code": 401, "meaning": "Unauthorized - Missing/invalid token"},
            {"code": 404, "meaning": "Not Found - Order does not exist"},
            {"code": 422, "meaning": "Unprocessable Entity - Validation failed"},
        ],
    }


# ---- DDR Fixtures ----


@pytest.fixture
def ddr_context():
    """Sample context for Design Decision Record template."""
    return {
        "ddr": {
            "id": "DDR-001",
            "title": "Use PostgreSQL for Order Storage",
            "status": "accepted",
            "date": "2026-03-01",
            "context": "Need a reliable RDBMS for transactional order data with ACID guarantees.",
            "decision": "Use PostgreSQL 16 with pgvector extension for order storage and vector search.",
            "rationale": "PostgreSQL provides strong ACID compliance, excellent JSON support, "
            "and pgvector enables AI-powered search without a separate vector DB.",
            "alternatives_considered": [
                {
                    "name": "MongoDB",
                    "pros": "Flexible schema, good for document-oriented data",
                    "cons": "Weaker transactional guarantees, separate vector DB needed",
                },
                {
                    "name": "CockroachDB",
                    "pros": "Distributed SQL, automatic sharding",
                    "cons": "Higher operational complexity, more expensive",
                },
            ],
            "consequences": [
                "Strong transactional guarantees for order operations",
                "Single database for relational and vector data",
                "Requires PostgreSQL expertise for operations",
            ],
            "related_api_contracts": [
                "Order Management API Contract",
                "Inventory API Contract",
            ],
        },
    }


# =========================================================================
# 1. ADR TEMPLATE UPDATE TESTS
# =========================================================================


class TestADRTemplateAlternativesConsidered:
    """Tests for ADR template Alternatives Considered section."""

    def test_adr_renders_alternatives_when_present(
        self, jinja_env, adr_with_alternatives, sample_date
    ):
        """AC: Alternatives Considered section rendered when non-empty."""
        template = jinja_env.get_template("adr.md.j2")
        content = template.render(adr=adr_with_alternatives, date=sample_date)

        assert "## Alternatives Considered" in content
        assert "Simple CRUD with audit log table" in content
        assert "Change Data Capture (CDC) with Debezium" in content
        assert "Temporal tables in PostgreSQL" in content

    def test_adr_omits_alternatives_when_empty(
        self, jinja_env, adr_without_alternatives, sample_date
    ):
        """AC: Backwards compatible - no section when alternatives_considered is empty."""
        template = jinja_env.get_template("adr.md.j2")
        content = template.render(adr=adr_without_alternatives, date=sample_date)

        assert "## Alternatives Considered" not in content

    def test_adr_backwards_compatible_existing_sections(
        self, jinja_env, adr_without_alternatives, sample_date
    ):
        """AC: Existing ADR sections still render correctly."""
        template = jinja_env.get_template("adr.md.j2")
        content = template.render(adr=adr_without_alternatives, date=sample_date)

        # All standard Nygard sections still present
        assert "## Context" in content
        assert "## Decision" in content
        assert "## Consequences" in content
        assert "Adopt CQRS Pattern" in content
        assert "Status: accepted" in content

    def test_adr_alternatives_section_position(
        self, jinja_env, adr_with_alternatives, sample_date
    ):
        """AC: Alternatives Considered appears between Decision and Consequences."""
        template = jinja_env.get_template("adr.md.j2")
        content = template.render(adr=adr_with_alternatives, date=sample_date)

        decision_pos = content.index("## Decision")
        alternatives_pos = content.index("## Alternatives Considered")
        consequences_pos = content.index("## Consequences")

        assert decision_pos < alternatives_pos < consequences_pos


# =========================================================================
# 2. CONTAINER TEMPLATE TESTS (C4 Level 2)
# =========================================================================


class TestContainerTemplate:
    """Tests for container.md.j2 template."""

    def test_container_template_exists(self, jinja_env):
        """AC: container.md.j2 template exists and is loadable."""
        template = jinja_env.get_template("container.md.j2")
        assert template is not None

    def test_container_renders_with_sample_data(
        self, jinja_env, container_context
    ):
        """AC: Template renders correctly with sample data."""
        template = jinja_env.get_template("container.md.j2")
        content = template.render(**container_context)

        assert "E-Commerce Platform" in content
        assert "Web Application" in content
        assert "API Gateway" in content
        assert "Order Database" in content

    def test_container_uses_c4_mermaid_syntax(
        self, jinja_env, container_context
    ):
        """AC: Uses native C4 Mermaid syntax (C4Container, Container, ContainerDb)."""
        template = jinja_env.get_template("container.md.j2")
        content = template.render(**container_context)

        assert "```mermaid" in content
        assert "C4Container" in content

    def test_container_has_container_elements(
        self, jinja_env, container_context
    ):
        """AC: Shows containers with Container() syntax."""
        template = jinja_env.get_template("container.md.j2")
        content = template.render(**container_context)

        assert "Container(" in content

    def test_container_has_database_elements(
        self, jinja_env, container_context
    ):
        """AC: Shows datastores with ContainerDb() syntax."""
        template = jinja_env.get_template("container.md.j2")
        content = template.render(**container_context)

        assert "ContainerDb(" in content

    def test_container_has_external_systems(
        self, jinja_env, container_context
    ):
        """AC: Shows external systems with System_Ext() syntax."""
        template = jinja_env.get_template("container.md.j2")
        content = template.render(**container_context)

        assert "System_Ext(" in content
        assert "Payment Gateway" in content
        assert "Email Service" in content

    def test_container_has_relationships(
        self, jinja_env, container_context
    ):
        """AC: Shows relationships with Rel() syntax."""
        template = jinja_env.get_template("container.md.j2")
        content = template.render(**container_context)

        assert "Rel(" in content
        assert "Makes API calls to" in content

    def test_container_shows_runtime_communication(
        self, jinja_env, container_context
    ):
        """AC: Relationships include technology/protocol information."""
        template = jinja_env.get_template("container.md.j2")
        content = template.render(**container_context)

        assert "HTTPS/JSON" in content
        assert "SQL/TCP" in content


# =========================================================================
# 3. COMPONENT-L3 TEMPLATE TESTS (C4 Level 3)
# =========================================================================


class TestComponentL3Template:
    """Tests for component-l3.md.j2 template."""

    def test_component_l3_template_exists(self, jinja_env):
        """AC: component-l3.md.j2 template exists and is loadable."""
        template = jinja_env.get_template("component-l3.md.j2")
        assert template is not None

    def test_component_l3_renders_with_sample_data(
        self, jinja_env, component_l3_context
    ):
        """AC: Template renders correctly with sample data."""
        template = jinja_env.get_template("component-l3.md.j2")
        content = template.render(**component_l3_context)

        assert "API Gateway" in content
        assert "Auth Handler" in content
        assert "Order Controller" in content
        assert "Event Publisher" in content
        assert "Data Access Layer" in content

    def test_component_l3_uses_c4_component_syntax(
        self, jinja_env, component_l3_context
    ):
        """AC: Uses native C4Component Mermaid syntax."""
        template = jinja_env.get_template("component-l3.md.j2")
        content = template.render(**component_l3_context)

        assert "```mermaid" in content
        assert "C4Component" in content

    def test_component_l3_has_component_elements(
        self, jinja_env, component_l3_context
    ):
        """AC: Shows components with Component() syntax."""
        template = jinja_env.get_template("component-l3.md.j2")
        content = template.render(**component_l3_context)

        assert "Component(" in content

    def test_component_l3_has_relationships(
        self, jinja_env, component_l3_context
    ):
        """AC: Shows internal relationships with Rel() syntax."""
        template = jinja_env.get_template("component-l3.md.j2")
        content = template.render(**component_l3_context)

        assert "Rel(" in content
        assert "Validates tokens via" in content

    def test_component_l3_is_per_container(
        self, jinja_env, component_l3_context
    ):
        """AC: Template renders per-container component breakdown."""
        template = jinja_env.get_template("component-l3.md.j2")
        content = template.render(**component_l3_context)

        # Should reference the parent container
        assert "API Gateway" in content
        assert "FastAPI / Python" in content


# =========================================================================
# 4. API CONTRACT TEMPLATE TESTS
# =========================================================================


class TestAPIContractTemplate:
    """Tests for api-contract.md.j2 template."""

    def test_api_contract_template_exists(self, jinja_env):
        """AC: api-contract.md.j2 template exists and is loadable."""
        template = jinja_env.get_template("api-contract.md.j2")
        assert template is not None

    def test_api_contract_renders_with_sample_data(
        self, jinja_env, api_contract_context
    ):
        """AC: Template renders correctly with sample data."""
        template = jinja_env.get_template("api-contract.md.j2")
        content = template.render(**api_contract_context)

        assert "Order Management" in content
        assert "1.0.0" in content

    def test_api_contract_has_consumer_types(
        self, jinja_env, api_contract_context
    ):
        """AC: Includes consumer types section."""
        template = jinja_env.get_template("api-contract.md.j2")
        content = template.render(**api_contract_context)

        assert "Consumer" in content or "consumer" in content
        assert "Web Application" in content
        assert "Mobile App" in content
        assert "Back Office" in content

    def test_api_contract_has_endpoints_table(
        self, jinja_env, api_contract_context
    ):
        """AC: Includes endpoints table."""
        template = jinja_env.get_template("api-contract.md.j2")
        content = template.render(**api_contract_context)

        assert "GET" in content
        assert "POST" in content
        assert "/api/v1/orders" in content
        assert "List orders" in content
        assert "Create order" in content

    def test_api_contract_has_request_response_schemas(
        self, jinja_env, api_contract_context
    ):
        """AC: Includes request/response schema sections."""
        template = jinja_env.get_template("api-contract.md.j2")
        content = template.render(**api_contract_context)

        assert "CreateOrderRequest" in content
        assert "OrderResponse" in content
        assert "customer_id" in content
        assert "status" in content

    def test_api_contract_has_authentication(
        self, jinja_env, api_contract_context
    ):
        """AC: Includes authentication section."""
        template = jinja_env.get_template("api-contract.md.j2")
        content = template.render(**api_contract_context)

        assert "Authentication" in content or "authentication" in content
        assert "OAuth2 Bearer Token" in content

    def test_api_contract_has_error_codes(
        self, jinja_env, api_contract_context
    ):
        """AC: Includes error codes section."""
        template = jinja_env.get_template("api-contract.md.j2")
        content = template.render(**api_contract_context)

        assert "400" in content
        assert "401" in content
        assert "404" in content
        assert "Bad Request" in content
        assert "Unauthorized" in content

    def test_api_contract_shows_protocol(
        self, jinja_env, api_contract_context
    ):
        """AC: Multi-protocol support - shows protocol type."""
        template = jinja_env.get_template("api-contract.md.j2")
        content = template.render(**api_contract_context)

        assert "REST" in content


# =========================================================================
# 5. DDR TEMPLATE TESTS
# =========================================================================


class TestDDRTemplate:
    """Tests for ddr.md.j2 template (Design Decision Record)."""

    def test_ddr_template_exists(self, jinja_env):
        """AC: ddr.md.j2 template exists and is loadable."""
        template = jinja_env.get_template("ddr.md.j2")
        assert template is not None

    def test_ddr_renders_with_sample_data(self, jinja_env, ddr_context):
        """AC: Template renders correctly with sample data."""
        template = jinja_env.get_template("ddr.md.j2")
        content = template.render(**ddr_context)

        assert "DDR-001" in content
        assert "Use PostgreSQL for Order Storage" in content

    def test_ddr_has_status_section(self, jinja_env, ddr_context):
        """AC: Includes Status section."""
        template = jinja_env.get_template("ddr.md.j2")
        content = template.render(**ddr_context)

        assert "Status" in content
        assert "accepted" in content

    def test_ddr_has_date(self, jinja_env, ddr_context):
        """AC: Includes Date."""
        template = jinja_env.get_template("ddr.md.j2")
        content = template.render(**ddr_context)

        assert "2026-03-01" in content

    def test_ddr_has_context_section(self, jinja_env, ddr_context):
        """AC: Includes Context section."""
        template = jinja_env.get_template("ddr.md.j2")
        content = template.render(**ddr_context)

        assert "## Context" in content
        assert "reliable RDBMS" in content

    def test_ddr_has_decision_section(self, jinja_env, ddr_context):
        """AC: Includes Decision section."""
        template = jinja_env.get_template("ddr.md.j2")
        content = template.render(**ddr_context)

        assert "## Decision" in content
        assert "PostgreSQL 16" in content

    def test_ddr_has_rationale_section(self, jinja_env, ddr_context):
        """AC: Includes Rationale section."""
        template = jinja_env.get_template("ddr.md.j2")
        content = template.render(**ddr_context)

        assert "## Rationale" in content
        assert "ACID compliance" in content

    def test_ddr_has_alternatives_considered(self, jinja_env, ddr_context):
        """AC: Includes Alternatives Considered section with pros/cons."""
        template = jinja_env.get_template("ddr.md.j2")
        content = template.render(**ddr_context)

        assert "## Alternatives Considered" in content
        assert "MongoDB" in content
        assert "CockroachDB" in content
        # Should include pros and cons
        assert "Flexible schema" in content
        assert "Distributed SQL" in content

    def test_ddr_has_consequences(self, jinja_env, ddr_context):
        """AC: Includes Consequences section."""
        template = jinja_env.get_template("ddr.md.j2")
        content = template.render(**ddr_context)

        assert "## Consequences" in content
        assert "Strong transactional guarantees" in content

    def test_ddr_has_related_api_contracts(self, jinja_env, ddr_context):
        """AC: Includes Related API Contracts section."""
        template = jinja_env.get_template("ddr.md.j2")
        content = template.render(**ddr_context)

        assert "Related API Contracts" in content
        assert "Order Management API Contract" in content
        assert "Inventory API Contract" in content

    def test_ddr_omits_api_contracts_when_empty(self, jinja_env):
        """AC: Related API Contracts section omitted when empty."""
        ddr_no_contracts = {
            "ddr": {
                "id": "DDR-002",
                "title": "Use Redis for Caching",
                "status": "proposed",
                "date": "2026-03-01",
                "context": "Need fast cache layer.",
                "decision": "Use Redis 7 for caching.",
                "rationale": "Redis is fast and reliable.",
                "alternatives_considered": [],
                "consequences": ["Fast cache reads"],
                "related_api_contracts": [],
            },
        }
        template = jinja_env.get_template("ddr.md.j2")
        content = template.render(**ddr_no_contracts)

        assert "## Related API Contracts" not in content


# =========================================================================
# 6. INTEGRATION: ArchitectureWriter with new templates
# =========================================================================


class TestArchitectureWriterNewTemplates:
    """Integration tests verifying ArchitectureWriter can load new templates."""

    def test_writer_can_load_container_template(self):
        """ArchitectureWriter's env can load container.md.j2."""
        writer = ArchitectureWriter()
        template = writer.env.get_template("container.md.j2")
        assert template is not None

    def test_writer_can_load_component_l3_template(self):
        """ArchitectureWriter's env can load component-l3.md.j2."""
        writer = ArchitectureWriter()
        template = writer.env.get_template("component-l3.md.j2")
        assert template is not None

    def test_writer_can_load_api_contract_template(self):
        """ArchitectureWriter's env can load api-contract.md.j2."""
        writer = ArchitectureWriter()
        template = writer.env.get_template("api-contract.md.j2")
        assert template is not None

    def test_writer_can_load_ddr_template(self):
        """ArchitectureWriter's env can load ddr.md.j2."""
        writer = ArchitectureWriter()
        template = writer.env.get_template("ddr.md.j2")
        assert template is not None
