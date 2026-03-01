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

from guardkit.planning.graphiti_design import SystemDesignGraphiti
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
def graphiti_service(mock_client: MagicMock) -> SystemDesignGraphiti:
    """Create a SystemDesignGraphiti instance with mock client."""
    return SystemDesignGraphiti(client=mock_client, project_id="test-project")


@pytest.fixture
def graphiti_service_disabled(mock_client_disabled: MagicMock) -> SystemDesignGraphiti:
    """Create a SystemDesignGraphiti instance with disabled client."""
    return SystemDesignGraphiti(client=mock_client_disabled, project_id="test-project")


@pytest.fixture
def graphiti_service_null() -> SystemDesignGraphiti:
    """Create a SystemDesignGraphiti instance with null client."""
    return SystemDesignGraphiti(client=None, project_id="test-project")


@pytest.fixture
def temp_output_dir(tmp_path) -> Path:
    """Create temporary output directory for testing."""
    return tmp_path / "docs" / "design"


@pytest.fixture
def writer() -> DesignWriter:
    """Create DesignWriter instance."""
    return DesignWriter()


# =========================================================================
# 1. SYSTEMDESIGNGRAPHITI: CONSTRUCTOR AND AVAILABILITY (5 tests)
# =========================================================================


class TestSDGConstructorAndAvailability:
    """Tests for SystemDesignGraphiti constructor and _available property."""

    def test_constructor_with_client_and_project_id(self, mock_client: MagicMock):
        """Test constructor accepts client and project_id."""
        service = SystemDesignGraphiti(client=mock_client, project_id="my-project")
        assert service._client is mock_client
        assert service._project_id == "my-project"

    def test_constructor_with_none_client(self):
        """Test constructor accepts None client."""
        service = SystemDesignGraphiti(client=None, project_id="my-project")
        assert service._client is None
        assert service._project_id == "my-project"

    def test_available_true_when_client_enabled(self, graphiti_service):
        """Test _available returns True when client exists and is enabled."""
        assert graphiti_service._available is True

    def test_available_false_when_client_disabled(self, graphiti_service_disabled):
        """Test _available returns False when client is disabled."""
        assert graphiti_service_disabled._available is False

    def test_available_false_when_client_none(self, graphiti_service_null):
        """Test _available returns False when client is None."""
        assert graphiti_service_null._available is False

    def test_group_constants(self):
        """Test GROUP constants are defined correctly."""
        assert SystemDesignGraphiti.DESIGN_GROUP == "project_design"
        assert SystemDesignGraphiti.CONTRACTS_GROUP == "api_contracts"


# =========================================================================
# 2. UPSERT_DESIGN_DECISION TESTS (8 tests)
# =========================================================================


