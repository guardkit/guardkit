"""
Data model entity for architecture knowledge.

This module provides the DataModel dataclass for capturing
data model definitions in the knowledge graph. Data models
describe the entities, their attributes, relationships, and
invariants within a bounded context.

Public API:
    DataModel: Frozen dataclass for data model definitions

Example:
    from guardkit.knowledge.entities.data_model import DataModel

    model = DataModel(
        bounded_context="Order Management",
        entities=[
            {
                "name": "Order",
                "attributes": ["id", "customer_id", "total", "status"],
                "relationships": ["has_many OrderLine"],
            },
        ],
        invariants=["Order total must equal sum of line items"],
    )
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List


def _slugify(name: str, max_length: int = 30) -> str:
    """Convert name to URL-safe slug.

    Args:
        name: The name to convert
        max_length: Maximum length of the slug (default 30)

    Returns:
        Lowercase, hyphenated slug truncated to max_length
    """
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    slug = re.sub(r'-+', '-', slug)
    return slug[:max_length]


@dataclass(frozen=True)
class DataModel:
    """Captures a data model definition.

    This entity represents the data model within a bounded context,
    including entity definitions with their attributes and relationships,
    as well as domain invariants.

    Attributes:
        bounded_context: The bounded context this data model belongs to
        entities: List of entity definitions (dicts with name, attributes, relationships)
        invariants: List of domain invariants/business rules

    Example:
        model = DataModel(
            bounded_context="Order Management",
            entities=[
                {
                    "name": "Order",
                    "attributes": ["id", "total"],
                    "relationships": ["has_many OrderLine"],
                }
            ],
            invariants=["Order total must equal sum of line items"],
        )
    """

    # Required field
    bounded_context: str

    # Optional fields with defaults
    entities: List[Dict] = field(default_factory=list)
    invariants: List[str] = field(default_factory=list)

    @property
    def entity_id(self) -> str:
        """Generate stable entity ID in format: DM-{bounded_context_slug}.

        The entity ID is deterministic - same bounded_context always
        produces the same ID regardless of other field values.

        Returns:
            Entity ID string (e.g., "DM-order-management")
        """
        slug = _slugify(self.bounded_context)
        return f"DM-{slug}"

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body.

        Creates a dictionary representation suitable for storage
        in Graphiti as an episode body. Returns only domain data;
        metadata fields are injected by GraphitiClient.

        Returns:
            Dictionary containing data model fields (no _metadata).
        """
        return {
            "bounded_context": self.bounded_context,
            "entities": self.entities,
            "invariants": self.invariants,
        }
