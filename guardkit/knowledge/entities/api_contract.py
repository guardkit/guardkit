"""
API contract entity for architecture knowledge.

This module provides the ApiContract dataclass for capturing
API contract definitions in the knowledge graph. API contracts
describe the external interfaces of bounded contexts.

Public API:
    ApiContract: Frozen dataclass for API contract definitions

Example:
    from guardkit.knowledge.entities.api_contract import ApiContract

    contract = ApiContract(
        bounded_context="Order Management",
        consumer_types=["web-frontend", "mobile-app"],
        endpoints=[
            {"path": "/orders", "method": "POST", "description": "Create order"},
        ],
        protocol="REST",
        version="1.0.0",
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
class ApiContract:
    """Captures an API contract definition.

    This entity represents the external API interface of a bounded
    context, including endpoint definitions, protocol type, and
    consumer information. Supports multiple protocols per bounded
    context (web + agent consumers).

    Attributes:
        bounded_context: The bounded context this API belongs to
        consumer_types: Types of consumers (e.g., "web-frontend", "mobile-app")
        endpoints: List of endpoint definitions (dicts with path, method, description)
        protocol: API protocol (REST, GraphQL, MCP, A2A, ACP)
        version: API version string (semver)

    Example:
        contract = ApiContract(
            bounded_context="Order Management",
            consumer_types=["web-frontend"],
            endpoints=[{"path": "/orders", "method": "POST", "description": "Create"}],
            protocol="REST",
            version="1.0.0",
        )
    """

    # Required fields
    bounded_context: str
    protocol: str  # REST, GraphQL, MCP, A2A, ACP
    version: str

    # Optional fields with defaults
    consumer_types: List[str] = field(default_factory=list)
    endpoints: List[Dict] = field(default_factory=list)

    @property
    def entity_id(self) -> str:
        """Generate stable entity ID in format: API-{bounded_context_slug}.

        The entity ID is deterministic - same bounded_context always
        produces the same ID regardless of other field values.

        Returns:
            Entity ID string (e.g., "API-order-management")
        """
        slug = _slugify(self.bounded_context)
        return f"API-{slug}"

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body.

        Creates a dictionary representation suitable for storage
        in Graphiti as an episode body. Returns only domain data;
        metadata fields are injected by GraphitiClient.

        Returns:
            Dictionary containing API contract fields (no _metadata).
        """
        return {
            "bounded_context": self.bounded_context,
            "consumer_types": self.consumer_types,
            "endpoints": self.endpoints,
            "protocol": self.protocol,
            "version": self.version,
        }