class TestUpsertDesignDecision:
    """Tests for upsert_design_decision method."""

    @pytest.mark.asyncio
    async def test_upsert_design_decision_calls_upsert_episode(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_design_decision: DesignDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_design_decision uses upsert_episode (NOT add_episode)."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-ddr1"))
        result = await graphiti_service.upsert_design_decision(sample_design_decision)
        mock_client.upsert_episode.assert_called_once()
        assert result == "uuid-ddr1"

    @pytest.mark.asyncio
    async def test_upsert_design_decision_uses_correct_group_id(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_design_decision: DesignDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_design_decision uses get_group_id for project_design group."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-ddr1"))
        await graphiti_service.upsert_design_decision(sample_design_decision)
        mock_client.get_group_id.assert_called_with("project_design")
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["group_id"] == "test-project__project_design"

    @pytest.mark.asyncio
    async def test_upsert_design_decision_uses_stable_entity_id(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_design_decision: DesignDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_design_decision uses DDR-NNN entity_id format."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-ddr1"))
        await graphiti_service.upsert_design_decision(sample_design_decision)
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_id"] == "DDR-001"

    @pytest.mark.asyncio
    async def test_upsert_design_decision_uses_json_episode_body(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_design_decision: DesignDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_design_decision passes JSON-serialized episode body."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-ddr1"))
        await graphiti_service.upsert_design_decision(sample_design_decision)
        call_kwargs = mock_client.upsert_episode.call_args[1]
        parsed = json.loads(call_kwargs["episode_body"])
        assert parsed["title"] == "Use CQRS Pattern"
        assert parsed["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_upsert_design_decision_returns_none_when_disabled(
        self,
        graphiti_service_disabled: SystemDesignGraphiti,
        sample_design_decision: DesignDecision,
    ):
        """Test upsert_design_decision returns None when client is disabled."""
        result = await graphiti_service_disabled.upsert_design_decision(sample_design_decision)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_design_decision_returns_none_when_client_none(
        self,
        graphiti_service_null: SystemDesignGraphiti,
        sample_design_decision: DesignDecision,
    ):
        """Test upsert_design_decision returns None when client is None."""
        result = await graphiti_service_null.upsert_design_decision(sample_design_decision)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_design_decision_returns_none_on_exception(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_design_decision: DesignDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_design_decision returns None and logs on exception."""
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("Network error"))
        with patch("guardkit.planning.graphiti_design.logger") as mock_logger:
            result = await graphiti_service.upsert_design_decision(sample_design_decision)
            assert result is None
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_upsert_design_decision_sets_design_decision_entity_type(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_design_decision: DesignDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_design_decision sets entity_type to 'design_decision'."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-ddr1"))
        await graphiti_service.upsert_design_decision(sample_design_decision)
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_type"] == "design_decision"


# =========================================================================
# 3. UPSERT_API_CONTRACT TESTS (8 tests)
# =========================================================================


class TestUpsertApiContract:
    """Tests for upsert_api_contract method."""

    @pytest.mark.asyncio
    async def test_upsert_api_contract_calls_upsert_episode(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_api_contract: ApiContract,
        mock_client: MagicMock,
    ):
        """Test upsert_api_contract uses upsert_episode."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-api1"))
        result = await graphiti_service.upsert_api_contract(sample_api_contract)
        mock_client.upsert_episode.assert_called_once()
        assert result == "uuid-api1"

    @pytest.mark.asyncio
    async def test_upsert_api_contract_uses_api_contracts_group(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_api_contract: ApiContract,
        mock_client: MagicMock,
    ):
        """Test upsert_api_contract uses 'api_contracts' group."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-api1"))
        await graphiti_service.upsert_api_contract(sample_api_contract)
        mock_client.get_group_id.assert_called_with("api_contracts")
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["group_id"] == "test-project__api_contracts"

    @pytest.mark.asyncio
    async def test_upsert_api_contract_uses_stable_entity_id(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_api_contract: ApiContract,
        mock_client: MagicMock,
    ):
        """Test upsert_api_contract uses API-{slug} entity_id format."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-api1"))
        await graphiti_service.upsert_api_contract(sample_api_contract)
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_id"] == "API-order-management"

    @pytest.mark.asyncio
    async def test_upsert_api_contract_uses_json_episode_body(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_api_contract: ApiContract,
        mock_client: MagicMock,
    ):
        """Test upsert_api_contract passes JSON-serialized episode body."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-api1"))
        await graphiti_service.upsert_api_contract(sample_api_contract)
        call_kwargs = mock_client.upsert_episode.call_args[1]
        parsed = json.loads(call_kwargs["episode_body"])
        assert parsed["bounded_context"] == "Order Management"
        assert parsed["protocol"] == "REST"

    @pytest.mark.asyncio
    async def test_upsert_api_contract_returns_none_when_disabled(
        self,
        graphiti_service_disabled: SystemDesignGraphiti,
        sample_api_contract: ApiContract,
    ):
        """Test upsert_api_contract returns None when client is disabled."""
        result = await graphiti_service_disabled.upsert_api_contract(sample_api_contract)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_api_contract_returns_none_when_client_none(
        self,
        graphiti_service_null: SystemDesignGraphiti,
        sample_api_contract: ApiContract,
    ):
        """Test upsert_api_contract returns None when client is None."""
        result = await graphiti_service_null.upsert_api_contract(sample_api_contract)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_api_contract_returns_none_on_exception(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_api_contract: ApiContract,
        mock_client: MagicMock,
    ):
        """Test upsert_api_contract returns None and logs on exception."""
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("DB error"))
        with patch("guardkit.planning.graphiti_design.logger") as mock_logger:
            result = await graphiti_service.upsert_api_contract(sample_api_contract)
            assert result is None
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_upsert_api_contract_sets_api_contract_entity_type(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_api_contract: ApiContract,
        mock_client: MagicMock,
    ):
        """Test upsert_api_contract sets entity_type to 'api_contract'."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-api1"))
        await graphiti_service.upsert_api_contract(sample_api_contract)
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_type"] == "api_contract"


