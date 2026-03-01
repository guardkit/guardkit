"""Tests for design entity definitions (TASK-SAD-003).

Verifies the data model layer for /system-design entities following
ADR-GBF-001 convention (domain data only, no _metadata in to_episode_body()).

Coverage Target: >=85%

Entities tested:
- DesignDecision: Stable entity_id (format: DDR-{NNN})
- ApiContract: Stable entity_id (format: API-{bounded_context_slug})
- DataModel: Stable entity_id (format: DM-{bounded_context_slug})
"""

import json
import pytest

from guardkit.knowledge.entities.design_decision import DesignDecision
from guardkit.knowledge.entities.api_contract import ApiContract
from guardkit.knowledge.entities.data_model import DataModel


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def sample_design_decision() -> DesignDecision:
    """Create a sample design decision record."""
    return DesignDecision(
        number=1,
        title="Use CQRS Pattern for Read/Write Separation",
        context="The Order aggregate has high read frequency and complex write operations",
        decision="Implement CQRS to separate command and query responsibilities",
        rationale="CQRS allows independent scaling of reads and writes",
        alternatives_considered=["Simple CRUD", "Event Sourcing only"],
        consequences=["Eventual consistency", "Two data models to maintain"],
        related_components=["Order Management", "Reporting"],
        status="accepted",
    )


@pytest.fixture
def sample_api_contract() -> ApiContract:
    """Create a sample API contract."""
    return ApiContract(
        bounded_context="Order Management",
        consumer_types=["web-frontend", "mobile-app", "internal-service"],
        endpoints=[
            {
                "path": "/orders",
                "method": "POST",
                "description": "Create a new order",
            },
            {
                "path": "/orders/{id}",
                "method": "GET",
                "description": "Get order by ID",
            },
        ],
        protocol="REST",
        version="1.0.0",
    )


@pytest.fixture
def sample_data_model() -> DataModel:
    """Create a sample data model."""
    return DataModel(
        bounded_context="Order Management",
        entities=[
            {
                "name": "Order",
                "attributes": ["id", "customer_id", "total", "status"],
                "relationships": ["has_many OrderLine", "belongs_to Customer"],
            },
            {
                "name": "OrderLine",
                "attributes": ["id", "order_id", "product_id", "quantity", "price"],
                "relationships": ["belongs_to Order", "belongs_to Product"],
            },
        ],
        invariants=[
            "Order total must equal sum of line items",
            "Order must have at least one line item",
        ],
    )


# =========================================================================
# 1. DESIGNDECISION TESTS
# =========================================================================


