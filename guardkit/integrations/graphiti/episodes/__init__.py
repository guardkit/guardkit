"""Episode schemas for Graphiti integration.

This package provides dataclass schemas for various episode types
that can be stored in the Graphiti knowledge graph.

Episode Types:
- ProjectArchitectureEpisode: Captures system architecture patterns
- ProjectOverviewEpisode: Captures project overview for North Star context
"""

from guardkit.integrations.graphiti.episodes.project_architecture import (
    ProjectArchitectureEpisode,
)
from guardkit.integrations.graphiti.episodes.project_overview import (
    ProjectOverviewEpisode,
)

__all__ = [
    "ProjectArchitectureEpisode",
    "ProjectOverviewEpisode",
]
