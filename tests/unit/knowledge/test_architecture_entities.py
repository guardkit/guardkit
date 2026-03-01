"""Tests for architecture entity definitions.

Verifies the data model layer for /system-plan entities following
ADR-GBF-001 convention (domain data only, no _metadata in to_episode_body()).

Coverage Target: >=85%
Test Count: 35+ tests organized by entity

Entities tested:
- ComponentDef: Methodology-aware episode body (DDD fields conditional)
- SystemContextDef: Stable entity_id (format: SYS-{slug})
- CrosscuttingConcernDef: Stable entity_id (format: XC-{slug})
- ArchitectureDecision: Stable entity_id (format: ADR-SP-{NNN})
- ArchitectureContext: format_for_prompt() and empty() classmethod
"""

import json
import pytest
from typing import List

# These imports will fail until implementation exists (TDD RED phase)
from guardkit.knowledge.entities.component import ComponentDef
from guardkit.knowledge.entities.system_context import SystemContextDef
from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef
from guardkit.knowledge.entities.architecture_context import (
    ArchitectureDecision,
    ArchitectureContext,
)


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def sample_component_ddd() -> ComponentDef:
    """Create a sample DDD-style component."""
    return ComponentDef(
        name="Order Management",
        description="Handles order lifecycle and fulfillment",
        responsibilities=["Create orders", "Track order status", "Handle returns"],
        dependencies=["Inventory", "Payment"],
        methodology="ddd",
        aggregate_roots=["Order", "OrderLine"],
        domain_events=["OrderCreated", "OrderShipped"],
        context_mapping="customer-downstream",
    )


@pytest.fixture
def sample_component_non_ddd() -> ComponentDef:
    """Create a sample non-DDD component (layered/modular)."""
    return ComponentDef(
        name="Auth Service",
        description="Handles authentication and authorization",
        responsibilities=["User login", "Token validation", "Role management"],
        dependencies=["User Store"],
        methodology="layered",
    )


@pytest.fixture
def sample_system_context() -> SystemContextDef:
    """Create a sample system context."""
    return SystemContextDef(
        name="E-Commerce Platform",
        purpose="Online retail with multi-tenant support",
        bounded_contexts=["Orders", "Inventory", "Customers"],
        external_systems=["Payment Gateway", "Shipping API"],
        methodology="ddd",
    )


@pytest.fixture
def sample_crosscutting() -> CrosscuttingConcernDef:
    """Create a sample crosscutting concern."""
    return CrosscuttingConcernDef(
        name="Observability",
        description="Unified logging, metrics, and tracing",
        applies_to=["All Services"],
        implementation_notes="Use OpenTelemetry SDK",
    )


@pytest.fixture
def sample_adr() -> ArchitectureDecision:
    """Create a sample architecture decision record."""
    return ArchitectureDecision(
        number=1,
        title="Use Event Sourcing for Order Aggregate",
        status="accepted",
        context="Orders require complete audit trail and temporal queries",
        decision="Implement event sourcing pattern for Order aggregate",
        consequences=["Full audit trail", "Complex replay logic"],
        related_components=["Order Management"],
    )


@pytest.fixture
def sample_architecture_context(
    sample_component_ddd: ComponentDef,
    sample_system_context: SystemContextDef,
    sample_adr: ArchitectureDecision,
) -> ArchitectureContext:
    """Create a sample architecture context."""
    return ArchitectureContext(
        system_context=sample_system_context,
        components=[sample_component_ddd],
        decisions=[sample_adr],
        crosscutting_concerns=[],
        retrieved_facts=[
            {"content": "Order service uses CQRS pattern", "score": 0.8},
            {"content": "Legacy system uses REST API", "score": 0.4},
        ],
    )


# =========================================================================
# 1. COMPONENTDEF TESTS (10 tests)
# =========================================================================