class TestDesignDecision:
    """Tests for DesignDecision dataclass."""

    def test_basic_instantiation(self, sample_design_decision: DesignDecision):
        """Test basic DDR creation with all fields."""
        assert sample_design_decision.number == 1
        assert sample_design_decision.title == "Use CQRS Pattern for Read/Write Separation"
        assert sample_design_decision.status == "accepted"
        assert len(sample_design_decision.alternatives_considered) == 2
        assert len(sample_design_decision.consequences) == 2
        assert len(sample_design_decision.related_components) == 2

    def test_entity_id_format(self, sample_design_decision: DesignDecision):
        """Test entity_id follows format: DDR-{NNN}."""
        entity_id = sample_design_decision.entity_id
        assert entity_id.startswith("DDR-")
        assert entity_id == "DDR-001"

    def test_entity_id_padding(self):
        """Test entity_id number is zero-padded to 3 digits."""
        ddr_single = DesignDecision(
            number=5,
            title="Test",
            context="ctx",
            decision="dec",
            rationale="rat",
            status="accepted",
        )
        assert ddr_single.entity_id == "DDR-005"

        ddr_double = DesignDecision(
            number=42,
            title="Test",
            context="ctx",
            decision="dec",
            rationale="rat",
            status="accepted",
        )
        assert ddr_double.entity_id == "DDR-042"

        ddr_triple = DesignDecision(
            number=123,
            title="Test",
            context="ctx",
            decision="dec",
            rationale="rat",
            status="accepted",
        )
        assert ddr_triple.entity_id == "DDR-123"

    def test_entity_id_is_deterministic(self):
        """Test same number produces same entity_id."""
        ddr1 = DesignDecision(
            number=7,
            title="Title A",
            context="ctx",
            decision="dec",
            rationale="rat",
            status="accepted",
        )
        ddr2 = DesignDecision(
            number=7,
            title="Title B",
            context="different",
            decision="different",
            rationale="different",
            status="proposed",
        )
        assert ddr1.entity_id == ddr2.entity_id

    def test_to_episode_body_structure(self, sample_design_decision: DesignDecision):
        """Test episode body has correct structure with all fields."""
        body = sample_design_decision.to_episode_body()

        assert body["number"] == 1
        assert body["title"] == "Use CQRS Pattern for Read/Write Separation"
        assert body["status"] == "accepted"
        assert "high read frequency" in body["context"]
        assert "CQRS" in body["decision"]
        assert body["rationale"] == "CQRS allows independent scaling of reads and writes"
        assert body["alternatives_considered"] == ["Simple CRUD", "Event Sourcing only"]
        assert body["consequences"] == ["Eventual consistency", "Two data models to maintain"]
        assert body["related_components"] == ["Order Management", "Reporting"]

    def test_to_episode_body_no_metadata(self, sample_design_decision: DesignDecision):
        """Test episode body has no _metadata (ADR-GBF-001)."""
        body = sample_design_decision.to_episode_body()
        assert "_metadata" not in body
        assert "entity_type" not in body
        assert "created_at" not in body

    def test_to_episode_body_is_json_serializable(
        self, sample_design_decision: DesignDecision
    ):
        """Test episode body can be serialized to JSON."""
        body = sample_design_decision.to_episode_body()
        json_str = json.dumps(body)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["title"] == "Use CQRS Pattern for Read/Write Separation"

    def test_to_episode_body_excludes_empty_optional_fields(self):
        """Test to_episode_body excludes superseded_by and supersedes when None."""
        ddr = DesignDecision(
            number=1,
            title="Test",
            context="ctx",
            decision="dec",
            rationale="rat",
            status="accepted",
        )
        body = ddr.to_episode_body()
        assert "superseded_by" not in body
        assert "supersedes" not in body

    def test_to_episode_body_includes_superseded_by_when_set(self):
        """Test to_episode_body includes superseded_by when not None."""
        ddr = DesignDecision(
            number=1,
            title="Test",
            context="ctx",
            decision="dec",
            rationale="rat",
            status="superseded",
            superseded_by="DDR-005",
        )
        body = ddr.to_episode_body()
        assert body["superseded_by"] == "DDR-005"

    def test_to_episode_body_includes_supersedes_when_set(self):
        """Test to_episode_body includes supersedes when not None."""
        ddr = DesignDecision(
            number=5,
            title="Test",
            context="ctx",
            decision="dec",
            rationale="rat",
            status="accepted",
            supersedes="DDR-001",
        )
        body = ddr.to_episode_body()
        assert body["supersedes"] == "DDR-001"

    def test_to_episode_body_excludes_empty_alternatives(self):
        """Test to_episode_body excludes alternatives_considered when empty."""
        ddr = DesignDecision(
            number=1,
            title="Test",
            context="ctx",
            decision="dec",
            rationale="rat",
            status="accepted",
            alternatives_considered=[],
        )
        body = ddr.to_episode_body()
        assert "alternatives_considered" not in body

    def test_to_episode_body_includes_nonempty_alternatives(self):
        """Test to_episode_body includes alternatives_considered when non-empty."""
        ddr = DesignDecision(
            number=1,
            title="Test",
            context="ctx",
            decision="dec",
            rationale="rat",
            status="accepted",
            alternatives_considered=["Option A"],
        )
        body = ddr.to_episode_body()
        assert body["alternatives_considered"] == ["Option A"]

    def test_defaults_for_optional_fields(self):
        """Test optional fields default correctly."""
        ddr = DesignDecision(
            number=1,
            title="Test",
            context="ctx",
            decision="dec",
            rationale="rat",
            status="accepted",
        )
        assert ddr.alternatives_considered == []
        assert ddr.consequences == []
        assert ddr.related_components == []
        assert ddr.superseded_by is None
        assert ddr.supersedes is None

    def test_mutable_defaults_no_shared_state(self):
        """Test mutable defaults don't share state between instances."""
        ddr1 = DesignDecision(
            number=1, title="T1", context="c", decision="d",
            rationale="r", status="accepted",
        )
        ddr2 = DesignDecision(
            number=2, title="T2", context="c", decision="d",
            rationale="r", status="accepted",
        )
        ddr1.alternatives_considered.append("Modified")
        assert len(ddr2.alternatives_considered) == 0

    def test_valid_status_values(self):
        """Test DDR accepts valid status values."""
        for status in ["proposed", "accepted", "deprecated", "superseded"]:
            ddr = DesignDecision(
                number=1,
                title="Test",
                context="ctx",
                decision="dec",
                rationale="rat",
                status=status,
            )
            assert ddr.status == status

    def test_frozen_dataclass(self, sample_design_decision: DesignDecision):
        """Test DesignDecision is a frozen dataclass (immutable)."""
        with pytest.raises(AttributeError):
            sample_design_decision.title = "Modified Title"


