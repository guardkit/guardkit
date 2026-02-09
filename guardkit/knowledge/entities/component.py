"""
Component definition entity for architecture knowledge.

This module provides the ComponentDef dataclass for capturing component
definitions in the knowledge graph. Components represent bounded contexts
(for DDD) or modules/services (for other methodologies).

Public API:
    ComponentDef: Dataclass for capturing component definitions

Example:
    from guardkit.knowledge.entities.component import ComponentDef

    component = ComponentDef(
        name="Order Management",
        description="Handles order lifecycle",
        responsibilities=["Create orders", "Track status"],
        dependencies=["Inventory", "Payment"],
        methodology="ddd",
        aggregate_roots=["Order", "OrderLine"],
        domain_events=["OrderCreated", "OrderShipped"],
        context_mapping="customer-downstream",
    )
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


def _slugify(name: str, max_length: int = 30) -> str:
    """Convert name to URL-safe slug.

    Args:
        name: The name to convert
        max_length: Maximum length of the slug (default 30)

    Returns:
        Lowercase, hyphenated slug truncated to max_length
    """
    # Convert to lowercase
    slug = name.lower()
    # Replace spaces and special chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    # Truncate to max length
    return slug[:max_length]


@dataclass
class ComponentDef:
    """Captures a component/bounded context definition.

    This entity represents an architectural component within a system.
    For DDD methodologies, it represents a bounded context with additional
    DDD-specific fields (aggregate roots, domain events, context mapping).

    Attributes:
        name: Component name (e.g., "Order Management")
        description: What the component does
        responsibilities: List of responsibilities
        dependencies: Other components this depends on
        methodology: Architecture methodology (ddd, layered, modular, etc.)
        aggregate_roots: DDD only - aggregate root names
        domain_events: DDD only - domain event names
        context_mapping: DDD only - relationship to other contexts

    Example:
        component = ComponentDef(
            name="Order Management",
            description="Handles order lifecycle",
            responsibilities=["Create orders"],
            dependencies=["Inventory"],
            methodology="ddd",
            aggregate_roots=["Order"],
            domain_events=["OrderCreated"],
            context_mapping="customer-downstream",
        )
    """

    # Core fields
    name: str
    description: str
    responsibilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    methodology: str = "layered"

    # DDD-specific fields (only used when methodology == "ddd")
    aggregate_roots: List[str] = field(default_factory=list)
    domain_events: List[str] = field(default_factory=list)
    context_mapping: Optional[str] = None

    @property
    def entity_id(self) -> str:
        """Generate stable entity ID in format: COMP-{slug}.

        The entity ID is deterministic - same name always produces
        the same ID regardless of other field values.

        Returns:
            Entity ID string (e.g., "COMP-order-management")
        """
        slug = _slugify(self.name)
        return f"COMP-{slug}"

    @property
    def entity_type(self) -> str:
        """Return entity type based on methodology.

        Returns:
            "bounded_context" for DDD methodology, "component" otherwise
        """
        if self.methodology == "ddd":
            return "bounded_context"
        return "component"

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body.

        Creates a dictionary representation suitable for storage
        in Graphiti as an episode body. Returns only domain data;
        metadata fields are injected by GraphitiClient.

        For DDD methodology, includes DDD-specific fields.
        For other methodologies, excludes DDD fields.

        Returns:
            Dictionary containing component fields (no _metadata).
        """
        body = {
            "name": self.name,
            "description": self.description,
            "responsibilities": self.responsibilities,
            "dependencies": self.dependencies,
            "methodology": self.methodology,
        }

        # Only include DDD fields if methodology is DDD
        if self.methodology == "ddd":
            body["aggregate_roots"] = self.aggregate_roots
            body["domain_events"] = self.domain_events
            body["context_mapping"] = self.context_mapping

        return body