class TestComponentDef:
    """Tests for ComponentDef dataclass."""

    def test_basic_instantiation(self, sample_component_ddd: ComponentDef):
        """Test basic component creation with all fields."""
        assert sample_component_ddd.name == "Order Management"
        assert sample_component_ddd.methodology == "ddd"
        assert len(sample_component_ddd.responsibilities) == 3

    def test_entity_id_format(self, sample_component_ddd: ComponentDef):
        """Test entity_id follows format: COMP-{slug}."""
        entity_id = sample_component_ddd.entity_id
        assert entity_id.startswith("COMP-")
        assert entity_id == "COMP-order-management"

    def test_entity_id_is_deterministic(self):
        """Test same input produces same entity_id."""
        comp1 = ComponentDef(
            name="My Component",
            description="Test",
            responsibilities=[],
            dependencies=[],
            methodology="layered",
        )
        comp2 = ComponentDef(
            name="My Component",
            description="Different desc",  # Different field
            responsibilities=[],
            dependencies=[],
            methodology="layered",
        )
        # Same name = same entity_id
        assert comp1.entity_id == comp2.entity_id

    def test_entity_id_slug_truncation(self):
        """Test entity_id slug is truncated to 30 chars."""
        comp = ComponentDef(
            name="This Is A Very Long Component Name That Exceeds Thirty Characters",
            description="Test",
            responsibilities=[],
            dependencies=[],
            methodology="layered",
        )
        # entity_id should have slug portion max 30 chars
        slug = comp.entity_id.replace("COMP-", "")
        assert len(slug) <= 30

    def test_entity_type_ddd(self, sample_component_ddd: ComponentDef):
        """Test entity_type returns 'bounded_context' for DDD methodology."""
        assert sample_component_ddd.entity_type == "bounded_context"

    def test_entity_type_non_ddd(self, sample_component_non_ddd: ComponentDef):
        """Test entity_type returns 'component' for non-DDD methodology."""
        assert sample_component_non_ddd.entity_type == "component"

    def test_to_episode_body_ddd_includes_ddd_fields(
        self, sample_component_ddd: ComponentDef
    ):
        """Test DDD methodology includes DDD-specific fields."""
        body = sample_component_ddd.to_episode_body()

        # DDD fields MUST be present
        assert "aggregate_roots" in body
        assert "domain_events" in body
        assert "context_mapping" in body
        assert body["aggregate_roots"] == ["Order", "OrderLine"]

    def test_to_episode_body_non_ddd_excludes_ddd_fields(
        self, sample_component_non_ddd: ComponentDef
    ):
        """Test non-DDD methodology excludes DDD-specific fields."""
        body = sample_component_non_ddd.to_episode_body()

        # DDD fields MUST NOT be present
        assert "aggregate_roots" not in body
        assert "domain_events" not in body
        assert "context_mapping" not in body

    def test_to_episode_body_no_metadata(self, sample_component_ddd: ComponentDef):
        """Test episode body has no _metadata (ADR-GBF-001)."""
        body = sample_component_ddd.to_episode_body()

        assert "_metadata" not in body
        assert "entity_type" not in body  # Injected by GraphitiClient
        assert "created_at" not in body

    def test_to_episode_body_is_json_serializable(
        self, sample_component_ddd: ComponentDef
    ):
        """Test episode body can be serialized to JSON."""
        body = sample_component_ddd.to_episode_body()
        json_str = json.dumps(body)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["name"] == "Order Management"


# =========================================================================
# 2. SYSTEMCONTEXTDEF TESTS (6 tests)
# =========================================================================


class TestSystemContextDef:
    """Tests for SystemContextDef dataclass."""

    def test_basic_instantiation(self, sample_system_context: SystemContextDef):
        """Test basic system context creation."""
        assert sample_system_context.name == "E-Commerce Platform"
        assert len(sample_system_context.bounded_contexts) == 3

    def test_entity_id_format(self, sample_system_context: SystemContextDef):
        """Test entity_id follows format: SYS-{slug}."""
        entity_id = sample_system_context.entity_id
        assert entity_id.startswith("SYS-")
        assert entity_id == "SYS-e-commerce-platform"

    def test_entity_id_is_deterministic(self):
        """Test same name produces same entity_id."""
        ctx1 = SystemContextDef(
            name="My System",
            purpose="Purpose A",
            bounded_contexts=[],
            external_systems=[],
            methodology="ddd",
        )
        ctx2 = SystemContextDef(
            name="My System",
            purpose="Purpose B",  # Different
            bounded_contexts=["ctx1"],  # Different
            external_systems=[],
            methodology="ddd",
        )
        assert ctx1.entity_id == ctx2.entity_id

    def test_to_episode_body_structure(self, sample_system_context: SystemContextDef):
        """Test episode body has correct structure."""
        body = sample_system_context.to_episode_body()

        assert body["name"] == "E-Commerce Platform"
        assert body["purpose"] == "Online retail with multi-tenant support"
        assert body["bounded_contexts"] == ["Orders", "Inventory", "Customers"]
        assert body["external_systems"] == ["Payment Gateway", "Shipping API"]
        assert body["methodology"] == "ddd"

    def test_to_episode_body_no_metadata(self, sample_system_context: SystemContextDef):
        """Test episode body has no _metadata (ADR-GBF-001)."""
        body = sample_system_context.to_episode_body()
        assert "_metadata" not in body

    def test_to_episode_body_is_json_serializable(
        self, sample_system_context: SystemContextDef
    ):
        """Test episode body can be serialized to JSON."""
        body = sample_system_context.to_episode_body()
        json_str = json.dumps(body)
        assert isinstance(json_str, str)