# =========================================================================
# 2. APICONTRACT TESTS
# =========================================================================


class TestApiContract:
    """Tests for ApiContract dataclass."""

    def test_basic_instantiation(self, sample_api_contract: ApiContract):
        """Test basic API contract creation."""
        assert sample_api_contract.bounded_context == "Order Management"
        assert sample_api_contract.protocol == "REST"
        assert sample_api_contract.version == "1.0.0"
        assert len(sample_api_contract.consumer_types) == 3
        assert len(sample_api_contract.endpoints) == 2

    def test_entity_id_format(self, sample_api_contract: ApiContract):
        """Test entity_id follows format: API-{bounded_context_slug}."""
        entity_id = sample_api_contract.entity_id
        assert entity_id.startswith("API-")
        assert entity_id == "API-order-management"

    def test_entity_id_is_deterministic(self):
        """Test same bounded_context produces same entity_id."""
        api1 = ApiContract(
            bounded_context="Order Management",
            consumer_types=["web"],
            endpoints=[],
            protocol="REST",
            version="1.0.0",
        )
        api2 = ApiContract(
            bounded_context="Order Management",
            consumer_types=["mobile"],
            endpoints=[{"path": "/test", "method": "GET", "description": "test"}],
            protocol="GraphQL",
            version="2.0.0",
        )
        assert api1.entity_id == api2.entity_id

    def test_entity_id_slug_truncation(self):
        """Test entity_id slug is truncated to 30 chars."""
        api = ApiContract(
            bounded_context="This Is A Very Long Bounded Context Name Exceeding Thirty Characters",
            consumer_types=[],
            endpoints=[],
            protocol="REST",
            version="1.0.0",
        )
        slug = api.entity_id.replace("API-", "")
        assert len(slug) <= 30

    def test_to_episode_body_structure(self, sample_api_contract: ApiContract):
        """Test episode body has correct structure."""
        body = sample_api_contract.to_episode_body()

        assert body["bounded_context"] == "Order Management"
        assert body["consumer_types"] == ["web-frontend", "mobile-app", "internal-service"]
        assert len(body["endpoints"]) == 2
        assert body["protocol"] == "REST"
        assert body["version"] == "1.0.0"

    def test_to_episode_body_no_metadata(self, sample_api_contract: ApiContract):
        """Test episode body has no _metadata (ADR-GBF-001)."""
        body = sample_api_contract.to_episode_body()
        assert "_metadata" not in body
        assert "entity_type" not in body
        assert "created_at" not in body

    def test_to_episode_body_is_json_serializable(
        self, sample_api_contract: ApiContract
    ):
        """Test episode body can be serialized to JSON."""
        body = sample_api_contract.to_episode_body()
        json_str = json.dumps(body)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["bounded_context"] == "Order Management"

    def test_supported_protocols(self):
        """Test API contract accepts all supported protocols."""
        for protocol in ["REST", "GraphQL", "MCP", "A2A", "ACP"]:
            api = ApiContract(
                bounded_context="Test",
                consumer_types=["web"],
                endpoints=[],
                protocol=protocol,
                version="1.0.0",
            )
            assert api.protocol == protocol

    def test_defaults_for_optional_fields(self):
        """Test optional fields default correctly."""
        api = ApiContract(
            bounded_context="Test",
            protocol="REST",
            version="1.0.0",
        )
        assert api.consumer_types == []
        assert api.endpoints == []

    def test_mutable_defaults_no_shared_state(self):
        """Test mutable defaults don't share state between instances."""
        api1 = ApiContract(
            bounded_context="Test1",
            protocol="REST",
            version="1.0.0",
        )
        api2 = ApiContract(
            bounded_context="Test2",
            protocol="REST",
            version="1.0.0",
        )
        api1.consumer_types.append("web")
        assert len(api2.consumer_types) == 0

    def test_frozen_dataclass(self, sample_api_contract: ApiContract):
        """Test ApiContract is a frozen dataclass (immutable)."""
        with pytest.raises(AttributeError):
            sample_api_contract.protocol = "GraphQL"

    def test_entity_id_special_chars_in_context(self):
        """Test entity_id handles special chars in bounded_context."""
        api = ApiContract(
            bounded_context="Auth/Login (Main)",
            consumer_types=[],
            endpoints=[],
            protocol="REST",
            version="1.0.0",
        )
        entity_id = api.entity_id
        assert "/" not in entity_id
        assert "(" not in entity_id
        assert ")" not in entity_id
        assert entity_id.startswith("API-")