# =========================================================================
# 4. UPSERT_DATA_MODEL TESTS (8 tests)
# =========================================================================


class TestUpsertDataModel:
    """Tests for upsert_data_model method."""

    @pytest.mark.asyncio
    async def test_upsert_data_model_calls_upsert_episode(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_data_model: DataModel,
        mock_client: MagicMock,
    ):
        """Test upsert_data_model uses upsert_episode."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-dm1"))
        result = await graphiti_service.upsert_data_model(sample_data_model)
        mock_client.upsert_episode.assert_called_once()
        assert result == "uuid-dm1"

    @pytest.mark.asyncio
    async def test_upsert_data_model_uses_project_design_group(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_data_model: DataModel,
        mock_client: MagicMock,
    ):
        """Test upsert_data_model uses 'project_design' group."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-dm1"))
        await graphiti_service.upsert_data_model(sample_data_model)
        mock_client.get_group_id.assert_called_with("project_design")
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["group_id"] == "test-project__project_design"

    @pytest.mark.asyncio
    async def test_upsert_data_model_uses_stable_entity_id(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_data_model: DataModel,
        mock_client: MagicMock,
    ):
        """Test upsert_data_model uses DM-{slug} entity_id format."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-dm1"))
        await graphiti_service.upsert_data_model(sample_data_model)
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_id"] == "DM-order-management"

    @pytest.mark.asyncio
    async def test_upsert_data_model_uses_json_episode_body(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_data_model: DataModel,
        mock_client: MagicMock,
    ):
        """Test upsert_data_model passes JSON-serialized episode body."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-dm1"))
        await graphiti_service.upsert_data_model(sample_data_model)
        call_kwargs = mock_client.upsert_episode.call_args[1]
        parsed = json.loads(call_kwargs["episode_body"])
        assert parsed["bounded_context"] == "Order Management"
        assert len(parsed["entities"]) == 2

    @pytest.mark.asyncio
    async def test_upsert_data_model_returns_none_when_disabled(
        self,
        graphiti_service_disabled: SystemDesignGraphiti,
        sample_data_model: DataModel,
    ):
        """Test upsert_data_model returns None when client is disabled."""
        result = await graphiti_service_disabled.upsert_data_model(sample_data_model)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_data_model_returns_none_when_client_none(
        self,
        graphiti_service_null: SystemDesignGraphiti,
        sample_data_model: DataModel,
    ):
        """Test upsert_data_model returns None when client is None."""
        result = await graphiti_service_null.upsert_data_model(sample_data_model)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_data_model_returns_none_on_exception(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_data_model: DataModel,
        mock_client: MagicMock,
    ):
        """Test upsert_data_model returns None and logs on exception."""
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("Timeout"))
        with patch("guardkit.planning.graphiti_design.logger") as mock_logger:
            result = await graphiti_service.upsert_data_model(sample_data_model)
            assert result is None
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_upsert_data_model_sets_data_model_entity_type(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_data_model: DataModel,
        mock_client: MagicMock,
    ):
        """Test upsert_data_model sets entity_type to 'data_model'."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-dm1"))
        await graphiti_service.upsert_data_model(sample_data_model)
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_type"] == "data_model"


# =========================================================================
# 5. SEARCH_DESIGN_CONTEXT TESTS (6 tests)
# =========================================================================


class TestSearchDesignContext:
    """Tests for search_design_context method."""

    @pytest.mark.asyncio
    async def test_search_design_context_returns_list(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test search_design_context returns list of results."""
        mock_client.search = AsyncMock(
            return_value=[
                {"fact": "CQRS pattern chosen", "uuid": "1", "score": 0.9},
                {"fact": "REST API for orders", "uuid": "2", "score": 0.8},
            ]
        )
        result = await graphiti_service.search_design_context("order processing", num_results=5)
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_design_context_uses_topic_as_query(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test search_design_context uses query parameter."""
        mock_client.search = AsyncMock(return_value=[])
        await graphiti_service.search_design_context("payment processing", num_results=5)
        call_args = mock_client.search.call_args
        assert "payment processing" in str(call_args)

    @pytest.mark.asyncio
    async def test_search_design_context_uses_num_results(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test search_design_context passes num_results to search."""
        mock_client.search = AsyncMock(return_value=[])
        await graphiti_service.search_design_context("test", num_results=10)
        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["num_results"] == 10

    @pytest.mark.asyncio
    async def test_search_design_context_searches_both_groups(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test search_design_context searches design and contracts groups."""
        mock_client.search = AsyncMock(return_value=[])
        await graphiti_service.search_design_context("test", num_results=5)
        call_kwargs = mock_client.search.call_args[1]
        assert "group_ids" in call_kwargs
        group_ids = call_kwargs["group_ids"]
        assert "test-project__project_design" in group_ids
        assert "test-project__api_contracts" in group_ids

    @pytest.mark.asyncio
    async def test_search_design_context_returns_empty_list_when_disabled(
        self, graphiti_service_disabled: SystemDesignGraphiti
    ):
        """Test search_design_context returns empty list when disabled."""
        result = await graphiti_service_disabled.search_design_context("test", num_results=5)
        assert result == []

    @pytest.mark.asyncio
    async def test_search_design_context_returns_empty_list_on_exception(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test search_design_context returns empty list on exception."""
        mock_client.search = AsyncMock(side_effect=Exception("Error"))
        with patch("guardkit.planning.graphiti_design.logger") as mock_logger:
            result = await graphiti_service.search_design_context("test", num_results=5)
            assert result == []
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]


# =========================================================================
# 6. HAS_DESIGN_CONTEXT TESTS (5 tests)
# =========================================================================


class TestHasDesignContext:
    """Tests for has_design_context method."""

    @pytest.mark.asyncio
    async def test_has_design_context_returns_true_when_found(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test has_design_context returns True when design context exists."""
        mock_client.search = AsyncMock(
            return_value=[{"fact": "Design decision exists", "score": 0.9}]
        )
        result = await graphiti_service.has_design_context()
        assert result is True

    @pytest.mark.asyncio
    async def test_has_design_context_returns_false_when_not_found(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test has_design_context returns False when no design context."""
        mock_client.search = AsyncMock(return_value=[])
        result = await graphiti_service.has_design_context()
        assert result is False

    @pytest.mark.asyncio
    async def test_has_design_context_returns_false_when_disabled(
        self, graphiti_service_disabled: SystemDesignGraphiti
    ):
        """Test has_design_context returns False when client is disabled."""
        result = await graphiti_service_disabled.has_design_context()
        assert result is False

    @pytest.mark.asyncio
    async def test_has_design_context_returns_false_when_client_none(
        self, graphiti_service_null: SystemDesignGraphiti
    ):
        """Test has_design_context returns False when client is None."""
        result = await graphiti_service_null.has_design_context()
        assert result is False

    @pytest.mark.asyncio
    async def test_has_design_context_returns_false_on_exception(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test has_design_context returns False on exception."""
        mock_client.search = AsyncMock(side_effect=Exception("Error"))
        with patch("guardkit.planning.graphiti_design.logger") as mock_logger:
            result = await graphiti_service.has_design_context()
            assert result is False
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]


# =========================================================================
# 7. GET_DESIGN_DECISIONS TESTS (5 tests)
# =========================================================================


class TestGetDesignDecisions:
    """Tests for get_design_decisions method."""

    @pytest.mark.asyncio
    async def test_get_design_decisions_returns_list(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_design_decisions returns list of facts."""
        mock_client.search = AsyncMock(
            return_value=[
                {"fact": "DDR-001: Use CQRS Pattern", "score": 0.9},
                {"fact": "DDR-002: Event Sourcing", "score": 0.85},
            ]
        )
        result = await graphiti_service.get_design_decisions()
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_design_decisions_searches_design_group(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_design_decisions searches the project_design group."""
        mock_client.search = AsyncMock(return_value=[])
        await graphiti_service.get_design_decisions()
        call_kwargs = mock_client.search.call_args[1]
        assert "group_ids" in call_kwargs
        assert "test-project__project_design" in call_kwargs["group_ids"]

    @pytest.mark.asyncio
    async def test_get_design_decisions_returns_empty_list_when_disabled(
        self, graphiti_service_disabled: SystemDesignGraphiti
    ):
        """Test get_design_decisions returns empty list when disabled."""
        result = await graphiti_service_disabled.get_design_decisions()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_design_decisions_returns_empty_list_on_exception(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_design_decisions returns empty list on exception."""
        mock_client.search = AsyncMock(side_effect=Exception("Error"))
        with patch("guardkit.planning.graphiti_design.logger") as mock_logger:
            result = await graphiti_service.get_design_decisions()
            assert result == []
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_design_decisions_returns_empty_list_when_client_none(
        self, graphiti_service_null: SystemDesignGraphiti
    ):
        """Test get_design_decisions returns empty list when client is None."""
        result = await graphiti_service_null.get_design_decisions()
        assert result == []


# =========================================================================
# 8. GET_API_CONTRACTS TESTS (5 tests)
# =========================================================================


class TestGetApiContracts:
    """Tests for get_api_contracts method."""

    @pytest.mark.asyncio
    async def test_get_api_contracts_returns_list(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_api_contracts returns list of facts."""
        mock_client.search = AsyncMock(
            return_value=[
                {"fact": "API-order-management: REST v1.0.0", "score": 0.9},
            ]
        )
        result = await graphiti_service.get_api_contracts()
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_api_contracts_searches_contracts_group(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_api_contracts searches the api_contracts group."""
        mock_client.search = AsyncMock(return_value=[])
        await graphiti_service.get_api_contracts()
        call_kwargs = mock_client.search.call_args[1]
        assert "group_ids" in call_kwargs
        assert "test-project__api_contracts" in call_kwargs["group_ids"]

    @pytest.mark.asyncio
    async def test_get_api_contracts_returns_empty_list_when_disabled(
        self, graphiti_service_disabled: SystemDesignGraphiti
    ):
        """Test get_api_contracts returns empty list when disabled."""
        result = await graphiti_service_disabled.get_api_contracts()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_api_contracts_returns_empty_list_on_exception(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_api_contracts returns empty list on exception."""
        mock_client.search = AsyncMock(side_effect=Exception("Error"))
        with patch("guardkit.planning.graphiti_design.logger") as mock_logger:
            result = await graphiti_service.get_api_contracts()
            assert result == []
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_api_contracts_returns_empty_list_when_client_none(
        self, graphiti_service_null: SystemDesignGraphiti
    ):
        """Test get_api_contracts returns empty list when client is None."""
        result = await graphiti_service_null.get_api_contracts()
        assert result == []


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


# =========================================================================
# 15. LOGGING TESTS (4 tests)
# =========================================================================


class TestLogging:
    """Tests for [Graphiti] prefix on log messages."""

    @pytest.mark.asyncio
    async def test_upsert_design_decision_logs_with_graphiti_prefix(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_design_decision: DesignDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_design_decision logs with [Graphiti] prefix."""
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("Error"))
        with patch("guardkit.planning.graphiti_design.logger") as mock_logger:
            await graphiti_service.upsert_design_decision(sample_design_decision)
            call_args = mock_logger.warning.call_args[0][0]
            assert "[Graphiti]" in call_args

    @pytest.mark.asyncio
    async def test_upsert_api_contract_logs_with_graphiti_prefix(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_api_contract: ApiContract,
        mock_client: MagicMock,
    ):
        """Test upsert_api_contract logs with [Graphiti] prefix."""
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("Error"))
        with patch("guardkit.planning.graphiti_design.logger") as mock_logger:
            await graphiti_service.upsert_api_contract(sample_api_contract)
            call_args = mock_logger.warning.call_args[0][0]
            assert "[Graphiti]" in call_args

    @pytest.mark.asyncio
    async def test_upsert_data_model_logs_with_graphiti_prefix(
        self,
        graphiti_service: SystemDesignGraphiti,
        sample_data_model: DataModel,
        mock_client: MagicMock,
    ):
        """Test upsert_data_model logs with [Graphiti] prefix."""
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("Error"))
        with patch("guardkit.planning.graphiti_design.logger") as mock_logger:
            await graphiti_service.upsert_data_model(sample_data_model)
            call_args = mock_logger.warning.call_args[0][0]
            assert "[Graphiti]" in call_args

    @pytest.mark.asyncio
    async def test_search_design_context_logs_with_graphiti_prefix(
        self,
        graphiti_service: SystemDesignGraphiti,
        mock_client: MagicMock,
    ):
        """Test search_design_context logs with [Graphiti] prefix."""
        mock_client.search = AsyncMock(side_effect=Exception("Error"))
        with patch("guardkit.planning.graphiti_design.logger") as mock_logger:
            await graphiti_service.search_design_context("test", 5)
            call_args = mock_logger.warning.call_args[0][0]
            assert "[Graphiti]" in call_args