# =========================================================================
# 3. CROSSCUTTINGCONCERNDEF TESTS (6 tests)
# =========================================================================


class TestCrosscuttingConcernDef:
    """Tests for CrosscuttingConcernDef dataclass."""

    def test_basic_instantiation(self, sample_crosscutting: CrosscuttingConcernDef):
        """Test basic crosscutting concern creation."""
        assert sample_crosscutting.name == "Observability"
        assert sample_crosscutting.applies_to == ["All Services"]

    def test_entity_id_format(self, sample_crosscutting: CrosscuttingConcernDef):
        """Test entity_id follows format: XC-{slug}."""
        entity_id = sample_crosscutting.entity_id
        assert entity_id.startswith("XC-")
        assert entity_id == "XC-observability"

    def test_entity_id_is_deterministic(self):
        """Test same name produces same entity_id."""
        xc1 = CrosscuttingConcernDef(
            name="Logging",
            description="Desc A",
            applies_to=["A"],
            implementation_notes="Note A",
        )
        xc2 = CrosscuttingConcernDef(
            name="Logging",
            description="Desc B",
            applies_to=["B"],
            implementation_notes="Note B",
        )
        assert xc1.entity_id == xc2.entity_id

    def test_to_episode_body_structure(
        self, sample_crosscutting: CrosscuttingConcernDef
    ):
        """Test episode body has correct structure."""
        body = sample_crosscutting.to_episode_body()

        assert body["name"] == "Observability"
        assert body["description"] == "Unified logging, metrics, and tracing"
        assert body["applies_to"] == ["All Services"]
        assert body["implementation_notes"] == "Use OpenTelemetry SDK"

    def test_to_episode_body_no_metadata(
        self, sample_crosscutting: CrosscuttingConcernDef
    ):
        """Test episode body has no _metadata (ADR-GBF-001)."""
        body = sample_crosscutting.to_episode_body()
        assert "_metadata" not in body

    def test_to_episode_body_is_json_serializable(
        self, sample_crosscutting: CrosscuttingConcernDef
    ):
        """Test episode body can be serialized to JSON."""
        body = sample_crosscutting.to_episode_body()
        json_str = json.dumps(body)
        assert isinstance(json_str, str)


# =========================================================================
# 4. ARCHITECTUREDECISION TESTS (8 tests)
# =========================================================================


