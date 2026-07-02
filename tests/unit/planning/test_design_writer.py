"""
Tests for SystemDesignGraphiti and DesignWriter (TASK-SAD-005).

TDD tests for:
- SystemDesignGraphiti: Graphiti read/write for /system-design entities
- DesignWriter: Markdown artefact generation from design entities
- scan_next_ddr_number: DDR numbering helper

Coverage Target: >=85%

Key patterns verified:
- All write operations use upsert_episode() (NOT add_episode())
- All write operations use client.get_group_id() for correct group prefixing
- All operations have graceful degradation (return None/[]/False on failure)
- [Graphiti] prefix on all log messages
- DesignWriter creates correct directory structure
- scan_next_ddr_number finds max DDR number
"""

import json
import logging
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from guardkit.knowledge.entities.design_decision import DesignDecision
from guardkit.knowledge.entities.api_contract import ApiContract
from guardkit.knowledge.entities.data_model import DataModel

from guardkit.planning.design_writer import DesignWriter, scan_next_ddr_number


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock GraphitiClient."""
    client = MagicMock()
    client.enabled = True
    client.get_group_id = MagicMock(
        side_effect=lambda group_name: f"test-project__{group_name}"
    )
    return client


@pytest.fixture
def mock_client_disabled() -> MagicMock:
    """Create a disabled mock GraphitiClient."""
    client = MagicMock()
    client.enabled = False
    return client


@pytest.fixture
def sample_design_decision() -> DesignDecision:
    """Create a sample design decision for testing."""
    return DesignDecision(
        number=1,
        title="Use CQRS Pattern",
        context="High read frequency, complex writes",
        decision="Implement CQRS",
        rationale="Independent scaling of reads and writes",
        alternatives_considered=["Simple CRUD", "Event Sourcing only"],
        consequences=["Eventual consistency", "Improved scalability"],
        related_components=["Order Management"],
        status="accepted",
    )


@pytest.fixture
def sample_api_contract() -> ApiContract:
    """Create a sample API contract for testing."""
    return ApiContract(
        bounded_context="Order Management",
        consumer_types=["web-frontend", "mobile-app"],
        endpoints=[
            {"path": "/orders", "method": "POST", "description": "Create order"},
            {"path": "/orders/{id}", "method": "GET", "description": "Get order"},
        ],
        protocol="REST",
        version="1.0.0",
    )


@pytest.fixture
def sample_data_model() -> DataModel:
    """Create a sample data model for testing."""
    return DataModel(
        bounded_context="Order Management",
        entities=[
            {
                "name": "Order",
                "attributes": ["id", "customer_id", "total", "status"],
                "relationships": ["has_many OrderLine"],
            },
            {
                "name": "OrderLine",
                "attributes": ["id", "product_id", "quantity", "price"],
                "relationships": ["belongs_to Order"],
            },
        ],
        invariants=["Order total must equal sum of line items"],
    )

@pytest.fixture
def temp_output_dir(tmp_path) -> Path:
    """Create temporary output directory for testing."""
    return tmp_path / "docs" / "design"


@pytest.fixture
def writer() -> DesignWriter:
    """Create DesignWriter instance."""
    return DesignWriter()


# =========================================================================
# 9. DESIGNWRITER: WRITE_DDR TESTS (6 tests)
# =========================================================================


class TestWriteDDR:
    """Tests for DesignWriter.write_ddr method."""

    def test_write_ddr_creates_output_directory(
        self, writer: DesignWriter, temp_output_dir: Path, sample_design_decision: DesignDecision
    ):
        """Test write_ddr creates output directory if needed."""
        assert not temp_output_dir.exists()
        writer.write_ddr(sample_design_decision, temp_output_dir)
        decisions_dir = temp_output_dir / "decisions"
        assert decisions_dir.exists()

    def test_write_ddr_creates_file_with_correct_name(
        self, writer: DesignWriter, temp_output_dir: Path, sample_design_decision: DesignDecision
    ):
        """Test write_ddr creates DDR-NNN.md file."""
        writer.write_ddr(sample_design_decision, temp_output_dir)
        expected_file = temp_output_dir / "decisions" / "DDR-001.md"
        assert expected_file.exists()

    def test_write_ddr_renders_title(
        self, writer: DesignWriter, temp_output_dir: Path, sample_design_decision: DesignDecision
    ):
        """Test write_ddr renders decision title."""
        writer.write_ddr(sample_design_decision, temp_output_dir)
        content = (temp_output_dir / "decisions" / "DDR-001.md").read_text()
        assert "Use CQRS Pattern" in content

    def test_write_ddr_renders_status(
        self, writer: DesignWriter, temp_output_dir: Path, sample_design_decision: DesignDecision
    ):
        """Test write_ddr renders decision status."""
        writer.write_ddr(sample_design_decision, temp_output_dir)
        content = (temp_output_dir / "decisions" / "DDR-001.md").read_text()
        assert "accepted" in content

    def test_write_ddr_renders_context_and_decision(
        self, writer: DesignWriter, temp_output_dir: Path, sample_design_decision: DesignDecision
    ):
        """Test write_ddr renders context, decision, and rationale sections."""
        writer.write_ddr(sample_design_decision, temp_output_dir)
        content = (temp_output_dir / "decisions" / "DDR-001.md").read_text()
        assert "## Context" in content
        assert "## Decision" in content
        assert "## Rationale" in content
        assert "High read frequency" in content
        assert "Implement CQRS" in content
        assert "Independent scaling" in content

    def test_write_ddr_renders_consequences(
        self, writer: DesignWriter, temp_output_dir: Path, sample_design_decision: DesignDecision
    ):
        """Test write_ddr renders consequences list."""
        writer.write_ddr(sample_design_decision, temp_output_dir)
        content = (temp_output_dir / "decisions" / "DDR-001.md").read_text()
        assert "Eventual consistency" in content
        assert "Improved scalability" in content


# =========================================================================
# 10. DESIGNWRITER: WRITE_API_CONTRACT TESTS (5 tests)
# =========================================================================


class TestWriteApiContract:
    """Tests for DesignWriter.write_api_contract method."""

    def test_write_api_contract_creates_contracts_directory(
        self, writer: DesignWriter, temp_output_dir: Path, sample_api_contract: ApiContract
    ):
        """Test write_api_contract creates contracts directory."""
        writer.write_api_contract(sample_api_contract, temp_output_dir)
        contracts_dir = temp_output_dir / "contracts"
        assert contracts_dir.exists()

    def test_write_api_contract_creates_file(
        self, writer: DesignWriter, temp_output_dir: Path, sample_api_contract: ApiContract
    ):
        """Test write_api_contract creates output file."""
        writer.write_api_contract(sample_api_contract, temp_output_dir)
        expected_file = temp_output_dir / "contracts" / "API-order-management.md"
        assert expected_file.exists()

    def test_write_api_contract_renders_bounded_context(
        self, writer: DesignWriter, temp_output_dir: Path, sample_api_contract: ApiContract
    ):
        """Test write_api_contract renders bounded context name."""
        writer.write_api_contract(sample_api_contract, temp_output_dir)
        content = (temp_output_dir / "contracts" / "API-order-management.md").read_text()
        assert "Order Management" in content

    def test_write_api_contract_renders_endpoints(
        self, writer: DesignWriter, temp_output_dir: Path, sample_api_contract: ApiContract
    ):
        """Test write_api_contract renders endpoint details."""
        writer.write_api_contract(sample_api_contract, temp_output_dir)
        content = (temp_output_dir / "contracts" / "API-order-management.md").read_text()
        assert "/orders" in content
        assert "POST" in content
        assert "Create order" in content

    def test_write_api_contract_renders_protocol_and_version(
        self, writer: DesignWriter, temp_output_dir: Path, sample_api_contract: ApiContract
    ):
        """Test write_api_contract renders protocol and version."""
        writer.write_api_contract(sample_api_contract, temp_output_dir)
        content = (temp_output_dir / "contracts" / "API-order-management.md").read_text()
        assert "REST" in content
        assert "1.0.0" in content


# =========================================================================
# 11. DESIGNWRITER: WRITE_DATA_MODEL TESTS (5 tests)
# =========================================================================


class TestWriteDataModel:
    """Tests for DesignWriter.write_data_model method."""

    def test_write_data_model_creates_models_directory(
        self, writer: DesignWriter, temp_output_dir: Path, sample_data_model: DataModel
    ):
        """Test write_data_model creates models directory."""
        writer.write_data_model(sample_data_model, temp_output_dir)
        models_dir = temp_output_dir / "models"
        assert models_dir.exists()

    def test_write_data_model_creates_file(
        self, writer: DesignWriter, temp_output_dir: Path, sample_data_model: DataModel
    ):
        """Test write_data_model creates output file."""
        writer.write_data_model(sample_data_model, temp_output_dir)
        expected_file = temp_output_dir / "models" / "DM-order-management.md"
        assert expected_file.exists()

    def test_write_data_model_renders_bounded_context(
        self, writer: DesignWriter, temp_output_dir: Path, sample_data_model: DataModel
    ):
        """Test write_data_model renders bounded context name."""
        writer.write_data_model(sample_data_model, temp_output_dir)
        content = (temp_output_dir / "models" / "DM-order-management.md").read_text()
        assert "Order Management" in content

    def test_write_data_model_renders_entities(
        self, writer: DesignWriter, temp_output_dir: Path, sample_data_model: DataModel
    ):
        """Test write_data_model renders entity definitions."""
        writer.write_data_model(sample_data_model, temp_output_dir)
        content = (temp_output_dir / "models" / "DM-order-management.md").read_text()
        assert "Order" in content
        assert "OrderLine" in content

    def test_write_data_model_renders_invariants(
        self, writer: DesignWriter, temp_output_dir: Path, sample_data_model: DataModel
    ):
        """Test write_data_model renders invariants."""
        writer.write_data_model(sample_data_model, temp_output_dir)
        content = (temp_output_dir / "models" / "DM-order-management.md").read_text()
        assert "Order total must equal sum of line items" in content


# =========================================================================
# 12. DESIGNWRITER: WRITE_COMPONENT_DIAGRAM TESTS (4 tests)
# =========================================================================


class TestWriteComponentDiagram:
    """Tests for DesignWriter.write_component_diagram method."""

    def test_write_component_diagram_creates_diagrams_directory(
        self, writer: DesignWriter, temp_output_dir: Path
    ):
        """Test write_component_diagram creates diagrams directory."""
        components = [
            {"name": "OrderService", "description": "Handles orders"},
            {"name": "PaymentService", "description": "Processes payments"},
        ]
        writer.write_component_diagram("Order Management", components, temp_output_dir)
        diagrams_dir = temp_output_dir / "diagrams"
        assert diagrams_dir.exists()

    def test_write_component_diagram_creates_file(
        self, writer: DesignWriter, temp_output_dir: Path
    ):
        """Test write_component_diagram creates output file."""
        components = [
            {"name": "OrderService", "description": "Handles orders"},
        ]
        writer.write_component_diagram("Order Management", components, temp_output_dir)
        # File should be named based on container slug
        files = list((temp_output_dir / "diagrams").glob("*.md"))
        assert len(files) >= 1

    def test_write_component_diagram_renders_container_name(
        self, writer: DesignWriter, temp_output_dir: Path
    ):
        """Test write_component_diagram renders container name."""
        components = [
            {"name": "OrderService", "description": "Handles orders"},
        ]
        writer.write_component_diagram("Order Management", components, temp_output_dir)
        files = list((temp_output_dir / "diagrams").glob("*.md"))
        content = files[0].read_text()
        assert "Order Management" in content

    def test_write_component_diagram_renders_mermaid(
        self, writer: DesignWriter, temp_output_dir: Path
    ):
        """Test write_component_diagram renders mermaid diagram."""
        components = [
            {"name": "OrderService", "description": "Handles orders"},
            {"name": "PaymentService", "description": "Processes payments"},
        ]
        writer.write_component_diagram("Order Management", components, temp_output_dir)
        files = list((temp_output_dir / "diagrams").glob("*.md"))
        content = files[0].read_text()
        assert "OrderService" in content
        assert "PaymentService" in content


# =========================================================================
# 13. SCAN_NEXT_DDR_NUMBER TESTS (5 tests)
# =========================================================================


class TestScanNextDDRNumber:
    """Tests for scan_next_ddr_number helper function."""

    def test_scan_next_ddr_number_returns_1_for_empty_dir(self, tmp_path: Path):
        """Test scan_next_ddr_number returns 1 when no DDR files exist."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir()
        result = scan_next_ddr_number(decisions_dir)
        assert result == 1

    def test_scan_next_ddr_number_returns_1_for_nonexistent_dir(self, tmp_path: Path):
        """Test scan_next_ddr_number returns 1 when directory doesn't exist."""
        decisions_dir = tmp_path / "decisions"
        result = scan_next_ddr_number(decisions_dir)
        assert result == 1

    def test_scan_next_ddr_number_finds_max_number(self, tmp_path: Path):
        """Test scan_next_ddr_number finds the max DDR number."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir()
        (decisions_dir / "DDR-001.md").write_text("# DDR-001")
        (decisions_dir / "DDR-002.md").write_text("# DDR-002")
        (decisions_dir / "DDR-003.md").write_text("# DDR-003")
        result = scan_next_ddr_number(decisions_dir)
        assert result == 4

    def test_scan_next_ddr_number_ignores_non_ddr_files(self, tmp_path: Path):
        """Test scan_next_ddr_number ignores non-DDR files."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir()
        (decisions_dir / "DDR-001.md").write_text("# DDR-001")
        (decisions_dir / "README.md").write_text("# README")
        (decisions_dir / "ADR-SP-001.md").write_text("# ADR")
        result = scan_next_ddr_number(decisions_dir)
        assert result == 2

    def test_scan_next_ddr_number_handles_gaps(self, tmp_path: Path):
        """Test scan_next_ddr_number handles gaps in numbering."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir()
        (decisions_dir / "DDR-001.md").write_text("# DDR-001")
        (decisions_dir / "DDR-005.md").write_text("# DDR-005")
        result = scan_next_ddr_number(decisions_dir)
        assert result == 6


# =========================================================================
# 14. INTEGRATION: CREATE + WRITE TESTS (3 tests)
# =========================================================================


class TestIntegration:
    """Integration tests: create entities, write via DesignWriter, verify output."""

    def test_create_design_decision_and_write(
        self, writer: DesignWriter, temp_output_dir: Path
    ):
        """Test creating a DesignDecision and writing it produces valid output."""
        decision = DesignDecision(
            number=1,
            title="Use Event Sourcing",
            context="Need complete audit trail",
            decision="Implement event sourcing for orders",
            rationale="Full history and temporal queries",
            consequences=["Complete audit", "Complex replay"],
            related_components=["Order Management"],
            status="accepted",
        )
        writer.write_ddr(decision, temp_output_dir)

        output_file = temp_output_dir / "decisions" / "DDR-001.md"
        assert output_file.exists()
        content = output_file.read_text()
        assert "DDR-001" in content
        assert "Use Event Sourcing" in content
        assert "## Context" in content
        assert "## Decision" in content
        assert "## Rationale" in content
        assert "## Consequences" in content

    def test_create_api_contract_and_write(
        self, writer: DesignWriter, temp_output_dir: Path
    ):
        """Test creating an ApiContract and writing it produces valid output."""
        contract = ApiContract(
            bounded_context="Payment Gateway",
            consumer_types=["web-frontend", "mobile-app"],
            endpoints=[
                {"path": "/payments", "method": "POST", "description": "Process payment"},
                {"path": "/payments/{id}", "method": "GET", "description": "Get payment"},
            ],
            protocol="REST",
            version="2.0.0",
        )
        writer.write_api_contract(contract, temp_output_dir)

        output_file = temp_output_dir / "contracts" / "API-payment-gateway.md"
        assert output_file.exists()
        content = output_file.read_text()
        assert "Payment Gateway" in content
        assert "/payments" in content
        assert "REST" in content
        assert "2.0.0" in content

    def test_create_data_model_and_write(
        self, writer: DesignWriter, temp_output_dir: Path
    ):
        """Test creating a DataModel and writing it produces valid output."""
        model = DataModel(
            bounded_context="Inventory",
            entities=[
                {
                    "name": "Product",
                    "attributes": ["id", "name", "sku", "price"],
                    "relationships": ["has_many StockLevel"],
                },
            ],
            invariants=["SKU must be unique", "Price must be positive"],
        )
        writer.write_data_model(model, temp_output_dir)

        output_file = temp_output_dir / "models" / "DM-inventory.md"
        assert output_file.exists()
        content = output_file.read_text()
        assert "Inventory" in content
        assert "Product" in content
        assert "SKU must be unique" in content


