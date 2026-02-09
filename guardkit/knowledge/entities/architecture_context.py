"""
Architecture context and decision entities for knowledge graph.

This module provides the ArchitectureDecision and ArchitectureContext
dataclasses for capturing architectural decisions and the overall
architecture context for coach/feature-plan integration.

Public API:
    ArchitectureDecision: Dataclass for Architecture Decision Records (ADRs)
    ArchitectureContext: Dataclass for aggregated architecture context

Example:
    from guardkit.knowledge.entities.architecture_context import (
        ArchitectureDecision,
        ArchitectureContext,
    )

    adr = ArchitectureDecision(
        number=1,
        title="Use Event Sourcing",
        status="accepted",
        context="Need audit trail",
        decision="Use event sourcing pattern",
        consequences=["Full history"],
        related_components=["Order Management"],
    )

    context = ArchitectureContext(
        system_context=system_ctx,
        components=[order_component],
        decisions=[adr],
        crosscutting_concerns=[],
        retrieved_facts=[{"content": "Uses CQRS", "score": 0.8}],
    )
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from guardkit.knowledge.entities.system_context import SystemContextDef
    from guardkit.knowledge.entities.component import ComponentDef
    from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef


@dataclass
class ArchitectureDecision:
    """Captures an Architecture Decision Record (ADR).

    This entity represents a significant architectural decision
    following the ADR format (context, decision, consequences).

    Attributes:
        number: ADR number (1, 2, 3, etc.)
        title: Decision title
        status: Decision status (proposed, accepted, deprecated, superseded)
        context: Why this decision was needed
        decision: What was decided
        consequences: List of consequences (positive and negative)
        related_components: Components affected by this decision

    Example:
        adr = ArchitectureDecision(
            number=1,
            title="Use Event Sourcing",
            status="accepted",
            context="Need complete audit trail",
            decision="Implement event sourcing",
            consequences=["Full history", "Complex replay"],
            related_components=["Order Management"],
        )
    """

    number: int
    title: str
    status: str  # proposed, accepted, deprecated, superseded
    context: str
    decision: str
    consequences: List[str] = field(default_factory=list)
    related_components: List[str] = field(default_factory=list)

    @property
    def entity_id(self) -> str:
        """Generate stable entity ID in format: ADR-SP-{NNN}.

        The entity ID is deterministic - same number always produces
        the same ID regardless of other field values.

        Returns:
            Entity ID string (e.g., "ADR-SP-001", "ADR-SP-042")
        """
        return f"ADR-SP-{self.number:03d}"

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body.

        Creates a dictionary representation suitable for storage
        in Graphiti as an episode body. Returns only domain data;
        metadata fields are injected by GraphitiClient.

        Returns:
            Dictionary containing ADR fields (no _metadata).
        """
        return {
            "number": self.number,
            "title": self.title,
            "status": self.status,
            "context": self.context,
            "decision": self.decision,
            "consequences": self.consequences,
            "related_components": self.related_components,
        }