class TestArchitectureDecision:
    """Tests for ArchitectureDecision dataclass."""

    def test_basic_instantiation(self, sample_adr: ArchitectureDecision):
        """Test basic ADR creation."""
        assert sample_adr.number == 1
        assert sample_adr.title == "Use Event Sourcing for Order Aggregate"
        assert sample_adr.status == "accepted"

    def test_entity_id_format(self, sample_adr: ArchitectureDecision):
        """Test entity_id follows format: ADR-SP-{NNN}."""
        entity_id = sample_adr.entity_id
        assert entity_id.startswith("ADR-SP-")
        assert entity_id == "ADR-SP-001"

    def test_entity_id_padding(self):
        """Test entity_id number is zero-padded to 3 digits."""
        adr_single = ArchitectureDecision(
            number=5,
            title="Test",
            status="accepted",
            context="",
            decision="",
            consequences=[],
            related_components=[],
        )
        assert adr_single.entity_id == "ADR-SP-005"

        adr_double = ArchitectureDecision(
            number=42,
            title="Test",
            status="accepted",
            context="",
            decision="",
            consequences=[],
            related_components=[],
        )
        assert adr_double.entity_id == "ADR-SP-042"

        adr_triple = ArchitectureDecision(
            number=123,
            title="Test",
            status="accepted",
            context="",
            decision="",
            consequences=[],
            related_components=[],
        )
        assert adr_triple.entity_id == "ADR-SP-123"

    def test_entity_id_is_deterministic(self):
        """Test same number produces same entity_id."""
        adr1 = ArchitectureDecision(
            number=7,
            title="Title A",
            status="accepted",
            context="",
            decision="",
            consequences=[],
            related_components=[],
        )
        adr2 = ArchitectureDecision(
            number=7,
            title="Title B",  # Different
            status="proposed",  # Different
            context="Different",
            decision="",
            consequences=[],
            related_components=[],
        )
        assert adr1.entity_id == adr2.entity_id

    def test_to_episode_body_structure(self, sample_adr: ArchitectureDecision):
        """Test episode body has correct structure."""
        body = sample_adr.to_episode_body()

        assert body["number"] == 1
        assert body["title"] == "Use Event Sourcing for Order Aggregate"
        assert body["status"] == "accepted"
        assert "Orders require complete audit trail" in body["context"]
        assert body["consequences"] == ["Full audit trail", "Complex replay logic"]
        assert body["related_components"] == ["Order Management"]

    def test_to_episode_body_no_metadata(self, sample_adr: ArchitectureDecision):
        """Test episode body has no _metadata (ADR-GBF-001)."""
        body = sample_adr.to_episode_body()
        assert "_metadata" not in body

    def test_to_episode_body_is_json_serializable(
        self, sample_adr: ArchitectureDecision
    ):
        """Test episode body can be serialized to JSON."""
        body = sample_adr.to_episode_body()
        json_str = json.dumps(body)
        assert isinstance(json_str, str)

    def test_valid_status_values(self):
        """Test ADR accepts valid status values."""
        for status in ["proposed", "accepted", "deprecated", "superseded"]:
            adr = ArchitectureDecision(
                number=1,
                title="Test",
                status=status,
                context="",
                decision="",
                consequences=[],
                related_components=[],
            )
            assert adr.status == status

    # --- New tests for TASK-SAD-002 ---

    def test_alternatives_considered_default_empty(self):
        """Test alternatives_considered defaults to empty list."""
        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
        )
        assert adr.alternatives_considered == []

    def test_alternatives_considered_with_values(self):
        """Test alternatives_considered can be populated."""
        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
            alternatives_considered=["Option A", "Option B", "Option C"],
        )
        assert adr.alternatives_considered == ["Option A", "Option B", "Option C"]
        assert len(adr.alternatives_considered) == 3

    def test_superseded_by_default_none(self):
        """Test superseded_by defaults to None."""
        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
        )
        assert adr.superseded_by is None

    def test_superseded_by_with_value(self):
        """Test superseded_by can reference another ADR."""
        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="superseded",
            context="ctx",
            decision="dec",
            superseded_by="ADR-SP-005",
        )
        assert adr.superseded_by == "ADR-SP-005"

    def test_supersedes_default_none(self):
        """Test supersedes defaults to None."""
        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
        )
        assert adr.supersedes is None

    def test_supersedes_with_value(self):
        """Test supersedes can reference another ADR."""
        adr = ArchitectureDecision(
            number=5,
            title="Use CQRS Instead",
            status="accepted",
            context="ctx",
            decision="dec",
            supersedes="ADR-SP-001",
        )
        assert adr.supersedes == "ADR-SP-001"

    def test_prefix_default_sp(self):
        """Test prefix defaults to 'SP' for backwards compatibility."""
        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
        )
        assert adr.prefix == "SP"

    def test_prefix_parametrised_arch(self):
        """Test prefix can be set to 'ARCH' for /system-arch."""
        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
            prefix="ARCH",
        )
        assert adr.prefix == "ARCH"
        assert adr.entity_id == "ADR-ARCH-001"

    def test_prefix_parametrised_fs(self):
        """Test prefix can be set to 'FS' for /feature-spec."""
        adr = ArchitectureDecision(
            number=3,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
            prefix="FS",
        )
        assert adr.prefix == "FS"
        assert adr.entity_id == "ADR-FS-003"

    def test_entity_id_default_prefix_backwards_compatible(self):
        """Test entity_id uses default 'SP' prefix, matching existing format."""
        adr = ArchitectureDecision(
            number=42,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
        )
        # Default must remain ADR-SP-042 for backwards compatibility
        assert adr.entity_id == "ADR-SP-042"

    def test_to_episode_body_includes_alternatives_when_nonempty(self):
        """Test to_episode_body includes alternatives_considered when non-empty."""
        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
            alternatives_considered=["Option A", "Option B"],
        )
        body = adr.to_episode_body()
        assert "alternatives_considered" in body
        assert body["alternatives_considered"] == ["Option A", "Option B"]

    def test_to_episode_body_excludes_alternatives_when_empty(self):
        """Test to_episode_body excludes alternatives_considered when empty."""
        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
            alternatives_considered=[],
        )
        body = adr.to_episode_body()
        assert "alternatives_considered" not in body

    def test_to_episode_body_includes_superseded_by_when_set(self):
        """Test to_episode_body includes superseded_by when not None."""
        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="superseded",
            context="ctx",
            decision="dec",
            superseded_by="ADR-SP-005",
        )
        body = adr.to_episode_body()
        assert "superseded_by" in body
        assert body["superseded_by"] == "ADR-SP-005"

    def test_to_episode_body_excludes_superseded_by_when_none(self):
        """Test to_episode_body excludes superseded_by when None."""
        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
        )
        body = adr.to_episode_body()
        assert "superseded_by" not in body

    def test_to_episode_body_includes_supersedes_when_set(self):
        """Test to_episode_body includes supersedes when not None."""
        adr = ArchitectureDecision(
            number=5,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
            supersedes="ADR-SP-001",
        )
        body = adr.to_episode_body()
        assert "supersedes" in body
        assert body["supersedes"] == "ADR-SP-001"

    def test_to_episode_body_excludes_supersedes_when_none(self):
        """Test to_episode_body excludes supersedes when None."""
        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="accepted",
            context="ctx",
            decision="dec",
        )
        body = adr.to_episode_body()
        assert "supersedes" not in body

    def test_to_episode_body_all_new_fields_populated(self):
        """Test to_episode_body with all new fields populated."""
        adr = ArchitectureDecision(
            number=5,
            title="Use CQRS",
            status="accepted",
            context="Need separation of reads/writes",
            decision="Implement CQRS",
            consequences=["Better read performance"],
            related_components=["Order Management"],
            alternatives_considered=["Event Sourcing only", "Simple CRUD"],
            superseded_by=None,
            supersedes="ADR-SP-001",
            prefix="ARCH",
        )
        body = adr.to_episode_body()

        # Core fields always present
        assert body["number"] == 5
        assert body["title"] == "Use CQRS"
        assert body["status"] == "accepted"
        assert body["decision"] == "Implement CQRS"

        # New fields conditionally present
        assert body["alternatives_considered"] == ["Event Sourcing only", "Simple CRUD"]
        assert body["supersedes"] == "ADR-SP-001"
        assert "superseded_by" not in body  # None → excluded

    def test_to_episode_body_backwards_compatible_no_new_fields(self):
        """Test to_episode_body remains backwards compatible with existing data."""
        adr = ArchitectureDecision(
            number=1,
            title="Use Event Sourcing",
            status="accepted",
            context="Need audit trail",
            decision="Event sourcing pattern",
            consequences=["Full history"],
            related_components=["Order Management"],
        )
        body = adr.to_episode_body()

        # Only original fields present
        assert set(body.keys()) == {
            "number", "title", "status", "context",
            "decision", "consequences", "related_components",
        }

    def test_mutable_defaults_alternatives_considered(self):
        """Test alternatives_considered mutable default doesn't share state."""
        adr1 = ArchitectureDecision(
            number=1, title="T1", status="accepted", context="c", decision="d",
        )
        adr2 = ArchitectureDecision(
            number=2, title="T2", status="accepted", context="c", decision="d",
        )
        adr1.alternatives_considered.append("Modified")
        assert len(adr2.alternatives_considered) == 0