# =========================================================================
# 3. DATAMODEL TESTS
# =========================================================================


class TestDataModel:
    """Tests for DataModel dataclass."""

    def test_basic_instantiation(self, sample_data_model: DataModel):
        """Test basic data model creation."""
        assert sample_data_model.bounded_context == "Order Management"
        assert len(sample_data_model.entities) == 2
        assert len(sample_data_model.invariants) == 2

    def test_entity_id_format(self, sample_data_model: DataModel):
        """Test entity_id follows format: DM-{bounded_context_slug}."""
        entity_id = sample_data_model.entity_id
        assert entity_id.startswith("DM-")
        assert entity_id == "DM-order-management"

    def test_entity_id_is_deterministic(self):
        """Test same bounded_context produces same entity_id."""
        dm1 = DataModel(
            bounded_context="Order Management",
            entities=[{"name": "Order", "attributes": [], "relationships": []}],
            invariants=["inv1"],
        )
        dm2 = DataModel(
            bounded_context="Order Management",
            entities=[{"name": "Customer", "attributes": [], "relationships": []}],
            invariants=["inv2", "inv3"],
        )
        assert dm1.entity_id == dm2.entity_id

    def test_entity_id_slug_truncation(self):
        """Test entity_id slug is truncated to 30 chars."""
        dm = DataModel(
            bounded_context="This Is A Very Long Bounded Context Name Exceeding Thirty Characters",
            entities=[],
            invariants=[],
        )
        slug = dm.entity_id.replace("DM-", "")
        assert len(slug) <= 30

    def test_to_episode_body_structure(self, sample_data_model: DataModel):
        """Test episode body has correct structure."""
        body = sample_data_model.to_episode_body()

        assert body["bounded_context"] == "Order Management"
        assert len(body["entities"]) == 2
        assert body["entities"][0]["name"] == "Order"
        assert "id" in body["entities"][0]["attributes"]
        assert body["invariants"] == [
            "Order total must equal sum of line items",
            "Order must have at least one line item",
        ]

    def test_to_episode_body_no_metadata(self, sample_data_model: DataModel):
        """Test episode body has no _metadata (ADR-GBF-001)."""
        body = sample_data_model.to_episode_body()
        assert "_metadata" not in body
        assert "entity_type" not in body
        assert "created_at" not in body

    def test_to_episode_body_is_json_serializable(
        self, sample_data_model: DataModel
    ):
        """Test episode body can be serialized to JSON."""
        body = sample_data_model.to_episode_body()
        json_str = json.dumps(body)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["bounded_context"] == "Order Management"

    def test_defaults_for_optional_fields(self):
        """Test optional fields default correctly."""
        dm = DataModel(
            bounded_context="Test",
        )
        assert dm.entities == []
        assert dm.invariants == []

    def test_mutable_defaults_no_shared_state(self):
        """Test mutable defaults don't share state between instances."""
        dm1 = DataModel(bounded_context="Test1")
        dm2 = DataModel(bounded_context="Test2")
        dm1.entities.append({"name": "Added", "attributes": [], "relationships": []})
        assert len(dm2.entities) == 0

    def test_frozen_dataclass(self, sample_data_model: DataModel):
        """Test DataModel is a frozen dataclass (immutable)."""
        with pytest.raises(AttributeError):
            sample_data_model.bounded_context = "Modified"

    def test_entity_id_special_chars_in_context(self):
        """Test entity_id handles special chars in bounded_context."""
        dm = DataModel(
            bounded_context="Auth/Login (Main)",
            entities=[],
            invariants=[],
        )
        entity_id = dm.entity_id
        assert "/" not in entity_id
        assert "(" not in entity_id
        assert ")" not in entity_id
        assert entity_id.startswith("DM-")

    def test_entity_dict_structure(self):
        """Test entities list contains dicts with name, attributes, relationships."""
        dm = DataModel(
            bounded_context="Test",
            entities=[
                {
                    "name": "User",
                    "attributes": ["id", "email", "name"],
                    "relationships": ["has_many Post"],
                }
            ],
            invariants=[],
        )
        body = dm.to_episode_body()
        entity = body["entities"][0]
        assert "name" in entity
        assert "attributes" in entity
        assert "relationships" in entity
