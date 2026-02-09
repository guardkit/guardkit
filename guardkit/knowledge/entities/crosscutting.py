"""
Crosscutting concern definition entity for architecture knowledge.

This module provides the CrosscuttingConcernDef dataclass for capturing
crosscutting concerns in the knowledge graph. Crosscutting concerns
represent aspects that affect multiple components (e.g., logging,
security, observability).

Public API:
    CrosscuttingConcernDef: Dataclass for capturing crosscutting concern definitions

Example:
    from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef

    concern = CrosscuttingConcernDef(
        name="Observability",
        description="Unified logging, metrics, and tracing",
        applies_to=["All Services"],
        implementation_notes="Use OpenTelemetry SDK",
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
class CrosscuttingConcernDef:
    """Captures a crosscutting concern definition.

    This entity represents an architectural concern that spans
    multiple components, such as logging, security, or observability.

    Attributes:
        name: Concern name (e.g., "Observability")
        description: What the concern addresses
        applies_to: List of components/services this applies to
        implementation_notes: How to implement this concern

    Example:
        concern = CrosscuttingConcernDef(
            name="Observability",
            description="Logging and tracing",
            applies_to=["All Services"],
            implementation_notes="Use OpenTelemetry",
        )
    """

    name: str
    description: str
    applies_to: List[str] = field(default_factory=list)
    implementation_notes: str = ""

    @property
    def entity_id(self) -> str:
        """Generate stable entity ID in format: XC-{slug}.

        The entity ID is deterministic - same name always produces
        the same ID regardless of other field values.

        Returns:
            Entity ID string (e.g., "XC-observability")
        """
        slug = _slugify(self.name)
        return f"XC-{slug}"

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body.

        Creates a dictionary representation suitable for storage
        in Graphiti as an episode body. Returns only domain data;
        metadata fields are injected by GraphitiClient.

        Returns:
            Dictionary containing crosscutting concern fields (no _metadata).
        """
        return {
            "name": self.name,
            "description": self.description,
            "applies_to": self.applies_to,
            "implementation_notes": self.implementation_notes,
        }