# =========================================================================
# 5. ARCHITECTURECONTEXT TESTS (10 tests)
# =========================================================================


class TestArchitectureContext:
    """Tests for ArchitectureContext dataclass."""

    def test_basic_instantiation(
        self, sample_architecture_context: ArchitectureContext
    ):
        """Test basic architecture context creation."""
        assert sample_architecture_context.system_context is not None
        assert len(sample_architecture_context.components) == 1
        assert len(sample_architecture_context.decisions) == 1

    def test_format_for_prompt_includes_system_context(
        self, sample_architecture_context: ArchitectureContext
    ):
        """Test format_for_prompt includes system context."""
        prompt = sample_architecture_context.format_for_prompt()

        assert "E-Commerce Platform" in prompt
        assert "Online retail with multi-tenant support" in prompt

    def test_format_for_prompt_includes_components(
        self, sample_architecture_context: ArchitectureContext
    ):
        """Test format_for_prompt includes component info."""
        prompt = sample_architecture_context.format_for_prompt()

        assert "Order Management" in prompt

    def test_format_for_prompt_includes_decisions(
        self, sample_architecture_context: ArchitectureContext
    ):
        """Test format_for_prompt includes architecture decisions."""
        prompt = sample_architecture_context.format_for_prompt()

        assert "Event Sourcing" in prompt
        assert "ADR-SP-001" in prompt

    def test_format_for_prompt_filters_facts_by_score(
        self, sample_architecture_context: ArchitectureContext
    ):
        """Test format_for_prompt only includes facts with score > 0.5."""
        prompt = sample_architecture_context.format_for_prompt()

        # High score fact (0.8) should be included
        assert "CQRS pattern" in prompt
        # Low score fact (0.4) should NOT be included
        assert "Legacy system" not in prompt

    def test_format_for_prompt_respects_token_budget(self):
        """Test format_for_prompt respects token budget parameter."""
        # Create context with many facts
        many_facts = [
            {"content": f"Fact number {i} with some content", "score": 0.9}
            for i in range(100)
        ]
        ctx = ArchitectureContext(
            system_context=None,
            components=[],
            decisions=[],
            crosscutting_concerns=[],
            retrieved_facts=many_facts,
        )

        # With small token budget, output should be truncated
        prompt_small = ctx.format_for_prompt(token_budget=100)
        prompt_large = ctx.format_for_prompt(token_budget=10000)

        assert len(prompt_small) < len(prompt_large)

    def test_empty_classmethod(self):
        """Test empty() classmethod creates valid empty context."""
        empty_ctx = ArchitectureContext.empty()

        assert empty_ctx.system_context is None
        assert empty_ctx.components == []
        assert empty_ctx.decisions == []
        assert empty_ctx.crosscutting_concerns == []
        assert empty_ctx.retrieved_facts == []

    def test_empty_context_format_for_prompt(self):
        """Test format_for_prompt on empty context returns placeholder."""
        empty_ctx = ArchitectureContext.empty()
        prompt = empty_ctx.format_for_prompt()

        # Should return some indication that no context is available
        assert len(prompt) > 0
        assert "no architecture context" in prompt.lower() or prompt == ""

    def test_format_for_prompt_includes_crosscutting_concerns(self):
        """Test format_for_prompt includes crosscutting concerns."""
        ctx = ArchitectureContext(
            system_context=None,
            components=[],
            decisions=[],
            crosscutting_concerns=[
                CrosscuttingConcernDef(
                    name="Security",
                    description="Authentication and authorization",
                    applies_to=["All APIs"],
                    implementation_notes="Use OAuth2",
                )
            ],
            retrieved_facts=[],
        )
        prompt = ctx.format_for_prompt()

        assert "Security" in prompt

    def test_architecture_context_mutable_defaults(self):
        """Test mutable defaults are properly handled (no shared state)."""
        ctx1 = ArchitectureContext.empty()
        ctx2 = ArchitectureContext.empty()

        ctx1.components.append(
            ComponentDef(
                name="Test",
                description="",
                responsibilities=[],
                dependencies=[],
                methodology="layered",
            )
        )

        # ctx2 should NOT be affected
        assert len(ctx2.components) == 0

    def test_format_for_prompt_very_small_budget_skips_facts(self):
        """Test format_for_prompt with very small budget skips facts section."""
        ctx = ArchitectureContext(
            system_context=None,
            components=[],
            decisions=[],
            crosscutting_concerns=[],
            retrieved_facts=[{"content": "Some fact", "score": 0.9}],
        )
        # With tiny budget, facts section should be empty
        prompt = ctx.format_for_prompt(token_budget=10)
        # Should just say no context available or be very short
        assert len(prompt) < 100

    def test_format_for_prompt_budget_truncates_sections(self):
        """Test sections are skipped when budget is exceeded."""
        # Create context with multiple sections
        ctx = ArchitectureContext(
            system_context=SystemContextDef(
                name="A Very Long System Name That Takes Up Space",
                purpose="A very long purpose description that takes up a lot of space in the output",
                bounded_contexts=["Context1", "Context2", "Context3"],
                external_systems=["External1", "External2"],
                methodology="ddd",
            ),
            components=[
                ComponentDef(
                    name="Component A",
                    description="A long description for component A",
                    responsibilities=[],
                    dependencies=[],
                    methodology="layered",
                ),
                ComponentDef(
                    name="Component B",
                    description="A long description for component B",
                    responsibilities=[],
                    dependencies=[],
                    methodology="layered",
                ),
            ],
            decisions=[
                ArchitectureDecision(
                    number=1,
                    title="Decision 1",
                    status="accepted",
                    context="Context",
                    decision="Decision",
                    consequences=[],
                    related_components=[],
                ),
            ],
            crosscutting_concerns=[
                CrosscuttingConcernDef(
                    name="Concern A",
                    description="Description A",
                    applies_to=[],
                    implementation_notes="",
                ),
            ],
            retrieved_facts=[
                {"content": "Fact 1", "score": 0.9},
                {"content": "Fact 2", "score": 0.8},
            ],
        )

        # Very small budget should truncate
        prompt_small = ctx.format_for_prompt(token_budget=50)
        prompt_full = ctx.format_for_prompt(token_budget=5000)

        assert len(prompt_small) < len(prompt_full)
        # Small prompt should not include all sections
        assert prompt_small.count("##") < prompt_full.count("##")


