"""
System context definition entity for architecture knowledge.

This module provides the SystemContextDef dataclass for capturing
the overall system context in the knowledge graph. System contexts
represent the highest-level view of a system's architecture.

Public API:
    SystemContextDef: Dataclass for capturing system context definitions

Example:
    from guardkit.knowledge.entities.system_context import SystemContextDef

    context = SystemContextDef(
        name="E-Commerce Platform",
        purpose="Online retail with multi-tenant support",
        bounded_contexts=["Orders", "Inventory", "Customers"],
        external_systems=["Payment Gateway", "Shipping API"],
        methodology="ddd",
    )
"""

import re
from dataclasses import dataclass, field
from typing import List


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
class SystemContextDef:
    """Captures a system context definition.

    This entity represents the highest-level view of a system's
    architecture, including its bounded contexts (for DDD) or
    major subsystems, and external system integrations.

    Attributes:
        name: System name (e.g., "E-Commerce Platform")
        purpose: What the system exists to do
        bounded_contexts: List of bounded context names (DDD) or subsystems
        external_systems: External systems the system integrates with
        methodology: Architecture methodology (ddd, layered, modular, etc.)

    Example:
        context = SystemContextDef(
            name="E-Commerce Platform",
            purpose="Online retail",
            bounded_contexts=["Orders", "Inventory"],
            external_systems=["Payment Gateway"],
            methodology="ddd",
        )
    """

    name: str
    purpose: str
    bounded_contexts: List[str] = field(default_factory=list)
    external_systems: List[str] = field(default_factory=list)
    methodology: str = "ddd"

    @property
    def entity_id(self) -> str:
        """Generate stable entity ID in format: SYS-{slug}.

        The entity ID is deterministic - same name always produces
        the same ID regardless of other field values.

        Returns:
            Entity ID string (e.g., "SYS-e-commerce-platform")
        """
        slug = _slugify(self.name)
        return f"SYS-{slug}"

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body.

        Creates a dictionary representation suitable for storage
        in Graphiti as an episode body. Returns only domain data;
        metadata fields are injected by GraphitiClient.

        Returns:
            Dictionary containing system context fields (no _metadata).
        """
        return {
            "name": self.name,
            "purpose": self.purpose,
            "bounded_contexts": self.bounded_contexts,
            "external_systems": self.external_systems,
            "methodology": self.methodology,
        }
