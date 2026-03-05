"""ArchitecturalDecisionEpisode schema for Graphiti integration.

This module provides the ArchitecturalDecisionEpisode dataclass for storing
architectural decisions, lessons learned, and failed approach knowledge.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ArchitecturalDecisionEpisode:
    """Architectural decision or lesson learned."""

    entity_type: str = "architectural_decision"

    title: str = ""
    summary: str = ""
    implications: List[str] = field(default_factory=list)
    evidence: str = ""
    decision_reference: str = ""
    date: str = ""

    def to_episode_content(self) -> str:
        """Convert to natural language for Graphiti."""
        implications_text = "\n".join(f"- {imp}" for imp in self.implications)
        return (
            f"Architectural Decision: {self.title}\n\n"
            f"{self.summary}\n\n"
            f"Implications:\n{implications_text}\n\n"
            f"Evidence: {self.evidence}\n"
            f"Decision: {self.decision_reference}\n"
            f"Date: {self.date}"
        )

    def get_entity_id(self) -> str:
        """Stable entity ID for upsert."""
        # Derive a slug from the title
        slug = self.title.lower().replace(" ", "_").replace(":", "")[:60]
        return f"arch_decision_{slug}"


# System-scoped architectural decisions to seed on init
ARCHITECTURAL_DECISION_DEFAULTS = {
    "graphiti_fidelity_limitation": ArchitecturalDecisionEpisode(
        title="Graphiti Fidelity Limitation: Facts Not Documents",
        summary=(
            "Graphiti is a knowledge graph that extracts semantic facts, not a "
            "document store that preserves verbatim content. Code examples cannot "
            "be reliably retrieved in copy-paste usable form."
        ),
        implications=[
            "Do NOT attempt to store/retrieve Python code blocks via Graphiti",
            "Pattern files (.claude/rules/patterns/) must remain as static markdown",
            "Use Graphiti for semantic search ('which pattern?'), not code retrieval",
            "Content preview (500 chars) is sufficient for semantic search episodes",
            "FEAT-CR01 context reduction is Graphiti-independent (path-gating + trimming)",
        ],
        evidence="docs/reviews/graphiti_enhancement/graphiti_code_retrieval_fidelity.md",
        decision_reference="TASK-REV-CROPT (pivot to Graphiti-independent reduction)",
        date="2026-02-05",
    ),
}