# =========================================================================
# 6. ENTITY ID SLUGIFICATION TESTS (5 tests)
# =========================================================================


class TestEntityIdSlugification:
    """Test the slugification logic for entity IDs."""

    def test_spaces_replaced_with_hyphens(self):
        """Test spaces are replaced with hyphens."""
        comp = ComponentDef(
            name="My Great Component",
            description="",
            responsibilities=[],
            dependencies=[],
            methodology="layered",
        )
        assert comp.entity_id == "COMP-my-great-component"

    def test_lowercase_conversion(self):
        """Test names are converted to lowercase."""
        comp = ComponentDef(
            name="UPPERCASE",
            description="",
            responsibilities=[],
            dependencies=[],
            methodology="layered",
        )
        assert comp.entity_id == "COMP-uppercase"

    def test_special_characters_handled(self):
        """Test special characters are handled in slugification."""
        comp = ComponentDef(
            name="Auth/Login (Main)",
            description="",
            responsibilities=[],
            dependencies=[],
            methodology="layered",
        )
        # Special chars should be removed or replaced
        entity_id = comp.entity_id
        assert "/" not in entity_id
        assert "(" not in entity_id
        assert ")" not in entity_id

    def test_consecutive_hyphens_collapsed(self):
        """Test consecutive hyphens are collapsed to single hyphen."""
        comp = ComponentDef(
            name="A   B",  # Multiple spaces
            description="",
            responsibilities=[],
            dependencies=[],
            methodology="layered",
        )
        assert "--" not in comp.entity_id

    def test_truncation_at_30_chars(self):
        """Test slug portion is max 30 characters."""
        long_name = "A" * 50  # 50 character name
        comp = ComponentDef(
            name=long_name,
            description="",
            responsibilities=[],
            dependencies=[],
            methodology="layered",
        )
        slug = comp.entity_id.replace("COMP-", "")
        assert len(slug) <= 30