@dataclass
class ArchitectureContext:
    """Aggregated architecture context for coach/feature-plan integration.

    This entity aggregates all architecture knowledge (system context,
    components, decisions, crosscutting concerns, and retrieved facts)
    into a single context object that can be formatted for prompts.

    Attributes:
        system_context: The system context definition (if available)
        components: List of component definitions
        decisions: List of architecture decisions
        crosscutting_concerns: List of crosscutting concerns
        retrieved_facts: Facts retrieved from knowledge graph with scores

    Example:
        context = ArchitectureContext(
            system_context=sys_ctx,
            components=[order_mgmt],
            decisions=[adr_001],
            crosscutting_concerns=[observability],
            retrieved_facts=[{"content": "Uses CQRS", "score": 0.8}],
        )

        prompt_context = context.format_for_prompt(token_budget=2000)
    """

    system_context: Optional[Any] = None  # SystemContextDef
    components: List[Any] = field(default_factory=list)  # List[ComponentDef]
    decisions: List[ArchitectureDecision] = field(default_factory=list)
    crosscutting_concerns: List[Any] = field(default_factory=list)  # List[CrosscuttingConcernDef]
    retrieved_facts: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "ArchitectureContext":
        """Create an empty architecture context for graceful degradation.

        Use this when no architecture knowledge is available to provide
        a valid but empty context object.

        Returns:
            Empty ArchitectureContext with all fields as None or empty lists.
        """
        return cls(
            system_context=None,
            components=[],
            decisions=[],
            crosscutting_concerns=[],
            retrieved_facts=[],
        )

    def format_for_prompt(self, token_budget: int = 4000) -> str:
        """Format architecture context for use in LLM prompts.

        Formats the architecture context into a structured string
        suitable for inclusion in prompts. Filters facts by score > 0.5
        and respects the token budget parameter.

        Args:
            token_budget: Maximum approximate tokens for the output.
                         Uses rough estimate of 4 chars per token.

        Returns:
            Formatted string containing architecture context.
            Returns empty indicator if no context is available.
        """
        sections = []
        char_budget = token_budget * 4  # Rough estimate: 4 chars per token
        current_chars = 0

        # Check if context is empty
        has_content = (
            self.system_context is not None
            or len(self.components) > 0
            or len(self.decisions) > 0
            or len(self.crosscutting_concerns) > 0
            or len([f for f in self.retrieved_facts if f.get("score", 0) > 0.5]) > 0
        )

        if not has_content:
            return "No architecture context available."

        # System Context Section
        if self.system_context is not None:
            sys_section = self._format_system_context()
            if current_chars + len(sys_section) <= char_budget:
                sections.append(sys_section)
                current_chars += len(sys_section)

        # Components Section
        if self.components:
            comp_section = self._format_components()
            if current_chars + len(comp_section) <= char_budget:
                sections.append(comp_section)
                current_chars += len(comp_section)

        # Decisions Section
        if self.decisions:
            dec_section = self._format_decisions()
            if current_chars + len(dec_section) <= char_budget:
                sections.append(dec_section)
                current_chars += len(dec_section)

        # Crosscutting Concerns Section
        if self.crosscutting_concerns:
            xc_section = self._format_crosscutting_concerns()
            if current_chars + len(xc_section) <= char_budget:
                sections.append(xc_section)
                current_chars += len(xc_section)

        # Retrieved Facts Section (filtered by score > 0.5)
        high_score_facts = [
            f for f in self.retrieved_facts if f.get("score", 0) > 0.5
        ]
        if high_score_facts:
            facts_section = self._format_facts(high_score_facts, char_budget - current_chars)
            if facts_section:
                sections.append(facts_section)

        return "\n\n".join(sections)

    def _format_system_context(self) -> str:
        """Format system context section."""
        ctx = self.system_context
        return f"""## System Context
**{ctx.name}**
{ctx.purpose}

Bounded Contexts: {', '.join(ctx.bounded_contexts) if ctx.bounded_contexts else 'None defined'}
External Systems: {', '.join(ctx.external_systems) if ctx.external_systems else 'None defined'}"""

    def _format_components(self) -> str:
        """Format components section."""
        lines = ["## Components"]
        for comp in self.components:
            lines.append(f"- **{comp.name}**: {comp.description}")
        return "\n".join(lines)

    def _format_decisions(self) -> str:
        """Format decisions section."""
        lines = ["## Architecture Decisions"]
        for dec in self.decisions:
            lines.append(f"- **{dec.entity_id}**: {dec.title} ({dec.status})")
        return "\n".join(lines)

    def _format_crosscutting_concerns(self) -> str:
        """Format crosscutting concerns section."""
        lines = ["## Crosscutting Concerns"]
        for xc in self.crosscutting_concerns:
            lines.append(f"- **{xc.name}**: {xc.description}")
        return "\n".join(lines)

    def _format_facts(self, facts: List[Dict[str, Any]], remaining_chars: int) -> str:
        """Format retrieved facts section within budget."""
        if remaining_chars <= 100:
            return ""

        lines = ["## Retrieved Architecture Facts"]
        current = len(lines[0])

        for fact in sorted(facts, key=lambda f: f.get("score", 0), reverse=True):
            content = fact.get("content", "")
            fact_line = f"- {content}"
            if current + len(fact_line) + 1 > remaining_chars:
                break
            lines.append(fact_line)
            current += len(fact_line) + 1

        return "\n".join(lines) if len(lines) > 1 else ""
